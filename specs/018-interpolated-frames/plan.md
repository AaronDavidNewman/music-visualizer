# Implementation Plan: Interpolated Frames

> **Amendment 2026-10-13**: the interpolation function was removed after the user saw the rendered frames ("The others don't really work"). Only `blend` is made: there is no function dropdown, no `interpolate_function` field and no response key for it, and no `soft_light`, `hard_light`, `overlay`, `screen` or `subtract` code. A request that still sends `interpolate_function` is accepted and the field is ignored. [spec.md](spec.md), [data-model.md](data-model.md) and [contracts/interpolate-api.md](contracts/interpolate-api.md) describe the result; this document is kept as it was written, so the passages about the five other functions, option B and the function dropdown describe the first version.

**Branch**: `018-interpolated-frames` (no git branch created; spec directory name only) | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/018-interpolated-frames/spec.md`

## Summary

A new setting, **interpolate** (a whole number from 1 to 5, default 1), draws only every n-th frame and makes the frames in between from their two drawn neighbors with the Pillow image library. The drawn frames are the frames numbered (from 0) `0, n, 2n, …` and always the last frame, drawn exactly as they are at interpolate 1 (so their files are byte-identical). Each in-between frame at position k of a gap of length g (g = n, or less at the end of the file) has the weight `w = k / g`: with **blend** (the default) it is `Image.blend(earlier, later, w)`; with `soft_light`, `hard_light`, `overlay`, `screen` or `subtract` (the user's answer, option B) it is `ImageChops.<function>(earlier, Image.blend(earlier, later, w))`. The frame count, file names, size and timing do not change. A second setting, the **interpolation function**, chooses among the six (default `blend`).

Work by area:

- **Backend**: a new module `app/services/frame_interpolation.py` (the two settings and their checks, `key_frames`, and `write_interpolated_frames`, which reads the drawn PNG files and writes the in-between ones on a small thread pool); `write_frames` gains `interpolate` and `interpolate_function`, draws only the drawn frames (each writer takes the list of frames to draw; `write_contour_frames` gets an `indices` argument) and then calls the new pass; the router gets two fields and two response keys.
- **Frontend**: a slider with a readout (`5 (one frame in 5 drawn)`), a dropdown of the six functions (disabled at 1), help texts, a summary line and the fields in `api.ts`, with their tests.
- **Tests**: the checks and the numbering; the in-between frames against Pillow's functions and against a numpy weighted mix for blend; drawn frames byte-identical to interpolate 1 for every image type and function; the count of pictures drawn (spies on the writers); the shorter last gap; the API; the page. At interpolate 1 the output must equal the four reference hashes.
- **Docs**: README.

A prototype (research.md) measured the costs: an in-between frame costs 0.6 to 0.9 ms with Pillow, drawing a frame costs 0.55 ms for Tiles and Blended tiles and 9.4 ms for the contour. So interpolation speeds up the contour by about 3 to 5 times (the picture work of 300 frames: 2.8 s down to 0.6 to 0.8 s) and does nothing for the tile pictures, which already cost as little to draw as to blend; the spec was reworded to say so (SC-005). Also worth knowing: with option B and a function other than blend, the animation steps back to the plain drawn frame at the next drawn frame (the spec's Edge Cases); the in-between frames are RGB PNGs while drawn frames keep their kind.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing numpy, Pillow 12.3 (`Image.blend`, `ImageChops`), matplotlib, FastAPI; Vue, vitest. No new dependency.

**Storage**: N/A. Same temp directories and file names; drawn frames are written exactly as before, in-between frames are RGB PNGs.

**Testing**: pytest and vitest. New: `test_frame_interpolation.py` (checks, numbering, the pass on hand-made files), `test_interpolation_rendering.py` (`write_frames` for the three image types and the six functions), `test_interpolation_api.py`; the existing exact-response-key tests gain the two keys. vitest: ranges, validation, readouts, help, rendered controls, the dropdown's disabled rule, summary. The colormap-list-tolerant helpers are used; no test states a number of contour levels.

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: A 300-frame contour job at interpolate 5 takes at most half the time of the same job at interpolate 1; Tiles and Blended tiles jobs take no more than 25% longer at any interpolate value (SC-005).

**Constraints**: At interpolate 1 the output is byte-identical to before (four reference hashes in quickstart.md); the drawn frames at any interpolate value are byte-identical to those of interpolate 1; deterministic output; the same frame count, file names, size and timing at every interpolate value; all interpolation arithmetic is Pillow's.

**Scale/Scope**: One new backend module (~120 lines), small changes in `frame_rendering.py`, `contour.py` and `jobs.py`; frontend edits to five files plus tests; README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency (Pillow is already used). Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/018-interpolated-frames/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── interpolate-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── services/
│   │   ├── frame_interpolation.py   # NEW: settings, key_frames(), write_interpolated_frames() (Pillow, thread pool)
│   │   ├── frame_rendering.py       # write_frames(interpolate=, interpolate_function=): draw only the drawn frames, then interpolate
│   │   └── contour.py               # write_contour_frames(..., indices=None)
│   └── routers/jobs.py              # + two fields, parsers, response keys
└── tests/
    ├── test_frame_interpolation.py  # NEW
    ├── test_interpolation_rendering.py # NEW
    ├── test_interpolation_api.py    # NEW
    └── test_note_count_api.py, test_resolution_api.py, test_colormap_api.py, test_contour_api.py   # exact response keys

frontend/src/
├── api.ts                           # + interpolate, interpolateFunction (settings, result, form fields)
├── App.vue                          # + summary line
├── components/
│   ├── SettingsForm.vue             # + Interpolate slider and function dropdown after the Resolution
│   └── SettingsForm.test.ts
└── utilities/
    ├── validation.ts                # + ranges, function list, validators, readouts
    ├── validation.test.ts
    ├── help.ts                      # + interpolateHelp, interpolateFunctionHelp
    └── help.test.ts

README.md                            # Interpolate documented
```

**Structure Decision**: The in-between frames are made by a separate pass over the written files, so the three writers only learn "which frames to draw" and nothing else about interpolation; the pass uses nothing but Pillow and the file names, so it is the same for every image type. Reading the drawn files again costs about 3 ms a frame, hidden by the thread pool, and avoids coupling the writers to a hand-over of their images.

## Complexity Tracking

No constitution violations. The thread pool in the interpolation pass is the same device as the blended writer's, for the same reason (Pillow releases the interpreter lock).
