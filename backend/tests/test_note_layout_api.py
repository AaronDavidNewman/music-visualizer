"""The note layout through the job endpoint (feature 026): the field ``note_layout``, ``rows`` (the default) or ``spiral``."""

import numpy as np
import pytest

from app.services.note_layout import note_order

from .frame_size import HEIGHT, WIDTH, tile_center
from .test_concentric import flat_pixel
from .test_jobs_api import SR, client, leftovers, note_tone, wav_bytes  # noqa: F401
from .test_peak_tile_colors_api import COLORMAP, ROWS, TONE_NOTE, all_frames, post
from .test_resolution_api import picture, tiny

MESSAGE = "The note layout must be one of rows, spiral."
ALL_TYPES = ["tiles", "blended", "contour", "circles", "circles_paint", "concentric"]
LAID_OUT = ["tiles", "blended", "concentric"]
ORDER = note_order("spiral")
TONE_CELL = int(np.flatnonzero(ORDER == TONE_NOTE)[0])  # the cell where the spiral puts the note of the tone


def tone(seconds=2.0):
    return wav_bytes(0.5 * note_tone(TONE_NOTE, seconds))


def row_of(pixel):
    return ROWS[tuple(int(v) for v in pixel)]


# --- the field --------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", ALL_TYPES)
def test_the_default_is_rows_for_every_image_type(client, image_type):
    r = post(client, tiny(), image_type=image_type)
    assert r.status_code == 200, r.text
    assert r.json()["note_layout"] == "rows"


@pytest.mark.parametrize("image_type", ALL_TYPES)
@pytest.mark.parametrize("value", ["rows", "spiral"])
def test_both_layouts_are_accepted_and_echoed_for_every_image_type(client, image_type, value):
    r = post(client, tiny(), image_type=image_type, note_layout=value)
    assert r.status_code == 200, r.text
    assert r.json()["note_layout"] == value


@pytest.mark.parametrize("value", ["Rows", "SPIRAL", " spiral", "spiral ", "", "circle", "1", "row"])
def test_a_layout_that_is_not_exactly_offered_is_refused_with_nothing_created(client, value):
    r = post(client, tiny(), image_type="tiles", note_layout=value)
    assert r.status_code == 400 and r.json()["detail"] == MESSAGE
    assert leftovers() == []


@pytest.mark.parametrize("image_type", ["tiles", "contour", "concentric"])
def test_the_layout_is_checked_before_the_file_is_read(client, image_type):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": image_type, "note_layout": "Spiral"})  # no file at all
    assert r.status_code == 400 and r.json()["detail"] == MESSAGE
    assert leftovers() == []


def test_the_response_has_the_keys_of_the_other_jobs_and_the_layout(client):
    keys = set(post(client, tiny(), image_type="tiles").json())
    assert "note_layout" in keys
    assert set(post(client, tiny(), image_type="concentric", note_layout="spiral").json()) == keys


# --- the frames -------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", LAID_OUT)
def test_rows_gives_the_frames_of_a_job_that_sends_no_layout(client, image_type):
    audio = tone(2.0)
    plain = all_frames(client, post(client, audio, image_type=image_type).json())
    assert all_frames(client, post(client, audio, image_type=image_type, note_layout="rows").json()) == plain


@pytest.mark.parametrize("image_type", ["tiles", "blended"])
def test_the_tile_of_the_note_is_where_the_spiral_puts_it(client, image_type):
    audio = tone(2.0)
    rows = post(client, audio, image_type=image_type).json()
    spiral = post(client, audio, image_type=image_type, note_layout="spiral").json()
    assert rows["frame_count"] == spiral["frame_count"]
    in_rows, in_spiral = picture(client, rows, 5), picture(client, spiral, 5)
    assert in_rows.shape == in_spiral.shape == (HEIGHT, WIDTH, 3)
    assert row_of(in_rows[tile_center(TONE_NOTE)]) == 255  # the tone is the strongest note: the last color
    assert row_of(in_spiral[tile_center(TONE_CELL)]) == 255
    assert row_of(in_spiral[tile_center(TONE_NOTE)]) < 255  # that cell holds another note in the spiral
    assert TONE_CELL != TONE_NOTE
    assert all_frames(client, rows) != all_frames(client, spiral)


def test_the_circle_of_the_note_is_where_the_spiral_puts_it(client):
    audio = tone(2.0)
    rows = post(client, audio, image_type="concentric").json()
    spiral = post(client, audio, image_type="concentric", note_layout="spiral").json()
    in_rows, in_spiral = picture(client, rows, 5), picture(client, spiral, 5)
    background = tuple(in_rows[0, 0])
    y, x = flat_pixel(TONE_NOTE, 10)
    assert tuple(in_rows[y, x]) != background  # the tone has all twelve rings, in its own cell (ring 10: the outer rings follow the beat)
    y, x = flat_pixel(TONE_CELL, 10)
    assert tuple(in_spiral[y, x]) != background
    assert tuple(in_spiral[flat_pixel(TONE_NOTE, 10)]) == background  # and that cell of the rows layout is only a dot now
    assert all_frames(client, rows) != all_frames(client, spiral)


