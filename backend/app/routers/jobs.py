import logging
import math
import re
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from ..config import settings
from ..services.frame_rendering import (
    DEFAULT_BRIGHTNESS,
    DEFAULT_ENERGY,
    DEFAULT_SMOOTHING,
    MAX_BRIGHTNESS,
    MAX_ENERGY,
    MAX_SMOOTHING,
    MIN_BRIGHTNESS,
    MIN_ENERGY,
    MIN_SMOOTHING,
    average_frames,
    frame_count,
    write_frames,
)
from ..services.color_levels import HUE_STEPS, UNIT_STEPS
from ..services.energy import frame_energies
from ..services.note_analysis import AudioAnalysisError, analyze_channels, read_wav, window_count
from ..services.window_spacing import default_spacing, resolve_step

router = APIRouter(prefix="/jobs", tags=["jobs"])
log = logging.getLogger(__name__)

_JOB_ID = re.compile(r"^[0-9a-f]{32}$")
_FRAME_CACHE = "public, max-age=31536000, immutable"
_COPY_CHUNK = 1024 * 1024


def _allowed_window_sizes() -> list[int]:
    sizes, size = [], 1
    while size <= settings.max_window_size:
        if size >= settings.min_window_size:
            sizes.append(size)
        size *= 2
    return sizes


def _parse_window_size(text: str | None) -> int:
    allowed = _allowed_window_sizes()
    message = f"The window size must be a power of 2 from {allowed[0]} to {allowed[-1]} ({', '.join(map(str, allowed))})."
    try:
        value = float(text)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=message) from None
    if not value.is_integer() or int(value) not in allowed:
        raise HTTPException(status_code=400, detail=message)
    return int(value)


def _parse_frame_rate(text: str | None) -> float:
    message = f"The frame rate must be a number from {settings.min_frame_rate:g} to {settings.max_frame_rate:g}."
    try:
        value = float(text)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=message) from None
    if not settings.min_frame_rate <= value <= settings.max_frame_rate:  # also false for NaN
        raise HTTPException(status_code=400, detail=message)
    return int(value) if value.is_integer() else value


def _parse_window_spacing(text: str | None) -> float | None:
    """The requested spacing, or None when the field is missing or empty."""
    if text is None or not text.strip():
        return None
    message = "The window spacing must be a number greater than 0."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not math.isfinite(value) or value <= 0:
        raise HTTPException(status_code=400, detail=message)
    return value


async def _sent_fields(request: Request) -> set[str]:
    """Names of the form fields the client actually sent.

    FastAPI reports an empty form value as missing, which would make ``brightness=`` silently use the
    default. This tells "not sent" apart from "sent empty", so an empty brightness can be refused.
    """
    return set((await request.form()).keys())


def _parse_brightness(text: str | None, sent: bool) -> int:
    """The requested brightness. Not sent means the default; anything sent must be a whole number 2..100."""
    if text is None and not sent:
        return DEFAULT_BRIGHTNESS
    text = text or ""
    message = f"The brightness must be a whole number from {MIN_BRIGHTNESS} to {MAX_BRIGHTNESS}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not value.is_integer() or not MIN_BRIGHTNESS <= value <= MAX_BRIGHTNESS:
        raise HTTPException(status_code=400, detail=message)
    return int(value)


def _parse_energy(text: str | None, sent: bool) -> int:
    """The requested energy root. Not sent means the default; anything sent must be a whole number 1..8."""
    if text is None and not sent:
        return DEFAULT_ENERGY
    text = text or ""
    message = f"The energy must be a whole number from {MIN_ENERGY} to {MAX_ENERGY}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not math.isfinite(value) or not value.is_integer() or not MIN_ENERGY <= value <= MAX_ENERGY:
        raise HTTPException(status_code=400, detail=message)
    return int(value)


def _parse_step(text: str | None, sent: bool, allowed: tuple[int, ...], label: str) -> int | None:
    """The requested colour step. Not sent or ``N/A`` (any case) means no rounding (None); otherwise one of ``allowed``."""
    if text is None and not sent:
        return None
    text = (text or "").strip()
    if text.lower() == "n/a":
        return None
    message = f"The {label} step must be N/A or one of {', '.join(map(str, allowed))}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not math.isfinite(value) or not value.is_integer() or int(value) not in allowed:
        raise HTTPException(status_code=400, detail=message)
    return int(value)


def _parse_smoothing(text: str | None, sent: bool) -> float:
    """The requested smoothing. Not sent means the default; anything sent must be a number 0.0..0.8."""
    if text is None and not sent:
        return DEFAULT_SMOOTHING
    text = text or ""
    message = f"The smoothing must be a number from {MIN_SMOOTHING} to {MAX_SMOOTHING}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not math.isfinite(value) or not MIN_SMOOTHING <= value <= MAX_SMOOTHING:
        raise HTTPException(status_code=400, detail=message)
    return value + 0.0  # turns -0.0 into 0.0


def _format_bytes(n: int) -> str:
    return f"{n // (1024 * 1024)} MB" if n >= 1024 * 1024 else f"{n} bytes"


