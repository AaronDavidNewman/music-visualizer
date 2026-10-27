"""Seeded test signals for the local_peaks measurement: click tracks, bursts, bumps, silence, and a slow reference energy."""

import numpy as np

RATE = 44100
IMPULSE = 32


def _signs(width):
    """+1, -1, +1, ...: a burst whose spread is the same wherever it falls (a random burst can be weak by chance)."""
    return np.where(np.arange(width) % 2 == 0, 1.0, -1.0)


def click_track(seconds=30, period=0.5, rate=RATE, width=16, seed=1, level=0.5, noise=0.005):
    """Quiet noise with one short loud burst every ``period`` seconds, the first at ``period``.

    Returns ``(left, right, clicks)``: the two channels and the sample at which each burst starts. A burst is ``width`` samples
    (at most one impulse window; it may straddle two) so a peak lies within 32 samples of it.
    """
    rng = np.random.default_rng(seed)
    count = int(round(seconds * rate))
    left = rng.normal(0, noise, count)
    right = rng.normal(0, noise, count)
    clicks = []
    t = period
    while t < seconds - 0.05:
        start = int(round(t * rate))
        left[start : start + width] += level * _signs(width)
        right[start : start + width] += level * 0.8 * _signs(width)
        clicks.append(start)
        t += period
    return left, right, np.array(clicks)


def bursts(starts, strengths, seconds, rate=RATE, width=16, seed=2, noise=0.005):
    """Quiet noise with a burst of the given strength (standard deviation) at each start sample, in both channels."""
    rng = np.random.default_rng(seed)
    count = int(round(seconds * rate))
    left = rng.normal(0, noise, count)
    right = rng.normal(0, noise, count)
    for start, strength in zip(starts, strengths):
        left[start : start + width] += strength * _signs(width)
        right[start : start + width] += strength * _signs(width)
    return left, right


def silence(seconds, rate=RATE):
    count = int(round(seconds * rate))
    return np.zeros(count), np.zeros(count)


def direct_energy(left, right):
    """The impulse energy worked out the slow, obvious way: a loop over 32-sample windows, standard deviation per channel, averaged."""
    left = np.asarray(left, dtype=np.float64)
    right = np.asarray(right, dtype=np.float64)
    out = []
    for i in range(len(left) // IMPULSE):
        a = left[i * IMPULSE : (i + 1) * IMPULSE]
        b = right[i * IMPULSE : (i + 1) * IMPULSE]
        out.append((np.std(a) + np.std(b)) / 2)
    return np.array(out)
