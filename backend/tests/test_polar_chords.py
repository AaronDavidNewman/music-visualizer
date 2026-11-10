"""The bars of the ``polar-chords`` picture: the setting, the notes, the chord and its place, the lengths (feature 032)."""

import itertools
import math

import numpy as np
import pytest

from app.services.image_types import IMAGE_TYPES
from app.services.note_layout import MIDDLE_C_CELL, MIDDLE_C_NOTE, note_order
from app.services.polar_chords import (
    ARCS,
    CHORD_ARCS,
    CHORD_ROOTS,
    DEFAULT_POLAR_NOTES,
    MAX_POLAR_NOTES,
    MIN_POLAR_NOTES,
    POLAR_CHORD_TYPES,
    chord_place,
    chord_root,
    check_polar_notes,
    follow_arcs,
    note_targets,
    polar_bars,
)

from .test_chords import oracle_window  # the independent calculation of which chord is recorded, written for feature 031

NOTES_MESSAGE = "The number of notes shown must be a whole number from 5 to 8."
A1, C3, C4, E4, F4, G4, C5 = 0, 15, 27, 31, 32, 34, 39  # note numbers: 0 is A1 (55 Hz), one step apart


def frames(*rows, columns=88) -> np.ndarray:
    """A ``(F, columns)`` array of zeros with, for each row, ``{note: strength}`` or a list of notes (strengths 1.0, 0.9, 0.8, ... in the order given)."""
    values = np.zeros((len(rows), columns))
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            row = {note: 1.0 - 0.1 * j for j, note in enumerate(row)}
        for note, strength in row.items():
            values[i, note] = strength
    return values


# ---- the setting ----------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("value, expected", [(5, 5), (6, 6), (7, 7), (8, 8), (5.0, 5), (np.int64(6), 6), (np.float64(8.0), 8)])
def test_the_number_of_notes_shown_is_a_whole_number_from_5_to_8(value, expected):
    result = check_polar_notes(value)
    assert result == expected and type(result) is int


@pytest.mark.parametrize("value", [4, 9, 0, -5, 6.5, True, False, "6", None, float("nan"), float("inf"), [6], 100])
def test_anything_else_is_refused_with_the_message(value):
    with pytest.raises(ValueError) as error:
        check_polar_notes(value)
    assert str(error.value) == NOTES_MESSAGE


def test_the_constants():
    assert (MIN_POLAR_NOTES, MAX_POLAR_NOTES, DEFAULT_POLAR_NOTES, ARCS, CHORD_ROOTS, CHORD_ARCS) == (5, 8, 5, 84, 12, 84)
    assert POLAR_CHORD_TYPES == ((7,), (4, 7), (3, 7), (4, 10), (4, 11), (3, 7, 10), (4, 6))
    assert len(POLAR_CHORD_TYPES) * CHORD_ROOTS == CHORD_ARCS  # one arc for each chord type on each of the 12 letters


def test_polar_chords_is_the_ninth_image_type():
    assert IMAGE_TYPES[8] == "polar-chords" and len(IMAGE_TYPES) == 11  # Energy Graphs (feature 034) and Chromatic Decay (feature 035) follow
    assert IMAGE_TYPES[7] == "decay-exp"


# ---- the bars of the notes ---------------------------------------------------------------------------------------------------------------


def test_the_loudest_notes_get_the_bars_loudest_first_with_their_strength_shares():
    values = frames({10: 0.5, 20: 1.0, 30: 0.8, 40: 0.2, 50: 0.1, 60: 0.05, 70: 0.3})
    bars = polar_bars(values, None, 5)
    assert bars.note_slots.tolist() == [[20, 30, 10, 70, 40]]
    np.testing.assert_allclose(bars.note_shares[0], np.sqrt([1.0, 0.8, 0.5, 0.3, 0.2]), rtol=1e-12)


@pytest.mark.parametrize("count", [5, 6, 7, 8])
def test_the_number_of_bars_is_the_number_of_notes_shown(count):
    values = frames({n: 1.0 - 0.01 * n for n in range(0, 40, 3)})  # 14 sounding notes
    bars = polar_bars(values, None, count)
    assert bars.note_slots.shape == (1, count) and bars.note_shares.shape == (1, count)
    assert bars.note_slots[0].tolist() == list(range(0, 3 * count, 3))  # the loudest are the lowest here
    assert (bars.note_slots >= 0).all()


