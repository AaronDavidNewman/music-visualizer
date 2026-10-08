"""Energy through the job endpoint: the brightness of each frame, the optional ``energy`` field, and robustness.

A frame's brightness (the largest channel of every tile) follows the overall energy of the audio in that frame,
relative to the loudest frame; a tile's saturation is its own note level.
"""

import colorsys

import numpy as np
import pytest

from app.config import settings

from .test_jobs_api import SR, client, expected_values, frame_rgb, post, wav_bytes  # noqa: F401

LOUD_FRAME, QUIET_FRAME, SILENT_FRAME = 15, 45, 75  # one-second stretches at 30 fps


def three_stretches(seed=1):
    """Mono noise at amplitude 0.8, then 0.2 (a quarter of the spread), then silence, one second each."""
    rng = np.random.default_rng(seed)
    return np.concatenate([rng.uniform(-0.8, 0.8, SR), rng.uniform(-0.2, 0.2, SR), np.zeros(SR)])


def frame_brightness(client, job, index):
    """The brightness of a served frame, 0 to 1, read from the pixels; every tile of a frame has the same one."""
    top = frame_rgb(client, job, index).max(axis=1)
    assert (top == top[0]).all(), "every tile of a frame must have the frame's brightness"
    return int(top[0]) / 255


def test_loud_quiet_and_silent_stretches_have_brightness_full_one_quarter_and_none(client):
    data = wav_bytes(three_stretches())
    job = post(client, data).json()
    expected = expected_values(data)
    assert expected[LOUD_FRAME] == pytest.approx(1.0, abs=0.05)
    assert expected[QUIET_FRAME] == pytest.approx(0.25, abs=0.05)
    assert expected[SILENT_FRAME] == 0.0

    assert frame_brightness(client, job, LOUD_FRAME) == pytest.approx(expected[LOUD_FRAME], abs=0.01)
    assert frame_brightness(client, job, LOUD_FRAME) > 0.95
    assert frame_brightness(client, job, QUIET_FRAME) == pytest.approx(expected[QUIET_FRAME], abs=0.01)
    assert frame_brightness(client, job, QUIET_FRAME) == pytest.approx(0.25, abs=0.06)
    assert not frame_rgb(client, job, SILENT_FRAME).any()  # silence is black


def test_the_loudest_frame_of_every_file_is_at_full_brightness(client):
    for seed, scale in ((2, 1.0), (3, 0.05)):  # the peak is relative, so a very quiet file is just as bright
        data = wav_bytes(three_stretches(seed) * scale)
        job = post(client, data).json()
        loudest = int(expected_values(data).argmax())
        assert frame_brightness(client, job, loudest) == 1.0, (seed, loudest)


def test_saturation_is_local_to_the_tile_while_brightness_is_the_frames(client):
    data = wav_bytes(three_stretches())
    job = post(client, data).json()
    rgb = frame_rgb(client, job, LOUD_FRAME)
    saturation = [(int(c.max()) - int(c.min())) / max(int(c.max()), 1) for c in rgb]
    assert max(saturation) > 0.5  # a tile with a strong level is strongly coloured
    assert min(saturation) < max(saturation)  # the tiles differ in saturation...
    assert (rgb.max(axis=1) == rgb.max()).all()  # ...but not in brightness


def test_the_same_file_gives_identical_frames(client):
    data = wav_bytes(three_stretches())
    a = post(client, data).json()
    b = post(client, data).json()
    for index in (0, LOUD_FRAME, QUIET_FRAME, SILENT_FRAME):
        ra = client.get(a["frame_url_template"].replace("{index}", str(index))).content
        rb = client.get(b["frame_url_template"].replace("{index}", str(index))).content
        assert ra == rb, index


def test_a_silent_file_creates_frames_and_is_entirely_black(client):
    r = post(client, wav_bytes(np.zeros(SR), np.zeros(SR)))
    assert r.status_code == 200
    job = r.json()
    for index in (0, 15, 29):
        assert not frame_rgb(client, job, index).any()


# --- the optional "energy" form field --------------------------------------------------------------------------------

ENERGY_MESSAGE = "The energy must be a whole number from 1 to 8."


def job_dirs():
    return [p for root in (settings.audio_temp_dir, settings.frames_temp_dir) if root.exists() for p in root.iterdir()]


def test_energy_defaults_to_one_and_is_reported(client):
    job = post(client, wav_bytes(three_stretches())).json()
    assert job["energy"] == 1


@pytest.mark.parametrize("value, expected", [("1", 1), ("2", 2), ("3", 3), ("8", 8), ("2.0", 2), (" 4 ", 4)])
def test_a_whole_number_from_1_to_8_is_accepted_and_reported(client, value, expected):
    r = post(client, wav_bytes(three_stretches()), energy=value)
    assert r.status_code == 200, r.text
    assert r.json()["energy"] == expected


