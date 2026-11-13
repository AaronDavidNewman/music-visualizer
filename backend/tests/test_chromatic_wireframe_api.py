"""The ``chromatic-wireframe`` image type through ``POST /api/jobs``: the type, the points of Chromatic Decay, the per-type decay rate, the ignored settings (feature 039)."""

import io

import numpy as np
import pytest
from PIL import Image

from app.services import chromatic_decay as cd
from app.services import chromatic_wireframe as cw
from app.services.frame_rendering import smooth_frames, write_frames
from app.services.image_types import IMAGE_TYPES
from app.services.local_peaks import DEFAULT_MIN_DISTANCE, DEFAULT_PROMINENCE, measure_local_peaks

from .frame_size import HEIGHT, WIDTH
from .test_chromatic_decay_api import C4, E4, SAMPLES, WINDOWS, loud_and_faint_file, tone_file  # noqa: F401
from .test_jobs_api import client, leftovers, note_tone, wav_bytes  # noqa: F401
from .test_peak_tile_colors_api import COLORMAP, post, pulse_wav
from .test_resolution_api import tiny

TYPE = "chromatic-wireframe"
TYPE_MESSAGE = f"The image type must be one of {', '.join(IMAGE_TYPES)}."
RATE_MESSAGE = "The decay rate must be a whole number from 1 to 10."
OLD_RATE_MESSAGE = "The decay rate must be a number from 0.25 to 4 in steps of 0.25."
THRESHOLD_MESSAGE = "The threshold must be a number from 0 to 10."
DISTANCE_MESSAGE = "The minimum distance must be a number from 100 to 2000 milliseconds."


def wireframe(client, data=None, **fields):
    return post(client, data, image_type=TYPE, **fields)


def picture(client, job, index):
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    assert r.status_code == 200
    return np.asarray(Image.open(io.BytesIO(r.content)).convert("RGB"))


def frames(client, job):
    return [picture(client, job, i) for i in range(job["frame_count"])]


def served_bytes(client, job):
    return [client.get(job["frame_url_template"].replace("{index}", str(i))).content for i in range(job["frame_count"])]


def spying(monkeypatch):
    """Record the arguments the job gives ``write_frames`` (and call the real one)."""
    import app.routers.jobs as jobs

    calls = []
    real = jobs.write_frames

    def spy(values, directory, **kwargs):
        calls.append((np.array(values), kwargs))
        return real(values, directory, **kwargs)

    monkeypatch.setattr(jobs, "write_frames", spy)
    return calls


# --- choosing it --------------------------------------------------------------------------------------------------------------


def test_it_is_the_thirteenth_image_type_and_the_message_lists_all_thirteen():
    assert IMAGE_TYPES[-1] == TYPE and len(IMAGE_TYPES) == 13
    assert TYPE_MESSAGE.endswith("chromatic-decay, rhythm-circles, chromatic-wireframe.")


def test_the_chromatic_types_are_exactly_the_two_that_share_the_points_and_the_settings():
    assert cd.CHROMATIC_TYPES == ("chromatic-decay", "chromatic-wireframe")


@pytest.mark.parametrize("name", ["chromatic_wireframe", "chromaticwireframe", "Chromatic-Wireframe", "chromatic-wireframe ", "wireframe", "chromatic-wire", "CHROMATIC-WIREFRAME", ""])
def test_a_name_that_is_not_exactly_chromatic_wireframe_is_refused_with_the_thirteen_names(client, name):
    r = post(client, tiny(), image_type=name)
    assert r.status_code == 400 and r.json()["detail"] == TYPE_MESSAGE
    assert leftovers() == []


def test_it_is_accepted_and_echoed_and_the_response_has_no_new_field(client):
    r = wireframe(client, tiny())
    assert r.status_code == 200, r.text
    job = r.json()
    other = post(client, tiny(), image_type="chromatic-decay").json()
    assert job["image_type"] == TYPE
    assert set(job) == set(other)  # no new response field
    assert job["frame_count"] == other["frame_count"] and job["window_count"] == other["window_count"]


