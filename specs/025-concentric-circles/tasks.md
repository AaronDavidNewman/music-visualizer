---

description: "Task list for Concentric (feature 025)"
---

# Tasks: Concentric

**Input**: Design documents from `/specs/025-concentric-circles/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/concentric.md, quickstart.md

**Tests**: Written first for each story (the project's practice): the steps, the colors and the geometry on plain arrays, the pixels of the frames, the API, and the page's group, controls and summary (server-side rendering and source guards, since there is no browser or DOM library here). The look in the player is the manual step of the quickstart.

**Organization**: By user story: US1 the picture itself (P1), US2 choosing it on the page and through the server (P2), US3 the corners: silent frames, no beat, equal volumes (P3). The library work for US3 is inside US1's functions; its tests come last because they also go through the API.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- Paths are from the repository root. The Spec Kit setup scripts cannot run here (PowerShell execution policy), so the feature files were written by hand. Backend checks run with the user's colormap lists possibly still inconsistent: use the temporary-default runner (`scratchpad/run_with_default.py`, file restored) and report the one expected list-mismatch failure. Edit files with their line endings preserved; avoid `sed -i`; scripts with backticks, backslashes or non-ASCII go in files written with the Write tool (a `\b` in an edit script once turned into a backspace character); replace test functions only block by block and compare test counts before and after.

---

## Phase 1: Setup

- [x] T001 Record the baseline before changing anything: the backend suite (temporary default colormap, file restored; expect 3,590 tests), the frontend suite (expect 536), typecheck and build; the four reference hashes (`scratchpad/hashes019.py`: `6819990556fd4095`, `f32a99c59fcb87fc`, `92b3a27dee73e223`, `400cc93e1bfca03d`); the per-file backend test counts (`scratchpad/count_tests.py <file>`); the tests that list the image types or the groups of a type (they derive from `IMAGE_TYPES` or name the five types: `test_image_types.py`, `test_image_type_api.py`, `test_circles*.py`, `groups.test.ts`, `validation.test.ts`, `SettingsForm.test.ts`, `App.test.ts`), because the sixth type will touch them.
  - Done: Baseline carried over from the end of feature 024 (nothing changed in between): backend 3,590 tests (temporary default colormap), frontend 536, typecheck and build clean; the four reference hashes `6819990556fd4095`, `f32a99c59fcb87fc`, `92b3a27dee73e223`, `400cc93e1bfca03d`; per-file counts saved (`scratchpad/counts_025_before.txt`).

---

## Phase 2: User Story 1 - Circles of rings whose size is the note's volume and whose colors follow the beat (Priority: P1) 🎯 MVP

**Goal**: `concentric.py` and its branch in `write_frames`: the 84 circles with their steps, rings, colors and background.

**Independent Test**: `write_frames(values, directory, image_type="concentric", beat=...)` for a frame with one loud note and quieter ones: the loud circle has radius 25 and 12 rings, the others fewer, the rings flat in the colormap's colors for the frame's position.

### Tests for User Story 1 (write first, they fail)

- [x] T002 [P] [US1] Create `backend/tests/test_concentric.py` (spec FR-002 to FR-008, SC-001 to SC-004; helpers in the file): (a) `ring_steps`: exact ratios `k * k / 144` of the loudest give step `k` for `k = 1 … 12`, ratios just above them give `k + 1`, the loudest note is 12, a note of 0 is 1, a silent frame is all 1, never below 1 or above 12, monotone in the value within a frame, each frame uses its own loudest (the same values scaled by 7 give the same steps; two frames with different loudest give different steps for the same value), input unchanged; (b) `ring_colors`: for every colormap the 12 colors of a frame are the table entries at `rint((k - 1) / 11 * (0.5 + 0.5 * p) * 255)` for positions 0, 0.25, 0.5 and 1, ring 1 always the first color, ring 12 the last at position 1 and row 128 at position 0, `beat=None` equal to position 0, one row of 12 colors per frame, wrong shapes or values of `beat` refused with the message of `check_beat`; (c) the geometry and pixels, through `write_concentric_frames` and `write_frames` on 600 x 400: the background (every pixel outside every circle, e.g. the corners and the gaps between rows, is exactly the colormap's row 128), the center pixel of every one of the 84 cells is ring 1's color, a pixel at the middle of ring `k` of the loudest circle (distance `(k - 0.5) * 25 / 12` from its center along the row) is `color[k]` for every `k` (the ring is flat), the same pixel of a circle of step `s < k` is the background and for `k <= s` is `color[k]` (a smaller circle is a full one with the outer rings left off), circles are centered on the tile centers of the original grid (compare the centroid of the non-background pixels of a lone circle with the tile center), the loudest circle's radius is 25 px (its widest non-background row is 49 or 50 pixels wide) and a circle of step `s` has radius `s * 25 / 12` (to within a pixel), neighbouring full circles in a row touch and no pixel of a circle lies outside its cell (set one note at a time and check that the non-background pixels are inside that cell's box), the edge is smooth (some pixels of a ring boundary are mixes), a frame equals a brute-force drawing of the rings on a 4 x 4 supersampled canvas averaged down (write the brute force in the test, for random steps and positions, exactly equal); (d) frames: the count, the names `frame_000000.png` and up, RGB 600 x 400, determinism (byte-identical runs), different positions give different frames, a frame at position 1 has ring 12's color the last color of the colormap and at position 0 only colors at table rows up to 128, no setting but the colormap, smoothing and beat changes the frames (threshold, note count, resolution, interpolate, gaussian and the circle settings given with extreme values leave the files byte-identical), the colormap is checked before anything is written and a bad colormap or note array (wrong shape, negative, NaN, fewer than 84 columns) refuses with nothing created; (e) the smoothing of `write_frames` applies (a note value smoothed from the frame before gives its smoothed step).
  - Done: `backend/tests/test_concentric.py` (130 tests at the end): the steps (exact `k * k / 144` for every k and just above, a rounding-noise test with three known noisy shares, the loudest 12, silent all 1, monotone, per frame, the four undrawn notes ignored, bad values refused), the ring colors (every colormap at positions 0, 0.25, 0.5 and 1, the whole colormap at the top and half way at the bottom, monotone, bad positions refused), the pixels (the 25 px radius, the background, every ring flat at a pixel wholly inside it for three notes and three positions, a smaller circle equal to a full one without its outer rings for every step, radius and center of circles of steps 1, 3, 6 and 12, no circle leaves its cell for all 84 notes, touching in a row, smooth mixed edges, **exactly equal to a brute-force drawing on a 4 x 4 canvas** for four random frames), the frames (names, RGB, size, determinism, position changes the picture, the last color at the top and nothing past the middle at the bottom, bad values refused before anything is written, no frames), and `write_frames` (smoothing and beat, the grid settings change nothing, the settings still checked, the other types still draw). One test of mine was wrong, not the code: other notes are dots, so the 'outside the cell' check compares with the silent picture.

### Implementation for User Story 1

- [x] T003 [US1] Create `backend/app/services/concentric.py` (module docstring: the picture, the steps, the rings and colors, the geometry that is worked out once, the supersampled edge identical to drawing the rings on a 4 x 4 canvas): `RINGS = 12`; `ring_steps(values)` (data-model.md: `clip(ceil(12 * sqrt(share) - 1e-9), 1, 12)`, `share` 0 when the frame's loudest is 0); `ring_colors(colormap, beat)`; the cached geometry per `(width, height)` (cells from `tile_edges` for the 12 x 7 grid, the full radius `min(smallest cell width, smallest cell height) / 2`, the 4 x 4 supersample classes with `np.hypot` distances from the cell centers, the two most frequent classes and the weight, an assertion that no pixel has a third class); `write_concentric_frames(values, colormap, directory, beat=None, width=IMAGE_WIDTH, height=IMAGE_HEIGHT)` (the checks first, then per frame the 84 x 13 color table, the two gathers and the blend, rounded to uint8, saved as `frame_<index>.png` with `compress_level=1` on the few-thread pool of the circles, the first worker error raised). Register the type: `IMAGE_TYPES` in `backend/app/services/image_types.py` (and its docstring: "a sixth, concentric, ...") and a branch in `write_frames` of `backend/app/services/frame_rendering.py` before the grid pipeline (every setting still checked; `smoothed[:, :SHOWN_NOTES]` and `beat` passed; returns); update the `write_frames` docstring. Run the tests of T002 and fix.
  - Done: `concentric.py`: `ring_steps`, `ring_colors`, the cached geometry (the two most frequent classes of the 4 x 4 sub-pixels, asserted to be at most two), `write_concentric_frames`; `IMAGE_TYPES` and its docstring; a branch in `write_frames`; its docstring. The prototype was exact (difference 0) and took 8.7 s for 1,800 frames.
- [x] T004 [US1] Run the whole backend suite (temporary default colormap) and fix the existing tests that the sixth type touches (lists of image types, loops over `IMAGE_TYPES` that assumed the grid pipeline, the refusal message with six names), keeping each test's meaning; the test counts must not drop.
  - Done: The whole backend suite after the registration: only two existing tests failed, both asserting the tuple of five types (updated, one by meaning: the first five stay in order); `test_image_types.py` and `test_image_type_api.py` gained one parametrized case each; no count dropped.
- [x] T005 [US1] Mutation checks, each caught by the tests and restored byte for byte (`scratchpad/mutate_024.py` with `more_025_us1.py`): the step with `round` or `floor` instead of `ceil`, without the square root, with 11 or 13 instead of 12, without the minimum of 1, against the file's loudest instead of the frame's, without the epsilon; the ring colors with `k / 12` instead of `(k - 1) / 11`, with the position weight 0.6, with the factor 1 instead of `0.5 + 0.5 * p`, with `floor` instead of `rint`, ring order reversed; the radius `R` 24 or 26, the center off by one pixel, the ring of a pixel with `floor` instead of `ceil`, the supersample factor 2 or 8, the weight of the second class inverted, a smaller circle's outer rings still drawn (step ignored), the background row 127, the cell of a pixel wrong, the table row of the background for ring 0 replaced by black.
  - Done: 24 mutations of the drawing (`scratchpad/mutate_024.py` with `more_025_us1.py`): 22 caught at once; the epsilon survived until a test with three known noisy shares was added (12 sqrt(share) is 9.000000000000002 for some values) and then was caught; the explicit colormap check is an equivalent mutant (`ring_colors` checks it again before anything is written).

**Checkpoint**: `write_frames(..., image_type="concentric")` draws the picture; the other types are unchanged.

---

## Phase 3: User Story 2 - Choose Concentric, tune the beat (Priority: P2)

**Goal**: The server measures the beat for every Concentric job; the page offers the sixth type with the Local peaks group (no checkbox) and Data smoothing and nothing of the grid settings.

**Independent Test**: Post a WAV with `image_type=concentric`: 200, 600 x 400 frames, the beat measured with `peak_distance` and `peak_prominence`; on the page choosing Concentric shows the five groups of the contract.

### Tests for User Story 2 (write first, they fail)

- [x] T006 [P] [US2] Create `backend/tests/test_concentric_api.py` (FR-001, FR-009 to FR-011, SC-005, SC-006; helpers as in `test_peak_tile_colors_api.py`: `post`, `pulse_wav`): `IMAGE_TYPES` has the six names in order and the refusal message lists them (`concentrics`, `Concentric`, empty refused); `image_type=concentric` is accepted for every colormap and echoed with the defaults (`beat_coloring` false, 100, 50); 600 x 400 RGB frames, the same count and timing as tiles for the same file; the beat is measured once with the two settings for every Concentric job, also with `beat_coloring=false` and `true` (spy on `measure_local_peaks`), and the frames of the two are byte-identical; the peak settings are checked before the file is read (no file needed) with the measurement's messages and nothing created, also for Concentric; different `peak_distance` or `peak_prominence` change the frames of a file where they change the beat; frames at the first loud click have ring 12 at (or near) the last color and frames before the first click stop at the middle of the colormap (decode the ring colors with a colormap whose rows are all different); the ignored settings (`threshold`, `note_count`, `resolution`, `interpolate`, `gaussian`, `blend_width`, the circle fields) are validated as before (bad values still refused) and have no effect (frames byte-identical with and without extreme values); smoothing applies; the five other image types are byte-identical with and without the Concentric code (compare with jobs of the same inputs run in the same test); the response keys are as for the other types.
  - Done: `backend/tests/test_concentric_api.py` (46 tests at the end): the six names and the message, refused names, every colormap with the defaults echoed, the same keys as tiles, 600 x 400 frames and the same count, the beat measured once with the two settings whatever the checkbox says (spy), the checkbox without effect on the frames, the peak settings refused before the file is read with nothing created, the beat changes the rings, the rings (before the first click ring 12 is row 128 within 2, at a loud click 235 or more, the center always row 0, the background), the tone is the biggest circle and quiet notes are dots, seven groups of ignored settings accepted and six still refused, smoothing, determinism, a silent file.
- [x] T007 [P] [US2] Frontend tests (vitest; no browser): `validation.test.ts` (`IMAGE_TYPES` has six entries ending with `{value: "concentric", label: "Concentric"}`, `validateImageType`, `imageTypeLabel("concentric")`, the refusal message lists six names, `gridSettingsApply("concentric")` false, `isCirclesType("concentric")` false, `beatColoringApplies("concentric")` false, a new `peakSettingsShown(imageType, beatColoring)` true for concentric always, for tiles and blended when the box is on, never for the others); `groups.test.ts` (the group `concentric-peaks` titled "Local peaks" with controls `["peak-distance", "peak-prominence"]`, `groupsFor("concentric")` equal to `["analysis", "colormap", "image-type", "concentric-peaks", "data-smoothing"]`, no other type has it, `groupOf("peak-distance", "concentric")` is `concentric-peaks`, `groupOf("beat-coloring", "concentric")` and the grid controls are undefined, `rowsOf(2)` is [2]; the existing expectations for the other types unchanged); `SettingsForm.test.ts` (SSR with `initialImageType="concentric"`: the five groups in order, the Local peaks group with both sliders and without the checkbox, no Threshold, Notes, Oversampling, Interpolate or Gaussian, no Image smoothing; Tiles still has the checkbox; the choices of the Image type select are the six labels; source guards that the group's id follows `shownGroups` and that the problem flag and the submit guard still cover the two errors); `App.test.ts` (the summary lines "Minimum distance:" and "Prominence:" show for concentric always and for tiles and blended with the box on, "Beat coloring:" not for concentric); `help.test.ts` (the Image type help describes Concentric: 84 circles, 12 rings, the beat, the middle color background).
  - Done: Frontend tests: validation (six types and labels, the refusal message, `gridSettingsApply`, `isCirclesType`, `beatColoringApplies`, the new `peakSettingsShown`), groups (twelve groups, `concentric-peaks`, the order for Concentric, no other type has it, `groupOf`), the form (six options, the five groups of Concentric in order, sliders without the checkbox, none of the grid controls, the checkbox kept for Tiles and Blended, the one group built for either id), the summary guards (the old 024 guard updated to the new rule), the Image type help. 19 tests added; 555 in all.

### Implementation for User Story 2

- [x] T008 [US2] Implement in `backend/app/routers/jobs.py`: the beat is measured when `image_type_value == "concentric"` or when it is `tiles` or `blended` with the box on (update the comment); nothing else changes (the fields, checks and response are as they are). Run the tests of T006 and fix.
  - Done: `jobs.py`: the beat is measured when the type is `concentric` or when it is tiles/blended with the box on; the comment updated. Nothing else changed.
- [x] T009 [US2] Implement the frontend: `frontend/src/utilities/validation.ts` (the sixth type, `gridSettingsApply` false for Concentric, `peakSettingsShown`), `groups.ts` (the group `concentric-peaks`, `groupsFor`, the doc comment), `help.ts` (the Image type help), `components/SettingsForm.vue` (one Local peaks group whose id is whichever of `local-peaks` and `concentric-peaks` is in `shownGroups`; the checkbox field only for `local-peaks`; the same two sliders), `App.vue` (the summary lines use `peakSettingsShown`). Run the tests of T007, then the frontend suite, `vue-tsc` and the build.
  - Done: Frontend: `validation.ts` (the type, `gridSettingsApply`, `peakSettingsShown`), `groups.ts` (`concentric-peaks`), `help.ts` (the Concentric sentence), `SettingsForm.vue` (`peaksGroup`: one group for either id, checkbox only for `local-peaks`), `App.vue` (`peakSettingsShown`). Typecheck and build clean.
- [x] T010 [US2] Mutation checks for the API and the page, each caught and restored: the beat measured only with the box on for Concentric, the beat measured for the other types, `peak_distance` and `peak_prominence` swapped, the checkbox shown for Concentric, the group shown for the wrong types, the grid groups shown for Concentric, the summary showing the two values for Contour, Threshold shown for Concentric, `gridSettingsApply` true for Concentric, the type missing from `IMAGE_TYPES` (frontend or backend), the label wrong, the help text without the description.
  - Done: 4 backend and 16 frontend mutations (`more_025_api.py`, `mutate_fe_025.py`); 19 caught at once, the one survivor (the help text's '12 rings' also appears elsewhere in the text) was caught after the test was made to look for 'a full circle is 12 rings'.

**Checkpoint**: Concentric can be chosen, tuned and created from the page and the API.

---

## Phase 4: User Story 3 - Quiet, silent and beat-less moments (Priority: P3)

**Goal**: The corners behave as the spec says through the whole pipeline.

**Independent Test**: Silent, beat-less and short files all make 600 x 400 Concentric frames without failing; the silent frames are 84 dots.

### Tests for User Story 3

- [x] T011 [US3] Add to `backend/tests/test_concentric.py` and `test_concentric_api.py` (spec Story 3, FR-005, SC-005): a silent file through the API makes frames in which every circle is step 1 (84 dots of ring 1's color on the background, radius about 2 px) and no failure; a file in which no beat is found (prominence 100 on a steady tone) has no ring past table row 128 in any frame; a file shorter than the peaks window; mono and stereo copies of the same sound make the same frames; a frame whose 84 notes are all equal and not zero has 84 full circles touching in rows; a frame of one sounding note has that note at step 12 and every other circle at step 1 (and the quiet notes of a real chord are in between); smoothing fills a silent frame between two loud ones from its neighbours (steps follow the smoothed values); the very last frame and a one-frame file.
  - Done: Corner tests: one sounding note is step 12 and the rest dots, a silent file is 84 dots exactly equal to the brute-force picture, a silent frame between two loud ones follows the smoothed values (exact against brute force), the last frame and a one-frame file, a file with no beat found has no ring past row 128, a file shorter than the peaks window, mono equals stereo, the position is held after the last click.

### Implementation for User Story 3

- [x] T012 [US3] Run the tests of T011 and fix whatever they find in `concentric.py`, `frame_rendering.py` or `jobs.py`; mutation checks, each caught and restored: a silent frame drawing nothing (no step-1 dots), a silent frame failing on the division, no beat given not meaning position 0, the loudest taken over 88 notes instead of the 84 drawn, a one-frame file failing.
  - Done: 4 mutations of the corners; 3 caught; 'a silent frame divides by zero' is an equivalent mutant (0 / 1e-300 is 0); no code change was needed.

**Checkpoint**: all three stories work together.

---

## Phase 5: Polish and cross-cutting

- [x] T013 [P] README (`README.md`, CRLF kept): the list of image types now has six (update the sentence that says five and the "Image type" bullet), a **Concentric** paragraph (since feature 025): the 84 circles, the full radius of 25 px, the steps and their formula, the rings and their colors with the position in the peak, the background, that ring 12 is the background's color at the bottom of the beat, the settings that apply (Local peaks without a checkbox, Data smoothing), the ignored ones, that the beat is always measured, the speed, and the page's groups.
  - Done: README (CRLF kept): the Image type bullet names six types, a **Concentric** paragraph (since feature 025) before the settings page paragraph.
- [x] T014 Final verification: the whole backend suite (temporary default colormap) with the per-file counts compared to T001 (nothing dropped), the frontend suite, typecheck and build, the four reference hashes equal to T001, `git status` showing only the files of this feature, the timing of quickstart section 4 (60 s at 30 frames a second, 1,800 frames), pictures of the same music at the strongest and at the lowest point of the beat and a silent frame (sent to the user), and a note in the report that the Spec Kit setup scripts could not be run. Mark all tasks `[x]` with a Done line each.
  - Done: Backend 3,768 tests pass (3,590 + 178 new: `test_concentric.py` 130, `test_concentric_api.py` 46, one case each in `test_image_types.py` and `test_image_type_api.py`; no other file's count changed), frontend 555 pass (536 + 19), typecheck and build clean, the four reference hashes equal, `git status` shows only this feature's files; a 60 s file at 30 frames a second (1,800 frames) takes 8.2 s through the API (tiles 1.2 s); a picture of the same note values at beat positions 0, 0.5 and 1 was sent to the user. The Spec Kit setup scripts could not be run (PowerShell execution policy), so `plan.md` and `tasks.md` were written by hand.

---

## Dependencies and order

- T001 first. T002 is written before T003; T004 and T005 after T003.
- US2 needs US1: T006 and T007 may be written in parallel with each other; T008 needs T003; T009 needs T007; T010 after T008 and T009.
- US3 needs US2 (it tests through the API): T011 then T012.
- T013 any time after T009; T014 last.

## Parallel opportunities

- T006 and T007 (backend and frontend tests); T013 alongside T010 to T012.

## Implementation strategy

MVP is US1: the picture on plain arrays and through `write_frames`. US2 makes it reachable (the API and the page) and fixes which settings apply. US3 pins the corners. No existing picture can change in any phase, so each phase can be verified against the four reference hashes.
