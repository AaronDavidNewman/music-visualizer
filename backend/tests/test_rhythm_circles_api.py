"""The ``rhythm-circles`` image type through ``POST /api/jobs``: the type, the local peaks settings, a click track end to end, silence, the ignored settings (feature 038),
and since feature 047 the six rings, the Vote limit and the Extra notes of the voted tempos."""

import io

import numpy as np
import pytest
from PIL import Image

from app.services import rhythm_circles as rc
from app.services.colormaps import lookup_table
from app.services.frame_rendering import write_frames
from app.services.image_types import IMAGE_TYPES

from .frame_size import HEIGHT, WIDTH
from .test_jobs_api import client, leftovers, wav_bytes  # noqa: F401
from .test_peak_tile_colors_api import COLORMAP, post, pulse_wav
from .test_resolution_api import tiny

TYPE_MESSAGE = f"The image type must be one of {', '.join(IMAGE_TYPES)}."
DISTANCE_MESSAGE = "The minimum distance must be a number from 100 to 2000 milliseconds."
FPS = 10
OUTER = HEIGHT / 2 - 10  # the outer radius of the first ring: 190
RINGS = 6
RING = OUTER / RINGS  # a ring and its gap
GAP = 4


def rhythm(client, data=None, **fields):
    return post(client, data, image_type="rhythm-circles", **fields)


def picture(client, job, index):
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    assert r.status_code == 200
    return np.asarray(Image.open(io.BytesIO(r.content)).convert("RGB"))


def raw(client, job, index):
    return client.get(job["frame_url_template"].replace("{index}", str(index))).content


def raws(client, job):
    return [raw(client, job, i) for i in range(job["frame_count"])]


def middle_radius(k):
    outer = OUTER - (k - 1) * RING
    return outer - (RING - GAP) / 2


def notch_row(k):
    return int(np.rint((1 - (k - 1) / 5) * 255))


def notch_turns(image, k, colormap=COLORMAP):
    """The place of the notch of ring ``k`` in turns clockwise from the top, read from the pixels at the middle of the ring."""
    table = lookup_table(colormap)
    target = table[notch_row(k)]
    turns = np.arange(720) / 720.0
    x = WIDTH / 2 + middle_radius(k) * np.sin(2 * np.pi * turns)
    y = HEIGHT / 2 - middle_radius(k) * np.cos(2 * np.pi * turns)
    colors = image[np.floor(y).astype(int), np.floor(x).astype(int)]
    hit = (colors == target).all(axis=1)
    assert hit.sum() > 60, f"ring {k}: {hit.sum()} samples in the notch color"  # about 90 of 720: an eighth
    return (np.angle(np.exp(2j * np.pi * turns[hit]).mean()) / (2 * np.pi)) % 1.0


def apart(a, b):
    """The distance of two places in turns on the circle."""
    d = abs(a - b) % 1.0
    return min(d, 1.0 - d)


class Spy:
    """Keeps the local peaks the job measured and the arguments it measured them with, and the arguments and the result of ``rhythm_angles``."""

    def __init__(self, monkeypatch):
        import app.routers.jobs as jobs

        self.calls, self.results = [], []
        self.rhythm_calls, self.rhythm_results = [], []
        real = jobs.measure_local_peaks
        real_rhythm = jobs.rhythm_angles

        def spy_rhythm(*args):
            self.rhythm_calls.append(args)
            self.rhythm_results.append(real_rhythm(*args))
            return self.rhythm_results[-1]

        monkeypatch.setattr(jobs, "rhythm_angles", spy_rhythm)

        def spy(left, right, rate, distance, prominence):
            self.calls.append((distance, prominence))
            self.results.append(real(left, right, rate, distance, prominence))
            return self.results[-1]

        monkeypatch.setattr(jobs, "measure_local_peaks", spy)


def expected_turns(spy, index=0):
    """The angles (turns, one frame a row, six columns) that the job's own call of ``rhythm_angles`` made."""
    return spy.rhythm_results[index].angles % 1.0


# --- choosing it --------------------------------------------------------------------------------------------------------------


def test_rhythm_circles_is_the_seventh_image_type_and_the_message_lists_all_eight():
    assert IMAGE_TYPES[6] == "rhythm-circles" and len(IMAGE_TYPES) == 10
    assert TYPE_MESSAGE.endswith("polar-chords, energy-graphs, chromatic-decay, rhythm-circles, chromatic-wireframe, polychord, spirograph.")


