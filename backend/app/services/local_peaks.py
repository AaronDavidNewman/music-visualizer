"""The ``local_peaks`` measurement: the periodic local maxima of the *overall* energy of a file (not only of its notes).

Two windows are involved:

* the **impulse window**: 32 consecutive, non-overlapping samples. The energy of an impulse window is the average of the
  standard deviation of the left channel's samples and that of the right channel's (each channel on its own, then
  averaged; a mono file has two equal channels). A file becomes one energy per 32 samples;
* the **peaks window**: a running window of 4096 impulse energies (the size is a parameter and its exact value is not
  important). ``scipy.signal.find_peaks`` is called on it with ``distance`` (the *minimum distance*, a time, converted
  to a number of impulse samples) and ``prominence`` (the *prominence* percentage of the window's largest energy).

The window moves through the file in steps of half its length. Each window *owns* its central half (the first window
also its start, the last its end), so the owned zones tile the file: a peak is judged once, with at least a quarter
window of energy on each side of it, and is neither lost nor reported twice. ``find_peaks`` can only keep the minimum
distance inside a window, so a last pass keeps it across the borders of the zones (the stronger of two close peaks
stays).

Every peak records the sample where the maximum is (the first sample of its impulse window), its energy, the smallest
and the largest impulse energy of the peaks window it was found in, and the rate in peaks per minute (60 times the file
rate over the samples since the previous peak; the first peak, with no predecessor, has the default rate of 60). A
finished measurement answers the interpolated energy and the rate at any point of the file (:class:`LocalPeaks`). After
the last peak there is no next peak to interpolate with, so the energy falls in a straight line from the last peak's
energy to 0 at the end of the file: the last beat is taken to last for whatever is left of the file, and a file always
ends on a down part of the beat.

This module knows nothing about the note analysis, the frames or the router: it takes the two channels and the file's
sample rate. The pictures use it through the job (``jobs.py``: the minimum distance is a setting, the prominence is
fixed: ``DEFAULT_PROMINENCE``) and ``tempo_finder`` makes a current tempo of the peak times.

Order of operations:
    1. Check the settings - ``check_min_distance()``, ``check_prominence()`` - before anything is measured
       (``measure_wav()`` before the file is read).
    2. Read the file - ``measure_wav()`` with ``note_analysis.read_wav()`` - two channels of ``RawSamples``
       ``(samples,)`` and the sample rate.
    3. Measure the loudness of the file - ``impulse_energy()`` - ``ImpulseEnergies`` ``(impulses,)``: one energy for
       each window of 32 samples.
    4. Turn the minimum distance into impulse windows - ``_distance_in_impulse_samples()`` - a whole number of impulse
       windows.
    5. Cut the energies into peaks windows that each own their central half - ``window_zones()`` (used by
       ``_window_peaks()``) - start, end and owned zone of each window (in impulse windows).
    6. Find the peaks of each window - ``_window_peaks()`` - ``scipy.signal.find_peaks`` with the distance and the
       prominence (a share of the window's largest energy), keeping only the peaks inside the zone the window owns.
    7. Keep the minimum distance across the borders of the zones - ``measure_local_peaks()`` - of two peaks that are too
       close the stronger stays.
    8. Record each peak - ``measure_local_peaks()`` - ``LocalPeak``: its sample, energy, the smallest and largest energy
       of its window, and its rate in beats per minute.
    9. Answer questions about the file - ``LocalPeaks`` - ``energy_at()``, ``rate_at()``, ``position_at()`` (a straight
       line through the peaks, down to 0 at the end of the file) and ``frame_positions()`` (``BeatPositions``
       ``(frames,)``: the place of the middle of each frame in the beat, 0 to 1).
"""

import math
import numbers
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cached_property
from os import PathLike

import numpy as np
from scipy.signal import find_peaks

from .array_types import ArrayLike, BeatPositions, ImpulseEnergies, PeakEnergies, PeakRates, PeakSamples, PointValues, RawSamples, Samples
from .note_analysis import _to_float, read_wav

IMPULSE_SAMPLES = 32
PEAKS_WINDOW = 4096

# the minimum distance between two peaks, in milliseconds
MIN_MIN_DISTANCE = 100.0
MAX_MIN_DISTANCE = 2000.0
DEFAULT_MIN_DISTANCE = 350.0

# the prominence, in percent of the largest energy of the peaks window; the job always uses the default (since feature
# 040 it is not a setting)
MIN_PROMINENCE = 0.0
MAX_PROMINENCE = 100.0
DEFAULT_PROMINENCE = 15.0

# peaks per minute before the first peak, and for the first peak: one per second
DEFAULT_RATE = 60.0


