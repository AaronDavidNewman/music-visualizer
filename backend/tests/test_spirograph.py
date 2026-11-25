"""Spirograph (feature 046): the settings, the curve and its colors, the scale, the tracked notes and the window of history."""

import math

import numpy as np
import pytest

from app.services import spirograph as sp
from app.services.colormaps import COLORMAPS, lookup_table
from app.services.held_notes import hold_loudest

NOTES_MESSAGE = "The number of spirograph notes must be a whole number from 5 to 12."
HISTORY_MESSAGE = "The history length must be a whole number from 5 to 12."


# --- the settings ---------------------------------------------------------------------------------------------------


FADE_MESSAGE = "The history fade must be a number from 0.4 to 0.85."


def test_the_defaults_are_8_notes_a_history_of_8_and_a_fade_of_0_7():
    assert sp.DEFAULT_SPIROGRAPH_SETTINGS == sp.SpirographSettings(8, 8, 0.7)
    assert sp.SpirographSettings(8, 8) == sp.DEFAULT_SPIROGRAPH_SETTINGS  # the fade is optional
    assert (sp.MIN_FADE, sp.MAX_FADE, sp.DEFAULT_FADE) == (0.4, 0.85, 0.7)


@pytest.mark.parametrize("value, expected", [(0.4, 0.4), (0.7, 0.7), (0.85, 0.85), (np.float32(0.5), float(np.float32(0.5))), (1 / 2, 0.5)])
def test_the_fade_is_a_number_from_0_4_to_0_85(value, expected):
    assert sp.check_spirograph_fade(value) == expected and type(sp.check_spirograph_fade(value)) is float


@pytest.mark.parametrize("value", [0.39, 0.86, 0, 1, -0.5, True, False, "0.7", None, float("nan"), float("inf"), [0.7], ""])
def test_a_fade_outside_0_4_to_0_85_or_not_a_number_is_refused_with_the_name_of_the_setting(value):
    with pytest.raises(ValueError) as error:
        sp.check_spirograph_fade(value)
    assert str(error.value) == FADE_MESSAGE


@pytest.mark.parametrize("value, expected", [(5, 5), (8, 8), (12, 12), (6.0, 6), (np.int64(7), 7)])
def test_the_number_of_notes_and_the_history_are_whole_numbers_from_5_to_12(value, expected):
    assert sp.check_spirograph_notes(value) == expected and type(sp.check_spirograph_notes(value)) is int
    assert sp.check_spirograph_history(value) == expected and type(sp.check_spirograph_history(value)) is int


@pytest.mark.parametrize("value", [4, 13, 7.5, 0, -8, True, False, "8", None, float("nan"), float("inf"), [8], ""])
def test_a_value_that_is_not_a_whole_number_from_5_to_12_is_refused_with_the_name_of_the_setting(value):
    with pytest.raises(ValueError) as notes:
        sp.check_spirograph_notes(value)
    assert str(notes.value) == NOTES_MESSAGE
    with pytest.raises(ValueError) as history:
        sp.check_spirograph_history(value)
    assert str(history.value) == HISTORY_MESSAGE


def test_the_settings_are_checked_together_and_returned_as_ints():
    assert sp.check_spirograph_settings(sp.SpirographSettings(9.0, np.int64(11))) == sp.SpirographSettings(9, 11)
    with pytest.raises(ValueError, match="number of spirograph notes"):
        sp.check_spirograph_settings(sp.SpirographSettings(4, 8))
    with pytest.raises(ValueError, match="history length"):
        sp.check_spirograph_settings(sp.SpirographSettings(8, 13))
    assert sp.check_spirograph_settings(sp.SpirographSettings(8, 8, 0.5)).fade == 0.5
    with pytest.raises(ValueError, match="history fade"):
        sp.check_spirograph_settings(sp.SpirographSettings(8, 8, 0.9))


@pytest.mark.parametrize("value", [None, (8, 8), {"notes": 8, "history": 8}, 8])
def test_anything_that_is_not_a_spirograph_settings_is_refused(value):
    with pytest.raises(ValueError, match="SpirographSettings"):
        sp.check_spirograph_settings(value)


# --- the curve (user story 1) ---------------------------------------------------------------------------------------


def formula(val: float, index: int, k: int, pct: float = 1.0) -> tuple[float, float]:
    """The formula in plain Python, point ``k`` of 0 to 999: ``loops = (index mod 12) val``; ``turns = 14 pct + 6`` and ``rc`` 5
    above half way, 4 otherwise; c1 to 2 pi and c2 to 2 pi turns in 1000 steps."""
    turns = 2 * 7 * pct + 6
    rc = 5.0 if pct > 0.5 else 4.0
    c1 = 2 * math.pi * k / 999
    c2 = 2 * math.pi * turns * k / 999
    loops = (index % 12) * val
    return val * (rc * math.cos(c1) + loops * math.cos(c2)), val * (rc * math.sin(c1) + loops * math.sin(c2))


