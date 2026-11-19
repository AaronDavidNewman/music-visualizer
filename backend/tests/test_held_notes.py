"""The held-notes rule (feature 044): ``held_notes.hold_loudest`` and ``check_extra_notes``.

User Story 1: a note that is still among the loudest n + k keeps its place when louder notes start. User Story 2: a free place goes to the loudest note that is not held. The rule is also
checked against ``specs/044-sustained-loudest-notes/tools/reference_selection.py``, a plain-Python version written from the spec and not from the code.
"""

import importlib.util
import time
from pathlib import Path

import numpy as np
import pytest

from app.services.held_notes import DEFAULT_EXTRA_NOTES, MAX_EXTRA_NOTES, MIN_EXTRA_NOTES, check_extra_notes, hold_loudest

_REFERENCE = Path(__file__).resolve().parents[2] / "specs" / "044-sustained-loudest-notes" / "tools" / "reference_selection.py"
_spec = importlib.util.spec_from_file_location("reference_selection", _REFERENCE)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
reference_selection = _module.reference_selection

A, B, C, D, E, F, G, H, I = range(9)  # nine notes, named so that the scenarios read like the spec


def frames_of(*rows):
    """``(frames, 84)`` strengths from rows given as ``{note: strength}``."""
    values = np.zeros((len(rows), 84))
    for frame, row in enumerate(rows):
        for note, strength in row.items():
            values[frame, note] = strength
    return values


def sounding(order, values):
    """The notes of every frame whose place is a sounding note: ``list`` of ``list`` of note indices, in place order."""
    return [[int(n) for n in order[f] if values[f, n] > 0] for f in range(order.shape[0])]


# ---- User Story 1: a note that is still sounding keeps its place ------------------------------------------------------------------------------


def test_a_louder_newcomer_does_not_displace_a_note_that_is_still_among_the_loudest_n_plus_k():
    values = frames_of({A: 5, B: 4, C: 3, D: 2, E: 1}, {F: 9, A: 5, B: 4, C: 3, D: 2, E: 1})  # n = 5, k = 2: A..E are the 2nd to 6th of 6
    chosen = sounding(hold_loudest(values, 5, 2), values)
    assert chosen[0] == [A, B, C, D, E]
    assert chosen[1] == [A, B, C, D, E]  # F, the loudest, is not in it
    assert F not in chosen[1]


def test_a_note_below_n_plus_k_is_freed_and_the_loudest_note_that_is_not_held_takes_its_place():
    # frame 1: F loudest, G and H next, then A..D, and E is the 8th (n + k = 7)
    values = frames_of({A: 5, B: 4, C: 3, D: 2, E: 1}, {F: 9, G: 8.5, H: 8, A: 5, B: 4, C: 3, D: 2, E: 1})
    chosen = sounding(hold_loudest(values, 5, 2), values)
    assert chosen[1] == [F, A, B, C, D]  # E fell to the 8th: freed; F is the loudest note that is not held
    assert E not in chosen[1] and G not in chosen[1] and H not in chosen[1]


def test_a_note_at_exactly_rank_n_plus_k_is_still_held_and_one_rank_lower_it_is_not():
    # n = 5, k = 2: E is the 7th in frame 1 (held) and the 8th in frame 2 (freed)
    values = frames_of(
        {A: 5, B: 4, C: 3, D: 2, E: 1},
        {F: 9, G: 8, A: 5, B: 4, C: 3, D: 2, E: 1},  # E is the 7th loudest
        {F: 9, G: 8, H: 7.5, A: 5, B: 4, C: 3, D: 2, E: 1},  # E is the 8th
    )
    chosen = sounding(hold_loudest(values, 5, 2), values)
    assert E in chosen[1]
    assert chosen[2] == [F, A, B, C, D]  # E is freed; F is the loudest note that is not held (G and H wait: one place is free)