@pytest.mark.parametrize("root, quiet", [(1, 0.25), (2, 0.5), (3, 0.63), (8, 0.84)])
def test_the_root_lifts_the_quiet_frame_and_leaves_the_loud_and_silent_ones(client, root, quiet):
    data = wav_bytes(three_stretches())
    job = post(client, data, energy=str(root)).json()
    expected = expected_values(data, root=root)
    assert frame_brightness(client, job, LOUD_FRAME) > 0.95
    assert frame_brightness(client, job, QUIET_FRAME) == pytest.approx(expected[QUIET_FRAME], abs=0.01)
    assert frame_brightness(client, job, QUIET_FRAME) == pytest.approx(quiet, abs=0.07)
    assert not frame_rgb(client, job, SILENT_FRAME).any()


@pytest.mark.parametrize("value", ["0", "9", "2.5", "abc", "-1", "nan", "inf", "-inf", "1e1", ""])
def test_a_bad_energy_is_refused_and_no_job_is_created(client, value):
    r = post(client, wav_bytes(three_stretches()), energy=value)
    assert r.status_code == 400
    assert r.json()["detail"] == ENERGY_MESSAGE
    assert job_dirs() == []


def test_a_bad_energy_is_refused_even_without_a_file(client):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "30", "energy": "9"})
    assert r.status_code == 400
    assert r.json()["detail"] == ENERGY_MESSAGE


def test_changing_only_the_energy_changes_only_the_brightness(client):
    data = wav_bytes(three_stretches())
    one = post(client, data, energy="1").json()
    eight = post(client, data, energy="8").json()
    rgb1, rgb8 = frame_rgb(client, one, QUIET_FRAME), frame_rgb(client, eight, QUIET_FRAME)
    assert rgb8.max() > rgb1.max()  # the quiet frame is brighter at root 8
    for n in np.flatnonzero(rgb1.max(axis=1) >= 60):
        h1, s1, _ = colorsys.rgb_to_hsv(*(rgb1[n] / 255))
        h8, s8, _ = colorsys.rgb_to_hsv(*(rgb8[n] / 255))
        assert s1 == pytest.approx(s8, abs=0.03), n  # a tile's saturation (its own level) does not change
        if s1 > 0.5:
            assert min(abs(h1 - h8), 1 - abs(h1 - h8)) < 0.02, n


def test_the_other_response_fields_are_unchanged(client):
    job = post(client, wav_bytes(three_stretches())).json()
    assert set(job) == {
        "job_id", "file_name", "sample_rate", "duration_seconds", "window_size", "frame_rate", "frame_count",
        "brightness", "smoothing", "energy", "window_spacing", "step_samples", "window_count", "spacing_raised",
        "frame_url_template", "hue_step", "saturation_step", "brightness_step",
    }  # fmt: skip


# --- robustness: short final frames, other sample rates, mono and stereo ---------------------------------------------


def test_a_short_final_frame_creates_all_frames_without_error(client):
    rng = np.random.default_rng(31)
    audio = rng.uniform(-0.5, 0.5, SR + 44)  # 1.001 s: the last of 31 frames holds 44 samples
    r = post(client, wav_bytes(audio))
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["frame_count"] == 31
    frame_rgb(client, job, 30)  # the short last frame is served


def test_a_final_frame_with_a_single_sample_creates_frames_without_error(client):
    audio = np.random.default_rng(32).uniform(-0.5, 0.5, SR + 1)
    r = post(client, wav_bytes(audio))
    assert r.status_code == 200, r.text
    assert r.json()["frame_count"] == 31


@pytest.mark.parametrize("rate", [22050, 48000])
def test_other_sample_rates_create_frames_and_keep_the_brightness_rule(client, rate):
    rng = np.random.default_rng(33)
    audio = np.concatenate([rng.uniform(-0.8, 0.8, rate), rng.uniform(-0.2, 0.2, rate), np.zeros(rate)])
    data = wav_bytes(audio, sample_rate=rate)
    job = post(client, data).json()
    assert job["sample_rate"] == rate
    expected = expected_values(data)
    assert frame_brightness(client, job, LOUD_FRAME) == pytest.approx(expected[LOUD_FRAME], abs=0.01)
    assert frame_brightness(client, job, LOUD_FRAME) > 0.95
    assert frame_brightness(client, job, QUIET_FRAME) == pytest.approx(expected[QUIET_FRAME], abs=0.01)
    assert frame_brightness(client, job, QUIET_FRAME) == pytest.approx(0.25, abs=0.06)
    assert not frame_rgb(client, job, SILENT_FRAME).any()


def test_a_mono_file_and_the_same_signal_in_both_channels_give_identical_frames(client):
    audio = three_stretches(34)
    mono = post(client, wav_bytes(audio)).json()
    stereo = post(client, wav_bytes(audio, audio)).json()
    for index in (0, LOUD_FRAME, QUIET_FRAME, SILENT_FRAME):
        a = client.get(mono["frame_url_template"].replace("{index}", str(index))).content
        b = client.get(stereo["frame_url_template"].replace("{index}", str(index))).content
        assert a == b, index
