"""The points of the ``decay-exp`` picture: the tapered gain, the exponential loss, the steps and the frames (feature 030)."""

import numpy as np
import pytest

from app.services import decay
from app.services.decay import steps_in_frame
from app.services.decay_exp import (
    FULL_CIRCLES,
    FULL_POINTS,
    MAX_TAPER,
    TAPER,
    TAPER_STEP,
    TAPER_STEPS,
    circle_points,
    circle_tapers,
    decay_exp_step,
    exp_gains,
    exp_loss_per_frame,
    next_taper,
    taper_of,
)
from app.services.note_layout import MIDDLE_C_CELL, MIDDLE_C_NOTE

RATE_MESSAGE = "The decay rate must be a number from 0.25 to 4 in steps of 0.25."
LAYOUT_MESSAGE = "The note layout must be one of rows, spiral."
NO_BEAT_GAINS = (24, 20, 16, 12, 8)


def frame(**notes) -> np.ndarray:
    """One frame of 88 note values with the given values at the given notes (``n12=0.5`` is note 12)."""
    row = np.zeros(88)
    for name, value in notes.items():
        row[int(name[1:])] = value
    return row[None, :]


def grid(**cells) -> np.ndarray:
    """A 7 x 12 array of points with the given points at the given cells (``c3_4=30`` is row 3, column 4)."""
    points = np.zeros((7, 12))
    for name, value in cells.items():
        row, column = name[1:].split("_")
        points[int(row), int(column)] = value
    return points


def taper(g):
    return g * np.exp(-g / 8)


def loss(p):
    return np.sin(np.pi / 2 * p / 64) ** 2


FIVE = frame(n10=1.0, n20=0.9, n30=0.8, n40=0.7, n50=0.6)  # five notes, loudest first: notes 10, 20, 30, 40, 50


# ---- the gain -------------------------------------------------------------------------------------------------------------------


def test_the_taper_is_8():
    assert TAPER == 8


def test_with_no_beat_the_five_loudest_notes_gain_the_tapered_24_20_16_12_8():
    result = exp_gains(FIVE)
    assert result.shape == (1, 84)
    expected = [24 * np.exp(-3), 20 * np.exp(-2.5), 16 * np.exp(-2), 12 * np.exp(-1.5), 8 * np.exp(-1)]
    np.testing.assert_allclose(result[0, [10, 20, 30, 40, 50]], expected, rtol=1e-12)
    np.testing.assert_allclose(expected, [1.1949, 1.6417, 2.1654, 2.6776, 2.9430], atol=5e-5)
    assert np.count_nonzero(result) == 5


def test_the_beat_bonus_comes_before_the_taper():
    top = exp_gains(FIVE, beat=[1.0])[0, [10, 20, 30, 40, 50]]
    np.testing.assert_allclose(top, [taper(g) for g in (32, 28, 24, 20, 16)], rtol=1e-12)
    half = exp_gains(FIVE, beat=[0.5])[0, [10, 20, 30, 40, 50]]
    np.testing.assert_allclose(half, [taper(g) for g in (28, 24, 20, 16, 12)], rtol=1e-12)
    assert abs(taper(32) - 0.5861) < 5e-5


def test_the_gain_is_the_gain_of_decay_tapered_for_any_values_and_beat():
    rng = np.random.default_rng(7)
    values = rng.random((40, 88))
    beat = rng.random(40)
    g = decay.gains(values, beat)
    np.testing.assert_array_equal(exp_gains(values, beat), g * np.exp(-g / 8))


def test_ties_go_to_the_lower_note_and_zero_notes_never_gain():
    tied = exp_gains(frame(n5=0.5, n9=0.5, n40=0.5, n41=0.5, n42=0.5, n60=0.5))
    assert [round(tied[0, n], 4) for n in (5, 9, 40, 41, 42, 60)] == [round(taper(g), 4) for g in (24, 20, 16, 12, 8)] + [0.0]
    three = exp_gains(frame(n1=0.3, n2=0.2, n3=0.1))
    assert np.count_nonzero(three) == 3


def test_a_silent_frame_gains_nothing_even_at_the_top_of_the_beat():
    assert not exp_gains(np.zeros((1, 88)), beat=[1.0]).any()