def test_with_fewer_sounding_notes_the_other_places_are_minus_one_and_have_no_share():
    bars = polar_bars(frames([10, 20, 30]), None, 5)
    assert bars.note_slots[0].tolist() == [10, 20, 30, -1, -1]
    assert bars.note_shares[0, 3:].tolist() == [0.0, 0.0]
    assert (bars.note_shares[0, :3] > 0).all()


def test_a_note_with_no_strength_never_has_a_bar():
    bars = polar_bars(frames({10: 1.0, 20: 0.0, 30: 0.0}), None, 5)
    assert bars.note_slots[0].tolist() == [10, -1, -1, -1, -1]


def test_equal_strengths_go_to_the_lower_note():
    row = {10: 1.0, 14: 1.0, 30: 1.0, 50: 1.0, 70: 1.0, 80: 1.0}  # six equal notes, five bars
    assert polar_bars(frames(row), None, 5).note_slots[0].tolist() == [10, 14, 30, 50, 70]


def test_the_four_notes_above_the_84_piano_notes_never_have_a_bar_but_they_set_the_scale():
    bars = polar_bars(frames({10: 1.0, 85: 4.0, 86: 3.0}), None, 5)
    assert bars.note_slots[0].tolist() == [10, -1, -1, -1, -1]
    assert bars.note_shares[0, 0] == pytest.approx(0.5)  # sqrt(1 / 4): the peak is the largest value of the whole array


def test_the_share_is_the_square_root_of_the_strength_over_the_largest_value_of_the_file():
    values = frames({10: 0.04}, {20: 1.0})
    bars = polar_bars(values, None, 5)
    assert bars.note_shares[0, 0] == pytest.approx(0.2) and bars.note_shares[1, 0] == pytest.approx(1.0)


def test_a_silent_file_has_no_bars_and_no_division_by_zero():
    bars = polar_bars(frames({}, {}), None, 5)
    assert (bars.note_slots == -1).all() and (bars.note_shares == 0).all() and np.isfinite(bars.note_shares).all()


def test_the_length_is_half_the_radius_at_the_bottom_of_the_peak_and_all_of_it_at_the_top():
    values = frames([10], [10], [10], [10])
    assert polar_bars(values, None, 5).length.tolist() == [0.5, 0.5, 0.5, 0.5]
    np.testing.assert_allclose(polar_bars(values, [0.0, 0.25, 0.5, 1.0], 5).length, [0.5, 0.625, 0.75, 1.0], rtol=1e-12)


def test_every_frame_has_one_length_so_all_bars_of_a_frame_are_equally_long():
    bars = polar_bars(frames([10, 20, 30]), [0.4], 5)
    assert bars.length.shape == (1,) and bars.length[0] == pytest.approx(0.7)


@pytest.mark.parametrize("beat", [[0.5], [0.5, 0.5, 0.5], [[0.5, 0.5]], [1.5, 0.5], [-0.1, 0.5], [float("nan"), 0.5], "ab"])
def test_a_bad_beat_is_refused_with_the_message_of_the_beat(beat):
    with pytest.raises(ValueError, match="The beat must be one number from 0 to 1 for each of the 2 frames."):
        polar_bars(frames([10], [20]), beat, 5)


@pytest.mark.parametrize("count", [4, 9, 0, True, 6.5, "6", None])
def test_a_number_of_notes_shown_outside_5_to_8_is_refused(count):
    with pytest.raises(ValueError) as error:
        polar_bars(frames([10]), None, count)
    assert str(error.value) == NOTES_MESSAGE


