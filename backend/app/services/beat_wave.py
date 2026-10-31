"""The beat wave of the ``contour`` picture: concentric rings that cut into the frame's values and swell and fade again over the beat.

For a grid of ``rows`` x ``columns`` values the **pattern** is a grid of the same shape with numbers from 0 to 1. For the point in column
``x`` and row ``y`` (counted from 0) let ``distance`` be its distance, in grid points, from the geometric center of the grid (the center of
``n`` points along an axis is at ``(n - 1) / 2``, so it lies between two points on an even axis) and ``largest`` the larger of ``rows`` and
``columns``. Then::

    pattern = (sin(waves * 2 * pi * sqrt(distance / largest)) + 1) / 2

that is, the sine of rings with ``waves`` waves across the largest dimension, rescaled from the range -1 to 1 to the range 0 to 1 (it is
0.5 at the center, where the distance is 0). The sine runs over the *square root* of the relative distance, so the rings are close together
near the center and the wave gets lower in frequency (the rings wider) towards the outside.

The **modifier** of a frame is ``1 - pattern * sin(pi * k)``, with ``k`` the frame's position in the local energy peak (0 at the minimum, 1 at
the maximum; see ``local_peaks``). The frame's values are multiplied by it before the contour is drawn. The position is passed through a
sine from 0 to pi, so the effect swells and fades smoothly over a beat: at ``k = 0`` the modifier is 1 everywhere, so a frame at the minimum
of the beat is the plain contour; as ``k`` grows the rings, where the pattern is 1, are dimmed by the factor ``1 - sin(pi * k)``, down to
nothing half way up the beat (``k = 0.5``), and come back as ``k`` goes on to 1, where the frame is again (all but exactly) the plain contour;
the places between the rings, where the pattern is 0, are always left alone.

The pattern depends only on the shape of the grid and the number of waves, so it is worked out once for a job (and kept).

This module knows nothing about matplotlib, images or the audio: the shape, the wave count and the position in the beat are passed in.
"""

import math
import numbers
from functools import lru_cache

import numpy as np

MIN_WAVE_COUNT = 2
MAX_WAVE_COUNT = 10
DEFAULT_WAVE_COUNT = 4

_MESSAGE = f"The wave count must be a whole number from {MIN_WAVE_COUNT} to {MAX_WAVE_COUNT}."


def check_wave_count(value) -> int:
    """Return ``value`` as an ``int`` when it is a whole number from 2 to 10 (a bool, a string or a fraction is refused)."""
    if (
        isinstance(value, bool)
        or not isinstance(value, numbers.Real)
        or not math.isfinite(value)
        or value != int(value)
        or not MIN_WAVE_COUNT <= value <= MAX_WAVE_COUNT
    ):
        raise ValueError(_MESSAGE)
    return int(value)


@lru_cache(maxsize=16)
def wave_pattern(rows: int, columns: int, waves: int) -> np.ndarray:
    """The pattern for a grid of ``rows`` x ``columns`` values with ``waves`` waves: a read-only float64 array of that shape, from 0 to 1."""
    rows, columns, waves = int(rows), int(columns), check_wave_count(waves)
    if rows < 1 or columns < 1:
        raise ValueError(f"The grid must have at least one row and one column (got {rows} x {columns}).")
    y, x = np.indices((rows, columns))
    distance = np.hypot(x - (columns - 1) / 2, y - (rows - 1) / 2)
    largest = max(rows, columns)
    pattern = (np.sin(waves * 2 * np.pi * np.sqrt(distance / largest)) + 1) / 2
    pattern.flags.writeable = False
    return pattern


def wave_modifier(rows: int, columns: int, waves: int, k: float) -> np.ndarray:
    """The modifier ``1 - pattern * k`` of a frame at position ``k`` (0 to 1) in the local peak: a new float64 array of shape ``(rows, columns)``."""
    if isinstance(k, bool) or not isinstance(k, numbers.Real) or not math.isfinite(k) or not 0.0 <= k <= 1.0:
        raise ValueError("The position in the beat must be a number from 0 to 1.")
    return 1.0 - wave_pattern(rows, columns, waves) * float(np.sin(np.pi*k))
