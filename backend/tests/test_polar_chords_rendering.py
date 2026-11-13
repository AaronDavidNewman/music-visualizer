"""The pictures of the ``polar-chords`` kind: wedges at the right angle, width, length and color; ``write_frames`` (feature 032).

The tests build the bars by hand (``PolarBars``) so that the drawing is checked on its own, then check that ``write_frames`` draws the bars of
``polar_bars``. Angles are degrees clockwise from straight up; the center is (300, 200) and the full radius 190 on the 600 x 400 frame.
"""

import math

import numpy as np
import pytest
from PIL import Image

from app.services.colormaps import COLORMAPS, lookup_table
from app.services.frame_rendering import write_frames
from app.services.polar_chords import PolarBars, polar_bars, write_polar_frames

from .frame_size import HEIGHT, WIDTH

CENTER = (WIDTH / 2, HEIGHT / 2)
RADIUS = 190.0
ARC = 360.0 / 84
CHORD_ARC = 360.0 / 84  # the chord ring has one arc for each of the 12 letters and 7 chord types
MIDDLE = 128


def make_bars(notes=(), chord=None, length=1.0, count=8) -> PolarBars:
    """One frame: ``notes`` is a list of (arc, share); ``chord`` is None or (place, share); ``length`` is the share of the full radius."""
    slots = np.full((1, count), -1, dtype=np.int16)
    shares = np.zeros((1, count))
    for i, (arc, share) in enumerate(notes):
        slots[0, i] = arc
        shares[0, i] = share
    place, chord_share = (-1, 0.0) if chord is None else chord
    return PolarBars(slots, shares, np.array([place], dtype=np.int16), np.array([chord_share]), np.array([length]))


def draw(directory, bars, colormap="viridis") -> np.ndarray:
    write_polar_frames(bars, colormap, directory, WIDTH, HEIGHT)
    return np.array(Image.open(directory / "frame_000000.png").convert("RGB"))


def pixel(image, angle, radius):
    """The pixel at ``radius`` pixels from the center, ``angle`` degrees clockwise from straight up."""
    x = CENTER[0] + radius * math.sin(math.radians(angle))
    y = CENTER[1] - radius * math.cos(math.radians(angle))
    return tuple(int(v) for v in image[int(math.floor(y)), int(math.floor(x))])


def note_angle(arc, fraction=0.5):
    return (arc + fraction) * ARC


def chord_angle(place, fraction=0.5):
    return 360.0 - (place + fraction) * CHORD_ARC


def note_color(colormap, share):
    return tuple(int(v) for v in lookup_table(colormap)[int(np.rint((0.5 - 0.5 * share) * 255))])


def chord_color(colormap, share):
    return tuple(int(v) for v in lookup_table(colormap)[int(np.rint((0.5 + 0.5 * share) * 255))])


def background(colormap):
    return tuple(int(v) for v in lookup_table(colormap)[MIDDLE])


def near(a, b, tolerance=1):
    return all(abs(x - y) <= tolerance for x, y in zip(a, b))


def covered_fraction(image, angle, radius, colour, back):
    """How much of the way from the background to the bar's color the pixel is, by the channel with the largest difference."""
    channel = max(range(3), key=lambda c: abs(colour[c] - back[c]))
    if colour[channel] == back[channel]:
        return 1.0
    return (pixel(image, angle, radius)[channel] - back[channel]) / (colour[channel] - back[channel])


def tip_of(image, angle, colour, back):
    """The outermost radius along a ray at which a bar still has at least half of its color."""
    tip = 0.0
    for radius in np.arange(5.0, RADIUS + 5, 0.25):
        if covered_fraction(image, angle, float(radius), colour, back) >= 0.5:
            tip = float(radius)
    return tip


# ---- the files --------------------------------------------------------------------------------------------------------------------------


def test_one_600_by_400_rgb_png_per_frame_named_from_zero(tmp_path):
    one = make_bars([(10, 0.5)])
    bars = PolarBars(*(np.concatenate([a, a, a]) for a in (one.note_slots, one.note_shares, one.chord_place, one.chord_share, one.length)))
    write_polar_frames(bars, "viridis", tmp_path, WIDTH, HEIGHT)
    assert [p.name for p in sorted(tmp_path.glob("*.png"))] == [f"frame_{i:06d}.png" for i in range(3)]
    image = Image.open(tmp_path / "frame_000002.png")
    assert image.size == (WIDTH, HEIGHT) and image.mode == "RGB"


