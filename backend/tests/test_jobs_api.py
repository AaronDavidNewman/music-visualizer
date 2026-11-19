import io
import math

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from scipy.io import wavfile

from .frame_size import HEIGHT, WIDTH, tile_center
from app.config import settings
from app.main import app
from app.services.colormaps import DEFAULT_COLORMAP, lookup_table

SR = 44100


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "audio_temp_dir", tmp_path / "audio")
    monkeypatch.setattr(settings, "frames_temp_dir", tmp_path / "frames")
    return TestClient(app)


@pytest.fixture
def full_client(client):
    """The same client. (The name stays for the tests that used it when frames also had a brightness of their own.)"""
    return client


def wav_bytes(left, right=None, sample_rate=SR, dtype=np.int16):
    scale = np.iinfo(dtype).max
    data = np.round(np.asarray(left) * scale).astype(dtype)
    if right is not None:
        data = np.stack([data, np.round(np.asarray(right) * scale).astype(dtype)], axis=1)
    buf = io.BytesIO()
    wavfile.write(buf, sample_rate, data)
    return buf.getvalue()


def tone(freq, seconds, sample_rate=SR):
    t = np.arange(int(seconds * sample_rate)) / sample_rate
    return np.sin(2 * np.pi * freq * t)


def post(client, data, window="4096", fps="30", name="song.wav"):
    form = {"window_size": window, "frame_rate": fps}
    return client.post("/api/jobs", files={"file": (name, data, "audio/wav")}, data=form)


def frame_rgb(client, job, index):
    """The centre-pixel colour of each of the 84 tiles of a served frame, shape (84, 3)."""
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    assert r.status_code == 200
    arr = np.asarray(Image.open(io.BytesIO(r.content)).convert("RGB"))
    return np.array([arr[tile_center(n)] for n in range(84)])


DEFAULT_ROWS = {tuple(row): i for i, row in enumerate(lookup_table(DEFAULT_COLORMAP).tolist())}


def frame_levels(client, job, index):
    """The row (0 to 255) in the ``hot`` table (the default colormap) of each of the 84 tiles of a served frame, decoded
    from the tile's centre pixel by exact lookup (every row of the table is a different colour); -1 for a colour that is
    not in the table, such as the black of a tile that the threshold hides."""
    return np.array([DEFAULT_ROWS.get(tuple(int(v) for v in c), -1) for c in frame_rgb(client, job, index)])


def test_submission_creates_frames_in_separate_dirs(client):
    audio = tone(440, 2.0)
    r = post(client, wav_bytes(audio, audio))
    assert r.status_code == 200
    job = r.json()

    assert job["file_name"] == "song.wav"
    assert job["sample_rate"] == SR
    assert job["duration_seconds"] == pytest.approx(2.0)
    assert job["window_size"] == 4096
    assert job["frame_rate"] == 30
    assert job["frame_count"] == math.ceil(2.0 * 30) == 60
    assert len(job["job_id"]) == 32
    assert job["frame_url_template"] == f"/api/jobs/{job['job_id']}/frames/{{index}}"

    audio_dir = settings.audio_temp_dir / job["job_id"]
    frames_dir = settings.frames_temp_dir / job["job_id"]
    assert (audio_dir / "audio.wav").is_file()
    assert len(list(frames_dir.glob("frame_*.png"))) == 60
    assert settings.audio_temp_dir != settings.frames_temp_dir
    assert not (frames_dir / "audio.wav").exists()


def test_silent_file_gives_the_first_colour_of_the_colormap_in_every_tile(client):
    job = post(client, wav_bytes(np.zeros(SR), np.zeros(SR))).json()
    assert job["frame_count"] == 30
    for index in (0, 15, 29):
        assert not frame_levels(client, job, index).any()


def test_two_submissions_are_separate(client):
    audio = tone(440, 0.5)
    a = post(client, wav_bytes(audio, audio)).json()
    b = post(client, wav_bytes(audio, audio)).json()
    assert a["job_id"] != b["job_id"]
    assert (settings.frames_temp_dir / a["job_id"]).is_dir()
    assert (settings.frames_temp_dir / b["job_id"]).is_dir()


def test_frame_endpoint_serves_png(client):
    audio = tone(440, 0.5)
    job = post(client, wav_bytes(audio, audio)).json()
    r = client.get(job["frame_url_template"].replace("{index}", "0"))
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert "max-age" in r.headers["cache-control"]
    img = Image.open(io.BytesIO(r.content))
    assert img.size == (WIDTH, HEIGHT)


@pytest.mark.parametrize("job_id", ["../x", "ABCDEF" * 5 + "AB", "abc123", "g" * 32, "0" * 31])
def test_frame_endpoint_rejects_bad_job_ids(client, job_id):
    assert client.get(f"/api/jobs/{job_id}/frames/0").status_code == 404