def test_a_curve_has_1000_points_that_are_the_formula():
    rng = np.random.default_rng(46)
    values = rng.random(40)
    indices = rng.integers(0, 84, 40)
    percents = rng.random(40)
    curves = sp.spiro_curves(values, indices, percents)
    assert curves.shape == (40, 1000, 2) and curves.dtype == np.float64
    for n in range(40):
        for k in (0, 1, 137, 499, 500, 998, 999):
            x, y = formula(values[n], int(indices[n]), k, percents[n])
            assert curves[n, k, 0] == pytest.approx(x, abs=1e-6)
            assert curves[n, k, 1] == pytest.approx(y, abs=1e-6)


def test_without_percentages_every_curve_is_at_the_top_of_a_peak():
    values, indices = np.array([0.3, 0.9, 0.5]), np.array([3, 80, 41])
    assert np.array_equal(sp.spiro_curves(values, indices), sp.spiro_curves(values, indices, np.ones(3)))
    x, y = formula(0.9, 80, 321)  # pct 1: 20 turns and rc 5
    assert sp.spiro_curves(values, indices)[1, 321].tolist() == pytest.approx([x, y], abs=1e-6)


def test_the_turns_go_from_6_at_the_bottom_to_20_at_the_top_of_the_peak_and_are_not_rounded():
    assert sp.turns_of([0.0, 0.25, 0.5, 1.0]).tolist() == [6.0, 9.5, 13.0, 20.0]
    assert sp.turns_of(np.zeros((2, 3))).shape == (2, 3)
    assert (sp.SMALL_TURNS, sp.MIN_TURNS) == (7, 6)


def test_the_big_circle_is_5_when_closer_to_the_peak_than_to_the_bottom_and_4_otherwise():
    assert sp.big_radii([0.0, 0.25, 0.5, 0.5000001, 0.75, 1.0]).tolist() == [4.0, 4.0, 4.0, 5.0, 5.0, 5.0]  # half way is not closer to the peak
    assert sp.RC == 5.0


@pytest.mark.parametrize("pct, turns", [(0.0, 6), (0.5, 13), (1.0, 20), (0.25, 9.5)])
def test_the_curve_closes_when_the_turns_are_a_whole_number_and_stays_open_otherwise(pct, turns):
    curve = sp.spiro_curves([0.5], [5], [pct])[0]
    gap = float(np.hypot(*(curve[-1] - curve[0])))
    assert (gap < 1e-9) == (turns == int(turns))
    assert sp.turns_of(pct) == turns


def test_the_first_point_is_on_the_x_axis_at_val_times_rc_plus_the_loops():
    val, index = 0.5, 42  # the letter is 42 mod 12 = 6
    top = sp.spiro_curves([val], [index], [1.0])[0, 0]
    bottom = sp.spiro_curves([val], [index], [0.0])[0, 0]
    assert top[0] == pytest.approx(val * (5 + 6 * val)) and bottom[0] == pytest.approx(val * (4 + 6 * val))
    assert top[1] == pytest.approx(0.0, abs=1e-12) and bottom[1] == pytest.approx(0.0, abs=1e-12)


def test_a_curve_of_value_0_is_all_at_the_center():
    assert np.all(sp.spiro_curves([0.0], [50]) == 0.0)


@pytest.mark.parametrize("index", [0, 12, 24, 72])
def test_a_note_of_letter_0_is_a_plain_circle_of_radius_rc_val(index):
    assert np.allclose(np.hypot(*sp.spiro_curves([0.8], [index], [1.0])[0].T), 4.0)  # rc 5
    assert np.allclose(np.hypot(*sp.spiro_curves([0.8], [index], [0.0])[0].T), 3.2)  # rc 4


def test_the_loops_follow_the_letter_of_the_note_and_not_its_octave():
    same = sp.spiro_curves([0.5, 0.5, 0.5], [5, 17, 65])  # F in three octaves
    assert np.array_equal(same[0], same[1]) and np.array_equal(same[0], same[2])
    other = sp.spiro_curves([0.5, 0.5], [5, 6])
    assert not np.allclose(other[0], other[1])


def test_the_curves_of_many_notes_are_the_curves_made_one_at_a_time():
    values, indices, percents = np.array([0.1, 0.9, 0.5]), np.array([3, 80, 41]), np.array([0.2, 0.9, 0.6])
    many = sp.spiro_curves(values, indices, percents)
    for n in range(3):
        assert np.array_equal(many[n], sp.spiro_curves(values[n : n + 1], indices[n : n + 1], percents[n : n + 1])[0])


