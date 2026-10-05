"""Turn per-window note values into per-frame grayscale images.

Frame ``f`` covers ``[f / frame_rate, (f + 1) / frame_rate)`` seconds. It is the mean of
the windows that start inside that period, or, if none does, the most recent window that
started before the period (which is the window covering its start when windows are consecutive). Each frame becomes an 11 x 8 grid of gray squares, one per note.
"""

import math
from pathlib import Path

import numpy as np
from PIL import Image

from .note_analysis import NOTE_COUNT, AnalysisResult

GRID_COLUMNS = 11
GRID_ROWS = 8
SQUARE_PIXELS = 20

assert GRID_COLUMNS * GRID_ROWS == NOTE_COUNT

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


def to_gray_levels(frames: np.ndarray) -> np.ndarray:
    """Scale to 0..255 against the largest value anywhere in ``frames`` (linear, no other normalization)."""
    peak = float(frames.max()) if frames.size else 0.0
    if peak <= 0:
        return np.zeros(frames.shape, dtype=np.uint8)
    return np.rint(255.0 * frames / peak).astype(np.uint8)


def render_frame(levels: np.ndarray) -> Image.Image:
    """Draw 88 gray levels as an 11 x 8 grid of squares; note 0 is top-left, reading left to right."""
    grid = np.asarray(levels, dtype=np.uint8).reshape(GRID_ROWS, GRID_COLUMNS)
    pixels = np.repeat(np.repeat(grid, SQUARE_PIXELS, axis=0), SQUARE_PIXELS, axis=1)
    return Image.fromarray(pixels, mode="L")


def write_frames(frames: np.ndarray, directory: Path) -> None:
    """Save one PNG per row of ``frames`` as ``frame_000000.png`` and up."""
    directory.mkdir(parents=True, exist_ok=True)
    for i, levels in enumerate(to_gray_levels(frames)):
        render_frame(levels).save(directory / f"frame_{i:06d}.png", compress_level=1)
