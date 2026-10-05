import io
import math

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from scipy.io import wavfile

from app.config import settings
from app.main import app

SR = 44100


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "audio_temp_dir", tmp_path / "audio")
    monkeypatch.setattr(settings, "frames_temp_dir", tmp_path / "frames")
    return TestClient(app)


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


def post(client, data, window="4096", fps="30", name="song.wav", spacing=None):
    form = {"window_size": window, "frame_rate": fps}
    if spacing is not None:
        form["window_spacing"] = spacing
    return client.post("/api/jobs", files={"file": (name, data, "audio/wav")}, data=form)


def frame_levels(client, job, index):
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    assert r.status_code == 200
    img = Image.open(io.BytesIO(r.content))
    arr = np.asarray(img)
    return arr.reshape(8, 20, 11, 20)[:, 0, :, 0].reshape(88)  # one value per square


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


def test_steady_note_has_one_brightest_square(client):
    # Note 36 (440 Hz) reads spectrum position 40 at window 4096 / 44100 Hz. Use the tone exactly
    # at the centre of that position so leakage into neighbouring positions is minimal.
    audio = tone(40 * SR / 4096, 1.0)
    job = post(client, wav_bytes(audio, audio)).json()
    hits = sum(frame_levels(client, job, i).argmax() == 36 for i in range(job["frame_count"]))
    assert hits / job["frame_count"] >= 0.95


def test_loudest_note_reaches_white_somewhere(client):
    audio = tone(440, 1.0)
    job = post(client, wav_bytes(audio, audio)).json()
    peak = max(frame_levels(client, job, i).max() for i in range(job["frame_count"]))
    assert peak == 255


def test_silent_file_gives_black_frames(client):
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
    assert (img.mode, img.size) == ("L", (220, 160))


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


# --- window spacing (feature 003) ---------------------------------------------


def test_quarter_spacing_sets_the_step(client):
    audio = tone(440, 3.0)
    n = len(audio)
    r = post(client, wav_bytes(audio, audio), window="8192", spacing="0.25")
    assert r.status_code == 200
    job = r.json()
    assert job["window_spacing"] == 0.25
    assert job["step_samples"] == 2048
    assert job["spacing_raised"] is False
    assert job["window_count"] == math.ceil(n / 2048)


def test_spacing_one_is_consecutive_windows(client):
    audio = tone(440, 3.0)
    job = post(client, wav_bytes(audio, audio), window="8192", spacing="1").json()
    assert job["step_samples"] == 8192
    assert job["window_count"] == math.ceil(len(audio) / 8192)


def test_spacing_above_one_is_accepted(client):
    audio = tone(440, 3.0)
    r = post(client, wav_bytes(audio, audio), window="8192", spacing="2")
    assert r.status_code == 200
    job = r.json()
    assert job["step_samples"] == 16384
    assert job["window_count"] == math.ceil(len(audio) / 16384)
    assert job["frame_count"] == 90  # still frames for the whole file


def test_non_integer_step_is_reported(client):
    audio = tone(440, 1.0)
    job = post(client, wav_bytes(audio, audio), window="4096", spacing="0.3").json()
    assert job["step_samples"] == pytest.approx(1228.8)


def test_same_settings_give_identical_frames(client):
    audio = tone(440, 1.0)
    data = wav_bytes(audio, audio)
    a = post(client, data, window="8192", spacing="0.25").json()
    b = post(client, data, window="8192", spacing="0.25").json()
    for index in (0, 10, 29):
        ra = client.get(a["frame_url_template"].replace("{index}", str(index))).content
        rb = client.get(b["frame_url_template"].replace("{index}", str(index))).content
        assert ra == rb


def test_spacing_one_matches_consecutive_window_analysis(client):
    """SC-002: spacing 1 gives the frames the application produced before spacing existed."""
    from app.services.frame_rendering import average_frames, frame_count, to_gray_levels
    from app.services.note_analysis import analyze_channels, read_wav

    left, right = tone(440, 2.0), tone(660, 2.0)
    job = post(client, wav_bytes(left, right), window="4096", spacing="1").json()
    rate, l, r = read_wav(settings.audio_temp_dir / job["job_id"] / "audio.wav")
    # consecutive windows: starts at multiples of the window size, the previous default behavior
    result = analyze_channels(l, r, rate, 4096)
    assert result.starts.tolist() == [i * 4096 for i in range(math.ceil(len(l) / 4096))]
    expected = to_gray_levels(average_frames(result, 30, frame_count(len(l), rate, 30)))
    for index in (0, 7, 30, 59):
        assert np.array_equal(frame_levels(client, job, index), expected[index])


