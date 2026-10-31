"""The rule of the beat wave: the pattern of rings and the modifier ``1 - pattern * sin(pi * k)`` (feature 028)."""

import numpy as np
import pytest

from app.services.beat_wave import (
    DEFAULT_WAVE_COUNT,
    check_wave_count,
    wave_modifier,
    wave_pattern,
)

MESSAGE = "The wave count must be a whole number from 2 to 10."
GRIDS = [(7, 12), (14, 24), (21, 36), (35, 60)]


def reference(rows: int, columns: int, waves: int) -> np.ndarray:
    """The formula written out directly, point by point, as an independent check (the sine runs over sqrt(distance / largest))."""
    out = np.zeros((rows, columns))
    maxdim = max(rows, columns)
    for y in range(rows):
        for x in range(columns):
            radius = np.sqrt((x - (columns - 1) / 2) ** 2 + (y - (rows - 1) / 2) ** 2)
            z1 = np.sin(waves * np.pi * 2 * np.sqrt(radius / maxdim))
            out[y, x] = (z1 + 1) / 2  # from -1..1 to 0..1
    return out


# ---- the count ------------------------------------------------------------------------------------------------------------------


def test_the_default_wave_count_is_4():
    assert DEFAULT_WAVE_COUNT == 4


@pytest.mark.parametrize("value", [2, 3, 4, 9, 10, 5.0, np.int64(7)])
def test_a_whole_number_from_2_to_10_is_accepted_and_returned_as_an_int(value):
    result = check_wave_count(value)
    assert result == int(value) and type(result) is int


@pytest.mark.parametrize("value", [0, 1, 11, -2, 2.5, 9.99, True, False, "5", None, float("nan"), float("inf"), [5]])
def test_anything_else_is_refused_with_the_message(value):
    with pytest.raises(ValueError) as error:
        check_wave_count(value)
    assert str(error.value) == MESSAGE


# ---- the pattern ----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("rows, columns", GRIDS)
@pytest.mark.parametrize("waves", range(2, 11))
def test_the_pattern_is_the_formula_of_the_description_at_every_point(rows, columns, waves):
    pattern = wave_pattern(rows, columns, waves)
    assert pattern.shape == (rows, columns) and pattern.dtype == np.float64
    assert np.allclose(pattern, reference(rows, columns, waves), atol=1e-12, rtol=0)


@pytest.mark.parametrize("rows, columns", GRIDS + [(5, 5), (7, 13), (1, 9), (9, 1)])
@pytest.mark.parametrize("waves", [2, 4, 10])
def test_every_value_is_from_0_to_1(rows, columns, waves):
    pattern = wave_pattern(rows, columns, waves)
    assert pattern.min() >= 0.0 and pattern.max() <= 1.0