def test_no_frames_make_no_files(tmp_path):
    empty = PolarBars(np.zeros((0, 5), np.int16), np.zeros((0, 5)), np.zeros(0, np.int16), np.zeros(0), np.zeros(0))
    write_polar_frames(empty, "viridis", tmp_path / "out", WIDTH, HEIGHT)
    assert list((tmp_path / "out").glob("*.png")) == []


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_background_is_the_middle_color_of_the_colormap_in_the_corners_and_outside_the_circle(tmp_path, name):
    image = draw(tmp_path, make_bars(), name)
    middle = background(name)
    assert tuple(image[0, 0]) == middle and tuple(image[-1, -1]) == middle and tuple(image[0, -1]) == middle
    assert (image.reshape(-1, 3) == np.array(middle)).all()  # no bars: the whole picture is the background


# ---- the bars of the notes -----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["viridis", "coolwarm", "hot"])
@pytest.mark.parametrize("arc, share", [(0, 1.0), (1, 0.3), (27, 0.8), (42, 0.5), (83, 1.0)])
def test_a_note_bar_fills_its_arc_in_its_color_and_the_arcs_next_to_it_are_the_background(tmp_path, name, arc, share):
    image = draw(tmp_path, make_bars([(arc, share)]), name)
    assert near(pixel(image, note_angle(arc), 0.3 * RADIUS), note_color(name, share))
    assert near(pixel(image, note_angle(arc), 0.8 * RADIUS), note_color(name, share))
    for neighbour in (arc - 1, arc + 1):
        assert pixel(image, note_angle(neighbour), 0.3 * RADIUS) == background(name)
        assert pixel(image, note_angle(neighbour), 0.8 * RADIUS) == background(name)


def test_a_bar_is_as_wide_as_its_arc_the_sides_are_where_the_arc_ends(tmp_path):
    arc = 20
    image = draw(tmp_path, make_bars([(arc, 1.0)], length=1.0))
    colour, back = note_color("viridis", 1.0), background("viridis")
    for radius in (0.5 * RADIUS, 0.9 * RADIUS):
        assert near(pixel(image, note_angle(arc, 0.3), radius), colour)  # inside, about 2 pixels from the start of the arc
        assert near(pixel(image, note_angle(arc, 0.7), radius), colour)  # inside, about 2 pixels from the end
        assert pixel(image, note_angle(arc, -0.3), radius) == back  # outside, about 2 pixels beyond
        assert pixel(image, note_angle(arc, 1.3), radius) == back


@pytest.mark.parametrize("arc", [3, 40, 83])
def test_a_bar_is_a_wedge_that_tapers_all_the_way_to_the_center(tmp_path, arc):
    # an arc is only 1.1 pixels wide 15 pixels from the center, 2.2 pixels at 30: the pixels there are partly the bar, partly the background
    colour, back = note_color("viridis", 1.0), background("viridis")
    image = draw(tmp_path, make_bars([(arc, 1.0)], length=0.5))
    assert covered_fraction(image, note_angle(arc), 15.0, colour, back) > 0.3
    assert covered_fraction(image, note_angle(arc), 30.0, colour, back) > 0.6
    assert covered_fraction(image, note_angle(arc), 60.0, colour, back) > 0.95
    assert covered_fraction(image, note_angle(arc + 3), 15.0, colour, back) < 0.1  # and not the arcs around it


@pytest.mark.parametrize("length", [0.5, 0.625, 0.75, 1.0])
def test_the_tip_of_a_bar_is_at_its_length_within_a_pixel(tmp_path, length):
    image = draw(tmp_path, make_bars([(30, 1.0), (60, 0.6)], length=length))
    for arc, share in ((30, 1.0), (60, 0.6)):
        tip = tip_of(image, note_angle(arc), note_color("viridis", share), background("viridis"))
        assert abs(tip - length * RADIUS) <= 1.0, (arc, length, tip)


def test_all_the_bars_of_a_frame_have_the_same_length(tmp_path):
    image = draw(tmp_path, make_bars([(5, 1.0), (30, 0.7), (40, 0.9)], chord=(2, 0.8), length=0.8))  # the chord place 2 is the note arc 81, counterclockwise
    tips = [
        tip_of(image, note_angle(5), note_color("viridis", 1.0), background("viridis")),
        tip_of(image, note_angle(30), note_color("viridis", 0.7), background("viridis")),
        tip_of(image, note_angle(40), note_color("viridis", 0.9), background("viridis")),
        tip_of(image, chord_angle(2), chord_color("viridis", 0.8), background("viridis")),
    ]
    assert max(tips) - min(tips) <= 0.75 and abs(tips[0] - 0.8 * RADIUS) <= 1.0