@pytest.mark.parametrize("name", ["rhythm_circles", "rhythmcircles", "Rhythm-Circles", "rhythm-circles ", "rhythm", "rhythm-", "RHYTHM-CIRCLES", "rhythm-circle", ""])
def test_a_name_that_is_not_exactly_rhythm_circles_is_refused_with_the_thirteen_names(client, name):
    r = post(client, tiny(), image_type=name)
    assert r.status_code == 400 and r.json()["detail"] == TYPE_MESSAGE
    assert leftovers() == []


def test_it_is_accepted_and_echoed_and_the_response_has_no_new_field(client):
    r = rhythm(client, tiny())
    exp = post(client, tiny(), image_type="decay-exp")
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["image_type"] == "rhythm-circles"
    assert set(job) == set(exp.json())
    assert job["frame_count"] == exp.json()["frame_count"] and job["window_count"] == exp.json()["window_count"]


def test_the_frames_are_png_pictures_of_the_usual_size(client):
    job = rhythm(client, pulse_wav()).json()
    assert job["frame_count"] > 20
    for i in range(job["frame_count"]):
        r = client.get(job["frame_url_template"].replace("{index}", str(i)))
        assert r.headers["content-type"] == "image/png"
        image = Image.open(io.BytesIO(r.content))
        assert image.size == (WIDTH, HEIGHT) and image.mode == "RGB"


# --- a click track end to end ---------------------------------------------------------------------------------------------------


def test_every_notch_of_every_frame_is_where_the_library_puts_it_for_the_peaks_the_job_measured(client, monkeypatch):
    spy = Spy(monkeypatch)
    job = rhythm(client, pulse_wav()).json()
    assert len(spy.results) == 1 and len(spy.rhythm_results) == 1
    peaks = spy.results[0]
    assert len(peaks.peaks) >= 8  # a click every half second for six seconds: the peaks are really there
    assert 100 < np.median([p.rate for p in peaks.peaks[1:]]) < 140  # about 120 beats per minute
    want = expected_turns(spy)
    assert want.shape == (job["frame_count"], RINGS)
    for i in range(job["frame_count"]):
        image = picture(client, job, i)
        for k in range(1, RINGS + 1):
            assert apart(notch_turns(image, k), want[i, k - 1]) * 360 < 3, (i, k)


def test_the_notch_of_the_local_peak_advances_its_rate_in_turns_a_minute_from_one_frame_to_the_next(client, monkeypatch):
    spy = Spy(monkeypatch)
    job = rhythm(client, pulse_wav()).json()
    peaks = spy.results[0]
    for first in (30, 40, 50):  # frames in the middle of the track, between peaks
        tempo = float(peaks.rate_at_time((first + 1.0) / FPS))  # the speed of the local peak circle (ring 5) there: one turn a beat
        assert 100 < tempo < 140
        gain = (notch_turns(picture(client, job, first + 1), 5) - notch_turns(picture(client, job, first), 5)) % 1.0
        assert apart(gain, tempo / 60.0 / FPS) * 360 < 8, (first, gain, tempo)  # a frame is a tenth of a second: about 72 degrees


def test_the_notch_of_the_first_and_second_tempo_rings_advances_by_a_tempo_from_76_to_144_beats_per_minute(client, monkeypatch):
    spy = Spy(monkeypatch)
    job = rhythm(client, pulse_wav()).json()
    for first in (30, 40, 50):
        for ring in (1, 3):  # the average and the raw first voted tempo
            gain = (notch_turns(picture(client, job, first + 1), ring) - notch_turns(picture(client, job, first), ring)) % 1.0
            assert 76 / 60 / FPS - 0.02 <= gain <= 144 / 60 / FPS + 0.02, (first, ring, gain)  # the tempo is a voted one (76 to 144) or the starting 120
    assert len(spy.rhythm_results) == 1


def test_the_local_peaks_settings_are_the_ones_the_peaks_are_measured_with_and_the_beat_is_not_measured_as_well(client, monkeypatch):
    from app.services.local_peaks import DEFAULT_MIN_DISTANCE, DEFAULT_PROMINENCE

    spy = Spy(monkeypatch)
    assert rhythm(client, tiny(), peak_distance="700").status_code == 200
    assert spy.calls == [(700, DEFAULT_PROMINENCE)]  # one measurement only: the beat of the other types is not measured
    assert rhythm(client, tiny()).status_code == 200
    assert spy.calls == [(700, DEFAULT_PROMINENCE), (DEFAULT_MIN_DISTANCE, DEFAULT_PROMINENCE)]
    assert (DEFAULT_MIN_DISTANCE, DEFAULT_PROMINENCE) == (350, 20)  # feature 040: the minimum distance defaults to 350 ms and the prominence is fixed at 20 percent