def test_the_shapes_and_types_of_the_bars():
    bars = polar_bars(frames([10, 20], [30], {}), [0.0, 0.5, 1.0], 6)
    assert bars.frame_count == 3
    assert bars.note_slots.dtype == np.int16 and bars.note_slots.shape == (3, 6)
    assert bars.note_shares.dtype == np.float64 and bars.note_shares.shape == (3, 6)
    assert bars.chord_place.dtype == np.int16 and bars.chord_place.shape == (3,)
    assert bars.chord_share.dtype == np.float64 and bars.chord_share.shape == (3,)
    assert bars.length.dtype == np.float64 and bars.length.shape == (3,)


def test_the_input_is_not_changed_and_two_runs_give_the_same_bars():
    values = frames([10, 20, 30, 40, 50, 60], [12, 16, 19])
    before = values.copy()
    one = polar_bars(values, [0.2, 0.9], 5)
    two = polar_bars(values, [0.2, 0.9], 5)
    np.testing.assert_array_equal(values, before)
    for name in ("note_slots", "note_shares", "chord_place", "chord_share", "length"):
        np.testing.assert_array_equal(getattr(one, name), getattr(two, name))
    assert not np.shares_memory(one.note_shares, values)


def test_84_and_88_columns_both_work_and_a_frame_does_not_depend_on_its_neighbours():
    short = frames([10, 20, 30], columns=84)
    assert polar_bars(short, None, 5).note_slots[0].tolist() == [10, 20, 30, -1, -1]
    both = frames([10, 20, 30], [40, 50])
    alone = note_targets(both[1:], 5)[0]
    together = note_targets(both, 5)[0]
    assert together[1].tolist() == alone[0].tolist()  # the notes (their arcs) of a frame; where the bars are in the picture also depends on the frames before


# ---- the chord: its root, its place, its bar --------------------------------------------------------------------------------------------

def play(rng, chord_type, root, inversion):
    """The notes of the chord type on the root letter, with chord tone ``inversion`` in the bass and the others in random octaves above it (0..83)."""
    tones = [(root + c) % 12 for c in (0, *chord_type)]
    bass_letter = tones[inversion]
    bass = bass_letter + 12 * int(rng.integers(0, 3))
    notes = [bass] + [bass + (tone - bass_letter) % 12 + 12 * int(rng.integers(0, 3)) for j, tone in enumerate(tones) if j != inversion]
    assert max(notes) < 84
    rng.shuffle(notes)
    return notes


def loud(rng, notes):
    """A row with the notes sounding at different strengths."""
    strengths = 0.5 + 0.1 * rng.permutation(len(notes))
    return {note: float(strengths[i]) for i, note in enumerate(notes)}


def chord_window(rng, chord_type, root, inversion):
    return frames(loud(rng, play(rng, chord_type, root, inversion)))


def oracle_root(chord_type, inversion, notes):
    """The letter (A is 0, one step per letter) that a chord is built on: the one whose chord tones are the letters of the notes, with the lowest note
    on the chord tone of the inversion."""
    chord = (0, *chord_type)
    letters = {note % 12 for note in notes}
    found = [r for r in range(12) if {(r + c) % 12 for c in chord} == letters and (r + chord[inversion]) % 12 == notes[0] % 12]
    assert len(found) == 1
    return found[0]


def test_the_place_of_a_chord_is_its_letter_times_7_plus_the_index_of_its_type_letter_after_letter():
    assert [chord_place(t, 0) for t in POLAR_CHORD_TYPES] == [0, 1, 2, 3, 4, 5, 6]  # letter 1 (A): its 7 types
    assert [chord_place(t, 1) for t in POLAR_CHORD_TYPES] == [7, 8, 9, 10, 11, 12, 13]  # then letter 2 (A#): its 7 types
    assert chord_place((4, 7), 3) == 22 and chord_place((4, 6), 11) == 83
    assert sorted(chord_place(t, r) for r in range(12) for t in POLAR_CHORD_TYPES) == list(range(CHORD_ARCS))  # every one of the 84 places, once


def test_a_chord_type_that_is_not_one_of_the_seven_or_a_root_that_is_not_a_letter_has_no_place():
    for bad in ((4,), (5, 7), (4, 7, 10), (3, 7, 11)):
        with pytest.raises(ValueError):
            chord_place(bad, 0)
    for bad in (-1, 12, 1.5, True, "3", None):
        with pytest.raises(ValueError):
            chord_place((4, 7), bad)


