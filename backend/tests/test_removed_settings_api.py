"""The settings that feature 043 removed: window spacing, Smoothing and Smoothing window.

A request that still sends them is neither refused nor affected (the form fields are not declared, so they are ignored), and the answer does not echo them.
"""

import numpy as np
import pytest

from .test_jobs_api import SR, client, note_tone, wav_bytes  # noqa: F401

REMOVED_KEYS = ("smoothing", "smoothing_window", "window_spacing", "spacing_raised")
BAD_VALUES = {"smoothing": "banana", "smoothing_window": "99", "window_spacing": "-1"}


def burst():
    return wav_bytes(np.concatenate([note_tone(36, 0.5), np.zeros(SR // 2)]))


def job_with(client, extra=None, image_type="contour"):
    form = {"window_size": "4096", "frame_rate": "10", "image_type": image_type, **(extra or {})}
    return client.post("/api/jobs", files={"file": ("song.wav", burst(), "audio/wav")}, data=form)


def served(client, job):
    return [client.get(job["frame_url_template"].replace("{index}", str(i))).content for i in range(job["frame_count"])]


def test_bad_values_of_the_removed_settings_are_not_refused_and_change_nothing(client):
    plain = job_with(client)
    assert plain.status_code == 200, plain.text
    odd = job_with(client, BAD_VALUES)
    assert odd.status_code == 200, odd.text
    assert served(client, odd.json()) == served(client, plain.json())


@pytest.mark.parametrize("name, value", [("smoothing", ""), ("smoothing_window", ""), ("window_spacing", ""), ("smoothing", "0.5"), ("smoothing_window", "5"), ("window_spacing", "0.25")])
def test_each_removed_setting_is_ignored_alone_with_an_empty_or_a_good_value(client, name, value):
    plain = job_with(client).json()
    r = job_with(client, {name: value})
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["step_samples"] == plain["step_samples"] == 2646
    assert job["window_count"] == plain["window_count"]
    assert served(client, job) == served(client, plain)  # a good value does not change the picture either: there is nothing to set


@pytest.mark.parametrize("extra", [None, BAD_VALUES])
def test_the_answer_has_none_of_the_removed_keys(client, extra):
    job = job_with(client, extra).json()
    for key in REMOVED_KEYS:
        assert key not in job, key
    for key in ("frame_rate", "frame_count", "window_size", "step_samples", "window_count"):
        assert key in job, key


@pytest.mark.parametrize("image_type", ["decay", "polychord", "energy-graphs"])
def test_the_removed_settings_are_ignored_for_other_image_types_too(client, image_type):
    plain = job_with(client, image_type=image_type)
    odd = job_with(client, BAD_VALUES, image_type=image_type)
    assert plain.status_code == odd.status_code == 200
    assert served(client, odd.json()) == served(client, plain.json())