def test_the_frames_are_png_pictures_of_the_usual_size(client):
    job = wireframe(client, tone_file()).json()
    for i in range(job["frame_count"]):
        r = client.get(job["frame_url_template"].replace("{index}", str(i)))
        assert r.headers["content-type"] == "image/png"
        assert Image.open(io.BytesIO(r.content)).size == (WIDTH, HEIGHT)


# --- the points are those of Chromatic Decay ---------------------------------------------------------------------------------------


def expected_frames(tmp_path, values, kwargs, name="expected"):
    """What the library draws from the arguments the job gave ``write_frames``: the points of Chromatic Decay and the wireframe of them."""
    smoothed = smooth_frames(values, kwargs["smoothing"], kwargs["smoothing_window"])
    points = cd.circle_points(smoothed, kwargs["beat"], kwargs["decay_rate"], kwargs["threshold"])
    cw.write_wireframe_frames(points, kwargs["colormap"], tmp_path / name, WIDTH, HEIGHT, kwargs["beat"])
    return points, [(tmp_path / name / f"frame_{i:06d}.png").read_bytes() for i in range(points.shape[0])]


@pytest.mark.parametrize("fields", [{}, {"decay_rate": "3"}, {"decay_rate": "10", "threshold": "2", "smoothing": "0.3"}])
def test_the_job_draws_the_points_of_chromatic_decay_for_the_same_file_and_settings(client, tmp_path, monkeypatch, fields):
    calls = spying(monkeypatch)
    data = pulse_wav()
    job = wireframe(client, data, **fields).json()
    decay = post(client, data, image_type="chromatic-decay", **fields).json()
    (values, kwargs), (values2, kwargs2) = calls
    assert kwargs["image_type"] == TYPE and kwargs2["image_type"] == "chromatic-decay"
    assert np.array_equal(values, values2)  # the same note values, beat, rate and threshold go to both
    for key in ("beat", "decay_rate", "threshold", "smoothing", "smoothing_window", "colormap"):
        assert np.array_equal(kwargs[key], kwargs2[key]), key
    assert kwargs["beat"] is not None  # the beat is measured for this type
    points, expected = expected_frames(tmp_path, values, kwargs)
    served = served_bytes(client, job)
    assert served == expected
    assert points.max() > 0  # something was drawn
    assert len(set(served)) > 1


def test_the_lines_take_their_colors_from_the_beat_of_the_local_peaks(client, tmp_path, monkeypatch):
    calls = spying(monkeypatch)
    wireframe(client, pulse_wav())
    _, kwargs = calls[0]
    beat = np.asarray(kwargs["beat"])
    assert beat.max() > 0 and len(np.unique(beat)) > 2  # a click track has a beat
    colors = cw.line_colors(beat, kwargs["colormap"])
    assert len({tuple(c) for c in colors}) > 2  # the lines have different colors


def test_the_beat_is_measured_with_the_local_peaks_settings(client, monkeypatch):
    import app.routers.jobs as jobs

    seen = []
    real = jobs.measure_local_peaks

    def spy(left, right, rate, distance, prominence):
        seen.append((distance, prominence))
        return real(left, right, rate, distance, prominence)

    monkeypatch.setattr(jobs, "measure_local_peaks", spy)
    assert wireframe(client, tiny(), peak_distance="700", peak_prominence="30").status_code == 200
    assert seen == [(700, 30)]


def test_the_local_peaks_settings_change_the_frames(client):
    data = pulse_wav()
    near = served_bytes(client, wireframe(client, data, peak_distance="100", peak_prominence="0").json())
    far = served_bytes(client, wireframe(client, data, peak_distance="2000", peak_prominence="90").json())
    assert near != far


def test_the_local_peaks_settings_are_validated_as_always(client):
    r = wireframe(client, tiny(), peak_distance="50")
    assert r.status_code == 400 and r.json()["detail"] == DISTANCE_MESSAGE
    assert leftovers() == []


# --- the decay rate: a whole number from 1 to 10 for this type, as for Chromatic Decay ---------------------------------------------


def test_the_decay_rate_is_1_when_not_sent(client):
    rate = wireframe(client, tiny()).json()["decay_rate"]
    assert rate == 1 and isinstance(rate, int)