def _save_upload(upload: UploadFile, path: Path) -> None:
    """Stream the upload to ``path``, refusing anything over the size limit."""
    written = 0
    with path.open("wb") as out:
        while chunk := upload.file.read(_COPY_CHUNK):
            written += len(chunk)
            if written > settings.max_audio_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"The file is larger than the {_format_bytes(settings.max_audio_bytes)} limit.",
                )
            out.write(chunk)


def _remove_job(job_id: str) -> None:
    for root in (settings.audio_temp_dir, settings.frames_temp_dir):
        shutil.rmtree(root / job_id, ignore_errors=True)


@router.post("")
def create_job(
    file: UploadFile | None = File(None),
    window_size: str | None = Form(None),
    frame_rate: str | None = Form(None),
    window_spacing: str | None = Form(None),
    brightness: str | None = Form(None),
    smoothing: str | None = Form(None),
    energy: str | None = Form(None),
    hue_step: str | None = Form(None),
    saturation_step: str | None = Form(None),
    brightness_step: str | None = Form(None),
    sent: set[str] = Depends(_sent_fields),
) -> dict:
    window = _parse_window_size(window_size)
    fps = _parse_frame_rate(frame_rate)
    requested_spacing = _parse_window_spacing(window_spacing)
    brightness_root = _parse_brightness(brightness, "brightness" in sent)
    smoothing_value = _parse_smoothing(smoothing, "smoothing" in sent)
    energy_root = _parse_energy(energy, "energy" in sent)
    hue_levels = _parse_step(hue_step, "hue_step" in sent, HUE_STEPS, "hue")
    saturation_levels = _parse_step(saturation_step, "saturation_step" in sent, UNIT_STEPS, "saturation")
    brightness_levels = _parse_step(brightness_step, "brightness_step" in sent, UNIT_STEPS, "brightness")
    if file is None:
        raise HTTPException(status_code=400, detail="No file was uploaded. Choose a .wav file.")

    file_name = Path((file.filename or "audio.wav").replace("\\", "/")).name  # for display only, never a path
    job_id = uuid.uuid4().hex
    audio_path = settings.audio_temp_dir / job_id / "audio.wav"
    frames_dir = settings.frames_temp_dir / job_id
    try:
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        _save_upload(file, audio_path)

        file_rate, left, right = read_wav(audio_path, display_name=file_name)
        samples = left.shape[0]
        if samples == 0:
            raise HTTPException(status_code=400, detail="The file contains no audio.")
        frames = frame_count(samples, file_rate, fps)
        if frames > settings.max_frames:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"This would create {frames:,} frames; the limit is {settings.max_frames:,}. "
                    "Lower the frame rate or use a shorter file."
                ),
            )

        if requested_spacing is None:  # not given: the default that gives each frame its own window
            requested_spacing = default_spacing(file_rate, fps, window)
        spacing, step, raised = resolve_step(requested_spacing, window)
        windows = window_count(samples, step)
        if windows > settings.max_windows:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"This would create {windows:,} windows; the limit is {settings.max_windows:,}. "
                    "Use a larger window spacing."
                ),
            )
        result = analyze_channels(left, right, file_rate, window, step=step)
        energies = frame_energies(left, right, file_rate, fps, frames)
        # write_frames smooths the note values, each tile's hue and each frame's brightness (from its energy),
        # all with the same smoothing, and only then rounds hue, saturation and brightness to the chosen levels
        write_frames(
            average_frames(result, fps, frames),
            frames_dir,
            brightness=brightness_root,
            smoothing=smoothing_value,
            energies=energies,
            energy_root=energy_root,
            hue_step=hue_levels,
            saturation_step=saturation_levels,
            value_step=brightness_levels,
        )
    except HTTPException:
        _remove_job(job_id)
        raise
    except AudioAnalysisError as exc:
        _remove_job(job_id)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        _remove_job(job_id)
        log.exception("Creating frames failed for upload %r", file.filename)
        raise HTTPException(status_code=500, detail="Something went wrong while creating the frames.") from None

    return {
        "job_id": job_id,
        "file_name": file_name,
        "sample_rate": file_rate,
        "duration_seconds": samples / file_rate,
        "window_size": window,
        "frame_rate": fps,
        "frame_count": frames,
        "brightness": brightness_root,
        "smoothing": smoothing_value,
        "energy": energy_root,
        "hue_step": hue_levels,
        "saturation_step": saturation_levels,
        "brightness_step": brightness_levels,
        "window_spacing": spacing,
        "step_samples": step,
        "window_count": result.window_count,
        "spacing_raised": raised,
        "frame_url_template": f"/api/jobs/{job_id}/frames/{{index}}",
    }


@router.get("/{job_id}/frames/{index}")
def get_frame(job_id: str, index: str) -> FileResponse:
    if not _JOB_ID.fullmatch(job_id) or not index.isascii() or not index.isdigit():
        raise HTTPException(status_code=404, detail="Frame not found.")
    path = settings.frames_temp_dir / job_id / f"frame_{int(index):06d}.png"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Frame not found.")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": _FRAME_CACHE})