def test_the_sides_and_the_tip_are_smooth_not_stair_steps(tmp_path):
    arc = 20
    image = draw(tmp_path, make_bars([(arc, 1.0)], length=0.8))
    colour, back = note_color("viridis", 1.0), background("viridis")
    side = [covered_fraction(image, note_angle(arc, 0.0), float(r), colour, back) for r in np.arange(60.0, 140.0, 1.7)]
    tip = [covered_fraction(image, note_angle(arc, 0.5), 0.8 * RADIUS + offset, colour, back) for offset in np.arange(-1.5, 1.5, 0.37)]
    for fractions in (side, tip):
        assert all(-0.02 <= f <= 1.02 for f in fractions)
        assert sum(0.05 < f < 0.95 for f in fractions) >= 0.3 * len(fractions)  # a hard edge would have no pixel in between


def test_the_first_note_goes_to_the_right_of_straight_up(tmp_path):
    image = draw(tmp_path, make_bars([(0, 1.0)]))
    assert near(pixel(image, 0.25 * ARC, 0.8 * RADIUS), note_color("viridis", 1.0))
    assert pixel(image, -0.25 * ARC, 0.8 * RADIUS) == background("viridis")


def test_the_last_note_ends_straight_up_coming_from_the_left(tmp_path):
    image = draw(tmp_path, make_bars([(83, 1.0)]))
    assert near(pixel(image, -0.25 * ARC, 0.8 * RADIUS), note_color("viridis", 1.0))
    assert pixel(image, 0.25 * ARC, 0.8 * RADIUS) == background("viridis")


def test_the_notes_go_clockwise_a_quarter_of_the_way_round_is_the_note_21(tmp_path):
    image = draw(tmp_path, make_bars([(21, 1.0)]))  # 21 arcs of 84 = 90 degrees = straight right
    assert near(pixel(image, 90.0 + 0.5 * ARC, 0.5 * RADIUS), note_color("viridis", 1.0))
    assert pixel(image, 270.0, 0.5 * RADIUS) == background("viridis")


def test_two_notes_next_to_each_other_touch_with_no_gap_and_no_seam(tmp_path):
    image = draw(tmp_path, make_bars([(10, 1.0), (11, 0.2)], length=1.0))
    a, b, back = note_color("viridis", 1.0), note_color("viridis", 0.2), background("viridis")
    edge = pixel(image, 11 * ARC, 0.8 * RADIUS)
    assert edge != back
    for channel in range(3):
        assert min(a[channel], b[channel]) - 2 <= edge[channel] <= max(a[channel], b[channel]) + 2
    assert near(pixel(image, note_angle(10, 0.3), 0.8 * RADIUS), a) and near(pixel(image, note_angle(11, 0.7), 0.8 * RADIUS), b)


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_colors_of_the_notes_run_from_the_middle_to_the_start_of_the_colormap(tmp_path, name):
    table = lookup_table(name)
    quiet = draw(tmp_path / "q", make_bars([(10, 0.0)]), name)
    assert near(pixel(quiet, note_angle(10), 0.3 * RADIUS), tuple(int(v) for v in table[MIDDLE]), 1)  # a share of 0: the middle color
    loud = draw(tmp_path / "l", make_bars([(10, 1.0)]), name)
    assert near(pixel(loud, note_angle(10), 0.3 * RADIUS), tuple(int(v) for v in table[0]), 1)  # a share of 1: the first color
    middle = draw(tmp_path / "m", make_bars([(10, 0.5)]), name)
    assert near(pixel(middle, note_angle(10), 0.3 * RADIUS), tuple(int(v) for v in table[int(np.rint(0.25 * 255))]), 1)


def test_a_faint_bar_is_nearly_the_background_color(tmp_path):
    image = draw(tmp_path, make_bars([(10, 0.02)]), "coolwarm")
    assert near(pixel(image, note_angle(10), 0.3 * RADIUS), background("coolwarm"), 6)


# ---- write_frames -----------------------------------------------------------------------------------------------------------------------