@pytest.mark.parametrize("text, value", [(str(n), n) for n in range(1, 11)] + [("3.0", 3), ("10.0", 10)])
def test_a_whole_number_from_1_to_10_is_accepted_and_echoed_as_an_integer(client, text, value):
    job = wireframe(client, tiny(), decay_rate=text).json()
    assert job["decay_rate"] == value and isinstance(job["decay_rate"], int)


@pytest.mark.parametrize("text", ["0", "11", "2.5", "0.5", "0.25", "-1", "", "x", "nan", "inf", " ", "1,5", "100"])
def test_anything_else_is_refused_with_the_message_before_the_file_is_read_and_nothing_is_left_behind(client, text):
    r = wireframe(client, tiny(), decay_rate=text)
    assert r.status_code == 400 and r.json()["detail"] == RATE_MESSAGE, text
    assert leftovers() == []


def test_a_bad_rate_is_refused_before_the_file_is_read_even_without_a_file(client):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": TYPE, "decay_rate": "11"})
    assert r.status_code == 400 and r.json()["detail"] == RATE_MESSAGE


@pytest.mark.parametrize("image_type", ["tiles", "decay", "decay-exp", "polar-chords", "energy-graphs", "rhythm-circles"])
def test_the_other_types_keep_their_own_range_and_message(client, image_type):
    for text in ("5", "10", "4.5", "0"):
        r = post(client, tiny(), image_type=image_type, decay_rate=text)
        assert r.status_code == 400 and r.json()["detail"] == OLD_RATE_MESSAGE, (image_type, text)
    assert post(client, tiny(), image_type=image_type, decay_rate="0.25").status_code == 200
    assert wireframe(client, tiny(), decay_rate="0.25").status_code == 400


@pytest.mark.parametrize("bad", [0, 11, 2.5, 0.5, True, "3", None])
def test_write_frames_refuses_a_bad_rate_for_this_type_before_writing_anything(tmp_path, bad):
    with pytest.raises(ValueError) as error:
        write_frames(np.zeros((2, 88)), tmp_path / "out", colormap=COLORMAP, image_type=TYPE, decay_rate=bad)
    assert str(error.value) == RATE_MESSAGE
    assert not (tmp_path / "out").exists()


# --- the threshold applies, as for Chromatic Decay ---------------------------------------------------------------------------------


def test_the_threshold_applies(client):
    data = loud_and_faint_file()
    plain = served_bytes(client, wireframe(client, data).json())
    high = served_bytes(client, wireframe(client, data, threshold="5").json())
    assert plain != high  # the faint note (2 percent of the loudest) is silent above 5 percent
    assert wireframe(client, data, threshold="5").json()["threshold"] == 5


@pytest.mark.parametrize("text", ["-1", "11", "x", "", "nan"])
def test_a_threshold_outside_0_to_10_is_refused_with_the_message(client, text):
    r = wireframe(client, tiny(), threshold=text)
    assert r.status_code == 400 and r.json()["detail"] == THRESHOLD_MESSAGE
    assert leftovers() == []


# --- write_frames ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("with_beat", [False, True])
@pytest.mark.parametrize("rate, threshold", [(1, 0), (4, 5)])
def test_write_frames_draws_the_wireframe_of_the_points_of_chromatic_decay(tmp_path, with_beat, rate, threshold):
    values = np.zeros((10, 88))
    values[:, C4] = 100.0
    values[:, E4] = 4.0
    beat = np.linspace(0.0, 1.0, 10) if with_beat else None
    write_frames(values, tmp_path / "out", colormap=COLORMAP, image_type=TYPE, decay_rate=rate, threshold=threshold, beat=beat)
    expected = tmp_path / "expected"
    cw.write_wireframe_frames(cd.circle_points(values, beat, rate, threshold), COLORMAP, expected, WIDTH, HEIGHT, beat)
    for i in range(10):
        assert (tmp_path / "out" / f"frame_{i:06d}.png").read_bytes() == (expected / f"frame_{i:06d}.png").read_bytes()


