"""The ``local_peaks`` measurement: the periodic local maxima of the *overall* energy of a file (not only of its notes).

Two windows are involved:

* the **impulse window**: 32 consecutive, non-overlapping samples. The energy of an impulse window is the average of the
  standard deviation of the left channel's samples and that of the right channel's (each channel on its own, then averaged; a
  mono file has two equal channels). A file becomes one energy per 32 samples;
* the **peaks window**: a running window of 4096 impulse energies (the size is a parameter and its exact value is not
  important). ``scipy.signal.find_peaks`` is called on it with ``distance`` (the *minimum distance*, a time, converted to a
  number of impulse samples) and ``prominence`` (the *prominence* percentage of the window's largest energy).

The window moves through the file in steps of half its length. Each window *owns* its central half (the first window also its
start, the last its end), so the owned zones tile the file: a peak is judged once, with at least a quarter window of energy on
each side of it, and is neither lost nor reported twice. ``find_peaks`` can only keep the minimum distance inside a window, so
a last pass keeps it across the borders of the zones (the stronger of two close peaks stays).

Every peak records the sample where the maximum is (the first sample of its impulse window), its energy, the smallest and the
largest impulse energy of the peaks window it was found in, and the rate in peaks per minute (60 times the file rate over the
samples since the previous peak; the first peak, with no predecessor, has the default rate of 60). A finished measurement
answers the interpolated energy and the rate at any point of the file (:class:`LocalPeaks`).

This module knows nothing about the note analysis, the frames or the router: it takes the two channels and the file's sample
rate. Nothing uses it yet; how it is used in the pictures is a later feature.
"""

import math
import numbers
from dataclasses import dataclass
from functools import cached_property

import numpy as np
from scipy.signal import find_peaks

from .note_analysis import _to_float, read_wav

IMPULSE_SAMPLES = 32
PEAKS_WINDOW = 4096

# the minimum distance between two peaks, in milliseconds
MIN_MIN_DISTANCE = 100.0
MAX_MIN_DISTANCE = 2000.0
DEFAULT_MIN_DISTANCE = 100.0

# the prominence, in percent of the largest energy of the peaks window
MIN_PROMINENCE = 0.0
MAX_PROMINENCE = 100.0
DEFAULT_PROMINENCE = 50.0

# peaks per minute before the first peak, and for the first peak: one per second
DEFAULT_RATE = 60.0


def _check_setting(value, low: float, high: float, message: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, numbers.Real)
        or not math.isfinite(value)
        or not low <= value <= high
    ):
        raise ValueError(message)
    return float(value) + 0.0  # turns -0.0 into 0.0


def check_min_distance(value) -> float:
    """Return ``value`` as a ``float`` when it is a number of milliseconds from 100 to 2000; anything else is refused."""
    return _check_setting(
        value,
        MIN_MIN_DISTANCE,
        MAX_MIN_DISTANCE,
        f"The minimum distance must be a number from {MIN_MIN_DISTANCE:g} to {MAX_MIN_DISTANCE:g} milliseconds.",
    )


def check_prominence(value) -> float:
    """Return ``value`` as a ``float`` when it is a percentage from 0 to 100; anything else is refused."""
    return _check_setting(
        value,
        MIN_PROMINENCE,
        MAX_PROMINENCE,
        f"The prominence must be a number from {MIN_PROMINENCE:g} to {MAX_PROMINENCE:g} percent.",
    )


@dataclass(frozen=True)
class LocalPeak:
    """One local maximum of the overall energy."""

    sample: int  # the first sample of the impulse window where the maximum is
    energy: float  # the impulse energy there
    window_min: float  # the smallest impulse energy of the peaks window it was found in
    window_max: float  # the largest impulse energy of that window
    rate: float  # peaks per minute, from the time since the previous peak (DEFAULT_RATE for the first peak)