@pytest.mark.parametrize(
    "values, indices",
    [
        ([-0.1], [3]),
        ([1.5], [3]),
        ([float("nan")], [3]),
        ([0.5], [84]),
        ([0.5], [-1]),
        ([0.5], [1.5]),
        ([0.5, 0.5], [3]),
        ([[0.5]], [[3]]),
        ("ab", [1, 2]),
    ],
)
def test_values_and_indices_that_are_not_allowed_are_refused(values, indices):
    with pytest.raises(ValueError):
        sp.spiro_curves(values, indices)


@pytest.mark.parametrize("percents", [[0.5, 0.5], [[0.5]], [-0.1], [1.1], [float("nan")], "a", [None]])
def test_percentages_that_are_not_one_number_from_0_to_1_for_each_note_are_refused(percents):
    with pytest.raises(ValueError, match="peak percentages"):
        sp.spiro_curves([0.5], [3], percents)


def test_a_value_of_exactly_1_is_allowed():
    assert sp.spiro_curves([1.0], [83]).shape == (1, 1000, 2)


# --- the place in the local peak -------------------------------------------------------------------------------------------


def test_the_peak_percentage_is_1_minus_the_stretched_beat_distance():
    from app.services.chromatic_decay import beat_distances

    beat = np.array([0.0, 0.6, 0.8, 1.0, 0.7, 0.0])
    assert np.allclose(sp.peak_percents(beat, 6), 1.0 - beat_distances(beat))


def test_the_top_of_the_beat_is_1_and_the_bottom_and_every_frame_outside_a_peak_is_0():
    beat = np.array([0.0, 0.55, 0.7, 0.85, 1.0, 0.0])
    percents = sp.peak_percents(beat, 6)
    assert percents.dtype == np.float64 and percents.shape == (6,)
    assert percents[4] == 1.0 and percents[0] == 0.0 and percents[5] == 0.0 and percents[1] == 0.0
    assert 0.0 < percents[2] < percents[3] < 1.0  # in between, in a straight line
    assert percents.min() >= 0.0 and percents.max() <= 1.0


def test_the_stretch_makes_the_whole_range_reachable_where_the_raw_position_never_falls_below_a_half():
    beat = np.array([0.55, 0.6, 0.7, 0.8, 0.9, 1.0])  # real music: inside a peak the position stays above about 0.55
    raw_near = (beat > 0.5).all()
    percents = sp.peak_percents(beat, 6)
    assert raw_near and percents.min() == 0.0 and percents.max() == 1.0
    assert (percents <= 0.5).any() and (percents > 0.5).any()


def test_without_a_beat_every_frame_is_at_the_top_of_a_peak():
    assert sp.peak_percents(None, 4).tolist() == [1.0] * 4
    assert sp.peak_percents(None, 0).shape == (0,)


def test_the_beat_is_not_changed():
    beat = np.array([0.0, 0.6, 0.8, 1.0])
    before = beat.copy()
    sp.peak_percents(beat, 4)
    assert np.array_equal(beat, before)


@pytest.mark.parametrize(
    "beat, frames",
    [([0.5, 0.5, 0.5], 4), ([1.5, 0.0], 2), ([-0.1, 0.0], 2), ([float("nan"), 0.0], 2), ([[0.5, 0.5]], 2), ("ab", 2), ([0.5], -1), ([0.5], True), ([0.5], 1.5)],
)
def test_a_beat_that_is_not_one_number_from_0_to_1_for_each_frame_is_refused(beat, frames):
    with pytest.raises(ValueError):
        sp.peak_percents(beat, frames)


# --- the colors -----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_13_reduced_colors_are_the_colormap_at_sqrt_k_over_12_times_256(name):
    table = lookup_table(name)
    colors = sp.reduced_colors(name)
    assert colors.shape == (13, 3) and colors.dtype == np.uint8
    for k in range(13):
        position = min(255, int(math.floor(math.sqrt(k / 12) * 256)))
        assert np.array_equal(colors[k], table[position])
    assert np.array_equal(colors[0], table[0])
    assert np.array_equal(colors[12], table[255])


def test_a_colormap_that_is_not_offered_is_refused():
    with pytest.raises(ValueError):
        sp.reduced_colors("not-a-colormap")


@pytest.mark.parametrize("m", range(13))
def test_the_value_m_over_12_takes_color_number_m(m):
    assert sp.color_numbers([m / 12])[0] == m


def test_color_numbers_of_the_edges_and_between():
    numbers = sp.color_numbers([0.0, 0.999, 1.0, 0.04, 0.0833, 1.7])
    assert numbers.tolist() == [0, 11, 12, 0, 0, 12]  # 1.7 would run past the end: held at 12
    assert numbers.dtype == np.intp


@pytest.mark.parametrize("bad", [[float("nan")], [-0.5], ["a"], [[0.5]]])
def test_color_numbers_refuses_what_is_not_a_list_of_values(bad):
    with pytest.raises(ValueError):
        sp.color_numbers(bad)


# --- the extent and the scale ---------------------------------------------------------------------------------------


