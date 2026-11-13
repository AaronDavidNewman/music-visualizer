"""The ``polar-chords`` image type through ``POST /api/jobs``: the type, Notes shown, the beat, the ignored settings, real tones and chords (feature 032)."""

import math

import numpy as np
import pytest

import app.routers.jobs as jobs
from app.services.colormaps import COLORMAPS, lookup_table
from app.services.image_types import IMAGE_TYPES
from app.services.note_layout import note_order

from .frame_size import HEIGHT, WIDTH
from .test_jobs_api import SR, client, leftovers, note_tone, wav_bytes  # noqa: F401
from .test_peak_tile_colors_api import COLORMAP, ROWS, TONE_NOTE, all_frames, post, pulse_wav
from .test_resolution_api import picture, tiny

TYPE_MESSAGE = f"The image type must be one of {', '.join(IMAGE_TYPES)}."
NOTES_MESSAGE = "The number of notes shown must be a whole number from 5 to 8."
DISTANCE_MESSAGE = "The minimum distance must be a number from 100 to 2000 milliseconds."
PROMINENCE_MESSAGE = "The prominence must be a number from 0 to 100 percent."
CENTER = (WIDTH / 2, HEIGHT / 2)
RADIUS = 190.0
ARC = 360.0 / 84
CHORD_ARC = 360.0 / 84
MIDDLE = 128
C4, E4, G4 = 27, 31, 34


def polar(client, data=None, **fields):
    return post(client, data, image_type="polar-chords", **fields)


def pixel(image, angle, radius):
    x = CENTER[0] + radius * math.sin(math.radians(angle))
    y = CENTER[1] - radius * math.cos(math.radians(angle))
    return tuple(int(v) for v in image[int(math.floor(y)), int(math.floor(x))])


def row_at(image, angle, radius):
    """The colormap row of the pixel, read back from the decodable colormap of the tests (None for a color that is not on the scale)."""
    return ROWS.get(pixel(image, angle, radius))


def chord(seconds=3.0):
    """A C major triad: three tones of the same strength at the notes C4, E4 and G4."""
    return wav_bytes(0.2 * (note_tone(C4, seconds) + note_tone(E4, seconds) + note_tone(G4, seconds)))


# --- choosing it --------------------------------------------------------------------------------------------------------------


def test_polar_chords_is_the_ninth_image_type_and_the_message_lists_all_thirteen():
    assert IMAGE_TYPES[8] == "polar-chords" and len(IMAGE_TYPES) == 13
    assert TYPE_MESSAGE == (
        "The image type must be one of tiles, blended, contour, circles, circles_paint, concentric, decay, decay-exp, polar-chords, energy-graphs, chromatic-decay, rhythm-circles, chromatic-wireframe."
    )


@pytest.mark.parametrize("name", ["polar_chords", "polarchords", "Polar-Chords", "polar-chords ", "polar-", "POLAR-CHORDS", ""])
def test_a_name_that_is_not_exactly_polar_chords_is_refused_with_the_nine_names(client, name):
    r = post(client, tiny(), image_type=name)
    assert r.status_code == 400 and r.json()["detail"] == TYPE_MESSAGE
    assert leftovers() == []


@pytest.mark.parametrize("name", COLORMAPS)
def test_polar_chords_is_accepted_and_echoed_with_every_colormap_and_the_defaults(client, name):
    r = post(client, tiny(), image_type="polar-chords", colormap=name)
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["image_type"] == "polar-chords" and job["colormap"] == name
    assert (job["polar_notes"], job["peak_distance"], job["peak_prominence"]) == (5, 100, 50)


def test_the_response_has_the_same_keys_as_for_the_other_types_and_polar_notes_is_in_all_of_them(client):
    keys = set(post(client, tiny(), image_type="tiles").json())
    assert "polar_notes" in keys
    assert set(polar(client, tiny()).json()) == keys


