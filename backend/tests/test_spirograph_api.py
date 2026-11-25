"""The ``spirograph`` image type through ``POST /api/jobs``: the type, its two settings, Extra notes, the ignored settings, the
frames (feature 046)."""

import io

import numpy as np
import pytest
from PIL import Image

import app.routers.jobs as jobs
from app.services.image_types import IMAGE_TYPES

from app.services.local_peaks import DEFAULT_PROMINENCE

from .frame_size import HEIGHT, WIDTH
from .test_jobs_api import SR, client, leftovers, note_tone, wav_bytes  # noqa: F401
from .test_peak_tile_colors_api import COLORMAP, post, pulse_wav
from .test_resolution_api import tiny

TYPE = "spirograph"
TYPE_MESSAGE = f"The image type must be one of {', '.join(IMAGE_TYPES)}."
NOTES_MESSAGE = "The number of spirograph notes must be a whole number from 5 to 12."
HISTORY_MESSAGE = "The history length must be a whole number from 5 to 12."
FADE_MESSAGE = "The history fade must be a number from 0.4 to 0.85."


def spiro(client, data=None, **fields):
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


def test_it_is_the_last_of_the_ten_image_types_and_the_message_lists_them():
    assert IMAGE_TYPES[-1] == TYPE and len(IMAGE_TYPES) == 10
    assert TYPE_MESSAGE.endswith("chromatic-wireframe, polychord, spirograph.")


@pytest.mark.parametrize("name", ["Spirograph", "spiro", "spirograph ", "SPIROGRAPH", "spiro-graph", ""])
def test_a_name_that_is_not_exactly_spirograph_is_refused_with_the_ten_names(client, name):
    r = post(client, tiny(), image_type=name)
    assert r.status_code == 400 and r.json()["detail"] == TYPE_MESSAGE
    assert leftovers() == []


def test_spirograph_with_no_other_field_makes_frames_and_reports_the_defaults(client):
    r = spiro(client, pulse_wav(seconds=3.0))
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["image_type"] == TYPE
    assert (job["spirograph_notes"], job["spirograph_history"], job["spirograph_fade"]) == (8, 8, 0.7)
    assert job["frame_count"] > 0
    first = picture(client, job, 0)
    assert first.shape == (HEIGHT, WIDTH, 3)
    assert any(picture(client, job, i).any() for i in range(job["frame_count"]))  # the tone is drawn
    assert not first[:5].any()  # on black


def test_the_response_has_the_same_keys_for_every_type_and_the_two_new_ones_are_in_all_of_them(client):
    keys = set(post(client, tiny(), image_type="contour").json())
    assert {"spirograph_notes", "spirograph_history", "spirograph_fade"} <= keys
    assert set(spiro(client, tiny()).json()) == keys
    assert post(client, tiny(), image_type="decay").json()["spirograph_notes"] == 8


def test_the_frame_count_is_that_of_the_other_types(client):
    audio = pulse_wav(seconds=3.0)
    assert spiro(client, audio).json()["frame_count"] == post(client, audio, image_type="contour").json()["frame_count"]


# --- the two settings -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["5", "8", "12", " 7 ", "6.0", "12.0"])
def test_a_whole_number_from_5_to_12_is_accepted_and_echoed_as_a_number(client, value):
    for field, key in (("spirograph_notes", "spirograph_notes"), ("spirograph_history", "spirograph_history")):
        r = spiro(client, tiny(), **{field: value})
        assert r.status_code == 200, r.text
        assert r.json()[key] == int(float(value)) and type(r.json()[key]) is int


@pytest.mark.parametrize("value", ["4", "13", "0", "-8", "7.5", "abc", "", "nan", "inf", "1e2", "5,5"])
def test_any_other_number_of_notes_is_refused_and_nothing_is_created(client, value):
    r = spiro(client, tiny(), spirograph_notes=value)
    assert r.status_code == 400 and r.json()["detail"] == NOTES_MESSAGE
    assert leftovers() == []


@pytest.mark.parametrize("value", ["4", "13", "0", "-8", "7.5", "abc", "", "nan", "inf", "1e2", "5,5"])
def test_any_other_history_length_is_refused_and_nothing_is_created(client, value):
    r = spiro(client, tiny(), spirograph_history=value)
    assert r.status_code == 400 and r.json()["detail"] == HISTORY_MESSAGE
    assert leftovers() == []


