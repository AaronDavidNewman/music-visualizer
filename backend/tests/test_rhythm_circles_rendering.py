"""The picture of the ``rhythm-circles`` image type (feature 038): eight concentric rings, each with a notch that rotates."""

import math
import time

import numpy as np
import pytest
from PIL import Image

from app.services import rhythm_circles as rc
from app.services.colormaps import COLORMAPS, lookup_table

WIDTH, HEIGHT = 600, 400
CENTER = (WIDTH / 2, HEIGHT / 2)
R = HEIGHT / 2 - 10  # the outer radius: 190
N = 8  # the rings
W = R / N  # the width of a ring with its gap: 23.75
GAP = 4
MIDDLE = 128


def ring_rows(k):
    """The colormap rows of ring k (1 outer, 8 innermost) and of its notch, written out here: rint(p x 255) and rint((1 - p) x 255), p = (k - 1) / 7."""
    p = (k - 1) / 7
    return int(np.rint(p * 255)), int(np.rint((1 - p) * 255))


def outer_radius(k):
    return R - (k - 1) * W


def inner_radius(k):
    return R - k * W + GAP


def middle_radius(k):
    return (outer_radius(k) + inner_radius(k)) / 2


def data_of(angles):
    return rc.RhythmData(np.asarray(angles, dtype=float).reshape(-1, N))


def draw(tmp_path, angles, colormap="viridis", size=(WIDTH, HEIGHT), name="frames"):
    directory = tmp_path / name
    data = data_of(angles)
    rc.write_rhythm_frames(data, colormap, directory, *size)
    return [np.asarray(Image.open(directory / f"frame_{i:06d}.png").convert("RGB")) for i in range(data.frame_count)]


def pixel(picture, turns, radius, center=CENTER):
    """The color at ``radius`` pixels from the center in the direction ``turns`` clockwise from straight up."""
    x = center[0] + radius * math.sin(2 * math.pi * turns)
    y = center[1] - radius * math.cos(2 * math.pi * turns)
    return tuple(int(v) for v in picture[int(math.floor(y)), int(math.floor(x))])


def color(table, row):
    return tuple(int(c) for c in table[row])


# --- the files ---------------------------------------------------------------------------------------------------------------


def test_one_png_per_frame_in_rgb_of_the_usual_size_and_the_directory_is_made(tmp_path):
    pictures = draw(tmp_path, np.zeros((3, N)), name="a/b")
    assert len(pictures) == 3 and all(p.shape == (HEIGHT, WIDTH, 3) for p in pictures)
    assert Image.open(tmp_path / "a/b/frame_000000.png").mode == "RGB"
    assert sorted(p.name for p in (tmp_path / "a/b").iterdir()) == [f"frame_{i:06d}.png" for i in range(3)]


@pytest.mark.parametrize("colormap", COLORMAPS)
def test_the_background_is_the_middle_color_of_the_colormap(tmp_path, colormap):
    (picture,) = draw(tmp_path, np.zeros((1, N)), colormap)
    background = color(lookup_table(colormap), MIDDLE)
    for x, y in ((1, 1), (WIDTH - 2, 1), (1, HEIGHT - 2), (WIDTH - 2, HEIGHT - 2)):
        assert tuple(int(v) for v in picture[y, x]) == background


def test_the_same_angles_draw_the_same_bytes(tmp_path):
    angles = np.random.default_rng(1).random((3, N)) * 5 - 2
    first = draw(tmp_path, angles, name="one")
    second = draw(tmp_path, angles, name="two")
    assert all(np.array_equal(a, b) for a, b in zip(first, second))
    assert (tmp_path / "one/frame_000002.png").read_bytes() == (tmp_path / "two/frame_000002.png").read_bytes()


# --- the rings ---------------------------------------------------------------------------------------------------------------


def test_the_eight_rings_have_equal_width_with_a_gap_between_them_and_nothing_outside_or_in_the_hole(tmp_path):
    (picture,) = draw(tmp_path, np.zeros((1, N)))  # every notch at the top: look straight down, away from them
    table = lookup_table("viridis")
    background = color(table, MIDDLE)
    for k in range(1, N + 1):
        ring, _ = ring_rows(k)
        assert pixel(picture, 0.5, middle_radius(k)) == color(table, ring), k
        assert pixel(picture, 0.5, outer_radius(k) - 1.0) == color(table, ring), k  # just inside the outer edge
        assert pixel(picture, 0.5, inner_radius(k) + 1.0) == color(table, ring), k  # just inside the inner edge
        assert pixel(picture, 0.5, outer_radius(k) + 1.0) == background, k  # outside: the gap of the ring outside, or the outside of the picture's rings
        if k < N:
            assert pixel(picture, 0.5, inner_radius(k) - 1.0) == background, k  # the gap before the next ring
    assert pixel(picture, 0.5, 1.5) == background  # the hole in the middle
    assert pixel(picture, 0.5, R + 3) == background


