"""Interpolated frames through the job endpoint: the optional ``interpolate`` field (1 to 5), its refusals, the response, and
the frames that are served for every image type. The frames in between are always blends (the interpolation function that
feature 018 offered was removed: a request that still sends ``interpolate_function`` is accepted and the field is ignored).

No colormap is named and no number of contour levels is assumed (see ``colormap_names.py``).
"""

import io
import time

import numpy as np
import pytest
from PIL import Image

from app.services.colormaps import COLORMAPS, lookup_table
from app.services.frame_interpolation import key_frames

from .frame_size import HEIGHT, WIDTH
from .test_frame_interpolation import INTERPOLATE_MESSAGE
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

TYPES = ["tiles", "blended", "contour"]
REMOVED = ("energy", "brightness", "hue_step", "saturation_step", "brightness_step", "interpolate_function")


def post(client, data=None, **fields):
    form = {"window_size": "4096", "frame_rate": "10", **fields}
    return client.post("/api/jobs", files={"file": ("song.wav", data or chord_wav(2), "audio/wav")}, data=form)


def changing_file(seconds=2.0):
    """Notes that start and stop, so that neighboring drawn frames differ."""
    tone = np.concatenate([note_tone(n, seconds / 4) for n in (30, 42, 36, 48)])
    return wav_bytes(tone, tone)


# --- the field ----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("value", ["1", "2", "3", "4", "5"])
def test_every_interpolate_value_is_accepted_and_echoed_as_a_whole_number(client, image_type, value):
    r = post(client, tiny(), interpolate=value, image_type=image_type)
    assert r.status_code == 200, r.text
    assert r.json()["interpolate"] == int(value) and isinstance(r.json()["interpolate"], int)


@pytest.mark.parametrize("text", ["3.0", " 3 ", "03", "3e0"])
def test_a_whole_number_written_another_way_is_accepted(client, text):
    r = post(client, tiny(), interpolate=text)
    assert r.status_code == 200, r.text
    assert r.json()["interpolate"] == 3


@pytest.mark.parametrize("image_type", TYPES)
def test_without_the_field_every_frame_is_drawn_and_the_frames_equal_those_sent_with_one(client, image_type):
    data = chord_wav(2)
    missing = post(client, data, image_type=image_type).json()
    explicit = post(client, data, image_type=image_type, interpolate="1").json()
    assert missing["interpolate"] == 1
    for i in range(0, missing["frame_count"], 2):
        assert frame_bytes(client, missing, i) == frame_bytes(client, explicit, i)


@pytest.mark.parametrize("text", ["", " ", "0", "6", "-1", "2.5", "abc", "nan", "inf", "-inf", "1e9", "3,", "3x", "1/2"])
def test_any_other_interpolate_value_is_refused_with_the_message(client, text):
    before = leftovers()
    r = post(client, tiny(), interpolate=text)
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == INTERPOLATE_MESSAGE
    assert leftovers() == before  # no job was created


