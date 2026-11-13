"""The noise floor through ``POST /api/jobs``: every image type, with and without a Threshold, real tones (feature 033).

A tone at the exact centre of a spectrum bin (``note_tone``) raises that note only, and nothing leaks into the other notes while the tone sounds
for a whole window, so a second tone 70 dB below the first is a faint note with nothing around it. The note values that reach ``write_frames`` are
recorded by a spy, so that what each picture is given can be checked without depending on how it draws.
"""

import numpy as np
import pytest

import app.routers.jobs as jobs
from app.services.image_types import IMAGE_TYPES
from app.services.noise_floor import NOISE_FLOOR

from .frame_size import HEIGHT, WIDTH  # noqa: F401
from .test_jobs_api import SR, client, frame_rgb, leftovers, note_tone, wav_bytes  # noqa: F401
from .test_peak_tile_colors_api import post
from .test_polar_chords_api import ARC, CHORD_ARC, MIDDLE, RADIUS, row_at
from .test_resolution_api import picture

WINDOW = "8192"  # at this size the notes from C5 (39) up have a spectrum bin of their own
LOUD, FAINT = 39, 46  # C5 and G5 (note 0 is A1)
AMPLITUDE = 0.2
SECONDS = (9 * 8192 + 0.5) / SR  # nine whole windows: in a last window that is only partly filled the tone is cut off and really leaks into the notes around it


def db(decibels):
    """The amplitude ratio of a number of decibels below (a negative number)."""
    return 10 ** (decibels / 20)


def audio(faint_db=-70.0, seconds=SECONDS):
    """A loud tone and, in the same file, a second tone ``faint_db`` decibels below it."""
    mix = AMPLITUDE * note_tone(LOUD, seconds, int(WINDOW))
    if faint_db is not None:
        mix = mix + AMPLITUDE * db(faint_db) * note_tone(FAINT, seconds, int(WINDOW))
    return wav_bytes(mix)


@pytest.fixture
def given(monkeypatch):
    """The note values given to ``write_frames`` by the job, one array for each call."""
    calls = []
    real = jobs.write_frames

    def spy(frames, *args, **kwargs):
        calls.append(np.array(frames))
        return real(frames, *args, **kwargs)

    monkeypatch.setattr(jobs, "write_frames", spy)
    return calls


def job_of(client, data, **fields):
    r = post(client, data, window_size=WINDOW, window_spacing="1", **fields)  # spacing 1: the windows follow one another, so the last one is full
    assert r.status_code == 200, r.text
    return r.json()


# ---- User Story 1: the notes that reach the pictures are cut -----------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", IMAGE_TYPES)
def test_a_note_70_db_below_the_loudest_is_0_in_every_frame_for_every_image_type(client, given, image_type):
    job_of(client, audio(-70.0), image_type=image_type)
    frames = given[0]
    assert frames.shape[1] == 88 and frames.shape[0] > 5
    assert (frames[:, FAINT] == 0.0).all()  # the faint note never sounds
    assert (frames[:, LOUD] > 0).sum() >= 5  # the loud one does, in the frames it fills
    sounding = frames[frames > 0]
    assert sounding.min() >= NOISE_FLOOR * frames.max()  # and no value is left under the floor (the windows are longer than the frames: a frame is one window)