@pytest.mark.parametrize("image_type, measurements", [("energy-graphs", 0), ("contour", 0), ("decay", 1), ("decay-exp", 1), ("polar-chords", 1), ("chromatic-decay", 1), ("chromatic-wireframe", 1), ("rhythm-circles", 1)])
def test_the_rhythm_is_measured_for_this_type_only_and_never_a_second_time(client, monkeypatch, image_type, measurements):
    spy = Spy(monkeypatch)
    assert post(client, tiny(), image_type=image_type).status_code == 200
    assert len(spy.calls) == measurements  # the beat of the types that use it is one measurement; Rhythm Circles uses the peaks instead of the beat


def test_the_defaults_are_the_ones_of_the_other_types(client, monkeypatch):
    from app.services.local_peaks import DEFAULT_MIN_DISTANCE, DEFAULT_PROMINENCE

    spy = Spy(monkeypatch)
    assert rhythm(client, tiny()).status_code == 200
    assert spy.calls == [(DEFAULT_MIN_DISTANCE, DEFAULT_PROMINENCE)]


def test_a_different_minimum_distance_gives_different_peaks_and_different_notches_that_still_match_the_library(client, monkeypatch):
    spy = Spy(monkeypatch)
    near = rhythm(client, pulse_wav(), peak_distance="100").json()
    far = rhythm(client, pulse_wav(), peak_distance="2000").json()
    assert len(spy.results[0].peaks) > len(spy.results[1].peaks)  # clicks half a second apart cannot all stay at 2 seconds
    assert raws(client, near) != raws(client, far)
    for job, index in ((near, 0), (far, 1)):
        want = expected_turns(spy, index)
        for i in range(0, job["frame_count"], 7):
            assert apart(notch_turns(picture(client, job, i), 5), want[i, 4]) * 360 < 3, i  # the local peak circle follows the peaks


@pytest.mark.parametrize("text", ["0", "20", "100", "101", "-1", "nan", "", "abc"])
def test_a_prominence_that_is_sent_is_ignored_and_the_measurement_uses_20_percent(client, monkeypatch, text):
    spy = Spy(monkeypatch)
    r = rhythm(client, tiny(), peak_prominence=text)
    assert r.status_code == 200, r.text
    assert "peak_prominence" not in r.json()
    assert spy.calls == [(350, 20)]


@pytest.mark.parametrize("field, text, message", [
    ("peak_distance", "99", DISTANCE_MESSAGE), ("peak_distance", "2001", DISTANCE_MESSAGE), ("peak_distance", "x", DISTANCE_MESSAGE),
])
def test_a_bad_peak_setting_is_refused_with_its_message_and_nothing_is_left_behind(client, field, text, message):
    r = rhythm(client, tiny(), **{field: text})
    assert r.status_code == 400 and r.json()["detail"] == message
    assert leftovers() == []


# --- no peaks, short and silent files -------------------------------------------------------------------------------------------------


def test_a_silent_file_turns_the_three_levels_at_the_defaults_and_leaves_the_three_rate_circles_standing(client, monkeypatch):
    spy = Spy(monkeypatch)
    job = rhythm(client, wav_bytes(np.zeros(44100 * 4))).json()
    assert spy.results[0].peaks == ()
    for i in range(job["frame_count"]):
        image = picture(client, job, i)
        for k, rpm in ((1, 120.0), (3, 120.0), (5, 60.0)):  # the starting tempo 120 twice and the default rate 60 of a peak: revolutions per minute
            assert apart(notch_turns(image, k), (i + 0.5) / FPS * rpm / 60.0) * 360 < 3, (i, k)
        for k in (2, 4, 6):  # their rates of change
            assert apart(notch_turns(image, k), 0.0) * 360 < 3, (i, k)


def test_a_file_shorter_than_a_window_and_a_silent_one_give_frames_without_error(client):
    for data in (tiny(), wav_bytes(np.zeros(2000)), wav_bytes(np.zeros(44100))):
        r = rhythm(client, data)
        assert r.status_code == 200, r.text
        job = r.json()
        for i in range(job["frame_count"]):
            assert picture(client, job, i).shape == (HEIGHT, WIDTH, 3)


# --- the other settings -----------------------------------------------------------------------------------------------------------------


