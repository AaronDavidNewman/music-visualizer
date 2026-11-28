"""The ``note_onsets``: when the notes of a file begin, for the tempo voting of Rhythm Circles (feature 047, fourth round).

The tempos are voted on the time between the starts of notes, so a start that is missing or found twice, or found a few hundredths of a second
late, spoils a vote. The first three rounds took a start from the held loudest notes (``held_notes.hold_loudest``), which finds a start
3 to 5 times too often (the energy of a new note leaks into the notes next to it for about 0.4 s, and as a note dies away the notes
that were below it rise into the selection) and only to the 60 ms analysis window. This module finds the starts from the **rise** of
the energy instead, and then places each one on the waveform.

* **The rise.** In each 60 ms analysis window, each of the 84 notes rises by how much its strength is above the larger of its strength in the
  2 windows before (never below 0); the rises of the notes are added (:func:`onset_rises`). A new note, or a chord, makes a
  large sum for one window or two; a note that is sustained or dies away makes none.
* **The peaks of the rise.** A window is a start when its rise is the largest within 2 windows either side (:data:`NEIGHBOURS`) and at
  least 20 % (:data:`RELATIVE_RISE`) of the largest rise within 33 windows (2 s) either side (:data:`LOCAL_WINDOWS`): so a quiet passage
  keeps its own starts next to a loud one, and the small rises of a ringing note are not starts. Of two starts closer than 2 windows
  (:data:`MIN_GAP_WINDOWS`, 120 ms) the one with the larger rise is kept (:func:`pick_onsets`). A start is first known as the time of
  the middle of its window.
* **The waveform.** The window is 93 ms long and the step 60 ms, so that time is only good to a window and is systematically early. Each start
  is moved to the moment, from 0.10 s before it to 0.05 s after it (:data:`BEFORE`, :data:`AFTER`), at which the root-mean-square level of the mix of the two
  channels (in frames of 512 samples every 128, :data:`FRAME`, :data:`HOP`) rises most (:func:`refine_starts`); a start whose
  refined time is within 30 ms of the one before (:data:`MERGE`) is the same start. A start with no rise on the waveform in that
  time stays where it is.

* **The trills** (fifth round). A trill, a flurry of very short notes a semitone or two apart, is heard as out of time: within a trill
  found by ``trills.find_trills`` the notes from one semitone below the trill's lowest note upward are left out of the rise, so the
  trill and its overtones make no starts while the instruments below it still do; with nothing below it, there is no start. A start
  inside a trill is still placed on the whole waveform, so it can land on a louder trill note near it.

The Extra notes setting does not take part: the starts do not come from a selection of the loudest notes. The held notes of the other pictures are unchanged.

Order of operations:
    1. Find the trills - ``trills.find_trills()`` (called by ``onset_starts()``) - ``TrillSpans`` ``(spans, 3)``: the first and last
       60 ms window and the lowest note of each trill, from the ``RawSamples`` ``(samples,)`` of the two channels.
    2. Measure the rise of each window - ``onset_rises()`` - ``OnsetRises`` ``(windows,)``: the sum over the 84 notes of how much the
       strength of each rose over its larger strength in the 2 windows before, from ``NoteStrengths`` ``(windows, 88)``, without the
       notes of the trills.
    3. Pick the peaks of the rise - ``pick_onsets()`` - ``StartTimes`` ``(starts,)``: the seconds of the middle of each window that is a
       start, strictly increasing.
    4. Place the starts on the waveform - ``refine_starts()`` (called by ``onset_starts()``, which makes steps 1 to 3 first; its
       ``_waveform_rise()`` makes the ``WaveformRises`` ``(frames,)`` around one start from the ``RawSamples`` ``(samples,)`` of the two
       channels) - ``StartTimes`` ``(starts,)``: the seconds of the moment of the largest rise of the level of the waveform near each
       start, the starts that land on the same moment merged.
"""

import math
import numbers

import numpy as np

from .array_types import ArrayLike, NoteStrengths, OnsetRises, RawSamples, StartTimes, TrillSpans, WaveformRises
from .buffer_interval import BUFFER_INTERVAL_MS
from .trills import TRILL_MARGIN, find_trills

