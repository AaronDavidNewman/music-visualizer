"""The ``decay-exp`` image type through ``POST /api/jobs``: the type, the rate, the ignored amounts, the beat, the corners (feature 030)."""

import numpy as np
import pytest

import app.routers.jobs as jobs
from app.services.colormaps import COLORMAPS, lookup_table
from app.services.image_types import IMAGE_TYPES

from .frame_size import HEIGHT, WIDTH
from .test_decay_api import centre, row_at
from .test_jobs_api import SR, client, leftovers, note_tone, wav_bytes  # noqa: F401
from .test_peak_tile_colors_api import COLORMAP, TONE_NOTE, all_frames, post, pulse_wav
from .test_resolution_api import picture, tiny

TYPE_MESSAGE = f"The image type must be one of {', '.join(IMAGE_TYPES)}."
RATE_MESSAGE = "The decay rate must be a number from 0.25 to 4 in steps of 0.25."
DISTANCE_MESSAGE = "The minimum distance must be a number from 100 to 2000 milliseconds."
PROMINENCE_MESSAGE = "The prominence must be a number from 0 to 100 percent."
MIDDLE_COLOR_ROW = 128


def exp(client, data=None, **fields):
    return post(client, data, image_type="decay-exp", **fields)


def decay(client, data=None, **fields):
    return post(client, data, image_type="decay", **fields)


# --- choosing it --------------------------------------------------------------------------------------------------------------


def test_decay_exp_is_the_eighth_image_type_and_the_message_lists_all_twelve():
    assert IMAGE_TYPES[6:8] == ("decay", "decay-exp") and len(IMAGE_TYPES) == 12
    assert TYPE_MESSAGE == "The image type must be one of tiles, blended, contour, circles, circles_paint, concentric, decay, decay-exp, polar-chords, energy-graphs, chromatic-decay, rhythm-circles."


@pytest.mark.parametrize("name", ["decay_exp", "decayexp", "Decay-Exp", "decay-exp ", "decay-", "DECAY-EXP", ""])
def test_a_name_that_is_not_exactly_decay_exp_is_refused_with_the_nine_names(client, name):
    r = post(client, tiny(), image_type=name)
    assert r.status_code == 400 and r.json()["detail"] == TYPE_MESSAGE
    assert leftovers() == []


@pytest.mark.parametrize("name", COLORMAPS)
def test_decay_exp_is_accepted_and_echoed_with_every_colormap_and_the_defaults(client, name):
    r = post(client, tiny(), image_type="decay-exp", colormap=name)
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["image_type"] == "decay-exp" and job["colormap"] == name
    assert (job["decay_rate"], job["note_layout"], job["peak_distance"], job["peak_prominence"]) == (1, "rows", 100, 50)


def test_the_response_has_the_same_keys_as_for_the_other_types(client):
    keys = set(post(client, tiny(), image_type="tiles").json())
    assert set(exp(client, tiny()).json()) == keys


def test_the_frames_are_600_by_400_rgb_pictures_and_their_count_is_that_of_the_other_types(client):
    audio = pulse_wav(seconds=3.0)
    job = exp(client, audio).json()
    tiles = post(client, audio, image_type="tiles").json()
    assert job["frame_count"] == tiles["frame_count"] > 0
    assert picture(client, job, 0).shape == (HEIGHT, WIDTH, 3)
    assert picture(client, job, job["frame_count"] - 1).shape == (HEIGHT, WIDTH, 3)


# --- the decay rate -----------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("rate", ["0.25", "0.5", "1", "2.5", "4", " 1.5 "])
def test_a_number_from_a_quarter_to_4_in_steps_of_a_quarter_is_accepted_and_echoed(client, rate):
    r = exp(client, tiny(), decay_rate=rate)
    assert r.status_code == 200, r.text
    assert r.json()["decay_rate"] == float(rate)


