"""The chord interval metric: chord types, inversions, matching, selection, storage, the picture's limits (feature 031).

The checks use an independent oracle written here: it works from frequencies (dividing the higher notes by 2 until they are less than an octave
above the lowest) and from explicit permutations of the notes, not from the bit masks that ``chords.py`` uses.

The notes of a window are first combined into the 12 letters (the octaves of a letter add up); a chord type with ``n`` intervals looks at
``min(n + 3, 6)`` of the loudest letters and takes the best ``n + 1`` of them that form the type.
"""

import itertools
import math

import numpy as np
import pytest

from app.services import frame_rendering, note_selection
from app.services.chords import (
    ChordRecord,
    check_chord_type,
    check_chord_types,
    inversion_patterns,
    measure_chords,
)

C2, C3, C4, E4, G4, C5 = 3, 15, 27, 31, 34, 39  # note numbers: 0 is A1 (55 Hz), one step apart
TYPE_MESSAGE = "A chord type must be 1 to 3 intervals, each a whole number of steps from 1 to 11, in increasing order (got {}).".format
LIST_MESSAGE = "The chord types must be a list of one or more chord types."
ALL_TYPES = [t for n in (1, 2, 3) for t in itertools.combinations(range(1, 12), n)]  # all 231 valid chord types


def windows(*rows, columns=88) -> np.ndarray:
    """A ``(W, columns)`` array of zeros with, for each row, ``{note: strength}`` or a list of notes (strengths 1.0, 0.9, 0.8, ... in the order given)."""
    values = np.zeros((len(rows), columns))
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            row = {note: 1.0 - 0.1 * j for j, note in enumerate(row)}
        for note, strength in row.items():
            values[i, note] = strength
    return values


# ---- the oracle -------------------------------------------------------------------------------------------------------------------


def note_frequency(note: int) -> float:
    return 55.0 * 2 ** (note / 12)


def oracle_fold(notes) -> tuple[int, ...]:
    """The steps above the lowest note after dividing the frequency of every higher note by 2 until it is less than an octave above the lowest."""
    lowest = note_frequency(min(notes))
    steps = []
    for note in sorted(notes):
        f = note_frequency(note)
        while f >= 2 * lowest * (1 - 1e-9):
            f /= 2
        steps.append(round(12 * math.log2(f / lowest)))
    return tuple(sorted(steps))


def oracle_inversions(chord_type) -> list[tuple[int, ...]]:
    """Inversion 0 to n made physically: move the lowest note up an octave and count from the new lowest note."""
    notes = [0, *chord_type]
    patterns = []
    for _ in notes:
        patterns.append(tuple(x - notes[0] for x in notes))
        notes = notes[1:] + [notes[0] + 12]
    return patterns


def floored(values):
    """The noise floor written out as a loop: every value strictly below a thousandth of the largest value of the whole array (all columns, the
    four undrawn notes too) is 0."""
    array = np.asarray(values, dtype=np.float64)
    flat = array.ravel().tolist()
    top = max(flat) if flat else 0.0
    return np.array([0.0 if v < top * 0.001 else v for v in flat]).reshape(array.shape)


def oracle_letters(row):
    """For each of the 12 letters: ``(strength, loudest note)``. The row has been through the noise floor (``floored``) already. The strength is the 7
    octaves added up, from the lowest octave, and the loudest note is the loudest octave (the lowest on a tie)."""
    letters = []
    for letter in range(12):
        octaves = [row[12 * octave + letter] for octave in range(7)]
        total = 0.0
        for value in octaves:
            total += value
        letters.append((total, 12 * octaves.index(max(octaves)) + letter))
    return letters


def oracle_window(row, types):
    """What should be recorded for one window of 84+ strengths: ``(chord_type, inversion, notes)`` or ``None``.

    A type with ``n`` intervals looks at the ``min(n + 3, 6)`` loudest sounding letters (equal strengths: the lower letter first). Every choice of
    ``n + 1`` of them that forms the type is a candidate; the best has the most intervals, then the loudest letters (added from the lowest letter),
    then the widest interval, then the lowest inversion, then the first choice in the order of the combinations of the louder letters.
    """
    letters = oracle_letters(row)
    rank = [letter for letter in sorted(range(12), key=lambda x: (-letters[x][0], x))[:6] if letters[letter][0] > 0]
    best = None
    for chord_type in types:
        n = len(chord_type)
        for index, combo in enumerate(itertools.combinations(range(min(n + 3, 6)), n + 1)):
            if combo[-1] >= len(rank):
                continue
            chosen = [rank[i] for i in combo]
            notes = sorted(letters[letter][1] for letter in chosen)
            steps = oracle_fold(notes)
            found = [k for k, pattern in enumerate(oracle_inversions(chord_type)) if pattern == steps]
            if not found:
                continue
            loudness = 0.0
            for letter in sorted(chosen):
                loudness += letters[letter][0]
            key = (n, loudness, max(chord_type), -found[0], -index)
            if best is None or key > best[0]:
                best = (key, chord_type, found[0], tuple(notes))
    return None if best is None else (best[1], best[2], best[3])


def as_tuple(record):
    return None if record is None else (record.chord_type, record.inversion, record.notes)


# ---- the inversions of a chord type -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "chord_type, expected",
    [
        ((4,), ((0, 4), (0, 8))),
        ((5,), ((0, 5), (0, 7))),
        ((7,), ((0, 7), (0, 5))),
        ((4, 7), ((0, 4, 7), (0, 3, 8), (0, 5, 9))),
        ((4, 8), ((0, 4, 8), (0, 4, 8), (0, 4, 8))),
        ((3, 7, 10), ((0, 3, 7, 10), (0, 4, 7, 9), (0, 3, 5, 8), (0, 2, 5, 9))),
        ((3, 6, 9), ((0, 3, 6, 9),) * 4),
    ],
)
def test_the_inversions_of_a_chord_type(chord_type, expected):
    assert inversion_patterns(chord_type) == expected


