"""The number of notes: choosing the highest-energy notes and spreading them over the grid: ``app/services/note_selection.py``."""

import numpy as np
import pytest

from app.services.note_selection import (
    DEFAULT_NOTE_COUNT,
    MAX_NOTE_COUNT,
    MIN_NOTE_COUNT,
    check_note_count,
    spread_notes,
    top_energy_notes,
)

MESSAGE = "The number of notes must be a whole number from 12 to 84."
COUNTS = [12, 13, 24, 36, 48, 83, 84]
ALL_COUNTS = list(range(12, 85))


def random_frames(frames=8, seed=1):
    return np.random.default_rng(seed).random((frames, 84)) ** 2


def ranking(values, count):
    """The choice written independently: rank by (-energy, note), keep the first ``count``, in order of pitch."""
    energy = values.sum(axis=0)
    ranked = sorted(range(84), key=lambda note: (-energy[note], note))
    return sorted(ranked[:count])


def with_np_interp(values, count):
    chosen = ranking(values, count)
    xs = np.linspace(0, count - 1, 84)
    return np.array([np.interp(xs, np.arange(count), row[chosen]) for row in values])


def test_constants():
    assert (MIN_NOTE_COUNT, MAX_NOTE_COUNT, DEFAULT_NOTE_COUNT) == (12, 84, 84)


@pytest.mark.parametrize("value", [12, 13, 50, 83, 84, np.int64(36), 36.0, np.float64(84.0)])
def test_note_counts_from_twelve_to_eighty_four_are_accepted(value):
    assert check_note_count(value) == int(value)
    assert isinstance(check_note_count(value), int)


@pytest.mark.parametrize(
    "bad", [0, 11, 85, -1, 100, 36.5, 12.0001, True, False, None, "36", "", float("nan"), float("inf"), -float("inf"), b"36"]
)
def test_other_note_counts_are_refused_with_the_message(bad):
    with pytest.raises(ValueError) as error:
        check_note_count(bad)
    assert str(error.value) == MESSAGE


# --- the choice -------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("count", ALL_COUNTS)
def test_the_chosen_notes_are_the_highest_energy_ones_in_order_of_pitch(count):
    values = random_frames(seed=count)
    chosen = top_energy_notes(values, count)
    assert chosen.tolist() == ranking(values, count)
    assert len(chosen) == count == len(set(chosen.tolist()))
    assert (np.diff(chosen) > 0).all() and chosen.min() >= 0 and chosen.max() <= 83


def test_ties_go_to_the_lower_note():
    values = np.zeros((4, 84))
    values[:, [10, 20, 30, 40, 50]] = 1.0  # five notes of exactly equal energy
    values[:, 60] = 5.0  # one stronger note
    chosen = top_energy_notes(values, 12)
    assert 60 in chosen
    # the cut falls among the zero-energy notes: the lowest ones are kept after the five equal ones and the strong one
    assert chosen.tolist() == ranking(values, 12)
    tie = np.zeros((3, 84))
    tie[:, 5:30] = 2.0  # 25 notes of equal energy; only 12 fit
    assert top_energy_notes(tie, 12).tolist() == list(range(5, 17))


def test_a_silent_input_chooses_the_lowest_notes():
    assert top_energy_notes(np.zeros((5, 84)), 12).tolist() == list(range(12))
    assert top_energy_notes(np.zeros((5, 84)), 84).tolist() == list(range(84))


def test_the_choice_depends_only_on_the_energy_of_each_note():
    values = random_frames(10, seed=3)
    chosen = top_energy_notes(values, 24)
    assert top_energy_notes(values[::-1], 24).tolist() == chosen.tolist()  # frame order does not matter
    rng = np.random.default_rng(4)
    shuffled = values.copy()
    for note in range(84):  # the same column sums, the values moved between frames
        shuffled[:, note] = rng.permutation(values[:, note])
    assert top_energy_notes(shuffled, 24).tolist() == chosen.tolist()
    assert top_energy_notes(values, 24).tolist() == chosen.tolist()  # and repeatable


def test_the_energy_is_over_the_whole_file_not_per_frame():
    values = np.zeros((2, 84))
    values[0, 5:17] = 1.0  # twelve notes loud in frame 0
    values[1, 40:52] = 0.9  # twelve other notes loud in frame 1, a little less in total
    chosen = top_energy_notes(values, 12)
    assert chosen.tolist() == list(range(5, 17))  # the same twelve for both frames (a per-frame choice would differ)
    assert top_energy_notes(values, 24).tolist() == list(range(5, 17)) + list(range(40, 52))


