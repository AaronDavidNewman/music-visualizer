# Implementation Plan: Discrete Color Levels

**Branch**: `010-discrete-color-levels` (no git branch created; spec directory name only) | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/010-discrete-color-levels/spec.md`

## Summary

Each of the three color properties (hue, saturation, brightness) gets an optional **step** that rounds its finished value to a small set of evenly spaced levels. Hue steps are N/A, 12, 36, 90, 180 on a 0° to 360° scale; saturation and brightness steps are N/A, 5, 10, 20, 50 on a 0 to 100 scale. A step `s` on a scale of size `R` gives `round((R + s) / s)` levels (the multiples of `s` from 0 to `R`, both ends included, so the maximum is always reachable and there are never fewer than 3). N/A leaves the property smooth, and is the default, so frames are identical to today's unless a step is chosen.

Technically: a new small service module `color_levels.py` holds the allowed steps, `level_count` and a vectorized `snap` (nearest level, halves up). `frame_rendering.py` applies it as the very last step on each property: on the smoothed hues (`hue_sequence` result), on each tile's saturation inside `tile_colors`, and on the smoothed frame brightness (`value_sequence` result). `write_frames` gains three optional step arguments and `create_job` gains three optional form fields (`hue_step`, `saturation_step`, `brightness_step`) with strict validation against the allowed lists, echoed in the response. The frontend adds three dropdowns (with the level count beside each), their explanations, validation helpers and result-summary lines. No new dependency.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: numpy, Pillow, FastAPI; Vue, vitest. No new packages.

**Storage**: N/A. Same temp directories; PNGs stay indexed-colour (a frame still has at most 84 flat colours; rounding only reduces how many differ).

**Testing**: pytest: `level_count` for every allowed step (hue 31, 11, 5, 3; saturation and brightness 21, 11, 6, 3); `snap` on hand-worked values (nearest level, half-way goes up, 0 and the maximum are fixed points, N/A returns the input unchanged, floating-point noise such as 6.000000000000001° with step 12 still rounds up); `tile_colors` with a saturation step (saturation of every tile is a level, black tiles stay black); `write_frames` per property (only the chosen property changes; levels are the only values that appear; smoothing is applied before rounding; adding a frame at the end changes no earlier frame; all-N/A output equals the output with no step arguments); the API fields (valid, N/A in any case, missing, empty, `0`, `7`, `51`, `12` for saturation, text, `2.5`) with the refusal message, and the response values. vitest: step lists, `levelCount`, level label text (`"20 (6 levels)"`, `"N/A (smooth)"`), validators, help texts.

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: Time to create the same frames no more than 10% longer than before (SC-009). Rounding is one vectorized numpy expression per property (hue once for the whole file, brightness once, saturation one 84-value array per frame), which is negligible next to the analysis and the PNG encoding. It is measured while implementing on the sample file.

**Constraints**: Deterministic output; image size, layout, frame count, timing and format unchanged; results already created are unchanged; with every step at N/A the output must be byte-for-byte what it is today.

**Scale/Scope**: One new backend module, edits to `frame_rendering.py` and `jobs.py`, one new test module plus edits to two existing ones, frontend edits to five files (`validation.ts`, `help.ts`, `api.ts`, `SettingsForm.vue`, `App.vue`) with tests, and documentation.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. The plan adds one small module and no dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/010-discrete-color-levels/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── color-levels-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── services/
│   │   ├── color_levels.py           # NEW: step lists, level_count(), snap()
│   │   └── frame_rendering.py        # tile_colors(saturation_step); write_frames(hue_step, saturation_step, value_step)
│   └── routers/jobs.py               # three optional form fields, _parse_step(), steps in the response
└── tests/
    ├── test_color_levels.py          # NEW: level counts, snap, API-independent edge cases
    ├── test_frame_rendering.py       # per-property rounding through tile_colors / write_frames
    └── test_jobs_api.py              # step fields validation and response

frontend/src/
├── api.ts                            # JobSettings / JobResult step fields, form fields
├── App.vue                           # "Hue steps / Saturation steps / Brightness steps" summary lines
├── components/SettingsForm.vue       # three dropdowns (new field row) with level counts and info popovers
└── utilities/
    ├── validation.ts                 # step lists, levelCount, levelLabel, validateStep
    ├── validation.test.ts
    ├── help.ts                       # hueStepHelp, saturationStepHelp, brightnessStepHelp
    └── help.test.ts

README.md                             # settings and image description: the three steps
```

**Structure Decision**: Rounding to levels is a pure function of a value, a step and a scale, independent of audio and of rendering, so it gets its own small module (`color_levels.py`) that both `frame_rendering.py` and `jobs.py` import (the job router needs the allowed lists for validation; rendering needs `snap`). This avoids putting the lists in `frame_rendering.py` beside unrelated constants and keeps the rounding rule testable in isolation. Rounding is applied where each property's final value already exists (hues after `hue_sequence`, brightness after `value_sequence`, saturation where `tile_colors` forms it), so no existing function changes meaning when its new argument is left out. The API field names follow the page's labels (`hue_step`, `saturation_step`, `brightness_step`), while backend code uses HSV names (`value_step`) for the frame brightness; the mapping is in [research.md](research.md) Decision 4, because the older `brightness` and `energy` fields already use different names from the page.

## Complexity Tracking

No constitution violations. Nothing to justify.