def test_the_value_is_checked_before_the_file_is_read(client):
    r = client.post(
        "/api/jobs",
        files={"file": ("song.wav", b"this is not audio", "audio/wav")},
        data={"window_size": "4096", "frame_rate": "10", "interpolate": "9"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == INTERPOLATE_MESSAGE


def test_the_response_has_the_usual_keys_and_the_interpolate_value(client):
    job = post(client, tiny(), interpolate="2").json()
    assert set(job) == {
        "job_id", "file_name", "sample_rate", "duration_seconds", "window_size", "frame_rate", "frame_count",
        "smoothing", "smoothing_window", "threshold", "image_type", "blend_width", "colormap", "resolution", "note_count",
        "interpolate", "circle_unit", "circle_memory", "circle_notes", "circle_radius", "circle_resize", "gaussian", "beat_coloring", "peak_distance", "peak_prominence", "window_spacing", "step_samples", "window_count", "spacing_raised", "frame_url_template",
    }  # fmt: skip
    for key in REMOVED:
        assert key not in job


@pytest.mark.parametrize("function", ["blend", "screen", "subtract", "Blend", "multiply", ""])
def test_the_removed_interpolation_function_field_is_accepted_and_ignored(client, function):
    data = changing_file()
    plain = post(client, data, interpolate="5").json()
    old = post(client, data, interpolate="5", interpolate_function=function)
    assert old.status_code == 200, old.text  # even an invalid value is not refused any more
    assert "interpolate_function" not in old.json()
    for i in range(plain["frame_count"]):
        assert frame_bytes(client, plain, i) == frame_bytes(client, old.json(), i)


def test_the_other_removed_fields_are_still_ignored_with_interpolation(client):
    data = chord_wav(2)
    plain = post(client, data, interpolate="3").json()
    old = post(client, data, interpolate="3", energy="3", hue_step="90")
    assert old.status_code == 200
    for i in range(0, plain["frame_count"], 3):
        assert frame_bytes(client, plain, i) == frame_bytes(client, old.json(), i)


# --- the frames ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("n", [2, 3, 5])
def test_the_frames_have_the_same_size_and_count_at_every_interpolate_value(client, image_type, n):
    data = chord_wav(2)
    base = post(client, data, image_type=image_type).json()
    job = post(client, data, image_type=image_type, interpolate=str(n)).json()
    assert job["frame_count"] == base["frame_count"] > 0
    for key in ("frame_rate", "window_size", "duration_seconds", "step_samples", "window_count"):
        assert job[key] == base[key]
    for i in range(job["frame_count"]):
        image = Image.open(io.BytesIO(frame_bytes(client, job, i)))
        assert image.format == "PNG" and image.size == (WIDTH, HEIGHT), i


@pytest.mark.parametrize("image_type", TYPES)
def test_the_drawn_frames_are_the_frames_of_interpolate_one_and_the_others_are_not(client, image_type):
    data = changing_file()
    full = post(client, data, image_type=image_type).json()
    part = post(client, data, image_type=image_type, interpolate="5").json()
    count = full["frame_count"]
    drawn = key_frames(count, 5)
    for i in drawn:
        assert frame_bytes(client, part, i) == frame_bytes(client, full, i), (image_type, i)
    others = [i for i in range(count) if i not in drawn]
    assert others and any(frame_bytes(client, part, i) != frame_bytes(client, full, i) for i in others)


@pytest.mark.parametrize("image_type", TYPES)
def test_the_frames_in_between_are_the_weighted_blends_of_their_served_neighbours(client, image_type):
    data = changing_file()
    job = post(client, data, image_type=image_type, interpolate="4").json()
    count = job["frame_count"]
    drawn = key_frames(count, 4)
    served = lambda i: np.asarray(Image.open(io.BytesIO(frame_bytes(client, job, i))).convert("RGB"), dtype=float)  # noqa: E731
    for a, b in zip(drawn[:-1], drawn[1:]):
        for i in range(a + 1, b):
            w = (i - a) / (b - a)
            assert np.abs(served(i) - ((1 - w) * served(a) + w * served(b))).max() <= 1.0 + 1e-9, (image_type, i)


@pytest.mark.parametrize("image_type", TYPES)
def test_with_the_other_settings_the_drawn_frames_are_unchanged_and_the_job_works(client, image_type):
    data = changing_file()
    options = dict(image_type=image_type, resolution="3", note_count="24", threshold="5", smoothing="0.4", smoothing_window="3")
    full = post(client, data, **options).json()
    part = post(client, data, interpolate="4", **options)
    assert part.status_code == 200, part.text
    part = part.json()
    for i in key_frames(full["frame_count"], 4):
        assert frame_bytes(client, part, i) == frame_bytes(client, full, i)


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("name", COLORMAPS)
def test_a_silent_file_gives_flat_frames(client, image_type, name):
    data = wav_bytes(np.zeros(SR), np.zeros(SR))
    job = post(client, data, colormap=name, image_type=image_type, interpolate="3").json()
    for i in range(job["frame_count"]):
        assert (picture(client, job, i) == lookup_table(name)[0]).all(), (image_type, name, i)


@pytest.mark.parametrize("image_type", TYPES)
def test_the_same_request_twice_gives_identical_frames(client, image_type):
    data = changing_file()
    options = dict(interpolate="4", image_type=image_type, smoothing="0.4", smoothing_window="3")
    a, b = post(client, data, **options).json(), post(client, data, **options).json()
    for i in range(0, a["frame_count"], 3):
        assert frame_bytes(client, a, i) == frame_bytes(client, b, i)


@pytest.mark.parametrize("image_type", TYPES)
def test_ten_seconds_at_thirty_frames_per_second_with_interpolation_and_the_highest_resolution_finish_within_a_minute(
    client, image_type
):
    tone = np.concatenate([note_tone(n, 1.0) for n in (24, 30, 36, 42, 48, 36, 30, 24, 40, 50)])
    data = wav_bytes(tone, tone)
    start = time.perf_counter()
    r = post(
        client, data, frame_rate="30", resolution="5", interpolate="5", image_type=image_type,
        smoothing="0.5", smoothing_window="3", threshold="5",
    )  # fmt: skip
    elapsed = time.perf_counter() - start
    assert r.status_code == 200, r.text
    assert r.json()["frame_count"] >= 300
    assert elapsed < 60, f"{r.json()['frame_count']} frames of {image_type} at interpolate 5 took {elapsed:.1f} s"