def test_columns_after_the_84th_are_ignored_and_the_input_is_not_changed():
    values = FIVE.copy()
    values[0, 86] = 5.0
    before = values.copy()
    result = exp_gains(values)
    assert result.shape == (1, 84)
    np.testing.assert_array_equal(values, before)
    np.testing.assert_array_equal(result, exp_gains(FIVE))


@pytest.mark.parametrize("bad", [np.full((1, 88), -1.0), np.full((1, 88), np.nan), np.zeros((1, 50)), np.zeros(88)])
def test_bad_values_are_refused_as_for_decay(bad):
    with pytest.raises(ValueError):
        exp_gains(bad)


# ---- the loss -------------------------------------------------------------------------------------------------------------------


def test_the_loss_is_nothing_at_0_points_and_sin_squared_of_the_points_above():
    assert exp_loss_per_frame(0.0) == 0.0
    points = np.array([1.0, 8.0, 24.0, 32.0, 48.0, 64.0])
    np.testing.assert_allclose(exp_loss_per_frame(points), np.sin(np.pi / 2 * points / 64) ** 2, rtol=1e-12)
    np.testing.assert_allclose(exp_loss_per_frame(points), [0.0006, 0.0381, 0.3087, 0.5, 0.8536, 1.0], atol=5e-5)


def test_the_loss_rises_with_the_points_from_nothing_to_one_per_neighbour_and_keeps_the_shape_of_the_input():
    points = np.linspace(0.01, 64, 200)
    assert (np.diff(exp_loss_per_frame(points)) > 0).all()
    assert exp_loss_per_frame(np.zeros((7, 12))).shape == (7, 12)
    assert exp_loss_per_frame(64.0) == pytest.approx(1.0) and exp_loss_per_frame(32.0) == pytest.approx(0.5)


def test_the_loss_does_not_warn_anywhere_from_0_to_64():
    with np.errstate(all="raise"):
        exp_loss_per_frame(np.linspace(0, 64, 1000))


# ---- the step -------------------------------------------------------------------------------------------------------------------


def test_an_interior_circle_gives_each_of_its_8_neighbours_the_loss_of_its_points():
    after = decay_exp_step(grid(c3_5=32))
    assert after[3, 5] == pytest.approx(32 - 8 * 0.5)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                assert after[3 + dy, 5 + dx] == pytest.approx(0.5)
    assert after.sum() == pytest.approx(32.0)


def test_an_edge_circle_loses_as_much_as_an_interior_one_and_what_the_missing_neighbours_would_have_got_vanishes():
    after = decay_exp_step(grid(c0_5=32))  # the top edge: 5 neighbours
    assert after[0, 5] == pytest.approx(28.0)
    assert after.sum() == pytest.approx(32 - 3 * 0.5)
    assert np.count_nonzero(after) == 6


def test_a_corner_circle_has_3_neighbours_and_loses_as_much_as_any_other():
    after = decay_exp_step(grid(c6_11=32))
    assert after[6, 11] == pytest.approx(28.0)
    assert after.sum() == pytest.approx(32 - 5 * 0.5)
    assert np.count_nonzero(after) == 4


def test_a_full_circle_gives_the_most_one_point_to_each_neighbour():
    after = decay_exp_step(grid(c3_5=64))
    assert after[3, 5] == pytest.approx(56.0)
    assert after[3, 6] == pytest.approx(1.0) and after[2, 4] == pytest.approx(1.0)
    assert after.sum() == pytest.approx(64.0)


def test_a_step_of_2_frames_gives_twice_as_much():
    one = decay_exp_step(grid(c3_5=32), 1)
    two = decay_exp_step(grid(c3_5=32), 2)
    assert 32 - two[3, 5] == pytest.approx(2 * (32 - one[3, 5]))
    assert two[3, 6] == pytest.approx(2 * one[3, 6])


def test_a_circle_never_gives_more_than_it_has():
    after = decay_exp_step(grid(c3_5=32), 10)  # would give 8 * 10 * 0.5 = 40
    assert after[3, 5] == 0.0
    assert after[3, 6] == pytest.approx(4.0) and after.sum() == pytest.approx(32.0)


def test_a_circle_with_few_points_gives_very_little():
    after = decay_exp_step(grid(c3_5=1))
    assert 1 - after[3, 5] == pytest.approx(8 * loss(1))
    assert 8 * loss(1) == pytest.approx(0.0048, abs=1e-4)
    assert not np.delete(after.ravel(), 3 * 12 + 5).any()  # the neighbours would get 0.0006 each: under a hundredth, so nothing