def _check_setting(value: object, low: float, high: float, message: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, numbers.Real)
        or not math.isfinite(value)
        or not low <= value <= high
    ):
        raise ValueError(message)
    return float(value) + 0.0  # turns -0.0 into 0.0


def check_min_distance(value: object) -> float:
    """Return ``value`` as a ``float`` when it is a number of milliseconds from 100 to 2000; anything else is refused.
    """
    return _check_setting(
        value,
        MIN_MIN_DISTANCE,
        MAX_MIN_DISTANCE,
        f"The minimum distance must be a number from {MIN_MIN_DISTANCE:g} to {MAX_MIN_DISTANCE:g} milliseconds.",
    )


def check_prominence(value: object) -> float:
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
    """The local peaks of one file, in order of sample, and the means to ask for the energy and the rate at any point.

    Attributes:
        ``peaks``: a tuple of ``LocalPeak``, one for each peak, in time order; the arrays below (``_samples`` and the
            others, made on first use) hold one entry for each peak.
    """

    peaks: tuple[LocalPeak, ...]
    file_rate: int
    sample_count: int
    min_distance: float
    prominence: float

    @cached_property
    def _samples(self) -> PeakSamples:
        """The sample of each peak, as float64.

        Returns:
            ``PeakSamples`` ``(peaks,)`` - the first sample of the impulse window where each peak is.
        """
        return np.array([p.sample for p in self.peaks], dtype=np.float64)

    @cached_property
    def _energies(self) -> PeakEnergies:
        """The impulse energy at each peak.

        Returns:
            ``PeakEnergies`` ``(peaks,)`` - the impulse energy at each peak (0 or more).
        """
        return np.array([p.energy for p in self.peaks], dtype=np.float64)

    @cached_property
    def _rates(self) -> PeakRates:
        """The rate of each peak.

        Returns:
            ``PeakRates`` ``(peaks,)`` - the rate of each peak in beats per minute (60 for the first).
        """
        return np.array([p.rate for p in self.peaks], dtype=np.float64)

    @cached_property
    def _window_mins(self) -> PeakEnergies:
        """The smallest impulse energy of the peaks window of each peak.

        Returns:
            ``PeakEnergies`` ``(peaks,)`` - the smallest impulse energy of the peaks window in which each peak was
            found.
        """
        return np.array([p.window_min for p in self.peaks], dtype=np.float64)

    @cached_property
    def _window_maxs(self) -> PeakEnergies:
        """The largest impulse energy of the peaks window of each peak.

        Returns:
            ``PeakEnergies`` ``(peaks,)`` - the largest impulse energy of the peaks window in which each peak was found.
        """
        return np.array([p.window_max for p in self.peaks], dtype=np.float64)

    def _energy_line(self, points: PointValues) -> PointValues:
        """The energy at the points, for a measurement that has peaks: the line through the peaks, then down to 0 at the
        end of the file.

        Arrays:
            ``points``: ``PointValues`` ``(points,)`` - sample numbers to ask about (any, also before the first peak or
                past the end of the file).

        Returns:
            ``PointValues`` ``(points,)`` - the interpolated energy at each point; 0 before the first peak and past the
            end.
        """
        # the last beat lasts for whatever is left of the file
        end = max(float(self.sample_count), self._samples[-1] + 1.0)
        return np.interp(
            points,
            np.append(self._samples, end),
            np.append(self._energies, 0.0),
            left=0.0,
            right=0.0,
        )

    def energy_at(self, point: float | ArrayLike) -> float | PointValues:
        """The interpolated energy at a sample number, or at each of a sequence of them.

        A straight line between the energy of the previous peak and that of the next; 0 before the first peak; after the
        last peak a straight line from the last peak's energy down to 0 at the end of the file (the last beat is taken
        to last for whatever is left of the file, so the file ends on a down part of the beat), and 0 past the end and
        for a negative point; 0 for a file without peaks.

        Arrays:
            ``point``: a number or ``ArrayLike`` ``(points,)`` - sample numbers of the file (finite numbers).

        Returns:
            A number for a single point, or ``PointValues`` ``(points,)`` - the interpolated impulse energy (0 or more)
            at each point.
        """
        points, scalar = _points(point)
        if not len(self.peaks):
            answer = np.zeros(points.shape)
        else:
            answer = self._energy_line(points)
        return float(answer) if scalar else answer

    def rate_at(self, point: float | ArrayLike) -> float | PointValues:
        """The rate, in peaks per minute, at a sample number, or at each of a sequence of them.

        The rate of the last peak at or before the point (it is not interpolated); the default of 60 before the first
        peak and for a file without peaks.

        Arrays:
            ``point``: a number or ``ArrayLike`` ``(points,)`` - sample numbers of the file (finite numbers).

        Returns:
            A number for a single point, or ``PointValues`` ``(points,)`` - the rate in beats per minute at each point.
        """
        points, scalar = _points(point)
        if not len(self.peaks):
            answer = np.full(points.shape, DEFAULT_RATE)
        else:
            before = np.searchsorted(self._samples, points, side="right") - 1
            answer = np.where(before < 0, DEFAULT_RATE, self._rates[np.maximum(before, 0)])
        return float(answer) if scalar else answer

    def position_at(self, point: float | ArrayLike) -> float | PointValues:
        """The place of a sample number (or of each of a sequence) in the local energy peak, from 0 to 1.

        The interpolated energy (see :meth:`energy_at`) between the smallest and the largest energy of the peaks windows
        of the neighbouring peaks, those two interpolated in the same straight line from the previous peak to the next.
        0 is the minimum, 1 the maximum; a value outside is held at the nearest end. It is 0 before the first peak, for
        a file without peaks and where the smallest and the largest energy leave no range; after the last peak the
        smallest and the largest energy are those of the last peak's window and the energy falls to 0 at the end of the
        file (see :meth:`energy_at`), so the position falls to 0 and the file ends on a down part of the beat.

        Arrays:
            ``point``: a number or ``ArrayLike`` ``(points,)`` - sample numbers of the file (finite numbers).

        Returns:
            A number for a single point, or ``PointValues`` ``(points,)`` - the place in the local energy peak at each
            point, from 0 (the bottom) to 1 (the top).
        """
        points, scalar = _points(point)
        if not len(self.peaks):
            answer = np.zeros(points.shape)
        else:
            energy = self._energy_line(points)
            low = np.interp(points, self._samples, self._window_mins, left=0.0, right=self._window_mins[-1])
            high = np.interp(points, self._samples, self._window_maxs, left=0.0, right=self._window_maxs[-1])
            span = high - low
            answer = np.where(span > 0.0, np.clip((energy - low) / np.where(span > 0.0, span, 1.0), 0.0, 1.0), 0.0)
        return float(answer) if scalar else answer

    def position_at_time(self, seconds: float | ArrayLike) -> float | PointValues:
        """:meth:`position_at` at a time in seconds (or at each of a sequence of them).

        Arrays:
            ``seconds``: a number or ``ArrayLike`` ``(points,)`` - times in seconds from the start of the file.

        Returns:
            A number for a single time, or ``PointValues`` ``(points,)`` - the place in the local energy peak at each
            time, from 0 to 1.
        """
        return self.position_at(_times(seconds, self.file_rate))

    def frame_positions(self, frame_rate: float, frames: int) -> BeatPositions:
        """The position in the local peak of the middle of each of ``frames`` frames of ``frame_rate`` frames per
        second.

        Returns:
            ``BeatPositions`` ``(frames,)`` - the place of the middle of each frame (at ``(f + 0.5) / frame_rate``
            seconds) in the local energy peak, from 0 to 1.
        """
        if isinstance(frame_rate, bool) or not isinstance(frame_rate, numbers.Real) or not math.isfinite(frame_rate) or frame_rate <= 0:
            raise ValueError("The frame rate must be a positive number.")
        if isinstance(frames, bool) or not isinstance(frames, numbers.Integral) or frames < 0:
            raise ValueError("The number of frames must be a whole number of at least 0.")
        return np.atleast_1d(self.position_at_time((np.arange(int(frames)) + 0.5) / float(frame_rate)))

    def energy_at_time(self, seconds: float | ArrayLike) -> float | PointValues:
        """The interpolated energy at a time in seconds (or at each of a sequence of them).

        Arrays:
            ``seconds``: a number or ``ArrayLike`` ``(points,)`` - times in seconds from the start of the file.

        Returns:
            A number for a single time, or ``PointValues`` ``(points,)`` - the interpolated impulse energy at each time.
        """
        return self.energy_at(_times(seconds, self.file_rate))

    def rate_at_time(self, seconds: float | ArrayLike) -> float | PointValues:
        """The rate, in peaks per minute, at a time in seconds (or at each of a sequence of them).

        Arrays:
            ``seconds``: a number or ``ArrayLike`` ``(points,)`` - times in seconds from the start of the file.

        Returns:
            A number for a single time, or ``PointValues`` ``(points,)`` - the rate in beats per minute at each time.
        """
        return self.rate_at(_times(seconds, self.file_rate))


