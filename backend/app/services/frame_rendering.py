"""Turn per-window note values into per-frame colour images.

Frame ``f`` covers ``[f / frame_rate, (f + 1) / frame_rate)`` seconds. It is the mean of
the windows that start inside that period, or, if none does, the most recent window that
started before the period (which is the window covering its start when windows are consecutive).
Each frame becomes a 12 x 7 grid of coloured tiles (one row per octave, one column per note name,
252 x 168 pixels, 3:2); a higher resolution (1 to 5) first interpolates the grid to 12 r x 7 r values, so the
same picture size has more and smaller tiles (see ``resolution``). A number of notes below 84 builds the picture from
only the notes with the most energy in the file, spread over the whole grid (see ``note_selection``).
The image type ``circles`` draws wandering circles instead of a grid (see ``circles``).
An interpolate value above 1 draws only every n-th frame and makes the frames in between from their neighbors with Pillow
(see ``frame_interpolation``).

A tile's color is the color of a matplotlib colormap (``summer``, ``autumn``, ``hot`` or ``cool``) at a position that
depends only on how strong the tile's own note is: its smoothed value as a share of the largest smoothed value in the
file, on a square-root scale (see ``colormaps``). Smoothing mixes each frame with a few earlier ones (see
``smooth_frames``) before the color is worked out. A threshold can hide faint notes: a note below it has a black tile (see
``hidden_notes``). The finished tile colors are written as the flat ``tiles`` picture or as ``blended`` tiles whose colors
fade into each other (see ``image_types``). The third kind, ``contour``, does not use tile colors: the smoothed values
themselves are drawn as a filled contour map (see ``contour``).
"""

import math
import numbers
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

from .circles import (
    DEFAULT_CIRCLE_MEMORY,
    DEFAULT_CIRCLE_NOTES,
    DEFAULT_CIRCLE_SIZE,
    DEFAULT_CIRCLE_UNIT,
    check_circle_memory,
    check_circle_notes,
    check_circle_size,
    check_circle_unit,
    write_circle_frames,
)
from .colormaps import DEFAULT_COLORMAP, check_colormap, colorize
from .contour import write_contour_frames
from .frame_interpolation import DEFAULT_INTERPOLATE, check_interpolate, key_frames, write_interpolated_frames
from .image_types import (
    DEFAULT_BLEND_WIDTH,
    DEFAULT_IMAGE_TYPE,
    check_blend_width,
    check_image_type,
    make_grid_blender,
    tile_edges,
)
from .note_analysis import NOTE_COUNT, AnalysisResult
from .note_selection import DEFAULT_NOTE_COUNT, check_note_count, spread_notes
from .resolution import DEFAULT_RESOLUTION, check_resolution, interpolate_grid

# 12 columns (the notes of an octave) by 7 rows (octaves) of tiles 21 wide by 24 tall: tile width is
# 87.5% of its height, so the 252 x 168 image is exactly 3:2, since (12 * 0.875) / 7 = 1.5.
GRID_COLUMNS = 12
GRID_ROWS = 7
SHOWN_NOTES = GRID_COLUMNS * GRID_ROWS  # notes 0..83 are drawn; the four highest (84..87) are not
TILE_WIDTH = 21
TILE_HEIGHT = 24
IMAGE_WIDTH = GRID_COLUMNS * TILE_WIDTH
IMAGE_HEIGHT = GRID_ROWS * TILE_HEIGHT

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
# note value in the whole file gets a black tile. 0 is off (the default); the page's slider ends at 10.
MIN_THRESHOLD = 0
MAX_THRESHOLD = 10
DEFAULT_THRESHOLD = 0

assert SHOWN_NOTES <= NOTE_COUNT
assert TILE_WIDTH * 8 == TILE_HEIGHT * 7  # tile width is exactly 87.5% of its height
assert IMAGE_WIDTH * 2 == IMAGE_HEIGHT * 3  # exactly 3:2

# Guards ceil() against floating-point noise such as 5.000000000000001.
_EPSILON = 1e-9
# Samples. A window starting this close below a frame boundary still belongs to the later frame.
_BOUNDARY_TOLERANCE = 1e-6


