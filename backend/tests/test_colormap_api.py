"""The colormap through the job endpoint: the optional ``colormap`` field (any name in ``COLORMAPS``), its refusals, the
response, the removed fields that are now ignored, and the colors in the served frames.

No colormap is named here: the list can be changed by hand (see ``colormap_names.py``).
"""

import numpy as np
import pytest

from app.services.colormaps import COLORMAPS, DEFAULT_COLORMAP, lookup_table

from .colormap_names import DECODABLE, FIRST, INVALID, MESSAGE, SECOND, WITHOUT_BLACK

from .test_jobs_api import (  # noqa: F401
    SR,
    burst_then_silence,
    chord_wav,
    client,
    expected_pixels,
    frame_rgb,
    frame_values,
    leftovers,
    note_tone,
    wav_bytes,
)

REMOVED = ("energy", "brightness", "hue_step", "saturation_step", "brightness_step")


def post_colormap(client, data=None, **fields):
    form = {"window_size": "4096", "frame_rate": "10", **fields}
    return client.post("/api/jobs", files={"file": ("song.wav", data or chord_wav(2), "audio/wav")}, data=form)


def frame_bytes(client, job, index):
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    assert r.status_code == 200
    return r.content


def tiny():
    return wav_bytes(np.zeros(22050))


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_offered_colormaps_are_accepted_and_echoed(client, name):
    r = post_colormap(client, tiny(), colormap=name)
    assert r.status_code == 200, r.text
    assert r.json()["colormap"] == name


def test_without_the_field_the_colormap_is_the_default_and_the_frames_equal_those_sent_with_it(client):
    data = chord_wav(2)
    missing = post_colormap(client, data).json()
    named = post_colormap(client, data, colormap=DEFAULT_COLORMAP).json()
    assert missing["colormap"] == DEFAULT_COLORMAP and named["colormap"] == DEFAULT_COLORMAP
    for i in range(missing["frame_count"]):
        assert frame_bytes(client, missing, i) == frame_bytes(client, named, i)


@pytest.mark.parametrize("text", INVALID)
def test_any_other_colormap_is_refused_with_the_choices(client, text):
    before = leftovers()
    r = post_colormap(client, tiny(), colormap=text)
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == MESSAGE
    assert leftovers() == before  # no job was created


