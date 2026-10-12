# Implementation Plan: Contour Image Type

**Branch**: `015-contour-image-type` (no git branch created; spec directory name only) | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/015-contour-image-type/spec.md`

## Summary

A third image type, `contour`, joins `tiles` and `blended`. A contour frame is a filled contour picture, drawn with matplotlib's `contourf`, of the 7 × 12 grid of the frame's smoothed note values (the 84 drawn notes, hidden notes as 0). The coordinates are `np.linspace(0, top, 12)` and `np.linspace(0, top, 7)` with `top` the largest value of the current frame, recomputed for every frame; the color scale is fixed from 0 to `peak`, the largest smoothed value in the whole file, with `vmin=0, vmax=peak` so a value has the same color in every frame; the contour **levels are chosen by matplotlib** (no `levels` argument, nothing hard-coded). The colormap is the job's selected colormap, the axis decorations are off (`set_axis_off`), and the PNG is saved with `pyplot.savefig` from a 2.52 × 1.68 inch, 100 dpi figure, which is exactly 252 × 168 pixels, like the other types.

The work is small and almost all of it is additive:

- **Backend**: a new module `app/services/contour.py` (the only code that touches `pyplot`; imported lazily, Agg backend, one figure per job, one process-wide lock because `pyplot` keeps global state) with `write_contour_frames`; `IMAGE_TYPES` gains `"contour"` (the router's validation, the refusal message and the response follow from the tuple); `write_frames` gets one branch for it. The tiles and blended paths are not edited.
- **Frontend**: one entry in the image type list, one sentence in the info text, and the Blend width slider's rule changes from "disabled for tiles" to "enabled only for blended".
- **Tests**: new tests for contour; the existing tests that hard-code the two image type names are changed to derive them from the list; the contour tests use the list-tolerant helpers from `backend/tests/colormap_names.py` and do not assume a number of levels.
- **Docs**: README.

A prototype (research.md) measured 8 ms per frame (300 frames in 2.5 s against the 60 s allowed by SC-007), an exact 252 × 168 opaque RGBA PNG with nothing white at the edges, byte-identical output on repetition, and that `contourf` draws a degenerate picture for a frame whose values are all equal, which is therefore drawn as one flat color instead (Decision 4).

One visible consequence worth knowing: the contour's color scale is **linear** from 0 to `peak` (as the request says), while the tiles use the square root of the strength. A quiet note is therefore closer to the start of the colormap in a contour than in the tiles (research Decision 2).

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing numpy, Pillow, FastAPI, matplotlib 3.10 (`matplotlib>=3.8`, already in `requirements.txt` since feature 014); Vue, vitest. No new dependency. `matplotlib.pyplot` is new for the application: it is imported lazily inside `contour.py` with `matplotlib.use("Agg")` first.

**Storage**: N/A. Same temp directories and file names (`frame_000000.png` and up); contour frames are RGBA PNGs written by matplotlib.

**Testing**: pytest and vitest. New: `test_contour.py` (size, opacity, edges, orientation, scale, locality of color, hidden notes equal to zeros, flat frames, determinism, performance bound, concurrent jobs, refusals) and an API module for the type (`image_type=contour` accepted and echoed, refusals with the three names, blend width accepted and ignored, other settings combined). Existing tests change in a few places (the two-name image type list and message). vitest: the list, label, validation message, the dropdown's options, the slider's disabled rule for each type, the help text.

**Target Platform**: Local developer machine, modern desktop browser; a server with no display (Agg).

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: A contour job of 300 frames within one minute (SC-007); measured 2.5 s for the drawing. Tiles and blended jobs are not slower (their code is untouched; matplotlib's drawing is not imported for them).

**Constraints**: Deterministic output; the same size, frame count, timing and file names as the other types; tiles and blended files byte-identical to before (reference hash in quickstart.md); matplotlib draws on a backend without a window; no number of contour levels and no colormap name is hard-coded in code or tests.

**Scale/Scope**: One new backend module (~80 lines), one branch in `write_frames`, a tuple entry; four small frontend edits; tests; README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/015-contour-image-type/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── image-type-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── services/
│   │   ├── contour.py               # NEW: write_contour_frames() (lazy matplotlib/pyplot, Agg, lock)
│   │   ├── image_types.py           # IMAGE_TYPES = ("tiles", "blended", "contour")
│   │   └── frame_rendering.py       # write_frames(): one new branch for "contour"
│   └── routers/jobs.py              # unchanged logic (validates by IMAGE_TYPES); docstring/help text mention
└── tests/
    ├── test_contour.py              # NEW
    ├── test_contour_api.py          # NEW
    ├── test_image_types.py          # the two-name list and message derived from the tuple
    ├── test_image_type_api.py       # likewise
    └── test_frame_rendering.py      # the refusal message derived from the tuple

frontend/src/
├── api.ts                           # comments: third value
├── components/
│   ├── SettingsForm.vue             # Blend width disabled unless imageType === 'blended'
│   └── SettingsForm.test.ts
└── utilities/
    ├── validation.ts                # IMAGE_TYPES + { value: "contour", label: "Contour" }
    ├── validation.test.ts
    ├── help.ts                      # imageTypeHelp: + Contour
    └── help.test.ts

README.md                            # Image type and Blend width paragraphs: the contour type
```

**Structure Decision**: The drawing is isolated in `contour.py`, which receives plain arrays (values, peak, colormap, directory, grid and image size) and knows nothing about the note analysis, like `image_types.py`; `frame_rendering.py` keeps the shared steps (smoothing, threshold, directory) and chooses the writer by the image type. matplotlib's `pyplot` is imported only there, only when a contour job runs, so server start and the other types pay nothing. A later fourth type is another module and another branch.

## Complexity Tracking

No constitution violations. The one thing that looks like extra machinery, a process-wide lock around the drawing, is there because `pyplot` has global state and FastAPI runs the endpoint on a thread pool (research Decision 1).
