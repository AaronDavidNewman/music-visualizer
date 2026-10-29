"""The points of the ``decay`` picture: the gains, the decay step, the interval, the layout, the radius and the color (feature 027)."""

import numpy as np
import pytest

from app.services.colormaps import COLORMAPS, lookup_table
from app.services.decay import (
    DEFAULT_DECAY_RATE,
    check_decay_rate,
    circle_colors,
    ring_colors,
    ring_positions,
    circle_points,
    circle_radii,
    decay_step,
    gains,
)
from app.services.note_layout import MIDDLE_C_CELL, MIDDLE_C_NOTE, note_order

RATE_MESSAGE = "The decay rate must be a whole number from 1 to 10."
FULL = 25.0


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


# ---- the rate -------------------------------------------------------------------------------------------------------------------


def test_the_default_rate_is_5():
    assert DEFAULT_DECAY_RATE == 5


@pytest.mark.parametrize("value", [1, 2, 5, 9, 10, 5.0, np.int64(3)])
def test_a_whole_number_from_1_to_10_is_accepted_and_returned_as_an_int(value):
    result = check_decay_rate(value)
    assert result == int(value) and type(result) is int


@pytest.mark.parametrize("value", [0, 11, -1, 2.5, 10.5, 0.99, True, False, "5", None, float("nan"), float("inf"), [5]])
def test_anything_else_is_refused_with_the_message(value):
    with pytest.raises(ValueError) as error:
        check_decay_rate(value)
    assert str(error.value) == RATE_MESSAGE


# ---- the gains ------------------------------------------------------------------------------------------------------------------


def test_the_five_loudest_notes_gain_24_20_16_12_and_8():
    values = frame(n0=0.1, n10=0.9, n20=0.8, n30=0.7, n40=0.6, n50=0.5, n60=0.4)
    result = gains(values)
    assert result.shape == (1, 84)
    assert {10: 24, 20: 20, 30: 16, 40: 12, 50: 8} == {n: result[0, n] for n in np.flatnonzero(result[0])}
    assert result[0, 0] == 0 and result[0, 60] == 0


@pytest.mark.parametrize("position, expected", [(0.0, [24, 20, 16, 12, 8]), (0.5, [28, 24, 20, 16, 12]), (1.0, [32, 28, 24, 20, 16])])
def test_the_beat_bonus_is_8_times_the_position_for_each_of_the_five(position, expected):
    values = frame(n1=5, n2=4, n3=3, n4=2, n5=1, n6=0.5)
    result = gains(values, [position])[0]
    assert [result[n] for n in (1, 2, 3, 4, 5)] == expected
    assert result[6] == 0 and np.count_nonzero(result) == 5


def test_the_beat_bonus_is_not_rounded():
    result = gains(frame(n1=1), [0.3])[0]
    assert result[1] == pytest.approx(24 + 8 * 0.3)


def test_equal_values_rank_the_lower_note_first():
    result = gains(frame(n9=1, n3=1, n6=1, n7=1, n8=1, n20=1, n40=1))[0]
    assert [result[n] for n in (3, 6, 7, 8, 9)] == [24, 20, 16, 12, 8]
    assert result[20] == 0 and result[40] == 0


def test_a_note_with_no_energy_never_gains_so_three_sounding_notes_give_three_gains():
    result = gains(frame(n5=0.3, n6=0.2, n7=0.1), [1.0])[0]
    assert np.count_nonzero(result) == 3
    assert [result[5], result[6], result[7]] == [32, 28, 24]


def test_a_silent_frame_gains_nothing_even_at_the_top_of_the_peak():
    assert not gains(np.zeros((2, 88)), [1.0, 1.0]).any()


def test_only_the_84_drawn_notes_count_and_the_input_is_not_changed():
    values = frame(n84=100, n85=100, n87=100, n2=1)
    before = values.copy()
    result = gains(values)
    assert result.shape == (1, 84) and result[0, 2] == 24 and np.count_nonzero(result) == 1
    assert np.array_equal(values, before)


@pytest.mark.parametrize(
    "values, beat",
    [
        (np.full((1, 88), -1.0), None),
        (np.full((1, 88), np.nan), None),
        (np.zeros((1, 83)), None),
        (np.zeros(88), None),
        (np.zeros((2, 88)), [0.5]),
        (np.zeros((1, 88)), [1.5]),
    ],
)
def test_bad_values_or_a_bad_beat_are_refused(values, beat):
    with pytest.raises(ValueError):
        gains(values, beat)


