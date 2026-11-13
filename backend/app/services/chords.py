"""The ``chords`` measurement: which chord the loudest notes of every analysis window form.

A **chord type** is a tuple of 1 to 3 *intervals*, each a whole number of steps (half steps) above an implied root: ``(4,)`` is the notes 0 and 4
(a major third), ``(4, 7)`` the notes 0, 4 and 7 (a major triad). A chord type with ``n`` intervals has ``n + 1`` notes and ``n + 1`` positions, the
root position (inversion 0) and ``n`` inversions: inversion ``k`` is made by moving the ``k`` lowest notes up an octave and counting the steps from
the new lowest note (``(4,)``: 0, 4 then 0, 8; ``(4, 7)``: 0, 4, 7 then 0, 3, 8 then 0, 5, 9).

The notes first go through the **noise floor** (``noise_floor.apply_noise_floor``, feature 033): a note strictly below a thousandth (-60 dB) of the
largest value of the whole array given is 0, so it is neither a note of a chord nor one of the recorded notes, whatever array the measurement is
given. The cut comes before the Notes limit, the Threshold and the combining of the octaves, so a letter is made of notes that were not cut only.

For every window the notes are then combined into the 12 **letters** (the 7 octaves of a letter are added up: an octave is the same note), and the
loudest letters are matched against every chord type asked for. A type with ``n`` intervals looks at the ``min(n + 3, 6)`` loudest letters (4 for one
interval, 5 for two, 6 for three; a letter with no strength does not count; equal strengths go to the lower letter) and tries every choice of ``n + 1`` of them. Each letter stands for its loudest octave
(the lowest on a tie). The notes of a choice are brought down by whole octaves until they are less than an octave above the lowest (dividing their
frequency by 2), and the steps above the lowest note are compared with every inversion of the type.

A louder note that fits no chord therefore does not hide a chord among the other loud letters, and the overtones of a note (which are other letters,
such as its fifth) can be taken for the notes of a chord. That is accepted: the chords are meant to be aggregated later.

When several choices, types or inversions match, exactly one is recorded: the one with the most intervals, then the one whose letters are the
loudest (their strengths added up), then the one with the largest interval, then the lowest inversion, then the first choice in the order of the
louder letters. (The loudest letters come before the widest interval so that a faint note that makes a wide interval cannot beat a louder chord; for
the same letters the widest interval still wins, so a fourth is recorded as an inverted fifth when both are asked for.) A record holds the chord type,
the inversion and the **original notes** (the loudest octave of each letter, lowest first, as they sound before moving them into one octave); a
window with no chord has no record.

The notes of the interval search can be limited the way the pictures limit theirs: ``note_count`` (the Notes setting: only the notes with the most
total energy over the file) and ``threshold`` (the Threshold setting: a note weaker than that percentage of the loudest value is hidden in the window).
The measurement has no limit of its own; the limits are those of ``note_selection`` and ``frame_rendering``, so that the notes used are the notes the
picture uses. The chosen notes keep their own pitch (the picture spreads them over its grid, which would change their intervals).

This module knows nothing about the note analysis, the audio, the frames or the router: it takes the note strengths of the windows. Nothing uses it
yet; how it is used is a later feature.
"""

import itertools
import numbers
from dataclasses import dataclass

import numpy as np

from .note_grid import NOTES
from .noise_floor import apply_noise_floor
from .note_selection import check_note_count, top_energy_notes

MIN_INTERVALS = 1
MAX_INTERVALS = 3
MAX_STEP = 11  # a chord spans less than an octave: 12 steps is the same note again
OCTAVE = 12
WINDOW_NOTES = MAX_INTERVALS + 1  # the most notes any chord type uses: a record holds at most this many
LETTERS = 12
OCTAVES = NOTES // LETTERS  # 7: the 84 piano notes
EXTRA_LETTERS = 2  # a type with n + 1 notes looks at this many letters more than it has notes: 4, 5 or 6 letters ...
MAX_LETTERS = WINDOW_NOTES + EXTRA_LETTERS  # ... six at most (the user's limit, because the choices multiply), reached by the 3-interval types

