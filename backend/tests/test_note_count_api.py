"""The number of notes through the job endpoint: the optional ``note_count`` field (a whole number from 12 to 84), its
refusals, the response, and the frames that are served for every image type.

No colormap is named and no number of contour levels is assumed (see ``colormap_names.py``).
"""

import io
import time

import numpy as np
import pytest
from PIL import Image

from app.services.colormaps import COLORMAPS, lookup_table

from .frame_size import HEIGHT, WIDTH
from .test_jobs_api import (  # noqa: F401
    SR,
    chord_wav,
    client,
    frame_rgb,
    leftovers,
    note_tone,
    wav_bytes,
)
from .test_resolution_api import frame_bytes, picture, tiny

MESSAGE = "The number of notes must be a whole number from 12 to 84."
TYPES = ["tiles", "blended", "contour"]
REMOVED = ("energy", "brightness", "hue_step", "saturation_step", "brightness_step")


def post(client, data=None, **fields):
    form = {"window_size": "4096", "frame_rate": "10", **fields}
    return client.post("/api/jobs", files={"file": ("song.wav", data or chord_wav(2), "audio/wav")}, data=form)


def two_notes(seconds=2.0):
    """A sustained note 36 and a quieter sustained note 48: with 12 of 84 notes they are the strongest."""
    audio = note_tone(36, seconds) + 0.4 * note_tone(48, seconds)
    return wav_bytes(audio, audio)


# --- the field ----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("value", ["12", "13", "48", "83", "84"])
def test_every_number_of_notes_from_twelve_to_eighty_four_is_accepted_and_echoed_as_a_whole_number(client, image_type, value):
    r = post(client, tiny(), note_count=value, image_type=image_type)
    assert r.status_code == 200, r.text
    assert r.json()["note_count"] == int(value) and isinstance(r.json()["note_count"], int)


@pytest.mark.parametrize("text", ["36.0", " 36 ", "036", "3.6e1"])
def test_a_whole_number_written_another_way_is_accepted(client, text):
    r = post(client, tiny(), note_count=text)
    assert r.status_code == 200, r.text
    assert r.json()["note_count"] == 36


@pytest.mark.parametrize("image_type", TYPES)
def test_without_the_field_all_84_notes_are_used_and_the_frames_equal_those_sent_with_84(client, image_type):
    data = chord_wav(2)
    missing = post(client, data, image_type=image_type).json()
    full = post(client, data, image_type=image_type, note_count="84").json()
    assert missing["note_count"] == 84 and full["note_count"] == 84
    for i in range(0, missing["frame_count"], 2):
        assert frame_bytes(client, missing, i) == frame_bytes(client, full, i)


@pytest.mark.parametrize(
    "text", ["", " ", "0", "11", "85", "-1", "36.5", "abc", "nan", "inf", "-inf", "1e9", "36,", "36x", "1/2", "100"]
)
def test_any_other_number_of_notes_is_refused_with_the_message(client, text):
    before = leftovers()
    r = post(client, tiny(), note_count=text)
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == MESSAGE
    assert leftovers() == before  # no job was created


