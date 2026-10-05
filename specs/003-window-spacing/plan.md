# Implementation Plan: Window Spacing Parameter

**Branch**: `003-window-spacing` | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-window-spacing/spec.md`

## Summary

Windows currently start at multiples of the window size. This feature makes the distance between window starts a user setting, the **window spacing**, expressed as a multiple of the window size. The backend gains one optional form field (`window_spacing`). It computes the step in samples (`spacing × window size`, never below 1 sample), starts window *k* at the nearest whole sample to `k × step`, and averages frames from the windows that start in each frame period, falling back to the most recent earlier window. A new default, one frame period divided by the window size and rounded down to 6 decimals, is computed in the browser from the frame rate, window size and the chosen file's sample rate (read from the WAV header in the browser). It is recalculated whenever any of those three change. The results summary shows the spacing used, the step in samples, and the number of windows analyzed. A spacing of 1 reproduces the current output exactly.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 with Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: FastAPI, numpy, scipy, Pillow; Vue, Vite, vitest. No new packages.

**Storage**: N/A. Same temp directories as feature 002.

**Testing**: pytest (analysis, spacing helpers, frame averaging, API) and vitest (default-spacing formula, WAV header reader, validation). Component behavior (field refresh on change) checked by typecheck, build and the manual quickstart, as in feature 002.

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: With the default spacing a 3-minute file at 30 fps stays within the 60 s target (SC-007); the default recalculates in the browser well under 1 s (SC-004); an oversize window count is refused in under 2 s without analysis (SC-008).

**Constraints**: At most 60,000 windows per submission (new setting). Step never below 1 sample. Same frame limit (30,000), window sizes (4096–32768) and frame rates (1–60) as feature 002.

**Scale/Scope**: Two backend modules changed and one added, one backend router changed, two frontend modules added, three frontend files changed.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. The change extends existing modules and adds one small helper module. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/003-window-spacing/
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
│   ├── config.py                       # + max_windows
│   ├── routers/jobs.py                 # + window_spacing field, window cap, new response fields
│   └── services/
│       ├── window_spacing.py           # NEW: default_spacing, resolve_step
│       ├── note_analysis.py            # window_starts, window_count, analyze_channels(step=...), AnalysisResult.starts
│       └── frame_rendering.py          # average_frames uses window start samples
└── tests/
    ├── test_window_spacing.py          # NEW
    ├── test_note_analysis.py           # + step tests
    ├── test_frame_rendering.py         # + overlap / gap tests
    └── test_jobs_api.py                # + spacing tests

frontend/src/
├── api.ts                              # + windowSpacing argument, new JobResult fields
├── App.vue                             # summary shows spacing, step, windows, raised notice
├── components/UploadForm.vue           # spacing field, live default, hints
└── lib/
    ├── spacing.ts                      # NEW: defaultSpacing, minSpacing, validateSpacing, formatting
    ├── spacing.test.ts                 # NEW
    ├── wavHeader.ts                    # NEW: read sample rate from a WAV file's header
    └── wavHeader.test.ts               # NEW
```

**Structure Decision**: Same two projects and layout as feature 002. The step and default rules are a small pure module on each side (`window_spacing.py`, `spacing.ts`) so they can be tested without the server or a browser. Both sides share a table of expected values in their tests to keep the formulas in agreement.

## Complexity Tracking

No constitution violations. Nothing to justify.
