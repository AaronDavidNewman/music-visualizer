"""The noise floor: a note this far below the loudest note of the file is not a note.

The note analysis gives every analysis window a strength for each note, and the strengths are never exactly 0: the spectrum leaks into notes nobody
plays, and recordings carry hiss. A strength **strictly below** one thousandth of the largest strength anywhere in the file (60 dB below it: the
strengths are magnitudes of the spectrum, amplitudes, so -60 dB is a factor of 1,000) is set to exactly 0, so that it is not counted as a note or as
part of a chord by any picture or measurement. A strength exactly at the floor is kept.

The floor is **fixed**: there is no setting for it, and it applies to every image type, whether or not the image type has a Threshold. The reference
is the loudest value of the whole file, the four notes above the 84 piano notes included, as for the Threshold setting; the analysed strengths have
no absolute decibel scale (they depend on the window size and on the recording), so "-60 dB" can only be a ratio to the loudest note of the file.

The cut is made once, on the analysed windows (``floor_analysis``, called by the job right after the analysis), and again by the chord measurement
on the strengths it is given (``chords.measure_chords``), so that it holds for any array. It is idempotent: the largest value is never cut, and what
is cut is below the floor of the array it came from.

This module knows nothing about the audio, the pictures or the job: it takes arrays of note strengths.
"""

import dataclasses
import numbers

import numpy as np

from .note_analysis import AnalysisResult

NOISE_FLOOR_DB = -60  # decibels of amplitude below the loudest note of the file
NOISE_FLOOR = 10 ** (NOISE_FLOOR_DB / 20)  # the same as a ratio of strengths: 0.001

VALUES_MESSAGE = "The note values must be finite numbers that are not negative."
PEAK_MESSAGE = "The peak must be a finite number that is not negative."


def apply_noise_floor(values, peak=None) -> np.ndarray:
    """A ``float64`` copy of ``values`` with every value strictly below ``NOISE_FLOOR * peak`` set to ``0.0``.

    ``values`` is an array of any shape of finite numbers that are not negative. ``peak`` is the largest value the floor is measured against: by
    default the largest value of ``values`` (all of it, whatever the columns), or 0 for an empty array. With a peak of 0 nothing is cut. The input is
    not changed.
    """
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError(VALUES_MESSAGE) from None
    if array.size and (not np.isfinite(array).all() or array.min() < 0):
        raise ValueError(VALUES_MESSAGE)
    if peak is None:
        reference = float(array.max()) if array.size else 0.0
    else:
        if isinstance(peak, (bool, np.bool_)) or not isinstance(peak, numbers.Real) or not np.isfinite(peak) or peak < 0:
            raise ValueError(PEAK_MESSAGE)
        reference = float(peak)
    result = array.copy()
    result[array < NOISE_FLOOR * reference] = 0.0
    return result


def floor_analysis(result: AnalysisResult) -> AnalysisResult:
    """A new analysis result whose frames are cut by the noise floor (the reference is the largest value of all windows and all columns).

    The sample rate, the window size, the sample count and the window starts and step are those of ``result``, which is not changed.
    """
    return dataclasses.replace(result, frames=apply_noise_floor(result.frames))
