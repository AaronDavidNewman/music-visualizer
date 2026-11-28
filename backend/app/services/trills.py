"""The ``trills``: where a trill is playing, so that its notes do not take part in the tempo voting of Rhythm Circles (feature 047, fifth round).

A trill is a flurry of very short notes: two neighbouring notes, one or two semitones apart, played one after the other many times
a second. A listener hears it as a flurry in pitch but out of time, and follows the beat around it. Its notes are too short for the
60 ms analysis windows (each about 93 ms long: the two notes blur into one sound that only flickers), so they are found on the waveform
itself, every 256 samples (about 6 ms at 44.1 kHz).

* **The levels.** The mix of the two channels, ``(left + right) / 2``, is cut into frames of :data:`FRAME` samples every :data:`HOP`
  (a Hann window); the energy of each frame in the band of each semitone from C3 to G#7 (the analysis columns :data:`FIRST_COLUMN` to
  ``FIRST_COLUMN + SEMITONES - 1``, a band reaching half a semitone either side of the note; the nearest frequency of the transform when
  the band holds none) is summed and taken as ``log10(1 + energy)`` (:func:`semitone_levels`).
* **The score.** Around the middle of each 60 ms analysis window, :data:`SPAN` seconds of the levels are looked at. For each note
  its level less its mean over the span is its **flicker**; the share of the flicker's power that is at 6 to 20 times a second
  (:data:`FLICKER_BAND`) is how **fast** it flickers. Two notes 1 or 2 semitones apart that take turns flicker against each other: the
  correlation of their flickers is negative. A pair scores ``max(-correlation, 0) x the smaller of their two fast shares``, but only
  when both notes are sounding (their mean level is above the 60th percentile of the mean levels of all the semitones,
  :data:`SOUNDING_PERCENTILE`). The score of the window is the best pair's, from 0 to 1, together with the lower note of that pair
  (:func:`trill_scores`).
* **The spans.** A window whose score is at least :data:`TRILL_SCORE` (0.2) is in a trill; windows in a trill with at most
  :data:`MAX_GAP_WINDOWS` windows between them are one span, and a span of fewer than :data:`MIN_WINDOWS` windows is dropped. A span
  keeps its first and last window, each moved out by :data:`EDGE_WINDOWS` (4 windows, 0.24 s: a score looks half a second around its
  window, so the score of a trill rises about a quarter of a second after it begins and falls as long before it ends), and the lowest of the
  lower notes of its windows in a trill (:func:`trill_spans`).

The spans are used by ``note_onsets.onset_rises``: within a span the notes from one semitone below the trill's lowest note
(:data:`TRILL_MARGIN`) upward do not count, so the trill and its overtones make no starts, while the lower instruments still do. The
values were chosen on the sample files of ``backend/audio`` (``research.md``, Decision 18).

Order of operations:
    1. Measure the levels of the semitones - ``semitone_levels()`` - ``SemitoneLevels`` ``(levels, 57)``: ``log10(1 + energy)`` of each
       semitone from C3 to G#7 in each frame of 2048 samples every 256, from the ``RawSamples`` ``(samples,)`` of the two channels.
    2. Score each 60 ms analysis window - ``trill_scores()`` - ``TrillScores`` ``(windows,)``: how much two neighbouring notes take
       turns quickly around the middle of the window, and ``TrillNotes`` ``(windows,)``: the analysis column of the lower note of the
       best pair.
    3. Join the windows in a trill into spans - ``trill_spans()`` - ``TrillSpans`` ``(spans, 3)``: the first window, the last window and
       the analysis column of the lowest note of each trill. ``find_trills()`` makes the three steps.
"""

import math
import numbers

import numpy as np

from .array_types import ArrayLike, RawSamples, SemitoneBands, SemitoneLevels, TrillNotes, TrillScores, TrillSpans
from .buffer_interval import BUFFER_INTERVAL_MS
from .note_analysis import BASE_FREQUENCY

FRAME = 2048  # samples in one frame of the levels
HOP = 256  # samples from one frame of the levels to the next
FIRST_COLUMN = 15  # the analysis column (0 = A1, 55 Hz) of the lowest semitone looked at: C3
SEMITONES = 57  # C3 to G#7
SPAN = 0.5  # seconds of the levels looked at around the middle of each analysis window
FLICKER_BAND = (6.0, 20.0)  # times a second: how fast the flicker of a trill's notes is
SOUNDING_PERCENTILE = 60  # a note of a pair must be louder on average than this percentile of the semitones
STEPS = (1, 2)  # semitones between the two notes of a trill
TRILL_SCORE = 0.2  # the score from which a window is in a trill
MAX_GAP_WINDOWS = 3  # windows in a trill with at most this many windows between them are one span
MIN_WINDOWS = 3  # a span of fewer windows is not a trill
TRILL_MARGIN = 1  # semitones below the lowest note of a trill that are ignored with it
EDGE_WINDOWS = 4  # windows (0.24 s) a span is widened by at each end: the score looks SPAN seconds around a window, so a span begins about half of it late and ends as early


