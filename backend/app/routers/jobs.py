import logging
import math
import re
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from ..config import settings
from ..services.colormaps import COLORMAPS, DEFAULT_COLORMAP
from ..services.frame_rendering import (
    DEFAULT_SMOOTHING,
    DEFAULT_SMOOTHING_WINDOW,
    DEFAULT_THRESHOLD,
    MAX_SMOOTHING,
    MAX_SMOOTHING_WINDOW,
    MAX_THRESHOLD,
    MIN_SMOOTHING,
    MIN_SMOOTHING_WINDOW,
    MIN_THRESHOLD,
    average_frames,
    frame_count,
    write_frames,
)
from ..services.circles import (
    DEFAULT_CIRCLE_MEMORY,
    DEFAULT_CIRCLE_NOTES,
    DEFAULT_CIRCLE_RESIZE,
    DEFAULT_CIRCLE_RADIUS,
    DEFAULT_CIRCLE_UNIT,
    MAX_CIRCLE_MEMORY,
    MAX_CIRCLE_NOTES,
    MAX_CIRCLE_RADIUS,
    MAX_CIRCLE_UNIT,
    MIN_CIRCLE_MEMORY,
    MIN_CIRCLE_NOTES,
    MIN_CIRCLE_RADIUS,
    MIN_CIRCLE_UNIT,
)
from ..services.frame_interpolation import DEFAULT_INTERPOLATE, MAX_INTERPOLATE, MIN_INTERPOLATE
from ..services.gaussian import DEFAULT_GAUSSIAN, MAX_GAUSSIAN, MIN_GAUSSIAN
from ..services.local_peaks import (
    DEFAULT_MIN_DISTANCE,
    DEFAULT_PROMINENCE,
    check_min_distance,
    check_prominence,
    measure_local_peaks,
)
from ..services.image_types import (
    DEFAULT_BLEND_WIDTH,
    DEFAULT_IMAGE_TYPE,
    IMAGE_TYPES,
    MAX_BLEND_WIDTH,
    MIN_BLEND_WIDTH,
)
from ..services.note_analysis import AudioAnalysisError, analyze_channels, read_wav, window_count
from ..services.note_selection import DEFAULT_NOTE_COUNT, MAX_NOTE_COUNT, MIN_NOTE_COUNT
from ..services.resolution import DEFAULT_RESOLUTION, MAX_RESOLUTION, MIN_RESOLUTION
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

    FastAPI reports an empty form value as missing, which would make ``smoothing=`` silently use the
    default. This tells "not sent" apart from "sent empty", so an empty smoothing can be refused.
    """
    return set((await request.form()).keys())


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


def _parse_gaussian(text: str | None, sent: bool) -> float:
    """The requested gaussian smoothing. Not sent means the default (off); anything sent must be a number 0..5."""
    if text is None and not sent:
        return DEFAULT_GAUSSIAN
    text = text or ""
    message = f"The gaussian smoothing must be a number from {MIN_GAUSSIAN:g} to {MAX_GAUSSIAN:g}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not math.isfinite(value) or not MIN_GAUSSIAN <= value <= MAX_GAUSSIAN:
        raise HTTPException(status_code=400, detail=message)
    return value + 0.0  # turns -0.0 into 0.0


def _parse_beat_coloring(text: str | None, sent: bool) -> bool:
    """Whether the tiles are colored half by the beat. Not sent means off; anything sent must be true, false, 1 or 0 (any case)."""
    if text is None and not sent:
        return False
    word = (text or "").strip().lower()
    if word in ("true", "1"):
        return True
    if word in ("false", "0"):
        return False
    raise HTTPException(status_code=400, detail="The beat coloring must be true or false.")


def _parse_peak_setting(text: str | None, sent: bool, default: float, check) -> float:
    """A setting of the local peaks measurement. Not sent means the default; anything sent must pass the measurement's own check."""
    if text is None and not sent:
        return default
    try:
        value = float(text or "")
    except ValueError:
        value = float("nan")  # not a number: the check refuses it with its own message
    try:
        return check(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


def _parse_colormap(text: str | None, sent: bool) -> str:
    """The requested colormap. Not sent means the default; anything sent must be exactly one of the offered names."""
    if text is None and not sent:
        return DEFAULT_COLORMAP
    if text not in COLORMAPS:
        raise HTTPException(status_code=400, detail=f"The colormap must be one of {', '.join(COLORMAPS)}.")
    return text


def _parse_image_type(text: str | None, sent: bool) -> str:
    """The requested image type. Not sent means the default; anything sent must be exactly one of the offered names."""
    if text is None and not sent:
        return DEFAULT_IMAGE_TYPE
    if text not in IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"The image type must be one of {', '.join(IMAGE_TYPES)}.")
    return text


