"""The ``chromatic-decay`` image type through ``POST /api/jobs``: the type, the per-type decay rate, the ignored settings, real tones, silence (feature 035)."""

import io
import math

import numpy as np
import pytest
from PIL import Image

from app.services import chromatic_decay as cd
from app.services.colormaps import lookup_table
from app.services.frame_rendering import write_frames
from app.services.image_types import IMAGE_TYPES

from .frame_size import HEIGHT, WIDTH
from .test_jobs_api import SR, client, leftovers, note_tone, wav_bytes  # noqa: F401
from .test_peak_tile_colors_api import COLORMAP, post
from .test_resolution_api import tiny

TYPE_MESSAGE = f"The image type must be one of {', '.join(IMAGE_TYPES)}."
RATE_MESSAGE = "The decay rate must be a whole number from 1 to 10."
OLD_RATE_MESSAGE = "The decay rate must be a number from 0.25 to 4 in steps of 0.25."
DISTANCE_MESSAGE = "The minimum distance must be a number from 100 to 2000 milliseconds."
C4, C5 = 27, 39  # the letter C in two octaves
WINDOW, STEP = 4096, 4410  # the window of the requests and the default spacing at 10 frames a second
WINDOWS = 28
SAMPLES = (WINDOWS - 1) * STEP + WINDOW  # the last window just fits: every window holds the same whole tone


def chromatic(client, data=None, **fields):
    return post(client, data, image_type="chromatic-decay", **fields)


def picture(client, job, index):
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    assert r.status_code == 200
    return np.asarray(Image.open(io.BytesIO(r.content)).convert("RGB"))


def frames(client, job):
    return [picture(client, job, i) for i in range(job["frame_count"])]


def tone_file(note=C4):
    """One steady tone at the centre of the spectrum position of ``note``, for exactly 28 windows."""
    return wav_bytes(0.4 * note_tone(note, 3.0)[:SAMPLES])


def center(position):
    ring = (min(WIDTH, HEIGHT) / 2 - 10) / (1 + math.sin(math.pi / 12))
    angle = math.radians(30 * position)
    return WIDTH / 2 + ring * math.sin(angle), HEIGHT / 2 - ring * math.cos(angle)


def color_at_position(image, position):
    x, y = center(position)
    return tuple(int(v) for v in image[int(math.floor(y)), int(math.floor(x))])


# --- choosing it --------------------------------------------------------------------------------------------------------------


def test_chromatic_decay_is_the_eleventh_image_type_and_the_message_lists_it():
    assert IMAGE_TYPES[10] == "chromatic-decay" and len(IMAGE_TYPES) == 13
    assert TYPE_MESSAGE.endswith("polar-chords, energy-graphs, chromatic-decay, rhythm-circles, chromatic-wireframe.")


@pytest.mark.parametrize("name", ["chromatic_decay", "chromaticdecay", "Chromatic-Decay", "chromatic-decay ", "chromatic", "chromatic-", "CHROMATIC-DECAY", ""])
def test_a_name_that_is_not_exactly_chromatic_decay_is_refused_with_the_thirteen_names(client, name):
    r = post(client, tiny(), image_type=name)
    assert r.status_code == 400 and r.json()["detail"] == TYPE_MESSAGE
    assert leftovers() == []


def test_it_is_accepted_and_echoed_and_the_response_has_no_new_field(client):
    chromatic_job = chromatic(client, tiny())
    exp_job = post(client, tiny(), image_type="decay-exp")
    assert chromatic_job.status_code == 200, chromatic_job.text
    job = chromatic_job.json()
    assert job["image_type"] == "chromatic-decay"
    assert set(job) == set(exp_job.json())  # no new response field
    assert job["frame_count"] == exp_job.json()["frame_count"] and job["window_count"] == exp_job.json()["window_count"]


def test_the_frames_are_png_pictures_of_the_usual_size(client):
    job = chromatic(client, tone_file()).json()
    for i in range(job["frame_count"]):
        r = client.get(job["frame_url_template"].replace("{index}", str(i)))
        assert r.headers["content-type"] == "image/png"
        assert Image.open(io.BytesIO(r.content)).size == (WIDTH, HEIGHT)


# --- the decay rate: a whole number from 1 to 10 for this type ---------------------------------------------------------------


def test_the_decay_rate_is_1_when_not_sent(client):
    rate = chromatic(client, tiny()).json()["decay_rate"]
    assert rate == 1 and isinstance(rate, int)  # an integer for this type, as sent back when it is given


