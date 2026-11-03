"""The video endpoints: ``POST`` and ``GET /api/jobs/{job_id}/video`` (feature 029)."""

import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from PIL import Image

import app.services.video as video
from app.config import settings
from app.services.image_types import IMAGE_TYPES

from .test_jobs_api import client, post  # noqa: F401
from .test_resolution_api import tiny

REAL_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
KEYS = {"job_id", "file_name", "path", "size_bytes", "frame_count", "frame_rate", "duration_seconds", "url"}


@pytest.fixture
def api(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", tmp_path / "output")
    return client


def render(api, fps="10", **fields):
    r = api.post(
        "/api/jobs",
        files={"file": ("song.wav", tiny(), "audio/wav")},
        data={"window_size": "4096", "frame_rate": fps, **fields},
    )
    assert r.status_code == 200, r.text
    return r.json()


def fake_ffmpeg(monkeypatch, data=b"mp4 bytes", returncode=0):
    def run(command, **kwargs):
        if returncode == 0:
            Path(command[-1]).write_bytes(data)
        return subprocess.CompletedProcess(command, returncode, b"", b"stderr text")

    monkeypatch.setattr(video.subprocess, "run", run)


def ffprobe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,r_frame_rate", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True,
        check=True,
    )
    return json.loads(out.stdout)


# --- the answer ----------------------------------------------------------------------------------------------------------------


def test_the_answer_has_the_keys_of_the_contract_and_the_file_is_under_the_output_directory(api, monkeypatch, tmp_path):
    job = render(api)
    fake_ffmpeg(monkeypatch)
    r = api.post(f"/api/jobs/{job['job_id']}/video")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == KEYS
    assert body["job_id"] == job["job_id"] and body["file_name"] == "video.mp4"
    assert body["url"] == f"/api/jobs/{job['job_id']}/video"
    assert Path(body["path"]) == tmp_path / "output" / job["job_id"] / "video.mp4"
    assert Path(body["path"]).read_bytes() == b"mp4 bytes" and body["size_bytes"] == 9
    assert body["frame_count"] == job["frame_count"] and body["frame_rate"] == job["frame_rate"]
    assert body["duration_seconds"] == pytest.approx(job["frame_count"] / job["frame_rate"])


def test_rendering_records_the_frame_rate_next_to_the_frames(api):
    job = render(api, fps="24.5")
    record = json.loads((settings.frames_temp_dir / job["job_id"] / "render.json").read_text())
    assert record == {"frame_rate": 24.5}


def test_a_refused_render_leaves_no_frames_behind(api):
    r = api.post("/api/jobs", files={"file": ("song.wav", tiny(), "audio/wav")}, data={"window_size": "4096", "frame_rate": "nope"})
    assert r.status_code == 400
    assert not settings.frames_temp_dir.exists() or not list(settings.frames_temp_dir.iterdir())


# --- errors --------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("job_id", ["ABC", "a" * 31, "g" * 32, "A" * 32, "a" * 33])
def test_a_malformed_id_is_not_found_for_both_methods(api, job_id):
    assert api.post(f"/api/jobs/{job_id}/video").status_code == 404
    assert api.get(f"/api/jobs/{job_id}/video").status_code == 404


def test_an_unknown_render_says_to_render_again_and_makes_nothing(api, tmp_path):
    r = api.post(f"/api/jobs/{'a' * 32}/video")
    assert r.status_code == 404 and r.json() == {"detail": "The frames of this render are no longer available. Render again."}
    assert not (tmp_path / "output" / ("a" * 32)).exists()


def test_a_render_without_its_record_is_gone_too(api):
    job = render(api)
    (settings.frames_temp_dir / job["job_id"] / "render.json").unlink()
    assert api.post(f"/api/jobs/{job['job_id']}/video").status_code == 404


def test_cleaned_up_frames_are_gone(api):
    job = render(api)
    shutil.rmtree(settings.frames_temp_dir / job["job_id"])
    assert api.post(f"/api/jobs/{job['job_id']}/video").status_code == 404


def test_a_missing_ffmpeg_is_a_503_with_its_message(api, monkeypatch, tmp_path):
    job = render(api)
    monkeypatch.setattr(settings, "ffmpeg_path", "no-such-ffmpeg-anywhere")
    r = api.post(f"/api/jobs/{job['job_id']}/video")
    assert r.status_code == 503
    assert r.json() == {"detail": "ffmpeg was not found. Install it, or set MV_FFMPEG_PATH to its location."}
    assert not (tmp_path / "output" / job["job_id"]).exists()


def test_a_failing_ffmpeg_is_a_500_and_leaves_no_file(api, monkeypatch, tmp_path):
    job = render(api)
    script = tmp_path / "fail.py"
    script.write_text("import sys; sys.exit(1)")
    monkeypatch.setattr(video.shutil, "which", lambda name: name)
    real_run = subprocess.run
    monkeypatch.setattr(video.subprocess, "run", lambda command, **kw: real_run([sys.executable, str(script)], **kw))
    r = api.post(f"/api/jobs/{job['job_id']}/video")
    assert r.status_code == 500 and r.json() == {"detail": "Something went wrong while making the video."}
    assert not (tmp_path / "output" / job["job_id"]).exists()


