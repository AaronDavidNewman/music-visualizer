"""The image type and the blend width through the job endpoint: the optional ``image_type`` (``tiles`` or ``blended``) and
``blend_width`` (10 to 25) fields, their refusals, the response, and the frames that are served.
"""

import io

import numpy as np
import pytest
from PIL import Image

from .test_color_levels_api import chord_wav
from .test_jobs_api import client, frame_rgb, leftovers, wav_bytes  # noqa: F401

TYPE_MESSAGE = "The image type must be one of tiles, blended."
WIDTH_MESSAGE = "The blend width must be a number from 10 to 25."


def post_type(client, data=None, **fields):
    form = {"window_size": "4096", "frame_rate": "10", **fields}
    return client.post("/api/jobs", files={"file": ("song.wav", data or chord_wav(2), "audio/wav")}, data=form)


def frame_bytes(client, job, index):
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    assert r.status_code == 200
    return r.content


def tiny():
    return wav_bytes(np.zeros(22050))


@pytest.mark.parametrize("name", ["tiles", "blended"])
def test_the_offered_image_types_are_accepted_and_echoed(client, name):
    r = post_type(client, tiny(), image_type=name)
    assert r.status_code == 200, r.text
    assert r.json()["image_type"] == name


def test_without_the_field_the_image_type_is_tiles_and_the_frames_equal_those_sent_with_tiles(client):
    data = chord_wav(2)
    missing = post_type(client, data).json()
    tiles = post_type(client, data, image_type="tiles").json()
    assert missing["image_type"] == "tiles" and tiles["image_type"] == "tiles"
    for i in range(missing["frame_count"]):
        assert frame_bytes(client, missing, i) == frame_bytes(client, tiles, i)


@pytest.mark.parametrize("text", ["", " ", "Tiles", "BLENDED", "Blended", " tiles", "blended ", "gradient", "1", "tiles,blended"])
def test_any_other_image_type_is_refused_with_the_choices(client, text):
    before = leftovers()
    r = post_type(client, tiny(), image_type=text)
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == TYPE_MESSAGE
    assert leftovers() == before  # no job was created


@pytest.mark.parametrize(
    "text, echoed",
    [("10", 10), ("25", 25), ("15", 15), ("12.5", 12.5), ("15.0", 15), (" 20 ", 20)],
)
def test_accepted_blend_widths_are_echoed(client, text, echoed):
    r = post_type(client, tiny(), image_type="blended", blend_width=text)
    assert r.status_code == 200, r.text
    assert r.json()["blend_width"] == echoed
    assert type(r.json()["blend_width"]) is type(echoed)  # whole numbers come back as integers


def test_without_the_width_it_is_25_for_both_types(client):
    for fields in ({}, {"image_type": "blended"}):
        assert post_type(client, tiny(), **fields).json()["blend_width"] == 25


@pytest.mark.parametrize(
    "text", ["", " ", "9", "9.99", "25.01", "26", "0", "-10", "100", "abc", "nan", "inf", "-inf", "1e9", "15%"]
)
def test_any_other_blend_width_is_refused_with_the_range(client, text):
    before = leftovers()
    r = post_type(client, tiny(), image_type="blended", blend_width=text)
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == WIDTH_MESSAGE
    assert leftovers() == before


def test_both_fields_are_checked_before_the_file_is_read(client):
    for fields, message in (({"image_type": "x"}, TYPE_MESSAGE), ({"blend_width": "99"}, WIDTH_MESSAGE)):
        r = client.post(
            "/api/jobs",
            files={"file": ("song.wav", b"this is not audio", "audio/wav")},
            data={"window_size": "4096", "frame_rate": "10", **fields},
        )
        assert r.status_code == 400
        assert r.json()["detail"] == message


def test_a_blend_width_with_tiles_is_accepted_and_changes_nothing(client):
    data = chord_wav(2)
    narrow = post_type(client, data, image_type="tiles", blend_width="10").json()
    wide = post_type(client, data, image_type="tiles", blend_width="25").json()
    assert narrow["blend_width"] == 10 and wide["blend_width"] == 25
    for i in range(narrow["frame_count"]):
        assert frame_bytes(client, narrow, i) == frame_bytes(client, wide, i)


def test_blended_frames_have_the_size_and_count_of_tiles_frames_and_the_middles_agree(client):
    data = chord_wav(2)
    tiles = post_type(client, data, image_type="tiles").json()
    blended = post_type(client, data, image_type="blended", blend_width="25").json()
    assert blended["frame_count"] == tiles["frame_count"] > 10
    others = {k: v for k, v in blended.items() if k not in ("job_id", "frame_url_template", "image_type")}
    assert others == {k: v for k, v in tiles.items() if k not in ("job_id", "frame_url_template", "image_type")}
    for i in range(tiles["frame_count"]):
        flat = Image.open(io.BytesIO(frame_bytes(client, tiles, i)))
        soft = Image.open(io.BytesIO(frame_bytes(client, blended, i)))
        assert flat.size == soft.size == (252, 168)
        assert (frame_rgb(client, tiles, i) == frame_rgb(client, blended, i)).all()  # the middle of every tile


def test_the_same_blended_request_twice_gives_identical_frames(client):
    data = chord_wav(2)
    a = post_type(client, data, image_type="blended", blend_width="18").json()
    b = post_type(client, data, image_type="blended", blend_width="18").json()
    for i in range(0, a["frame_count"], 3):
        assert frame_bytes(client, a, i) == frame_bytes(client, b, i)


def test_served_pictures_have_the_right_format_size_and_headers(client):
    data = chord_wav(2)
    tiles = post_type(client, data, image_type="tiles").json()
    blended = post_type(client, data, image_type="blended").json()
    flat_response = client.get(tiles["frame_url_template"].replace("{index}", "5"))
    soft_response = client.get(blended["frame_url_template"].replace("{index}", "5"))
    assert flat_response.headers["content-type"] == soft_response.headers["content-type"] == "image/png"
    assert flat_response.headers["cache-control"] == soft_response.headers["cache-control"]
    flat, soft = Image.open(io.BytesIO(flat_response.content)), Image.open(io.BytesIO(soft_response.content))
    assert flat.mode == "P" and soft.mode == "RGB"
    assert flat.size == soft.size == (252, 168)
    assert len(soft_response.content) > len(flat_response.content)  # true-colour files are larger


def test_the_middles_agree_with_tiles_for_a_combination_of_other_settings(client):
    data = chord_wav(2)
    other = dict(
        smoothing="0.5",
        smoothing_window="3",
        saturation_step="20",
        brightness_step="50",
        hue_step="90",
        threshold="5",
        brightness="3",
        energy="2",
    )
    tiles = post_type(client, data, image_type="tiles", **other).json()
    blended = post_type(client, data, image_type="blended", blend_width="12", **other).json()
    assert tiles["frame_count"] == blended["frame_count"]
    for i in range(0, tiles["frame_count"], 2):
        assert (frame_rgb(client, tiles, i) == frame_rgb(client, blended, i)).all(), i
    # and the fades really are there: the pictures are not the same
    assert any(frame_bytes(client, tiles, i) != frame_bytes(client, blended, i) for i in range(tiles["frame_count"]))