def test_the_first_frame_is_the_plain_n_loudest_and_so_is_a_frame_after_silence():
    values = frames_of({A: 5, B: 4, C: 3, D: 2, E: 1, F: 0.5}, {}, {F: 9, A: 5, B: 4, C: 3, D: 2, E: 1})
    chosen = sounding(hold_loudest(values, 5, 5), values)
    assert chosen[0] == [A, B, C, D, E]  # nothing held yet: F is the 6th, so it is out
    assert chosen[1] == []
    assert chosen[2] == [F, A, B, C, D]  # after the silent frame nothing is held: the plain 5 loudest


def test_a_held_note_whose_strength_falls_to_0_is_not_held_whatever_its_rank():
    values = frames_of({A: 5, B: 4, C: 3, D: 2, E: 1}, {A: 5, B: 4, C: 3, D: 2, E: 0})
    chosen = sounding(hold_loudest(values, 5, 5), values)
    assert chosen[1] == [A, B, C, D]  # E stopped: not held, and no other note sounds to take the place


def test_a_note_held_through_a_long_decay_keeps_its_place_as_long_as_it_stays_within_n_plus_k():
    # E fades from 1 to 0.1 while a new note starts louder in every frame; with k = 5 it is held while it is within the loudest 10
    rows = [{A: 9, B: 8, C: 7, D: 6, E: 5}]
    for step in range(1, 5):
        rows.append({A: 9, B: 8, C: 7, D: 6, E: 5 - step * 0.5, 20 + step: 10 + step})
        rows[-1].update({30 + step: 1.0 + step})  # a newcomer that is quieter than the faded E
    values = frames_of(*rows)
    chosen = sounding(hold_loudest(values, 5, 5), values)
    assert all(frame == [A, B, C, D, E] for frame in chosen)  # E is held through its whole decay; no newcomer, however loud, takes a place


# ---- k = 0 is the old behaviour ------------------------------------------------------------------------------------------------------------------


def old_selection(values, count):
    return np.argsort(-values, axis=1, kind="stable")[:, :count]


@pytest.mark.parametrize("count", [5, 6, 7, 8])
@pytest.mark.parametrize("columns", [84, 12])
def test_with_extra_0_the_result_is_exactly_the_old_argsort(count, columns):
    rng = np.random.default_rng(count * 100 + columns)
    values = rng.random((80, columns)) ** 3
    values[rng.random(values.shape) < 0.5] = 0.0  # zeros: fewer than count sound in some frames
    assert np.array_equal(hold_loudest(values, count, 0), old_selection(values, count))


@pytest.mark.parametrize("count", [5, 8])
def test_with_extra_0_ties_go_to_the_lower_note_as_before(count):
    rng = np.random.default_rng(7)
    values = np.round(rng.random((60, 84)) * 3) / 3  # four distinct values: many ties
    assert np.array_equal(hold_loudest(values, count, 0), old_selection(values, count))


def test_a_steady_chord_is_the_same_for_every_extra():
    values = np.tile(np.linspace(1.0, 0.1, 84), (20, 1))
    for count in (5, 8):
        base = hold_loudest(values, count, 0)
        for extra in range(1, count + 1):
            assert np.array_equal(hold_loudest(values, count, extra), base), (count, extra)


# ---- the reference --------------------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("count", [5, 6, 7, 8])
def test_the_rule_agrees_with_the_independent_reference_for_every_extra_on_84_notes(count):
    rng = np.random.default_rng(1000 + count)
    values = rng.random((60, 84)) ** 4
    values[rng.random(values.shape) < 0.6] = 0.0
    values[20] = 0.0  # a silent frame in the middle
    values = np.round(values, 2)  # ties
    for extra in range(0, count + 1):
        got = sounding(hold_loudest(values, count, extra), values)
        assert got == reference_selection(values.tolist(), count, extra), (count, extra)


@pytest.mark.parametrize("extra", range(0, 6))
def test_the_rule_agrees_with_the_independent_reference_on_12_letters(extra):
    rng = np.random.default_rng(2000 + extra)
    values = np.round(rng.random((120, 12)) ** 3, 2)
    values[rng.random(values.shape) < 0.3] = 0.0
    got = sounding(hold_loudest(values, 5, extra), values)
    assert got == reference_selection(values.tolist(), 5, extra)


