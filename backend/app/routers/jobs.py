"""The job endpoints: ``POST /api/jobs`` turns an uploaded WAV file into the frames of an animation,
``GET /api/jobs/{job_id}/frames/{index}`` serves one frame, ``GET /api/jobs/{job_id}/obj`` serves the ZIP of the 3D files
of a job that was made with the 3D export (feature 045).

These are the steps of ``create_job()``, the shared steps READ to SAVE of the pipeline overview in
``services/image_types.py``.

Order of operations:
    1. Read and check every setting of the form - ``create_job()`` with the ``_parse_*`` functions (``_parse_extra_notes()``
       checks the Extra notes k against the number of notes of the picture; ``_parse_spirograph_settings()`` the three settings
       of Spirograph) - a setting that is
       not sent takes its default and one that is wrong is refused (400) before the file is read.
    2. Save the upload - ``_save_upload()`` - into the audio folder, refused above the size limit.
    3. Read the file - ``note_analysis.read_wav()`` - two ``RawSamples`` ``(samples,)``; a file with no audio is
       refused.
    4. Count the frames and the windows - ``frame_rendering.frame_count()``, ``buffer_interval.buffer_step()`` (the fixed
       60 ms step between the frequency buffers, whatever the frame rate) and ``note_analysis.window_count()`` - refused
       above ``max_frames`` and ``max_windows``.
    5. Analyze and apply the noise floor - ``note_analysis.analyze_channels()`` then ``noise_floor.floor_analysis()`` -
       ``NoteStrengths`` ``(windows, 88)``.
    6. Measure, only for the image types that use it (Spirograph, feature 046, uses the beat only: the turns and the
       radius of its curves follow the place in the local energy peak) - ``local_peaks.measure_local_peaks()`` with ``frame_positions()``
       (the beat: ``BeatPositions`` ``(frames,)``), for Polychord also ``polychord.frame_tempos()`` (``FrameTempos``
       ``(frames,)``, from the same measurement). Rhythm Circles (feature 047) calls
       ``rhythm_circles.rhythm_angles()`` (``CircleAngles`` ``(frames, 6)``) with the local peaks, the 60 ms windows of step 5 and the two channels of step 2 (the starts of the
       notes are found in the windows and placed on the waveform, not found in the frames, so they do not depend on the frame rate) and the Vote limit; Extra notes plays no part.
    7. Average the windows into frames and draw them - ``frame_rendering.average_frames()`` then ``frame_rendering.write_frames()`` (for Energy Graphs ``energy_graphs.frame_energy()`` is made in the same call,
       after the averaging) - one PNG for each frame in the frames folder of the job, and with ``export_obj`` (Contour and
       Chromatic Wireframe only) one OBJ file for each frame in its ``obj`` folder.
    8. Record the frame rate - ``render.json`` in the same folder - for the video that is made later.
    9. On any failure remove everything the job made (``_remove_job()``) and answer with the message; on success answer
       with the settings used and the address of the frames (and of the 3D files, when they were made).
    10. (Later, ``get_obj()``) pack the OBJ files of a job into one ZIP - ``obj_export.zip_obj_files()`` - in the output
       folder, on the first request.
"""