# ---- the points -----------------------------------------------------------------------------------------------------------------


def test_the_gain_lands_on_the_cell_of_the_note_in_the_rows_layout():
    points = circle_points(frame(n30=1), decay_rate=10)
    assert points.shape == (1, 84)
    assert points[0, 30] == 24 and np.count_nonzero(points) == 1


def test_a_note_kept_loud_reaches_64_and_stays_there():
    values = np.repeat(frame(n30=1), 20, axis=0)
    points = circle_points(values, np.ones(20), decay_rate=10)[:, 30]
    assert points.max() == 64
    assert points[2] == 64  # 32 + 32
    assert (points <= 64).all()


def test_a_decay_step_never_leaves_a_circle_below_0_or_above_64():
    rng = np.random.default_rng(1)
    values = rng.random((200, 88)) * (rng.random((200, 88)) > 0.7)
    points = circle_points(values, rng.random(200), decay_rate=2)
    assert points.min() >= 0 and points.max() <= 64


def test_a_cell_in_the_middle_with_30_points_ends_at_14_and_gives_2_to_each_of_its_8_neighbours():
    after = decay_step(grid(c3_5=30))
    assert after[3, 5] == 14
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                assert after[3 + dy, 5 + dx] == 2
    assert after.sum() == 14 + 16  # nothing is lost in the middle


def test_a_cell_on_an_edge_loses_16_in_all_but_sends_2_to_each_of_its_5_neighbours_only():
    after = decay_step(grid(c0_5=30))
    assert after[0, 5] == 14
    assert sorted(np.flatnonzero(after.ravel()).tolist()) == sorted([5, 4, 6, 12 + 4, 12 + 5, 12 + 6])
    assert after[0, 4] == after[0, 6] == after[1, 4] == after[1, 5] == after[1, 6] == 2
    assert after.sum() == pytest.approx(14 + 10)  # 6 points vanished


@pytest.mark.parametrize("row, column", [(0, 0), (0, 11), (6, 0), (6, 11)])
def test_a_cell_in_a_corner_loses_16_in_all_but_sends_2_to_each_of_its_3_neighbours_only(row, column):
    points = np.zeros((7, 12))
    points[row, column] = 30
    after = decay_step(points)
    assert after[row, column] == 14
    assert np.count_nonzero(after) == 4 and after.sum() == pytest.approx(14 + 6)  # 10 points vanished


def test_a_cell_with_exactly_16_points_ends_at_0_and_its_neighbours_get_2():
    after = decay_step(grid(c3_5=16))
    assert after[3, 5] == 0 and after[2, 4] == after[4, 6] == after[3, 6] == 2


def test_a_cell_with_fewer_than_16_points_gives_only_what_it_has_in_the_same_proportions():
    after = decay_step(grid(c3_5=8))
    assert after[3, 5] == 0
    assert after[2, 4] == after[3, 6] == after[4, 6] == 1  # half of 2 each
    assert after.sum() == pytest.approx(8)
    corner = decay_step(grid(c0_0=8))
    assert corner[0, 0] == 0 and corner[0, 1] == corner[1, 0] == corner[1, 1] == 1 and corner.sum() == pytest.approx(3)


def test_cells_give_and_receive_at_the_same_time_from_the_points_before_the_step():
    after = decay_step(grid(c3_5=30, c3_6=30))
    assert after[3, 5] == after[3, 6] == 30 - 16 + 2


def test_a_circle_never_ends_above_64_when_it_receives():
    after = decay_step(grid(c3_5=63, c3_6=30))
    assert after[3, 5] == 63 - 16 + 2 and after[3, 6] == 30 - 16 + 2
    full = np.full((7, 12), 64.0)
    assert decay_step(full).max() <= 64


def test_the_grid_does_not_wrap_around():
    after = decay_step(grid(c3_0=30, c0_5=30))
    assert after[3, 11] == 0 and after[6, 5] == 0 and after[2, 11] == after[4, 11] == 0


def test_a_decay_step_never_makes_the_total_grow_and_keeps_every_cell_from_0_to_64():
    rng = np.random.default_rng(7)
    for _ in range(200):
        points = rng.random((7, 12)) * 64
        after = decay_step(points)
        assert after.sum() <= points.sum() + 1e-9
        assert after.min() >= 0 and after.max() <= 64