def test_there_are_231_chord_types_and_every_inversion_pattern_is_the_one_made_by_moving_notes_up_an_octave():
    assert len(ALL_TYPES) == 231
    for chord_type in ALL_TYPES:
        patterns = inversion_patterns(chord_type)
        assert list(patterns) == oracle_inversions(chord_type)
        assert len(patterns) == len(chord_type) + 1
        for pattern in patterns:
            assert pattern[0] == 0 and list(pattern) == sorted(set(pattern)) and pattern[-1] < 12


# ---- the parameters ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("value, expected", [((4,), (4,)), ([4], (4,)), ((4, 7), (4, 7)), ([3, 6, 9], (3, 6, 9)), (5, (5,)), (np.int64(4), (4,)), ((np.int64(4), np.int32(7)), (4, 7))])
def test_a_chord_type_is_a_tuple_of_whole_numbers_and_a_bare_number_is_a_one_interval_type(value, expected):
    result = check_chord_type(value)
    assert result == expected and type(result) is tuple and all(type(x) is int for x in result)


@pytest.mark.parametrize(
    "value",
    [(), [], (1, 2, 3, 4), (0,), (12,), (-4,), (7, 4), (4, 4), (4, 12), (4.5,), (4.0,), (True,), ("4",), None, (None,), "47", 12, 0, True, 4.0, {4: 7}],
)
def test_anything_else_is_refused_with_the_message(value):
    with pytest.raises(ValueError) as error:
        check_chord_type(value)
    assert str(error.value) == TYPE_MESSAGE(repr(value))


def test_python_reads_two_bare_numbers_in_parentheses_as_two_one_interval_types():
    assert check_chord_types(((5), (7))) == ((5,), (7,))  # ((5), (7)) is (5, 7) in Python
    assert check_chord_types([(5,), (7,)]) == ((5,), (7,))
    assert check_chord_types([5, 7]) == ((5,), (7,))


def test_the_order_given_is_kept_and_a_generator_is_accepted():
    assert check_chord_types([(4, 7), (4,), (8,)]) == ((4, 7), (4,), (8,))
    assert check_chord_types(t for t in [(4,), (7,)]) == ((4,), (7,))


@pytest.mark.parametrize("value", [[], (), None, 4, "ab", b"ab", 4.5, True])
def test_a_missing_or_empty_list_is_refused(value):
    with pytest.raises(ValueError) as error:
        check_chord_types(value)
    assert str(error.value) == LIST_MESSAGE


@pytest.mark.parametrize("value", [[(4,), (4,)], [(4,), [4]], [(4, 7), (5,), (4, 7)], [4, 4]])
def test_a_chord_type_given_twice_is_refused(value):
    with pytest.raises(ValueError) as error:
        check_chord_types(value)
    assert "is given more than once." in str(error.value) and str(error.value).startswith("The chord type (")


def test_a_bad_chord_type_in_the_list_is_refused_with_the_type_message():
    with pytest.raises(ValueError) as error:
        check_chord_types([(4,), (7, 4)])
    assert str(error.value) == TYPE_MESSAGE(repr((7, 4)))


def test_the_list_given_is_not_changed():
    given = [[4], (4, 7)]
    check_chord_types(given)
    assert given == [[4], (4, 7)]


# ---- User Story 1: the worked examples --------------------------------------------------------------------------------------------


def only(notes, types, **limits):
    """The record of the one window whose sounding notes are given (strengths 1.0, 0.9, 0.8, ... in the order given)."""
    return measure_chords(windows(notes), types, **limits).record(0)


def test_c3_with_e4_is_a_third_in_root_position_and_the_original_notes_are_recorded_not_the_folded_ones():
    # E4 is 16 steps above C3: brought down an octave it is 4 steps above (E3), but the record keeps E4
    assert only([C3, E4], [(4,)]) == ChordRecord((4,), 0, (C3, E4))


def test_e4_with_c5_is_a_third_in_first_inversion():
    assert only([E4, C5], [(4,)]) == ChordRecord((4,), 1, (E4, C5))  # 8 steps apart: 0, 8


def test_c_e_g_in_each_position_of_a_triad():
    types = [(4, 7)]
    assert only([C4, E4, G4], types) == ChordRecord((4, 7), 0, (27, 31, 34))
    assert only([E4, G4, C5], types) == ChordRecord((4, 7), 1, (31, 34, 39))
    assert only([G4, C5, 43], types) == ChordRecord((4, 7), 2, (34, 39, 43))


def test_the_notes_may_be_in_any_octaves_and_are_recorded_lowest_to_highest_as_they_sound():
    # C2, G3 and E4: the lowest is C, G is 19 steps up (7 after folding), E is 28 steps up (4): root position
    assert only([E4, C2, 22], [(4, 7)]) == ChordRecord((4, 7), 0, (C2, 22, E4))
    # the loudest is not the lowest: the order of the strengths does not matter
    assert only([G4, E4, C4], [(4, 7)]) == ChordRecord((4, 7), 0, (C4, E4, G4))


def test_a_longer_chord_type_wins_over_a_shorter_one_that_also_fits():
    # C, E, G: the two loudest (C, E) are a third and also match (4), but the three loudest are the triad
    assert only([C4, E4, G4], [(4,), (4, 7)]) == ChordRecord((4, 7), 0, (27, 31, 34))
    assert only([C4, E4, G4], [(4, 7), (4,)]) == ChordRecord((4, 7), 0, (27, 31, 34))


def test_the_widest_wins_in_both_directions():
    # (8) in root position over (4) in first inversion: E4 and C5 are 8 steps apart
    assert only([E4, C5], [(4,), (8,)]) == ChordRecord((8,), 0, (E4, C5))
    # and the other way round: 4 steps apart is (4) in root position and (8) in first inversion; (8) is wider
    assert only([C3, E4], [(4,), (8,)]) == ChordRecord((8,), 1, (C3, E4))


