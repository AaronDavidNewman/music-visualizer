"""The picture of the ``chromatic-decay`` image type (feature 035): twelve circles on a ring in circle-of-fifths order."""

import math
import time

import numpy as np
import pytest
from PIL import Image

from app.services import chromatic_decay as cd
from app.services.colormaps import COLORMAPS, lookup_table
from app.services.decay import ring_colors

WIDTH, HEIGHT = 600, 400
MARGIN = 10
MIDDLE = 128
SIN15 = math.sin(math.pi / 12)


def ring_radius(width=WIDTH, height=HEIGHT):
    return (min(width, height) / 2 - MARGIN) / (1 + SIN15)


def full_radius(width=WIDTH, height=HEIGHT):
    return ring_radius(width, height) * SIN15


def center(position, width=WIDTH, height=HEIGHT):
    """The center of the circle at a place of the ring (0 at the top, clockwise), from the formulas of the contract."""
    angle = math.radians(30 * position)
    return width / 2 + ring_radius(width, height) * math.sin(angle), height / 2 - ring_radius(width, height) * math.cos(angle)


def pixel_at(picture, x, y):
    return tuple(int(v) for v in picture[int(math.floor(y)), int(math.floor(x))])


def points_of(**letters):
    """One frame of 12 points with the given letters (``L3=40`` is letter 3, C)."""
    row = np.zeros(12)
    for name, value in letters.items():
        row[int(name[1:])] = value
    return row


def draw(tmp_path, points, colormap="viridis", size=(WIDTH, HEIGHT), name="frames"):
    directory = tmp_path / name
    points = np.asarray(points, dtype=float).reshape(-1, 12)
    cd.write_chromatic_frames(points, colormap, directory, *size)
    return [np.asarray(Image.open(directory / f"frame_{i:06d}.png").convert("RGB")) for i in range(points.shape[0])]


# --- the files ----------------------------------------------------------------------------------------


def test_one_png_per_frame_in_rgb_of_the_usual_size_and_the_directory_is_made(tmp_path):
    pictures = draw(tmp_path, np.zeros((3, 12)), name="a/b")
    assert len(pictures) == 3 and all(p.shape == (HEIGHT, WIDTH, 3) for p in pictures)
    assert Image.open(tmp_path / "a/b/frame_000000.png").mode == "RGB"
    assert sorted(p.name for p in (tmp_path / "a/b").iterdir()) == [f"frame_{i:06d}.png" for i in range(3)]


