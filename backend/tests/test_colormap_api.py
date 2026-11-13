"""The colormap through the job endpoint: the optional ``colormap`` field (any name in ``COLORMAPS``), its refusals, the
response, the removed fields that are now ignored, and the colors in the served frames.

No colormap is named here: the list can be changed by hand (see ``colormap_names.py``).
"""

import numpy as np
import pytest

from app.services.colormaps import COLORMAPS, DEFAULT_COLORMAP

from .frame_size import HEIGHT, WIDTH
from .colormap_names import FIRST, INVALID, MESSAGE, SECOND

from .test_jobs_api import (  # noqa: F401
    SR,
    burst_then_silence,
    chord_wav,
    client,
    expected_pixels,
    frame_rgb,
    frame_values,
    leftovers,
    note_tone,
    wav_bytes,
)

REMOVED = ("energy", "brightness", "hue_step", "saturation_step", "brightness_step")


def post_colormap(client, data=None, **fields):
    form = {"window_size": "4096", "frame_rate": "10", **fields}
    return client.post("/api/jobs", files={"file": ("song.wav", data or chord_wav(2), "audio/wav")}, data=form)


def frame_bytes(client, job, index):
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    assert r.status_code == 200
    return r.content


def tiny():
    return wav_bytes(np.zeros(22050))


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_offered_colormaps_are_accepted_and_echoed(client, name):
    r = post_colormap(client, tiny(), colormap=name)
    assert r.status_code == 200, r.text
    assert r.json()["colormap"] == name


def test_without_the_field_the_colormap_is_the_default_and_the_frames_equal_those_sent_with_it(client):
    data = chord_wav(2)
    missing = post_colormap(client, data).json()
    named = post_colormap(client, data, colormap=DEFAULT_COLORMAP).json()
    assert missing["colormap"] == DEFAULT_COLORMAP and named["colormap"] == DEFAULT_COLORMAP
    for i in range(missing["frame_count"]):
        assert frame_bytes(client, missing, i) == frame_bytes(client, named, i)


@pytest.mark.parametrize("text", INVALID)
def test_any_other_colormap_is_refused_with_the_choices(client, text):
    before = leftovers()
    r = post_colormap(client, tiny(), colormap=text)
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == MESSAGE
    assert leftovers() == before  # no job was created


def test_the_colormap_is_checked_before_the_file_is_read(client):
    r = client.post(
        "/api/jobs",
        files={"file": ("song.wav", b"this is not audio", "audio/wav")},
        data={"window_size": "4096", "frame_rate": "10", "colormap": "x"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == MESSAGE


def test_the_removed_fields_are_accepted_and_ignored(client):
    data = chord_wav(2)
    plain = post_colormap(client, data).json()
    old = post_colormap(
        client, data, energy="3", brightness="4", hue_step="90", saturation_step="20", brightness_step="50"
    )
    assert old.status_code == 200, old.text
    old = old.json()
    for i in range(plain["frame_count"]):
        assert frame_bytes(client, plain, i) == frame_bytes(client, old, i)


def test_even_invalid_values_of_the_removed_fields_are_ignored(client):
    r = post_colormap(client, tiny(), energy="99", brightness="abc", hue_step="7", saturation_step="", brightness_step="x")
    assert r.status_code == 200, r.text


def test_the_response_has_the_colormap_and_none_of_the_removed_settings(client):
    job = post_colormap(client, tiny(), energy="3", brightness="4", hue_step="90").json()
    assert "colormap" in job
    for key in REMOVED:
        assert key not in job
    assert set(job) == {
        "job_id", "file_name", "sample_rate", "duration_seconds", "window_size", "frame_rate", "frame_count",
        "smoothing", "smoothing_window", "threshold", "image_type", "colormap", "resolution", "note_count", "interpolate",
        "gaussian", "beat_coloring", "peak_distance", "peak_prominence", "note_layout", "decay_rate", "wave_count", "polar_notes", "decay_low", "decay_medium", "decay_high", "decay_saturated", "window_spacing",
        "step_samples", "window_count", "spacing_raised", "frame_url_template",
    }  # fmt: skip


def test_two_colormaps_give_different_pictures_of_the_same_sound(client):
    if FIRST == SECOND:
        pytest.skip("only one colormap is offered")
    data = chord_wav(2)
    a_job = post_colormap(client, data, colormap=FIRST).json()
    b_job = post_colormap(client, data, colormap=SECOND).json()
    assert any(frame_bytes(client, a_job, i) != frame_bytes(client, b_job, i) for i in range(a_job["frame_count"]))


def test_the_same_request_twice_gives_identical_frames(client):
    data = chord_wav(2)
    a = post_colormap(client, data, colormap=FIRST, smoothing="0.4").json()
    b = post_colormap(client, data, colormap=FIRST, smoothing="0.4").json()
    for i in range(0, a["frame_count"], 3):
        assert frame_bytes(client, a, i) == frame_bytes(client, b, i)


# --- with the other settings (User Story 3) -----------------------------------------------------------------------------


def test_the_pictures_have_the_same_size_count_and_format_for_all_the_colormaps(client):
    import io

    from PIL import Image

    data = chord_wav(2)
    jobs = {name: post_colormap(client, data, colormap=name).json() for name in COLORMAPS}
    counts = {job["frame_count"] for job in jobs.values()}
    assert len(counts) == 1
    for name, job in jobs.items():
        img = Image.open(io.BytesIO(frame_bytes(client, job, 3)))
        assert img.size == (WIDTH, HEIGHT) and img.mode in ("RGB", "RGBA"), name  # the contour is drawn by matplotlib
