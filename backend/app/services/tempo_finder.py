"""The ``tempo_finder``: a current tempo, between 60 and 156 beats per minute, that follows the local peaks of a file
(feature 040).

A peak of the energy is not always on the beat (a tied note leaves none on it, a group of beats has a peak of its own),
so the tempo of the latest interval between two peaks is a poor tempo. This finder keeps a **current tempo** that each
new interval only *nudges*:

* the tempo starts at **120** beats per minute. The first peak has no interval, so it gives no sample;
* every later peak gives a **sample**: ``60 / the seconds since the previous peak``. The latest **5** samples are kept
  (fewer while there are fewer);
* a sample is **matched** to the tempo or to a **slower or faster** tempo related to it (:data:`RATIOS`): the value
  among ``s`` (it is the tempo), ``2 s`` (it is the half of the tempo), ``1.5 s`` (two thirds of it), ``s / 2`` (it is
  twice the tempo) and ``s / 1.5`` (one and a half times it) nearest to the tempo *in ratio* is what the sample stands
  for (the plain tempo on a tie), **but only when the sample is within** :data:`HARMONIC_TOLERANCE` (15 percent) **of
  that related tempo**: a sample that is not near any of them stands for itself, so steady peaks at 150 beats per minute
  drift to 150 and not to 100 (150 is one and a half times 100, but nothing near 100 was ever heard). Faster tempos are
  considered too because peaks come often faster than the beat (a peak on each half beat, a roll): without them such
  samples would only push the tempo up to its limit;
* with the mean and the standard deviation (of the whole population of the kept samples, the new one included, and at
  least :data:`MIN_STEP`: a perfectly steady beat has a deviation of 0 and the tempo would never move) of the kept
  samples: **within one deviation** of the tempo, the tempo becomes the average of the sample and the mean; otherwise it
  moves by one deviation toward the sample (never past it);
* **above 156** the tempo becomes **78**, **below 60** it becomes **120**, and in both cases the kept samples are thrown
  away and counted from scratch, so the tempo is always from 60 to 156.

The tempo after a peak is the tempo from that peak until the next one. This module knows nothing about the audio, the
job or the pictures: it takes the times of the peaks, in seconds. How it is shown is ``rhythm_circles``'s business.

Order of operations:
    1. Check the times - ``_times()`` (called first by ``find_tempo()``) - ``PeakTimes`` ``(peaks,)`` as float64: finite
       and strictly increasing, else refused.
    2. Start at 120 beats per minute - ``find_tempo()`` - the first peak gives no sample, so ``tempos[0]`` is 120.
    3. For each later peak, take its sample - ``find_tempo()`` - 60 divided by the seconds since the previous peak:
       beats per minute.
    4. Match the sample to a related tempo - ``match_sample()`` - the nearest in ratio of the tempo, half, two thirds,
       double and one and a half times it, only when within 15 percent of it, else the sample stands for itself.
    5. Keep the latest 5 matched samples and take their mean and (at least 1 beat per minute) standard deviation -
       ``find_tempo()``.
    6. Move the tempo - ``find_tempo()`` - within one deviation of the sample: the average of the sample and the mean;
       otherwise one deviation toward the sample.
    7. Keep it in range - ``find_tempo()`` - above 156 it becomes 78, below 60 it becomes 120, and the kept samples are
       thrown away.
    8. Store the tempo after the peak - ``find_tempo()`` - ``Tempos`` ``(peaks,)`` in a ``TempoTrack`` with the number
       of restarts.
"""

import math
from dataclasses import dataclass

import numpy as np

from .array_types import ArrayLike, PeakTimes, Tempos

