"""The ``tempo_votes``: the tempo of a file found by voting on the spacing of its sustained loudest notes (feature 047).

The local peaks of the energy are not always on the beat, so Rhythm Circles takes two of its tempos from the **notes**: every
time a new one of the loudest notes starts, the time since the previous start is a **note length**, and that length could be a
half, a quarter, an eighth or a sixteenth note, any of those dotted (1.5 times as long), or a triplet (1/3 or 2/3 of a beat), in
any of 18 tempos. Each tempo that the length could fit gets votes, and the tempos with the most votes are the tempos of the
music.

* **The starts** are the times at which a note begins, found by ``note_onsets`` (from the rise of the note strengths of the 60 ms
  analysis windows, placed on the waveform: until the fourth round of feature 047 they were the entries of the held loudest notes
  into their selection), so the tempos do not depend on the frame rate. Notes that begin together are one start. The first start only
  begins the run.
* **The tempos** are the metronome markings ``72 + 4n`` from 76 to 144 beats per minute, 18 of them (:data:`TEMPOS`).
* **A tempo is possible for a note length** when the length can be one of the note values (:data:`NOTE_BEATS`, in beats, a beat
  being a quarter note: 2, 1, 1/2, 1/4, each times 1.5 for the dotted note, and the triplets 1/3 and 2/3) at that tempo: a note
  of ``b`` beats at tempo ``T`` is ``60 b / T`` seconds long. It **fits** when either the tempo that the length implies,
  ``60 b / L``, is within half a bin (:data:`HALF_BIN`, 2 beats per minute) of ``T``, or the note's length at ``T`` differs from
  ``L`` by at most half the **time resolution** of the starts (a start is only known to a window, 60 ms, so the half bin alone would
  almost never match a measured length; Rhythm Circles gives 40 ms now that the starts are placed on the waveform); both comparisons are inclusive (:func:`fitting_tempos`).
* **The points.** A fitting tempo does not always get the same: a plain note (a half, quarter, eighth or sixteenth) gives it 2
  points, a dotted note or a triplet only 1 (they are less likely), so that when a measured length fits many tempos the ones that
  fit as a plain note rank above the ones that fit only as a dotted note or a triplet. A tempo gets the points of the best note
  value that fits it, once however many fit (:func:`tempo_points`).
* **The votes.** At every start after the first (a **cycle**, its length the time since the previous start): one vote is taken
  from every tempo (never below 0), then each tempo that fits gets its points, 2 or 1 (never above the **vote limit**, 20 unless
  the job says), so the votes are whole numbers from 0 to the limit, and a tempo that stops fitting is forgotten in at most as many
  cycles as the limit (:func:`vote_tempos`).
* **The ranking.** After each start the tempo with the most votes is the **first** (the **raw**) tempo and the next the **second**; a tie goes
  to the lower tempo; a place whose tempo has no votes holds the starting tempo, 120 (:func:`ranked_tempos`; Rhythm Circles takes its
  tempo from :func:`leading_tempos` since the fifth round).
* **The fifth round** (what Rhythm Circles uses, :func:`leading_tempos`):

  - **The last 2 starts.** A start votes with its time since each of the last :data:`LOOKBACK` (2) starts; each tempo gets the better
    of the points of the two lengths (once, not their sum). A note between two beats then does not hide the time from beat to beat.
  - **Beats divided in 2 or in 3.** The votes are kept twice: once with the note values above (a beat divided in 2) and once with the
    note values of a beat divided in 3 (:data:`TRIPLE_NOTE_BEATS`: the beat is a dotted quarter; two beats, a beat, a quarter, an
    eighth and a sixteenth note give 2 points, a dotted eighth, two quarters and three beats 1). After each start the **meter** is the
    one whose best tempo has more votes; when they are equal the meter stays (2 at first).
  - **A tie keeps the tempo.** The leading tempo is the chosen meter's tempo with the most votes; when several are equal and the tempo
    before is one of them it stays, else the lowest of them; with no vote at all it stays (120 at first) (:func:`meter_tempos`).
  - **The vote limit** is 40 unless the job says (it was 20): with two lengths a start gives more points, and 20 was reached too soon.
* **The average.** The first tempo jumps from one start to the next, so the **average tempo** after a start is the straight average of the
  first tempo after it and after the 4 starts before it (:data:`AVERAGE_COUNT`, 5 in all; fewer at the beginning of the file: the mean
  of those there are). The second tempo is not drawn any more (:func:`average_tempos`).

This module knows nothing about the audio, the job or the picture: it takes the start times. How the tempos are drawn is
``rhythm_circles``'s business.

Order of operations:
    1. Check the setting - ``check_vote_limit()`` - the vote limit as a whole number from 1 to 100.
    2. Find the points that each note length gives to each tempo - ``tempo_points()`` (called by ``vote_tempos()``, which makes it
       first; its ``_fits_by_note()`` makes the ``FitMatrix`` ``(cycles, 18, 10)`` of which note value fits which tempo, and
       ``fitting_tempos()`` the ``(cycles, 18)`` of the tempos that any note value fits) - ``TempoPoints`` ``(cycles, 18)``: for
       each time between two starts, 2, 1 or 0 for each of the 18 tempos.
    3. Vote - ``vote_tempos()`` - ``TempoVotes`` ``(starts, 18)``: after each start, one vote less for every tempo and its points
       more (the best points of its time since each of the last ``lookback`` starts, for the note values of one meter), from 0 to the
       vote limit.
    4. Rank - ``ranked_tempos()`` - ``RankedTempos`` ``(starts, 2)``: after each start the tempo with the most votes and the
       next (ties to the lower tempo, 120 for a place without votes); or, for Rhythm Circles, vote for both meters with the last 2
       starts and choose the meter and its leading tempo - ``leading_tempos()`` (``MeterVotes`` ``(starts, 2, 18)``, then
       ``meter_tempos()``) - ``MeterTempos`` ``(starts, 2)``: the leading tempo and the meter after each start.
    5. Average the first tempos - ``average_tempos()`` - ``AveragedTempos`` ``(starts,)``: the mean of the first tempo after each
       start and after the 4 starts before it.
    6. Make the circle series - ``vote_series()`` - ``CircleSeries`` ``(starts, 4)``: the average tempo, its rate of change, the
       first (raw) tempo, its rate of change, in revolutions per minute.
"""