@dataclass(frozen=True)
class LocalPeaks:
    """The local peaks of one file, in order of sample, and the means to ask for the energy and the rate at any point."""

    peaks: tuple[LocalPeak, ...]
    file_rate: int
    sample_count: int
    min_distance: float
    prominence: float

    @cached_property
    def _samples(self) -> np.ndarray:
        return np.array([p.sample for p in self.peaks], dtype=np.float64)

    @cached_property
    def _energies(self) -> np.ndarray:
        return np.array([p.energy for p in self.peaks], dtype=np.float64)

    @cached_property
    def _rates(self) -> np.ndarray:
        return np.array([p.rate for p in self.peaks], dtype=np.float64)

    @cached_property
    def _window_mins(self) -> np.ndarray:
        return np.array([p.window_min for p in self.peaks], dtype=np.float64)

    @cached_property
    def _window_maxs(self) -> np.ndarray:
        return np.array([p.window_max for p in self.peaks], dtype=np.float64)

    def energy_at(self, point):
        """The interpolated energy at a sample number, or at each of a sequence of them.

        A straight line between the energy of the previous peak and that of the next; 0 before the first peak; the last peak's
        energy after the last (also past the end of the file and for a negative point); 0 for a file without peaks.
        """
        points, scalar = _points(point)
        if not len(self.peaks):
            answer = np.zeros(points.shape)
        else:
            answer = np.interp(points, self._samples, self._energies, left=0.0, right=self._energies[-1])
        return float(answer) if scalar else answer

    def rate_at(self, point):
        """The rate, in peaks per minute, at a sample number, or at each of a sequence of them.

        The rate of the last peak at or before the point (it is not interpolated); the default of 60 before the first peak and
        for a file without peaks.
        """
        points, scalar = _points(point)
        if not len(self.peaks):
            answer = np.full(points.shape, DEFAULT_RATE)
        else:
            before = np.searchsorted(self._samples, points, side="right") - 1
            answer = np.where(before < 0, DEFAULT_RATE, self._rates[np.maximum(before, 0)])
        return float(answer) if scalar else answer

    def position_at(self, point):
        """The place of a sample number (or of each of a sequence) in the local energy peak, from 0 to 1.

        The interpolated energy (see :meth:`energy_at`) between the smallest and the largest energy of the peaks windows of
        the neighbouring peaks, those two interpolated in the same straight line from the previous peak to the next. 0 is the
        minimum, 1 the maximum; a value outside is held at the nearest end. It is 0 before the first peak, for a file without
        peaks and where the smallest and the largest energy leave no range; after the last peak it is worked out from the
        last peak's own values.
        """
        points, scalar = _points(point)
        if not len(self.peaks):
            answer = np.zeros(points.shape)
        else:
            energy = np.interp(points, self._samples, self._energies, left=0.0, right=self._energies[-1])
            low = np.interp(points, self._samples, self._window_mins, left=0.0, right=self._window_mins[-1])
            high = np.interp(points, self._samples, self._window_maxs, left=0.0, right=self._window_maxs[-1])
            span = high - low
            answer = np.where(span > 0.0, np.clip((energy - low) / np.where(span > 0.0, span, 1.0), 0.0, 1.0), 0.0)
        return float(answer) if scalar else answer

    def position_at_time(self, seconds):
        """:meth:`position_at` at a time in seconds (or at each of a sequence of them)."""
        return self.position_at(_times(seconds, self.file_rate))

    def frame_positions(self, frame_rate, frames) -> np.ndarray:
        """The position in the local peak of the middle of each of ``frames`` frames of ``frame_rate`` frames per second."""
        if isinstance(frame_rate, bool) or not isinstance(frame_rate, numbers.Real) or not math.isfinite(frame_rate) or frame_rate <= 0:
            raise ValueError("The frame rate must be a positive number.")
        if isinstance(frames, bool) or not isinstance(frames, numbers.Integral) or frames < 0:
            raise ValueError("The number of frames must be a whole number of at least 0.")
        return np.atleast_1d(self.position_at_time((np.arange(int(frames)) + 0.5) / float(frame_rate)))

    def energy_at_time(self, seconds):
        """The interpolated energy at a time in seconds (or at each of a sequence of them)."""
        return self.energy_at(_times(seconds, self.file_rate))

    def rate_at_time(self, seconds):
        """The rate, in peaks per minute, at a time in seconds (or at each of a sequence of them)."""
        return self.rate_at(_times(seconds, self.file_rate))


def _points(point) -> tuple[np.ndarray, bool]:
    """``point`` as a float64 array and whether it was a single number; anything that is not finite numbers is refused."""
    array = np.asarray(point)
    if array.dtype.kind not in "iuf":
        raise ValueError("The point must be a finite number.")
    array = array.astype(np.float64)
    if not np.all(np.isfinite(array)):
        raise ValueError("The point must be a finite number.")
    return array, array.ndim == 0


def _times(seconds, file_rate: int) -> np.ndarray:
    points, _ = _points(seconds)
    return points * file_rate


def _channel(samples, name: str) -> np.ndarray:
    array = np.asarray(samples)
    if array.ndim != 1 or not (np.issubdtype(array.dtype, np.number) and not np.issubdtype(array.dtype, np.complexfloating)):
        raise ValueError("The left and right channels must be one-dimensional and of the same length.")
    return _to_float(array)