@pytest.mark.parametrize("text, value", [(str(n), n) for n in range(1, 11)] + [("3.0", 3), ("10.0", 10), ("1e1", 10)])
def test_a_whole_number_from_1_to_10_is_accepted_and_echoed_as_an_integer(client, text, value):
    job = chromatic(client, tiny(), decay_rate=text).json()
    assert job["decay_rate"] == value and isinstance(job["decay_rate"], int)


@pytest.mark.parametrize("text", ["0", "11", "2.5", "0.5", "0.25", "-1", "", "x", "nan", "inf", "-inf", " ", "1,5", "10.5", "100"])
def test_anything_else_is_refused_with_the_message_before_the_file_is_read_and_nothing_is_left_behind(client, text):
    r = chromatic(client, tiny(), decay_rate=text)
    assert r.status_code == 400 and r.json()["detail"] == RATE_MESSAGE, text
    assert leftovers() == []


def test_a_bad_rate_is_refused_before_the_file_is_read_even_without_a_file(client):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "10", "image_type": "chromatic-decay", "decay_rate": "11"})
    assert r.status_code == 400 and r.json()["detail"] == RATE_MESSAGE


@pytest.mark.parametrize("image_type", ["tiles", "blended", "decay", "decay-exp", "polar-chords", "energy-graphs"])
def test_the_other_types_keep_their_own_range_and_message(client, image_type):
    for text in ("5", "10", "4.5", "0"):
        r = post(client, tiny(), image_type=image_type, decay_rate=text)
        assert r.status_code == 400 and r.json()["detail"] == OLD_RATE_MESSAGE, (image_type, text)
    assert leftovers() == []  # the refusals left nothing behind
    for text in ("0.25", "1", "4"):
        assert post(client, tiny(), image_type=image_type, decay_rate=text).status_code == 200, (image_type, text)


def test_a_rate_is_valid_for_one_type_and_not_for_the_other(client):
    assert post(client, tiny(), image_type="decay-exp", decay_rate="0.25").status_code == 200
    assert chromatic(client, tiny(), decay_rate="0.25").status_code == 400
    assert chromatic(client, tiny(), decay_rate="7").status_code == 200
    assert post(client, tiny(), image_type="decay-exp", decay_rate="7").status_code == 400


@pytest.mark.parametrize("bad", [0, 11, 2.5, 0.5, True, "3", None])
def test_write_frames_refuses_a_bad_rate_for_this_type_before_writing_anything(tmp_path, bad):
    with pytest.raises(ValueError) as error:
        write_frames(np.zeros((2, 88)), tmp_path / "out", colormap=COLORMAP, image_type="chromatic-decay", decay_rate=bad)
    assert str(error.value) == RATE_MESSAGE
    assert not (tmp_path / "out").exists()


def test_write_frames_keeps_the_old_check_for_the_other_types(tmp_path):
    with pytest.raises(ValueError) as error:
        write_frames(np.zeros((2, 88)), tmp_path / "out", colormap=COLORMAP, image_type="decay-exp", decay_rate=5)
    assert str(error.value) == OLD_RATE_MESSAGE
    write_frames(np.zeros((2, 88)), tmp_path / "ok", colormap=COLORMAP, image_type="chromatic-decay", decay_rate=7)  # fine for this type
    assert len(list((tmp_path / "ok").glob("*.png"))) == 2


@pytest.mark.parametrize("rate", [1, 4])
@pytest.mark.parametrize("with_beat", [False, True])
def test_write_frames_draws_the_ring_from_the_simulation_with_the_beat_and_the_rate(tmp_path, rate, with_beat):
    values = np.zeros((8, 88))
    values[:, C4] = 2.0
    beat = np.linspace(0.0, 1.0, 8) if with_beat else None
    write_frames(values, tmp_path / "out", colormap=COLORMAP, image_type="chromatic-decay", decay_rate=rate, beat=beat)
    expected = tmp_path / "expected"
    cd.write_chromatic_frames(cd.circle_points(values, beat, rate), COLORMAP, expected, WIDTH, HEIGHT, beat=beat)  # with a beat: the target in the middle
    for i in range(8):
        assert (tmp_path / "out" / f"frame_{i:06d}.png").read_bytes() == (expected / f"frame_{i:06d}.png").read_bytes()