@pytest.mark.parametrize("colormap", COLORMAPS)
def test_the_background_is_the_middle_color_of_the_colormap(tmp_path, colormap):
    (picture,) = draw(tmp_path, np.full((1, 12), 40.0), colormap)
    background = tuple(int(c) for c in lookup_table(colormap)[MIDDLE])
    for x, y in ((1, 1), (WIDTH - 2, 1), (1, HEIGHT - 2), (WIDTH - 2, HEIGHT - 2), (WIDTH // 2, HEIGHT // 2)):
        assert pixel_at(picture, x, y) == background


def test_the_same_points_draw_the_same_bytes(tmp_path):
    points = np.random.default_rng(1).random((2, 12)) * 64
    first = draw(tmp_path, points, name="one")
    second = draw(tmp_path, points, name="two")
    assert all(np.array_equal(a, b) for a, b in zip(first, second))
    assert (tmp_path / "one/frame_000001.png").read_bytes() == (tmp_path / "two/frame_000001.png").read_bytes()


# --- the ring ------------------------------------------------------------------------------------------


def test_the_geometry_of_the_ring_lets_two_neighbouring_full_circles_just_touch():
    for k in range(12):
        (x0, y0), (x1, y1) = center(k), center((k + 1) % 12)
        assert math.hypot(x1 - x0, y1 - y0) == pytest.approx(2 * full_radius(), abs=1e-9)
    assert full_radius() == pytest.approx(39.06, abs=0.01) and ring_radius() == pytest.approx(150.94, abs=0.01)
    assert center(0) == pytest.approx((300.0, 200 - ring_radius()), abs=1e-9)  # position 0 is the top


@pytest.mark.parametrize("letter", range(12))
def test_a_letter_with_points_is_drawn_at_its_place_on_the_ring(tmp_path, letter):
    points = np.zeros(12)
    points[letter] = 40.0
    (picture,) = draw(tmp_path, points)
    table = lookup_table("viridis")
    for position in range(12):
        # the circle at every place: the center of the one with points is the last color (40 points), the others the first (0 points)
        want = tuple(int(c) for c in table[255 if position == cd.ring_position(letter) else 0])
        assert pixel_at(picture, *center(position)) == want, (letter, position)


def test_c_is_at_the_top_and_g_is_next_clockwise(tmp_path):
    points = np.zeros(12)
    points[cd.letter_at(0)] = 40.0  # C
    (c_picture,) = draw(tmp_path, points)
    top_x, top_y = center(0)
    assert pixel_at(c_picture, top_x, top_y) == tuple(int(c) for c in lookup_table("viridis")[255])
    assert top_y < 100 and abs(top_x - 300) < 1  # at the top, in the middle
    points = np.zeros(12)
    points[cd.letter_at(1)] = 40.0  # G
    (g_picture,) = draw(tmp_path, points, name="g")
    gx, gy = center(1)
    assert gx > 300 and gy < 200  # clockwise from the top: to the right and above the middle
    assert pixel_at(g_picture, gx, gy) == tuple(int(c) for c in lookup_table("viridis")[255])


def test_nothing_is_drawn_outside_the_full_radius_of_a_circle_on_the_outer_side_of_the_ring(tmp_path):
    (picture,) = draw(tmp_path, np.full((1, 12), 40.0))
    background = pixel_at(picture, 1, 1)
    for k in range(12):
        x, y = center(k)
        angle = math.radians(30 * k)
        outside = (x + (full_radius() + 3) * math.sin(angle), y - (full_radius() + 3) * math.cos(angle))
        assert pixel_at(picture, *outside) == background, k
        inside = (x + (full_radius() - 3) * math.sin(angle), y - (full_radius() - 3) * math.cos(angle))
        assert pixel_at(picture, *inside) != background, k


def test_the_middle_of_the_ring_is_empty_and_neighbouring_full_circles_meet_at_the_midpoint(tmp_path):
    (picture,) = draw(tmp_path, np.full((1, 12), 40.0))
    background = pixel_at(picture, 1, 1)
    assert pixel_at(picture, 300, 200) == background
    for k in range(12):
        (x0, y0), (x1, y1) = center(k), center((k + 1) % 12)
        assert pixel_at(picture, (x0 + x1) / 2, (y0 + y1) / 2) != background, k  # the edges of the two circles meet there


# --- size and color follow the points ----------------------------------------------------------------


def extent_along_the_row(picture, k):
    """The number of pixels of the row through the center of the circle at place ``k`` that are not background, within its box."""
    cx, cy = center(k)
    background = tuple(picture[1, 1])
    row = picture[int(math.floor(cy))]
    half = int(full_radius()) + 4
    left = int(round(cx)) - half
    return sum(1 for x in range(left, left + 2 * half + 1) if tuple(row[x]) != background)


@pytest.mark.parametrize("p", [0, 6, 12, 18, 24, 40, 64])
def test_the_size_of_a_circle_follows_its_points_one_twelfth_at_0_and_full_from_24(tmp_path, p):
    points = np.zeros(12)
    points[cd.letter_at(0)] = p  # the circle at the top
    (picture,) = draw(tmp_path, points)
    radius = full_radius() * (1 / 12 + 11 / 12 * min(p, 24) / 24)
    assert abs(extent_along_the_row(picture, 0) - 2 * radius) <= 2.5


def test_the_color_follows_the_points_like_decay(tmp_path):
    table = lookup_table("viridis")
    for p in (0, 16, 32, 48, 64):
        points = np.zeros(12)
        points[cd.letter_at(0)] = p
        (picture,) = draw(tmp_path, points, name=f"p{p}")
        want = ring_colors(np.array([float(p)]), "viridis")[0]  # (12, 3): ring 1 first
        cx, cy = center(0)
        assert pixel_at(picture, cx, cy) == tuple(int(c) for c in want[0]), p  # the center: ring 1
        if p == 0:
            assert tuple(want[0]) == tuple(table[0])
        if p == 32:
            assert tuple(want[0]) == tuple(table[255])


def test_a_circle_with_more_than_32_points_has_rings_whose_outer_ring_is_a_color_further_back(tmp_path):
    points = np.zeros(12)
    points[cd.letter_at(0)] = 48.0
    (picture,) = draw(tmp_path, points)
    want = ring_colors(np.array([48.0]), "viridis")[0]
    cx, cy = center(0)
    ring_width = full_radius() / 12
    for ring in (1, 6, 12):  # the middle of ring k is at (k - 0.5) widths from the center, probed straight up (away from the ring's center)
        got = pixel_at(picture, cx, cy - (ring - 0.5) * ring_width)
        assert got == tuple(int(c) for c in want[ring - 1]), ring
    assert tuple(want[0]) != tuple(want[11])


def test_only_the_circle_of_a_letter_that_changed_changes(tmp_path):
    a, b = np.zeros(12), np.zeros(12)
    a[cd.letter_at(4)] = 40.0
    b[cd.letter_at(4)] = 20.0
    first, second = draw(tmp_path, np.array([a, b]))
    changed = np.argwhere((first != second).any(axis=2))
    cx, cy = center(4)
    reach = full_radius() + 2
    assert len(changed) > 0
    assert all(abs(x + 0.5 - cx) <= reach and abs(y + 0.5 - cy) <= reach for y, x in changed)


# --- bad input, other sizes, speed --------------------------------------------------------------------


@pytest.mark.parametrize(
    "points",
    [np.zeros((2, 84)), np.zeros(12), np.zeros((2, 11)), np.full((1, 12), np.nan), np.full((1, 12), np.inf), -np.ones((1, 12)), np.full((1, 12), 64.5), np.zeros((2, 12, 1))],
)
def test_bad_points_are_refused_before_anything_is_written(tmp_path, points):
    with pytest.raises(ValueError):
        cd.write_chromatic_frames(points, "viridis", tmp_path / "out", WIDTH, HEIGHT)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("colormap, size", [("nope", (WIDTH, HEIGHT)), ("viridis", (0, HEIGHT)), ("viridis", (WIDTH, -1)), ("viridis", (True, HEIGHT)), ("viridis", (600.5, 400))])
def test_a_bad_colormap_or_size_is_refused_before_anything_is_written(tmp_path, colormap, size):
    with pytest.raises(ValueError):
        cd.write_chromatic_frames(np.zeros((1, 12)), colormap, tmp_path / "out", *size)
    assert not (tmp_path / "out").exists()


def test_no_frames_write_nothing_and_do_not_fail(tmp_path):
    cd.write_chromatic_frames(np.zeros((0, 12)), "viridis", tmp_path / "out", WIDTH, HEIGHT)
    assert list((tmp_path / "out").glob("*.png")) == []


def test_another_frame_size_scales_the_ring(tmp_path):
    letter = cd.letter_at(0)
    points = np.zeros(12)
    points[letter] = 40.0
    (picture,) = draw(tmp_path, points, size=(300, 200))
    assert picture.shape == (200, 300, 3)
    assert pixel_at(picture, *center(0, 300, 200)) == tuple(int(c) for c in lookup_table("viridis")[255])
    assert pixel_at(picture, 150, 100) == tuple(int(c) for c in lookup_table("viridis")[MIDDLE])  # the middle of the ring is empty


def test_a_hundred_frames_draw_in_a_few_seconds(tmp_path):
    points = np.random.default_rng(2).random((100, 12)) * 64
    started = time.perf_counter()
    cd.write_chromatic_frames(points, "viridis", tmp_path / "many", WIDTH, HEIGHT)
    assert time.perf_counter() - started < 10.0


# --- the smooth edges between the rings ------------------------------------------------------------------


def test_the_ring_weights_of_every_pixel_follow_the_formula_of_decay_worked_out_here_pixel_by_pixel():
    places = cd._geometry(WIDTH, HEIGHT)
    ring_width = full_radius() / 12
    rng = np.random.default_rng(4)
    for position in (0, 1, 7):
        rows, columns, distance, weights = places[position]
        cx, cy = center(position)
        height, width = distance.shape
        matrix = weights.reshape(height, width, 12)
        for y, x in zip(rng.integers(0, height, 300), rng.integers(0, width, 300)):
            d = math.hypot(columns.start + x + 0.5 - cx, rows.start + y + 0.5 - cy)
            assert distance[y, x] == pytest.approx(d, abs=1e-3)
            ring = min(max(math.ceil(d / ring_width) - 1, 0), 11)
            inside = d - ring * ring_width
            before = min(max(0.5 - inside, 0.0), 1.0) if ring > 0 else 0.0
            after = min(max(0.5 - (ring_width - inside), 0.0), 1.0) if ring < 11 else 0.0
            want = np.zeros(12)
            want[ring] += 1 - before - after
            want[max(ring - 1, 0)] += before
            want[min(ring + 1, 11)] += after
            assert matrix[y, x] == pytest.approx(want, abs=1e-4)
            assert matrix[y, x].sum() == pytest.approx(1.0, abs=1e-5)


def test_a_pixel_next_to_the_edge_between_two_rings_is_the_blend_the_formula_gives(tmp_path):
    points = np.zeros(12)
    points[cd.letter_at(0)] = 64.0  # the rings run from the last color (ring 1) to the first (ring 12): all different
    (picture,) = draw(tmp_path, points)
    cx, cy = center(0)
    ring_width = full_radius() / 12
    colours = ring_colors(np.array([64.0]), "viridis")[0].astype(float)

    def shares(x, y):
        d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
        ring = min(max(math.ceil(d / ring_width) - 1, 0), 11)
        inside = d - ring * ring_width
        before = min(max(0.5 - inside, 0.0), 1.0) if ring > 0 else 0.0
        after = min(max(0.5 - (ring_width - inside), 0.0), 1.0) if ring < 11 else 0.0
        return ring, before, after

    # the pixels of the circle with the most of two rings in them (the closest to an edge), in the upper half, away from its neighbours
    pixels = [(x, y) for y in range(int(cy) - 38, int(cy) + 1) for x in range(int(cx) - 12, int(cx) + 13)]
    for x, y in sorted(pixels, key=lambda xy: -(shares(*xy)[1] + shares(*xy)[2]))[:20]:
        ring, before, after = shares(x, y)
        assert before + after > 0.3  # these really are blended pixels
        want = (1 - before - after) * colours[ring] + before * colours[max(ring - 1, 0)] + after * colours[min(ring + 1, 11)]
        assert np.abs(np.array(picture[y, x], dtype=float) - want).max() <= 1.5
        assert np.abs(want - colours[ring]).max() > 1.0  # and a blend differs from the plain ring color


# --- the rings that show the beat in the middle (feature 036) -----------------------------------------------------------------

from .test_chromatic_decay_peaks import oracle_distances, oracle_levels  # noqa: E402

PEAK_RADIUS = 70.0
PEAK_RING_WIDTH = PEAK_RADIUS / 12
MIDDLE_X, MIDDLE_Y = WIDTH / 2, HEIGHT / 2


def draw_with_beat(tmp_path, points, beat, colormap="viridis", size=(WIDTH, HEIGHT), name="beat"):
    directory = tmp_path / name
    points = np.asarray(points, dtype=float).reshape(-1, 12)
    cd.write_chromatic_frames(points, colormap, directory, *size, beat=beat)
    return [np.asarray(Image.open(directory / f"frame_{i:06d}.png").convert("RGB")) for i in range(points.shape[0])]


def ring_color(levels_row, k, colormap="viridis"):
    """The color of ring k (1 at the center) from the table, written out here: row rint(level x 255)."""
    return tuple(int(c) for c in lookup_table(colormap)[int(np.rint(levels_row[k - 1] * 255))])


def pixel_for_ring(k, size=(WIDTH, HEIGHT)):
    """The pixel straight up from the middle of the picture whose center is nearest to the middle of ring k."""
    width, height = size
    radius, ring_width = cd.peak_circle_geometry(width, height)
    target = (k - 0.5) * ring_width
    cx, cy = width / 2, height / 2
    column = int(math.floor(cx))
    row = min(range(int(cy - radius) - 2, int(cy) + 1), key=lambda y: abs(math.hypot(column + 0.5 - cx, y + 0.5 - cy) - target))
    return column, row


def test_with_no_beat_there_is_no_target_and_the_middle_is_empty_as_before(tmp_path):
    points = np.random.default_rng(3).random((3, 12)) * 64
    pictures = draw(tmp_path, points)
    ys, xs = np.mgrid[0:HEIGHT, 0:WIDTH]
    middle = np.hypot(xs + 0.5 - MIDDLE_X, ys + 0.5 - MIDDLE_Y) < 100
    for picture in pictures:
        assert (picture[middle] == picture[1, 1]).all()  # nothing in the middle
    explicit = draw_with_beat(tmp_path, points, None, name="none")
    assert all(np.array_equal(x, y) for x, y in zip(pictures, explicit))  # beat=None is exactly the picture without the argument


def test_the_center_pixel_has_the_color_of_the_distance_of_the_current_frame(tmp_path):
    beat = np.array([1.0, 0.0, 0.75, 0.5, 0.25])
    pictures = draw_with_beat(tmp_path, np.zeros((5, 12)), beat)
    table = lookup_table("viridis")
    for f, picture in enumerate(pictures):
        want = tuple(int(c) for c in table[int(np.rint(oracle_distances(beat.tolist())[f] * 255))])  # the distance, stretched over the range of this beat
        assert pixel_at(picture, MIDDLE_X, MIDDLE_Y) == want, f
    assert pixel_at(pictures[0], MIDDLE_X, MIDDLE_Y) == tuple(int(c) for c in table[0])  # at the top of the beat: the first color
    assert pixel_at(pictures[1], MIDDLE_X, MIDDLE_Y) == tuple(int(c) for c in table[255])  # outside every peak: the last color
    assert pixel_at(pictures[4], MIDDLE_X, MIDDLE_Y) == tuple(int(c) for c in table[255])  # the lowest position inside the peaks is the last color too


def test_ring_k_has_the_color_of_the_average_of_the_two_frames_it_stands_for_read_from_the_picture(tmp_path):
    beat = np.zeros(30)
    beat[10] = 1.0  # a peak at frame 10 only
    pictures = draw_with_beat(tmp_path, np.zeros((30, 12)), beat)
    levels = oracle_levels(beat.tolist())
    for f in range(8, 28):
        for k in range(1, 13):
            x, y = pixel_for_ring(k)
            assert pixel_at(pictures[f], x + 0.5, y + 0.5) == ring_color(levels[f], k), (f, k)
    # the peak travels outward: ring 2 is half way at frames 11 and 12, ring 3 at frames 13 and 14
    x2, y2 = pixel_for_ring(2)
    x3, y3 = pixel_for_ring(3)
    half = tuple(int(c) for c in lookup_table("viridis")[int(np.rint(0.5 * 255))])
    assert [f for f in range(30) if pixel_at(pictures[f], x2 + 0.5, y2 + 0.5) == half] == [11, 12]
    assert [f for f in range(30) if pixel_at(pictures[f], x3 + 0.5, y3 + 0.5) == half] == [13, 14]


def test_the_twelve_rings_are_of_equal_width_and_the_colors_change_where_they_should(tmp_path):
    beat = np.random.default_rng(5).random(30)
    pictures = draw_with_beat(tmp_path, np.zeros((30, 12)), beat)
    levels = oracle_levels(beat.tolist())
    frame = 29
    checked = 0
    for y in range(int(MIDDLE_Y) - 75, int(MIDDLE_Y) + 1):
        d = math.hypot(int(MIDDLE_X) + 0.5 - MIDDLE_X, y + 0.5 - MIDDLE_Y)
        ring = min(max(math.ceil(d / PEAK_RING_WIDTH) - 1, 0), 11)
        edge_distance = min(abs(d - k * PEAK_RING_WIDTH) for k in range(0, 13))
        if edge_distance > 0.6 and d < PEAK_RADIUS - 0.6:
            assert pixel_at(pictures[frame], int(MIDDLE_X) + 0.5, y + 0.5) == ring_color(levels[frame], ring + 1), (y, ring)
            checked += 1
    assert checked > 40  # most of the radius was checked


def test_the_target_is_140_pixels_across_and_centered_with_background_just_outside(tmp_path):
    (picture,) = draw_with_beat(tmp_path, np.zeros((1, 12)), np.zeros(1))  # level 1 everywhere: all rings in the last color, which is not the background
    background = tuple(picture[1, 1])
    for line, middle in ((picture[int(MIDDLE_Y)], MIDDLE_X), (picture[:, int(MIDDLE_X)], MIDDLE_Y)):
        lit = [i for i in range(int(middle) - 90, int(middle) + 90) if tuple(line[i]) != background]
        assert abs((max(lit) + 1 - min(lit)) - 140) <= 2.5  # 140 across
        assert abs((max(lit) + 1 + min(lit)) / 2 - middle) <= 1.0  # centered
    for dx, dy in ((72, 0), (-72, 0), (0, 72), (0, -72)):
        assert pixel_at(picture, MIDDLE_X + dx, MIDDLE_Y + dy) == background
    assert pixel_at(picture, MIDDLE_X + 68, MIDDLE_Y) != background


def test_the_circles_of_the_letters_are_the_same_with_and_without_the_target_and_it_does_not_touch_them(tmp_path):
    points = np.full((1, 12), 64.0)  # every circle full size: the nearest to the middle
    (plain,) = draw(tmp_path, points, name="plain")
    (target,) = draw_with_beat(tmp_path, points, np.array([0.3]), name="target")
    ys, xs = np.mgrid[0:HEIGHT, 0:WIDTH]
    distance = np.hypot(xs + 0.5 - MIDDLE_X, ys + 0.5 - MIDDLE_Y)
    outside = distance > 75
    assert np.array_equal(plain[outside], target[outside])  # nothing but the middle changed
    gap = (distance > 73) & (distance < 109)  # between the target and the nearest edge of a circle (111.9 from the middle)
    assert (target[gap] == np.array(tuple(plain[1, 1]))).all()  # background all round: they do not touch


def test_another_frame_size_scales_the_target(tmp_path):
    (picture,) = draw_with_beat(tmp_path, np.zeros((1, 12)), np.zeros(1), size=(300, 200), name="small")
    background = tuple(picture[1, 1])
    last = tuple(int(c) for c in lookup_table("viridis")[255])
    assert pixel_at(picture, 150, 100) == last
    assert max(abs(x - y) for x, y in zip(pixel_at(picture, 150 + 34, 100), last)) <= 1 and pixel_at(picture, 150 + 37, 100) == background  # radius 35 (70 / 2); a blend may be a level off


@pytest.mark.parametrize("beat", [np.zeros(2), np.zeros(4), np.array([0.0, 1.5, 0.0]), np.array([-0.1, 0.0, 0.0]), np.array([np.nan, 0.0, 0.0]), np.zeros((3, 1)), np.array([True, False, True]), "abc"])
def test_a_beat_that_does_not_fit_the_frames_is_refused_before_anything_is_written(tmp_path, beat):
    with pytest.raises(ValueError):
        cd.write_chromatic_frames(np.zeros((3, 12)), "viridis", tmp_path / "out", WIDTH, HEIGHT, beat=beat)
    assert not (tmp_path / "out").exists()


def test_the_picture_with_the_target_is_deterministic(tmp_path):
    points = np.random.default_rng(4).random((4, 12)) * 64
    beat = np.random.default_rng(5).random(4)
    first = draw_with_beat(tmp_path, points, beat, name="one")
    second = draw_with_beat(tmp_path, points, beat, name="two")
    assert all(np.array_equal(a, b) for a, b in zip(first, second))
    assert (tmp_path / "one/frame_000003.png").read_bytes() == (tmp_path / "two/frame_000003.png").read_bytes()


def test_a_hundred_frames_with_a_beat_draw_in_a_few_seconds(tmp_path):
    rng = np.random.default_rng(6)
    started = time.perf_counter()
    cd.write_chromatic_frames(rng.random((100, 12)) * 64, "viridis", tmp_path / "many", WIDTH, HEIGHT, beat=rng.random(100))
    assert time.perf_counter() - started < 10.0


def test_a_beat_that_only_goes_from_0_6_to_1_fills_the_picture_with_the_whole_colormap_from_the_first_color_to_the_last(tmp_path):
    beat = np.concatenate([np.linspace(1.0, 0.6, 30), np.linspace(0.6, 1.0, 30)])  # real music: never near 0 inside a peak
    pictures = draw_with_beat(tmp_path, np.zeros((60, 12)), beat, colormap="coolwarm")
    table = lookup_table("coolwarm")
    centers = [pixel_at(p, MIDDLE_X, MIDDLE_Y) for p in pictures]
    assert centers[0] == tuple(int(c) for c in table[0])  # the top of the beat: the first color
    rows = sorted({int(np.argmin(np.abs(table.astype(int) - np.array(c)).sum(axis=1))) for c in centers})
    assert rows[0] <= 2 and rows[-1] >= 250  # from one end of the colormap to the other
    assert len(rows) >= 25  # and through the colors between, past the middle one (128) as well as before it
    assert any(r > 140 for r in rows) and any(r < 115 for r in rows)
