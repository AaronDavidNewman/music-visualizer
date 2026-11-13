"""The note layout through the job endpoint (feature 026): the field ``note_layout``, ``rows`` (the default) or ``spiral``."""

import numpy as np
import pytest

from app.services.note_layout import note_order

from .frame_size import HEIGHT, WIDTH
from .test_jobs_api import SR, client, leftovers, note_tone, wav_bytes  # noqa: F401
from .test_peak_tile_colors_api import TONE_NOTE, all_frames, post
from .test_resolution_api import picture, tiny

MESSAGE = "The note layout must be one of rows, spiral."
ALL_TYPES = ["contour", "decay", "decay-exp", "polar-chords"]
LAID_OUT = ["decay", "decay-exp", "polar-chords"]
ORDER = note_order("spiral")


def tone(seconds=2.0):
    return wav_bytes(0.5 * note_tone(TONE_NOTE, seconds))


# --- the field --------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", ALL_TYPES)
def test_the_default_is_rows_for_every_image_type(client, image_type):
    r = post(client, tiny(), image_type=image_type)
    assert r.status_code == 200, r.text
    assert r.json()["note_layout"] == "rows"


@pytest.mark.parametrize("image_type", ALL_TYPES)
@pytest.mark.parametrize("value", ["rows", "spiral"])
def test_both_layouts_are_accepted_and_echoed_for_every_image_type(client, image_type, value):
    r = post(client, tiny(), image_type=image_type, note_layout=value)
    assert r.status_code == 200, r.text
    assert r.json()["note_layout"] == value


@pytest.mark.parametrize("value", ["Rows", "SPIRAL", " spiral", "spiral ", "", "circle", "1", "row"])
def test_a_layout_that_is_not_exactly_offered_is_refused_with_nothing_created(client, value):
    r = post(client, tiny(), image_type="decay", note_layout=value)
    assert r.status_code == 400 and r.json()["detail"] == MESSAGE
    assert leftovers() == []


@pytest.mark.parametrize("image_type", ["contour", "decay", "polar-chords"])
def test_the_layout_is_checked_before_the_file_is_read(client, image_type):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": image_type, "note_layout": "Spiral"})  # no file at all
    assert r.status_code == 400 and r.json()["detail"] == MESSAGE
    assert leftovers() == []


def test_the_response_has_the_keys_of_the_other_jobs_and_the_layout(client):
    keys = set(post(client, tiny(), image_type="contour").json())
    assert "note_layout" in keys
    assert set(post(client, tiny(), image_type="decay", note_layout="spiral").json()) == keys


# --- the frames -------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", LAID_OUT)
def test_rows_gives_the_frames_of_a_job_that_sends_no_layout(client, image_type):
    audio = tone(2.0)
    plain = all_frames(client, post(client, audio, image_type=image_type).json())
    assert all_frames(client, post(client, audio, image_type=image_type, note_layout="rows").json()) == plain


@pytest.mark.parametrize("image_type", ["contour", "chromatic-decay", "chromatic-wireframe"])
def test_the_contour_and_the_chromatic_pictures_ignore_the_layout(client, image_type):
    audio = tone(2.0)
    rows = all_frames(client, post(client, audio, image_type=image_type).json())
    assert all_frames(client, post(client, audio, image_type=image_type, note_layout="spiral").json()) == rows


@pytest.mark.parametrize("image_type", LAID_OUT)
def test_the_frames_keep_their_size_count_and_two_runs_are_identical(client, image_type):
    audio = tone(2.0)
    one = post(client, audio, image_type=image_type, note_layout="spiral").json()
    two = post(client, audio, image_type=image_type, note_layout="spiral").json()
    assert all_frames(client, one) == all_frames(client, two)
    assert one["frame_count"] == post(client, audio, image_type=image_type).json()["frame_count"] > 0
    assert picture(client, one, 0).shape == (HEIGHT, WIDTH, 3)


# --- the other settings keep their meaning (Story 3) ---------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", LAID_OUT)
def test_a_silent_file_and_a_short_file_make_frames_in_the_spiral_layout(client, image_type):
    assert post(client, tiny(), image_type=image_type, note_layout="spiral").json()["frame_count"] > 0
    short = wav_bytes(np.clip(0.3 * note_tone(TONE_NOTE, 0.3), -0.9, 0.9))
    job = post(client, short, image_type=image_type, note_layout="spiral").json()
    assert job["frame_count"] >= 1 and picture(client, job, 0).shape == (HEIGHT, WIDTH, 3)


@pytest.mark.parametrize("image_type", LAID_OUT)
def test_mono_and_stereo_copies_make_the_same_frames_in_the_spiral_layout(client, image_type):
    audio = 0.4 * note_tone(20, 2.0) + 0.2 * note_tone(36, 2.0)
    mono = post(client, wav_bytes(audio), image_type=image_type, note_layout="spiral").json()
    stereo = post(client, wav_bytes(audio, audio), image_type=image_type, note_layout="spiral").json()
    assert all_frames(client, mono) == all_frames(client, stereo)
