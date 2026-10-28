# Implementation Plan: Concentric

**Branch**: `025-concentric-circles` (no git branch created; spec directory name only) | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/025-concentric-circles/spec.md`

## Summary

A sixth image type, `concentric` (label "Concentric"): **84 circles, one per drawn note, centered on the tiles of the 12 × 7 grid** of the 600 × 400 frame. A circle has a **step** from 1 to 12 (`step = max(1, ceil(12 × sqrt(value ÷ the frame's loudest value)))`, 1 for a silent frame) and is drawn as `step` **concentric rings** of radius `k / 12` of the full radius (25 px: half the cell width, so neighbours in a row touch). Ring `k` has the colormap's table entry at `rint((k − 1) / 11 × (0.5 + 0.5 × position) × 255)`, where `position` is the frame's position in the local energy peak (feature 024: from the local peaks measurement, read in the middle of the frame, 0 when no beat is known). The background is the colormap's middle color (row 128). Only the Local peaks settings (no checkbox: the beat always colors this type) and Data smoothing apply.

How it is drawn (research Decision 1): the geometry is the same in every frame, so it is **worked out once**: from a 4 × 4 supersample of each pixel, the pixel's cell, its main ring `a`, its second ring `b` (0 = outside the circle) and the weight of `b`. A frame is then **two table lookups and a blend**: a table of 84 × 13 colors (row 0 the background; row `k` the ring's color if the circle's step reaches `k`, else the background) is indexed by `cell × 13 + a` and `cell × 13 + b`. This reproduces the brute-force supersampled drawing exactly (maximum difference 0 on random steps and colors) and takes about 15 ms a frame including the PNG: **1,800 frames in about 9 seconds** on four threads.

Work by area:

- **Backend, drawing** (new `app/services/concentric.py`): constants (`RINGS = 12`), `ring_steps(values)`, `ring_colors(colormap, beat)` (the 12 colors of every frame), the cached geometry, and `write_concentric_frames(values, colormap, directory, beat, width, height)`.
- **Backend, wiring**: `IMAGE_TYPES` gains `concentric` (the refusal message lists six names); `write_frames` gets a branch that returns before the grid pipeline (every setting is still checked for every type; the ones that do not apply are ignored); `jobs.py` measures the beat for every Concentric job (and for Tiles and Blended tiles when the box is on, as before), whatever `beat_coloring` says for Concentric.
- **Frontend**: `IMAGE_TYPES` gains the sixth choice; `gridSettingsApply` is false for Concentric (so Threshold, Notes, Oversampling, Interpolate and Gaussian are neither shown nor summarised); a new group `concentric-peaks` titled "Local peaks" with Minimum distance and Prominence (no checkbox), shown after Image type for Concentric; the form renders the Local peaks group for either id and the checkbox only for Tiles and Blended tiles; the summary shows the two values for Concentric; the Image type help describes the new type; tests.
- **Tests**: the steps (the formula at exact ratios `k² / 144`, loudest 12, silent 1, never below 1, monotone, per frame), the ring colors (every colormap, positions 0, 0.5 and 1, `rint` of the formula), the geometry (centers, radius 25, neighbours touching, nothing outside a cell, ring radii), the pixels (a ring's flat color at its center-line, background between circles, a smaller circle equal to the first rings of a full one, no pixel changed outside its cell), the supersampled edge equal to a brute-force drawing, the whole `write_frames` and API paths (six image types, the ignored settings, the beat measured for every Concentric job and the settings checked first, smoothing applies, silent file, no beat, short file, mono equals stereo, determinism), the other five types unchanged (the four reference hashes), and the page (group, controls, no checkbox, summary, help).
- **Docs**: README, `quickstart.md`.

Worth knowing: at position 0 ring 12 is table row 128, the same color as the background (both the middle of the colormap), so a full circle at the bottom of the beat seems to end at ring 11 (row 116); this follows from the clarified colors and background and is in the spec as an edge case.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: numpy, Pillow (PNG saving), FastAPI, scipy (the measurement); Vue, vitest. No new dependency.

**Storage**: Same temp directories and file names; frames are 600 × 400 RGB PNGs (about 60 KB each in the prototype). The geometry (a few arrays of 240,000 entries) is cached in memory.

**Testing**: pytest (`test_concentric.py` for the drawing, `test_concentric_api.py` for the endpoint, the lists of image types in the existing tests) and vitest (validation, groups, SettingsForm, App, help).

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: 1,800 frames within 30 seconds (SC-007); measured about 9 s.

**Constraints**: Deterministic; 600 × 400 frames with the same count, names and timing as the other types; the five other image types byte-identical (the four reference hashes `6819990556fd4095`, `f32a99c59fcb87fc`, `92b3a27dee73e223`, `400cc93e1bfca03d`).

**Scale/Scope**: One new backend module (~150 lines), a few lines in `image_types.py`, `frame_rendering.py` and `jobs.py`; frontend edits to about seven files plus tests; README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/025-concentric-circles/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── concentric.md
└── tasks.md             # /speckit-tasks (not created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/services/
│   ├── concentric.py           # NEW: steps, ring colors, geometry, write_concentric_frames
│   ├── image_types.py          # IMAGE_TYPES gains concentric (+ its docstring)
│   └── frame_rendering.py      # a branch for concentric
├── app/routers/jobs.py         # the beat is measured for every concentric job
└── tests/
    ├── test_concentric.py      # NEW
    ├── test_concentric_api.py  # NEW
    └── (the existing tests that list the image types)

frontend/
└── src/
    ├── utilities/validation.ts  # the sixth type, gridSettingsApply, peak settings shown
    ├── utilities/groups.ts      # the group concentric-peaks and groupsFor
    ├── utilities/help.ts        # the Image type help
    ├── App.vue                  # summary lines
    └── components/SettingsForm.vue  # the Local peaks group for either id (+ tests of each)
README.md
```

**Structure Decision**: Existing web-application layout. The drawing is its own module, as the circles and the paint are, and knows nothing about audio: it takes the smoothed note values and one beat position per frame.

## Complexity Tracking

> No Constitution Check violations to justify.
