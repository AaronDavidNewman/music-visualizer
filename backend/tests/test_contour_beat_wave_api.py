"""The contour beat wave through ``POST /api/jobs``: the wave count, the beat measured with the box on, the ignored cases, the corners (feature 028)."""

import time

import numpy as np
import pytest

import app.routers.jobs as jobs

from .frame_size import HEIGHT, WIDTH
from .test_jobs_api import SR, client, leftovers, note_tone, wav_bytes  # noqa: F401
from .test_peak_tile_colors_api import COLORMAP, TONE_NOTE, all_frames, post, pulse_wav
from .test_resolution_api import picture, tiny

MESSAGE = "The wave count must be a whole number from 2 to 10."
DISTANCE_MESSAGE = "The minimum distance must be a number from 100 to 2000 milliseconds."
PROMINENCE_MESSAGE = "The prominence must be a number from 0 to 100 percent."
OTHER_TYPES = ["tiles", "blended", "circles", "circles_paint", "concentric", "decay", "decay-exp", "polar-chords"]


def contour(client, data=None, **fields):
    return post(client, data, image_type="contour", **fields)


# --- the field -----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", ["tiles", "blended", "contour", "circles", "circles_paint", "concentric", "decay", "decay-exp", "polar-chords"])
def test_the_default_is_4_and_is_reported_for_every_image_type(client, image_type):
    r = post(client, tiny(), image_type=image_type)
    assert r.status_code == 200, r.text
    assert r.json()["wave_count"] == 4 and r.json()["beat_coloring"] is False


@pytest.mark.parametrize("count", ["2", "6", "10", "5.0", " 4 "])
def test_a_whole_number_from_2_to_10_is_accepted_and_echoed(client, count):
    r = contour(client, tiny(), wave_count=count)
    assert r.status_code == 200, r.text
    assert r.json()["wave_count"] == int(float(count))


@pytest.mark.parametrize("count", ["0", "1", "11", "2.5", "-1", "abc", "", "nan", "inf", "1e3"])
def test_anything_else_is_refused_with_the_message_and_nothing_is_created(client, count):
    r = contour(client, tiny(), wave_count=count)
    assert r.status_code == 400 and r.json()["detail"] == MESSAGE
    assert leftovers() == []


def test_the_count_is_checked_before_the_file_is_read(client):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": "contour", "wave_count": "11"})  # no file at all
    assert r.status_code == 400 and r.json()["detail"] == MESSAGE
    assert leftovers() == []


@pytest.mark.parametrize("image_type", OTHER_TYPES)
def test_a_count_sent_with_another_type_is_checked_echoed_and_has_no_effect(client, image_type):
    audio = tiny()
    plain = post(client, audio, image_type=image_type).json()
    sent = post(client, audio, image_type=image_type, wave_count="7")
    assert sent.status_code == 200 and sent.json()["wave_count"] == 7
    assert all_frames(client, sent.json()) == all_frames(client, plain)
    assert post(client, audio, image_type=image_type, wave_count="11").status_code == 400


def test_the_response_has_the_same_keys_for_contour_as_for_the_other_types(client):
    keys = set(post(client, tiny(), image_type="tiles").json())
    assert "wave_count" in keys
    assert set(contour(client, tiny()).json()) == keys


# --- the beat is measured exactly when the box is on ---------------------------------------------------------------------------


@pytest.fixture
def measured(monkeypatch):
    calls = []
    real = jobs.measure_local_peaks

    def spy(left, right, file_rate, min_distance, prominence, *args, **kwargs):
        calls.append((len(left), file_rate, min_distance, prominence))
        return real(left, right, file_rate, min_distance, prominence, *args, **kwargs)

    monkeypatch.setattr(jobs, "measure_local_peaks", spy)
    return calls


@pytest.mark.parametrize("box", ["true", "True", "1"])
def test_the_beat_is_measured_once_with_the_two_settings_when_the_box_is_on(client, measured, box):
    r = contour(client, tiny(), beat_coloring=box, peak_distance="300", peak_prominence="20")
    assert r.status_code == 200 and r.json()["beat_coloring"] is True
    assert measured == [(22050, SR, 300.0, 20.0)]


@pytest.mark.parametrize("box", [None, "false", "0"])
def test_the_beat_is_not_measured_when_the_box_is_off_or_not_sent(client, measured, box):
    fields = {} if box is None else {"beat_coloring": box}
    assert contour(client, tiny(), **fields).status_code == 200
    assert measured == []


@pytest.mark.parametrize(
    "fields, message",
    [({"peak_distance": "50"}, DISTANCE_MESSAGE), ({"peak_distance": "abc"}, DISTANCE_MESSAGE), ({"peak_prominence": "101"}, PROMINENCE_MESSAGE), ({"peak_prominence": ""}, PROMINENCE_MESSAGE)],
)
def test_the_peak_settings_are_checked_before_the_file_is_read_with_nothing_created(client, measured, fields, message):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": "contour", "beat_coloring": "true", **fields})
    assert r.status_code == 400 and r.json()["detail"] == message
    assert contour(client, tiny(), beat_coloring="true", **fields).status_code == 400
    assert leftovers() == [] and measured == []


# --- the pictures --------------------------------------------------------------------------------------------------------------


def test_with_the_box_off_the_wave_count_makes_no_difference(client):
    audio = pulse_wav(seconds=3.0)
    plain = all_frames(client, contour(client, audio).json())
    for count in ("2", "10"):
        assert all_frames(client, contour(client, audio, wave_count=count).json()) == plain


