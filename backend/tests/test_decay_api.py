"""The ``decay`` image type through ``POST /api/jobs``: the type, the rate, the beat, the ignored settings, the corners (feature 027)."""

import time

import numpy as np
import pytest

import app.routers.jobs as jobs
from app.services.colormaps import COLORMAPS, lookup_table
from app.services.image_types import IMAGE_TYPES
from app.services.note_grid import tile_edges

from .frame_size import HEIGHT, WIDTH
from .test_jobs_api import SR, client, leftovers, note_tone, wav_bytes  # noqa: F401
from .test_peak_tile_colors_api import COLORMAP, ROWS, TONE_NOTE, all_frames, post, pulse_wav
from .test_resolution_api import picture, tiny

TYPE_MESSAGE = f"The image type must be one of {', '.join(IMAGE_TYPES)}."
RATE_MESSAGE = "The decay rate must be a number from 0.25 to 4 in steps of 0.25."
DISTANCE_MESSAGE = "The minimum distance must be a number from 100 to 2000 milliseconds."
PROMINENCE_MESSAGE = "The prominence must be a number from 0 to 100 percent."
MIDDLE_COLOR_ROW = 128
COLUMN_EDGES = tile_edges(12, WIDTH)
ROW_EDGES = tile_edges(7, HEIGHT)


def decay(client, data=None, **fields):
    return post(client, data, image_type="decay", **fields)


def centre(cell: int) -> tuple[int, int]:
    row, column = divmod(cell, 12)
    return (COLUMN_EDGES[column] + COLUMN_EDGES[column + 1]) // 2, (ROW_EDGES[row] + ROW_EDGES[row + 1]) // 2


def row_at(client, job, index, cell=TONE_NOTE) -> int:
    """The colormap row of the center of the circle of a cell in a served frame."""
    x, y = centre(cell)
    return ROWS[tuple(int(v) for v in picture(client, job, index)[y, x])]


# --- choosing it --------------------------------------------------------------------------------------------------------------


def test_decay_is_the_second_image_type_and_the_message_lists_all_eight():
    assert IMAGE_TYPES[1] == "decay" and len(IMAGE_TYPES) == 8
    assert TYPE_MESSAGE == "The image type must be one of contour, decay, decay-exp, polar-chords, energy-graphs, chromatic-decay, rhythm-circles, chromatic-wireframe."


@pytest.mark.parametrize("name", ["decays", "Decay", "decay ", "DECAY", ""])
def test_a_name_that_is_not_exactly_decay_is_refused_with_the_nine_names(client, name):
    r = post(client, tiny(), image_type=name)
    assert r.status_code == 400 and r.json()["detail"] == TYPE_MESSAGE
    assert leftovers() == []


@pytest.mark.parametrize("name", COLORMAPS)
def test_decay_is_accepted_and_echoed_with_every_colormap_and_the_defaults(client, name):
    r = post(client, tiny(), image_type="decay", colormap=name)
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["image_type"] == "decay" and job["colormap"] == name
    assert (job["decay_rate"], job["note_layout"], job["peak_distance"], job["peak_prominence"]) == (1, "rows", 100, 50)


def test_the_response_has_the_same_keys_as_for_the_other_types_and_decay_rate_is_in_all_of_them(client):
    keys = set(post(client, tiny(), image_type="contour").json())
    assert "decay_rate" in keys
    assert set(decay(client, tiny()).json()) == keys


def test_the_frames_are_600_by_400_rgb_pictures_and_their_count_is_that_of_the_other_types(client):
    audio = pulse_wav(seconds=3.0)
    job = decay(client, audio).json()
    tiles = post(client, audio, image_type="contour").json()
    assert job["frame_count"] == tiles["frame_count"] > 0
    assert picture(client, job, 0).shape == (HEIGHT, WIDTH, 3)
    assert picture(client, job, job["frame_count"] - 1).shape == (HEIGHT, WIDTH, 3)


# --- the decay rate -----------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("rate", ["0.25", "0.5", "0.75", "1", "1.25", "2.5", "3", "4", "4.0", " 1.5 "])
def test_a_number_from_a_quarter_to_4_in_steps_of_a_quarter_is_accepted_and_echoed(client, rate):
    r = decay(client, tiny(), decay_rate=rate)
    assert r.status_code == 200, r.text
    assert r.json()["decay_rate"] == float(rate)


