"""The note threshold through the job endpoint: the optional ``threshold`` field (0 to 10, percent of the largest note
value), its refusals, the response, and the frames.
"""


import numpy as np
import pytest

from app.services.note_analysis import NoteBinAnalyzer

from .colormap_names import WITHOUT_BLACK
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


def tiles(client, job, index=MID_FRAME):
    return frame_rgb(client, job, index)


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


def test_the_hidden_set_does_not_depend_on_the_colormap_and_the_rest_stays_as_it_was(client):
    data = wav_bytes(two_tones())
    settings = dict(smoothing="0.8")
    off = post_threshold(client, data, threshold="0", **settings).json()
    on = post_threshold(client, data, threshold="6", **settings).json()
    for i in (MID_FRAME - 4, MID_FRAME, MID_FRAME + 4):
        a, b = tiles(client, off, i), tiles(client, on, i)
        black = ~b.any(axis=1)
        assert (a[~black] == b[~black]).all(), i  # every tile is black or the tile without the threshold

    # the colormap changes the colours of the tiles that are shown, not which tiles are hidden (black); the colormap
    # colormap with no black entry, where a black tile is always a hidden one (compared only if two such are offered)
    if len(WITHOUT_BLACK) >= 2:
        one = post_threshold(client, data, threshold="6", colormap=WITHOUT_BLACK[0]).json()
        two = post_threshold(client, data, threshold="6", colormap=WITHOUT_BLACK[1]).json()
        for i in (MID_FRAME - 4, MID_FRAME, MID_FRAME + 4):
            assert (~tiles(client, one, i).any(axis=1) == ~tiles(client, two, i).any(axis=1)).all(), i
