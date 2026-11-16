"""Polychord (feature 042): the settings, the letters, the turns, the copies, the tempos and colors, the segments."""

import math

import numpy as np
import pytest

from app.services import polychord as pc

NOTES_MESSAGE = "The number of notes must be a whole number from 5 to 8."
MIN_COPIES_MESSAGE = "The minimum number of copies must be a whole number from 1 to 12."
MAX_COPIES_MESSAGE = "The maximum number of copies must be a whole number from 1 to 12."
ORDER_MESSAGE = "The maximum number of copies must not be less than the minimum."
ROTATION_MESSAGE = "The rotation must be a number from -360 to 360 degrees a second."


# --- the settings ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("value, expected", [(5, 5), (6, 6), (8, 8), (6.0, 6), (np.int64(7), 7)])
def test_the_number_of_notes_is_a_whole_number_from_5_to_8(value, expected):
    assert pc.check_polychord_notes(value) == expected
    assert type(pc.check_polychord_notes(value)) is int


@pytest.mark.parametrize("value", [4, 9, 5.5, 0, -6, True, False, "6", None, float("nan"), float("inf"), [6], ""])
def test_a_number_of_notes_that_is_not_a_whole_number_from_5_to_8_is_refused(value):
    with pytest.raises(ValueError) as error:
        pc.check_polychord_notes(value)
    assert str(error.value) == NOTES_MESSAGE


@pytest.mark.parametrize("value, expected", [(1, 1), (12, 12), (3.0, 3), (np.int64(4), 4)])
def test_the_copies_are_whole_numbers_from_1_to_12(value, expected):
    assert pc.check_polychord_copies(value, "minimum") == expected
    assert pc.check_polychord_copies(value, "maximum") == expected


@pytest.mark.parametrize("value", [0, 13, 2.5, -1, True, "3", None, float("nan"), float("inf")])
def test_copies_that_are_not_whole_numbers_from_1_to_12_are_refused_with_the_name_of_the_setting(value):
    with pytest.raises(ValueError) as error:
        pc.check_polychord_copies(value, "minimum")
    assert str(error.value) == MIN_COPIES_MESSAGE
    with pytest.raises(ValueError) as error:
        pc.check_polychord_copies(value, "maximum")
    assert str(error.value) == MAX_COPIES_MESSAGE


@pytest.mark.parametrize("value, expected", [(-360, -360.0), (0, 0.0), (15.5, 15.5), (360, 360.0), (np.float32(2.5), 2.5)])
def test_the_rotation_is_a_number_from_minus_360_to_360(value, expected):
    assert pc.check_polychord_rotation(value) == expected
    assert type(pc.check_polychord_rotation(value)) is float


@pytest.mark.parametrize("value", [-360.1, 361, 1000, True, "15", None, float("nan"), float("inf"), float("-inf")])
def test_a_rotation_outside_the_limits_or_not_a_number_is_refused(value):
    with pytest.raises(ValueError) as error:
        pc.check_polychord_rotation(value)
    assert str(error.value) == ROTATION_MESSAGE


def test_the_defaults_are_6_notes_3_to_12_copies_and_15_degrees_a_second():
    defaults = pc.DEFAULT_POLYCHORD_SETTINGS
    assert (defaults.notes, defaults.min_copies, defaults.max_copies, defaults.rotation) == (6, 3, 12, 15.0)
    assert pc.check_polychord_settings(defaults) == defaults


def test_settings_are_checked_together_and_a_maximum_under_the_minimum_is_refused():
    assert pc.check_polychord_settings(pc.PolychordSettings(5, 7, 7, 0.0)).max_copies == 7
    with pytest.raises(ValueError) as error:
        pc.check_polychord_settings(pc.PolychordSettings(6, 8, 7, 15.0))
    assert str(error.value) == ORDER_MESSAGE
    with pytest.raises(ValueError):
        pc.check_polychord_settings(pc.PolychordSettings(9, 3, 12, 15.0))
    with pytest.raises(ValueError):
        pc.check_polychord_settings("not settings")