def _check_rate(sample_rate: float) -> float:
    """The sample rate as a float: a positive finite number, else refused."""
    if isinstance(sample_rate, (bool, np.bool_)) or not isinstance(sample_rate, numbers.Real) or not math.isfinite(sample_rate) or sample_rate <= 0:
        raise ValueError("The sample rate must be a positive number.")
    return float(sample_rate)


def _check_channels(left: ArrayLike, right: ArrayLike, sample_rate: float) -> tuple[RawSamples, RawSamples, float]:
    """The two channels and the sample rate, checked: 1-D arrays of numbers of the same length and a positive finite rate.

    Arrays:
        ``left``, ``right``: ``ArrayLike`` ``(samples,)`` - the two channels of the file as read.

    Returns:
        The two ``RawSamples`` ``(samples,)`` as they were given (as arrays) and the rate as a float.
    """
    rate = _check_rate(sample_rate)
    try:
        channels = (np.asarray(left), np.asarray(right))
    except (TypeError, ValueError):
        raise ValueError("The samples must be numbers.") from None
    if any(c.ndim != 1 or c.dtype.kind not in "iuf" for c in channels) or channels[0].shape != channels[1].shape:
        raise ValueError("The two channels must be 1-D arrays of numbers of the same length.")
    return channels[0], channels[1], rate


def _band_matrix(sample_rate: float) -> SemitoneBands:
    """Which frequencies of the transform of a frame belong to which semitone: a float64 array ``(1025, 57)`` of 0 and 1.

    The band of a semitone of frequency ``f`` reaches from ``f / 2^(1/24)`` (included) to ``f x 2^(1/24)`` (excluded); a band that holds
    no frequency of the transform takes the nearest one.

    Returns:
        ``SemitoneBands`` ``(1025, 57)`` - 1 where the frequency (row) is in the band of the semitone (column), else 0.
    """
    frequencies = np.fft.rfftfreq(FRAME, 1.0 / sample_rate)
    bands = np.zeros((frequencies.shape[0], SEMITONES))
    for semitone in range(SEMITONES):
        middle = BASE_FREQUENCY * 2.0 ** ((FIRST_COLUMN + semitone) / 12)
        inside = (frequencies >= middle * 2.0 ** (-1 / 24)) & (frequencies < middle * 2.0 ** (1 / 24))
        if not inside.any():
            inside = np.abs(frequencies - middle) == np.abs(frequencies - middle).min()
        bands[inside, semitone] = 1.0
    return bands