import json
import logging
import math
import re
import shutil
import uuid
from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from ..config import settings
from ..services.buffer_interval import buffer_step
from ..services.colormaps import COLORMAPS, DEFAULT_COLORMAP
from ..services.obj_export import NOT_AVAILABLE_MESSAGE, OBJ_EXPORT_TYPES, OBJ_FOLDER, zip_obj_files
from ..services.held_notes import DEFAULT_EXTRA_NOTES, MAX_EXTRA_NOTES, check_extra_notes, notes_of
from ..services.frame_rendering import (
    DEFAULT_THRESHOLD,
    MAX_THRESHOLD,
    MIN_THRESHOLD,
    average_frames,
    frame_count,
    write_frames,
)
from ..services.frame_interpolation import DEFAULT_INTERPOLATE, MAX_INTERPOLATE, MIN_INTERPOLATE
from ..services.gaussian import DEFAULT_GAUSSIAN, MAX_GAUSSIAN, MIN_GAUSSIAN
from ..services.beat_wave import DEFAULT_WAVE_COUNT, MAX_WAVE_COUNT, MIN_WAVE_COUNT
from ..services.chromatic_decay import CHROMATIC_TYPES, DEFAULT_RATE as DEFAULT_CHROMATIC_RATE, RATE_MESSAGE as CHROMATIC_RATE_MESSAGE, check_chromatic_rate
from ..services.decay import (
    DEFAULT_DECAY_AMOUNTS,
    DECAY_RATE_MESSAGE,
    DEFAULT_DECAY_RATE,
    check_decay_rate,
    LEVELS,
    MAX_DECAY_AMOUNT,
    MIN_DECAY_AMOUNT,
)
from ..services.note_layout import DEFAULT_NOTE_LAYOUT, check_note_layout
from ..services.polar_chords import DEFAULT_POLAR_NOTES, NOTES_MESSAGE as POLAR_NOTES_MESSAGE, check_polar_notes
from ..services.polychord import (
    DEFAULT_MAX_COPIES,
    DEFAULT_MIN_COPIES,
    DEFAULT_NOTES as DEFAULT_POLYCHORD_NOTES,
    DEFAULT_ROTATION,
    MAX_COPIES_MESSAGE,
    MIN_COPIES_MESSAGE,
    NOTES_MESSAGE as POLYCHORD_NOTES_MESSAGE,
    ROTATION_MESSAGE,
    PolychordData,
    PolychordSettings,
    check_polychord_copies,
    check_polychord_notes,
    check_polychord_rotation,
    check_polychord_settings,
    frame_tempos,
)
from ..services.local_peaks import (
    DEFAULT_MIN_DISTANCE,
    DEFAULT_PROMINENCE,
    check_min_distance,
    measure_local_peaks,
)
from ..services.energy_graphs import frame_energy
from ..services.rhythm_circles import rhythm_angles
from ..services.tempo_votes import DEFAULT_VOTE_LIMIT, VOTE_LIMIT_MESSAGE, check_vote_limit
from ..services.spirograph import (
    DEFAULT_FADE as DEFAULT_SPIROGRAPH_FADE,
    DEFAULT_HISTORY as DEFAULT_SPIROGRAPH_HISTORY,
    DEFAULT_NOTES as DEFAULT_SPIROGRAPH_NOTES,
    FADE_MESSAGE as SPIROGRAPH_FADE_MESSAGE,
    HISTORY_MESSAGE as SPIROGRAPH_HISTORY_MESSAGE,
    NOTES_MESSAGE as SPIROGRAPH_NOTES_MESSAGE,
    SpirographSettings,
    check_spirograph_fade,
    check_spirograph_history,
    check_spirograph_notes,
)
from ..services.image_types import DEFAULT_IMAGE_TYPE, IMAGE_TYPES
from ..services.noise_floor import floor_analysis
from ..services.note_analysis import AudioAnalysisError, analyze_channels, read_wav, window_count
from ..services.note_selection import DEFAULT_NOTE_COUNT, MAX_NOTE_COUNT, MIN_NOTE_COUNT
from ..services.resolution import DEFAULT_RESOLUTION, MAX_RESOLUTION, MIN_RESOLUTION

router = APIRouter(prefix="/jobs", tags=["jobs"])
log = logging.getLogger(__name__)

_JOB_ID = re.compile(r"^[0-9a-f]{32}$")
_FRAME_CACHE = "public, max-age=31536000, immutable"
OBJ_ARCHIVE = "obj.zip"  # the name of the ZIP of the 3D files, in the output folder of the job and as downloaded
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


async def _sent_fields(request: Request) -> set[str]:
    """Names of the form fields the client actually sent.

    FastAPI reports an empty form value as missing, which would make ``gaussian=`` silently use the
    default. This tells "not sent" apart from "sent empty", so an empty gaussian smoothing can be refused.
    """
    return set((await request.form()).keys())


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
    """Whether the contour's beat wave is on. Not sent means off; anything sent must be true, false, 1 or 0 (any case).
    """
    if text is None and not sent:
        return False
    word = (text or "").strip().lower()
    if word in ("true", "1"):
        return True
    if word in ("false", "0"):
        return False
    raise HTTPException(status_code=400, detail="The beat coloring must be true or false.")


def _parse_export_obj(text: str | None, sent: bool, image_type: str) -> bool:
    """Whether the 3D export is on (feature 045). Not sent means off; anything sent must be true, false, 1 or 0 (any case); on is
    refused for every picture but Contour and Chromatic Wireframe."""
    if text is None and not sent:
        return False
    word = (text or "").strip().lower()
    if word in ("true", "1"):
        if image_type not in OBJ_EXPORT_TYPES:
            raise HTTPException(status_code=400, detail=NOT_AVAILABLE_MESSAGE)
        return True
    if word in ("false", "0"):
        return False
    raise HTTPException(status_code=400, detail="The 3D export must be true or false.")


