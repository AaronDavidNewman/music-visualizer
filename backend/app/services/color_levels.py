"""Round hue, saturation and brightness to a small number of evenly spaced levels.

Each property has an optional *step* (``None`` means N/A: no rounding). On a scale of size ``R`` (360 for hue,
100 for saturation and brightness) a step ``s`` gives the levels ``0, s, 2s ... R``: ``round((R + s) / s)`` of them,
both ends included, so the top of the scale is always reachable and there are never fewer than 3.
Rounding is the last step for each property (after smoothing and the root settings). A value half-way between two
levels goes to the higher one.
"""

import math
import numbers

import numpy as np

HUE_SCALE = 360
UNIT_SCALE = 100
HUE_STEPS = (12, 36, 90, 180)
UNIT_STEPS = (5, 10, 20, 50)

# Guards floor() against products such as 5.999999999999999 that are 6 in exact arithmetic.
_EPSILON = 1e-9


def level_count(step: int, scale: int) -> int:
    """Number of levels for ``step`` on a scale of size ``scale``: ``round((scale + step) / step)``, halves up."""
    return math.floor((scale + step) / step + 0.5)


def check_step(step, allowed: tuple[int, ...], label: str) -> int | None:
    """Return ``None`` for N/A, or the step as an ``int`` when it is a whole number in ``allowed``.

    Anything else raises ``ValueError("The <label> step must be N/A or one of 12, 36, ...")``.
    """
    message = f"The {label} step must be N/A or one of {', '.join(map(str, allowed))}."
    if step is None:
        return None
    if isinstance(step, bool) or not isinstance(step, numbers.Real) or not math.isfinite(step):
        raise ValueError(message)
    if step != int(step) or int(step) not in allowed:
        raise ValueError(message)
    return int(step)


def snap(values, step: int | None, scale: int) -> np.ndarray:
    """Round ``values`` (on the 0..1 scale) to the nearest level of ``step`` on ``scale``; a new float64 array.

    ``step=None`` returns an unchanged copy. Otherwise each value ``x`` becomes ``min(k * step, scale) / scale`` with
    ``k = floor(x * scale / step + 0.5)``. 0 and 1 are fixed points. The result for a value depends on that value only.
    """
    out = np.array(values, dtype=np.float64, copy=True)
    if step is None:
        return out
    levels = np.floor(out * scale / step + 0.5 + _EPSILON)
    return np.clip(np.minimum(levels * step, scale), 0.0, None) / scale
