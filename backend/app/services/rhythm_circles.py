"""The ``rhythm-circles`` kind of picture: how rhythmic a section of sound is, as four concentric notched circles that
rotate.

Each circle is a ring of one color with a **notch** (an arc of 1/8 of the circle) in a contrasting color, and it
rotates; the notch shows the rotation. The speeds come from the **local peaks** of the sound (``local_peaks``: the
periodic maxima of its energy, the beats), whose times and rates are measured for the whole file, and from the **current
tempo** that the ``tempo_finder`` makes of them (always from 60 to 156 beats per minute; a peak is not always on the
beat, so the tempo of the latest peak alone is a poor tempo). There are two **layers**, each a **level** and, inside it,
the **rate of change** of that level (the circles of half and two thirds of the current tempo, and the eight circles
that were hard to read, were dropped in the second version of the feature). From the outer circle to the innermost:

1. **the current tempo**: the tempo finder's tempo after the latest peak (120 before the second peak and with no peak),
   in beats per minute: the circle makes as many revolutions per minute as the tempo has beats per minute, one for each
   beat, **clockwise** being positive;
2. **the rate of change of the current tempo**, from one peak to the next, divided by the seconds between them (beats
   per minute per second, taken as revolutions per minute); positive (clockwise) when it speeds up, negative
   (counterclockwise) when it slows down. A restart of the tempo (156 to 78, 60 to 120) is a spike in it;
3. **the local peak**: the rate of the latest peak, in beats per minute (60 for the first peak and before it): the
   circle makes as many revolutions per minute as the peak has beats per minute;
4. **the rate of change of the local peak**: the rate of a peak less the rate of the previous peak, divided by the
   seconds between them.

Every speed is **constant between two peaks and changes at each peak**; the **angle** of a circle is the running total
of its speed over time from the start of the file (an integral, exact at the time of each peak), so a notch never jumps
when a speed changes. Before the first peak (and with no peak at all) the speeds are those of the starting tempo of 120
and a peak rate of 60, and no change: ``DEFAULT_SPEEDS``.

The numbers are pure functions of the peaks (``peak_series``, ``circle_speeds``, ``circle_angles``, ``rhythm_angles``:
small arrays, testable without audio); the picture (``write_rhythm_frames``) is drawn independently for every frame from
the angles.

This module knows nothing about the audio, the job or the page: the peaks (or their times and rates), the frame rate and
the picture size are passed in.

Order of operations:
    1. Take the times and the rates of the peaks - ``rhythm_angles()`` - ``PeakTimes`` ``(peaks,)`` (each peak's sample
       over the file's sample rate) and ``PeakRates`` ``(peaks,)`` (each peak's rate in beats per minute).
    2. Find the current tempo - ``peak_series()`` with ``tempo_finder.find_tempo()`` - ``Tempos`` ``(peaks,)``: the
       tempo after each peak, from 60 to 156.
    3. Make the four series - ``peak_series()`` - ``CircleSeries`` ``(peaks, 4)``: the current tempo, its rate of
       change, the peak's rate, its rate of change, in revolutions per minute (a rate of change is the difference from
       the previous peak over the seconds between them).
    4. Choose the moments - ``rhythm_angles()`` - ``Moments`` ``(frames,)``: the middle of each frame,
       ``(f + 0.5) / frame_rate`` seconds.
    5. Turn the speeds into angles - ``circle_angles()`` (with ``circle_speeds()``'s step function) - ``CircleAngles``
       ``(frames, 4)``: the running total of ``speed / 60`` from the start of the file, in turns, so a notch never jumps
       when a speed changes; returned in a ``RhythmData``.
    6. (Drawing, ``write_rhythm_frames()``) check the data - ``_check_data()`` - and make the colors of the rings and of
       their notches - ``ring_colors_rows()`` - ``Indices`` ``(4,)`` into the colormap: the ring ``k`` at position
       ``(k - 1) / 3``, its notch at the opposite position.
    7. Make what never changes between frames, once for the picture size - ``_geometry()`` - the pixels that a ring
       touches, their ring, coverage, distance and direction.
    8. Draw each frame on its own (a few threads) - ``_frame()`` - each ring with a notch of an eighth of the circle
       centered at its angle, over the background: ``Pictures`` ``(height, width, 3)``, saved as ``frame_<index>.png``.
"""

