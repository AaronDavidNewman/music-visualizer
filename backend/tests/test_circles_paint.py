"""Circles paint (feature 022): the circles of Circles, with no memory, painted onto a copy of the previous picture.

The circles themselves (which notes, where, which color, how large) are those of ``plan_circles`` and are tested in
``test_circles.py``; this module is about the canvas: what a frame is made of, what is solid and what is smooth, what is kept.
"""

import math
import threading

import numpy as np
import pytest
from PIL import Image

from app.services import circles, circles_paint
from app.services.circles import MIDDLE_COLOR_ROW, REFERENCE_WIDTH, SUPERSAMPLE, plan_circles, resize_factor
from app.services.colormaps import COLORMAPS, lookup_table

from .frame_size import HEIGHT, SCALE, WIDTH
from .test_circles import (
    A4,
    C4,
    F3,
    F5,
    MEMORY_MESSAGE,
    NOTES_MESSAGE,
    RADIUS_MESSAGE,
    RESIZE_MESSAGE,
    UNIT_MESSAGE,
    expected_step,
    frames_of,
    steady,
)


def paint(values, directory, colormap=None, peak=None, notes=8, unit=4, radius=4, resize=False, width=WIDTH, height=HEIGHT):
    """Write the frames of ``values`` ((frames, 84)) and return them as a list of (height, width, 3) arrays."""
    peak = float(values.max()) if peak is None else peak
    colormap = COLORMAPS[0] if colormap is None else colormap
    circles_paint.write_paint_frames(values, peak, colormap, directory, notes, unit, radius, width, height, resize)
    files = sorted(directory.glob("frame_*.png"))
    assert [f.name for f in files] == [f"frame_{i:06d}.png" for i in range(len(values))]
    return [np.asarray(Image.open(f)) for f in files]


def color_of(colormap, share):
    """The colormap's color for a note whose share of the file's loudest value is ``share`` (the tiles' square-root scale)."""
    return tuple(int(v) for v in lookup_table(colormap)[int(np.rint(math.sqrt(share) * 255))])


def background_of(colormap):
    return tuple(int(v) for v in lookup_table(colormap)[MIDDLE_COLOR_ROW])


def coverage(picture, colormap, color):
    """How much of ``color`` a picture of a circle on the plain background shows at each pixel: 0 (background) to 1 (the color)."""
    background, color = np.array(background_of(colormap), dtype=float), np.array(color, dtype=float)
    channel = int(np.abs(color - background).argmax())
    return (picture[:, :, channel].astype(float) - background[channel]) / (color[channel] - background[channel])


def centroid(weights):
    ys, xs = np.mgrid[0 : weights.shape[0], 0 : weights.shape[1]]
    total = weights.sum()
    return (xs * weights).sum() / total + 0.5, (ys * weights).sum() / total + 0.5  # the center of the pixel is at +0.5


def circle_boxes(values, notes=8, unit=4, radius=4, resize=False):
    """For every frame, the whole-pixel boxes ``(x0, y0, x1, y1)`` (clipped to the frame) that the painting of its circles may touch."""
    boxes = []
    for added, _ in plan_circles(values, float(values.max()), notes, unit, None, WIDTH, HEIGHT):
        frame_boxes = []
        for x, y, color in added:
            r = radius * SCALE * resize_factor(color, resize)
            frame_boxes.append(
                (max(math.floor(x - r) - 1, 0), max(math.floor(y - r) - 1, 0), min(math.ceil(x + r) + 1, WIDTH), min(math.ceil(y + r) + 1, HEIGHT))
            )
        boxes.append(frame_boxes)
    return boxes


def melody(frames=40, seed=31):
    """(frames, 84) values: a few strong notes at a time, so that circles wander, overlap and wrap around."""
    values = np.random.default_rng(seed).random((frames, 84)) ** 3
    values[:, 40:] *= 0.1
    return values


# --- the plan: the same circles as Circles, with no memory ---------------------------------------------------------------------------


@pytest.mark.parametrize("settings", [dict(notes=5, unit=1), dict(notes=8, unit=4), dict(notes=12, unit=10)])
def test_the_plan_with_no_memory_adds_exactly_the_circles_that_the_plan_with_a_memory_adds(settings):
    values = np.random.default_rng(7).random((60, 84)) ** 2
    peak = float(values.max())
    with_memory = list(plan_circles(values, peak, settings["notes"], settings["unit"], 100, WIDTH, HEIGHT))
    without = list(plan_circles(values, peak, settings["notes"], settings["unit"], None, WIDTH, HEIGHT))
    assert [a for a, _ in with_memory] == [a for a, _ in without]
    assert all(remembered == [] for _, remembered in without)  # nothing is kept


