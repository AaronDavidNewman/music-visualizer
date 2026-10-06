# Implementation Plan: Note Smoothing

**Branch**: `006-note-smoothing` | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-note-smoothing/spec.md`

## Summary

Add a **smoothing** value *s*, from 0.0 to 0.8, that turns each note's sequence of frame values into a running average: the first frame is unchanged, and every later frame is `s × (previous smoothed value) + (1 − s) × (this frame's value)`, computed for each of the 88 notes on its own. The step runs on the averaged note values after `average_frames` and before they are scaled to gray levels, so the scaling, brightness, octave layout and everything after it work on the smoothed values unchanged. Smoothing 0 returns the values untouched, so existing output is identical. The backend gains one optional form field (`smoothing`), validated on the server like brightness (an omitted field means 0, anything sent must be a number from 0.0 to 0.8), and reports the value used. The form gets a slider, 0.00 to 0.80 in steps of 0.01, with the value shown next to it.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 with Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: numpy; Vue, Vite, vitest. No new packages.

**Storage**: N/A. Same temp directories as before.

**Testing**: pytest (the recurrence against an independent reference, the worked example, fade lengths, note independence, API field, errors, and equality with the previous output at 0) and vitest (the validation helper and the slider's range). The slider itself is checked by typecheck, build and the manual quickstart, as in earlier features.

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: Changing only the smoothing changes frame count, window count and time by no more than 10% (SC-008). The recurrence is one vector operation of 88 values per frame, at most 30,000 frames.

**Constraints**: Smoothing is a float from 0.0 to 0.8 inclusive; default 0.0; the range is fixed, not a setting. Server validation happens before any file is stored.

**Scale/Scope**: One new service function, one router change, one frontend helper, three frontend files changed.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. The change adds one function to an existing module. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/006-note-smoothing/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── http-api-changes.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── routers/jobs.py                 # + smoothing field, validation, smoothing step, response field
│   └── services/frame_rendering.py     # MIN/MAX/DEFAULT_SMOOTHING, smooth_frames(frames, smoothing)
└── tests/
    ├── test_frame_rendering.py         # + smoothing recurrence, fades, independence
    └── test_jobs_api.py                # + smoothing request, response, errors

frontend/src/
├── api.ts                              # smoothing in JobSettings and JobResult
├── App.vue                             # summary shows smoothing
├── components/UploadForm.vue           # slider with value readout
└── lib/
    ├── validation.ts                   # SMOOTHING_RANGE, DEFAULT_SMOOTHING, validateSmoothing, formatSmoothing
    └── validation.test.ts              # + smoothing cases
```

**Structure Decision**: Same two projects and layout as features 002 to 005. The recurrence lives in `frame_rendering.py` beside the other per-frame steps (`average_frames`, `to_gray_levels`), so the pipeline reads in order: average, smooth, scale, brighten, draw. The router calls it as its own step, which keeps `write_frames` unchanged.

## Complexity Tracking

No constitution violations. Nothing to justify.
