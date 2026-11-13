"""The image type through the job endpoint: the optional ``image_type`` field (any name in ``IMAGE_TYPES``), its refusals, the response, and the frames that are served."""

import io

import numpy as np
import pytest
from PIL import Image

from app.services.image_types import DEFAULT_IMAGE_TYPE, IMAGE_TYPES

from .frame_size import HEIGHT, WIDTH
from .test_jobs_api import chord_wav, client, leftovers, wav_bytes  # noqa: F401

TYPE_MESSAGE = f"The image type must be one of {', '.join(IMAGE_TYPES)}."
REMOVED = ["tiles", "blended", "circles", "circles_paint", "concentric"]


def post_type(client, data=None, **fields):
    form = {"window_size": "4096", "frame_rate": "10", **fields}
    return client.post("/api/jobs", files={"file": ("song.wav", data or chord_wav(2), "audio/wav")}, data=form)


def frame_bytes(client, job, index):
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    assert r.status_code == 200
    return r.content


def tiny():
    return wav_bytes(np.zeros(22050))


@pytest.mark.parametrize("name", IMAGE_TYPES)
def test_the_offered_image_types_are_accepted_and_echoed(client, name):
    r = post_type(client, tiny(), image_type=name)
    assert r.status_code == 200, r.text
    assert r.json()["image_type"] == name


def test_without_the_field_the_image_type_is_the_contour_and_the_frames_equal_those_sent_with_it(client):
    data = chord_wav(2)
    missing = post_type(client, data).json()
    named = post_type(client, data, image_type="contour").json()
    assert DEFAULT_IMAGE_TYPE == "contour"
    assert missing["image_type"] == "contour" and named["image_type"] == "contour"
    for i in range(missing["frame_count"]):
        assert frame_bytes(client, missing, i) == frame_bytes(client, named, i)


@pytest.mark.parametrize("text", REMOVED + ["", " ", "Contour", "CONTOUR", " contour", "contour ", "contours", "gradient", "1", "contour,decay"])
def test_any_other_image_type_is_refused_with_the_choices_and_so_are_the_five_that_were_removed(client, text):
    before = leftovers()
    r = post_type(client, tiny(), image_type=text)
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == TYPE_MESSAGE
    assert leftovers() == before


def test_the_image_type_is_checked_before_the_file_is_read(client):
    r = client.post(
        "/api/jobs",
        files={"file": ("song.wav", b"this is not audio", "audio/wav")},
        data={"window_size": "4096", "frame_rate": "10", "image_type": "x"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == TYPE_MESSAGE


def test_the_removed_fields_of_the_removed_types_are_accepted_and_ignored(client):
    data = chord_wav(2)
    plain = post_type(client, data).json()
    old = post_type(client, data, blend_width="12", circle_unit="3", circle_memory="200", circle_notes="6", circle_radius="5", circle_resize="true")
    assert old.status_code == 200, old.text
    old = old.json()
    for key in ("blend_width", "circle_unit", "circle_memory", "circle_notes", "circle_radius", "circle_resize"):
        assert key not in old
    for i in range(plain["frame_count"]):
        assert frame_bytes(client, plain, i) == frame_bytes(client, old, i)


def test_the_same_request_twice_gives_identical_frames(client):
    data = chord_wav(2)
    a = post_type(client, data, image_type="decay").json()
    b = post_type(client, data, image_type="decay").json()
    for i in range(0, a["frame_count"], 3):
        assert frame_bytes(client, a, i) == frame_bytes(client, b, i)


@pytest.mark.parametrize("name", ["contour", "decay", "decay-exp", "polar-chords", "chromatic-decay", "chromatic-wireframe"])
def test_served_pictures_have_the_right_format_size_and_headers(client, name):
    job = post_type(client, chord_wav(2), image_type=name).json()
    response = client.get(job["frame_url_template"].replace("{index}", "5"))
    assert response.headers["content-type"] == "image/png"
    assert "immutable" in response.headers["cache-control"]
    image = Image.open(io.BytesIO(response.content))
    assert image.format == "PNG" and image.size == (WIDTH, HEIGHT)
