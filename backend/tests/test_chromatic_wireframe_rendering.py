"""The picture of the ``chromatic-wireframe`` image type (feature 039): one line for each frame, in the color of its place in the beat."""

import time

import numpy as np
import pytest
from PIL import Image

from app.services import chromatic_wireframe as cw
from app.services.colormaps import COLORMAPS, lookup_table

WIDTH, HEIGHT = 600, 400
LINES = 66  # the lines that fit on 600 x 400: the stack runs from the bottom margin to the top one
STEP = 4
BASE = 390.0  # the base of the front line: the bottom margin
COLORMAP = "viridis"
TABLE = lookup_table(COLORMAP)
FIRST, LAST = (np.array(TABLE[row], dtype=float) for row in (0, 255))
BACKGROUND = np.zeros(3)  # the picture is on black, whatever the colormap
# positions in the beat: LOW is the bottom of the range of the peaks (the first color, the background's), OFF is half way up it, TOP the top of a peak (the last color)
LOW, OFF, TOP = 0.6, 0.8, 1.0


def stretched_distance(beat):
    """The distance from the peak stretched over the range of the beat of the file, written out here (as ``chromatic_decay.beat_distances`` defines it)."""
    beat = np.asarray(beat, dtype=float)
    inside = beat > 0
    low, high = float(np.percentile(beat[inside], 1)), float(beat[inside].max())
    return np.clip((high - beat) / (high - low), 0.0, 1.0)


def colors_of(beat):
    """The color of the line of every frame of ``beat`` as ``write`` draws it (with the extra frame at LOW that gives the others their range)."""
    distance = stretched_distance(list(beat) + [LOW])
    return [np.array(TABLE[int(np.rint((1 - d) * 255))], dtype=float) for d in distance[:-1]]


def read(directory, index):
    return np.asarray(Image.open(directory / f"frame_{index:06d}.png").convert("RGB"))


def write(tmp_path, points, beat=None, colormap=COLORMAP, width=WIDTH, height=HEIGHT, name="frames"):
    """Write the frames. With a beat, one silent frame at LOW is added at the end: it is the bottom of the range, so that the other positions are not the first color."""
    directory = tmp_path / name
    points = np.asarray(points, dtype=float)
    if beat is not None and len(beat):
        points = np.vstack([points, np.zeros((1, 12))])
        beat = list(beat) + [LOW]
    cw.write_wireframe_frames(points, colormap, directory, width, height, beat)
    return directory


def silent(frames):
    return np.zeros((frames, 12))


# a frame with points of very different sizes: its letters have different frequencies and amplitudes, and the sum swings about 40 pixels up and 20 down (a frame of equal
# points would be a flat line, the sines of the 12 letters cancelling each other, and a silent one too)
LOUD = np.random.default_rng(3).uniform(0, 64, 12)


def probe(picture, depth, index, points_row, lines=LINES, width=WIDTH, height=HEIGHT):
    """The pixel at the screen position of vertex ``index`` of the line of ``points_row`` at ``depth``."""
    X, Z = cw.line_heights(points_row, width, height)
    x, y = cw.project_line(X, Z, depth, lines, width, height)
    return picture[int(np.floor(y[index])), int(np.floor(x[index]))].astype(float)


def share(pixel, color, background=BACKGROUND):
    """How much of the way from the background to ``color`` the pixel is, and how far it is from that straight line (a mix of the two)."""
    direction = color - background
    fraction = float((pixel - background) @ direction / (direction @ direction))
    residual = float(np.abs(pixel - (background + fraction * direction)).max())
    return fraction, residual


def has_color(pixel, color, minimum=0.55):
    fraction, residual = share(pixel, color)
    return fraction >= minimum and residual <= 14


def is_background(pixel):
    return bool(np.abs(pixel - BACKGROUND).max() <= 1)


