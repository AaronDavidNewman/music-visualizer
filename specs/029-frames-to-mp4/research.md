# Research: Frames to MP4

No `NEEDS CLARIFICATION` items remained after the spec; these are the design choices.

## Decision 1: Encode with libx264, `yuv420p`, no audio

- **Decision**: `ffmpeg -y -framerate <fps> -start_number 0 -i <dir>/frame_%06d.png -an -vf "pad=ceil(iw/2)*2:ceil(ih/2)*2" -c:v libx264 -pix_fmt yuv420p -movflags +faststart <tmp>.mp4`.
- **Rationale**: H.264 in `yuv420p` plays in every browser and player. `-an` guarantees no audio stream (and the audio is never an input anyway). `pad` rounds odd sizes up to even, which `yuv420p` requires. `+faststart` lets the browser start playing the download at once. The installed ffmpeg (a 2018 build, `N-92806`) has `libx264` and supports every flag used.
- **Alternatives**: `mpeg4` (always built in, but poorer quality and less compatible); `-crf` settings exposed to the user (out of scope; ffmpeg's default CRF 23 is fine); `scale` instead of `pad` (would resample the pictures).

## Decision 2: The frame rate is stored with the frames

- **Decision**: after `write_frames`, `create_job` writes `render.json` with `{"frame_rate": fps}` in the frames directory. The video service reads it; the frame count is the number of `frame_*.png` files.
- **Rationale**: the frames directory is the only thing the render leaves behind, and the fps is not recoverable from it. Reading it server side means the endpoint takes no input from the client except the job id, so there is nothing to validate or tamper with, and the video length always matches the render.
- **Alternatives**: the client sends `frame_rate` (trusts the client, easy to get wrong); an in-memory job table (lost on restart; the app has none today).

## Decision 3: Synchronous request in a worker thread

- **Decision**: `POST /api/jobs/{job_id}/video` is a plain `def` that runs ffmpeg with `subprocess.run` (timeout from `video_timeout_seconds`, default 600 s) and returns when done.
- **Rationale**: `POST /api/jobs` already works this way (the page waits with a "working" message), 1,000 frames take seconds, and it needs no job table, polling or progress channel. FastAPI runs a plain `def` in its thread pool, so other requests (the frame images) are not blocked.
- **Alternatives**: background task plus polling (more state for a local tool); streaming ffmpeg progress (not required by the spec).

## Decision 4: No partial files, replace on repeat

- **Decision**: ffmpeg writes to `video.tmp.mp4` in `backend/output/<job_id>/`; on success it is moved over `video.mp4` with `os.replace`; on any failure the temporary file is deleted and the output directory is removed if it is empty (a directory created by this attempt must not be left behind either).
- **Rationale**: meets FR-006 and FR-009 and SC-005 without extra bookkeeping; `os.replace` is atomic, so a player downloading the old file is not handed a half-written one.
- **Alternatives**: `-y` straight onto `video.mp4` (leaves a broken file on failure).

## Decision 5: One conversion at a time per render

- **Decision**: a module-level set of job ids (guarded by a lock) marks the conversions in progress; a second `POST` for the same job gets `409` with "A video is already being made for this render." The button is also disabled on the page while working.
- **Rationale**: FR-007; two ffmpeg runs would race on the same temporary file. In-memory is enough for a single-process local app.
- **Alternatives**: a lock file in the output directory (survives a crash with a stale lock, more cleanup).

## Decision 6: Finding ffmpeg and the output directory

- **Decision**: new settings `ffmpeg_path` (default `"ffmpeg"`, resolved with `shutil.which`; env `MV_FFMPEG_PATH` for a full path such as `C:\ffmpeg\bin\ffmpeg.exe`) and `output_dir` (default `backend/output`, env `MV_OUTPUT_DIR`). A missing executable is `503` with "ffmpeg was not found. Install it, or set MV_FFMPEG_PATH." `backend/output/` goes in `.gitignore`.
- **Rationale**: ffmpeg is on the user's PATH today, but a setting costs one line and makes the tests and other machines easy. `output_dir` as a setting lets tests use a temp directory.
- **Alternatives**: hard-coding the Windows path (not portable).

## Decision 7: Job ids and paths

- **Decision**: the `job_id` is validated with the existing `^[0-9a-f]{32}$` pattern before any path is built (the frame endpoint does the same), so a request cannot reach outside `frames_temp_dir` or `output_dir`. The response reports the absolute path of the saved file.
- **Rationale**: path traversal safety; the absolute path is what the user needs to find the file.
