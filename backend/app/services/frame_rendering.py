"""Turn per-window note values into per-frame colour images.

Frame ``f`` covers ``[f / frame_rate, (f + 1) / frame_rate)`` seconds. It is the mean of
the windows that start inside that period, or, if none does, the most recent window that
started before the period (which is the window covering its start when windows are consecutive).
The note values of a frame (one row of 88) are smoothed over the earlier frames (see ``smooth_frames``) and drawn as the chosen image type (see ``image_types``).
``contour`` draws the 12 x 7 grid of the 84 notes (one row for each octave, one column for each note name) as a filled contour map (see ``contour``); a higher resolution
(1 to 5) first interpolates the grid to 12 r x 7 r values (see ``resolution``), and a number of notes below 84 builds the picture from only the notes with the most
energy in the file, spread over the whole grid (see ``note_selection``). An interpolate value above 1 draws only every n-th frame and makes the frames in between from
their neighbors with Pillow (see ``frame_interpolation``). A threshold can hide faint notes: a note below it is 0 (see ``hidden_below``). The other image types draw
circles, bars, a histogram, rings or lines from the note values or from the measurements of the whole file (``decay``, ``decay_exp``, ``polar_chords``,
``energy_graphs``, ``chromatic_decay``, ``rhythm_circles``, ``chromatic_wireframe``).
"""

import math
import numbers
from pathlib import Path

import numpy as np

from .colormaps import DEFAULT_COLORMAP, check_beat, check_colormap
from .beat_wave import DEFAULT_WAVE_COUNT, check_wave_count
from .decay import DEFAULT_DECAY_AMOUNTS, DEFAULT_DECAY_RATE, check_decay_amounts, check_decay_rate, circle_points, write_decay_frames
from .chromatic_decay import CHROMATIC_TYPES, check_chromatic_rate, circle_points as chromatic_points, write_chromatic_frames
from .chromatic_wireframe import write_wireframe_frames
from .decay_exp import circle_points as decay_exp_points
from .energy_graphs import EnergyGraphData, write_energy_frames
from .rhythm_circles import RhythmData, write_rhythm_frames
from .polar_chords import DEFAULT_POLAR_NOTES, check_polar_notes, polar_bars, write_polar_frames
from .contour import write_contour_frames
from .gaussian import DEFAULT_GAUSSIAN, blur_frames, check_gaussian
from .frame_interpolation import DEFAULT_INTERPOLATE, check_interpolate, key_frames, write_interpolated_frames
from .image_types import DEFAULT_IMAGE_TYPE, check_image_type
from .note_analysis import NOTE_COUNT, AnalysisResult
from .note_grid import GRID_COLUMNS, GRID_ROWS
from .note_layout import DEFAULT_NOTE_LAYOUT, check_note_layout
from .note_selection import DEFAULT_NOTE_COUNT, check_note_count, spread_notes
from .resolution import DEFAULT_RESOLUTION, check_resolution, interpolate_grid

# 12 columns (the notes of an octave) by 7 rows (octaves) of notes spread over a 600 x 400 frame (see ``note_grid``).
SHOWN_NOTES = GRID_COLUMNS * GRID_ROWS  # notes 0..83 are drawn; the four highest (84..87) are not
IMAGE_WIDTH = 600
IMAGE_HEIGHT = 400

# Smoothing mixes each frame with the earlier frames of a window (0 = none). The smoothing is the weight of each earlier
# frame against a weight of 1 for the current one; the window is how many earlier frames are looked at. Fixed ranges;
# 0 and 1 are the defaults.
MIN_SMOOTHING = 0.0
MAX_SMOOTHING = 0.8
DEFAULT_SMOOTHING = 0.0
MIN_SMOOTHING_WINDOW = 1
MAX_SMOOTHING_WINDOW = 20
DEFAULT_SMOOTHING_WINDOW = 1

# The threshold hides faint notes: a drawn note whose smoothed value in a frame is below this percentage of the largest
# note value in the whole file is 0. 0 is off (the default); the page's slider ends at 10.
MIN_THRESHOLD = 0
MAX_THRESHOLD = 10
DEFAULT_THRESHOLD = 0