SAMPLES = int(np.ceil(2 * (WIDTH - 2 * cw.MARGIN))) + 1  # the points of a line
INTERIOR = [k * (SAMPLES - 1) // 13 for k in range(1, 13)]  # twelve points spread along the line, away from its ends


# ---------------------------------------------------------------- files and background


def test_one_rgb_png_per_frame_with_the_names_of_the_other_types(tmp_path):
    directory = write(tmp_path, silent(4), None)
    assert sorted(p.name for p in directory.iterdir()) == [f"frame_{i:06d}.png" for i in range(4)]
    image = Image.open(directory / "frame_000000.png")
    assert image.size == (WIDTH, HEIGHT) and image.mode == "RGB"


@pytest.mark.parametrize("colormap", COLORMAPS)
def test_the_background_is_black_for_every_colormap(tmp_path, colormap):
    directory = write(tmp_path, silent(1), [TOP], colormap=colormap)
    picture = read(directory, 0)
    expected = (0, 0, 0)
    for x, y in ((0, 0), (WIDTH - 1, 0), (0, HEIGHT - 1), (WIDTH - 1, HEIGHT - 1), (300, 5)):
        assert tuple(picture[y, x]) == tuple(expected)


# ---------------------------------------------------------------- one line for each frame


def test_the_front_line_is_drawn_in_the_color_of_its_frame(tmp_path):
    beat = [OFF, TOP, OFF, TOP, OFF]
    directory = write(tmp_path, silent(5), beat)
    row = np.zeros(12)
    for t, color in enumerate(colors_of(beat)):
        picture = read(directory, t)
        for index in INTERIOR:
            assert has_color(probe(picture, 0, index, row), color), (t, index)


def test_each_line_has_one_color_along_its_whole_length(tmp_path):
    directory = write(tmp_path, silent(3), [OFF, TOP, OFF])
    picture = read(directory, 1)
    row = np.zeros(12)
    X, _ = cw.line_heights(row, WIDTH, HEIGHT)
    colors = colors_of([OFF, TOP, OFF])
    for depth, color in ((0, colors[1]), (1, colors[0])):
        for index in range(0, X.size, 7):
            assert has_color(probe(picture, depth, index, row), color, minimum=0.45), (depth, index)


def test_a_picture_has_a_line_for_every_frame_so_far_and_not_more(tmp_path):
    frames = 80
    beat = [TOP if f % 2 else OFF for f in range(frames)]
    colors = colors_of(beat)
    directory = write(tmp_path, silent(frames), beat)
    row = np.zeros(12)
    # the first picture has the front line only; the second has two
    first, second = read(directory, 0), read(directory, 1)
    assert has_color(probe(first, 0, INTERIOR[5], row), colors[0])
    assert is_background(probe(first, 1, INTERIOR[5], row, lines=LINES))
    assert has_color(probe(second, 1, INTERIOR[5], row), colors[0])  # the line of frame 0 is at depth 1
    # a picture with history to spare shows exactly as many lines as fit: the line at the place of a 57th is not there
    last = read(directory, frames - 1)
    assert has_color(probe(last, LINES - 1, INTERIOR[5], row), colors[frames - LINES])
    X, Z = cw.line_heights(row, WIDTH, HEIGHT)
    x, y = cw.project_line(X, Z, LINES - 1, LINES, WIDTH, HEIGHT)
    beyond = last[int(round(y[INTERIOR[5]] - STEP)), int(x[INTERIOR[5]])].astype(float)
    assert is_background(beyond)


def test_the_colors_move_back_with_their_frames(tmp_path):
    beat = [OFF, TOP, TOP, OFF, OFF, OFF, TOP, OFF, TOP, TOP]
    colors = colors_of(beat)
    directory = write(tmp_path, silent(10), beat)
    row = np.zeros(12)
    for t in range(10):
        picture = read(directory, t)
        for depth in range(t + 1):
            assert has_color(probe(picture, depth, INTERIOR[3], row), colors[t - depth]), (t, depth)


def test_lines_of_different_frames_have_different_colors_when_their_places_in_the_beat_differ(tmp_path):
    directory = write(tmp_path, silent(2), [OFF, TOP])
    picture = read(directory, 1)
    row = np.zeros(12)
    colors = colors_of([OFF, TOP])
    front, behind = probe(picture, 0, INTERIOR[2], row), probe(picture, 1, INTERIOR[2], row)
    assert has_color(front, colors[1]) and has_color(behind, colors[0])
    assert np.abs(front - behind).max() > 60


def test_the_shape_of_a_line_follows_the_points_of_its_frame(tmp_path):
    rows = np.zeros((2, 12))
    rows[1] = LOUD
    directory = write(tmp_path, rows, [TOP, TOP])
    picture = read(directory, 1)
    front = rows[1]
    # the front line is not the line of the silent frame: it is drawn where its own heights put it (the front line is drawn last, so nothing covers it)
    X, Z = cw.line_heights(front, WIDTH, HEIGHT)
    _, y = cw.project_line(X, Z, 0, LINES, WIDTH, HEIGHT)
    assert np.ptp(y) > 30  # large swings
    hits = sum(has_color(probe(picture, 0, i, front), colors_of([TOP, TOP])[1], minimum=0.4) for i in range(0, X.size, 5))
    assert hits > 0.85 * len(range(0, X.size, 5))


def test_no_beat_draws_every_line_in_the_first_color(tmp_path):
    directory = write(tmp_path, silent(4), None)
    picture = read(directory, 3)
    row = np.zeros(12)
    for depth in range(4):
        assert has_color(probe(picture, depth, INTERIOR[4], row), FIRST)
    assert not np.any(np.all(np.abs(picture.astype(float) - LAST) <= 3, axis=2))


def test_silence_draws_the_same_flat_line_in_every_frame(tmp_path):
    directory = write(tmp_path, silent(8), [OFF] * 8)
    picture = read(directory, 7)
    X, Z = cw.line_heights(np.zeros(12), WIDTH, HEIGHT)
    assert np.ptp(Z) < 1e-9  # no points, no frequency: the sines are constants and sum to nothing
    colors = colors_of([OFF] * 8)
    for depth in range(8):
        assert has_color(probe(picture, depth, INTERIOR[0], np.zeros(12)), colors[7 - depth])


# ---------------------------------------------------------------- repeatable, checked, quick


def test_the_same_input_gives_the_same_bytes_and_the_directory_is_made(tmp_path):
    rng = np.random.default_rng(5)
    points = rng.uniform(0, 64, size=(6, 12))
    beat = rng.uniform(0, 1, size=6)
    one = write(tmp_path, points, beat, name="a/b/one")
    two = write(tmp_path, points, beat, name="two")
    for index in range(6):
        assert (one / f"frame_{index:06d}.png").read_bytes() == (two / f"frame_{index:06d}.png").read_bytes()


@pytest.mark.parametrize(
    "bad",
    [
        np.zeros((3, 11)),
        np.zeros((3, 13)),
        np.zeros(12),
        np.full((3, 12), np.nan),
        np.full((3, 12), np.inf),
        np.full((3, 12), -0.5),
        np.full((3, 12), 64.5),
    ],
)
def test_bad_points_are_refused_before_anything_is_written(tmp_path, bad):
    with pytest.raises(ValueError):
        cw.write_wireframe_frames(bad, COLORMAP, tmp_path / "out", WIDTH, HEIGHT, None)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("beat", [[0.1, 0.2], [0.1, 0.2, 0.3, 0.4], [0.1, np.nan, 0.3], [0.1, 1.5, 0.3], [-0.1, 0.2, 0.3], [[0.1, 0.2, 0.3]]])
def test_a_bad_beat_is_refused_before_anything_is_written(tmp_path, beat):
    with pytest.raises(ValueError):
        cw.write_wireframe_frames(silent(3), COLORMAP, tmp_path / "out", WIDTH, HEIGHT, beat)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("colormap, size", [("nonesuch", (600, 400)), (COLORMAP, (0, 400)), (COLORMAP, (600, 30)), (COLORMAP, (600.0, 400)), (COLORMAP, (True, 400))])
def test_a_bad_colormap_or_size_is_refused_before_anything_is_written(tmp_path, colormap, size):
    with pytest.raises(ValueError):
        cw.write_wireframe_frames(silent(3), colormap, tmp_path / "out", size[0], size[1], None)
    assert not (tmp_path / "out").exists()


def test_a_hundred_frames_are_drawn_in_a_few_seconds(tmp_path):
    rng = np.random.default_rng(2)
    started = time.perf_counter()
    write(tmp_path, rng.uniform(0, 64, size=(100, 12)), rng.uniform(0, 1, size=100))
    assert time.perf_counter() - started < 60


def test_no_frames_write_nothing_and_do_not_fail(tmp_path):
    directory = write(tmp_path, np.zeros((0, 12)), [])
    assert list(directory.iterdir()) == []


def test_an_older_line_has_the_shape_of_its_own_frame(tmp_path):
    rows = np.zeros((2, 12))
    rows[0] = LOUD  # an older frame with a large swing; the front frame is silent
    directory = write(tmp_path, rows, [OFF, OFF])
    picture = read(directory, 1)
    colors = colors_of([OFF, OFF])
    X, Z = cw.line_heights(rows[0], WIDTH, HEIGHT)
    x, y = cw.project_line(X, Z, 1, LINES, WIDTH, HEIGHT)
    _, front_y = cw.project_line(*cw.line_heights(rows[1], WIDTH, HEIGHT), 0, LINES, WIDTH, HEIGHT)
    away = [i for i in range(0, X.size, 5) if front_y[i] - y[i] > 4]  # above the front line: below it the older line is hidden
    assert len(away) > 40
    hits = sum(has_color(probe(picture, 1, i, rows[0]), colors[0], minimum=0.4) for i in away)
    assert hits > 0.85 * len(away)


def test_points_that_are_not_twelve_columns_are_refused_even_when_there_are_no_frames(tmp_path):
    for bad in (np.zeros((0, 5)), np.zeros((0, 13)), np.zeros((0,))):
        with pytest.raises(ValueError):
            cw.write_wireframe_frames(bad, COLORMAP, tmp_path / "out", WIDTH, HEIGHT, None)
        assert not (tmp_path / "out").exists()


# ---------------------------------------------------------------- the view: hidden lines, depth, limits, look


def test_a_front_line_that_is_high_hides_the_older_line_below_it(tmp_path):
    rows = np.zeros((2, 12))
    rows[1] = LOUD  # the front line swings up: where it does the older, silent line is below it
    directory = write(tmp_path, rows, [OFF, TOP])
    picture = read(directory, 1)
    colors = colors_of([OFF, TOP])
    _, Z = cw.line_heights(rows[1], WIDTH, HEIGHT)
    high = [i for i in range(0, SAMPLES, 11) if Z[i] > 8]  # where the front line is well above its base the silent line behind it is under it
    assert len(high) > 20
    for index in high:
        assert is_background(probe(picture, 1, index, rows[0]))  # hidden: the area below the front line is the background
        assert has_color(probe(picture, 0, index, rows[1]), colors[1])
    assert is_background(picture[HEIGHT - 3, 300].astype(float))  # below the lowest line, down to the bottom edge


def test_an_older_line_above_the_front_line_is_seen(tmp_path):
    rows = np.zeros((2, 12))
    rows[0] = LOUD  # the older line swings high, above the silent front line
    directory = write(tmp_path, rows, [OFF, TOP])
    picture = read(directory, 1)
    colors = colors_of([OFF, TOP])
    X, Z = cw.line_heights(rows[0], WIDTH, HEIGHT)
    _, older_y = cw.project_line(X, Z, 1, LINES, WIDTH, HEIGHT)
    _, front_y = cw.project_line(*cw.line_heights(rows[1], WIDTH, HEIGHT), 0, LINES, WIDTH, HEIGHT)
    seen = [i for i in range(0, SAMPLES, 11) if front_y[i] - older_y[i] > 12]  # where the older line is well above the front one (the front one is flat)
    assert len(seen) > 20
    for index in seen:
        assert has_color(probe(picture, 1, index, rows[0]), colors[0])
        assert has_color(probe(picture, 0, index, rows[1]), colors[1])


def test_where_two_lines_cross_the_nearer_one_is_on_top(tmp_path):
    older = LOUD
    front = np.random.default_rng(4).uniform(0, 64, 12)  # another loud frame: its line crosses the older one in several places
    colors = colors_of([OFF, TOP])
    directory = write(tmp_path, np.array([older, front]), [OFF, TOP])
    picture = read(directory, 1)
    xo, yo = cw.project_line(*cw.line_heights(older, WIDTH, HEIGHT), 1, LINES, WIDTH, HEIGHT)
    xf, yf = cw.project_line(*cw.line_heights(front, WIDTH, HEIGHT), 0, LINES, WIDTH, HEIGHT)
    difference = yf - np.interp(xf, xo, yo)
    crossings = [i for i in range(len(xf) - 1) if difference[i] * difference[i + 1] < 0 and abs(difference[i]) < 1]
    assert len(crossings) >= 2  # the two lines do cross
    for i in crossings[:4]:
        pixel = picture[int(yf[i]), int(xf[i])].astype(float)
        assert np.abs(pixel - colors[1]).sum() < np.abs(pixel - colors[0]).sum()  # the pixel on both lines is the color of the nearer one


def test_older_lines_are_a_step_higher_and_smaller(tmp_path):
    frames = 80
    beat = [OFF] * frames
    directory = write(tmp_path, silent(frames), beat)
    picture = read(directory, frames - 1)
    colors = colors_of(beat)
    row = np.zeros(12)
    X, Z = cw.line_heights(row, WIDTH, HEIGHT)
    assert np.ptp(Z) == 0  # silent: every line is flat on its base, so a line's place is exactly base - depth x step
    x, y = cw.project_line(X, Z, LINES - 1, LINES, WIDTH, HEIGHT)
    assert y[0] == pytest.approx(BASE - (LINES - 1) * STEP) and np.ptp(y) == 0
    # the oldest line runs from 75 % of the half width either side of the middle, 65 steps higher: it is drawn there, at both ends
    assert x.min() == pytest.approx(300 - 290 * 0.75) and x.max() == pytest.approx(300 + 290 * 0.75)
    for index in (3, SAMPLES - 4):
        assert has_color(probe(picture, LINES - 1, index, row), colors[frames - LINES], minimum=0.4)
    # in the rows above the line of depth 60 only the lines older than it are drawn, which are not wider than the one of depth 61
    top = BASE - 60 * STEP - 3
    level = picture[: int(top)].astype(float)
    inked = np.where((np.abs(level - BACKGROUND).max(axis=2) > 40).any(axis=0))[0]
    wide = 290 * (1 - 0.25 * 61 / (LINES - 1))
    assert inked.min() >= 300 - wide - 2 and inked.max() <= 300 + wide + 2
    assert inked.min() <= 300 - 290 * 0.75 + 3 and inked.max() >= 300 + 290 * 0.75 - 3  # and the oldest of them does reach its own width
    # the front line is on the bottom margin and spans the whole plot
    front = picture[int(BASE) - 4 : int(BASE) + 4].astype(float)
    inked = np.where((np.abs(front - BACKGROUND).max(axis=2) > 40).any(axis=0))[0]
    assert inked.min() <= 11 and inked.max() >= WIDTH - 12


@pytest.mark.parametrize("size", [(600, 400), (300, 200), (1000, 300), (640, 360)])
def test_no_line_leaves_the_picture(tmp_path, size):
    width, height = size
    rng = np.random.default_rng(width)
    frames = cw.line_geometry(width, height)[0] + 6
    sets = (("extremes", rng.choice([0.0, 64.0], size=(frames, 12))), ("random", rng.uniform(0, 64, size=(frames, 12))), ("loud", np.tile(LOUD, (frames, 1))))
    for name, points in sets if size == (WIDTH, HEIGHT) else sets[1:]:  # (the other sizes only with the random points and the full swing, to keep the test quick)
        directory = write(tmp_path, points, rng.uniform(0, 1, size=frames), width=width, height=height, name=name)
        picture = read(directory, frames - 1).astype(float)
        ink = np.abs(picture - BACKGROUND).max(axis=2) > 1
        margin = cw.MARGIN
        assert not ink[:, : margin - 1].any() and not ink[:, width - margin + 1 :].any()  # left and right
        assert not ink[: margin - 1].any() and not ink[height - margin + 1 :].any()  # top and bottom
        assert ink.any()


def test_the_front_line_and_the_step_scale_with_the_picture(tmp_path):
    width, height = 300, 200
    lines = cw.line_geometry(width, height)[0]
    assert lines == 61
    directory = write(tmp_path, silent(4), [OFF, TOP, OFF, TOP], width=width, height=height)
    picture = read(directory, 3)
    row = np.zeros(12)
    samples = int(np.ceil(2 * cw.band_width(width))) + 1
    colors = colors_of([OFF, TOP, OFF, TOP])
    for depth in range(4):
        assert has_color(probe(picture, depth, 5 * samples + 7, row, lines, width, height), colors[3 - depth])
    X, Z = cw.line_heights(row, width, height)
    _, y0 = cw.project_line(X, Z, 0, lines, width, height)
    _, y1 = cw.project_line(X, Z, 1, lines, width, height)
    assert y0[5 * samples + 7] == pytest.approx(190) and y1[5 * samples + 7] == pytest.approx(188)  # the base is the bottom margin (200 - 10), a step of 2


def test_the_stroke_is_thin_and_smooth(tmp_path):
    directory = write(tmp_path, silent(1), [TOP])
    picture = read(directory, 0).astype(float)
    X, Z = cw.line_heights(np.zeros(12), WIDTH, HEIGHT)
    x, y = cw.project_line(X, Z, 0, LINES, WIDTH, HEIGHT)
    for index in INTERIOR:
        column = picture[:, int(x[index])]
        fractions = np.array([share(pixel, LAST)[0] for pixel in column])
        covered = fractions[fractions > 0.05]
        assert 1.2 <= fractions.clip(0, 1).sum() <= 2.2  # about 1.5 pixels thick
        assert 2 <= len(covered) <= 3
        assert ((fractions > 0.1) & (fractions < 0.9)).any()  # an edge pixel is a mix of the line and the background: smooth