def test_a_circle_with_no_points_gives_nothing():
    assert not decay_exp_step(np.zeros((7, 12))).any()


def test_a_circle_left_with_under_a_hundredth_of_a_point_has_none():
    after = decay_exp_step(grid(c3_5=0.005))
    assert after[3, 5] == 0.0 and not after.any()


def test_all_circles_give_and_receive_at_the_same_time_from_the_points_before_the_step():
    after = decay_exp_step(grid(c3_5=32, c3_6=32))
    assert after[3, 5] == pytest.approx(32 - 4 + 0.5)
    assert after[3, 6] == pytest.approx(32 - 4 + 0.5)
    assert after[3, 4] == pytest.approx(0.5)  # it has the neighbour on one side only


def test_in_a_grid_of_full_circles_the_middle_ones_keep_64_and_the_edges_lose():
    after = decay_exp_step(np.full((7, 12), 64.0))
    assert after[3, 5] == 64.0  # gives 8, gets 8
    assert after[0, 5] == pytest.approx(61.0) and after[0, 0] == pytest.approx(59.0)
    assert after.max() == 64.0


def test_the_grid_does_not_wrap_around():
    after = decay_exp_step(grid(c3_11=32, c3_0=0))
    assert after[3, 0] == 0.0 and after[2, 0] == 0.0 and after[4, 0] == 0.0
    after = decay_exp_step(grid(c0_5=32))
    assert not after[6].any()


def test_the_step_checks_the_shape_and_does_not_change_its_input():
    with pytest.raises(ValueError):
        decay_exp_step(np.zeros((12, 7)))
    points = grid(c3_5=32)
    before = points.copy()
    decay_exp_step(points)
    np.testing.assert_array_equal(points, before)


def test_over_random_grids_the_total_never_grows_and_every_circle_stays_within_0_and_64():
    rng = np.random.default_rng(11)
    for _ in range(200):
        points = rng.random((7, 12)) * 64 * (rng.random((7, 12)) < 0.6)
        frames = float(rng.choice([0.25, 0.5, 1, 2, 4]))
        after = decay_exp_step(points, frames)
        assert after.sum() <= points.sum() + 1e-9
        assert after.min() >= 0.0 and after.max() <= 64.0


# ---- the points of all frames ---------------------------------------------------------------------------------------------------


def test_the_points_have_the_shape_frames_by_84():
    values = np.zeros((7, 88))
    assert circle_points(values).shape == (7, 84)
    assert circle_points(values).dtype == np.float64


def test_a_note_without_a_step_has_exactly_the_tapered_gain_after_its_first_frame():
    # a rate of 4: no decay step in frames 1 to 3, a step after frame 4; the taper is 8 in the first frame, 8.01 in the second, and so on
    points = circle_points(np.repeat(frame(n30=1.0), 6, axis=0), None, "rows", 4)
    gains_ = [24 * np.exp(-24 / taper_of(i)) for i in range(4)]
    assert points[0, 30] == pytest.approx(24 * np.exp(-3))  # the first frame is at the taper of 8, as ever
    assert points[1, 30] == pytest.approx(sum(gains_[:2]))
    assert points[2, 30] == pytest.approx(sum(gains_[:3]))
    held = sum(gains_)
    assert points[3, 30] == pytest.approx(held - 8 * 4 * loss(held))  # a step of 4 frames' worth
    assert points[3, 29] == pytest.approx(4 * loss(held)) and points[3, 31] > 0


def test_the_beat_bonus_is_added_before_the_taper_in_the_points_of_all_frames():
    # rate 4: no step in the first frame, so the points are the gain itself
    points = circle_points(frame(n30=1.0), beat=[1.0], note_layout="rows", decay_rate=4)
    assert points[0, 30] == pytest.approx(taper(32))
    assert points[0, 30] != pytest.approx(taper(24))


def test_the_points_stay_between_0_and_64_also_at_a_rate_of_4_where_the_gains_of_3_frames_add_up():
    points = circle_points(np.repeat(FIVE, 600, axis=0), None, "rows", 4)
    assert points.min() >= 0.0 and points.max() <= 64.0


