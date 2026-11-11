"""The threshold of the ``chromatic-decay`` image type (feature 037): a note value strictly below a percent of the largest smoothed value is 0.

Every expectation is worked out here with plain loops, not with the code under test.
"""

import numpy as np
import pytest

from app.services import chromatic_decay as cd
from app.services.frame_rendering import _check_threshold

from .test_chromatic_decay_step import oracle_simulation

A, AS, B, C, CS, D, DS, E, F, FS, G, GS = range(12)
MESSAGE = "The threshold must be a number from 0 to 10."


def oracle_threshold(values, threshold):
    """Every value strictly below threshold / 100 x (the largest value of the whole array, all frames and all columns) is 0; the others are unchanged."""
    values = [list(row) for row in values]
    top = max((v for row in values for v in row), default=0.0)
    floor = threshold / 100.0 * top
    return [[0.0 if (threshold > 0 and v < floor) else v for v in row] for row in values]


def note(letter, octave=2):
    return 12 * octave + letter


def frames_with(count=8, **letters):
    """``count`` frames of 88 note values with the given letters (``C=100`` is the letter C in octave 2)."""
    row = np.zeros(88)
    for name, value in letters.items():
        row[note(globals()[name])] = value
    return np.tile(row, (count, 1))


# --- the number ------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("good", [0, 1, 5, 10, 2.5, 5.0, 0.0, np.int64(3), np.float64(7.5)])
def test_a_number_from_0_to_10_is_a_threshold(good):
    assert cd.check_threshold(good) == float(good) and isinstance(cd.check_threshold(good), float)


@pytest.mark.parametrize("bad", [-0.1, -1, 10.0001, 11, 100, True, False, "5", "", None, float("nan"), float("inf"), float("-inf"), [5], np.nan])
def test_anything_else_is_refused_with_the_message(bad):
    with pytest.raises(ValueError) as error:
        cd.check_threshold(bad)
    assert str(error.value) == MESSAGE


def test_the_constants():
    assert (cd.MIN_THRESHOLD, cd.MAX_THRESHOLD, cd.DEFAULT_THRESHOLD) == (0, 10, 0)
    assert cd.THRESHOLD_MESSAGE == MESSAGE


def test_the_check_gives_the_same_answers_as_the_check_of_the_other_image_types():
    table = [0, 1, 2, 5, 10, 0.5, 9.99, 10.0, -1, -0.0001, 10.01, 11, 50, True, False, "5", "x", "", None, np.nan, np.inf, -np.inf, np.int32(4), np.float32(2.5), 1e-9, 3.3333]
    for value in table:
        try:
            other = _check_threshold(value)
        except ValueError:
            other = ValueError
        try:
            mine = cd.check_threshold(value)
        except ValueError:
            mine = ValueError
        assert mine == other, value


# --- the rule ----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("columns", [84, 88])
@pytest.mark.parametrize("threshold", [0, 1, 2.5, 5, 10])
def test_the_rule_agrees_with_the_loop_oracle_on_random_arrays(columns, threshold):
    rng = np.random.default_rng(columns + int(threshold * 10))
    values = rng.random((12, columns)) ** 3 * 100  # many faint values and a few loud ones
    values[rng.random(values.shape) < 0.3] = 0.0
    got = cd.apply_threshold(values, threshold)
    assert got.shape == values.shape and got.dtype == np.float64
    assert got.tolist() == oracle_threshold(values.tolist(), threshold)


def test_a_value_exactly_at_the_floor_is_kept_and_one_just_below_is_not():
    values = np.zeros((1, 84))
    values[0, 0], values[0, 1], values[0, 2], values[0, 3] = 100.0, 5.0, 4.999999, 5.000001
    got = cd.apply_threshold(values, 5)[0]
    assert got[0] == 100.0 and got[1] == 5.0 and got[2] == 0.0 and got[3] == 5.000001


def test_the_reference_is_the_largest_value_of_the_whole_array_not_of_the_frame():
    values = np.zeros((3, 84))
    values[0, 5] = 100.0  # the loudest of the file, in the first frame
    values[2, 9] = 4.0  # the loudest of its own frame, but under 5 percent of the whole
    values[1, 7] = 6.0
    got = cd.apply_threshold(values, 5)
    assert got[2, 9] == 0.0 and got[1, 7] == 6.0 and got[0, 5] == 100.0
    assert cd.apply_threshold(values, 2)[2, 9] == 4.0  # at 2 percent the floor is 2: kept