def test_the_beat_changes_the_frames(tmp_path):
    values = np.zeros((8, 88))
    values[:, C4] = 2.0
    write_frames(values, tmp_path / "flat", colormap=COLORMAP, image_type="chromatic-decay", beat=np.zeros(8))
    write_frames(values, tmp_path / "peak", colormap=COLORMAP, image_type="chromatic-decay", beat=np.ones(8))
    assert (tmp_path / "flat/frame_000007.png").read_bytes() != (tmp_path / "peak/frame_000007.png").read_bytes()


def test_the_beat_is_measured_for_this_type_with_the_local_peaks_settings_and_not_for_a_type_that_does_not_use_it(client, monkeypatch):
    import app.routers.jobs as jobs

    calls = []
    real = jobs.measure_local_peaks

    def spy(left, right, rate, distance, prominence):
        calls.append((distance, prominence))
        return real(left, right, rate, distance, prominence)

    monkeypatch.setattr(jobs, "measure_local_peaks", spy)
    assert chromatic(client, tiny(), peak_distance="700", peak_prominence="30").status_code == 200
    assert calls == [(700, 30)]
    assert post(client, tiny(), image_type="tiles").status_code == 200
    assert calls == [(700, 30)]  # Tiles without the beat coloring never measures it


# --- real tones ---------------------------------------------------------------------------------------------------------------------


def test_a_steady_c_charges_the_circle_at_the_top_and_its_two_neighbours_on_the_ring_light_up(client):
    job = chromatic(client, tone_file(C4)).json()
    assert job["window_count"] == WINDOWS
    table = lookup_table(COLORMAP)
    first = tuple(int(v) for v in table[0])  # the color of a circle with no points
    last = picture(client, job, job["frame_count"] - 1)
    top = color_at_position(last, 0)  # C
    g, f = color_at_position(last, 1), color_at_position(last, 11)  # the next ones clockwise and counterclockwise: G and F
    assert top != first
    assert g == f != first  # the two receivers hold the same points and are lit
    assert top != g
    for position in (2, 3, 4, 5, 6, 7, 8, 9, 10):
        assert color_at_position(last, position) == first, position  # nothing has reached the others
    first_frame = picture(client, job, 0)
    assert color_at_position(first_frame, 1) == first and color_at_position(first_frame, 11) == first  # in the first frame only C has points


def test_the_same_note_an_octave_up_lights_the_same_circles(client):
    # (not byte for byte: the beat measured from the audio differs a little between the two tones, which changes the gains a little; the library test
    # of the octaves is exact)
    first = tuple(int(v) for v in lookup_table(COLORMAP)[0])
    lit = []
    for note in (C4, C5):
        job = chromatic(client, tone_file(note)).json()
        last = picture(client, job, job["frame_count"] - 1)
        lit.append([position for position in range(12) if color_at_position(last, position) != first])
    assert lit[0] == lit[1] == [0, 1, 11]  # C at the top and its two neighbours on the ring, G and F


def test_another_letter_is_drawn_at_its_own_place_on_the_ring(client):
    job = chromatic(client, tone_file(C4 + 7)).json()  # G
    last = picture(client, job, job["frame_count"] - 1)
    first = tuple(int(v) for v in lookup_table(COLORMAP)[0])
    assert color_at_position(last, 1) != first  # G is the second place of the ring
    assert color_at_position(last, 0) == color_at_position(last, 2) != first  # its receivers C and D, the places on either side, are lit alike


def test_a_slower_decay_rate_makes_different_frames(client):
    one = frames(client, chromatic(client, tone_file(), decay_rate="1").json())
    ten = frames(client, chromatic(client, tone_file(), decay_rate="10").json())
    assert any(not np.array_equal(a, b) for a, b in zip(one, ten))


def test_the_same_file_and_settings_make_identical_frames(client):
    first = frames(client, chromatic(client, tone_file(), decay_rate="3").json())
    second = frames(client, chromatic(client, tone_file(), decay_rate="3").json())
    assert all(np.array_equal(a, b) for a, b in zip(first, second))


# --- the settings that apply and the ones that do not --------------------------------------------------------------------------


SETTINGS = [
    {"note_layout": "spiral"},
    {"decay_low": "2", "decay_medium": "2.5", "decay_high": "3", "decay_saturated": "1"},
    {"note_count": "20"},  # (the threshold applies to this type since feature 037)
    {"resolution": "3", "interpolate": "2", "gaussian": "1"},
    {"polar_notes": "7", "blend_width": "15", "wave_count": "6"},
    {"beat_coloring": "true"},
]