def test_a_slow_ffmpeg_is_a_504(api, monkeypatch):
    job = render(api)
    monkeypatch.setattr(video.shutil, "which", lambda name: name)

    def slow(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 1)

    monkeypatch.setattr(video.subprocess, "run", slow)
    r = api.post(f"/api/jobs/{job['job_id']}/video")
    assert r.status_code == 504 and "too long" in r.json()["detail"]


def test_a_second_request_while_one_runs_is_a_409_and_the_third_works(api, monkeypatch):
    job = render(api)
    url = f"/api/jobs/{job['job_id']}/video"
    monkeypatch.setattr(video.shutil, "which", lambda name: name)
    started, release = threading.Event(), threading.Event()

    def blocking(command, **kwargs):
        started.set()
        assert release.wait(10)
        Path(command[-1]).write_bytes(b"x")
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(video.subprocess, "run", blocking)
    first = {}
    worker = threading.Thread(target=lambda: first.update(r=api.post(url)))
    worker.start()
    try:
        assert started.wait(10)
        second = api.post(url)
        assert second.status_code == 409 and second.json() == {"detail": "A video is already being made for this render."}
    finally:
        release.set()
        worker.join(10)
    assert first["r"].status_code == 200
    assert api.post(url).status_code == 200


# --- download and replace ------------------------------------------------------------------------------------------------------


def test_the_file_can_be_downloaded(api, monkeypatch):
    job = render(api)
    url = f"/api/jobs/{job['job_id']}/video"
    fake_ffmpeg(monkeypatch, data=b"the video")
    api.post(url)
    r = api.get(url)
    assert r.status_code == 200 and r.content == b"the video"
    assert r.headers["content-type"] == "video/mp4"
    assert "attachment" in r.headers["content-disposition"] and "video.mp4" in r.headers["content-disposition"]


def test_nothing_to_download_before_the_video_is_made(api):
    job = render(api)
    r = api.get(f"/api/jobs/{job['job_id']}/video")
    assert r.status_code == 404 and r.json() == {"detail": "No video has been made for this render."}


def test_making_it_again_leaves_one_new_video(api, monkeypatch, tmp_path):
    job = render(api)
    url = f"/api/jobs/{job['job_id']}/video"
    fake_ffmpeg(monkeypatch, data=b"first")
    api.post(url)
    fake_ffmpeg(monkeypatch, data=b"second")
    assert api.post(url).status_code == 200
    assert [p.name for p in (tmp_path / "output" / job["job_id"]).iterdir()] == ["video.mp4"]
    assert api.get(url).content == b"second"


def test_two_renders_keep_two_videos(api, monkeypatch, tmp_path):
    a, b = render(api), render(api)
    fake_ffmpeg(monkeypatch, data=b"a")
    api.post(f"/api/jobs/{a['job_id']}/video")
    fake_ffmpeg(monkeypatch, data=b"b")
    api.post(f"/api/jobs/{b['job_id']}/video")
    assert api.get(f"/api/jobs/{a['job_id']}/video").content == b"a"
    assert api.get(f"/api/jobs/{b['job_id']}/video").content == b"b"


# --- the real ffmpeg -----------------------------------------------------------------------------------------------------------


@pytest.mark.skipif(not REAL_FFMPEG, reason="ffmpeg and ffprobe are not installed")
@pytest.mark.parametrize("image_type", IMAGE_TYPES)
def test_a_real_video_is_silent_h264_at_the_frame_rate_and_as_long_as_the_frames(api, image_type):
    job = render(api, fps="10", image_type=image_type)
    r = api.post(f"/api/jobs/{job['job_id']}/video")
    assert r.status_code == 200, r.text
    info = ffprobe(r.json()["path"])
    assert [s["codec_type"] for s in info["streams"]] == ["video"]
    assert info["streams"][0]["codec_name"] == "h264"
    assert info["streams"][0]["r_frame_rate"] == "10/1"
    assert abs(float(info["format"]["duration"]) - job["frame_count"] / job["frame_rate"]) <= 1 / job["frame_rate"]


@pytest.mark.skipif(not REAL_FFMPEG, reason="ffmpeg and ffprobe are not installed")
def test_a_real_video_with_a_fractional_frame_rate_matches_the_music(api):
    job = render(api, fps="24.5")
    r = api.post(f"/api/jobs/{job['job_id']}/video")
    assert r.status_code == 200, r.text
    info = ffprobe(r.json()["path"])
    assert abs(float(info["format"]["duration"]) - job["frame_count"] / 24.5) <= 1 / 24.5
    assert [s["codec_type"] for s in info["streams"]] == ["video"]


@pytest.mark.skipif(not REAL_FFMPEG, reason="ffmpeg and ffprobe are not installed")
def test_a_real_video_from_odd_sized_pictures_plays(api):
    directory = settings.frames_temp_dir / ("b" * 32)
    directory.mkdir(parents=True)
    for i in range(6):
        Image.new("RGB", (599, 399), (i * 40, 10, 10)).save(directory / f"frame_{i:06d}.png")
    (directory / "render.json").write_text(json.dumps({"frame_rate": 6}))
    r = api.post(f"/api/jobs/{'b' * 32}/video")
    assert r.status_code == 200, r.text
    stream = ffprobe(r.json()["path"])["streams"][0]
    assert stream["codec_name"] == "h264"