def _parse_peak_setting(text: str | None, sent: bool, default: float, check: Callable[[object], float]) -> float:
    """A setting of the local peaks measurement. Not sent means the default; anything sent must pass the measurement's
    own check."""
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


def _parse_note_layout(text: str | None, sent: bool) -> str:
    """The requested note layout. Not sent means rows; anything sent must be exactly ``rows`` or ``spiral``."""
    if text is None and not sent:
        return DEFAULT_NOTE_LAYOUT
    try:
        return check_note_layout(text or "")
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


def _parse_decay_rate(text: str | None, sent: bool, image_type: str = DEFAULT_IMAGE_TYPE) -> float | int:
    """The requested number of frames between decay steps. Not sent means the default; anything sent must be a number
    0.25..4 in steps of 0.25, or, for Chromatic Decay (feature 035) and Chromatic Wireframe (feature 039), a whole
    number from 1 to 10."""
    chromatic = image_type in CHROMATIC_TYPES
    if text is None and not sent:
        return DEFAULT_CHROMATIC_RATE if chromatic else DEFAULT_DECAY_RATE
    text = text or ""
    try:
        return check_chromatic_rate(float(text)) if chromatic else check_decay_rate(float(text))
    except ValueError:  # not a number, or not one of the allowed values
        raise HTTPException(status_code=400, detail=CHROMATIC_RATE_MESSAGE if chromatic else DECAY_RATE_MESSAGE) from None


def _parse_decay_amount(text: str | None, sent: bool, index: int) -> float:
    """The requested decay amount of one saturation level (``LEVELS[index]``). Not sent means the default; anything sent
    must be a number 0.5..3."""
    if text is None and not sent:
        return DEFAULT_DECAY_AMOUNTS[index]
    text = text or ""
    message = f"The {LEVELS[index]} saturation decay must be a number from {MIN_DECAY_AMOUNT:g} to {MAX_DECAY_AMOUNT:g}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not math.isfinite(value) or not MIN_DECAY_AMOUNT <= value <= MAX_DECAY_AMOUNT:
        raise HTTPException(status_code=400, detail=message)
    return value


def _parse_polar_notes(text: str | None, sent: bool) -> int:
    """The requested number of notes shown by Polar Chords. Not sent means the default; anything sent must be a whole
    number 5..8."""
    if text is None and not sent:
        return DEFAULT_POLAR_NOTES
    try:
        return check_polar_notes(float(text or ""))
    except ValueError:
        raise HTTPException(status_code=400, detail=POLAR_NOTES_MESSAGE) from None


def _parse_extra_notes(text: str | None, sent: bool, image_type: str, polar_notes: int, polychord_notes: int, spirograph_notes: int) -> int:
    """The requested Extra notes (k, feature 044). Not sent means the default (2); anything sent must be a whole number 1..8, and for a picture that takes the n loudest notes
    also at most its n (5, the Notes shown of Polar Chords, the Number of notes of Polychord or the smaller of the Number of notes of Spirograph and 8); the other pictures accept
    1..8 and ignore it."""
    if text is None and not sent:
        return DEFAULT_EXTRA_NOTES
    try:
        value = check_extra_notes(float(text or ""), MAX_EXTRA_NOTES)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"The extra notes must be a whole number from 1 to {MAX_EXTRA_NOTES}.") from None
    limit = notes_of(image_type, polar_notes, polychord_notes, spirograph_notes)
    if value > limit:
        raise HTTPException(status_code=400, detail=f"The extra notes must be a whole number from 1 to {limit}.")
    return value