def semitone_levels(left: ArrayLike, right: ArrayLike, sample_rate: float) -> SemitoneLevels:
    """The level of each semitone from C3 to G#7 in each frame of the waveform: a float64 array ``(levels, 57)``.

    Frame ``k`` is the :data:`FRAME` samples of the mix ``(left + right) / 2`` from sample ``k x HOP``, times a Hann window; its level in a
    semitone is ``log10(1 + the energy of the transform in the band of the semitone)``. Only the frames that fit in the file are made (none
    when it is shorter than a frame). The file is taken a piece at a time, so the whole file is never held as a transform. The inputs are
    not changed.

    Arrays:
        ``left``, ``right``: ``ArrayLike`` ``(samples,)`` - the two channels of the file as read (``RawSamples``), of the same length.

    Returns:
        ``SemitoneLevels`` ``(levels, 57)`` - the level of each semitone (columns, C3 upward) in each frame (rows), 0 or more.
    """
    left, right, rate = _check_channels(left, right, sample_rate)
    count = max((left.shape[0] - FRAME) // HOP + 1, 0)
    levels = np.zeros((count, SEMITONES))
    if not count:
        return levels
    bands = _band_matrix(rate)
    window = np.hanning(FRAME)
    piece = 1024  # frames transformed at a time
    for first in range(0, count, piece):
        last = min(first + piece, count)  # one past the last frame of this piece
        begin, end = first * HOP, (last - 1) * HOP + FRAME
        mix = (left[begin:end].astype(np.float64) + right[begin:end].astype(np.float64)) / 2
        frames = np.lib.stride_tricks.sliding_window_view(mix, FRAME)[::HOP]
        energy = np.abs(np.fft.rfft(frames * window, axis=1)) ** 2
        levels[first:last] = np.log10(1.0 + energy @ bands)
    return levels


def trill_scores(levels: ArrayLike, sample_rate: float, windows: int) -> tuple[TrillScores, TrillNotes]:
    """How much a trill is playing around the middle of each 60 ms analysis window, and its lower note.

    For window ``w`` the levels of the :data:`SPAN` seconds whose middle frame is the one whose middle is nearest the window's middle,
    ``(w + 0.5) x BUFFER_INTERVAL_MS`` (the whole part of the frame number), are scored as the module says; a window whose span does not
    fit in the levels scores 0. The inputs are not changed.

    Arrays:
        ``levels``: ``ArrayLike`` ``(levels, 57)`` - the level of each semitone in each frame (``SemitoneLevels``).

    Returns:
        ``TrillScores`` ``(windows,)`` - the score of each window, from 0 to 1, and ``TrillNotes`` ``(windows,)`` - the analysis column of
        the lower note of its best pair, -1 where the score is 0.
    """
    rate = _check_rate(sample_rate)
    if isinstance(windows, (bool, np.bool_)) or not isinstance(windows, numbers.Integral) or windows < 0:
        raise ValueError("The number of windows must be a whole number of at least 0.")
    try:
        array = np.asarray(levels, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The levels must be numbers.") from None
    if array.ndim != 2 or array.shape[1] != SEMITONES or not np.isfinite(array).all():
        raise ValueError(f"The levels must be a (levels, {SEMITONES}) array of finite numbers.")
    scores = np.zeros(int(windows))
    notes = np.full(int(windows), -1, dtype=np.int64)
    step = HOP / rate  # seconds from one frame to the next
    span = int(SPAN / step)
    flicker_rates = np.fft.rfftfreq(span, step)
    fast = (flicker_rates >= FLICKER_BAND[0]) & (flicker_rates <= FLICKER_BAND[1])
    taper = np.hanning(span)[:, None]
    for w in range(int(windows)):
        middle = int(((w + 0.5) * BUFFER_INTERVAL_MS / 1000 - FRAME / 2 / rate) / step)
        first = middle - span // 2
        if first < 0 or first + span > array.shape[0]:
            continue
        part = array[first : first + span]
        flicker = part - part.mean(axis=0)
        power = np.abs(np.fft.rfft(flicker * taper, axis=0)) ** 2
        share = power[fast].sum(axis=0) / (power[1:].sum(axis=0) + 1e-12)
        means = part.mean(axis=0)
        sounding = np.percentile(means, SOUNDING_PERCENTILE)
        for apart in STEPS:
            low, high = flicker[:, :-apart], flicker[:, apart:]
            correlation = (low * high).sum(axis=0) / (np.sqrt((low * low).sum(axis=0) * (high * high).sum(axis=0)) + 1e-12)
            pair = np.maximum(-correlation, 0.0) * np.minimum(share[:-apart], share[apart:])
            pair = np.where(np.minimum(means[:-apart], means[apart:]) > sounding, pair, 0.0)
            best = int(np.argmax(pair))
            if pair[best] > scores[w]:
                scores[w], notes[w] = pair[best], FIRST_COLUMN + best
    return scores, notes


def trill_spans(scores: ArrayLike, notes: ArrayLike) -> TrillSpans:
    """The trills, as spans of analysis windows: an integer array ``(spans, 3)``.

    A window is in a trill when its score is at least :data:`TRILL_SCORE`; two windows in a trill with at most :data:`MAX_GAP_WINDOWS`
    windows between them are in the same span; a span of fewer than :data:`MIN_WINDOWS` windows (from its first to its last) is dropped;
    a span that is kept is widened by :data:`EDGE_WINDOWS` at each end (never before window 0 or after the last window). The inputs are
    not changed.

    Arrays:
        ``scores``: ``ArrayLike`` ``(windows,)`` - the score of each window (``TrillScores``), finite.
        ``notes``: ``ArrayLike`` ``(windows,)`` - the analysis column of the lower note of each window's best pair (``TrillNotes``).

    Returns:
        ``TrillSpans`` ``(spans, 3)`` - the first window, the last window and the lowest lower note (an analysis column) of the windows in
        a trill, of each span, in time order.
    """
    try:
        score_array = np.asarray(scores, dtype=np.float64)
        note_array = np.asarray(notes)
    except (TypeError, ValueError):
        raise ValueError("The scores and the notes must be numbers.") from None
    if score_array.ndim != 1 or note_array.shape != score_array.shape or not np.isfinite(score_array).all() or note_array.dtype.kind not in "iu":
        raise ValueError("The scores and the notes must be 1-D arrays of the same length: finite scores and whole-number notes.")
    spans: list[list[int]] = []
    for window in np.flatnonzero(score_array >= TRILL_SCORE):
        note = int(note_array[window])
        if spans and window - spans[-1][1] <= MAX_GAP_WINDOWS + 1:
            spans[-1][1] = int(window)
            spans[-1][2] = min(spans[-1][2], note)
        else:
            spans.append([int(window), int(window), note])
    kept = [span for span in spans if span[1] - span[0] + 1 >= MIN_WINDOWS]
    kept = [[max(first - EDGE_WINDOWS, 0), min(last + EDGE_WINDOWS, score_array.shape[0] - 1), note] for first, last, note in kept]
    return np.asarray(kept, dtype=np.int64).reshape(-1, 3)


def find_trills(left: ArrayLike, right: ArrayLike, sample_rate: float, windows: int) -> TrillSpans:
    """The trills of a file, as spans of its 60 ms analysis windows: :func:`semitone_levels`, :func:`trill_scores`, :func:`trill_spans`.

    Arrays:
        ``left``, ``right``: ``ArrayLike`` ``(samples,)`` - the two channels of the file as read (``RawSamples``), of the same length.

    Returns:
        ``TrillSpans`` ``(spans, 3)`` - the first window, the last window and the analysis column of the lowest note of each trill.
    """
    levels = semitone_levels(left, right, sample_rate)
    return trill_spans(*trill_scores(levels, sample_rate, windows))
