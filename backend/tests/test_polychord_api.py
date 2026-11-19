"""The ``polychord`` image type through ``POST /api/jobs``: the type, its four settings, the one measurement, the ignored
settings, the frames (feature 042)."""

import io

import numpy as np
import pytest
from PIL import Image

import app.routers.jobs as jobs
from app.services import polychord as pc
from app.services.image_types import IMAGE_TYPES
from app.services.local_peaks import DEFAULT_PROMINENCE

from .frame_size import HEIGHT, WIDTH
from .test_jobs_api import SR, client, leftovers, note_tone, wav_bytes  # noqa: F401
from .test_peak_tile_colors_api import COLORMAP, post, pulse_wav
from .test_resolution_api import tiny

TYPE = "polychord"
TYPE_MESSAGE = f"The image type must be one of {', '.join(IMAGE_TYPES)}."
NOTES_MESSAGE = "The number of notes must be a whole number from 5 to 8."
MIN_MESSAGE = "The minimum number of copies must be a whole number from 1 to 12."
MAX_MESSAGE = "The maximum number of copies must be a whole number from 1 to 12."
ORDER_MESSAGE = "The maximum number of copies must not be less than the minimum."
ROTATION_MESSAGE = "The rotation must be a number from -360 to 360 degrees a second."
DISTANCE_MESSAGE = "The minimum distance must be a number from 100 to 2000 milliseconds."


def poly(client, data=None, **fields):
    return post(client, data, image_type=TYPE, **fields)


def picture(client, job, index):
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    assert r.status_code == 200
    return np.asarray(Image.open(io.BytesIO(r.content)).convert("RGB"))


def served_bytes(client, job):
    return [client.get(job["frame_url_template"].replace("{index}", str(i))).content for i in range(job["frame_count"])]


def spying(monkeypatch):
    """Record the arguments the job gives ``write_frames`` (and call the real one)."""
    calls = []
    real = jobs.write_frames

    def spy(values, directory, **kwargs):
        calls.append((np.array(values), kwargs))
        return real(values, directory, **kwargs)

    monkeypatch.setattr(jobs, "write_frames", spy)
    return calls


# --- choosing it ----------------------------------------------------------------------------------------------------


def test_it_is_the_last_of_the_nine_image_types_and_the_message_lists_them():
    assert IMAGE_TYPES[-1] == TYPE and len(IMAGE_TYPES) == 9
    assert TYPE_MESSAGE.endswith("rhythm-circles, chromatic-wireframe, polychord.")


@pytest.mark.parametrize("name", ["Polychord", "poly-chord", "poly_chord", "polychord ", "chord", "POLYCHORD", ""])
def test_a_name_that_is_not_exactly_polychord_is_refused_with_the_nine_names(client, name):
    r = post(client, tiny(), image_type=name)
    assert r.status_code == 400 and r.json()["detail"] == TYPE_MESSAGE
    assert leftovers() == []


def test_polychord_with_no_other_field_makes_frames_and_reports_the_defaults(client):
    r = poly(client, tiny())
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["image_type"] == TYPE
    assert (job["polychord_notes"], job["polychord_min_copies"], job["polychord_max_copies"], job["polychord_rotation"]) == (6, 3, 12, 15.0)
    assert job["frame_count"] > 0
    assert picture(client, job, 0).shape == (HEIGHT, WIDTH, 3)


def test_the_response_has_the_same_keys_for_every_type_and_the_four_new_ones_are_in_all_of_them(client):
    keys = set(post(client, tiny(), image_type="contour").json())
    assert {"polychord_notes", "polychord_min_copies", "polychord_max_copies", "polychord_rotation"} <= keys
    assert set(poly(client, tiny()).json()) == keys


def test_the_frame_count_is_that_of_the_other_types(client):
    audio = pulse_wav(seconds=3.0)
    assert poly(client, audio).json()["frame_count"] == post(client, audio, image_type="contour").json()["frame_count"]


# --- the four settings ----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["5", "6", "8", " 7 ", "6.0", "8.0"])
def test_a_whole_number_of_notes_from_5_to_8_is_accepted_and_echoed_as_a_number(client, value):
    r = poly(client, tiny(), polychord_notes=value)
    assert r.status_code == 200, r.text
    assert r.json()["polychord_notes"] == int(float(value))


@pytest.mark.parametrize("value", ["4", "9", "0", "-6", "6.5", "abc", "", "nan", "inf", "1e1", "5,5"])
def test_any_other_number_of_notes_is_refused_and_nothing_is_created(client, value):
    r = poly(client, tiny(), polychord_notes=value)
    assert r.status_code == 400 and r.json()["detail"] == NOTES_MESSAGE
    assert leftovers() == []