def test_the_root_of_a_chord_is_the_letter_of_its_lowest_note_less_the_chord_tone_that_is_in_the_bass():
    assert chord_root((4, 7), 0, C4) == 3  # C major with C in the bass: C is the letter 3 (A is 0)
    assert chord_root((4, 7), 1, E4) == 3  # with E in the bass, E being the chord tone 4 above C
    assert chord_root((4, 7), 2, G4) == 3
    assert chord_root((7,), 1, C4) == 8  # a fourth, C in the bass and F above it, is the fifth of F (7 steps below C is F, the letter 8)
    assert chord_root((3, 7, 10), 0, A1) == 0  # A minor seventh on A
    for bad in (-1, 3, 1.5, True):  # (4, 7) has the inversions 0 to 2
        with pytest.raises(ValueError):
            chord_root((4, 7), bad, C4)


def test_every_type_on_every_root_in_every_inversion_has_its_bar_in_the_place_of_its_root_and_type_and_no_other():
    rng = np.random.default_rng(12)
    for chord_type in POLAR_CHORD_TYPES:
        for root in range(12):
            for inversion in range(len(chord_type) + 1):
                for count in (5, 8):
                    values = chord_window(rng, chord_type, root, inversion)
                    bars = polar_bars(values, None, count)
                    expected = oracle_window(values[0, :84], POLAR_CHORD_TYPES)  # the type that the rules of feature 031 record
                    place = oracle_root(expected[0], expected[1], expected[2]) * 7 + POLAR_CHORD_TYPES.index(expected[0])
                    assert bars.chord_place.tolist() == [place], (chord_type, root, inversion)
                    assert place == root * 7 + POLAR_CHORD_TYPES.index(chord_type), (chord_type, root, inversion)  # and it is the chord that was played
                    assert bars.chord_place.dtype == np.int16 and 0 <= bars.chord_place[0] < CHORD_ARCS


def test_the_inversion_and_the_octaves_do_not_change_the_place_but_the_root_and_the_type_do():
    rng = np.random.default_rng(13)
    seen = {}
    for chord_type in ((4, 7), (3, 7), (3, 7, 10)):
        for root in range(12):
            places = {int(polar_bars(chord_window(rng, chord_type, root, k), None, 5).chord_place[0]) for k in range(len(chord_type) + 1) for _ in range(3)}
            assert places == {root * 7 + POLAR_CHORD_TYPES.index(chord_type)}, (chord_type, root)
            seen[chord_type, root] = places.pop()
    assert len(set(seen.values())) == len(seen)  # a different root or type is a different place


def test_the_worked_examples_of_the_places():
    major_c = polar_bars(frames([C4, E4, G4], [E4, G4, C5], [G4, C5, 43]), None, 5)
    assert major_c.chord_place.tolist() == [22, 22, 22]  # (4, 7) on C: letter 3, type 1; whatever the voicing
    assert polar_bars(frames([E4, 35, 38]), None, 5).chord_place.tolist() == [50]  # E major: letter 7, type 1
    assert polar_bars(frames([C4, G4]), None, 5).chord_place.tolist() == [21]  # (7) on C: letter 3, type 0
    assert polar_bars(frames([C4, F4]), None, 5).chord_place.tolist() == [56]  # a fourth is an inverted fifth, of F: letter 8, type 0
    assert polar_bars(frames([0, 7]), None, 5).chord_place.tolist() == [0]  # A and E: the very first place
    assert polar_bars(frames([12, 15, 19]), None, 5).chord_place.tolist() == [2]  # A C E: (3, 7) on A, a minor triad


def test_the_longest_type_wins_in_the_picture_too_a_seventh_chord_is_not_its_triad():
    # A C E G: A minor seventh (3, 7, 10); its three loudest notes alone would be the triad (3, 7)
    bars = polar_bars(frames([12, 15, 19, 22]), None, 5)  # A2 C3 E3 G3 with strengths 1.0, 0.9, 0.8, 0.7
    assert bars.chord_place.tolist() == [5]  # on A: letter 0, type 5


