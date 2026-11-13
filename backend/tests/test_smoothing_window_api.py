"""The smoothing window through the job endpoint: the optional ``smoothing_window`` field (a whole number from 1 to 20),
its refusals, the response, and the frames.
"""

import numpy as np
import pytest

from .test_jobs_api import (  # noqa: F401
    SR,
    burst_then_silence,
    client,
    expected_pixels,
    frame_levels,
    frame_values,
    full_client,
    leftovers,
    wav_bytes,
)

MESSAGE = "The smoothing window must be a whole number from 1 to 20."


def post_window(client, data, **fields):
    form = {"window_size": "4096", "frame_rate": "30", **fields}
    return client.post("/api/jobs", files={"file": ("song.wav", data, "audio/wav")}, data=form)


def burst_wav():
    audio = burst_then_silence()
    return wav_bytes(audio, audio)


def frame_bytes(client, job, index):
    return client.get(job["frame_url_template"].replace("{index}", str(index))).content


@pytest.mark.parametrize("text, echoed", [("1", 1), ("5", 5), ("20", 20), ("5.0", 5), (" 7 ", 7)])
def test_accepted_values_are_echoed_as_integers(client, text, echoed):
    r = post_window(client, wav_bytes(np.zeros(SR // 2)), smoothing_window=text)
    assert r.status_code == 200, r.text
    assert r.json()["smoothing_window"] == echoed
    assert type(r.json()["smoothing_window"]) is int


def test_without_the_field_the_window_is_one_and_the_frames_equal_those_sent_with_one(client):
    data = burst_wav()
    missing = post_window(client, data, smoothing="0.5").json()
    one = post_window(client, data, smoothing="0.5", smoothing_window="1").json()
    assert missing["smoothing_window"] == 1 and one["smoothing_window"] == 1
    for i in (0, 10, 29, 31, 45, 59):
        assert frame_bytes(client, missing, i) == frame_bytes(client, one, i)


@pytest.mark.parametrize("text", ["", " ", "0", "-1", "21", "100", "2.5", "abc", "nan", "inf", "-inf", "1e9"])
def test_anything_else_is_refused_with_the_range(client, text):
    before = leftovers()
    r = post_window(client, wav_bytes(np.zeros(SR // 2)), smoothing_window=text)
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == MESSAGE
    assert leftovers() == before  # no job was created


def test_a_bad_window_is_refused_before_the_file_is_read(client):
    r = client.post(
        "/api/jobs",
        files={"file": ("song.wav", b"this is not audio", "audio/wav")},
        data={"window_size": "4096", "frame_rate": "30", "smoothing_window": "99"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == MESSAGE


def test_with_smoothing_zero_every_window_gives_the_frames_of_no_smoothing(client):
    data = burst_wav()
    plain = post_window(client, data).json()
    for w in ("1", "5", "20"):
        job = post_window(client, data, smoothing="0", smoothing_window=w).json()
        assert job["smoothing"] == 0.0 and job["smoothing_window"] == int(w)
        for i in (0, 10, 29, 31, 45, 59):
            assert frame_bytes(client, job, i) == frame_bytes(client, plain, i), (w, i)


def test_the_same_request_twice_gives_identical_frames(client):
    data = burst_wav()
    a = post_window(client, data, smoothing="0.6", smoothing_window="5").json()
    b = post_window(client, data, smoothing="0.6", smoothing_window="5").json()
    for i in (0, 20, 30, 40, 59):
        assert frame_bytes(client, a, i) == frame_bytes(client, b, i)


def test_silence_at_the_end_differs_only_where_it_does_without_the_threshold(client):
    audio = burst_then_silence()
    longer = np.concatenate([audio, np.zeros(SR)])
    stepped = dict(smoothing="0.8", smoothing_window="8", threshold="10")
    plain = dict(smoothing="0.8", smoothing_window="8")

    def differing(fields):
        a = post_window(client, wav_bytes(audio, audio), **fields).json()
        b = post_window(client, wav_bytes(longer, longer), **fields).json()
        return a, [i for i in range(a["frame_count"]) if frame_bytes(client, a, i) != frame_bytes(client, b, i)]

    job, with_steps = differing(stepped)
    _, without = differing(plain)
    assert set(with_steps) <= set(without)  # the threshold adds no difference of its own
    assert all(i == job["frame_count"] - 1 for i in with_steps)  # at most the last frame, as before smoothing changed
