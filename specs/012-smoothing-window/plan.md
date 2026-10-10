# Implementation Plan: Smoothing Window

**Branch**: `012-smoothing-window` (no git branch created; spec directory name only) | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/012-smoothing-window/spec.md`

## Summary

Smoothing changes from an endless running average to a **windowed weighted average**. A new setting, the **smoothing window** `w` (a whole number from 1 to 20, default 1), says how many earlier frames are looked at; the existing **smoothing** `s` (0 to 0.8, default 0) is the weight of each of them against a weight of 1 for the current frame:

`smoothed[t] = ( A[t] + s·A[t−1] + … + s·A[t−w] ) / ( 1 + s·k )`, with `k = min(t, w)` earlier frames actually available

where `A` are the **unsmoothed** values, so a value is forgotten exactly `w` frames after it last occurred. With `s = 0` the output is exactly the input for every `w`. The same function replaces the old running average everywhere it was used: each note's value, each tile's hue (a plain 0..1 number) and each frame's brightness. Smoothing still comes first; the gray levels, the roots, the level steps (feature 010) and the threshold (011) work on the smoothed values unchanged.

Technically: `smooth_frames(frames, smoothing, window=1)` in `frame_rendering.py` is rewritten (its only job is this formula; it adds each earlier frame with a shifted slice, `w` vectorized passes over the whole array, then divides by the per-frame weight sum), and `hue_sequence`, `value_sequence` and `write_frames` pass a new `smoothing_window` argument through. `create_job` gains an optional `smoothing_window` form field with strict validation and echoes it. The frontend adds a whole-number field before the Smoothing slider, validation, an explanation, a rewritten Smoothing explanation, and a summary line. No new dependency, module or change to the analysis, energy, hue calculation, level steps or threshold.

Because the meaning of an existing setting changes, a number of existing tests that encode the old behavior (a reference running average, "a stopped note fades more slowly at higher smoothing", and so on) are rewritten to the new definition; they are listed in [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: numpy, Pillow, FastAPI; Vue, vitest. No new packages.

**Storage**: N/A. Same temp directories; PNGs stay indexed-colour.

**Testing**: pytest: `smooth_frames` against an independent reference loop written in the test (the spec's worked example 8, 4, 2 with `w = 2`, `s = 0.5` giving 8, 5.33, 4; frames near the start; an impulse that is non-zero for exactly `w` frames then exactly 0, for every `w` from 1 to 20; constant input unchanged; `s = 0` returns an equal new array for every `w`; the input never modified; causality, i.e. appending frames changes no earlier output; each note uses only its own history; window and smoothing validation including bools, floats, 0, 21, `nan`); `hue_sequence` and `value_sequence` with a window (same function, plain-number hue, brightness smoothed from its own history); `write_frames` (`s = 0` byte-identical for every window; the three quantities smoothed with the same `w` and `s`; smoothing before the level steps and the threshold); the API field (valid, missing, empty, `0`, `21`, `2.5`, text, `nan`, `inf`) and its response, plus a stopped note disappearing after exactly `w` frames through the API. The existing smoothing tests are rewritten for the new definition. vitest: window constants, validation, help texts, the rendered field.

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: Creating the same frames takes no longer than before at smoothing 0 and no more than 25% longer at `w = 20`, `s = 0.8` (SC-008). The cost is `w` shifted additions over a `(frames, 88)`, a `(frames, 84)` and a `(frames,)` array, a few million floating-point operations per job.

**Constraints**: Deterministic output; image size, layout, frame count, timing unchanged; with smoothing 0 the output is byte-for-byte what it is today; results already created are unchanged.

**Scale/Scope**: Edits to `frame_rendering.py` and `jobs.py` (no new module), a new test module for the window plus rewrites in `test_frame_rendering.py`, `test_jobs_api.py`, `test_frame_brightness.py`, `test_color_levels_api.py`/`test_threshold_api.py` where they depend on the old smoothing, frontend edits to five files with tests, and the README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. The plan adds no module and no dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/012-smoothing-window/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── smoothing-window-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── services/frame_rendering.py   # MIN/MAX/DEFAULT_SMOOTHING_WINDOW, smooth_frames(window=), hue_sequence/value_sequence/write_frames(smoothing_window=)
│   └── routers/jobs.py               # optional "smoothing_window" form field, _parse_smoothing_window(), "smoothing_window" in the response
└── tests/
    ├── test_smoothing_window.py      # NEW: the formula, the window, validation, causality, impulse response
    ├── test_frame_rendering.py       # old running-average tests rewritten for the new definition; hue/threshold/steps tests adjusted
    ├── test_frame_brightness.py      # brightness smoothing tests rewritten
    ├── test_jobs_api.py              # smoothing tests rewritten (no longer a running average)
    ├── test_smoothing_window_api.py  # NEW: the field's validation, response, and frames through the API
    └── test_energy_api.py            # expected response keys gain "smoothing_window"

frontend/src/
├── api.ts                            # JobSettings.smoothingWindow, JobResult.smoothing_window, form field
├── App.vue                           # "Smoothing window: n" summary line
├── components/
│   ├── SettingsForm.vue              # Smoothing window number field before the Smoothing slider, with info popover
│   └── SettingsForm.test.ts          # the field is rendered, starts at 1, is disabled while busy
└── utilities/
    ├── validation.ts                 # SMOOTHING_WINDOW_RANGE, DEFAULT_SMOOTHING_WINDOW, validateSmoothingWindow
    ├── validation.test.ts
    ├── help.ts                       # smoothingWindowHelp, smoothingHelp rewritten
    └── help.test.ts

README.md                             # the Smoothing description rewritten; the window documented
```

**Structure Decision**: The new smoothing is a replacement of one existing pure function, so it stays in `frame_rendering.py` where `smooth_frames` already is, and everything that already called it (notes, hues, brightness) keeps its call site and only gains the `window` argument. This means the order of the pipeline (smooth first; then gray levels, roots, steps, threshold) is untouched and features 010 and 011 need no code change. A separate module would add indirection for one function; the window field's tests go in new modules (as in features 010 and 011) so the shared `post` helper stays unchanged.

## Complexity Tracking

No constitution violations. Nothing to justify.
