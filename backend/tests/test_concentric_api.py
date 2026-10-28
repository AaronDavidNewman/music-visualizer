"""The Concentric image type through the job endpoint (feature 025): ``image_type=concentric``.

How a frame is drawn is tested on its own in ``test_concentric.py``; this module is about the endpoint: choosing the type, which
settings apply and which are ignored, that the beat is always measured, and the frames that are served.
"""

import numpy as np
import pytest

import app.routers.jobs as jobs
from app.services.colormaps import COLORMAPS, lookup_table
from app.services.image_types import IMAGE_TYPES

from .frame_size import HEIGHT, WIDTH
from .test_concentric import MIDDLE_COLOR_ROW, flat_pixel
from .test_jobs_api import SR, client, leftovers, note_tone, wav_bytes  # noqa: F401
from .test_peak_tile_colors_api import COLORMAP, ROWS, TONE_NOTE, all_frames, post, pulse_wav
from .test_resolution_api import picture, tiny

TYPE_MESSAGE = f"The image type must be one of {', '.join(IMAGE_TYPES)}."
DISTANCE_MESSAGE = "The minimum distance must be a number from 100 to 2000 milliseconds."
PROMINENCE_MESSAGE = "The prominence must be a number from 0 to 100 percent."


def concentric(client, data=None, **fields):
    return post(client, data, image_type="concentric", **fields)


def ring_row(client, job, index, ring, note=TONE_NOTE):
    """The colormap row of ring ``ring`` of the circle of ``note`` in a served frame."""
    y, x = flat_pixel(note, ring)
    return ROWS[tuple(int(v) for v in picture(client, job, index)[y, x])]


# --- choosing it --------------------------------------------------------------------------------------------------------------


def test_concentric_is_the_sixth_image_type_and_the_message_lists_all_six():
    assert IMAGE_TYPES == ("tiles", "blended", "contour", "circles", "circles_paint", "concentric")
    assert TYPE_MESSAGE.endswith("circles_paint, concentric.")


@pytest.mark.parametrize("name", ["concentrics", "Concentric", "concentric ", "concentric_circles", ""])
def test_a_name_that_is_not_exactly_concentric_is_refused_with_the_six_names(client, name):
    r = post(client, tiny(), image_type=name)
    assert r.status_code == 400 and r.json()["detail"] == TYPE_MESSAGE
    assert leftovers() == []


@pytest.mark.parametrize("name", COLORMAPS)
def test_concentric_is_accepted_and_echoed_with_every_colormap_and_the_defaults(client, name):
    r = post(client, tiny(), image_type="concentric", colormap=name)
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["image_type"] == "concentric" and job["colormap"] == name
    assert (job["beat_coloring"], job["peak_distance"], job["peak_prominence"]) == (False, 100, 50)


def test_the_response_has_the_same_keys_as_for_the_other_types(client):
    keys = set(post(client, tiny(), image_type="tiles").json())
    assert set(concentric(client, tiny()).json()) == keys


def test_the_frames_are_600_by_400_rgb_pictures_and_their_count_is_that_of_the_other_types(client):
    audio = pulse_wav(seconds=3.0)
    job = concentric(client, audio).json()
    tiles = post(client, audio, image_type="tiles").json()
    assert job["frame_count"] == tiles["frame_count"] > 0
    assert picture(client, job, 0).shape == (HEIGHT, WIDTH, 3)
    assert picture(client, job, job["frame_count"] - 1).shape == (HEIGHT, WIDTH, 3)


# --- the beat is always measured -----------------------------------------------------------------------------------------------


@pytest.fixture
def measured(monkeypatch):
    calls = []
    real = jobs.measure_local_peaks

    def spy(left, right, file_rate, min_distance, prominence, *args, **kwargs):
        calls.append((len(left), file_rate, min_distance, prominence))
        return real(left, right, file_rate, min_distance, prominence, *args, **kwargs)

    monkeypatch.setattr(jobs, "measure_local_peaks", spy)
    return calls