def all_frames(directory) -> list[bytes]:
    return [path.read_bytes() for path in sorted(directory.glob("frame_*.png"))]


def stream(frames=12, seed=4) -> np.ndarray:
    return np.random.default_rng(seed).random((frames, 88)) ** 2


@pytest.mark.parametrize("count", [5, 6, 8])
def test_write_frames_draws_the_bars_of_polar_bars(tmp_path, count):
    values = stream()
    beat = np.linspace(0, 1, 12)
    write_frames(values, tmp_path / "a", colormap="viridis", image_type="polar-chords", beat=beat, polar_notes=count)
    write_polar_frames(polar_bars(values, beat, count), "viridis", tmp_path / "b", WIDTH, HEIGHT)
    assert all_frames(tmp_path / "a") == all_frames(tmp_path / "b") and len(all_frames(tmp_path / "a")) == 12


def test_write_frames_uses_5_notes_and_no_beat_by_default(tmp_path):
    values = stream(4)
    write_frames(values, tmp_path / "a", colormap="viridis", image_type="polar-chords")
    write_frames(values, tmp_path / "b", colormap="viridis", image_type="polar-chords", polar_notes=5, beat=np.zeros(4))
    assert all_frames(tmp_path / "a") == all_frames(tmp_path / "b")


def test_the_number_of_notes_shown_changes_the_picture(tmp_path):
    values = stream(4)
    write_frames(values, tmp_path / "a", colormap="viridis", image_type="polar-chords", polar_notes=5)
    write_frames(values, tmp_path / "b", colormap="viridis", image_type="polar-chords", polar_notes=8)
    assert all_frames(tmp_path / "a") != all_frames(tmp_path / "b")


def test_the_settings_that_do_not_apply_do_not_change_the_frames(tmp_path):
    values = stream(6)
    write_frames(values, tmp_path / "a", colormap="viridis", image_type="polar-chords")
    write_frames(
        values,
        tmp_path / "b",
        colormap="viridis",
        image_type="polar-chords",
        threshold=0.9,
        note_count=40,
        resolution=3,
        interpolate=2,
        gaussian=2.0,
        decay_rate=4,
        decay_amounts=(3.0, 3.0, 0.5, 0.5),
        wave_count=7,
    )
    assert all_frames(tmp_path / "a") == all_frames(tmp_path / "b")


@pytest.mark.parametrize("image_type", ["contour", "decay", "decay-exp", "polar-chords"])
@pytest.mark.parametrize("bad", [4, 9, 6.5, True, "6", None])
def test_a_bad_number_of_notes_shown_is_refused_before_anything_is_written_for_every_type(tmp_path, image_type, bad):
    with pytest.raises(ValueError, match="The number of notes shown must be a whole number from 5 to 8."):
        write_frames(stream(3), tmp_path / "out", colormap="viridis", image_type=image_type, polar_notes=bad)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("image_type", ["decay"])
def test_the_number_of_notes_shown_has_no_effect_on_the_other_types(tmp_path, image_type):
    values = stream(4)
    write_frames(values, tmp_path / "a", colormap="viridis", image_type=image_type)
    write_frames(values, tmp_path / "b", colormap="viridis", image_type=image_type, polar_notes=8)
    assert all_frames(tmp_path / "a") == all_frames(tmp_path / "b")


def test_two_runs_give_identical_files_and_polar_chords_differs_from_the_decay_picture(tmp_path):
    values = stream(4)
    write_frames(values, tmp_path / "a", colormap="viridis", image_type="polar-chords")
    write_frames(values, tmp_path / "b", colormap="viridis", image_type="polar-chords")
    write_frames(values, tmp_path / "c", colormap="viridis", image_type="decay")
    assert all_frames(tmp_path / "a") == all_frames(tmp_path / "b") != all_frames(tmp_path / "c")


@pytest.mark.parametrize("length", [0.5, 0.63, 0.7, 0.82, 0.9, 1.0])
def test_the_tip_is_exact_to_a_fraction_of_a_pixel(tmp_path, length):
    # the notes 20 and 21 meet on the line straight to the right; with the same color and length they make one bar along that line, and the
    # coverage of the pixels of a row along it adds up to the length (a pixel centered r from the center is covered clip(length - r + 0.5, 0, 1))
    colour, back = note_color("viridis", 1.0), background("viridis")
    image = draw(tmp_path, make_bars([(20, 1.0), (21, 1.0)], length=length))
    row = 199  # the pixel row just above the line
    channel = max(range(3), key=lambda c: abs(colour[c] - back[c]))
    first = 360  # a pixel centered 60.5 from the center
    total = sum((float(image[row, x, channel]) - back[channel]) / (colour[channel] - back[channel]) for x in range(first, 300 + 195))
    assert total == pytest.approx(length * RADIUS - 60.0, abs=0.2)