CHORD_LIST_MESSAGE = "The chord types must be a list of one or more chord types."
VALUES_SHAPE_MESSAGE = "Each window needs at least {notes} note values (got shape {shape})."
VALUES_MESSAGE = "The note values must be finite numbers that are not negative."


def _whole(value) -> bool:
    return isinstance(value, (int, np.integer)) and not isinstance(value, (bool, np.bool_))


def check_chord_type(value) -> tuple[int, ...]:
    """Return ``value`` as a tuple of ``int`` when it is a chord type: 1 to 3 whole numbers from 1 to 11 in strictly increasing order.

    A tuple or a list is accepted, and a bare whole number is the one-interval type (``5`` is ``(5,)``). Booleans, fractions (also ``4.0``), strings
    and ``None`` are refused.
    """
    message = f"A chord type must be {MIN_INTERVALS} to {MAX_INTERVALS} intervals, each a whole number of steps from 1 to {MAX_STEP}, in increasing order (got {value!r})."
    if _whole(value):
        items = (value,)
    elif isinstance(value, (tuple, list)):
        items = tuple(value)
    else:
        raise ValueError(message)
    if not MIN_INTERVALS <= len(items) <= MAX_INTERVALS or not all(_whole(x) and 1 <= x <= MAX_STEP for x in items):
        raise ValueError(message)
    result = tuple(int(x) for x in items)
    if any(a >= b for a, b in zip(result, result[1:])):
        raise ValueError(message)
    return result


def check_chord_types(types) -> tuple[tuple[int, ...], ...]:
    """Return the list of chord types as a tuple of checked chord types, in the order given.

    The list must not be empty and must not hold a chord type twice. (Python reads ``((5), (7))`` as ``(5, 7)``: two bare numbers, which are the
    one-interval types ``(5,)`` and ``(7,)``, as intended.)
    """
    if types is None or isinstance(types, (str, bytes, numbers.Number)):
        raise ValueError(CHORD_LIST_MESSAGE)
    try:
        given = list(types)
    except TypeError:
        raise ValueError(CHORD_LIST_MESSAGE) from None
    if not given:
        raise ValueError(CHORD_LIST_MESSAGE)
    checked = tuple(check_chord_type(t) for t in given)
    seen = set()
    for chord_type in checked:
        if chord_type in seen:
            raise ValueError(f"The chord type {chord_type!r} is given more than once.")
        seen.add(chord_type)
    return checked


def inversion_patterns(chord_type) -> tuple[tuple[int, ...], ...]:
    """The steps above the lowest note for inversion 0 (root position) to ``n`` of a chord type with ``n`` intervals.

    Inversion ``k`` has the notes ``c[k], ..., c[n], c[0] + 12, ..., c[k - 1] + 12`` (``c`` being 0 and the intervals), counted from ``c[k]``.
    """
    chord = (0, *check_chord_type(chord_type))
    patterns = []
    for k in range(len(chord)):
        notes = chord[k:] + tuple(x + OCTAVE for x in chord[:k])
        patterns.append(tuple(x - notes[0] for x in notes))
    return tuple(patterns)


@dataclass(frozen=True)
class ChordRecord:
    """The chord recorded for one window: its type as given, its inversion (0 is root position) and the original notes (0 to 83, lowest first)."""

    chord_type: tuple[int, ...]
    inversion: int
    notes: tuple[int, ...]