@pytest.mark.parametrize("spacing", [None, "", "   "])
def test_missing_spacing_uses_the_default_44100(client, spacing):
    audio = tone(440, 3.0)
    job = post(client, wav_bytes(audio, audio), window="4096", fps="30", spacing=spacing).json()
    assert job["window_spacing"] == 0.358886
    assert job["spacing_raised"] is False
    assert job["window_count"] >= job["frame_count"] == 90


def test_default_spacing_depends_on_the_files_sample_rate(client):
    audio = tone(440, 3.0, sample_rate=48000)
    job = post(client, wav_bytes(audio, audio, sample_rate=48000), window="4096", fps="30").json()
    assert job["window_spacing"] == 0.390625  # 1600 samples per frame / 4096
    assert job["window_count"] >= job["frame_count"] == 90


def test_default_changes_with_frame_rate_and_window_size(client):
    audio = tone(440, 3.0)
    data = wav_bytes(audio, audio)
    assert post(client, data, fps="60").json()["window_spacing"] == 0.179443
    assert post(client, data, window="8192", fps="60").json()["window_spacing"] == 0.089721


# --- spacing limits and errors (feature 003, User Story 3) ----------------------


def test_step_below_one_sample_is_raised_and_reported(client, monkeypatch):
    monkeypatch.setattr(settings, "max_windows", 100000)
    audio = tone(440, 0.3)  # 13,230 samples -> one window per sample at the 1-sample minimum
    r = post(client, wav_bytes(audio, audio), window="4096", spacing="0.00001")
    assert r.status_code == 200
    job = r.json()
    assert job["spacing_raised"] is True
    assert job["window_spacing"] == 1 / 4096
    assert job["step_samples"] == 1
    assert job["window_count"] == len(audio)


def test_exactly_one_sample_is_not_reported_as_raised(client):
    audio = tone(440, 0.1)
    job = post(client, wav_bytes(audio, audio), window="4096", spacing=repr(1 / 4096)).json()
    assert job["spacing_raised"] is False
    assert job["step_samples"] == 1
    assert job["window_spacing"] == 1 / 4096


@pytest.mark.parametrize("spacing", ["0", "-1", "-0.5", "abc", "nan", "inf", "-inf", "1,5"])
def test_bad_window_spacing_is_refused(client, spacing):
    audio = tone(440, 0.2)
    r = post(client, wav_bytes(audio, audio), spacing=spacing)
    assert_rejected(r, 400, "window spacing", "greater than 0")


def test_too_many_windows_is_refused_before_analysis(client, monkeypatch):
    from app.routers import jobs
    from app.services.note_analysis import window_count

    def fail(*args, **kwargs):
        raise AssertionError("analysis must not run")

    monkeypatch.setattr(settings, "max_windows", 10)
    monkeypatch.setattr(jobs, "analyze_channels", fail)
    audio = tone(440, 1.0)
    expected = window_count(len(audio), 0.01 * 4096)
    assert expected > 10
    r = post(client, wav_bytes(audio, audio), window="4096", spacing="0.01")
    assert_rejected(r, 400, f"{expected:,} windows", "limit is 10", "larger window spacing")


def test_window_limit_does_not_apply_at_the_default_spacing(client):
    audio = tone(440, 3.0)
    job = post(client, wav_bytes(audio, audio)).json()
    assert job["window_count"] < settings.max_windows


def test_a_huge_window_count_is_refused_quickly_without_building_windows(client):
    import time

    audio = tone(440, 5.0)
    started = time.perf_counter()
    r = post(client, wav_bytes(audio, audio), window="32768", spacing="0.00003051")
    assert_rejected(r, 400, "windows", "limit is 60,000", "larger window spacing")
    assert time.perf_counter() - started < 2


def test_spacing_larger_than_the_file_gives_one_window(client):
    audio = tone(440, 1.0)
    r = post(client, wav_bytes(audio, audio), window="4096", spacing="1000")
    assert r.status_code == 200
    job = r.json()
    assert job["window_count"] == 1
    assert job["spacing_raised"] is False
    assert job["frame_count"] == 30  # every frame uses that one window


def test_recovers_after_a_spacing_error(client):
    audio = tone(440, 0.2)
    data = wav_bytes(audio, audio)
    assert post(client, data, spacing="0").status_code == 400
    assert post(client, data, spacing="0.5").status_code == 200
