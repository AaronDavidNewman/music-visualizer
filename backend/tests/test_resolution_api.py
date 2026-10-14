"""The resolution through the job endpoint: the optional ``resolution`` field (a whole number from 1 to 5), its refusals,
the response, and the frames that are served for every image type.

No colormap is named and no number of contour levels is assumed (see ``colormap_names.py``).
"""

import io
import time

import numpy as np
import pytest
from PIL import Image

from app.services.colormaps import COLORMAPS, lookup_table

from .colormap_names import WITHOUT_BLACK
from .test_jobs_api import (  # noqa: F401
    SR,
    chord_wav,
    client,
    frame_rgb,
    leftovers,
    note_tone,
    wav_bytes,
)

MESSAGE = "The oversampling must be a whole number from 1 to 5."
TYPES = ["tiles", "blended", "contour"]
REMOVED = ("energy", "brightness", "hue_step", "saturation_step", "brightness_step")


def post(client, data=None, **fields):
    form = {"window_size": "4096", "frame_rate": "10", **fields}
    return client.post("/api/jobs", files={"file": ("song.wav", data or chord_wav(2), "audio/wav")}, data=form)


def frame_bytes(client, job, index):
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    assert r.status_code == 200
    return r.content


def picture(client, job, index):
    return np.asarray(Image.open(io.BytesIO(frame_bytes(client, job, index))).convert("RGB"))


def tiny():
    return wav_bytes(np.zeros(22050))