def test_the_settings_that_do_not_apply_are_accepted_and_change_nothing(client):
    base = rhythm(client, pulse_wav()).json()
    other = rhythm(
        client,
        pulse_wav(), threshold="7", note_count="40", resolution="2", interpolate="2", gaussian="2",
        note_layout="spiral", decay_rate="3", polar_notes="6", wave_count="3", beat_coloring="true",
    )
    assert other.status_code == 200, other.text
    other = other.json()
    assert other["frame_count"] == base["frame_count"]
    assert raws(client, base) == raws(client, other)


def test_a_bad_setting_of_another_type_is_refused_as_for_every_type(client):
    for field, text in (("threshold", "11"), ("resolution", "9"), ("decay_rate", "5")):
        r = rhythm(client, tiny(), **{field: text})
        assert r.status_code == 400, field
    assert leftovers() == []


def test_the_colormap_decides_the_colors_and_the_notch_of_the_outer_ring_is_the_opposite_end(client):
    job = rhythm(client, pulse_wav()).json()
    image = picture(client, job, 30)
    table = lookup_table(COLORMAP)
    assert (image[0, 0] == table[128]).all()  # the background is the middle row
    notch_turns(image, 1)  # finds the notch in row 255 of the colormap, the opposite end for the outer ring (it asserts that it is there)
    other = rhythm(client, pulse_wav(), colormap="viridis" if COLORMAP != "viridis" else "magma").json()
    assert raw(client, job, 30) != raw(client, other, 30)


def test_the_same_file_and_settings_give_identical_frames(client):
    first = rhythm(client, pulse_wav()).json()
    second = rhythm(client, pulse_wav()).json()
    assert raws(client, first) == raws(client, second)


# --- write_frames -------------------------------------------------------------------------------------------------------------------


def some_data(frames=6):
    return rc.RhythmData(np.linspace(0.0, 1.7, frames * 6).reshape(frames, 6))


def test_write_frames_draws_the_same_bytes_as_write_rhythm_frames(tmp_path):
    data = some_data()
    write_frames(np.zeros((6, 88)), tmp_path / "out", colormap=COLORMAP, image_type="rhythm-circles", rhythm=data)
    rc.write_rhythm_frames(data, COLORMAP, tmp_path / "expected", WIDTH, HEIGHT)
    for i in range(6):
        assert (tmp_path / "out" / f"frame_{i:06d}.png").read_bytes() == (tmp_path / "expected" / f"frame_{i:06d}.png").read_bytes()


def test_write_frames_needs_the_data_before_it_writes_anything(tmp_path):
    with pytest.raises(ValueError) as error:
        write_frames(np.zeros((3, 88)), tmp_path / "out", colormap=COLORMAP, image_type="rhythm-circles")
    assert str(error.value) == "Rhythm Circles needs the rhythm data."
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("frames", [2, 4])
def test_write_frames_needs_the_right_number_of_frames(tmp_path, frames):
    with pytest.raises(ValueError) as error:
        write_frames(np.zeros((3, 88)), tmp_path / "out", colormap=COLORMAP, image_type="rhythm-circles", rhythm=some_data(frames))
    assert str(error.value) == f"The rhythm data has {frames} frames but 3 were given."
    assert not (tmp_path / "out").exists()


def test_write_frames_ignores_the_data_for_another_type(tmp_path):
    values = np.zeros((3, 88))
    write_frames(values, tmp_path / "with", colormap=COLORMAP, image_type="decay-exp", rhythm=some_data(3))
    write_frames(values, tmp_path / "without", colormap=COLORMAP, image_type="decay-exp")
    for i in range(3):
        assert (tmp_path / "with" / f"frame_{i:06d}.png").read_bytes() == (tmp_path / "without" / f"frame_{i:06d}.png").read_bytes()


# --- the Vote limit of the voted tempos (feature 047; the Extra notes play no part since the fourth round) -----------------------------------------------------------------

VOTE_MESSAGE = "The vote limit must be a whole number from 1 to 100."


def test_the_job_calls_rhythm_angles_with_the_60_ms_windows_the_two_channels_and_the_vote_limit_and_measures_the_peaks_once(client, monkeypatch):
    spy = Spy(monkeypatch)
    job = rhythm(client, pulse_wav()).json()
    assert len(spy.calls) == 1 and len(spy.rhythm_calls) == 1
    peaks, fps, frames, values, left, right, limit = spy.rhythm_calls[0]
    assert peaks is spy.results[0] and fps == FPS and frames == job["frame_count"]
    assert values.ndim == 2 and values.shape[1] == 88 and limit == 40  # the default (20 until the fifth round of feature 047)
    assert left.ndim == 1 and left.shape == right.shape and left.shape[0] > 0  # the two channels of the file, to place the starts on the waveform
    assert values.shape[0] != frames  # the windows of the analysis (one every 60 ms), not the frames
    assert job["extra_notes"] == 2 and job["vote_limit"] == 40  # the default Vote limit since the fifth round of feature 047