import math
import numbers
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from .array_types import (
    ArrayLike,
    CircleAngles,
    CircleSeries,
    CircleSpeeds,
    ColorList,
    Indices,
    Moments,
    PeakRates,
    PeakTimes,
    Pictures,
    PixelAngles,
    PixelNumbers,
    PixelWeights,
    CenterDistances,
    Rgb,
)
from .colormaps import COLORMAP_STEPS, MIDDLE_COLOR_ROW, check_colormap, lookup_table
from .frame_saving import SAVE_WORKERS
from .local_peaks import DEFAULT_RATE, LocalPeaks
from .tempo_finder import START_TEMPO, find_tempo

LAYERS = 2  # the current tempo and the local peak's own tempo: each a level and the rate of change of that level
CIRCLES = 2 * LAYERS  # outer to inner: the level and the rate of change of each layer
# revolutions per minute before the first peak: the tempo of 120, the peak of 60
DEFAULT_SPEEDS = (START_TEMPO, 0.0, DEFAULT_RATE, 0.0)
NOTCH = 1 / 8  # the arc of a notch, as a share of the circle
# what ``_geometry`` returns: pixel numbers, ring, coverage, distance, angle
_Geometry = tuple[PixelNumbers, Indices, PixelWeights, CenterDistances, PixelAngles]
MARGIN = 10  # pixels between the outer circle and the nearer edge of the picture
GAP = 4  # pixels between two rings on the 600 x 400 picture (scaled with the picture)
REFERENCE_SIZE = 400  # the smaller side of the picture that GAP is for


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
        raise ValueError("The peak times must be numbers.") from None
    if array.ndim != 1 or not np.isfinite(array).all() or (array.size > 1 and (np.diff(array) <= 0).any()):
        raise ValueError("The peak times must be a 1-D array of finite numbers in strictly increasing order.")
    return array