def test_the_number_of_notes_is_checked_before_the_file_is_read(client):
    r = client.post(
        "/api/jobs",
        files={"file": ("song.wav", b"this is not audio", "audio/wav")},
        data={"window_size": "4096", "frame_rate": "10", "note_count": "5"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == MESSAGE


def test_the_response_has_the_usual_keys_and_the_number_of_notes(client):
    job = post(client, tiny(), note_count="24").json()
    assert set(job) == {
        "job_id", "file_name", "sample_rate", "duration_seconds", "window_size", "frame_rate", "frame_count",
        "smoothing", "smoothing_window", "threshold", "image_type", "blend_width", "colormap", "resolution", "note_count",
        "interpolate", "circle_unit", "circle_memory", "circle_notes", "circle_radius", "circle_resize", "gaussian", "beat_coloring", "peak_distance", "peak_prominence", "note_layout", "decay_rate", "window_spacing", "step_samples", "window_count", "spacing_raised", "frame_url_template",
    }  # fmt: skip
    for key in REMOVED:
        assert key not in job


def test_the_removed_fields_are_still_ignored_with_a_number_of_notes(client):
    data = chord_wav(2)
    plain = post(client, data, note_count="24").json()
    old = post(client, data, note_count="24", energy="3", hue_step="90")
    assert old.status_code == 200
    for i in range(0, plain["frame_count"], 3):
        assert frame_bytes(client, plain, i) == frame_bytes(client, old.json(), i)


# --- the frames ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("n", [12, 48, 84])
def test_the_frames_have_the_same_size_and_count_whatever_the_number_of_notes(client, image_type, n):
    data = chord_wav(2)
    base = post(client, data, image_type=image_type).json()
    job = post(client, data, image_type=image_type, note_count=str(n)).json()
    assert job["frame_count"] == base["frame_count"] > 0
    for key in ("frame_rate", "window_size", "duration_seconds", "step_samples", "window_count"):
        assert job[key] == base[key]
    for i in (0, job["frame_count"] // 2, job["frame_count"] - 1):
        image = Image.open(io.BytesIO(frame_bytes(client, job, i)))
        assert image.format == "PNG" and image.size == (WIDTH, HEIGHT)


@pytest.mark.parametrize("image_type", TYPES)
def test_twelve_notes_make_a_different_picture_from_all_84(client, image_type):
    data = two_notes()
    full = post(client, data, image_type=image_type).json()
    few = post(client, data, image_type=image_type, note_count="12").json()
    middle = full["frame_count"] // 2
    assert frame_bytes(client, full, middle) != frame_bytes(client, few, middle)


def test_the_same_notes_are_used_in_every_frame_of_a_steady_file(client):
    data = two_notes(3.0)
    job = post(client, data, note_count="12").json()
    inside = [picture(client, job, i) for i in range(6, job["frame_count"] - 6)]
    assert len(inside) > 2
    assert all((p == inside[0]).all() for p in inside)  # steady notes, the same chosen notes: a steady picture


@pytest.mark.parametrize("image_type", TYPES)
def test_the_resolution_and_the_number_of_notes_work_together(client, image_type):
    r = post(client, two_notes(1.0), image_type=image_type, resolution="3", note_count="12")
    assert r.status_code == 200, r.text
    job = r.json()
    assert (job["resolution"], job["note_count"]) == (3, 12)
    assert Image.open(io.BytesIO(frame_bytes(client, job, 0))).size == (WIDTH, HEIGHT)


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("name", COLORMAPS)
def test_a_silent_file_is_flat_in_the_first_color_with_few_notes(client, image_type, name):
    data = wav_bytes(np.zeros(SR), np.zeros(SR))
    job = post(client, data, colormap=name, image_type=image_type, note_count="12", threshold="1").json()
    for i in (0, job["frame_count"] // 2, job["frame_count"] - 1):
        assert (picture(client, job, i) == lookup_table(name)[0]).all(), (image_type, name, i)


@pytest.mark.parametrize("image_type", TYPES)
def test_the_same_request_twice_gives_identical_frames(client, image_type):
    data = chord_wav(2)
    options = dict(note_count="30", image_type=image_type, smoothing="0.4", smoothing_window="3", threshold="3")
    a, b = post(client, data, **options).json(), post(client, data, **options).json()
    for i in range(0, a["frame_count"], 3):
        assert frame_bytes(client, a, i) == frame_bytes(client, b, i)


@pytest.mark.parametrize("image_type", TYPES)
def test_ten_seconds_at_thirty_frames_per_second_with_few_notes_and_the_highest_resolution_finish_within_a_minute(
    client, image_type
):
    tone = np.concatenate([note_tone(n, 1.0) for n in (24, 30, 36, 42, 48, 36, 30, 24, 40, 50)])
    data = wav_bytes(tone, tone)
    start = time.perf_counter()
    r = post(
        client, data, frame_rate="30", resolution="5", note_count="12", image_type=image_type,
        smoothing="0.5", smoothing_window="3", threshold="5",
    )  # fmt: skip
    elapsed = time.perf_counter() - start
    assert r.status_code == 200, r.text
    assert r.json()["frame_count"] >= 300
    assert elapsed < 60, f"{r.json()['frame_count']} frames of {image_type} with 12 notes at resolution 5 took {elapsed:.1f} s"