def test_the_settings_are_a_frozen_value():
    with pytest.raises(Exception):
        pc.DEFAULT_POLYCHORD_SETTINGS.notes = 7  # type: ignore[misc]


# --- the letters ----------------------------------------------------------------------------------------------------

# the letters as the application counts them: 0 is A
A, A_SHARP, B, C, C_SHARP, D, D_SHARP, E, F, F_SHARP, G, G_SHARP = range(12)


def note_values(frames: list[dict[int, float]]) -> np.ndarray:
    """``(frames, 88)`` note values from one dict per frame of ``{column: value}``."""
    values = np.zeros((len(frames), 88))
    for row, notes in enumerate(frames):
        for column, value in notes.items():
            values[row, column] = value
    return values


def oracle_letters(row: np.ndarray, count: int) -> list[int]:
    """The ``count`` loudest of the first 84 notes (ties to the lower note), as letters, -1 for the missing."""
    ranked = sorted(range(84), key=lambda note: (-row[note], note))
    letters = [note % 12 for note in ranked[:count] if row[note] > 0]
    return letters + [-1] * (count - len(letters))


def test_the_loudest_notes_are_the_loudest_of_the_first_84_columns_as_letters_loudest_first():
    rng = np.random.default_rng(7)
    for _ in range(40):
        values = rng.integers(0, 5, size=(6, 88)).astype(float) * rng.random()  # lots of zeros and of ties
        for count in (5, 6, 7, 8):
            letters = pc.loudest_letters(values, count)
            assert letters.shape == (6, count)
            assert letters.dtype.kind == "i"
            for row in range(6):
                assert list(letters[row]) == oracle_letters(values[row], count)


def test_a_tie_in_loudness_goes_to_the_lower_note_and_the_same_letter_can_appear_twice():
    values = note_values([{3: 1.0, 15: 1.0, 27: 1.0, 40: 0.5}])  # C in three octaves, then E
    assert list(pc.loudest_letters(values, 5)[0]) == [C, C, C, (40 % 12), -1]
    values = note_values([{20: 0.5, 5: 0.5}])  # two different notes with the same value: the lower one first
    assert list(pc.loudest_letters(values, 5)[0][:2]) == [5 % 12, 20 % 12]


def test_a_note_that_does_not_sound_is_not_used_and_a_silent_frame_has_no_letters():
    values = note_values([{}, {10: 0.2}])
    letters = pc.loudest_letters(values, 6)
    assert list(letters[0]) == [-1] * 6
    assert list(letters[1]) == [10 % 12] + [-1] * 5


def test_the_columns_after_the_84th_are_not_notes_of_a_letter_and_the_input_is_not_changed():
    values = note_values([{84: 9.0, 87: 9.0, 20: 0.1}])
    before = values.copy()
    assert list(pc.loudest_letters(values, 5)[0]) == [20 % 12, -1, -1, -1, -1]
    assert np.array_equal(values, before)


@pytest.mark.parametrize("bad", [np.zeros(88), np.zeros((3, 4)), np.zeros((2, 3, 88)), "text", None])
def test_note_values_of_the_wrong_shape_are_refused(bad):
    with pytest.raises(ValueError):
        pc.loudest_letters(bad, 6)


@pytest.mark.parametrize("count", [4, 9, 6.5, True, None])
def test_a_count_of_letters_outside_5_to_8_is_refused(count):
    with pytest.raises(ValueError):
        pc.loudest_letters(np.zeros((2, 88)), count)


def test_nan_or_negative_note_values_are_refused():
    for bad in (np.nan, np.inf, -1.0):
        values = np.zeros((1, 88))
        values[0, 5] = bad
        with pytest.raises(ValueError):
            pc.loudest_letters(values, 6)


# --- the turns ------------------------------------------------------------------------------------------------------

# from C, the interval to each letter, in order of the circle of fifths: C G D A E B F# C# G# D# A# F
AFTER_C = [(C, 0), (G, 30), (D, 60), (A, 90), (E, 120), (B, 150), (F_SHARP, 180), (C_SHARP, -150), (G_SHARP, -120), (D_SHARP, -90), (A_SHARP, -60), (F, -30)]


