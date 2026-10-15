"""``write_frames(..., image_type="circles")``: the pictures of wandering circles.

No colormap is named and no number of contour levels is assumed (see ``colormap_names.py``). Where a circle should be is
worked out here from the note's frequency (see ``test_circles.py``); what is drawn is watched by a spy on the drawing of
a disc and by decoding the pictures.
"""

import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

import math

from app.services.circles import SUPERSAMPLE
from app.services.colormaps import COLORMAPS, lookup_table
from app.services.frame_rendering import write_frames
from app.services.image_types import IMAGE_TYPES

from .frame_size import HEIGHT, SCALE, WIDTH
from .colormap_names import INVALID
from .test_circles import (
    A4,
    steady,
    RADIUS_MESSAGE,
    RESIZE_MESSAGE,
    C4,
    F3,
    F5,
    MEMORY_MESSAGE,
    NOTES_MESSAGE,
    UNIT_MESSAGE,
    W,
    H,
    expected_step,
)

BACKEND = Path(__file__).resolve().parents[1]
TYPES = ["tiles", "blended", "contour", "circles"]


def notes(*per_frame):
    """(frames, 88) note values; each frame is a dict {note: value}."""
    out = np.zeros((len(per_frame), 88))
    for t, values in enumerate(per_frame):
        for note, value in values.items():
            out[t, note] = value
    return out


def write(frames, directory, **options):
    write_frames(frames, directory, image_type="circles", **options)
    return sorted(directory.glob("frame_*.png"))


def rgb(path):
    return np.asarray(Image.open(path).convert("RGB"))


def name(i):
    return f"frame_{i:06d}.png"


class Discs:
    """Records every disc that is drawn: (box, fill), in the order they are drawn."""

    def __init__(self, monkeypatch, per_reference_pixel=SCALE):
        """``per_reference_pixel``: finished-picture pixels in one pixel of the 252-pixel reference frame (the app's frame by default)."""
        self.calls = []
        original = ImageDraw.ImageDraw.ellipse
        unit = SUPERSAMPLE * per_reference_pixel

        def spy(draw, xy, fill=None, *args, **kwargs):
            x0, y0, x1, y1 = xy  # the box of a disc in the large picture: its last pixel is included, so the far ends are one short
            self.calls.append(((x0 / unit, y0 / unit, (x1 + 1) / unit, (y1 + 1) / unit), fill))  # in reference pixels
            return original(draw, xy, fill, *args, **kwargs)

        monkeypatch.setattr(ImageDraw.ImageDraw, "ellipse", spy)

    def by_frame(self, memory_sizes):
        """Split the calls into frames, given how many discs each frame draws."""
        frames, start = [], 0
        for size in memory_sizes:
            frames.append(self.calls[start : start + size])
            start += size
        assert start == len(self.calls)
        return frames


def pixel(picture, x, y):
    """The pixel of a picture at the place (x, y) given in reference pixels."""
    return picture[min(int(y * SCALE), HEIGHT - 1), min(int(x * SCALE), WIDTH - 1)]


def centre(box):
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def walk(index, unit, count):
    """The places of a steady note's circles, worked out from the frequency (the middle plus the steps, wrapped)."""
    dx, dy = expected_step(index, unit)
    return [((W / 2 + k * dx) % W, (H / 2 + k * dy) % H) for k in range(1, count + 1)]


# --- the pictures -----------------------------------------------------------------------------------------------------------------


def test_every_frame_is_an_rgb_png_of_the_image_size_one_per_input_frame(tmp_path):
    files = write(np.random.default_rng(1).random((6, 88)), tmp_path)
    assert [f.name for f in files] == [name(i) for i in range(6)]
    for f in files:
        image = Image.open(f)
        assert image.size == (WIDTH, HEIGHT) and image.mode == "RGB"