def test_with_the_box_on_the_frames_follow_the_beat_and_the_wave_count(client):
    audio = pulse_wav(seconds=4.0)
    off = all_frames(client, contour(client, audio).json())
    on = all_frames(client, contour(client, audio, beat_coloring="true").json())
    assert len(on) == len(off) and on != off
    assert any(a == b for a, b in zip(on, off))  # the frames at the minimum of the beat (or before the first beat) are the plain ones
    assert any(a != b for a, b in zip(on, off))
    two = all_frames(client, contour(client, audio, beat_coloring="true", wave_count="2").json())
    ten = all_frames(client, contour(client, audio, beat_coloring="true", wave_count="10").json())
    assert two != ten


def test_the_minimum_distance_and_the_prominence_change_the_frames_with_the_box_on(client):
    audio = pulse_wav()
    default = all_frames(client, contour(client, audio, beat_coloring="true").json())
    far = all_frames(client, contour(client, audio, beat_coloring="true", peak_distance="2000").json())
    high = all_frames(client, contour(client, audio, beat_coloring="true", peak_prominence="95").json())
    assert far != default and high != default


def test_the_frames_are_600_by_400_rgb_pictures_and_their_count_is_that_of_the_other_types(client):
    audio = pulse_wav(seconds=3.0)
    job = contour(client, audio, beat_coloring="true").json()
    tiles = post(client, audio, image_type="tiles").json()
    assert job["frame_count"] == tiles["frame_count"] > 0
    assert picture(client, job, 0).shape == (HEIGHT, WIDTH, 3)
    assert picture(client, job, job["frame_count"] - 1).shape == (HEIGHT, WIDTH, 3)


def test_two_runs_give_identical_frames(client):
    audio = pulse_wav(seconds=3.0)
    first = all_frames(client, contour(client, audio, beat_coloring="true", wave_count="5").json())
    assert first == all_frames(client, contour(client, audio, beat_coloring="true", wave_count="5").json())


def test_the_other_settings_still_apply_with_the_wave(client):
    audio = pulse_wav(seconds=3.0)
    base = all_frames(client, contour(client, audio, beat_coloring="true").json())
    for fields in ({"threshold": "8"}, {"note_count": "30"}, {"smoothing": "0.5", "smoothing_window": "4"}, {"resolution": "2"}):
        r = contour(client, audio, beat_coloring="true", **fields)
        assert r.status_code == 200, (fields, r.text)
        assert all_frames(client, r.json()) != base, fields


@pytest.mark.parametrize("fields", [{"note_layout": "spiral"}, {"decay_rate": "2"}, {"circle_unit": "9"}, {"circle_notes": "12"}])
def test_the_settings_of_the_other_pictures_are_accepted_and_ignored_by_contour(client, fields):
    audio = pulse_wav(seconds=3.0)
    plain = all_frames(client, contour(client, audio, beat_coloring="true").json())
    r = contour(client, audio, beat_coloring="true", **fields)
    assert r.status_code == 200 and all_frames(client, r.json()) == plain


# --- the corners (Story 3) -----------------------------------------------------------------------------------------------------


def test_a_silent_file_is_the_same_with_the_box_on_and_off(client):
    off = all_frames(client, contour(client, tiny()).json())
    on = contour(client, tiny(), beat_coloring="true")
    assert on.status_code == 200 and all_frames(client, on.json()) == off


def test_a_file_in_which_no_beat_is_found_is_the_same_with_the_box_on_and_off(client):
    audio = wav_bytes(0.5 * note_tone(TONE_NOTE, 4.0))
    off = all_frames(client, contour(client, audio, peak_prominence="100").json())
    on = all_frames(client, contour(client, audio, beat_coloring="true", peak_prominence="100").json())
    assert on == off


def test_a_file_shorter_than_the_peaks_window_makes_frames(client):
    short = wav_bytes(np.clip(0.15 * note_tone(TONE_NOTE, 0.4), -0.9, 0.9))
    job = contour(client, short, beat_coloring="true").json()
    assert job["frame_count"] >= 1
    assert picture(client, job, 0).shape == (HEIGHT, WIDTH, 3)


def test_oversampling_interpolate_and_gaussian_work_with_the_wave(client):
    audio = pulse_wav(seconds=3.0)
    base = contour(client, audio, beat_coloring="true").json()
    for fields in ({"resolution": "3"}, {"interpolate": "3"}, {"gaussian": "2"}):
        r = contour(client, audio, beat_coloring="true", **fields)
        assert r.status_code == 200, (fields, r.text)
        assert r.json()["frame_count"] == base["frame_count"]
        assert picture(client, r.json(), 0).shape == (HEIGHT, WIDTH, 3)


def test_mono_and_stereo_copies_of_the_same_sound_make_the_same_frames(client):
    mono = 0.5 * note_tone(TONE_NOTE, 2.0)
    a = contour(client, wav_bytes(mono), beat_coloring="true").json()
    b = contour(client, wav_bytes(np.stack([mono, mono], axis=1)), beat_coloring="true").json()
    assert all_frames(client, a) == all_frames(client, b)


def test_the_wave_costs_no_more_than_a_few_seconds_over_the_plain_contour(client):
    audio = pulse_wav(seconds=10.0)
    fields = {"window_size": "4096", "frame_rate": "30", "image_type": "contour", "colormap": COLORMAP}

    def run(**extra):
        started = time.perf_counter()
        r = client.post("/api/jobs", files={"file": ("long.wav", audio, "audio/wav")}, data={**fields, **extra})
        assert r.status_code == 200, r.text
        return time.perf_counter() - started

    plain = run()
    wave = run(beat_coloring="true")
    assert wave < plain * 1.25 + 3, (plain, wave)