START_TEMPO = 120.0  # beats per minute before the first sample, and after a restart from below
LOW_LIMIT = 60.0  # a tempo below it is restarted at START_TEMPO
HIGH_LIMIT = 156.0  # a tempo above it is restarted at HIGH_RESTART
HIGH_RESTART = 78.0  # 156 halved, as written
WINDOW = 5  # the number of samples kept
MIN_STEP = 1.0  # beats per minute: the smallest deviation that is used
# a sample stands for a related tempo only within this share of it (15 percent); farther, it stands for itself
HARMONIC_TOLERANCE = 0.15
# a sample close to the tempo, to its half, two thirds, double or one and a half times stands for ``s * ratio``
RATIOS = (1.0, 2.0, 1.5, 0.5, 2 / 3)


@dataclass(frozen=True)
class TempoTrack:
    """The current tempo after each peak and how many times it was restarted.

    Attributes:
        ``tempos``: ``Tempos`` ``(peaks,)`` - the current tempo after each peak in beats per minute, each from 60 to 156
            (``tempos[0]`` is 120: the first peak gives no sample).
    """

    tempos: Tempos
    restarts: int


def _times(times: ArrayLike) -> PeakTimes:
    """The peak times as a float64 array; anything that is not a list of finite numbers in strictly increasing order is
    refused.

    Arrays:
        ``times``: ``ArrayLike`` ``(peaks,)`` - the time of each local peak in seconds, strictly increasing.

    Returns:
        ``PeakTimes`` ``(peaks,)`` - the same times as float64.
    """
    try:
        array = np.asarray(times, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The peak times must be a 1-D array of finite numbers in strictly increasing order.") from None
    if array.ndim != 1 or not np.isfinite(array).all() or (array.size > 1 and (np.diff(array) <= 0).any()):
        raise ValueError("The peak times must be a 1-D array of finite numbers in strictly increasing order.")
    return array


def match_sample(sample: float, tempo: float) -> float:
    """The tempo that ``sample`` (beats per minute) stands for: ``sample * ratio`` for the ratio in :data:`RATIOS` that
    comes nearest to ``tempo`` in ratio.

    The first ratio (the plain tempo) when two are equally near, and the plain tempo when the nearest ratio (other than
    the plain tempo) leaves the sample more than :data:`HARMONIC_TOLERANCE` away from the tempo: a sample that is not
    near a related tempo stands for itself.
    """
    best = min(RATIOS, key=lambda ratio: abs(math.log(sample * ratio / tempo)))
    # (for the plain tempo this sends it to itself: no change)
    if abs(math.log(sample * best / tempo)) > math.log(1 + HARMONIC_TOLERANCE):
        best = RATIOS[0]
    return sample * best


def find_tempo(times: ArrayLike) -> TempoTrack:
    """The current tempo after each peak, for peaks at ``times`` (seconds, finite, strictly increasing).

    ``tempos[0]`` is :data:`START_TEMPO` (the first peak gives no sample); every tempo is from :data:`LOW_LIMIT` to
    :data:`HIGH_LIMIT`. The input is not changed.

    Arrays:
        ``times``: ``ArrayLike`` ``(peaks,)`` - the time of each local peak in seconds, finite and strictly increasing
            (``PeakTimes``).

    Returns:
        A ``TempoTrack`` whose ``tempos`` is ``Tempos`` ``(peaks,)``: the current tempo after each peak, in beats per
        minute, from 60 to 156.
    """
    times = _times(times)
    tempos = np.full(times.shape, START_TEMPO)
    tempo, window, restarts = START_TEMPO, [], 0
    for i in range(1, times.shape[0]):
        sample = match_sample(60.0 / (times[i] - times[i - 1]), tempo)
        window = (window + [sample])[-WINDOW:]
        mean = float(np.mean(window))
        deviation = max(float(np.std(window)), MIN_STEP)
        if abs(sample - tempo) <= deviation:
            tempo = (sample + mean) / 2
        else:
            # the gap is more than a deviation here, so this never passes the sample
            tempo += math.copysign(deviation, sample - tempo)
        if tempo > HIGH_LIMIT:
            tempo, window, restarts = HIGH_RESTART, [], restarts + 1
        elif tempo < LOW_LIMIT:
            tempo, window, restarts = START_TEMPO, [], restarts + 1
        tempos[i] = tempo
    return TempoTrack(tempos, restarts)