def test_a_fourth_is_recorded_as_an_inverted_fifth_because_the_widest_wins():
    assert only([C4, G4], [(5,), (7,)]) == ChordRecord((7,), 0, (C4, G4))  # a fifth: 7 steps
    assert only([C4, 32], [(5,), (7,)]) == ChordRecord((7,), 1, (C4, 32))  # a fourth: 5 steps
    assert only([C4, 32], [(5,)]) == ChordRecord((5,), 0, (C4, 32))  # asked for on its own it is (5)


def test_a_chord_type_with_three_intervals_uses_the_four_loudest_notes_and_has_four_positions():
    types = [(3, 7, 10)]
    played = [[27, 30, 34, 37], [30, 34, 37, 39], [34, 37, 39, 42], [37, 39, 42, 46]]  # C Eb G Bb, then each note in the bass
    for inversion, notes in enumerate(played):
        assert only(notes, types) == ChordRecord((3, 7, 10), inversion, tuple(notes))


def test_the_same_input_gives_the_same_records():
    values = windows([C3, E4], [E4, C5], [C4, E4, G4], {})
    one = measure_chords(values, [(4,), (4, 7)])
    two = measure_chords(values, [(4,), (4, 7)])
    assert one == two and one.records() == two.records()


# ---- folding and the notes that count ---------------------------------------------------------------------------------------------


def test_the_same_letter_in_two_octaves_is_one_letter_so_two_octaves_alone_are_no_chord():
    assert only([C2, C3], [(4,)]) is None
    assert only([C2, C3, 19], [(4, 7)]) is None  # C2, C3 and E3: only two letters, a triad needs three
    assert only([C2, 19, C3], [(4,)]) == ChordRecord((4,), 0, (C2, 19))  # C2 and C3 are one letter beside E3: a third
    assert only([C2, 19, C3], [(4, 7)]) is None


def test_the_octaves_of_a_letter_are_added_up_before_the_loudest_letters_are_chosen():
    # letters 1 and 2 are the loudest; C (two octaves of 0.3 = 0.6) beats 3 (0.5), so with E (0.58) the third C-E is among the 4 loudest letters. Each of the
    # notes of C alone (0.3) would be too weak to be among the loudest.
    row = {28: 1.0, 29: 0.9, C4: 0.3, C5: 0.3, E4: 0.58, 30: 0.5}
    assert only(row, [(4,)]) == ChordRecord((4,), 0, (C4, E4))


def test_a_letter_is_recorded_with_its_loudest_octave_and_the_lowest_octave_on_a_tie():
    assert only({C4: 0.3, C5: 0.5, E4: 0.9}, [(4,)]) == ChordRecord((4,), 1, (E4, C5))  # C5 is the louder C: E4 to C5 is 8 steps, a third inverted
    assert only({C4: 0.5, C5: 0.3, E4: 0.9}, [(4,)]) == ChordRecord((4,), 0, (C4, E4))
    assert only({C4: 0.4, C5: 0.4, E4: 0.9}, [(4,)]) == ChordRecord((4,), 0, (C4, E4))  # equal: the lower octave


def test_a_note_an_octave_or_more_above_the_lowest_folds_onto_it_and_never_makes_a_new_step():
    assert only([C3, C3 + 24], [(4,)]) is None  # two octaves up: the same letter again
    assert only([C3, C3 + 12], [(4,)]) is None
    assert only([C3, C3 + 12 + 4], [(4,)]) == ChordRecord((4,), 0, (C3, C3 + 16))


def test_a_note_with_no_strength_does_not_count():
    assert only([C3], [(4,)]) is None  # one sounding note
    assert only({C3: 1.0, E4: 0.0}, [(4,)]) is None
    assert only([C4, E4, G4], [(3, 7, 10)]) is None  # three sounding notes, four needed
    assert only([C4, E4, G4], [(3, 7, 10), (4,)]) == ChordRecord((4,), 0, (C4, E4))  # another type of the list can still match
    assert measure_chords(windows({}), [(4,)]).record(0) is None


def test_equal_strengths_go_to_the_lower_letter():
    # 3, 7 and 11 are all a third apart (3-7, 7-11) or an inverted third (3-11) and equally loud: the louder letters are taken in order, the lower first
    assert measure_chords(windows({3: 1.0, 7: 1.0, 11: 1.0}), [(4,)]).record(0) == ChordRecord((4,), 0, (3, 7))
    assert measure_chords(windows({11: 1.0, 7: 1.0, 3: 1.0}), [(4,)]).record(0) == ChordRecord((4,), 0, (3, 7))  # the order of writing does not matter


def test_a_louder_note_that_fits_nothing_does_not_hide_the_chord_among_the_loudest_letters():
    # C and E, then a louder F#: the two loudest letters are F# and C (6 steps, no match), but C and E are still among the 4 loudest
    assert only({C4: 0.9, E4: 0.8, 33: 1.0}, [(4,)]) == ChordRecord((4,), 0, (C4, E4))
    # C E G loud and a faint D: the triad is the loudest choice of three letters
    assert only({C4: 1.0, E4: 0.9, G4: 0.8, 29: 0.1}, [(4, 7)]) == ChordRecord((4, 7), 0, (C4, E4, G4))


def test_of_the_choices_that_form_a_chord_type_the_loudest_letters_win():
    # two major triads share the note G: C E G and G B D (38 is B, 41 is D); the louder one is recorded
    row = {C4: 1.0, E4: 0.9, G4: 0.8, 38: 0.3, 41: 0.2}
    assert only(row, [(4, 7)]) == ChordRecord((4, 7), 0, (C4, E4, G4))
    row = {C4: 0.3, E4: 0.2, G4: 0.8, 38: 1.0, 41: 0.9}
    assert only(row, [(4, 7)]) == ChordRecord((4, 7), 0, (G4, 38, 41))