def test_two_bars_next_to_each_other_with_the_same_color_make_one_bar_with_no_seam(tmp_path):
    colour = note_color("viridis", 1.0)
    image = draw(tmp_path, make_bars([(10, 1.0), (11, 1.0)], length=1.0))
    for radius in (0.4 * RADIUS, 0.6 * RADIUS, 0.85 * RADIUS):
        for angle in np.linspace(10.3 * ARC, 11.7 * ARC, 60):  # across the line between the two arcs, about 2 pixels inside the outer sides
            assert near(pixel(image, float(angle), radius), colour, 2), (radius, angle)


# ---- the chord bar -----------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["viridis", "coolwarm", "hot"])
@pytest.mark.parametrize("place, share", [(0, 1.0), (1, 0.3), (3, 0.8), (41, 0.5), (83, 1.0)])
def test_a_chord_bar_fills_its_place_counterclockwise_in_its_color_and_the_places_next_to_it_are_the_background(tmp_path, name, place, share):
    image = draw(tmp_path, make_bars(chord=(place, share)), name)
    assert near(pixel(image, chord_angle(place), 0.3 * RADIUS), chord_color(name, share))
    assert near(pixel(image, chord_angle(place), 0.8 * RADIUS), chord_color(name, share))
    for neighbour in (place - 1, place + 1):
        assert pixel(image, chord_angle(neighbour), 0.3 * RADIUS) == background(name)
        assert pixel(image, chord_angle(neighbour), 0.8 * RADIUS) == background(name)


def test_the_first_place_starts_straight_up_and_goes_to_the_left_the_last_of_84_ends_straight_up_coming_from_the_right(tmp_path):
    first = draw(tmp_path / "first", make_bars(chord=(0, 1.0)))
    assert near(pixel(first, -0.25 * CHORD_ARC, 0.8 * RADIUS), chord_color("viridis", 1.0))
    assert pixel(first, 0.25 * CHORD_ARC, 0.8 * RADIUS) == background("viridis")
    last = draw(tmp_path / "last", make_bars(chord=(83, 1.0)))
    assert near(pixel(last, 0.25 * CHORD_ARC, 0.8 * RADIUS), chord_color("viridis", 1.0))
    assert pixel(last, -0.25 * CHORD_ARC, 0.8 * RADIUS) == background("viridis")


def test_the_chords_go_counterclockwise_the_place_21_is_a_quarter_turn_to_the_left_of_straight_up(tmp_path):
    image = draw(tmp_path, make_bars(chord=(21, 1.0)))  # counterclockwise from 90 to 94.3 degrees: straight to the left (270 clockwise) is at its edge, 92 is inside
    assert near(pixel(image, 360.0 - 92.0, 0.5 * RADIUS), chord_color("viridis", 1.0))
    assert pixel(image, 90.0, 0.5 * RADIUS) == background("viridis")  # the right-hand side
    assert pixel(image, 360.0 - 80.0, 0.5 * RADIUS) == background("viridis")  # 80 degrees counterclockwise is the place 18


@pytest.mark.parametrize("length", [0.5, 0.75, 1.0])
def test_the_chord_bar_is_as_long_as_the_note_bars(tmp_path, length):
    image = draw(tmp_path, make_bars([(5, 1.0)], chord=(2, 0.8), length=length))
    back = background("viridis")
    chord_tip = tip_of(image, chord_angle(2), chord_color("viridis", 0.8), back)
    note_tip = tip_of(image, note_angle(5), note_color("viridis", 1.0), back)
    assert abs(chord_tip - length * RADIUS) <= 1.0 and abs(chord_tip - note_tip) <= 0.75


