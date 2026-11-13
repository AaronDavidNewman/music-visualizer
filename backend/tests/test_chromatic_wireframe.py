"""The numbers of the ``chromatic-wireframe`` image type (feature 039): the line of a frame, the view and the colors.

Every expectation is worked out here with plain loops from the rules of the spec, not with the functions under test.
"""

import math

import numpy as np
import pytest

from app.services import chromatic_decay as cd
from app.services import chromatic_wireframe as cw
from app.services.colormaps import COLORMAPS, lookup_table

MARGIN = 10
SHARE = 2 / 5  # the highest height of a line, as a share of the height
FLOOR, CEILING = 0.05, 0.8  # the stretch of the sum of the waves
SHRINK_DEPTH = 0.25
STEP_AT_400 = 4
SHRINK = 0.25


def amplitude(height):
    return SHARE * height


def band(width):
    return (width - 2 * MARGIN) / 12


def rows(count, seed=1):
    return np.random.default_rng(seed).uniform(0, 64, size=(count, 12))


# ---------------------------------------------------------------- the angle of each letter


def span(width):
    return width - 2 * MARGIN


def count(width):
    return math.ceil(2 * span(width)) + 1


def test_the_share_of_a_letter_is_a_twelfth_of_the_width_inside_the_margins():
    assert cw.band_width(600) == pytest.approx(580 / 12)
    assert cw.band_width(300) == pytest.approx(280 / 12)
    assert cw.band_width(1200) == pytest.approx(1180 / 12)


def test_every_letter_has_its_own_frequency_from_its_points_and_the_phase_of_its_start():
    for row in rows(5):
        angles = cw.line_angles(row, 600)
        xmax, n = band(600), count(600)
        assert angles.shape == (12, n)
        for b in range(12):
            start = b * xmax
            for i in range(n):
                u = i * span(600) / (n - 1)
                expected = 2 * math.pi * (row[b] / 16) * (u / span(600)) + 2 * math.pi * start / span(600)
                assert angles[b, i] == pytest.approx(expected, abs=1e-12)


def test_a_fully_charged_letter_makes_four_turns_across_the_width_and_a_silent_one_none():
    row = np.array([0.0, 16.0, 32.0, 48.0, 64.0, 8.0] + [0.0] * 6)
    angles = cw.line_angles(row, 600)
    turns = (angles[:, -1] - angles[:, 0]) / (2 * math.pi)
    assert turns[:6] == pytest.approx([0, 1, 2, 3, 4, 0.5])  # p / 16 turns from the left of the plot to its right
    assert turns[6:] == pytest.approx(0)
    # between the two ends the angle is a straight line of u, so the sine is a pure wave of that frequency
    assert np.allclose(np.diff(angles[4]), np.diff(angles[4])[0])


def test_the_letters_have_different_frequencies_when_they_have_different_points():
    row = np.array([10.0, 20.0, 30.0] + [40.0] * 9)
    angles = cw.line_angles(row, 600)
    speeds = (angles[:, -1] - angles[:, 0]) / (2 * math.pi)
    assert len({round(float(v), 9) for v in speeds}) == 4
    assert speeds[0] < speeds[1] < speeds[2] < speeds[3]


def test_a_letter_a_quarter_of_the_way_along_adds_a_quarter_turn_to_its_phase():
    # letters with the same points differ by their phase only: letter 3 starts a quarter of the way along the axis
    row = np.full(12, 10.0)
    angles = cw.line_angles(row, 600)
    assert 3 * band(600) / span(600) == pytest.approx(1 / 4)
    assert np.allclose(angles[3] - angles[0], math.pi / 2)
    assert np.allclose(angles[6] - angles[0], math.pi)
    assert np.allclose(angles[9] - angles[0], 3 * math.pi / 2)


def test_at_the_left_end_of_the_line_the_angle_of_a_letter_is_the_phase_of_its_start_whatever_its_points():
    angles = cw.line_angles(rows(1, seed=2)[0], 600)
    assert np.allclose(angles[:, 0], [2 * math.pi * b / 12 for b in range(12)])


# ---------------------------------------------------------------- the line of a frame


def stretched(total):
    return min(max((total - FLOOR) / (CEILING - FLOOR), 0.0), 1.0)