def test_the_decay_step_does_not_change_its_input_and_wants_a_7_by_12_array():
    points = grid(c3_5=30)
    before = points.copy()
    decay_step(points)
    assert np.array_equal(points, before)
    with pytest.raises(ValueError):
        decay_step(np.zeros((12, 7)))


# ---- the interval ---------------------------------------------------------------------------------------------------------------


def one_gain_then_silence(frames: int, rate: int, **kwargs) -> np.ndarray:
    values = np.zeros((frames, 88))
    values[0, 30] = 1
    return circle_points(values, decay_rate=rate, **kwargs)


def test_a_rate_of_3_decays_after_frames_3_6_and_9_counting_from_1():
    points = one_gain_then_silence(7, 3)[:, 30]
    # 24 - 16 = 8 at frame 3 (the 8 cells around get 2); at frame 6 it gives its 8 and gets 8 x 0.25 back from its neighbours
    assert points.tolist() == [24, 24, 8, 8, 8, 2, 2]


def test_a_rate_of_1_decays_every_frame_and_a_rate_of_10_first_at_frame_10():
    assert one_gain_then_silence(3, 1)[:, 30].tolist() == [8, 2, 1.75]
    ten = one_gain_then_silence(12, 10)[:, 30]
    assert set(ten[:9]) == {24} and ten[9] == 8 and ten[10] == 8


def test_the_neighbours_receive_in_the_frame_of_the_decay_step():
    points = one_gain_then_silence(4, 4)
    assert points[2, 31] == 0 and points[3, 31] == 2
    assert points[3, 30 - 12] == 2 and points[3, 30 + 12] == 2  # the cells above and below


def test_the_state_starts_at_0_and_the_input_is_not_changed():
    values = frame(n30=1)
    before = values.copy()
    circle_points(values)
    assert np.array_equal(values, before)
    assert not circle_points(np.zeros((5, 88))).any()


def test_two_runs_give_the_same_points():
    rng = np.random.default_rng(3)
    values = rng.random((60, 88))
    beat = rng.random(60)
    assert np.array_equal(circle_points(values, beat, "rows", 4), circle_points(values, beat, "rows", 4))


@pytest.mark.parametrize("layout", ["Rows", "", None, "grid"])
def test_a_bad_layout_or_rate_is_refused(layout):
    with pytest.raises(ValueError):
        circle_points(frame(n1=1), None, layout, 5)
    with pytest.raises(ValueError, match=RATE_MESSAGE):
        circle_points(frame(n1=1), None, "rows", 0)


# ---- the layout -----------------------------------------------------------------------------------------------------------------


def test_in_the_spiral_layout_middle_c_gains_at_row_3_column_6():
    points = circle_points(frame(**{f"n{MIDDLE_C_NOTE}": 1}), decay_rate=10, note_layout="spiral")
    row, column = MIDDLE_C_CELL
    assert points[0, row * 12 + column] == 24 and np.count_nonzero(points) == 1


def test_in_the_spiral_layout_the_points_spread_to_the_cells_around_the_cell_whatever_notes_they_hold():
    points = circle_points(np.vstack([frame(**{f"n{MIDDLE_C_NOTE}": 1}), np.zeros((1, 88))]), decay_rate=2, note_layout="spiral")[1]
    row, column = MIDDLE_C_CELL
    around = [(row + dy) * 12 + column + dx for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
    assert points[row * 12 + column] == 8
    assert all(points[cell] == 2 for cell in around) and np.count_nonzero(points) == 9
    assert sorted(note_order("spiral")[around]) != sorted(range(MIDDLE_C_NOTE - 4, MIDDLE_C_NOTE + 5))  # these are not pitch neighbours


def test_the_ranking_is_in_note_order_also_in_the_spiral_so_equal_notes_go_to_the_lower_note():
    values = frame(n5=1, n6=1, n7=1, n8=1, n9=1, n10=1)
    order = note_order("spiral").tolist()
    points = circle_points(values, decay_rate=10, note_layout="spiral")[0]
    assert [points[order.index(n)] for n in (5, 6, 7, 8, 9)] == [24, 20, 16, 12, 8]
    assert points[order.index(10)] == 0


# ---- the long run ---------------------------------------------------------------------------------------------------------------


def test_after_a_loud_passage_and_a_long_silence_every_circle_is_back_at_0():
    rng = np.random.default_rng(5)
    loud = rng.random((40, 88))
    values = np.vstack([loud, np.zeros((300, 88))])
    points = circle_points(values, np.concatenate([np.ones(40), np.zeros(300)]), decay_rate=1)
    assert points[39].max() > 0
    assert not points[-1].any()


def test_a_circle_left_with_less_than_a_hundredth_of_a_point_has_none():
    after = decay_step(grid(c3_5=16.1, c0_0=0.005))
    assert after[3, 5] == pytest.approx(0.1)
    assert after[0, 0] == 0
    assert decay_step(grid(c3_5=0.02))[3, 5] == 0  # it gives its 0.02 away and receives nothing


def test_the_total_never_grows_in_a_silent_stretch():
    rng = np.random.default_rng(9)
    values = np.vstack([rng.random((10, 88)), np.zeros((50, 88))])
    totals = circle_points(values, decay_rate=3).sum(axis=1)[10:]
    assert (np.diff(totals) <= 1e-9).all()


# ---- radius and color -----------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "points, radius",
    [(0, FULL / 12), (24, FULL), (30, FULL), (64, FULL), (12, FULL * (1 / 12 + 11 / 12 * 0.5)), (6, FULL * (1 / 12 + 11 / 12 * 0.25))],
)
def test_the_radius_is_a_twelfth_at_0_points_full_from_24_and_linear_between(points, radius):
    assert circle_radii(points) == pytest.approx(radius)