def _points(point: float | ArrayLike) -> tuple[PointValues, bool]:
    """``point`` as a float64 array and whether it was a single number; anything that is not finite numbers is refused.

    Arrays:
        ``point``: a number or ``ArrayLike`` ``(points,)`` - finite numbers (sample numbers, or seconds).

    Returns:
        A tuple of ``PointValues`` ``(points,)`` (or ``()`` for a single number) - the same numbers as float64 - and
        whether a single number was given.
    """
    array = np.asarray(point)
    if array.dtype.kind not in "iuf":
        raise ValueError("The point must be a finite number.")
    array = array.astype(np.float64)
    if not np.all(np.isfinite(array)):
        raise ValueError("The point must be a finite number.")
    return array, array.ndim == 0


def _times(seconds: float | ArrayLike, file_rate: int) -> PointValues:
    """Times in seconds as sample numbers.

    Arrays:
        ``seconds``: a number or ``ArrayLike`` ``(points,)`` - times in seconds from the start of the file.

    Returns:
        ``PointValues`` ``(points,)`` - the same times as sample numbers (seconds times the file's sample rate).
    """
    points, _ = _points(seconds)
    return points * file_rate


def _channel(samples: RawSamples | ArrayLike, name: str) -> Samples:
    """One channel as a float64 array scaled to about -1 to 1; anything that is not a one-dimensional list of real
    numbers is refused.

    Arrays:
        ``samples``: ``RawSamples`` ``(samples,)`` - one channel of the file as read (integers or floating point).

    Returns:
        ``Samples`` ``(samples,)`` - the scaled samples.
    """
    array = np.asarray(samples)
    if array.ndim != 1 or not (np.issubdtype(array.dtype, np.number) and not np.issubdtype(array.dtype, np.complexfloating)):
        raise ValueError("The left and right channels must be one-dimensional and of the same length.")
    return _to_float(array)


