# Implementation Plan: Brightness Parameter

**Branch**: `004-brightness-parameter` | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-brightness-parameter/spec.md`

## Summary

Frames are currently brightened with a fixed square root, `255 × sqrt(level / 255)`. This feature makes the root a user setting, **brightness**, a whole number from 2 to 100, so the display step becomes `255 × (level / 255)^(1 / brightness)`, rounded to a whole gray level. Brightness 2 is the default and reproduces today's images exactly. The backend gains one optional form field (`brightness`), validated on the server, and passes it to the frame writer, which maps levels through a 256-entry table built from the formula. The form gets a whole-number field with the 2–100 range and a hint about contrast, and the results summary shows the value used. The form's submit event and `submitJob` are changed from a growing list of positional arguments to one settings object, since a fifth number would otherwise be easy to mix up.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 with Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: FastAPI, numpy, Pillow; Vue, Vite, vitest. No new packages.

**Storage**: N/A. Same temp directories as feature 002.

**Testing**: pytest (the formula over every level and brightness, rendering, API) and vitest (validation). Component behavior checked by typecheck, build and the manual quickstart, as in earlier features.

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: Changing only the brightness changes total time by no more than 10% (SC-006). The table lookup makes the display step cheaper than the per-frame `power` call it replaces.

**Constraints**: Brightness is an integer from 2 to 100, fixed (not a setting). Default 2. Server validation before any file is stored.

**Scale/Scope**: One backend service function reworked, one router changed, one frontend helper added, three frontend files changed.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. The change extends existing modules and adds no new ones. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/004-brightness-parameter/
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
│   ├── routers/jobs.py                 # + brightness field, validation, response field
│   └── services/frame_rendering.py     # MIN/MAX/DEFAULT_BRIGHTNESS, boost_levels(levels, brightness), render_frame/write_frames(brightness)
└── tests/
    ├── test_frame_rendering.py         # + formula over all levels and brightnesses
    └── test_jobs_api.py                # + brightness request, response, errors

frontend/src/
├── api.ts                              # JobSettings object, brightness in JobResult
├── App.vue                             # passes settings object, summary shows brightness
├── components/UploadForm.vue           # brightness field, emits one settings object
└── lib/
    ├── validation.ts                   # BRIGHTNESS_RANGE, DEFAULT_BRIGHTNESS, validateBrightness
    └── validation.test.ts              # + brightness cases
```

**Structure Decision**: Same two projects and layout as features 002 and 003. The formula lives next to the existing display step in `frame_rendering.py` so there is one place that decides what a gray level looks like. The range is defined once on each side (Python constants, TypeScript constants), each covered by tests that use the same boundary values.

## Complexity Tracking

No constitution violations. Nothing to justify.
