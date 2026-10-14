"""The contour image type through the job endpoint: ``image_type=contour``, its refusals, the response, the Blend width
that it ignores, and the frames that are served, combined with the other settings.

No colormap is named and no number of contour levels is assumed (see ``colormap_names.py`` and ``test_contour.py``).
"""

import io

import numpy as np
import pytest
from PIL import Image

from app.services.colormaps import COLORMAPS, lookup_table
from app.services.image_types import IMAGE_TYPES

from .colormap_names import FIRST, SECOND
from .test_contour import near_scale
from .test_jobs_api import (  # noqa: F401
    SR,
    chord_wav,
    client,
    frame_rgb,
    leftovers,
    note_tone,
    wav_bytes,
)

TYPE_MESSAGE = f"The image type must be one of {', '.join(IMAGE_TYPES)}."
REMOVED = ("energy", "brightness", "hue_step", "saturation_step", "brightness_step")


def post(client, data=None, **fields):
    form = {"window_size": "4096", "frame_rate": "10", "image_type": "contour", **fields}
    return client.post("/api/jobs", files={"file": ("song.wav", data or chord_wav(2), "audio/wav")}, data=form)


def frame_bytes(client, job, index):
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    assert r.status_code == 200
    return r.content


def frame_image(client, job, index):
    return np.asarray(Image.open(io.BytesIO(frame_bytes(client, job, index))))


def tiny():
    return wav_bytes(np.zeros(22050))


# --- choosing it ------------------------------------------------------------------------------------------------------


def test_contour_is_one_of_the_offered_types_and_tiles_stays_the_default():
    assert "contour" in IMAGE_TYPES
    assert IMAGE_TYPES[0] == "tiles"


@pytest.mark.parametrize("name", COLORMAPS)
def test_contour_is_accepted_and_echoed_with_every_colormap(client, name):
    r = post(client, tiny(), colormap=name)
    assert r.status_code == 200, r.text
    assert r.json()["image_type"] == "contour"
    assert r.json()["colormap"] == name


def test_the_response_has_the_usual_keys_and_nothing_extra_for_contour(client):
    job = post(client, tiny()).json()
    assert set(job) == {
        "job_id", "file_name", "sample_rate", "duration_seconds", "window_size", "frame_rate", "frame_count",
        "smoothing", "smoothing_window", "threshold", "image_type", "blend_width", "colormap", "resolution", "note_count", "interpolate",
        "circle_unit", "circle_memory", "circle_notes", "circle_size", "circle_resize", "window_spacing",
        "step_samples", "window_count", "spacing_raised", "frame_url_template",
    }  # fmt: skip
    for key in REMOVED:
        assert key not in job