assert SHOWN_NOTES <= NOTE_COUNT
assert IMAGE_WIDTH * 2 == IMAGE_HEIGHT * 3  # exactly 3:2

# Guards ceil() against floating-point noise such as 5.000000000000001.
_EPSILON = 1e-9
# Samples. A window starting this close below a frame boundary still belongs to the later frame.
_BOUNDARY_TOLERANCE = 1e-6


def frame_count(sample_count: int, sample_rate: float, frame_rate: float) -> int:
    """Number of frames for audio of ``sample_count`` samples: duration * frame rate, rounded up."""
    return max(0, math.ceil(sample_count * frame_rate / sample_rate - _EPSILON))

def frame_windows(result: AnalysisResult, frame_rate: float, frames: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Which windows of ``result`` belong to each of ``frames`` frames: three integer arrays ``(first, stop, earlier)``, one entry per frame.

    Windows are assigned to frames by their exact start position (``k * step``), not by the rounded start sample: frame ``i`` owns the windows
    ``first[i]`` up to (not including) ``stop[i]``. A frame that owns none (``stop == first``) falls back to window ``earlier[i]``, the last
    window that started before it (the first window when there is none). Every window is owned by exactly one frame.
    """
    if frames == 0 or result.frames.shape[0] == 0:
        zeros = np.zeros(frames, dtype=np.intp)
        return zeros, zeros.copy(), zeros.copy()
    positions = result.window_positions
    boundaries = np.arange(frames + 1) * (result.sample_rate / frame_rate) - _BOUNDARY_TOLERANCE
    edges = np.searchsorted(positions, boundaries, side="left")
    first, stop = edges[:-1], edges[1:]
    return first, stop, np.maximum(first - 1, 0)


def average_frames(result: AnalysisResult, frame_rate: float, frames: int) -> np.ndarray:
    """Average the window rows of ``result`` into ``frames`` rows of 88 values.

    Windows are assigned to frames as ``frame_windows`` says. A frame whose period has no window start uses the last window that started before it.
    """
    windows = result.frames
    if frames == 0 or windows.shape[0] == 0:
        return np.zeros((frames, NOTE_COUNT))

    first, stop, earlier = frame_windows(result, frame_rate, frames)
    running = np.vstack([np.zeros((1, NOTE_COUNT)), np.cumsum(windows, axis=0)])
    counts = stop - first
    has_windows = counts > 0
    out = windows[earlier].copy()
    out[has_windows] = (running[stop[has_windows]] - running[first[has_windows]]) / counts[has_windows, None]
    return np.maximum(out, 0.0)

def _check_smoothing_window(window) -> int:
    if (
        isinstance(window, bool)
        or not isinstance(window, numbers.Integral)
        or not MIN_SMOOTHING_WINDOW <= window <= MAX_SMOOTHING_WINDOW
    ):
        raise ValueError(
            f"The smoothing window must be a whole number from {MIN_SMOOTHING_WINDOW} to {MAX_SMOOTHING_WINDOW}."
        )
    return int(window)

def smooth_frames(
    frames: np.ndarray, smoothing: float = DEFAULT_SMOOTHING, window: int = DEFAULT_SMOOTHING_WINDOW
) -> np.ndarray:
    """A weighted average of every note over the current frame and the ``window`` frames before it.

    ``frames`` has one row per frame and one column per note. With ``s`` the smoothing and ``w`` the window, row ``t``
    becomes ``( A[t] + s*A[t-1] + ... + s*A[t-k] ) / ( 1 + s*k )`` where ``A`` are the *unsmoothed* rows and
    ``k = min(t, w)`` is the number of earlier rows that exist. The weights are divided by their sum, so a constant
    value stays constant and the first row is left as it is. Only the row itself and earlier rows are used, never later
    ones, and never earlier smoothed results, so a value is forgotten exactly ``w`` rows after it last occurred. Each
    note uses only its own history. ``smoothing`` is a number from 0.0 to 0.8 and ``window`` a whole number from 1 to
    20; smoothing 0 returns the values unchanged for every window. The input is never modified.
    """
    if (
        isinstance(smoothing, bool)
        or not isinstance(smoothing, numbers.Real)
        or not math.isfinite(smoothing)
        or not MIN_SMOOTHING <= smoothing <= MAX_SMOOTHING
    ):
        raise ValueError(f"The smoothing must be a number from {MIN_SMOOTHING} to {MAX_SMOOTHING}.")
    window = _check_smoothing_window(window)
    out = np.array(frames, dtype=np.float64, copy=True)
    if smoothing == 0 or out.shape[0] < 2:
        return out
    s = float(smoothing)
    total = out.copy()
    for j in range(1, min(window, out.shape[0] - 1) + 1):
        total[j:] += s * out[:-j]
    earlier = np.minimum(np.arange(out.shape[0]), window)
    total /= (1.0 + s * earlier).reshape((-1,) + (1,) * (out.ndim - 1))
    return total

def _check_threshold(threshold) -> float:
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, numbers.Real)
        or not math.isfinite(threshold)
        or not MIN_THRESHOLD <= threshold <= MAX_THRESHOLD
    ):
        raise ValueError(f"The threshold must be a number from {MIN_THRESHOLD} to {MAX_THRESHOLD}.")
    return float(threshold)

def hidden_below(values: np.ndarray, peak: float, threshold: float = DEFAULT_THRESHOLD) -> np.ndarray:
    """Which values are too faint to show: a boolean array of the shape of ``values`` (any grid, drawn values).

    A value is hidden when it is *strictly* below ``threshold`` percent of ``peak`` (the largest note value of the whole
    file); one exactly at the threshold is shown. With threshold 0, or when ``peak`` is 0, nothing is hidden.
    """
    threshold = _check_threshold(threshold)
    return np.asarray(values, dtype=np.float64) < threshold / 100.0 * float(peak)


def write_frames(
    frames: np.ndarray,
    directory: Path,
    colormap: str = DEFAULT_COLORMAP,
    smoothing: float = DEFAULT_SMOOTHING,
    smoothing_window: int = DEFAULT_SMOOTHING_WINDOW,
    threshold: float = DEFAULT_THRESHOLD,
    image_type: str = DEFAULT_IMAGE_TYPE,
    resolution: int = DEFAULT_RESOLUTION,
    note_count: int = DEFAULT_NOTE_COUNT,
    interpolate: int = DEFAULT_INTERPOLATE,
    gaussian: float = DEFAULT_GAUSSIAN,
    beat: np.ndarray | None = None,
    note_layout: str = DEFAULT_NOTE_LAYOUT,
    decay_rate: float = DEFAULT_DECAY_RATE,
    wave_count: int = DEFAULT_WAVE_COUNT,
    decay_amounts: tuple[float, float, float, float] = DEFAULT_DECAY_AMOUNTS,
    polar_notes: int = DEFAULT_POLAR_NOTES,
    energy: EnergyGraphData | None = None,
    rhythm: RhythmData | None = None,
) -> None:
    """Save one PNG per row of ``frames`` (averaged note values) as ``frame_000000.png`` and up.

    ``smoothing`` (0.0 to 0.8, default none) and ``smoothing_window`` (a whole number from 1 to 20, default 1) smooth
    the note values over the frames: a frame is the weighted average of itself and the ``smoothing_window`` frames
    before it, each of those with the weight ``smoothing`` (see ``smooth_frames``). Smoothing 0 changes nothing.

    ``threshold`` (0 to 10, default 0 = off) is a percentage of the largest note value in the file (after smoothing): a
    note below it is 0 in that frame (``hidden_below``), whatever the colormap is.

    ``image_type`` is ``contour`` (the default, see below), ``decay``, ``decay-exp``, ``polar-chords``, ``energy-graphs``, ``chromatic-decay``, ``rhythm-circles``
    or ``chromatic-wireframe`` (see ``image_types``).

    ``image_type="contour"`` draws the grid of values (the 84 drawn notes, or the finer interpolated grid; the values the
    threshold hides are 0) as a filled contour map in the ``colormap``, with matplotlib (see ``contour``): the contour levels are
    chosen by matplotlib, and the color scale is *linear* from 0 to the largest smoothed value in the whole file.

    ``resolution`` (a whole number from 1 to 5, default 1) makes the grid that every frame is drawn from finer: the 7 x 12
    grid of the smoothed values of the drawn notes is interpolated to 7r x 12r values (``interpolate_grid``: ``np.linspace``
    positions and ``np.interp``, corners kept, no value outside the original range) *after* the smoothing, and the
    threshold and the colors are worked out on those values. The picture keeps its size; the scale of
    the colors and the threshold's reference are the largest value of the whole file before the interpolation. Frames of
    the original grid (1) are written exactly as without the setting.

    ``note_count`` (a whole number from 12 to 84, default 84 = all drawn notes) builds the picture from only the
    ``note_count`` notes with the most energy, the energy of a note being the sum of its smoothed values over the whole
    file, so the same notes are used in every frame. Their values are spread over the 84 values of the original grid
    (``spread_notes``: ``np.linspace`` positions and ``np.interp``, in order of pitch) *after* the smoothing and before the
    resolution step, the threshold and the colors, which work on the spread values as they do on the note values. The scale
    of the colors and the threshold's reference are still the largest value of the whole file over all 88 notes, so the
    same strength has the same color at every number of notes. With 84 notes nothing changes.

    ``interpolate`` (a whole number from 1 to 5, default 1 = every frame drawn) draws only every n-th frame, the frames
    ``0, n, 2n, ...`` (counting from 0) and always the last one, exactly as they are drawn at 1; the other frames are
    made from their two nearest drawn frames with the Pillow library (see ``frame_interpolation``): ``Image.blend`` mixes
    them with the weight of the frame's position in its gap. The smoothing, the notes, the resolution, the threshold and
    the colors are worked out for all frames as before; only the drawing is skipped. The number of frames, their names and the size do not change, and at 1 nothing
    changes. ``resolution``, ``note_count``, ``interpolate`` and ``gaussian`` describe the grid of ``contour`` and are accepted and ignored by the other image types.

    ``beat`` (feature 024; ``None`` or one number from 0 to 1 for each frame, the frame's place in the local energy peak,
    see ``local_peaks``) is used by ``contour`` (its beat wave, see ``wave_count``), ``decay``, ``decay-exp``, ``polar-chords``, ``chromatic-decay`` and
    ``chromatic-wireframe``. The other image types ignore it.

    ``note_layout`` (``"rows"``, the default, or ``"spiral"``, see ``note_layout``) says which note is drawn in which cell of the 12 x 7 grid
    for ``decay``, ``decay-exp`` and ``polar-chords``; the other image types check it and ignore it. With ``rows`` the pictures are what
    they always were. Only the place of a note changes: its value, strength, hiding and color are those of the note.

    ``image_type="decay"`` draws 84 circles on the 12 x 7 grid, each as one flat disc
    that keeps points from 0 to 64 from frame to frame (see ``decay``): the five loudest notes of a frame gain 24, 20, 16, 12 and 8 points
    plus up to 8 from ``beat``, every ``decay_rate`` frames (a number from 0.25 to 4 in steps of 0.25, default 1; below 1 several steps a frame) each circle gives points to
    each neighbour at the rate of its saturation level (``decay_amounts``: four numbers from 0.5 to 3, the points given to each neighbour per
    frame by a low, medium, high and saturated circle; default 0.5, 1, 2, 3); the points set the size (full from 24) and the color (the last from 32). Smoothing, the colormap,
    ``beat`` and ``note_layout`` apply; every other setting is checked and ignored. ``decay_rate`` and ``decay_amounts`` are checked
    for every image type and have no effect on the others.

    ``image_type="decay-exp"`` is ``decay`` with two amounts changed (see ``decay_exp``): a note that would gain ``g`` points gains ``g * exp(-g / 8)``, and
    a circle with ``p`` points gives each neighbour ``sin(pi / 2 * p / 64) ** 2`` per frame instead of the amount of its saturation level. ``decay_rate``,
    ``beat``, ``note_layout``, smoothing and the colormap apply; ``decay_amounts`` and every other setting are checked and ignored.

    ``image_type="chromatic-decay"`` is ``decay-exp`` for the 12 chromatic tones only (see ``chromatic_decay``): 12 circles on a ring in circle-of-fifths order,
    charged by the loudest octave of each letter, whose points decay to the letters 5 and 7 above. ``decay_rate`` is for this type a **whole number from 1 to 10**
    (frames between decay steps; anything else is refused with ``ValueError``); ``beat``, smoothing and the colormap apply; ``note_layout``, ``decay_amounts``
    and every other setting are checked and ignored; ``threshold`` (0 to 10, 0 off) applies as a percent of the largest smoothed note value of the whole file: a
    note strictly below it is 0 before the letters are charged (feature 037). With a ``beat`` the middle of the ring of letters also has a target of 12 concentric rings, 140 pixels
    across, that shows the distance from the local peak of the current frame and of the frames before it (feature 036); without one there is no target.

    ``image_type="energy-graphs"`` draws a running histogram of the notes with two data sets, the rank points and the quasi-decibel amplitudes (see
    ``energy_graphs``), from ``energy``, the totals of every frame made by ``energy_graphs.frame_energy`` (required for this type, ignored by the others; it
    must have one frame for each row of ``frames``). Only the colormap applies; every other setting is checked and ignored.

    ``image_type="chromatic-wireframe"`` draws the points of ``chromatic-decay`` (the same simulation, with the same decay rate, whole number 1 to 10, and threshold) as
    a ridge plot in three dimensions (see ``chromatic_wireframe``): one line across the 12 letters for each frame, the newest in front and the earlier frames behind it
    as far as there is room, every line in the colormap color of its frame's place in the
    ``beat`` (the last color at the top of a peak; the first for every line without a beat). Smoothing, the colormap, the threshold and ``beat`` apply; ``note_layout``,
    ``decay_amounts`` and every other setting are checked and ignored.

    ``image_type="rhythm-circles"`` draws eight concentric notched rings turned by the tempo of the local peaks, the aggregated tempos (the average or the fastest) of its latest 2, 4 and 8 peaks and the rates of change of all four (see
    ``rhythm_circles``), from ``rhythm``, the angles of every frame made by ``rhythm_circles.rhythm_angles`` (required for this type, ignored by the others; it
    must have one frame for each row of ``frames``). Only the colormap applies; every other setting is checked and ignored.

    ``image_type="polar-chords"`` draws a polar bar graph (see ``polar_chords``): the ``polar_notes`` loudest notes of a frame (a whole number from 5 to 8,
    default 5, checked for every image type and used by this one only) as bars clockwise from the top, one arc of 84 for each note (in the order of the
    cells of ``note_layout``: ``rows`` is the order of pitch), and the chord that
    ``chords.measure_chords`` records for the frame as one bar counterclockwise, one arc of 84 for each of the 12 root letters and 7 chord types (the types of a letter together, the letters from A). Every bar
    reaches out to ``0.5 + 0.5 * beat`` of the full radius. Smoothing, the colormap, ``beat`` and ``note_layout`` apply; every other setting is checked and ignored.

    ``wave_count`` (a whole number from 2 to 10, default 4) is the number of waves of the **beat wave** of ``contour`` (see ``beat_wave``): with
    ``beat`` given, the frame's grid of values is multiplied by ``1 - pattern * beat`` before the contour is drawn, with a pattern of concentric
    rings with ``wave_count`` waves across the largest dimension of the grid; a frame at beat 0 (and every frame with ``beat=None``) is the plain
    contour. It is checked for every image type and has no effect on the others.

    Every argument is checked before anything is written.
    """
    colormap = check_colormap(colormap)
    _check_threshold(threshold)
    _check_smoothing_window(smoothing_window)
    image_type = check_image_type(image_type)
    resolution = check_resolution(resolution)
    note_count = check_note_count(note_count)
    interpolate = check_interpolate(interpolate)
    gaussian = check_gaussian(gaussian)
    note_layout = check_note_layout(note_layout)
    decay_rate = check_chromatic_rate(decay_rate) if image_type in CHROMATIC_TYPES else check_decay_rate(decay_rate)  # a whole number from 1 to 10 for Chromatic Decay and Chromatic Wireframe
    decay_amounts = check_decay_amounts(decay_amounts)
    wave_count = check_wave_count(wave_count)
    polar_notes = check_polar_notes(polar_notes)
    if beat is not None:
        beat = check_beat(beat, len(frames))  # checked for every image type, used by contour, decay, decay-exp, polar-chords, chromatic-decay and chromatic-wireframe
    smoothed = smooth_frames(frames, smoothing, smoothing_window)
    peak = float(smoothed.max()) if smoothed.size else 0.0
    if image_type == "decay":  # 84 discs that keep points from frame to frame; the grid settings above are checked and not used
        points = circle_points(smoothed, beat, note_layout, decay_rate, decay_amounts)
        write_decay_frames(points, colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT)
        return
    if image_type == "decay-exp":  # the same discs with the points gained and lost along an exponential curve; decay_amounts is checked and not used
        points = decay_exp_points(smoothed, beat, note_layout, decay_rate)
        write_decay_frames(points, colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT)
        return
    if image_type == "chromatic-decay":  # the 12 letters on a ring, decaying to the letters 5 and 7 above; note_layout and decay_amounts are checked and not used
        points = chromatic_points(smoothed, beat, decay_rate, threshold)  # a note under the threshold of the whole file is 0 before the letters are charged
        write_chromatic_frames(points, colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT, beat=beat)  # the beat also fills the target in the middle
        return
    if image_type == "chromatic-wireframe":  # the same points as chromatic-decay, drawn as a line for each frame in three dimensions; note_layout and decay_amounts are checked and not used
        points = chromatic_points(smoothed, beat, decay_rate, threshold)
        write_wireframe_frames(points, colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT, beat=beat)  # the beat decides the color of every line
        return
    if image_type == "energy-graphs":  # a histogram of two data sets, made from ``energy`` (the rest of the settings above are checked and not used)
        if energy is None:
            raise ValueError("The energy graphs need the energy data.")
        if energy.frame_count != len(frames):
            raise ValueError(f"The energy data has {energy.frame_count} frames but {len(frames)} were given.")
        write_energy_frames(energy, colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT)
        return
    if image_type == "rhythm-circles":  # eight notched rings turned by ``rhythm`` (the rest of the settings above are checked and not used)
        if rhythm is None:
            raise ValueError("Rhythm Circles needs the rhythm data.")
        if rhythm.frame_count != len(frames):
            raise ValueError(f"The rhythm data has {rhythm.frame_count} frames but {len(frames)} were given.")
        write_rhythm_frames(rhythm, colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT)
        return
    if image_type == "polar-chords":  # a polar bar graph: the loudest notes clockwise, the chord counterclockwise; the grid settings above are checked and not used
        write_polar_frames(polar_bars(smoothed, beat, polar_notes, note_layout), colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT)
        return
    columns, rows = GRID_COLUMNS * resolution, GRID_ROWS * resolution  # the contour: the last image type
    shown = spread_notes(smoothed[:, :SHOWN_NOTES], note_count)  # (the contour always has the rows layout)
    values = interpolate_grid(shown, GRID_COLUMNS, GRID_ROWS, resolution)
    hidden = hidden_below(values, peak, threshold)
    frames_to_draw = key_frames(values.shape[0], interpolate)
    values[hidden] = 0
    write_contour_frames(
        values,
        peak,
        colormap,
        directory,
        columns,
        rows,
        IMAGE_WIDTH,
        IMAGE_HEIGHT,
        indices=frames_to_draw,
        beat=beat,
        waves=wave_count,
    )
    blur_frames(directory, frames_to_draw, gaussian)  # the drawn frames only: an in-between frame is a blend of blurred frames
    write_interpolated_frames(directory, values.shape[0], interpolate)