def impulse_energy(left: RawSamples | ArrayLike, right: RawSamples | ArrayLike) -> ImpulseEnergies:
    """One energy per window of 32 samples: the average of the left and the right standard deviation of that window.

    Integer samples are scaled to about -1 to 1 (as in the note analysis) so the bit depth does not matter. A last
    window of fewer than 32 samples is dropped. The inputs are not changed.

    Arrays:
        ``left``: ``RawSamples`` ``(samples,)`` - the left channel as read from the file.
        ``right``: ``RawSamples`` ``(samples,)`` - the right channel, the same length as ``left``.

    Returns:
        ``ImpulseEnergies`` ``(impulses,)`` - the energy of each window of 32 samples, in time order (``impulses`` is
        ``samples // 32``); 0 or more.
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


def window_zones(count: int, window: int) -> Iterator[tuple[int, int, int, int]]:
    """Yield ``(start, end, low, high)`` for every peaks window over ``count`` impulse samples.

    The window is ``[start, end)`` and owns the zone ``[low, high)``: its central half, plus the start of the file for
    the first window and the end of the file for the last. The zones tile ``[0, count)`` (no gap and no overlap), and a
    peak in a zone has at least a quarter window of energy on each side of it unless it is at the start or the end of
    the file.
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


def _window_peaks(energy: ImpulseEnergies, distance: int, prominence: float, window: int) -> Iterator[tuple[int, float, float]]:
    """Yield ``(index, window_min, window_max)`` for every peak of every peaks window, each in the zone its window owns.

    Arrays:
        ``energy``: ``ImpulseEnergies`` ``(impulses,)`` - the energy of each window of 32 samples of the whole file.

    Yields:
        For each peak: its index into ``energy`` (an impulse window), and the smallest and largest energy of the peaks
        window it was found in.
    """
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
    left: RawSamples | ArrayLike,
    right: RawSamples | ArrayLike,
    file_rate: int,
    min_distance: float = DEFAULT_MIN_DISTANCE,
    prominence: float = DEFAULT_PROMINENCE,
    window: int = PEAKS_WINDOW,
) -> LocalPeaks:
    """Find the periodic local maxima of the overall energy of a file.

    ``min_distance`` (milliseconds, 100 to 2000) and ``prominence`` (percent, 0 to 100) are checked before anything is
    measured. ``window`` is the size of the peaks window in impulse samples; the result does not depend on it for peaks
    that are well apart.

    Arrays:
        ``left``: ``RawSamples`` ``(samples,)`` - the left channel as read from the file.
        ``right``: ``RawSamples`` ``(samples,)`` - the right channel, the same length as ``left``.

    Returns:
        A ``LocalPeaks``: the peaks in time order (an empty tuple for silence), from which ``frame_positions()`` gives
        ``BeatPositions`` ``(frames,)``.
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


def measure_wav(path: str | PathLike[str], min_distance: float = DEFAULT_MIN_DISTANCE, prominence: float = DEFAULT_PROMINENCE, display_name: str | None = None) -> LocalPeaks:
    """:func:`measure_local_peaks` of a mono or stereo WAV file (the settings are checked before the file is read)."""
    min_distance = check_min_distance(min_distance)
    prominence = check_prominence(prominence)
    file_rate, left, right = read_wav(path, display_name)
    return measure_local_peaks(left, right, int(file_rate), min_distance, prominence)