# ---- User Story 2: a free place is taken by the loudest note that is not held --------------------------------------------------------------


def test_two_free_places_go_to_the_two_loudest_newcomers():
    # frame 0: A..E. Frame 1: D and E fall out of the loudest 5 + 1; F, G, H, I sound (F > G > H > I) and A, B, C are still loud
    values = frames_of(
        {A: 9, B: 8, C: 7, D: 6, E: 5},
        {A: 9, B: 8, C: 7, F: 4.5, G: 4, H: 3.5, I: 3, D: 0.4, E: 0.3},
    )
    chosen = sounding(hold_loudest(values, 5, 1), values)
    assert chosen[1] == [A, B, C, F, G]  # D and E are 8th and 9th; F and G take the two places and H does not


def test_fewer_notes_than_n_selects_only_those_and_pads_with_notes_of_strength_0():
    values = frames_of({A: 3, C: 2})
    order = hold_loudest(values, 5, 2)
    assert order.shape == (1, 5)
    assert sounding(order, values) == [[A, C]]
    assert list(order[0, :2]) == [A, C]
    assert all(values[0, n] == 0 for n in order[0, 2:])
    assert len(set(order[0].tolist())) == 5  # five different notes, none twice


def test_a_note_that_lost_its_place_and_sounds_again_is_a_newcomer_with_no_claim_from_before():
    # n = 2, k = 1: C starts loudest and holds the second place... A and B are held; F is louder than B
    values = frames_of(
        {A: 5, B: 4},
        {A: 5, C: 4.5, B: 4, D: 3},  # B is the 3rd = n + k: held
        {A: 5, C: 4.5, D: 4, B: 3},  # B is the 4th: freed (a place: C is a newcomer after the frame, and takes it)
        {A: 5, B: 4.8, C: 4.5, D: 4},  # B sounds again, the 2nd loudest, but C and A are held and B has no claim
    )
    chosen = sounding(hold_loudest(values, 2, 1), values)
    assert chosen[1] == [A, B]  # C is louder than B but B is held (3rd of n + k = 3)
    assert chosen[2] == [A, C]  # B is the 4th: freed; C, the loudest note that is not held, takes the place
    assert chosen[3] == [A, C]  # B sounds again as the 2nd loudest, but it is a newcomer and both places are held: it has to wait


def test_two_notes_of_equal_strength_compete_with_the_lower_note_winning():
    values = frames_of({C: 5, A: 5, B: 5})
    assert sounding(hold_loudest(values, 2, 1), values) == [[A, B]]
    # for the rank used for n + k: A and C are equal, so A is louder than C
    values = frames_of({A: 5}, {C: 6, B: 5.5, A: 5, D: 5, E: 5})
    chosen = sounding(hold_loudest(values, 1, 1), values)  # n + k = 2: A is the 3rd (after C and B)
    assert A not in chosen[1]


@pytest.mark.parametrize("count", [5, 6, 7, 8])
def test_properties_of_every_selection(count):
    rng = np.random.default_rng(3000 + count)
    values = np.round(rng.random((100, 84)) ** 4, 2)
    values[rng.random(values.shape) < 0.5] = 0.0
    for extra in range(0, count + 1):
        copy = values.copy()
        order = hold_loudest(values, count, extra)
        assert np.array_equal(values, copy)  # the input is not changed
        assert order.shape == (100, count) and order.dtype == np.intp
        for frame in range(100):
            row = values[frame]
            places = order[frame].tolist()
            assert len(set(places)) == count  # no note twice, even in the padding
            live = [n for n in places if row[n] > 0]
            assert places[: len(live)] == live  # the sounding notes come first
            assert len(live) <= count
            ranked = [(-row[n], n) for n in live]
            assert ranked == sorted(ranked)  # ordered by loudness, ties by the lower note
            assert all(row[n] == 0 for n in places[len(live) :])


