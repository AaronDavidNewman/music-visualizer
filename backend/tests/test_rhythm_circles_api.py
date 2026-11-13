"""The ``rhythm-circles`` image type through ``POST /api/jobs``: the type, the local peaks settings, a click track end to end, silence, the ignored settings (feature 038)."""

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
PROMINENCE_MESSAGE = "The prominence must be a number from 0 to 100 percent."
FPS = 10
OUTER = HEIGHT / 2 - 10  # the outer radius of the first ring: 190
RINGS = 8
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
    return int(np.rint((1 - (k - 1) / 7) * 255))


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
    """Keeps the local peaks the job measured and the arguments it measured them with."""

    def __init__(self, monkeypatch):
        import app.routers.jobs as jobs

        self.calls, self.results = [], []
        real = jobs.measure_local_peaks

        def spy(left, right, rate, distance, prominence):
            self.calls.append((distance, prominence))
            self.results.append(real(left, right, rate, distance, prominence))
            return self.results[-1]

        monkeypatch.setattr(jobs, "measure_local_peaks", spy)


def expected_turns(peaks, job):
    return rc.rhythm_angles(peaks, FPS, job["frame_count"]).angles % 1.0


# --- choosing it --------------------------------------------------------------------------------------------------------------


def test_rhythm_circles_is_the_seventh_image_type_and_the_message_lists_all_eight():
    assert IMAGE_TYPES[6] == "rhythm-circles" and len(IMAGE_TYPES) == 8
    assert TYPE_MESSAGE.endswith("polar-chords, energy-graphs, chromatic-decay, rhythm-circles, chromatic-wireframe.")


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
    assert len(spy.results) == 1
    peaks = spy.results[0]
    assert len(peaks.peaks) >= 8  # a click every half second for six seconds: the peaks are really there
    assert 100 < np.median([p.rate for p in peaks.peaks[1:]]) < 140  # about 120 beats per minute
    want = expected_turns(peaks, job)
    for i in range(job["frame_count"]):
        image = picture(client, job, i)
        for k in range(1, RINGS + 1):
            assert apart(notch_turns(image, k), want[i, k - 1]) * 360 < 3, (i, k)


def test_the_outer_notch_advances_the_tempo_in_turns_a_minute_from_one_frame_to_the_next(client, monkeypatch):
    spy = Spy(monkeypatch)
    job = rhythm(client, pulse_wav()).json()
    peaks = spy.results[0]
    for first in (30, 40, 50):  # frames in the middle of the track, between peaks
        tempo = float(peaks.rate_at_time((first + 1.0) / FPS))  # the speed of the outer circle there: one turn a beat
        assert 100 < tempo < 140
        gain = (notch_turns(picture(client, job, first + 1), 1) - notch_turns(picture(client, job, first), 1)) % 1.0
        assert apart(gain, tempo / 60.0 / FPS) * 360 < 8, (first, gain, tempo)  # a frame is a tenth of a second: about 72 degrees


def test_the_local_peaks_settings_are_the_ones_the_peaks_are_measured_with_and_the_beat_is_not_measured_as_well(client, monkeypatch):
    from app.services.local_peaks import DEFAULT_MIN_DISTANCE, DEFAULT_PROMINENCE

    spy = Spy(monkeypatch)
    assert rhythm(client, tiny(), peak_distance="700", peak_prominence="30").status_code == 200
    assert spy.calls == [(700, 30)]  # one measurement only: the beat of the other types is not measured
    assert rhythm(client, tiny()).status_code == 200
    assert spy.calls == [(700, 30), (DEFAULT_MIN_DISTANCE, DEFAULT_PROMINENCE)]


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
    for job, peaks in ((near, spy.results[0]), (far, spy.results[1])):
        want = expected_turns(peaks, job)
        for i in range(0, job["frame_count"], 7):
            assert apart(notch_turns(picture(client, job, i), 1), want[i, 0]) * 360 < 3, i


def test_a_different_prominence_gives_different_peaks_and_different_notches_that_still_match_the_library(client, monkeypatch):
    spy = Spy(monkeypatch)
    low = rhythm(client, pulse_wav(), peak_prominence="0").json()
    high = rhythm(client, pulse_wav(), peak_prominence="100").json()
    assert len(spy.results[0].peaks) != len(spy.results[1].peaks)
    assert raws(client, low) != raws(client, high)
    for job, peaks in ((low, spy.results[0]), (high, spy.results[1])):
        want = expected_turns(peaks, job)
        for i in range(0, job["frame_count"], 7):
            assert apart(notch_turns(picture(client, job, i), 1), want[i, 0]) * 360 < 3, i


@pytest.mark.parametrize("field, text, message", [
    ("peak_distance", "99", DISTANCE_MESSAGE), ("peak_distance", "2001", DISTANCE_MESSAGE), ("peak_distance", "x", DISTANCE_MESSAGE),
    ("peak_prominence", "-1", PROMINENCE_MESSAGE), ("peak_prominence", "101", PROMINENCE_MESSAGE), ("peak_prominence", "nan", PROMINENCE_MESSAGE),
])
def test_a_bad_peak_setting_is_refused_with_its_message_and_nothing_is_left_behind(client, field, text, message):
    r = rhythm(client, tiny(), **{field: text})
    assert r.status_code == 400 and r.json()["detail"] == message
    assert leftovers() == []


# --- no peaks, short and silent files -------------------------------------------------------------------------------------------------


def test_a_silent_file_turns_the_tempo_and_its_fastest_tempos_a_turn_a_second_and_leaves_the_four_rate_circles_standing(client, monkeypatch):
    spy = Spy(monkeypatch)
    job = rhythm(client, wav_bytes(np.zeros(44100 * 4))).json()
    assert spy.results[0].peaks == ()
    for i in range(job["frame_count"]):
        image = picture(client, job, i)
        for k in (1, 3, 5, 7):  # the fastest tempos of 8, 4 and 2 peaks and the tempo: 60 beats per minute, a turn a second
            assert apart(notch_turns(image, k), (i + 0.5) / FPS) * 360 < 3, (i, k)
        for k in (2, 4, 6, 8):  # their rates of change
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
        pulse_wav(),
        smoothing="0.5", smoothing_window="4", threshold="7", note_count="40", resolution="2", interpolate="2", gaussian="2",
        note_layout="spiral", decay_rate="3", polar_notes="6", wave_count="3", beat_coloring="true",
    )
    assert other.status_code == 200, other.text
    other = other.json()
    assert other["frame_count"] == base["frame_count"]
    assert raws(client, base) == raws(client, other)


def test_a_bad_setting_of_another_type_is_refused_as_for_every_type(client):
    for field, text in (("smoothing", "0.9"), ("threshold", "11"), ("resolution", "9"), ("decay_rate", "5")):
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
    return rc.RhythmData(np.linspace(0.0, 1.7, frames * 8).reshape(frames, 8))


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