def test_loudness_comes_before_the_widest_interval_but_the_widest_still_decides_among_the_same_letters():
    # B is faint. (4, 11) fits C E B and (4, 7) fits C E G: the triad is louder, though (4, 11) has the wider interval
    row = {C4: 1.0, E4: 0.9, G4: 0.8, 38: 0.1}
    assert only(row, [(4, 7), (4, 11)]) == ChordRecord((4, 7), 0, (C4, E4, G4))
    assert only(row, [(4, 11), (4, 7)]) == ChordRecord((4, 7), 0, (C4, E4, G4))
    # the same two letters: a fifth (7) over the same notes seen as a fourth (5)
    assert only([C4, G4], [(5,), (7,)]) == ChordRecord((7,), 0, (C4, G4))


# how many letters a chord type looks at: 2 + 2 for one interval, 3 + 2 for two, 4 + 2 for three (6 at most). Letters 1 and 2 are loud and form no chord with
# anything; the chord is C-E (0, 4), C-E-G (0, 4, 7) or C-Eb-G-Bb (0, 3, 7, 10) on the notes 27 to 37
@pytest.mark.parametrize(
    "chord_type, in_reach, out_of_reach",
    [
        ((4,), [28, 29, 27, 31], [28, 29, 30, 27, 31]),
        ((4, 7), [28, 29, 27, 31, 34], [28, 29, 30, 27, 31, 34]),
        ((3, 7, 10), [28, 29, 27, 30, 34, 37], [28, 29, 31, 27, 30, 34, 37]),
    ],
)
def test_a_chord_type_looks_at_two_more_letters_than_it_has_notes_but_at_six_at_most(chord_type, in_reach, out_of_reach):
    assert only(in_reach, [chord_type]) == ChordRecord(chord_type, 0, tuple(sorted(in_reach[2:])))  # the two loud fillers are the first two notes
    assert only(out_of_reach, [chord_type]) is None  # the weakest letter of the chord is one place too far down


# ---- the noise floor (feature 033): a note below a thousandth of the loudest value (-60 dB) is 0, and is no part of a chord ------------------------


def test_a_note_below_the_floor_is_no_part_of_a_chord_and_one_exactly_at_it_is():
    # the seventh chord (4, 7, 10) would win over the triad if B-flat counted; the loudest value is 1.0, so the floor is 0.001
    types = [(4, 7), (4, 7, 10)]
    triad = ChordRecord((4, 7), 0, (C4, E4, G4))
    assert only({C4: 1.0, E4: 0.9, G4: 0.8, 37: 0.0009}, types) == triad
    assert only({C4: 1.0, E4: 0.9, G4: 0.8, 37: 1e-9}, types) == triad
    assert only({C4: 1.0, E4: 0.9, G4: 0.8, 37: 0.001}, types) == ChordRecord((4, 7, 10), 0, (C4, E4, G4, 37))  # exactly at the floor: it counts
    assert only({C4: 1.0, E4: 0.9, G4: 0.8, 37: 0.0011}, types) == ChordRecord((4, 7, 10), 0, (C4, E4, G4, 37))
    assert only({C4: 1.0, E4: 0.9, G4: 0.8, 37: 1e-9}, [(4, 7, 10)]) is None


def test_a_faint_note_does_not_complete_a_chord_and_is_not_among_the_recorded_notes():
    assert only({C4: 1.0, E4: 0.9, G4: 0.0009}, [(4,), (4, 7)]) == ChordRecord((4,), 0, (C4, E4))
    assert only({C4: 1.0, E4: 0.9, G4: 0.0011}, [(4,), (4, 7)]) == ChordRecord((4, 7), 0, (C4, E4, G4))


def test_the_floor_is_the_loudest_value_of_the_whole_array_so_a_window_of_faint_notes_has_no_chord_beside_a_loud_one():
    values = windows({C4: 1.0}, {C4: 0.0005, E4: 0.0004})
    assert measure_chords(values, [(4,)]).record(1) is None
    assert measure_chords(windows({C4: 0.0005, E4: 0.0004}), [(4,)]).record(0) == ChordRecord((4,), 0, (C4, E4))  # alone it is the loudest there is


def test_the_four_undrawn_notes_set_the_floor_too():
    assert measure_chords(windows({C4: 0.5, E4: 0.4, 87: 1000.0}), [(4,)]).record(0) is None  # the floor is 1.0
    assert measure_chords(windows({C4: 0.5, E4: 0.4, 87: 100.0}), [(4,)]).record(0) == ChordRecord((4,), 0, (C4, E4))  # the floor is 0.1


def test_the_notes_are_cut_before_the_octaves_of_a_letter_are_added_up():
    # C2 and C3 are 0.0006 each, 0.0012 together, which is above the floor of 0.001; each is under it, so the letter C does not sound
    assert only({E4: 1.0, C2: 0.0006, C3: 0.0006}, [(4,)]) is None
    assert only({E4: 1.0, C2: 0.0011, C3: 0.0006}, [(4,)]) == ChordRecord((4,), 0, (C2, E4))  # one octave at or above the floor: the letter sounds, as C2


def test_cutting_values_that_have_been_cut_changes_nothing_so_the_job_and_the_measurement_agree():
    rng = np.random.default_rng(11)
    for _ in range(40):
        values = random_windows(rng, 8)
        types = [ALL_TYPES[int(i)] for i in rng.choice(len(ALL_TYPES), 4, replace=False)]
        cut = floored(values)
        assert measure_chords(values, types) == measure_chords(cut, types)


def test_the_four_notes_above_the_84_piano_notes_are_never_used():
    row = {C4: 1.0, E4: 0.9, 84: 5.0, 85: 5.0, 86: 5.0, 87: 5.0}
    assert measure_chords(windows(row), [(4,)]).record(0) == ChordRecord((4,), 0, (C4, E4))
    assert measure_chords(windows({84: 5.0, 85: 5.0}), [(1,)]).record(0) is None


# ---- the selection rules against an independent oracle -----------------------------------------------------------------------------


