"""The 12 x 7 grid of the 84 drawn notes that the decay pictures (``decay``, ``decay_exp``, ``chromatic_decay``) and the chord measurement share.

Note ``n`` is at row ``n // 12`` from the top and column ``n % 12`` (one row for each octave, one column for each note name). A circle at full size just touches its
neighbours in a row: the **full radius** is half the narrower side of a cell (25 pixels on the 600 x 400 frame, whose cells are 50 pixels wide and 57 or 58 high).
A circle is drawn as up to ``RINGS`` flat rings.
"""

import numpy as np

RINGS = 12
GRID_COLUMNS = 12
GRID_ROWS = 7
NOTES = GRID_COLUMNS * GRID_ROWS  # the 84 drawn notes


def tile_edges(count: int, size: int) -> np.ndarray:
    """The pixel positions of the ``count + 1`` cell edges across ``size`` pixels: the nearest whole pixels to an even split.

    When ``size`` is a multiple of ``count`` every cell is the same width (the edges are the multiples of ``size / count``);
    otherwise cells differ by at most one pixel.
    """
    return np.rint(np.linspace(0, size, count + 1)).astype(np.int64)


def _check_values(values) -> np.ndarray:
    """The note values as a float64 ``(frames, columns)`` array of at least 84 columns, finite and 0 or more."""
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] < NOTES:
        raise ValueError(f"At least {NOTES} note values per frame are needed (got shape {values.shape}).")
    if values.size and not np.isfinite(values).all():
        raise ValueError("The note values must be finite numbers.")
    if values.size and values.min() < 0:
        raise ValueError("The note values must be 0 or more.")
    return values


def full_radius(width: int, height: int) -> float:
    """The radius at which circles in neighbouring cells just touch: half the narrower side of a cell (25 pixels on 600 x 400)."""
    return min(np.diff(tile_edges(GRID_COLUMNS, width)).min(), np.diff(tile_edges(GRID_ROWS, height)).min()) / 2
