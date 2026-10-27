"""The beat coloring through the job endpoint (feature 024): ``beat_coloring``, ``peak_distance`` and ``peak_prominence``.

How the colors are worked out is tested on plain arrays in ``test_peak_tile_colors.py``, ``test_colormaps.py`` and
``test_local_peaks.py``; this module is about the endpoint: the three fields, their refusals, the response, that the beat is
measured only when it is used, and the frames that are served.
"""

import numpy as np
import pytest

import app.routers.jobs as jobs
from app.services.colormaps import COLORMAPS, lookup_table

from .colormap_names import DECODABLE
from .frame_size import HEIGHT, WIDTH, tile_center
from .test_jobs_api import SR, client, leftovers, note_tone, wav_bytes  # noqa: F401
from .test_resolution_api import frame_bytes, picture, tiny

BEAT_MESSAGE = "The beat coloring must be true or false."
DISTANCE_MESSAGE = "The minimum distance must be a number from 100 to 2000 milliseconds."
PROMINENCE_MESSAGE = "The prominence must be a number from 0 to 100 percent."
TONE_NOTE = 36
COLORMAP = DECODABLE[0]  # every row of this colormap is different, so the row of a color can be read back
ROWS = {tuple(row): i for i, row in enumerate(lookup_table(COLORMAP).tolist())}


def post(client, data=None, **fields):
    form = {"window_size": "4096", "frame_rate": "10", "colormap": COLORMAP, **fields}
    return client.post("/api/jobs", files={"file": ("song.wav", data or pulse_wav(), "audio/wav")}, data=form)


def pulse_wav(seconds=7.0, period=0.5, first=1.0, strengths=(0.8, 0.5)):
    """A steady tone with a short click every ``period`` seconds from ``first``, alternately loud and soft."""
    audio = 0.15 * note_tone(TONE_NOTE, seconds)
    t = first
    n = 0
    while t < seconds - 0.1:
        start = int(round(t * SR))
        audio[start : start + 16] += strengths[n % len(strengths)] * np.where(np.arange(16) % 2 == 0, 1.0, -1.0)
        t += period
        n += 1
    return wav_bytes(np.clip(audio, -0.99, 0.99))


def strong_row(client, job, index):
    """The colormap row of the tile of the steady tone in a served frame."""
    pixel = picture(client, job, index)[tile_center(TONE_NOTE)]
    return ROWS[tuple(int(v) for v in pixel)]


def all_frames(client, job):
    return [frame_bytes(client, job, i) for i in range(job["frame_count"])]


# --- the fields ----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", ["tiles", "blended", "contour", "circles", "circles_paint"])
def test_the_defaults_are_off_100_and_50_and_are_reported_for_every_image_type(client, image_type):
    r = post(client, tiny(), image_type=image_type)
    assert r.status_code == 200, r.text
    job = r.json()
    assert (job["beat_coloring"], job["peak_distance"], job["peak_prominence"]) == (False, 100, 50)


@pytest.mark.parametrize("text, expected", [("true", True), ("false", False), ("1", True), ("0", False), ("TRUE", True), (" False ", False), ("True", True)])
def test_beat_coloring_accepts_true_false_1_and_0_in_any_case(client, text, expected):
    r = post(client, tiny(), image_type="tiles", beat_coloring=text)
    assert r.status_code == 200, r.text
    assert r.json()["beat_coloring"] is expected


@pytest.mark.parametrize("text", ["", "maybe", "yes", "no", "2", "-1", "on", "t", "1.0"])
def test_beat_coloring_that_is_not_true_false_1_or_0_is_refused_with_nothing_created(client, text):
    r = post(client, tiny(), beat_coloring=text)
    assert r.status_code == 400 and r.json()["detail"] == BEAT_MESSAGE
    assert leftovers() == []


@pytest.mark.parametrize("text, expected", [("100", 100), ("2000", 2000), ("100.5", 100.5), ("750", 750), ("1999.9", 1999.9)])
def test_peak_distance_accepts_100_to_2000_and_the_response_has_it(client, text, expected):
    r = post(client, tiny(), peak_distance=text)
    assert r.status_code == 200, r.text
    assert r.json()["peak_distance"] == expected


@pytest.mark.parametrize("text", ["99.9", "0", "-100", "2000.1", "5000", "", "abc", "nan", "inf", "-inf", "1e9", "100 ms"])
def test_peak_distance_outside_the_range_or_not_a_number_is_refused_with_nothing_created(client, text):
    r = post(client, tiny(), peak_distance=text)
    assert r.status_code == 400 and r.json()["detail"] == DISTANCE_MESSAGE
    assert leftovers() == []


@pytest.mark.parametrize("text, expected", [("0", 0), ("100", 100), ("50.5", 50.5), ("1", 1), ("99.9", 99.9)])
def test_peak_prominence_accepts_0_to_100_and_the_response_has_it(client, text, expected):
    r = post(client, tiny(), peak_prominence=text)
    assert r.status_code == 200, r.text
    assert r.json()["peak_prominence"] == expected