def oracle_turn(previous: int, letter: int) -> int:
    """The turn in degrees counted from the semitones between the letters: the number of fifths up that gives that
    interval is ``7 x interval mod 12`` (7 x 7 is 1 mod 12), the shorter way round, the tritone as +6."""
    fifths = (7 * ((letter - previous) % 12)) % 12
    if fifths > 6:
        fifths -= 12
    return 30 * fifths


@pytest.mark.parametrize("letter, degrees", AFTER_C)
def test_the_twelve_intervals_from_c_turn_as_the_user_described(letter, degrees):
    turns = pc.link_turns(np.array([[C, letter, -1, -1, -1]]))
    assert turns[0, 0] == 0
    assert turns[0, 1] == degrees


def test_a_fifth_up_is_plus_30_a_fourth_up_minus_30_the_same_letter_straight_and_the_tritone_backwards():
    assert pc.link_turns(np.array([[C, G, -1, -1, -1]]))[0, 1] == 30
    assert pc.link_turns(np.array([[C, F, -1, -1, -1]]))[0, 1] == -30
    assert pc.link_turns(np.array([[C, C, -1, -1, -1]]))[0, 1] == 0
    assert pc.link_turns(np.array([[C, F_SHARP, -1, -1, -1]]))[0, 1] == 180
    assert pc.link_turns(np.array([[F_SHARP, C, -1, -1, -1]]))[0, 1] == 180


def test_every_pair_of_letters_turns_by_the_oracle_and_between_minus_150_and_180():
    for previous in range(12):
        for letter in range(12):
            turn = pc.link_turns(np.array([[previous, letter, -1, -1, -1]]))[0, 1]
            assert turn == oracle_turn(previous, letter)
            assert -150 <= turn <= 180


def test_a_turn_is_measured_from_the_previous_link_not_from_the_loudest():
    turns = pc.link_turns(np.array([[C, G, D, A, E, B]]))[0]
    assert list(turns) == [0, 30, 30, 30, 30, 30]  # each a fifth above the one before
    turns = pc.link_turns(np.array([[C, G, C, F, F_SHARP, -1]]))[0]
    assert list(turns) == [0, 30, -30, -30, oracle_turn(F, F_SHARP), 0]


def test_a_missing_letter_turns_nothing_and_the_frames_are_independent():
    letters = np.array([[C, D, -1, -1, -1], [G, -1, -1, -1, -1], [-1, -1, -1, -1, -1]])
    turns = pc.link_turns(letters)
    assert turns.shape == (3, 5)
    assert turns.dtype == np.float64
    assert list(turns[0]) == [0, 60, 0, 0, 0]
    assert list(turns[1]) == [0, 0, 0, 0, 0]
    assert list(turns[2]) == [0, 0, 0, 0, 0]


@pytest.mark.parametrize("bad", [np.zeros(5), np.full((2, 5), 12), np.full((2, 5), -2), np.full((2, 5), 1.5), "text", None])
def test_letters_that_are_not_whole_numbers_from_minus_1_to_11_in_two_dimensions_are_refused(bad):
    with pytest.raises(ValueError):
        pc.link_turns(bad)


# --- the segments ---------------------------------------------------------------------------------------------------

SIZES = [(600, 400), (300, 200), (200, 600), (1800, 1200), (100, 100)]


def unit(angle_degrees: float) -> tuple[float, float]:
    """The direction on the screen (y down) of an angle in degrees clockwise from straight up."""
    radians = math.radians(angle_degrees)
    return math.sin(radians), -math.cos(radians)


def oracle_width(fraction: float, height: int) -> float:
    start = height / 60
    return max(1.0, start - (start - start / 5) * fraction)


def figure(letters: list[int], start: float, copies: int, width: int, height: int, notes: int):
    letters_row = np.array(letters + [-1] * (notes - len(letters)))
    turns = pc.link_turns(letters_row[None, :])[0]
    return pc.figure_segments(turns, letters_row, start, copies, width, height, notes)