@pytest.mark.parametrize("bad", [99, 501, 0, 1.5, "300", True])
def test_a_memory_that_is_given_is_still_checked_and_only_none_means_no_memory(bad):
    with pytest.raises(ValueError):
        list(plan_circles(np.zeros((2, 84)), 1.0, 8, 4, bad))


# --- the canvas: what a frame is made of ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("colormap", COLORMAPS)
def test_the_first_frame_is_the_background_of_the_colormap_with_the_circle_painted_on_it(tmp_path, colormap):
    frames = paint(frames_of({F5: 1.0}), tmp_path, colormap=colormap)
    picture = frames[0]
    assert picture.shape == (HEIGHT, WIDTH, 3)
    assert tuple(picture[0, 0]) == background_of(colormap) == tuple(picture[-1, -1])  # far from the circle
    assert (picture != np.array(background_of(colormap))).any()  # and the circle is there


def test_every_pixel_outside_the_circles_of_a_frame_is_the_pixel_of_the_previous_frame(tmp_path):
    values = melody(40)
    frames = paint(values, tmp_path, notes=6)
    boxes = circle_boxes(values, notes=6)
    for t in range(1, len(frames)):
        outside = np.ones((HEIGHT, WIDTH), dtype=bool)
        for x0, y0, x1, y1 in boxes[t]:
            outside[y0:y1, x0:x1] = False
        assert outside.sum() > 0
        assert (frames[t][outside] == frames[t - 1][outside]).all(), t  # exactly


def test_a_frame_with_no_sound_is_an_exact_copy_of_the_frame_before(tmp_path):
    values = frames_of({F5: 1.0}, {C4: 0.6}, {}, {}, {}, {F3: 0.9})
    frames = paint(values, tmp_path)
    assert (frames[2] == frames[1]).all() and (frames[3] == frames[1]).all() and (frames[4] == frames[1]).all()
    assert (frames[5] != frames[4]).any()  # and the next sound paints again


def test_two_runs_give_byte_identical_files(tmp_path):
    values = melody(25)
    paint(values, tmp_path / "a")
    paint(values, tmp_path / "b")
    for i in range(25):
        name = f"frame_{i:06d}.png"
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()


def test_a_saved_frame_is_not_changed_by_what_is_painted_after_it(tmp_path):
    values = frames_of(*steady(F5, 12))
    frames = paint(values, tmp_path)
    assert len({frame.tobytes() for frame in frames}) == 12  # every frame is its own picture: each file holds its own copy


# --- the circles: solid inside, smooth on the edge ---------------------------------------------------------------------------------


@pytest.mark.parametrize("colormap", COLORMAPS)
def test_a_circle_is_solid_exactly_its_color_inside_whatever_was_painted_there_before(tmp_path, colormap):
    values = frames_of(*steady(F5, 14, 1.0, 0.5))  # the volume alternates, so the circle moves every frame and overlaps its trail
    frames = paint(values, tmp_path, colormap=colormap, radius=8)  # a radius of 19 pixels: each circle covers part of the one before
    r = 8 * SCALE
    for t, (added, _) in enumerate(plan_circles(values, 1.0, 8, 4, None, WIDTH, HEIGHT)):
        (x, y, color), = added
        want = tuple(int(v) for v in lookup_table(colormap)[color])
        for dx, dy in ((0, 0), (0.5 * r, 0), (-0.5 * r, 0), (0, 0.5 * r), (0, -0.5 * r)):
            px, py = int(x + dx) % WIDTH, int(y + dy) % HEIGHT
            if 0 <= x + dx < WIDTH and 0 <= y + dy < HEIGHT:
                assert tuple(frames[t][py, px]) == want, (t, dx, dy)