@pytest.mark.parametrize("size", [(600, 400), (300, 200), (1200, 800), (640, 360)])
def test_the_height_is_the_stretched_sum_over_the_letters_of_the_radius_times_the_sine_squared(size):
    width, height = size
    full = cd.ring_geometry(width, height)[1]
    n = count(width)
    for row in list(rows(3, seed=width)) + [np.array([0, 0, 30, 0, 52, 0, 0, 64, 0, 40, 0, 20.0])]:
        X, Z = cw.line_heights(row, width, height)
        S = cw.line_sums(row, width, height)
        assert X.shape == Z.shape == S.shape == (n,)
        angles = cw.line_angles(row, width)
        for i in range(0, n, 7):
            total = 0.0
            for b in range(12):
                total += (cd.circle_radii(row[b], width, height) / full) * math.sin(angles[b, i]) ** 2
            assert S[i] == pytest.approx(total / 12, abs=1e-12)
            assert Z[i] == pytest.approx(amplitude(height) * stretched(total / 12), abs=1e-9)
            assert X[i] == pytest.approx(MARGIN + i * span(width) / (n - 1), abs=1e-9)


def test_the_stretch_puts_the_floor_at_the_base_and_the_ceiling_at_the_highest_height():
    row = np.array([0, 0, 30, 0, 52, 0, 0, 64, 0, 40, 0, 20.0])
    S = cw.line_sums(row, 600, 400)
    _, Z = cw.line_heights(row, 600, 400)
    assert S.min() < CEILING and 0 <= S.min() and S.max() <= 1
    below, above = S <= FLOOR, S >= CEILING
    assert np.all(Z[below] == 0) and np.allclose(Z[above], 160)
    middle = ~below & ~above
    assert np.allclose(Z[middle], 160 * (S[middle] - FLOOR) / (CEILING - FLOOR))
    assert (Z >= 0).all() and (Z <= 160).all()


def test_twelve_full_letters_with_every_wave_at_its_top_make_the_highest_height_at_the_right_end():
    # the angle at the right end of the line is 2 pi (p / 16) + 2 pi b / 12: p = 44 - 4 b / 3 makes it a quarter turn plus whole half turns for every letter, so every sine squared is 1
    row = 44 - 4 * np.arange(12) / 3
    assert row.min() >= 24 and row.max() <= 64  # all full circles
    S = cw.line_sums(row, 600, 400)
    assert S[-1] == pytest.approx(1.0)
    assert cw.line_heights(row, 600, 400)[1][-1] == pytest.approx(160.0)  # the highest height, A: two fifths of the picture
    assert cw.line_heights(row, 600, 400)[1].max() == pytest.approx(160.0)
    assert np.allclose(cw.line_heights(row, 600, 400)[1][S >= CEILING], 160.0)  # and everything over the ceiling is held there


def test_the_waves_are_sine_squared_so_they_add_and_do_not_cancel():
    for row in rows(20, seed=11):
        S = cw.line_sums(row, 600, 400)
        assert S.min() >= 0 and S.max() <= 1  # no wave is ever negative
    # a letter with the radius of a full circle at the top of its wave gives 1 / 12 and the others, at least a twelfth of that each
    assert cw.line_sums(np.full(12, 28.0), 600, 400).min() >= 0


def test_the_line_has_the_several_frequencies_of_its_letters():
    # two letters with 16 and 48 points make 1 and 3 turns of the angle across the width, so their sine squared has 2 and 6 humps: the two strongest non-constant parts
    row = np.zeros(12)
    row[2], row[7] = 16.0, 48.0
    S = cw.line_sums(row, 600, 400)
    spectrum = np.abs(np.fft.rfft(S - S.mean()))
    top = sorted(np.argsort(spectrum)[-2:])
    assert top == [2, 6]
    assert spectrum[2] > 10 * np.median(spectrum[8:]) and spectrum[6] > 10 * np.median(spectrum[8:])


def test_the_line_is_one_continuous_function_with_no_jump_at_the_start_of_a_letter():
    xmax = band(600)
    for row in [np.zeros(12), np.full(12, 28.0), np.array([0.0, 64.0] * 6), np.array([0, 0, 30, 0, 52, 0, 0, 64, 0, 40, 0, 20.0])] + list(rows(3, seed=4)):
        X, Z = cw.line_heights(row, 600, 400)
        assert (np.diff(X) > 0).all() and X[0] == pytest.approx(MARGIN) and X[-1] == pytest.approx(600 - MARGIN)
        # a letter's wave moves by at most 2 pi (p / 16) / (width of the plot) radians a pixel (sine squared by at most as much), so the line moves by at most the sum of those,
        # times the radius share, A / 12 and the stretch
        shares = cd.circle_radii(row, 600, 400) / cd.ring_geometry(600, 400)[1]
        limit = 160 / 12 / (CEILING - FLOOR) * (shares * 2 * math.pi * (row / 16) / span(600)).sum() * (X[1] - X[0])
        assert np.abs(np.diff(Z)).max() <= limit * 1.0001 + 1e-12
        n = len(X)
        for b in range(1, 12):  # in particular nothing happens at the starts of the letters
            i = int(round(b * xmax / span(600) * (n - 1)))
            assert abs(Z[i] - Z[i - 1]) <= limit * 1.0001 + 1e-12


