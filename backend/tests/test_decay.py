"""The points of the ``decay`` picture: the gains, the decay step, the interval, the layout, the radius and the color (feature 027)."""

import numpy as np
import pytest

from app.services.colormaps import COLORMAPS, lookup_table
from app.services.decay import (
    DEFAULT_DECAY_RATE,
    DEFAULT_DECAY_AMOUNTS,
    check_decay_amount,
    check_decay_amounts,
    check_decay_rate,
    circle_colors,
    ring_colors,
    ring_positions,
    circle_points,
    circle_radii,
    decay_step,
    steps_in_frame,
    gains,
    decay_per_frame,
)
from app.services.note_layout import MIDDLE_C_CELL, MIDDLE_C_NOTE, note_order

RATE_MESSAGE = "The decay rate must be a number from 0.25 to 4 in steps of 0.25."
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


def test_the_default_rate_is_1_frame():
    assert DEFAULT_DECAY_RATE == 1.0


@pytest.mark.parametrize("value", [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 2.75, 3, 4, 4.0, np.float32(0.5), np.int64(2)])
def test_a_number_from_a_quarter_to_4_in_steps_of_a_quarter_is_accepted_and_returned_as_a_float(value):
    result = check_decay_rate(value)
    assert result == float(value) and type(result) is float


@pytest.mark.parametrize(
    "value", [0, 0.2, 0.24, 0.3, 1.1, 2.3, 3.99, 4.25, 5, 10, -1, -0.25, True, False, "5", None, float("nan"), float("inf"), [1]]
)
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
    points = circle_points(frame(n30=1), decay_rate=4)
    assert points.shape == (1, 84)
    assert points[0, 30] == 24 and np.count_nonzero(points) == 1


def test_a_note_kept_loud_reaches_64_and_stays_there():
    values = np.repeat(frame(n30=1), 20, axis=0)
    points = circle_points(values, np.ones(20), decay_rate=4)[:, 30]
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


@pytest.mark.parametrize("points", [9, 12, 16, 20])
def test_a_cell_with_9_to_20_points_gives_1_to_each_neighbour_and_loses_8_a_frame(points):
    after = decay_step(grid(c3_5=points))
    assert after[3, 5] == points - 8
    assert after[2, 4] == after[4, 6] == after[3, 6] == after[2, 6] == 1
    assert after.sum() == pytest.approx(points)  # in the middle nothing vanishes


@pytest.mark.parametrize("points", [1, 4, 8])
def test_a_cell_with_1_to_8_points_gives_half_a_point_to_each_neighbour_a_frame_which_is_1_every_2_frames(points):
    one = decay_step(grid(c3_5=points))
    give_one = min(points, 4.0)  # 0.5 to each of 8 neighbours, or all it has
    assert one[3, 5] == points - give_one and one[2, 4] == one[3, 6] == give_one / 8
    two = decay_step(grid(c3_5=points), frames=2)  # a step of 2 frames' worth: 1 to each neighbour (or all it has)
    give_two = min(points, 8.0)
    assert two[3, 5] == points - give_two and two[2, 4] == two[4, 6] == give_two / 8
    if points >= 4:
        assert one[2, 4] == 0.5
    if points >= 8:
        assert two[2, 4] == 1.0


def test_a_cell_with_fewer_points_than_it_would_give_gives_only_what_it_has_in_the_same_proportions():
    after = decay_step(grid(c3_5=3))  # it would give 4 (0.5 to each of 8): it has 3
    assert after[3, 5] == 0 and after[2, 4] == after[3, 6] == after[4, 6] == pytest.approx(3 / 8)
    assert after.sum() == pytest.approx(3)
    corner = decay_step(grid(c0_0=3))
    assert corner[0, 0] == 0 and corner[0, 1] == corner[1, 0] == corner[1, 1] == pytest.approx(3 / 8) and corner.sum() == pytest.approx(9 / 8)


def test_the_bands_do_not_overlap_8_is_the_top_of_the_lowest_20_the_top_of_the_middle_and_64_alone_is_saturated():
    assert decay_step(grid(c3_5=8))[3, 6] == 0.5 and decay_step(grid(c3_5=8.5))[3, 6] == 1.0
    assert decay_step(grid(c3_5=20))[3, 6] == 1.0 and decay_step(grid(c3_5=20.5))[3, 6] == 2.0
    assert decay_step(grid(c3_5=63.9))[3, 6] == 2.0 and decay_step(grid(c3_5=64))[3, 6] == 3.0