def impulse_energy(left, right) -> np.ndarray:
    """One energy per window of 32 samples: the average of the left and the right standard deviation of that window.

    Integer samples are scaled to about -1 to 1 (as in the note analysis) so the bit depth does not matter. A last window of
    fewer than 32 samples is dropped. The inputs are not changed.
    """
    left, right = _channel(left, "left"), _channel(right, "right")
    if len(left) != len(right):
        raise ValueError("The left and right channels must be one-dimensional and of the same length.")
    count = len(left) // IMPULSE_SAMPLES
    used = count * IMPULSE_SAMPLES
    spread_left = left[:used].reshape(count, IMPULSE_SAMPLES).std(axis=1)
    spread_right = right[:used].reshape(count, IMPULSE_SAMPLES).std(axis=1)
    return (spread_left + spread_right) / 2


def _distance_in_impulse_samples(min_distance: float, file_rate: int) -> int:
    return max(1, round(min_distance / 1000.0 * file_rate / IMPULSE_SAMPLES))


def window_zones(count: int, window: int):
    """Yield ``(start, end, low, high)`` for every peaks window over ``count`` impulse samples.

    The window is ``[start, end)`` and owns the zone ``[low, high)``: its central half, plus the start of the file for the first
    window and the end of the file for the last. The zones tile ``[0, count)`` (no gap and no overlap), and a peak in a zone has
    at least a quarter window of energy on each side of it unless it is at the start or the end of the file.
    """
    step, quarter = window // 2, window // 4
    start = 0
    while count:
        end = min(start + window, count)
        last = end == count
        yield start, end, 0 if start == 0 else start + quarter, end if last else start + 3 * quarter
        if last:
            break
        start += step


def _window_peaks(energy: np.ndarray, distance: int, prominence: float, window: int):
    """Yield ``(index, window_min, window_max)`` for every peak of every peaks window, each in the zone its window owns."""
    for start, end, low, high in window_zones(len(energy), window):
        part = energy[start:end]
        top = float(part.max())
        if top > 0.0:
            found, _ = find_peaks(part, distance=distance, prominence=prominence / 100.0 * top)
            smallest = float(part.min())
            for index in found:
                if low <= start + int(index) < high:
                    yield start + int(index), smallest, top


def measure_local_peaks(
    left,
    right,
    file_rate: int,
    min_distance: float = DEFAULT_MIN_DISTANCE,
    prominence: float = DEFAULT_PROMINENCE,
    window: int = PEAKS_WINDOW,
) -> LocalPeaks:
    """Find the periodic local maxima of the overall energy of a file.

    ``min_distance`` (milliseconds, 100 to 2000) and ``prominence`` (percent, 0 to 100) are checked before anything is
    measured. ``window`` is the size of the peaks window in impulse samples; the result does not depend on it for peaks that
    are well apart.
    """
    min_distance = check_min_distance(min_distance)
    prominence = check_prominence(prominence)
    if isinstance(file_rate, bool) or not isinstance(file_rate, numbers.Integral) or file_rate <= 0:
        raise ValueError("The sample rate must be a positive whole number.")
    if isinstance(window, bool) or not isinstance(window, numbers.Integral) or window < 8:
        raise ValueError("The peaks window must be a whole number of at least 8 impulse samples.")
    file_rate, window = int(file_rate), int(window) // 2 * 2
    energy = impulse_energy(left, right)
    distance = _distance_in_impulse_samples(min_distance, file_rate)

    kept: list[tuple[int, float, float]] = []
    for found in _window_peaks(energy, distance, prominence, window):
        if kept and found[0] - kept[-1][0] < distance:
            # only close to the last peak across the border of two zones: the stronger one stays
            if energy[found[0]] > energy[kept[-1][0]]:
                kept[-1] = found
            continue
        kept.append(found)

    peaks = []
    previous = None
    for index, smallest, largest in kept:
        sample = index * IMPULSE_SAMPLES
        rate = DEFAULT_RATE if previous is None else 60.0 * file_rate / (sample - previous)
        peaks.append(LocalPeak(sample, float(energy[index]), smallest, largest, rate))
        previous = sample
    return LocalPeaks(tuple(peaks), file_rate, len(np.asarray(left)), min_distance, prominence)


def measure_wav(path, min_distance: float = DEFAULT_MIN_DISTANCE, prominence: float = DEFAULT_PROMINENCE, display_name: str | None = None) -> LocalPeaks:
    """:func:`measure_local_peaks` of a mono or stereo WAV file (the settings are checked before the file is read)."""
    min_distance = check_min_distance(min_distance)
    prominence = check_prominence(prominence)
    file_rate, left, right = read_wav(path, display_name)
    return measure_local_peaks(left, right, int(file_rate), min_distance, prominence)