@pytest.mark.parametrize("image_type", ["contour", "circles", "circles_paint"])
def test_contour_and_the_circles_ignore_the_layout(client, image_type):
    audio = tone(2.0)
    rows = all_frames(client, post(client, audio, image_type=image_type).json())
    assert all_frames(client, post(client, audio, image_type=image_type, note_layout="spiral").json()) == rows


@pytest.mark.parametrize("image_type", LAID_OUT)
def test_the_frames_keep_their_size_count_and_two_runs_are_identical(client, image_type):
    audio = tone(2.0)
    one = post(client, audio, image_type=image_type, note_layout="spiral").json()
    two = post(client, audio, image_type=image_type, note_layout="spiral").json()
    assert all_frames(client, one) == all_frames(client, two)
    assert one["frame_count"] == post(client, audio, image_type=image_type).json()["frame_count"] > 0
    assert picture(client, one, 0).shape == (HEIGHT, WIDTH, 3)


# --- the other settings keep their meaning (Story 3) ---------------------------------------------------------------------------


def chord(seconds=2.0):
    """Three tones of different volume (and so different strength): the notes 20, 36 and 50, loudest first."""
    audio = 0.4 * note_tone(20, seconds) + 0.2 * note_tone(36, seconds) + 0.1 * note_tone(50, seconds)
    return wav_bytes(audio)


def centres(image):
    """The colour at the middle of every cell of a served tile frame."""
    return [tuple(int(v) for v in image[tile_center(cell)]) for cell in range(84)]


@pytest.mark.parametrize("image_type", ["tiles", "blended"])
@pytest.mark.parametrize(
    "fields",
    [{}, {"threshold": "5"}, {"threshold": "10"}, {"note_count": "36"}, {"note_count": "12", "threshold": "3"}, {"beat_coloring": "true"}, {"smoothing": "0.4", "smoothing_window": "3"}],
)
def test_the_colour_of_every_note_is_the_same_wherever_the_layout_puts_it(client, image_type, fields):
    audio = chord()
    rows = post(client, audio, image_type=image_type, **fields).json()
    spiral = post(client, audio, image_type=image_type, note_layout="spiral", **fields).json()
    assert rows["frame_count"] == spiral["frame_count"] > 3
    for index in (2, rows["frame_count"] // 2, rows["frame_count"] - 1):
        in_rows, in_spiral = centres(picture(client, rows, index)), centres(picture(client, spiral, index))
        for cell in range(84):
            assert in_spiral[cell] == in_rows[int(ORDER[cell])], (index, cell, fields)


def test_the_same_notes_are_hidden_in_both_layouts(client):
    audio = chord()
    rows = post(client, audio, image_type="tiles", threshold="10").json()
    spiral = post(client, audio, image_type="tiles", threshold="10", note_layout="spiral").json()
    in_rows, in_spiral = centres(picture(client, rows, 5)), centres(picture(client, spiral, 5))
    hidden_rows = {n for n in range(84) if in_rows[n] == (0, 0, 0)}
    hidden_spiral = {int(ORDER[cell]) for cell in range(84) if in_spiral[cell] == (0, 0, 0)}
    assert hidden_rows == hidden_spiral
    assert 20 not in hidden_rows and 36 not in hidden_rows  # the loud notes are shown
    assert len(hidden_rows) > 60


def test_the_rings_of_every_note_are_the_same_wherever_the_layout_puts_it(client):
    audio = chord()
    rows = post(client, audio, image_type="concentric").json()
    spiral = post(client, audio, image_type="concentric", note_layout="spiral").json()
    in_rows, in_spiral = picture(client, rows, 6), picture(client, spiral, 6)
    for cell in range(84):
        for ring in (1, 4, 8, 11):
            assert tuple(in_spiral[flat_pixel(cell, ring)]) == tuple(in_rows[flat_pixel(int(ORDER[cell]), ring)]), (cell, ring)


@pytest.mark.parametrize("image_type", LAID_OUT)
def test_a_silent_file_and_a_short_file_make_frames_in_the_spiral_layout(client, image_type):
    assert post(client, tiny(), image_type=image_type, note_layout="spiral").json()["frame_count"] > 0
    short = wav_bytes(np.clip(0.3 * note_tone(TONE_NOTE, 0.3), -0.9, 0.9))
    job = post(client, short, image_type=image_type, note_layout="spiral").json()
    assert job["frame_count"] >= 1 and picture(client, job, 0).shape == (HEIGHT, WIDTH, 3)


@pytest.mark.parametrize("image_type", LAID_OUT)
def test_mono_and_stereo_copies_make_the_same_frames_in_the_spiral_layout(client, image_type):
    audio = 0.4 * note_tone(20, 2.0) + 0.2 * note_tone(36, 2.0)
    mono = post(client, wav_bytes(audio), image_type=image_type, note_layout="spiral").json()
    stereo = post(client, wav_bytes(audio, audio), image_type=image_type, note_layout="spiral").json()
    assert all_frames(client, mono) == all_frames(client, stereo)
