# Implementation Plan: Interpolated Resolution

**Branch**: `016-interpolated-resolution` (no git branch created; spec directory name only) | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/016-interpolated-resolution/spec.md`

## Summary

A new setting, **resolution** (a whole number from 1 to 5, default 1), makes the grid that a frame is drawn from finer. After smoothing, the 7 × 12 grid of each frame's 84 drawn note values is interpolated to 7r × 12r values with `np.linspace` positions and `np.interp` (every row, then every column), so the corners stay the original values and no value goes outside the original range. The Threshold and the colors are then worked out on the interpolated values, and the picture is made by the existing image type: more and smaller tiles for Tiles and Blended tiles, a finer contour for Contour. The picture keeps its size, 252 × 168 pixels.

Work by area:

- **Backend**: a new module `app/services/resolution.py` (the setting, its check, `interpolate_grid`); `write_frames` gains `resolution` and interpolates between smoothing and coloring; `colorize` gets an optional `peak` (the interpolated array no longer holds the four undrawn notes); a `hidden_below` helper for the threshold on any grid; the Tiles writer is generalized to any grid (tile edges at the nearest pixel, a palette PNG up to 256 tiles, true-color above); the blender is generalized to the same tile edges, with the existing `make_blender` kept as a wrapper; the router gets the `resolution` field and response key. Contour needs no change in `contour.py`.
- **Frontend**: a slider with a readout (`3× (36 × 21)`), a help text, a summary line and the field in `api.ts`, with their tests.
- **Tests**: interpolation properties and equality with `np.interp`; the tile grid read back from pictures; the three image types at every resolution; threshold, colormap, silent file; the API; the page. At resolution 1 the output must equal the reference hashes recorded before the change.
- **Docs**: README.

A prototype (research.md) measured the interpolation at 0.2 s for 1,800 frames at 5×, Tiles at 5× as a true-color PNG at 0.98 ms a frame (2.4 KB), and the contour drawing at about 8.5 ms a frame whatever the grid size, so a 300-frame job at 5× takes a few seconds against the minute allowed.

Points worth knowing: at 5× the tiles are 4 or 5 pixels wide, so a Blended picture's fade (25% of a tile at most) is about one pixel at each edge; above 1× Tiles frames can no longer be palette PNGs (more than 256 colors), so they are larger than today's (about 2.4 KB against 1 KB).

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing numpy, Pillow, matplotlib, FastAPI; Vue, vitest. No new dependency.

**Storage**: N/A. Same temp directories and file names; Tiles frames are palette PNGs at 1× and true-color PNGs above, Blended frames true-color, Contour frames as written by matplotlib.

**Testing**: pytest and vitest. New: `test_resolution.py` (check function, interpolation), tests of the three image types at every resolution in `test_frame_rendering.py` (or a new module), `test_resolution_api.py`; changes to the existing blender and colorize tests only where signatures grow (all additions are optional arguments). vitest: range, validation, readout, help, rendered slider, summary. The colormap-list-tolerant helpers are used; no test states a number of contour levels.

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: A 300-frame job at resolution 5 within one minute for every image type (SC-005); the 1× jobs are not slower (tiles about 1 s and blended about 1.3 s for the 60 second file, contour about 25 s).

**Constraints**: At resolution 1 the output is byte-identical to before for every image type (reference hashes in quickstart.md); deterministic output; the same size, frame count, timing and file names at every resolution.

**Scale/Scope**: One new backend module (~60 lines), changes in `frame_rendering.py`, `image_types.py`, `colormaps.py` and `jobs.py`; frontend edits to five files plus tests; README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/016-interpolated-resolution/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── resolution-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── services/
│   │   ├── resolution.py            # NEW: MIN/MAX/DEFAULT_RESOLUTION, check_resolution(), interpolate_grid()
│   │   ├── frame_rendering.py       # write_frames(resolution=): interpolate, hidden_below(), grid tile writer
│   │   ├── image_types.py           # make_grid_blender() on rounded tile edges; make_blender() kept as a wrapper
│   │   └── colormaps.py             # colorize(..., peak=None)
│   └── routers/jobs.py              # + resolution field, parser, response key
└── tests/
    ├── test_resolution.py           # NEW
    ├── test_resolution_api.py       # NEW
    ├── test_frame_rendering.py      # + resolution in the three image types
    └── test_image_types.py          # + the generalized blender (uniform edges equal the old result)

frontend/src/
├── api.ts                           # + resolution (settings, result, form field)
├── App.vue                          # + summary line
├── components/
│   ├── SettingsForm.vue             # + Resolution slider
│   └── SettingsForm.test.ts
└── utilities/
    ├── validation.ts                # + RESOLUTION_RANGE, DEFAULT_RESOLUTION, validateResolution, formatResolution
    ├── validation.test.ts
    ├── help.ts                      # + resolutionHelp
    └── help.test.ts

README.md                            # Resolution documented
```

**Structure Decision**: The setting and the interpolation live in their own pure-numpy module with the grid shape passed in, like `image_types.py` and `contour.py`, so the rest of the backend stays unaware of the note grid's numbers; `frame_rendering.py` keeps the shared steps and chooses the writer. The blender and the tile writer are generalized with one tile-edge rule that reduces exactly to today's at 1×, instead of a second code path for finer grids, so there is one thing to keep correct.

## Complexity Tracking

No constitution violations. The one place that looks heavier than necessary, rewriting the blender's axis weights on tile edges, is what keeps a single implementation for every grid size; the 1× output is held identical by the reference hashes and by the existing blender tests, which stay unchanged.
