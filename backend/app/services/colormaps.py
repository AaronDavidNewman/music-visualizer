"""Colors from a named matplotlib colormap.

A tile's color is the color of the chosen colormap at one position of its scale, and the position depends only on how
strong the tile's own note is: its smoothed value as a share of the largest smoothed value anywhere in the file, on a
square-root scale, rounded to one of 256 table entries. No other note, no loudness of the frame and no frame number takes
part, so a note of the same strength has the same color wherever and whenever it sounds.

This is the only module that uses matplotlib. It is imported the first time a table is needed (never ``pyplot``), so the
server starts and the tests that do not draw run without paying for it.
"""

import functools
import math
import numbers

import numpy as np

COLORMAPS = ("summer", "autumn", "hot", "cool", "viridis", "Greys", "hsv")
DEFAULT_COLORMAP = "hot"
COLORMAP_STEPS = 256


def check_colormap(value) -> str:
    """Return ``value`` when it is exactly one of the offered names (no trimming, no case folding)."""
    if not isinstance(value, str) or value not in COLORMAPS:
        raise ValueError(f"The colormap must be one of {', '.join(COLORMAPS)}.")
    return value


@functools.lru_cache(maxsize=None)
def lookup_table(name: str) -> np.ndarray:
    """The 8-bit colors of the colormap ``name``: a read-only ``uint8`` array of shape ``(256, 3)``.

    The scale is sampled at 256 evenly spaced positions, so the table spans the whole colormap whatever its own number of
    entries is: row 0 is the first color of the scale and row 255 the last.
    """
    check_colormap(name)
    from matplotlib import colormaps  # imported here on purpose: see the module docstring

    table = np.ascontiguousarray(colormaps[name](np.linspace(0, 1, COLORMAP_STEPS), bytes=True)[:, :3], dtype=np.uint8)
    table.setflags(write=False)
    return table


def colorize(smoothed, colormap: str, shown: int, peak: float | None = None) -> np.ndarray:
    """The color of every drawn tile in every frame: a ``uint8`` array of shape ``(frames, shown, 3)``.

    ``smoothed`` has one row per frame and one column per note (88), after smoothing. ``peak`` is the largest value
    anywhere in it (all notes count, also the ones that are not drawn). For the first ``shown`` notes the position on the
    scale is ``sqrt(value / peak)`` and the color is the table entry ``rint(position * 255)``: a note with no strength
    has the first color, the note with the largest value the last, and a stronger note never has an earlier one. When no
    note has any strength every tile has the first color. The input is not modified.

    ``peak`` is the reference value for the scale; leave it out to use the largest value of ``smoothed``. A caller whose
    array does not hold every note (for instance a finer grid made by interpolation, which has no undrawn notes) passes
    the peak of the whole file; a value above it gets the last color.
    """
    table = lookup_table(colormap)
    smoothed = np.asarray(smoothed, dtype=np.float64)
    if smoothed.ndim != 2 or smoothed.shape[1] < shown:
        raise ValueError(f"At least {shown} note values per frame are needed (got shape {smoothed.shape}).")
    if smoothed.size and smoothed.min() < 0:
        raise ValueError("The note values must be 0 or more.")
    if peak is None:
        peak = float(smoothed.max()) if smoothed.size else 0.0
    elif isinstance(peak, bool) or not isinstance(peak, numbers.Real) or not math.isfinite(peak) or peak < 0:
        raise ValueError("The peak must be a finite number, 0 or more.")
    share = np.minimum(smoothed[:, :shown] / peak, 1.0) if peak > 0 else np.zeros((smoothed.shape[0], shown))
    index = np.rint(np.sqrt(share) * (COLORMAP_STEPS - 1)).astype(np.intp)
    return table[index]
