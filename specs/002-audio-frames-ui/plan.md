# Implementation Plan: Audio Upload and Frame Visualization UI

**Branch**: `002-audio-frames-ui` | **Date**: 2026-10-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-audio-frames-ui/spec.md`

## Summary

Add a browser UI and one backend endpoint. The user picks a `.wav`, sets window size and frame rate, and submits. The FastAPI backend streams the upload into a per-submission folder in a temporary *audio* directory, reads the WAV, rejects unusable input, runs the feature 001 note analysis, averages the 88-value windows into frame periods of 1 ÷ frame rate seconds, and writes one PNG per frame (grayscale originally, colored since feature 007) (originally an 11 × 8 grid of 20-pixel squares, now a 12 × 7 grid of 21 × 24 tiles from feature 005; brightness scaled against the file's loudest value, then brightened by the brightness-th root from feature 004) into a per-submission folder in a separate temporary *frames* directory. The response carries the metadata the UI needs, and each PNG is served at its own URL. The Vue frontend shows a form, a busy state, error messages, and a player with play/pause, loop, a position slider and the frame time.

The submission is one synchronous request. The sample file analyzes in about 0.5 s, so the cost is image writing, which is measured against SC-002 during implementation.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 with Vue 3.5 (frontend, Node 22)

**Primary Dependencies**: Backend: FastAPI, python-multipart, numpy, scipy, Pillow (all present). Frontend: Vue 3, Vite 5, vue-tsc. New dev dependency: `vitest` for frontend logic tests. No other new runtime dependencies.

**Storage**: Files only. Uploaded audio in `<tmp>/music-visualizer/audio/<job_id>/audio.wav`; frame images in `<tmp>/music-visualizer/frames/<job_id>/frame_000000.png`. No database.

**Testing**: pytest with FastAPI `TestClient` and synthetic WAVs (backend); vitest for pure frontend logic (validation, playback timing); `vue-tsc` type check and `vite build` for the components. Manual browser check in quickstart.

**Target Platform**: Local developer machine (Windows here), modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: 3-minute file at 30 fps and the default window in under 60 s end to end (SC-002); playback within 10% of the chosen rate up to 30 fps (SC-006).

**Constraints**: Upload up to 200 MB; at most 30,000 frames per submission; window size one of 4096, 8192, 16384, 32768; frame rate 1–60. File names never influence storage paths.

**Scale/Scope**: Single user, one submission at a time in the UI. One router, two services, three Vue components, a few pure helpers.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. The design reuses the existing layout (routers, services, config) and adds no new layers. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/002-audio-frames-ui/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── http-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── config.py                    # + temp dirs, limits (audio size, frames, window, fps)
│   ├── main.py                      # + include jobs router
│   ├── routers/
│   │   └── jobs.py                  # POST /api/jobs, GET /api/jobs/{id}/frames/{index}
│   └── services/
│       ├── note_analysis.py         # small refactor: public read_wav, analyze_channels, sample_count
│       └── frame_rendering.py       # frame averaging, brightness, grid layout, PNG writing
└── tests/
    ├── test_frame_rendering.py
    └── test_jobs_api.py

frontend/
├── package.json                     # + vitest, test script
└── src/
    ├── App.vue                      # replaces HelloWorld; owns state: idle / busy / done / error
    ├── api.ts                       # submitJob(), frameUrl()
    ├── lib/
    │   ├── validation.ts            # window size / frame rate / file checks
    │   ├── validation.test.ts
    │   ├── playback.ts              # frame index from elapsed time, clamp, loop
    │   └── playback.test.ts
    └── components/
        ├── UploadForm.vue
        └── FramePlayer.vue
```

**Structure Decision**: This is a web application and both projects already exist. The backend gets one router and one service module, following the existing `routers/` and `services/` split. The frontend replaces the hello-world component with three components. Logic that can be wrong without a browser (validation, playback timing) lives in plain TypeScript modules so it is unit-testable.

## Complexity Tracking

No constitution violations. Nothing to justify.
