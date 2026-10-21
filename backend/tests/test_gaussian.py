"""The Gaussian smoothing setting of the Image smoothing group: 0 to 5, Pillow's GaussianBlur, a radius of 3:2 like the frame."""

import io
import math

import numpy as np
import pytest
from PIL import Image, ImageFilter

import app.services.frame_rendering as rendering
from app.services.colormaps import COLORMAPS, lookup_table
from app.services.gaussian import ASPECT, blur_frames, blur_radius, check_gaussian

from .frame_size import COLUMN_EDGES, HEIGHT, ROW_EDGES, WIDTH
from .test_jobs_api import chord_wav, client, leftovers  # noqa: F401
from .test_resolution_api import frame_bytes, tiny

MESSAGE = "The gaussian smoothing must be a number from 0 to 5."
TYPES = ["tiles", "blended", "contour"]


def music(frames=4, seed=6):
    return np.random.default_rng(seed).random((frames, 88)) ** 2


def write(tmp_path, label, frames=None, **options):
    directory = tmp_path / label
    rendering.write_frames(music() if frames is None else frames, directory, colormap=COLORMAPS[0], **options)
    return sorted(directory.glob("frame_*.png"))


def pixels(file):
    return np.asarray(Image.open(file)).astype(int)


# --- the setting ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("good", [0, 0.0, 0.5, 1, 2.5, 4, 5, 5.0, np.float64(3.5), np.int64(2), -0.0])
def test_a_number_from_0_to_5_is_accepted_as_a_float(good):
    value = check_gaussian(good)
    assert isinstance(value, float) and value == float(good)
    assert str(value) != "-0.0"


@pytest.mark.parametrize("bad", [-0.1, -1, 5.0001, 6, 100, float("nan"), float("inf"), -float("inf"), True, False, "2", "", None, [1], b"1"])
def test_anything_else_is_refused_with_the_message(bad):
    with pytest.raises(ValueError) as error:
        check_gaussian(bad)
    assert str(error.value) == MESSAGE


def test_the_radius_is_three_to_two_like_the_frame_so_a_setting_of_4_is_6_across_and_4_down():
    assert ASPECT == 1.5
    assert blur_radius(4) == (6.0, 4.0)
    assert blur_radius(5) == (7.5, 5.0)
    assert blur_radius(1) == (1.5, 1.0)
    assert WIDTH * 2 == HEIGHT * 3  # the frame is 3:2


# --- the frames ----------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("resolution", [1, 5])
def test_at_zero_the_frames_are_exactly_what_they_were_without_the_setting(tmp_path, image_type, resolution):
    plain = write(tmp_path, "plain", image_type=image_type, resolution=resolution)
    zero = write(tmp_path, "zero", image_type=image_type, resolution=resolution, gaussian=0)
    assert [f.read_bytes() for f in plain] == [f.read_bytes() for f in zero]


def test_at_zero_the_flat_tiles_keep_their_palette():
    # nothing is read or written at zero: the indexed-colour PNG of the original grid stays one
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        files = write(Path(d), "a", image_type="tiles", gaussian=0)
        assert Image.open(files[0]).mode == "P"


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("value", [0.5, 2, 4, 5])
def test_a_frame_is_the_unblurred_frame_blurred_with_a_radius_of_1_5_value_across_and_value_down(tmp_path, image_type, value):
    plain = write(tmp_path, "plain", image_type=image_type)
    blurred = write(tmp_path, "blurred", image_type=image_type, gaussian=value)
    assert len(plain) == len(blurred) == 4
    for a, b in zip(plain, blurred):
        source = Image.open(a)
        source = source.convert("RGB") if source.mode == "P" else source
        want = np.asarray(source.filter(ImageFilter.GaussianBlur((1.5 * value, value)))).astype(int)
        got = pixels(b)
        assert got.shape == want.shape and (got == want).all(), (image_type, value, a.name)
        assert Image.open(b).size == (600, 400)


def test_the_picture_modes_after_blurring(tmp_path):
    modes = {}
    for image_type in TYPES:
        modes[image_type] = (Image.open(write(tmp_path, f"p_{image_type}", image_type=image_type)[0]).mode, Image.open(write(tmp_path, f"b_{image_type}", image_type=image_type, gaussian=2)[0]).mode)
    assert modes["tiles"] == ("P", "RGB")  # a blurred tile has more colors than a palette holds
    assert modes["blended"] == ("RGB", "RGB")
    assert modes["contour"][0] == modes["contour"][1]  # the picture keeps its kind (and its opaque alpha if it has one)
    if modes["contour"][1] == "RGBA":
        assert (pixels(write(tmp_path, "c", image_type="contour", gaussian=2)[0])[..., 3] == 255).all()