def test_a_faint_extra_note_does_not_turn_a_triad_into_a_seventh_chord_but_one_at_the_noise_floor_does():
    # A C E (3, 7) with a G: A minor seventh (3, 7, 10) if the G counts. The loudest value is 1.0, so the noise floor (-60 dB) is 0.001
    assert polar_bars(frames({12: 1.0, 15: 0.9, 19: 0.8, 22: 0.0009}), None, 5).chord_place.tolist() == [2]  # the triad, on A
    assert polar_bars(frames({12: 1.0, 15: 0.9, 19: 0.8, 22: 0.001}), None, 5).chord_place.tolist() == [5]  # exactly at the floor: the seventh chord


@pytest.mark.parametrize("row", [[C4, C4 + 1], [C4, C4 + 3, C4 + 6], [C4, C4 + 6], [C4, C4 + 2], [C4], []])
def test_a_frame_whose_loudest_notes_form_none_of_the_seven_has_no_chord_bar(row):
    bars = polar_bars(frames(row), None, 5)
    assert bars.chord_place.tolist() == [-1] and bars.chord_share.tolist() == [0.0]


def test_the_strength_share_of_the_chord_is_the_square_root_of_the_average_of_its_notes_over_the_peak():
    bars = polar_bars(frames({C4: 1.0, E4: 0.9, G4: 0.5}), None, 5)
    assert bars.chord_share[0] == pytest.approx(math.sqrt((1.0 + 0.9 + 0.5) / 3 / 1.0))
    quiet = polar_bars(frames({C4: 0.2, E4: 0.2, G4: 0.2}, {40: 1.0}), None, 5)
    assert quiet.chord_share[0] == pytest.approx(math.sqrt(0.2))
    assert quiet.chord_share[1] == 0.0


def test_when_a_frame_holds_only_the_notes_of_a_chord_every_one_of_them_has_its_note_bar():
    rng = np.random.default_rng(14)
    for _ in range(60):
        t = POLAR_CHORD_TYPES[int(rng.integers(0, 7))]
        values = chord_window(rng, t, int(rng.integers(0, 12)), int(rng.integers(0, len(t) + 1)))
        bars = polar_bars(values, None, 5)
        sounding = set(np.flatnonzero(values[0, :84]).tolist())
        assert bars.chord_place[0] >= 0 and sounding <= set(bars.note_slots[0].tolist())


def test_the_chord_is_looked_for_without_any_limit_on_all_84_notes():
    # the chord notes are the loudest; a note count of the pictures would have no effect here because nothing of the kind is given
    values = frames({0: 1.0, 80: 0.9})  # A1 and a note 80 steps up: an interval of 8 (not one of the seven)
    assert polar_bars(values, None, 5).chord_place.tolist() == [-1]
    assert polar_bars(frames({0: 1.0, 83: 0.9}), None, 5).chord_place.tolist() == [-1]  # 83 steps = 11 mod 12
    assert polar_bars(frames({0: 1.0, 7 + 12 * 6: 0.9}), None, 5).chord_place.tolist() == [0]  # A1 and E7: a fifth, (7) on A


def test_the_chords_of_a_file_are_independent_of_the_frames_around_them():
    rng = np.random.default_rng(15)
    rows = [chord_window(rng, POLAR_CHORD_TYPES[i % 7], i % 12, 0)[0] for i in range(10)]
    together = polar_bars(np.array(rows), None, 5).chord_place.tolist()
    alone = [int(polar_bars(np.array([row]), None, 5).chord_place[0]) for row in rows]
    assert together == alone


def test_a_faint_chord_is_still_found_when_the_file_has_a_much_louder_note_elsewhere():
    # the image type has no threshold: 3 percent of the loudest value of the file is enough for a chord
    values = frames({40: 1.0}, {C4: 0.03, E4: 0.028, G4: 0.026})
    bars = polar_bars(values, None, 5)
    assert bars.chord_place.tolist() == [-1, 22]
    assert bars.chord_share[1] == pytest.approx(math.sqrt(0.028))


# ---- the note layout: rows or spiral (revision of feature 032) ---------------------------------------------------------------------------------