def peak_series(times: ArrayLike, tempos: ArrayLike) -> CircleSeries:
    """The four series of the peaks: a float64 array ``(peaks, 4)`` in revolutions per minute, the circles from the
    outer (column 0) to the innermost (column 3).

    ``times`` are the times of the peaks in seconds (strictly increasing) and ``tempos`` their rates in beats per minute
    (above 0). For peak ``i`` the columns 0 and 2 are the levels of the layers, outer to inner: **the current tempo**
    (the tempo finder's tempo after the peak, from the peak times alone: :func:`tempo_finder.find_tempo`) and **the
    peak's own rate** ``tempos[i]``; the column after each is the change of that level:
    ``(x[i] - x[i - 1]) / (times[i] - times[i - 1])`` (0 for the first peak). The inputs are not changed.

    Arrays:
        ``times``: ``ArrayLike`` ``(peaks,)`` - the time of each local peak in seconds, strictly increasing
            (``PeakTimes``).
        ``tempos``: ``ArrayLike`` ``(peaks,)`` - the rate of each local peak in beats per minute, above 0
            (``PeakRates``).

    Returns:
        ``CircleSeries`` ``(peaks, 4)`` - the four speeds after each peak, in revolutions per minute: the current tempo,
        its rate of change, the peak's rate, its rate of change.
    """
    times = _times(times)
    try:
        tempos = np.asarray(tempos, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The tempos must be numbers.") from None
    if tempos.shape != times.shape or not np.isfinite(tempos).all() or (tempos <= 0).any():
        raise ValueError("The tempos must be one finite number above 0 for each peak.")
    peaks = times.shape[0]
    series = np.zeros((peaks, CIRCLES))
    if not peaks:
        return series
    current = find_tempo(times).tempos
    levels = [current, tempos]
    for circle, level in enumerate(levels):  # the level in column 2c, the change of the level in column 2c + 1
        series[:, 2 * circle] = level
        series[1:, 2 * circle + 1] = np.diff(level) / np.diff(times)
    return series


def _series(times: ArrayLike, series: ArrayLike) -> tuple[PeakTimes, CircleSeries]:
    """The times and the series as float64 arrays; refused when the series does not have one row of four finite numbers
    for each peak.

    Arrays:
        ``times``: ``ArrayLike`` ``(peaks,)`` - the time of each local peak in seconds, strictly increasing.
        ``series``: ``ArrayLike`` ``(peaks, 4)`` - the four speeds after each peak (``CircleSeries``).

    Returns:
        A tuple of ``PeakTimes`` ``(peaks,)`` and ``CircleSeries`` ``(peaks, 4)``, both as float64.
    """
    times = _times(times)
    try:
        series = np.asarray(series, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The series must be numbers.") from None
    if series.shape != (times.shape[0], CIRCLES) or not np.isfinite(series).all():
        raise ValueError(f"The series must be a ({times.shape[0]}, {CIRCLES}) array of finite numbers, one row for each peak.")
    return times, series


def _moments(moments: float | ArrayLike) -> Moments:
    """The moments as a one-dimensional float64 array of finite times of 0 seconds or more; anything else is refused.

    Arrays:
        ``moments``: a number or ``ArrayLike`` ``(moments,)`` - times in seconds from the start of the file.

    Returns:
        ``Moments`` ``(moments,)`` - the same times as float64 (a single number becomes an array of one).
    """
    try:
        array = np.atleast_1d(np.asarray(moments, dtype=np.float64))
    except (TypeError, ValueError):
        raise ValueError("The moments must be numbers.") from None
    if array.ndim != 1 or not np.isfinite(array).all() or (array < 0).any():
        raise ValueError("The moments must be finite numbers of seconds, 0 or more.")
    return array


def circle_speeds(times: ArrayLike, series: ArrayLike, moments: float | ArrayLike) -> CircleSpeeds:
    """The speed of the four circles at each moment, in revolutions per minute: a float64 array ``(moments, 4)``.

    A step function: the row of ``series`` of the latest peak at or before the moment, ``DEFAULT_SPEEDS`` before the
    first peak and with no peaks.

    Arrays:
        ``times``: ``ArrayLike`` ``(peaks,)`` - the time of each local peak in seconds, strictly increasing.
        ``series``: ``ArrayLike`` ``(peaks, 4)`` - the four speeds after each peak (``CircleSeries``).
        ``moments``: a number or ``ArrayLike`` ``(moments,)`` - times in seconds from the start of the file.

    Returns:
        ``CircleSpeeds`` ``(moments, 4)`` - the four speeds, in revolutions per minute, at each moment.
    """
    times, series = _series(times, series)
    moments = _moments(moments)
    latest = np.searchsorted(times, moments, side="right") - 1
    rows = np.vstack([np.asarray(DEFAULT_SPEEDS)[None, :], series])
    return rows[latest + 1]


def circle_angles(times: ArrayLike, series: ArrayLike, moments: float | ArrayLike) -> CircleAngles:
    """The angle of the four circles at each moment, in **turns** (clockwise positive): a float64 array
    ``(moments, 4)``, not wrapped to one turn.

    The running total of ``speed / 60`` over time from 0 to the moment: the speed is ``DEFAULT_SPEEDS`` until the first
    peak and the row of each peak from its time until the next, so the angle is continuous and its slope changes at each
    peak.

    Arrays:
        ``times``: ``ArrayLike`` ``(peaks,)`` - the time of each local peak in seconds, strictly increasing.
        ``series``: ``ArrayLike`` ``(peaks, 4)`` - the four speeds after each peak (``CircleSeries``).
        ``moments``: a number or ``ArrayLike`` ``(moments,)`` - times in seconds from the start of the file.

    Returns:
        ``CircleAngles`` ``(moments, 4)`` - the angle of each ring at each moment, in turns, clockwise positive, not
        wrapped.
    """
    times, series = _series(times, series)
    moments = _moments(moments)
    breakpoints = np.concatenate([[0.0], times])
    speeds = np.vstack([np.asarray(DEFAULT_SPEEDS)[None, :], series])  # the speed from each breakpoint until the next
    # the angle at each breakpoint
    turns = np.vstack([np.zeros((1, CIRCLES)), np.cumsum(speeds[:-1] * np.diff(breakpoints)[:, None] / 60.0, axis=0)])
    latest = np.searchsorted(breakpoints, moments, side="right") - 1
    return turns[latest] + speeds[latest] * (moments - breakpoints[latest])[:, None] / 60.0


@dataclass(frozen=True)
class RhythmData:
    """The angle of every circle at the middle of every frame: ``angles`` is ``(frames, 4)`` float64 turns, clockwise
    positive, not wrapped.

    Attributes:
        ``angles``: ``CircleAngles`` ``(frames, 4)`` - the angle of the notch of each ring at the middle of each frame,
            in turns, clockwise positive, not wrapped; the columns are the rings from the outer one (the current tempo)
            to the innermost (the rate of change of the local peak).
    """

    angles: CircleAngles

    @property
    def frame_count(self) -> int:
        """The number of frames: the length of axis 0 of ``angles``."""
        return int(self.angles.shape[0])


def _check_data(data: RhythmData) -> CircleAngles:
    """The angles of a ``RhythmData`` as a float64 ``(frames, 4)`` array; refused when they are not finite numbers in
    that shape.

    Returns:
        ``CircleAngles`` ``(frames, 4)`` - the angles of the data as float64.
    """
    angles = np.asarray(data.angles)
    if angles.ndim != 2 or angles.shape[1] != CIRCLES or angles.dtype.kind not in "iuf" or not np.isfinite(angles.astype(np.float64)).all():
        raise ValueError(f"The angles must be a (frames, {CIRCLES}) array of finite numbers.")
    return angles.astype(np.float64)


def rhythm_angles(peaks: LocalPeaks, frame_rate: float, frames: int) -> RhythmData:
    """The angles of the four circles at the middle of each of ``frames`` frames of ``frame_rate`` frames a second, from
    the local peaks of a file.

    The time of a peak is its sample over the file's sample rate and its tempo its rate in beats per minute (see
    :func:`peak_series`); the middle of frame ``f`` is at ``(f + 0.5) / frame_rate`` seconds, as for the position in the
    local peak of the other pictures.
    """
    if isinstance(frame_rate, (bool, np.bool_)) or not isinstance(frame_rate, numbers.Real) or not math.isfinite(frame_rate) or frame_rate <= 0:
        raise ValueError("The frame rate must be a positive number.")
    if isinstance(frames, (bool, np.bool_)) or not isinstance(frames, numbers.Integral) or frames < 0:
        raise ValueError("The number of frames must be a whole number of at least 0.")
    times = [peak.sample / peaks.file_rate for peak in peaks.peaks]
    series = peak_series(times, [peak.rate for peak in peaks.peaks])
    moments = (np.arange(int(frames)) + 0.5) / float(frame_rate)
    return RhythmData(circle_angles(times, series, moments))


def ring_colors_rows() -> tuple[Indices, Indices]:
    """The colormap table rows of the four rings and of their notches: ``rint(p x 255)`` and ``rint((1 - p) x 255)``
    with ``p = (k - 1) / 3`` for ring ``k`` (1 the outer): each ring has its own color from the start of the colormap
    (outer) to its end (innermost) and its notch the color at the opposite end.

    Returns:
        A tuple of two ``Indices`` ``(4,)`` into the 256 rows of the colormap's ``ColorTable``: the row of the color of
        each ring, and the row of the color of its notch.
    """
    position = np.arange(CIRCLES) / (CIRCLES - 1)
    return np.rint(position * (COLORMAP_STEPS - 1)).astype(np.intp), np.rint((1.0 - position) * (COLORMAP_STEPS - 1)).astype(np.intp)


@lru_cache(maxsize=4)
def _geometry(width: int, height: int) -> _Geometry:
    """What never changes between frames, for the pixels that any ring touches:
    ``(index, ring, coverage, distance, angle)``.

    The rings are centered in the picture; the outer radius is ``min(width, height) / 2 - MARGIN``, a ring is a quarter
    of it wide less a gap (``GAP`` on 600 x 400, scaled with the picture) on its inner side, ring 1 the outer one.
    ``index`` are the flat numbers of the pixels, ``ring`` (0 to 3) the ring of each, ``coverage`` how much of the pixel
    the ring covers (smooth edges half a pixel each side: ``clip(r_out - d + 0.5, 0, 1) x clip(d - r_in + 0.5, 0, 1)``),
    ``distance`` its distance from the center in pixels and ``angle`` its direction in turns clockwise from straight up.

    Returns:
        A tuple of five arrays, each ``(pixels,)`` for the pixels that a ring touches: ``PixelNumbers`` (the flat pixel
        number), ``Indices`` (the ring, 0 outer to 3 innermost), ``PixelWeights`` (how much of the pixel the ring
        covers, 0 to 1), ``CenterDistances`` (pixels) and ``PixelAngles`` (turns clockwise from straight up).
    """
    size = min(width, height)
    outer = size / 2 - MARGIN
    ring_width = outer / CIRCLES
    gap = GAP * size / REFERENCE_SIZE
    ys, xs = np.mgrid[0:height, 0:width]
    dx = xs + 0.5 - width / 2
    dy = ys + 0.5 - height / 2
    distance = np.hypot(dx, dy)
    angle = (np.arctan2(dx, -dy) / (2 * np.pi)) % 1.0
    coverage = np.zeros((CIRCLES,) + distance.shape)
    for k in range(CIRCLES):
        r_out = outer - k * ring_width
        r_in = outer - (k + 1) * ring_width + gap
        coverage[k] = np.clip(r_out - distance + 0.5, 0.0, 1.0) * np.clip(distance - r_in + 0.5, 0.0, 1.0)
    best = coverage.argmax(axis=0)
    strength = np.take_along_axis(coverage, best[None], axis=0)[0]
    index = np.flatnonzero(strength.ravel() > 0)
    return index, best.ravel()[index], strength.ravel()[index].astype(np.float32), distance.ravel()[index].astype(np.float32), angle.ravel()[index].astype(np.float32)


def _frame(angles: CircleAngles, background: Rgb, rings: ColorList, notches: ColorList, geometry: _Geometry, width: int, height: int) -> Pictures:
    """One picture, a ``uint8`` array ``(height, width, 3)``, from the 4 angles (turns) of the frame: the rings, each
    with its notch (an arc of ``NOTCH`` of the circle centered at its angle, edges half a pixel of arc length each
    side), over the background.

    Arrays:
        ``angles``: ``CircleAngles`` ``(4,)`` - the angle of the notch of each ring in this frame, in turns.
        ``background``: ``Rgb`` ``(3,)`` - the background color (the middle color of the colormap).
        ``rings``: ``ColorList`` ``(4, 3)`` - the color of each ring, outer first.
        ``notches``: ``ColorList`` ``(4, 3)`` - the color of the notch of each ring.

    Returns:
        ``Pictures`` ``(height, width, 3)`` - the picture of the frame.
    """
    index, ring, coverage, distance, angle = geometry
    theta = np.mod(angles, 1.0).astype(np.float32)[ring]
    delta = np.mod(angle - theta + 0.5, 1.0) - 0.5  # the signed distance in turns from the center of the notch
    in_notch = np.clip((NOTCH / 2 - np.abs(delta)) * (2 * np.pi) * distance + 0.5, 0.0, 1.0)[:, None]
    colour = rings[ring] + (notches[ring] - rings[ring]) * in_notch
    picture = np.empty((height * width, 3), dtype=np.float32)
    picture[:] = background
    picture[index] = background + (colour - background) * coverage[:, None]
    return np.rint(picture).astype(np.uint8).reshape(height, width, 3)


def write_rhythm_frames(data: RhythmData, colormap: str, directory: Path, width: int, height: int) -> None:
    """Save one PNG of ``width`` x ``height`` pixels per frame of ``data`` as ``frame_000000.png`` and up. Everything is
    checked before anything is written."""
    colormap = check_colormap(colormap)
    angles = _check_data(data)
    for size in (width, height):
        if isinstance(size, (bool, np.bool_)) or not isinstance(size, numbers.Integral) or size < 1:
            raise ValueError("The picture size must be two whole numbers of at least 1.")
    width, height = int(width), int(height)
    table = lookup_table(colormap)
    background = table[MIDDLE_COLOR_ROW].astype(np.float32)
    ring_rows, notch_rows = ring_colors_rows()
    rings, notches = table[ring_rows].astype(np.float32), table[notch_rows].astype(np.float32)
    geometry = _geometry(width, height)
    directory.mkdir(parents=True, exist_ok=True)

    def write(frame: int) -> None:
        picture = _frame(angles[frame], background, rings, notches, geometry, width, height)
        Image.fromarray(picture, "RGB").save(directory / f"frame_{frame:06d}.png", compress_level=1)

    with ThreadPoolExecutor(max_workers=SAVE_WORKERS) as pool:
        for future in [pool.submit(write, i) for i in range(angles.shape[0])]:
            future.result()  # raises the first error of a worker, if there was one
