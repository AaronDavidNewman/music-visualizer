"""The ``energy-graphs`` image type through ``POST /api/jobs``: the type, the ignored settings, real tones, silence (feature 034)."""

import io
import math

import numpy as np
import pytest
from PIL import Image

from app.services.image_types import IMAGE_TYPES

from .frame_size import HEIGHT, WIDTH
from .test_energy_graphs_rendering import PLOT_HEIGHT, bar_height
from .test_jobs_api import SR, client, leftovers, note_tone, wav_bytes  # noqa: F401
from .test_peak_tile_colors_api import post
from .test_resolution_api import tiny

TYPE_MESSAGE = f"The image type must be one of {', '.join(IMAGE_TYPES)}."
A3, E4 = 24, 31  # notes 24 and 31 of the 84 (A1 is 0)
WINDOW = 4096
STEP = 4410  # the default window spacing at 10 frames a second: a window for each frame
WINDOWS = 28
SAMPLES = (WINDOWS - 1) * STEP + WINDOW  # the last window just fits: every window holds a whole, identical tone (it is bin centred, so any start does)
FREQUENCY, AMPLITUDE = 0, 1  # the two data sets of the histogram


def energy(client, data=None, **fields):
    return post(client, data, image_type="energy-graphs", **fields)


def picture(client, job, index):
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    assert r.status_code == 200
    return np.asarray(Image.open(io.BytesIO(r.content)).convert("RGB"))


def frames(client, job):
    return [picture(client, job, i) for i in range(job["frame_count"])]


def two_tones(second=0.2, seconds=3.0):
    """A3 at 0.4 and E4 at ``second``, both in the centre of the spectrum position of their note, for exactly 28 windows."""
    return wav_bytes((0.4 * note_tone(A3, seconds) + second * note_tone(E4, seconds))[:SAMPLES])


def softmax(totals):
    """The softmax of the totals divided by their largest, with the smallest value of the data set taken off every one (the smallest bar has no height)."""
    largest = max(totals)
    x = [t / largest for t in totals]
    total = sum(math.exp(v) for v in x)
    shares = [math.exp(v) / total for v in x]
    return [s - min(shares) for s in shares]


def heights(image):
    background = image[2, 2]
    return [[bar_height(image, note, data_set, background) for note in range(84)] for data_set in (FREQUENCY, AMPLITUDE)]


def expected_heights(second):
    """The bars of the last frame of ``two_tones(second)`` from the totals worked out by hand: 28 windows, A3 and E4 ranked 84 and 83, 1 and the ratio of decibels."""
    ranks = [0.0] * 84
    ranks[A3], ranks[E4] = 84 * WINDOWS, 83 * WINDOWS
    amplitude = [0.0] * 84
    amplitude[A3] = float(WINDOWS)
    amplitude[E4] = WINDOWS * math.log10(second * 2048) / math.log10(0.4 * 2048)  # an exact-bin tone of amplitude A reads A * 4096 / 2
    frequency, amp = softmax(ranks), softmax(amplitude)
    tallest = max(max(frequency), max(amp))
    return [[round(PLOT_HEIGHT * s / tallest) for s in shares] for shares in (frequency, amp)]


# --- choosing it --------------------------------------------------------------------------------------------------------------


def test_energy_graphs_is_the_tenth_and_last_image_type_and_the_message_lists_it():
    assert IMAGE_TYPES[-1] == "energy-graphs" and len(IMAGE_TYPES) == 10
    assert TYPE_MESSAGE.endswith("polar-chords, energy-graphs.")


@pytest.mark.parametrize("name", ["energy_graphs", "energygraphs", "Energy-Graphs", "energy-graphs ", "energy-", "ENERGY-GRAPHS", ""])
def test_a_name_that_is_not_exactly_energy_graphs_is_refused_with_the_ten_names(client, name):
    r = post(client, tiny(), image_type=name)
    assert r.status_code == 400 and r.json()["detail"] == TYPE_MESSAGE
    assert leftovers() == []


def test_it_is_accepted_and_echoed_and_the_response_has_no_new_field(client):
    energy_job = energy(client, tiny())
    polar_job = post(client, tiny(), image_type="polar-chords")
    assert energy_job.status_code == 200, energy_job.text
    job = energy_job.json()
    assert job["image_type"] == "energy-graphs"
    assert set(job) == set(polar_job.json())  # no new response field
    assert job["frame_count"] == polar_job.json()["frame_count"] and job["window_count"] == polar_job.json()["window_count"]