def test_every_ring_is_the_same_width_within_a_pixel(tmp_path):
    (picture,) = draw(tmp_path, np.zeros((1, N)))
    table = lookup_table("viridis")
    for k in range(1, N + 1):
        ring, _ = ring_rows(k)
        width = 0
        for step in range(0, 1990):  # walk straight down from the center in tenths of a pixel (the picture is 200 pixels below it) and measure the ring
            r = step / 10
            if pixel(picture, 0.5, r) == color(table, ring):
                width += 0.1
        assert abs(width - (W - GAP)) <= 1.3, (k, width)


@pytest.mark.parametrize("theta", [0.0, 0.25, 0.5, 0.75, 0.1234, 0.9])
def test_the_notch_of_every_ring_is_in_the_color_at_the_opposite_end_at_the_direction_of_its_angle(tmp_path, theta):
    (picture,) = draw(tmp_path, np.full((1, N), theta))
    table = lookup_table("viridis")
    for k in range(1, N + 1):
        ring, notch = ring_rows(k)
        assert pixel(picture, theta, middle_radius(k)) == color(table, notch), (k, theta)  # in the notch
        for side in (-0.08, 0.08, 0.5):  # 29 degrees either side of the center of the notch, and the opposite side
            assert pixel(picture, theta + side, middle_radius(k)) == color(table, ring), (k, theta, side)


def test_each_ring_has_its_own_angle(tmp_path):
    angles = [0.0, 0.25, 0.5, 0.75, 0.125, 0.875, 0.375, 0.625]
    (picture,) = draw(tmp_path, angles)
    table = lookup_table("viridis")
    for k, theta in enumerate(angles, start=1):
        ring, notch = ring_rows(k)
        assert pixel(picture, theta, middle_radius(k)) == color(table, notch), k
        assert pixel(picture, theta + 0.5, middle_radius(k)) == color(table, ring), k


@pytest.mark.parametrize("k", range(1, N + 1))
def test_the_notch_is_an_eighth_of_the_circle_wide(tmp_path, k):
    (picture,) = draw(tmp_path, np.full((1, N), 0.3))
    table = lookup_table("viridis")
    ring, notch = ring_rows(k)
    samples = [pixel(picture, i / 1440, middle_radius(k)) for i in range(1440)]
    share = sum(1 for c in samples if c == color(table, notch)) / 1440
    assert abs(share - 1 / 8) <= 0.02, (k, share)  # 45 degrees: not 1/16 (0.0625) nor 1/4


@pytest.mark.parametrize("k", [1, N])
def test_the_area_of_the_notch_is_an_eighth_of_the_ring_with_smooth_edges(tmp_path, k):
    # the share of the ring in the notch color, summed over the pixels (a blended edge pixel counts for its blend), is 1/8 within 0.4 percent of the ring: the
    # edges are half a pixel of arc length each side, not hard and not shifted (on the innermost ring a shift of half a pixel is 4 percent of the notch)
    (picture,) = draw(tmp_path, np.full((1, N), 0.3))
    table = lookup_table("viridis")
    ring, notch = ring_rows(k)
    ring_color, notch_color = np.array(color(table, ring), dtype=float), np.array(color(table, notch), dtype=float)
    ys, xs = np.mgrid[0:HEIGHT, 0:WIDTH]
    distance = np.hypot(xs + 0.5 - CENTER[0], ys + 0.5 - CENTER[1])
    inside = (distance > inner_radius(k) + 1.0) & (distance < outer_radius(k) - 1.0)  # away from the edges of the ring itself
    direction = notch_color - ring_color
    share = ((picture[inside].astype(float) - ring_color) @ direction) / (direction @ direction)
    assert abs(share.mean() - 1 / 8) <= 0.004, (k, share.mean())


def test_the_notch_moves_with_the_angle_and_only_the_ring_that_moved_changes(tmp_path):
    still, moved = draw(tmp_path, [[0.0] * N, [0.0] * (N - 1) + [0.5]])
    ys, xs = np.mgrid[0:HEIGHT, 0:WIDTH]
    distance = np.hypot(xs + 0.5 - CENTER[0], ys + 0.5 - CENTER[1])
    outside_last_ring = distance > outer_radius(N) + 2
    assert np.array_equal(still[outside_last_ring], moved[outside_last_ring])  # rings 1 to 7 are the same
    assert not np.array_equal(still[~outside_last_ring], moved[~outside_last_ring])  # ring 8 turned half way round