@pytest.mark.parametrize("rate", ["0", "0.2", "0.24", "0.3", "1.1", "3.9", "4.25", "5", "10", "-1", "-0.25", "abc", "", "nan", "inf", "1e3"])
def test_anything_else_is_refused_with_the_message_and_nothing_is_created(client, rate):
    r = decay(client, tiny(), decay_rate=rate)
    assert r.status_code == 400 and r.json()["detail"] == RATE_MESSAGE
    assert leftovers() == []


def test_the_rate_is_checked_before_the_file_is_read(client):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": "decay", "decay_rate": "5"})  # no file at all
    assert r.status_code == 400 and r.json()["detail"] == RATE_MESSAGE
    assert leftovers() == []


@pytest.mark.parametrize("image_type", ["contour"])
def test_a_rate_sent_with_another_type_is_checked_echoed_and_has_no_effect(client, image_type):
    audio = tiny()
    plain = post(client, audio, image_type=image_type).json()
    sent = post(client, audio, image_type=image_type, decay_rate="2")
    assert sent.status_code == 200 and sent.json()["decay_rate"] == 2
    assert all_frames(client, sent.json()) == all_frames(client, plain)
    assert post(client, audio, image_type=image_type, decay_rate="5").status_code == 400


def test_the_rate_changes_the_frames(client):
    audio = pulse_wav(seconds=4.0)
    one = all_frames(client, decay(client, audio, decay_rate="0.25").json())
    ten = all_frames(client, decay(client, audio, decay_rate="4").json())
    assert one != ten and len(one) == len(ten)


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
    assert decay(client, tiny(), **fields).status_code == 200
    assert measured == [(22050, SR, 300.0, 20.0)]


def test_the_checkbox_has_no_effect_on_the_frames_of_decay(client):
    audio = pulse_wav(seconds=4.0)
    plain = all_frames(client, decay(client, audio).json())
    assert all_frames(client, decay(client, audio, beat_coloring="true").json()) == plain


@pytest.mark.parametrize(
    "fields, message",
    [({"peak_distance": "50"}, DISTANCE_MESSAGE), ({"peak_distance": "abc"}, DISTANCE_MESSAGE), ({"peak_prominence": "101"}, PROMINENCE_MESSAGE), ({"peak_prominence": ""}, PROMINENCE_MESSAGE)],
)
def test_the_peak_settings_are_checked_before_the_file_is_read_with_nothing_created(client, measured, fields, message):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": "decay", **fields})
    assert r.status_code == 400 and r.json()["detail"] == message
    assert decay(client, tiny(), **fields).status_code == 400
    assert leftovers() == [] and measured == []


def test_the_minimum_distance_and_the_prominence_change_the_beat_that_charges_the_circles(client):
    audio = pulse_wav()
    default = all_frames(client, decay(client, audio).json())
    far = all_frames(client, decay(client, audio, peak_distance="2000").json())
    high = all_frames(client, decay(client, audio, peak_prominence="95").json())
    assert far != default and high != default


# --- the picture --------------------------------------------------------------------------------------------------------------


def test_a_steady_tone_charges_its_circle_to_the_last_color_and_the_silent_notes_stay_small_dots(client):
    job = decay(client, wav_bytes(0.5 * note_tone(TONE_NOTE, 4.0)), decay_rate="1", peak_prominence="100").json()
    last = job["frame_count"] - 1
    assert row_at(client, job, last) == 255  # the circle settles above 32 points (24 a frame in, 16 to 24 out)
    assert row_at(client, job, last, cell=0) < 40 and row_at(client, job, last, cell=83) < 40  # leakage of the tone gives them a point or so


def test_the_circle_of_a_note_that_stops_loses_its_points_and_its_color_over_the_following_intervals(client):
    audio = np.concatenate([0.5 * note_tone(TONE_NOTE, 2.0), np.zeros(SR * 6)])
    job = decay(client, wav_bytes(audio), decay_rate="1", peak_prominence="100").json()
    rows = [row_at(client, job, i) for i in range(job["frame_count"])]
    assert max(rows) == 255 and rows[-1] == 0
    assert row_at(client, job, job["frame_count"] - 1, cell=TONE_NOTE + 1) <= 4  # a neighbour's last few points are still leaking away at half a point a frame