def _parse_blend_width(text: str | None, sent: bool) -> int | float:
    """The requested blend width. Not sent means the default; anything sent must be a number 10..25 (percent)."""
    if text is None and not sent:
        return DEFAULT_BLEND_WIDTH
    text = text or ""
    message = f"The blend width must be a number from {MIN_BLEND_WIDTH} to {MAX_BLEND_WIDTH}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not math.isfinite(value) or not MIN_BLEND_WIDTH <= value <= MAX_BLEND_WIDTH:
        raise HTTPException(status_code=400, detail=message)
    return int(value) if value.is_integer() else value


def _parse_circle_unit(text: str | None, sent: bool) -> int:
    """The requested circle unit in pixels. Not sent means the default; anything sent must be a whole number 1..10."""
    if text is None and not sent:
        return DEFAULT_CIRCLE_UNIT
    text = text or ""
    message = f"The circle movement must be a whole number from {MIN_CIRCLE_UNIT} to {MAX_CIRCLE_UNIT}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not math.isfinite(value) or not value.is_integer() or not MIN_CIRCLE_UNIT <= value <= MAX_CIRCLE_UNIT:
        raise HTTPException(status_code=400, detail=message)
    return int(value)


def _parse_circle_memory(text: str | None, sent: bool) -> int:
    """The requested circle memory. Not sent means the default; anything sent must be a whole number 100..500."""
    if text is None and not sent:
        return DEFAULT_CIRCLE_MEMORY
    text = text or ""
    message = f"The circle memory must be a whole number from {MIN_CIRCLE_MEMORY} to {MAX_CIRCLE_MEMORY}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not math.isfinite(value) or not value.is_integer() or not MIN_CIRCLE_MEMORY <= value <= MAX_CIRCLE_MEMORY:
        raise HTTPException(status_code=400, detail=message)
    return int(value)


def _parse_circle_notes(text: str | None, sent: bool) -> int:
    """The requested number of circles per frame. Not sent means the default; anything sent must be a whole number 5..12."""
    if text is None and not sent:
        return DEFAULT_CIRCLE_NOTES
    text = text or ""
    message = f"The number of circle notes must be a whole number from {MIN_CIRCLE_NOTES} to {MAX_CIRCLE_NOTES}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not math.isfinite(value) or not value.is_integer() or not MIN_CIRCLE_NOTES <= value <= MAX_CIRCLE_NOTES:
        raise HTTPException(status_code=400, detail=message)
    return int(value)


def _parse_circle_radius(text: str | None, sent: bool) -> int:
    """The requested circle radius in pixels. Not sent means the default; anything sent must be a whole number 4..8."""
    if text is None and not sent:
        return DEFAULT_CIRCLE_RADIUS
    text = text or ""
    message = f"The circle radius must be a whole number from {MIN_CIRCLE_RADIUS} to {MAX_CIRCLE_RADIUS}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not math.isfinite(value) or not value.is_integer() or not MIN_CIRCLE_RADIUS <= value <= MAX_CIRCLE_RADIUS:
        raise HTTPException(status_code=400, detail=message)
    return int(value)


def _parse_circle_resize(text: str | None, sent: bool) -> bool:
    """Whether the circles are resized by volume. Not sent means off; anything sent must be true, false, 1 or 0 (any case)."""
    if text is None and not sent:
        return DEFAULT_CIRCLE_RESIZE
    word = (text or "").strip().lower()
    if word in ("true", "1"):
        return True
    if word in ("false", "0"):
        return False
    raise HTTPException(status_code=400, detail="The circle resize must be true or false.")


