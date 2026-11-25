"""Held notes: which notes a picture counts as the loudest ones of a frame, when a note that is still sounding keeps its place (feature 044).

The pictures that take the n loudest notes of a frame (Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe, Polychord and Spirograph) used to rank the notes of each frame by
strength and take the first n. That forgets how long a note lasts, which has a lot to do with how loud it is heard: most notes start louder (the attack) and then fade, and a note
that starts later can be louder than a note that is still ringing. A **held note** is a note that was in the selection of the frame before and is still among the loudest **n + k** of
this frame (and still sounds): it keeps one of the n places. A note that is not held is a **newcomer** and can only take a **free place**, which is a place that no held note occupies:
at the start, when fewer than n notes sound, or when a held note has fallen below the loudest n + k. ``k`` is the *Extra notes* setting, 1 to n. With ``k = 0`` a note is held only
while it is among the loudest n, which is exactly the old selection: the library functions default to 0 and so change nothing for a caller that does not pass ``k``.

The same rule serves two kinds of unit: the 84 notes (Decay, Decay Exp, Polar Chords, Polychord, Spirograph) and the 12 letters (Chromatic Decay, Chromatic Wireframe, whose letter energy is the loudest octave
of each letter). Ties in strength go to the lower note (letter), as in every picture.

This module knows nothing about the audio, the pictures or the job: it takes an array of strengths and answers with an array of places.

Order of operations:
    1. Check the values and the numbers - ``hold_loudest()`` - ``NoteStrengths``-shaped ``(frames, columns)`` finite numbers that are not negative, a whole ``count`` from 1 to the
       number of columns and a whole ``extra`` from 0 to ``count``.
    2. Rank the notes of every frame, all frames at once - ``hold_loudest()`` - a stable ``argsort`` of the negative strengths ``(frames, columns)`` (the notes from the loudest down) and its
       inverse (the rank of each note, 0 for the loudest).
    3. Frame by frame (the only loop, because a frame depends on the selection of the frame before) - ``hold_loudest()`` - keep the notes of the previous selection that rank within the
       loudest ``count + extra`` and sound; give the free places to the loudest notes that are not held; order the selection by rank. The first frame, and a frame after one in which
       nothing sounded, has nothing held, so its selection is the ``count`` loudest.
    4. Pad - ``hold_loudest()`` - ``LoudestIndices`` ``(frames, count)``: when fewer than ``count`` notes sound, the last places hold the next notes in the ranking, whose strength is 0, so that
       ``values[order] > 0`` says that a place is empty.
"""

import numbers

import numpy as np

from .array_types import ArrayLike, LoudestIndices, NoteStrengths

MIN_EXTRA_NOTES = 1  # the least k the user can choose
MAX_EXTRA_NOTES = 8  # the most: the largest n of Polar Chords and Polychord (up to 8 notes); Spirograph takes up to 12 notes but its k also stops at 8 (feature 046)
DEFAULT_EXTRA_NOTES = 2  # k when a job does not say
LOUDEST_COUNT = 5  # n for the pictures that always take the five loudest notes (Decay, Decay Exp, Chromatic Decay, Chromatic Wireframe)
HELD_NOTES_TYPES = ("decay", "decay-exp", "polar-chords", "chromatic-decay", "chromatic-wireframe", "polychord", "spirograph")  # the image types that take the n loudest notes


def notes_of(image_type: str, polar_notes: int, polychord_notes: int, spirograph_notes: int = MAX_EXTRA_NOTES) -> int:
    """The number of notes n of a picture, which is the largest value of k that the picture accepts: ``LOUDEST_COUNT`` for Decay, Decay Exp, Chromatic Decay and Chromatic Wireframe,
    ``polar_notes`` for Polar Chords, ``polychord_notes`` for Polychord, the smaller of ``spirograph_notes`` (5 to 12) and ``MAX_EXTRA_NOTES`` for Spirograph (k stops at 8 even for
    12 notes), and ``MAX_EXTRA_NOTES`` for a picture that does not take the n loudest notes (the widest value its Extra notes can have).

    Returns:
        The number of notes as an ``int``: the largest value of k that the picture accepts.
    """
    if image_type == "polar-chords":
        return polar_notes
    if image_type == "polychord":
        return polychord_notes
    if image_type == "spirograph":
        return min(spirograph_notes, MAX_EXTRA_NOTES)
    if image_type in HELD_NOTES_TYPES:
        return LOUDEST_COUNT
    return MAX_EXTRA_NOTES