def test_the_settings_of_the_other_pictures_are_accepted_and_ignored(client):
    audio = pulse_wav(seconds=3.0)
    plain = all_frames(client, decay(client, audio).json())
    for fields in (
        {"threshold": "5"}, {"note_count": "20"}, {"resolution": "3"}, {"interpolate": "3"}, {"gaussian": "2"},
    ):
        r = decay(client, audio, **fields)
        assert r.status_code == 200, (fields, r.text)
        assert all_frames(client, r.json()) == plain, fields


@pytest.mark.parametrize("fields", [{"threshold": "11"}, {"note_count": "5"}, {"resolution": "6"}, {"interpolate": "9"}, {"gaussian": "-1"}])
def test_those_settings_are_still_checked(client, fields):
    assert decay(client, tiny(), **fields).status_code == 400


def test_the_smoothing_applies(client):
    audio = pulse_wav(seconds=3.0)
    plain = all_frames(client, decay(client, audio).json())
    smooth = all_frames(client, decay(client, audio, smoothing="0.6", smoothing_window="5").json())
    assert smooth != plain and len(smooth) == len(plain)


def test_the_spiral_layout_applies_and_is_echoed(client):
    audio = pulse_wav(seconds=3.0)
    rows = decay(client, audio, note_layout="rows").json()
    spiral = decay(client, audio, note_layout="spiral")
    assert spiral.status_code == 200 and spiral.json()["note_layout"] == "spiral"
    assert all_frames(client, spiral.json()) != all_frames(client, rows)
    assert decay(client, audio, note_layout="Spiral").status_code == 400


def test_two_runs_give_identical_frames(client):
    audio = pulse_wav(seconds=3.0)
    assert all_frames(client, decay(client, audio).json()) == all_frames(client, decay(client, audio).json())


# --- the corners (Story 3) ----------------------------------------------------------------------------------------------------


def test_a_silent_file_makes_frames_of_the_smallest_dots_in_the_first_color_without_failing(client):
    job = decay(client, tiny()).json()
    assert job["frame_count"] > 0
    image = picture(client, job, 0)
    table = lookup_table(COLORMAP)
    assert tuple(image[0, 0]) == tuple(table[MIDDLE_COLOR_ROW])
    for cell in (0, 41, 83):
        x, y = centre(cell)
        assert tuple(image[y, x]) == tuple(table[0])
    assert np.unique(image.reshape(-1, 3), axis=0).shape[0] < 400
    assert len(set(all_frames(client, job))) == 1


def test_a_file_in_which_no_beat_is_found_works_with_no_bonus(client):
    audio = wav_bytes(0.5 * note_tone(TONE_NOTE, 4.0))
    job = decay(client, audio, peak_prominence="100").json()  # a prominence of 100 % finds no peak in a steady tone
    assert job["frame_count"] > 0 and row_at(client, job, 0) == int(np.rint(8 / 32 * 255))  # 24 gained, and a step of the default rate (1 frame) gives 16 away


def test_a_file_shorter_than_the_peaks_window_makes_frames(client):
    short = wav_bytes(np.clip(0.15 * note_tone(TONE_NOTE, 0.4), -0.9, 0.9))
    job = decay(client, short).json()
    assert job["frame_count"] >= 1
    assert picture(client, job, 0).shape == (HEIGHT, WIDTH, 3)


@pytest.mark.parametrize("rate", ["0.25", "0.75", "4"])
def test_mono_and_stereo_copies_of_the_same_sound_make_the_same_frames(client, rate):
    mono = 0.5 * note_tone(TONE_NOTE, 2.0)
    a = decay(client, wav_bytes(mono), decay_rate=rate).json()
    b = decay(client, wav_bytes(np.stack([mono, mono], axis=1)), decay_rate=rate).json()
    assert all_frames(client, a) == all_frames(client, b)