def _parse_interpolate(text: str | None, sent: bool) -> int:
    """The requested interpolate value. Not sent means 1 (every frame drawn); anything sent must be a whole number 1..5."""
    if text is None and not sent:
        return DEFAULT_INTERPOLATE
    text = text or ""
    message = f"The interpolate value must be a whole number from {MIN_INTERPOLATE} to {MAX_INTERPOLATE}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not math.isfinite(value) or not value.is_integer() or not MIN_INTERPOLATE <= value <= MAX_INTERPOLATE:
        raise HTTPException(status_code=400, detail=message)
    return int(value)


def _parse_note_count(text: str | None, sent: bool) -> int:
    """The requested number of notes. Not sent means all 84; anything sent must be a whole number 12..84."""
    if text is None and not sent:
        return DEFAULT_NOTE_COUNT
    text = text or ""
    message = f"The number of notes must be a whole number from {MIN_NOTE_COUNT} to {MAX_NOTE_COUNT}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not math.isfinite(value) or not value.is_integer() or not MIN_NOTE_COUNT <= value <= MAX_NOTE_COUNT:
        raise HTTPException(status_code=400, detail=message)
    return int(value)


def _parse_resolution(text: str | None, sent: bool) -> int:
    """The requested resolution. Not sent means the default (1); anything sent must be a whole number 1..5."""
    if text is None and not sent:
        return DEFAULT_RESOLUTION
    text = text or ""
    message = f"The oversampling must be a whole number from {MIN_RESOLUTION} to {MAX_RESOLUTION}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not math.isfinite(value) or not value.is_integer() or not MIN_RESOLUTION <= value <= MAX_RESOLUTION:
        raise HTTPException(status_code=400, detail=message)
    return int(value)


def _parse_smoothing_window(text: str | None, sent: bool) -> int:
    """The requested smoothing window. Not sent means the default; anything sent must be a whole number 1..20."""
    if text is None and not sent:
        return DEFAULT_SMOOTHING_WINDOW
    text = text or ""
    message = f"The smoothing window must be a whole number from {MIN_SMOOTHING_WINDOW} to {MAX_SMOOTHING_WINDOW}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if (
        not math.isfinite(value)
        or not value.is_integer()
        or not MIN_SMOOTHING_WINDOW <= value <= MAX_SMOOTHING_WINDOW
    ):
        raise HTTPException(status_code=400, detail=message)
    return int(value)