def test_the_colormap_is_checked_before_the_file_is_read(client):
    r = client.post(
        "/api/jobs",
        files={"file": ("song.wav", b"this is not audio", "audio/wav")},
        data={"window_size": "4096", "frame_rate": "10", "colormap": "x"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == MESSAGE


def test_the_removed_fields_are_accepted_and_ignored(client):
    data = chord_wav(2)
    plain = post_colormap(client, data).json()
    old = post_colormap(
        client, data, energy="3", brightness="4", hue_step="90", saturation_step="20", brightness_step="50"
    )
    assert old.status_code == 200, old.text
    old = old.json()
    for i in range(plain["frame_count"]):
        assert frame_bytes(client, plain, i) == frame_bytes(client, old, i)


def test_even_invalid_values_of_the_removed_fields_are_ignored(client):
    r = post_colormap(client, tiny(), energy="99", brightness="abc", hue_step="7", saturation_step="", brightness_step="x")
    assert r.status_code == 200, r.text


def test_the_response_has_the_colormap_and_none_of_the_removed_settings(client):
    job = post_colormap(client, tiny(), energy="3", brightness="4", hue_step="90").json()
    assert "colormap" in job
    for key in REMOVED:
        assert key not in job
    assert set(job) == {
        "job_id", "file_name", "sample_rate", "duration_seconds", "window_size", "frame_rate", "frame_count",
        "smoothing", "smoothing_window", "threshold", "image_type", "blend_width", "colormap", "resolution", "window_spacing",
        "step_samples", "window_count", "spacing_raised", "frame_url_template",
    }  # fmt: skip


@pytest.mark.parametrize("name", COLORMAPS)
def test_every_tile_of_every_served_frame_is_the_table_colour_of_its_own_strength(client, name):
    data = chord_wav(2)
    job = post_colormap(client, data, colormap=name).json()
    table = lookup_table(name)
    expected = table[expected_pixels(job, 0)]  # worked out independently from the analysis values
    for i in range(job["frame_count"]):
        assert (frame_rgb(client, job, i) == expected[i]).all(), (name, i)


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_strongest_tile_of_the_file_has_the_last_colour(client, name):
    job = post_colormap(client, chord_wav(2), colormap=name).json()
    last = lookup_table(name)[255]
    assert any((frame_rgb(client, job, i) == last).all(axis=1).any() for i in range(job["frame_count"]))


def test_changing_the_colormap_changes_the_colours_and_not_which_tiles_are_strong(client):
    # a colour can be turned back into its table row only for tables whose 256 rows are all different colours
    if len(DECODABLE) < 2:
        pytest.skip("fewer than two offered colormaps have 256 different colours")
    first, second = DECODABLE[0], DECODABLE[1]
    data = chord_wav(2)
    a_job = post_colormap(client, data, colormap=first).json()
    b_job = post_colormap(client, data, colormap=second).json()
    assert frame_bytes(client, a_job, 5) != frame_bytes(client, b_job, 5)
    a, b = lookup_table(first), lookup_table(second)
    for i in range(a_job["frame_count"]):
        rows_a = [int(np.flatnonzero((a == c).all(axis=1))[0]) for c in frame_rgb(client, a_job, i)]
        rows_b = [int(np.flatnonzero((b == c).all(axis=1))[0]) for c in frame_rgb(client, b_job, i)]
        assert rows_a == rows_b  # the same positions on the scale, whatever the scale


def test_two_colormaps_give_different_pictures_of_the_same_sound(client):
    if FIRST == SECOND:
        pytest.skip("only one colormap is offered")
    data = chord_wav(2)
    a_job = post_colormap(client, data, colormap=FIRST).json()
    b_job = post_colormap(client, data, colormap=SECOND).json()
    assert any(frame_bytes(client, a_job, i) != frame_bytes(client, b_job, i) for i in range(a_job["frame_count"]))


def test_a_steady_tone_has_one_colour_in_every_frame_while_it_sounds(client):
    audio = note_tone(36, 3.0)
    job = post_colormap(client, wav_bytes(audio, audio), colormap=SECOND).json()
    inside = [frame_rgb(client, job, i)[36] for i in range(4, job["frame_count"] - 4)]
    assert all((c == inside[0]).all() for c in inside)  # steady: it does not blink


def test_a_note_keeps_its_colour_when_a_quieter_note_is_added(client):
    one = note_tone(36, 3.0) * 0.5
    both = (note_tone(36, 3.0) + 0.2 * note_tone(48, 3.0)) * 0.5  # the same loud note and a quieter one
    a = post_colormap(client, wav_bytes(one, one), colormap=DEFAULT_COLORMAP).json()
    b = post_colormap(client, wav_bytes(both, both), colormap=DEFAULT_COLORMAP).json()
    last = lookup_table(DEFAULT_COLORMAP)[255]
    for i in (8, 12, 16):  # frames well inside the tones
        assert (frame_rgb(client, a, i)[36] == last).all()  # the loudest note of the file: the last colour
        assert (frame_rgb(client, b, i)[36] == last).all()  # still the loudest note, unchanged by the added one
        assert not (frame_rgb(client, b, i)[48] == last).all()  # the quieter note is further down the scale
        assert not (frame_rgb(client, b, i)[48] == frame_rgb(client, a, i)[48]).all()  # and it is only in file b


def test_the_same_request_twice_gives_identical_frames(client):
    data = chord_wav(2)
    a = post_colormap(client, data, colormap=FIRST, smoothing="0.4").json()
    b = post_colormap(client, data, colormap=FIRST, smoothing="0.4").json()
    for i in range(0, a["frame_count"], 3):
        assert frame_bytes(client, a, i) == frame_bytes(client, b, i)


# --- with the other settings (User Story 3) -----------------------------------------------------------------------------


@pytest.mark.parametrize("name", COLORMAPS)
def test_blended_and_tiles_pictures_have_the_same_tile_middles_for_every_colormap(client, name):
    data = chord_wav(2)
    other = dict(colormap=name, smoothing="0.5", smoothing_window="3", threshold="5")
    tiles = post_colormap(client, data, image_type="tiles", **other).json()
    blended = post_colormap(client, data, image_type="blended", blend_width="15", **other).json()
    assert tiles["frame_count"] == blended["frame_count"]
    for i in range(0, tiles["frame_count"], 2):
        assert (frame_rgb(client, tiles, i) == frame_rgb(client, blended, i)).all(), (name, i)


@pytest.mark.parametrize("name", COLORMAPS)
def test_with_a_threshold_every_served_tile_is_black_or_a_colour_of_the_table(client, name):
    job = post_colormap(client, chord_wav(2), colormap=name, threshold="5").json()
    table = {tuple(row) for row in lookup_table(name).tolist()}
    black = 0
    for i in range(job["frame_count"]):
        for colour in frame_rgb(client, job, i):
            colour = tuple(int(v) for v in colour)
            assert colour == (0, 0, 0) or colour in table, (name, i, colour)
            black += colour == (0, 0, 0) and colour not in table
    if name in WITHOUT_BLACK:  # in a table that has black itself, a hidden tile cannot be told from a black entry
        assert black > 0  # some notes really were hidden


@pytest.mark.parametrize("name", COLORMAPS)
def test_a_silent_file_has_the_first_colour_of_the_colormap_in_every_tile(client, name):
    data = wav_bytes(np.zeros(SR), np.zeros(SR))
    first = lookup_table(name)[0]
    for fields in ({}, {"threshold": "1"}):  # nothing is below a share of the (zero) largest value, so nothing is hidden
        job = post_colormap(client, data, colormap=name, **fields).json()
        for i in (0, job["frame_count"] // 2, job["frame_count"] - 1):
            assert (frame_rgb(client, job, i) == first).all(), (name, fields, i)


def test_the_pictures_have_the_same_size_count_and_format_for_all_the_colormaps(client):
    import io

    from PIL import Image

    data = chord_wav(2)
    jobs = {name: post_colormap(client, data, colormap=name).json() for name in COLORMAPS}
    counts = {job["frame_count"] for job in jobs.values()}
    assert len(counts) == 1
    for name, job in jobs.items():
        img = Image.open(io.BytesIO(frame_bytes(client, job, 3)))
        assert img.size == (252, 168) and img.mode == "P", name