@pytest.mark.parametrize("colormap", COLORMAPS)
@pytest.mark.parametrize("index", [F5, F3, A4, C4, 0, 83, 11, 52])
def test_the_newest_circle_is_at_the_expected_place_in_the_color_of_the_strength(tmp_path, colormap, index):
    unit = 10
    frames = notes(*steady(index, 5))  # the volume alternates 1.0 and 0.5, so the note moves every frame
    files = write(frames, tmp_path, colormap=colormap, circle_unit=unit)
    table = lookup_table(colormap)
    for t, (x, y) in enumerate(walk(index, unit, 5)):
        picture = rgb(files[t])
        share = 1.0 if t % 2 == 0 else 0.5  # the file's loudest value is 1.0
        want = table[int(np.rint(math.sqrt(share) * 255))]  # the square-root scale of the tiles
        assert tuple(pixel(picture, x, y)) == tuple(want), (colormap, index, t)


def test_the_background_is_the_middle_color_of_the_colormap_and_a_silent_input_is_all_that_color(tmp_path):
    for colormap in COLORMAPS:
        middle = tuple(int(v) for v in lookup_table(colormap)[128])  # the table entry at the middle of the scale
        files = write(notes({A4: 1.0}), tmp_path / f"one_{colormap}", colormap=colormap, circle_unit=4)
        picture = rgb(files[0])
        assert tuple(picture[0, 0]) == middle and tuple(picture[-1, -1]) == middle  # far from the one circle
        for f in write(np.zeros((4, 88)), tmp_path / colormap, colormap=colormap, threshold=5, smoothing=0.4, smoothing_window=3):
            assert (rgb(f) == np.array(middle)).all()


def test_a_trail_the_earlier_circles_stay_in_the_picture_until_the_memory_drops_them(tmp_path, monkeypatch):
    discs = Discs(monkeypatch)
    frames = 130
    write(notes(*steady(F5, frames)), tmp_path, circle_memory=100, circle_unit=4)
    sizes = [min(t + 1, 100) for t in range(frames)]  # the memory fills, then stays at 100
    per_frame = discs.by_frame(sizes)
    places = walk(F5, 4, frames)
    for t, drawn in enumerate(per_frame):
        want = places[max(0, t + 1 - 100) : t + 1]  # exactly the last 100 circles, oldest first
        got = [centre(box) for box, _ in drawn]
        assert len(got) == len(want) and np.allclose(np.array(got), np.array(want), atol=1e-9), t


def test_with_several_circles_a_frame_the_count_is_the_circles_so_far_up_to_the_memory(tmp_path, monkeypatch):
    discs = Discs(monkeypatch)
    frames = np.random.default_rng(4).random((40, 88)) + 0.1
    write(frames, tmp_path, circle_notes=8, circle_memory=100)
    sizes = [min((t + 1) * 8, 100) for t in range(40)]
    assert [len(f) for f in discs.by_frame(sizes)] == sizes


def test_the_newest_circle_is_drawn_last_and_within_a_frame_the_strongest_is_on_top(tmp_path, monkeypatch):
    discs = Discs(monkeypatch)
    colormap = COLORMAPS[0]
    frames = notes({F5: 1.0, A4: 0.5, C4: 0.1}, {F5: 1.0, A4: 0.5, C4: 0.1})
    write(frames, tmp_path, colormap=colormap, circle_notes=5, circle_memory=100)
    first, second = discs.by_frame([3, 6])
    table = lookup_table(colormap)
    strongest = tuple(int(v) for v in table[255])
    colour = lambda fill: tuple(fill[:3])  # noqa: E731 - the fill is (r, g, b, opacity)
    assert colour(first[-1][1]) == strongest and colour(second[-1][1]) == strongest  # the last disc of a frame is the strongest note's
    assert first[-1][1][3] == 255 and second[-1][1][3] == 255  # and it is the newest: opaque
    assert [colour(f) for _, f in second[:3]] == [colour(f) for _, f in first]  # the old circles come first, in order
    assert strongest not in [colour(f) for _, f in first[:-1]]


