# Implementation Plan: Circles Paint

**Branch**: `022-circles-paint` (no git branch created; spec directory name only) | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/022-circles-paint/spec.md`

## Summary

A fifth image type, `circles_paint` (label "Circles paint"), makes the same circles as `circles` but **without a memory**: the first frame is the background with its circles painted on it, and every later frame is **a copy of the previous frame's picture with this frame's circles painted on top**, solid, never fading or clearing (the clarifications). Which circles are put down, where, in which color and radius is not touched: `plan_circles` (ranks, movement, stay-in-place, wrap, colors, scaling to the 600 × 400 frame) is reused as it is, and the new writer only draws what it yields in `added`. Each circle is painted through its own small **coverage mask** (the disc drawn on a patch four times larger and averaged down, as the smooth edges of Circles are) composited onto the canvas with Pillow's `paste`, so the interior is exactly the circle's color and the edge mixes it with what is under it.

Work by area:

- **Backend**: a new module `app/services/circles_paint.py` (`write_paint_frames`: the canvas, the per-circle masks and the saving on a few threads); `circles.plan_circles` accepts `memory=None` (no buffer kept, `remembered` is empty); `IMAGE_TYPES` gains `circles_paint`; `write_frames` gets a branch that returns before the grid pipeline; the router needs no new field (the circle fields are the same and `circle_memory` is validated and ignored, as the settings that a type does not use are today).
- **Frontend**: `IMAGE_TYPES` gains the fifth choice; the group model gets the group `circles_paint` ("Circles paint": Movement, Radius, Resize by volume, Notes, no Memory); `gridSettingsApply` and the summary treat both circle types as circles, with the Memory line for `circles` only; the Image type help text describes the new type; tests.
- **Tests**: the plan reused (a `memory=None` plan equals the plan with a memory in what it adds), the canvas (every pixel outside this frame's circles equals the previous frame's, the first frame, silent frames copy the previous one, determinism), the circles (solid interior of exactly the color, a smooth mix on the edge, strongest on top, clipped and not wrapped at the edges, the scaling to 600 × 400, equal to Circles' newest circles in place, color and radius), no memory (the first circles survive more circles than Circles' memory could hold), the API, the page's groups and summary; the four other types stay equal to the reference hashes.
- **Docs**: README (the image types and a Circles paint paragraph), amendment notes on the circles documents (019, 020) that list four image types.

A prototype (research.md) measured 1,800 frames at 600 × 400: painting takes 4.4 s at the default settings and 2.5 s at the largest (Circles takes 17 s and, with the resize on, 176 s on the same music), and its files take 78 to 332 MB (Circles 113 and 130 MB).

Worth knowing: the canvas never clears, so on a long file it becomes dense layers of the latest circles (stated in the spec as expected); the files are larger than Circles' at the default settings because a canvas that keeps its detail compresses less (332 against 113 MB for a 60 second job), which the spec's "same order" allows. **A thing found on the way, outside this feature**: Circles with Resize by volume on at the largest settings took 176 s on random-but-music-like data, above the two minutes that feature 021 set as its limit for the costliest settings (that limit was checked with the resize off); this is reported, not changed here.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: numpy, Pillow (`Image.paste` with a mask, `ImageDraw`), FastAPI; Vue, vitest. No new dependency.

**Storage**: Same temp directories and file names; frames are 600 × 400 RGB PNGs. The canvas lives in memory for the length of one job (one 720 KB image).

**Testing**: pytest and vitest. New: `test_circles_paint.py` (plan reuse, canvas, circles, API), image-type lists in the existing tests that derive from `IMAGE_TYPES`; vitest: validation, groups, the form for the new type, the summary, the help text.

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: 1,800 frames within one minute at the default and the largest settings and no slower than Circles (SC-006); measured 4.4 s and 2.5 s.

**Constraints**: Deterministic; 600 × 400, same count, names and timing as the other types; the four other image types byte-identical to before (the four reference hashes); the circles of Circles paint equal to the newest circles of Circles in place, color and radius.

**Scale/Scope**: One new backend module (~100 lines), a few lines in `circles.py`, `frame_rendering.py` and `image_types.py`; frontend edits to five files plus tests; README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/022-circles-paint/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── circles-paint.md
└── tasks.md             # /speckit-tasks (not created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/services/
│   ├── circles_paint.py        # NEW: write_paint_frames (the canvas and the painting)
│   ├── circles.py              # plan_circles(memory=None): no buffer kept
│   ├── frame_rendering.py      # a branch for circles_paint
│   └── image_types.py          # IMAGE_TYPES gains circles_paint (+ its docstring)
└── tests/
    └── test_circles_paint.py   # NEW (+ the existing tests that list the image types)

frontend/
└── src/
    ├── utilities/validation.ts # the fifth type, isCirclesType, gridSettingsApply
    ├── utilities/groups.ts     # the group circles_paint
    ├── utilities/help.ts       # the Image type help
    ├── App.vue                 # the summary: Memory for circles only
    └── components/SettingsForm.vue  # TYPE_GROUP_IDS (+ tests of each)
README.md
```

**Structure Decision**: Existing web-application layout. The painter is its own module so that `circles.py` stays the home of the plan and the memory version; the plan is shared.

## Complexity Tracking

> No Constitution Check violations to justify.