def arc_of(note, layout):
    """The arc of a note: the cell the layout draws it in (an independent calculation from the order of the cells)."""
    return int(np.flatnonzero(note_order(layout) == note)[0])


def test_with_the_rows_layout_the_arc_of_a_note_is_its_number_as_it_always_was():
    values = frames([10, 20, 30], [5], [83])
    assert note_targets(values, 5, "rows")[0].tolist() == note_targets(values, 5)[0].tolist()
    assert note_targets(values, 5)[0].tolist() == [[10, 20, 30, -1, -1], [5, -1, -1, -1, -1], [83, -1, -1, -1, -1]]


def test_with_the_spiral_layout_the_arc_of_a_note_is_the_cell_in_which_the_spiral_draws_it():
    cell = MIDDLE_C_CELL[0] * 12 + MIDDLE_C_CELL[1]
    assert cell == 29  # row 3, column 6 (counted from 1)
    assert polar_bars(frames([MIDDLE_C_NOTE]), None, 5, note_layout="spiral").note_slots[0, 0] == 29
    assert polar_bars(frames([MIDDLE_C_NOTE]), None, 5, note_layout="rows").note_slots[0, 0] == 27
    # the next note up is in the cell to the right of middle C, the next note down in the cell to its left
    assert polar_bars(frames([MIDDLE_C_NOTE + 1]), None, 5, note_layout="spiral").note_slots[0, 0] == 30
    assert polar_bars(frames([MIDDLE_C_NOTE - 1]), None, 5, note_layout="spiral").note_slots[0, 0] == 28


@pytest.mark.parametrize("layout", ["rows", "spiral"])
def test_every_note_has_the_arc_of_its_cell_and_the_84_arcs_are_all_different(layout):
    arcs = []
    for note in range(84):
        bars = polar_bars(frames({note: 1.0}), None, 5, note_layout=layout)
        assert bars.note_slots[0, 0] == arc_of(note, layout)
        arcs.append(int(bars.note_slots[0, 0]))
    assert sorted(arcs) == list(range(84))


def test_the_notes_that_get_a_bar_are_the_same_in_both_layouts_only_their_arcs_differ():
    rng = np.random.default_rng(21)
    for _ in range(30):
        values = rng.random((6, 88)) ** 3
        rows, rows_shares = note_targets(values, 6, "rows")
        spiral, spiral_shares = note_targets(values, 6, "spiral")
        np.testing.assert_array_equal(rows_shares, spiral_shares)  # the loudest notes, in the same order, with the same strengths
        order = note_order("spiral")
        assert (order[spiral] == rows).all()  # the note drawn in an arc of the spiral is the note of the rows layout
        assert not (rows == spiral).all()


def test_ties_still_go_to_the_lower_note_not_the_lower_arc():
    row = {10: 1.0, 14: 1.0, 30: 1.0, 50: 1.0, 70: 1.0, 80: 1.0}  # six equal notes, five bars
    spiral = polar_bars(frames(row), None, 5, note_layout="spiral")
    assert spiral.note_slots[0].tolist() == [arc_of(n, "spiral") for n in (10, 14, 30, 50, 70)]  # one frame: the bars are in the arcs of their notes
    assert arc_of(80, "spiral") not in spiral.note_slots[0].tolist()


def test_the_chord_the_lengths_and_the_shares_do_not_depend_on_the_layout():
    rng = np.random.default_rng(22)
    for _ in range(30):
        values = rng.random((8, 88)) ** 3
        values[rng.random(values.shape) < 0.4] = 0.0
        beat = rng.random(8)
        rows = polar_bars(values, beat, 5, note_layout="rows")
        spiral = polar_bars(values, beat, 5, note_layout="spiral")
        for name in ("chord_place", "chord_share", "length"):
            np.testing.assert_array_equal(getattr(rows, name), getattr(spiral, name), err_msg=name)
        np.testing.assert_array_equal(note_targets(values, 5, "rows")[1], note_targets(values, 5, "spiral")[1])  # and the strengths of the notes
    # a major triad on C is the chord at place 22 whatever the layout: it is about the real notes
    for layout in ("rows", "spiral"):
        assert polar_bars(frames([C4, E4, G4]), None, 5, note_layout=layout).chord_place.tolist() == [22]