@pytest.mark.parametrize("count", [5, 8])
def test_a_selection_has_exactly_the_notes_that_sound_up_to_n_whatever_k(count):
    rng = np.random.default_rng(4000 + count)
    values = np.round(rng.random((100, 84)) ** 4, 2)
    values[rng.random(values.shape) < 0.5] = 0.0
    for extra in range(0, count + 1):
        order = hold_loudest(values, count, extra)
        for frame in range(100):
            live = [n for n in order[frame] if values[frame, n] > 0]
            assert len(live) == min(count, int((values[frame] > 0).sum())), (extra, frame)  # SC-003: never more than n, and fewer only when fewer sound


def test_a_held_note_is_never_displaced_by_a_louder_note_that_is_not_held_while_it_is_within_n_plus_k():
    rng = np.random.default_rng(5)
    values = np.round(rng.random((200, 84)) ** 3, 3)
    count, extra = 5, 3
    order = hold_loudest(values, count, extra)
    for frame in range(1, 200):
        previous = {int(n) for n in order[frame - 1] if values[frame - 1, n] > 0}
        ranked = sorted(range(84), key=lambda n: (-values[frame, n], n))
        reach = {n for n in ranked[: count + extra] if values[frame, n] > 0}
        held = previous & reach
        assert held <= {int(n) for n in order[frame]}, frame  # every note that qualifies is still in the selection


# ---- the checks -----------------------------------------------------------------------------------------------------------------------------------


def test_the_constants_are_the_ones_of_the_spec():
    assert (MIN_EXTRA_NOTES, MAX_EXTRA_NOTES, DEFAULT_EXTRA_NOTES) == (1, 8, 2)


@pytest.mark.parametrize("value, limit", [(1, 8), (8, 8), (5, 5), (3, 5), (2.0, 8), (np.int64(4), 8)])
def test_check_extra_notes_accepts_a_whole_number_from_1_to_the_limit(value, limit):
    assert check_extra_notes(value, limit) == int(value)


@pytest.mark.parametrize("value", [0, 9, -1, 2.5, "2", None, True, False, float("nan"), float("inf"), [2]])
def test_check_extra_notes_refuses_anything_else(value):
    with pytest.raises(ValueError, match="The extra notes must be a whole number from 1 to 8."):
        check_extra_notes(value)


def test_check_extra_notes_names_the_limit_of_the_picture():
    with pytest.raises(ValueError) as error:
        check_extra_notes(6, 5)
    assert str(error.value) == "The extra notes must be a whole number from 1 to 5."


@pytest.mark.parametrize("extra", [True, 1.5, "1", None, -1, 6, float("nan")])
def test_hold_loudest_refuses_a_bad_extra(extra):
    with pytest.raises(ValueError, match="The extra notes must be a whole number from 0 to 5."):
        hold_loudest(np.ones((2, 84)), 5, extra)


@pytest.mark.parametrize("count", [0, 85, True, 2.5, "5", None])
def test_hold_loudest_refuses_a_bad_count(count):
    with pytest.raises(ValueError, match="The count must be a whole number from 1 to 84."):
        hold_loudest(np.ones((2, 84)), count, 0)


@pytest.mark.parametrize("values", [np.ones(84), np.ones((2, 3, 4)), np.full((2, 84), np.nan), np.full((2, 84), np.inf), -np.ones((2, 84)), "abc", [["a"]]])
def test_hold_loudest_refuses_bad_values(values):
    with pytest.raises(ValueError):
        hold_loudest(values, 5, 0)


def test_no_frames_gives_an_empty_result():
    assert hold_loudest(np.zeros((0, 84)), 5, 2).shape == (0, 5)


def test_thirty_thousand_frames_are_selected_in_a_few_seconds():
    values = np.random.default_rng(6).random((30000, 84)) ** 3
    start = time.perf_counter()
    order = hold_loudest(values, 8, 8)
    elapsed = time.perf_counter() - start
    assert order.shape == (30000, 8)
    assert elapsed < 5, f"30,000 frames took {elapsed:.1f} s"
