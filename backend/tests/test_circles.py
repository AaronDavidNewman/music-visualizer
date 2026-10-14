"""The circles image type, the part that decides what goes where: ``app/services/circles.py``.

The move of a note is worked out here independently from its frequency, never by reading the code under test.
"""

import math

import numpy as np
import pytest

from app.services.circles import (
    DEFAULT_CIRCLE_MEMORY,
    DEFAULT_CIRCLE_SIZE,
    MAX_CIRCLE_SIZE,
    MIN_CIRCLE_SIZE,
    MIDDLE_COLOR_ROW,
    check_circle_size,
    circle_opacity,
    circle_radius,
    DEFAULT_CIRCLE_NOTES,
    DEFAULT_CIRCLE_UNIT,
    MAX_CIRCLE_MEMORY,
    MAX_CIRCLE_NOTES,
    MAX_CIRCLE_UNIT,
    MIN_CIRCLE_MEMORY,
    MIN_CIRCLE_NOTES,
    MIN_CIRCLE_UNIT,
    check_circle_memory,
    check_circle_notes,
    check_circle_unit,
    note_move,
    plan_circles,
    step_pixels,
)

W, H = 252, 168
UNIT_MESSAGE = "The circle unit must be a whole number from 1 to 10."
MEMORY_MESSAGE = "The circle memory must be a whole number from 100 to 500."
NOTES_MESSAGE = "The number of circle notes must be a whole number from 5 to 12."
SIZE_MESSAGE = "The circle size must be a whole number from 25 to 50."

F5, F3, A4, C4 = 44, 20, 36, 27  # indices of the drawn notes (0 is A1, 55 Hz)


def expected_move(index):
    """(angle, units) worked out from the note's frequency: C-based pitch class, scientific octave."""
    frequency = 55.0 * 2 ** (index / 12)
    midi = round(69 + 12 * math.log2(frequency / 440.0))
    pitch_class, octave = midi % 12, midi // 12 - 1
    angle = 30 * pitch_class
    if octave < 4:
        angle = (360 - angle) % 360
    return angle, 1 + abs(octave - 4)


def expected_step(index, unit):
    angle, units = expected_move(index)
    return units * unit * math.cos(math.radians(angle)), -units * unit * math.sin(math.radians(angle))


def frames_of(*per_frame, size=84):
    """(frames, 84) values; each frame is a dict {note: value}."""
    out = np.zeros((len(per_frame), size))
    for t, values in enumerate(per_frame):
        for note, value in values.items():
            out[t, note] = value
    return out


def steady(note, count, high=1.0, low=0.5):
    """A note that sounds in every frame but alternates between two volumes (two different colors), so that it keeps moving."""
    return [{note: high if t % 2 == 0 else low} for t in range(count)]


def run(values, peak=None, notes=8, unit=4, memory=100):
    peak = float(values.max()) if peak is None else peak
    return list(plan_circles(values, peak, notes, unit, memory))


# --- the settings --------------------------------------------------------------------------------------------------------------


def test_constants():
    assert (MIN_CIRCLE_UNIT, MAX_CIRCLE_UNIT, DEFAULT_CIRCLE_UNIT) == (1, 10, 4)
    assert (MIN_CIRCLE_MEMORY, MAX_CIRCLE_MEMORY, DEFAULT_CIRCLE_MEMORY) == (100, 500, 300)
    assert (MIN_CIRCLE_NOTES, MAX_CIRCLE_NOTES, DEFAULT_CIRCLE_NOTES) == (5, 12, 8)
    assert (MIN_CIRCLE_SIZE, MAX_CIRCLE_SIZE, DEFAULT_CIRCLE_SIZE) == (25, 50, 25)
    assert MIDDLE_COLOR_ROW == 128  # the table entry at the middle of the scale (0.5 of 255 rounds to 128)