def tile_grid(image, r):
    """The colors at the middle of every tile of a 12r x 7r picture (edges at the nearest whole pixel)."""
    xe = np.rint(np.linspace(0, 252, 12 * r + 1)).astype(int)
    ye = np.rint(np.linspace(0, 168, 7 * r + 1)).astype(int)
    return image[np.ix_((ye[:-1] + ye[1:] - 1) // 2, (xe[:-1] + xe[1:] - 1) // 2)]


# --- the field ----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("value", ["1", "2", "3", "4", "5"])
def test_every_resolution_from_one_to_five_is_accepted_and_echoed_as_a_whole_number(client, image_type, value):
    r = post(client, tiny(), resolution=value, image_type=image_type)
    assert r.status_code == 200, r.text
    assert r.json()["resolution"] == int(value) and isinstance(r.json()["resolution"], int)


@pytest.mark.parametrize("text", ["3.0", " 3 ", "03", "3e0"])
def test_a_whole_number_written_another_way_is_accepted(client, text):
    r = post(client, tiny(), resolution=text)
    assert r.status_code == 200, r.text
    assert r.json()["resolution"] == 3


@pytest.mark.parametrize("image_type", TYPES)
def test_without_the_field_the_resolution_is_one_and_the_frames_equal_those_sent_with_one(client, image_type):
    data = chord_wav(2)
    missing = post(client, data, image_type=image_type).json()
    one = post(client, data, image_type=image_type, resolution="1").json()
    assert missing["resolution"] == 1 and one["resolution"] == 1
    for i in range(0, missing["frame_count"], 2):
        assert frame_bytes(client, missing, i) == frame_bytes(client, one, i)


@pytest.mark.parametrize(
    "text", ["", " ", "0", "6", "-1", "2.5", "abc", "nan", "inf", "-inf", "1e9", "3,", "3x", "1/2"]
)
def test_any_other_resolution_is_refused_with_the_message(client, text):
    before = leftovers()
    r = post(client, tiny(), resolution=text)
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == MESSAGE
    assert leftovers() == before  # no job was created


def test_the_resolution_is_checked_before_the_file_is_read(client):
    r = client.post(
        "/api/jobs",
        files={"file": ("song.wav", b"this is not audio", "audio/wav")},
        data={"window_size": "4096", "frame_rate": "10", "resolution": "9"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == MESSAGE


def test_the_response_has_the_usual_keys_and_the_resolution(client):
    job = post(client, tiny(), resolution="2").json()
    assert set(job) == {
        "job_id", "file_name", "sample_rate", "duration_seconds", "window_size", "frame_rate", "frame_count",
        "smoothing", "smoothing_window", "threshold", "image_type", "blend_width", "colormap", "resolution", "note_count",
        "interpolate", "circle_unit", "circle_memory", "circle_notes", "circle_radius", "circle_resize", "window_spacing", "step_samples", "window_count", "spacing_raised", "frame_url_template",
    }  # fmt: skip
    for key in REMOVED:
        assert key not in job


def test_the_removed_fields_are_still_ignored_with_a_resolution(client):
    data = chord_wav(2)
    plain = post(client, data, resolution="3").json()
    old = post(client, data, resolution="3", energy="3", hue_step="90")
    assert old.status_code == 200
    for i in range(0, plain["frame_count"], 3):
        assert frame_bytes(client, plain, i) == frame_bytes(client, old.json(), i)


# --- the frames ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("r", [1, 2, 3, 5])
def test_the_frames_have_the_same_size_and_count_at_every_resolution(client, image_type, r):
    data = chord_wav(2)
    base = post(client, data, image_type=image_type).json()
    job = post(client, data, image_type=image_type, resolution=str(r)).json()
    assert job["frame_count"] == base["frame_count"] > 0
    for key in ("frame_rate", "window_size", "duration_seconds", "step_samples", "window_count"):
        assert job[key] == base[key]
    for i in (0, job["frame_count"] // 2, job["frame_count"] - 1):
        image = Image.open(io.BytesIO(frame_bytes(client, job, i)))
        assert image.format == "PNG" and image.size == (252, 168)


@pytest.mark.parametrize("r", [1, 2, 3, 5])
def test_a_tiles_frame_is_a_grid_of_12r_by_7r_flat_tiles(client, r):
    job = post(client, chord_wav(2), resolution=str(r)).json()
    image = picture(client, job, job["frame_count"] // 2)
    xe = np.rint(np.linspace(0, 252, 12 * r + 1)).astype(int)
    ye = np.rint(np.linspace(0, 168, 7 * r + 1)).astype(int)
    for ty in range(7 * r):
        for tx in range(12 * r):
            tile = image[ye[ty] : ye[ty + 1], xe[tx] : xe[tx + 1]]
            assert (tile == tile[0, 0]).all(), (r, ty, tx)  # one flat color per tile
    # and the tiles are really there: neighbouring tiles of a chord differ somewhere
    grid = tile_grid(image, r)
    assert (grid[:, 1:] != grid[:, :-1]).any()


def test_a_finer_picture_is_not_the_coarse_one_blown_up(client):
    data = chord_wav(2)
    one = post(client, data).json()
    three = post(client, data, resolution="3").json()
    i = one["frame_count"] // 2
    coarse = picture(client, one, i)
    fine = picture(client, three, i)
    blown_up = np.kron(tile_grid(coarse, 1), np.ones((3, 3, 1), dtype=np.uint8))  # (21, 36, 3)
    assert (tile_grid(fine, 3) != blown_up).any()


@pytest.mark.parametrize("image_type", TYPES)
def test_the_same_request_twice_gives_identical_frames(client, image_type):
    data = chord_wav(2)
    options = dict(resolution="4", image_type=image_type, smoothing="0.4", smoothing_window="3", threshold="3")
    a, b = post(client, data, **options).json(), post(client, data, **options).json()
    for i in range(0, a["frame_count"], 3):
        assert frame_bytes(client, a, i) == frame_bytes(client, b, i)


def test_a_note_hidden_by_the_threshold_leaves_black_tiles_with_a_finer_edge_at_a_higher_resolution(client):
    if not WITHOUT_BLACK:
        pytest.skip("every offered colormap has pure black")
    name = WITHOUT_BLACK[0]
    loud, faint = note_tone(36, 3.0), note_tone(37, 3.0) * 0.3
    data = wav_bytes(loud + faint, loud + faint)
    middle = None
    counts = {}
    for r in (1, 5):
        job = post(client, data, colormap=name, threshold="10", resolution=str(r)).json()
        middle = job["frame_count"] // 2
        black = ~tile_grid(picture(client, job, middle), r).reshape(-1, 3).any(axis=1)
        counts[r] = black.mean()
        assert black.any() and not black.all()
    assert counts[1] != counts[5]  # the hidden share of the picture differs: the edge of the hidden region has moved


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("name", COLORMAPS)
def test_a_silent_file_is_flat_in_the_first_color_at_a_high_resolution(client, image_type, name):
    data = wav_bytes(np.zeros(SR), np.zeros(SR))
    job = post(client, data, colormap=name, image_type=image_type, resolution="5", threshold="1").json()
    for i in (0, job["frame_count"] // 2, job["frame_count"] - 1):
        assert (picture(client, job, i) == lookup_table(name)[0]).all(), (image_type, name, i)


@pytest.mark.parametrize("image_type", TYPES)
def test_ten_seconds_at_thirty_frames_per_second_at_the_highest_resolution_finish_within_a_minute(client, image_type):
    tone = np.concatenate([note_tone(n, 1.0) for n in (24, 30, 36, 42, 48, 36, 30, 24, 40, 50)])
    data = wav_bytes(tone, tone)
    start = time.perf_counter()
    r = post(client, data, frame_rate="30", resolution="5", image_type=image_type, smoothing="0.5", smoothing_window="3", threshold="5")
    elapsed = time.perf_counter() - start
    assert r.status_code == 200, r.text
    assert r.json()["frame_count"] >= 300
    assert elapsed < 60, f"{r.json()['frame_count']} frames of {image_type} at resolution 5 took {elapsed:.1f} s"
