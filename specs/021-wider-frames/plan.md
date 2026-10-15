# Implementation Plan: Wider Frames (600 Pixels)

**Branch**: `021-wider-frames` (no git branch created; spec directory name only) | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/021-wider-frames/spec.md`

## Summary

Every frame of every image type becomes **600 × 400 pixels** (3:2, as the 252 × 168 of today) and is **drawn at that size**, not enlarged. The frame geometry is already one pair of constants (`IMAGE_WIDTH`, `IMAGE_HEIGHT` in `frame_rendering.py`) that is passed down to the contour, blended and circles writers, and the tile edges are already computed as "the nearest whole pixels to an even split", so the change in the grid types is mostly the two constants (columns become exactly 50 px, rows 57 or 58 px) and the removal of the 21 × 24 tile constants. The **Circles** work (clarification, option A): Movement and Radius keep their numbers and are measured against a **252-pixel reference frame**, so the circle writer derives `scale = width / 252` and applies it to the step length, the radius (and with it the resize factor) while the start in the middle and the wrap-around already follow the width and height. The **player** shows the frame at up to its full 600 px (no more stretching of a small picture, no pixelated scaling) and scales down on a narrow screen.

Work by area:

- **Backend**: `frame_rendering.py` (the two constants, the reference size and the scale, the removed tile constants and asserts, docstrings); `circles.py` (`REFERENCE_WIDTH = 252`, `scale` in `plan_circles` and `write_circle_frames`, defaults unchanged so a 252-wide call is exactly what it was); `image_types.py` and `contour.py` only their comments (their code already takes `width` and `height`).
- **Frontend**: `FramePlayer.vue` (frame and controls at most 600 px wide, `image-rendering` back to the browser's smooth scaling, the comment); the help texts of Movement and Radius say that they are measured against a 252-pixel-wide frame; their tests.
- **Tests**: one shared place for the frame size (`tests/frame_size.py`, plus one test that states 600 × 400 literally); the ~50 uses of 252 and 168 and of the 21 × 24 tiles in 16 test files follow it; new tests for the size of every frame of every type, resolution (1 to 5) and interpolate (1 to 5), the tile columns and rows within one pixel and the tile colors equal to the old ones, the new frame equal to the old one at the same geometry after reducing it (contour, blended), and the circles scaling (positions, radius, wrap, resize) in reference pixels.
- **Docs**: README (the sizes: 252 × 168, 12 × 7 tiles of 21 × 24, the 10-pixel feather, the circles and player paragraphs), amendment notes on the earlier specs that state the old size, and this feature's contract.

A prototype (research.md) timed 1,800-frame jobs at both sizes: tiles 0.7 to 7.1 s, blended 0.9 to 8.5 s, contour 4 to 34 s, circles 3 to 19 s at 600 × 400, and the files take 1.3 to 3.6 times the room. Everything is inside the spec's limits (one minute at the defaults, two at the costliest settings, 4 times the room); the closest to a limit is the room taken by blended frames (3.6 of 4).

Worth knowing: the frames are **not byte-identical** to before for any type (they are a different size); what must be equal is the content: the tile colors at the tile centers, and the positions and colors of everything else. The look in a browser (the 600 px frame in the player) cannot be seen with the tools of this project; see the quickstart.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: numpy, Pillow, matplotlib (contour), FastAPI; Vue, vitest. No new dependency.

**Storage**: Same temp directories and file names; frames are PNGs (indexed colour for the original tile grid, true colour otherwise), about 2.4 times as many pixels each.

**Testing**: pytest (sizes, geometry, content equivalence, circles scaling) and vitest (the player's styles, the help texts).

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: A 60 second, 1,800 frame job within one minute at the default settings and within two minutes at the costliest settings, for every image type (SC-005); measured at most about 34 s.

**Constraints**: Every frame exactly 600 × 400; the same count, names, order and timing; the same colors and positions in proportion; circles' settings and request fields unchanged; room at most 4 times the old (SC-006).

**Scale/Scope**: Two constants and their derived values in `frame_rendering.py`, a scale in `circles.py`, a few comments; the player's CSS; help texts; tests (16 files touched by the size, 3 or 4 new); README and amendment notes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/021-wider-frames/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── frame-size.md
└── tasks.md             # /speckit-tasks (not created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/services/
│   ├── frame_rendering.py   # IMAGE_WIDTH/HEIGHT 600/400, the reference size and the scale, no 21 x 24 tile constants
│   ├── circles.py           # REFERENCE_WIDTH and the scale applied to the step and the radius
│   ├── image_types.py       # comments only
│   └── contour.py           # comments only
└── tests/
    ├── frame_size.py        # NEW: the size the tests expect, imported by the tests that need it
    ├── test_frame_size.py   # NEW: 600 x 400 literally; every type, resolution and interpolate; tile columns and rows; old/new equivalence
    └── test_*.py            # the ~50 uses of 252, 168 and 21 x 24 follow the shared size; circles tests in reference pixels

frontend/
└── src/
    ├── components/FramePlayer.vue    # at most 600 px wide, smooth scaling, 3:2
    └── utilities/help.ts             # Movement and Radius measured against a 252-pixel-wide frame (+ tests)
README.md
```

**Structure Decision**: Existing web-application layout. The size stays defined in one place (`frame_rendering.py`); everything else reads it or is given it.

## Complexity Tracking

> No Constitution Check violations to justify.