@pytest.mark.parametrize("field, low_message", [("polychord_min_copies", MIN_MESSAGE), ("polychord_max_copies", MAX_MESSAGE)])
@pytest.mark.parametrize("value", ["0", "13", "-1", "2.5", "abc", "", "nan", "inf", "1e2"])
def test_copies_that_are_not_whole_numbers_from_1_to_12_are_refused_with_the_name_of_the_setting(client, field, low_message, value):
    r = poly(client, tiny(), **{field: value})
    assert r.status_code == 400 and r.json()["detail"] == low_message
    assert leftovers() == []


@pytest.mark.parametrize("low, high", [("1", "1"), ("1", "12"), ("12", "12"), ("5", "5"), (" 3 ", "9.0")])
def test_copies_at_and_between_the_limits_are_accepted_and_echoed(client, low, high):
    r = poly(client, tiny(), polychord_min_copies=low, polychord_max_copies=high)
    assert r.status_code == 200, r.text
    assert (r.json()["polychord_min_copies"], r.json()["polychord_max_copies"]) == (int(float(low)), int(float(high)))


@pytest.mark.parametrize("low, high", [("8", "7"), ("12", "11"), ("4", "1")])
def test_a_maximum_under_the_minimum_is_refused_and_nothing_is_created(client, low, high):
    r = poly(client, tiny(), polychord_min_copies=low, polychord_max_copies=high)
    assert r.status_code == 400 and r.json()["detail"] == ORDER_MESSAGE
    assert leftovers() == []


def test_a_minimum_alone_above_the_default_maximum_is_fine_at_12_and_the_default_minimum_above_a_low_maximum_is_refused(client):
    assert poly(client, tiny(), polychord_min_copies="12").status_code == 200
    r = poly(client, tiny(), polychord_max_copies="2")  # the default minimum is 3
    assert r.status_code == 400 and r.json()["detail"] == ORDER_MESSAGE


@pytest.mark.parametrize("value, expected", [("-360", -360.0), ("0", 0.0), ("15", 15.0), ("-15.5", -15.5), ("360", 360.0), (" 90 ", 90.0), ("1e2", 100.0)])
def test_a_rotation_from_minus_360_to_360_is_accepted_and_echoed_as_a_number(client, value, expected):
    r = poly(client, tiny(), polychord_rotation=value)
    assert r.status_code == 200, r.text
    assert r.json()["polychord_rotation"] == expected


@pytest.mark.parametrize("value", ["-360.5", "361", "1000", "abc", "", "nan", "inf", "-inf", "1,5"])
def test_any_other_rotation_is_refused_and_nothing_is_created(client, value):
    r = poly(client, tiny(), polychord_rotation=value)
    assert r.status_code == 400 and r.json()["detail"] == ROTATION_MESSAGE
    assert leftovers() == []


@pytest.mark.parametrize(
    "fields, message",
    [
        ({"polychord_notes": "9"}, NOTES_MESSAGE),
        ({"polychord_min_copies": "0"}, MIN_MESSAGE),
        ({"polychord_max_copies": "13"}, MAX_MESSAGE),
        ({"polychord_min_copies": "9", "polychord_max_copies": "8"}, ORDER_MESSAGE),
        ({"polychord_rotation": "nan"}, ROTATION_MESSAGE),
    ],
)
def test_every_setting_is_checked_before_the_file_is_read_with_nothing_created(client, fields, message):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": TYPE, **fields})  # no file at all
    assert r.status_code == 400 and r.json()["detail"] == message
    garbage = client.post("/api/jobs", files={"file": ("song.wav", b"not a wav", "audio/wav")}, data={"window_size": "4096", "frame_rate": "10", "image_type": TYPE, **fields})
    assert garbage.status_code == 400 and garbage.json()["detail"] == message  # the settings message, not the audio one
    assert leftovers() == []


@pytest.mark.parametrize("image_type", ["contour", "decay", "chromatic-wireframe", "rhythm-circles"])
def test_the_polychord_settings_sent_with_another_type_are_checked_echoed_and_have_no_effect(client, image_type):
    audio = tiny()
    plain = post(client, audio, image_type=image_type).json()
    sent = post(client, audio, image_type=image_type, polychord_notes="8", polychord_min_copies="2", polychord_max_copies="5", polychord_rotation="-90")
    assert sent.status_code == 200
    assert (sent.json()["polychord_notes"], sent.json()["polychord_rotation"]) == (8, -90.0)
    assert served_bytes(client, sent.json()) == served_bytes(client, plain)
    assert post(client, audio, image_type=image_type, polychord_notes="9").status_code == 400