@pytest.mark.parametrize("rate", ["0", "0.2", "1.1", "4.25", "5", "10", "-1", "abc", "", "nan", "inf"])
def test_anything_else_is_refused_with_the_message_and_nothing_is_created(client, rate):
    r = exp(client, tiny(), decay_rate=rate)
    assert r.status_code == 400 and r.json()["detail"] == RATE_MESSAGE
    assert leftovers() == []


def test_the_rate_is_checked_before_the_file_is_read(client):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": "decay-exp", "decay_rate": "5"})
    assert r.status_code == 400 and r.json()["detail"] == RATE_MESSAGE
    assert leftovers() == []


def test_the_rate_changes_the_frames(client):
    audio = pulse_wav(seconds=4.0)
    quarter = all_frames(client, exp(client, audio, decay_rate="0.25").json())
    four = all_frames(client, exp(client, audio, decay_rate="4").json())
    assert quarter != four and len(quarter) == len(four)


# --- the four decay amounts are checked and have no effect --------------------------------------------------------------------


def test_the_four_decay_amounts_are_accepted_echoed_and_have_no_effect(client):
    audio = pulse_wav(seconds=3.0)
    plain = all_frames(client, exp(client, audio).json())
    r = exp(client, audio, decay_low="3", decay_medium="3", decay_high="0.5", decay_saturated="0.5")
    assert r.status_code == 200
    assert [r.json()[k] for k in ("decay_low", "decay_medium", "decay_high", "decay_saturated")] == [3, 3, 0.5, 0.5]
    assert all_frames(client, r.json()) == plain


@pytest.mark.parametrize("level", ["low", "medium", "high", "saturated"])
@pytest.mark.parametrize("value", ["0.4", "3.1", "abc", "", "nan"])
def test_a_bad_decay_amount_is_still_refused_before_the_file_is_read(client, level, value):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": "decay-exp", f"decay_{level}": value})
    assert r.status_code == 400
    assert r.json()["detail"] == f"The {level} saturation decay must be a number from 0.5 to 3."
    assert leftovers() == []


def test_the_decay_amounts_still_change_decay(client):
    audio = pulse_wav(seconds=4.0)
    plain = all_frames(client, decay(client, audio).json())
    assert all_frames(client, decay(client, audio, decay_low="3", decay_medium="3", decay_high="3").json()) != plain


# --- the beat is always measured ----------------------------------------------------------------------------------------------


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
    assert exp(client, tiny(), **fields).status_code == 200
    assert measured == [(22050, SR, 300.0, 20.0)]


def test_the_checkbox_has_no_effect_on_the_frames(client):
    audio = pulse_wav(seconds=4.0)
    plain = all_frames(client, exp(client, audio).json())
    assert all_frames(client, exp(client, audio, beat_coloring="true").json()) == plain


@pytest.mark.parametrize(
    "fields, message",
    [({"peak_distance": "50"}, DISTANCE_MESSAGE), ({"peak_distance": "abc"}, DISTANCE_MESSAGE), ({"peak_prominence": "101"}, PROMINENCE_MESSAGE), ({"peak_prominence": ""}, PROMINENCE_MESSAGE)],
)
def test_the_peak_settings_are_checked_before_the_file_is_read_with_nothing_created(client, measured, fields, message):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": "decay-exp", **fields})
    assert r.status_code == 400 and r.json()["detail"] == message
    assert exp(client, tiny(), **fields).status_code == 400
    assert leftovers() == [] and measured == []


def test_the_minimum_distance_and_the_prominence_change_the_beat_that_charges_the_circles(client):
    audio = pulse_wav()
    default = all_frames(client, exp(client, audio).json())
    far = all_frames(client, exp(client, audio, peak_distance="2000").json())
    high = all_frames(client, exp(client, audio, peak_prominence="95").json())
    assert far != default and high != default


# --- the picture --------------------------------------------------------------------------------------------------------------