def test_the_frames_are_600_by_400_rgb_pictures_and_their_count_is_that_of_the_other_types(client):
    audio = pulse_wav(seconds=3.0)
    job = polar(client, audio).json()
    tiles = post(client, audio, image_type="tiles").json()
    assert job["frame_count"] == tiles["frame_count"] > 0
    assert picture(client, job, 0).shape == (HEIGHT, WIDTH, 3)
    assert picture(client, job, job["frame_count"] - 1).shape == (HEIGHT, WIDTH, 3)


# --- Notes shown --------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["5", "6", "7", "8", " 6 ", "6.0", "8.0"])
def test_a_whole_number_from_5_to_8_is_accepted_and_echoed_as_a_number(client, value):
    r = polar(client, tiny(), polar_notes=value)
    assert r.status_code == 200, r.text
    assert r.json()["polar_notes"] == int(float(value))


@pytest.mark.parametrize("value", ["4", "9", "0", "-5", "6.5", "abc", "", "nan", "inf", "1e1", "5,5"])
def test_anything_else_is_refused_with_the_message_and_nothing_is_created(client, value):
    r = polar(client, tiny(), polar_notes=value)
    assert r.status_code == 400 and r.json()["detail"] == NOTES_MESSAGE
    assert leftovers() == []


def test_notes_shown_is_checked_before_the_file_is_read(client):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": "polar-chords", "polar_notes": "9"})  # no file at all
    assert r.status_code == 400 and r.json()["detail"] == NOTES_MESSAGE
    assert leftovers() == []


@pytest.mark.parametrize("image_type", ["tiles", "blended", "contour", "circles", "circles_paint", "concentric", "decay", "decay-exp"])
def test_notes_shown_sent_with_another_type_is_checked_echoed_and_has_no_effect(client, image_type):
    audio = tiny()
    plain = post(client, audio, image_type=image_type).json()
    sent = post(client, audio, image_type=image_type, polar_notes="8")
    assert sent.status_code == 200 and sent.json()["polar_notes"] == 8
    assert all_frames(client, sent.json()) == all_frames(client, plain)
    assert post(client, audio, image_type=image_type, polar_notes="9").status_code == 400


def many_notes(seconds=3.0):
    return wav_bytes(0.1 * sum(note_tone(n, seconds) * (1.0 - 0.1 * i) for i, n in enumerate((24, 27, 31, 34, 38, 41, 45, 48))))


def test_notes_shown_changes_the_frames_of_a_file_with_many_notes(client):
    audio = many_notes()
    five = all_frames(client, polar(client, audio, polar_notes="5").json())
    eight = all_frames(client, polar(client, audio, polar_notes="8").json())
    assert five != eight and len(five) == len(eight)


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
    assert polar(client, tiny(), **fields).status_code == 200
    assert measured == [(22050, SR, 300.0, 20.0)]


def test_the_checkbox_has_no_effect_on_the_frames(client):
    audio = pulse_wav(seconds=4.0)
    plain = all_frames(client, polar(client, audio).json())
    assert all_frames(client, polar(client, audio, beat_coloring="true").json()) == plain


@pytest.mark.parametrize(
    "fields, message",
    [({"peak_distance": "50"}, DISTANCE_MESSAGE), ({"peak_distance": "abc"}, DISTANCE_MESSAGE), ({"peak_prominence": "101"}, PROMINENCE_MESSAGE), ({"peak_prominence": ""}, PROMINENCE_MESSAGE)],
)
def test_the_peak_settings_are_checked_before_the_file_is_read_with_nothing_created(client, measured, fields, message):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": "polar-chords", **fields})
    assert r.status_code == 400 and r.json()["detail"] == message
    assert polar(client, tiny(), **fields).status_code == 400
    assert leftovers() == [] and measured == []


def test_the_minimum_distance_and_the_prominence_change_the_length_of_the_bars(client):
    audio = pulse_wav()
    default = all_frames(client, polar(client, audio).json())
    far = all_frames(client, polar(client, audio, peak_distance="2000").json())
    high = all_frames(client, polar(client, audio, peak_prominence="95").json())
    assert far != default and high != default