@pytest.mark.parametrize("rows, columns", [(5, 5), (7, 13), (9, 3)])
def test_the_exact_center_of_an_odd_sized_grid_has_distance_0_and_so_the_pattern_one_half(rows, columns):
    pattern = wave_pattern(rows, columns, 4)
    assert pattern[(rows - 1) // 2, (columns - 1) // 2] == 0.5


def test_the_center_of_an_even_axis_lies_between_two_points_so_the_pattern_is_symmetric_about_it():
    pattern = wave_pattern(7, 12, 4)
    assert np.array_equal(pattern, pattern[::-1])
    assert np.array_equal(pattern, pattern[:, ::-1])
    assert pattern[3, 5] == pattern[3, 6]  # the two points either side of the center are the same distance away


@pytest.mark.parametrize("rows, columns, waves", [(21, 36, 3), (35, 60, 10), (14, 24, 2), (6, 11, 7)])
def test_the_pattern_is_symmetric_left_to_right_and_top_to_bottom(rows, columns, waves):
    pattern = wave_pattern(rows, columns, waves)
    assert np.allclose(pattern, pattern[::-1], atol=1e-12)
    assert np.allclose(pattern, pattern[:, ::-1], atol=1e-12)


def test_the_first_ring_of_1_is_at_a_quarter_wave_of_the_square_root_of_the_distance():
    # a single row of 2001 points: the center is at 1000, the largest dimension is 2001; with 2 waves the sine of 4 pi sqrt(d / 2001) is 1
    # where sqrt(d / 2001) = 1 / 8, that is d = 2001 / 64 = 31.3 points, and -1 at three quarters of a wave, d = 9 * 2001 / 64 = 281.4 points
    pattern = wave_pattern(1, 2001, 2)[0]
    distance = np.abs(np.arange(2001) - 1000)
    assert pattern[distance == 31].min() > 0.999
    assert pattern[distance == 281].max() < 0.001


def test_the_rings_are_wider_towards_the_outside_than_near_the_center():
    row = wave_pattern(1, 2001, 6)[0, 1000:]  # from the center to the edge
    crossings = np.flatnonzero(np.diff(np.sign(row - 0.5)))  # the places where the pattern crosses one half
    widths = np.diff(crossings)
    assert len(widths) >= 6
    assert widths[0] < widths[-1] and (np.diff(widths) >= -1).all()  # the half waves get longer and longer (to within a point of rounding)


def test_a_larger_wave_count_has_more_rings_across_the_picture():
    counts = []
    for waves in (2, 4, 6, 10):
        row = wave_pattern(41, 41, waves)[20, 20:]  # from the center to the edge
        counts.append(int(np.count_nonzero(np.diff(np.sign(row - 0.5)))))
    assert counts == sorted(counts) and counts[0] < counts[-1]


def test_the_largest_dimension_is_the_larger_of_rows_and_columns_so_a_grid_and_its_transpose_have_transposed_patterns():
    wide = wave_pattern(7, 12, 4)
    tall = wave_pattern(12, 7, 4)
    assert np.allclose(wide, tall.T, atol=1e-12)


def test_the_pattern_is_read_only_and_the_same_object_is_returned_for_the_same_arguments():
    first = wave_pattern(7, 12, 4)
    assert wave_pattern(7, 12, 4) is first
    with pytest.raises(ValueError):
        first[0, 0] = 5.0
    assert wave_pattern(7, 12, 5) is not first
    assert not np.array_equal(wave_pattern(7, 12, 5), first)


@pytest.mark.parametrize("rows, columns, waves", [(0, 12, 4), (7, 0, 4), (7, 12, 1), (7, 12, 11), (7, 12, 2.5)])
def test_a_bad_grid_or_wave_count_is_refused(rows, columns, waves):
    with pytest.raises(ValueError):
        wave_pattern(rows, columns, waves)


# ---- the modifier ---------------------------------------------------------------------------------------------------------------


def test_at_the_minimum_of_the_beat_the_modifier_is_exactly_1_everywhere():
    assert np.array_equal(wave_modifier(7, 12, 4, 0.0), np.ones((7, 12)))
    assert np.array_equal(wave_modifier(14, 24, 10, 0), np.ones((14, 24)))


@pytest.mark.parametrize("k", [0.1, 0.25, 0.5, 0.75, 1.0])
def test_the_modifier_is_one_minus_the_pattern_times_the_sine_of_pi_k(k):
    pattern = wave_pattern(7, 12, 4)
    assert np.allclose(wave_modifier(7, 12, 4, k), 1 - pattern * np.sin(np.pi * k), atol=1e-15, rtol=0)


def test_half_way_up_the_beat_a_point_of_pattern_1_is_cut_to_nothing_and_a_point_of_pattern_0_is_left_alone():
    pattern = wave_pattern(41, 41, 4)
    modifier = wave_modifier(41, 41, 4, 0.5)
    assert np.allclose(modifier, 1 - pattern)
    assert modifier.min() < 0.01 and modifier.max() > 0.99


@pytest.mark.parametrize("rows, columns", [(7, 12), (21, 36)])
def test_at_the_top_of_the_beat_the_modifier_is_again_all_but_exactly_1(rows, columns):
    assert np.allclose(wave_modifier(rows, columns, 4, 1.0), 1.0, atol=1e-15, rtol=0)


@pytest.mark.parametrize("k", [0.05, 0.2, 0.35, 0.45])
def test_the_effect_is_the_same_going_up_the_beat_and_coming_down_it(k):
    assert np.allclose(wave_modifier(21, 36, 4, k), wave_modifier(21, 36, 4, 1 - k), atol=1e-12, rtol=0)


@pytest.mark.parametrize("k", [0.0, 0.3, 0.7, 1.0])
def test_the_modifier_is_between_1_minus_sin_pi_k_and_1_so_it_never_makes_a_value_negative_or_larger(k):
    modifier = wave_modifier(21, 36, 6, k)
    assert modifier.min() >= 1 - np.sin(np.pi * k) - 1e-12 and modifier.max() <= 1.0


def test_the_modifier_is_a_new_array_and_never_changes_the_cached_pattern():
    before = wave_pattern(7, 12, 4).copy()
    first = wave_modifier(7, 12, 4, 0.5)
    first[:] = 7.0
    assert np.array_equal(wave_pattern(7, 12, 4), before)
    assert np.allclose(wave_modifier(7, 12, 4, 0.5), 1 - before)


def test_the_modifier_grows_stronger_up_to_half_way_up_the_beat_and_weaker_after_it():
    deviation = [float(np.abs(wave_modifier(21, 36, 4, k) - 1).sum()) for k in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5)]
    assert deviation[0] == 0 and deviation == sorted(deviation) and len(set(deviation)) == len(deviation)
    after = [float(np.abs(wave_modifier(21, 36, 4, k) - 1).sum()) for k in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)]
    assert after == sorted(after, reverse=True) and len(set(after)) == len(after)
    assert after[-1] < 1e-12


@pytest.mark.parametrize("k", [-0.1, 1.1, float("nan"), float("inf"), True, None, "0.5", [0.5]])
def test_a_position_outside_0_to_1_or_not_a_number_is_refused(k):
    with pytest.raises(ValueError):
        wave_modifier(7, 12, 4, k)