NOTE_COLUMNS = 84  # the first columns of the note strengths that are notes (the rest are not)
BACK_WINDOWS = 2  # a note rises over the larger of its strength in this many windows before
NEIGHBOURS = 2  # a start has the largest rise within this many windows either side
LOCAL_WINDOWS = 33  # and at least RELATIVE_RISE of the largest rise within this many windows either side (2 s of 60 ms windows)
RELATIVE_RISE = 0.2  # the share of the largest rise nearby that a start's rise must be
MIN_GAP_WINDOWS = 2  # two starts closer than this many windows (120 ms) are one: the larger rise is kept
FRAME = 512  # the samples of one frame of the waveform's level
HOP = 128  # the samples from one frame of the waveform's level to the next
BEFORE = 0.10  # seconds before the time of a window that the waveform is searched for the start
AFTER = 0.05  # and after it
MERGE = 0.03  # seconds: a refined start this close to the one before it is the same start


def _check_window_values(values: ArrayLike) -> NoteStrengths:
    """The note strengths as a float64 array ``(windows, columns)`` of at least 84 columns; anything else is refused.

    Arrays:
        ``values``: ``ArrayLike`` ``(windows, columns)`` - the strength of each note in each analysis window.

    Returns:
        ``NoteStrengths`` ``(windows, columns)`` - the same values as float64.
    """
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The note strengths must be numbers.") from None
    if array.ndim != 2 or array.shape[1] < NOTE_COLUMNS:
        raise ValueError(f"The note strengths must be a (windows, 88) array: at least {NOTE_COLUMNS} columns.")
    if not np.isfinite(array).all() or (array < 0).any():
        raise ValueError("The note strengths must be finite numbers of 0 or more.")
    return array