def test_a_minute_of_frames_at_30_a_second_is_made_in_a_reasonable_time(client):
    audio = wav_bytes(np.clip(0.3 * note_tone(TONE_NOTE, 60.0), -0.9, 0.9))
    started = time.perf_counter()
    r = client.post("/api/jobs", files={"file": ("long.wav", audio, "audio/wav")}, data={"window_size": "4096", "frame_rate": "30", "image_type": "decay", "colormap": COLORMAP})
    elapsed = time.perf_counter() - started
    assert r.status_code == 200 and r.json()["frame_count"] >= 1700
    assert elapsed < 30, elapsed

# --- the four decay amounts (one for each saturation level) --------------------------------------------------------------------------

AMOUNT_FIELDS = ["decay_low", "decay_medium", "decay_high", "decay_saturated"]
AMOUNT_DEFAULTS = [0.5, 1.0, 2.0, 3.0]
LEVEL_NAMES = ["low", "medium", "high", "saturated"]


def amount_message(level):
    return f"The {level} saturation decay must be a number from 0.5 to 3."


@pytest.mark.parametrize("image_type", ["contour", "decay", "decay-exp", "polar-chords"])
def test_the_defaults_are_reported_for_every_image_type(client, image_type):
    r = post(client, tiny(), image_type=image_type)
    assert r.status_code == 200, r.text
    assert [r.json()[f] for f in AMOUNT_FIELDS] == AMOUNT_DEFAULTS


@pytest.mark.parametrize("field, default", list(zip(AMOUNT_FIELDS, AMOUNT_DEFAULTS)))
@pytest.mark.parametrize("value, expected", [("0.5", 0.5), ("1", 1.0), ("1.25", 1.25), ("3", 3.0), ("3.0", 3.0), (" 2.5 ", 2.5)])
def test_a_number_from_half_to_3_is_accepted_and_echoed_others_keep_their_defaults(client, field, default, value, expected):
    r = decay(client, tiny(), **{field: value})
    assert r.status_code == 200, r.text
    job = r.json()
    assert job[field] == expected
    assert [job[f] for f in AMOUNT_FIELDS if f != field] == [d for f, d in zip(AMOUNT_FIELDS, AMOUNT_DEFAULTS) if f != field]


@pytest.mark.parametrize("field, level", list(zip(AMOUNT_FIELDS, LEVEL_NAMES)))
@pytest.mark.parametrize("value", ["0.49", "0", "3.01", "4", "-1", "abc", "", "nan", "inf", "-inf", "1e3"])
def test_anything_else_is_refused_with_the_message_of_its_level_and_nothing_is_created(client, field, level, value):
    r = decay(client, tiny(), **{field: value})
    assert r.status_code == 400 and r.json()["detail"] == amount_message(level)
    assert leftovers() == []


@pytest.mark.parametrize("field, level", list(zip(AMOUNT_FIELDS, LEVEL_NAMES)))
def test_the_amounts_are_checked_before_the_file_is_read(client, field, level):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": "decay", field: "5"})  # no file at all
    assert r.status_code == 400 and r.json()["detail"] == amount_message(level)
    assert leftovers() == []


@pytest.mark.parametrize("image_type", ["contour"])
def test_amounts_sent_with_another_type_are_checked_echoed_and_have_no_effect(client, image_type):
    audio = tiny()
    plain = post(client, audio, image_type=image_type).json()
    sent = post(client, audio, image_type=image_type, decay_low="3", decay_medium="3", decay_high="0.5", decay_saturated="0.5")
    assert sent.status_code == 200
    assert [sent.json()[f] for f in AMOUNT_FIELDS] == [3.0, 3.0, 0.5, 0.5]
    assert all_frames(client, sent.json()) == all_frames(client, plain)
    assert post(client, audio, image_type=image_type, decay_high="9").status_code == 400


def test_each_amount_changes_the_decay_frames_and_the_defaults_do_not(client):
    audio = pulse_wav(seconds=6.0)
    base = all_frames(client, decay(client, audio, decay_rate="1").json())
    same = all_frames(client, decay(client, audio, decay_rate="1", decay_low="0.5", decay_medium="1", decay_high="2", decay_saturated="3").json())
    assert same == base
    for field, other in zip(AMOUNT_FIELDS, ["3", "3", "0.5", "0.5"]):
        changed = all_frames(client, decay(client, audio, decay_rate="1", **{field: other}).json())
        assert changed != base, field