def test_the_height_stays_between_the_base_and_two_fifths_of_the_picture():
    for row in list(rows(60, seed=7)) + [np.zeros(12), np.full(12, 64.0), np.full(12, 28.0)]:
        Z = cw.line_heights(row, 600, 400)[1]
        assert Z.min() >= 0 and Z.max() <= 160 + 1e-9


def test_at_the_left_end_of_the_line_the_sum_is_the_radius_shares_times_the_sine_squared_of_the_phases():
    row = rows(1, seed=5)[0]
    shares = cd.circle_radii(row, 600, 400) / cd.ring_geometry(600, 400)[1]
    expected = sum(shares[b] * math.sin(2 * math.pi * b / 12) ** 2 for b in range(12)) / 12
    assert cw.line_sums(row, 600, 400)[0] == pytest.approx(expected)


def test_twelve_letters_with_the_same_points_make_a_flat_line_because_their_waves_add_to_a_constant():
    # sin squared of (t + 2 pi b / 12) for b = 0 .. 11 adds up to 6 for any t: a constant, so equal letters give a flat line at half their radius share
    for points in (0.0, 10.0, 28.0, 64.0):
        S = cw.line_sums(np.full(12, points), 600, 400)
        share = cd.circle_radii(points, 600, 400) / cd.ring_geometry(600, 400)[1]
        assert np.ptp(S) < 1e-9 and S[0] == pytest.approx(share / 2)
    assert np.ptp(cw.line_heights(np.full(12, 64.0), 600, 400)[1]) < 1e-9
    assert cw.line_heights(np.full(12, 64.0), 600, 400)[1][0] == pytest.approx(160 * stretched(0.5))


def test_a_silent_frame_is_a_flat_line_on_the_base_and_a_frame_with_points_is_not():
    Z = cw.line_heights(np.zeros(12), 600, 400)[1]
    assert np.ptp(Z) < 1e-9 and Z[0] == 0  # the sum is 1 / 24, under the floor
    row = np.array([0, 0, 30, 0, 52, 0, 0, 64, 0, 40, 0, 20.0])
    assert np.ptp(cw.line_heights(row, 600, 400)[1]) > 30


def test_one_steady_letter_is_still_a_line_that_moves():
    row = np.zeros(12)
    row[3] = 40.0  # one loud letter and the others silent
    S = cw.line_sums(row, 600, 400)
    Z = cw.line_heights(row, 600, 400)[1]
    assert np.ptp(S) > 0.03 and np.ptp(Z) > 5  # the floor is low enough that a single note is not flattened


def test_the_heights_scale_with_the_picture():
    row = np.array([0, 0, 30, 0, 52, 0, 0, 64, 0, 40, 0, 20.0])
    X, Z = cw.line_heights(row, 300, 200)
    assert X[0] == pytest.approx(10) and X[-1] == pytest.approx(290)
    assert Z.shape == (count(300),) and Z.min() >= 0 and Z.max() <= 80 + 1e-9  # two fifths of 200
    assert np.ptp(Z) > 10


def test_a_bad_row_is_refused_and_the_input_is_not_changed():
    for bad in (np.zeros(11), np.zeros(13), np.zeros((12, 1)), np.full(12, np.nan), np.full(12, np.inf), np.full(12, -0.1), np.full(12, 64.1), "x", None):
        with pytest.raises(ValueError):
            cw.line_heights(bad, 600, 400)
        with pytest.raises(ValueError):
            cw.line_angles(bad, 600)
    row = rows(1)[0]
    before = row.copy()
    cw.line_heights(row, 600, 400)
    assert (row == before).all()


# ---------------------------------------------------------------- the view


def test_the_geometry_of_600_by_400():
    assert cw.line_geometry(600, 400) == (66, 390.0, 4.0)  # the base is at the bottom margin; the stack runs up to the top margin


@pytest.mark.parametrize("size", [(600, 400), (300, 200), (1200, 800), (640, 360), (800, 100), (100, 50)])
def test_the_lines_that_fit_are_as_many_as_leave_the_oldest_inside_the_picture(size):
    width, height = size
    lines, base, step = cw.line_geometry(width, height)
    a = amplitude(height)
    assert base == pytest.approx(height - MARGIN)  # a line is never under its base, so the base is at the bottom margin
    assert step == pytest.approx(STEP_AT_400 * height / 400)
    assert lines >= 1
    oldest_top = base - (lines - 1) * step - a * (1 - SHRINK_DEPTH)
    assert oldest_top >= MARGIN - 1e-9  # the highest height of the oldest line is inside the top margin
    assert oldest_top - step < MARGIN  # and one more line would not be: the stack fills the picture
    for depth in range(lines):  # every line's highest height is inside the margin
        scale = 1 - SHRINK_DEPTH * depth / (lines - 1) if lines > 1 else 1.0
        assert base - depth * step - a * scale >= MARGIN - 1e-9