def test_cells_give_and_receive_at_the_same_time_from_the_points_before_the_step():
    after = decay_step(grid(c3_5=30, c3_6=30))
    assert after[3, 5] == after[3, 6] == 30 - 16 + 2


def test_a_circle_never_ends_above_64_when_it_receives():
    full = np.full((7, 12), 64.0)
    for frames in (1, 2, 10):
        after = decay_step(full, frames)
        assert after.max() <= 64
        assert after[3, 5] == 64  # an interior circle gives and receives the same: a full grid stays full
    for frames in (1, 3, 10):  # a circle in the middle of saturated ones receives from all eight and never exceeds 64
        ring = np.full((7, 12), 64.0)
        ring[3, 5] = 20.0
        assert decay_step(ring, frames)[3, 5] <= 64


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
    # frames 1 and 2: nothing; frame 3: a step of 3 frames' worth (the circle has 24 points: 2 to each neighbour a frame, 48 a step) gives all 24
    # away; frame 6: the 8 neighbours, with 3 points each, give theirs away and the circle gets 3 of it back
    assert points.tolist() == [24, 24, 0, 0, 0, 3, 3]


def test_a_rate_of_1_decays_every_frame_and_a_rate_of_4_first_at_frame_4():
    # 24 points: 2 to each of 8 neighbours = 16 a frame, so 8 are left; then 4 a frame at 8 points, and the neighbours (2 points each, which they
    # give away at once) give 8 x 0.25 = 2 back
    assert one_gain_then_silence(3, 1)[:2, 30].tolist() == [8, 6]
    four = one_gain_then_silence(12, 4)[:, 30]
    assert four[:3].tolist() == [24, 24, 24] and four[3:7].tolist() == [0, 0, 0, 0]  # 4 frames' worth is 64: all 24 points go at once
    assert four[7] == 3  # at frame 8 the neighbours (3 each) give theirs away and the circle gets 3 back


def test_the_neighbours_receive_in_the_frame_of_the_decay_step():
    points = one_gain_then_silence(4, 4)
    assert points[2, 31] == 0 and points[3, 31] == 3  # 24 points shared by 8 neighbours
    assert points[3, 30 - 12] == 3 and points[3, 30 + 12] == 3  # the cells above and below


def test_the_average_rate_is_that_of_the_bands_whatever_the_decay_rate_so_a_step_moves_that_many_frames_worth():
    one = decay_step(grid(c3_5=60), frames=1)
    three = decay_step(grid(c3_5=60), frames=3)
    assert one[3, 5] == 60 - 16 and one[3, 6] == 2  # 2 to each of 8 neighbours a frame
    assert three[3, 5] == 60 - 48 and three[3, 6] == 6  # three frames' worth in one step


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
        circle_points(frame(n1=1), None, layout, 1)
    with pytest.raises(ValueError, match=RATE_MESSAGE):
        circle_points(frame(n1=1), None, "rows", 0)


# ---- the layout -----------------------------------------------------------------------------------------------------------------


def test_in_the_spiral_layout_middle_c_gains_at_row_3_column_6():
    points = circle_points(frame(**{f"n{MIDDLE_C_NOTE}": 1}), decay_rate=4, note_layout="spiral")
    row, column = MIDDLE_C_CELL
    assert points[0, row * 12 + column] == 24 and np.count_nonzero(points) == 1