@pytest.mark.parametrize("fields", SETTINGS)
def test_the_settings_that_do_not_apply_are_accepted_and_change_nothing(client, fields):
    plain = frames(client, chromatic(client, tone_file()).json())
    other = chromatic(client, tone_file(), **fields)
    assert other.status_code == 200, other.text
    assert all(np.array_equal(a, b) for a, b in zip(plain, frames(client, other.json())))


def test_the_local_peaks_settings_are_validated_as_always(client):
    r = chromatic(client, tiny(), peak_distance="50")
    assert r.status_code == 400 and r.json()["detail"] == DISTANCE_MESSAGE
    assert leftovers() == []
    assert chromatic(client, tiny(), peak_distance="500", peak_prominence="20").status_code == 200


def test_a_setting_of_another_type_that_is_not_allowed_is_refused_as_for_every_type(client):
    r = chromatic(client, tiny(), polar_notes="9")
    assert r.status_code == 400 and r.json()["detail"] == "The number of notes shown must be a whole number from 5 to 8."
    assert leftovers() == []


def test_the_data_smoothing_applies(client):
    half = np.concatenate([0.4 * note_tone(C4, 3.0)[: SAMPLES // 2], np.zeros(SAMPLES - SAMPLES // 2)])  # a tone that stops half way
    data = wav_bytes(half)
    plain = frames(client, chromatic(client, data).json())
    smoothed = frames(client, chromatic(client, data, smoothing="0.8", smoothing_window="10").json())
    assert any(not np.array_equal(a, b) for a, b in zip(plain, smoothed))  # the smoothed tone lingers after it stops and keeps gaining
    assert chromatic(client, data, smoothing="0.9").status_code == 400  # and its range is validated


def test_the_colormap_decides_the_colors(client):
    one = chromatic(client, tone_file(), colormap="viridis").json()
    two = chromatic(client, tone_file(), colormap="hot").json()
    assert not np.array_equal(picture(client, one, 5), picture(client, two, 5))


@pytest.mark.parametrize("seconds", [0.0023, 0.5])
def test_a_silent_file_or_one_shorter_than_a_window_gives_pictures_without_error(client, seconds):
    job = chromatic(client, wav_bytes(np.zeros(int(SR * seconds))), decay_rate="10").json()
    assert job["frame_count"] >= 1
    first = tuple(int(v) for v in lookup_table(COLORMAP)[0])
    image = picture(client, job, 0)
    assert all(color_at_position(image, position) == first for position in range(12))  # twelve circles with no points


# --- the rings in the middle that show the beat (feature 036) ------------------------------------------------------------------

from scipy.io import wavfile  # noqa: E402

from app.services.local_peaks import DEFAULT_MIN_DISTANCE, DEFAULT_PROMINENCE, measure_local_peaks  # noqa: E402

from .test_chromatic_decay_peaks import oracle_distances, oracle_levels  # noqa: E402
from .test_chromatic_decay_rendering import pixel_for_ring  # noqa: E402
from .test_peak_tile_colors_api import pulse_wav  # noqa: E402


def measured_beat(data, frames, distance=DEFAULT_MIN_DISTANCE, prominence=DEFAULT_PROMINENCE, fps=10):
    """The position in the local peak of every frame, measured here the way the job measures it, from the bytes of the file."""
    rate, audio = wavfile.read(io.BytesIO(data))
    return np.asarray(measure_local_peaks(audio, audio, rate, distance, prominence).frame_positions(fps, frames))


def level_color(level):
    return tuple(int(c) for c in lookup_table(COLORMAP)[int(np.rint(level * 255))])


def color_at_ring(image, k):
    x, y = pixel_for_ring(k)
    return tuple(int(v) for v in image[y, x])


def test_a_pulsed_file_shows_the_distance_from_the_peak_in_the_center_of_every_frame(client):
    data = pulse_wav()
    job = chromatic(client, data).json()
    beat = measured_beat(data, job["frame_count"])
    assert beat.max() > 0.5 and beat.min() < 0.1  # the file really has a beat: some frames near a peak and some far from one
    table = lookup_table(COLORMAP)
    for f, image in enumerate(frames(client, job)):
        assert color_at_ring(image, 1) == tuple(int(c) for c in table[int(np.rint(oracle_distances(beat.tolist())[f] * 255))]), f


def test_the_outer_rings_show_the_averages_of_the_earlier_frames(client):
    data = pulse_wav()
    job = chromatic(client, data).json()
    beat = measured_beat(data, job["frame_count"])
    levels = oracle_levels(beat.tolist())
    for f, image in enumerate(frames(client, job)):
        for k in (2, 4, 7, 12):
            assert color_at_ring(image, k) == level_color(levels[f, k - 1]), (f, k)


def test_a_steady_tone_and_a_silent_file_show_the_distance_of_their_own_beat_and_silence_is_far_from_a_peak_in_every_ring(client):
    silent = wav_bytes(np.zeros(SR))
    job = chromatic(client, silent).json()
    far = level_color(1.0)
    for image in frames(client, job):
        assert all(color_at_ring(image, k) == far for k in range(1, 13))
    tone = tone_file()
    job = chromatic(client, tone).json()
    beat = measured_beat(tone, job["frame_count"])
    for f, image in enumerate(frames(client, job)):
        assert color_at_ring(image, 1) == level_color(oracle_distances(beat.tolist())[f]), f


def test_the_local_peaks_settings_change_the_rings(client):
    data = pulse_wav()
    job_a = chromatic(client, data, peak_distance="100", peak_prominence="50").json()
    job_b = chromatic(client, data, peak_distance="2000", peak_prominence="100").json()
    beat_a = measured_beat(data, job_a["frame_count"], 100.0, 50.0)
    beat_b = measured_beat(data, job_b["frame_count"], 2000.0, 100.0)
    assert not np.array_equal(beat_a, beat_b)  # the two settings do measure different beats on this file
    centers_a = [color_at_ring(image, 1) for image in frames(client, job_a)]
    centers_b = [color_at_ring(image, 1) for image in frames(client, job_b)]
    assert centers_a != centers_b
    assert centers_a == [level_color(d) for d in oracle_distances(beat_a.tolist())] and centers_b == [level_color(d) for d in oracle_distances(beat_b.tolist())]


def test_the_target_is_in_every_frame_and_the_circles_of_the_letters_are_outside_it(client):
    job = chromatic(client, pulse_wav()).json()
    first = tuple(int(v) for v in lookup_table(COLORMAP)[0])
    for image in frames(client, job):
        ys, xs = np.mgrid[0 : image.shape[0], 0 : image.shape[1]]
        distance = np.hypot(xs + 0.5 - 300, ys + 0.5 - 200)
        assert (image[distance < 66] != np.array(tuple(image[1, 1]))).any(axis=1).mean() > 0.5  # the middle is filled (a ring may match the background)
        assert (image[(distance > 73) & (distance < 105)] == np.array(tuple(image[1, 1]))).all()  # nothing between it and the circles


def test_a_real_beat_goes_through_the_whole_colormap_from_the_first_color_to_the_last_not_only_to_the_middle(client):
    data = pulse_wav()
    job = chromatic(client, data).json()
    beat = measured_beat(data, job["frame_count"])
    table = lookup_table(COLORMAP)
    centers = [color_at_ring(image, 1) for image in frames(client, job)]
    rows = sorted({int(np.argmin(np.abs(table.astype(int) - np.array(c)).sum(axis=1))) for c in centers})
    assert rows[0] <= 2 and rows[-1] >= 250  # both ends of the colormap are used
    assert any(r > 140 for r in rows)  # past the middle color (128), which is as far as the plain 1 - position would go on a beat that stays above 0.5


# --- the threshold (feature 037) ----------------------------------------------------------------------------------------------

from app.services.frame_rendering import smooth_frames  # noqa: E402

THRESHOLD_MESSAGE = "The threshold must be a number from 0 to 10."
E4 = 31  # the letter E


def loud_and_faint_file(faint=0.008):
    """C4 at 0.4 and E4 at a fiftieth of that (2 percent of the loudest), both in the centre of the spectrum position of their note, for 28 windows."""
    return wav_bytes(0.4 * note_tone(C4, 3.0)[:SAMPLES] + faint * note_tone(E4, 3.0)[:SAMPLES])


def circle_color(client, job, letter, index=-1):
    image = picture(client, job, job["frame_count"] - 1 if index == -1 else index)
    return color_at_position(image, cd.ring_position(letter))


def test_the_threshold_removes_the_faint_note_from_the_picture_and_without_it_the_faint_circle_grows(client):
    first = tuple(int(v) for v in lookup_table(COLORMAP)[0])  # a circle with no points
    data = loud_and_faint_file()
    e = cd.letter_at(cd.ring_position(7))  # the letter E is 7 (counting from A)
    for text in (None, "0", "1"):  # off, and 1 percent: the faint note (2 percent of the loudest) is above the floor and charges its circle (the exact boundary is tested on arrays)
        fields = {} if text is None else {"threshold": text}
        assert circle_color(client, chromatic(client, data, **fields).json(), e) != first, text
    job = chromatic(client, data, threshold="5").json()
    assert circle_color(client, job, e) == first  # 2 percent is under 5 percent: E is never charged
    assert circle_color(client, job, 3) != first  # the loud C is
    assert job["threshold"] == 5


@pytest.mark.parametrize("text, value", [("1", 1), ("5", 5), ("10", 10), ("2.5", 2.5), ("0", 0)])
def test_a_threshold_from_0_to_10_is_accepted_and_echoed(client, text, value):
    assert chromatic(client, tiny(), threshold=text).json()["threshold"] == value


def test_no_threshold_and_a_threshold_of_0_give_the_same_frames(client):
    data = loud_and_faint_file()
    plain = frames(client, chromatic(client, data).json())
    zero = frames(client, chromatic(client, data, threshold="0").json())
    assert all(np.array_equal(a, b) for a, b in zip(plain, zero))


@pytest.mark.parametrize("text", ["-1", "11", "10.5", "x", "", "nan", "inf", "-0.5"])
def test_a_threshold_outside_0_to_10_is_refused_with_the_message_before_the_file_is_read(client, text):
    r = chromatic(client, tiny(), threshold=text)
    assert r.status_code == 400 and r.json()["detail"] == THRESHOLD_MESSAGE, text
    assert leftovers() == []


@pytest.mark.parametrize("threshold", [0, 5, 10])
def test_write_frames_passes_the_threshold_to_the_points(tmp_path, threshold):
    values = np.zeros((10, 88))
    values[:, C4] = 100.0
    values[:, E4] = 4.0
    beat = np.linspace(0.0, 1.0, 10)
    write_frames(values, tmp_path / "out", colormap=COLORMAP, image_type="chromatic-decay", decay_rate=2, threshold=threshold, beat=beat)
    expected = tmp_path / "expected"
    cd.write_chromatic_frames(cd.circle_points(values, beat, 2, threshold), COLORMAP, expected, WIDTH, HEIGHT, beat=beat)
    for i in range(10):
        assert (tmp_path / "out" / f"frame_{i:06d}.png").read_bytes() == (expected / f"frame_{i:06d}.png").read_bytes()
    if threshold == 5:  # 4 percent of the loudest is under 5 percent: the threshold really changes the picture
        other = tmp_path / "other"
        write_frames(values, other, colormap=COLORMAP, image_type="chromatic-decay", decay_rate=2, threshold=0, beat=beat)
        assert (tmp_path / "out/frame_000009.png").read_bytes() != (other / "frame_000009.png").read_bytes()


def test_write_frames_refuses_a_bad_threshold_before_writing(tmp_path):
    with pytest.raises(ValueError) as error:
        write_frames(np.zeros((2, 88)), tmp_path / "out", colormap=COLORMAP, image_type="chromatic-decay", threshold=11)
    assert str(error.value) == THRESHOLD_MESSAGE
    assert not (tmp_path / "out").exists()


def test_the_data_smoothing_acts_before_the_threshold(tmp_path):
    values = np.zeros((12, 88))
    values[:6, C4] = 100.0  # a loud tone that stops half way; its smoothed tail lingers
    values[:, E4] = 3.0
    beat = np.zeros(12)
    write_frames(values, tmp_path / "out", colormap=COLORMAP, image_type="chromatic-decay", threshold=5, smoothing=0.8, smoothing_window=5, beat=beat)
    smoothed = smooth_frames(values, 0.8, 5)
    expected = tmp_path / "expected"
    cd.write_chromatic_frames(cd.circle_points(smoothed, beat, 1, 5), COLORMAP, expected, WIDTH, HEIGHT, beat=beat)
    for i in range(12):
        assert (tmp_path / "out" / f"frame_{i:06d}.png").read_bytes() == (expected / f"frame_{i:06d}.png").read_bytes()
    unsmoothed = tmp_path / "unsmoothed"
    cd.write_chromatic_frames(cd.circle_points(values, beat, 1, 5), COLORMAP, unsmoothed, WIDTH, HEIGHT, beat=beat)
    assert (tmp_path / "out/frame_000011.png").read_bytes() != (unsmoothed / "frame_000011.png").read_bytes()  # the smoothing really changed the result


def test_the_threshold_does_not_change_the_other_image_types_their_own_tests_say_so_and_the_response_has_the_same_fields(client):
    with_threshold = chromatic(client, tiny(), threshold="5").json()
    plain = chromatic(client, tiny()).json()
    assert set(with_threshold) == set(plain)