def test_the_first_link_starts_at_the_center_and_each_link_starts_where_the_previous_one_ended():
    notes = 6
    segments, _ = figure([C, G, D, F_SHARP, C, A], 20.0, 1, 600, 400, notes)
    assert segments.shape == (notes * pc.PIECES_PER_LINK, 2, 2)
    assert tuple(segments[0, 0]) == (300.0, 200.0)
    for index in range(1, len(segments)):
        assert np.allclose(segments[index, 0], segments[index - 1, 1])  # pieces and links join end to start


def test_the_links_follow_the_oracle_walk_with_the_turns_added_to_the_direction():
    letters = [C, G, D, F_SHARP, C, A, E]
    notes = 7
    length = pc.link_length(600, 400, notes)
    x, y = 300.0, 200.0
    angle = 35.0
    expected_ends = []
    for index, letter in enumerate(letters):
        if index:
            angle += oracle_turn(letters[index - 1], letter)
        dx, dy = unit(angle)
        x, y = x + length * dx, y + length * dy
        expected_ends.append((x, y))
    segments, _ = figure(letters, 35.0, 1, 600, 400, notes)
    for index, end in enumerate(expected_ends):
        last_piece = segments[(index + 1) * pc.PIECES_PER_LINK - 1, 1]
        assert last_piece == pytest.approx(end, abs=1e-6)


def test_every_link_has_the_same_length_and_is_cut_into_equal_pieces_in_a_straight_line():
    notes = 8
    length = pc.link_length(600, 400, notes)
    segments, _ = figure([C, D, E, F, G, A, B, C_SHARP], 0.0, 1, 600, 400, notes)
    for link in range(notes):
        pieces = segments[link * pc.PIECES_PER_LINK:(link + 1) * pc.PIECES_PER_LINK]
        total = pieces[-1, 1] - pieces[0, 0]
        assert math.hypot(*total) == pytest.approx(length)
        for piece in pieces:
            assert math.hypot(*(piece[1] - piece[0])) == pytest.approx(length / pc.PIECES_PER_LINK)
            direction = (piece[1] - piece[0]) / np.linalg.norm(piece[1] - piece[0])
            assert direction == pytest.approx(total / np.linalg.norm(total))


def test_the_width_falls_in_a_straight_line_along_the_figure_so_no_link_ends_wider_than_the_next_starts():
    for notes, letters in ((6, [C, G, D, A, E, B]), (8, [C, D, E, F, G, A, B, C_SHARP]), (5, [C, G])):
        _, widths = figure(letters, 0.0, 1, 600, 400, notes)
        count = len(letters)
        assert widths.shape == (count * pc.PIECES_PER_LINK,)
        for index, value in enumerate(widths):
            fraction = (index + 0.5) / (count * pc.PIECES_PER_LINK)
            assert value == pytest.approx(oracle_width(fraction, 400))
        steps = np.diff(widths)
        assert (steps < 0).all()
        assert steps == pytest.approx(steps[0])  # the same step at a join of two links as inside a link


def test_a_figure_with_fewer_links_still_ends_thin_and_a_wide_start_is_height_over_60():
    _, widths = figure([C, G], 0.0, 1, 600, 400, 8)
    assert widths[0] == pytest.approx(400 / 60 * (1 - 0.8 * 0.5 / 12))
    assert widths[-1] == pytest.approx(400 / 60 * (1 - 0.8 * 11.5 / 12))


def test_a_width_is_never_under_one_pixel():
    _, widths = figure([C, G, D, A, E, B], 0.0, 1, 200, 120, 6)  # 2 pixels at the start, 0.4 at the end by the line
    assert widths.min() >= 1.0