@pytest.mark.parametrize("box", [None, "false", "true"])
def test_the_beat_is_measured_once_with_the_two_settings_whatever_the_checkbox_says(client, measured, box):
    fields = {"peak_distance": "300", "peak_prominence": "20"}
    if box is not None:
        fields["beat_coloring"] = box
    assert concentric(client, tiny(), **fields).status_code == 200
    assert measured == [(22050, SR, 300.0, 20.0)]


def test_the_checkbox_has_no_effect_on_the_frames_of_concentric(client):
    audio = pulse_wav(seconds=4.0)
    plain = all_frames(client, concentric(client, audio).json())
    assert all_frames(client, concentric(client, audio, beat_coloring="true").json()) == plain
    assert all_frames(client, concentric(client, audio, beat_coloring="false").json()) == plain
    assert concentric(client, audio, beat_coloring="true").json()["beat_coloring"] is True


@pytest.mark.parametrize("fields, message", [({"peak_distance": "50"}, DISTANCE_MESSAGE), ({"peak_distance": "abc"}, DISTANCE_MESSAGE), ({"peak_prominence": "101"}, PROMINENCE_MESSAGE), ({"peak_prominence": ""}, PROMINENCE_MESSAGE)])
def test_the_peak_settings_are_checked_before_the_file_is_read_with_nothing_created(client, measured, fields, message):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": "concentric", **fields})  # no file at all
    assert r.status_code == 400 and r.json()["detail"] == message
    assert concentric(client, tiny(), **fields).status_code == 400
    assert leftovers() == [] and measured == []


def test_the_minimum_distance_and_the_prominence_change_the_beat_that_colors_the_rings(client):
    audio = pulse_wav()
    default = all_frames(client, concentric(client, audio).json())
    far = all_frames(client, concentric(client, audio, peak_distance="2000").json())
    high = all_frames(client, concentric(client, audio, peak_prominence="95").json())
    assert far != default and high != default


# --- the picture ---------------------------------------------------------------------------------------------------------------


def test_the_rings_follow_the_beat_before_the_first_click_the_middle_and_at_a_loud_click_the_end_of_the_colormap(client):
    job = concentric(client, pulse_wav()).json()
    table = lookup_table(COLORMAP)
    before = ring_row(client, job, 3, 12)  # 0.35 s: no beat yet, position 0
    loud = ring_row(client, job, 10, 12)  # the first, loud click
    assert abs(before - 128) <= 2, before
    assert loud >= 235, loud
    assert ring_row(client, job, 10, 1) == 0 and ring_row(client, job, 3, 1) == 0  # the center is always the first color
    assert tuple(picture(client, job, 3)[0, 0]) == tuple(table[MIDDLE_COLOR_ROW])  # the background


def test_the_tone_is_the_biggest_circle_and_the_quiet_notes_are_dots(client):
    job = concentric(client, pulse_wav()).json()
    index = 20
    assert ring_row(client, job, index, 1) == 0 and ring_row(client, job, index, 12) > 0  # the tone has all twelve rings
    other = 0  # a note with no energy: one ring only
    y, x = flat_pixel(other, 1)
    assert ROWS[tuple(int(v) for v in picture(client, job, index)[y, x])] == 0
    y, x = flat_pixel(other, 2)
    assert tuple(picture(client, job, index)[y, x]) == tuple(lookup_table(COLORMAP)[MIDDLE_COLOR_ROW])


# --- the settings --------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fields",
    [{"threshold": "10"}, {"note_count": "12"}, {"resolution": "5"}, {"interpolate": "5"}, {"gaussian": "5"}, {"blend_width": "10"},
     {"circle_unit": "10", "circle_memory": "500", "circle_notes": "12", "circle_radius": "8", "circle_resize": "true"}],
)
def test_the_settings_of_the_other_pictures_are_accepted_and_ignored(client, fields):
    audio = pulse_wav(seconds=3.0)
    plain = all_frames(client, concentric(client, audio).json())
    assert all_frames(client, concentric(client, audio, **fields).json()) == plain


