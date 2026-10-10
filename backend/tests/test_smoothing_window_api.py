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
NOTE = 36


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


@pytest.mark.parametrize("window", [1, 3, 6])
def test_frames_are_the_windowed_average_of_each_note_and_a_stopped_note_is_exactly_gone(full_client, window):
    data = burst_wav()
    off = post_window(full_client, data).json()
    last = int(np.flatnonzero(frame_values(off)[:, NOTE] > 0)[-1])  # the last frame in which the note has a value
    job = post_window(full_client, data, smoothing="0.5", smoothing_window=str(window)).json()
    assert job["smoothing"] == 0.5 and job["smoothing_window"] == window
    expected = expected_pixels(job, 0.5, window=window)
    for index in (0, 1, 2, 15, 29, last, last + 1, last + window, last + window + 1, last + window + 2):
        assert np.array_equal(frame_levels(full_client, job, index), expected[index]), (window, index)
    assert int(expected[last + window][NOTE]) > 0  # still visible on the last frame of the window
    assert int(frame_levels(full_client, job, last + window)[NOTE]) > 0
    assert int(frame_levels(full_client, job, last + window + 1)[NOTE]) == 0  # then exactly gone
    assert (frame_levels(full_client, job, last + window + 1)[NOTE:] >= 0).all()


def test_a_larger_window_keeps_a_stopped_note_visible_for_longer(full_client):
    data = burst_wav()
    visible_until = {}
    for window in (1, 4, 8):
        job = post_window(full_client, data, smoothing="0.5", smoothing_window=str(window)).json()
        levels = [int(frame_levels(full_client, job, i)[NOTE]) for i in range(job["frame_count"])]
        visible_until[window] = max(i for i, level in enumerate(levels) if level > 0)
    assert visible_until[1] < visible_until[4] < visible_until[8]
    assert visible_until[4] - visible_until[1] == 3 and visible_until[8] - visible_until[4] == 4


def test_the_same_request_twice_gives_identical_frames(client):
    data = burst_wav()
    a = post_window(client, data, smoothing="0.6", smoothing_window="5").json()
    b = post_window(client, data, smoothing="0.6", smoothing_window="5").json()
    for i in (0, 20, 30, 40, 59):
        assert frame_bytes(client, a, i) == frame_bytes(client, b, i)


def test_all_the_steps_and_the_threshold_work_on_the_smoothed_values(client):
    import colorsys

    from .test_jobs_api import frame_rgb

    data = burst_wav()
    settings = dict(smoothing="0.8", smoothing_window="8", saturation_step="20", brightness_step="50")
    off = post_window(client, data, threshold="0", **settings).json()
    on = post_window(client, data, threshold="10", **settings).json()
    seen = 0
    for i in range(off["frame_count"]):
        a, b = frame_rgb(client, off, i), frame_rgb(client, on, i)
        black = ~b.any(axis=1)
        assert (a[~black] == b[~black]).all(), i  # every tile is black or the tile without the threshold
        for rgb in b:
            top = int(rgb.max())
            assert top in (0, 128, 255)  # the frame brightness is one of the three levels
            if top >= 100:
                hsv = colorsys.rgb_to_hsv(*(rgb / 255))
                assert min(abs(hsv[1] - level / 5) for level in range(6)) < 0.03  # one of the six saturations
                seen += 1
    assert seen > 20


def test_silence_at_the_end_differs_only_where_it_does_without_the_steps(client):
    audio = burst_then_silence()
    longer = np.concatenate([audio, np.zeros(SR)])
    stepped = dict(smoothing="0.8", smoothing_window="8", saturation_step="50", brightness_step="50", threshold="10")
    plain = dict(smoothing="0.8", smoothing_window="8")

    def differing(fields):
        a = post_window(client, wav_bytes(audio, audio), **fields).json()
        b = post_window(client, wav_bytes(longer, longer), **fields).json()
        return a, [i for i in range(a["frame_count"]) if frame_bytes(client, a, i) != frame_bytes(client, b, i)]

    job, with_steps = differing(stepped)
    _, without = differing(plain)
    assert set(with_steps) <= set(without)  # the steps add no difference of their own
    assert all(i == job["frame_count"] - 1 for i in with_steps)  # at most the last frame, as before smoothing changed