def frame_count(sample_count: int, sample_rate: float, frame_rate: float) -> int:
    """Number of frames for audio of ``sample_count`` samples: duration * frame rate, rounded up."""
    return max(0, math.ceil(sample_count * frame_rate / sample_rate - _EPSILON))

def average_frames(result: AnalysisResult, frame_rate: float, frames: int) -> np.ndarray:
    """Average the window rows of ``result`` into ``frames`` rows of 88 values.

    Windows are assigned to frames by their exact start position (``k * step``), not by the rounded
    start sample. A frame whose period has no window start uses the last window that started before it.
    """
    windows = result.frames
    if frames == 0 or windows.shape[0] == 0:
        return np.zeros((frames, NOTE_COUNT))

    positions = result.window_positions
    boundaries = np.arange(frames + 1) * (result.sample_rate / frame_rate) - _BOUNDARY_TOLERANCE
    edges = np.searchsorted(positions, boundaries, side="left")
    first, stop = edges[:-1], edges[1:]
    earlier = np.maximum(first - 1, 0)

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


def hidden_notes(smoothed: np.ndarray, threshold: float = DEFAULT_THRESHOLD) -> np.ndarray:
    """Which drawn notes are too faint to show: a boolean array of shape ``(frames, 84)``.

    ``smoothed`` has one row per frame and one column per note (88), after smoothing. The reference is the largest
    value anywhere in it, the same value ``to_gray_levels`` scales against (so the four undrawn notes count too). A
    note is hidden when its value is *strictly* below ``threshold`` percent of that reference; one exactly at the
    threshold is shown. With threshold 0 nothing is hidden (values are never negative), the note with the largest value
    is never hidden, and when no note has any value nothing is hidden. The comparison uses the unrounded value, before
    any root, so no other setting changes which notes are hidden.
    """
    threshold = _check_threshold(threshold)
    smoothed = np.asarray(smoothed, dtype=np.float64)
    if smoothed.ndim != 2 or smoothed.shape[1] < SHOWN_NOTES:
        raise ValueError(f"At least {SHOWN_NOTES} note values per frame are needed (got shape {smoothed.shape}).")
    peak = float(smoothed.max()) if smoothed.size else 0.0
    return hidden_below(smoothed[:, :SHOWN_NOTES], peak, threshold)

# The number of the tile each pixel belongs to, for a grid of ``columns`` x ``rows`` tiles in the whole picture: the tile
# edges are the nearest whole pixels to an even split, so for the original 12 x 7 grid every tile is 21 x 24 pixels and a
# finer grid has smaller tiles that differ by at most one pixel.
def _tile_index(columns: int, rows: int) -> np.ndarray:
    column_of = np.repeat(np.arange(columns), np.diff(tile_edges(columns, IMAGE_WIDTH)))
    row_of = np.repeat(np.arange(rows), np.diff(tile_edges(rows, IMAGE_HEIGHT)))
    return row_of[:, None] * columns + column_of[None, :]


# A frame of the original grid has at most 84 flat colours, so it is saved as an indexed-colour PNG: this index image never
# changes and only the 84-entry palette differs per frame. A finer grid can have more colours than a palette holds (256).
_PALETTE_TILES = 256
_TILE_INDEX_BYTES = _tile_index(GRID_COLUMNS, GRID_ROWS).astype(np.uint8).tobytes()

def _palette_frame(colours: np.ndarray) -> Image.Image:
    """The frame as an indexed-colour image whose palette is the 84 tile colours (decodes to exactly ``render_frame``)."""
    image = Image.frombytes("P", (IMAGE_WIDTH, IMAGE_HEIGHT), _TILE_INDEX_BYTES)
    image.putpalette(np.ascontiguousarray(colours, dtype=np.uint8).tobytes())
    return image


# Blended frames are blended and encoded on a few threads: each frame is independent, numpy and the PNG encoder release
# the interpreter lock for their heavy work, and the files are the same whatever the number of threads.
_BLEND_WORKERS = max(1, min(4, os.cpu_count() or 1))