def test_the_angle_is_taken_modulo_one_turn_and_a_negative_angle_turns_the_other_way(tmp_path):
    base, plus_one, minus = draw(tmp_path, [[0.25] * N, [1.25] * N, [-0.75] * N])
    assert np.array_equal(base, plus_one) and np.array_equal(base, minus)
    big = draw(tmp_path, [[1234.25] * N], name="big")[0]
    assert np.array_equal(base, big)


def test_a_half_turn_swaps_the_notch_for_the_other_side(tmp_path):
    first, second = draw(tmp_path, [[0.0] * N, [0.5] * N])
    table = lookup_table("viridis")
    for k in range(1, N + 1):
        ring, notch = ring_rows(k)
        assert pixel(first, 0.0, middle_radius(k)) == color(table, notch) and pixel(second, 0.5, middle_radius(k)) == color(table, notch)
        assert pixel(first, 0.5, middle_radius(k)) == color(table, ring) and pixel(second, 0.0, middle_radius(k)) == color(table, ring)


def test_a_clockwise_quarter_turn_puts_the_notch_on_the_right(tmp_path):
    (picture,) = draw(tmp_path, np.full((1, N), 0.25))
    table = lookup_table("viridis")
    ring, notch = ring_rows(1)
    assert pixel(picture, 0.25, middle_radius(1)) == color(table, notch)  # clockwise from the top is to the right
    x = int(CENTER[0] + middle_radius(1))
    assert tuple(int(v) for v in picture[int(CENTER[1]), x]) == color(table, notch)
    assert tuple(int(v) for v in picture[int(CENTER[1]), int(CENTER[0] - middle_radius(1))]) == color(table, ring)


# --- bad input, other sizes, speed -------------------------------------------------------------------------------------------


@pytest.mark.parametrize("angles", [np.zeros(N), np.zeros((3, 7)), np.zeros((3, 6)), np.zeros((2, N, 1)), np.full((2, N), np.nan), np.full((2, N), np.inf)])
def test_bad_angles_are_refused_before_anything_is_written(tmp_path, angles):
    with pytest.raises(ValueError):
        rc.write_rhythm_frames(rc.RhythmData(angles), "viridis", tmp_path / "out", WIDTH, HEIGHT)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("colormap, size", [("nope", (WIDTH, HEIGHT)), ("viridis", (0, HEIGHT)), ("viridis", (WIDTH, -1)), ("viridis", (True, HEIGHT)), ("viridis", (600.5, 400))])
def test_a_bad_colormap_or_size_is_refused_before_anything_is_written(tmp_path, colormap, size):
    with pytest.raises(ValueError):
        rc.write_rhythm_frames(data_of(np.zeros((1, N))), colormap, tmp_path / "out", *size)
    assert not (tmp_path / "out").exists()


def test_no_frames_write_nothing_and_do_not_fail(tmp_path):
    rc.write_rhythm_frames(data_of(np.zeros((0, N))), "viridis", tmp_path / "out", WIDTH, HEIGHT)
    assert list((tmp_path / "out").glob("*.png")) == []


def test_another_frame_size_scales_the_rings(tmp_path):
    (picture,) = draw(tmp_path, np.zeros((1, N)), size=(300, 200), name="small")
    table = lookup_table("viridis")
    center = (150.0, 100.0)
    outer = 100 - 10  # 90
    assert picture.shape == (200, 300, 3)
    assert pixel(picture, 0.5, outer - 1.5, center) == color(table, ring_rows(1)[0])
    assert pixel(picture, 0.5, outer + 2.0, center) == color(table, MIDDLE)
    assert pixel(picture, 0.5, 79.75, center) == color(table, MIDDLE)  # the gap of 2 pixels between ring 1 (it starts at 80.75) and ring 2 (it ends at 78.75)
    assert pixel(picture, 0.5, 74.0, center) == color(table, ring_rows(2)[0])


def test_a_hundred_frames_draw_in_a_few_seconds(tmp_path):
    angles = np.random.default_rng(2).random((100, N)) * 10
    started = time.perf_counter()
    rc.write_rhythm_frames(data_of(angles), "viridis", tmp_path / "many", WIDTH, HEIGHT)
    assert time.perf_counter() - started < 10.0
