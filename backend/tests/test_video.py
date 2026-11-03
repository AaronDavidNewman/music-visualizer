"""The service that joins the frames of a render into a silent MP4, with a fake ffmpeg (feature 029)."""

import json
import logging
import subprocess
from pathlib import Path

import pytest

import app.services.video as video
from app.services.video import (
    FRAMES_GONE,
    IN_PROGRESS,
    NOT_FOUND,
    TOO_LONG,
    VideoError,
    build_command,
    create_video,
)

JOB = "0123456789abcdef0123456789abcdef"
FFMPEG = "ffmpeg"


def make_render(frames_root: Path, job=JOB, count=5, frame_rate=24, record=True):
    directory = frames_root / job
    directory.mkdir(parents=True)
    for i in range(count):
        (directory / f"frame_{i:06d}.png").write_bytes(b"png")
    if record:
        (directory / "render.json").write_text(json.dumps({"frame_rate": frame_rate}))
    return directory


class FakeFfmpeg:
    """Stands in for subprocess.run: records the commands and writes the output file like ffmpeg would."""

    def __init__(self, returncode=0, data=b"mp4", error=None, write=True):
        self.returncode, self.data, self.error, self.write = returncode, data, error, write
        self.commands = []

    def __call__(self, command, **kwargs):
        self.commands.append(command)
        self.kwargs = kwargs
        if self.error:
            raise self.error
        if self.write:
            Path(command[-1]).write_bytes(self.data)
        return subprocess.CompletedProcess(command, self.returncode, b"", b"boom: something failed")


@pytest.fixture
def roots(tmp_path, monkeypatch):
    monkeypatch.setattr(video.shutil, "which", lambda name: name)
    return tmp_path / "frames", tmp_path / "output"


def run(roots, **kwargs):
    return create_video(JOB, frames_root=roots[0], output_root=roots[1], ffmpeg=FFMPEG, **kwargs)


# --- the command ---------------------------------------------------------------------------------------------------------------


def test_the_command_has_only_the_frames_as_input_and_no_audio():
    command = build_command("ffmpeg", Path("frames"), 24, Path("out.mp4"))
    assert command == [
        "ffmpeg", "-y", "-framerate", "24", "-start_number", "0", "-i", str(Path("frames") / "frame_%06d.png"),
        "-an", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "out.mp4",
    ]  # fmt: skip
    assert command.count("-i") == 1 and "-an" in command


@pytest.mark.parametrize("rate, text", [(24.5, "24.5"), (30, "30"), (30.0, "30"), (1, "1"), (60, "60"), (29.97, "29.97")])
def test_the_frame_rate_is_passed_as_it_is(rate, text):
    command = build_command("ffmpeg", Path("f"), rate, Path("o.mp4"))
    assert command[command.index("-framerate") + 1] == text


# --- making the video ----------------------------------------------------------------------------------------------------------


def test_the_video_is_made_in_the_directory_of_the_render_and_described(roots, monkeypatch):
    make_render(roots[0], count=48, frame_rate=24)
    fake = FakeFfmpeg(data=b"twelve bytes")
    monkeypatch.setattr(video.subprocess, "run", fake)
    result = run(roots)
    assert result.path == roots[1] / JOB / "video.mp4"
    assert result.path.read_bytes() == b"twelve bytes"
    assert (result.job_id, result.size_bytes, result.frame_count, result.frame_rate) == (JOB, 12, 48, 24)
    assert result.duration_seconds == 2
    assert [p.name for p in (roots[1] / JOB).iterdir()] == ["video.mp4"]
    assert len(fake.commands) == 1 and fake.commands[0][-1].endswith("video.tmp.mp4")


def test_only_frame_pictures_are_counted(roots, monkeypatch):
    directory = make_render(roots[0], count=3)
    (directory / "notes.txt").write_text("x")
    (directory / "frame_000009.txt").write_text("x")
    monkeypatch.setattr(video.subprocess, "run", FakeFfmpeg())
    assert run(roots).frame_count == 3


def test_a_non_integer_frame_rate_gives_a_duration_of_count_over_rate(roots, monkeypatch):
    make_render(roots[0], count=49, frame_rate=24.5)
    monkeypatch.setattr(video.subprocess, "run", FakeFfmpeg())
    result = run(roots)
    assert result.frame_rate == 24.5 and result.duration_seconds == pytest.approx(2.0)


def test_the_timeout_is_handed_to_the_runner(roots, monkeypatch):
    make_render(roots[0])
    fake = FakeFfmpeg()
    monkeypatch.setattr(video.subprocess, "run", fake)
    run(roots, timeout=12)
    assert fake.kwargs["timeout"] == 12


def test_making_it_again_replaces_the_video(roots, monkeypatch):
    make_render(roots[0])
    monkeypatch.setattr(video.subprocess, "run", FakeFfmpeg(data=b"first"))
    run(roots)
    monkeypatch.setattr(video.subprocess, "run", FakeFfmpeg(data=b"second"))
    run(roots)
    assert [p.name for p in (roots[1] / JOB).iterdir()] == ["video.mp4"]
    assert (roots[1] / JOB / "video.mp4").read_bytes() == b"second"