def test_the_chord_bar_is_drawn_over_a_note_bar_that_covers_the_same_angles(tmp_path):
    # chord place 0 covers 4.3 degrees counterclockwise from the top: the angles of the note arc 83 (clockwise from 355.7 to 360 degrees)
    image = draw(tmp_path, make_bars([(83, 1.0), (10, 0.9)], chord=(0, 0.6)))
    assert near(pixel(image, note_angle(83), 0.5 * RADIUS), chord_color("viridis", 0.6))  # under the chord: the chord
    assert near(pixel(image, note_angle(10), 0.5 * RADIUS), note_color("viridis", 0.9))  # outside it: the note
    only_note = draw(tmp_path / "n", make_bars([(83, 1.0)]))
    assert near(pixel(only_note, note_angle(83), 0.5 * RADIUS), note_color("viridis", 1.0))


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_colors_of_the_chord_run_from_the_middle_to_the_end_of_the_colormap_and_the_notes_from_the_middle_to_the_start(tmp_path, name):
    table = lookup_table(name)
    quiet = draw(tmp_path / "q", make_bars(chord=(3, 0.0)), name)
    assert near(pixel(quiet, chord_angle(3), 0.3 * RADIUS), tuple(int(v) for v in table[MIDDLE]), 1)
    loud = draw(tmp_path / "l", make_bars(chord=(3, 1.0)), name)
    assert near(pixel(loud, chord_angle(3), 0.3 * RADIUS), tuple(int(v) for v in table[255]), 1)  # the last color
    middle = draw(tmp_path / "m", make_bars(chord=(3, 0.5)), name)
    assert near(pixel(middle, chord_angle(3), 0.3 * RADIUS), tuple(int(v) for v in table[int(np.rint(0.75 * 255))]), 1)
    assert near(pixel(draw(tmp_path / "n", make_bars([(10, 1.0)]), name), note_angle(10), 0.3 * RADIUS), tuple(int(v) for v in table[0]), 1)  # the first color


def test_a_frame_with_a_chord_differs_from_the_same_frame_without_it_only_in_the_chords_place(tmp_path):
    notes = [(5, 1.0), (30, 0.7), (60, 0.9)]
    with_chord = draw(tmp_path / "a", make_bars(notes, chord=(2, 0.8), length=0.8))
    without = draw(tmp_path / "b", make_bars(notes, length=0.8))
    changed = np.argwhere((with_chord != without).any(axis=2))
    assert len(changed) > 100
    for y, x in changed:
        angle = math.degrees(math.atan2(x + 0.5 - CENTER[0], -(y + 0.5 - CENTER[1]))) % 360
        offset = (chord_angle(2, 0.5) - angle + 180) % 360 - 180  # degrees from the middle of the chord's arc
        radius = math.hypot(x + 0.5 - CENTER[0], y + 0.5 - CENTER[1])
        assert abs(offset) <= CHORD_ARC / 2 + math.degrees(1.0 / max(radius, 1.0)), (x, y, offset)


def test_a_chord_bar_and_a_note_bar_in_the_same_frame_both_have_their_own_colors(tmp_path):
    image = draw(tmp_path, make_bars([(5, 1.0)], chord=(2, 0.8)))
    assert near(pixel(image, note_angle(5), 0.3 * RADIUS), note_color("viridis", 1.0))
    assert near(pixel(image, chord_angle(2), 0.3 * RADIUS), chord_color("viridis", 0.8))


def test_a_chord_place_outside_the_84_is_refused(tmp_path):
    bars = make_bars()
    bars.chord_place[0] = 84
    with pytest.raises(ValueError, match="arcs of the bars"):
        write_polar_frames(bars, "viridis", tmp_path / "out", WIDTH, HEIGHT)
    assert not (tmp_path / "out").exists()


# ---- quiet, silent and busy moments (User Story 4) ------------------------------------------------------------------------------------------


def test_a_silent_file_through_write_frames_is_the_background_only(tmp_path):
    write_frames(np.zeros((4, 88)), tmp_path, colormap="viridis", image_type="polar-chords")
    for path in sorted(tmp_path.glob("frame_*.png")):
        assert (np.array(Image.open(path).convert("RGB")).reshape(-1, 3) == background("viridis")).all()


def test_with_all_84_notes_loud_at_once_there_are_as_many_bars_as_notes_shown_and_at_most_one_chord():
    values = np.ones((3, 88))
    for count in (5, 8):
        bars = polar_bars(values, None, count)
        assert (bars.note_slots >= 0).all() and bars.note_slots.shape == (3, count)
        assert bars.note_slots[0].tolist() == list(range(count))  # equal strengths: the lowest notes
        assert (bars.chord_place <= 83).all()