@dataclass(frozen=True, eq=False)
class ChordSeries:
    """The chords of a whole file: one entry for every analysis window, in window order, stored like the note strengths.

    ``chord_types`` are the checked chord types in the order given. ``type_index`` (``int16``, ``(W,)``) is the index of the chord type of every
    window in it, ``inversion`` (``int8``, ``(W,)``) its inversion, ``notes`` (``int16``, ``(W, 4)``) the original notes, lowest first; ``-1`` is
    "no chord" in the first two and the padding (and "no chord") in the third. The arrays are read-only.
    """

    chord_types: tuple[tuple[int, ...], ...]
    type_index: np.ndarray
    inversion: np.ndarray
    notes: np.ndarray

    @property
    def window_count(self) -> int:
        return int(self.type_index.shape[0])

    def record(self, index: int) -> ChordRecord | None:
        """The chord of window ``index`` (negative counts from the end), or ``None`` when the window has no chord."""
        if not _whole(index) or not -self.window_count <= index < self.window_count:
            raise IndexError(f"The window must be a whole number from {-self.window_count} to {self.window_count - 1} (got {index!r}).")
        index = int(index) % self.window_count
        chord = int(self.type_index[index])
        if chord < 0:
            return None
        notes = tuple(int(n) for n in self.notes[index] if n >= 0)
        return ChordRecord(self.chord_types[chord], int(self.inversion[index]), notes)

    def records(self) -> list[ChordRecord | None]:
        """The chord of every window, in order: a list of :class:`ChordRecord` and ``None``."""
        return [self.record(i) for i in range(self.window_count)]

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, ChordSeries)
            and self.chord_types == other.chord_types
            and np.array_equal(self.type_index, other.type_index)
            and np.array_equal(self.inversion, other.inversion)
            and np.array_equal(self.notes, other.notes)
        )

    __hash__ = None  # type: ignore[assignment]


def _pattern_mask(pattern) -> int:
    mask = 0
    for step in pattern:
        mask |= 1 << step
    return mask


def _check_values(values) -> np.ndarray:
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError(VALUES_MESSAGE) from None
    if array.ndim != 2 or array.shape[1] < NOTES:
        raise ValueError(VALUES_SHAPE_MESSAGE.format(notes=NOTES, shape=array.shape))
    if array.size and (not np.isfinite(array).all() or array.min() < 0):
        raise ValueError(VALUES_MESSAGE)
    return array