def test_frame_endpoint_missing_frames_are_404(client):
    audio = tone(440, 0.5)
    job = post(client, wav_bytes(audio, audio)).json()
    base = f"/api/jobs/{job['job_id']}/frames"
    assert client.get(f"{base}/{job['frame_count']}").status_code == 404
    assert client.get(f"{base}/-1").status_code == 404
    assert client.get(f"{base}/abc").status_code == 404
    assert client.get(f"/api/jobs/{'0' * 32}/frames/0").status_code == 404


# --- errors (User Story 3) ---------------------------------------------------


def leftovers():
    return [p for root in (settings.audio_temp_dir, settings.frames_temp_dir) if root.exists() for p in root.iterdir()]


def assert_rejected(r, status, *fragments):
    assert r.status_code == status, r.text
    detail = r.json()["detail"]
    assert isinstance(detail, str)
    for fragment in fragments:
        assert fragment.lower() in detail.lower(), detail
    assert leftovers() == []


def test_not_a_wav_file(client):
    assert_rejected(post(client, b"this is not audio", name="x.wav"), 400, "could not read", "x.wav")


def test_more_than_two_channels(client):
    buf = io.BytesIO()
    wavfile.write(buf, SR, np.zeros((SR // 10, 3), dtype=np.int16))
    assert_rejected(post(client, buf.getvalue()), 400, "3 channels", "song.wav")


def test_file_with_no_audio(client):
    assert_rejected(post(client, wav_bytes(np.zeros(0), np.zeros(0))), 400, "no audio")


def test_missing_file(client):
    r = client.post("/api/jobs", data={"window_size": "4096", "frame_rate": "30"})
    assert_rejected(r, 400, "file")


@pytest.mark.parametrize("window", ["0", "2048", "4095", "5000", "65536", "4096.5", "abc", "", "-4096"])
def test_bad_window_size(client, window):
    audio = tone(440, 0.2)
    assert_rejected(post(client, wav_bytes(audio, audio), window=window), 400, "window size", "power of 2", "4096", "32768")


@pytest.mark.parametrize("fps", ["0", "61", "0.5", "abc", ""])
def test_bad_frame_rate(client, fps):
    audio = tone(440, 0.2)
    assert_rejected(post(client, wav_bytes(audio, audio), fps=fps), 400, "frame rate", "1", "60")


def test_missing_settings(client):
    audio = tone(440, 0.2)
    r = client.post("/api/jobs", files={"file": ("a.wav", wav_bytes(audio, audio), "audio/wav")})
    assert_rejected(r, 400, "window size")


def test_too_many_frames_is_rejected_before_analysis(client, monkeypatch):
    from app.routers import jobs

    def fail(*args, **kwargs):
        raise AssertionError("analysis must not run")

    monkeypatch.setattr(settings, "max_frames", 10)
    monkeypatch.setattr(jobs, "analyze_channels", fail)
    audio = tone(440, 1.0)  # 30 frames at 30 fps
    assert_rejected(post(client, wav_bytes(audio, audio)), 400, "30 frames", "limit is 10")


def test_sample_rate_too_low_for_notes(client):
    audio = tone(440, 1.0, sample_rate=8000)
    assert_rejected(post(client, wav_bytes(audio, audio, sample_rate=8000)), 400, "too low")


def test_upload_over_size_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "max_audio_bytes", 1000)
    audio = tone(440, 0.5)
    assert_rejected(post(client, wav_bytes(audio, audio)), 413, "larger than", "limit")


def test_unexpected_failure_gives_generic_message_and_cleans_up(client, monkeypatch):
    from app.routers import jobs

    def boom(*args, **kwargs):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(jobs, "write_frames", boom)
    audio = tone(440, 0.2)
    r = TestClient(app, raise_server_exceptions=False).post(
        "/api/jobs",
        files={"file": ("a.wav", wav_bytes(audio, audio), "audio/wav")},
        data={"window_size": "4096", "frame_rate": "30"},
    )
    assert_rejected(r, 500, "something went wrong")
    assert "disk on fire" not in r.text


def test_file_name_cannot_choose_where_files_go(client, tmp_path):
    audio = tone(440, 0.2)
    r = post(client, wav_bytes(audio, audio), name="../../evil.wav")
    assert r.status_code == 200
    assert r.json()["file_name"] == "evil.wav"
    assert list(tmp_path.rglob("evil*")) == []
    job_id = r.json()["job_id"]
    assert {p.name for p in (settings.audio_temp_dir / job_id).iterdir()} == {"audio.wav"}


def test_recovers_after_an_error(client):
    assert post(client, b"junk").status_code == 400
    audio = tone(440, 0.2)
    assert post(client, wav_bytes(audio, audio)).status_code == 200


@pytest.mark.parametrize("window", ["4096", "8192", "16384", "32768"])
def test_every_allowed_window_size_is_accepted(client, window):
    audio = tone(440, 0.5)
    r = post(client, wav_bytes(audio, audio), window=window)
    assert r.status_code == 200
    assert r.json()["window_size"] == int(window)


# --- the frequency buffers: always 60 ms apart (features 003 and 043) ---------------------------------------------


def test_the_step_is_60_ms_in_samples(client):
    from app.services.note_analysis import window_count

    audio = tone(440, 3.0)
    r = post(client, wav_bytes(audio, audio))
    assert r.status_code == 200
    job = r.json()
    assert job["step_samples"] == 2646  # 60 ms at 44100 Hz
    assert job["window_count"] == window_count(len(audio), 2646.0)
    assert job["frame_count"] == 90


@pytest.mark.parametrize("window", ["4096", "8192", "16384", "32768"])
def test_the_window_size_does_not_change_the_step(client, window):
    audio = tone(440, 3.0)
    job = post(client, wav_bytes(audio, audio), window=window).json()
    assert job["step_samples"] == 2646
    assert job["window_size"] == int(window)


@pytest.mark.parametrize("fps", ["1", "10", "24", "30", "60"])
def test_the_frame_rate_does_not_change_the_buffers(client, fps):
    audio = tone(440, 3.0)
    base = post(client, wav_bytes(audio, audio), fps="30").json()
    job = post(client, wav_bytes(audio, audio), fps=fps).json()
    assert job["step_samples"] == base["step_samples"] == 2646
    assert job["window_count"] == base["window_count"]
    assert job["frame_count"] == math.ceil(3.0 * int(fps) - 1e-9)


@pytest.mark.parametrize("rate, step", [(22050, 1323), (32000, 1920), (48000, 2880), (96000, 5760)])  # the analyzer refuses a rate under 16745 Hz at the smallest window
def test_the_step_follows_the_sample_rate_of_the_file(client, rate, step):
    audio = tone(440, 2.0, sample_rate=rate)
    r = post(client, wav_bytes(audio, audio, sample_rate=rate), window="4096")
    assert r.status_code == 200, r.text
    assert r.json()["step_samples"] == step


def test_same_settings_give_identical_frames(client):
    audio = tone(440, 1.0)
    data = wav_bytes(audio, audio)
    a = post(client, data, window="8192").json()
    b = post(client, data, window="8192").json()
    for index in (0, 10, 29):
        ra = client.get(a["frame_url_template"].replace("{index}", str(index))).content
        rb = client.get(b["frame_url_template"].replace("{index}", str(index))).content
        assert ra == rb


def test_a_file_shorter_than_the_interval_gives_one_window_and_one_frame_for_every_frame_it_covers(client):
    audio = tone(440, 1000 / SR)  # 1000 samples: under 60 ms
    job = post(client, wav_bytes(audio, audio), window="4096", fps="30").json()
    assert job["window_count"] == 1
    assert job["frame_count"] == 1


def test_too_many_windows_is_refused_before_analysis(client, monkeypatch):
    from app.routers import jobs
    from app.services.note_analysis import window_count

    def fail(*args, **kwargs):
        raise AssertionError("analysis must not run")

    monkeypatch.setattr(settings, "max_windows", 10)
    monkeypatch.setattr(jobs, "analyze_channels", fail)
    audio = tone(440, 1.0)
    expected = window_count(len(audio), 2646.0)
    assert expected > 10
    r = post(client, wav_bytes(audio, audio), window="4096")
    assert_rejected(r, 400, f"{expected:,} windows", "limit is 10", "shorter file")
    assert "window spacing" not in r.json()["detail"]


def test_the_window_limit_does_not_apply_to_an_ordinary_file(client):
    audio = tone(440, 3.0)
    job = post(client, wav_bytes(audio, audio)).json()
    assert job["window_count"] < settings.max_windows


def test_a_huge_window_count_is_refused_quickly_without_building_windows(client, monkeypatch):
    import time

    monkeypatch.setattr(settings, "max_windows", 5)
    audio = tone(440, 5.0)
    started = time.perf_counter()
    r = post(client, wav_bytes(audio, audio), window="32768")
    assert_rejected(r, 400, "windows", "limit is 5", "shorter file")
    assert time.perf_counter() - started < 2


def test_recovers_after_a_window_limit_error(client, monkeypatch):
    audio = tone(440, 1.0)
    data = wav_bytes(audio, audio)
    with monkeypatch.context() as m:
        m.setattr(settings, "max_windows", 2)
        assert post(client, data).status_code == 400
    assert post(client, data).status_code == 200


# --- octave grid layout (feature 005) --------------------------------------------


def note_tone(note, seconds=1.0, window=4096):
    """A tone at the exact centre of the spectrum position the analysis reads for this note."""
    from app.services.note_analysis import NoteBinAnalyzer

    return tone(NoteBinAnalyzer(SR, window).bin_indices[note] * SR / window, seconds)


def test_frame_images_are_the_image_size_and_exactly_three_to_two(client):
    audio = tone(440, 0.5)
    job = post(client, wav_bytes(audio, audio)).json()
    for index in (0, job["frame_count"] - 1):
        r = client.get(job["frame_url_template"].replace("{index}", str(index)))
        img = Image.open(io.BytesIO(r.content))
        assert img.size == (WIDTH, HEIGHT)
        assert img.size[0] * 2 == img.size[1] * 3


def test_one_of_the_four_omitted_notes_leaves_no_visible_tile_at_full_white(client):
    audio = note_tone(86)  # 7902 Hz is not drawn, but it still sets the 0-255 scale
    job = post(client, wav_bytes(audio, audio)).json()
    for index in (0, 10, 29):
        assert frame_levels(client, job, index).max() < 255


# --- the note values of a frame (features 006 and 043) ------------------------------------------------------------


def frame_values(job):
    """The averaged note values per frame of a stored job, from the services (with the noise floor of feature 033: the
    notes more than 60 dB below the loudest of the file are 0, as the job makes them). The frames are drawn as they are
    (feature 043 removed the smoothing)."""
    from app.services.frame_rendering import average_frames, frame_count
    from app.services.noise_floor import floor_analysis
    from app.services.note_analysis import analyze_channels, read_wav

    rate, left, right = read_wav(settings.audio_temp_dir / job["job_id"] / "audio.wav")
    result = floor_analysis(analyze_channels(left, right, rate, job["window_size"], step=job["step_samples"]))
    return average_frames(result, job["frame_rate"], frame_count(len(left), rate, job["frame_rate"]))


def expected_pixels(job):
    """The hot-table row of every tile of every frame, worked out independently of the code under test: take the share of
    the largest value, the square root, and round to one of 256 entries."""
    values = frame_values(job)
    peak = values.max()
    share = values[:, :84] / peak if peak > 0 else np.zeros((len(values), 84))
    return np.rint(np.sqrt(share) * 255).astype(int)


def burst_then_silence():
    """A steady note for one second, then silence for one second (60 frames at 30 fps)."""
    return np.concatenate([note_tone(36, 1.0), np.zeros(SR)])


def test_a_silent_file_stays_black(client):
    job = post(client, wav_bytes(np.zeros(SR), np.zeros(SR))).json()
    for index in (0, 15, 29):
        assert not frame_levels(client, job, index).any()


def test_a_note_that_stops_is_gone_in_the_frames_after_it(client):
    """With no smoothing between the frames, a frame after the burst shows nothing of it."""
    audio = burst_then_silence()
    job = post(client, wav_bytes(audio, audio)).json()
    assert frame_levels(client, job, 15).any()
    assert not frame_levels(client, job, 59).any()


# --- the served pictures --------------------------------------------------------------


def two_notes():
    """Notes 24 and 28 sounding together for one second."""
    return (note_tone(24) + note_tone(28)) / 2


def chord_wav(seconds=3):
    """Several notes whose loudness falls and rises, so that frames differ from one another."""
    t = np.arange(seconds * SR) / SR
    audio = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((220, 0.5), (277.18, 0.35), (329.63, 0.3), (440, 0.2)))
    audio = audio * np.interp(t, [0, 1, 2, 3], [1.0, 0.3, 0.9, 0.05])
    return wav_bytes(0.8 * audio / np.abs(audio).max())


def test_counts_and_timing_do_not_depend_on_colour(client):
    audio = two_notes()
    job = post(client, wav_bytes(audio, audio)).json()
    assert job["frame_count"] == math.ceil(job["duration_seconds"] * job["frame_rate"] - 1e-9)
    assert job["window_count"] >= 1  # one buffer every 60 ms: fewer than the 30 frames a second of the default (feature 043)
    assert job["step_samples"] == 2646


def test_the_same_file_and_settings_give_byte_identical_colour_frames(client):
    audio = two_notes()
    data = wav_bytes(audio, audio)
    a = post(client, data).json()
    b = post(client, data).json()
    for index in (0, 10, 29):
        ra = client.get(a["frame_url_template"].replace("{index}", str(index))).content
        rb = client.get(b["frame_url_template"].replace("{index}", str(index))).content
        assert ra == rb