def test_the_extent_of_a_file_with_no_sound_is_0():
    assert sp.file_extent(np.zeros((6, 5)), np.zeros((6, 5), dtype=np.intp)) == 0.0


def test_the_extent_is_the_largest_val_times_rc_plus_the_loops():
    values = np.array([[0.2, 0.9], [0.5, 0.0]])
    indices = np.array([[10, 40], [83, 5]])
    for percents in (None, [1.0, 1.0], [0.0, 0.0], [0.0, 1.0], [1.0, 0.0]):
        near = np.ones(2) if percents is None else np.array(percents)
        want = max(
            v * ((5.0 if near[row] > 0.5 else 4.0) + (i % 12) * v) for row in range(2) for v, i in zip(values[row], indices[row])
        )
        assert sp.file_extent(values, indices, percents) == pytest.approx(want), percents


def test_the_extent_is_the_farthest_point_of_any_curve_from_the_center():
    rng = np.random.default_rng(7)
    values = rng.random((6, 4))
    indices = rng.integers(0, 84, (6, 4))
    percents = rng.random(6)
    curves = sp.spiro_curves(values.ravel(), indices.ravel(), np.repeat(percents, 4))
    farthest = float(np.hypot(curves[..., 0], curves[..., 1]).max())
    assert sp.file_extent(values, indices, percents) == pytest.approx(farthest, abs=1e-9)


def test_the_percentages_of_the_extent_must_be_one_number_for_each_frame():
    with pytest.raises(ValueError, match="peak percentages"):
        sp.file_extent(np.zeros((3, 4)), np.zeros((3, 4), dtype=np.intp), [0.5, 0.5])


def test_the_extent_refuses_values_and_indices_of_different_shapes():
    with pytest.raises(ValueError):
        sp.file_extent(np.zeros((3, 4)), np.zeros((3, 5), dtype=np.intp))


@pytest.mark.parametrize("width, height", [(600, 400), (150, 100), (400, 400), (90, 60)])
def test_the_scale_makes_the_largest_curve_just_fill_the_room(width, height):
    scale = sp.pixels_per_unit(12.0, width, height)
    assert 12.0 * scale == pytest.approx(min(width, height) / 2 - sp.MARGIN - sp.MAX_LINE_WIDTH)
    assert sp.full_radius(width, height) == pytest.approx(12.0 * scale)


@pytest.mark.parametrize("width, height", [(600, 400), (150, 100), (400, 400), (90, 60), (100, 300)])
def test_the_smallest_curve_is_half_of_the_smallest_side_across_and_never_more_than_the_full_size(width, height):
    assert sp.smallest_radius(width, height) == pytest.approx(min(width, height) / 4)  # a quarter from the center: half across
    assert sp.smallest_radius(width, height) <= sp.full_radius(width, height)  # equal on a picture with no more room than that


@pytest.mark.parametrize("width, height", [(20, 20), (600, 20), (0, 400), (600.5, 400), (True, 400), ("600", 400)])
def test_the_radii_refuse_a_picture_with_no_room_or_a_bad_size(width, height):
    with pytest.raises(ValueError):
        sp.full_radius(width, height)
    with pytest.raises(ValueError):
        sp.smallest_radius(width, height)


def test_the_scale_is_0_when_nothing_sounds():
    assert sp.pixels_per_unit(0.0, 600, 400) == 0.0


@pytest.mark.parametrize("width, height", [(20, 20), (600, 20), (0, 400), (600.5, 400), (True, 400), ("600", 400)])
def test_a_picture_with_no_room_or_a_bad_size_is_refused(width, height):
    with pytest.raises(ValueError):
        sp.pixels_per_unit(5.0, width, height)


@pytest.mark.parametrize("extent", [-1.0, float("nan"), float("inf")])
def test_a_bad_extent_is_refused(extent):
    with pytest.raises(ValueError):
        sp.pixels_per_unit(extent, 600, 400)


# --- the tracked notes (user story 2) -------------------------------------------------------------------------------


def random_notes(frames: int = 12, seed: int = 5) -> np.ndarray:
    """``(frames, 88)`` strengths, most notes weak or 0, a few loud ones."""
    rng = np.random.default_rng(seed)
    notes = rng.random((frames, 88)) ** 5
    notes[rng.random((frames, 88)) < 0.5] = 0.0
    return notes


def test_the_tracked_notes_are_two_arrays_of_frames_by_count():
    values, indices = sp.tracked_notes(random_notes(), 7)
    assert values.shape == indices.shape == (12, 7)
    assert values.dtype == np.float64 and indices.dtype == np.intp


def test_the_loudest_note_of_the_file_is_value_1_and_the_others_are_the_square_root_of_their_share():
    notes = random_notes()
    notes[3, 20] = 5.0
    values, indices = sp.tracked_notes(notes, 5)
    assert values.max() == 1.0
    assert values[3, 0] == 1.0 and indices[3, 0] == 20
    assert values.min() >= 0.0
    assert values[3, 1] == pytest.approx(math.sqrt(notes[3, indices[3, 1]] / 5.0))