def test_copies_follow_copy_zero_each_turned_a_further_30_degrees_about_the_center():
    notes = 6
    letters = [C, G, D, F_SHARP, A, E]
    base, base_widths = figure(letters, 12.0, 1, 600, 400, notes)
    many, many_widths = figure(letters, 12.0, 5, 600, 400, notes)
    assert many.shape == (5 * len(base), 2, 2)
    for copy in range(5):
        theta = math.radians(30 * copy)
        rotation = np.array([[math.cos(theta), -math.sin(theta)], [math.sin(theta), math.cos(theta)]])
        centered = base - np.array([300.0, 200.0])
        expected = centered @ rotation.T + np.array([300.0, 200.0])  # y is down, so this is clockwise on screen
        assert many[copy * len(base):(copy + 1) * len(base)] == pytest.approx(expected, abs=1e-6)
        assert many_widths[copy * len(base):(copy + 1) * len(base)] == pytest.approx(base_widths)


def test_no_letters_gives_no_pieces():
    segments, widths = figure([], 0.0, 12, 600, 400, 6)
    assert segments.shape == (0, 2, 2)
    assert widths.shape == (0,)


def reach(width: int, height: int) -> float:
    """The farthest a figure of notes straight links gets from the center: the room, 1.4 times over."""
    return 1.4 * (min(width, height) / 2 - pc.MARGIN - pc.start_width(height) / 2)


@pytest.mark.parametrize("width, height", SIZES)
def test_no_piece_is_ever_farther_from_the_center_than_the_straight_figure_reaches(width, height):
    rng = np.random.default_rng(width + height)
    for _ in range(60):
        notes = int(rng.integers(5, 9))
        count = int(rng.integers(0, notes + 1))
        letters = [int(v) for v in rng.integers(0, 12, size=count)]
        segments, _ = figure(letters, float(rng.uniform(-720, 720)), int(rng.integers(1, 13)), width, height, notes)
        if not len(segments):
            continue
        distances = np.hypot(*(segments.reshape(-1, 2) - np.array([width / 2, height / 2])).T)
        assert distances.max() <= reach(width, height) * count / notes + 1e-6


def test_the_longest_figure_going_straight_on_reaches_forty_percent_past_the_room_and_leaves_the_picture():
    notes = 8
    segments, _ = figure([C] * notes, 90.0, 1, 600, 400, notes)  # straight to the right
    assert segments[-1, 1, 0] - 300.0 == pytest.approx(reach(600, 400))
    assert segments[-1, 1, 1] == pytest.approx(200.0)
    segments, _ = figure([C] * notes, 0.0, 1, 600, 400, notes)  # straight up: the shorter side decides
    assert 200.0 - segments[-1, 1, 1] == pytest.approx(reach(600, 400))
    assert segments[-1, 1, 1] < 0  # above the picture


def test_a_link_is_forty_percent_longer_than_the_room_over_the_notes_allowed():
    assert pc.LENGTH_FACTOR == 1.4
    assert pc.link_length(600, 400, 8) == pytest.approx(1.4 * (200 - 10 - 400 / 60 / 2) / 8)


def test_the_length_of_a_link_depends_on_the_setting_not_on_how_many_notes_sound():
    assert pc.link_length(600, 400, 5) > pc.link_length(600, 400, 8)
    segments_two, _ = figure([C, G], 0.0, 1, 600, 400, 6)
    segments_six, _ = figure([C, G, D, A, E, B], 0.0, 1, 600, 400, 6)
    assert segments_two[:pc.PIECES_PER_LINK * 2] == pytest.approx(segments_six[:pc.PIECES_PER_LINK * 2])


@pytest.mark.parametrize("width, height", [(20, 20), (30, 400), (400, 25), (0, 400), (600, -1)])
def test_a_picture_too_small_for_a_figure_is_refused(width, height):
    with pytest.raises(ValueError):
        pc.link_length(width, height, 6)


@pytest.mark.parametrize("width, height", [(600.5, 400), (True, 400), ("600", 400), (None, 400)])
def test_a_picture_size_that_is_not_two_whole_numbers_is_refused(width, height):
    with pytest.raises(ValueError):
        pc.link_length(width, height, 6)


# --- the copies and the starting angles -----------------------------------------------------------------------------


