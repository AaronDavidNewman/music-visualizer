# Implementation Plan: Image Type (Blended Tiles)

**Branch**: `013-image-type-blended-tiles` (no git branch created; spec directory name only) | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/013-image-type-blended-tiles/spec.md`

## Summary

A job gets an **image type** (`tiles`, the default, or `blended`) and, for the blended type, a **blend width** (10 to 25 percent of the tile width, default 25). Everything that decides the 84 finished tile colors of a frame (analysis, smoothing and window, roots, level steps, threshold, hue, brightness) is unchanged. Only the last step differs: `tiles` writes the existing palette PNG exactly as now; `blended` turns the 12 × 7 grid of finished colors into a 252 × 168 true-color picture in which the colors of neighboring tiles are blended across each shared edge with a Gaussian feather (changed from a straight ramp on 2026-10-10 because that looked too blurry).

The blend is separable. For a pixel at distance `d` (measured from the pixel's center) from the nearest *inner* edge, with reach `B = blend width × 21 px`: if `d < B` the pixel's own tile gets the weight `F(d) = (Φ(4d / B) − Φ(−4)) / (1 − 2·Φ(−4))` (a Gaussian blur of the sharp edge with `σ = B / 4`, cut off at the reach and renormalised: 0.5 at the edge, exactly 1 at `B`) and the tile on the other side of the edge the rest; otherwise the pixel has its own tile's color exactly. Horizontal and vertical weights are computed separately and a pixel is the mix of up to four tiles with the products of the weights (so a corner is 25% each). The outer border of the picture has no inner edge and is not blended. The same `B` in pixels is used in both directions.

Technically: a new service module `image_types.py` holds the type names, the blend width limits, their validation and the pure function `blend_tile_colors` (two numpy passes: columns on the 7 tile rows, then rows; float32; rounded to 8 bits); it takes the tile geometry as arguments so it needs nothing from `frame_rendering.py`. `write_frames` gains `image_type` and `blend_width`, and for `blended` saves an RGB PNG instead of the palette PNG. `create_job` gains two optional form fields and echoes both. The frontend adds an Image type dropdown and a Blend width slider (disabled for Tiles), their explanations, validation and summary lines. No new dependency.

**Performance caveat found while planning** (see research Decision 5): a throwaway prototype measured a tiles frame at 0.33 ms and a blended frame at 1.4 ms (0.54 ms of arithmetic plus the true-color PNG), about 4 times a tiles frame and roughly 3 times a whole job for a 60 s file (a naive version of the blend was 17 times slower, which is why the two-pass form is used). That misses the "no more than twice as long" target in SC-006. The plan keeps the target for now, measures early on the real code, and if the real figure is above twice, reports it to the user with the measured numbers and proposes a realistic bound instead of changing the spec silently. **Outcome**: the first whole-job measurement was 3.1 to 3.8 times; blending and encoding the frames on a few threads (research Decision 5) brought it to 1.02 to 1.33 times on the development machine, so the target is met.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: numpy, Pillow, FastAPI; Vue, vitest. No new packages.

**Storage**: N/A. Same temp directories and file names (`frame_000000.png`); blended files are true-color PNGs (about 15 to 25 KB each against about 1 KB for tiles).

**Testing**: pytest: the blend function against an independent, deliberately naive per-pixel reference written in the test (all four tile colors weighted by the formula), including: pixels outside every band equal their tile exactly; the pair of pixels on either side of an inner edge average to the even mix (within 1 level); monotone, no-overshoot change across a band in every channel; a uniform frame and an all-black frame unchanged; corner = 25% each; the picture's border not blended; a black tile fading with its neighbor; rows are not wrapped (last tile of a row does not blend with the first of the next); the band never reaches farther than the blend width, at every width from 10 to 25, and the count of changed pixels never shrinks as the width grows; determinism; input not modified; shape/dtype; validation of type and width. `write_frames`: default and `tiles` byte-identical to the previous output (including a stored reference hash), blended frames have the tiles frame's colors in the middle of every tile for combinations of smoothing and window, roots, all three level steps, the threshold; same size and count; invalid arguments refused before writing. API: the two fields (valid, missing, every refused kind) and the response, `blend_width` ignored for `tiles`, frames served as PNG of the right size. vitest: the type list, blend width constants and validation, texts, and the rendered controls.

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: Tiles jobs no slower than before (identical code path). Blended jobs: target in SC-006 is at most twice the time of the tiles job for the same file; expected about 3 times on a 60 s file (see above). Measured early (task T002) and again at the end.

**Constraints**: Deterministic output; image size (252 × 168), layout, frame count and timing unchanged; with `tiles` the output must be byte-for-byte what it is today; results already created are unchanged.

**Scale/Scope**: One new backend module, edits to `frame_rendering.py` and `jobs.py`, one new test module for the module plus an API test module and a few additions, frontend edits to five files with tests, and the README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. The plan adds one small module and no dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/013-image-type-blended-tiles/
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
│   │   ├── image_types.py            # NEW: IMAGE_TYPES, DEFAULT_IMAGE_TYPE, blend width limits, checks, blend_tile_colors()
│   │   └── frame_rendering.py        # write_frames(image_type=, blend_width=): tiles -> palette PNG (unchanged), blended -> RGB PNG
│   └── routers/jobs.py               # optional "image_type" and "blend_width" form fields, "image_type"/"blend_width" in the response
└── tests/
    ├── test_image_types.py           # NEW: the blend function, validation
    ├── test_image_type_api.py        # NEW: the fields, response, frames through the API
    ├── test_frame_rendering.py       # write_frames with the image type (middles equal the tiles colors for many settings)
    └── test_energy_api.py            # expected response keys gain "image_type" and "blend_width"

frontend/src/
├── api.ts                            # JobSettings.imageType/blendWidth, JobResult.image_type/blend_width, form fields
├── App.vue                           # "Image type: ..." and (for blended) "Blend width: n%" summary lines
├── components/
│   ├── SettingsForm.vue              # Image type dropdown and Blend width slider (disabled for Tiles), with info popovers
│   └── SettingsForm.test.ts
└── utilities/
    ├── validation.ts                 # IMAGE_TYPES, BLEND_WIDTH_RANGE, validators, labels and readout
    ├── validation.test.ts
    ├── help.ts                       # imageTypeHelp, blendWidthHelp
    └── help.test.ts

README.md                             # the image types and the blend width
```

**Structure Decision**: Choosing a kind of picture and blending pixels are independent of the note analysis and of the color rules, so they get their own small module (`image_types.py`), like `color_levels.py`. It owns the allowed names and limits (the router needs them) and the blend function, which takes the tile geometry as arguments so that `frame_rendering.py` can import it without a circular import and without the module knowing the grid. `write_frames` keeps being the single place that turns finished colors into files, and chooses the file writer by image type; the tiles branch is the existing code unchanged, which is what guarantees byte-identical output. The type is a plain name checked against a tuple so that another type can be added later by adding a name and a writer.

## Complexity Tracking

No constitution violations. Nothing to justify.