def _parse_polychord_settings(notes: str | None, min_copies: str | None, max_copies: str | None, rotation: str | None, sent: set[str]) -> PolychordSettings:
    """The four settings of Polychord. A setting that is not sent takes its default; anything sent must be allowed (the
    number of notes a whole number 5..8, each number of copies a whole number 1..12, the maximum not under the minimum,
    the rotation a number from -360 to 360), or the answer is a 400 with the message of that setting."""
    try:
        notes_value = check_polychord_notes(float(notes or "")) if notes is not None or "polychord_notes" in sent else DEFAULT_POLYCHORD_NOTES
    except ValueError:
        raise HTTPException(status_code=400, detail=POLYCHORD_NOTES_MESSAGE) from None
    try:
        min_value = check_polychord_copies(float(min_copies or ""), "minimum") if min_copies is not None or "polychord_min_copies" in sent else DEFAULT_MIN_COPIES
    except ValueError:
        raise HTTPException(status_code=400, detail=MIN_COPIES_MESSAGE) from None
    try:
        max_value = check_polychord_copies(float(max_copies or ""), "maximum") if max_copies is not None or "polychord_max_copies" in sent else DEFAULT_MAX_COPIES
    except ValueError:
        raise HTTPException(status_code=400, detail=MAX_COPIES_MESSAGE) from None
    try:
        rotation_value = check_polychord_rotation(float(rotation or "")) if rotation is not None or "polychord_rotation" in sent else DEFAULT_ROTATION
    except ValueError:
        raise HTTPException(status_code=400, detail=ROTATION_MESSAGE) from None
    try:
        return check_polychord_settings(PolychordSettings(notes_value, min_value, max_value, rotation_value))
    except ValueError as error:  # the maximum under the minimum
        raise HTTPException(status_code=400, detail=str(error)) from None


def _parse_spirograph_settings(notes: str | None, history: str | None, fade: str | None, sent: set[str]) -> SpirographSettings:
    """The three settings of Spirograph. A setting that is not sent takes its default (8, 8 and 0.7); anything sent must be allowed (the number of
    notes and the history length whole numbers 5..12, the history fade a number 0.4..0.85), or the answer is a 400 with the message of that setting."""
    try:
        notes_value = check_spirograph_notes(float(notes or "")) if notes is not None or "spirograph_notes" in sent else DEFAULT_SPIROGRAPH_NOTES
    except ValueError:
        raise HTTPException(status_code=400, detail=SPIROGRAPH_NOTES_MESSAGE) from None
    try:
        history_value = check_spirograph_history(float(history or "")) if history is not None or "spirograph_history" in sent else DEFAULT_SPIROGRAPH_HISTORY
    except ValueError:
        raise HTTPException(status_code=400, detail=SPIROGRAPH_HISTORY_MESSAGE) from None
    try:
        fade_value = check_spirograph_fade(float(fade or "")) if fade is not None or "spirograph_fade" in sent else DEFAULT_SPIROGRAPH_FADE
    except ValueError:
        raise HTTPException(status_code=400, detail=SPIROGRAPH_FADE_MESSAGE) from None
    return SpirographSettings(notes_value, history_value, fade_value)


def _parse_vote_limit(text: str | None, sent: bool) -> int:
    """The requested Vote limit of Rhythm Circles (feature 047). Not sent means the default (20); anything sent must be a whole number from 1 to 100 (an empty text, a
    word and ``nan`` are refused too), or the answer is a 400 with the message of the setting."""
    if text is None and not sent:
        return DEFAULT_VOTE_LIMIT
    try:
        return check_vote_limit(float(text or ""))
    except ValueError:
        raise HTTPException(status_code=400, detail=VOTE_LIMIT_MESSAGE) from None


def _parse_wave_count(text: str | None, sent: bool) -> int:
    """The requested number of waves of the contour's beat wave. Not sent means the default; anything sent must be a
    whole number 2..10."""
    if text is None and not sent:
        return DEFAULT_WAVE_COUNT
    text = text or ""
    message = f"The wave count must be a whole number from {MIN_WAVE_COUNT} to {MAX_WAVE_COUNT}."
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=message) from None
    if not math.isfinite(value) or not value.is_integer() or not MIN_WAVE_COUNT <= value <= MAX_WAVE_COUNT:
        raise HTTPException(status_code=400, detail=message)
    return int(value)


