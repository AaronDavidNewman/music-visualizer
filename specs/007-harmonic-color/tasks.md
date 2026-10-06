---

description: "Task list for Harmonic Color"
---

# Tasks: Harmonic Color

**Input**: Design documents from `/specs/007-harmonic-color/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/image-color.md, quickstart.md

**Tests**: Included, following the plan: pytest for the color rule and the API. There is no frontend code change, so the frontend is only re-run (tests, typecheck, build) and checked by the quickstart.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 or US2

## Phase 1: Setup

- [x] T001 Run `pytest` in `backend/` and `npm test` in `frontend/` to confirm a green baseline before changing anything (376 backend and 127 frontend tests at the end of feature 006), and note the numbers

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Make the existing tests read pixels in a way that works for both a gray and a colored image, so they stay meaningful (and green) before and after the change.

- [x] T002 [P] In `backend/tests/test_frame_rendering.py` update every test that reads rendered pixels so it works for both grayscale and RGB images: convert with `np.asarray(image.convert("RGB"))` and take the brightest channel (`.max(axis=2)`) wherever a tile's gray level is compared (`tile()` helper, the flat-tile and per-note tests, the brightness tests, the first-note and last-note tests, `test_each_tile_has_the_same_gray_as_the_previous_layout`, `test_render_frame_applies_the_boost` and `test_render_frame_uses_the_brightness`); remove assertions that depend on the mode being `"L"` and the sum-of-pixels assertions in `test_lowest_note_is_top_left_and_last_drawn_note_is_bottom_right` (replace them with checks that the lit tile is at the right place and every other tile is black); for the two brightness tests where every tile holds the same level, compare the brightest channel only; keep the image-size and `write_frames` checks as they are
- [x] T003 [P] In `backend/tests/test_jobs_api.py` update the pixel helpers so they work for both gray and RGB images: `frame_levels` converts the PNG to RGB and returns, for each of the 84 tiles, the largest channel at the tile's center pixel; `tile_means` converts to RGB and takes `.max(axis=2)` before averaging each tile; the `("L", (252, 168))` check in `test_frame_endpoint_serves_png` becomes a check of size only (the mode is checked in T008); everything else stays
- [x] T004 Run `pytest` from `backend/` and confirm every test still passes unchanged in meaning (the same 376 pass) with the old grayscale code

**Checkpoint**: The tests no longer care whether the image is gray or colored.

---

## Phase 3: User Story 1 - Color each tile by the notes that sound with it (Priority: P1) 🎯 MVP

**Goal**: Each tile is drawn with hue from its eight related notes, 50% saturation and its gray level as the value.

**Independent Test**: A full-brightness tile with only note n+12 lit comes out as (128, 255, 159), with only n+1 lit as (128, 159, 255), and with no related note lit as (128, 255, 255).

### Tests for User Story 1

- [x] T005 [P] [US1] In `backend/tests/test_frame_rendering.py` add tests for `tile_hues`, `tile_colors` and the RGB image, using a small reference implementation written in the test (a plain loop over tiles that applies the formula, with `colorsys` for the conversion, independent of the functions under test): the constants are `SATURATION == 0.5`, `DEFAULT_HUE == 0.5`, `RELATED_DOWN == (12, 7, -5, 5)` and `RELATED_UP == (4, 6, -1, 1)`; with no related note lit every hue is 0.5 (180°); a frame with only note 36 at level 255 (brightness 2 maps 255 to 255) makes the hue of tile 24 equal 0.375 (135°) because 36 is its n+12 partner, the hue of tile 29 equal 0.375 (36 is n+7), tile 41 equal 0.375 (n-5), tile 31 equal 0.375 (n+5), and tiles 32, 30, 37 and 35 equal 0.625 (225°) because 36 is their n+4, n+6, n-1 and n+1 partner; the colors for a full-brightness tile are exactly (128, 255, 255) with no related note lit, (128, 255, 159) with only n+12 lit, (128, 159, 255) with only n+1 lit and (255, 128, 128) with all four notes of either group lit and none of the other, and a tile at level 128 with nothing related lit is (64, 128, 128); both groups equally bright gives hue 0.5; the hue never leaves 0 to 1 over 2,000 random frames and equals the reference for them (to within 1e-9); an n+7 partner at about half brightness (level 128 after the boost) gives a hue of about 157.4°; partners past the ends count as silent and the average still divides by four (tile 83's n+12 partner does not exist, so a frame with only note 83 lit changes no other tile's hue except those it is a partner of, and tile 83's own hue is 0.5); notes 84 to 87 count as partners (only note 84 lit at 255 gives tile 72 the hue 0.375 and tile 83 the hue 0.625 because 84 is its n+1 partner) even though they are not drawn; a tile with level 0 is (0, 0, 0) at any hue; for every tile with a level above 0 the largest channel equals the displayed gray level and the smallest channel is within 1 of half of it; for random frames, hues recovered with `colorsys.rgb_to_hsv` from tiles whose gray level is 128 or more are within 2° of the rule (wrapped around the wheel); `render_frame` returns mode `"RGB"` at size (252, 168), every tile is one flat color, every pixel of a frame of all-zero levels is (0, 0, 0), the same input gives the same image twice, and `write_frames` writes RGB PNGs of size (252, 168) with identical bytes on repeat

### Implementation for User Story 1

- [x] T006 [US1] In `backend/app/services/frame_rendering.py` add `import colorsys`; add the constants `SATURATION = 0.5`, `DEFAULT_HUE = 0.5`, `RELATED_DOWN = (12, 7, -5, 5)` and `RELATED_UP = (4, 6, -1, 1)`; add `tile_hues(levels, brightness=DEFAULT_BRIGHTNESS)` (boost all the levels with `boost_levels`, divide by 255, pad with 12 zeros on each side, then for tiles 0 to 83 take the average of the four down partners and of the four up partners by shifted slices, always dividing by 4, and return `DEFAULT_HUE + 0.5 * (up - down)` clipped to 0 to 1; refuse fewer than `SHOWN_NOTES` levels as `render_frame` does); add `tile_colors(levels, brightness=DEFAULT_BRIGHTNESS)` returning an `(84, 3)` `uint8` array by calling `colorsys.hsv_to_rgb(hue, SATURATION, value)` for each tile in a list comprehension (value is the tile's boosted level divided by 255) and rounding with `numpy.rint(x * 255)`; change `render_frame` to build its tiles from `tile_colors`, reshape to `(GRID_ROWS, GRID_COLUMNS, 3)`, repeat rows `TILE_HEIGHT` times and columns `TILE_WIDTH` times, and return an `"RGB"` image; update the module and function docstrings to describe the color rule; leave `to_gray_levels`, `boost_levels`, `smooth_frames`, `average_frames` and `write_frames` unchanged
- [x] T007 [US1] Run `pytest` from `backend/` and fix failures in T005 and any test that still assumes a gray image

**Checkpoint**: Tiles are drawn in the color the rule gives.

---

## Phase 4: User Story 2 - Brightness, layout and everything else stay as they were (Priority: P2)

**Goal**: Nothing except the color changes: brightness, positions, size, counts, timing and the settings behave as before, and the docs describe the colored image.

**Independent Test**: For the same file and settings every tile's brightest channel equals its previous gray level, silent files are black, and the frame count and image size are unchanged.

### Tests for User Story 2

- [x] T008 [P] [US2] In `backend/tests/test_jobs_api.py` add tests: a served frame has mode `"RGB"` and size (252, 168) with width ÷ height exactly 1.5; for several frames of a two-tone file (notes 24 and 36 at the same time, so each tile has a lit partner) the brightest channel at every tile's center equals the gray level worked out independently (from `read_wav`, `analyze_channels`, `average_frames`, `to_gray_levels` and the brightness root, as in the earlier tests) and the darkest channel is within 1 of half of it; the hue of tile 24 at its center pixel, recovered with `colorsys.rgb_to_hsv`, matches the hue worked out independently from the displayed gray levels of its partners (within 2°) for frames where the tile has a value of at least 128, and is shifted below 180° while note 36 sounds, and the hue of tile 25 (which has note 24 as its n−1 partner) is shifted above 180° when tile 25 is bright enough; a single steady note's brightest tile has a hue of about 180°; a silent file gives frames in which every pixel is (0, 0, 0) at brightness 2 and 100 and at smoothing 0 and 0.8; `frame_count`, `window_count`, `step_samples` and `window_spacing` are as before; the same file and settings submitted twice give byte-identical frames; the color follows the final brightness: at `brightness=4` and at `smoothing=0.5` the brightest channel of each tile equals the independently worked-out displayed level, so both settings keep their effect on brightness; the loudest tile still has a brightest channel of 255 somewhere

### Implementation for User Story 2

- [x] T009 [P] [US2] Update the written description of the frame image from gray tiles to colored tiles, with each change saying the color was added by feature 007 and keeping the older numbers only as history: `README.md` (the "grayscale PNG" and brightness sentences: tiles are colored, value is the gray level, saturation 50%, hue from the related notes, the two groups, the worked colors, the pastel look, no gray-scale option, no saturation setting); in `specs/002-audio-frames-ui/` the spec (FR-009 and FR-010 wording about gray and "brightness"), `contracts/http-api.md` (the "252 × 168 grayscale" and gray-level lines), `data-model.md` (the Frame Image paragraph), `research.md` and `plan.md` and `quickstart.md` (the "gray tiles" wording); in `specs/005-octave-grid-layout/contracts/image-layout.md` and `data-model.md` ("8-bit grayscale", "single gray level") a note that feature 007 made the tiles colored with the same positions and the same brightest channel; and in `specs/004-brightness-parameter/` and `specs/006-note-smoothing/` contracts one line each saying the brightness and smoothing now set the tile's value and so its brightest channel
- [x] T010 [US2] Run the whole backend suite (`pytest` from `backend/`) and the frontend checks (`npm test`, `npm run typecheck`, `npm run build` in `frontend/`) and fix failures

**Checkpoint**: Both stories work and the docs match.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T011 Using `backend/audio/fotr-intro1-echo.wav`, check on real data: (a) SC-001: for many frames at brightness 2, 4 and 10 and at smoothing 0 and 0.5, every tile's brightest channel equals the gray level the old grayscale drawing gave for that note (`boost_levels` of the same levels) and its darkest channel is within 1 of half of it; (b) SC-003: for many frames, recover each tile's hue from its pixels with `colorsys.rgb_to_hsv` for tiles with a value of 128 or more and compare with the rule worked out independently from the displayed levels (within 2°), and report how much of the hue wheel the real music actually uses (a histogram or the min, median and max hue) so the effect on this file is known; (c) SC-007: time rendering all 10,224 frames with the previous grayscale drawing (reproduced in the script) against the new color drawing, and then time the same `POST /api/jobs` end to end on an unused port started from `backend/` with the venv (check the port first; do not stop or reuse a server the user is running), compare with the earlier 5.4 to 6.8 s, confirm a served frame is an RGB PNG of 252 × 168, then stop the server and delete only the job folders created in this run; (d) save a picture of the same frame in the old gray drawing and the new color drawing side by side and look at it. **Results:** (a) SC-001 holds in 636 frame and setting combinations (brightest channel equals the old gray level, darkest within 1 of half). (b) SC-003 holds: hue recovered from the pixels is within 0.62° of the rule over the sampled tiles with value 128 or more. On this sustained, echo-heavy music those tiles use hues from 154° to 235° (median 188°, 5% to 95% range 169° to 211°), and 48% are within 10° of cyan, so the colors are mostly teal to blue; the effect is real but modest here, and stronger with chords. (c) **SC-007 was missed by the first implementation and fixed:** saving 24-bit RGB PNGs made drawing and saving the 10,224 frames take 6.9 s against 4.3 s for gray (+61% on a step that is most of a submission). The profile showed PNG encoding of three channels (2.1 s against 0.7 s) and repeating three channels (1.0 s against 0.3 s) were the cost, not `colorsys` (0.6 s). Frames are now saved as indexed-colour PNGs (lossless, a palette of the 84 tile colors, level 6), which decode to exactly the pixels of `render_frame` (tested). The step is now within noise of gray (+8%, −5%, −5% over three runs), files are 9.8 MB for the sample submission against 5.6 MB for gray, and the end-to-end `POST /api/jobs` took 6.1, 6.4 and 6.6 s against the earlier 5.4 to 6.8 s. The served frame is a `P`-mode PNG of 252 × 168 that decodes to RGB. (d) A picture of old gray against new color frames was produced and looked at: same positions and brightness, with teal, blue and green tints.
- [x] T012 Report that the browser walkthrough in `quickstart.md` (step 3, in particular that the page shows the colored frames at the same size and plays them as before) was not run if no browser can be driven from this session. **Not run: no browser could be driven from this session.** There is no frontend code change, the served file is a standard PNG with the same URL, size and proportions, and the frontend tests, typecheck and build pass, but I have not seen the colored frames on the page, or the animation playing, in a browser.
- [x] T013 Mark completed tasks `[x]` in this file

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → Phase 5.
- T002 and T003 are independent (different files). T004 follows both. T005 comes before T006 and should fail first. T008 and T009 are independent of each other.
- Only `backend/app/services/frame_rendering.py` changes in the source tree; there is no frontend code change.

## Implementation Strategy

- **MVP**: Phases 1 to 3: the tiles are drawn in color by the rule and every earlier test still passes.
- **Then**: Phase 4 proves nothing else changed (brightness, layout, counts, silence, settings) through the API and brings the docs in line, and Phase 5 checks the real file, the timing target and the colors on real music.

## Change after implementation (2026-10-06)

- The hue rule was changed at the user's request after the first version showed only teal and blue: each group's brightness is now **added instead of averaged**, the hue is clipped to 0°-360°, and the lists are `RELATED_DOWN = (4, 5, 7)` and `RELATED_UP = (3, 6, 8, 11)`. Tasks T005 and T008 above describe the original lists and averaging; the tests were rewritten to read the lists from the constants and to use sums, and the worked colors, spec, contract, data model, research, plan and quickstart were updated. The task descriptions above are left as written.
- Smoothing (feature 006) now also smooths each tile's hue over the frames; see the feature 006 spec, FR-014.