def test_the_input_is_not_modified_by_the_choice():
    values = random_frames()
    before = values.copy()
    top_energy_notes(values, 30)
    assert (values == before).all()


# --- the spread ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("count", ALL_COUNTS)
def test_the_spread_equals_np_interp_over_the_chosen_notes(count):
    values = random_frames(5, seed=100 + count)
    got = spread_notes(values, count)
    assert got.shape == (5, 84) and got.dtype == np.float64
    assert np.allclose(got, with_np_interp(values, count), atol=1e-12, rtol=0)


def test_with_all_eighty_four_notes_the_spread_is_exactly_the_input_and_a_new_array():
    values = random_frames()
    got = spread_notes(values, 84)
    assert np.array_equal(got, values)
    assert got is not values and not np.shares_memory(got, values)
    got[0, 0] = -1.0
    assert values[0, 0] != -1.0


@pytest.mark.parametrize("count", COUNTS)
def test_the_first_and_last_values_are_the_first_and_last_chosen_notes_exactly(count):
    values = random_frames(6, seed=count)
    chosen = top_energy_notes(values, count)
    got = spread_notes(values, count)
    assert np.array_equal(got[:, 0], values[:, chosen[0]])
    assert np.array_equal(got[:, -1], values[:, chosen[-1]])


@pytest.mark.parametrize("count", COUNTS)
def test_every_value_is_between_the_smallest_and_the_largest_chosen_value(count):
    values = random_frames(20, seed=200 + count)
    chosen = top_energy_notes(values, count)
    got = spread_notes(values, count)
    low, high = values[:, chosen].min(axis=1), values[:, chosen].max(axis=1)
    assert (got.min(axis=1) >= low - 1e-12).all() and (got.max(axis=1) <= high + 1e-12).all()


@pytest.mark.parametrize("count", [12, 24, 48, 83])
def test_a_note_that_is_not_chosen_changes_no_output_value(count):
    values = random_frames(6, seed=count)
    chosen = set(top_energy_notes(values, count).tolist())
    others = [n for n in range(84) if n not in chosen]
    energy = values.sum(axis=0)
    threshold = energy[sorted(chosen)].min()
    changed = values.copy()
    rng = np.random.default_rng(9)
    for note in others:  # new values for the left-out notes, kept below the weakest chosen note's energy
        new = rng.random(values.shape[0])
        changed[:, note] = new * (0.9 * threshold / max(new.sum(), 1e-12))
    assert set(top_energy_notes(changed, count).tolist()) == chosen
    assert np.array_equal(spread_notes(changed, count), spread_notes(values, count))


@pytest.mark.parametrize("count", COUNTS)
def test_equal_values_stay_equal_and_a_ramp_stays_a_ramp(count):
    assert np.allclose(spread_notes(np.full((3, 84), 0.37), count), 0.37, atol=1e-15, rtol=0)
    ramp = np.tile(np.arange(84, dtype=float)[None, :], (2, 1))  # note n has the value n, energy rises with n
    got = spread_notes(ramp, count)
    assert (np.diff(got, axis=1) >= -1e-12).all()
    assert got[0, 0] == top_energy_notes(ramp, count)[0] and got[0, -1] == 83


def test_no_frames_gives_an_empty_result():
    assert spread_notes(np.zeros((0, 84)), 12).shape == (0, 84)
    assert top_energy_notes(np.zeros((0, 84)), 12).tolist() == list(range(12))


@pytest.mark.parametrize("bad", [np.ones((2, 83)), np.ones(84), np.ones((2, 3, 28)), np.ones((2, 88))])
def test_input_of_the_wrong_shape_is_refused(bad):
    with pytest.raises(ValueError):
        spread_notes(bad, 24)
    with pytest.raises(ValueError):
        top_energy_notes(bad, 24)


@pytest.mark.parametrize("count", [0, 11, 85, 36.5, None, "36", True])
def test_a_bad_count_is_refused_by_both_functions(count):
    for function in (spread_notes, top_energy_notes):
        with pytest.raises(ValueError) as error:
            function(random_frames(), count)
        assert str(error.value) == MESSAGE


@pytest.mark.parametrize("count", COUNTS)
def test_the_same_input_gives_the_same_output_and_the_input_is_not_modified(count):
    values = random_frames()
    before = values.copy()
    assert np.array_equal(spread_notes(values, count), spread_notes(values, count))
    assert (values == before).all()