def test_drawing_a_frame_does_not_depend_on_the_frames_around_it_once_the_bars_are_worked_out(tmp_path):
    # the bars follow their notes from frame to frame, so the bars of a frame depend on the frames before it; drawing them does not
    bars = polar_bars(stream(6, seed=9), np.linspace(0, 1, 6), 5)
    order = np.array([3, 0, 5, 1, 4, 2])
    shuffled = PolarBars(bars.note_slots[order], bars.note_shares[order], bars.chord_place[order], bars.chord_share[order], bars.length[order])
    write_polar_frames(bars, "viridis", tmp_path / "a", WIDTH, HEIGHT)
    write_polar_frames(shuffled, "viridis", tmp_path / "b", WIDTH, HEIGHT)
    straight, reordered = all_frames(tmp_path / "a"), all_frames(tmp_path / "b")
    assert reordered == [straight[i] for i in order]


def test_the_picture_of_a_frame_depends_on_the_frames_before_it_because_the_bars_follow_their_notes(tmp_path):
    values = np.zeros((3, 88))
    values[0, 10] = 1.0
    values[1, 40] = 1.0
    values[2, 40] = 1.0
    write_frames(values, tmp_path / "after", colormap="viridis", image_type="polar-chords")
    write_frames(values[1:], tmp_path / "alone", colormap="viridis", image_type="polar-chords")
    assert all_frames(tmp_path / "after")[1] != all_frames(tmp_path / "alone")[0]  # the bar is on its way from the note 10, not yet in the arc of the note 40


# ---- the note layout: rows or spiral ----------------------------------------------------------------------------------------------------------


def test_write_frames_with_the_spiral_layout_draws_the_bars_of_the_spiral_arcs(tmp_path):
    values = stream(8)
    beat = np.linspace(0, 1, 8)
    write_frames(values, tmp_path / "a", colormap="viridis", image_type="polar-chords", beat=beat, note_layout="spiral")
    write_polar_frames(polar_bars(values, beat, 5, note_layout="spiral"), "viridis", tmp_path / "b", WIDTH, HEIGHT)
    assert all_frames(tmp_path / "a") == all_frames(tmp_path / "b")


def test_the_spiral_layout_changes_the_picture_and_rows_is_what_it_always_was(tmp_path):
    values = stream(6)
    write_frames(values, tmp_path / "default", colormap="viridis", image_type="polar-chords")
    write_frames(values, tmp_path / "rows", colormap="viridis", image_type="polar-chords", note_layout="rows")
    write_frames(values, tmp_path / "spiral", colormap="viridis", image_type="polar-chords", note_layout="spiral")
    assert all_frames(tmp_path / "default") == all_frames(tmp_path / "rows") != all_frames(tmp_path / "spiral")


@pytest.mark.parametrize("layout, arc", [("rows", 27), ("spiral", 29)])
def test_middle_c_is_in_the_arc_of_its_layout(tmp_path, layout, arc):
    values = np.zeros((1, 88))
    values[0, 27] = 1.0  # middle C
    write_frames(values, tmp_path, colormap="viridis", image_type="polar-chords", note_layout=layout)
    image = np.array(Image.open(tmp_path / "frame_000000.png").convert("RGB"))
    assert near(pixel(image, note_angle(arc), 0.3 * RADIUS), note_color("viridis", 1.0))
    other = 29 if arc == 27 else 27
    assert pixel(image, note_angle(other), 0.3 * RADIUS) == background("viridis")


def test_the_chord_bar_is_in_the_same_place_in_both_layouts(tmp_path):
    values = np.zeros((1, 88))
    values[0, [27, 31, 34]] = [1.0, 0.9, 0.8]  # C4 E4 G4: (4, 7) on C, the letter 3 (A is 0): place 3 * 7 + 1 = 22
    write_frames(values, tmp_path / "rows", colormap="viridis", image_type="polar-chords", note_layout="rows")
    write_frames(values, tmp_path / "spiral", colormap="viridis", image_type="polar-chords", note_layout="spiral")
    for name in ("rows", "spiral"):
        image = np.array(Image.open(tmp_path / name / "frame_000000.png").convert("RGB"))
        assert near(pixel(image, chord_angle(22), 0.3 * RADIUS), chord_color("viridis", np.sqrt((1.0 + 0.9 + 0.8) / 3)), 2)
