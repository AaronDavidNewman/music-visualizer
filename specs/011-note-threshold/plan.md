# Implementation Plan: Note Threshold

**Branch**: `011-note-threshold` (no git branch created; spec directory name only) | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/011-note-threshold/spec.md`

## Summary

A new **Threshold** setting hides faint notes. It is a number from 0 to 10 (percent of the **largest note value anywhere in the file**, measured after smoothing). 0 is off and is the default. For every frame, a note whose smoothed value is **strictly below** `threshold / 100 × (largest smoothed note value)` gets a black tile (RGB 0, 0, 0, which is HSV 0, 0, 0). All other tiles are drawn exactly as before. The comparison uses the unrounded smoothed value before the Saturation root, so no other setting changes which notes are hidden, and a hidden note still counts as a related note when other tiles' hues are worked out (the spec's literal reading, FR-007).

Technically: `frame_rendering.py` gains `MIN/MAX/DEFAULT_THRESHOLD`, a pure `hidden_notes(smoothed, threshold)` that returns a boolean `(frames, 84)` mask, and a `hidden` argument on `tile_colors` that blacks the masked tiles after the colors are worked out. `write_frames` computes the smoothed note values once, uses them both for the gray levels (as now) and for the mask, and passes each frame's row to `tile_colors`. `create_job` gains an optional `threshold` form field with the usual strict validation and echoes it. The frontend adds a slider (the Smoothing pattern) with a readout, an explanation, validation and a summary line. No new dependency and no change to the analysis, energy, hue or level code.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: numpy, Pillow, FastAPI; Vue, vitest. No new packages.

**Storage**: N/A. Same temp directories; PNGs stay indexed-colour (a frame has at most 84 flat colours; hidden tiles share one black).

**Testing**: pytest: `hidden_notes` on hand-worked values (strictly below hides, equal shows, 0 hides nothing, the largest value is never hidden, a silent input hides nothing and does not fail, the reference is the whole file's smoothed maximum and not each frame's); `tile_colors` with a mask (hidden tiles exactly `(0, 0, 0)`, the others identical to the call without it, hues untouched); `write_frames` (threshold 0 gives byte-identical files to no argument; a loud and a faint note at known values; smoothing before comparison with a note that fades; Saturation root, saturation/brightness/hue steps leave the hidden set unchanged and hidden tiles black; hidden notes still shift neighbors' hues; frame brightness untouched; only black or unchanged tiles appear at every threshold 1 to 10); the API field (valid, missing, empty, negative, above 10, text, `nan`, `inf`, decimals) with the refusal message, and the response. vitest: threshold constants, validation, readout text, explanation text, and a server-side render of the form showing the slider.

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: Time to create the same frames no more than 10% longer than before (SC-008). The mask is one vectorized comparison over the whole `(frames, 88)` array; applying it is one boolean assignment per frame.

**Constraints**: Deterministic output; image size, layout, frame count, timing, and every shown tile unchanged; with the threshold at 0 the output must be byte-for-byte what it is today; results already created are unchanged.

**Scale/Scope**: Edits to `frame_rendering.py` and `jobs.py` (no new backend module), one new test module plus edits to `test_frame_rendering.py` and one existing API-keys test, frontend edits to six files (`validation.ts`, `help.ts`, `api.ts`, `SettingsForm.vue`, `App.vue`, plus their tests), and documentation.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. The plan adds no module and no dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/011-note-threshold/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── threshold-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── services/frame_rendering.py   # MIN/MAX/DEFAULT_THRESHOLD, hidden_notes(), tile_colors(hidden=), write_frames(threshold=)
│   └── routers/jobs.py               # optional "threshold" form field, _parse_threshold(), "threshold" in the response
└── tests/
    ├── test_frame_rendering.py       # hidden_notes, tile_colors mask, write_frames behavior
    ├── test_threshold_api.py         # NEW: the field's validation, response, and frames through the API
    └── test_energy_api.py            # expected response keys gain "threshold"

frontend/src/
├── api.ts                            # JobSettings.threshold, JobResult.threshold, form field
├── App.vue                           # "Threshold: Off | n%" summary line
├── components/
│   ├── SettingsForm.vue              # Threshold slider with readout and info popover
│   └── SettingsForm.test.ts          # the slider is rendered, starts at Off, is disabled while busy
└── utilities/
    ├── validation.ts                 # THRESHOLD_RANGE, DEFAULT_THRESHOLD, validateThreshold, formatThreshold
    ├── validation.test.ts
    ├── help.ts                       # thresholdHelp
    └── help.test.ts

README.md                             # settings and API description: the threshold
```

**Structure Decision**: The threshold is a drawing decision that needs the smoothed note values, which exist only inside `write_frames`, next to the code that already turns them into gray levels, so it lives in `frame_rendering.py` beside `value_sequence` and `hue_sequence`, as a small pure function (`hidden_notes`) plus an optional argument on `tile_colors`. This is the smallest change: every new argument is optional, so existing callers and tests are unaffected. The API tests go in a new module (as in feature 010) to keep the shared `post` helper unchanged. In the frontend the field follows the Smoothing slider exactly.

## Complexity Tracking

No constitution violations. Nothing to justify.
