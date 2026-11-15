"""The resolution setting and the interpolation that makes the grid of note values finer.

A frame is drawn from a grid with one value per drawn note (12 columns by 7 rows). The *resolution* ``r`` is a whole
number from 1 to 5: the picture is drawn from a grid of ``r`` times as many columns and rows instead, made from the
original one by linear interpolation. The new positions are ``np.linspace`` from the first to the last original column
(``columns * r`` of them) and from the first to the last original row (``rows * r`` of them), and the values are read
with ``np.interp``: along every original row first, then along every new column. So the four corners keep their original
values, every new value lies between the original values around it (it can never be louder than the loudest note or
quieter than the quietest one), and the end of one row never mixes with the start of the next. At ``r = 1`` the grid is
returned unchanged. Beyond the corners the new positions usually fall between original notes, so the largest value of a
finer grid can be a little below the original largest value, never above it.

This module knows nothing about the note analysis or the pictures: the grid shape is passed in.

Order of operations:
    1. Check the setting - ``check_resolution()`` - a whole number from 1 to 5, else refused.
    2. Check the grid - ``interpolate_grid()`` - ``GridValues`` ``(frames, rows * columns)``.
    3. At resolution 1 return a copy; otherwise, for each frame, read each original row at ``columns * r`` evenly spaced
       positions (``np.interp``), giving ``(rows, columns * r)``, then read each new column at ``rows * r`` evenly
       spaced positions, giving ``(rows * r, columns * r)``.
    4. Flatten each frame row by row - ``GridValues`` ``(frames, rows * r * columns * r)``.
"""

import math
import numbers

import numpy as np

from .array_types import GridValues

MIN_RESOLUTION = 1
MAX_RESOLUTION = 5
DEFAULT_RESOLUTION = 1


def check_resolution(value: object) -> int:
    """Return ``value`` as an ``int`` when it is a whole number from 1 to 5 (no strings, no fractions, no booleans)."""
    if (
        isinstance(value, bool)
        or not isinstance(value, numbers.Real)
        or not math.isfinite(value)
        or int(value) != value
        or not MIN_RESOLUTION <= value <= MAX_RESOLUTION
    ):
        raise ValueError(f"The oversampling must be a whole number from {MIN_RESOLUTION} to {MAX_RESOLUTION}.")
    return int(value)


def interpolate_grid(values: GridValues, columns: int, rows: int, resolution: int) -> GridValues:
    """The grid of every frame made ``resolution`` times finer: shape ``(frames, rows * r * columns * r)``, row-major.

    ``values`` has one row per frame and ``rows * columns`` values per frame (the original grid row by row, so note
    ``n`` is at row ``n // columns`` and column ``n % columns``). The result has the new row ``y`` and column ``x`` of a
    frame at index ``y * columns * r + x``. The input is never modified; at resolution 1 a copy of it is returned.

    Arrays:
        ``values``: ``GridValues`` ``(frames, rows * columns)`` - one value for each cell of the original grid in each
            frame, row by row (for the drawn notes, 84 cells:
        7 rows by 12 columns).

    Returns:
        ``GridValues`` ``(frames, rows * r * columns * r)`` - the same grid made ``r = resolution`` times finer in each
        direction, row by row; each new value lies between the original values around it, and the four corners keep
        their values.
    """
    r = check_resolution(resolution)
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != rows * columns:
        raise ValueError(f"Each frame needs {rows * columns} values (got shape {values.shape}).")
    if r == 1:
        return values.copy()
    frames = values.shape[0]
    grid = values.reshape(frames, rows, columns)
    original_columns, original_rows = np.arange(columns), np.arange(rows)
    xs = np.linspace(0, columns - 1, columns * r)
    ys = np.linspace(0, rows - 1, rows * r)
    across = np.empty((frames, rows, columns * r))
    for t in range(frames):
        for row in range(rows):
            across[t, row] = np.interp(xs, original_columns, grid[t, row])
    out = np.empty((frames, rows * r, columns * r))
    for t in range(frames):
        for column in range(columns * r):
            out[t, :, column] = np.interp(ys, original_rows, across[t, :, column])
    return out.reshape(frames, rows * r * columns * r)