def stretched(beat: list[float], minimum: int, maximum: int) -> list[int]:
    """The copies by the rule of the spec written out with a loop: inside the peaks (position above 0) the highest
    position is the top of the beat and the 1st percentile the bottom, a frame outside every peak is the bottom."""
    inside = [b for b in beat if b > 0]
    high = max(inside) if inside else 0.0
    low = float(np.percentile(inside, 1)) if inside else 0.0
    out = []
    for b in beat:
        share = b if high - low <= 0 else min(1.0, max(0.0, (b - low) / (high - low)))  # no range: the position itself
        out.append(math.floor(minimum + share * (maximum - minimum) + 0.5))
    return out


def test_the_top_of_the_beat_has_the_most_copies_the_bottom_and_outside_a_peak_the_fewest():
    beat = [0.0, 0.6, 0.8, 1.0, 0.7, 0.0, 0.95]
    copies = pc.copy_counts(beat, 3, 12)
    assert copies.shape == (7,)
    assert copies.dtype.kind == "i"
    assert copies[3] == 12  # the highest position of the file
    assert copies[0] == 3 and copies[5] == 3  # outside every peak
    assert copies[1] == 3  # the lowest position inside the peaks is the bottom of the beat
    assert list(copies) == stretched(beat, 3, 12)


def test_the_copies_in_between_are_in_proportion_and_always_within_the_limits():
    rng = np.random.default_rng(11)
    for _ in range(50):
        beat = list(rng.uniform(0.3, 1.0, size=30) * (rng.random(30) > 0.2))
        low, high = sorted(int(v) for v in rng.integers(1, 13, size=2))
        copies = pc.copy_counts(beat, low, high)
        assert list(copies) == stretched(beat, low, high)
        assert copies.min() >= low and copies.max() <= high


def test_a_minimum_equal_to_the_maximum_gives_that_number_whatever_the_beat():
    assert list(pc.copy_counts([0.0, 0.5, 1.0], 7, 7)) == [7, 7, 7]


def test_no_beat_gives_the_minimum_for_every_frame_and_needs_the_number_of_frames():
    assert list(pc.copy_counts(None, 4, 12, frames=3)) == [4, 4, 4]
    with pytest.raises(ValueError):
        pc.copy_counts(None, 4, 12)


def test_a_beat_with_no_position_inside_a_peak_is_all_minimum():
    assert list(pc.copy_counts([0.0, 0.0, 0.0], 3, 12)) == [3, 3, 3]


@pytest.mark.parametrize("beat", [[0.5, 1.5], [-0.1, 0.5], [float("nan")], [[0.5]], "text"])
def test_a_beat_outside_0_to_1_or_not_one_number_per_frame_is_refused(beat):
    with pytest.raises(ValueError):
        pc.copy_counts(beat, 3, 12)


def test_the_starting_angle_is_the_rotation_times_the_time_of_the_frame():
    angles = pc.start_angles(30.0, 10.0, 5)
    assert angles.shape == (5,)
    assert list(angles) == pytest.approx([0.0, 3.0, 6.0, 9.0, 12.0])
    assert list(pc.start_angles(-15.0, 20.0, 3)) == pytest.approx([0.0, -0.75, -1.5])
    assert list(pc.start_angles(0.0, 25.0, 4)) == [0.0, 0.0, 0.0, 0.0]
    assert list(pc.start_angles(360.0, 1.0, 3)) == pytest.approx([0.0, 360.0, 720.0])
    assert pc.start_angles(15.0, 10.0, 0).shape == (0,)


@pytest.mark.parametrize("rotation", [-360.0, -137.5, -1.0, 0.0, 15.0, 90.0, 360.0])
def test_consecutive_frames_differ_by_the_rotation_over_the_frame_rate(rotation):
    for rate in (10.0, 24.0, 60.0):
        angles = pc.start_angles(rotation, rate, 50)
        assert np.diff(angles) == pytest.approx(rotation / rate, abs=1e-9)