def play(rng, chord_type, inversion):
    """The notes of a chord type played with chord note ``inversion`` in the bass and the others in random octaves above it, in 0 to 83."""
    chord = (0, *chord_type)
    bass = int(rng.integers(0, 36))
    notes = [bass] + [bass + (chord[j] - chord[inversion]) % 12 + 12 * int(rng.integers(0, 3)) for j in range(len(chord)) if j != inversion]
    rng.shuffle(notes)
    return notes


def row_of(rng, notes, extra=0):
    """Strengths: the notes loud and different from each other, ``extra`` other notes faint."""
    strengths = rng.permutation(len(notes)) * 0.1 + 0.5
    row = {note: float(strengths[i]) for i, note in enumerate(notes)}
    for _ in range(extra):
        row.setdefault(int(rng.integers(0, 84)), float(rng.random() * 0.04 + 0.01))
    return row


def assert_like_the_oracle(values, types):
    series = measure_chords(values, types)
    cut = floored(values)  # the measurement cuts the faint notes first
    for i in range(values.shape[0]):
        assert as_tuple(series.record(i)) == oracle_window(cut[i], check_chord_types(types)), (i, types)


def test_every_chord_type_in_every_inversion_and_several_octave_placements_is_found_on_its_own():
    rng = np.random.default_rng(1)
    for chord_type in ALL_TYPES:
        rows, played = [], []
        for inversion in range(len(chord_type) + 1):
            for _ in range(3):
                notes = play(rng, chord_type, inversion)
                rows.append(row_of(rng, notes))
                played.append(notes)
        values = windows(*rows)
        series = measure_chords(values, [chord_type])
        patterns = oracle_inversions(chord_type)
        for i, notes in enumerate(played):
            found = [k for k, pattern in enumerate(patterns) if pattern == oracle_fold(notes)]
            assert series.record(i) == ChordRecord(chord_type, found[0], tuple(sorted(notes))), (chord_type, notes)


def test_every_pair_of_types_gives_what_the_oracle_gives_in_both_orders_of_the_list():
    rng = np.random.default_rng(2)
    for chord_type in ALL_TYPES:
        for other in (ALL_TYPES[int(i)] for i in rng.integers(0, len(ALL_TYPES), 3)):
            if other == chord_type:
                continue
            rows = [row_of(rng, play(rng, chord_type, k)) for k in range(len(chord_type) + 1)]
            rows += [row_of(rng, play(rng, other, k)) for k in range(len(other) + 1)]
            values = windows(*rows)
            assert_like_the_oracle(values, [chord_type, other])
            assert_like_the_oracle(values, [other, chord_type])


def test_random_lists_of_types_and_random_windows_give_what_the_oracle_gives():
    rng = np.random.default_rng(3)
    for _ in range(300):
        types = [ALL_TYPES[int(i)] for i in rng.choice(len(ALL_TYPES), int(rng.integers(2, 9)), replace=False)]
        rows = []
        for _ in range(12):
            if rng.random() < 0.6:
                t = types[int(rng.integers(0, len(types)))]
                rows.append(row_of(rng, play(rng, t, int(rng.integers(0, len(t) + 1))), extra=int(rng.integers(0, 3))))
            else:
                notes = [int(n) for n in rng.choice(40, int(rng.integers(1, 7)), replace=False)]
                strengths = np.round(rng.random(len(notes)), 1) + 0.1  # rounded: equal strengths happen
                rows.append({n: float(s) for n, s in zip(notes, strengths)})
        assert_like_the_oracle(windows(*rows), types)


def test_the_order_of_the_list_never_changes_the_record():
    # two different chord types never match at the same inversion, so the position in the list is never what decides
    rng = np.random.default_rng(4)
    for _ in range(200):
        types = [ALL_TYPES[int(i)] for i in rng.choice(len(ALL_TYPES), 6, replace=False)]
        t = types[0]
        values = windows(*[row_of(rng, play(rng, t, k), extra=int(rng.integers(0, 3))) for k in range(len(t) + 1)])
        first = measure_chords(values, types).records()
        shuffled = list(types)
        rng.shuffle(shuffled)
        assert measure_chords(values, shuffled).records() == first


def test_two_types_with_the_same_length_and_width_the_lowest_inversion_wins():
    # (5, 7) in first inversion is (2, 7) in root position: both have 2 intervals and a widest of 7
    notes = [C4, C4 + 2, C4 + 7]
    assert only(notes, [(5, 7), (2, 7)]) == ChordRecord((2, 7), 0, tuple(notes))
    assert only(notes, [(2, 7), (5, 7)]) == ChordRecord((2, 7), 0, tuple(notes))
    assert only(notes, [(5, 7)]) == ChordRecord((5, 7), 1, tuple(notes))


def test_a_symmetrical_chord_is_recorded_in_root_position_whatever_the_order_and_octaves_of_its_notes():
    rng = np.random.default_rng(5)
    for chord_type, size in (((4, 8), 3), ((3, 6, 9), 4), ((6,), 2)):
        for _ in range(20):
            notes = play(rng, chord_type, int(rng.integers(0, size)))
            record = measure_chords(windows(row_of(rng, notes)), [chord_type]).record(0)
            assert record == ChordRecord(chord_type, 0, tuple(sorted(notes)))


# ---- User Story 2: one entry for every window ---------------------------------------------------------------------------------------


def three_kinds():
    """Four windows: a third, a triad in first inversion, silence, a triad in root position."""
    return windows([C3, E4], [E4, G4, C5], {}, [C4, E4, G4])


def test_there_is_one_entry_for_every_window_stored_in_arrays_of_that_length():
    series = measure_chords(three_kinds(), [(4,), (4, 7)])
    assert series.window_count == 4
    assert series.type_index.shape == (4,) and series.type_index.dtype == np.int16
    assert series.inversion.shape == (4,) and series.inversion.dtype == np.int8
    assert series.notes.shape == (4, 4) and series.notes.dtype == np.int16
    assert series.chord_types == ((4,), (4, 7))