def test_a_layout_that_is_not_offered_is_refused():
    for bad in ("Spiral", "ROWS", " rows", "", "circle", None, 1):
        with pytest.raises(ValueError, match="The note layout must be one of rows, spiral."):
            polar_bars(frames([10]), None, 5, note_layout=bad)


# ---- the bars follow their notes: one arc a frame (revision of feature 032) -----------------------------------------------------------------


def targets_of(*columns):
    """A ``(frames, ranks)`` array of target arcs from one list of arcs per rank."""
    return np.array(columns, dtype=np.int16).T


def test_the_first_frame_is_in_the_arcs_of_the_notes():
    targets = targets_of([10, 10], [40, 40], [83, 83])
    assert follow_arcs(targets)[0].tolist() == [10, 40, 83]


def test_a_bar_whose_note_changes_moves_one_arc_a_frame_toward_it_clockwise_when_that_is_shorter():
    positions = follow_arcs(targets_of([10, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20]))
    assert positions[:, 0].tolist() == [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 20, 20]  # 10 arcs in 10 frames, then it stays


def test_and_counterclockwise_when_that_is_shorter():
    positions = follow_arcs(targets_of([20, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]))
    assert positions[:, 0].tolist() == [20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 10]


def test_a_bar_goes_round_the_top_of_the_circle_by_the_shorter_way():
    assert follow_arcs(targets_of([1, 83, 83, 83]))[:, 0].tolist() == [1, 0, 83, 83]  # 1, 0, 83: not all the way round the other side
    assert follow_arcs(targets_of([83, 1, 1, 1]))[:, 0].tolist() == [83, 0, 1, 1]
    assert follow_arcs(targets_of([80, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]))[:, 0].tolist() == [80, 81, 82, 83, 0, 1, 2, 3, 4, 5, 5, 5]


def test_a_note_exactly_on_the_other_side_of_the_circle_is_reached_clockwise():
    positions = follow_arcs(targets_of([0] + [42] * 44))[:, 0]
    assert positions[1] == 1 and positions[42] == 42 and positions[-1] == 42  # 42 steps, all clockwise


def test_a_bar_never_moves_more_than_one_arc_a_frame_however_far_the_note_is():
    rng = np.random.default_rng(31)
    targets = rng.integers(0, 84, (200, 3)).astype(np.int16)
    positions = follow_arcs(targets)
    step = (positions[1:].astype(int) - positions[:-1] + 42) % 84 - 42  # the signed distance round the circle
    assert (np.abs(step) <= 1).all()
    assert positions.min() >= 0 and positions.max() <= 83 and positions.dtype == np.int16 and positions.shape == targets.shape


def test_a_bar_that_has_reached_its_note_stays_and_follows_it_when_it_moves_by_one_arc():
    positions = follow_arcs(targets_of([30, 30, 30, 31, 32, 31, 31]))
    assert positions[:, 0].tolist() == [30, 30, 30, 31, 32, 31, 31]


def test_each_rank_follows_its_own_note_independently_of_the_others():
    both = follow_arcs(targets_of([10, 20, 20, 20], [50, 40, 40, 40]))
    assert both[:, 0].tolist() == follow_arcs(targets_of([10, 20, 20, 20]))[:, 0].tolist()
    assert both[:, 1].tolist() == follow_arcs(targets_of([50, 40, 40, 40]))[:, 0].tolist()


def test_a_rank_without_a_note_loses_its_place_and_comes_back_in_the_arc_of_its_note():
    positions = follow_arcs(targets_of([10, -1, -1, 60, 60, 60]))
    assert positions[:, 0].tolist() == [10, -1, -1, 60, 60, 60]  # it does not slide in from where it was


def test_the_targets_are_not_changed():
    targets = targets_of([10, 20, 30, 40])
    before = targets.copy()
    follow_arcs(targets)
    np.testing.assert_array_equal(targets, before)