@pytest.mark.parametrize("rate", [0, -10.0, float("nan"), float("inf"), True, "10", None])
def test_a_frame_rate_that_is_not_a_positive_number_is_refused(rate):
    with pytest.raises(ValueError):
        pc.start_angles(15.0, rate, 3)


@pytest.mark.parametrize("frames", [-1, 2.5, True, None, "3"])
def test_a_number_of_frames_that_is_not_a_whole_number_of_at_least_0_is_refused(frames):
    with pytest.raises(ValueError):
        pc.start_angles(15.0, 10.0, frames)


# --- the tempos and the colors --------------------------------------------------------------------------------------

from app.services.colormaps import DEFAULT_COLORMAP, lookup_table  # noqa: E402
from app.services.local_peaks import LocalPeak, LocalPeaks  # noqa: E402
from app.services.tempo_finder import find_tempo  # noqa: E402

FILE_RATE = 44100


def peaks_at(seconds: list[float]) -> LocalPeaks:
    peaks = tuple(LocalPeak(sample=int(round(t * FILE_RATE)), energy=1.0, window_min=0.0, window_max=1.0, rate=120.0) for t in seconds)
    return LocalPeaks(peaks=peaks, file_rate=FILE_RATE, sample_count=int(60 * FILE_RATE), min_distance=350.0, prominence=15.0)


def test_with_no_peak_every_frame_has_the_starting_tempo_of_120():
    tempos = pc.frame_tempos(peaks_at([]), 10.0, 5)
    assert tempos.shape == (5,)
    assert tempos.dtype == np.float64
    assert list(tempos) == [120.0] * 5


def test_the_tempo_of_a_frame_is_the_tempo_after_the_latest_peak_at_the_middle_of_the_frame():
    seconds = [0.5 + 0.5 * i for i in range(40)]  # a steady 120 beats a minute for 20 seconds
    peaks = peaks_at(seconds)
    found = find_tempo([p.sample / FILE_RATE for p in peaks.peaks]).tempos
    frame_rate, frames = 10.0, 220
    tempos = pc.frame_tempos(peaks, frame_rate, frames)
    times = [p.sample / FILE_RATE for p in peaks.peaks]
    for frame in range(frames):
        moment = (frame + 0.5) / frame_rate
        latest = [i for i, t in enumerate(times) if t <= moment]
        assert tempos[frame] == (found[latest[-1]] if latest else 120.0)
    assert (tempos >= 60).all() and (tempos <= 156).all()


def test_the_tempo_before_the_first_peak_is_120_and_changes_only_at_a_peak():
    seconds = [1.0, 1.4, 1.8, 2.2, 2.6, 3.0, 3.4, 3.8]  # 150 beats a minute
    tempos = pc.frame_tempos(peaks_at(seconds), 10.0, 50)
    assert list(tempos[:10]) == [120.0] * 10  # moments 0.05 to 0.95: before the first peak at 1.0
    assert (tempos[10:] != 120.0).any()  # and it moves toward 150 afterwards
    for frame in range(1, 50):
        if tempos[frame] != tempos[frame - 1]:  # a change needs a peak between the two moments
            before, now = (frame - 0.5) / 10.0, (frame + 0.5) / 10.0
            assert any(before < t <= now for t in seconds)


def test_a_peak_exactly_at_the_middle_of_a_frame_counts_for_that_frame_and_one_a_frame_earlier_does_not():
    seconds = [0.65, 1.05, 1.45, 1.85, 2.25]  # 150 beats a minute; the second peak is at 1.05, the middle of frame 10
    peaks = peaks_at(seconds)
    found = find_tempo([p.sample / FILE_RATE for p in peaks.peaks]).tempos
    assert found[1] != 120.0  # the tempo moves at the second peak
    tempos = pc.frame_tempos(peaks, 10.0, 30)
    assert tempos[9] == found[0] == 120.0  # the moment 0.95: only the first peak (0.65) has come
    assert tempos[10] == found[1]  # the moment 1.05 is the peak itself
    assert tempos[11] == found[1]
    assert tempos[14] == found[2]  # 1.45