def test_in_the_spiral_layout_the_points_spread_to_the_cells_around_the_cell_whatever_notes_they_hold():
    points = circle_points(np.vstack([frame(**{f"n{MIDDLE_C_NOTE}": 1}), np.zeros((1, 88))]), decay_rate=2, note_layout="spiral")[1]
    row, column = MIDDLE_C_CELL
    around = [(row + dy) * 12 + column + dx for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
    assert points[row * 12 + column] == 0  # a step of 2 frames' worth (the circle has 24 points: 32 would go) gives them all away
    assert all(points[cell] == 3 for cell in around) and np.count_nonzero(points) == 8
    assert sorted(note_order("spiral")[around]) != sorted(range(MIDDLE_C_NOTE - 4, MIDDLE_C_NOTE + 5))  # these are not pitch neighbours


def test_the_ranking_is_in_note_order_also_in_the_spiral_so_equal_notes_go_to_the_lower_note():
    values = frame(n5=1, n6=1, n7=1, n8=1, n9=1, n10=1)
    order = note_order("spiral").tolist()
    points = circle_points(values, decay_rate=4, note_layout="spiral")[0]
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
    after = decay_step(grid(c3_5=8.005, c0_0=0.005))  # 8.005 gives 8 (1 to each neighbour) and keeps 0.005
    assert after[3, 5] == 0
    assert after[0, 0] == 0
    assert decay_step(grid(c3_5=8.5))[3, 5] == pytest.approx(0.5)  # but 0.5 is kept
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


# ---- the rate varies with the points: 1 to 8 points half a point a frame, 9 to 20 one, 21 to 63 two, 64 three, to each neighbour --------------


@pytest.mark.parametrize(
    "points, rate",
    [(0, 0.0), (0.01, 0.5), (1, 0.5), (8, 0.5), (8.01, 1.0), (9, 1.0), (20, 1.0), (20.01, 2.0), (21, 2.0), (40, 2.0), (63, 2.0), (63.99, 2.0), (64, 3.0)],
)
def test_the_rate_per_neighbour_per_frame_follows_the_bands(points, rate):
    assert decay_per_frame(np.array(float(points))) == rate


def test_the_rate_never_falls_as_the_points_rise_above_0_and_has_the_shape_of_an_array_of_points():
    rates = decay_per_frame(np.linspace(0.01, 64, 600))
    assert (np.diff(rates) >= 0).all() and set(rates.tolist()) == {0.5, 1.0, 2.0, 3.0}
    assert decay_per_frame(np.zeros((7, 12))).shape == (7, 12)


def test_a_saturated_circle_in_the_middle_gives_3_to_each_of_its_8_neighbours_and_loses_24():
    after = decay_step(grid(c3_5=64))
    assert after[3, 5] == 40
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                assert after[3 + dy, 5 + dx] == 3
    assert after.sum() == 64  # nothing is lost in the middle


def test_a_saturated_circle_on_an_edge_or_in_a_corner_loses_24_as_if_it_had_8_neighbours():
    edge = decay_step(grid(c0_5=64))
    assert edge[0, 5] == 40
    assert np.count_nonzero(edge) == 6 and edge[0, 4] == edge[0, 6] == edge[1, 4] == edge[1, 5] == edge[1, 6] == 3
    assert edge.sum() == pytest.approx(40 + 15)  # 9 points vanished (3 for each of the 3 neighbours it does not have)
    corner = decay_step(grid(c0_0=64))
    assert corner[0, 0] == 40 and np.count_nonzero(corner) == 4
    assert corner.sum() == pytest.approx(40 + 9)  # 15 vanished


def test_from_21_to_63_points_a_circle_gives_2_to_each_neighbour_and_loses_16():
    for points in (21, 40, 63):
        after = decay_step(grid(c3_5=points))
        assert after[3, 5] == points - 16 and after[2, 4] == after[4, 6] == 2, points


def test_a_circle_that_has_enough_points_gives_exactly_8_times_frames_times_its_rate():
    for points, frames in ((24, 1), (40, 1), (64, 1), (64, 2), (60, 3), (20, 5), (14, 7)):
        after = decay_step(grid(c3_5=points), frames)
        give = min(points, 8 * frames * float(decay_per_frame(np.array(float(points)))))
        assert after[3, 5] == pytest.approx(points - give) and after.sum() == pytest.approx(points), (points, frames)
        assert after[2, 4] == pytest.approx(give / 8)


def test_a_step_of_10_frames_worth_empties_a_saturated_circle_and_gives_each_neighbour_an_eighth():
    after = decay_step(grid(c3_5=64), frames=10)  # it would give 240
    assert after[3, 5] == 0 and after[2, 4] == after[3, 6] == 8


def test_a_saturated_circle_gives_a_neighbour_more_than_one_that_is_not_quite_saturated():
    assert decay_step(grid(c3_5=64))[3, 6] == 3 > decay_step(grid(c3_5=63))[3, 6] == 2


def test_a_long_note_spreads_to_its_neighbours_faster_once_its_circle_is_full():
    held = np.repeat(frame(n30=1), 4, axis=0)  # a beat of 1 adds 32 to the circle every frame; a step is taken every frame
    points = circle_points(held, np.ones(4), decay_rate=1)
    centre = [float(points[i, 30]) for i in range(4)]
    # frame 1: 32 points give 16 (2 to each of 8) -> 16; frame 2: 16 + 32 = 48 gives 16 -> 32 and the neighbours (2 each, which they give away) give 2 back
    assert centre[:2] == pytest.approx([16.0, 34.0])
    assert centre[2] > 40  # the circle is saturated by the third frame and keeps filling its neighbours at 3 each
    around = points.reshape(4, 7, 12)[:, 1:4, 5:8].sum(axis=(1, 2)) - np.array(centre)
    assert around[0] == pytest.approx(16.0) and (np.diff(around) > 0).all()  # more and more is collected by the neighbours

# ---- the four decay amounts, one for each saturation level ----------------------------------------------------------------------


def amount_message(level):
    return f"The {level} saturation decay must be a number from 0.5 to 3."


def test_the_default_amounts_are_the_bands_of_before():
    assert DEFAULT_DECAY_AMOUNTS == (0.5, 1.0, 2.0, 3.0)
    points = np.linspace(0, 64, 129)
    assert np.array_equal(decay_per_frame(points), decay_per_frame(points, (0.5, 1.0, 2.0, 3.0)))
    assert np.array_equal(decay_step(grid(c3_5=64)), decay_step(grid(c3_5=64), 1, DEFAULT_DECAY_AMOUNTS))


@pytest.mark.parametrize("value", [0.5, 1, 1.25, 2.999, 3, 3.0, np.float32(1.5), np.int64(2)])
def test_a_number_from_half_to_3_is_accepted_and_returned_as_a_float(value):
    result = check_decay_amount(value, "high")
    assert result == pytest.approx(float(value)) and type(result) is float


@pytest.mark.parametrize("value", [0, 0.49, 0.4999, 3.01, 4, -1, float("nan"), float("inf"), -float("inf"), True, False, "1", None, [1]])
@pytest.mark.parametrize("level", ["low", "medium", "high", "saturated"])
def test_anything_else_is_refused_with_the_message_naming_the_level(value, level):
    with pytest.raises(ValueError) as error:
        check_decay_amount(value, level)
    assert str(error.value) == amount_message(level)


def test_four_amounts_are_checked_each_by_its_own_level_and_returned_as_a_tuple_of_floats():
    assert check_decay_amounts([1, 2, 3, 0.5]) == (1.0, 2.0, 3.0, 0.5)
    assert check_decay_amounts(np.array([0.5, 1.5, 2.5, 3.0])) == (0.5, 1.5, 2.5, 3.0)
    for index, level in enumerate(("low", "medium", "high", "saturated")):
        bad = [1.0, 1.0, 1.0, 1.0]
        bad[index] = 3.5
        with pytest.raises(ValueError, match=amount_message(level)):
            check_decay_amounts(bad)


@pytest.mark.parametrize("amounts", [(1, 1, 1), (1, 1, 1, 1, 1), 5, None, "abcd"])
def test_anything_but_four_numbers_is_refused(amounts):
    with pytest.raises(ValueError):
        check_decay_amounts(amounts)


def test_each_saturation_level_uses_its_own_amount():
    amounts = (1.5, 2.5, 0.5, 1.0)
    rates = decay_per_frame(np.array([0.0, 0.01, 5.0, 8.0, 8.5, 15.0, 20.0, 20.5, 40.0, 63.9, 64.0]), amounts)
    assert rates.tolist() == [0.0, 1.5, 1.5, 1.5, 2.5, 2.5, 2.5, 0.5, 0.5, 0.5, 1.0]


@pytest.mark.parametrize("points, level", [(5, 0), (15, 1), (40, 2), (64, 3)])
def test_a_step_gives_each_neighbour_the_amount_of_the_level_and_the_other_amounts_do_not_matter(points, level):
    base = [1.0, 1.0, 1.0, 1.0]
    for amount in (0.5, 1.5, 3.0):
        amounts = list(base)
        amounts[level] = amount
        other = [3.0 if i != level else amount for i in range(4)]  # the other three amounts changed too
        for chosen in (amounts, other):
            after = decay_step(grid(c3_5=points), 1, chosen)
            give = min(points, 8 * amount)
            assert after[3, 5] == pytest.approx(points - give) and after[2, 4] == pytest.approx(give / 8), (points, level, amount, chosen)


def test_a_larger_amount_empties_a_circle_sooner_and_a_smaller_one_keeps_it_longer():
    slow = decay_step(grid(c3_5=64), 1, (0.5, 0.5, 0.5, 0.5))
    fast = decay_step(grid(c3_5=64), 1, (3.0, 3.0, 3.0, 3.0))
    assert slow[3, 5] == 64 - 4 and fast[3, 5] == 64 - 24
    assert slow[2, 4] == 0.5 and fast[2, 4] == 3.0


def test_the_amounts_work_with_the_frames_of_a_step_and_never_give_more_than_the_circle_has():
    after = decay_step(grid(c3_5=30), 4, (0.5, 1.0, 2.5, 3.0))  # 4 frames x 2.5 x 8 = 80: all 30 go
    assert after[3, 5] == 0 and after[2, 4] == pytest.approx(30 / 8)


def test_circle_points_uses_the_amounts_and_the_default_amounts_change_nothing():
    values = np.zeros((3, 88))
    values[0, 30] = 1
    plain = circle_points(values, None, "rows", 1)
    assert np.array_equal(plain, circle_points(values, None, "rows", 1, DEFAULT_DECAY_AMOUNTS))
    custom = circle_points(values, None, "rows", 1, (0.5, 1.0, 3.0, 3.0))  # 24 points are in the high level: 3 to each of 8 = 24: all of it
    assert plain[0, 30] == 8 and custom[0, 30] == 0
    assert custom[0, 31] == 3.0


def test_bad_amounts_are_refused_by_circle_points():
    with pytest.raises(ValueError, match=amount_message("medium")):
        circle_points(frame(n1=1), None, "rows", 1, (0.5, 4.0, 2.0, 3.0))

# ---- the rate from 0.25 to 4 frames in steps of 0.25: several steps a frame below 1 -------------------------------------------------------


@pytest.mark.parametrize(
    "rate, pattern",
    [
        (0.25, [4] * 8),
        (0.5, [2] * 8),
        (0.75, [1, 1, 2, 1, 1, 2, 1, 1]),
        (1.0, [1] * 8),
        (1.25, [0, 1, 1, 1, 1, 0, 1, 1]),
        (1.5, [0, 1, 1, 0, 1, 1, 0, 1]),
        (2.0, [0, 1, 0, 1, 0, 1, 0, 1]),
        (4.0, [0, 0, 0, 1, 0, 0, 0, 1]),
    ],
)
def test_the_steps_in_each_frame_are_those_that_fall_in_it_when_a_step_is_taken_every_rate_frames(rate, pattern):
    assert [steps_in_frame(i, rate) for i in range(8)] == pattern


@pytest.mark.parametrize("rate", [q / 4 for q in range(1, 17)])
def test_the_steps_and_their_size_add_up_to_the_frames_that_have_passed_whatever_the_rate(rate):
    frames = 40
    steps = sum(steps_in_frame(i, rate) for i in range(frames))
    assert frames - rate < steps * rate <= frames  # the frames' worth moved is all of it but the last part of a step still to come


def test_a_step_is_taken_at_the_end_of_a_frame_in_which_its_time_falls_and_never_lost_or_taken_twice():
    for rate in (0.75, 1.25, 1.5, 2.5, 3.0):
        times = [rate * k for k in range(1, int(40 / rate) + 1)]
        for i in range(40):
            expected = sum(1 for t in times if i < t <= i + 1)
            assert steps_in_frame(i, rate) == expected, (rate, i)


def test_a_rate_below_1_takes_several_smaller_steps_in_a_frame_and_decays_in_smaller_pieces():
    coarse = one_gain_then_silence(4, 1)[:, 30]
    fine = one_gain_then_silence(4, 0.25)[:, 30]
    assert np.abs(np.diff(fine)).max() < np.abs(np.diff(coarse)).max() or fine[0] > coarse[0]  # a frame of decay in four pieces: gentler
    sequential = np.zeros((7, 12))
    sequential[2, 6] = 24.0
    for _ in range(4):
        sequential = decay_step(sequential, 0.25)
    assert fine[0] == pytest.approx(sequential[2, 6])  # the first frame is exactly four steps of a quarter of a frame's worth
    assert fine[0] != pytest.approx(decay_step(grid(c2_6=24.0), 1)[2, 6])  # not the same as one step of a whole frame


def test_a_rate_of_a_quarter_never_empties_a_circle_in_one_step_the_way_a_large_rate_does():
    held = np.repeat(frame(n30=1), 12, axis=0)
    quarter = circle_points(held, np.ones(12), decay_rate=0.25)[:, 30]
    four = circle_points(held, np.ones(12), decay_rate=4)[:, 30]
    assert np.abs(np.diff(quarter)).max() < np.abs(np.diff(four)).max()  # the circle changes in smaller pieces


def test_every_rate_gives_points_from_0_to_64_a_total_that_never_grows_and_no_error():
    rng = np.random.default_rng(21)
    values = rng.random((40, 88)) ** 2
    beat = rng.random(40)
    for q in range(1, 17):
        points = circle_points(values, beat, "rows", q / 4)
        assert points.shape == (40, 84) and points.min() >= 0 and points.max() <= 64