@pytest.mark.parametrize("text", ["-0.1", "-1", "100.1", "101", "", "abc", "nan", "inf", "50%"])
def test_peak_prominence_outside_the_range_or_not_a_number_is_refused_with_nothing_created(client, text):
    r = post(client, tiny(), peak_prominence=text)
    assert r.status_code == 400 and r.json()["detail"] == PROMINENCE_MESSAGE
    assert leftovers() == []


@pytest.mark.parametrize("box", ["true", "false"])
@pytest.mark.parametrize("image_type", ["tiles", "contour"])
def test_the_two_settings_are_checked_before_the_file_is_read_whether_the_box_is_on_or_off(client, box, image_type):
    for fields, message in (({"peak_distance": "50"}, DISTANCE_MESSAGE), ({"peak_prominence": "101"}, PROMINENCE_MESSAGE), ({"beat_coloring": "maybe"}, BEAT_MESSAGE)):
        r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "beat_coloring": box, "image_type": image_type, **fields})  # no file at all
        assert r.status_code == 400 and r.json()["detail"] == message
        assert leftovers() == []


def test_the_response_keeps_the_values_that_were_sent(client):
    job = post(client, tiny(), image_type="blended", beat_coloring="true", peak_distance="450", peak_prominence="25").json()
    assert (job["beat_coloring"], job["peak_distance"], job["peak_prominence"]) == (True, 450, 25)


# --- the frames ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", ["tiles", "blended"])
def test_with_the_box_off_the_frames_are_those_of_a_job_that_sends_none_of_the_fields(client, image_type):
    audio = pulse_wav()
    plain = post(client, audio, image_type=image_type).json()
    off = post(client, audio, image_type=image_type, beat_coloring="false", peak_distance="1500", peak_prominence="5").json()
    assert all_frames(client, plain) == all_frames(client, off)
    assert off["frame_count"] == plain["frame_count"]


@pytest.mark.parametrize("image_type", ["tiles", "blended"])
def test_with_the_box_on_the_tiles_follow_the_strength_of_the_beats(client, image_type):
    audio = pulse_wav()
    job = post(client, audio, image_type=image_type, beat_coloring="true").json()
    rows = [strong_row(client, job, i) for i in range(job["frame_count"])]
    before = rows[:9]  # frames before the first click (1.0 s): the position in the peak is 0, so about the middle of the colormap
    assert all(abs(r - 128) <= 16 for r in before), before
    loud = rows[10]  # the frame of the first, loud click
    soft = rows[15]  # the frame of the second, soft click
    assert loud >= 235, rows
    assert 150 < soft < loud - 30, rows
    plain = post(client, audio, image_type=image_type).json()
    assert all_frames(client, plain) != all_frames(client, job)
    assert all(strong_row(client, plain, i) >= 235 for i in range(plain["frame_count"]))  # 100 % harmonic: the steady tone is the strongest tile


def test_the_minimum_distance_and_the_prominence_change_the_beat_that_is_found(client):
    audio = pulse_wav()
    default = all_frames(client, post(client, audio, image_type="tiles", beat_coloring="true").json())
    far = all_frames(client, post(client, audio, image_type="tiles", beat_coloring="true", peak_distance="2000").json())
    high = all_frames(client, post(client, audio, image_type="tiles", beat_coloring="true", peak_prominence="95").json())
    assert far != default and high != default


@pytest.mark.parametrize("image_type", ["contour", "circles", "circles_paint"])
def test_the_other_image_types_are_the_same_with_the_box_on(client, image_type):
    audio = pulse_wav(seconds=3.0)
    without = post(client, audio, image_type=image_type).json()
    with_box = post(client, audio, image_type=image_type, beat_coloring="true", peak_distance="700", peak_prominence="20").json()
    assert all_frames(client, without) == all_frames(client, with_box)
    assert with_box["beat_coloring"] is True


def test_the_frames_keep_their_size_and_count_with_the_box_on(client):
    audio = pulse_wav(seconds=3.0)
    plain = post(client, audio, image_type="tiles").json()
    job = post(client, audio, image_type="tiles", beat_coloring="true").json()
    assert job["frame_count"] == plain["frame_count"]
    assert picture(client, job, 0).shape == (HEIGHT, WIDTH, 3)


# --- the beat is measured only when it is used ------------------------------------------------------------------------------


@pytest.fixture
def measured(monkeypatch):
    calls = []
    real = jobs.measure_local_peaks

    def spy(left, right, file_rate, min_distance, prominence, *args, **kwargs):
        calls.append((len(left), file_rate, min_distance, prominence))
        return real(left, right, file_rate, min_distance, prominence, *args, **kwargs)

    monkeypatch.setattr(jobs, "measure_local_peaks", spy)
    return calls