def test_the_radius_never_decreases_with_the_points():
    radii = circle_radii(np.linspace(0, 64, 200))
    assert (np.diff(radii) >= 0).all()


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_color_is_the_table_entry_at_the_points_over_32_and_saturates_at_32(name):
    table = lookup_table(name)
    colors = circle_colors(np.array([0, 16, 8, 32, 40, 64]), name)
    assert colors.dtype == np.uint8 and colors.shape == (6, 3)
    assert tuple(colors[0]) == tuple(table[0])
    assert tuple(colors[1]) == tuple(table[128])  # rint(127.5) = 128
    assert tuple(colors[2]) == tuple(table[int(np.rint(0.25 * 255))])
    assert tuple(colors[3]) == tuple(colors[4]) == tuple(colors[5]) == tuple(table[255])


# ---- the rings ------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("points", [0, 5, 16, 24, 31, 32])
def test_up_to_32_points_every_ring_is_at_the_same_place_on_the_colormap(points):
    positions = ring_positions(np.array(float(points)))
    assert positions.shape == (12,)
    assert np.allclose(positions, points / 32)


def test_at_64_points_ring_1_is_the_last_color_and_ring_12_the_first_with_even_steps_between():
    positions = ring_positions(np.array(64.0))
    assert positions[0] == pytest.approx(1.0) and positions[11] == pytest.approx(0.0)
    assert np.allclose(np.diff(positions), -1 / 11)


def test_at_48_points_ring_12_is_half_way_back():
    positions = ring_positions(np.array(48.0))
    assert positions[0] == pytest.approx(1.0) and positions[11] == pytest.approx(0.5)
    assert np.allclose(positions, 1 - 0.5 * np.arange(12) / 11)


def test_ring_1_is_always_the_color_of_the_flat_circle_and_ring_12_comes_back_as_the_points_fall():
    points = np.linspace(0, 64, 129)
    positions = ring_positions(points)
    assert np.allclose(positions[:, 0], np.minimum(points, 32) / 32)
    assert (np.diff(positions[:, 11]) <= 1e-12)[points[1:] > 32].all()  # outer ring: further back as the points rise above 32
    assert (np.diff(positions[points >= 32, 11]) < 0).all()
    assert (positions >= -1e-12).all() and (positions <= 1 + 1e-12).all()


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_ring_colors_are_the_table_entries_at_the_positions(name):
    table = lookup_table(name)
    for points in (0, 20, 32, 40, 50, 64):
        colors = ring_colors(np.array(float(points)), name)
        assert colors.shape == (12, 3) and colors.dtype == np.uint8
        rows = np.rint(ring_positions(np.array(float(points))) * 255).astype(int)
        assert np.array_equal(colors, table[rows])
        assert tuple(circle_colors(np.array(float(points)), name)) == tuple(colors[0])


def test_ring_colors_keep_the_shape_of_an_array_of_points():
    assert ring_colors(np.zeros((3, 84)), "viridis").shape == (3, 84, 12, 3)
    assert circle_colors(np.zeros((3, 84)), "viridis").shape == (3, 84, 3)