def test_the_edge_of_a_circle_is_a_mix_of_its_color_and_what_was_under_it(tmp_path):
    colormap = COLORMAPS[0]
    picture = paint(frames_of({A4: 1.0}), tmp_path, colormap=colormap, radius=8)[0].astype(int)
    background, color = np.array(background_of(colormap)), np.array(color_of(colormap, 1.0))
    pixels = picture.reshape(-1, 3)
    solid = (pixels == background).all(axis=1) | (pixels == color).all(axis=1)
    edge = pixels[~solid]
    assert len(edge) >= 20  # a hard-edged disc has no such pixels; a smooth one has a ring of them
    low, high = np.minimum(background, color), np.maximum(background, color)
    assert ((edge >= low - 1) & (edge <= high + 1)).all()  # every one is a mix of the two colors, nothing else


def test_the_same_circle_painted_again_changes_only_its_edge_and_only_toward_its_color(tmp_path):
    colormap = COLORMAPS[0]
    # the same note at the same volume stays in place, so frame 1 paints the very circle of frame 0 again
    values = frames_of({C4: 1.0}, {C4: 1.0})
    frames = paint(values, tmp_path, colormap=colormap, radius=8)
    color = np.array(color_of(colormap, 1.0))
    first, second = frames[0].astype(int), frames[1].astype(int)
    inside = (first == color).all(axis=2)
    assert (second[inside] == first[inside]).all()  # the solid inside does not change
    changed = (second != first).any(axis=2)
    assert changed.any() and not (changed & inside).any()  # only edge pixels change (a mix is mixed again)
    toward = np.abs(second - color).sum(axis=2) <= np.abs(first - color).sum(axis=2)
    assert toward.all()  # and every pixel is at least as near to the circle's color as before: the edge hardens, never softens


def test_where_circles_of_one_frame_overlap_the_strongest_note_is_on_top(tmp_path):
    colormap = COLORMAPS[0]
    values = frames_of({F5: 1.0, F3: 0.6})  # 8 reference pixels apart: with a radius of 8 they overlap deeply
    picture = paint(values, tmp_path, colormap=colormap, radius=8, notes=5)[0]
    (weak, strong) = plan_circles(values, 1.0, 5, 4, None, WIDTH, HEIGHT).__next__()[0]  # weakest first
    middle = ((weak[0] + strong[0]) / 2, (weak[1] + strong[1]) / 2)
    assert tuple(picture[int(middle[1]), int(middle[0])]) == color_of(colormap, 1.0)  # the loud note's color
    far_side = (weak[0] + (weak[0] - strong[0]) / 2, weak[1] + (weak[1] - strong[1]) / 2)
    assert tuple(picture[int(far_side[1]), int(far_side[0])]) == color_of(colormap, 0.6)  # the quieter circle where the loud one is not


def test_a_circle_past_an_edge_is_cut_off_and_nothing_is_painted_on_the_opposite_edge(tmp_path):
    # C4 moves to the right, one unit (4 x 600 / 252 = 9.5 pixels) a frame; with a radius of 8 (19 pixels) a circle reaches over the right edge
    values = frames_of(*steady(C4, 40))
    frames = paint(values, tmp_path, radius=8)
    r = 8 * SCALE
    for t, (added, _) in enumerate(plan_circles(values, 1.0, 8, 4, None, WIDTH, HEIGHT)):
        (x, y, _), = added
        if x + r > WIDTH:  # the first circle that sticks out over the right edge (before any circle has wrapped to the left)
            assert (frames[t][int(y), WIDTH - 1] != np.array(background_of(COLORMAPS[0]))).any()  # it is painted up to the edge
            assert tuple(frames[t][int(y), 0]) == background_of(COLORMAPS[0])  # and not again on the left
            return
    pytest.fail("no circle reached the right edge")


def test_the_circle_has_the_radius_and_the_place_of_the_settings_scaled_to_the_frame(tmp_path):
    colormap = COLORMAPS[0]
    for radius, unit in ((4, 7), (6, 3), (8, 10)):
        picture = paint(frames_of({F5: 1.0}), tmp_path / f"{radius}_{unit}", colormap=colormap, radius=radius, unit=unit)[0]
        weights = coverage(picture, colormap, color_of(colormap, 1.0))
        assert weights.sum() == pytest.approx(math.pi * (radius * SCALE) ** 2, rel=0.05)  # the area of a disc of that radius
        dx, dy = expected_step(F5, unit)
        x, y = centroid(weights)
        assert x == pytest.approx(WIDTH / 2 + dx * SCALE, abs=0.3) and y == pytest.approx(HEIGHT / 2 + dy * SCALE, abs=0.3)