def test_a_value_is_the_square_root_of_the_strength_over_the_largest_strength_of_all_88_columns():
    notes = random_notes()
    notes[2, 86] = 100.0  # one of the four highest notes, which are not drawn: it is still the loudest of the file
    values, indices = sp.tracked_notes(notes, 5)
    assert values.max() < 1.0
    frame = 6
    for place in range(5):
        if values[frame, place] > 0:
            assert values[frame, place] == pytest.approx(math.sqrt(notes[frame, indices[frame, place]] / 100.0))


@pytest.mark.parametrize("extra", [0, 2, 5])
def test_the_indices_are_the_held_notes_of_the_first_84_columns(extra):
    notes = random_notes(30, seed=9)
    _, indices = sp.tracked_notes(notes, 6, extra)
    assert np.array_equal(indices, hold_loudest(notes[:, :84], 6, extra))


def test_with_no_extra_notes_the_indices_are_the_plain_loudest_in_order():
    notes = random_notes(20, seed=11)
    _, indices = sp.tracked_notes(notes, 8)
    assert np.array_equal(indices, np.argsort(-notes[:, :84], axis=1, kind="stable")[:, :8])


def test_a_silent_frame_has_value_0_in_every_place_and_a_silent_file_does_not_divide_by_zero():
    notes = random_notes()
    notes[4] = 0.0
    values, _ = sp.tracked_notes(notes, 6)
    assert not values[4].any()
    silent, _ = sp.tracked_notes(np.zeros((5, 88)), 6)
    assert silent.shape == (5, 6) and not silent.any()


def test_fewer_sounding_notes_than_places_leave_the_last_places_at_value_0():
    notes = np.zeros((3, 88))
    notes[1, 10] = 0.5
    notes[1, 40] = 0.25
    values, indices = sp.tracked_notes(notes, 5)
    assert values[1].tolist() == [1.0, pytest.approx(math.sqrt(0.5)), 0.0, 0.0, 0.0]
    assert indices[1, :2].tolist() == [10, 40]


def test_equal_strengths_go_to_the_lower_note_first():
    notes = np.zeros((1, 88))
    notes[0, [30, 12, 50, 12 + 1]] = 1.0
    _, indices = sp.tracked_notes(notes, 5)
    assert indices[0, :4].tolist() == [12, 13, 30, 50]


def test_the_input_is_not_changed():
    notes = random_notes()
    before = notes.copy()
    sp.tracked_notes(notes, 6, 2)
    assert np.array_equal(notes, before)


@pytest.mark.parametrize("count", [4, 13, 7.5, True, "8", None])
def test_a_count_outside_5_to_12_is_refused(count):
    with pytest.raises(ValueError, match="number of spirograph notes"):
        sp.tracked_notes(random_notes(), count)


@pytest.mark.parametrize(
    "bad",
    [np.zeros((3, 80)), np.zeros(88), np.full((3, 88), -1.0), np.full((3, 88), np.nan), "abc"],
)
def test_note_values_that_are_not_frames_by_at_least_84_numbers_of_0_or_more_are_refused(bad):
    with pytest.raises(ValueError):
        sp.tracked_notes(bad, 6)


def test_an_extra_above_the_count_is_refused():
    with pytest.raises(ValueError):
        sp.tracked_notes(random_notes(), 5, 6)


# --- the window of history ------------------------------------------------------------------------------------------

W, H = 600, 400


def window_inputs(frames: int = 30, notes: int = 6) -> tuple[np.ndarray, np.ndarray]:
    """Values and indices in which every row and place has its own number, so that a mix-up of rows would show."""
    values = np.array([[(t * notes + j + 1) / (frames * notes + 5) for j in range(notes)] for t in range(frames)])
    indices = np.array([[(t * 7 + j * 3) % 84 for j in range(notes)] for t in range(frames)], dtype=np.intp)
    return values, indices


def expected_pixels(values, indices, scale: float, percents=None) -> np.ndarray:
    """The pixels of curves of the given values, indices and peak percentages (1 when not given): the formula's shape, sized so
    that the farthest point is between a quarter of the smallest side and the full radius from the center, by ``ext * scale / full``."""
    full = min(W, H) / 2 - 10 - sp.MAX_LINE_WIDTH
    smallest = min(W, H) / 4
    near = np.ones(len(values)) if percents is None else np.asarray(percents, dtype=float)
    units = sp.spiro_curves(np.asarray(values, dtype=float), np.asarray(indices), near)
    out = np.empty_like(units)
    for n, (val, index) in enumerate(zip(values, indices)):
        ext = val * ((5.0 if near[n] > 0.5 else 4.0) + (index % 12) * val)
        radius = smallest + (full - smallest) * min(1.0, ext * scale / full)
        out[n, :, 0] = W / 2 + units[n, :, 0] * radius / ext
        out[n, :, 1] = H / 2 - units[n, :, 1] * radius / ext
    return out