def _save_blended(blend, colours: np.ndarray, path: Path) -> None:
    # a blended frame has many colours, so it is a true-color PNG; level 1 costs far less time than level 6
    # for a file only a little larger
    Image.fromarray(blend(colours), "RGB").save(path, compress_level=1)


def write_frames(
    frames: np.ndarray,
    directory: Path,
    colormap: str = DEFAULT_COLORMAP,
    smoothing: float = DEFAULT_SMOOTHING,
    smoothing_window: int = DEFAULT_SMOOTHING_WINDOW,
    threshold: float = DEFAULT_THRESHOLD,
    image_type: str = DEFAULT_IMAGE_TYPE,
    blend_width: float = DEFAULT_BLEND_WIDTH,
    resolution: int = DEFAULT_RESOLUTION,
    note_count: int = DEFAULT_NOTE_COUNT,
    interpolate: int = DEFAULT_INTERPOLATE,
    circle_unit: int = DEFAULT_CIRCLE_UNIT,
    circle_memory: int = DEFAULT_CIRCLE_MEMORY,
    circle_notes: int = DEFAULT_CIRCLE_NOTES,
    circle_size: int = DEFAULT_CIRCLE_SIZE,
) -> None:
    """Save one PNG per row of ``frames`` (averaged note values) as ``frame_000000.png`` and up.

    ``smoothing`` (0.0 to 0.8, default none) and ``smoothing_window`` (a whole number from 1 to 20, default 1) smooth
    the note values over the frames: a frame is the weighted average of itself and the ``smoothing_window`` frames
    before it, each of those with the weight ``smoothing`` (see ``smooth_frames``). Smoothing 0 changes nothing.

    Every drawn tile then gets the color of the ``colormap`` (``summer``, ``autumn``, ``hot`` or ``cool``) at the position
    of its own note's strength: the smoothed value as a share of the largest smoothed value in the whole file, square-rooted
    (see ``colormaps.colorize``). It depends on no other note and on nothing about the frame as a whole.

    ``threshold`` (0 to 10, default 0 = off) is a percentage of the largest note value in the file (after smoothing): a
    note below it gets a black tile in that frame (``hidden_notes``), whatever the colormap is.

    ``image_type`` is ``tiles`` (the default: flat tiles, written as palette PNGs), ``contour`` (see below) or ``blended`` (the same finished tile
    colors, but the colors of neighbouring tiles fade into each other across every shared edge; true-color PNGs).
    ``blend_width`` (10 to 25, default 25) is how far that fade reaches on each side of an edge, as a percentage of the
    tile width (the mean width of a tile at the chosen resolution); it has no effect for ``tiles``. See ``image_types``.

    ``resolution`` (a whole number from 1 to 5, default 1) makes the grid that every frame is drawn from finer: the 7 x 12
    grid of the smoothed values of the drawn notes is interpolated to 7r x 12r values (``interpolate_grid``: ``np.linspace``
    positions and ``np.interp``, corners kept, no value outside the original range) *after* the smoothing, and the
    threshold and the colors are worked out on those values. The picture keeps its size, so tiles get smaller; the scale of
    the colors and the threshold's reference are the largest value of the whole file before the interpolation. Frames of
    the original grid (1) are written exactly as without the setting.

    ``image_type="contour"`` draws the grid of values (the 84 drawn notes, or the finer interpolated grid; the values the
    threshold hides are 0) as a
    filled contour map in the ``colormap`` instead of tiles, with matplotlib (see ``contour``): the contour levels are
    chosen by matplotlib, and the color scale is *linear* from 0 to the largest smoothed value in the whole file (the
    tiles use the square root of the strength). ``blend_width`` has no effect for it either.

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
    changes.

    ``image_type="circles"`` draws circles that wander as the music plays instead of a grid (see ``circles``): in every
    frame the ``circle_notes`` (5 to 12, default 8) strongest notes of that frame each put down a circle, placed relative
    to the circle that its rank had in the previous frame (moved by an angle from the note's name and a distance from its
    octave, in units of ``circle_unit`` pixels, 1 to 10, default 4), colored by the colormap at the note's strength on the
    tiles' scale, and remembered in a circular buffer of the last ``circle_memory`` (100 to 500, default 300) circles that
    every frame draws in full, on a background of the colormap's middle color, each circle as large as ``circle_size`` (its
    circumference in pixels, 25 to 50, default 25) and with an opacity that falls with its age (the oldest barely visible). Smoothing and the colormap apply; ``interpolate``, ``resolution``, ``note_count``,
    ``threshold`` and ``blend_width`` describe a grid of tiles or skipped frames and are accepted and ignored. The three
    circle settings are checked for every image type and have no effect for the others.

    Every argument is checked before anything is written.
    """
    colormap = check_colormap(colormap)
    _check_threshold(threshold)
    _check_smoothing_window(smoothing_window)
    image_type = check_image_type(image_type)
    blend_width = check_blend_width(blend_width)
    resolution = check_resolution(resolution)
    note_count = check_note_count(note_count)
    interpolate = check_interpolate(interpolate)
    circle_unit = check_circle_unit(circle_unit)
    circle_memory = check_circle_memory(circle_memory)
    circle_notes = check_circle_notes(circle_notes)
    circle_size = check_circle_size(circle_size)
    smoothed = smooth_frames(frames, smoothing, smoothing_window)
    peak = float(smoothed.max()) if smoothed.size else 0.0
    if image_type == "circles":
        write_circle_frames(
            smoothed[:, :SHOWN_NOTES],
            peak,
            colormap,
            directory,
            circle_notes,
            circle_unit,
            circle_memory,
            circle_size,
            IMAGE_WIDTH,
            IMAGE_HEIGHT,
        )
        return
    columns, rows = GRID_COLUMNS * resolution, GRID_ROWS * resolution
    shown = spread_notes(smoothed[:, :SHOWN_NOTES], note_count)
    values = interpolate_grid(shown, GRID_COLUMNS, GRID_ROWS, resolution)
    hidden = hidden_below(values, peak, threshold)
    frames_to_draw = key_frames(values.shape[0], interpolate)
    if image_type == "contour":
        values[hidden] = 0
        write_contour_frames(
            values, peak, colormap, directory, columns, rows, IMAGE_WIDTH, IMAGE_HEIGHT, indices=frames_to_draw
        )
    else:
        colours = colorize(values, colormap, columns * rows, peak)
        colours[hidden] = 0
        _write_tile_frames(colours, directory, image_type, blend_width, columns, rows, frames_to_draw)
    write_interpolated_frames(directory, values.shape[0], interpolate)