def test_the_frames_are_png_pictures_of_the_usual_size(client):
    job = energy(client, two_tones(seconds=1.0)).json()
    for i in range(job["frame_count"]):
        r = client.get(job["frame_url_template"].replace("{index}", str(i)))
        assert r.headers["content-type"] == "image/png"
        assert Image.open(io.BytesIO(r.content)).size == (WIDTH, HEIGHT)


# --- the two data sets with real tones -----------------------------------------------------------------------------------------


def test_the_last_frame_is_the_softmax_of_the_totals_of_all_windows_above_the_smallest_for_both_data_sets(client):
    job = energy(client, two_tones()).json()
    assert job["window_count"] == WINDOWS
    last = heights(picture(client, job, job["frame_count"] - 1))
    for got, want in zip(last, expected_heights(0.2)):
        assert max(abs(g - w) for g, w in zip(got, want)) <= 2


def test_the_tallest_bar_is_the_same_height_in_every_frame_with_a_sound(client):
    job = energy(client, two_tones()).json()
    for image in frames(client, job):
        assert max(max(h) for h in heights(image)) == PLOT_HEIGHT


def test_the_amplitude_data_set_shows_what_the_rank_data_set_cannot(client):
    # E4 is always the second loudest, so its rank total is 83/84 of A3's however faint it is; its amplitude total is not
    quiet = energy(client, two_tones(second=0.04)).json()
    last = heights(picture(client, quiet, quiet["frame_count"] - 1))
    frequency_ratio = last[FREQUENCY][E4] / last[FREQUENCY][A3]
    amplitude_ratio = last[AMPLITUDE][E4] / last[AMPLITUDE][A3]
    assert amplitude_ratio < frequency_ratio - 0.03
    for got, want in zip(last, expected_heights(0.04)):
        assert max(abs(g - w) for g, w in zip(got, want)) <= 2


def test_the_same_file_and_settings_make_identical_frames(client):
    first = frames(client, energy(client, two_tones(seconds=1.0)).json())
    second = frames(client, energy(client, two_tones(seconds=1.0)).json())
    assert all(np.array_equal(a, b) for a, b in zip(first, second))


# --- silence, the ignored settings ----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("seconds", [0.0023, 0.5])
def test_a_silent_file_or_one_shorter_than_a_window_gives_pictures_without_bars(client, seconds):
    job = energy(client, wav_bytes(np.zeros(int(SR * seconds)))).json()
    assert job["frame_count"] >= 1
    image = picture(client, job, 0)
    assert all(h == 0 for data_set in heights(image) for h in data_set)


SETTINGS = [
    {"smoothing": "0.5", "smoothing_window": "5"},
    {"threshold": "5"},
    {"resolution": "3", "note_count": "20", "interpolate": "2"},
    {"note_layout": "spiral"},
    {"polar_notes": "7", "decay_rate": "2"},
    {"peak_distance": "500", "peak_prominence": "20", "beat_coloring": "true"},
]


@pytest.mark.parametrize("fields", SETTINGS)
def test_the_settings_that_do_not_apply_are_accepted_and_change_nothing(client, fields):
    plain = frames(client, energy(client, two_tones(seconds=1.0)).json())
    other = energy(client, two_tones(seconds=1.0), **fields)
    assert other.status_code == 200, other.text
    assert all(np.array_equal(a, b) for a, b in zip(plain, frames(client, other.json())))


def test_a_setting_that_is_not_allowed_is_refused_as_for_every_type(client):
    r = energy(client, tiny(), polar_notes="9")
    assert r.status_code == 400 and r.json()["detail"] == "The number of notes shown must be a whole number from 5 to 8."
    assert leftovers() == []


def test_the_colormap_decides_the_colors(client):
    one = energy(client, two_tones(seconds=1.0), colormap="viridis").json()
    two = energy(client, two_tones(seconds=1.0), colormap="hot").json()
    assert not np.array_equal(picture(client, one, 2), picture(client, two, 2))
    assert picture(client, one, 2)[2, 2].tolist() != picture(client, two, 2)[2, 2].tolist()