def entry_percents(frames: int = 30) -> np.ndarray:
    """A peak percentage for each frame that goes up and down across a half, so that the entries of a window differ."""
    return (np.sin(np.arange(frames) * 0.9) + 1) / 2


def radii(curves: np.ndarray) -> np.ndarray:
    """The distance of the farthest point of each curve (in pixels) from the center of the picture."""
    return np.hypot(curves[..., 0] - W / 2, curves[..., 1] - H / 2).max(axis=1)


def test_a_picture_well_into_the_file_has_notes_times_history_curves():
    values, indices = window_inputs()
    for history in (5, 8, 12):
        curves, numbers, widths = sp.window_curves(values, indices, 25, history, 10.0, W, H)
        assert curves.shape == (6 * history, 1000, 2) and numbers.shape == (6 * history,) and widths.shape == (6 * history,)


def test_the_first_frames_use_the_entries_that_exist():
    values, indices = window_inputs()
    for frame in range(0, 8):
        curves, _, _ = sp.window_curves(values, indices, frame, 8, 10.0, W, H)
        assert len(curves) == 6 * (frame + 1)
    assert len(sp.window_curves(values, indices, 7, 8, 10.0, W, H)[0]) == 6 * 8
    assert len(sp.window_curves(values, indices, 8, 8, 10.0, W, H)[0]) == 6 * 8  # the window is full and slides


def test_a_place_with_value_0_draws_nothing():
    values, indices = window_inputs()
    values[19, 2] = 0.0
    values[20, :] = 0.0
    curves, numbers, widths = sp.window_curves(values, indices, 22, 8, 10.0, W, H)
    assert len(curves) == 6 * 8 - 1 - 6 and len(numbers) == len(curves) == len(widths)


def test_a_step_uses_the_value_and_the_index_of_its_own_entry_and_place_in_the_order_of_the_loops():
    values, indices = window_inputs()
    frame, history, scale = 20, 6, 12.5
    fade = 0.6
    curves, numbers, _ = sp.window_curves(values, indices, frame, history, scale, W, H, fade)
    k = 0
    for row in range(frame - history + 1, frame + 1):  # the outer loop: oldest entry first
        for place in range(6):  # the inner loop: loudest place first
            val, index = values[row, place] * fade ** (frame - row), int(indices[row, place])  # the value fades, the index does not
            want = expected_pixels([val], [index], scale)[0]
            for point in (0, 321, 999):
                assert curves[k, point, 0] == pytest.approx(want[point, 0], abs=1e-6)
                assert curves[k, point, 1] == pytest.approx(want[point, 1], abs=1e-6)
            assert numbers[k] == sp.color_numbers([val])[0]
            k += 1
    assert k == len(curves)


def test_consecutive_windows_share_all_but_one_entry_and_each_shared_entry_is_one_fade_smaller():
    values, indices = window_inputs()
    fade, scale = 0.5, 10.0
    first, _, _ = sp.window_curves(values, indices, 15, 8, scale, W, H, fade)  # the entries (rows) 8 to 15
    second, _, _ = sp.window_curves(values, indices, 16, 8, scale, W, H, fade)  # the entries 9 to 16: row 8 has gone, row 16 is new
    assert len(first) == len(second) == 48
    ages = np.arange(6, -1, -1)  # the shared rows 9 to 15 are 6, 5, ..., 0 frames old in the first window
    for window, extra_age in ((first[6:], 0), (second[:-6], 1)):
        faded = (values[9:16] * fade ** (ages + extra_age)[:, None]).reshape(-1)
        assert np.allclose(window, expected_pixels(faded, indices[9:16].reshape(-1), scale))


def test_the_newest_entry_is_not_faded_and_each_older_one_is_multiplied_once_more():
    values, indices = window_inputs()
    for fade in (0.4, 0.7, 0.85):
        curves, _, _ = sp.window_curves(values, indices, 20, 5, 1.0, W, H, fade)
        for entry, row in enumerate(range(16, 21)):
            want = expected_pixels(values[row] * fade ** (20 - row), indices[row], 1.0)
            assert np.allclose(curves[entry * 6 : entry * 6 + 6], want), (fade, row)


def test_a_lower_fade_makes_the_older_curves_smaller_and_leaves_the_newest_alone():
    values, indices = window_inputs()
    slow, slow_numbers, slow_widths = sp.window_curves(values, indices, 20, 8, 10.0, W, H, 0.85)
    fast, fast_numbers, fast_widths = sp.window_curves(values, indices, 20, 8, 10.0, W, H, 0.4)
    assert np.array_equal(slow[-6:], fast[-6:]) and np.array_equal(slow_numbers[-6:], fast_numbers[-6:])  # the frame's own entry
    assert (radii(fast[:-6]) < radii(slow[:-6])).all()  # a lower fade: a smaller value, a smaller share, a smaller curve
    assert (fast_numbers[:-6] <= slow_numbers[:-6]).all()  # the colors are lower in the colormap
    assert np.array_equal(slow_widths, fast_widths)  # the line width follows the age only, not the fade