def test_each_disc_has_the_radius_that_was_asked_for_whatever_the_movement_and_the_color_of_its_strength(tmp_path, monkeypatch):
    discs = Discs(monkeypatch)
    colormap = COLORMAPS[0]
    table = lookup_table(colormap)
    for radius, unit in ((4, 4), (6, 4), (6, 10), (8, 1)):
        discs.calls.clear()
        write(notes({F5: 1.0, A4: 0.25}), tmp_path / f"{radius}_{unit}", colormap=colormap, circle_unit=unit, circle_radius=radius)
        assert len(discs.calls) == 2
        for box, fill in discs.calls:
            x0, y0, x1, y1 = box
            assert x1 - x0 == pytest.approx(2 * radius) and y1 - y0 == pytest.approx(2 * radius)
        fills = [fill for _, fill in discs.calls]
        # weakest first: the quarter-strength note (half way along the scale) is the older of the two, one place back in the memory
        assert fills == [(*(int(v) for v in table[round(0.5 * 255)]), round(255 * 299 / 300)), (*(int(v) for v in table[255]), 255)]


def test_the_radius_changes_how_many_pixels_a_circle_covers(tmp_path):
    areas = {}
    for radius in (4, 6, 8):
        files = write(notes({A4: 1.0}), tmp_path / str(radius), colormap=COLORMAPS[0], circle_radius=radius, circle_unit=4)
        picture = rgb(files[0])
        background = np.array(lookup_table(COLORMAPS[0])[128])
        areas[radius] = int((picture != background).any(axis=2).sum())
        assert areas[radius] == pytest.approx(math.pi * radius**2 * SCALE**2, rel=0.25), radius  # the area of a disc of that radius
    assert areas[4] < areas[6] < areas[8]


def test_the_edge_of_a_circle_is_smooth_with_in_between_colors(tmp_path):
    colormap = COLORMAPS[0]
    table = lookup_table(colormap)
    background, colour = np.array(table[128], dtype=int), np.array(table[255], dtype=int)
    picture = rgb(write(notes({A4: 1.0}), tmp_path, colormap=colormap, circle_radius=8)[0]).astype(int)
    pixels = picture.reshape(-1, 3)
    solid = (pixels == background).all(axis=1) | (pixels == colour).all(axis=1)
    edge = pixels[~solid]
    assert len(edge) >= 20  # a hard-edged disc of this size has no such pixels; a smooth one has a ring of them
    low, high = np.minimum(background, colour), np.maximum(background, colour)
    assert ((edge >= low - 1) & (edge <= high + 1)).all()  # every one is a mix of the two colors, nothing else


@pytest.mark.parametrize("radius", [4, 5, 6, 7, 8])
def test_the_area_a_circle_covers_is_that_of_a_disc_of_its_radius_to_within_eight_percent(tmp_path, radius):
    colormap = COLORMAPS[0]
    table = lookup_table(colormap)
    background, colour = np.array(table[128], dtype=float), np.array(table[255], dtype=float)
    channel = int(np.abs(colour - background).argmax())
    picture = rgb(write(notes({A4: 1.0}), tmp_path, colormap=colormap, circle_radius=radius)[0]).astype(float)
    coverage = (picture[:, :, channel] - background[channel]) / (colour[channel] - background[channel])
    assert coverage.sum() == pytest.approx(math.pi * radius**2 * SCALE**2, rel=0.08)  # the shape is kept to a quarter of a pixel


def test_a_note_at_the_same_volume_is_drawn_again_on_the_same_place_and_the_older_circles_there_are_covered(tmp_path, monkeypatch):
    discs = Discs(monkeypatch)
    colormap = COLORMAPS[0]
    files = write(notes(*({F5: 1.0} for _ in range(6))), tmp_path, colormap=colormap, circle_unit=10)
    frames = discs.by_frame([1, 2, 3, 4, 5, 6])
    first = centre(frames[0][0][0])
    for t, drawn in enumerate(frames):
        assert all(centre(box) == pytest.approx(first, abs=1e-9) for box, _ in drawn), t  # all on the one place
        assert drawn[-1][1][3] == 255  # the newest is opaque and hides the older ones under it
    x, y = first
    assert tuple(pixel(rgb(files[-1]), x, y)) == tuple(lookup_table(colormap)[255])


