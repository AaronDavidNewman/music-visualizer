# Implementation Plan: Colormap Colors

**Branch**: `014-colormap-colors` (no git branch created; spec directory name only) | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/014-colormap-colors/spec.md`

## Summary

The color of a tile stops being computed from hue, saturation and a per-frame brightness, and becomes **one lookup in a matplotlib colormap**. For a frame, the note values are smoothed as today (`smooth_frames`, with the smoothing and its window); the strength share of a note is its smoothed value divided by the largest smoothed value in the whole file (all 88 notes count); the colormap position is the **square root** of that share; the tile's color is the colormap's color at the position rounded to one of 256 steps. A note hidden by the threshold (`hidden_notes`, unchanged) is painted black afterwards. The 84 finished colors then go to the same two writers as now (flat palette PNG for `tiles`, true-color PNG for `blended`).

Because a tile's color now depends only on its own smoothed value and on the file's largest value, the "blinking" sources are gone: no hue shifted by related notes, no whole-frame brightness from the frame's energy, no per-frame normalization, and no level steps.

Offered colormaps: `summer`, `autumn`, `hot` (default) and `cool`, taken from matplotlib so that the colors are exactly matplotlib's. The settings **Brightness** (energy root), **Saturation** (brightness root), **Hue steps**, **Saturation steps** and **Brightness steps** are removed from the page, the server and the response; a request that still sends them is accepted and the values are ignored (the router simply no longer declares them). A new optional form field `colormap` is added and echoed.

Technically this is mostly a **removal**. A new module `colormaps.py` holds the four names, their check, a cached 256-entry lookup table per name (read from `matplotlib.colormaps` the first time it is needed) and the strength-to-color function. `frame_rendering.py` loses the hue, boost, value-sequence, tile-color and render functions and the HSV constants, keeping frame counting, window-to-frame averaging, smoothing, the threshold, the palette writer, the blended writer and a much shorter `write_frames`. `energy.py` and `color_levels.py` become unused and are deleted together with the tests that only covered retired behavior. `create_job` loses five fields and gains one. The frontend loses five controls (and their validation, texts, summary lines and tests) and gains a Colormap dropdown. matplotlib is added to `requirements.txt` and installed into the backend virtual environment (it was not installed; the package index is reachable and a dry run resolves matplotlib 3.10 with seven small dependencies).

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing numpy, scipy, Pillow, FastAPI; Vue, vitest. **New: matplotlib** (`matplotlib>=3.8` in `backend/requirements.txt`; installed version at planning time resolves to 3.10.9), imported lazily by `colormaps.py` so that startup and tests that do not draw pay nothing.

**Storage**: N/A. Same temp directories and file names; tiles frames are still palette PNGs and blended frames true-color PNGs.

**Testing**: pytest. New: a module for the colormaps (the cached table equals matplotlib's own 8-bit table for every offered name, first and last colors, entries ordered, distinct for `hot` and `cool`; the strength-to-color function: same strength same color, the strongest note is the last color, no strength is the first color, monotone positions over a sweep of strengths, the square-root scale on hand-worked values, silent input, locality: changing other notes changes no other tile, steady input gives steady colors); `write_frames` (threshold hides to exactly black for every colormap, smoothing and window applied before the color, both image types give equal tile middles, determinism, bad arguments refused before writing); API tests for the `colormap` field (valid, missing, every refused kind, the message, response), removed fields accepted and ignored (frames identical with and without them), colors in served frames decoded back to positions with the lookup table. The existing tests are pruned and rewritten (research Decision 6). vitest: colormap list, validation, texts, rendered control, removed controls gone.

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: Frames for the `tiles` image type take no longer than before (SC-008). The color work becomes cheaper: no energy pass over the samples, no hue computation per frame, one table lookup over an `(frames, 84)` array. Blended frames keep their present cost.

**Constraints**: Deterministic output; image size, layout, frame count, timing and the note analysis unchanged; image types, blend width, smoothing, smoothing window and threshold behave as before on the new tile colors; results already created are unchanged.

**Scale/Scope**: One new backend module, large deletions in `frame_rendering.py` and `jobs.py`, two backend modules deleted (`energy.py`, `color_levels.py`) with five test modules deleted and two large ones pruned and rewritten, frontend edits to five files plus their tests, and the README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. One new dependency (matplotlib), asked for by the user by name. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/014-colormap-colors/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── colormap-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── requirements.txt                  # + matplotlib
├── app/
│   ├── services/
│   │   ├── colormaps.py              # NEW: COLORMAPS, DEFAULT_COLORMAP, check_colormap(), lookup_table(), colorize()
│   │   ├── frame_rendering.py        # SHRUNK: smoothing, threshold, averaging, writers; write_frames(colormap=, ...)
│   │   ├── energy.py                 # DELETED (no longer used)
│   │   └── color_levels.py           # DELETED (no longer used)
│   └── routers/jobs.py               # -5 fields (energy, brightness, hue/saturation/brightness steps), +colormap; response keys
└── tests/
    ├── test_colormaps.py             # NEW
    ├── test_colormap_api.py          # NEW
    ├── test_frame_rendering.py       # PRUNED and rewritten (colors, writers, threshold, image types)
    ├── test_jobs_api.py              # PRUNED and rewritten (the pipeline, decoded colors, remaining settings)
    ├── test_energy.py, test_energy_api.py, test_frame_brightness.py,
    │   test_color_levels.py, test_color_levels_api.py      # DELETED
    └── test_threshold_api.py, test_smoothing_window_api.py, test_image_type_api.py   # adapted (helpers, colors)

frontend/src/
├── api.ts                            # -5 settings/result fields, +colormap
├── App.vue                           # summary: -5 lines, +"Colormap: Hot"
├── components/
│   ├── SettingsForm.vue              # -5 controls, +Colormap dropdown
│   └── SettingsForm.test.ts
└── utilities/
    ├── validation.ts                 # -energy/brightness ranges and the step helpers, +COLORMAPS, validateColormap
    ├── validation.test.ts
    ├── help.ts                       # -4 help texts, +colormapHelp
    └── help.test.ts

README.md                             # the color description rewritten; removed settings gone; Colormap documented
```

**Structure Decision**: Everything about turning a strength into a color lives in `colormaps.py`, the one place that knows matplotlib, so the rest of the backend stays free of it and a future mapping function (the user expects more later) is another module beside it, chosen by the writer, not a change to `frame_rendering.py`. `frame_rendering.py` keeps what is independent of the color rule (frame counting, averaging, smoothing, the threshold mask, the PNG writers). Dead code is deleted rather than kept, because the retired rules (harmonic hue, frame energy, level steps) are replaced, not made optional, and keeping them would leave untested code reachable only by tests.

## Complexity Tracking

No constitution violations. Nothing to justify.
