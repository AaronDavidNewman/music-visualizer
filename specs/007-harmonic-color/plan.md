# Implementation Plan: Harmonic Color

**Branch**: `007-harmonic-color` | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-harmonic-color/spec.md`

## Summary

Frame images change from gray tiles to colored tiles. Each tile's HSV **value** is the final gray level it has today (after scaling, the brightness root and smoothing, with 255 meaning 100%), its **saturation** is fixed at 50%, and its **hue** starts at 180° and is moved by the final gray levels of related notes: the notes at offsets `RELATED_DOWN = (4, 5, 7)` pull it down and the notes at offsets `RELATED_UP = (3, 6, 8, 11)` push it up. Their brightness (0 to 1) is **added, not averaged**, and the hue is `clip(180° + 180° × (U − D), 0°, 360°)`, with partners outside the 88-note series counting as silent. (The first version averaged four-note groups and gave no red on real music; see research Decision 1.) The HSV values are converted to RGB with Python's `colorsys`, as requested. The change is confined to the drawing step in `frame_rendering.py`: the 252 × 168 octave layout, frame counts, timing, analysis, smoothing and settings are untouched, and the image becomes a color PNG (saved as an indexed-colour PNG of the tile colors, which decodes to exactly the RGB values; see research Decision 9). No frontend code changes are needed, since the page already displays whatever PNG the server returns.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`); the frontend is unchanged

**Primary Dependencies**: Existing only: numpy, Pillow, and the standard library's `colorsys`. No new packages.

**Storage**: N/A. Same temp directories. PNGs become color: indexed-colour files whose palette is the frame's 84 tile colors (about 9.8 MB for the sample submission, against 5.6 MB when gray).

**Testing**: pytest: the hue formula against an independent reference, the worked colors from the spec, the ends of the range, the four undrawn notes as partners, wrap-around at 0°/360°, brightest-channel equality with the old gray level, silent files, layout unchanged, determinism, and the API tests updated to read RGB images.

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: Time to create the same frames no more than 25% longer than before (SC-007). Measured while planning: `colorsys` for 10,224 frames × 84 tiles costs about 0.4 s of a ~6 s submission. Measured while implementing: saving 24-bit RGB PNGs missed the budget (+61% on the drawing step), so frames are saved as indexed-colour PNGs, which brought the step to within noise of the old gray version (see research Decision 9).

**Constraints**: Saturation fixed at 50%; no gray-scale option; image size, layout and frame count unchanged; related-note groups fixed.

**Scale/Scope**: One service module changed (new helpers, `render_frame` returns RGB), tests updated and added, docs updated. No frontend code.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. The change adds helper functions to an existing module. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/007-harmonic-color/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── image-color.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/services/frame_rendering.py   # SATURATION, DEFAULT_HUE, RELATED_DOWN/UP, tile_hues, tile_colors; render_frame draws RGB
└── tests/
    ├── test_frame_rendering.py       # layout/boost tests read the max channel; new color tests
    └── test_jobs_api.py              # image helpers read RGB; mode "RGB"

README.md and specs/002..006 docs     # image description: gray tiles -> colored tiles
```

**Structure Decision**: No new files in the source tree. The color rule is two small functions beside `render_frame` (`tile_hues` computes the hue of each of the 84 tiles from the 88 final gray levels, `tile_colors` turns hue, saturation and value into RGB), so the drawing step reads in order: boost the levels, find each tile's hue, convert, draw. The frontend needs no change because the image URL, size and proportions are the same.

## Complexity Tracking

No constitution violations. Nothing to justify.