def radius_of(box):
    return (box[2] - box[0]) / 2


def test_the_resize_scales_each_radius_by_the_strength_of_its_note_from_one_to_three_times(tmp_path, monkeypatch):
    discs = Discs(monkeypatch)
    base = 6
    shares = (1e-9, 0.25, 1.0)  # about no energy, a quarter, the loudest note of the file
    write(notes({C4: shares[0], A4: shares[1], F5: shares[2]}), tmp_path, circle_radius=base, circle_resize=True)
    assert len(discs.calls) == 3  # weakest first
    for (box, _), share in zip(discs.calls, shares):
        color = int(np.rint(math.sqrt(share) * 255))
        assert radius_of(box) == pytest.approx(base * (1.0 + 2.0 * color / 255), abs=1e-9)
    assert radius_of(discs.calls[0][0]) == pytest.approx(base * 1.0, abs=1e-9)  # no energy: the radius that was asked for, not smaller
    assert radius_of(discs.calls[2][0]) == pytest.approx(base * 3.0, abs=1e-9)


def test_with_the_resize_off_or_not_given_every_circle_has_the_radius_that_was_set(tmp_path, monkeypatch):
    discs = Discs(monkeypatch)
    base = 7
    frames = notes({C4: 1e-9, A4: 0.25, F5: 1.0})
    write(frames, tmp_path / "a", circle_radius=7)
    write(frames, tmp_path / "b", circle_radius=7, circle_resize=False)
    assert len(discs.calls) == 6
    assert all(radius_of(box) == pytest.approx(base, abs=1e-9) for box, _ in discs.calls)


def test_the_resize_changes_only_the_sizes_not_the_places_the_colors_or_the_opacities(tmp_path, monkeypatch):
    discs = Discs(monkeypatch)
    frames = np.random.default_rng(12).random((15, 88)) ** 2
    write(frames, tmp_path / "off", circle_notes=6, circle_memory=100)
    count = len(discs.calls)
    write(frames, tmp_path / "on", circle_notes=6, circle_memory=100, circle_resize=True)
    off, on = discs.calls[:count], discs.calls[count:]
    assert len(off) == len(on) > 0
    assert np.allclose(np.array([centre(b) for b, _ in off]), np.array([centre(b) for b, _ in on]), atol=1e-9)
    assert [f for _, f in off] == [f for _, f in on]
    assert [radius_of(b) for b, _ in off] != [radius_of(b) for b, _ in on]


def test_no_circle_is_smaller_than_the_radius_or_larger_than_three_times_it_whatever_the_music(tmp_path, monkeypatch):
    discs = Discs(monkeypatch)
    base = 7
    write(np.random.default_rng(21).random((20, 88)) ** 3, tmp_path, circle_radius=base, circle_resize=True, circle_notes=12)
    radii = [radius_of(box) for box, _ in discs.calls]
    assert len(radii) > 0 and min(radii) >= base - 1e-9 and max(radii) <= 3 * base + 1e-9
    assert max(radii) > 1.5 * base  # and the loud ones really are larger


def test_a_circle_keeps_the_size_it_was_given_when_it_was_put_down_while_later_circles_are_other_sizes(tmp_path, monkeypatch):
    discs = Discs(monkeypatch)
    write(notes({F5: 1.0}, {F3: 0.04}), tmp_path, circle_resize=True)
    first, second = discs.by_frame([1, 2])
    assert radius_of(first[0][0]) == radius_of(second[0][0])  # the first circle is drawn the same in the next frame
    assert radius_of(second[1][0]) < radius_of(second[0][0])  # and the quieter new one is smaller


def test_the_loudest_circle_covers_about_nine_times_the_area_when_resized(tmp_path):
    colormap = COLORMAPS[0]
    table = lookup_table(colormap)
    background, colour = np.array(table[128], dtype=float), np.array(table[255], dtype=float)
    channel = int(np.abs(colour - background).argmax())

    def covered(resize):
        picture = rgb(write(notes({A4: 1.0}), tmp_path / str(resize), colormap=colormap, circle_radius=6, circle_resize=resize)[0]).astype(float)
        return ((picture[:, :, channel] - background[channel]) / (colour[channel] - background[channel])).sum()

    assert covered(True) == pytest.approx(9 * covered(False), rel=0.08)  # three times the radius