def test_the_painted_area_is_not_biased_either_way_over_many_radii_and_places(tmp_path):
    # one circle's area is right only to a quarter of a pixel in its edge (a few percent), but the average over many must be exact:
    # a mask that is a quarter of a pixel too large (or too small) shows as a bias of about two percent
    colormap = COLORMAPS[0]
    color = color_of(colormap, 1.0)
    ratios = []
    for radius in (4, 5, 6, 7, 8):
        for unit in (1, 4, 7, 10):
            picture = paint(frames_of({41: 1.0}), tmp_path / f"{radius}_{unit}", colormap=colormap, notes=5, unit=unit, radius=radius)[0]
            ratios.append(coverage(picture, colormap, color).sum() / (math.pi * (radius * SCALE) ** 2))
    assert abs(float(np.mean(ratios)) - 1.0) < 0.006, np.mean(ratios)
    assert max(abs(r - 1.0) for r in ratios) < 0.03


def test_with_the_resize_a_loud_circle_is_up_to_three_times_the_radius(tmp_path):
    colormap = COLORMAPS[0]
    plain = coverage(paint(frames_of({A4: 1.0}), tmp_path / "a", colormap=colormap, radius=5)[0], colormap, color_of(colormap, 1.0)).sum()
    resized = coverage(paint(frames_of({A4: 1.0}), tmp_path / "b", colormap=colormap, radius=5, resize=True)[0], colormap, color_of(colormap, 1.0)).sum()
    assert resized == pytest.approx(9 * plain, rel=0.08)  # three times the radius, nine times the area


# --- no memory ------------------------------------------------------------------------------------------------------------------------


def test_nothing_is_dropped_however_many_circles_have_been_painted(tmp_path):
    colormap = COLORMAPS[0]
    # frame 0: a loud rank 0 and a quiet rank 1; then 600 frames of rank 0 alone moving along a lane that does not cross rank 1's circle
    quiet = {C4: 1.0, A4: 0.25}
    first = {F5: 1.0, A4: 0.25}
    values = frames_of(first, *[{C4: 1.0 if t % 2 == 0 else 0.5} for t in range(600)])
    frames = paint(values, tmp_path, colormap=colormap, notes=5, unit=4, radius=4)
    place = plan_circles(values, 1.0, 5, 4, None, WIDTH, HEIGHT).__next__()[0][0]  # the quiet circle of frame 0 (weakest first)
    x, y, color = place
    want = tuple(int(v) for v in lookup_table(colormap)[color])
    assert tuple(frames[0][int(y), int(x)]) == want
    assert tuple(frames[-1][int(y), int(x)]) == want  # 600 frames and 600 circles later it is still there (Circles would have dropped it)
    del quiet


# --- the circles are those of Circles -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("settings", [dict(notes=5, unit=1, radius=4), dict(notes=8, unit=4, radius=6), dict(notes=12, unit=10, radius=8)])
def test_the_paint_and_circles_put_down_the_same_circles_at_the_same_place_in_the_same_color_and_size(tmp_path, settings):
    colormap = COLORMAPS[0]
    values = frames_of({F5: 1.0})
    painted = paint(values, tmp_path / "paint", colormap=colormap, **settings)[0]
    circles.write_circle_frames(values, 1.0, colormap, tmp_path / "circles", settings["notes"], settings["unit"], 100, settings["radius"], WIDTH, HEIGHT)
    drawn = np.asarray(Image.open(tmp_path / "circles" / "frame_000000.png"))  # the newest circle is opaque
    color = color_of(colormap, 1.0)
    a, b = coverage(painted, colormap, color), coverage(drawn, colormap, color)
    assert centroid(a)[0] == pytest.approx(centroid(b)[0], abs=0.3) and centroid(a)[1] == pytest.approx(centroid(b)[1], abs=0.3)
    assert a.sum() == pytest.approx(b.sum(), rel=0.03)  # the same size


# --- the settings and the errors -------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"unit": 0}, UNIT_MESSAGE),
        ({"unit": 11}, UNIT_MESSAGE),
        ({"radius": 3}, RADIUS_MESSAGE),
        ({"radius": 9}, RADIUS_MESSAGE),
        ({"radius": 4.5}, RADIUS_MESSAGE),
        ({"notes": 4}, NOTES_MESSAGE),
        ({"notes": 13}, NOTES_MESSAGE),
        ({"resize": 1}, RESIZE_MESSAGE),
        ({"resize": "true"}, RESIZE_MESSAGE),
    ],
)
def test_a_setting_that_is_not_allowed_is_refused_before_anything_is_written(tmp_path, kwargs, message):
    with pytest.raises(ValueError) as error:
        paint(frames_of({F5: 1.0}), tmp_path / "out", **kwargs)
    assert str(error.value) == message
    assert not (tmp_path / "out").exists()


