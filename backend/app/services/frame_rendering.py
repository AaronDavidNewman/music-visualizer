"""Turn per-window note values into per-frame colour images.

Frame ``f`` covers ``[f / frame_rate, (f + 1) / frame_rate)`` seconds. It is the mean of the windows that start inside
that period, or, if none does, the most recent window that started before the period (which is the window covering its
start when windows are consecutive). The note values of a frame (one row of 88) are drawn as the chosen image type (see
``image_types``); this averaging is the only smoothing of the note data (feature 043: the frequency buffers are always 60 ms
apart, so the frame rate alone decides how many of them each frame averages). ``contour`` draws the 12 x 7 grid of
the 84 notes (one row for each octave, one column for each note name) as a filled contour map (see ``contour``); a
higher resolution (1 to 5) first interpolates the grid to 12 r x 7 r values (see ``resolution``), and a number of notes
below 84 builds the picture from only the notes with the most energy in the file, spread over the whole grid (see
``note_selection``). An interpolate value above 1 draws only every n-th frame and makes the frames in between from their
neighbors with Pillow (see ``frame_interpolation``). A threshold can hide faint notes: a note below it is 0 (see
``hidden_below``). The other image types draw circles, bars, a histogram, rings or lines from the note values or from
the measurements of the whole file (``decay``, ``decay_exp``, ``polar_chords``, ``energy_graphs``, ``chromatic_decay``,
``rhythm_circles``, ``chromatic_wireframe``, ``polychord``).

These are the shared steps AVERAGE and DRAW of the pipeline overview in ``image_types``; the job does steps 1 to 3 and
calls ``write_frames()`` for the rest.

Order of operations:
    1. Count the frames - ``frame_count()`` - the duration times the frame rate, rounded up: a whole number.
    2. Decide which analysis windows each frame owns - ``frame_windows()`` (called by ``average_frames()``) - three
       ``WindowRanges`` ``(frames,)``: ``first``, ``stop`` and ``earlier``.
    3. Average the windows into frames - ``average_frames()`` - ``NoteStrengths`` ``(frames, 88)``: the mean of the
       windows a frame owns (or the last earlier window).
    4. Check every setting before anything is written - ``write_frames()`` - colormap, threshold, image type, resolution,
       note count, interpolate, gaussian, note layout, decay rate and amounts, wave count, polar notes, extra notes
       (k, 0 to the number of notes of the picture) and ``beat`` (``BeatPositions`` ``(frames,)`` or ``None``).
    5. Find the largest note value of the whole file - ``write_frames()`` - the ``peak`` that the threshold and the
       colors are measured against.
    6. Draw, by image type (each type's own steps are in its module and in the overview of ``image_types``):
         * ``decay``, ``decay-exp``, ``chromatic-decay``, ``chromatic-wireframe``: simulate the circles' points from the
           note values (the five loudest notes or letters are the held ones, ``held_notes.hold_loudest()``, inside the
           gains), then draw them (``decay``, ``decay_exp``, ``chromatic_decay``, ``chromatic_wireframe``);
         * ``polar-chords``: ``polar_chords.polar_bars()`` (its loudest notes are the held ones), then ``write_polar_frames()``; ``energy-graphs`` and
           ``rhythm-circles``: draw from the measurements the job made (``energy``, ``rhythm``), which must have one
           frame for each row; ``polychord``: draw from the note values, the beat and the tempos the job measured
           (``polychord``, which must have one tempo for each row) with the four settings
           (``polychord.write_polychord_frames()``);
         * ``contour``: keep the 84 drawn notes and spread the ``note_count`` loudest over them
           (``note_selection.spread_notes()``) - make the grid finer (``resolution.interpolate_grid()``) - hide the
           faint values (``hidden_below()``) - draw the drawn frames (``contour.write_contour_frames()``) - blur them
           (``gaussian.blur_frames()``) - make the in-between frames
           (``frame_interpolation.write_interpolated_frames()``).
"""

import math
import numbers
from pathlib import Path

import numpy as np