# --- the circles at another frame width (feature 021): the settings are measured on a 252-pixel-wide reference frame -------------


def melody_values(frames=40, seed=31):
    """(frames, 84) values: a few strong notes at a time, so that circles wander a long way and wrap around."""
    rng = np.random.default_rng(seed)
    values = rng.random((frames, 84)) ** 3
    values[:, 40:] *= 0.1
    return values


def draw_discs(monkeypatch, tmp_path, width, height, per_reference_pixel, **options):
    from app.services.circles import write_circle_frames

    discs = Discs(monkeypatch, per_reference_pixel=per_reference_pixel)
    settings = dict(notes=6, unit=7, memory=100, radius=5, resize=False)
    settings.update(options)
    write_circle_frames(
        melody_values(), 1.0, COLORMAPS[0], tmp_path, settings["notes"], settings["unit"], settings["memory"], settings["radius"], width, height,
        resize=settings["resize"],
    )
    return discs.calls


@pytest.mark.parametrize("resize", [False, True])
def test_a_frame_of_another_width_has_the_same_discs_in_reference_pixels_but_larger_on_the_frame(tmp_path, resize):
    scale = 600 / 252

    def discs(label, width, height, per_reference_pixel):
        with pytest.MonkeyPatch.context() as patch:  # one spy at a time: a spy that stays patched would record the next run too
            return draw_discs(patch, tmp_path / label, width, height, per_reference_pixel, resize=resize)

    small = discs("small", 252, 168, 1.0)
    big = discs("big", 600, 400, scale)  # reported in reference pixels
    raw = discs("raw", 600, 400, 1.0)  # reported in the pixels of the frame itself
    assert len(small) == len(big) == len(raw) > 0
    # reference pixels: the discs are those of the 252 frame (the wrap at 600 x 400 is the wrap at 252 x 168 scaled)
    assert np.allclose(np.array([centre(b) for b, _ in small]), np.array([centre(b) for b, _ in big]), atol=1e-6)
    assert np.allclose(np.array([radius_of(b) for b, _ in small]), np.array([radius_of(b) for b, _ in big]), atol=1e-6)
    assert [f for _, f in small] == [f for _, f in big]  # the same colors and opacities
    # on the frame itself the centers and radii are 600 / 252 times as large
    assert np.allclose(np.array([centre(b) for b, _ in raw]), scale * np.array([centre(b) for b, _ in small]), atol=1e-6)
    assert np.allclose(np.array([radius_of(b) for b, _ in raw]), scale * np.array([radius_of(b) for b, _ in small]), atol=1e-6)


def test_a_circle_has_the_radius_of_the_setting_times_the_frame_width_over_252(tmp_path, monkeypatch):
    discs = draw_discs(monkeypatch, tmp_path, 600, 400, 1.0, radius=4, resize=False)
    for box, _ in discs:
        assert radius_of(box) == pytest.approx(4 * 600 / 252, abs=1e-9)


def test_the_scale_follows_the_width_and_not_the_height(tmp_path, monkeypatch):
    discs = draw_discs(monkeypatch, tmp_path, 600, 300, 1.0, radius=4, resize=False)  # a frame that is not 3:2
    for box, _ in discs:
        assert radius_of(box) == pytest.approx(4 * 600 / 252, abs=1e-9)
        assert 0 <= centre(box)[1] <= 300  # but the wrap-around follows the height


