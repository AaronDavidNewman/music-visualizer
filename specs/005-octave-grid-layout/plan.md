# Implementation Plan: Octave Grid Layout

**Branch**: `005-octave-grid-layout` | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-octave-grid-layout/spec.md`

## Summary

Frame images change from an 11 × 8 grid of 20-pixel squares to a 12 × 7 grid of 21 × 24 pixel rectangles: 252 × 168 pixels, exactly 3:2. Row *r* holds notes 12*r* to 12*r* + 11, so each row is an octave, each column is one note name, and the tile directly below a note is the same note one octave higher (double the frequency). Only the first 84 notes are drawn, 55 Hz up to about 6645 Hz; the four highest are left out of the picture but still analyzed. Everything upstream of drawing is untouched: analysis, window spacing, frame averaging, 0–255 scaling and the brightness root. The change is confined to `render_frame` and its constants, the frame display's CSS, the tests that read pixel positions, and the docs that describe the image.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 with Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: numpy, Pillow; Vue, Vite. No new packages.

**Storage**: N/A. Same temp directories as before. Images already stored are not touched.

**Testing**: pytest (layout geometry, note placement, octave rule, omitted notes, image size, API pixel positions). The frontend change is one CSS rule, checked by typecheck, build and the manual quickstart.

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: Frame count, window count and total time unchanged within 10% (SC-005). The drawing step does the same amount of work at about the same image size (252 × 168 against 220 × 160 pixels).

**Constraints**: Exactly 3:2 with whole-pixel tiles; tile width is 87.5% of tile height; 84 notes shown; gray levels per note identical to the previous layout.

**Scale/Scope**: One service function and its constants, one CSS rule, test updates, doc updates.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. The change edits one existing function and adds no modules. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/005-octave-grid-layout/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── image-layout.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/services/frame_rendering.py   # new grid constants, render_frame draws 12 x 7 tiles of 21 x 24
└── tests/
    ├── test_frame_rendering.py       # layout tests; existing 11 x 8 expectations updated
    └── test_jobs_api.py              # frame_levels reads the new grid; image size 252 x 168

frontend/src/
└── components/FramePlayer.vue        # .frame gets aspect-ratio: 3 / 2

README.md and specs/002-audio-frames-ui/*   # image description updated (superseded notes)
```

**Structure Decision**: No new files in the source tree. The geometry lives next to the existing drawing code in `frame_rendering.py`, and the aspect ratio appears once in the stylesheet. The tests that previously located a note by `row = n // 11` now share one helper that finds a tile by `n // 12` and `n % 12`.

## Complexity Tracking

No constitution violations. Nothing to justify.
