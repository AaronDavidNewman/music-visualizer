"""Turn per-window note values into per-frame colour images.

Frame ``f`` covers ``[f / frame_rate, (f + 1) / frame_rate)`` seconds. It is the mean of
the windows that start inside that period, or, if none does, the most recent window that
started before the period (which is the window covering its start when windows are consecutive).
Each frame becomes a 12 x 7 grid of coloured tiles (one row per octave, one column per note name,
252 x 168 pixels, 3:2).

A tile's color is the color of a matplotlib colormap (``summer``, ``autumn``, ``hot`` or ``cool``) at a position that
depends only on how strong the tile's own note is: its smoothed value as a share of the largest smoothed value in the
file, on a square-root scale (see ``colormaps``). Smoothing mixes each frame with a few earlier ones (see
``smooth_frames``) before the color is worked out. A threshold can hide faint notes: a note below it has a black tile (see
``hidden_notes``). The finished tile colors are written as the flat ``tiles`` picture or as ``blended`` tiles whose colors
fade into each other (see ``image_types``).
"""

import math
import numbers
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

from .colormaps import DEFAULT_COLORMAP, check_colormap, colorize
from .image_types import DEFAULT_BLEND_WIDTH, DEFAULT_IMAGE_TYPE, check_blend_width, check_image_type, make_blender
from .note_analysis import NOTE_COUNT, AnalysisResult

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
    return smoothed[:, :SHOWN_NOTES] < threshold / 100.0 * peak

# The number of the tile each pixel belongs to. A frame has at most 84 flat colours, so it is saved as an
# indexed-colour PNG: this index image never changes and only the 84-entry palette differs per frame.
_TILE_INDEX_BYTES = (
    np.repeat(
        np.repeat(np.arange(SHOWN_NOTES, dtype=np.uint8).reshape(GRID_ROWS, GRID_COLUMNS), TILE_HEIGHT, axis=0),
        TILE_WIDTH,
        axis=1,
    )
    .astype(np.uint8)
    .tobytes()
)

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

    ``image_type`` is ``tiles`` (the default: flat tiles, written as palette PNGs) or ``blended`` (the same finished tile
    colors, but the colors of neighbouring tiles fade into each other across every shared edge; true-color PNGs).
    ``blend_width`` (10 to 25, default 25) is how far that fade reaches on each side of an edge, as a percentage of the
    tile width; it has no effect for ``tiles``. See ``image_types``.

    Every argument is checked before anything is written.
    """
    colormap = check_colormap(colormap)
    _check_threshold(threshold)
    _check_smoothing_window(smoothing_window)
    image_type = check_image_type(image_type)
    blend_width = check_blend_width(blend_width)
    smoothed = smooth_frames(frames, smoothing, smoothing_window)
    colours = colorize(smoothed, colormap, SHOWN_NOTES)
    colours[hidden_notes(smoothed, threshold)] = 0
    directory.mkdir(parents=True, exist_ok=True)
    blend = pool = None
    futures = []
    if image_type == "blended":
        blend = make_blender(blend_width, GRID_COLUMNS, GRID_ROWS, TILE_WIDTH, TILE_HEIGHT)
        pool = ThreadPoolExecutor(max_workers=_BLEND_WORKERS)
    try:
        for i in range(colours.shape[0]):
            path = directory / f"frame_{i:06d}.png"
            if blend is None:
                # Level 6 makes these files about a third of the size of level 1 for roughly 0.2 s more per 10,000 frames.
                _palette_frame(colours[i]).save(path, compress_level=6)
            else:
                futures.append(pool.submit(_save_blended, blend, colours[i], path))
        for future in futures:
            future.result()  # raises the first error of a worker, if there was one
    finally:
        if pool is not None:
            pool.shutdown(wait=True)
