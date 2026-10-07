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


@pytest.fixture
def full_client(client, monkeypatch):
    """A client whose frames are all at full brightness, whatever the loudness.

    The tests of the note-level pipeline (scaling, the brightness root, smoothing, layout) read each tile's
    gray level from its saturation, which is exact when the frame's brightness is 1. Energy is tested on its own
    in test_energy_api.py with the real measure.
    """
    from app.routers import jobs

    monkeypatch.setattr(jobs, "frame_energies", lambda left, right, rate, fps, frames: np.ones(frames))
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


def post(
    client, data, window="4096", fps="30", name="song.wav", spacing=None, brightness=None, smoothing=None, energy=None
):
    form = {"window_size": window, "frame_rate": fps}
    if energy is not None:
        form["energy"] = energy
    if spacing is not None:
        form["window_spacing"] = spacing
    if brightness is not None:
        form["brightness"] = brightness
    if smoothing is not None:
        form["smoothing"] = smoothing
    return client.post("/api/jobs", files={"file": (name, data, "audio/wav")}, data=form)


def frame_levels(client, job, index):
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    assert r.status_code == 200
    img = Image.open(io.BytesIO(r.content))
    rgb = np.asarray(img.convert("RGB")).astype(int)
    # a tile's gray level is its saturation: the largest colour channel minus the smallest, when the frame is at
    # full brightness (use full_client); otherwise it is that level scaled by the frame's brightness
    arr = rgb.max(axis=2) - rgb.min(axis=2)
    # one value per note: the centre pixel of tile n, which is at row n // 12, column n % 12 (24 x 21 pixel tiles)
    return np.array([arr[(n // 12) * 24 + 12, (n % 12) * 21 + 10] for n in range(84)])


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


def test_loudest_note_reaches_white_somewhere(full_client):
    audio = tone(440, 1.0)
    job = post(full_client, wav_bytes(audio, audio)).json()
    peak = max(frame_levels(full_client, job, i).max() for i in range(job["frame_count"]))
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
    assert img.size == (252, 168)


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


def test_spacing_one_matches_consecutive_window_analysis(full_client):
    """SC-002: spacing 1 gives the frames the application produced before spacing existed."""
    from app.services.frame_rendering import average_frames, boost_levels, frame_count, to_gray_levels
    from app.services.note_analysis import analyze_channels, read_wav

    left, right = tone(440, 2.0), tone(660, 2.0)
    job = post(full_client, wav_bytes(left, right), window="4096", spacing="1").json()
    rate, l, r = read_wav(settings.audio_temp_dir / job["job_id"] / "audio.wav")
    # consecutive windows: starts at multiples of the window size, the previous default behavior
    result = analyze_channels(l, r, rate, 4096)
    assert result.starts.tolist() == [i * 4096 for i in range(math.ceil(len(l) / 4096))]
    expected = boost_levels(to_gray_levels(average_frames(result, 30, frame_count(len(l), rate, 30))))
    for index in (0, 7, 30, 59):
        assert np.array_equal(frame_levels(full_client, job, index), expected[index][:84])


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


# --- brightness (feature 004) ---------------------------------------------------


def raw_levels(client, job, count=None):
    """The pre-brightness 0..255 levels for the frames of a stored job, computed straight from the services."""
    from app.services.frame_rendering import average_frames, frame_count, to_gray_levels
    from app.services.note_analysis import analyze_channels, read_wav

    rate, left, right = read_wav(settings.audio_temp_dir / job["job_id"] / "audio.wav")
    result = analyze_channels(left, right, rate, job["window_size"], step=job["step_samples"])
    frames = average_frames(result, job["frame_rate"], frame_count(len(left), rate, job["frame_rate"]))
    return to_gray_levels(frames)


def displayed(levels, brightness):
    """Independent computation of the displayed level (does not use boost_levels)."""
    return np.array([round(255 * (int(v) / 255) ** (1 / brightness)) for v in levels.reshape(-1)]).reshape(levels.shape)


def test_no_brightness_means_two_and_matches_the_old_square_root(full_client):
    left, right = tone(440, 1.0), tone(660, 1.0)
    job = post(full_client, wav_bytes(left, right)).json()
    assert job["brightness"] == 2
    levels = raw_levels(full_client, job)
    for index in (0, 5, 29):
        assert np.array_equal(frame_levels(full_client, job, index), displayed(levels[index][:84], 2))
        assert np.array_equal(
            frame_levels(full_client, job, index), np.array([round(255 * (v / 255) ** 0.5) for v in levels[index][:84]])
        )


def test_brightness_four_uses_the_fourth_root(full_client):
    audio = tone(440, 1.0)
    job = post(full_client, wav_bytes(audio, audio), brightness="4").json()
    assert job["brightness"] == 4
    levels = raw_levels(full_client, job)
    for index in (0, 10, 29):
        assert np.array_equal(frame_levels(full_client, job, index), displayed(levels[index][:84], 4))


def test_brightness_changes_only_the_gray_levels(client):
    left, right = tone(440, 1.0), tone(660, 1.0)
    data = wav_bytes(left, right)
    jobs = {b: post(client, data, brightness=str(b)).json() for b in (2, 4, 10)}
    keys = ("frame_count", "window_count", "step_samples", "window_spacing", "duration_seconds", "frame_rate")
    for b in (4, 10):
        assert {k: jobs[b][k] for k in keys} == {k: jobs[2][k] for k in keys}
    previous_mean = -1.0
    for b in (2, 4, 10):
        first = frame_levels(client, jobs[b], 0)
        assert first.mean() > previous_mean
        previous_mean = first.mean()
    for index in (0, 10, 29):
        low, mid, high = (frame_levels(client, jobs[b], index) for b in (2, 4, 10))
        assert (mid >= low).all() and (high >= mid).all()


@pytest.mark.parametrize("brightness", ["2", "100"])
def test_silent_file_stays_black_at_any_brightness(client, brightness):
    job = post(client, wav_bytes(np.zeros(SR), np.zeros(SR)), brightness=brightness).json()
    for index in (0, 15, 29):
        assert not frame_levels(client, job, index).any()


@pytest.mark.parametrize("brightness", [None, "10"])
def test_the_loudest_note_is_still_the_brightest_square(client, brightness):
    audio = tone(40 * SR / 4096, 1.0)
    job = post(client, wav_bytes(audio, audio), brightness=brightness).json()
    hits = sum(frame_levels(client, job, i).argmax() == 36 for i in range(job["frame_count"]))
    assert hits / job["frame_count"] >= 0.95


def test_same_brightness_gives_identical_frames(client):
    audio = tone(440, 1.0)
    data = wav_bytes(audio, audio)
    a = post(client, data, brightness="4").json()
    b = post(client, data, brightness="4").json()
    for index in (0, 10, 29):
        ra = client.get(a["frame_url_template"].replace("{index}", str(index))).content
        rb = client.get(b["frame_url_template"].replace("{index}", str(index))).content
        assert ra == rb


def test_a_whole_number_with_a_decimal_point_is_accepted(client):
    audio = tone(440, 0.3)
    job = post(client, wav_bytes(audio, audio), brightness="5.0").json()
    assert job["brightness"] == 5


# --- brightness: refusing bad values (feature 004, User Story 2) -----------------
# These confirm the strict rule written with the router change; they pass as soon as they are added.


@pytest.mark.parametrize("brightness", ["1", "101", "0", "-3", "2.5", "abc", "nan", "inf", "-inf", "1e9", "", "  "])
def test_bad_brightness_is_refused(client, brightness):
    audio = tone(440, 0.2)
    r = post(client, wav_bytes(audio, audio), brightness=brightness)
    assert_rejected(r, 400, "brightness", "whole number", "2", "100")
    assert r.json()["detail"] == "The brightness must be a whole number from 2 to 100."


def test_a_refused_brightness_never_reads_the_file(client, monkeypatch):
    from app.routers import jobs

    def fail(*args, **kwargs):
        raise AssertionError("the file must not be read")

    monkeypatch.setattr(jobs, "read_wav", fail)
    audio = tone(440, 0.2)
    assert_rejected(post(client, wav_bytes(audio, audio), brightness="101"), 400, "brightness")


@pytest.mark.parametrize("brightness", ["2", "100"])
def test_the_limits_are_accepted(client, brightness):
    audio = tone(440, 0.2)
    r = post(client, wav_bytes(audio, audio), brightness=brightness)
    assert r.status_code == 200
    assert r.json()["brightness"] == int(brightness)


def test_recovers_after_a_brightness_error(client):
    audio = tone(440, 0.2)
    data = wav_bytes(audio, audio)
    assert post(client, data, brightness="1").status_code == 400
    assert post(client, data, brightness="3").status_code == 200


# --- octave grid layout (feature 005) --------------------------------------------


def note_tone(note, seconds=1.0, window=4096):
    """A tone at the exact centre of the spectrum position the analysis reads for this note."""
    from app.services.note_analysis import NoteBinAnalyzer

    return tone(NoteBinAnalyzer(SR, window).bin_indices[note] * SR / window, seconds)


def tile_means(client, job, index):
    """Mean gray of each tile as a 7 x 12 array, found from the pixels alone (rows = octaves, columns = notes)."""
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    rgb = np.asarray(Image.open(io.BytesIO(r.content)).convert("RGB")).astype(float)
    arr = rgb.max(axis=2) - rgb.min(axis=2)  # a tile's gray level is its saturation (use full_client)
    return arr.reshape(7, 24, 12, 21).mean(axis=(1, 3))


def brightest_tile_share(client, job, row, col):
    hits = sum(
        np.unravel_index(tile_means(client, job, i).argmax(), (7, 12)) == (row, col)
        for i in range(job["frame_count"])
    )
    return hits / job["frame_count"]


def test_frame_images_are_252_by_168_and_exactly_three_to_two(client):
    audio = tone(440, 0.5)
    job = post(client, wav_bytes(audio, audio)).json()
    for index in (0, job["frame_count"] - 1):
        r = client.get(job["frame_url_template"].replace("{index}", str(index)))
        img = Image.open(io.BytesIO(r.content))
        assert img.size == (252, 168)
        assert img.size[0] * 2 == img.size[1] * 3


@pytest.mark.parametrize("note, row, col", [(36, 3, 0), (48, 4, 0), (60, 5, 0), (83, 6, 11)])
def test_a_steady_note_lights_the_tile_for_its_octave_and_note_name(full_client, note, row, col):
    audio = note_tone(note)
    job = post(full_client, wav_bytes(audio, audio)).json()
    assert brightest_tile_share(full_client, job, row, col) >= 0.95


def test_the_tile_below_a_lit_tile_is_the_next_octave(full_client):
    """Note 36 is at row 3, column 0; note 48, an octave up (double the frequency), is directly below it."""
    low = post(full_client, wav_bytes(*(2 * [note_tone(36)]))).json()
    high = post(full_client, wav_bytes(*(2 * [note_tone(48)]))).json()
    (r1, c1), (r2, c2) = (
        np.unravel_index(tile_means(full_client, job, 5).argmax(), (7, 12)) for job in (low, high)
    )
    assert (r2, c2) == (r1 + 1, c1)


def test_one_of_the_four_omitted_notes_leaves_no_visible_tile_at_full_white(client):
    audio = note_tone(86)  # 7902 Hz is not drawn, but it still sets the 0-255 scale
    job = post(client, wav_bytes(audio, audio)).json()
    for index in (0, 10, 29):
        assert frame_levels(client, job, index).max() < 255


# --- note smoothing (feature 006) -------------------------------------------------


def frame_values(job):
    """The averaged note values per frame of a stored job, before smoothing and scaling, from the services."""
    from app.services.frame_rendering import average_frames, frame_count
    from app.services.note_analysis import analyze_channels, read_wav

    rate, left, right = read_wav(settings.audio_temp_dir / job["job_id"] / "audio.wav")
    result = analyze_channels(left, right, rate, job["window_size"], step=job["step_samples"])
    return average_frames(result, job["frame_rate"], frame_count(len(left), rate, job["frame_rate"]))


def ref_smooth(values, s):
    """The running average written out by hand (not using smooth_frames)."""
    out = [list(values[0])]
    for n in range(1, len(values)):
        out.append([s * out[n - 1][k] + (1 - s) * values[n][k] for k in range(len(values[n]))])
    return np.array(out)


def expected_pixels(job, smoothing, brightness=2):
    """Frame pixels worked out independently: smooth the values, scale them to 0-255, then brighten."""
    from app.services.frame_rendering import to_gray_levels

    values = frame_values(job)
    if smoothing:
        values = ref_smooth(values.tolist(), smoothing)
    return displayed(to_gray_levels(values), brightness)[:, :84]


def burst_then_silence():
    """A steady note for one second, then silence for one second (60 frames at 30 fps)."""
    return np.concatenate([note_tone(36, 1.0), np.zeros(SR)])


def test_no_smoothing_means_zero_and_matches_the_unsmoothed_pipeline(full_client):
    audio = burst_then_silence()
    job = post(full_client, wav_bytes(audio, audio)).json()
    assert job["smoothing"] == 0.0
    expected = expected_pixels(job, 0)
    for index in (0, 20, 29, 31, 40, 59):
        assert np.array_equal(frame_levels(full_client, job, index), expected[index])


@pytest.mark.parametrize("smoothing", ["0", "0.0", "-0.0"])
def test_zero_smoothing_gives_byte_identical_frames_to_no_field(client, smoothing):
    audio = burst_then_silence()
    data = wav_bytes(audio, audio)
    plain = post(client, data).json()
    zero = post(client, data, smoothing=smoothing).json()
    assert zero["smoothing"] == 0.0
    for index in (0, 29, 31, 59):
        a = client.get(plain["frame_url_template"].replace("{index}", str(index))).content
        b = client.get(zero["frame_url_template"].replace("{index}", str(index))).content
        assert a == b


def test_half_smoothing_gives_the_running_average_of_each_note(full_client):
    audio = burst_then_silence()
    job = post(full_client, wav_bytes(audio, audio), smoothing="0.5").json()
    assert job["smoothing"] == 0.5
    expected = expected_pixels(job, 0.5)
    for index in (0, 1, 15, 29, 30, 31, 33, 40, 59):
        assert np.array_equal(frame_levels(full_client, job, index), expected[index]), index


def test_a_stopped_note_fades_more_slowly_at_higher_smoothing(full_client):
    audio = burst_then_silence()
    data = wav_bytes(audio, audio)
    at = {s: post(full_client, data, smoothing=s).json() for s in ("0", "0.5", "0.8")}
    after_stop = 35  # about 5 frames after the note stops
    tile = {s: int(frame_levels(full_client, job, after_stop)[36]) for s, job in at.items()}
    assert tile["0"] == 0  # no smoothing: the tile is already black
    assert tile["0.8"] > tile["0.5"] > tile["0"]


def test_smoothing_does_not_change_counts_or_timing(client):
    audio = burst_then_silence()
    data = wav_bytes(audio, audio)
    jobs = [post(client, data, smoothing=s).json() for s in ("0", "0.5", "0.8")]
    keys = ("frame_count", "window_count", "step_samples", "window_spacing", "duration_seconds", "frame_rate")
    for job in jobs[1:]:
        assert {k: job[k] for k in keys} == {k: jobs[0][k] for k in keys}


@pytest.mark.parametrize("smoothing", ["0", "0.8"])
def test_a_silent_file_stays_black_at_any_smoothing(client, smoothing):
    job = post(client, wav_bytes(np.zeros(SR), np.zeros(SR)), smoothing=smoothing).json()
    for index in (0, 15, 29):
        assert not frame_levels(client, job, index).any()


def test_the_same_smoothing_gives_identical_frames(client):
    audio = burst_then_silence()
    data = wav_bytes(audio, audio)
    a = post(client, data, smoothing="0.5").json()
    b = post(client, data, smoothing="0.5").json()
    for index in (0, 20, 31, 59):
        ra = client.get(a["frame_url_template"].replace("{index}", str(index))).content
        rb = client.get(b["frame_url_template"].replace("{index}", str(index))).content
        assert ra == rb


def test_the_loudest_smoothed_value_still_reaches_white(client):
    audio = burst_then_silence()
    job = post(client, wav_bytes(audio, audio), smoothing="0.8").json()
    assert max(frame_levels(client, job, i).max() for i in range(job["frame_count"])) == 255


@pytest.mark.parametrize("smoothing, expected", [("0.8", 0.8), ("0.35", 0.35), ("0.123456", 0.123456)])
def test_smoothing_values_in_range_are_accepted_and_reported(client, smoothing, expected):
    audio = tone(440, 0.3)
    r = post(client, wav_bytes(audio, audio), smoothing=smoothing)
    assert r.status_code == 200
    assert r.json()["smoothing"] == expected


# --- smoothing: refusing bad values (feature 006, User Story 2) ---------------------
# These confirm the strict rule written with the router change; they pass as soon as they are added.


@pytest.mark.parametrize("smoothing", ["-0.1", "0.81", "1", "1e9", "abc", "nan", "inf", "-inf", "", "  "])
def test_bad_smoothing_is_refused(client, smoothing):
    audio = tone(440, 0.2)
    r = post(client, wav_bytes(audio, audio), smoothing=smoothing)
    assert_rejected(r, 400, "smoothing", "0.0", "0.8")
    assert r.json()["detail"] == "The smoothing must be a number from 0.0 to 0.8."


def test_a_refused_smoothing_never_reads_the_file(client, monkeypatch):
    from app.routers import jobs

    def fail(*args, **kwargs):
        raise AssertionError("the file must not be read")

    monkeypatch.setattr(jobs, "read_wav", fail)
    audio = tone(440, 0.2)
    assert_rejected(post(client, wav_bytes(audio, audio), smoothing="0.81"), 400, "smoothing")


def test_recovers_after_a_smoothing_error(client):
    audio = tone(440, 0.2)
    data = wav_bytes(audio, audio)
    assert post(client, data, smoothing="-0.1").status_code == 400
    assert post(client, data, smoothing="0.3").status_code == 200


# --- harmonic colour (feature 007) ----------------------------------------------------


def frame_rgb(client, job, index):
    """The centre-pixel colour of each of the 84 tiles of a served frame, shape (84, 3)."""
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    assert r.status_code == 200
    arr = np.asarray(Image.open(io.BytesIO(r.content)).convert("RGB"))
    return np.array([arr[(n // 12) * 24 + 12, (n % 12) * 21 + 10] for n in range(84)])


def two_notes():
    """Note 24 and its first "down" partner (24 + RELATED_DOWN[0]) sounding together for one second."""
    from app.services.frame_rendering import RELATED_DOWN

    return (note_tone(24) + note_tone(24 + RELATED_DOWN[0])) / 2


def ref_hue_fractions(job, index, brightness=2, smoothing=0):
    """The hue of each tile worked out independently from the displayed gray levels of all 88 notes."""
    from app.services.frame_rendering import to_gray_levels

    values = frame_values(job)
    if smoothing:
        values = ref_smooth(values.tolist(), smoothing)
    shown = displayed(to_gray_levels(values)[index], brightness) / 255

    from app.services.frame_rendering import RELATED_DOWN, RELATED_UP

    def lum(k):
        return shown[k] if 0 <= k < 88 else 0.0

    # the brightness of the partners is added (not averaged) and the hue is clipped to the wheel
    return np.array(
        [
            min(
                1.0,
                max(
                    0.0,
                    0.5 + 0.5 * (sum(lum(n + o) for o in RELATED_UP) - sum(lum(n + o) for o in RELATED_DOWN)),
                ),
            )
            for n in range(84)
        ]
    )


def hue_gap_degrees(a, b):
    d = abs(a - b) % 1.0
    return min(d, 1 - d) * 360


def test_served_frames_are_rgb_images_of_the_same_size_and_shape(client):
    audio = two_notes()
    job = post(client, wav_bytes(audio, audio)).json()
    for index in (0, job["frame_count"] - 1):
        r = client.get(job["frame_url_template"].replace("{index}", str(index)))
        img = Image.open(io.BytesIO(r.content))
        assert img.mode in ("P", "RGB")  # saved as an indexed-colour PNG; it decodes to exact RGB values
        assert np.asarray(img.convert("RGB")).shape == (168, 252, 3)
        assert img.size == (252, 168)
        assert img.size[0] * 2 == img.size[1] * 3


def expected_values(data, fps=30, root=1):
    """Each frame's brightness worked out from the WAV bytes by the plain-Python reference in test_energy.py."""
    from .test_energy import reference_energies

    rate, arr = wavfile.read(io.BytesIO(data))
    left, right = (arr, arr) if arr.ndim == 1 else (arr[:, 0], arr[:, 1])
    scale = float(np.iinfo(arr.dtype).max) + 1.0
    frames = math.ceil(len(left) * fps / rate - 1e-9)
    energies = np.array(reference_energies(left / scale, right / scale, rate, fps, frames))
    peak = energies.max()
    return (energies / peak) ** (1.0 / root) if peak > 0 else np.zeros(frames)


def test_every_tile_has_the_frames_brightness_and_its_own_level_as_its_saturation(client):
    audio = two_notes()
    data = wav_bytes(audio, audio)
    job = post(client, data).json()
    levels = expected_pixels(job, 0)  # gray levels worked out independently of the drawing code
    value = expected_values(data)  # the frame's energy relative to the loudest frame (root 1)
    assert value.max() == 1.0
    for index in (0, 5, 15, 29):
        rgb = frame_rgb(client, job, index)
        top = round(255 * value[index])
        assert (np.abs(rgb.max(axis=1) - top) <= 1).all(), index  # the same brightness in every tile of the frame
        darkest = top * (1 - levels[index] / 255)  # saturation is the tile's own level
        assert (np.abs(rgb.min(axis=1) - darkest) <= 1.5).all(), index


def hue_readable(rgb):
    """Whether a tile's hue can be read back from its 8-bit colour: bright enough and saturated enough."""
    top, low = int(rgb.max()), int(rgb.min())
    return top >= 128 and (top - low) / top >= 0.5


def test_the_hue_of_a_tile_follows_the_related_notes(client):
    import colorsys

    audio = two_notes()
    job = post(client, wav_bytes(audio, audio)).json()
    checked = 0
    for index in (3, 10, 20):
        rgb = frame_rgb(client, job, index)
        expected = ref_hue_fractions(job, index)
        for n in range(84):
            if hue_readable(rgb[n]):
                h, _s, _v = colorsys.rgb_to_hsv(*(rgb[n] / 255))
                assert hue_gap_degrees(h, expected[n]) <= 2.0, (index, n)
                checked += 1
    assert checked > 0
    # the second note is a "down" partner of note 24, so tile 24 is pulled below 180 degrees while both sound
    rgb = frame_rgb(client, job, 10)
    h, _s, _v = colorsys.rgb_to_hsv(*(rgb[24] / 255))
    assert h * 360 < 180


def test_a_single_steady_note_is_cyan(client):
    import colorsys

    audio = note_tone(40)
    data = wav_bytes(audio, audio)
    job = post(client, data).json()
    rgb = frame_rgb(client, job, 10)
    most_saturated = int((rgb.max(axis=1).astype(int) - rgb.min(axis=1)).argmax())
    assert most_saturated == 40  # the loudest note has the most saturated tile
    h, s, v = colorsys.rgb_to_hsv(*(rgb[40] / 255))
    assert abs(h * 360 - 180) <= 3
    assert s > 0.9
    # every tile has the frame's brightness: its energy relative to the loudest frame (a steady tone: nearly 1)
    assert v == pytest.approx(expected_values(data)[10], abs=0.02)
    assert v > 0.9
    assert (rgb.max(axis=1) == rgb[40].max()).all()


@pytest.mark.parametrize("brightness, smoothing", [("2", "0"), ("100", "0"), ("2", "0.8")])
def test_a_silent_file_is_black_in_every_channel(client, brightness, smoothing):
    job = post(client, wav_bytes(np.zeros(SR), np.zeros(SR)), brightness=brightness, smoothing=smoothing).json()
    for index in (0, 15, 29):
        r = client.get(job["frame_url_template"].replace("{index}", str(index)))
        arr = np.asarray(Image.open(io.BytesIO(r.content)).convert("RGB"))
        assert arr.shape == (168, 252, 3) and not arr.any()


def test_counts_and_timing_do_not_depend_on_colour(client):
    audio = two_notes()
    job = post(client, wav_bytes(audio, audio)).json()
    assert job["frame_count"] == math.ceil(job["duration_seconds"] * job["frame_rate"] - 1e-9)
    assert job["window_count"] >= job["frame_count"]
    assert job["step_samples"] > 0 and job["window_spacing"] > 0


def test_the_same_file_and_settings_give_byte_identical_colour_frames(client):
    audio = two_notes()
    data = wav_bytes(audio, audio)
    a = post(client, data).json()
    b = post(client, data).json()
    for index in (0, 10, 29):
        ra = client.get(a["frame_url_template"].replace("{index}", str(index))).content
        rb = client.get(b["frame_url_template"].replace("{index}", str(index))).content
        assert ra == rb


def test_brightness_and_smoothing_still_set_the_tile_saturation(full_client):
    audio = burst_then_silence()
    data = wav_bytes(audio, audio)
    four = post(full_client, data, brightness="4").json()
    expected = expected_pixels(four, 0, brightness=4)
    for index in (5, 20, 33):
        assert np.array_equal(frame_levels(full_client, four, index), expected[index])
    smooth = post(full_client, data, smoothing="0.5").json()
    expected = expected_pixels(smooth, 0.5)
    for index in (5, 30, 33):
        assert np.array_equal(frame_levels(full_client, smooth, index), expected[index])


def test_the_loudest_frame_reaches_full_brightness_in_every_tile(client):
    audio = two_notes()
    job = post(client, wav_bytes(audio, audio)).json()
    assert max(frame_rgb(client, job, i).max() for i in range(job["frame_count"])) == 255
    loudest = int(expected_values(wav_bytes(audio, audio)).argmax())
    assert (frame_rgb(client, job, loudest).max(axis=1) == 255).all()


# --- smoothing also applies to the hues (feature 006 and 007) ---------------------------


def partner_burst():
    """Note 24 and its first "down" partner for one second, then silence: the tile's hue changes over time."""
    return np.concatenate([two_notes(), np.zeros(SR)])


def ref_smoothed_hue_rows(job, smoothing):
    """Per-frame hues worked out independently: smooth the values, scale, brighten, hue, then smooth the hues."""
    from app.services.frame_rendering import RELATED_DOWN, RELATED_UP, to_gray_levels

    values = frame_values(job)
    if smoothing:
        values = ref_smooth(values.tolist(), smoothing)
    levels = to_gray_levels(values)
    raw = []
    for row in levels:
        shown = displayed(row, 2) / 255

        def lum(k):
            return shown[k] if 0 <= k < 88 else 0.0

        raw.append(
            [
                min(1.0, max(0.0, 0.5 + 0.5 * (sum(lum(n + o) for o in RELATED_UP) - sum(lum(n + o) for o in RELATED_DOWN))))
                for n in range(84)
            ]
        )
    raw = np.array(raw)
    out = [raw[0].copy()]
    for n in range(1, len(raw)):
        out.append(smoothing * out[n - 1] + (1 - smoothing) * raw[n])
    return raw, np.array(out)


def pixel_hue_fraction(rgb):
    import colorsys

    return colorsys.rgb_to_hsv(*(rgb / 255))[0]


def test_the_hues_in_the_served_frames_are_smoothed_with_the_same_parameter(client):
    audio = partner_burst()
    job = post(client, wav_bytes(audio, audio), smoothing="0.5").json()
    raw, smoothed = ref_smoothed_hue_rows(job, 0.5)
    checked = differs = 0
    for index in range(0, 40):
        rgb = frame_rgb(client, job, index)
        for n in (24, 28):  # the two notes that are sounding; their tiles are saturated and their colour is readable
            if hue_readable(rgb[n]):
                got = pixel_hue_fraction(rgb[n])
                gap = abs(got - smoothed[index][n]) % 1.0
                assert min(gap, 1 - gap) * 360 <= 2.0, (index, n, got * 360, smoothed[index][n] * 360)
                checked += 1
                raw_gap = abs(got - raw[index][n]) % 1.0
                differs += int(min(raw_gap, 1 - raw_gap) * 360 > 2.0)
    assert checked > 10
    assert differs > 0  # smoothing the hues really changes the colours compared with the unsmoothed hues


def test_without_smoothing_the_hues_are_the_unsmoothed_ones(client):
    audio = partner_burst()
    job = post(client, wav_bytes(audio, audio)).json()
    raw, smoothed = ref_smoothed_hue_rows(job, 0)
    assert np.array_equal(raw, smoothed)
    checked = 0
    for index in range(0, 30, 3):
        rgb = frame_rgb(client, job, index)
        for n in (24, 28):
            if hue_readable(rgb[n]):
                got = pixel_hue_fraction(rgb[n])
                gap = abs(got - raw[index][n]) % 1.0
                assert min(gap, 1 - gap) * 360 <= 2.0
                checked += 1
    assert checked > 5


def test_hue_smoothing_does_not_change_saturation_counts_or_timing(full_client):
    audio = partner_burst()
    data = wav_bytes(audio, audio)
    a = post(full_client, data, smoothing="0.8").json()
    b = post(full_client, data, smoothing="0.8").json()
    keys = ("frame_count", "window_count", "step_samples", "window_spacing", "duration_seconds")
    assert {k: a[k] for k in keys} == {k: b[k] for k in keys}
    expected = expected_pixels(a, 0.8)  # the saturation is still the smoothed, scaled, brightened gray level
    for index in (3, 15, 29, 35):
        assert np.array_equal(frame_levels(full_client, a, index), expected[index])
    for index in (0, 10, 40):  # byte-identical on repeat
        ra = full_client.get(a["frame_url_template"].replace("{index}", str(index))).content
        rb = full_client.get(b["frame_url_template"].replace("{index}", str(index))).content
        assert ra == rb