def test_the_picture_is_not_the_picture_of_decay_and_the_first_frame_is_less_charged(client):
    audio = wav_bytes(0.5 * note_tone(TONE_NOTE, 3.0))
    exp_job = exp(client, audio, peak_prominence="100").json()  # a prominence of 100 % finds no peak in a steady tone: no bonus
    decay_job = decay(client, audio, peak_prominence="100").json()
    assert all_frames(client, exp_job) != all_frames(client, decay_job)
    # decay: 24 points, 16 given away: row 64; decay-exp: 1.19 points, of which hardly any is given away: row 9
    assert row_at(client, decay_job, 0) == int(np.rint(8 / 32 * 255))
    assert row_at(client, exp_job, 0) < row_at(client, decay_job, 0)


def test_the_settings_of_the_other_pictures_are_accepted_and_ignored(client):
    audio = pulse_wav(seconds=3.0)
    plain = all_frames(client, exp(client, audio).json())
    for fields in (
        {"threshold": "5"}, {"note_count": "20"}, {"resolution": "3"}, {"interpolate": "3"}, {"gaussian": "2"}, {"blend_width": "10"},
        {"circle_unit": "9"}, {"circle_memory": "100"}, {"circle_notes": "12"}, {"circle_radius": "8"}, {"circle_resize": "true"},
    ):
        r = exp(client, audio, **fields)
        assert r.status_code == 200, (fields, r.text)
        assert all_frames(client, r.json()) == plain, fields


@pytest.mark.parametrize("fields", [{"threshold": "11"}, {"note_count": "5"}, {"resolution": "6"}, {"interpolate": "9"}, {"gaussian": "-1"}, {"circle_notes": "99"}])
def test_those_settings_are_still_checked(client, fields):
    assert exp(client, tiny(), **fields).status_code == 400


def test_the_smoothing_applies(client):
    audio = pulse_wav(seconds=3.0)
    plain = all_frames(client, exp(client, audio).json())
    smooth = all_frames(client, exp(client, audio, smoothing="0.6", smoothing_window="5").json())
    assert smooth != plain and len(smooth) == len(plain)


def test_the_spiral_layout_applies_and_is_echoed(client):
    audio = pulse_wav(seconds=3.0)
    rows = exp(client, audio, note_layout="rows").json()
    spiral = exp(client, audio, note_layout="spiral")
    assert spiral.status_code == 200 and spiral.json()["note_layout"] == "spiral"
    assert all_frames(client, spiral.json()) != all_frames(client, rows)
    assert exp(client, audio, note_layout="Spiral").status_code == 400


def test_two_runs_give_identical_frames(client):
    audio = pulse_wav(seconds=3.0)
    assert all_frames(client, exp(client, audio).json()) == all_frames(client, exp(client, audio).json())


# --- the corners (Story 3) ----------------------------------------------------------------------------------------------------


def test_a_silent_file_makes_frames_of_the_smallest_dots_in_the_first_color_without_failing(client):
    job = exp(client, tiny()).json()
    assert job["frame_count"] > 0
    image = picture(client, job, 0)
    table = lookup_table(COLORMAP)
    assert tuple(image[0, 0]) == tuple(table[MIDDLE_COLOR_ROW])
    for cell in (0, 41, 83):
        x, y = centre(cell)
        assert tuple(image[y, x]) == tuple(table[0])
    assert len(set(all_frames(client, job))) == 1


def test_a_file_shorter_than_the_peaks_window_makes_frames(client):
    short = wav_bytes(np.clip(0.15 * note_tone(TONE_NOTE, 0.4), -0.9, 0.9))
    job = exp(client, short).json()
    assert job["frame_count"] >= 1
    assert picture(client, job, 0).shape == (HEIGHT, WIDTH, 3)


@pytest.mark.parametrize("rate", ["0.25", "0.75", "4"])
def test_mono_and_stereo_copies_of_the_same_sound_make_the_same_frames(client, rate):
    mono = 0.5 * note_tone(TONE_NOTE, 2.0)
    a = exp(client, wav_bytes(mono), decay_rate=rate).json()
    b = exp(client, wav_bytes(np.stack([mono, mono], axis=1)), decay_rate=rate).json()
    assert all_frames(client, a) == all_frames(client, b)