def test_the_columns_after_the_84th_raise_the_floor_too_as_for_the_other_image_types():
    values = np.zeros((1, 88))
    values[0, 10] = 10.0
    values[0, 86] = 1000.0  # not a note of a letter, but one of the values passed in
    assert cd.apply_threshold(values, 5)[0, 10] == 0.0  # 5 percent of 1000 is 50
    assert cd.apply_threshold(values[:, :84], 5)[0, 10] == 10.0  # without that column the largest is 10


def test_a_threshold_of_0_returns_an_equal_copy_and_nothing_is_changed():
    values = np.random.default_rng(1).random((5, 88)) * 10
    before = values.copy()
    got = cd.apply_threshold(values, 0)
    assert np.array_equal(got, values) and got is not values
    got[0, 0] = -5.0
    assert np.array_equal(values, before)  # the copy is independent
    assert np.array_equal(cd.apply_threshold(values), values)  # the default is off


def test_a_silent_or_empty_array_is_unchanged_without_error():
    assert not cd.apply_threshold(np.zeros((4, 88)), 10).any()
    assert cd.apply_threshold(np.zeros((0, 88)), 10).shape == (0, 88)


def test_the_input_is_not_changed_by_a_threshold_above_0():
    values = np.random.default_rng(2).random((5, 88)) * 10
    before = values.copy()
    cd.apply_threshold(values, 10)
    assert np.array_equal(values, before)


@pytest.mark.parametrize("bad", [np.zeros(88), np.zeros((3, 83)), -np.ones((2, 88)), np.full((2, 88), np.nan), np.full((2, 88), np.inf)])
def test_bad_values_are_refused(bad):
    with pytest.raises(ValueError):
        cd.apply_threshold(bad, 5)


@pytest.mark.parametrize("bad", [-1, 11, True, "5", None, float("nan")])
def test_a_bad_threshold_is_refused_with_the_message(bad):
    with pytest.raises(ValueError) as error:
        cd.apply_threshold(np.ones((2, 88)), bad)
    assert str(error.value) == MESSAGE


# --- the effect on the points -------------------------------------------------------------------------------------------------


def oracle_with_threshold(values, beat, rate, threshold):
    return oracle_simulation(np.array(oracle_threshold(values.tolist(), threshold)).reshape(-1, values.shape[1]), beat, rate)


@pytest.mark.parametrize("rate", [1, 3, 10])
@pytest.mark.parametrize("threshold", [0, 1, 5, 10])
def test_the_points_and_tapers_agree_with_the_oracle_for_random_values_with_and_without_a_beat(rate, threshold):
    rng = np.random.default_rng(rate * 100 + threshold)
    values = rng.random((50, 88)) ** 3 * 100
    values[rng.random(values.shape) < 0.5] = 0.0
    beat = rng.random(50)
    for b in (None, beat):
        want_points, want_tapers = oracle_with_threshold(values, b, rate, threshold)
        assert np.allclose(cd.circle_points(values, b, rate, threshold), want_points, rtol=1e-12, atol=1e-12)
        assert np.allclose(cd.circle_tapers(values, b, rate, threshold), want_tapers, rtol=0, atol=1e-12)


def test_a_faint_letter_gains_nothing_at_5_percent_and_gains_at_2_percent_and_without_a_threshold():
    values = frames_with(30, C=100.0, E=90.0, G=80.0, B=3.0)  # B is 3 percent of the loudest
    # in the first frame nothing has had time to decay into B (a receiver of E), so its points are exactly its own gain
    assert cd.circle_points(values, None, 1, 5)[0, B] == 0.0  # under 5 percent: it gains nothing
    assert cd.circle_points(values, None, 1, 2)[0, B] > 0  # over 2 percent: it gains
    assert cd.circle_points(values, None, 1, 0)[0, B] > 0
    assert cd.circle_points(values, None, 1)[0, B] > 0
    assert not cd.letter_gains(cd.apply_threshold(values, 5))[:, B].any() and cd.letter_gains(cd.apply_threshold(values, 2))[:, B].all()
    # later it can still be lit by the decay of the letters that do sound (E gives to B), but less than when it also gains
    assert cd.circle_points(values, None, 1, 5)[:, B].sum() < cd.circle_points(values, None, 1, 2)[:, B].sum()


