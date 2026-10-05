"""Window spacing: how far apart analysis windows start, as a multiple of the window size.

Both functions are mirrored in ``frontend/src/lib/spacing.ts``; the two test suites share a table of
expected values so the formulas stay in agreement.
"""

import math


def default_spacing(sample_rate: float, frame_rate: float, window_size: int) -> float:
    """Spacing that gives each frame its own window: one frame period in samples, over the window size.

    Rounded down to 6 decimals so the step is never longer than a frame period.
    """
    return math.floor(1e6 * (sample_rate / frame_rate) / window_size + 1e-9) / 1e6


def resolve_step(spacing: float, window_size: int) -> tuple[float, float, bool]:
    """Return ``(spacing_used, step_in_samples, raised)`` for a requested spacing.

    A step below one sample is raised to exactly one sample (``raised`` is then True).
    """
    step = spacing * window_size
    if step < 1:
        return 1 / window_size, 1.0, True
    return spacing, step, False
