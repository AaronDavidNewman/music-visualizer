"""Energy: how intense the audio is in each frame, whether or not it is tonal.

The audio is looked at in very short *internal windows*: 32 samples at 44.1 kHz, proportionally more or fewer
at other sample rates, so a window always covers about 0.73 ms. In each window the spread (population standard
deviation) of the left channel and of the right channel are found and averaged. The energy of a frame is the
mean of that over the internal windows laid end to end from the frame's first sample. A constant level has no
spread and so no energy; noise and percussion count as much as tones.
"""

import math
import numbers

import numpy as np

from .note_analysis import _to_float

INTERNAL_WINDOW_AT_44K = 32
REFERENCE_RATE = 44100


def internal_window(sample_rate: float) -> int:
    """Samples in an internal window: 32 at 44,100 Hz, scaled in proportion and rounded to the nearest sample.

    16 at 22,050 Hz, 8 at 11,025 Hz, 35 at 48,000 Hz. Never below 2, since one sample has no spread.
    """
    return max(2, math.floor(INTERNAL_WINDOW_AT_44K * sample_rate / REFERENCE_RATE + 0.5))


def _spread(channel: np.ndarray, window: int) -> float:
    """Mean of the standard deviations of the full ``window``-sample windows of ``channel`` (scaled to about -1..1).

    A leftover shorter than a window is ignored. If there is no full window, the samples there are
    measured as one window (a single sample, or none, has no spread).
    """
    samples = _to_float(channel)
    full = samples.shape[0] // window
    if full == 0:
        return float(samples.std()) if samples.shape[0] > 1 else 0.0
    return float(samples[: full * window].reshape(full, window).std(axis=1).mean())


def frame_energies(left, right, sample_rate: float, frame_rate: float, frames: int) -> np.ndarray:
    """The energy of each of ``frames`` frames, as a float64 array of shape ``(frames,)``.

    Frame ``f`` covers the samples from ``rint(f * sample_rate / frame_rate)`` up to the start of frame
    ``f + 1`` (and no further than the end of the audio), so the frames tile the file with no gap or overlap.
    ``left`` and ``right`` are the raw PCM channels of equal length. A mono file may pass the same array for both;
    it is then measured once.
    """
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, numbers.Real) or not (
        math.isfinite(sample_rate) and sample_rate > 0
    ):
        raise ValueError(f"The sample rate must be a number greater than 0 (got {sample_rate!r}).")
    if isinstance(frame_rate, bool) or not isinstance(frame_rate, numbers.Real) or not (
        math.isfinite(frame_rate) and frame_rate > 0
    ):
        raise ValueError(f"The frame rate must be a number greater than 0 (got {frame_rate!r}).")
    if isinstance(frames, bool) or not isinstance(frames, numbers.Integral) or frames < 0:
        raise ValueError(f"The number of frames must be a whole number, 0 or more (got {frames!r}).")
    left = np.asarray(left)
    right = left if right is left else np.asarray(right)
    if left.ndim != 1 or right.shape != left.shape:
        raise ValueError("The left and right channels must be 1-D arrays of the same length.")

    total = left.shape[0]
    window = internal_window(sample_rate)
    bounds = np.minimum(np.rint(np.arange(int(frames) + 1) * (sample_rate / frame_rate)), total).astype(np.int64)
    mono = right is left

    out = np.zeros(int(frames))
    for f in range(int(frames)):
        start, stop = int(bounds[f]), int(bounds[f + 1])
        if stop - start < 2:
            continue  # no samples, or one: no spread
        spread_left = _spread(left[start:stop], window)
        out[f] = spread_left if mono else (spread_left + _spread(right[start:stop], window)) / 2
    return out