def test_minus_one_marks_no_chord_and_the_unused_places_of_the_notes():
    series = measure_chords(three_kinds(), [(4,), (4, 7)])
    assert series.type_index.tolist() == [0, 1, -1, 1]
    assert series.inversion.tolist() == [0, 1, -1, 0]
    assert series.notes.tolist() == [[15, 31, -1, -1], [31, 34, 39, -1], [-1, -1, -1, -1], [27, 31, 34, -1]]


def test_record_gives_the_chord_of_a_window_or_none_and_reads_the_arrays_back():
    series = measure_chords(three_kinds(), [(4,), (4, 7)])
    assert series.record(0) == ChordRecord((4,), 0, (C3, E4))
    assert series.record(1) == ChordRecord((4, 7), 1, (E4, G4, C5))
    assert series.record(2) is None
    assert series.record(3) == ChordRecord((4, 7), 0, (C4, E4, G4))
    assert series.record(-1) == series.record(3) and series.record(-4) == series.record(0)
    record = series.record(1)
    assert type(record.inversion) is int and all(type(n) is int for n in record.notes) and type(record.chord_type) is tuple


@pytest.mark.parametrize("index", [4, 5, -5, 100, 1.0, "1", None])
def test_a_window_that_does_not_exist_raises_index_error(index):
    with pytest.raises(IndexError):
        measure_chords(three_kinds(), [(4,)]).record(index)


def test_records_is_the_list_of_all_the_records_in_window_order():
    series = measure_chords(three_kinds(), [(4,), (4, 7)])
    assert series.records() == [series.record(i) for i in range(4)]
    assert len(series.records()) == 4 and series.records()[2] is None


def test_500_windows_with_a_triad_in_the_middle_give_the_triad_in_exactly_those_windows():
    values = np.zeros((500, 88))
    values[200:300, [C4, E4, G4]] = [1.0, 0.9, 0.8]
    series = measure_chords(values, [(4, 7)])
    assert series.window_count == 500
    for i in range(500):
        expected = ChordRecord((4, 7), 0, (C4, E4, G4)) if 200 <= i < 300 else None
        assert series.record(i) == expected


def test_a_record_depends_on_its_own_window_only_so_shuffling_the_windows_shuffles_the_records():
    rng = np.random.default_rng(6)
    types = [(4,), (3, 7), (4, 7), (5,), (3, 7, 10)]
    rows = []
    for _ in range(80):
        t = types[int(rng.integers(0, len(types)))]
        rows.append(row_of(rng, play(rng, t, int(rng.integers(0, len(t) + 1))), extra=int(rng.integers(0, 3))))
    values = windows(*rows)
    order = rng.permutation(80)
    straight = measure_chords(values, types).records()
    shuffled = measure_chords(values[order], types).records()
    assert shuffled == [straight[i] for i in order]


def test_a_silent_window_has_no_chord_wherever_it_stands():
    values = windows({}, [C3, E4], {}, {}, [C3, E4])
    assert [r is None for r in measure_chords(values, [(4,)]).records()] == [True, False, True, True, False]


def test_no_windows_give_an_empty_series():
    series = measure_chords(np.zeros((0, 88)), [(4,)])
    assert series.window_count == 0 and series.records() == [] and series.notes.shape == (0, 4)
    with pytest.raises(IndexError):
        series.record(0)


def test_the_input_is_not_changed_and_the_result_does_not_share_memory_with_it():
    values = three_kinds()
    before = values.copy()
    series = measure_chords(values, [(4,), (4, 7)])
    np.testing.assert_array_equal(values, before)
    assert not any(np.shares_memory(values, a) for a in (series.type_index, series.inversion, series.notes))


def test_the_result_cannot_be_changed():
    series = measure_chords(three_kinds(), [(4,)])
    with pytest.raises(Exception):
        series.chord_types = ()  # frozen
    for array in (series.type_index, series.inversion, series.notes):
        with pytest.raises(ValueError):
            array[0] = 5  # read-only


def test_two_runs_give_equal_results_and_different_input_gives_different_results():
    values = three_kinds()
    assert measure_chords(values, [(4,), (4, 7)]) == measure_chords(values.copy(), [(4,), (4, 7)])
    assert measure_chords(values, [(4,), (4, 7)]) != measure_chords(values, [(4, 7), (4,)])  # the index of a type depends on the list
    assert measure_chords(values, [(4,)]) != "not a series"


def test_a_file_of_4000_windows_with_10_types_is_measured_in_well_under_a_few_seconds():
    import time

    rng = np.random.default_rng(7)
    values = rng.random((4000, 88)) ** 3
    types = [ALL_TYPES[int(i)] for i in rng.choice(len(ALL_TYPES), 10, replace=False)]
    started = time.perf_counter()
    series = measure_chords(values, types)
    assert time.perf_counter() - started < 3.0
    assert series.window_count == 4000


# ---- User Story 3: only the notes the image type would use ---------------------------------------------------------------------------


def allowed_by_the_pictures(values, note_count=None, threshold=None):
    """The note strengths with every note that the noise floor and then the picture's Notes and Threshold settings leave out set to 0 (the picture's own
    functions for the two settings)."""
    cut = floored(values)
    strength = cut[:, :84].copy()
    if note_count is not None:
        keep = np.zeros(84, dtype=bool)
        keep[note_selection.top_energy_notes(strength, note_count)] = True
        strength[:, ~keep] = 0.0
    if threshold is not None:
        strength[frame_rendering.hidden_below(cut[:, :84], float(values.max()), threshold)] = 0.0
    return strength


def assert_limited_like_the_oracle(values, types, note_count=None, threshold=None):
    series = measure_chords(values, types, note_count=note_count, threshold=threshold)
    strength = allowed_by_the_pictures(values, note_count, threshold)
    checked = check_chord_types(types)
    for i in range(values.shape[0]):
        assert as_tuple(series.record(i)) == oracle_window(strength[i], checked), (i, note_count, threshold)


def random_windows(rng, count=30):
    values = rng.random((count, 88)) ** 4
    values[rng.random(values.shape) < 0.5] = 0.0
    return values