def test_a_colormap_that_is_not_offered_is_refused_before_anything_is_written(tmp_path):
    with pytest.raises(ValueError):
        paint(frames_of({F5: 1.0}), tmp_path / "out", colormap="no-such-colormap")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("shape", [(3, 83), (3, 88), (84,), (0, 84, 1)])
def test_values_of_the_wrong_shape_are_refused(tmp_path, shape):
    with pytest.raises(ValueError):
        circles_paint.write_paint_frames(np.zeros(shape), 1.0, COLORMAPS[0], tmp_path / "out", 8, 4, 4, WIDTH, HEIGHT, False)


def test_no_frames_write_nothing_and_a_silent_file_gives_the_plain_background(tmp_path):
    assert paint(np.zeros((0, 84)), tmp_path / "none", peak=1.0) == []
    for colormap in COLORMAPS:
        for picture in paint(np.zeros((4, 84)), tmp_path / colormap, colormap=colormap, peak=1.0):
            assert (picture == np.array(background_of(colormap))).all()


def test_an_error_while_saving_a_picture_is_raised_and_the_threads_are_shut_down(tmp_path, monkeypatch):
    def broken(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(Image.Image, "save", broken)
    before = threading.active_count()
    with pytest.raises(OSError, match="disk full"):
        paint(frames_of(*steady(F5, 6)), tmp_path)
    assert threading.active_count() == before


def test_the_supersampling_is_the_one_of_the_circles():
    assert SUPERSAMPLE == 4 and circles.REFERENCE_WIDTH == REFERENCE_WIDTH == 252


# --- through the API (feature 022, story 2) ----------------------------------------------------------------------------------------

import io  # noqa: E402

from .test_circles_api import TYPE_MESSAGE, post as post_circles, steady_note  # noqa: E402
from .test_jobs_api import chord_wav, client, leftovers  # noqa: E402,F401
from .test_resolution_api import frame_bytes, picture, tiny  # noqa: E402


def post_paint(client, data=None, **fields):
    return post_circles(client, data, **{"image_type": "circles_paint", **fields})


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_type_is_accepted_with_every_colormap_and_reports_the_circle_settings(client, name):
    r = post_paint(client, steady_note(), colormap=name)
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["image_type"] == "circles_paint"
    assert (job["circle_unit"], job["circle_radius"], job["circle_memory"], job["circle_notes"], job["circle_resize"]) == (4, 4, 300, 8, False)
    tiles = post_circles(client, steady_note(), image_type="tiles").json()
    assert job["frame_count"] == tiles["frame_count"]
    for i in range(job["frame_count"]):
        image = Image.open(io.BytesIO(frame_bytes(client, job, i)))
        assert image.format == "PNG" and image.size == (600, 400) and image.mode == "RGB", (name, i)


@pytest.mark.parametrize("text", ["", " ", "circle_paint", "Circles_paint", " circles_paint", "circles_paint ", "circles paint", "paint", "circles-paint"])
def test_any_other_image_type_is_refused_with_the_five_names(client, text):
    before = leftovers()
    r = post_paint(client, tiny(), image_type=text)
    assert r.status_code == 400
    assert r.json()["detail"] == TYPE_MESSAGE and "circles, circles_paint" in TYPE_MESSAGE
    assert leftovers() == before


@pytest.mark.parametrize(
    "field, text, message",
    [
        ("circle_unit", "0", UNIT_MESSAGE),
        ("circle_unit", "11", UNIT_MESSAGE),
        ("circle_radius", "3", RADIUS_MESSAGE),
        ("circle_radius", "9", RADIUS_MESSAGE),
        ("circle_radius", "5.5", RADIUS_MESSAGE),
        ("circle_notes", "4", NOTES_MESSAGE),
        ("circle_notes", "13", NOTES_MESSAGE),
        ("circle_resize", "maybe", RESIZE_MESSAGE),
        ("circle_memory", "99", MEMORY_MESSAGE),
        ("circle_memory", "501", MEMORY_MESSAGE),
        ("circle_memory", "abc", MEMORY_MESSAGE),
    ],
)
def test_a_circle_setting_that_is_not_allowed_is_refused_before_a_job_is_created_as_for_circles(client, field, text, message):
    before = leftovers()
    r = post_paint(client, tiny(), **{field: text})
    assert r.status_code == 400 and r.json()["detail"] == message
    assert leftovers() == before
    # and before the file is read
    r = client.post(
        "/api/jobs",
        files={"file": ("song.wav", b"this is not audio", "audio/wav")},
        data={"window_size": "4096", "frame_rate": "10", "image_type": "circles_paint", field: text},
    )
    assert r.status_code == 400 and r.json()["detail"] == message


def test_the_memory_is_accepted_and_has_no_effect(client):
    data = chord_wav(3)
    plain = post_paint(client, data).json()
    last = plain["frame_count"] - 1
    for memory in ("100", "500"):
        other = post_paint(client, data, circle_memory=memory).json()
        assert other["circle_memory"] == int(memory)
        assert all(frame_bytes(client, plain, i) == frame_bytes(client, other, i) for i in (0, last // 2, last))


def test_the_settings_that_do_not_apply_are_accepted_and_ignored(client):
    data = chord_wav(3)
    plain = post_paint(client, data).json()
    ignored = post_paint(client, data, interpolate="5", resolution="5", note_count="12", threshold="10", blend_width="10")
    assert ignored.status_code == 200, ignored.text
    ignored = ignored.json()
    assert ignored["frame_count"] == plain["frame_count"]
    assert all(frame_bytes(client, plain, i) == frame_bytes(client, ignored, i) for i in range(plain["frame_count"]))


@pytest.mark.parametrize("field, low, high", [("circle_unit", "2", "10"), ("circle_radius", "4", "8"), ("circle_notes", "5", "12"), ("circle_resize", "false", "true")])
def test_each_circle_setting_that_is_sent_changes_the_frames(client, field, low, high):
    data = chord_wav(3)  # many notes sound, so every setting has something to change
    a = post_paint(client, data, **{field: low}).json()
    b = post_paint(client, data, **{field: high}).json()
    last = a["frame_count"] - 1
    assert frame_bytes(client, a, last) != frame_bytes(client, b, last), field


def test_smoothing_and_the_colormap_apply_and_the_colormap_changes_only_the_colors(client):
    data = steady_note()
    plain = post_paint(client, data).json()
    smooth = post_paint(client, data, smoothing="0.5", smoothing_window="3").json()
    assert plain["frame_count"] == smooth["frame_count"]
    if len(COLORMAPS) > 1:
        a = post_paint(client, data, colormap=COLORMAPS[0]).json()
        b = post_paint(client, data, colormap=COLORMAPS[1]).json()
        last = a["frame_count"] - 1
        background_a, background_b = background_of(COLORMAPS[0]), background_of(COLORMAPS[1])
        lit_a = (picture(client, a, last) != np.array(background_a)).any(axis=2)
        lit_b = (picture(client, b, last) != np.array(background_b)).any(axis=2)
        assert (lit_a == lit_b).mean() > 0.97  # the same places painted
        assert frame_bytes(client, a, last) != frame_bytes(client, b, last)


def test_the_canvas_only_grows_in_the_player_nothing_painted_goes_back_to_the_background(client):
    job = post_paint(client, steady_note(), colormap=COLORMAPS[0]).json()
    background = np.array(background_of(COLORMAPS[0]))
    counts = [int((picture(client, job, i) != background).any(axis=2).sum()) for i in range(job["frame_count"])]
    assert counts[0] > 0 and all(b >= a for a, b in zip(counts, counts[1:])) and counts[-1] > counts[0]


def test_the_same_request_twice_gives_identical_frames(client):
    data = chord_wav(2)
    a, b = post_paint(client, data, smoothing="0.4", smoothing_window="3").json(), post_paint(client, data, smoothing="0.4", smoothing_window="3").json()
    assert all(frame_bytes(client, a, i) == frame_bytes(client, b, i) for i in range(a["frame_count"]))


@pytest.mark.parametrize("image_type", ["tiles", "blended", "contour", "circles"])
def test_the_other_image_types_are_not_changed_by_the_new_one(client, image_type):
    data = chord_wav(2)
    a = post_circles(client, data, image_type=image_type).json()
    b = post_circles(client, data, image_type=image_type, circle_radius="8", circle_notes="12").json()
    if image_type != "circles":
        assert all(frame_bytes(client, a, i) == frame_bytes(client, b, i) for i in range(a["frame_count"]))
    assert Image.open(io.BytesIO(frame_bytes(client, a, 0))).size == (600, 400)


# --- through write_frames --------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("memory", [99, 501, 250.5, "300", True, None])
def test_write_frames_checks_the_memory_for_the_new_type_as_for_every_type_before_writing(tmp_path, memory):
    from app.services.frame_rendering import write_frames

    with pytest.raises(ValueError) as error:
        write_frames(np.random.default_rng(1).random((3, 88)), tmp_path / "out", image_type="circles_paint", circle_memory=memory)
    assert str(error.value) == MEMORY_MESSAGE
    assert not (tmp_path / "out").exists()


def test_write_frames_gives_the_same_frames_whatever_the_memory_and_the_ignored_settings(tmp_path):
    from app.services.frame_rendering import write_frames

    frames = np.random.default_rng(2).random((12, 88)) ** 2
    write_frames(frames, tmp_path / "plain", colormap=COLORMAPS[0], image_type="circles_paint")
    write_frames(
        frames, tmp_path / "other", colormap=COLORMAPS[0], image_type="circles_paint", circle_memory=500,
        interpolate=5, resolution=5, note_count=12, threshold=10, blend_width=10,
    )
    for i in range(12):
        name = f"frame_{i:06d}.png"
        assert (tmp_path / "plain" / name).read_bytes() == (tmp_path / "other" / name).read_bytes(), i


# --- the look of Circles, and the limits (story 3) ---------------------------------------------------------------------------------


@pytest.mark.parametrize("unit, notes, radius, resize", [(1, 5, 4, False), (10, 12, 8, True), (1, 12, 8, True), (10, 5, 4, False)])
def test_the_settings_at_their_extremes_all_work_and_the_picture_is_neither_blank_nor_one_color(tmp_path, unit, notes, radius, resize):
    values = np.random.default_rng(unit + notes + radius).random((30, 84)) ** 2
    frames = paint(values, tmp_path, notes=notes, unit=unit, radius=radius, resize=resize)
    assert len(frames) == 30 and all(f.shape == (HEIGHT, WIDTH, 3) for f in frames)
    assert len({tuple(p) for p in frames[-1].reshape(-1, 3)[::97]}) > 3  # many colors on the canvas


def test_a_very_quiet_file_paints_in_the_colors_of_its_own_peak(tmp_path):
    colormap = COLORMAPS[0]
    values = frames_of({F5: 1e-6, A4: 0.25e-6}, {F5: 1e-6})
    picture = paint(values, tmp_path, colormap=colormap, peak=1e-6)[0]
    (weak, strong) = plan_circles(values, 1e-6, 8, 4, None, WIDTH, HEIGHT).__next__()[0]
    assert tuple(picture[int(strong[1]), int(strong[0])]) == color_of(colormap, 1.0)  # the loudest note of the file: the last color
    assert tuple(picture[int(weak[1]), int(weak[0])]) == color_of(colormap, 0.25)


def test_smoothing_is_applied_before_the_strongest_notes_are_chosen_so_it_changes_what_is_painted(tmp_path):
    from app.services.frame_rendering import write_frames

    frames = np.zeros((3, 88))
    frames[:, 10:16] = 0.2
    frames[0, 60] = 1.0  # a click: raw it is gone in frame 1; smoothed it still has most of its value
    write_frames(frames, tmp_path / "raw", colormap=COLORMAPS[0], image_type="circles_paint")
    write_frames(frames, tmp_path / "smooth", colormap=COLORMAPS[0], image_type="circles_paint", smoothing=0.8, smoothing_window=1)
    raw, smooth = (np.asarray(Image.open(tmp_path / label / "frame_000001.png")) for label in ("raw", "smooth"))
    assert (raw != smooth).any()


def test_three_hundred_frames_at_the_largest_settings_finish_well_within_a_minute(tmp_path):
    import time

    values = np.random.default_rng(5).random((300, 84)) ** 2
    start = time.perf_counter()
    paint(values, tmp_path, notes=12, unit=10, radius=8, resize=True)
    assert time.perf_counter() - start < 60