def _parse_threshold(text: str | None, sent: bool) -> int | float:
    """The requested threshold. Not sent means off (0); anything sent must be a number 0..50 (percent)."""
    if text is None and not sent:
        return DEFAULT_THRESHOLD
    text = text or ""
    message = f"The threshold must be a number from {MIN_THRESHOLD} to {MAX_THRESHOLD}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not math.isfinite(value) or not MIN_THRESHOLD <= value <= MAX_THRESHOLD:
        raise HTTPException(status_code=400, detail=message)
    return int(value) if value.is_integer() else value


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
    smoothing: str | None = Form(None),
    threshold: str | None = Form(None),
    smoothing_window: str | None = Form(None),
    image_type: str | None = Form(None),
    blend_width: str | None = Form(None),
    colormap: str | None = Form(None),
    resolution: str | None = Form(None),
    note_count: str | None = Form(None),
    interpolate: str | None = Form(None),
    circle_unit: str | None = Form(None),
    circle_memory: str | None = Form(None),
    circle_notes: str | None = Form(None),
    circle_radius: str | None = Form(None),
    circle_resize: str | None = Form(None),
    gaussian: str | None = Form(None),
    beat_coloring: str | None = Form(None),
    peak_distance: str | None = Form(None),
    peak_prominence: str | None = Form(None),
    sent: set[str] = Depends(_sent_fields),
) -> dict:
    window = _parse_window_size(window_size)
    fps = _parse_frame_rate(frame_rate)
    requested_spacing = _parse_window_spacing(window_spacing)
    smoothing_value = _parse_smoothing(smoothing, "smoothing" in sent)
    threshold_value = _parse_threshold(threshold, "threshold" in sent)
    window_value = _parse_smoothing_window(smoothing_window, "smoothing_window" in sent)
    image_type_value = _parse_image_type(image_type, "image_type" in sent)
    blend_width_value = _parse_blend_width(blend_width, "blend_width" in sent)
    colormap_value = _parse_colormap(colormap, "colormap" in sent)
    resolution_value = _parse_resolution(resolution, "resolution" in sent)
    note_count_value = _parse_note_count(note_count, "note_count" in sent)
    interpolate_value = _parse_interpolate(interpolate, "interpolate" in sent)
    circle_unit_value = _parse_circle_unit(circle_unit, "circle_unit" in sent)
    circle_memory_value = _parse_circle_memory(circle_memory, "circle_memory" in sent)
    circle_notes_value = _parse_circle_notes(circle_notes, "circle_notes" in sent)
    circle_radius_value = _parse_circle_radius(circle_radius, "circle_radius" in sent)
    circle_resize_value = _parse_circle_resize(circle_resize, "circle_resize" in sent)
    gaussian_value = _parse_gaussian(gaussian, "gaussian" in sent)
    beat_coloring_value = _parse_beat_coloring(beat_coloring, "beat_coloring" in sent)
    peak_distance_value = _parse_peak_setting(peak_distance, "peak_distance" in sent, DEFAULT_MIN_DISTANCE, check_min_distance)
    peak_prominence_value = _parse_peak_setting(peak_prominence, "peak_prominence" in sent, DEFAULT_PROMINENCE, check_prominence)
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
        # the beat coloring (tiles and blended tiles only): the position of the middle of each frame in the local energy peak
        # of the whole file, from the local peaks measurement; the other pictures and the box off never measure it
        beat = None
        if beat_coloring_value and image_type_value in ("tiles", "blended"):
            beat = measure_local_peaks(
                left, right, file_rate, peak_distance_value, peak_prominence_value
            ).frame_positions(fps, frames)
        # write_frames smooths the note values (each frame is mixed with the earlier frames of the window), colors every
        # tile from the colormap at its own note's strength, blacks the tiles of notes below the threshold, and writes
        # the finished tile colors as the chosen image type; a resolution above 1 first interpolates the grid of smoothed
        # note values to a finer one, and a number of notes below 84 first builds the picture from the notes with the most
        # energy in the file only; an interpolate value above 1 draws only every n-th frame and makes the others from their
        # neighbors with Pillow; the image type circles draws wandering circles instead (its three settings)
        write_frames(
            average_frames(result, fps, frames),
            frames_dir,
            colormap=colormap_value,
            smoothing=smoothing_value,
            smoothing_window=window_value,
            threshold=threshold_value,
            image_type=image_type_value,
            blend_width=blend_width_value,
            resolution=resolution_value,
            note_count=note_count_value,
            interpolate=interpolate_value,
            circle_unit=circle_unit_value,
            circle_memory=circle_memory_value,
            circle_notes=circle_notes_value,
            circle_radius=circle_radius_value,
            circle_resize=circle_resize_value,
            gaussian=gaussian_value,
            beat=beat,
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
        "smoothing": smoothing_value,
        "threshold": threshold_value,
        "smoothing_window": window_value,
        "image_type": image_type_value,
        "blend_width": blend_width_value,
        "colormap": colormap_value,
        "resolution": resolution_value,
        "note_count": note_count_value,
        "interpolate": interpolate_value,
        "circle_unit": circle_unit_value,
        "circle_memory": circle_memory_value,
        "circle_notes": circle_notes_value,
        "circle_radius": circle_radius_value,
        "circle_resize": circle_resize_value,
        "gaussian": gaussian_value,
        "beat_coloring": beat_coloring_value,
        "peak_distance": peak_distance_value,
        "peak_prominence": peak_prominence_value,
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