# --- the picture --------------------------------------------------------------------------------------------------------------


def test_a_steady_tone_is_a_bar_at_the_angle_of_its_note_from_the_first_half_of_the_colormap_half_the_radius_long_without_a_beat(client):
    job = polar(client, wav_bytes(0.5 * note_tone(TONE_NOTE, 3.0)), peak_prominence="100").json()  # a prominence of 100 % finds no peak in a steady tone
    image = picture(client, job, job["frame_count"] - 1)
    angle = (TONE_NOTE + 0.5) * ARC
    assert row_at(image, angle, 0.3 * RADIUS) == 0  # the loudest possible note has the first color
    assert pixel(image, angle, 0.45 * RADIUS) != tuple(lookup_table(COLORMAP)[MIDDLE])  # still in the bar
    assert pixel(image, angle, 0.6 * RADIUS) == tuple(lookup_table(COLORMAP)[MIDDLE])  # beyond half the radius it is the background
    assert pixel(image, 180.0, 0.3 * RADIUS) == tuple(lookup_table(COLORMAP)[MIDDLE])  # nothing at the opposite side


def test_a_triad_makes_three_note_bars_and_the_chord_bar_for_a_major_triad_counterclockwise(client):
    job = polar(client, chord(), peak_prominence="100").json()
    image = picture(client, job, job["frame_count"] // 2)
    for note in (C4, E4, G4):
        assert row_at(image, (note + 0.5) * ARC, 0.3 * RADIUS) <= 30  # the first half of the colormap
    place = 3 * 7 + 1  # (4, 7) on C: the letter 3 (A is 0) times 7 chord types, plus the type 1
    row = row_at(image, 360.0 - (place + 0.5) * CHORD_ARC, 0.3 * RADIUS)
    assert row is not None and row >= 200  # the second half of the colormap
    for other in (0, 21, 23, 41):  # the other places (the places of other types and roots; none of them is under a note bar): no chord bar (a faint note bar over one of them is close to the background color, a chord bar would not be)
        assert max(abs(int(a) - int(b)) for a, b in zip(pixel(image, 360.0 - (other + 0.5) * CHORD_ARC, 0.3 * RADIUS), lookup_table(COLORMAP)[MIDDLE])) <= 8


def test_a_silent_file_makes_frames_of_the_background_only(client):
    job = polar(client, tiny()).json()
    assert job["frame_count"] > 0
    image = picture(client, job, 0)
    assert (image.reshape(-1, 3) == lookup_table(COLORMAP)[MIDDLE]).all()
    assert len(set(all_frames(client, job))) == 1


def test_a_file_shorter_than_the_peaks_window_makes_frames(client):
    short = wav_bytes(np.clip(0.15 * note_tone(TONE_NOTE, 0.4), -0.9, 0.9))
    job = polar(client, short).json()
    assert job["frame_count"] >= 1
    assert picture(client, job, 0).shape == (HEIGHT, WIDTH, 3)


def test_the_settings_of_the_other_pictures_are_accepted_and_ignored(client):
    audio = pulse_wav(seconds=3.0)
    plain = all_frames(client, polar(client, audio).json())
    for fields in (
        {"threshold": "5"}, {"note_count": "20"}, {"resolution": "3"}, {"interpolate": "3"}, {"gaussian": "2"}, {"blend_width": "10"},
        {"circle_unit": "9"}, {"circle_memory": "100"}, {"circle_notes": "12"}, {"circle_radius": "8"}, {"circle_resize": "true"},
        {"decay_rate": "2"}, {"decay_low": "3"}, {"wave_count": "7"},
    ):
        r = polar(client, audio, **fields)
        assert r.status_code == 200, (fields, r.text)
        assert all_frames(client, r.json()) == plain, fields


@pytest.mark.parametrize("fields", [{"threshold": "11"}, {"note_count": "5"}, {"resolution": "6"}, {"interpolate": "9"}, {"gaussian": "-1"}, {"circle_notes": "99"}, {"note_layout": "Spiral"}, {"decay_rate": "5"}])
def test_those_settings_are_still_checked(client, fields):
    assert polar(client, tiny(), **fields).status_code == 400


def test_the_smoothing_applies(client):
    audio = pulse_wav(seconds=3.0)
    plain = all_frames(client, polar(client, audio).json())
    smooth = all_frames(client, polar(client, audio, smoothing="0.6", smoothing_window="5").json())
    assert smooth != plain and len(smooth) == len(plain)


def test_two_runs_give_identical_frames(client):
    audio = pulse_wav(seconds=3.0)
    assert all_frames(client, polar(client, audio).json()) == all_frames(client, polar(client, audio).json())


@pytest.mark.parametrize("notes", ["5", "8"])
def test_mono_and_stereo_copies_of_the_same_sound_make_the_same_frames(client, notes):
    mono = 0.5 * note_tone(TONE_NOTE, 2.0)
    a = polar(client, wav_bytes(mono), polar_notes=notes).json()
    b = polar(client, wav_bytes(np.stack([mono, mono], axis=1)), polar_notes=notes).json()
    assert all_frames(client, a) == all_frames(client, b)


# --- the note layout ----------------------------------------------------------------------------------------------------------


def test_the_spiral_layout_applies_and_is_echoed(client):
    audio = pulse_wav(seconds=3.0)
    rows = polar(client, audio, note_layout="rows").json()
    spiral = polar(client, audio, note_layout="spiral")
    assert spiral.status_code == 200 and spiral.json()["note_layout"] == "spiral" and rows["note_layout"] == "rows"
    assert all_frames(client, spiral.json()) != all_frames(client, rows)
    assert all_frames(client, rows) == all_frames(client, polar(client, audio).json())  # rows is the default and what it always was
    assert polar(client, audio, note_layout="Spiral").status_code == 400


def test_a_steady_tone_is_in_the_arc_of_its_note_in_the_layout_chosen(client):
    audio = wav_bytes(0.5 * note_tone(TONE_NOTE, 3.0))
    for layout in ("rows", "spiral"):
        job = polar(client, audio, peak_prominence="100", note_layout=layout).json()
        image = picture(client, job, job["frame_count"] - 1)
        order = note_order(layout)
        arc = int(np.flatnonzero(order == TONE_NOTE)[0])
        assert row_at(image, (arc + 0.5) * ARC, 0.3 * RADIUS) == 0, layout


# --- the bars follow their notes -----------------------------------------------------------------------------------------------


def loud_arcs(image):
    """The note arcs whose bar has (nearly) the first color of the colormap: the bar of a note as loud as the loudest of the file."""
    found = []
    for arc in range(84):
        row = row_at(image, (arc + 0.5) * ARC, 0.3 * RADIUS)
        if row is not None and row <= 20:
            found.append(arc)
    return found


def test_when_the_note_jumps_far_the_bar_slides_to_it_one_arc_a_frame_instead_of_jumping(client):
    audio = wav_bytes(np.concatenate([0.5 * note_tone(36, 1.5), 0.5 * note_tone(48, 3.0)]))  # note 36, then note 48: twelve arcs away
    job = polar(client, audio, frame_rate="30", peak_prominence="100").json()
    seen = []  # (frame, arc) wherever the loudest bar is easy to see: the last window of the file is only partly filled and the change of tone is noisy
    for index in range(job["frame_count"]):
        found = loud_arcs(picture(client, job, index))
        if len(found) == 1:
            seen.append((index, found[0]))
    assert seen[0] == (0, 36) and seen[-1][1] == 48
    for (before, a), (after, b) in zip(seen, seen[1:]):
        assert abs(b - a) <= after - before, (before, a, after, b)  # never faster than one arc a frame
    arcs = [arc for _, arc in seen]
    assert len(set(range(36, 49)) & set(arcs)) >= 11  # it passed the arcs on the way (a frame or two is not clear: the change of tone is noisy): 37, 38, ... 47
    assert arcs == sorted(arcs)  # and went the one way