import numbers

import numpy as np

from .array_types import ArrayLike, AveragedTempos, CircleSeries, FitMatrix, MeterTempos, MeterVotes, RankedTempos, StartTimes, TempoPoints, TempoVotes
from .tempo_finder import START_TEMPO

TEMPOS = tuple(72 + 4 * n for n in range(1, 19))  # beats per minute: 76, 80 ... 144, the standard metronome markings in range
# the length in beats of a half, a quarter, an eighth and a sixteenth note, each dotted (times 1.5), and the two triplets
NOTE_BEATS = (2.0, 1.0, 0.5, 0.25, 3.0, 1.5, 0.75, 0.375, 1 / 3, 2 / 3)
# the points a note value gives to a tempo it fits, in the order of NOTE_BEATS: 2 for a half, quarter, eighth or sixteenth note, 1 for a
# dotted note or a triplet (they are less likely than a plain note, so they count half as much and a tempo that only they fit ranks lower)
PLAIN_POINTS = 2
DOTTED_POINTS = 1
TRIPLET_POINTS = 1
NOTE_POINTS = (PLAIN_POINTS,) * 4 + (DOTTED_POINTS,) * 4 + (TRIPLET_POINTS,) * 2
# a beat divided in 3 (fifth round; the beat is a dotted quarter): two beats, a beat, a quarter (2/3), an eighth (1/3) and a sixteenth (1/6)
# note give 2 points; a dotted eighth (1/2), two quarters (4/3) and three beats give 1
TRIPLE_NOTE_BEATS = (2.0, 1.0, 2 / 3, 1 / 3, 1 / 6, 0.5, 4 / 3, 3.0)
TRIPLE_NOTE_POINTS = (PLAIN_POINTS,) * 5 + (DOTTED_POINTS,) * 3
METERS = (2, 3)  # a beat divided in 2 (NOTE_BEATS) or in 3 (TRIPLE_NOTE_BEATS)
LOOKBACK = 2  # Rhythm Circles: a start votes with its time since each of this many starts before it
HALF_BIN = 2.0  # beats per minute: half the distance between two neighbouring tempos
SLACK = 1e-9  # added to the inclusive comparisons so that an exact case (0.5 s and the implied 90 against 88 and 92) is inclusive
DEFAULT_VOTE_LIMIT = 40  # the most votes a tempo can have when a job does not say (20 until the fifth round of feature 047)
MIN_VOTE_LIMIT = 1  # the least the setting can be
MAX_VOTE_LIMIT = 100  # the most
VOTE_LIMIT_MESSAGE = f"The vote limit must be a whole number from {MIN_VOTE_LIMIT} to {MAX_VOTE_LIMIT}."
NO_VOTES_TEMPO = START_TEMPO  # what a place whose tempo has no votes holds, beats per minute
AVERAGE_COUNT = 5  # how many first tempos (the latest and the 4 before it) the average tempo takes the straight average of