def test_the_fade_is_the_default_of_0_7_when_it_is_not_given():
    values, indices = window_inputs()
    given = sp.window_curves(values, indices, 20, 8, 10.0, W, H, 0.7)
    assert np.array_equal(given[0], sp.window_curves(values, indices, 20, 8, 10.0, W, H)[0])


def test_a_fade_that_is_not_allowed_is_refused_in_the_window():
    values, indices = window_inputs()
    for fade in (0.3, 0.9, True, "0.5", float("nan")):
        with pytest.raises(ValueError, match="history fade"):
            sp.window_curves(values, indices, 5, 8, 1.0, W, H, fade)


def test_a_curve_takes_the_turns_and_the_big_radius_of_its_own_entrys_frame():
    values, indices = window_inputs()
    percents = entry_percents()
    frame, history, scale, fade = 20, 6, 12.5, 0.6
    curves, _, _ = sp.window_curves(values, indices, frame, history, scale, W, H, fade, percents)
    assert len({round(float(percents[r]), 6) for r in range(frame - history + 1, frame + 1)}) == history  # the entries differ
    assert any(percents[r] > 0.5 for r in range(15, 21)) and any(percents[r] <= 0.5 for r in range(15, 21))  # and fall on both sides
    k = 0
    for row in range(frame - history + 1, frame + 1):
        for place in range(6):
            val, index = values[row, place] * fade ** (frame - row), int(indices[row, place])
            want = expected_pixels([val], [index], scale, [percents[row]])[0]
            for point in (0, 321, 999):
                assert curves[k, point, 0] == pytest.approx(want[point, 0], abs=1e-6)
                assert curves[k, point, 1] == pytest.approx(want[point, 1], abs=1e-6)
            k += 1
    assert k == len(curves)


def test_an_entry_keeps_its_own_percentage_in_the_pictures_that_it_is_in():
    values, indices = window_inputs()
    percents = entry_percents()
    first, _, _ = sp.window_curves(values, indices, 15, 8, 10.0, W, H, 0.5, percents)
    second, _, _ = sp.window_curves(values, indices, 16, 8, 10.0, W, H, 0.5, percents)
    ages = np.arange(6, -1, -1)  # the shared rows 9 to 15
    for window, extra_age in ((first[6:], 0), (second[:-6], 1)):
        faded = (values[9:16] * 0.5 ** (ages + extra_age)[:, None]).reshape(-1)
        assert np.allclose(window, expected_pixels(faded, indices[9:16].reshape(-1), 10.0, np.repeat(percents[9:16], 6)))


def test_without_percentages_the_window_is_every_frame_at_the_top_of_a_peak():
    values, indices = window_inputs()
    plain = sp.window_curves(values, indices, 20, 8, 10.0, W, H)
    for given in (None, np.ones(30)):
        again = sp.window_curves(values, indices, 20, 8, 10.0, W, H, 0.7, given)
        assert all(np.array_equal(a, b) for a, b in zip(plain, again))
    assert not np.allclose(plain[0], sp.window_curves(values, indices, 20, 8, 10.0, W, H, 0.7, np.zeros(30))[0])


@pytest.mark.parametrize("percents", [np.zeros(29), np.zeros(31), np.full(30, 1.5), np.full(30, -0.1), np.full(30, np.nan), np.zeros((30, 1))])
def test_percentages_that_are_not_one_number_from_0_to_1_for_each_frame_are_refused_in_the_window(percents):
    values, indices = window_inputs()
    with pytest.raises(ValueError, match="peak percentages"):
        sp.window_curves(values, indices, 5, 8, 1.0, W, H, 0.7, percents)


# --- the size between half and full, and the line width by age ----------------------------------------------------------


def test_every_curve_reaches_between_half_the_smallest_side_across_and_the_full_size_and_the_largest_of_the_file_the_full_size():
    values, indices = window_inputs()
    percents = entry_percents()
    scale = sp.pixels_per_unit(sp.file_extent(values, indices, percents), W, H)
    full, smallest = sp.full_radius(W, H), sp.smallest_radius(W, H)
    for frame in (0, 5, 12, 29):
        curves, _, _ = sp.window_curves(values, indices, frame, 8, scale, W, H, 0.85, percents)
        reach = radii(curves)
        assert (reach >= smallest - 1e-9).all() and (reach <= full + 1e-9).all(), frame
    assert smallest == pytest.approx(min(W, H) / 4)
    rc = np.where(percents > 0.5, 5.0, 4.0)[:, None]
    farthest = (values * (rc + np.mod(indices, 12) * values)).max(axis=1)  # the extent of each frame's loudest curve
    loudest = int(farthest.argmax())  # the frame of the curve with the largest extent of the file
    curves, _, _ = sp.window_curves(values, indices, loudest, 5, scale, W, H, 0.85, percents)
    assert radii(curves).max() == pytest.approx(full)  # in its own frame, not faded, it fills the room