def test_the_same_note_only_50_db_below_is_not_cut(client, given):
    job_of(client, audio(-50.0), image_type="contour")
    frames = given[0]
    middle = frames[frames.shape[0] // 2]
    assert middle[FAINT] > 0 and middle[FAINT] == pytest.approx(db(-50.0) * middle[LOUD], rel=0.02)


def test_the_note_just_above_the_floor_is_kept_and_just_under_it_is_cut(client, given):
    job_of(client, audio(-59.0), image_type="contour")  # 1.12 thousandths
    job_of(client, audio(-61.0), image_type="contour")  # 0.89 thousandths
    kept, cut = given
    assert (kept[kept.shape[0] // 2][FAINT] > 0) and (cut[cut.shape[0] // 2][FAINT] == 0.0)


def test_a_stretch_in_which_only_a_faint_note_sounds_is_silence(client, given):
    quarter = int(SECONDS / 4 * SR)
    loud = AMPLITUDE * note_tone(LOUD, SECONDS, int(WINDOW))
    faint = AMPLITUDE * db(-70.0) * note_tone(FAINT, SECONDS, int(WINDOW))
    job_of(client, wav_bytes(np.concatenate([loud[:quarter], faint[quarter : 3 * quarter], loud[3 * quarter :]])), image_type="decay-exp")
    frames = given[0]
    silent = np.flatnonzero(frames.sum(axis=1) == 0)
    assert silent.size >= 2  # the windows that lie wholly in the middle half: nothing in them is a note, however the faint tone compares with silence
    loud_rows = np.flatnonzero(frames[:, LOUD] > 0)
    assert loud_rows.min() < silent.min() and loud_rows.max() > silent.max()  # between the loud stretches


def test_a_silent_file_gives_values_of_0(client, given):
    job_of(client, wav_bytes(np.zeros(int(SECONDS * SR))), image_type="contour")
    assert (given[0] == 0.0).all()


# ---- the pictures themselves -------------------------------------------------------------------------------------------------------------------


def test_polar_chords_shows_only_the_loud_note_not_the_faint_one(client):
    job = job_of(client, audio(-70.0), image_type="polar-chords", polar_notes="8", peak_prominence="100")
    image = picture(client, job, job["frame_count"] // 2)
    assert row_at(image, (LOUD + 0.5) * ARC, 0.3 * RADIUS) <= 30  # the loud note has its bar
    assert row_at(image, (FAINT + 0.5) * ARC, 0.3 * RADIUS) == MIDDLE  # the faint note has none: with eight bars to give, it is still not a note
    other = job_of(client, audio(-50.0), image_type="polar-chords", polar_notes="8", peak_prominence="100")
    assert row_at(picture(client, other, other["frame_count"] // 2), (FAINT + 0.5) * ARC, 0.3 * RADIUS) != MIDDLE  # at 50 dB down it has one


# ---- User Story 2: the chords --------------------------------------------------------------------------------------------------------------------


def test_a_triad_with_a_faint_extra_tone_gives_the_chord_bar_of_the_triad_not_of_a_seventh_chord(client):
    # A minor (A5, C6, E6) with a G6 tone 70 dB below: with the G it would be the minor seventh chord (place 5 on A), without it the minor triad (place 2)
    a5, c6, e6, g6 = 48, 51, 55, 58
    mix = AMPLITUDE / 3 * (note_tone(a5, SECONDS, int(WINDOW)) + note_tone(c6, SECONDS, int(WINDOW)) + note_tone(e6, SECONDS, int(WINDOW)))
    mix = mix + AMPLITUDE / 3 * db(-70.0) * note_tone(g6, SECONDS, int(WINDOW))
    job = job_of(client, wav_bytes(mix), image_type="polar-chords", polar_notes="8", peak_prominence="100")
    image = picture(client, job, job["frame_count"] // 2)
    assert row_at(image, 360.0 - (2 + 0.5) * CHORD_ARC, 0.3 * RADIUS) >= 200  # the triad's bar, in the second half of the colormap
    assert row_at(image, 360.0 - (5 + 0.5) * CHORD_ARC, 0.3 * RADIUS) == MIDDLE  # not the seventh chord's
    assert row_at(image, (g6 + 0.5) * ARC, 0.3 * RADIUS) == MIDDLE  # and the faint G has no note bar either


# ---- User Story 3: fixed, for every picture, with or without a Threshold --------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", IMAGE_TYPES)
def test_the_values_the_pictures_are_given_do_not_depend_on_the_threshold_and_the_faint_note_is_0_for_any_of_them(client, given, image_type):
    for threshold in ("0", "5", "10"):
        job_of(client, audio(-70.0), image_type=image_type, threshold=threshold)
    zero, five, ten = given
    for frames in (zero, five, ten):
        assert (frames[:, FAINT] == 0.0).all()  # a Threshold of 0 hides nothing more, and does not switch the floor off
    np.testing.assert_array_equal(zero, five)  # the Threshold works inside write_frames, after the cut
    np.testing.assert_array_equal(zero, ten)


def test_the_floor_adds_no_field_to_the_request_or_the_response(client):
    plain = job_of(client, audio(-70.0), image_type="contour")
    with_extra = job_of(client, audio(-70.0), image_type="contour", noise_floor="0", noise_floor_db="-20")  # not a field of the request: ignored like any unknown field
    assert set(plain) == set(with_extra)
    assert not [key for key in plain if "noise" in key or "floor" in key]


def test_a_file_in_which_every_note_is_at_or_above_the_floor_or_silent_is_given_to_the_pictures_unchanged():
    from app.services.noise_floor import floor_analysis
    from app.services.note_analysis import AnalysisResult

    frames = np.zeros((6, 88))
    frames[:, 39] = 1000.0
    frames[:, 46] = 1.0  # exactly a thousandth of the loudest: still a note
    frames[2, 50] = 3.0
    result = AnalysisResult(44100.0, 8192, frames, 49152, None, 8192.0)
    np.testing.assert_array_equal(floor_analysis(result).frames, frames)
