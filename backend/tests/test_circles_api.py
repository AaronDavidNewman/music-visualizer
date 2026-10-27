"""The circles image type through the job endpoint: ``image_type=circles`` and its three settings ``circle_unit``,
``circle_memory`` and ``circle_notes``, their refusals, the response, and the frames that are served.

Where each circle goes is tested exactly in ``test_circles.py`` and ``test_circles_rendering.py``; this module is about the
endpoint. No colormap is named and no number of contour levels is assumed (see ``colormap_names.py``).
"""

import io
import time

import numpy as np
import pytest
from PIL import Image

from app.services.colormaps import COLORMAPS, lookup_table
from app.services.image_types import IMAGE_TYPES

from .frame_size import HEIGHT, WIDTH
from .test_circles import MEMORY_MESSAGE, NOTES_MESSAGE, RADIUS_MESSAGE, RESIZE_MESSAGE, UNIT_MESSAGE
from .test_jobs_api import (  # noqa: F401
    SR,
    chord_wav,
    client,
    frame_rgb,
    leftovers,
    note_tone,
    wav_bytes,
)
from .test_resolution_api import frame_bytes, picture, tiny

TYPE_MESSAGE = f"The image type must be one of {', '.join(IMAGE_TYPES)}."
REMOVED = ("energy", "brightness", "hue_step", "saturation_step", "brightness_step", "interpolate_function")


def post(client, data=None, **fields):
    form = {"window_size": "4096", "frame_rate": "10", "image_type": "circles", **fields}
    return client.post("/api/jobs", files={"file": ("song.wav", data or chord_wav(2), "audio/wav")}, data=form)