def test_a_tiny_value_is_still_half_the_smallest_side_across():
    values = np.full((6, 2), 1e-6)
    values[0, 0] = 1.0  # sets the extent of the file
    indices = np.full((6, 2), 40, dtype=np.intp)
    scale = sp.pixels_per_unit(sp.file_extent(values, indices), W, H)
    curves, _, _ = sp.window_curves(values, indices, 5, 5, scale, W, H, 0.4)
    assert radii(curves).min() == pytest.approx(min(W, H) / 4, rel=1e-3)
    assert radii(curves).min() >= min(W, H) / 4


def test_a_bigger_extent_is_a_bigger_curve_between_the_two_sizes():
    values = np.array([[0.2, 0.5, 0.9, 1.0]] * 5)
    indices = np.array([[30, 30, 30, 30]] * 5, dtype=np.intp)
    scale = sp.pixels_per_unit(sp.file_extent(values, indices), W, H)
    curves, _, _ = sp.window_curves(values, indices, 0, 5, scale, W, H, 0.85)
    assert (np.diff(radii(curves)) > 0).all()


@pytest.mark.parametrize(
    "history, widths",
    [(5, [3, 2, 2, 1, 1]), (8, [3, 2, 2, 2, 2, 1, 1, 1]), (12, [3, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1])],
)
def test_the_line_width_is_3_for_the_newest_entry_and_falls_from_2_to_1_with_the_age_rounded_to_whole_pixels(history, widths):
    got = [sp.entry_line_width(age, history) for age in range(history)]
    assert got == widths and all(type(w) is int for w in got)
    assert got == sorted(got, reverse=True) and min(got) >= 1  # never wider for an older entry


@pytest.mark.parametrize("history", range(5, 13))
def test_the_newest_entry_is_always_3_and_every_older_entry_is_at_least_1_thinner_whatever_the_history(history):
    widths = [sp.entry_line_width(age, history) for age in range(history)]
    assert widths[0] == sp.MAX_LINE_WIDTH == 3  # hard-coded, whatever the history length (5 was too thick)
    assert max(widths[1:]) <= 2 and widths[1] == 2 and widths[-1] == sp.MIN_LINE_WIDTH == 1
    assert widths == sorted(widths, reverse=True)


@pytest.mark.parametrize("age, history", [(-1, 8), (8, 8), (1.5, 8), (True, 8), ("1", 8), (0, 4), (0, 13)])
def test_an_age_or_history_that_is_not_allowed_is_refused(age, history):
    with pytest.raises(ValueError):
        sp.entry_line_width(age, history)


def test_the_curves_of_a_window_have_the_width_of_their_entry():
    values, indices = window_inputs()
    values[19, :] = 0.0  # a silent entry draws nothing and takes none of the widths
    curves, _, widths = sp.window_curves(values, indices, 22, 8, 10.0, W, H)
    assert len(widths) == len(curves) == 6 * 7
    ages = [age for age in range(7, -1, -1) if 22 - age != 19]  # the oldest entry first
    want = np.repeat([sp.entry_line_width(age, 8) for age in ages], 6)
    assert np.array_equal(widths, want)
    assert widths[-6:].tolist() == [3.0] * 6 and widths[:6].tolist() == [1.0] * 6  # the frame's own entry is 3, the oldest 1


def test_in_the_first_frames_the_newest_entry_is_still_the_widest():
    values, indices = window_inputs()
    _, _, widths = sp.window_curves(values, indices, 2, 8, 10.0, W, H)
    assert widths.tolist() == [2.0] * 6 + [2.0] * 6 + [3.0] * 6  # ages 2, 1, 0 of a history of 8: 1.83 and 2 round to 2


@pytest.mark.parametrize(
    "frame, history, scale",
    [(-1, 8, 1.0), (30, 8, 1.0), (3.5, 8, 1.0), (True, 8, 1.0), (5, 4, 1.0), (5, 13, 1.0), (5, 8, -1.0), (5, 8, float("nan"))],
)
def test_a_frame_history_or_scale_that_is_not_allowed_is_refused(frame, history, scale):
    values, indices = window_inputs()
    with pytest.raises(ValueError):
        sp.window_curves(values, indices, frame, history, scale, W, H)


def test_values_and_indices_of_different_shapes_are_refused_in_the_window():
    values, indices = window_inputs()
    with pytest.raises(ValueError):
        sp.window_curves(values, indices[:, :5], 5, 8, 1.0, W, H)