@pytest.mark.parametrize(
    "check, good, bad, message",
    [
        (check_circle_unit, [1, 4, 10, np.int64(7), 4.0], [0, 11, -1, 2.5, 10.0001], UNIT_MESSAGE),
        (check_circle_memory, [100, 300, 500, np.int64(250), 300.0], [0, 99, 501, 250.5, 1000], MEMORY_MESSAGE),
        (check_circle_notes, [5, 8, 12, np.int64(6), 8.0], [0, 4, 13, 7.5, 100], NOTES_MESSAGE),
        (check_circle_size, [25, 37, 50, np.int64(40), 30.0], [0, 24, 51, 30.5, 100], SIZE_MESSAGE),
    ],
)
def test_each_setting_accepts_the_whole_numbers_in_its_range_and_refuses_the_rest(check, good, bad, message):
    for value in good:
        assert check(value) == int(value) and isinstance(check(value), int)
    for value in bad + [True, False, None, "4", "", b"4", float("nan"), float("inf"), -float("inf")]:
        with pytest.raises(ValueError) as error:
            check(value)
        assert str(error.value) == message


# --- the size and the opacity of a circle ----------------------------------------------------------------------------------------


def test_the_size_is_the_circumference_in_pixels_from_about_the_old_default_circle_to_about_fifty():
    assert circle_radius(25) == pytest.approx(25 / (2 * math.pi)) and circle_radius(25) == pytest.approx(3.98, abs=0.01)  # about the old unit-4 circle
    assert circle_radius(50) == pytest.approx(7.96, abs=0.01)
    assert 2 * math.pi * circle_radius(37) == pytest.approx(37)