def _write_tile_frames(
    colours: np.ndarray, directory: Path, image_type: str, blend_width: float, columns: int, rows: int, frames_to_draw
) -> None:
    """Draw the frames ``frames_to_draw`` of ``tiles`` or ``blended`` from the finished tile colors (all frames' colors)."""
    directory.mkdir(parents=True, exist_ok=True)
    blend = pool = None
    futures = []
    index = _tile_index(columns, rows)
    if image_type == "blended":
        blend = make_grid_blender(blend_width, columns, rows, IMAGE_WIDTH, IMAGE_HEIGHT)
        pool = ThreadPoolExecutor(max_workers=_BLEND_WORKERS)
    try:
        for i in frames_to_draw:
            path = directory / f"frame_{i:06d}.png"
            if blend is None and columns * rows <= _PALETTE_TILES:
                # Level 6 makes these files about a third of the size of level 1 for roughly 0.2 s more per 10,000 frames.
                _palette_frame(colours[i]).save(path, compress_level=6)
            elif blend is None:
                # a finer grid has more colors than a palette holds: a true-color picture (level 6: about 45% smaller
                # than level 1 for under 0.15 ms more per frame)
                Image.fromarray(colours[i][index], "RGB").save(path, compress_level=6)
            else:
                futures.append(pool.submit(_save_blended, blend, colours[i], path))
        for future in futures:
            future.result()  # raises the first error of a worker, if there was one
    finally:
        if pool is not None:
            pool.shutdown(wait=True)
