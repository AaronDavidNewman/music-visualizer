"""Join the frames of a render into one silent MP4 with ffmpeg (feature 029)."""

import json
import logging
import os
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

FRAME_PATTERN = "frame_%06d.png"
RENDER_FILE = "render.json"
VIDEO_FILE = "video.mp4"
TEMP_FILE = "video.tmp.mp4"

FRAMES_GONE = "The frames of this render are no longer available. Render again."
NOT_FOUND = "ffmpeg was not found. Install it, or set MV_FFMPEG_PATH to its location."
IN_PROGRESS = "A video is already being made for this render."
FAILED = "Something went wrong while making the video."
TOO_LONG = "Making the video took too long and was stopped."

# The jobs whose video is being made now; a second request for one of them is refused.
_working: set[str] = set()
_working_lock = threading.Lock()


class VideoError(Exception):
    """A failure with a message fit to show the user and the HTTP status that goes with it."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class VideoResult:
    job_id: str
    path: Path
    size_bytes: int
    frame_count: int
    frame_rate: float
    duration_seconds: float


def build_command(ffmpeg: str, frames_dir: Path, frame_rate: float, output_file: Path) -> list[str]:
    """The ffmpeg command: only the frames go in (no audio), H.264 in yuv420p comes out, the size padded up to even numbers."""
    return [
        ffmpeg,
        "-y",
        "-framerate",
        f"{frame_rate:g}",
        "-start_number",
        "0",
        "-i",
        str(frames_dir / FRAME_PATTERN),
        "-an",
        "-vf",
        "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_file),
    ]


def _read_render(frames_dir: Path) -> tuple[int, float]:
    """The frame count and the frame rate of a render, or a 404 when its frames (or its record) are gone."""
    try:
        frame_rate = float(json.loads((frames_dir / RENDER_FILE).read_text(encoding="utf-8"))["frame_rate"])
    except (OSError, ValueError, KeyError, TypeError):
        raise VideoError(404, FRAMES_GONE) from None
    count = sum(1 for _ in frames_dir.glob("frame_*.png"))
    if count == 0 or not frame_rate > 0:
        raise VideoError(404, FRAMES_GONE)
    return count, frame_rate


def create_video(
    job_id: str,
    *,
    frames_root: Path,
    output_root: Path,
    ffmpeg: str = "ffmpeg",
    timeout: float | None = None,
) -> VideoResult:
    """Make ``output_root/<job_id>/video.mp4`` from the frames of the render, replacing an earlier one.

    Nothing is left behind on a failure: ffmpeg writes a temporary file that is moved over the video only when it succeeded,
    and a directory made by this attempt is removed again. A video that already existed is kept.
    """
    with _working_lock:
        if job_id in _working:
            raise VideoError(409, IN_PROGRESS)
        _working.add(job_id)
    try:
        return _create(job_id, frames_root, output_root, ffmpeg, timeout)
    finally:
        with _working_lock:
            _working.discard(job_id)


def _create(job_id: str, frames_root: Path, output_root: Path, ffmpeg: str, timeout: float | None) -> VideoResult:
    frames_dir = frames_root / job_id
    count, frame_rate = _read_render(frames_dir)

    program = shutil.which(ffmpeg)
    if program is None:
        raise VideoError(503, NOT_FOUND)

    out_dir = output_root / job_id
    made_dir = not out_dir.exists()
    out_dir.mkdir(parents=True, exist_ok=True)
    temp = out_dir / TEMP_FILE
    final = out_dir / VIDEO_FILE
    try:
        try:
            done = subprocess.run(build_command(program, frames_dir, frame_rate, temp), capture_output=True, timeout=timeout)
        except FileNotFoundError:
            raise VideoError(503, NOT_FOUND) from None
        except subprocess.TimeoutExpired:
            raise VideoError(504, TOO_LONG) from None
        if done.returncode != 0 or not temp.is_file():
            log.error("ffmpeg failed for job %s (exit %s): %s", job_id, done.returncode, done.stderr.decode("utf-8", "replace")[-2000:])
            raise VideoError(500, FAILED)
        os.replace(temp, final)
    except BaseException:
        temp.unlink(missing_ok=True)
        if made_dir:
            try:
                out_dir.rmdir()
            except OSError:
                pass
        raise

    return VideoResult(job_id, final, final.stat().st_size, count, frame_rate, count / frame_rate)