def check_extra_notes(value: object, limit: int = MAX_EXTRA_NOTES) -> int:
    """The *Extra notes* setting as a whole number: ``value`` must be a whole number from 1 to ``limit`` (a bool, a string, a fraction or a non-finite number is refused).

    ``limit`` is 8 for any picture and the picture's own n (5, or the Notes shown / Number of notes setting, at most 8) for the seven that use it.

    Returns:
        The number as an ``int``, from ``MIN_EXTRA_NOTES`` to ``limit``.
    """
    message = f"The extra notes must be a whole number from {MIN_EXTRA_NOTES} to {limit}."
    if isinstance(value, bool) or not isinstance(value, numbers.Real) or not np.isfinite(value) or float(value) != int(value):
        raise ValueError(message)
    if not MIN_EXTRA_NOTES <= int(value) <= limit:
        raise ValueError(message)
    return int(value)


def _check_values(values: ArrayLike) -> NoteStrengths:
    """The strengths as a float64 ``(frames, columns)`` array; anything else is refused.

    Arrays:
        ``values``: ``ArrayLike`` ``(frames, columns)`` - the strength of each note (or letter) in each frame, finite and not negative.

    Returns:
        ``NoteStrengths`` ``(frames, columns)`` - the same numbers as float64.
    """
    message = "The note values must be finite numbers that are not negative."
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError(message) from None
    if array.ndim != 2:
        raise ValueError("The note values must be a (frames, notes) array.")
    if array.size and (not np.isfinite(array).all() or array.min() < 0):
        raise ValueError(message)
    return array


def _whole(value: object, low: int, high: int) -> int | None:
    """``value`` as an int when it is a whole number from ``low`` to ``high`` (a bool or a fraction is not), else None."""
    if isinstance(value, bool) or not isinstance(value, numbers.Real) or not np.isfinite(value) or float(value) != int(value):
        return None
    return int(value) if low <= int(value) <= high else None


def hold_loudest(values: ArrayLike, count: int, extra: int = 0) -> LoudestIndices:
    """The notes that count as the ``count`` loudest of every frame, a note that is still among the loudest ``count + extra`` keeping its place: ``(frames, count)``, loudest first.

    In every frame the *held* notes are those of the selection of the frame before that rank within the loudest ``count + extra`` (rank 1 is the loudest; equal strengths: the lower
    note is louder) and have a strength above 0. A place that no held note occupies is free and goes to the loudest note that is not held and sounds; a note that is not held never
    takes the place of a held one, however loud. The first frame, and any frame after a frame in which nothing sounded, has nothing held: it is the ``count`` loudest. The selection is
    ordered by loudness (not by the order in which the notes were chosen). With ``extra`` 0 the result is exactly ``np.argsort(-values, axis=1, kind="stable")[:, :count]``. When fewer
    than ``count`` notes sound the last places hold notes whose strength is 0. The input is not changed.

    Arrays:
        ``values``: ``ArrayLike`` ``(frames, columns)`` - the strength of each note (84 columns, or the 12 letter energies) in each frame (``NoteStrengths``).

    Returns:
        ``LoudestIndices`` ``(frames, count)`` - for each frame the index (0 to ``columns - 1``) of the note at each of the ``count`` places, loudest first, held notes among them; a place
        with no sounding note holds a note whose strength is 0.
    """
    array = _check_values(values)
    frames, columns = array.shape
    checked = _whole(count, 1, columns)
    if checked is None:
        raise ValueError(f"The count must be a whole number from 1 to {columns}.")
    count = checked
    allowed = _whole(extra, 0, count)
    if allowed is None:
        raise ValueError(f"The extra notes must be a whole number from 0 to {count}.")
    reach = count + allowed

    order = np.argsort(-array, axis=1, kind="stable")  # the notes of each frame from the loudest down
    rank = np.empty_like(order)
    np.put_along_axis(rank, order, np.broadcast_to(np.arange(columns), order.shape), axis=1)  # the place of each note in that order
    result = np.empty((frames, count), dtype=np.intp)
    previous: list[int] = []
    for frame in range(frames):
        row = array[frame]
        ranks = rank[frame]
        held = [note for note in previous if ranks[note] < reach and row[note] > 0]
        free = count - len(held)
        if free:
            taken = set(held)
            for note in order[frame, :count].tolist():  # at most len(held) of these are held, so free newcomers are among them
                if row[note] <= 0:
                    break  # the rest do not sound either
                if note not in taken:
                    held.append(note)
                    free -= 1
                    if not free:
                        break
        held.sort(key=ranks.__getitem__)
        sounding = len(held)
        result[frame, :sounding] = held
        if sounding < count:
            result[frame, sounding:] = order[frame, sounding:count]  # every sounding note is selected here, so these are the notes whose strength is 0
        previous = held
    return result
