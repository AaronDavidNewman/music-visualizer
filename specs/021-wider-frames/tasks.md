---

description: "Task list for the 600-pixel frames (feature 021)"
---

# Tasks: Wider Frames (600 Pixels)

**Input**: Design documents from `/specs/021-wider-frames/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/frame-size.md, quickstart.md

**Tests**: Written first for each story (the project's practice): sizes of every frame, the tile geometry and colors, the old/new equivalence of contour, blended and circles, the circles' scaling, and the player's styles. The page itself cannot be looked at with this tooling (no browser); that is the manual step of the quickstart.

**Organization**: By user story: US1 every frame is 600 × 400 and sharper (P1), US2 circles keep their look (P2), US3 the player and the limits (P3). **Order matters**: the circles' scaling (US2, T008 to T010) must be in place before the two constants are changed in US1 (T006), or every circles test that works in reference pixels would fail for the wrong reason; the tests of US1 (T004, T005) are written first and fail until T006.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- Paths are from the repository root. Backend checks run with the user's colormap lists possibly still inconsistent: use the temporary-default runner (`scratchpad/run_with_default.py`, file restored) and report the one expected list-mismatch failure. Edit files with their line endings preserved; avoid `sed -i`; scripts with backticks or non-ASCII go in files written with the Write tool; replace test functions only block by block and compare test counts before and after.

---

## Phase 1: Setup

- [x] T001 Record the baseline before changing anything: the backend suite (temporary default colormap, file restored), the frontend suite, typecheck and build; the four reference hashes (`scratchpad/hashes019.py`); the number of collected tests per backend test file; the list of every test and source line that mentions 252, 168, `TILE_WIDTH` or `TILE_HEIGHT` (about 50 in 16 test files, plus `frame_rendering.py`, `circles.py`, `image_types.py`); and the timing and room prototype (`scratchpad/size_proto.py`) as the "before" figures.
  - Done: Baseline: backend 2,850 passed plus the one expected failure (the user's colormap lists do not match, run with the temporary default colormap, file restored), 2,851 tests collected; frontend 457 tests; the four reference hashes `1fb17963…`, `f6f336a1…`, `fce777da…`, `886b2e42…`; the per-file test counts saved (`scratchpad/counts_before.txt`); the prototype's "before" times and room (`scratchpad/size_proto.py`).

---

## Phase 2: Foundational (one definition of the size in the tests)

**Purpose**: The tests read the frame size from one place, so that changing it is a one-line change and the many tests do not carry their own 252 and 168. Done while the size is still 252 × 168, so the suite must stay green.

- [x] T002 Create `backend/tests/frame_size.py` (`WIDTH`, `HEIGHT`, `REFERENCE_WIDTH = 252`, `REFERENCE_HEIGHT = 168`, `SCALE = WIDTH / REFERENCE_WIDTH`, taking `WIDTH` and `HEIGHT` from `app.services.frame_rendering`'s `IMAGE_WIDTH` and `IMAGE_HEIGHT`) and make the tests that mention 252 or 168 import them: `test_circles.py` (`W`, `H`), `test_circles_api.py`, `test_circles_rendering.py`, `test_colormap_api.py`, `test_contour.py`, `test_contour_api.py`, `test_frame_interpolation.py`, `test_image_types.py`, `test_image_type_api.py`, `test_interpolation_api.py`, `test_interpolation_rendering.py`, `test_jobs_api.py`, `test_note_count_api.py`, `test_note_count_rendering.py`, `test_resolution_api.py`, `test_resolution_rendering.py`; the tile-center lookups of `test_frame_rendering.py` that use `TILE_WIDTH`/`TILE_HEIGHT` use `tile_edges` instead (centers of the tiles). The suite must pass unchanged at 252 × 168 and the test counts must equal those of T001.
  - Done: `backend/tests/frame_size.py` (`WIDTH`, `HEIGHT`, `REFERENCE_*`, `SCALE`, `COLUMN_EDGES`, `ROW_EDGES`, `tile_center`); 13 test files now read the size from it (every 252 and 168 that was the frame size); the tile-center lookups of `test_jobs_api.py` and `test_frame_rendering.py` use `tile_center`; the function-level tests of `test_image_types.py` and `test_frame_interpolation.py` keep their own explicit geometry on purpose (they test pure functions, independent of the frame size). The suite passed unchanged at 252 x 168 and the test counts were identical to T001.

---

## Phase 3: User Story 2 - Circles keep their look at the larger size (Priority: P2), done first (see the order note)

**Goal**: The circle writer derives `scale = width / 252` and applies it to the step and the radius, so that a 252-wide call is exactly what it was and a 600-wide call gives the same picture in proportion.

**Independent Test**: Call the circle writer with `width=252, height=168` and with `width=600, height=400` for the same values: the disc centers and radii differ by exactly 600 / 252 (before the wrap), the colors and opacities are equal, and the pictures reduced to 252 × 168 are close.

### Tests for User Story 2 (write first, they fail)

- [x] T008 [P] [US2] In `backend/tests/test_circles.py` and `backend/tests/test_circles_rendering.py`: `plan_circles(..., width=600, height=400)` places the first circle of a steady note at the middle (300, 200) plus the step times `600 / 252`, for every note and unit, and wraps modulo 600 and 400; the discs drawn at `width=600` have centers equal to the 252 ones scaled by 600 / 252 (a window of frames where nothing wraps) and radii equal to `radius × 600 / 252` (and `× (1 + 2 c / 255)` with the resize), with the same fills (colors and opacities); at `width=252` everything is exactly as before; the picture at 600 × 400 is exactly 600 × 400 and, reduced to 252 × 168, is close to the 252 × 168 one (mean absolute difference below a small bound); the `Discs` spy of `test_circles_rendering.py` reports reference pixels (it divides by `SCALE`) so that the existing circles tests keep their expectations, and pixel lookups multiply by `SCALE`.
  - Done: `test_circles.py` (the plan at width 600: the reference plan scaled by 600 / 252 for 80 frames including every wrap, the first circle, a steady note and the wrap, the scale from the width and the wrap from the height on a 600 x 300 frame, nothing changed at 252) and `test_circles_rendering.py` (the `Discs` spy reports reference pixels, `pixel()` for lookups, areas times `SCALE` squared; the discs at 252 and at 600 are the same in reference pixels, 600 / 252 times as large on the frame, the same fills, with and without the resize; the radius of a disc; the picture reduced to 252 x 168 is close and covers the same share). They failed before T009 (8 failures) and the picture test was strengthened with the covered share because it passed without the scaling.

### Implementation for User Story 2

- [x] T009 [US2] Edit `backend/app/services/circles.py`: `REFERENCE_WIDTH = 252`; `plan_circles` and `write_circle_frames` compute `scale = width / REFERENCE_WIDTH` and use `unit * scale` for the step and `radius * scale` for the radius; defaults of `width`/`height` stay 252/168; docstrings updated (the settings are measured against the 252-pixel reference frame). The settings, checks, messages and request fields do not change.
  - Done: `circles.py`: `REFERENCE_WIDTH = 252`; `plan_circles` and `write_circle_frames` derive `frame_scale = width / 252` and use `unit * frame_scale` and `radius * frame_scale`; defaults of width and height stay 252 / 168; docstrings.
- [x] T010 [US2] Verify: the circle tests (old and new) pass at 252 and at 600; mutation checks, each caught and restored: no scale on the step, no scale on the radius, the scale from the height instead of the width, the scale applied twice, the scale applied to the resize factor only, the start not in the middle of the new frame, the wrap still modulo 252.
  - Done: 402 circle tests pass at 252 and at 600. Mutation checks, all 8 caught and restored: no scale on the step, none on the radius, the plan's scale from the height, the radius' scale from the height, the radius scaled twice, only the resize factor scaled, the start not in the middle, the wrap still at 252.

**Checkpoint**: the circles are correct at any frame width; nothing has changed for 252.

---

## Phase 4: User Story 1 - Every frame is 600 pixels wide and sharper (Priority: P1) 🎯 MVP

**Goal**: Every frame of every image type is 600 × 400, drawn at that size, with the same content.

**Independent Test**: Create frames for each image type, oversampling and interpolate value: every PNG is 600 × 400; tile colors at the tile centers equal the old ones; contour and blended frames reduced to 252 × 168 are close to the old frames.

### Tests for User Story 1 (write first, they fail until T006)

- [x] T004 [P] [US1] Create `backend/tests/test_frame_size.py`: the literal numbers (`IMAGE_WIDTH == 600`, `IMAGE_HEIGHT == 400`, `REFERENCE_WIDTH == 252`, `REFERENCE_HEIGHT == 168`), the invariants (3:2, the same ratio as the reference, `FRAME_SCALE`), no `TILE_WIDTH`/`TILE_HEIGHT` any more; every frame file of every image type is exactly 600 × 400 for oversampling 1 to 5 and interpolate 1 to 5 (the written PNGs, including the in-between ones, through `write_frames`) and through the API for each type; the PNG modes are those of before (indexed for the original grid of tiles, RGB for the others as they were); the number, names and order of the frames equal those of before; the tile columns and rows within one pixel for every oversampling (decoded from the PNG, the runs of equal color per tile), with the default grid in columns of exactly 50 and rows of 57 or 58; the tile colors at the tile centers equal the colors of the same tiles at 252 × 168 (render both through `render_frame`-level helpers or by patching the size) for every oversampling.
  - Done: `backend/tests/test_frame_size.py` (59 tests): the literal 600 x 400 and the invariants, no tile constants, every frame of every type for interpolate 1, 3 and 5 and for resolution 1, 3, 5 is 600 x 400 (and through the API for each type at the defaults and at resolution 5 / interpolate 5), the number, names and PNG mode equal those of the old size (the old size is rendered by patching the two constants), tile columns and rows within one pixel (the color changes only at the nearest-whole-pixel even split, nearly every edge a change) for oversampling 1 to 5, the 50 px columns and 57 / 58 px rows, and the tile colors at the centers equal the old ones for oversampling 1 to 5. A first version of the geometry test counted runs of equal color and failed at oversampling 4 and 5 where two neighbors share a color; it was rewritten.
- [x] T005 [P] [US1] In `backend/tests/test_frame_size.py` and `test_contour.py`/`test_image_types.py`: the equivalence of the content: the contour writer called at `252, 168` and at `600, 400` for the same values, the new frame reduced to 252 × 168 (area average) has a mean absolute difference from the old frame below a small bound and the same colors in the flat regions; `make_grid_blender` at both sizes gives frames that are close after the reduction, the feather reach equals `blend width % × (width / columns)` and so scales with the tile (12.5 px at 25% of a 50 px tile); a contour frame at 600 × 400 has finer edges than the old one enlarged (more distinct values along an edge than the nearest-neighbor enlargement of the old frame); the interpolated frames have the new size and are blends of the drawn ones.
  - Done: In the same file: contour and blended frames reduced to 252 x 168 are within a mean absolute difference of 4 of the old frames (for blended at 1 and 5, contour at 1 and 5), the feather fades only within its reach at both sizes, and the in-between frames of interpolate 3 are 600 x 400 and lie between the drawn frames. The task text also asked for a test that a contour frame is finer than the old one enlarged; that was not written as an assertion (no robust measure of "finer"): the comparison picture sent to the user shows it instead.

### Implementation for User Story 1

- [x] T006 [US1] Edit `backend/app/services/frame_rendering.py` (research Decision 1): `IMAGE_WIDTH = 600`, `IMAGE_HEIGHT = 400`, `REFERENCE_WIDTH = 252`, `REFERENCE_HEIGHT = 168`, `FRAME_SCALE`, the invariants as assertions, `TILE_WIDTH`/`TILE_HEIGHT` and their assertions removed, the comments and the module docstring (252 × 168, 21 × 24 tiles, "10 pixels across") corrected; the same in the docstrings of `backend/app/services/image_types.py` and `backend/app/services/contour.py`. No other code change is expected (the writers take the size as arguments and `tile_edges` spreads the rows). Fix whatever the first run shows.
  - Done: `frame_rendering.py`: `IMAGE_WIDTH = 600`, `IMAGE_HEIGHT = 400`, `REFERENCE_WIDTH`, `REFERENCE_HEIGHT`, `FRAME_SCALE`, the two invariants as assertions, `TILE_WIDTH`/`TILE_HEIGHT` gone, the comments; the docstrings of `image_types.py` (50 x 57/58 tiles, the feather of 12.5 px on each side). No other code needed to change: the writers already took the size and `tile_edges` spreads the rows.
- [x] T007 [US1] Run the whole backend suite (temporary default colormap): fix the tests that still depend on the old pixel geometry (a lookup that assumed 21 × 24 tiles, a size written as a number, a blended test with fixed pixel offsets such as "8 pixels in from the edge": use the tile edges and the reach), keeping each test's meaning; the test counts must not drop. Mutation checks, each caught and restored: `IMAGE_WIDTH` 252, `IMAGE_HEIGHT` 399, the rows given by integer division (unequal rows), the contour figure sized with the old constants, the palette index image still 252 × 168, the blended reach computed from the old tile width, the interpolated frames resized back to the old size.
  - Done: Whole backend suite after the change: 69 failures at first, all tests that assumed 21 x 24 tiles or the old last pixel: the tile-center lookup of `test_jobs_api.py` (one helper, 45 tests), the geometry test (`{21}`/`{24}`), `test_frame_rendering.py` (the blended range filter window and the flat middle, now computed from the reach), `test_contour_api.py` (the corner pixels 167 and 251, and a threshold test that claimed byte-identical pictures for a 0.1 % threshold: at the new size the contour of the near-silent leakage moves by a fraction of a pixel, so it now asserts the difference is more than 5 times smaller than that of a 5 % threshold). Test counts did not drop (2,851 to 2,920). Mutation checks, all caught and restored: the width 252, the height 399, the height 420, the tile edges floored, an inner edge one pixel off, the contour figure sized with the old numbers, the palette index image still 252 x 168, the blended reach from the old tile width, the in-between frames resized back, the tile index with the old height (the first five crash at import through the new assertions; the two edge mutations were added to show the tests themselves catch a wrong geometry).

**Checkpoint**: every frame is 600 × 400 and has the old content; the circles are scaled (T009).

---

## Phase 5: User Story 3 - The page shows the frames at their real size, and the job stays practical (Priority: P3)

**Goal**: The player shows the frame at up to 600 px with smooth scaling, the circles' help texts say what the numbers are measured against, and the time and room limits hold.

**Independent Test**: The player's styles have `max-width: 600px`, `aspect-ratio: 3 / 2` and no pixelated rendering; the help texts mention the 252-pixel-wide frame; the prototype's times and room are inside the limits.

### Tests for User Story 3 (write first)

- [x] T011 [P] [US3] `frontend/src/components/FramePlayer.test.ts` (new, source guards with `?raw`, as for the other components): the frame is `width: 100%` with `max-width: 600px` and `aspect-ratio: 3 / 2`, the controls have the same maximum width, there is no `image-rendering: pixelated`, and the comment no longer says 252 × 168; in `frontend/src/utilities/help.test.ts`: `circleUnitHelp` and `circleRadiusHelp` say that the number is measured against a frame 252 pixels wide and drawn about 2.4 times larger on the 600-pixel frame, and still say Movement and radius; the readouts are unchanged (`formatCircleUnit`, `formatCircleRadius` give "4 px").
  - Done: `frontend/src/components/FramePlayer.test.ts` (new, source guards): the frame `width: 100%` with `max-width: 600px`, 3:2, no `image-rendering`, no border, the slider the same width, 600 x 400 in the comment; `help.test.ts` for the 252-pixel statement.

### Implementation for User Story 3

- [x] T012 [US3] Edit `frontend/src/components/FramePlayer.vue` (research Decision 6) and `frontend/src/utilities/help.ts` (research Decision 7).
  - Done: `FramePlayer.vue` (`width: 100%; max-width: 600px`, `outline` instead of the border so that the image gets all 600 pixels, no pixelated scaling; the same width for the slider) and `help.ts`. Frontend 463 tests, typecheck and build clean.
- [x] T013 [US3] Measure time and room (the prototype `scratchpad/size_proto.py` adapted to the real code, circles included with their scaling) for the 60 second, 1,800 frame job of each image type at the default and at the costliest settings: every default job within one minute, every costliest job within two, and the room at most 4 times the old (blended is the closest at 3.6); if blended exceeds 4 times, raise its PNG compression level first (research Decision 10) and measure again; record the figures in this task's notes.
  - Done: 60 s, 1,800 frames, old size to new size (time, room): tiles 0.6 to 1.0 s (2 to 5 MB); tiles oversampling 5 2.3 to 7.1 s (9 to 12 MB); blended 1.0 to 6.4 s (18 to 67 MB, x3.6); blended oversampling 5 1.1 to 6.7 s (22 to 77 MB); contour 15 to 20 s (4 to 10 MB); contour oversampling 5 17 to 21 s; contour oversampling 5 with interpolate 5 4.2 to 6.3 s; circles at the defaults 3.8 to 17.8 s (40 to 109 MB, x2.8); circles at the largest settings 9.6 to 50 s (76 to 220 MB, x2.9). Every default job is far below one minute and the costliest (circles, 50 s) below two; the largest room ratio is 3.6 (blended), inside 4, so no tuning was needed. The circles cost more than the 19 s of the first prototype because the scaled discs are larger and overlap more.

**Checkpoint**: all three stories work.

---

## Phase 6: Polish & Cross-Cutting

- [x] T014 [P] Update `README.md` (the frame size 600 × 400, the grid of 12 × 7 tiles of 50 × 57/58 pixels, the blended feather in pixels, the circles' scaling by 600 / 252 and the reference frame, the player at up to 600 px) and add amendment notes (not rewrites) at the top of the `spec.md` of the features that define the old size (`002-audio-frames-ui`, `005-octave-grid-layout`, `013-image-type-blended-tiles`, `015-contour-image-type`, `019-generative-circles`), saying the frame is 600 × 400 since feature 021 and, for 019, that Movement and Radius are measured against a 252-pixel-wide frame.
  - Done: README: a Frame size paragraph before Circles, the sizes in the Image type, Blended, Contour, Circles, Blend width, Oversampling and Interpolate paragraphs, the circles' reference frame and the scaling; amendment notes at the top of the specs 002, 005, 013, 015 and 019 (spec, and for 019 the data model).
- [x] T015 Final verification: the backend suite (temporary default, file restored; only the user's list-mismatch failure may remain), the list-tolerance run (`scratchpad/tolerance.py`), the frontend vitest, vue-tsc and build; the four reference hashes now differ from T001 (the frames are another size), which is expected: record the new hashes; a scan of the code and the README for the old size where it should be gone (252 × 168 as a frame size, 21 × 24 tiles).
  - Done: Backend 2,919 passed plus the user's list-mismatch failure; the list-tolerance run 2,671 passed and only `test_the_frontends_default_matches_this_one` failed (the same unsettled default), both files restored; frontend 463 tests, typecheck and build clean. The new reference hashes (tiles `68199905…`, blended `f32a99c5…`, Blues/smoothing/threshold `92b3a27d…`, contour `dff443e8…`) differ from T001 as expected (the frames are another size). A scan of `backend/app` and `frontend/src` for 252 and 168 finds only the reference frame, the old defaults of the circle writer and the help texts, which are intended.
- [x] T016 Walk the quickstart: sections 1 to 4 through the suites and the prototype; render a comparison picture (old frame enlarged next to the new frame, for contour, blended and circles) and send it to the user; section 5 (the page in a browser) cannot be done with this tooling: say so, list what the tests and style guards cover, and what only a person can check (the 600 px frame in the player, the narrow-window scaling, how crisp it looks).
  - Done: Quickstart 1 to 4 done through the suites and the prototype; the comparison picture (the old frame shown at 600 wide with pixelated scaling, as the page did, beside the new frame, for tiles, blended tiles, contour and circles) was sent to the user. **Step 5 (the page in a browser) was not done**: this tooling has no browser. Covered: the size of every frame, the geometry and the colors, the player's styles and the help texts. Only a person can check: the 600 px frame in the player, the narrow-window scaling, how crisp it looks, that the outline looks right without a border.

---

## Dependencies & Execution Order

- **Setup (T001)** first, then **T002** (the tests read the size from one place).
- **US2 (T008 to T010)** next, because the circles' scaling must exist before the constants change: T008 then T009 then T010.
- **US1 (T004, T005 tests; T006 the change; T007)**: the tests can be written any time after T002; T006 needs T009.
- **US3 (T011 to T013)** needs the new size (T006) for the measurement T013; T011 and T012 are independent of the backend.
- **Polish (T014 to T016)** last; T014 can run alongside T015.

### Parallel opportunities

- T004 with T005 with T008 (different files).
- T011 and T012 with the backend work (a different project).
- T014 with T015.

## Implementation Strategy

1. T001, T002 (no behaviour change), then the circles' scaling (US2), then the one change of two constants (US1) with its tests, fixing what the old geometry assumptions break.
2. The player and the help texts (US3), then the measurement of time and room.
3. Documentation, the full verification, and an honest report of what only a browser can confirm.

## Notes

- The frames are not byte-identical to before for any image type (they are another size); the reference hashes change and are recorded again.
- The circles' settings and request fields do not change; only what the numbers are measured against.
