"""Discrete colour levels through the job endpoint: the optional ``hue_step``, ``saturation_step`` and
``brightness_step`` fields (N/A, or one value from each list), their refusals, the response, and the frames.
"""

import colorsys

import numpy as np
import pytest

from .test_jobs_api import SR, client, frame_rgb, leftovers, tone, wav_bytes  # noqa: F401

HSV_TOLERANCE = 0.03


def chord_wav(seconds=3):
    """Several notes whose loudness falls and rises, so frames differ in brightness, saturation and hue."""
    t = np.arange(seconds * SR) / SR
    audio = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((220, 0.5), (277.18, 0.35), (329.63, 0.3), (440, 0.2)))
    audio = audio * np.interp(t, [0, 1, 2, 3], [1.0, 0.3, 0.9, 0.05])
    return wav_bytes(0.8 * audio / np.abs(audio).max())


def post_steps(client, data=None, **fields):
    form = {"window_size": "4096", "frame_rate": "10", **fields}
    return client.post("/api/jobs", files={"file": ("song.wav", data or chord_wav(), "audio/wav")}, data=form)


def tiles_hsv(client, job, index):
    return np.array([colorsys.rgb_to_hsv(*(c / 255.0)) for c in frame_rgb(client, job, index)])


def all_frames_hsv(client, job):
    return [tiles_hsv(client, job, i) for i in range(job["frame_count"])]


def distance_to_levels(values, step, scale):
    levels = np.arange(0, scale + 1, step) / scale
    return np.abs(np.asarray(values)[:, None] - levels[None, :]).min(axis=1)


FIELDS = [
    ("hue_step", [12, 36, 90, 180], "hue", "12, 36, 90, 180"),
    ("saturation_step", [5, 10, 20, 50], "saturation", "5, 10, 20, 50"),
    ("brightness_step", [5, 10, 20, 50], "brightness", "5, 10, 20, 50"),
]


@pytest.mark.parametrize("field, allowed, label, listing", FIELDS)
def test_every_allowed_value_is_accepted_and_echoed(client, field, allowed, label, listing):
    data = chord_wav(1)
    for step in allowed:
        for text in (str(step), f"{step}.0"):
            r = post_steps(client, data, **{field: text})
            assert r.status_code == 200, r.text
            assert r.json()[field] == step


@pytest.mark.parametrize("field, allowed, label, listing", FIELDS)
@pytest.mark.parametrize("text", ["N/A", "n/a", " N/A ", "N/a"])
def test_na_in_any_case_means_no_rounding(client, field, allowed, label, listing, text):
    r = post_steps(client, chord_wav(1), **{field: text})
    assert r.status_code == 200, r.text
    assert r.json()[field] is None


def test_without_the_fields_every_step_is_null_and_the_frames_equal_those_with_na(client):
    data = chord_wav(1)
    missing = post_steps(client, data).json()
    explicit = post_steps(client, data, hue_step="N/A", saturation_step="N/A", brightness_step="N/A").json()
    for key in ("hue_step", "saturation_step", "brightness_step"):
        assert missing[key] is None and explicit[key] is None
    for i in range(missing["frame_count"]):
        a = client.get(missing["frame_url_template"].replace("{index}", str(i))).content
        b = client.get(explicit["frame_url_template"].replace("{index}", str(i))).content
        assert a == b


def test_the_response_carries_all_three_values_used(client):
    job = post_steps(client, chord_wav(1), hue_step="90", saturation_step="20", brightness_step="N/A").json()
    assert (job["hue_step"], job["saturation_step"], job["brightness_step"]) == (90, 20, None)


@pytest.mark.parametrize("field, allowed, label, listing", FIELDS)
@pytest.mark.parametrize("text", ["", "0", "-12", "7", "51", "2.5", "abc", "nan", "inf", "12 36"])
def test_anything_else_is_refused_with_the_allowed_choices(client, field, allowed, label, listing, text):
    if text in {str(a) for a in allowed}:
        pytest.skip("allowed for this field")
    before = leftovers()
    r = post_steps(client, chord_wav(1), **{field: text})
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == f"The {label} step must be N/A or one of {listing}."
    assert leftovers() == before  # no job was created


def test_values_from_the_other_list_are_refused(client):
    assert post_steps(client, chord_wav(1), saturation_step="90").status_code == 400
    assert post_steps(client, chord_wav(1), brightness_step="180").status_code == 400
    assert post_steps(client, chord_wav(1), hue_step="5").status_code == 400
    assert post_steps(client, chord_wav(1), hue_step="50").status_code == 400