def test_the_picture_at_another_width_is_that_size_and_is_the_reference_picture_reduced(tmp_path):
    from app.services.circles import write_circle_frames

    values = melody_values(12)
    write_circle_frames(values, 1.0, COLORMAPS[0], tmp_path / "small", 6, 7, 100, 5, 252, 168)
    write_circle_frames(values, 1.0, COLORMAPS[0], tmp_path / "big", 6, 7, 100, 5, 600, 400)
    for i in range(12):
        small = Image.open(tmp_path / "small" / name(i))
        big = Image.open(tmp_path / "big" / name(i))
        assert small.size == (252, 168) and big.size == (600, 400) and big.mode == "RGB"
        reduced = np.asarray(big.resize((252, 168), Image.BOX)).astype(int)
        difference = np.abs(reduced - np.asarray(small).astype(int))
        assert difference.mean() < 6.0, (i, difference.mean())  # the same picture, only finer at the edges
        background = np.array(lookup_table(COLORMAPS[0])[128])
        covered_small = (np.asarray(small) != background).any(axis=2).mean()
        covered_big = (np.asarray(big) != background).any(axis=2).mean()
        assert covered_big == pytest.approx(covered_small, rel=0.15), i  # the circles cover the same share of the frame


def test_the_opacity_of_a_circle_falls_with_its_age_until_it_is_barely_visible(tmp_path, monkeypatch):
    discs = Discs(monkeypatch)
    frames = 130
    write(notes(*({F5: 1.0} for _ in range(frames))), tmp_path, circle_memory=100)
    last = discs.by_frame([min(t + 1, 100) for t in range(frames)])[-1]  # the full memory after the last frame
    alphas = [fill[3] for _, fill in last]
    assert alphas == [round(255 * (100 - age) / 100) for age in range(99, -1, -1)]  # oldest first: 3, 5, 8 ... 255
    assert alphas[0] <= 3 and alphas[-1] == 255
    assert alphas == sorted(alphas)


def test_an_old_circle_is_blended_into_the_background_by_its_opacity(tmp_path):
    colormap = COLORMAPS[0]
    table = lookup_table(colormap)
    background = np.array(table[128], dtype=float)
    unit, memory, frames = 10, 100, 5
    index = 83  # G#8: 5 units, so 50 pixels between circles: they do not overlap each other in the first frames
    files = write(notes(*steady(index, frames)), tmp_path, colormap=colormap, circle_unit=unit, circle_memory=memory, circle_radius=4)
    picture = rgb(files[-1])
    for age, (x, y) in enumerate(reversed(walk(index, unit, frames))):  # age 0 is the newest circle
        alpha = round(255 * (memory - age) / memory) / 255
        share = 1.0 if (frames - 1 - age) % 2 == 0 else 0.5  # the volume alternates, so the colors do
        colour = np.array(table[int(np.rint(math.sqrt(share) * 255))], dtype=float)
        want = (1 - alpha) * background + alpha * colour
        got = pixel(picture, x, y).astype(float)
        assert np.abs(got - want).max() <= 3, (age, got, want)  # integer blending in Pillow: within a few levels of 255


def test_the_circles_follow_the_smoothed_values_and_the_colormap_changes_only_the_colors(tmp_path, monkeypatch):
    discs = Discs(monkeypatch)
    impulse = notes({F5: 1.0}, {}, {}, {}, {}, {})
    write(impulse, tmp_path / "plain", circle_unit=4)
    plain_calls = len(discs.calls)
    write(impulse, tmp_path / "smooth", circle_unit=4, smoothing=0.5, smoothing_window=3)
    smooth_calls = len(discs.calls) - plain_calls
    assert plain_calls == 6  # one circle put down in frame 0 and drawn again in each of the six frames: 6 discs in all
    assert smooth_calls > plain_calls  # smoothing leaves a trace in the frames after the impulse: more circles are put down
    # the colormap changes the colors and not the places
    if len(COLORMAPS) > 1:
        before = len(discs.calls)
        write(impulse, tmp_path / "a", colormap=COLORMAPS[0])
        middle = len(discs.calls)
        write(impulse, tmp_path / "b", colormap=COLORMAPS[1])
        a, b = discs.calls[before:middle], discs.calls[middle:]
        assert [centre(c[0]) for c in a] == [centre(c[0]) for c in b]  # the same places
        assert [c[1] for c in a] != [c[1] for c in b]  # in other colors