def test_two_renders_do_not_touch_each_other(roots, monkeypatch):
    other = "f" * 32
    make_render(roots[0])
    make_render(roots[0], job=other)
    monkeypatch.setattr(video.subprocess, "run", FakeFfmpeg(data=b"a"))
    run(roots)
    monkeypatch.setattr(video.subprocess, "run", FakeFfmpeg(data=b"b"))
    create_video(other, frames_root=roots[0], output_root=roots[1], ffmpeg=FFMPEG)
    assert (roots[1] / JOB / "video.mp4").read_bytes() == b"a"
    assert (roots[1] / other / "video.mp4").read_bytes() == b"b"


# --- failures ------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("what", ["no directory", "no record", "no frames", "bad record", "zero rate"])
def test_missing_frames_are_a_404_and_nothing_is_created(roots, monkeypatch, what):
    fake = FakeFfmpeg()
    monkeypatch.setattr(video.subprocess, "run", fake)
    if what == "no record":
        make_render(roots[0], record=False)
    elif what == "no frames":
        make_render(roots[0], count=0)
    elif what == "bad record":
        (make_render(roots[0]) / "render.json").write_text("not json")
    elif what == "zero rate":
        make_render(roots[0], frame_rate=0)
    with pytest.raises(VideoError) as caught:
        run(roots)
    assert caught.value.status == 404 and str(caught.value) == FRAMES_GONE
    assert not (roots[1] / JOB).exists() and fake.commands == []


def test_a_missing_ffmpeg_is_a_503_and_nothing_is_created(roots, monkeypatch):
    make_render(roots[0])
    monkeypatch.setattr(video.shutil, "which", lambda name: None)
    with pytest.raises(VideoError) as caught:
        run(roots)
    assert caught.value.status == 503 and str(caught.value) == NOT_FOUND
    assert not (roots[1] / JOB).exists()


def test_an_ffmpeg_that_cannot_be_started_is_a_503_and_nothing_is_left(roots, monkeypatch):
    make_render(roots[0])
    monkeypatch.setattr(video.subprocess, "run", FakeFfmpeg(error=FileNotFoundError()))
    with pytest.raises(VideoError) as caught:
        run(roots)
    assert caught.value.status == 503 and not (roots[1] / JOB).exists()


def test_an_ffmpeg_error_is_a_500_that_is_logged_and_leaves_nothing(roots, monkeypatch, caplog):
    make_render(roots[0])
    monkeypatch.setattr(video.subprocess, "run", FakeFfmpeg(returncode=1, data=b"half"))
    with caplog.at_level(logging.ERROR, logger="app.services.video"), pytest.raises(VideoError) as caught:
        run(roots)
    assert caught.value.status == 500 and str(caught.value) == "Something went wrong while making the video."
    assert "boom: something failed" in caplog.text
    assert not (roots[1] / JOB).exists()


def test_a_success_code_without_a_file_is_still_an_error(roots, monkeypatch):
    make_render(roots[0])
    monkeypatch.setattr(video.subprocess, "run", FakeFfmpeg(write=False))
    with pytest.raises(VideoError) as caught:
        run(roots)
    assert caught.value.status == 500 and not (roots[1] / JOB).exists()


def test_a_timeout_is_a_504_and_leaves_nothing(roots, monkeypatch):
    make_render(roots[0])
    monkeypatch.setattr(video.subprocess, "run", FakeFfmpeg(error=subprocess.TimeoutExpired("ffmpeg", 1)))
    with pytest.raises(VideoError) as caught:
        run(roots)
    assert caught.value.status == 504 and str(caught.value) == TOO_LONG
    assert not (roots[1] / JOB).exists()


def test_a_failure_keeps_the_video_that_was_there(roots, monkeypatch):
    make_render(roots[0])
    monkeypatch.setattr(video.subprocess, "run", FakeFfmpeg(data=b"good"))
    run(roots)
    monkeypatch.setattr(video.subprocess, "run", FakeFfmpeg(returncode=1, data=b"half"))
    with pytest.raises(VideoError):
        run(roots)
    assert [p.name for p in (roots[1] / JOB).iterdir()] == ["video.mp4"]
    assert (roots[1] / JOB / "video.mp4").read_bytes() == b"good"


# --- one at a time -------------------------------------------------------------------------------------------------------------


def test_a_second_request_while_one_runs_is_a_409_and_the_job_is_free_afterwards(roots, monkeypatch):
    make_render(roots[0])
    seen = {}

    def second_while_first_runs(command, **kwargs):
        with pytest.raises(VideoError) as caught:
            run(roots)
        seen["status"], seen["message"] = caught.value.status, str(caught.value)
        Path(command[-1]).write_bytes(b"x")
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(video.subprocess, "run", second_while_first_runs)
    run(roots)
    assert seen == {"status": 409, "message": IN_PROGRESS}
    assert video._working == set()


@pytest.mark.parametrize("error", [subprocess.TimeoutExpired("ffmpeg", 1), FileNotFoundError(), RuntimeError("odd")])
def test_the_job_is_free_again_after_every_kind_of_failure(roots, monkeypatch, error):
    make_render(roots[0])
    monkeypatch.setattr(video.subprocess, "run", FakeFfmpeg(error=error))
    with pytest.raises(Exception):
        run(roots)
    assert video._working == set()
    assert not (roots[1] / JOB).exists()