def test_a_bad_step_is_refused_before_the_file_is_read(client):
    r = client.post(
        "/api/jobs",
        files={"file": ("song.wav", b"this is not audio", "audio/wav")},
        data={"window_size": "4096", "frame_rate": "10", "hue_step": "7"},
    )
    assert r.status_code == 400
    assert "hue step" in r.json()["detail"]


def test_a_saturation_step_gives_only_those_saturations(client):
    job = post_steps(client, saturation_step="20").json()
    seen = set()
    for hsv in all_frames_hsv(client, job):
        bright = hsv[:, 2] > 0.4
        assert (distance_to_levels(hsv[bright, 1], 20, 100) < HSV_TOLERANCE).all()
        seen |= set(np.round(hsv[bright, 1] * 5).astype(int))
    assert len(seen) >= 3  # several of the six levels really occur


def test_a_brightness_step_gives_only_those_frame_brightnesses(client):
    job = post_steps(client, brightness_step="50").json()
    values = []
    for i in range(job["frame_count"]):
        top = frame_rgb(client, job, i).max(axis=1)
        assert (top == top[0]).all()
        values.append(int(top[0]))
    assert set(values) <= {0, 128, 255}
    assert 255 in values  # the loudest frame is at full brightness


def test_the_largest_hue_step_gives_only_red_and_cyan(client):
    job = post_steps(client, hue_step="180").json()
    seen = 0
    for hsv in all_frames_hsv(client, job):
        good = (hsv[:, 1] > 0.3) & (hsv[:, 2] > 0.4)
        degrees = hsv[good, 0] * 360
        assert (np.minimum(np.abs(degrees - 180), np.minimum(degrees, 360 - degrees)) < 3).all()
        seen += int(good.sum())
    assert seen > 10


def test_the_same_request_twice_gives_identical_frames(client):
    data = chord_wav(1)
    fields = {"hue_step": "36", "saturation_step": "10", "brightness_step": "20", "smoothing": "0.4"}
    a = post_steps(client, data, **fields).json()
    b = post_steps(client, data, **fields).json()
    for i in range(a["frame_count"]):
        first = client.get(a["frame_url_template"].replace("{index}", str(i))).content
        second = client.get(b["frame_url_template"].replace("{index}", str(i))).content
        assert first == second


def chord_audio(seconds=3):
    t = np.arange(seconds * SR) / SR
    audio = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((220, 0.5), (277.18, 0.35), (329.63, 0.3), (440, 0.2)))
    audio = audio * np.interp(t, [0, 1, 2, 3], [1.0, 0.3, 0.9, 0.05])
    return 0.8 * audio / np.abs(audio).max()


def test_smoothing_and_two_steps_give_only_the_levels_and_silence_at_the_end_changes_nothing(client):
    audio = chord_audio(3)
    fields = {"smoothing": "0.8", "saturation_step": "50", "brightness_step": "50"}
    short = post_steps(client, wav_bytes(audio), **fields).json()
    longer = post_steps(client, wav_bytes(np.concatenate([audio, np.zeros(SR)])), **fields).json()
    assert longer["frame_count"] == short["frame_count"] + 10

    for i in range(short["frame_count"]):
        hsv = tiles_hsv(client, short, i)
        assert round(float(hsv[:, 2].max()) * 255) in (0, 128, 255)
        bright = hsv[:, 2] > 0.4
        assert (distance_to_levels(hsv[bright, 1], 50, 100) < HSV_TOLERANCE).all()

    # Silence at the end changes no earlier frame, except the last one, whose analysis window the end of the file
    # cuts short. That already happens without any step, so the steps must add no difference of their own.
    def differing(first, second):
        return [
            i
            for i in range(first["frame_count"])
            if client.get(first["frame_url_template"].replace("{index}", str(i))).content
            != client.get(second["frame_url_template"].replace("{index}", str(i))).content
        ]

    plain_short = post_steps(client, wav_bytes(audio), smoothing="0.8").json()
    plain_longer = post_steps(client, wav_bytes(np.concatenate([audio, np.zeros(SR)])), smoothing="0.8").json()
    # the steps add no difference of their own (they can only round one away)
    assert set(differing(short, longer)) <= set(differing(plain_short, plain_longer))
    assert all(i == short["frame_count"] - 1 for i in differing(short, longer))