def _parse_interpolate(text: str | None, sent: bool) -> int:
    """The requested interpolate value. Not sent means 1 (every frame drawn); anything sent must be a whole number 1..5.
    """
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
    threshold: str | None = Form(None),
    image_type: str | None = Form(None),
    colormap: str | None = Form(None),
    resolution: str | None = Form(None),
    note_count: str | None = Form(None),
    interpolate: str | None = Form(None),
    gaussian: str | None = Form(None),
    beat_coloring: str | None = Form(None),
    peak_distance: str | None = Form(None),
    note_layout: str | None = Form(None),
    decay_rate: str | None = Form(None),
    wave_count: str | None = Form(None),
    polar_notes: str | None = Form(None),
    polychord_notes: str | None = Form(None),
    polychord_min_copies: str | None = Form(None),
    polychord_max_copies: str | None = Form(None),
    polychord_rotation: str | None = Form(None),
    spirograph_notes: str | None = Form(None),
    spirograph_history: str | None = Form(None),
    spirograph_fade: str | None = Form(None),
    vote_limit: str | None = Form(None),
    decay_low: str | None = Form(None),
    decay_medium: str | None = Form(None),
    decay_high: str | None = Form(None),
    decay_saturated: str | None = Form(None),
    extra_notes: str | None = Form(None),
    export_obj: str | None = Form(None),
    sent: set[str] = Depends(_sent_fields),
) -> dict:
    window = _parse_window_size(window_size)
    fps = _parse_frame_rate(frame_rate)
    threshold_value = _parse_threshold(threshold, "threshold" in sent)
    image_type_value = _parse_image_type(image_type, "image_type" in sent)
    colormap_value = _parse_colormap(colormap, "colormap" in sent)
    resolution_value = _parse_resolution(resolution, "resolution" in sent)
    note_count_value = _parse_note_count(note_count, "note_count" in sent)
    interpolate_value = _parse_interpolate(interpolate, "interpolate" in sent)
    gaussian_value = _parse_gaussian(gaussian, "gaussian" in sent)
    beat_coloring_value = _parse_beat_coloring(beat_coloring, "beat_coloring" in sent)
    peak_distance_value = _parse_peak_setting(peak_distance, "peak_distance" in sent, DEFAULT_MIN_DISTANCE, check_min_distance)
    note_layout_value = _parse_note_layout(note_layout, "note_layout" in sent)
    decay_rate_value = _parse_decay_rate(decay_rate, "decay_rate" in sent, image_type_value)
    wave_count_value = _parse_wave_count(wave_count, "wave_count" in sent)
    polar_notes_value = _parse_polar_notes(polar_notes, "polar_notes" in sent)
    polychord_settings_value = _parse_polychord_settings(polychord_notes, polychord_min_copies, polychord_max_copies, polychord_rotation, sent)
    spirograph_settings_value = _parse_spirograph_settings(spirograph_notes, spirograph_history, spirograph_fade, sent)
    vote_limit_value = _parse_vote_limit(vote_limit, "vote_limit" in sent)
    extra_notes_value = _parse_extra_notes(
        extra_notes, "extra_notes" in sent, image_type_value, polar_notes_value, polychord_settings_value.notes, spirograph_settings_value.notes
    )
    export_obj_value = _parse_export_obj(export_obj, "export_obj" in sent, image_type_value)
    decay_amounts_value = tuple(
        _parse_decay_amount(text, name in sent, index)
        for index, (name, text) in enumerate(
            (("decay_low", decay_low), ("decay_medium", decay_medium), ("decay_high", decay_high), ("decay_saturated", decay_saturated))
        )
    )
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

        # the frequency buffers are always measured every 60 ms (feature 043), whatever the frame rate: the frame rate only
        # decides how many frames are made, and each frame averages the buffers that start in it
        step = buffer_step(file_rate)
        windows = window_count(samples, step)
        if windows > settings.max_windows:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"This would create {windows:,} windows; the limit is {settings.max_windows:,}. "
                    "Use a shorter file."
                ),
            )
        # the noise floor (feature 033): a note more than 60 dB below the loudest note of the file is 0 in every window,
        # whatever the image type, so that no picture or measurement counts it as a note. It is fixed (no setting) and
        # made once, here, before the frames are averaged
        result = floor_analysis(analyze_channels(left, right, file_rate, window, step=step))
        # the beat: the position of the middle of each frame in the local energy peak of the whole file, from the local
        # peaks measurement. Decay, Decay Exp, Polar Chords, Chromatic Decay and Chromatic Wireframe are always colored
        # by it, and Spirograph's curves are turned and sized by it; contour (its beat wave) only with the beat coloring box on; the other pictures and the box off never
        # measure it. Polychord (feature 042) takes both the beat (the number of copies) and the current tempo (the
        # color) from one measurement of the local peaks
        beat = None
        polychord = None
        if image_type_value == "polychord":
            peaks = measure_local_peaks(left, right, file_rate, peak_distance_value, DEFAULT_PROMINENCE)
            beat = peaks.frame_positions(fps, frames)
            polychord = PolychordData(frame_tempos(peaks, fps, frames), fps)
        elif image_type_value in ("decay", "decay-exp", "polar-chords", "spirograph", *CHROMATIC_TYPES) or (beat_coloring_value and image_type_value == "contour"):
            beat = measure_local_peaks(left, right, file_rate, peak_distance_value, DEFAULT_PROMINENCE).frame_positions(fps, frames)
        # the windows averaged into the frames (the note strengths that every picture is drawn from): made once, for write_frames
        values = average_frames(result, fps, frames)
        # Rhythm Circles (features 038, 040 and 047) turns its two inner rings with the local peaks themselves (one
        # measurement, with the minimum distance of the request; the prominence is not a setting (feature 040): every
        # measurement uses 20 percent) and its four outer rings with the average and the raw best-voted tempo of the starts of the
        # notes (found from the rise of the note strengths and placed on the waveform; Vote limit, not Extra notes), not with the beat
        rhythm = None
        if image_type_value == "rhythm-circles":
            peaks = measure_local_peaks(left, right, file_rate, peak_distance_value, DEFAULT_PROMINENCE)
            rhythm = rhythm_angles(peaks, fps, frames, result.frames, left, right, vote_limit_value)  # the starts come from the 60 ms windows and the waveform, not the frames
        # write_frames draws the frames (the averaged note values) as the chosen image type; for the contour, a resolution
        # above 1 first interpolates the grid of note values to a finer one, a number of notes below 84 first builds the picture from the notes with the most
        # energy in the file only, and an interpolate value above 1 draws only every n-th frame and makes the others
        # from their neighbors with Pillow
        write_frames(
            values,
            frames_dir,
            colormap=colormap_value,
            threshold=threshold_value,
            image_type=image_type_value,
            resolution=resolution_value,
            note_count=note_count_value,
            interpolate=interpolate_value,
            gaussian=gaussian_value,
            beat=beat,
            note_layout=note_layout_value,
            decay_rate=decay_rate_value,
            wave_count=wave_count_value,
            polar_notes=polar_notes_value,
            decay_amounts=decay_amounts_value,
            energy=frame_energy(result, fps, frames) if image_type_value == "energy-graphs" else None,
            rhythm=rhythm,
            polychord=polychord,
            polychord_settings=polychord_settings_value,
            spirograph_settings=spirograph_settings_value,
            extra_notes=extra_notes_value,
            export_obj=export_obj_value,
        )
        # The video made from these frames later (feature 029) needs the frame rate, and the frames do not hold it.
        (frames_dir / "render.json").write_text(json.dumps({"frame_rate": fps}), encoding="utf-8")
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
        "threshold": threshold_value,
        "image_type": image_type_value,
        "colormap": colormap_value,
        "resolution": resolution_value,
        "note_count": note_count_value,
        "interpolate": interpolate_value,
        "gaussian": gaussian_value,
        "beat_coloring": beat_coloring_value,
        "peak_distance": peak_distance_value,
        "note_layout": note_layout_value,
        "decay_rate": decay_rate_value,
        "wave_count": wave_count_value,
        "polar_notes": polar_notes_value,
        "polychord_notes": polychord_settings_value.notes,
        "polychord_min_copies": polychord_settings_value.min_copies,
        "polychord_max_copies": polychord_settings_value.max_copies,
        "polychord_rotation": polychord_settings_value.rotation,
        "spirograph_notes": spirograph_settings_value.notes,
        "spirograph_history": spirograph_settings_value.history,
        "spirograph_fade": spirograph_settings_value.fade,
        "vote_limit": vote_limit_value,
        "extra_notes": extra_notes_value,
        "export_obj": export_obj_value,
        "obj_url": f"/api/jobs/{job_id}/obj" if export_obj_value else None,
        "decay_low": decay_amounts_value[0],
        "decay_medium": decay_amounts_value[1],
        "decay_high": decay_amounts_value[2],
        "decay_saturated": decay_amounts_value[3],
        "step_samples": step,
        "window_count": result.window_count,
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


@router.get("/{job_id}/obj")
def get_obj(job_id: str) -> FileResponse:
    """The ZIP of the 3D files (feature 045) of a job made with the 3D export: one ``frame_<index>.obj`` for each frame. It is
    packed into the output folder on the first request and reused while no file is newer."""
    if not _JOB_ID.fullmatch(job_id):
        raise HTTPException(status_code=404, detail="Render not found.")
    folder = settings.frames_temp_dir / job_id / OBJ_FOLDER
    files = list(folder.glob("*.obj")) if folder.is_dir() else []
    if not files:
        raise HTTPException(status_code=404, detail="No 3D export was made for this render.")
    archive = settings.output_dir / job_id / OBJ_ARCHIVE
    if not archive.is_file() or archive.stat().st_mtime < max(path.stat().st_mtime for path in files):
        zip_obj_files(folder, archive)
    return FileResponse(archive, media_type="application/zip", filename=OBJ_ARCHIVE)