def test_a_maximum_number_of_copies_below_the_minimum_is_refused_by_copy_counts_too():
    with pytest.raises(ValueError):
        pc.copy_counts([0.5, 1.0], 8, 7)
    with pytest.raises(ValueError):
        pc.copy_counts(None, 8, 7, frames=2)


def test_a_tempo_input_that_is_not_peaks_or_a_bad_rate_or_count_is_refused():
    with pytest.raises(ValueError):
        pc.frame_tempos(peaks_at([1.0]), 0.0, 5)
    with pytest.raises(ValueError):
        pc.frame_tempos(peaks_at([1.0]), 10.0, -1)
    with pytest.raises(ValueError):
        pc.frame_tempos("peaks", 10.0, 5)


def row(name: str, index: int) -> list[int]:
    return [int(v) for v in lookup_table(name)[index]]


def test_the_slowest_tempo_is_the_first_color_the_fastest_the_last_and_108_the_middle():
    colors = pc.tempo_colors(np.array([60.0, 156.0, 108.0]), DEFAULT_COLORMAP)
    assert colors.shape == (3, 3)
    assert colors.dtype == np.uint8
    assert list(colors[0]) == row(DEFAULT_COLORMAP, 0)
    assert list(colors[1]) == row(DEFAULT_COLORMAP, 255)
    assert list(colors[2]) == row(DEFAULT_COLORMAP, 128)  # rint(127.5) is 128 (the 255 x 0.5 of 108 in 60 to 156)


def test_a_tempo_outside_60_to_156_is_held_at_the_ends():
    colors = pc.tempo_colors(np.array([0.0, 59.9, 156.1, 1000.0]), DEFAULT_COLORMAP)
    assert list(colors[0]) == list(colors[1]) == row(DEFAULT_COLORMAP, 0)
    assert list(colors[2]) == list(colors[3]) == row(DEFAULT_COLORMAP, 255)


def test_a_faster_tempo_never_has_an_earlier_row_of_the_colormap_than_a_slower_one():
    table = lookup_table(DEFAULT_COLORMAP)
    tempos = np.arange(60, 157, dtype=float)
    colors = pc.tempo_colors(tempos, DEFAULT_COLORMAP)
    rows = [int(np.flatnonzero((table == c).all(axis=1))[0]) for c in colors]
    assert rows == sorted(rows)
    assert rows[0] == 0 and rows[-1] == 255
    assert rows == [int(np.rint((t - 60) / 96 * 255)) for t in tempos]


@pytest.mark.parametrize("tempos", [[float("nan")], [[100.0]], "text", None])
def test_tempos_that_are_not_one_number_per_frame_are_refused(tempos):
    with pytest.raises(ValueError):
        pc.tempo_colors(tempos, DEFAULT_COLORMAP)


def test_an_unknown_colormap_is_refused():
    with pytest.raises(ValueError):
        pc.tempo_colors(np.array([100.0]), "not-a-colormap")


def test_figure_segments_refuses_what_does_not_fit():
    turns = np.zeros(6)
    letters = np.array([C, G, -1, -1, -1, -1])
    with pytest.raises(ValueError):
        pc.figure_segments(turns, letters, 0.0, 0, 600, 400, 6)  # no copies
    with pytest.raises(ValueError):
        pc.figure_segments(turns, letters, 0.0, 13, 600, 400, 6)
    with pytest.raises(ValueError):
        pc.figure_segments(turns, letters, float("nan"), 3, 600, 400, 6)
    with pytest.raises(ValueError):
        pc.figure_segments(turns[:5], letters, 0.0, 3, 600, 400, 6)  # turns and letters must agree
    with pytest.raises(ValueError):
        pc.figure_segments(turns, letters, 0.0, 3, 600, 400, 9)  # notes outside 5 to 8
    with pytest.raises(ValueError):
        pc.figure_segments(np.zeros(7), np.array([C] * 7), 0.0, 3, 600, 400, 6)  # more links than notes