def _check_rate(value: float, what: str) -> float:
    """A positive finite number as a float; anything else is refused with a message that names ``what``."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Real) or not np.isfinite(value) or value <= 0:
        raise ValueError(f"The {what} must be a positive number.")
    return float(value)


def _check_spans(spans: ArrayLike) -> TrillSpans:
    """The trills as an integer array ``(spans, 3)`` (first window, last window, lowest note); anything else is refused.

    Arrays:
        ``spans``: ``ArrayLike`` ``(spans, 3)`` - the trills (``TrillSpans``): whole numbers, the first window not after the last.

    Returns:
        ``TrillSpans`` ``(spans, 3)`` - the same spans as int64.
    """
    array = np.asarray(spans)
    if array.size == 0:
        return np.zeros((0, 3), dtype=np.int64)
    if array.ndim != 2 or array.shape[1] != 3 or array.dtype.kind not in "iu" or (array[:, 0] > array[:, 1]).any() or (array[:, :2] < 0).any():
        raise ValueError("The trills must be a (spans, 3) array of whole numbers: the first window, the last window and the lowest note.")
    return array.astype(np.int64)


def onset_rises(values: ArrayLike, spans: ArrayLike = ()) -> OnsetRises:
    """How much the notes rise in each analysis window: a float64 array ``(windows,)``.

    For each of the first 84 notes, the rise in a window is how much its strength is above the larger of its strength in the
    :data:`BACK_WINDOWS` windows before (the windows before the first are 0, so everything in the first window is a rise), never
    below 0; the rise of a window is the sum of the 84 rises. Within each trill of ``spans`` (from its first to its last window) the
    notes from ``TRILL_MARGIN`` semitone below the trill's lowest note upward are left out of the sum, so a trill and its overtones
    make no rise (fifth round of feature 047). The inputs are not changed.

    Arrays:
        ``values``: ``ArrayLike`` ``(windows, columns)`` - the strength of each note in each 60 ms analysis window (``NoteStrengths``),
            88 columns of which the first 84 are the notes; finite and not negative.
        ``spans``: ``ArrayLike`` ``(spans, 3)`` - the trills (``TrillSpans``): first window, last window, analysis column of the lowest
            note; none by default.

    Returns:
        ``OnsetRises`` ``(windows,)`` - the summed rise of the notes in each window, 0 or more.
    """
    notes = _check_window_values(values)[:, :NOTE_COLUMNS]
    trills = _check_spans(spans)
    before = np.zeros_like(notes)
    for back in range(1, BACK_WINDOWS + 1):
        shifted = np.vstack([np.zeros((back, NOTE_COLUMNS)), notes[:-back]])[: notes.shape[0]]
        before = np.maximum(before, shifted)
    rises = np.maximum(notes - before, 0.0)
    for first, last, lowest in trills:
        rises[first : last + 1, max(int(lowest) - TRILL_MARGIN, 0) :] = 0.0
    return rises.sum(axis=1)


def _largest_within(rises: OnsetRises, reach: int) -> OnsetRises:
    """The largest rise within ``reach`` windows either side of each window (the window itself included).

    Arrays:
        ``rises``: ``OnsetRises`` ``(windows,)`` - the summed rise of each window.

    Returns:
        ``OnsetRises`` ``(windows,)`` - for each window, the largest of ``rises[w - reach]`` to ``rises[w + reach]`` that exist.
    """
    padded = np.pad(rises, reach, constant_values=0.0)
    return np.lib.stride_tricks.sliding_window_view(padded, 2 * reach + 1).max(axis=1)


def pick_onsets(rises: ArrayLike) -> StartTimes:
    """The windows that are starts, as the seconds of the middle of each: a float64 array ``(starts,)``.

    A window is a start when its rise is above 0 and the largest within :data:`NEIGHBOURS` windows either side and at least
    :data:`RELATIVE_RISE` of the largest within :data:`LOCAL_WINDOWS` either side; of two starts less than :data:`MIN_GAP_WINDOWS` windows
    apart the one with the larger rise is kept (the earlier when they are equal). The time of a window is
    ``(window + 0.5) / windows a second``, the windows being ``BUFFER_INTERVAL_MS`` apart. The input is not changed.

    Arrays:
        ``rises``: ``ArrayLike`` ``(windows,)`` - the summed rise of each analysis window (``OnsetRises``), finite and not negative.

    Returns:
        ``StartTimes`` ``(starts,)`` - the seconds of the middle of each window that is a start, strictly increasing.
    """
    try:
        array = np.asarray(rises, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The rises must be numbers.") from None
    if array.ndim != 1 or not np.isfinite(array).all() or (array < 0).any():
        raise ValueError("The rises must be a 1-D array of finite numbers of 0 or more.")
    if not array.shape[0]:
        return np.zeros(0)
    peak = (array > 0) & (array >= _largest_within(array, NEIGHBOURS))
    strong = array >= RELATIVE_RISE * _largest_within(array, LOCAL_WINDOWS)
    kept: list[int] = []
    for window in np.flatnonzero(peak & strong):  # a start can replace the one before it, so this is a loop (over the starts only)
        if kept and window - kept[-1] < MIN_GAP_WINDOWS:
            if array[window] > array[kept[-1]]:
                kept[-1] = int(window)
            continue
        kept.append(int(window))
    return (np.asarray(kept, dtype=np.float64) + 0.5) * BUFFER_INTERVAL_MS / 1000


def _waveform_rise(left: RawSamples, right: RawSamples, sample_rate: float, start: float) -> tuple[float, WaveformRises] | None:
    """The rise of the level of the waveform in the frames whose middle is from :data:`BEFORE` before ``start`` to :data:`AFTER` after it.

    The level of a frame is the root-mean-square of the mix of the two channels, ``(left + right) / 2``, over :data:`FRAME` samples;
    frame ``k`` begins at sample ``k * HOP``, its middle is at ``(k * HOP + FRAME / 2) / sample_rate`` seconds, and its rise is its level
    over the level of the frame before, never below 0 (0 for frame 0).

    Arrays:
        ``left``, ``right``: ``RawSamples`` ``(samples,)`` - the two channels as read from the file.

    Returns:
        ``None`` when no frame lies in that time, else the time of the middle of the first frame and ``WaveformRises`` ``(frames,)``,
        the rise of each frame from there on, 0 or more.
    """
    frames_in_file = (left.shape[0] - FRAME) // HOP  # the frames that fit in the file: k from 0 to frames_in_file - 1
    first = max(math.ceil(((start - BEFORE) * sample_rate - FRAME / 2) / HOP), 0)
    stop = min(math.ceil(((start + AFTER) * sample_rate - FRAME / 2) / HOP), frames_in_file)  # one past the last frame
    if stop <= first:
        return None
    before = max(first - 1, 0)  # the level of the frame before the first is needed for its rise
    begin, end = before * HOP, (stop - 1) * HOP + FRAME
    mix = (left[begin:end].astype(np.float64) + right[begin:end].astype(np.float64)) / 2
    frames = np.lib.stride_tricks.sliding_window_view(mix, FRAME)[::HOP]  # (stop - before, FRAME)
    levels = np.sqrt((frames**2).mean(axis=1))
    rises = np.maximum(np.diff(levels, prepend=levels[0]), 0.0)[first - before :]
    return (first * HOP + FRAME / 2) / sample_rate, rises


def refine_starts(starts: ArrayLike, left: ArrayLike, right: ArrayLike, sample_rate: float) -> StartTimes:
    """Move each start to the moment of the largest rise of the level of the waveform near it: a float64 array ``(starts,)``.

    For each start the frames of the waveform's level (:func:`_waveform_rise`) that are from :data:`BEFORE` before it to :data:`AFTER`
    after it are searched; the start becomes the time of the middle of the frame with the largest rise (the first of equal ones). A start with no rise in
    that time (silence, or a constant level) stays where it is. A start that is not more than :data:`MERGE` after the one kept before it
    is the same start and is dropped, so the times are strictly increasing. The whole mix is looked at, also inside a trill (placing a
    start there on the waveform below the trill's notes was tried in the fifth round and measured worse on the sample music). The inputs
    are not changed.

    Arrays:
        ``starts``: ``ArrayLike`` ``(starts,)`` - the time of each start in seconds, strictly increasing (``StartTimes``).
        ``left``, ``right``: ``ArrayLike`` ``(samples,)`` - the two channels of the file, as read (``RawSamples``), of the same length.

    Returns:
        ``StartTimes`` ``(starts,)`` - the refined times in seconds, strictly increasing, no more than the starts given.
    """
    rate = _check_rate(sample_rate, "sample rate")
    try:
        times = np.asarray(starts, dtype=np.float64)
        channels = (np.asarray(left), np.asarray(right))
    except (TypeError, ValueError):
        raise ValueError("The starts and the samples must be numbers.") from None
    if times.ndim != 1 or not np.isfinite(times).all() or (times.size > 1 and (np.diff(times) <= 0).any()):
        raise ValueError("The starts must be a 1-D array of finite numbers in strictly increasing order.")
    if any(c.ndim != 1 or c.dtype.kind not in "iuf" for c in channels) or channels[0].shape != channels[1].shape:
        raise ValueError("The two channels must be 1-D arrays of numbers of the same length.")
    kept: list[float] = []
    for start in times:
        found = _waveform_rise(channels[0], channels[1], rate, float(start))
        moment = float(start)
        if found is not None and found[1].max() > 0:
            first_time, rises = found
            moment = first_time + int(np.argmax(rises)) * HOP / rate
        if not kept or moment - kept[-1] > MERGE:
            kept.append(moment)
    return np.asarray(kept, dtype=np.float64)


def onset_starts(values: ArrayLike, left: ArrayLike, right: ArrayLike, sample_rate: float) -> StartTimes:
    """When the notes of a file begin: a float64 array ``(starts,)`` of seconds, strictly increasing.

    The trills are found on the waveform (``trills.find_trills``); the peaks of the rise of the note strengths of the 60 ms windows,
    without the notes of the trills (:func:`onset_rises`, :func:`pick_onsets`), are each moved to the rise of the waveform near it
    (:func:`refine_starts`). The inputs are not changed.

    Arrays:
        ``values``: ``ArrayLike`` ``(windows, 88)`` - the strength of each note in each 60 ms analysis window (``NoteStrengths``).
        ``left``, ``right``: ``ArrayLike`` ``(samples,)`` - the two channels of the file as read (``RawSamples``).

    Returns:
        ``StartTimes`` ``(starts,)`` - the seconds at which a note begins, strictly increasing.
    """
    windows = _check_window_values(values)
    spans = find_trills(left, right, sample_rate, windows.shape[0])
    return refine_starts(pick_onsets(onset_rises(windows, spans)), left, right, sample_rate)