def heavy(notes, rows=20):
    """``rows`` windows in which the given notes sound at full strength: they get the most energy over the file."""
    return [{note: 1.0 for note in notes}] * rows


def test_with_no_limit_everything_is_as_with_a_threshold_of_0_and_all_84_notes():
    rng = np.random.default_rng(8)
    types = [(4,), (3, 7), (4, 7), (5,), (3, 7, 10)]
    for _ in range(20):
        values = random_windows(rng)
        plain = measure_chords(values, types)
        assert plain == measure_chords(values, types, threshold=0)
        assert plain == measure_chords(values, types, note_count=84)
        assert plain == measure_chords(values, types, note_count=84, threshold=0)


def test_with_a_number_of_notes_only_the_notes_with_the_most_energy_over_the_file_can_be_in_a_chord():
    chosen = list(range(40, 52))
    values = windows(*heavy(chosen), {C4: 1.0, E4: 0.9, G4: 0.8, 40: 0.1, 44: 0.1, 47: 0.1})
    target = 20
    allowed = {int(n) for n in note_selection.top_energy_notes(values[:, :84], 12)}
    assert allowed == set(chosen)
    # the loud chord is made of notes that are not among the twelve; the faint chord is
    assert measure_chords(values, [(4, 7)], note_count=12).record(target) == ChordRecord((4, 7), 0, (40, 44, 47))
    assert measure_chords(values, [(4, 7)]).record(target) == ChordRecord((4, 7), 0, (C4, E4, G4))


def test_the_chosen_notes_keep_their_own_pitch_they_are_not_spread_over_a_grid():
    chosen = [C2, 19, G4] + list(range(60, 69))  # twelve notes, among them C2, E3 and G4
    values = windows(*heavy(chosen), {C2: 1.0, 19: 0.9, G4: 0.8})
    series = measure_chords(values, [(4, 7)], note_count=12)
    assert series.record(20) == ChordRecord((4, 7), 0, (C2, 19, G4))  # C2 to E3 is 16 steps (4), to G4 is 31 (7): the real intervals


def test_a_threshold_hides_a_note_that_is_strictly_below_that_percent_of_the_largest_value_anywhere():
    values = np.zeros((4, 88))
    values[0, 87] = 10.0  # the largest value of the file is in a note that is never drawn: it still sets the scale
    values[1, [C4, E4]] = [1.0, 1.0]  # exactly 10 percent of 10: counts
    values[2, [C4, E4]] = [1.0, 0.99]  # just below: hidden
    values[3, [C4, E4]] = [5.0, 9.0]
    series = measure_chords(values, [(4,)], threshold=10)
    assert series.record(1) == ChordRecord((4,), 0, (C4, E4))
    assert series.record(2) is None
    assert series.record(3) == ChordRecord((4,), 0, (C4, E4))
    assert measure_chords(values, [(4,)], threshold=0).record(2) == ChordRecord((4,), 0, (C4, E4))


def test_the_threshold_is_worked_out_for_every_window_and_a_hidden_note_can_not_take_a_place_among_the_loudest():
    values = np.zeros((2, 88))
    values[0, [C4, E4, G4]] = [10.0, 9.0, 8.0]  # a loud window sets the scale
    values[1, [C4, E4, G4]] = [0.5, 0.4, 0.3]  # the same notes, quiet: below 10 percent of 10
    values[1, 40] = 5.0
    assert measure_chords(values, [(4, 7)], threshold=10).record(0) == ChordRecord((4, 7), 0, (C4, E4, G4))
    assert measure_chords(values, [(4, 7)], threshold=10).record(1) is None  # only note 40 counts in window 1
    assert measure_chords(values, [(4, 7)]).record(1) == ChordRecord((4, 7), 0, (C4, E4, G4))  # without the threshold the loud note 40 is just one more letter
    values[1, 40] = 0.0
    assert measure_chords(values, [(4, 7)]).record(1) == ChordRecord((4, 7), 0, (C4, E4, G4))
    assert measure_chords(values, [(4, 7)], threshold=10).record(1) is None  # all three hidden


def test_with_every_note_hidden_the_window_has_no_chord():
    values = windows({C4: 0.5, E4: 0.4, 87: 10.0})
    assert measure_chords(values, [(4,)]).record(0) == ChordRecord((4,), 0, (C4, E4))
    assert measure_chords(values, [(4,)], threshold=10).record(0) is None


def test_a_note_counts_only_if_it_passes_both_limits_and_a_louder_note_that_does_not_takes_no_place():
    chosen = list(range(40, 52))
    values = windows(*heavy(chosen), {C4: 9.0, E4: 8.0, G4: 7.0, 40: 0.3, 44: 0.2, 47: 0.1}, {87: 10.0})
    target = 20
    # without the limits the three loudest are C E G
    assert measure_chords(values, [(4, 7)]).record(target) == ChordRecord((4, 7), 0, (C4, E4, G4))
    # the number of notes leaves out C E G (the faint chord inside is found)
    assert measure_chords(values, [(4, 7)], note_count=12).record(target) == ChordRecord((4, 7), 0, (40, 44, 47))
    # the threshold (10 percent of 10 = 1) hides the faint notes; C E G pass it
    assert measure_chords(values, [(4, 7)], threshold=10).record(target) == ChordRecord((4, 7), 0, (C4, E4, G4))
    # both: C E G fail the first, the faint ones fail the second: nothing is left
    assert measure_chords(values, [(4, 7)], note_count=12, threshold=10).record(target) is None


def test_random_arrays_and_random_limits_give_what_the_oracle_gives_with_the_pictures_own_functions():
    rng = np.random.default_rng(9)
    for _ in range(200):
        values = random_windows(rng, 12)
        if rng.random() < 0.5:
            values = np.round(values, 1)  # many equal strengths and equal energies: ties go to the lower note
        types = [ALL_TYPES[int(i)] for i in rng.choice(len(ALL_TYPES), int(rng.integers(1, 6)), replace=False)]
        note_count = [None, 12, 20, 40, 84][int(rng.integers(0, 5))]
        threshold = [None, 0, 1, 3, 10, 7.5][int(rng.integers(0, 6))]
        assert_limited_like_the_oracle(values, types, note_count, threshold)