def test_smoothing_is_applied_before_the_choice_of_the_strongest_note(tmp_path, monkeypatch):
    # a click at note 60 in frame 0 and six steady quieter notes: raw, the click is gone in frame 1; smoothed (0.8, window 1)
    # it still has 0.44 of its value and is the strongest note of frame 1
    discs = Discs(monkeypatch)
    frames = np.zeros((2, 88))
    frames[:, 10:16] = 0.2
    frames[0, 60] = 1.0
    unit = 4
    write(frames, tmp_path / "raw", circle_unit=unit)
    raw_first, raw_second = discs.by_frame([7, 13])  # frame 0: six steady notes and the click; frame 1: the six steady ones are added
    discs.calls.clear()
    write(frames, tmp_path / "smooth", circle_unit=unit, smoothing=0.8, smoothing_window=1)
    smooth_first, smooth_second = discs.by_frame([7, 14])  # smoothed, the click is still there in frame 1
    # the strongest circle of frame 0 is the click's (the last disc of the frame); it is rank 0 in both runs
    place0 = centre(raw_first[-1][0])
    assert place0 == pytest.approx(tuple(walk(60, unit, 1)[0]), abs=1e-9)
    # frame 1: raw, the strongest is the lowest of the steady notes (note 10, ties to the lower); smoothed, it is the click's note again
    dx10, dy10 = expected_step(10, unit)
    dx60, dy60 = expected_step(60, unit)
    assert centre(raw_second[-1][0]) == pytest.approx(((place0[0] + dx10) % W, (place0[1] + dy10) % H), abs=1e-9)
    assert centre(smooth_second[-1][0]) == pytest.approx(((place0[0] + dx60) % W, (place0[1] + dy60) % H), abs=1e-9)


def test_a_very_quiet_file_still_draws_circles_in_the_colors_of_their_share_of_its_own_peak(tmp_path):
    colormap = COLORMAPS[0]
    files = write(notes({F5: 1e-6, A4: 0.25e-6}, {F5: 1e-6}), tmp_path, colormap=colormap, circle_unit=10)
    table = lookup_table(colormap)
    picture = rgb(files[0])
    x, y = walk(F5, 10, 1)[0]
    assert tuple(pixel(picture, x, y)) == tuple(table[255])  # the loudest note of the file: the last color
    assert (picture.reshape(-1, 3).sum(axis=1) > 0).any()


@pytest.mark.parametrize("unit, memory, count, radius", [(1, 100, 5, 4), (10, 500, 12, 8), (1, 500, 12, 8), (10, 100, 5, 4)])
def test_the_settings_at_their_extremes_all_work(tmp_path, unit, memory, count, radius):
    frames = np.random.default_rng(unit + memory + count).random((30, 88)) ** 2
    files = write(frames, tmp_path, circle_unit=unit, circle_memory=memory, circle_notes=count, circle_radius=radius)
    assert len(files) == 30 and all(Image.open(f).size == (WIDTH, HEIGHT) for f in files)


def test_the_other_settings_do_not_apply_to_circles_and_are_ignored(tmp_path):
    frames = np.random.default_rng(6).random((12, 88)) ** 2
    plain = write(frames, tmp_path / "plain")
    ignored = write(
        frames, tmp_path / "ignored", interpolate=5, resolution=5, note_count=12, threshold=10, blend_width=10
    )
    assert [f.read_bytes() for f in plain] == [f.read_bytes() for f in ignored]
    assert len(ignored) == 12  # no frame is skipped: every frame is drawn


def test_two_runs_give_byte_identical_files(tmp_path):
    frames = np.random.default_rng(8).random((20, 88)) ** 2
    options = dict(circle_unit=6, circle_memory=200, circle_notes=10, smoothing=0.3, smoothing_window=3)
    a = write(frames, tmp_path / "a", **options)
    b = write(frames, tmp_path / "b", **options)
    assert [f.read_bytes() for f in a] == [f.read_bytes() for f in b]


# --- the image type list and the refusals ----------------------------------------------------------------------------------------


