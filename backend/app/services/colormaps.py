"""Colors from a named matplotlib colormap.

A picture takes its colors from the table of the chosen colormap (256 entries, row 0 the first color and row 255 the last; row 128 is the middle color that most
pictures use as their background).

This is the only module that uses matplotlib. It is imported the first time a table is needed (never ``pyplot``), so the
server starts and the tests that do not draw run without paying for it.
"""

import functools

import numpy as np

COLORMAPS = ("coolwarm", "YlOrRd", "inferno", "Blues", "viridis", "Greys", "hsv", "hot", "Wistia", "Paired", "gist_rainbow")
DEFAULT_COLORMAP = "coolwarm"
COLORMAP_STEPS = 256
MIDDLE_COLOR_ROW = 128  # the middle color of the colormap: the background of most pictures


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


def check_beat(beat, frames: int) -> np.ndarray:
    """Return ``beat`` as a float64 array when it is one number from 0 to 1 for each of ``frames`` frames; else refuse it."""
    message = f"The beat must be one number from 0 to 1 for each of the {frames} frames."
    array = np.asarray(beat)
    if array.ndim != 1 or array.shape[0] != frames or array.dtype.kind not in "iuf":
        raise ValueError(message)
    array = array.astype(np.float64)
    if not np.all(np.isfinite(array)) or array.min(initial=0.0) < 0.0 or array.max(initial=1.0) > 1.0:
        raise ValueError(message)
    return array
