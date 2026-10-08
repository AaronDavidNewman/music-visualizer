"""The note threshold through the job endpoint: the optional ``threshold`` field (0 to 10, percent of the largest note
value), its refusals, the response, and the frames.
"""

import math

import numpy as np
import pytest

from app.services.frame_rendering import average_frames
from app.services.note_analysis import NoteBinAnalyzer, analyze_channels
from app.services.window_spacing import default_spacing, resolve_step

from .test_jobs_api import SR, client, frame_rgb, leftovers, wav_bytes  # noqa: F401

FPS = 10
LOUD_NOTE, FAINT_NOTE = 36, 43  # about 440 Hz and 659 Hz
WINDOW = 4096
MID_FRAME = 10


def bin_centre_hz(note):
    """The frequency in the middle of the FFT bin that the analysis reads for this note, so that a tone of that
    frequency is measured at its full, exactly proportional, value (a tone between bins would be measured low)."""
    return NoteBinAnalyzer(SR, WINDOW).bin_indices[note] * SR / WINDOW


def two_tones(seconds=2, loud=0.8, faint=0.04):
    t = np.arange(seconds * SR) / SR
    return loud * np.sin(2 * np.pi * bin_centre_hz(LOUD_NOTE) * t) + faint * np.sin(
        2 * np.pi * bin_centre_hz(FAINT_NOTE) * t
    )


def post_threshold(client, data, **fields):
    form = {"window_size": str(WINDOW), "frame_rate": str(FPS), **fields}
    return client.post("/api/jobs", files={"file": ("song.wav", data, "audio/wav")}, data=form)


def faint_share(audio):
    """The faint note's value in the middle of the file as a percentage of the file's largest note value."""
    spacing = default_spacing(SR, FPS, WINDOW)
    _, step, _ = resolve_step(spacing, WINDOW)
    result = analyze_channels(audio, audio, SR, WINDOW, step=step)
    frames = average_frames(result, FPS, math.ceil(len(audio) / SR * FPS))
    return 100.0 * frames[MID_FRAME, FAINT_NOTE] / frames.max()


def tiles(client, job, index=MID_FRAME):
    return frame_rgb(client, job, index)


def is_black(rgb):
    return not np.asarray(rgb).any()


@pytest.mark.parametrize("text, echoed", [("0", 0), ("1", 1), ("5", 5), ("10", 10), ("2.5", 2.5), ("5.0", 5), (" 4 ", 4)])
def test_accepted_values_are_echoed(client, text, echoed):
    r = post_threshold(client, wav_bytes(two_tones(1)), threshold=text)
    assert r.status_code == 200, r.text
    assert r.json()["threshold"] == echoed
    assert type(r.json()["threshold"]) is type(echoed)  # whole numbers come back as integers


def test_without_the_field_the_threshold_is_zero_and_the_frames_equal_those_sent_with_zero(client):
    data = wav_bytes(two_tones(1))
    missing = post_threshold(client, data).json()
    zero = post_threshold(client, data, threshold="0").json()
    assert missing["threshold"] == 0 and zero["threshold"] == 0
    for i in range(missing["frame_count"]):
        a = client.get(missing["frame_url_template"].replace("{index}", str(i))).content
        b = client.get(zero["frame_url_template"].replace("{index}", str(i))).content
        assert a == b


@pytest.mark.parametrize("text", ["", " ", "-1", "-0.5", "10.1", "11", "50", "100", "abc", "nan", "inf", "-inf", "1e9", "5%"])
def test_anything_else_is_refused_with_the_range(client, text):
    before = leftovers()
    r = post_threshold(client, wav_bytes(two_tones(1)), threshold=text)
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == "The threshold must be a number from 0 to 10."
    assert leftovers() == before  # no job was created


def test_a_bad_threshold_is_refused_before_the_file_is_read(client):
    r = client.post(
        "/api/jobs",
        files={"file": ("song.wav", b"this is not audio", "audio/wav")},
        data={"window_size": "4096", "frame_rate": str(FPS), "threshold": "99"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "The threshold must be a number from 0 to 10."


def test_a_faint_tone_turns_black_above_its_share_and_the_loud_one_is_unchanged(client):
    audio = two_tones()
    data = wav_bytes(audio)
    share = faint_share(audio)
    assert 2 < share < 8, share  # the setup really has a faint note well below the loud one

    off = tiles(client, post_threshold(client, data, threshold="0").json())
    assert not is_black(off[LOUD_NOTE]) and not is_black(off[FAINT_NOTE])

    hiding = post_threshold(client, data, threshold=str(math.ceil(share) + 3)).json()
    got = tiles(client, hiding)
    assert is_black(got[FAINT_NOTE])
    assert got[LOUD_NOTE].tolist() == off[LOUD_NOTE].tolist()

    keeping = post_threshold(client, data, threshold=str(max(1, math.floor(share) - 3))).json()
    got = tiles(client, keeping)
    assert got[FAINT_NOTE].tolist() == off[FAINT_NOTE].tolist()
    assert got[LOUD_NOTE].tolist() == off[LOUD_NOTE].tolist()


@pytest.mark.parametrize("threshold", [1, 3, 6, 10])
def test_every_tile_is_black_or_exactly_the_tile_without_a_threshold(client, threshold):
    data = wav_bytes(two_tones())
    off = post_threshold(client, data, threshold="0").json()
    got = post_threshold(client, data, threshold=str(threshold)).json()
    for i in (MID_FRAME - 5, MID_FRAME, MID_FRAME + 5):
        a, b = tiles(client, off, i), tiles(client, got, i)
        black = ~b.any(axis=1)
        assert (a[~black] == b[~black]).all(), (threshold, i)
        assert not black[LOUD_NOTE], (threshold, i)  # the loudest note is never hidden


def test_the_same_request_twice_gives_identical_frames(client):
    data = wav_bytes(two_tones(1))
    a = post_threshold(client, data, threshold="6", smoothing="0.4").json()
    b = post_threshold(client, data, threshold="6", smoothing="0.4").json()
    for i in range(a["frame_count"]):
        first = client.get(a["frame_url_template"].replace("{index}", str(i))).content
        second = client.get(b["frame_url_template"].replace("{index}", str(i))).content
        assert first == second


def test_the_hidden_set_does_not_depend_on_the_saturation_root_and_other_settings_leave_the_rest_alone(client):
    data = wav_bytes(two_tones())
    settings = dict(smoothing="0.8", saturation_step="20", brightness_step="50")
    off = post_threshold(client, data, threshold="0", **settings).json()
    on = post_threshold(client, data, threshold="6", **settings).json()
    for i in (MID_FRAME - 4, MID_FRAME, MID_FRAME + 4):
        a, b = tiles(client, off, i), tiles(client, on, i)
        black = ~b.any(axis=1)
        assert (a[~black] == b[~black]).all(), i  # every tile is black or the tile without the threshold

    # the Saturation root (the API's brightness field) changes how strongly tiles are coloured, not which are hidden
    low = post_threshold(client, data, threshold="6", brightness="2").json()
    high = post_threshold(client, data, threshold="6", brightness="100").json()
    for i in (MID_FRAME - 4, MID_FRAME, MID_FRAME + 4):
        assert (~tiles(client, low, i).any(axis=1) == ~tiles(client, high, i).any(axis=1)).all(), i