def test_bad_targets_are_refused():
    for bad in (np.zeros(5), np.full((3, 2), 84), np.full((3, 2), -2), np.array([[1.5, 2.0]])):
        with pytest.raises(ValueError):
            follow_arcs(bad)


def test_in_the_picture_the_first_frame_is_the_notes_and_the_next_frames_move_a_bar_one_arc_toward_a_new_note():
    rows = [{10: 1.0}] + [{20: 1.0}] * 12
    bars = polar_bars(frames(*rows), None, 5)
    assert bars.note_slots[:, 0].tolist() == [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 20, 20]
    assert (bars.note_slots[:, 1:] == -1).all()
    assert bars.note_shares[0, 0] > 0 and bars.note_shares[5, 0] == bars.note_shares[12, 0] == 1.0  # the color and the strength are the new note's at once


def test_in_the_picture_a_steady_note_does_not_move():
    bars = polar_bars(frames(*([{36: 1.0}] * 20)), None, 5)
    assert set(bars.note_slots[:, 0].tolist()) == {36}


def test_the_bar_of_the_second_loudest_note_is_tracked_apart_from_the_loudest():
    rows = [{10: 1.0, 50: 0.5}] + [{12: 1.0, 40: 0.5}] * 12
    bars = polar_bars(frames(*rows), None, 5)
    assert bars.note_slots[:, 0].tolist() == [10, 11, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12]
    assert bars.note_slots[:, 1].tolist() == [50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 40, 40]


def test_two_bars_on_the_same_arc_show_only_the_louder_one():
    rows = [{10: 1.0, 12: 0.5}, {14: 1.0, 12: 0.5}, {14: 1.0, 12: 0.5}, {14: 1.0, 12: 0.5}, {14: 1.0, 12: 0.5}]
    bars = polar_bars(frames(*rows), None, 5)
    # the loudest bar goes 10, 11, 12, 13, 14; the second stays at 12; in the frame in which both are at 12 only the louder is drawn
    assert bars.note_slots[:, 0].tolist() == [10, 11, 12, 13, 14]
    assert bars.note_slots[:, 1].tolist() == [12, 12, -1, 12, 12]
    assert bars.note_shares[2, 1] == 0.0 and bars.note_shares[1, 1] > 0


def test_the_arcs_of_the_bars_of_a_frame_are_always_different():
    rng = np.random.default_rng(32)
    for _ in range(20):
        values = rng.random((40, 88)) ** 3
        values[rng.random(values.shape) < 0.5] = 0.0
        bars = polar_bars(values, None, 8)
        for row in bars.note_slots:
            shown = row[row >= 0]
            assert len(shown) == len(set(shown.tolist()))


def test_in_the_picture_the_movement_is_in_the_arcs_of_the_note_layout():
    # middle C (27) is in arc 29 with the spiral and the next note up (28) in arc 30: the bar moves from arc 29 to arc 30, one arc
    rows = [{27: 1.0}, {28: 1.0}, {28: 1.0}]
    assert polar_bars(frames(*rows), None, 5, note_layout="spiral").note_slots[:, 0].tolist() == [29, 30, 30]
    # a jump in pitch that is far in the rows layout is a slide of arcs in whatever arcs the layout puts the notes
    spiral = polar_bars(frames({27: 1.0}, *([{70: 1.0}] * 60)), None, 5, note_layout="spiral").note_slots[:, 0]
    assert spiral[0] == 29 and spiral[-1] == arc_of(70, "spiral")
    assert (np.abs((spiral[1:].astype(int) - spiral[:-1] + 42) % 84 - 42) <= 1).all()


def test_the_chord_the_lengths_and_the_strengths_do_not_follow_anything():
    rows = [{C4: 1.0, E4: 0.9, G4: 0.8}, {40: 1.0, 44: 0.9, 47: 0.8}]
    bars = polar_bars(frames(*rows), [0.2, 0.9], 5)
    assert bars.chord_place.tolist() == [22, 29]  # the chord is where its root and type are, at once: (4, 7) on C, then (4, 7) on the letter 4
    np.testing.assert_allclose(bars.length, [0.6, 0.95])
    np.testing.assert_array_equal(bars.note_shares, note_targets(frames(*rows), 5)[1])