@pytest.mark.parametrize("fields", [{"threshold": "11"}, {"note_count": "3"}, {"resolution": "9"}, {"interpolate": "0"}, {"gaussian": "9"}, {"circle_unit": "99"}])
def test_those_settings_are_still_checked(client, fields):
    r = concentric(client, tiny(), **fields)
    assert r.status_code == 400
    assert leftovers() == []


def test_the_smoothing_applies(client):
    # two notes that swap their loudness: the steps of both change from frame to frame, and smoothing spreads the change
    seconds = np.arange(4 * SR) / SR
    fade = np.sin(np.pi * seconds / 8) ** 2
    audio = wav_bytes(0.4 * fade * note_tone(36, 4.0) + 0.4 * (1 - fade) * note_tone(48, 4.0))
    plain = all_frames(client, concentric(client, audio).json())
    smooth = all_frames(client, concentric(client, audio, smoothing="0.8", smoothing_window="10").json())
    assert smooth != plain and len(smooth) == len(plain)


def test_two_runs_give_identical_frames(client):
    audio = pulse_wav(seconds=3.0)
    assert all_frames(client, concentric(client, audio).json()) == all_frames(client, concentric(client, audio).json())


def test_a_silent_file_makes_frames_of_dots_without_failing(client):
    job = concentric(client, tiny()).json()
    assert job["frame_count"] > 0
    image = picture(client, job, 0)
    table = lookup_table(COLORMAP)
    assert tuple(image[0, 0]) == tuple(table[MIDDLE_COLOR_ROW])
    for note in (0, 41, 83):
        y, x = flat_pixel(note, 1)
        assert tuple(image[y, x]) == tuple(table[0])
        y, x = flat_pixel(note, 2)
        assert tuple(image[y, x]) == tuple(table[MIDDLE_COLOR_ROW])
    assert np.unique(image.reshape(-1, 3), axis=0).shape[0] < 400


# --- the corners (Story 3) --------------------------------------------------------------------------------------------------------


def test_a_file_in_which_no_beat_is_found_has_no_ring_past_the_middle_of_the_colormap(client):
    # a prominence of 100 % is reached only by a peak that stands on exact silence, so a steady tone has no peak at all
    audio = wav_bytes(0.5 * note_tone(TONE_NOTE, 4.0))
    job = concentric(client, audio, peak_prominence="100").json()
    rows = [ring_row(client, job, i, 12) for i in range(job["frame_count"])]
    assert max(rows) <= 128 and min(rows) >= 127, rows
    beat = concentric(client, wav_bytes(0.5 * note_tone(TONE_NOTE, 4.0))).json()  # the default prominence finds the ripple of the tone
    assert job["frame_count"] == beat["frame_count"]


def test_a_file_shorter_than_the_peaks_window_makes_frames(client):
    short = wav_bytes(np.clip(0.15 * note_tone(TONE_NOTE, 0.4), -0.9, 0.9))
    job = concentric(client, short).json()
    assert job["frame_count"] >= 1
    assert picture(client, job, 0).shape == (HEIGHT, WIDTH, 3)


def test_mono_and_stereo_copies_of_the_same_sound_make_the_same_frames(client):
    audio = np.clip(0.15 * note_tone(TONE_NOTE, 4.0), -0.9, 0.9)
    audio[SR : SR + 16] += 0.7 * np.where(np.arange(16) % 2 == 0, 1.0, -1.0)
    audio[2 * SR : 2 * SR + 16] += 0.4 * np.where(np.arange(16) % 2 == 0, 1.0, -1.0)
    audio = np.clip(audio, -0.99, 0.99)
    mono = concentric(client, wav_bytes(audio)).json()
    stereo = concentric(client, wav_bytes(audio, audio)).json()
    assert all_frames(client, mono) == all_frames(client, stereo)


def test_the_last_frames_after_the_last_click_keep_the_colours_of_the_last_peak(client):
    job = concentric(client, pulse_wav()).json()
    rows = [ring_row(client, job, i, 12) for i in range(65, job["frame_count"])]
    assert len(set(rows)) == 1, rows  # the position is held after the last peak