def test_the_limits_do_not_change_the_callers_array():
    values = random_windows(np.random.default_rng(10))
    before = values.copy()
    measure_chords(values, [(4,), (4, 7)], note_count=12, threshold=10)
    np.testing.assert_array_equal(values, before)


@pytest.mark.parametrize("bad", [11, 85, 0, -12, 20.5, True, "20", float("nan")])
def test_a_number_of_notes_the_picture_would_refuse_is_refused_with_its_message(bad):
    with pytest.raises(ValueError) as error:
        measure_chords(windows([C4, E4]), [(4,)], note_count=bad)
    assert str(error.value) == "The number of notes must be a whole number from 12 to 84."


@pytest.mark.parametrize("bad", [-1, 11, 10.5, float("nan"), float("inf"), True, "5"])
def test_a_threshold_the_picture_would_refuse_is_refused_with_its_message(bad):
    with pytest.raises(ValueError) as error:
        measure_chords(windows([C4, E4]), [(4,)], threshold=bad)
    assert str(error.value) == "The threshold must be a number from 0 to 10."


def test_the_limits_are_checked_before_any_window_is_measured_and_after_the_chord_types():
    with pytest.raises(ValueError, match="chord types"):
        measure_chords(windows([C4, E4]), [], note_count=5)
    with pytest.raises(ValueError, match="number of notes"):
        measure_chords(np.zeros((3, 5)), [(4,)], note_count=5)  # the bad limit is reported before the bad shape


def test_a_bad_threshold_is_reported_before_a_bad_array_shape():
    with pytest.raises(ValueError, match="threshold"):
        measure_chords(np.zeros((3, 5)), [(4,)], threshold=11)


# ---- User Story 4: parameters and the odd cases ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("bad, message", [([], LIST_MESSAGE), ([(7, 4)], TYPE_MESSAGE(repr((7, 4)))), ([(4,), (4,)], "The chord type (4,) is given more than once.")])
def test_bad_chord_types_are_refused_first_before_the_values_are_even_looked_at(bad, message):
    with pytest.raises(ValueError) as error:
        measure_chords(np.zeros((3, 5)), bad)  # the array is wrong too
    assert str(error.value) == message


@pytest.mark.parametrize(
    "values, message",
    [
        (np.zeros(88), "Each window needs at least 84 note values (got shape (88,))."),
        (np.zeros((3, 83)), "Each window needs at least 84 note values (got shape (3, 83))."),
        (np.zeros((2, 3, 88)), "Each window needs at least 84 note values (got shape (2, 3, 88))."),
        (np.full((2, 88), np.nan), "The note values must be finite numbers that are not negative."),
        (np.full((2, 88), np.inf), "The note values must be finite numbers that are not negative."),
        (np.full((2, 88), -0.5), "The note values must be finite numbers that are not negative."),
        ([["a"] * 88], "The note values must be finite numbers that are not negative."),
        (None, "Each window needs at least 84 note values (got shape ())."),
    ],
)
def test_wrong_note_values_are_refused_with_a_message_naming_the_problem(values, message):
    with pytest.raises(ValueError) as error:
        measure_chords(values, [(4,)])
    assert str(error.value) == message


def test_arrays_of_84_or_88_columns_and_integers_or_lists_are_accepted():
    row = windows([C3, E4])
    expected = ChordRecord((4,), 0, (C3, E4))
    assert measure_chords(row[:, :84], [(4,)]).record(0) == expected
    assert measure_chords(row, [(4,)]).record(0) == expected
    assert measure_chords((row * 100).astype(np.int64), [(4,)]).record(0) == expected
    assert measure_chords(row.tolist(), [(4,)]).record(0) == expected
    assert measure_chords(row.astype(np.float32), [(4,)]).record(0) == expected


def test_a_window_whose_letters_match_nothing_has_no_chord():
    assert only([33, 34, 35], [(4,)]) is None  # three neighbouring steps: no third in them
    assert only([C4, 34, 41], [(4,)]) is None  # C, G and D: 7, 2 and 5 steps apart, no third (4 or 8 steps)


def test_fewer_allowed_notes_than_a_chord_type_needs_means_no_chord_for_that_type_in_that_window():
    chosen = list(range(40, 52))
    values = windows(*heavy(chosen), {40: 0.5, 44: 0.4, 47: 0.3, C4: 1.0, E4: 0.9, G4: 0.8, 37: 0.7})
    target = 20
    # without the limit the four loudest are C E G Bb: a seventh chord (4, 7, 10)
    assert measure_chords(values, [(4, 7, 10)]).record(target) == ChordRecord((4, 7, 10), 0, (C4 + 0, E4, G4, 37))
    # with twelve notes allowed only three of them sound: the four-note type finds no chord, and the three-note type finds the faint triad
    assert measure_chords(values, [(4, 7, 10)], note_count=12).record(target) is None
    assert measure_chords(values, [(4, 7, 10), (4, 7)], note_count=12).record(target) == ChordRecord((4, 7), 0, (40, 44, 47))


def test_all_231_chord_types_can_be_asked_for_at_once():
    values = windows(*[row_of(np.random.default_rng(i), play(np.random.default_rng(i), ALL_TYPES[i], 0)) for i in range(0, 231, 7)])
    series = measure_chords(values, ALL_TYPES)
    assert series.window_count == len(range(0, 231, 7))
    assert_like_the_oracle(values, ALL_TYPES)


def test_a_list_given_as_a_tuple_or_a_generator_works_the_same_as_a_list():
    values = windows([C3, E4], [C4, E4, G4])
    expected = measure_chords(values, [(4,), (4, 7)])
    assert measure_chords(values, ((4,), (4, 7))) == expected
    assert measure_chords(values, (t for t in [(4,), (4, 7)])) == expected
    assert measure_chords(values, [[4], [4, 7]]) == expected