def test_the_frames_are_252_by_168_pngs_and_their_count_and_timing_equal_those_of_tiles(client):
    data = chord_wav(2)
    cont = post(client, data).json()
    tiles = post(client, data, image_type="tiles").json()
    assert cont["frame_count"] == tiles["frame_count"] > 0
    for key in ("frame_rate", "window_size", "duration_seconds", "step_samples", "window_count"):
        assert cont[key] == tiles[key]
    for i in (0, cont["frame_count"] // 2, cont["frame_count"] - 1):
        image = Image.open(io.BytesIO(frame_bytes(client, cont, i)))
        assert image.format == "PNG" and image.size == (252, 168)


@pytest.mark.parametrize(
    "text", ["", " ", "Contour", "CONTOUR", " contour", "contour ", "contours", "contour,tiles", "gradient", "1"]
)
def test_any_other_image_type_is_refused_with_the_three_names(client, text):
    before = leftovers()
    r = client.post(
        "/api/jobs",
        files={"file": ("song.wav", tiny(), "audio/wav")},
        data={"window_size": "4096", "frame_rate": "10", "image_type": text},
    )
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == TYPE_MESSAGE
    assert "tiles" in TYPE_MESSAGE and "blended" in TYPE_MESSAGE and "contour" in TYPE_MESSAGE
    assert leftovers() == before  # no job was created


def test_the_type_is_checked_before_the_file_is_read(client):
    r = client.post(
        "/api/jobs",
        files={"file": ("song.wav", b"this is not audio", "audio/wav")},
        data={"window_size": "4096", "frame_rate": "10", "image_type": "Contour"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == TYPE_MESSAGE


# --- the blend width --------------------------------------------------------------------------------------------------


def test_a_blend_width_sent_with_contour_is_accepted_and_has_no_effect(client):
    data = chord_wav(2)
    a = post(client, data, blend_width="10")
    b = post(client, data, blend_width="25")
    assert a.status_code == b.status_code == 200
    a, b = a.json(), b.json()
    assert a["blend_width"] == 10 and b["blend_width"] == 25  # reported as sent, as for tiles
    for i in range(0, a["frame_count"], 3):
        assert frame_bytes(client, a, i) == frame_bytes(client, b, i)


@pytest.mark.parametrize("width", ["9", "26", "", "abc", "nan"])
def test_an_invalid_blend_width_is_still_refused_with_contour(client, width):
    r = post(client, tiny(), blend_width=width)
    assert r.status_code == 400
    assert r.json()["detail"] == "The blend width must be a number from 10 to 25."


# --- the other types are not changed --------------------------------------------------------------------------------------


def test_tiles_and_blended_do_not_depend_on_contour_having_been_made_before(client):
    data = chord_wav(2)
    before = {t: post(client, data, image_type=t).json() for t in ("tiles", "blended")}
    contour = post(client, data).json()
    after = {t: post(client, data, image_type=t).json() for t in ("tiles", "blended")}
    assert contour["image_type"] == "contour"
    for t in ("tiles", "blended"):
        for i in range(0, before[t]["frame_count"], 4):
            assert frame_bytes(client, before[t], i) == frame_bytes(client, after[t], i)


def test_missing_image_type_is_still_tiles(client):
    job = client.post(
        "/api/jobs", files={"file": ("song.wav", tiny(), "audio/wav")}, data={"window_size": "4096", "frame_rate": "10"}
    ).json()
    assert job["image_type"] == "tiles"


# --- with the other settings --------------------------------------------------------------------------------------------


def steady_note_file(note=36, seconds=3.0):
    audio = note_tone(note, seconds)
    return wav_bytes(audio, audio)


@pytest.mark.parametrize("name", COLORMAPS)
def test_a_steady_note_is_one_contour_peak_at_its_place_in_the_grid_for_every_colormap(client, name):
    # note 36 is row 3, column 0 of the grid: the loudest note of the file, so the end of the scale at its grid point and
    # the start of it in the opposite corner
    job = post(client, steady_note_file(36), colormap=name).json()
    picture = frame_image(client, job, job["frame_count"] // 2)
    assert near_scale(picture[round(3 / 6 * 167), 0][:3], name, 1.0), name
    assert near_scale(picture[167, 251][:3], name, 0.0), name


def test_changing_the_colormap_changes_the_pictures_and_not_the_frame_count(client):
    if FIRST == SECOND:
        pytest.skip("only one colormap is offered")
    data = chord_wav(2)
    a = post(client, data, colormap=FIRST).json()
    b = post(client, data, colormap=SECOND).json()
    assert a["frame_count"] == b["frame_count"]
    assert any(frame_bytes(client, a, i) != frame_bytes(client, b, i) for i in range(a["frame_count"]))


def test_smoothing_with_a_window_keeps_a_trace_of_a_note_after_it_stops(client):
    tone = np.concatenate([note_tone(36, 1.0), np.zeros(SR)])  # one second of sound, one of silence: 20 frames at 10 per second
    data = wav_bytes(tone, tone)
    plain = post(client, data, smoothing="0", frame_rate="10").json()
    smooth = post(client, data, smoothing="0.8", smoothing_window="8", frame_rate="10").json()
    flat = lambda img: len({tuple(p) for p in img[..., :3].reshape(-1, 3).tolist()}) == 1  # noqa: E731
    assert plain["frame_count"] == smooth["frame_count"] == 20
    # without smoothing the picture is flat (nothing sounds) from the frame after the tone; with a window of 8 it keeps a
    # trace for 8 more frames and then is flat again
    assert all(flat(frame_image(client, plain, i)) for i in range(11, 20))
    assert not any(flat(frame_image(client, smooth, i)) for i in range(0, 16))
    assert flat(frame_image(client, smooth, 19))


def test_a_threshold_changes_the_contour_by_hiding_a_faint_note(client):
    loud, faint = note_tone(36, 3.0), note_tone(48, 3.0) * 0.03  # a faint note an octave up, next to the loud one in the grid
    data = wav_bytes(loud + faint, loud + faint)
    hidden = post(client, data, threshold="5").json()
    shown = post(client, data, threshold="0").json()
    middle = hidden["frame_count"] // 2
    assert frame_bytes(client, hidden, middle) != frame_bytes(client, shown, middle)
    # and a threshold that hides nothing (the faint note is above it) changes nothing
    assert frame_bytes(client, post(client, data, threshold="0.1").json(), middle) == frame_bytes(client, shown, middle)


@pytest.mark.parametrize("name", COLORMAPS)
def test_a_silent_file_gives_flat_frames_of_the_first_color_of_the_colormap(client, name):
    data = wav_bytes(np.zeros(SR), np.zeros(SR))
    first = lookup_table(name)[0]
    for fields in ({}, {"threshold": "1"}, {"smoothing": "0.5", "smoothing_window": "3"}):
        job = post(client, data, colormap=name, **fields).json()
        for i in (0, job["frame_count"] // 2, job["frame_count"] - 1):
            assert (frame_image(client, job, i)[..., :3] == first).all(), (name, fields, i)


def test_the_same_request_twice_gives_identical_frames(client):
    data = chord_wav(2)
    a = post(client, data, smoothing="0.4", smoothing_window="3", threshold="3").json()
    b = post(client, data, smoothing="0.4", smoothing_window="3", threshold="3").json()
    for i in range(0, a["frame_count"], 3):
        assert frame_bytes(client, a, i) == frame_bytes(client, b, i)


def test_ten_seconds_at_thirty_frames_per_second_finish_within_a_minute(client):
    import time

    tone = np.concatenate([note_tone(n, 1.0) for n in (24, 30, 36, 42, 48, 36, 30, 24, 40, 50)])
    data = wav_bytes(tone, tone)
    start = time.perf_counter()
    r = post(client, data, frame_rate="30")
    elapsed = time.perf_counter() - start
    assert r.status_code == 200, r.text
    assert r.json()["frame_count"] >= 300
    assert elapsed < 60, f"{r.json()['frame_count']} contour frames took {elapsed:.1f} s"