@pytest.mark.parametrize("value, expected", [("0.4", 0.4), ("0.7", 0.7), ("0.85", 0.85), (" 0.5 ", 0.5), ("0.60", 0.6), ("4e-1", 0.4)])
def test_a_fade_from_0_4_to_0_85_is_accepted_and_echoed_as_a_number(client, value, expected):
    r = spiro(client, tiny(), spirograph_fade=value)
    assert r.status_code == 200, r.text
    assert r.json()["spirograph_fade"] == expected


@pytest.mark.parametrize("value", ["0.39", "0.86", "0", "1", "-0.5", "abc", "", "nan", "inf", "0,7", "7"])
def test_any_other_fade_is_refused_and_nothing_is_created(client, value):
    r = spiro(client, tiny(), spirograph_fade=value)
    assert r.status_code == 400 and r.json()["detail"] == FADE_MESSAGE
    assert leftovers() == []


def test_the_fade_makes_different_pictures(client):
    audio = pulse_wav(seconds=3.0)
    slow = served_bytes(client, spiro(client, audio, spirograph_fade="0.85").json())
    fast = served_bytes(client, spiro(client, audio, spirograph_fade="0.4").json())
    assert slow != fast and slow != served_bytes(client, spiro(client, audio).json())


def test_the_two_settings_make_different_pictures(client):
    audio = pulse_wav(seconds=3.0)
    base = served_bytes(client, spiro(client, audio).json())
    assert served_bytes(client, spiro(client, audio, spirograph_notes="5", extra_notes="2").json()) != base
    assert served_bytes(client, spiro(client, audio, spirograph_history="12").json()) != base


@pytest.mark.parametrize(
    "fields, message",
    [
        ({"spirograph_notes": "13"}, NOTES_MESSAGE),
        ({"spirograph_history": "4"}, HISTORY_MESSAGE),
        ({"spirograph_notes": "nan"}, NOTES_MESSAGE),
        ({"spirograph_fade": "0.9"}, FADE_MESSAGE),
    ],
)
def test_every_setting_is_checked_before_the_file_is_read_with_nothing_created(client, fields, message):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": TYPE, **fields})  # no file at all
    assert r.status_code == 400 and r.json()["detail"] == message
    garbage = client.post("/api/jobs", files={"file": ("song.wav", b"not a wav", "audio/wav")}, data={"window_size": "4096", "frame_rate": "10", "image_type": TYPE, **fields})
    assert garbage.status_code == 400 and garbage.json()["detail"] == message  # the settings message, not the audio one
    assert leftovers() == []


@pytest.mark.parametrize("image_type", ["contour", "decay", "chromatic-wireframe", "polychord"])
def test_the_spirograph_settings_sent_with_another_type_are_checked_echoed_and_have_no_effect(client, image_type):
    audio = tiny()
    plain = post(client, audio, image_type=image_type).json()
    sent = post(client, audio, image_type=image_type, spirograph_notes="12", spirograph_history="5", spirograph_fade="0.5")
    assert sent.status_code == 200
    assert (sent.json()["spirograph_notes"], sent.json()["spirograph_history"], sent.json()["spirograph_fade"]) == (12, 5, 0.5)
    assert served_bytes(client, sent.json()) == served_bytes(client, plain)
    assert post(client, audio, image_type=image_type, spirograph_notes="13").status_code == 400
    assert post(client, audio, image_type=image_type, spirograph_history="4").status_code == 400
    assert post(client, audio, image_type=image_type, spirograph_fade="0.9").status_code == 400


# --- Extra notes (feature 044) ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("notes, limit", [("5", 5), ("6", 6), ("8", 8), ("9", 8), ("12", 8)])
def test_extra_notes_goes_up_to_the_smaller_of_the_notes_and_8(client, notes, limit):
    r = spiro(client, tiny(), spirograph_notes=notes, extra_notes=str(limit + 1))
    assert r.status_code == 400 and r.json()["detail"] == f"The extra notes must be a whole number from 1 to {limit}."
    assert leftovers() == []
    assert spiro(client, tiny(), spirograph_notes=notes, extra_notes=str(limit)).json()["extra_notes"] == limit


def test_extra_notes_that_is_not_sent_is_2_and_the_default_notes_allow_up_to_8(client):
    assert spiro(client, tiny()).json()["extra_notes"] == 2
    assert spiro(client, tiny(), extra_notes="8").status_code == 200
    r = spiro(client, tiny(), extra_notes="9")
    assert r.status_code == 400 and r.json()["detail"] == "The extra notes must be a whole number from 1 to 8."