@pytest.mark.parametrize("image_type", ["tiles", "blended"])
def test_the_beat_is_measured_once_with_the_two_settings_when_the_box_is_on(client, measured, image_type):
    post(client, tiny(), image_type=image_type, beat_coloring="true", peak_distance="300", peak_prominence="20")
    assert measured == [(22050, SR, 300.0, 20.0)]


@pytest.mark.parametrize("image_type", ["tiles", "blended"])
def test_the_beat_is_not_measured_when_the_box_is_off(client, measured, image_type):
    post(client, tiny(), image_type=image_type, beat_coloring="false", peak_distance="300")
    post(client, tiny(), image_type=image_type)
    assert measured == []


@pytest.mark.parametrize("image_type", ["contour", "circles", "circles_paint"])
def test_the_beat_is_not_measured_for_the_other_image_types(client, measured, image_type):
    post(client, tiny(), image_type=image_type, beat_coloring="true")
    assert measured == []


def test_a_bad_setting_stops_the_job_before_the_beat_is_measured(client, measured):
    post(client, tiny(), image_type="tiles", beat_coloring="true", peak_distance="5")
    assert measured == []
    assert leftovers() == []


# --- the corners: no beat, silence, hidden tiles, short files (Story 3) --------------------------------------------------------


@pytest.mark.parametrize("image_type", ["tiles", "blended"])
def test_a_silent_file_makes_the_same_frames_with_the_box_on_and_off(client, image_type):
    off = post(client, tiny(), image_type=image_type).json()
    on = post(client, tiny(), image_type=image_type, beat_coloring="true").json()
    assert on["frame_count"] == off["frame_count"] > 0
    assert all_frames(client, on) == all_frames(client, off)  # no peaks: the position is 0 and a silent tile is at row 0 either way
    assert picture(client, on, 0).shape == (HEIGHT, WIDTH, 3)


def test_a_file_in_which_no_beat_is_found_has_no_tile_past_the_middle_of_the_colormap(client):
    # a prominence of 100 % is reached only by a peak that stands on exact silence, so a steady tone has no peak at all
    audio = wav_bytes(0.5 * note_tone(TONE_NOTE, 4.0))
    job = post(client, audio, image_type="tiles", beat_coloring="true", peak_prominence="100").json()
    off = post(client, audio, image_type="tiles").json()
    for index in range(job["frame_count"]):
        colours = np.unique(picture(client, job, index).reshape(-1, 3), axis=0)
        assert max(ROWS[tuple(int(v) for v in c)] for c in colours) <= 128, index
    # while the box off leaves the steady tone at the last color
    assert max(ROWS[tuple(int(v) for v in c)] for c in np.unique(picture(client, off, 5).reshape(-1, 3), axis=0)) == 255


def test_after_the_last_click_the_position_is_held(client):
    job = post(client, pulse_wav(), image_type="tiles", beat_coloring="true").json()
    rows = [strong_row(client, job, i) for i in range(job["frame_count"])]
    last_click_frame = 65  # the last click is at 6.5 s, ten frames a second
    assert len(set(rows[last_click_frame:])) == 1, rows[last_click_frame:]


@pytest.mark.parametrize("image_type, hidden", [("tiles", (0, 0, 0)), ("blended", None)])
def test_tiles_hidden_by_the_threshold_are_drawn_as_before_in_every_frame(client, image_type, hidden):
    job = post(client, pulse_wav(), image_type=image_type, beat_coloring="true", threshold="10").json()
    expected = hidden if hidden is not None else tuple(int(v) for v in lookup_table(COLORMAP)[128])
    for index in range(0, job["frame_count"], 7):
        assert tuple(int(v) for v in picture(client, job, index)[tile_center(0)]) == expected, index


@pytest.mark.parametrize("image_type", ["tiles", "blended"])
def test_a_file_shorter_than_the_peaks_window_makes_frames_with_the_box_on(client, image_type):
    short = wav_bytes(np.clip(0.15 * note_tone(TONE_NOTE, 0.4), -0.9, 0.9))
    job = post(client, short, image_type=image_type, beat_coloring="true").json()
    assert job["frame_count"] >= 1
    assert picture(client, job, 0).shape == (HEIGHT, WIDTH, 3)


def test_mono_and_stereo_copies_of_the_same_sound_make_the_same_frames(client):
    audio = np.clip(0.15 * note_tone(TONE_NOTE, 4.0), -0.9, 0.9)
    audio[SR : SR + 16] += 0.7 * np.where(np.arange(16) % 2 == 0, 1.0, -1.0)
    audio[2 * SR : 2 * SR + 16] += 0.4 * np.where(np.arange(16) % 2 == 0, 1.0, -1.0)
    mono = post(client, wav_bytes(np.clip(audio, -0.99, 0.99)), image_type="tiles", beat_coloring="true").json()
    stereo = post(client, wav_bytes(np.clip(audio, -0.99, 0.99), np.clip(audio, -0.99, 0.99)), image_type="tiles", beat_coloring="true").json()
    assert all_frames(client, mono) == all_frames(client, stereo)