def test_the_blur_is_wider_across_than_down_in_the_ratio_of_the_frame(tmp_path):
    # one bright tile among tiles that the threshold hides: its edges, blurred, show the two radii
    frames = np.zeros((1, 88))
    frames[0, 26] = 1.0  # row 2, column 2 of the grid
    value = 4
    picture = pixels(write(tmp_path, "one", frames, image_type="tiles", threshold=5, gaussian=value)[0])
    channel = int(np.abs(np.array(lookup_table(COLORMAPS[0])[255], dtype=int)).argmax())
    plane = picture[..., channel].astype(float)
    top = plane.max()
    y_mid = int((ROW_EDGES[2] + ROW_EDGES[3]) // 2)
    x_mid = int((COLUMN_EDGES[2] + COLUMN_EDGES[3]) // 2)

    def edge_width(profile, edge, reach=35):
        # the number of pixels near an edge whose value is between 10% and 90% of the tile's own value
        part = profile[edge - reach : edge + reach]
        return int(((part > 0.1 * top) & (part < 0.9 * top)).sum())

    across = edge_width(plane[y_mid], int(COLUMN_EDGES[2]))  # a vertical edge: blurred by the x radius (6)
    down = edge_width(plane[:, x_mid], int(ROW_EDGES[2]))  # a horizontal edge: blurred by the y radius (4)
    # 10% to 90% of a Gaussian edge is 2.56 sigma: 15.4 pixels across and 10.2 down for a setting of 4
    assert across == pytest.approx(2.56 * 1.5 * value, abs=2.5) and down == pytest.approx(2.56 * value, abs=2.5)
    assert across / down == pytest.approx(1.5, abs=0.25)


def test_more_smoothing_means_a_smoother_picture_and_the_same_average_color(tmp_path):
    def roughness(picture):
        return np.abs(np.diff(picture, axis=0)).mean() + np.abs(np.diff(picture, axis=1)).mean()

    results = []
    for value in (0, 1, 3, 5):
        file = write(tmp_path, f"v{value}", image_type="blended", gaussian=value)[0]
        results.append(pixels(file))
    rough = [roughness(p) for p in results]
    assert rough[0] > rough[1] > rough[2] > rough[3]
    means = [p.reshape(-1, 3).mean(axis=0) for p in results]
    for m in means[1:]:
        assert np.abs(m - means[0]).max() < 2.0  # a blur moves color around; it does not change how much there is (borders aside)


def test_a_picture_of_one_flat_color_does_not_change(tmp_path):
    files = write(tmp_path, "silent", np.zeros((3, 88)), image_type="tiles", gaussian=5)
    first = lookup_table(COLORMAPS[0])[0]
    for f in files:
        assert (pixels(f)[..., :3] == np.array(first)).all()


def test_with_interpolate_only_the_drawn_frames_are_blurred_and_the_others_are_blends_of_them(tmp_path):
    drawn = write(tmp_path, "all", image_type="blended", gaussian=2)  # every frame drawn
    thinned = write(tmp_path, "thin", image_type="blended", gaussian=2, interpolate=3)  # frames 0 and 3 drawn, 1 and 2 blended
    assert (pixels(thinned[0]) == pixels(drawn[0])).all() and (pixels(thinned[3]) == pixels(drawn[3])).all()
    a, b = Image.open(thinned[0]).convert("RGB"), Image.open(thinned[3]).convert("RGB")
    for k in (1, 2):
        want = np.asarray(Image.blend(a, b, k / 3)).astype(int)
        assert (pixels(thinned[k]) == want).all(), k
        assert Image.open(thinned[k]).size == (600, 400)


def test_the_circle_types_do_not_use_it_and_ignore_it(tmp_path):
    for image_type in ("circles", "circles_paint"):
        plain = write(tmp_path, f"p_{image_type}", image_type=image_type)
        blurred = write(tmp_path, f"b_{image_type}", image_type=image_type, gaussian=5)
        assert [f.read_bytes() for f in plain] == [f.read_bytes() for f in blurred]


@pytest.mark.parametrize("image_type", ["tiles", "blended", "contour", "circles", "circles_paint"])
@pytest.mark.parametrize("bad", [-0.5, 5.5, float("nan"), float("inf"), True, "2", None])
def test_a_bad_value_is_refused_for_every_image_type_before_anything_is_written(tmp_path, image_type, bad):
    with pytest.raises(ValueError) as error:
        rendering.write_frames(music(), tmp_path / "out", image_type=image_type, gaussian=bad)
    assert str(error.value) == MESSAGE
    assert not (tmp_path / "out").exists()


def test_blur_frames_with_zero_touches_nothing_and_an_error_in_a_frame_is_raised(tmp_path):
    files = write(tmp_path, "a", image_type="tiles")
    before = [f.read_bytes() for f in files]
    blur_frames(tmp_path / "a", range(4), 0)
    assert [f.read_bytes() for f in files] == before
    with pytest.raises(OSError):
        blur_frames(tmp_path / "a", [0, 99], 2)  # frame 99 does not exist
    with pytest.raises(ValueError):
        blur_frames(tmp_path / "a", range(4), 6)


# --- through the API -------------------------------------------------------------------------------------------------------------------


def post(client, data=None, **fields):
    form = {"window_size": "4096", "frame_rate": "5", "colormap": COLORMAPS[0], **fields}
    return client.post("/api/jobs", files={"file": ("song.wav", data or chord_wav(2), "audio/wav")}, data=form)


def test_the_setting_is_off_by_default_and_reported_as_a_number(client):
    job = post(client, tiny()).json()
    assert job["gaussian"] == 0.0 and isinstance(job["gaussian"], float)


@pytest.mark.parametrize("text, expected", [("0", 0.0), ("2.5", 2.5), ("5", 5.0), (" 3 ", 3.0), ("4.0", 4.0), ("0.5", 0.5), ("1e0", 1.0), ("-0", 0.0)])
def test_the_setting_accepts_numbers_from_0_to_5(client, text, expected):
    job = post(client, tiny(), gaussian=text).json()
    assert job["gaussian"] == expected and isinstance(job["gaussian"], float)


@pytest.mark.parametrize("text", ["", " ", "-0.1", "5.1", "6", "abc", "nan", "inf", "-inf", "1e9", "2,5", "2x"])
@pytest.mark.parametrize("image_type", ["tiles", "circles"])
def test_anything_else_is_refused_before_a_job_is_created_for_every_image_type(client, image_type, text):
    before = leftovers()
    r = post(client, tiny(), image_type=image_type, gaussian=text)
    assert r.status_code == 400 and r.json()["detail"] == MESSAGE
    assert leftovers() == before


def test_it_is_checked_before_the_file_is_read(client):
    r = client.post(
        "/api/jobs",
        files={"file": ("song.wav", b"this is not audio", "audio/wav")},
        data={"window_size": "4096", "frame_rate": "10", "gaussian": "9"},
    )
    assert r.status_code == 400 and r.json()["detail"] == MESSAGE


@pytest.mark.parametrize("image_type", TYPES)
def test_the_frames_the_server_gives_are_blurred_and_still_600_by_400(client, image_type):
    data = chord_wav(2)
    plain = post(client, data, image_type=image_type).json()
    blurred = post(client, data, image_type=image_type, gaussian="3").json()
    assert plain["frame_count"] == blurred["frame_count"]
    for i in range(blurred["frame_count"]):
        image = Image.open(io.BytesIO(frame_bytes(client, blurred, i)))
        assert image.format == "PNG" and image.size == (600, 400)
        assert frame_bytes(client, plain, i) != frame_bytes(client, blurred, i)


@pytest.mark.parametrize("image_type", ["circles", "circles_paint"])
def test_the_circle_types_give_the_same_frames_with_or_without_it(client, image_type):
    data = chord_wav(2)
    plain = post(client, data, image_type=image_type).json()
    blurred = post(client, data, image_type=image_type, gaussian="5").json()
    assert blurred["gaussian"] == 5.0
    assert all(frame_bytes(client, plain, i) == frame_bytes(client, blurred, i) for i in range(plain["frame_count"]))


def test_the_same_request_twice_gives_identical_frames(client):
    data = chord_wav(2)
    a, b = post(client, data, gaussian="2.5").json(), post(client, data, gaussian="2.5").json()
    assert all(frame_bytes(client, a, i) == frame_bytes(client, b, i) for i in range(a["frame_count"]))


def test_with_interpolation_the_served_in_between_frames_are_600_by_400(client):
    job = post(client, chord_wav(2), image_type="blended", gaussian="2", interpolate="3").json()
    for i in range(job["frame_count"]):
        assert Image.open(io.BytesIO(frame_bytes(client, job, i))).size == (600, 400)