def steady_note(seconds=3.0, changing=True):
    """One note. With ``changing`` its loudness alternates every tenth of a second (every frame at 10 frames a second), so its
    circle moves every frame; without it the note is one steady volume, and its circle stays where it is."""
    audio = note_tone(36, seconds)
    if changing:
        audio = audio * np.where((np.arange(audio.size) * 10 // SR) % 2 == 0, 1.0, 0.4)
    return wav_bytes(audio, audio)


# --- choosing it ---------------------------------------------------------------------------------------------------------------


def test_circles_is_the_fourth_image_type_circles_paint_the_fifth_and_tiles_stays_the_first():
    assert IMAGE_TYPES == ("tiles", "blended", "contour", "circles", "circles_paint")


@pytest.mark.parametrize("name", COLORMAPS)
def test_circles_is_accepted_and_echoed_with_every_colormap_with_the_default_settings(client, name):
    r = post(client, tiny(), colormap=name)
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["image_type"] == "circles" and job["colormap"] == name
    assert (job["circle_unit"], job["circle_memory"], job["circle_notes"], job["circle_radius"]) == (4, 300, 8, 4)
    assert "circle_size" not in job


@pytest.mark.parametrize(
    "fields, expected",
    [
        ({"circle_unit": "10", "circle_memory": "500", "circle_notes": "12", "circle_radius": "8"}, (10, 500, 12, 8)),
        ({"circle_unit": "1", "circle_memory": "100", "circle_notes": "5", "circle_radius": "4"}, (1, 100, 5, 4)),
        ({"circle_unit": "4.0", "circle_memory": " 250 ", "circle_notes": "07", "circle_radius": " 6.0 "}, (4, 250, 7, 6)),
    ],
)
def test_the_three_settings_are_echoed_as_whole_numbers(client, fields, expected):
    job = post(client, tiny(), **fields).json()
    assert (job["circle_unit"], job["circle_memory"], job["circle_notes"], job["circle_radius"]) == expected
    assert all(isinstance(job[k], int) for k in ("circle_unit", "circle_memory", "circle_notes", "circle_radius"))


def test_a_request_that_still_sends_the_old_circle_size_is_accepted_and_the_field_is_ignored(client):
    data = chord_wav(2)
    plain = post(client, data).json()
    old = post(client, data, circle_size="40")
    assert old.status_code == 200, old.text
    old = old.json()
    assert "circle_size" not in old and old["circle_radius"] == 4
    last = plain["frame_count"] - 1
    assert frame_bytes(client, plain, last) == frame_bytes(client, old, last)


def test_the_resize_is_off_by_default_and_is_echoed_as_a_boolean(client):
    job = post(client, tiny()).json()
    assert job["circle_resize"] is False


@pytest.mark.parametrize(
    "text, expected",
    [("true", True), ("True", True), ("TRUE", True), (" true ", True), ("1", True), ("false", False), ("False", False), (" FALSE ", False), ("0", False)],
)
def test_the_resize_accepts_true_false_one_and_zero_in_any_case(client, text, expected):
    job = post(client, tiny(), circle_resize=text).json()
    assert job["circle_resize"] is expected


def test_the_frames_are_pngs_of_the_image_size_and_their_count_equals_that_of_tiles(client):
    data = chord_wav(2)
    circles = post(client, data).json()
    tiles = post(client, data, image_type="tiles").json()
    assert circles["frame_count"] == tiles["frame_count"] > 0
    for key in ("frame_rate", "window_size", "duration_seconds", "step_samples", "window_count"):
        assert circles[key] == tiles[key]
    for i in range(circles["frame_count"]):
        image = Image.open(io.BytesIO(frame_bytes(client, circles, i)))
        assert image.format == "PNG" and image.size == (WIDTH, HEIGHT) and image.mode == "RGB", i


@pytest.mark.parametrize("text", ["", " ", "Circles", "CIRCLES", " circles", "circles ", "circle", "contours", "1"])
def test_any_other_image_type_is_refused_with_the_four_names(client, text):
    before = leftovers()
    r = client.post(
        "/api/jobs",
        files={"file": ("song.wav", tiny(), "audio/wav")},
        data={"window_size": "4096", "frame_rate": "10", "image_type": text},
    )
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == TYPE_MESSAGE
    assert leftovers() == before


# --- the three settings -----------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", ["circles", "tiles"])
@pytest.mark.parametrize(
    "field, texts, message",
    [
        ("circle_unit", ["", " ", "0", "11", "-1", "2.5", "abc", "nan", "inf", "1e9", "4,", "4x"], UNIT_MESSAGE),
        ("circle_memory", ["", " ", "0", "99", "501", "250.5", "abc", "nan", "inf", "1e9", "-100"], MEMORY_MESSAGE),
        ("circle_notes", ["", " ", "0", "4", "13", "7.5", "abc", "nan", "inf", "1e9", "-5"], NOTES_MESSAGE),
        ("circle_radius", ["", " ", "0", "3", "9", "5.5", "abc", "nan", "inf", "1e9", "-4"], RADIUS_MESSAGE),
        ("circle_resize", ["", " ", "yes", "no", "on", "off", "2", "-1", "tru", "truee", "nan", "t", "0.0"], RESIZE_MESSAGE),
    ],
)
def test_a_circle_setting_that_is_not_allowed_is_refused_before_a_job_is_created_for_every_image_type(
    client, image_type, field, texts, message
):
    for text in texts:
        before = leftovers()
        r = post(client, tiny(), image_type=image_type, **{field: text})
        assert r.status_code == 400, (field, text, r.text)
        assert r.json()["detail"] == message, (field, text)
        assert leftovers() == before  # no job was created


def test_the_settings_are_checked_before_the_file_is_read(client):
    for fields, message in (({"circle_unit": "99"}, UNIT_MESSAGE), ({"circle_memory": "1"}, MEMORY_MESSAGE), ({"circle_notes": "1"}, NOTES_MESSAGE), ({"circle_radius": "1"}, RADIUS_MESSAGE), ({"circle_resize": "maybe"}, RESIZE_MESSAGE)):
        r = client.post(
            "/api/jobs",
            files={"file": ("song.wav", b"this is not audio", "audio/wav")},
            data={"window_size": "4096", "frame_rate": "10", "image_type": "circles", **fields},
        )
        assert r.status_code == 400
        assert r.json()["detail"] == message


def test_the_response_has_the_usual_keys_and_the_four_circle_keys(client):
    job = post(client, tiny()).json()
    assert set(job) == {
        "job_id", "file_name", "sample_rate", "duration_seconds", "window_size", "frame_rate", "frame_count",
        "smoothing", "smoothing_window", "threshold", "image_type", "blend_width", "colormap", "resolution", "note_count",
        "interpolate", "circle_unit", "circle_memory", "circle_notes", "circle_radius", "circle_resize", "gaussian", "beat_coloring", "peak_distance", "peak_prominence", "window_spacing",
        "step_samples", "window_count", "spacing_raised", "frame_url_template",
    }  # fmt: skip
    for key in REMOVED:
        assert key not in job


# --- the frames ------------------------------------------------------------------------------------------------------------------


def test_the_settings_that_do_not_apply_to_circles_are_accepted_and_ignored(client):
    data = steady_note()
    plain = post(client, data).json()
    ignored = post(client, data, interpolate="5", resolution="5", note_count="12", threshold="10", blend_width="10")
    assert ignored.status_code == 200, ignored.text
    ignored = ignored.json()
    assert (ignored["interpolate"], ignored["resolution"], ignored["note_count"], ignored["threshold"]) == (5, 5, 12, 10)  # as sent
    assert ignored["frame_count"] == plain["frame_count"]
    for i in range(plain["frame_count"]):
        assert frame_bytes(client, plain, i) == frame_bytes(client, ignored, i)


@pytest.mark.parametrize("image_type", ["tiles", "blended", "contour"])
def test_the_circle_settings_do_not_change_the_other_image_types(client, image_type):
    data = chord_wav(2)
    plain = post(client, data, image_type=image_type).json()
    other = post(client, data, image_type=image_type, circle_unit="10", circle_memory="500", circle_notes="12", circle_radius="8", circle_resize="true").json()
    for i in range(0, plain["frame_count"], 3):
        assert frame_bytes(client, plain, i) == frame_bytes(client, other, i)


def test_a_steady_note_draws_a_growing_trail_on_a_background_of_the_colormaps_middle_color(client):
    colormap = COLORMAPS[0]
    middle = tuple(int(v) for v in lookup_table(colormap)[128])
    job = post(client, steady_note(), colormap=colormap, circle_unit="6").json()
    count = job["frame_count"]
    lit = [int((picture(client, job, i) != np.array(middle)).any(axis=2).sum()) for i in range(count)]
    assert lit[0] > 0 and lit[-1] > lit[0]  # circles appear, and the earlier ones stay: the picture fills up
    assert tuple(picture(client, job, 0)[0, 0]) == middle  # the background where there is no circle


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_strongest_circles_have_the_last_color_of_the_colormap(client, name):
    job = post(client, steady_note(changing=False), colormap=name, circle_unit="8").json()
    last = tuple(int(v) for v in lookup_table(name)[255])
    image = picture(client, job, job["frame_count"] - 1)
    assert (image == np.array(last)).all(axis=2).any(), name


def test_smoothing_applies_and_the_colormap_changes_only_the_colors(client):
    data = steady_note()
    plain = post(client, data).json()
    smooth = post(client, data, smoothing="0.5", smoothing_window="3").json()
    assert plain["frame_count"] == smooth["frame_count"]
    if len(COLORMAPS) > 1:
        a = post(client, data, colormap=COLORMAPS[0]).json()
        b = post(client, data, colormap=COLORMAPS[1]).json()
        i = a["frame_count"] - 1
        lit_a = picture(client, a, i).sum(axis=2) > 0
        lit_b = picture(client, b, i).sum(axis=2) > 0
        assert lit_a.shape == lit_b.shape and (lit_a == lit_b).mean() > 0.9  # the same places (a color can be black in a map)
        assert frame_bytes(client, a, i) != frame_bytes(client, b, i)


@pytest.mark.parametrize(
    "field, low, high",
    [("circle_unit", "2", "10"), ("circle_memory", "100", "500"), ("circle_notes", "5", "12"), ("circle_radius", "4", "8")],
)
def test_each_setting_that_is_sent_changes_the_frames(client, field, low, high):
    data = chord_wav(3)  # many notes sound (the partials and the leakage), so every setting has something to change
    a = post(client, data, **{field: low}).json()
    b = post(client, data, **{field: high}).json()
    last = a["frame_count"] - 1
    assert (a[field], b[field]) == (int(low), int(high))
    assert frame_bytes(client, a, last) != frame_bytes(client, b, last), field


def test_the_resize_changes_the_frames_and_off_is_the_same_as_not_sent(client):
    data = chord_wav(3)
    plain = post(client, data).json()
    off = post(client, data, circle_resize="false").json()
    on = post(client, data, circle_resize="true").json()
    last = plain["frame_count"] - 1
    assert frame_bytes(client, plain, last) == frame_bytes(client, off, last)
    assert frame_bytes(client, plain, last) != frame_bytes(client, on, last)
    assert on["circle_resize"] is True


def test_a_note_that_stays_at_one_volume_covers_less_than_one_that_keeps_changing(client):
    colormap = COLORMAPS[0]
    middle = np.array(lookup_table(colormap)[128])

    def lit(changing):
        job = post(client, steady_note(changing=changing), colormap=colormap, circle_unit="6").json()
        return int((picture(client, job, job["frame_count"] - 1) != middle).any(axis=2).sum())

    assert lit(False) < lit(True)


def test_a_silent_file_gives_frames_of_the_middle_color_of_the_colormap(client):
    data = wav_bytes(np.zeros(SR), np.zeros(SR))
    for colormap in COLORMAPS:
        middle = lookup_table(colormap)[128]
        job = post(client, data, colormap=colormap, threshold="1", smoothing="0.4").json()
        for i in range(job["frame_count"]):
            assert (picture(client, job, i) == middle).all(), (colormap, i)


def test_the_same_request_twice_gives_identical_frames(client):
    data = chord_wav(2)
    options = dict(circle_unit="6", circle_memory="200", circle_notes="10", smoothing="0.4", smoothing_window="3")
    a, b = post(client, data, **options).json(), post(client, data, **options).json()
    for i in range(a["frame_count"]):
        assert frame_bytes(client, a, i) == frame_bytes(client, b, i)


def test_ten_seconds_at_thirty_frames_per_second_with_the_largest_settings_finish_within_a_minute(client):
    tone = np.concatenate([note_tone(n, 1.0) for n in (24, 30, 36, 42, 48, 36, 30, 24, 40, 50)])
    data = wav_bytes(tone, tone)
    start = time.perf_counter()
    r = post(client, data, frame_rate="30", circle_unit="10", circle_memory="500", circle_notes="12", circle_radius="8", smoothing="0.5", smoothing_window="3")
    elapsed = time.perf_counter() - start
    assert r.status_code == 200, r.text
    assert r.json()["frame_count"] >= 300
    assert elapsed < 60, f"{r.json()['frame_count']} circle frames took {elapsed:.1f} s"