from .array_types import ArrayLike, BeatPositions, HiddenMask, NoteStrengths, WindowRanges
from .colormaps import DEFAULT_COLORMAP, check_beat, check_colormap
from .beat_wave import DEFAULT_WAVE_COUNT, check_wave_count
from .decay import DEFAULT_DECAY_AMOUNTS, DEFAULT_DECAY_RATE, check_decay_amounts, check_decay_rate, circle_points, write_decay_frames
from .chromatic_decay import CHROMATIC_TYPES, check_chromatic_rate, circle_points as chromatic_points, write_chromatic_frames
from .chromatic_wireframe import write_wireframe_frames
from .decay_exp import circle_points as decay_exp_points
from .energy_graphs import EnergyGraphData, write_energy_frames
from .polychord import DEFAULT_POLYCHORD_SETTINGS, PolychordData, PolychordSettings, check_polychord_settings, write_polychord_frames
from .rhythm_circles import RhythmData, write_rhythm_frames
from .polar_chords import DEFAULT_POLAR_NOTES, check_polar_notes, polar_bars, write_polar_frames
from .held_notes import check_extra_notes, notes_of
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

# The threshold hides faint notes: a drawn note whose value in a frame is below this percentage of the largest
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

def frame_windows(result: AnalysisResult, frame_rate: float, frames: int) -> tuple[WindowRanges, WindowRanges, WindowRanges]:
    """Which windows of ``result`` belong to each of ``frames`` frames: three integer arrays ``(first, stop, earlier)``,
    one entry per frame.

    Windows are assigned to frames by their exact start position (``k * step``), not by the rounded start sample: frame
    ``i`` owns the windows ``first[i]`` up to (not including) ``stop[i]``. A frame that owns none (``stop == first``)
    falls back to window ``earlier[i]``, the last window that started before it (the first window when there is none).
    Every window is owned by exactly one frame.

    Returns:
        A tuple of three ``WindowRanges`` ``(frames,)``: ``first`` (the first analysis window each frame owns), ``stop``
        (the window after the last it owns) and ``earlier`` (the last window that started before the frame, to fall back
        to). Window numbers are counted from 0 in time order.
    """
    if frames == 0 or result.frames.shape[0] == 0:
        zeros = np.zeros(frames, dtype=np.intp)
        return zeros, zeros.copy(), zeros.copy()
    positions = result.window_positions
    boundaries = np.arange(frames + 1) * (result.sample_rate / frame_rate) - _BOUNDARY_TOLERANCE
    edges = np.searchsorted(positions, boundaries, side="left")
    first, stop = edges[:-1], edges[1:]
    return first, stop, np.maximum(first - 1, 0)