def test_write_frames_needs_no_extra_data_and_does_not_read_rhythm_or_energy(tmp_path):
    write_frames(np.zeros((3, 88)), tmp_path / "out", colormap=COLORMAP, image_type=TYPE)
    assert len(list((tmp_path / "out").iterdir())) == 3


def test_the_other_image_types_never_reach_the_wireframe(tmp_path, monkeypatch):
    import app.services.frame_rendering as fr

    def refuse(*args, **kwargs):
        raise AssertionError("the wireframe was drawn for another type")

    monkeypatch.setattr(fr, "write_wireframe_frames", refuse)
    values = np.zeros((3, 88))
    values[:, C4] = 2.0
    for image_type in ("tiles", "blended", "contour", "circles", "circles_paint", "concentric", "decay", "decay-exp", "polar-chords", "chromatic-decay"):
        write_frames(values, tmp_path / image_type, colormap=COLORMAP, image_type=image_type, beat=np.zeros(3))


# --- the settings that apply and the ones that do not ------------------------------------------------------------------------------

SETTINGS = [
    {"note_layout": "spiral"},
    {"decay_low": "2", "decay_medium": "2.5", "decay_high": "3", "decay_saturated": "1"},
    {"note_count": "20"},
    {"resolution": "3", "interpolate": "2", "gaussian": "1"},
    {"polar_notes": "7", "blend_width": "15", "wave_count": "6"},
    {"beat_coloring": "true"},
]


@pytest.mark.parametrize("fields", SETTINGS)
def test_the_settings_that_do_not_apply_are_accepted_and_change_nothing(client, fields):
    plain = served_bytes(client, wireframe(client, tone_file()).json())
    other = wireframe(client, tone_file(), **fields)
    assert other.status_code == 200, other.text
    assert served_bytes(client, other.json()) == plain


def test_a_setting_of_another_type_that_is_not_allowed_is_refused_as_for_every_type(client):
    r = wireframe(client, tiny(), note_layout="diagonal")
    assert r.status_code == 400
    assert leftovers() == []


def test_the_data_smoothing_applies(client):
    data = pulse_wav()
    plain = served_bytes(client, wireframe(client, data).json())
    smooth = served_bytes(client, wireframe(client, data, smoothing="0.6", smoothing_window="5").json())
    assert plain != smooth


def test_the_colormap_decides_the_colors(client):
    one = picture(client, wireframe(client, tone_file()).json(), 10)
    two = picture(client, wireframe(client, tone_file(), colormap="hot").json(), 10)
    assert not np.array_equal(one, two)


@pytest.mark.parametrize("seconds", [0.0, 0.05, 0.3])
def test_a_silent_file_or_one_shorter_than_a_window_gives_pictures_without_error(client, seconds):
    r = wireframe(client, wav_bytes(np.zeros(int(22050 * seconds) + 1)))
    assert r.status_code == 200, r.text
    job = r.json()
    for i in range(job["frame_count"]):
        assert picture(client, job, i).shape == (HEIGHT, WIDTH, 3)


def test_the_same_file_and_settings_make_identical_frames(client):
    first = served_bytes(client, wireframe(client, pulse_wav(), decay_rate="3").json())
    second = served_bytes(client, wireframe(client, pulse_wav(), decay_rate="3").json())
    assert first == second


def test_a_steady_tone_changes_the_line_through_the_circle_of_its_letter(client, tmp_path, monkeypatch):
    calls = spying(monkeypatch)
    wireframe(client, tone_file(C4))
    values, kwargs = calls[0]
    points, _ = expected_frames(tmp_path, values, kwargs)
    last = points[-1]
    assert last[3] == last.max() and last[3] > 5  # the letter C (3, counting from A) is charged most
    radii = cd.circle_radii(last, WIDTH, HEIGHT)
    assert radii[3] == radii.max() and radii[3] > radii[8]  # its circle is the largest, so its sine is the strongest in the sum
    _, loud = cw.line_heights(last, WIDTH, HEIGHT)
    _, quiet = cw.line_heights(np.zeros(12), WIDTH, HEIGHT)
    assert np.abs(loud - quiet).max() > 1  # the line is not that of a silent frame
