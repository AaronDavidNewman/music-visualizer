"""The ``rhythm-circles`` kind of picture: how rhythmic a section of sound is, as six concentric notched circles that
rotate.

Each circle is a ring of one color with a **notch** (an arc of 1/8 of the circle) in a contrasting color, and it
rotates; the notch shows the rotation. The speeds come from two measurements of the sound. The **voted tempos**
(``tempo_votes``, feature 047) are found from the notes: every time a note begins (``note_onsets``: found from the rise of the note
strengths and placed on the rise of the waveform; feature 047, fourth round; the notes of a trill and above it make no starts, fifth
round), the time since each of the 2 starts before it is a note length, and the tempos (the 18 metronome markings from 76 to 144 beats
per minute) at which that length could be a half, quarter, eighth or sixteenth note, dotted or a triplet, are voted for, and again
with the note values of a beat divided in 3; the meter whose best tempo has more votes gives the **first** (raw) tempo (a tie keeps
the tempo before), and the **average** of the last 5 first tempos steadies it. The **local peaks** (``local_peaks``: the
periodic maxima of its energy, the beats) give the tempo of the latest peak, unchanged. There are three **layers**, each a
**level** and, inside it, the **rate of change** of that level (the circles of the tempo finder's current tempo, which
were here from feature 040 until feature 047, are gone). From the outer circle to the innermost:

1. **the average tempo**: the straight average of the first tempo (the one with the most votes) after the latest start and
   after the 4 starts before it, 5 in all (fewer at the beginning), in beats per minute (120 before the second start and
   with no vote): the circle makes as many revolutions per minute as the tempo has beats per minute, one for each beat,
   **clockwise** being positive;
2. **the rate of change of the average tempo**, from one start to the next, divided by the seconds between them (beats
   per minute per second, taken as revolutions per minute); positive (clockwise) when it speeds up, negative
   (counterclockwise) when it slows down;
3. **the raw tempo**: the first tempo as the votes have it, not averaged: the tempo with the most votes after the latest
   start, in beats per minute (120 where it has no votes);
4. **the rate of change of the raw tempo**, in the same way;
5. **the local peak**: the rate of the latest peak, in beats per minute (60 for the first peak and before it): the
   circle makes as many revolutions per minute as the peak has beats per minute;
6. **the rate of change of the local peak**: the rate of a peak less the rate of the previous peak, divided by the
   seconds between them.

Every speed is **constant between two events and changes at each event** (a note start for the first four circles, a
peak for the last two); the **angle** of a circle is the running total of its speed over time from the start of the file
(an integral, exact at the time of each event), so a notch never jumps when a speed changes. Before the first event the
speeds are those of the starting tempo of 120 (the voted tempos) and a peak rate of 60, and no change: ``DEFAULT_SPEEDS``.

The numbers are pure functions of the starts and the peaks (``peak_series``, ``circle_speeds``, ``circle_angles``,
``rhythm_angles``: small arrays, testable without audio); the picture (``write_rhythm_frames``) is drawn independently for
every frame from the angles.

This module knows nothing about the job or the page: the peaks, the note strengths and the two channels of the audio (for the
starts), the Vote limit setting, the frame rate and the picture size are passed in.

Order of operations:
    1. Take the times and the rates of the peaks - ``rhythm_angles()`` - ``PeakTimes`` ``(peaks,)`` (each peak's sample
       over the file's sample rate) and ``PeakRates`` ``(peaks,)`` (each peak's rate in beats per minute).
    2. Make the peak circles' series - ``peak_series()`` - ``CircleSeries`` ``(peaks, 2)``: the peak's rate and its rate
       of change (the difference from the previous peak over the seconds between them), in revolutions per minute.
    3. Find the starts of the notes - ``note_onsets.onset_starts()`` on the 60 ms analysis windows, not on the frames, so the
       starts do not depend on the frame rate, and on the ``RawSamples`` ``(samples,)`` of the two channels, which place each start
       on the waveform - ``StartTimes`` ``(starts,)``.
    4. Vote and make the vote circles' series - ``tempo_votes.leading_tempos()`` (``MeterTempos`` ``(starts, 2)``: the votes of
       both meters with the last 2 starts, ``MeterVotes`` ``(starts, 2, 18)``, and the meter and its leading tempo; only column 0,
       the raw tempo, is used),
       ``tempo_votes.average_tempos()`` (``AveragedTempos`` ``(starts,)``: the straight average of the last 5 raw tempos) and
       ``tempo_votes.vote_series()`` (``CircleSeries`` ``(starts, 4)``): the average tempo, its rate of change, the raw tempo,
       its rate of change.
    5. Choose the moments - ``rhythm_angles()`` - ``Moments`` ``(frames,)``: the middle of each frame,
       ``(f + 0.5) / frame_rate`` seconds.
    6. Turn the speeds into angles - ``circle_angles()`` (with ``circle_speeds()``'s step function) once for each group of
       circles (the four vote circles at the starts, the two peak circles at the peaks), joined side by side -
       ``CircleAngles`` ``(frames, 6)``: the running total of ``speed / 60`` from the start of the file, in turns, so a
       notch never jumps when a speed changes; returned in a ``RhythmData``.
    7. (Drawing, ``write_rhythm_frames()``) check the data - ``_check_data()`` - and make the colors of the rings and of
       their notches - ``ring_colors_rows()`` - ``Indices`` ``(6,)`` into the colormap: the ring ``k`` at position
       ``(k - 1) / 5``, its notch at the opposite position.
    8. Make what never changes between frames, once for the picture size - ``_geometry()`` - the pixels that a ring
       touches, their ring, coverage, distance and direction.
    9. Draw each frame on its own (a few threads) - ``_frame()`` - each ring with a notch of an eighth of the circle
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
    NoteStrengths,
    PeakRates,
    PeakTimes,
    Pictures,
    PixelAngles,
    PixelNumbers,
    PixelWeights,
    RawSamples,
    CenterDistances,
    Rgb,
)
from .colormaps import COLORMAP_STEPS, MIDDLE_COLOR_ROW, check_colormap, lookup_table
from .frame_saving import SAVE_WORKERS
from .local_peaks import DEFAULT_RATE, LocalPeaks
from .tempo_finder import START_TEMPO
from .note_onsets import onset_starts
from .tempo_votes import average_tempos, check_vote_limit, leading_tempos, vote_series

LAYERS = 3  # the average tempo, the raw (first voted) tempo and the local peak's own tempo: each a level and the rate of change of that level
CIRCLES = 2 * LAYERS  # outer to inner: the level and the rate of change of each layer
# revolutions per minute before the first start: the average and the raw tempo are the starting tempo of 120, with no change
VOTE_DEFAULTS = (START_TEMPO, 0.0, START_TEMPO, 0.0)
PEAK_DEFAULTS = (DEFAULT_RATE, 0.0)  # and before the first peak: the rate of 60, with no change
DEFAULT_SPEEDS = VOTE_DEFAULTS + PEAK_DEFAULTS
NOTCH = 1 / 8  # the arc of a notch, as a share of the circle
START_RESOLUTION = 0.04  # seconds: how well a start is known (the starts are placed on the waveform), so a length fits within 20 ms
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
    """The two series of the peaks: a float64 array ``(peaks, 2)`` in revolutions per minute, the local peak's circle
    (column 0) and the rate of change of its circle (column 1).

    ``times`` are the times of the peaks in seconds (strictly increasing) and ``tempos`` their rates in beats per minute
    (above 0). For peak ``i`` column 0 is **the peak's own rate** ``tempos[i]`` and column 1 its change:
    ``(x[i] - x[i - 1]) / (times[i] - times[i - 1])`` (0 for the first peak). The inputs are not changed.

    Arrays:
        ``times``: ``ArrayLike`` ``(peaks,)`` - the time of each local peak in seconds, strictly increasing
            (``PeakTimes``).
        ``tempos``: ``ArrayLike`` ``(peaks,)`` - the rate of each local peak in beats per minute, above 0
            (``PeakRates``).

    Returns:
        ``CircleSeries`` ``(peaks, 2)`` - the two speeds after each peak, in revolutions per minute: the peak's rate and
        its rate of change.
    """
    times = _times(times)
    try:
        tempos = np.asarray(tempos, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The tempos must be numbers.") from None
    if tempos.shape != times.shape or not np.isfinite(tempos).all() or (tempos <= 0).any():
        raise ValueError("The tempos must be one finite number above 0 for each peak.")
    series = np.zeros((times.shape[0], len(PEAK_DEFAULTS)))
    if not times.shape[0]:
        return series
    series[:, 0] = tempos
    series[1:, 1] = np.diff(tempos) / np.diff(times)
    return series


def _series(times: ArrayLike, series: ArrayLike, defaults: tuple[float, ...]) -> tuple[PeakTimes, CircleSeries]:
    """The times and the series as float64 arrays; refused when the series does not have one row of ``len(defaults)``
    finite numbers for each event.

    Arrays:
        ``times``: ``ArrayLike`` ``(events,)`` - the time of each event (a note start or a local peak) in seconds, strictly
            increasing.
        ``series``: ``ArrayLike`` ``(events, circles)`` - the speeds after each event (``CircleSeries``), as many columns as
            ``defaults``.

    Returns:
        A tuple of ``PeakTimes`` ``(events,)`` and ``CircleSeries`` ``(events, circles)``, both as float64.
    """
    times = _times(times)
    try:
        series = np.asarray(series, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The series must be numbers.") from None
    width = len(defaults)
    if series.shape != (times.shape[0], width) or not np.isfinite(series).all():
        raise ValueError(f"The series must be a ({times.shape[0]}, {width}) array of finite numbers, one row for each event.")
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


def circle_speeds(times: ArrayLike, series: ArrayLike, moments: float | ArrayLike, defaults: tuple[float, ...] = DEFAULT_SPEEDS) -> CircleSpeeds:
    """The speed of the circles of a group at each moment, in revolutions per minute: a float64 array ``(moments, circles)``,
    as many circles as ``defaults`` has numbers (6 for ``DEFAULT_SPEEDS``, 4 for ``VOTE_DEFAULTS``, 2 for ``PEAK_DEFAULTS``).

    A step function: the row of ``series`` of the latest event (a note start or a peak) at or before the moment, ``defaults``
    before the first event and with no events.

    Arrays:
        ``times``: ``ArrayLike`` ``(events,)`` - the time of each event in seconds, strictly increasing.
        ``series``: ``ArrayLike`` ``(events, circles)`` - the speeds after each event (``CircleSeries``).
        ``moments``: a number or ``ArrayLike`` ``(moments,)`` - times in seconds from the start of the file.

    Returns:
        ``CircleSpeeds`` ``(moments, circles)`` - the speeds, in revolutions per minute, at each moment.
    """
    times, series = _series(times, series, defaults)
    moments = _moments(moments)
    latest = np.searchsorted(times, moments, side="right") - 1
    rows = np.vstack([np.asarray(defaults, dtype=np.float64)[None, :], series])
    return rows[latest + 1]


def circle_angles(times: ArrayLike, series: ArrayLike, moments: float | ArrayLike, defaults: tuple[float, ...] = DEFAULT_SPEEDS) -> CircleAngles:
    """The angle of the circles of a group at each moment, in **turns** (clockwise positive): a float64 array
    ``(moments, circles)``, not wrapped to one turn; as many circles as ``defaults`` has numbers.

    The running total of ``speed / 60`` over time from 0 to the moment: the speed is ``defaults`` until the first event and
    the row of each event from its time until the next, so the angle is continuous and its slope changes at each event.

    Arrays:
        ``times``: ``ArrayLike`` ``(events,)`` - the time of each event in seconds, strictly increasing.
        ``series``: ``ArrayLike`` ``(events, circles)`` - the speeds after each event (``CircleSeries``).
        ``moments``: a number or ``ArrayLike`` ``(moments,)`` - times in seconds from the start of the file.

    Returns:
        ``CircleAngles`` ``(moments, circles)`` - the angle of each ring at each moment, in turns, clockwise positive, not
        wrapped.
    """
    times, series = _series(times, series, defaults)
    moments = _moments(moments)
    breakpoints = np.concatenate([[0.0], times])
    speeds = np.vstack([np.asarray(defaults, dtype=np.float64)[None, :], series])  # the speed from each breakpoint until the next
    # the angle at each breakpoint
    turns = np.vstack([np.zeros((1, len(defaults))), np.cumsum(speeds[:-1] * np.diff(breakpoints)[:, None] / 60.0, axis=0)])
    latest = np.searchsorted(breakpoints, moments, side="right") - 1
    return turns[latest] + speeds[latest] * (moments - breakpoints[latest])[:, None] / 60.0


@dataclass(frozen=True)
class RhythmData:
    """The angle of every circle at the middle of every frame: ``angles`` is ``(frames, 6)`` float64 turns, clockwise
    positive, not wrapped.

    Attributes:
        ``angles``: ``CircleAngles`` ``(frames, 6)`` - the angle of the notch of each ring at the middle of each frame,
            in turns, clockwise positive, not wrapped; the columns are the rings from the outer one (the average tempo)
            to the innermost (the rate of change of the local peak).
    """

    angles: CircleAngles

    @property
    def frame_count(self) -> int:
        """The number of frames: the length of axis 0 of ``angles``."""
        return int(self.angles.shape[0])


def _check_data(data: RhythmData) -> CircleAngles:
    """The angles of a ``RhythmData`` as a float64 ``(frames, 6)`` array; refused when they are not finite numbers in
    that shape.

    Returns:
        ``CircleAngles`` ``(frames, 6)`` - the angles of the data as float64.
    """
    angles = np.asarray(data.angles)
    if angles.ndim != 2 or angles.shape[1] != CIRCLES or angles.dtype.kind not in "iuf" or not np.isfinite(angles.astype(np.float64)).all():
        raise ValueError(f"The angles must be a (frames, {CIRCLES}) array of finite numbers.")
    return angles.astype(np.float64)


def rhythm_angles(
    peaks: LocalPeaks, frame_rate: float, frames: int, windows: NoteStrengths, left: RawSamples, right: RawSamples, vote_limit: int
) -> RhythmData:
    """The angles of the six circles at the middle of each of ``frames`` frames of ``frame_rate`` frames a second, from the
    local peaks and the note strengths of a file.

    The time of a peak is its sample over the file's sample rate and its tempo its rate in beats per minute (see
    :func:`peak_series`); the middle of frame ``f`` is at ``(f + 0.5) / frame_rate`` seconds, as for the position in the
    local peak of the other pictures. The starts of the notes are voted on (``vote_limit`` the Vote limit); they are found
    from the rise of the note strengths in the 60 ms analysis windows (``windows``, one row every ``BUFFER_INTERVAL_MS``), not in the frames,
    and placed on the waveform of the two channels (``left`` and ``right``, at the file's sample rate, ``peaks.file_rate``), and are
    known to :data:`START_RESOLUTION`, 40 ms (``note_onsets``; the notes of a trill and above it make none); the votes are those of
    ``tempo_votes.leading_tempos`` (the last 2 starts, a beat divided in 2 or in 3, a tie keeps the tempo), so the voted tempos do not depend on the frame rate (it only decides at which
    moments the finished tempos are sampled into angles); the average of the last 5 first tempos and its change turn the first two
    circles, the raw first tempo and its change the next two, the peaks the last two. The Extra notes setting plays no part.

    Arrays:
        ``windows``: ``ArrayLike`` ``(windows, 88)`` - the strength of each note in each 60 ms analysis window
            (``NoteStrengths``, ``AnalysisResult.frames``); any number of rows, not tied to the frames.
        ``left``, ``right``: ``RawSamples`` ``(samples,)`` - the two channels of the file as read, of the same length; the starts are
            placed on their waveform.

    Returns:
        ``RhythmData`` - its ``angles`` ``CircleAngles`` ``(frames, 6)``.
    """
    if isinstance(frame_rate, (bool, np.bool_)) or not isinstance(frame_rate, numbers.Real) or not math.isfinite(frame_rate) or frame_rate <= 0:
        raise ValueError("The frame rate must be a positive number.")
    if isinstance(frames, (bool, np.bool_)) or not isinstance(frames, numbers.Integral) or frames < 0:
        raise ValueError("The number of frames must be a whole number of at least 0.")
    limit = check_vote_limit(vote_limit)
    array = np.asarray(windows)
    if array.ndim != 2:
        raise ValueError("The note strengths must have one row for each analysis window and a column for each of the 88 notes.")
    moments = (np.arange(int(frames)) + 0.5) / float(frame_rate)
    peak_times = [peak.sample / peaks.file_rate for peak in peaks.peaks]
    peak_rows = peak_series(peak_times, [peak.rate for peak in peaks.peaks])
    starts = onset_starts(array, left, right, peaks.file_rate)  # the rows of ``windows`` are 60 ms apart
    raw = leading_tempos(starts, START_RESOLUTION, limit)[:, 0]  # the first tempo after each start (the meter in column 1 is not drawn)
    vote_rows = vote_series(starts, np.column_stack([average_tempos(raw), raw]))  # the average first, the raw tempo inside it
    vote_angles = circle_angles(starts, vote_rows, moments, VOTE_DEFAULTS)
    peak_angles = circle_angles(peak_times, peak_rows, moments, PEAK_DEFAULTS)
    return RhythmData(np.hstack([vote_angles, peak_angles]))


def ring_colors_rows() -> tuple[Indices, Indices]:
    """The colormap table rows of the six rings and of their notches: ``rint(p x 255)`` and ``rint((1 - p) x 255)``
    with ``p = (k - 1) / 5`` for ring ``k`` (1 the outer): each ring has its own color from the start of the colormap
    (outer) to its end (innermost) and its notch the color at the opposite end.

    Returns:
        A tuple of two ``Indices`` ``(6,)`` into the 256 rows of the colormap's ``ColorTable``: the row of the color of
        each ring, and the row of the color of its notch.
    """
    position = np.arange(CIRCLES) / (CIRCLES - 1)
    return np.rint(position * (COLORMAP_STEPS - 1)).astype(np.intp), np.rint((1.0 - position) * (COLORMAP_STEPS - 1)).astype(np.intp)


@lru_cache(maxsize=4)
def _geometry(width: int, height: int) -> _Geometry:
    """What never changes between frames, for the pixels that any ring touches:
    ``(index, ring, coverage, distance, angle)``.

    The rings are centered in the picture; the outer radius is ``min(width, height) / 2 - MARGIN``, a ring is a sixth
    of it wide less a gap (``GAP`` on 600 x 400, scaled with the picture) on its inner side, ring 1 the outer one.
    ``index`` are the flat numbers of the pixels, ``ring`` (0 to 5) the ring of each, ``coverage`` how much of the pixel
    the ring covers (smooth edges half a pixel each side: ``clip(r_out - d + 0.5, 0, 1) x clip(d - r_in + 0.5, 0, 1)``),
    ``distance`` its distance from the center in pixels and ``angle`` its direction in turns clockwise from straight up.

    Returns:
        A tuple of five arrays, each ``(pixels,)`` for the pixels that a ring touches: ``PixelNumbers`` (the flat pixel
        number), ``Indices`` (the ring, 0 outer to 5 innermost), ``PixelWeights`` (how much of the pixel the ring
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
    """One picture, a ``uint8`` array ``(height, width, 3)``, from the 6 angles (turns) of the frame: the rings, each
    with its notch (an arc of ``NOTCH`` of the circle centered at its angle, edges half a pixel of arc length each
    side), over the background.

    Arrays:
        ``angles``: ``CircleAngles`` ``(6,)`` - the angle of the notch of each ring in this frame, in turns.
        ``background``: ``Rgb`` ``(3,)`` - the background color (the middle color of the colormap).
        ``rings``: ``ColorList`` ``(6, 3)`` - the color of each ring, outer first.
        ``notches``: ``ColorList`` ``(6, 3)`` - the color of the notch of each ring.

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