def _letters(strength: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The 12 letters of every window: ``(strength, note)``, each ``(windows, 12)``.

    The strength of a letter is its 7 octaves added up (from the lowest octave, so the sum is always done the same way); the notes have been through
    the noise floor already. The note of a letter is its loudest octave, the lowest one on a tie.
    """
    by_octave = strength.reshape(strength.shape[0], OCTAVES, LETTERS)
    total = by_octave[:, 0].copy()
    for octave in range(1, OCTAVES):
        total += by_octave[:, octave]
    note = by_octave.argmax(axis=1) * LETTERS + np.arange(LETTERS)
    return total, note


def _greater(new, old) -> np.ndarray:
    """Whether the score ``new`` beats ``old`` in every window: the kinds of score are compared in order, the first that differs decides."""
    result = np.zeros(new[0].shape, dtype=bool)
    tied = np.ones(new[0].shape, dtype=bool)
    for a, b in zip(new, old):
        result |= tied & (a > b)
        tied &= a == b
    return result


def measure_chords(values, chord_types, note_count=None, threshold=None) -> ChordSeries:
    """The chord of every window: which of ``chord_types`` the loudest notes form, and in which inversion (see the module text).

    ``values`` is ``(windows, 84 to 88)``, the note strengths of the analysis; the columns after the 84th are never in a chord. ``chord_types`` is
    the list of chord types to look for (:func:`check_chord_types`). ``note_count`` and ``threshold`` are optional and limit the notes like the
    pictures' Notes and Threshold settings. Everything is checked before any window is measured. The input is not changed. The noise floor is
    applied to ``values`` first (see the module text).
    """
    types = check_chord_types(chord_types)
    if note_count is not None:
        note_count = check_note_count(note_count)
    if threshold is not None:
        from .frame_rendering import hidden_below  # when needed: the picture module may use this one later

        hidden_below(np.zeros(1), 0.0, threshold)  # raises the picture's message for a threshold it would refuse
    values = _check_values(values)
    values = apply_noise_floor(values)  # the noise floor first: a faint note is 0 and so is no part of a chord (idempotent for values already cut)
    strength = values[:, :NOTES].copy()
    if note_count is not None:  # only the notes with the most energy over the whole file: the same in every window, each in its own pitch
        left_out = np.ones(NOTES, dtype=bool)
        left_out[top_energy_notes(strength, note_count)] = False
        strength[:, left_out] = 0.0
    if threshold is not None:  # a note strictly below the percentage of the largest value anywhere (the four extra notes count) is hidden in its window
        strength[hidden_below(values[:, :NOTES], float(values.max()) if values.size else 0.0, threshold)] = 0.0

    windows = strength.shape[0]
    letters, letter_note = _letters(strength)
    # the loudest letters of every window, once: a stable sort on the negative strength puts equal strengths in the order of the letters
    order = np.argsort(-letters, axis=1, kind="stable")[:, :MAX_LETTERS]
    ranked = np.take_along_axis(letters, order, axis=1)
    ranked_note = np.take_along_axis(letter_note, order, axis=1)

    # the best match so far in every window as the kinds of score compared one after the other (all "greater is better"); any match beats these
    best = (np.zeros(windows, dtype=np.int64), np.zeros(windows), np.zeros(windows, dtype=np.int64), np.zeros(windows, dtype=np.int64), np.zeros(windows, dtype=np.int64))
    best_type = np.full(windows, -1, dtype=np.int16)
    best_inversion = np.full(windows, -1, dtype=np.int8)
    best_notes = np.full((windows, WINDOW_NOTES), -1, dtype=np.int16)

    for position, chord_type in enumerate(types):
        count = len(chord_type) + 1
        reach = count + EXTRA_LETTERS  # how many of the loudest letters this type looks at
        patterns = inversion_patterns(chord_type)
        for index, choice in enumerate(itertools.combinations(range(reach), count)):
            places = list(choice)
            sounding = (ranked[:, places] > 0).all(axis=1)
            chosen = np.sort(ranked_note[:, places], axis=1)  # the notes of the letters, lowest first
            steps = (chosen - chosen[:, :1]) % OCTAVE  # the steps above the lowest note, the higher notes folded down
            mask = np.bitwise_or.reduce(1 << steps, axis=1)  # one bit for each step above the lowest note

            inversion = np.full(windows, -1, dtype=np.int8)
            for k in reversed(range(count)):  # the lowest inversion that matches is the one that is kept
                inversion[mask == _pattern_mask(patterns[k])] = k
            matched = sounding & (inversion >= 0)  # the letters are all different, so the masks have exactly ``count`` bits like the patterns

            # the loudness of the choice, added up from the lowest letter so that equal choices give the very same sum
            by_letter = np.take_along_axis(letters, np.sort(order[:, places], axis=1), axis=1)
            loudness = by_letter[:, 0].copy()
            for column in range(1, count):
                loudness += by_letter[:, column]

            # the most intervals, the loudest letters, the largest interval, the lowest inversion, the first choice of the louder letters; two different
            # types never tie on all of these (they cannot match the same letters at the same inversion with the same widest interval), so the order of
            # the list given never decides
            score = (
                np.full(windows, len(chord_type), dtype=np.int64),
                loudness,
                np.full(windows, chord_type[-1], dtype=np.int64),
                -inversion.astype(np.int64),
                np.full(windows, -index, dtype=np.int64),
            )
            better = matched & _greater(score, best)
            for kept, new in zip(best, score):
                kept[better] = new[better]
            best_type[better] = position
            best_inversion[better] = inversion[better]
            best_notes[better] = -1
            best_notes[better, :count] = chosen[better]

    for array in (best_type, best_inversion, best_notes):
        array.flags.writeable = False
    return ChordSeries(types, best_type, best_inversion, best_notes)