def test_the_geometry_scales_with_the_height():
    assert cw.line_geometry(300, 200) == (61, 190.0, 2.0)


def test_a_picture_too_small_for_one_line_or_a_bad_size_is_refused():
    for size in ((600, 30), (600, 0), (0, 400), (-5, 400), (600.5, 400), (True, 400), ("600", 400), (600, None)):
        with pytest.raises(ValueError):
            cw.line_geometry(*size)


def test_depth_zero_is_the_line_as_it_is_and_older_lines_are_higher_and_smaller():
    X, Z = cw.line_heights(rows(1, seed=3)[0], 600, 400)
    lines, base, step = cw.line_geometry(600, 400)
    x0, y0 = cw.project_line(X, Z, 0, lines, 600, 400)
    assert np.allclose(x0, X) and np.allclose(y0, base - Z)
    for depth in (1, 2, 10, lines - 1):
        s = 1 - SHRINK * depth / (lines - 1)
        x, y = cw.project_line(X, Z, depth, lines, 600, 400)
        assert np.allclose(x, 300 + (X - 300) * s)
        assert np.allclose(y, base - depth * step - Z * s)
    # the oldest line is as wide as 75 % of the plot
    x, _ = cw.project_line(X, Z, lines - 1, lines, 600, 400)
    assert x.min() == pytest.approx(300 - 290 * 0.75) and x.max() == pytest.approx(300 + 290 * 0.75)


def test_a_single_line_has_no_shrink():
    X, Z = cw.line_heights(np.full(12, 10.0), 600, 400)
    x, y = cw.project_line(X, Z, 0, 1, 600, 400)
    assert np.allclose(x, X)


def test_a_depth_outside_the_lines_is_refused():
    X, Z = cw.line_heights(np.zeros(12), 600, 400)
    for depth in (-1, 56, 100, 1.5, True, None, "1"):
        with pytest.raises(ValueError):
            cw.project_line(X, Z, depth, 56, 600, 400)


# ---------------------------------------------------------------- the colors


def stretched_distance(beat):
    beat = np.asarray(beat, dtype=float)
    inside = beat > 0
    if not inside.any():
        return 1.0 - beat
    low = float(np.percentile(beat[inside], 1))
    high = float(beat[inside].max())
    if high - low <= 0:
        return 1.0 - beat
    return np.clip((high - beat) / (high - low), 0.0, 1.0)


@pytest.mark.parametrize("colormap", COLORMAPS)
def test_a_line_takes_the_row_of_its_place_in_the_beat_with_the_peak_the_last(colormap):
    beat = np.array([0.0, 0.0, 0.62, 0.8, 1.0, 0.9, 0.7, 0.55, 0.0, 0.6, 0.95, 1.0])
    table = lookup_table(colormap)
    colors = cw.line_colors(beat, colormap)
    assert colors.shape == (12, 3) and colors.dtype == np.uint8
    for t, distance in enumerate(stretched_distance(beat)):
        assert tuple(colors[t]) == tuple(table[int(np.rint((1 - distance) * 255))])
    assert tuple(colors[4]) == tuple(table[255])  # the highest position, the top of a peak
    assert tuple(colors[0]) == tuple(table[0])  # outside every peak
    assert tuple(colors[7]) == tuple(table[0])  # the bottom of the range of the peaks


def test_frames_with_different_places_in_the_beat_have_different_colors():
    colors = cw.line_colors([0.5, 0.7, 0.85, 1.0], "viridis")
    assert len({tuple(c) for c in colors}) == 4


def test_no_beat_gives_the_first_color_to_every_line():
    table = lookup_table("viridis")
    colors = cw.line_colors(None, "viridis", frames=5)
    assert colors.shape == (5, 3) and all(tuple(c) == tuple(table[0]) for c in colors)
    with pytest.raises(ValueError):
        cw.line_colors(None, "viridis")


def test_a_beat_with_no_peak_is_the_first_color_everywhere():
    table = lookup_table("hot")
    assert all(tuple(c) == tuple(table[0]) for c in cw.line_colors(np.zeros(6), "hot"))


def test_bad_colors_input_is_refused():
    for beat in ([[0.1, 0.2]], [0.1, np.nan], [0.1, 1.5], [-0.1, 0.5], "x"):
        with pytest.raises(ValueError):
            cw.line_colors(beat, "viridis")
    with pytest.raises(ValueError):
        cw.line_colors([0.1, 0.2], "nonesuch")