def check_vote_limit(value: object) -> int:
    """The Vote limit setting as a whole number: ``value`` must be a whole number from ``MIN_VOTE_LIMIT`` to ``MAX_VOTE_LIMIT``
    (a bool, a string, ``None``, a fraction or a non-finite number is refused with ``VOTE_LIMIT_MESSAGE``).

    Returns:
        The limit as an ``int``, from 1 to 100.
    """
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Real) or not np.isfinite(value) or float(value) != int(value):
        raise ValueError(VOTE_LIMIT_MESSAGE)
    if not MIN_VOTE_LIMIT <= int(value) <= MAX_VOTE_LIMIT:
        raise ValueError(VOTE_LIMIT_MESSAGE)
    return int(value)


def _check_starts(start_times: ArrayLike) -> StartTimes:
    """The start times as a float64 array; anything that is not a list of finite numbers in strictly increasing order is refused.

    Arrays:
        ``start_times``: ``ArrayLike`` ``(starts,)`` - the time of each start in seconds, strictly increasing.

    Returns:
        ``StartTimes`` ``(starts,)`` - the same times as float64.
    """
    try:
        array = np.asarray(start_times, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The start times must be numbers.") from None
    if array.ndim != 1 or not np.isfinite(array).all() or (array.size > 1 and (np.diff(array) <= 0).any()):
        raise ValueError("The start times must be a 1-D array of finite numbers in strictly increasing order.")
    return array


def _check_resolution(resolution: float) -> float:
    """The time resolution of the starts as a float: a finite number of 0 seconds or more, else refused."""
    if isinstance(resolution, (bool, np.bool_)) or not isinstance(resolution, numbers.Real) or not np.isfinite(resolution) or resolution < 0:
        raise ValueError("The resolution must be a finite number of seconds, 0 or more.")
    return float(resolution)


def _note_table(meter: int) -> tuple[tuple[float, ...], tuple[int, ...]]:
    """The note values (in beats) and their points for a meter: :data:`NOTE_BEATS` for 2, :data:`TRIPLE_NOTE_BEATS` for 3; anything else is refused."""
    if isinstance(meter, (bool, np.bool_)) or meter not in METERS:
        raise ValueError(f"The meter must be one of {METERS}.")
    return (NOTE_BEATS, NOTE_POINTS) if meter == 2 else (TRIPLE_NOTE_BEATS, TRIPLE_NOTE_POINTS)


def fitting_tempos(lengths: ArrayLike, resolution: float, meter: int = 2) -> FitMatrix:
    """Which of the 18 tempos each note length can be a note of: a boolean array ``(cycles, 18)``.

    A length ``L`` fits a tempo ``T`` when for some note value ``b`` of :data:`NOTE_BEATS` either the tempo the length implies,
    ``60 b / L``, is within :data:`HALF_BIN` of ``T``, or the length of that note at ``T``, ``60 b / T``, is within
    ``resolution / 2`` of ``L`` (both inclusive, with :data:`SLACK`). ``resolution`` is the time resolution of the starts in
    seconds (0 for start times that are exact). ``meter`` 3 takes the note values of a beat divided in 3 (:data:`TRIPLE_NOTE_BEATS`)
    in place of :data:`NOTE_BEATS`. The inputs are not changed.

    Arrays:
        ``lengths``: ``ArrayLike`` ``(cycles,)`` - the time between two starts, in seconds, each above 0.

    Returns:
        ``FitMatrix`` ``(cycles, 18)`` - true where the length fits the tempo (the columns are :data:`TEMPOS` in order).
    """
    return _fits_by_note(lengths, resolution, meter).any(axis=2)


def tempo_points(lengths: ArrayLike, resolution: float, meter: int = 2) -> TempoPoints:
    """The points each note length gives to each of the 18 tempos: an integer array ``(cycles, 18)`` of 0, 1 or 2.

    A tempo gets the points of the best note value that the length fits at that tempo (:func:`fitting_tempos`'s rule, one note
    value at a time): :data:`PLAIN_POINTS` (2) for a half, quarter, eighth or sixteenth note, :data:`DOTTED_POINTS` and
    :data:`TRIPLET_POINTS` (1) for a dotted note and a triplet, 0 for a tempo that no note value fits. A tempo gets its points once however many
    note values fit (the most they give, not their sum). ``meter`` 3 takes the note values and points of a beat divided in 3
    (:data:`TRIPLE_NOTE_BEATS`, :data:`TRIPLE_NOTE_POINTS`). The inputs are not changed.

    Arrays:
        ``lengths``: ``ArrayLike`` ``(cycles,)`` - the time between two starts, in seconds, each above 0.

    Returns:
        ``TempoPoints`` ``(cycles, 18)`` - 0 where no note value fits the tempo, else the points of the best fitting one
        (the columns are :data:`TEMPOS` in order).
    """
    fits = _fits_by_note(lengths, resolution, meter)  # (cycles, 18, note values)
    points = np.asarray(_note_table(meter)[1], dtype=np.int64)[None, None, :]
    return np.where(fits, points, 0).max(axis=2)


def _fits_by_note(lengths: ArrayLike, resolution: float, meter: int = 2) -> FitMatrix:
    """For each note length, tempo and note value, whether the value fits: a boolean array ``(cycles, 18, values)`` (the rule of
    :func:`fitting_tempos`, before the note values are combined; the last axis is the meter's note values in order: :data:`NOTE_BEATS`,
    10, for 2, :data:`TRIPLE_NOTE_BEATS`, 8, for 3).

    Arrays:
        ``lengths``: ``ArrayLike`` ``(cycles,)`` - the time between two starts, in seconds, each above 0.

    Returns:
        ``FitMatrix`` ``(cycles, 18, values)`` - true where the note value fits the tempo for the length.
    """
    note_beats = _note_table(meter)[0]
    try:
        array = np.asarray(lengths, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The note lengths must be numbers.") from None
    if array.ndim != 1 or not np.isfinite(array).all() or (array <= 0).any():
        raise ValueError("The note lengths must be a 1-D array of finite numbers above 0.")
    half = _check_resolution(resolution) / 2 + SLACK
    tempos = np.asarray(TEMPOS, dtype=np.float64)[None, :, None]  # (1, 18, 1)
    beats = np.asarray(note_beats, dtype=np.float64)[None, None, :]  # (1, 1, values)
    seconds = array[:, None, None]  # (cycles, 1, 1)
    by_tempo = np.abs(60.0 * beats / seconds - tempos) <= HALF_BIN + SLACK  # the tempo that the length implies, within half a bin
    by_length = np.abs(60.0 * beats / tempos - seconds) <= half  # the length of the note at the tempo, within the time resolution
    return by_tempo | by_length


def vote_tempos(start_times: ArrayLike, resolution: float, limit: int, meter: int = 2, lookback: int = 1) -> TempoVotes:
    """The votes of the 18 tempos after each start: an integer array ``(starts, 18)``, row 0 all 0.

    At every start after the first, one vote is taken from every tempo (never below 0), then each tempo gets the points that the
    time since the previous start gives it (:func:`tempo_points`: 2 for a plain note value, 1 for a dotted one or a triplet, 0 for no fit; once
    however many note values fit), never above ``limit``. With ``lookback`` above 1 (Rhythm Circles takes :data:`LOOKBACK`, 2) the time
    since each of the last ``lookback`` starts (those there are) is a length, and each tempo gets the best of their points (once, not
    their sum). ``meter`` 3 takes the note values of a beat divided in 3. The inputs are not changed.

    Arrays:
        ``start_times``: ``ArrayLike`` ``(starts,)`` - the time of each start in seconds, strictly increasing (``StartTimes``).

    Returns:
        ``TempoVotes`` ``(starts, 18)`` - the votes of each tempo after each start, whole numbers from 0 to ``limit``.
    """
    starts = _check_starts(start_times)
    resolution = _check_resolution(resolution)
    limit = check_vote_limit(limit)
    _note_table(meter)
    if isinstance(lookback, (bool, np.bool_)) or not isinstance(lookback, numbers.Integral) or lookback < 1:
        raise ValueError("The lookback must be a whole number of at least 1.")
    votes = np.zeros((starts.shape[0], len(TEMPOS)), dtype=np.int64)
    points = np.zeros((max(starts.shape[0] - 1, 0), len(TEMPOS)), dtype=np.int64)  # row i: the points of start i + 1
    for back in range(1, min(int(lookback), starts.shape[0] - 1) + 1):  # the time since the start ``back`` before
        points[back - 1 :] = np.maximum(points[back - 1 :], tempo_points(starts[back:] - starts[:-back], resolution, meter))
    for cycle in range(points.shape[0]):  # a vote depends on the one before it (the two limits), so this is the only loop
        now = np.maximum(votes[cycle] - 1, 0)
        votes[cycle + 1] = np.where(points[cycle] > 0, np.minimum(now + points[cycle], limit), now)
    return votes


def ranked_tempos(votes: ArrayLike) -> RankedTempos:
    """The two best-voted tempos after each start: a float64 array ``(starts, 2)`` in beats per minute.

    Column 0 is the tempo with the most votes and column 1 the next; a tie goes to the lower tempo; a place whose tempo has no
    votes holds :data:`NO_VOTES_TEMPO` (120) instead.

    Arrays:
        ``votes``: ``ArrayLike`` ``(starts, 18)`` - the votes of each tempo after each start (``TempoVotes``).

    Returns:
        ``RankedTempos`` ``(starts, 2)`` - the first and the second tempo after each start.
    """
    try:
        array = np.asarray(votes, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The votes must be numbers.") from None
    if array.ndim != 2 or array.shape[1] != len(TEMPOS) or not np.isfinite(array).all() or (array < 0).any() or (array != np.floor(array)).any():
        raise ValueError(f"The votes must be a (starts, {len(TEMPOS)}) array of whole numbers of 0 or more.")
    order = np.argsort(-array, axis=1, kind="stable")  # the tempos are in ascending order, so a stable sort ranks ties lower first
    places = order[:, :2]
    tempos = np.asarray(TEMPOS, dtype=np.float64)[places]
    return np.where(np.take_along_axis(array, places, axis=1) > 0, tempos, NO_VOTES_TEMPO)


def meter_tempos(votes: ArrayLike) -> MeterTempos:
    """The leading tempo and the meter after each start, from the votes of the two meters: a float64 array ``(starts, 2)``.

    The meter starts as 2 and the tempo as :data:`NO_VOTES_TEMPO` (120). After each start the meter becomes the other one only when the
    other's best tempo has more votes than the best of the meter now; then, if the meter's best tempo has any vote, the tempo becomes the
    meter's tempo with the most votes: the tempo before when it is one of the equal best, else the lowest of them. With no vote the
    tempo stays. The input is not changed.

    Arrays:
        ``votes``: ``ArrayLike`` ``(starts, 2, 18)`` - the votes of each tempo after each start for beats divided in 2 and in 3
            (``MeterVotes``), whole numbers of 0 or more.

    Returns:
        ``MeterTempos`` ``(starts, 2)`` - column 0 the leading tempo in beats per minute, column 1 the meter, 2 or 3.
    """
    try:
        array = np.asarray(votes, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The votes must be numbers.") from None
    if array.ndim != 3 or array.shape[1:] != (len(METERS), len(TEMPOS)) or not np.isfinite(array).all() or (array < 0).any() or (array != np.floor(array)).any():
        raise ValueError(f"The votes must be a (starts, {len(METERS)}, {len(TEMPOS)}) array of whole numbers of 0 or more.")
    tempos = np.asarray(TEMPOS, dtype=np.float64)
    result = np.zeros((array.shape[0], 2))
    place, tempo = 0, NO_VOTES_TEMPO  # the meter (its place in METERS) and the tempo before
    for start in range(array.shape[0]):  # each choice depends on the one before (a tie keeps it), so this is a loop
        best = array[start].max(axis=1)
        if best[1 - place] > best[place]:
            place = 1 - place
        if best[place] > 0:
            leaders = tempos[array[start, place] == best[place]]
            if tempo not in leaders:
                tempo = float(leaders[0])
        result[start] = tempo, METERS[place]
    return result


def leading_tempos(start_times: ArrayLike, resolution: float, limit: int) -> MeterTempos:
    """The tempo of Rhythm Circles after each start (fifth round of feature 047): a float64 array ``(starts, 2)``, the tempo and the meter.

    The starts are voted on twice with :func:`vote_tempos`, for beats divided in 2 and in 3, each start with its time since each of the
    last :data:`LOOKBACK` starts, and :func:`meter_tempos` chooses the meter and its leading tempo. The inputs are not changed.

    Arrays:
        ``start_times``: ``ArrayLike`` ``(starts,)`` - the time of each start in seconds, strictly increasing (``StartTimes``).

    Returns:
        ``MeterTempos`` ``(starts, 2)`` - the leading tempo in beats per minute and the meter (2 or 3) after each start; the
        ``MeterVotes`` ``(starts, 2, 18)`` it is chosen from are made on the way.
    """
    votes: MeterVotes = np.stack([vote_tempos(start_times, resolution, limit, meter, LOOKBACK) for meter in METERS], axis=1)
    return meter_tempos(votes)


def average_tempos(tempos: ArrayLike) -> AveragedTempos:
    """The straight average of the last 5 tempos after each start: a float64 array ``(starts,)`` in beats per minute.

    Entry ``i`` is the mean of ``tempos[i - 4]`` to ``tempos[i]`` (:data:`AVERAGE_COUNT` of them, all of them weighing the same);
    for the first four starts, the mean of all there are (entry 0 is ``tempos[0]``). The input is not changed.

    Arrays:
        ``tempos``: ``ArrayLike`` ``(starts,)`` - the first tempo after each start, in beats per minute (column 0 of ``RankedTempos``).

    Returns:
        ``AveragedTempos`` ``(starts,)`` - the average tempo after each start.
    """
    try:
        array = np.asarray(tempos, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The tempos must be numbers.") from None
    if array.ndim != 1 or not np.isfinite(array).all():
        raise ValueError("The tempos must be a 1-D array of finite numbers.")
    total = np.concatenate([[0.0], np.cumsum(array)])  # total[i] is the sum of the first i tempos
    ends = np.arange(1, array.shape[0] + 1)
    begins = np.maximum(ends - AVERAGE_COUNT, 0)
    return (total[ends] - total[begins]) / (ends - begins)


def vote_series(start_times: ArrayLike, levels: ArrayLike) -> CircleSeries:
    """The four speeds of the vote rings after each start: a float64 array ``(starts, 4)`` in revolutions per minute.

    ``levels`` holds the level of the two layers after each start (for Rhythm Circles the average tempo and the first tempo). The
    columns are the first layer's level, its rate of change, the second layer's level, its rate of change; the rate of change at a
    start is ``(level now - level at the previous start) / (seconds between the starts)``, 0 for the first start. The inputs are not
    changed.

    Arrays:
        ``start_times``: ``ArrayLike`` ``(starts,)`` - the time of each start in seconds, strictly increasing (``StartTimes``).
        ``levels``: ``ArrayLike`` ``(starts, 2)`` - the level of each of the two layers after each start, in beats per minute (for
            Rhythm Circles ``AveragedTempos`` and column 0 of ``RankedTempos``, side by side).

    Returns:
        ``CircleSeries`` ``(starts, 4)`` - the first level, its rate of change, the second level, its rate of change.
    """
    starts = _check_starts(start_times)
    try:
        levels = np.asarray(levels, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The levels must be numbers.") from None
    if levels.shape != (starts.shape[0], 2) or not np.isfinite(levels).all():
        raise ValueError(f"The levels must be a ({starts.shape[0]}, 2) array of finite numbers, one row for each start.")
    series = np.zeros((starts.shape[0], 4))
    for place in range(2):  # the level in column 2p, the change of the level in column 2p + 1
        series[:, 2 * place] = levels[:, place]
        series[1:, 2 * place + 1] = np.diff(levels[:, place]) / np.diff(starts)
    return series