def test_the_threshold_only_removes_notes_it_does_not_change_the_gains_of_the_letters_that_stay():
    values = frames_with(10, C=100.0, E=90.0, G=80.0, B=3.0, FS=2.0)
    with_threshold = cd.letter_gains(cd.apply_threshold(values, 5))
    without = cd.letter_gains(values)
    for letter in (C, E, G):  # the three loud letters are the first three in rank either way
        assert np.array_equal(with_threshold[:, letter], without[:, letter])
    assert (without[:, [B, FS]] > 0).all() and not with_threshold[:, [B, FS]].any()  # the faint ones took the 4th and 5th places only without it


def test_a_letter_whose_octaves_are_all_under_the_floor_does_not_count_and_two_faint_octaves_do_not_add_up():
    values = np.zeros((6, 88))
    values[:, note(C, 1)] = 100.0
    values[:, note(E, 1)], values[:, note(E, 3)], values[:, note(E, 5)] = 2.0, 2.5, 3.0  # three faint octaves of E: each alone is under 5 percent
    gains = cd.letter_gains(cd.apply_threshold(values, 5))
    assert gains[:, C].all() and not gains[:, E].any()
    values[:, note(E, 5)] = 6.0  # one octave at 6 percent: E counts, as its largest octave
    assert cd.letter_gains(cd.apply_threshold(values, 5))[:, E].all()


def test_a_frame_where_only_faint_notes_sound_has_no_gains_while_the_loud_frames_have():
    values = np.zeros((6, 88))
    values[0, note(C)] = 100.0
    values[1:4, note(E)] = 3.0  # only faint notes in these frames
    gains = cd.letter_gains(cd.apply_threshold(values, 5))
    assert gains[0, C] > 0 and not gains[1:4].any() and not gains[4:].any()
    points = cd.circle_points(values, None, 1, 5)
    assert not points[:, E].any()  # E is never charged: it is faint in every frame


def test_a_threshold_of_0_and_the_argument_left_out_are_the_same_as_before_the_feature():
    rng = np.random.default_rng(11)
    values = rng.random((40, 88)) * 5
    beat = rng.random(40)
    for rate in (1, 4):
        want_points, want_tapers = oracle_simulation(values, beat, rate)  # the oracle of feature 035, with no threshold at all
        assert np.allclose(cd.circle_points(values, beat, rate), want_points, rtol=1e-12, atol=1e-12)
        assert np.array_equal(cd.circle_points(values, beat, rate), cd.circle_points(values, beat, rate, 0))
        assert np.array_equal(cd.circle_tapers(values, beat, rate), cd.circle_tapers(values, beat, rate, 0))
        assert np.allclose(cd.circle_tapers(values, beat, rate), want_tapers, rtol=0, atol=1e-12)


def test_values_with_nothing_under_the_floor_give_the_same_points_at_any_threshold():
    values = np.full((20, 88), 50.0)
    values[:, ::2] = 100.0  # the smallest value is 50 percent of the largest
    assert np.array_equal(cd.circle_points(values, None, 2, 10), cd.circle_points(values, None, 2, 0))


@pytest.mark.parametrize("bad", [-1, 11, True, "5", None])
def test_a_bad_threshold_is_refused_by_the_points_and_the_tapers(bad):
    with pytest.raises(ValueError) as error:
        cd.circle_points(np.ones((3, 88)), None, 1, bad)
    assert str(error.value) == MESSAGE
    with pytest.raises(ValueError):
        cd.circle_tapers(np.ones((3, 88)), None, 1, bad)


def test_the_inputs_are_not_changed_and_the_result_is_deterministic():
    values = np.random.default_rng(5).random((20, 88)) * 100
    beat = np.random.default_rng(6).random(20)
    values_before, beat_before = values.copy(), beat.copy()
    first = cd.circle_points(values, beat, 3, 7)
    assert np.array_equal(values, values_before) and np.array_equal(beat, beat_before)
    assert np.array_equal(first, cd.circle_points(values, beat, 3, 7))