def test_circles_is_the_fourth_image_type_and_circles_paint_the_fifth():
    assert IMAGE_TYPES == ("tiles", "blended", "contour", "circles", "circles_paint")


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"circle_unit": 0}, UNIT_MESSAGE),
        ({"circle_unit": 11}, UNIT_MESSAGE),
        ({"circle_unit": 2.5}, UNIT_MESSAGE),
        ({"circle_unit": None}, UNIT_MESSAGE),
        ({"circle_memory": 99}, MEMORY_MESSAGE),
        ({"circle_memory": 501}, MEMORY_MESSAGE),
        ({"circle_memory": "300"}, MEMORY_MESSAGE),
        ({"circle_notes": 4}, NOTES_MESSAGE),
        ({"circle_notes": 13}, NOTES_MESSAGE),
        ({"circle_notes": True}, NOTES_MESSAGE),
        ({"circle_radius": 3}, RADIUS_MESSAGE),
        ({"circle_radius": 9}, RADIUS_MESSAGE),
        ({"circle_radius": 5.5}, RADIUS_MESSAGE),
        ({"circle_radius": "6"}, RADIUS_MESSAGE),
        ({"circle_radius": True}, RADIUS_MESSAGE),
        ({"circle_resize": 1}, RESIZE_MESSAGE),
        ({"circle_resize": "true"}, RESIZE_MESSAGE),
        ({"circle_resize": None}, RESIZE_MESSAGE),
        ({"circle_resize": 1.0}, RESIZE_MESSAGE),
    ],
)
def test_a_bad_circle_setting_is_refused_before_anything_is_written_for_every_image_type(tmp_path, image_type, kwargs, message):
    with pytest.raises(ValueError) as error:
        write_frames(np.random.default_rng(1).random((3, 88)), tmp_path / "out", image_type=image_type, **kwargs)
    assert str(error.value) == message
    assert not (tmp_path / "out").exists()


def test_other_arguments_are_still_checked_for_circles(tmp_path):
    for kwargs in ({"colormap": INVALID[0]}, {"threshold": 11}, {"resolution": 6}, {"note_count": 11}, {"interpolate": 6}, {"blend_width": 5}):
        with pytest.raises(ValueError):
            write_frames(np.zeros((3, 88)), tmp_path / "out", image_type="circles", **kwargs)
    assert not (tmp_path / "out").exists()


def test_an_error_while_saving_a_picture_is_raised_and_the_threads_are_shut_down(tmp_path, monkeypatch):
    import threading

    def broken(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(Image.Image, "save", broken)
    before = threading.active_count()
    with pytest.raises(OSError, match="disk full"):
        write(np.random.default_rng(1).random((6, 88)), tmp_path)
    assert threading.active_count() == before


def test_no_frames_and_one_frame_work(tmp_path):
    assert write(np.zeros((0, 88)), tmp_path / "none") == []
    assert [f.name for f in write(notes({A4: 1.0}), tmp_path / "one")] == [name(0)]


# --- the environment and the time ----------------------------------------------------------------------------------------------------


def test_a_circles_job_does_not_import_the_drawing_library_of_matplotlib():
    code = (
        f"import sys, tempfile, pathlib, numpy as np\nsys.path.insert(0, {str(BACKEND)!r})\n"
        "import app.main\n"
        "from app.services.frame_rendering import write_frames\n"
        "d = pathlib.Path(tempfile.mkdtemp())\n"
        "write_frames(np.random.default_rng(1).random((3, 88)), d, image_type='circles')\n"
        "print('matplotlib.pyplot' in sys.modules)\n"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split()[-1] == "False"


def test_three_hundred_frames_with_the_largest_settings_finish_well_within_a_minute(tmp_path):
    frames = np.random.default_rng(3).random((300, 88)) ** 2
    start = time.perf_counter()
    files = write(frames, tmp_path, circle_unit=10, circle_memory=500, circle_notes=12, circle_radius=8, smoothing=0.3, smoothing_window=3)
    elapsed = time.perf_counter() - start
    assert len(files) == 300
    assert elapsed < 60, f"300 circle frames took {elapsed:.1f} s"