def average_frames(result: AnalysisResult, frame_rate: float, frames: int) -> NoteStrengths:
    """Average the window rows of ``result`` into ``frames`` rows of 88 values.

    Windows are assigned to frames as ``frame_windows`` says. A frame whose period has no window start uses the last
    window that started before it.

    Returns:
        ``NoteStrengths`` ``(frames, 88)`` - the strength of each of the 88 notes in each frame: the mean of the
        analysis windows the frame owns (``result.frames`` is ``(windows, 88)``), or the last window before it when it
        owns none; never negative.
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

def _check_threshold(threshold: object) -> float:
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, numbers.Real)
        or not math.isfinite(threshold)
        or not MIN_THRESHOLD <= threshold <= MAX_THRESHOLD
    ):
        raise ValueError(f"The threshold must be a number from {MIN_THRESHOLD} to {MAX_THRESHOLD}.")
    return float(threshold)

def hidden_below(values: ArrayLike, peak: float, threshold: float = DEFAULT_THRESHOLD) -> HiddenMask:
    """Which values are too faint to show: a boolean array of the shape of ``values`` (any grid, drawn values).

    A value is hidden when it is *strictly* below ``threshold`` percent of ``peak`` (the largest note value of the whole
    file); one exactly at the threshold is shown. With threshold 0, or when ``peak`` is 0, nothing is hidden.

    Arrays:
        ``values``: ``ArrayLike`` any shape - note strengths or grid values (0 or more); ``peak`` is the largest such
            value of the whole file.

    Returns:
        ``HiddenMask`` the shape of ``values`` - True where the value is strictly below ``threshold`` percent of
        ``peak``.
    """
    threshold = _check_threshold(threshold)
    return np.asarray(values, dtype=np.float64) < threshold / 100.0 * float(peak)


def _check_extra_notes(value: object, image_type: str, polar_notes: int, polychord_settings: PolychordSettings) -> int:
    """The Extra notes setting k for ``write_frames``: 0 (off) or a whole number from 1 to the number of notes of the picture.

    The number of notes n is 5 for ``decay``, ``decay-exp``, ``chromatic-decay`` and ``chromatic-wireframe``, ``polar_notes`` for ``polar-chords`` and the notes of
    ``polychord_settings`` for ``polychord``; a picture that does not take the n loudest notes accepts 0 to 8 and ignores it.

    Returns:
        The number as an ``int``.
    """
    if isinstance(value, numbers.Real) and not isinstance(value, bool) and value == 0:
        return 0
    return check_extra_notes(value, notes_of(image_type, polar_notes, polychord_settings.notes))


def write_frames(
    frames: NoteStrengths,
    directory: Path,
    colormap: str = DEFAULT_COLORMAP,
    threshold: float = DEFAULT_THRESHOLD,
    image_type: str = DEFAULT_IMAGE_TYPE,
    resolution: int = DEFAULT_RESOLUTION,
    note_count: int = DEFAULT_NOTE_COUNT,
    interpolate: int = DEFAULT_INTERPOLATE,
    gaussian: float = DEFAULT_GAUSSIAN,
    beat: BeatPositions | None = None,
    note_layout: str = DEFAULT_NOTE_LAYOUT,
    decay_rate: float = DEFAULT_DECAY_RATE,
    wave_count: int = DEFAULT_WAVE_COUNT,
    decay_amounts: tuple[float, float, float, float] = DEFAULT_DECAY_AMOUNTS,
    polar_notes: int = DEFAULT_POLAR_NOTES,
    energy: EnergyGraphData | None = None,
    rhythm: RhythmData | None = None,
    polychord: PolychordData | None = None,
    polychord_settings: PolychordSettings = DEFAULT_POLYCHORD_SETTINGS,
    extra_notes: int = 0,
) -> None:
    """Save one PNG per row of ``frames`` (averaged note values) as ``frame_000000.png`` and up.

    ``frames`` are drawn as they are: there is no smoothing between the averaging of the frequency buffers into frames
    (``average_frames``) and the drawing.

    ``threshold`` (0 to 10, default 0 = off) is a percentage of the largest note value in the file: a
    note below it is 0 in that frame (``hidden_below``), whatever the colormap is.

    ``image_type`` is ``contour`` (the default, see below), ``decay``, ``decay-exp``, ``polar-chords``,
    ``energy-graphs``, ``chromatic-decay``, ``rhythm-circles``, ``chromatic-wireframe`` or ``polychord`` (see
    ``image_types``).

    ``image_type="contour"`` draws the grid of values (the 84 drawn notes, or the finer interpolated grid; the values
    the threshold hides are 0) as a filled contour map in the ``colormap``, with matplotlib (see ``contour``): the
    contour levels are chosen by matplotlib, and the color scale is *linear* from 0 to the largest note value in the
    whole file.

    ``resolution`` (a whole number from 1 to 5, default 1) makes the grid that every frame is drawn from finer: the 7 x
    12 grid of the note values of the drawn notes is interpolated to 7r x 12r values (``interpolate_grid``:
    ``np.linspace`` positions and ``np.interp``, corners kept, no value outside the original range), and the threshold and the colors are worked out on those values. The picture keeps its size; the scale of
    the colors and the threshold's reference are the largest value of the whole file before the interpolation. Frames of
    the original grid (1) are written exactly as without the setting.

    ``note_count`` (a whole number from 12 to 84, default 84 = all drawn notes) builds the picture from only the
    ``note_count`` notes with the most energy, the energy of a note being the sum of its values over the whole
    file, so the same notes are used in every frame. Their values are spread over the 84 values of the original grid
    (``spread_notes``: ``np.linspace`` positions and ``np.interp``, in order of pitch) before
    the resolution step, the threshold and the colors, which work on the spread values as they do on the note values.
    The scale of the colors and the threshold's reference are still the largest value of the whole file over all 88
    notes, so the same strength has the same color at every number of notes. With 84 notes nothing changes.

    ``interpolate`` (a whole number from 1 to 5, default 1 = every frame drawn) draws only every n-th frame, the frames
    ``0, n, 2n, ...`` (counting from 0) and always the last one, exactly as they are drawn at 1; the other frames are
    made from their two nearest drawn frames with the Pillow library (see ``frame_interpolation``): ``Image.blend``
    mixes them with the weight of the frame's position in its gap. The notes, the resolution, the
    threshold and the colors are worked out for all frames as before; only the drawing is skipped. The number of frames,
    their names and the size do not change, and at 1 nothing changes. ``resolution``, ``note_count``, ``interpolate``
    and ``gaussian`` describe the grid of ``contour`` and are accepted and ignored by the other image types.

    ``beat`` (feature 024; ``None`` or one number from 0 to 1 for each frame, the frame's place in the local energy
    peak, see ``local_peaks``) is used by ``contour`` (its beat wave, see ``wave_count``), ``decay``, ``decay-exp``,
    ``polar-chords``, ``chromatic-decay`` and ``chromatic-wireframe``. The other image types ignore it.

    ``note_layout`` (``"rows"``, the default, or ``"spiral"``, see ``note_layout``) says which note is drawn in which
    cell of the 12 x 7 grid for ``decay``, ``decay-exp`` and ``polar-chords``; the other image types check it and ignore
    it. With ``rows`` the pictures are what they always were. Only the place of a note changes: its value, strength,
    hiding and color are those of the note.

    ``image_type="decay"`` draws 84 circles on the 12 x 7 grid, each as one flat disc that keeps points from 0 to 64
    from frame to frame (see ``decay``): the five loudest notes of a frame gain 24, 20, 16, 12 and 8 points plus up to 8
    from ``beat``, every ``decay_rate`` frames (a number from 0.25 to 4 in steps of 0.25, default 1; below 1 several
    steps a frame) each circle gives points to each neighbour at the rate of its saturation level (``decay_amounts``:
    four numbers from 0.5 to 3, the points given to each neighbour per frame by a low, medium, high and saturated
    circle; default 0.5, 1, 2, 3); the points set the size (full from 24) and the color (the last from 32). The
    colormap, ``beat`` and ``note_layout`` apply; every other setting is checked and ignored. ``decay_rate`` and
    ``decay_amounts`` are checked for every image type and have no effect on the others.

    ``image_type="decay-exp"`` is ``decay`` with two amounts changed (see ``decay_exp``): a note that would gain ``g``
    points gains ``g * exp(-g / 8)``, and a circle with ``p`` points gives each neighbour ``sin(pi / 2 * p / 64) ** 2``
    per frame instead of the amount of its saturation level. ``decay_rate``, ``beat``, ``note_layout`` and
    the colormap apply; ``decay_amounts`` and every other setting are checked and ignored.

    ``image_type="chromatic-decay"`` is ``decay-exp`` for the 12 chromatic tones only (see ``chromatic_decay``): 12
    circles on a ring in circle-of-fifths order, charged by the loudest octave of each letter, whose points decay to the
    letters 5 and 7 above. ``decay_rate`` is for this type a **whole number from 1 to 10** (frames between decay steps;
    anything else is refused with ``ValueError``); ``beat`` and the colormap apply; ``note_layout``,
    ``decay_amounts`` and every other setting are checked and ignored; ``threshold`` (0 to 10, 0 off) applies as a
    percent of the largest note value of the whole file: a note strictly below it is 0 before the letters are
    charged (feature 037). With a ``beat`` the middle of the ring of letters also has a target of 12 concentric rings,
    140 pixels across, that shows the distance from the local peak of the current frame and of the frames before it
    (feature 036); without one there is no target.

    ``image_type="energy-graphs"`` draws a running histogram of the notes with two data sets, the rank points and the
    quasi-decibel amplitudes (see ``energy_graphs``), from ``energy``, the totals of every frame made by
    ``energy_graphs.frame_energy`` (required for this type, ignored by the others; it must have one frame for each row
    of ``frames``). Only the colormap applies; every other setting is checked and ignored.

    ``image_type="chromatic-wireframe"`` draws the points of ``chromatic-decay`` (the same simulation, with the same
    decay rate, whole number 1 to 10, and threshold) as a ridge plot in three dimensions (see ``chromatic_wireframe``):
    one line across the 12 letters for each frame, the newest in front and the earlier frames behind it as far as there
    is room, every line in the colormap color of its frame's place in the ``beat`` (the last color at the top of a peak;
    the first for every line without a beat). The colormap, the threshold and ``beat`` apply;
    ``note_layout``, ``decay_amounts`` and every other setting are checked and ignored.

    ``image_type="polychord"`` draws the loudest notes of each frame as a chain of tapering links that bends by
    the circle of fifths, repeated as copies turned 30 degrees, from ``polychord`` (a ``polychord.PolychordData``: the
    tempo of every frame and the frame rate; required for this type, ignored by the others, and it must have one tempo
    for each row of ``frames``) and ``polychord_settings`` (a ``polychord.PolychordSettings``: the number of notes, the
    minimum and maximum number of copies and the rotation; checked for every image type, used by this one only; see
    ``polychord``). The number of copies follows ``beat`` (the minimum for every frame without one) and every link of a
    frame has one color from its tempo. The colormap and ``beat`` apply; the threshold, ``note_layout``,
    ``decay_amounts`` and every other setting are checked and ignored.

    ``image_type="rhythm-circles"`` draws four concentric notched rings turned by the current tempo found from the local
    peaks, the tempo of the latest local peak and the rates of change of both (see ``rhythm_circles``), from ``rhythm``,
    the angles of every frame made by ``rhythm_circles.rhythm_angles`` (required for this type, ignored by the others;
    it must have one frame for each row of ``frames``). Only the colormap applies; every other setting is checked and
    ignored.

    ``image_type="polar-chords"`` draws a polar bar graph (see ``polar_chords``): the ``polar_notes`` loudest notes of a
    frame (a whole number from 5 to 8, default 5, checked for every image type and used by this one only) as bars
    clockwise from the top, one arc of 84 for each note (in the order of the cells of ``note_layout``: ``rows`` is the
    order of pitch), and the chord that ``chords.measure_chords`` records for the frame as one bar counterclockwise, one
    arc of 84 for each of the 12 root letters and 7 chord types (the types of a letter together, the letters from A).
    Every bar reaches out to ``0.5 + 0.5 * beat`` of the full radius. The colormap, ``beat`` and
    ``note_layout`` apply; every other setting is checked and ignored.

    ``wave_count`` (a whole number from 2 to 10, default 4) is the number of waves of the **beat wave** of ``contour``
    (see ``beat_wave``): with ``beat`` given, the frame's grid of values is multiplied by ``1 - pattern * beat`` before
    the contour is drawn, with a pattern of concentric rings with ``wave_count`` waves across the largest dimension of
    the grid; a frame at beat 0 (and every frame with ``beat=None``) is the plain contour. It is checked for every image
    type and has no effect on the others.

    ``extra_notes`` (feature 044; 0, the default, to the number of notes of the picture: 5, ``polar_notes`` or the notes of
    ``polychord_settings``; 0 to 8 for the other types, which ignore it) is the Extra notes setting k of the pictures that take the
    n loudest notes (``decay``, ``decay-exp``, ``polar-chords``, ``chromatic-decay``, ``chromatic-wireframe``, ``polychord``): a note
    that was among the n loudest in the frame before keeps its place while it is among the loudest n + k (see ``held_notes``). With 0 the
    n loudest notes are chosen as before. A job passes 1 to n (2 when the request does not say).

    Every argument is checked before anything is written.

    Arrays:
        ``frames``: ``NoteStrengths`` ``(frames, 88)`` - the strength of each of the 88 notes in each frame, averaged
            from the frequency buffers (the analysis windows), drawn as they are.
        ``beat``: ``BeatPositions`` ``(frames,)`` or ``None`` - the place of the middle of each frame in the local
            energy peak, from 0 (bottom) to 1 (top); ``None`` for none.
    """
    colormap = check_colormap(colormap)
    _check_threshold(threshold)
    image_type = check_image_type(image_type)
    resolution = check_resolution(resolution)
    note_count = check_note_count(note_count)
    interpolate = check_interpolate(interpolate)
    gaussian = check_gaussian(gaussian)
    note_layout = check_note_layout(note_layout)
    # a whole number from 1 to 10 for Chromatic Decay and Chromatic Wireframe
    decay_rate = check_chromatic_rate(decay_rate) if image_type in CHROMATIC_TYPES else check_decay_rate(decay_rate)
    decay_amounts = check_decay_amounts(decay_amounts)
    wave_count = check_wave_count(wave_count)
    polar_notes = check_polar_notes(polar_notes)
    polychord_settings = check_polychord_settings(polychord_settings)
    extra_notes = _check_extra_notes(extra_notes, image_type, polar_notes, polychord_settings)
    if beat is not None:
        # checked for every image type, used by contour, decay, decay-exp, polar-chords, chromatic-decay and
        # chromatic-wireframe
        beat = check_beat(beat, len(frames))
    peak = float(frames.max()) if frames.size else 0.0
    # 84 discs that keep points from frame to frame; the grid settings above are checked and not used
    if image_type == "decay":
        points = circle_points(frames, beat, note_layout, decay_rate, decay_amounts, extra_notes)
        write_decay_frames(points, colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT)
        return
    # the same discs with the points gained and lost along an exponential curve; decay_amounts is checked and not used
    if image_type == "decay-exp":
        points = decay_exp_points(frames, beat, note_layout, decay_rate, extra_notes)
        write_decay_frames(points, colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT)
        return
    # the 12 letters on a ring, decaying to the letters 5 and 7 above; note_layout and decay_amounts are checked and not
    # used
    if image_type == "chromatic-decay":
        # a note under the threshold of the whole file is 0 before the letters are charged
        points = chromatic_points(frames, beat, decay_rate, threshold, extra_notes)
        # the beat also fills the target in the middle
        write_chromatic_frames(points, colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT, beat=beat)
        return
    # the same points as chromatic-decay, drawn as a line for each frame in three dimensions; note_layout and
    # decay_amounts are checked and not used
    if image_type == "chromatic-wireframe":
        points = chromatic_points(frames, beat, decay_rate, threshold, extra_notes)
        # the beat decides the color of every line
        write_wireframe_frames(points, colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT, beat=beat)
        return
    # a histogram of two data sets, made from ``energy`` (the rest of the settings above are checked and not used)
    if image_type == "energy-graphs":
        if energy is None:
            raise ValueError("The energy graphs need the energy data.")
        if energy.frame_count != len(frames):
            raise ValueError(f"The energy data has {energy.frame_count} frames but {len(frames)} were given.")
        write_energy_frames(energy, colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT)
        return
    # the loudest notes as a rosette of tapering links, from the note values, ``beat`` and the tempos in
    # ``polychord`` (the rest of the settings above are checked and not used)
    if image_type == "polychord":
        if polychord is None:
            raise ValueError("Polychord needs the polychord data.")
        if polychord.tempos.shape != (len(frames),):
            raise ValueError(f"The polychord data has {polychord.tempos.size} tempos but {len(frames)} frames were given.")
        write_polychord_frames(frames, beat, polychord.tempos, polychord_settings, polychord.frame_rate, colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT, extra_notes)
        return
    # four notched rings turned by ``rhythm`` (the rest of the settings above are checked and not used)
    if image_type == "rhythm-circles":
        if rhythm is None:
            raise ValueError("Rhythm Circles needs the rhythm data.")
        if rhythm.frame_count != len(frames):
            raise ValueError(f"The rhythm data has {rhythm.frame_count} frames but {len(frames)} were given.")
        write_rhythm_frames(rhythm, colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT)
        return
    # a polar bar graph: the loudest notes clockwise, the chord counterclockwise; the grid settings above are checked
    # and not used
    if image_type == "polar-chords":
        write_polar_frames(polar_bars(frames, beat, polar_notes, note_layout, extra_notes), colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT)
        return
    columns, rows = GRID_COLUMNS * resolution, GRID_ROWS * resolution  # the contour: the last image type
    shown = spread_notes(frames[:, :SHOWN_NOTES], note_count)  # (the contour always has the rows layout)
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
    # the drawn frames only: an in-between frame is a blend of blurred frames
    blur_frames(directory, frames_to_draw, gaussian)
    write_interpolated_frames(directory, values.shape[0], interpolate)