def test_at_the_default_rate_a_circle_with_a_note_keeps_nearly_all_it_gains_in_its_first_frame():
    points = circle_points(np.repeat(frame(n30=1.0), 3, axis=0))
    gain = taper(24)
    assert points[0, 30] == pytest.approx(gain - 8 * loss(gain))  # 1.1949 points give 0.0069 away
    assert points[0, 30] > 1.18
    assert np.count_nonzero(points[0]) == 1  # each neighbour would get 0.0009: under a hundredth, so nothing


def test_a_steady_note_charges_its_circle_up_as_the_taper_rises_and_levels_off_at_the_taper_of_12():
    values = np.repeat(frame(n30=1.0), 1000, axis=0)
    points = circle_points(values)
    assert circle_tapers(values)[-1] == 12.0
    assert 30.0 < points[-1, 30] < 40.0  # about 34: its gain, 24 * e^(-2), is balanced by what it gives to its neighbours
    assert points[50, 30] < points[300, 30] < points[-1, 30]  # it took a long while to get there
    assert (points > FULL_POINTS).sum(axis=1).max() <= FULL_CIRCLES  # one circle over 32: the taper is never turned down


def test_five_steady_notes_charge_their_circles_but_not_to_64_because_the_taper_turns_down():
    points = circle_points(np.repeat(FIVE, 1500, axis=0))
    assert 40.0 < points[-1].max() < 64.0
    assert points.min() >= 0.0 and points.max() < 64.0
    assert (points > FULL_POINTS).sum(axis=1).max() > FULL_CIRCLES  # so that the taper does turn down


def test_the_steps_of_a_frame_follow_the_rate_as_in_decay():
    values = np.repeat(FIVE, 12, axis=0)
    for rate in (0.25, 0.75, 2.0):
        points = circle_points(values, None, "rows", rate)
        tapers = circle_tapers(values, None, "rows", rate)
        # a hand-run of the same loop with the module's own pieces
        gained = decay.arrange_notes(exp_gains(values, None, tapers), "rows").reshape(-1, 7, 12)
        state = np.zeros((7, 12))
        for i in range(12):
            state = np.clip(state + gained[i], 0, 64)
            for _ in range(steps_in_frame(i, rate)):
                state = decay_exp_step(state, rate)
            np.testing.assert_allclose(points[i], state.reshape(84), rtol=0, atol=1e-12)


def test_the_spiral_layout_puts_the_gain_of_middle_c_in_its_cell_and_spreads_to_the_cells_around_it():
    values = np.repeat(frame(**{f"n{MIDDLE_C_NOTE}": 1.0}), 1, axis=0)
    points = circle_points(values, None, "spiral", 4)  # no step in frame 1: only the gain
    middle_c = MIDDLE_C_CELL[0] * 12 + MIDDLE_C_CELL[1]
    assert points[0, middle_c] == pytest.approx(taper(24))
    assert np.count_nonzero(points[0]) == 1
    after = circle_points(np.repeat(values, 4, axis=0), None, "spiral", 4)[3]
    row, column = MIDDLE_C_CELL
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                assert after[(row + dy) * 12 + column + dx] > 0


def test_the_ranking_is_in_note_order_also_in_the_spiral():
    values = frame(n5=0.5, n6=0.5)
    rows = circle_points(values, None, "rows", 4)
    spiral = circle_points(values, None, "spiral", 4)
    # the lower note wins the tie: it gets the 24, the other the 20
    assert rows[0].max() == pytest.approx(taper(20)) and rows[0, 5] == pytest.approx(taper(24)) and rows[0, 6] == pytest.approx(taper(20))
    assert sorted(spiral[0][spiral[0] > 0]) == pytest.approx(sorted([taper(24), taper(20)]))


def test_a_bad_rate_or_layout_is_refused_with_the_messages_of_decay():
    for rate in (0, 0.2, 5, True, "1", None, float("nan")):
        with pytest.raises(ValueError, match=RATE_MESSAGE.replace(".", r"\.")):
            circle_points(frame(n1=1.0), None, "rows", rate)
    with pytest.raises(ValueError, match="layout"):
        circle_points(frame(n1=1.0), None, "columns")


def test_the_same_input_gives_the_same_points_and_the_input_is_not_changed():
    rng = np.random.default_rng(3)
    values = rng.random((30, 88))
    beat = rng.random(30)
    before = values.copy()
    first = circle_points(values, beat, "rows", 0.75)
    np.testing.assert_array_equal(first, circle_points(values, beat, "rows", 0.75))
    np.testing.assert_array_equal(values, before)


