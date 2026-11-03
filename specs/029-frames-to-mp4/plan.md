# Implementation Plan: Frames to MP4

**Branch**: `029-frames-to-mp4` (no git branch created; spec directory name only) | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/029-frames-to-mp4/spec.md`

## Summary

A **Create video** button under the frame player joins the frames of the finished render into a **silent H.264 MP4** with ffmpeg and saves it as `backend/output/<job_id>/video.mp4`. The page shows "working", then where the file was saved plus a download link, or a plain error.

How it is done (research Decisions 1 to 6):

- **A new pure-ish service, `services/video.py`**, builds and runs the ffmpeg command (`-framerate <fps> -start_number 0 -i frame_%06d.png -an -c:v libx264 -pix_fmt yuv420p -vf pad=ceil(iw/2)*2:ceil(ih/2)*2 -movflags +faststart`), writes to a temporary file in the render's output directory and renames it over `video.mp4` only when ffmpeg succeeded (so a failure never leaves a partial file, and a repeat replaces the old video). It finds ffmpeg through a new setting `ffmpeg_path` (env `MV_FFMPEG_PATH`, default: `ffmpeg` on the PATH) and raises `VideoError` with a user-fit message for every failure (ffmpeg missing, frames gone, ffmpeg failed or timed out).
- **The frame rate is stored server side**: `create_job` writes a tiny `render.json` (`{"frame_rate": …}`) next to the frames after `write_frames`, so the video endpoint never trusts the client for it. The frame count is the number of `frame_*.png` files on disk.
- **Two endpoints in a new router `routers/video.py`**: `POST /api/jobs/{job_id}/video` (synchronous, a plain `def` so FastAPI runs it in the thread pool; 404 when the frames are gone, 409 when a video for the same job is already being made, 503 when ffmpeg is missing, 500 otherwise) and `GET /api/jobs/{job_id}/video` (the file, `video/mp4`, as a download). An in-memory set of job ids being converted gives the 409.
- **Config**: `output_dir` (default `backend/output`, env `MV_OUTPUT_DIR`), `ffmpeg_path`, `video_timeout_seconds` (600). `backend/output/` is added to `.gitignore`.
- **Frontend**: `api.ts` gets `createVideo(job)` and `videoUrl(job)` and a `VideoResult` type; a new component `VideoExport.vue` (props: the `JobResult`) with the states idle / working / done / error, reset whenever the result changes, placed under `FramePlayer` in `App.vue`.
- **Tests**: backend unit tests on the command and the failure handling with a fake runner, API tests with a stub ffmpeg for the status codes, and (skipped when ffmpeg is absent) one real conversion checked with `ffprobe` for frame rate, duration and no audio stream; frontend tests for the api functions and the component states.

## Technical Context

**Language/Version**: Python 3.10 (backend), TypeScript with Vue 3 (frontend)

**Primary Dependencies**: FastAPI, pydantic-settings, the standard `subprocess` module; ffmpeg (external program, already on the user's PATH); nothing new in `requirements.txt` or `package.json`

**Storage**: files: frames in `frames_temp_dir/<job_id>/`, the video in `backend/output/<job_id>/video.mp4`

**Testing**: pytest (backend), vitest (frontend)

**Target Platform**: a local single-user app, developed on Windows 10

**Project Type**: web application (`backend/` + `frontend/`)

**Performance Goals**: 1,000 frames to a video in under 60 seconds (spec SC-004); the page stays responsive while it works (the request runs in a worker thread)

**Constraints**: no audio in the video; no partial files after a failure; one video per render; frames, settings and every other feature unchanged

**Scale/Scope**: up to `max_frames` (30,000) frames of 600 × 400 pixels per render

## Constitution Check

`.specify/memory/constitution.md` is still the unfilled template, so there are no project gates to evaluate. The plan follows the habits of the existing features instead: validation at the API edge with plain messages, settings in `config.py`, pure logic in `services/`, thin routers, tests beside each layer. No violations; Complexity Tracking is empty.

Re-checked after Phase 1: unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/029-frames-to-mp4/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── video-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks, not made here
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── config.py                  # + output_dir, ffmpeg_path, video_timeout_seconds
│   ├── main.py                    # + include the video router
│   ├── routers/
│   │   ├── jobs.py                # + write render.json after write_frames
│   │   └── video.py               # NEW: POST and GET /jobs/{job_id}/video
│   └── services/
│       └── video.py               # NEW: build_command, create_video, VideoError
├── tests/
│   ├── test_video.py              # NEW: the service
│   └── test_video_api.py          # NEW: the endpoints (+ one real ffmpeg test)
└── output/                        # created at run time, git-ignored

frontend/src/
├── api.ts                         # + VideoResult, createVideo, videoUrl
├── api.test.ts                    # + tests
├── App.vue                        # + <VideoExport :result="result" />
└── components/
    ├── VideoExport.vue            # NEW
    └── VideoExport.test.ts        # NEW

.gitignore                         # + backend/output/
```

**Structure Decision**: the existing web-application layout; the new code sits beside the files for the other features and touches `jobs.py` only to record the frame rate.

## Complexity Tracking

No violations to justify.
