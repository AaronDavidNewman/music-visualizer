import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings
from ..services.video import VIDEO_FILE, VideoError, create_video

router = APIRouter(prefix="/jobs", tags=["video"])

_JOB_ID = re.compile(r"^[0-9a-f]{32}$")


def _check_id(job_id: str) -> None:
    if not _JOB_ID.fullmatch(job_id):
        raise HTTPException(status_code=404, detail="Render not found.")


@router.post("/{job_id}/video")
def make_video(job_id: str) -> dict:
    """Join the frames of the render into a silent MP4 in the output directory (a plain ``def``: ffmpeg runs in a worker thread)."""
    _check_id(job_id)
    try:
        video = create_video(
            job_id,
            frames_root=settings.frames_temp_dir,
            output_root=settings.output_dir,
            ffmpeg=settings.ffmpeg_path,
            timeout=settings.video_timeout_seconds,
        )
    except VideoError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    return {
        "job_id": job_id,
        "file_name": VIDEO_FILE,
        "path": str(video.path),
        "size_bytes": video.size_bytes,
        "frame_count": video.frame_count,
        "frame_rate": video.frame_rate,
        "duration_seconds": video.duration_seconds,
        "url": f"/api/jobs/{job_id}/video",
    }


@router.get("/{job_id}/video")
def get_video(job_id: str) -> FileResponse:
    _check_id(job_id)
    path = settings.output_dir / job_id / VIDEO_FILE
    if not path.is_file():
        raise HTTPException(status_code=404, detail="No video has been made for this render.")
    return FileResponse(path, media_type="video/mp4", filename=VIDEO_FILE)