def test_decay_and_decay_exp_differ_for_the_same_input_and_decay_is_unchanged():
    values = np.repeat(frame(n30=1.0), 3, axis=0)
    assert decay.circle_points(values)[0, 30] == pytest.approx(24 - 0.0 * 24, abs=24)  # decay: 24 gained, then the decay of a step
    assert decay.circle_points(values)[0, 30] != circle_points(values)[0, 30]
    # the 027 numbers: 24 points, a circle of the high band gives 2 to each of its 8 neighbours: 24 - 16 = 8
    assert decay.circle_points(values)[0, 30] == pytest.approx(8.0)


# ---- quiet, silent and beat-less moments (Story 3) -------------------------------------------------------------------------------


def test_a_silent_file_gives_points_that_are_all_0():
    assert not circle_points(np.zeros((30, 88)), None, "rows", 1).any()
    assert not circle_points(np.zeros((30, 88)), np.ones(30), "spiral", 0.25).any()


def test_with_fewer_than_5_sounding_notes_only_those_gain():
    points = circle_points(frame(n10=0.3, n11=0.2), None, "rows", 4)  # no step in frame 1
    assert np.count_nonzero(points[0]) == 2
    assert points[0, 10] == pytest.approx(taper(24)) and points[0, 11] == pytest.approx(taper(20))


def test_a_silent_frame_in_the_middle_adds_nothing_and_the_circles_only_decay():
    values = np.zeros((6, 88))
    values[:2] = np.repeat(FIVE, 2, axis=0)
    points = circle_points(values, None, "rows", 1)
    assert (points[2:].sum(axis=1) <= points[1].sum() + 1e-9).all()
    assert (np.diff(points[1:].sum(axis=1)) <= 1e-9).all()  # the total never grows once the sound stops


def test_after_a_loud_passage_the_circles_fade_away_slowly_and_the_total_never_grows():
    # the loss of a circle falls with the square of its points (sin^2 of a small angle), so the tail is long: measured for five notes held for 100
    # frames at a rate of 1, the largest circle has under 1 point by frame 3,100 (1 minute 43 s at 30 frames a second), under a tenth by about
    # 31,800 and is exactly 0 only at about 228,700
    values = np.zeros((40000, 88))
    values[:100] = np.repeat(FIVE, 100, axis=0)
    points = circle_points(values, None, "rows", 1)
    assert points[99].max() > 30.0
    largest = points.max(axis=1)
    assert largest[4000] < 1.0 and largest[-1] < 0.1
    assert (np.diff(points[100:].sum(axis=1)) <= 1e-9).all()
    assert points.min() >= 0.0 and points.max() <= 64.0


# ---- the taper (feature 030, revised) -----------------------------------------------------------------------------------------------


def test_the_taper_starts_and_bottoms_at_8_tops_at_12_and_moves_in_steps_of_a_hundredth():
    assert (TAPER, MAX_TAPER, TAPER_STEP, TAPER_STEPS) == (8, 12, 0.01, 400)
    assert (FULL_POINTS, FULL_CIRCLES) == (32, 10)


def test_taper_of_is_8_plus_a_hundredth_for_each_step_exactly_at_both_ends():
    assert taper_of(0) == 8.0 and taper_of(400) == 12.0
    assert taper_of(1) == pytest.approx(8.01) and taper_of(250) == pytest.approx(10.5)
    assert taper_of(np.int64(100)) == pytest.approx(9.0)


@pytest.mark.parametrize("bad", [-1, 401, 1.5, True, "1", None, float("nan")])
def test_taper_of_refuses_anything_but_a_whole_number_of_steps_from_0_to_400(bad):
    with pytest.raises(ValueError, match="taper steps"):
        taper_of(bad)


def test_while_rising_the_taper_goes_up_a_step_a_frame_and_stops_at_the_top():
    assert next_taper(0, True, 0) == (1, True)
    assert next_taper(399, True, 5) == (400, True)
    assert next_taper(400, True, 5) == (400, True)  # it never goes over 12


def test_more_than_10_circles_over_32_points_turn_it_down_exactly_at_11():
    assert next_taper(100, True, FULL_CIRCLES) == (101, True)  # 10 do not
    assert next_taper(100, True, FULL_CIRCLES + 1) == (99, False)  # 11 do
    assert next_taper(400, True, 84) == (399, False)