# --- the settings of the other types are ignored --------------------------------------------------------------------


@pytest.mark.parametrize(
    "fields",
    [{"threshold": "5"}, {"decay_rate": "2"}, {"note_layout": "spiral"}, {"polar_notes": "8"}, {"note_count": "20"}, {"resolution": "2"}, {"peak_distance": "300"}, {"polychord_notes": "8"}, {"beat_coloring": "true"}],
)
def test_the_settings_of_the_other_types_are_accepted_and_ignored(client, fields):
    audio = pulse_wav(seconds=3.0)
    plain = spiro(client, audio).json()
    sent = spiro(client, audio, **fields)
    assert sent.status_code == 200, sent.text
    assert served_bytes(client, sent.json()) == served_bytes(client, plain)


def test_the_3d_export_is_refused_for_spirograph(client):
    r = spiro(client, tiny(), export_obj="true")
    assert r.status_code == 400 and r.json()["detail"] == "The 3D export is only available for Contour and Chromatic Wireframe."
    assert leftovers() == []


# --- the measurement and the frames ---------------------------------------------------------------------------------


def test_the_local_peaks_are_measured_once_for_spirograph_with_the_minimum_distance_of_the_request(client, monkeypatch):
    calls = []
    real = jobs.measure_local_peaks

    def spy(left, right, file_rate, min_distance, prominence):
        calls.append((len(left), file_rate, min_distance, prominence))
        return real(left, right, file_rate, min_distance, prominence)

    monkeypatch.setattr(jobs, "measure_local_peaks", spy)
    assert spiro(client, tiny(), peak_distance="300").status_code == 200
    assert calls == [(22050, SR, 300.0, DEFAULT_PROMINENCE)]  # the beat only: no tempo is made from it
    assert post(client, tiny(), image_type="contour").status_code == 200
    assert len(calls) == 1  # Contour without the beat coloring measures nothing


def test_the_job_gives_write_frames_the_settings_and_the_beat_and_no_other_data(client, monkeypatch):
    calls = spying(monkeypatch)
    job = spiro(client, tiny(), spirograph_notes="10", spirograph_history="6", extra_notes="3").json()
    (values, kwargs), = calls
    assert (kwargs["spirograph_settings"].notes, kwargs["spirograph_settings"].history) == (10, 6)
    assert kwargs["image_type"] == TYPE and kwargs["extra_notes"] == 3
    beat = np.asarray(kwargs["beat"])
    assert beat.shape == (job["frame_count"],) and beat.min() >= 0 and beat.max() <= 1  # the place of each frame in the local peak
    assert kwargs.get("polychord") is None and kwargs["energy"] is None and kwargs["rhythm"] is None  # no tempo, no other measurement


def test_the_minimum_distance_is_echoed_and_changes_the_pictures_through_the_beat(client):
    audio = pulse_wav(seconds=3.0)
    near = spiro(client, audio, peak_distance="100")
    far = spiro(client, audio, peak_distance="2000")
    assert near.status_code == far.status_code == 200
    assert (near.json()["peak_distance"], far.json()["peak_distance"]) == (100.0, 2000.0)
    assert served_bytes(client, near.json()) != served_bytes(client, far.json())


def test_the_defaults_are_the_settings_the_job_gives_when_none_is_sent(client, monkeypatch):
    calls = spying(monkeypatch)
    spiro(client, tiny())
    assert (calls[0][1]["spirograph_settings"].notes, calls[0][1]["spirograph_settings"].history) == (8, 8)


def test_a_failure_while_drawing_removes_the_job_and_answers_500(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("drawing failed")

    monkeypatch.setattr(jobs, "write_frames", boom)
    r = spiro(client, tiny())
    assert r.status_code == 500
    assert leftovers() == []


def test_the_frames_are_what_the_library_draws_from_what_the_job_gave_write_frames(client, tmp_path, monkeypatch):
    from app.services.frame_rendering import write_frames

    calls = spying(monkeypatch)
    job = spiro(client, pulse_wav(seconds=3.0), spirograph_notes="6", spirograph_history="7").json()
    values, kwargs = calls[0]
    write_frames(values, tmp_path / "direct", **kwargs)
    direct = [p.read_bytes() for p in sorted((tmp_path / "direct").glob("frame_*.png"))]
    assert direct == served_bytes(client, job)
    assert COLORMAP  # the colormap of these tests is the one the job used