@pytest.mark.parametrize("memory", [100, 300, 500])
def test_the_opacity_falls_in_a_straight_line_from_opaque_to_barely_visible_just_before_the_memory_drops_a_circle(memory):
    alphas = [circle_opacity(age, memory) for age in range(memory)]  # age 0 is the newest, memory - 1 the oldest a full memory holds
    assert alphas[0] == 255  # the newest is opaque
    assert alphas[-1] == round(255 / memory) and alphas[-1] <= 3  # barely visible (1 to 3 of 255)
    assert all(a > b or a == b for a, b in zip(alphas, alphas[1:])) and alphas[0] > alphas[-1]  # never rises
    for age, alpha in enumerate(alphas):
        assert alpha == round(255 * (memory - age) / memory)  # the formula, worked out here
        assert 0 < alpha <= 255
    assert alphas[memory // 2] == round(255 * 0.5)  # half way back, about half opaque


# --- the move of a note ---------------------------------------------------------------------------------------------------------


def test_the_users_examples_with_their_corrected_distances():
    assert note_move(F5) == (150, 2)  # octave 5: one above 4 -> 2 units
    assert note_move(F3) == (210, 2)  # octave 3: below 4, the angle mirrored (360 - 150), 2 units
    assert note_move(A4) == (270, 1)  # octave 4 moves 1 unit
    assert note_move(C4) == (0, 1)
    assert note_move(0) == (90, 4)  # A1: pitch class 9 = 270, mirrored, octave 1 -> 1 + 3
    assert note_move(83) == (240, 5)  # G#8: pitch class 8 = 240, octave 8 -> 1 + 4


@pytest.mark.parametrize("index", range(84))
def test_every_note_moves_as_its_frequency_says(index):
    assert note_move(index) == expected_move(index)
    angle, units = note_move(index)
    assert angle % 30 == 0 and 0 <= angle < 360 and 1 <= units <= 5


def test_octave_four_moves_one_unit_and_each_octave_away_adds_one():
    units = {}
    for index in range(84):
        octave = (33 + index) // 12 - 1
        units.setdefault(octave, set()).add(note_move(index)[1])
    assert units == {1: {4}, 2: {3}, 3: {2}, 4: {1}, 5: {2}, 6: {3}, 7: {4}, 8: {5}}


def test_below_octave_four_the_angle_is_mirrored_and_from_octave_four_up_it_is_the_note_name():
    for index in range(84):
        midi = 33 + index
        name_angle = 30 * (midi % 12)
        octave = midi // 12 - 1
        angle, _ = note_move(index)
        assert angle == (name_angle if octave >= 4 else (360 - name_angle) % 360)


@pytest.mark.parametrize("bad", [-1, 84, 1.5, None, "3", True])
def test_a_note_that_is_not_a_drawn_note_is_refused(bad):
    with pytest.raises(ValueError):
        note_move(bad)


def test_the_step_in_pixels_has_0_degrees_pointing_right_and_angles_counter_clockwise_on_the_screen():
    dx, dy = step_pixels(F5, 4)  # 150 degrees, 2 units of 4 pixels: left and up
    assert dx == pytest.approx(8 * math.cos(math.radians(150))) and dy == pytest.approx(-8 * math.sin(math.radians(150)))
    assert dx < 0 and dy < 0
    assert step_pixels(A4, 4) == pytest.approx((0.0, 4.0), abs=1e-9)  # 270 degrees: straight down, one unit
    assert step_pixels(C4, 4) == pytest.approx((4.0, 0.0), abs=1e-9)  # 0 degrees: right
    for index in range(84):
        for unit in (1, 4, 10):
            dx, dy = step_pixels(index, unit)
            assert math.hypot(dx, dy) == pytest.approx(note_move(index)[1] * unit)
            assert (dx, dy) == pytest.approx(expected_step(index, unit), abs=1e-9)


# --- the placement ---------------------------------------------------------------------------------------------------------------


def test_the_first_circle_is_the_middle_of_the_picture_moved_by_the_note_and_each_frame_moves_on_from_the_last():
    values = frames_of(*steady(F5, 6))
    unit = 4
    x, y = W / 2, H / 2
    dx, dy = expected_step(F5, unit)
    for t, (added, memory) in enumerate(run(values, unit=unit)):
        x, y = (x + dx) % W, (y + dy) % H
        assert len(added) == 1
        assert added[0][0] == pytest.approx(x, abs=1e-9) and added[0][1] == pytest.approx(y, abs=1e-9), t
        assert len(memory) == t + 1  # the trail: every earlier circle is still remembered


@pytest.mark.parametrize("index", [F5, F3, A4, C4, 0, 83, 10, 61])
def test_a_steady_note_walks_by_its_step_every_frame_modulo_the_picture(index):
    unit = 7
    dx, dy = expected_step(index, unit)
    values = frames_of(*steady(index, 40, 0.8, 0.5))
    places = [added[0][:2] for added, _ in run(values, unit=unit)]
    for k, (x, y) in enumerate(places, start=1):
        assert x == pytest.approx((W / 2 + k * dx) % W, abs=1e-6) and y == pytest.approx((H / 2 + k * dy) % H, abs=1e-6)
        assert 0 <= x < W and 0 <= y < H


def test_a_rank_that_keeps_walking_wraps_around_the_picture():
    values = frames_of(*steady(C4, 60))  # 0 degrees, 1 unit of 10 pixels: 10 pixels to the right each frame
    xs = [added[0][0] for added, _ in run(values, unit=10)]
    assert all(0 <= x < W for x in xs)
    assert xs[:2] == [pytest.approx(136.0), pytest.approx(146.0)]
    assert any(b < a for a, b in zip(xs, xs[1:]))  # it came back in at the left edge


def test_the_circle_of_a_rank_continues_from_the_same_rank_of_the_previous_frame_not_from_the_same_note():
    unit = 4
    # frame 0: A is the strongest, B the second; frame 1: B is the strongest, A the second
    a, b = F5, F3
    values = frames_of({a: 1.0, b: 0.5}, {a: 0.5, b: 1.0})
    steps = {i: expected_step(i, unit) for i in (a, b)}
    middle = (W / 2, H / 2)
    r0_f0 = ((middle[0] + steps[a][0]) % W, (middle[1] + steps[a][1]) % H)  # rank 0 in frame 0
    r1_f0 = ((middle[0] + steps[b][0]) % W, (middle[1] + steps[b][1]) % H)
    frames = run(values, unit=unit)
    added1 = frames[1][0]  # weakest first: rank 1 then rank 0
    r1_f1, r0_f1 = added1[0][:2], added1[1][:2]
    assert r0_f1 == pytest.approx(((r0_f0[0] + steps[b][0]) % W, (r0_f0[1] + steps[b][1]) % H), abs=1e-9)  # B, now rank 0, from A's place
    assert r1_f1 == pytest.approx(((r1_f0[0] + steps[a][0]) % W, (r1_f0[1] + steps[a][1]) % H), abs=1e-9)  # A, now rank 1, from B's place


def test_the_strongest_notes_of_each_frame_are_chosen_weakest_first_and_notes_without_energy_put_nothing_down():
    rng = np.random.default_rng(2)
    values = rng.random((10, 84))
    values[:, 80:] = 0.0  # four notes are always silent
    values[3, :] = 0.0  # a silent frame
    for notes in (5, 8, 12):
        for t, (added, memory) in enumerate(run(values, notes=notes)):
            if t == 3:
                assert added == [] and memory == frames_before(run(values, notes=notes), t)
                continue
            top = np.sort(values[t])[::-1][:notes]
            colours = [c[2] for c in added]
            assert len(added) == notes
            assert colours == sorted(colours)  # weakest first: the strongest is added last, so it is on top
            want = [int(np.rint(math.sqrt(min(v / values.max(), 1.0)) * 255)) for v in np.sort(top)]
            assert colours == want


def frames_before(frames, t):
    return frames[t - 1][1]


def test_ties_go_to_the_lower_note():
    values = frames_of({10: 0.5, 20: 0.5, 30: 0.5, 40: 0.5, 50: 0.5, 60: 0.5, 70: 0.5})  # seven equal notes, five fit
    unit = 4
    added = run(values, unit=unit, notes=5)[0][0]
    chosen = [10, 20, 30, 40, 50]  # the five lowest notes of the seven
    # every rank starts from the middle, so a circle's place is the middle plus the step of its note; weakest first = rank 4 first
    want = [((W / 2 + expected_step(n, unit)[0]) % W, (H / 2 + expected_step(n, unit)[1]) % H) for n in reversed(chosen)]
    assert [c[:2] for c in added] == pytest.approx(want, abs=1e-9)


def test_a_silent_frame_adds_nothing_and_a_rank_without_a_note_keeps_its_last_place():
    values = frames_of({F5: 1.0}, {}, {}, {F5: 0.5})  # another volume, so that the note moves on
    frames = run(values, unit=4)
    assert frames[1][0] == [] and frames[2][0] == []
    assert frames[1][1] == frames[0][1] == frames[2][1]  # the memory is unchanged
    dx, dy = expected_step(F5, 4)
    x, y = frames[3][0][0][:2]  # the same rank continues from where it last was: two steps from the middle
    assert (x, y) == pytest.approx(((W / 2 + 2 * dx) % W, (H / 2 + 2 * dy) % H), abs=1e-9)


def test_the_color_index_is_the_tiles_square_root_scale_of_the_share_of_the_files_peak():
    values = frames_of({F5: 1.0, A4: 0.25, C4: 0.01})
    colours = {c[2] for c in run(values, peak=1.0)[0][0]}
    assert colours == {255, int(np.rint(0.5 * 255)), int(np.rint(0.1 * 255))}
    # a peak larger than the frame's loudest note scales the colors down; a value above the peak is clipped to the last color
    assert max(c[2] for c in run(values, peak=4.0)[0][0]) == int(np.rint(0.5 * 255))
    assert max(c[2] for c in run(values, peak=0.5)[0][0]) == 255


def test_the_same_strength_has_the_same_color_in_every_frame():
    values = frames_of(*({F5: 0.6, A4: 0.3} for _ in range(5)))
    colours = [[c[2] for c in added] for added, _ in run(values, peak=1.0)]
    assert all(c == colours[0] for c in colours)


# --- a note that stays ----------------------------------------------------------------------------------------------------------


def place_of_rank0(frames, t):
    return tuple(frames[t][0][-1][:2])  # the strongest circle is the last one added


def test_the_same_note_at_the_same_volume_stays_where_it_is():
    values = frames_of(*({F5: 1.0} for _ in range(6)))
    frames = run(values, unit=7)
    dx, dy = expected_step(F5, 7)
    first = ((W / 2 + dx) % W, (H / 2 + dy) % H)  # the first circle of a rank has no note before it, so it moves from the middle
    for t in range(6):
        assert place_of_rank0(frames, t) == pytest.approx(first, abs=1e-9), t
        assert len(frames[t][1]) == t + 1  # a circle is still put down each frame, on the same place


@pytest.mark.parametrize("index", [F5, F3, A4, C4, 0, 83])
def test_every_note_stays_when_it_repeats_at_the_same_volume_and_moves_when_the_volume_changes(index):
    unit = 5
    values = frames_of({index: 0.7}, {index: 0.7}, {index: 0.7}, {index: 0.4}, {index: 0.4})
    frames = run(values, unit=unit, peak=1.0)
    dx, dy = expected_step(index, unit)
    p1 = ((W / 2 + dx) % W, (H / 2 + dy) % H)
    p2 = ((p1[0] + dx) % W, (p1[1] + dy) % H)  # the quieter note is a different volume: it moves one step
    got = [place_of_rank0(frames, t) for t in range(5)]
    assert got[0] == pytest.approx(p1, abs=1e-9) and got[1] == pytest.approx(p1, abs=1e-9) and got[2] == pytest.approx(p1, abs=1e-9)
    assert got[3] == pytest.approx(p2, abs=1e-9)
    assert got[4] == pytest.approx(p2, abs=1e-9)  # and stays again at its new volume


def test_the_same_volume_means_the_same_color_so_values_that_round_to_one_color_stay_and_others_move():
    unit = 6
    values = frames_of({F5: 0.500}, {F5: 0.5001}, {F5: 0.52})  # the first two are one color on the 256-color scale, the third is not
    colours = [added[-1][2] for added, _ in run(values, unit=unit, peak=1.0)]
    assert colours[0] == colours[1] != colours[2]
    frames = run(values, unit=unit, peak=1.0)
    dx, dy = expected_step(F5, unit)
    p1 = ((W / 2 + dx) % W, (H / 2 + dy) % H)
    assert place_of_rank0(frames, 1) == pytest.approx(p1, abs=1e-9)  # stayed
    assert place_of_rank0(frames, 2) == pytest.approx(((p1[0] + dx) % W, (p1[1] + dy) % H), abs=1e-9)  # moved


def test_a_different_note_at_the_same_volume_moves_and_so_does_the_note_that_comes_back_after_it():
    unit = 4
    values = frames_of({F5: 0.8}, {F3: 0.8}, {F5: 0.8})  # the note of the rank changes every frame
    frames = run(values, unit=unit, peak=1.0)
    x, y = W / 2, H / 2
    for t, note in enumerate((F5, F3, F5)):
        dx, dy = expected_step(note, unit)
        x, y = (x + dx) % W, (y + dy) % H
        assert place_of_rank0(frames, t) == pytest.approx((x, y), abs=1e-9), t


def test_the_note_of_a_rank_is_compared_with_the_last_note_of_that_rank_even_across_a_silent_stretch():
    values = frames_of({F5: 0.8}, {}, {}, {F5: 0.8}, {F5: 0.8})
    frames = run(values, unit=4, peak=1.0)
    assert frames[1][0] == [] and frames[2][0] == []
    assert place_of_rank0(frames, 3) == pytest.approx(place_of_rank0(frames, 0), abs=1e-9)  # the same note at the same volume: it stays
    assert place_of_rank0(frames, 4) == pytest.approx(place_of_rank0(frames, 0), abs=1e-9)


def test_each_rank_stays_or_moves_on_its_own():
    unit = 6
    # rank 0 is F5 at the same volume throughout (stays); rank 1 is A4 at 0.4, 0.4, then 0.3 (stays, then moves)
    values = frames_of({F5: 1.0, A4: 0.4}, {F5: 1.0, A4: 0.4}, {F5: 1.0, A4: 0.3})
    frames = run(values, unit=unit, peak=1.0)
    fx, fy = expected_step(F5, unit)
    ax, ay = expected_step(A4, unit)
    f_place = ((W / 2 + fx) % W, (H / 2 + fy) % H)
    a_place = ((W / 2 + ax) % W, (H / 2 + ay) % H)
    for t in range(3):
        added = frames[t][0]  # weakest first: rank 1 then rank 0
        assert added[1][:2] == pytest.approx(f_place, abs=1e-9), t
        want = a_place if t < 2 else ((a_place[0] + ax) % W, (a_place[1] + ay) % H)
        assert added[0][:2] == pytest.approx(want, abs=1e-9), t


def test_a_steady_note_at_one_volume_never_leaves_its_place_however_long_it_lasts():
    values = frames_of(*({C4: 0.9} for _ in range(300)))
    places = {tuple(round(v, 9) for v in added[0][:2]) for added, _ in run(values, unit=10, memory=500)}
    assert len(places) == 1


# --- the memory ------------------------------------------------------------------------------------------------------------------


def test_the_memory_holds_the_last_circles_and_drops_the_oldest():
    values = frames_of(*({F5: 1.0} for _ in range(130)))
    frames = run(values, memory=100)
    all_added = [c for added, _ in frames for c in added]
    assert len(all_added) == 130
    for t, (_, memory) in enumerate(frames):
        assert memory == all_added[max(0, t + 1 - 100) : t + 1]  # exactly the last 100, oldest first, newest last
    assert len(frames[-1][1]) == 100 and frames[-1][1][0] == all_added[30]


@pytest.mark.parametrize("notes", [5, 8, 12])
def test_with_several_circles_a_frame_the_count_is_the_circles_so_far_up_to_the_memory(notes):
    rng = np.random.default_rng(notes)
    values = rng.random((60, 84)) + 0.1  # every note sounds in every frame
    frames = run(values, notes=notes, memory=100)
    for t, (added, memory) in enumerate(frames):
        assert len(added) == notes
        assert len(memory) == min((t + 1) * notes, 100)
    assert len(frames[-1][1]) == 100  # full: the memory never grows beyond its size


# --- general ---------------------------------------------------------------------------------------------------------------------


def test_the_plan_is_deterministic_and_does_not_modify_the_values():
    rng = np.random.default_rng(9)
    values = rng.random((20, 84))
    before = values.copy()
    assert run(values) == run(values)
    assert (values == before).all()


@pytest.mark.parametrize("bad", [np.ones((3, 83)), np.ones(84), np.ones((3, 88)), np.ones((3, 2, 42))])
def test_values_of_the_wrong_shape_are_refused(bad):
    with pytest.raises(ValueError):
        run(bad, peak=1.0)


def test_no_frames_and_a_silent_file_plan_nothing():
    assert run(np.zeros((0, 84)), peak=0.0) == []
    frames = run(np.zeros((5, 84)), peak=0.0)
    assert len(frames) == 5 and all(added == [] and memory == [] for added, memory in frames)