def test_once_turned_down_it_keeps_falling_whatever_the_number_of_circles_until_it_is_back_at_8():
    assert next_taper(99, False, 0) == (98, False)
    assert next_taper(2, False, 3) == (1, False)
    assert next_taper(1, False, 3) == (0, True)  # back at 8: it turns up again


def test_it_never_goes_below_8_even_with_many_full_circles_at_8():
    assert next_taper(0, True, 84) == (0, True)
    assert next_taper(0, False, 84) == (0, True)


def test_whatever_the_counts_the_taper_stays_between_8_and_12_and_moves_by_one_step_at_most():
    rng = np.random.default_rng(5)
    steps, rising = 0, True
    for count in rng.integers(0, 30, 5000):
        new, rising = next_taper(steps, rising, int(count))
        assert 0 <= new <= TAPER_STEPS and abs(new - steps) <= 1
        steps = new


def test_exp_gains_takes_one_taper_for_all_frames_or_one_for_each_and_refuses_a_bad_one():
    values = np.repeat(FIVE, 3, axis=0)
    g = decay.gains(values)
    np.testing.assert_array_equal(exp_gains(values, None, 10.0), g * np.exp(-g / 10.0))
    each = np.array([8.0, 9.0, 12.0])
    np.testing.assert_array_equal(exp_gains(values, None, each), g * np.exp(-g / each[:, None]))
    np.testing.assert_array_equal(exp_gains(values), exp_gains(values, None, 8))
    for bad in (0, -1, float("nan"), float("inf"), np.ones(2), np.ones((3, 1))):
        with pytest.raises(ValueError, match="taper"):
            exp_gains(values, None, bad)


def test_the_first_frame_is_at_the_taper_of_8_and_a_silent_file_raises_it_by_a_hundredth_a_frame_up_to_12():
    tapers = circle_tapers(np.zeros((450, 88)))
    assert tapers[0] == 8.0
    np.testing.assert_allclose(tapers[:401], 8 + 0.01 * np.arange(401), rtol=0, atol=1e-12)
    assert tapers[400] == 12.0 and (tapers[400:] == 12.0).all()  # 400 frames at 0.01 is exactly 4, no drift, and it stays at the top


def test_the_taper_is_the_same_whatever_the_decay_rate_per_frame_it_counts_frames_not_steps():
    values = np.zeros((20, 88))
    for rate in (0.25, 1, 4):
        np.testing.assert_allclose(circle_tapers(values, None, "rows", rate), 8 + 0.01 * np.arange(20), rtol=0, atol=1e-12)


def test_with_more_than_10_circles_over_32_points_it_turns_down_and_goes_all_the_way_back_to_8_before_rising_again():
    values = np.repeat(FIVE, 3000, axis=0)
    points = circle_points(values)
    tapers = circle_tapers(values)
    over = (points > FULL_POINTS).sum(axis=1)
    assert over.max() > FULL_CIRCLES
    first = int(np.flatnonzero(over > FULL_CIRCLES)[0])
    assert tapers[first + 1] == pytest.approx(tapers[first] - 0.01)  # the very next frame falls
    assert tapers.min() == 8.0 and tapers.max() < 12.0 and tapers.max() > 9.0
    # every turn from falling to rising happens at exactly 8: it never turns up on its own above 8
    falling = np.diff(tapers) < -1e-9
    for i in range(1, len(tapers) - 1):
        if falling[i - 1] and not falling[i]:
            assert tapers[i] == 8.0, i
    # and every frame obeys the rule, replayed from the counts of circles
    steps, rising = 0, True
    for i in range(len(tapers)):
        assert tapers[i] == taper_of(steps)
        steps, rising = next_taper(steps, rising, int(over[i]))


def test_the_taper_changes_what_a_note_gains_over_the_frames():
    values = np.repeat(frame(n30=1.0), 500, axis=0)
    fixed = circle_points(values)  # taper rising to 12
    assert circle_tapers(values)[-1] == 12.0
    flat = np.zeros_like(fixed)
    state = np.zeros((7, 12))
    for i in range(500):  # the same run at a fixed taper of 8, to see that the rising taper made a difference
        state = decay_exp_step(np.clip(state + decay.arrange_notes(exp_gains(values[i : i + 1]), "rows").reshape(7, 12), 0, 64))
        flat[i] = state.reshape(84)
    assert fixed[-1, 30] > flat[-1, 30] + 5