def test_the_vote_limit_that_is_sent_is_used_and_echoed(client, monkeypatch):
    spy = Spy(monkeypatch)
    job = rhythm(client, tiny(), vote_limit="5").json()
    assert job["vote_limit"] == 5 and spy.rhythm_calls[0][6] == 5
    job = rhythm(client, tiny(), vote_limit="100", extra_notes="5").json()
    assert job["vote_limit"] == 100 and job["extra_notes"] == 5 and spy.rhythm_calls[1][6] == 100


def test_the_extra_notes_do_not_change_the_rhythm_circles(client, monkeypatch):
    spy = Spy(monkeypatch)
    for extra in ("1", "3", "5"):
        assert rhythm(client, pulse_wav(), extra_notes=extra).json()["extra_notes"] == int(extra)  # still accepted and echoed
    first, *others = spy.rhythm_results
    assert all(np.array_equal(first.angles, other.angles) for other in others)  # the starts are not found among the loudest notes any more


@pytest.mark.parametrize("text", ["0", "101", "2.5", "abc", "", "nan", "inf", "-1", "1e3"])
def test_a_vote_limit_that_is_not_a_whole_number_from_1_to_100_is_refused_before_the_file_is_read_and_nothing_is_left_behind(client, monkeypatch, text):
    spy = Spy(monkeypatch)
    r = rhythm(client, tiny(), vote_limit=text)
    assert r.status_code == 400 and r.json()["detail"] == VOTE_MESSAGE
    assert leftovers() == [] and spy.calls == []  # nothing was measured: the file was not read


@pytest.mark.parametrize("image_type", IMAGE_TYPES)
def test_the_vote_limit_is_checked_and_echoed_for_every_image_type(client, image_type):
    ok = post(client, tiny(), image_type=image_type, vote_limit="7")
    assert ok.status_code == 200 and ok.json()["vote_limit"] == 7
    assert post(client, tiny(), image_type=image_type).json()["vote_limit"] == 40  # the default
    bad = post(client, tiny(), image_type=image_type, vote_limit="0")
    assert bad.status_code == 400 and bad.json()["detail"] == VOTE_MESSAGE


def test_the_extra_notes_of_rhythm_circles_are_accepted_up_to_8_like_a_picture_that_ignores_them(client):
    for value in ("5", "6", "8"):
        assert rhythm(client, tiny(), extra_notes=value).status_code == 200
    r = rhythm(client, tiny(), extra_notes="9")
    assert r.status_code == 400 and r.json()["detail"] == "The extra notes must be a whole number from 1 to 8."


def test_a_different_vote_limit_changes_the_pictures_of_a_file_whose_spacing_changes(client):
    low = rhythm(client, changing_notes_wav(), vote_limit="2").json()
    high = rhythm(client, changing_notes_wav(), vote_limit="100").json()
    assert raws(client, low) != raws(client, high)


def tone(seconds, hertz=440.0, rate=44100):
    time = np.arange(int(seconds * rate)) / rate
    return 0.5 * np.sin(2 * np.pi * hertz * time) * np.minimum(1.0, np.minimum(time, seconds - time) * 200)


def changing_notes_wav():
    """Notes of different pitch every 0.4 s for 12 s, then every 0.65 s for 12 s, as a WAV (the spacing changes, so the two limits rank the tempos differently)."""
    rate = 44100
    pieces = []
    for index in range(30):
        pieces.append(tone(0.4, 220.0 * 2 ** ((index * 5 % 12) / 12), rate))
    for index in range(18):
        pieces.append(tone(0.65, 220.0 * 2 ** ((index * 7 % 12) / 12), rate))
    return wav_bytes(np.concatenate(pieces))


def test_the_other_image_types_make_the_same_pictures_whatever_the_vote_limit(client):
    for image_type in ("decay", "contour", "polychord"):
        one = post(client, tiny(), image_type=image_type, vote_limit="1").json()
        hundred = post(client, tiny(), image_type=image_type, vote_limit="100").json()
        assert raws(client, one) == raws(client, hundred), image_type
