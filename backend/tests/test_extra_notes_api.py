"""The Extra notes (k) setting through ``POST /api/jobs`` (feature 044, User Story 3): the optional ``extra_notes`` field and the ``extra_notes`` key of the answer."""

import numpy as np
import pytest

import app.routers.jobs as jobs
from app.services.image_types import IMAGE_TYPES

from .test_jobs_api import SR, client, leftovers, note_tone, wav_bytes  # noqa: F401

FIVE = ("decay", "decay-exp", "chromatic-decay", "chromatic-wireframe", "rhythm-circles")  # rhythm-circles since feature 047: its voted tempos follow the starts of the 5 loudest notes
OTHER = ("contour", "energy-graphs")
MESSAGE_8 = "The extra notes must be a whole number from 1 to 8."


def tiny():
    return wav_bytes(np.zeros(SR // 2))


def post(client, image_type, data=None, **fields):
    form = {"window_size": "4096", "frame_rate": "10", "image_type": image_type, **fields}
    return client.post("/api/jobs", files={"file": ("song.wav", data or tiny(), "audio/wav")}, data=form)


def refused(response, message):
    assert response.status_code == 400, response.text
    assert response.json()["detail"] == message


@pytest.mark.parametrize("image_type", IMAGE_TYPES)
def test_not_sent_means_2_and_the_answer_says_so_for_every_picture(client, image_type):
    r = post(client, image_type)
    assert r.status_code == 200, r.text
    assert r.json()["extra_notes"] == 2


@pytest.mark.parametrize("image_type", FIVE)
@pytest.mark.parametrize("value", ["1", "2", "5"])
def test_one_to_five_is_accepted_and_echoed_for_the_pictures_of_five_notes(client, image_type, value):
    r = post(client, image_type, extra_notes=value)
    assert r.status_code == 200, r.text
    assert r.json()["extra_notes"] == int(value)
    assert type(r.json()["extra_notes"]) is int


@pytest.mark.parametrize("image_type", FIVE)
def test_six_is_refused_for_the_pictures_of_five_notes(client, image_type):
    refused(post(client, image_type, extra_notes="6"), "The extra notes must be a whole number from 1 to 5.")


@pytest.mark.parametrize("notes", ["5", "6", "7", "8"])
def test_polar_chords_accepts_k_up_to_its_notes_shown(client, notes):
    n = int(notes)
    assert post(client, "polar-chords", polar_notes=notes, extra_notes=notes).status_code == 200
    refused(post(client, "polar-chords", polar_notes=notes, extra_notes=str(n + 1)), f"The extra notes must be a whole number from 1 to {n}." if n < 8 else MESSAGE_8)


def test_polar_chords_without_polar_notes_has_n_5(client):
    refused(post(client, "polar-chords", extra_notes="6"), "The extra notes must be a whole number from 1 to 5.")


@pytest.mark.parametrize("notes", ["5", "6", "8"])
def test_polychord_accepts_k_up_to_its_number_of_notes(client, notes):
    n = int(notes)
    assert post(client, "polychord", polychord_notes=notes, extra_notes=notes).json()["extra_notes"] == n
    if n < 8:
        refused(post(client, "polychord", polychord_notes=notes, extra_notes=str(n + 1)), f"The extra notes must be a whole number from 1 to {n}.")


def test_polychord_without_its_notes_has_the_default_of_6(client):
    assert post(client, "polychord", extra_notes="6").status_code == 200
    refused(post(client, "polychord", extra_notes="7"), "The extra notes must be a whole number from 1 to 6.")


@pytest.mark.parametrize("image_type", OTHER)
def test_the_other_pictures_accept_1_to_8_and_ignore_it(client, image_type):
    data = wav_bytes(np.concatenate([note_tone(36, 0.3), np.zeros(SR // 5)]))
    one = post(client, image_type, data, extra_notes="1").json()
    eight = post(client, image_type, data, extra_notes="8").json()
    assert (one["extra_notes"], eight["extra_notes"]) == (1, 8)
    for index in range(one["frame_count"]):
        a = client.get(one["frame_url_template"].replace("{index}", str(index))).content
        b = client.get(eight["frame_url_template"].replace("{index}", str(index))).content
        assert a == b, index


@pytest.mark.parametrize("image_type", ["decay", "contour", "polychord"])
@pytest.mark.parametrize("value", ["0", "9", "-1", "2.5", "abc", "nan", "inf", "-inf", "", "  ", "1e9", "2,5"])
def test_anything_that_is_not_a_whole_number_from_1_to_8_is_refused_for_every_picture(client, image_type, value):
    refused(post(client, image_type, extra_notes=value), MESSAGE_8)
    assert leftovers() == []


def test_a_refusal_happens_before_the_file_is_read_and_leaves_nothing_behind(client, monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("the file must not be read")

    monkeypatch.setattr(jobs, "read_wav", fail)
    refused(post(client, "decay", extra_notes="6"), "The extra notes must be a whole number from 1 to 5.")
    refused(post(client, "contour", extra_notes="9"), MESSAGE_8)
    refused(post(client, "polychord", polychord_notes="5", extra_notes="6"), "The extra notes must be a whole number from 1 to 5.")
    assert leftovers() == []


def test_the_job_gives_write_frames_the_value_of_the_request_and_2_by_default(client, monkeypatch):
    given = []
    real = jobs.write_frames

    def spy(frames, *args, **kwargs):
        given.append(kwargs["extra_notes"])
        return real(frames, *args, **kwargs)

    monkeypatch.setattr(jobs, "write_frames", spy)
    post(client, "decay")
    post(client, "decay", extra_notes="4")
    post(client, "contour", extra_notes="7")
    assert given == [2, 4, 7]


def test_after_a_refusal_the_next_request_is_accepted(client):
    refused(post(client, "decay", extra_notes="9"), MESSAGE_8)
    assert post(client, "decay", extra_notes="3").status_code == 200


def test_k_changes_the_frames_of_a_job_where_a_note_is_displaced(client):
    """A real file: five tones struck together that fade, then louder tones start: with k = 5 the faded ones keep their circles, with k = 1 they lose them sooner."""
    t = np.arange(int(3 * SR)) / SR
    fading = sum(0.1 * np.sin(2 * np.pi * f * t) for f in (110.0, 146.83, 164.81, 196.0, 220.0)) * np.exp(-t * 0.5)
    late = sum(0.5 * np.sin(2 * np.pi * f * t) for f in (440.0, 554.37, 659.25)) * (t > 1.0)
    data = wav_bytes(np.clip(fading + late, -0.99, 0.99))
    low = post(client, "decay", data, extra_notes="1").json()
    high = post(client, "decay", data, extra_notes="5").json()
    frames = [
        (client.get(low["frame_url_template"].replace("{index}", str(i))).content, client.get(high["frame_url_template"].replace("{index}", str(i))).content)
        for i in range(low["frame_count"])
    ]
    assert any(a != b for a, b in frames)