# --- the settings of the other types are ignored --------------------------------------------------------------------


@pytest.mark.parametrize("fields", [{"threshold": "5"}, {"decay_rate": "2"}, {"note_layout": "spiral"}, {"polar_notes": "8"}, {"decay_low": "2"}, {"note_count": "20"}, {"resolution": "2"}])
def test_the_settings_of_the_other_types_are_accepted_and_ignored(client, fields):
    audio = pulse_wav(seconds=3.0)
    plain = poly(client, audio).json()
    sent = poly(client, audio, **fields)
    assert sent.status_code == 200, sent.text
    assert served_bytes(client, sent.json()) == served_bytes(client, plain)


# --- the measurement and the frames ---------------------------------------------------------------------------------


@pytest.fixture
def measured(monkeypatch):
    calls = []
    real = jobs.measure_local_peaks

    def spy(left, right, file_rate, min_distance, prominence, *args, **kwargs):
        calls.append((len(left), file_rate, min_distance, prominence))
        return real(left, right, file_rate, min_distance, prominence, *args, **kwargs)

    monkeypatch.setattr(jobs, "measure_local_peaks", spy)
    return calls


def test_the_local_peaks_are_measured_once_for_both_the_beat_and_the_tempo(client, measured):
    assert poly(client, tiny(), peak_distance="300").status_code == 200
    assert measured == [(22050, SR, 300.0, DEFAULT_PROMINENCE)]


def test_the_job_gives_write_frames_the_beat_the_tempos_the_frame_rate_and_the_settings(client, monkeypatch):
    calls = spying(monkeypatch)
    job = poly(client, pulse_wav(), polychord_notes="7", polychord_min_copies="2", polychord_max_copies="9", polychord_rotation="-20").json()
    (values, kwargs), = calls
    assert kwargs["image_type"] == TYPE
    assert kwargs["beat"] is not None and kwargs["beat"].shape == (job["frame_count"],)
    data = kwargs["polychord"]
    assert isinstance(data, pc.PolychordData)
    assert data.tempos.shape == (job["frame_count"],) and data.frame_rate == job["frame_rate"] == 10.0
    assert ((data.tempos >= 60) & (data.tempos <= 156)).all()
    assert kwargs["polychord_settings"] == pc.PolychordSettings(7, 2, 9, -20.0)


def test_the_frames_are_what_the_library_draws_from_what_the_job_gave_write_frames(client, tmp_path, monkeypatch):
    calls = spying(monkeypatch)
    job = poly(client, pulse_wav(), polychord_notes="8", polychord_min_copies="2", polychord_max_copies="10", polychord_rotation="45").json()
    (values, kwargs), = calls
    data = kwargs["polychord"]
    pc.write_polychord_frames(values, kwargs["beat"], data.tempos, kwargs["polychord_settings"], data.frame_rate, kwargs["colormap"], tmp_path / "expected", WIDTH, HEIGHT)
    expected = [(tmp_path / "expected" / f"frame_{i:06d}.png").read_bytes() for i in range(job["frame_count"])]
    assert served_bytes(client, job) == expected
    assert any(picture(client, job, i).any() for i in range(job["frame_count"]))  # something was drawn


def test_the_defaults_are_the_settings_the_job_gives_when_none_is_sent(client, monkeypatch):
    calls = spying(monkeypatch)
    poly(client, tiny())
    assert calls[0][1]["polychord_settings"] == pc.DEFAULT_POLYCHORD_SETTINGS


def test_the_picture_turns_with_the_rotation_through_the_job(client):
    audio = pulse_wav(seconds=3.0)
    still = served_bytes(client, poly(client, audio, polychord_rotation="0").json())
    turning = served_bytes(client, poly(client, audio, polychord_rotation="90").json())
    assert still[0] == turning[0]  # frame 0 starts at 0 degrees
    assert still[1] != turning[1]
    assert len(set(turning)) > len(set(still))


def test_the_other_types_are_not_given_polychord_data(client, monkeypatch):
    calls = spying(monkeypatch)
    post(client, tiny(), image_type="chromatic-wireframe")
    post(client, tiny(), image_type="contour")
    assert all(kwargs.get("polychord") is None for _, kwargs in calls)


def test_a_failure_while_drawing_removes_the_job_and_answers_500(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("drawing failed")

    monkeypatch.setattr(jobs, "write_frames", boom)
    r = poly(client, tiny())
    assert r.status_code == 500
    assert leftovers() == []
