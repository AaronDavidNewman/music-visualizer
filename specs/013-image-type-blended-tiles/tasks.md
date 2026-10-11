---

description: "Task list for Image Type (Blended Tiles)"
---

# Tasks: Image Type (Blended Tiles)

**Input**: Design documents from `/specs/013-image-type-blended-tiles/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/image-type-api.md, quickstart.md

**Tests**: Included, following the plan: pytest for the blend function against an independent reference, the frame writer and the API, and vitest for the new validation, texts and the rendered controls. Behavior in a real browser is checked by the quickstart steps.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root. Backend commands run in `backend/` with the venv's Python (`.venv/Scripts/python -m pytest`), frontend commands in `frontend/`. The API fields are `image_type` (`tiles` or `blended`, default `tiles`) and `blend_width` (10 to 25, default 25).

**Working notes** (learned in features 010 to 012): do not use `git stash` to compare with old code (it emptied the index once; use the saved reference run instead); keep each existing file's line endings (many files are CRLF) when editing from a script; write helper scripts to files with the Write tool rather than shell heredocs that contain backticks (the shell runs them as commands); do not run a bare `cat >` in a command (it waits for input and hangs).

**Change on 2026-10-10**: after these tasks were completed the fade's shape was changed from a straight ramp to a Gaussian feather (spec Clarifications; `feather_weight` in `image_types.py`). Task descriptions below that say "linear" or give the ramp formula describe the first version.

**Known risk** (research Decision 5): planning measured a blended frame at about 1.4 ms against 0.33 ms for a tiles frame, which projects to about three times the time of a tiles job. The spec's SC-006 says at most twice. Do not change the spec to fit: measure the real code (T004 and T021), and if the job time is more than twice, report the numbers to the user with a proposed realistic bound and let them decide.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2 or US3

## Phase 1: Setup

- [x] T001 Run `pytest` in `backend/` and `npm test`, `npm run typecheck` and `npm run build` in `frontend/` to confirm a green baseline before changing anything (957 backend and 257 frontend tests at the end of feature 012), and note the numbers. Run the reference script `baseline.py` from the session scratchpad (it creates frames for a fixed 4 s multi-note file through the test client and prints a combined hash of all frames; the recorded hash with default settings is `2688e9c214af0555e279e1171ce578b468b29fda5847c11df19b1a70049d88b2`) and confirm the same hash, so the tiles output can be compared with it later (SC-001)
  - Done: 957 backend and 257 frontend tests passed, typecheck and build clean; the reference hash was `2688e9c2…` as recorded.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The blend itself, in one tested place with its limits and checks, and an early measurement of what it costs.

- [x] T002 Create `backend/app/services/image_types.py` per data-model.md and research Decisions 1 to 4: constants `IMAGE_TYPES = ("tiles", "blended")`, `DEFAULT_IMAGE_TYPE = "tiles"`, `MIN_BLEND_WIDTH = 10`, `MAX_BLEND_WIDTH = 25`, `DEFAULT_BLEND_WIDTH = 25`; `check_image_type(value) -> str` (must be a `str` exactly equal to one of `IMAGE_TYPES`, no trimming or case folding, else `ValueError(f"The image type must be one of {', '.join(IMAGE_TYPES)}.")`, i.e. `The image type must be one of tiles, blended.`); `check_blend_width(value) -> float` (a real number, not a bool, finite, from 10 to 25 inclusive, else `ValueError("The blend width must be a number from 10 to 25.")`); `axis_weights(size, tile, count, reach)` returning, for each pixel along one axis, the own tile index, the neighbor tile index and the own weight per "Weights along one axis" (distance measured from the pixel's center to the nearest *inner* edge; own weight `0.5 + d / (2 * reach)` when `d < reach`, else 1 with the neighbor equal to the own tile; first and last tiles have no inner edge on their outer side); and `make_blender(blend_width, columns, rows, tile_width, tile_height)` returning a function that takes the finished colors (`uint8`, shape `(rows * columns, 3)`, tile `(r, c)` at index `columns * r + c`) and returns the picture (`uint8`, shape `(rows * tile_height, columns * tile_width, 3)`) using two passes in `float32`: expand the columns of the `(rows, columns, 3)` grid to the full width, then the rows, then `np.rint` and `astype(np.uint8)`; the reach is `blend_width / 100 * tile_width` pixels in both directions and the index/weight arrays are computed once, when the blender is made. Also add `blend_tile_colors(colors, blend_width, columns, rows, tile_width, tile_height)` as a convenience that makes a blender and applies it once. The module must not import from `frame_rendering.py`. Docstrings: the weights, that the picture's border is not blended, that outside the bands pixels are exactly their tile's color
- [x] T003 [P] Create `backend/tests/test_image_types.py` for `app/services/image_types.py`. Use an independent, deliberately naive per-pixel reference written in the test (for every pixel: find the nearest inner edge on each axis with plain arithmetic, compute the four weights, mix with Python floats, round) on a 12 × 7 grid of 21 × 24 tiles; check: constants; the blender agrees with the reference to within 1 level at every pixel for random tile colors (about 60 percent of tiles black) at widths 10, 15, 20, 25 and 12.5; pixels farther than the reach from every inner edge equal their tile's color exactly (all widths); the two pixels on either side of an inner edge average to the even mix of the two tiles' colors within 1 level in every channel (both vertical and horizontal edges, all widths); monotone change with no overshoot across a band in every channel; a frame whose tiles share one color and an all-black frame come back unchanged (flat); at a point where four tiles meet the average of the four pixels around it is the 25 percent mix; the picture's border is not blended (the outermost pixels equal their tile's color, and the first and last columns/rows of tiles are flat on the outer side); the last tile of a row does not blend with the first tile of the next row; a black tile fades with a colored neighbor; every output channel lies between the minimum and maximum of the tile colors in its 2 × 2 neighborhood; for widths 10 to 25 in steps of 1 the number of pixels whose color differs from their tile's color never decreases as the width grows, and is larger at 25 than at 10; output shape `(168, 252, 3)` and dtype `uint8`; the input is not modified; two calls give identical results; `check_image_type` accepts `tiles` and `blended` and refuses `""`, `"Tiles"`, `" tiles"`, `"tiles "`, `"gradient"`, `None`, `1` with the exact message; `check_blend_width` accepts 10, 25, 12.5, `np.int64(20)` and refuses 9.99, 25.01, 0, -1, `True`, `float("nan")`, `float("inf")`, `"15"`, `None` with the exact message
  - Done: 48 tests. One sanity assertion of mine was wrong (at 25 percent the flat middles are about 36 percent of the picture, not over 40); the check now computes the expected share.
- [x] T004 Measure the cost of the real blender (research Decision 5): with a scratchpad script (write it with the Write tool), time 300 random frames through (a) `_palette_frame(...).save(..., compress_level=6)` as tiles are written today, (b) `make_blender(25, 12, 7, 21, 24)` alone, and (c) the blender plus `Image.fromarray(..., "RGB").save(..., compress_level=1)`; print milliseconds per frame and the ratio to (a), and the file sizes. Expected from the prototype: (a) about 0.33 ms, (b) about 0.55 ms, (c) about 1.4 ms (about 4 times (a)). Record the numbers under this task. If (c) is much higher than the prototype, find out why before going on (for example float64 instead of float32, or per-frame index arrays being rebuilt)
  - Done, real code: tiles frame 0.25 ms; blender arithmetic 0.61 ms; blended frame with the RGB PNG at level 1 1.39 ms (5.7 times a tiles frame; 23 KB against 1 KB), at level 6 1.71 ms (15 KB). As in the prototype, the PNG encoder is more than half of the cost.

**Checkpoint**: `pytest backend/tests/test_image_types.py` passes and the per-frame cost is known; nothing else has changed.

---

## Phase 3: User Story 1 - Get frames whose tiles blend into each other (Priority: P1) 🎯 MVP

**Goal**: Frames can be made as blended tiles through the job API, with `tiles` (the default) changing nothing (FR-001 to FR-009, FR-011 to FR-013, FR-016).

**Independent Test**: Quickstart "Story 1". The same file made as tiles and as blended tiles has the same size and frame count; in the blended frames the middle of every tile has the tile's color and the colors fade across the edges.

### Tests for User Story 1

- [x] T005 [P] [US1] In `backend/tests/test_frame_rendering.py` add tests for `write_frames` with the new arguments (append; the file has CRLF line endings; reuse its `LEVEL_FRAMES`, `LEVEL_ENERGIES`, `tile_rgb`, `written_tiles`, `frame_files` helpers): `image_type="tiles"` and no argument write byte-identical files, also with `blend_width` set to 10 and 25 (SC-001, FR-015 effect); `image_type="blended"` writes the same number of files with the same names; each blended file is an RGB PNG of 252 × 168 (check with Pillow) and each tiles file is still a palette PNG; in every blended frame the center pixel of each of the 84 tiles equals the same tile's center pixel in the tiles frame (SC-005, use `tile_rgb`); a frame set with all tiles equal and a silent frame set (zero energies) are pixel-identical between the types; two runs give identical files; invalid arguments (`image_type` of `"Tiles"`, `""`, `None`, `3`; `blend_width` of 9, 26, `nan`, `True`, `"15"`) raise `ValueError` with the exact messages before anything is written (the directory has no PNG files)
- [x] T006 [P] [US1] Create `backend/tests/test_image_type_api.py` for the fields, in the style of `test_threshold_api.py` (import `client`, `frame_rgb`, `leftovers`, `wav_bytes`, `burst_then_silence` and the like from `test_jobs_api`): `image_type` values `tiles` and `blended` are accepted and echoed; a request without the field returns `tiles`, and the frames equal those of a request that sends `tiles`; refused with 400 and the exact detail `The image type must be one of tiles, blended.` for empty, `Tiles`, `BLENDED`, ` tiles`, `gradient`, `1`, with no job created (the temp directories are unchanged); `blend_width` values `10`, `25`, `15`, `12.5`, `15.0`, ` 20 ` are accepted and echoed (a whole number comes back as an integer, `12.5` as `12.5`); a request without it returns `25`; refused with 400 and the exact detail `The blend width must be a number from 10 to 25.` for empty, ` `, `9`, `9.99`, `25.01`, `26`, `0`, `-10`, `100`, `abc`, `nan`, `inf`, `1e9`, `15%`, with no job created; both fields are checked before the file is read (a non-audio body with `image_type=x` and with `blend_width=99` each gets its own message); with `image_type=tiles` any valid `blend_width` is accepted and the frames are byte-identical for widths 10 and 25; with a generated multi-note WAV a blended frame has the same size as a tiles frame and the same frame count, and the middle of every tile has the tiles frame's color; the same blended request twice gives identical frame bytes
  - Done in `backend/tests/test_image_type_api.py` (a new file, so the shared `post` helper stays unchanged).

### Implementation for User Story 1

- [x] T007 [US1] In `backend/app/services/frame_rendering.py` import from `image_types.py` (`DEFAULT_BLEND_WIDTH`, `DEFAULT_IMAGE_TYPE`, `check_blend_width`, `check_image_type`, `make_blender`) and give `write_frames` two optional keywords `image_type: str = DEFAULT_IMAGE_TYPE` and `blend_width: float = DEFAULT_BLEND_WIDTH`, validated up front with the other checks (before anything is written). When the type is `blended`, build the blender once before the loop with `make_blender(blend_width, GRID_COLUMNS, GRID_ROWS, TILE_WIDTH, TILE_HEIGHT)` and, for each frame, save `Image.fromarray(blender(colours), "RGB")` with `compress_level=1`; when the type is `tiles` keep the existing line `_palette_frame(colours).save(..., compress_level=6)` exactly as it is. Update the docstring of `write_frames` and the module docstring (one sentence each). Make T005 pass
- [x] T008 [US1] In `backend/app/routers/jobs.py` add `_parse_image_type(text, sent) -> str` (not sent gives `DEFAULT_IMAGE_TYPE`; sent must equal one of `IMAGE_TYPES` exactly, else `HTTPException(400, "The image type must be one of tiles, blended.")`) and `_parse_blend_width(text, sent) -> int | float` (not sent gives `DEFAULT_BLEND_WIDTH`; sent must parse as a finite float from `MIN_BLEND_WIDTH` to `MAX_BLEND_WIDTH`, else `HTTPException(400, "The blend width must be a number from 10 to 25.")`; return an `int` for a whole number), in the style of `_parse_threshold`. Add the form fields `image_type: str | None = Form(None)` and `blend_width: str | None = Form(None)` to `create_job`, parse them next to the other settings (before the file is read), pass `image_type=...` and `blend_width=...` to `write_frames`, add `"image_type"` and `"blend_width"` to the response (always both), and update the comment above `write_frames`. Make T006 pass
- [x] T009 [US1] In `backend/tests/test_energy_api.py` add `"image_type"` and `"blend_width"` to the expected response keys in `test_the_other_response_fields_are_unchanged` (an intended addition). Run `pytest` in `backend/` and confirm everything passes. Then run the reference script from T001 with no `image_type` field, with `image_type=tiles` and with `image_type=tiles` plus `blend_width=10`, and confirm all three hashes are identical to the recorded one (SC-001)
  - Done: 1061 backend tests passed at this point; the reference script gave the identical hash with no `image_type`, with `image_type=tiles`, and with `image_type=tiles` plus `blend_width=10`; `blended` gives a different hash, as it should.

**Checkpoint**: The API makes blended frames and, with the defaults, produces exactly the old frames.

---

## Phase 4: User Story 2 - Choose the image type on the page and see what was used (Priority: P2)

**Goal**: An Image type dropdown, a Blend width slider, their explanations and summary lines (FR-010, FR-015, FR-016).

**Independent Test**: Quickstart "Story 2". Open the page, choose Blended tiles, move the slider, create frames, see both settings in the summary.

### Tests for User Story 2

- [x] T010 [P] [US2] In `frontend/src/utilities/validation.test.ts` add tests for the new helpers from `validation.ts` (written in T012; keep CRLF): `IMAGE_TYPES` is exactly `tiles`/`Tiles` and `blended`/`Blended tiles` in that order and `DEFAULT_IMAGE_TYPE` is `"tiles"`; `imageTypeLabel("tiles")` is `"Tiles"` and `imageTypeLabel("blended")` is `"Blended tiles"`; `validateImageType` returns `null` for `"tiles"` and `"blended"` and `The image type must be one of tiles, blended.` for `""`, `"Tiles"`, `" blended"`, `"gradient"`; `BLEND_WIDTH_RANGE` is `{ min: 10, max: 25, step: 1 }` and `DEFAULT_BLEND_WIDTH` is 25; `validateBlendWidth` returns `null` for 10, 25, 17, `"12.5"`, `"20"` and `The blend width must be a number from 10 to 25.` for 9.99, 26, 0, `""`, `"  "`, `"abc"`, `"NaN"`, `"Infinity"`, `"15%"`; `formatBlendWidth(25)` is `"25% of a tile"` and `formatBlendWidth(12.5)` is `"12.5% of a tile"`; `formatBlendWidthSummary(15)` is `"15%"`
- [x] T011 [P] [US2] In `frontend/src/utilities/help.test.ts` add tests that `imageTypeHelp` says what both types look like (flat tiles with hard edges; blended tiles whose colors fade into each other across the edges) and `blendWidthHelp` says it is how far the fade reaches on each side of an edge, as a share of a tile, the range 10 to 25, and that it only applies to Blended tiles; in `frontend/src/components/SettingsForm.test.ts` add tests (using the existing `render` helper) that the rendered form has a select with id `image-type` offering `Tiles` then `Blended tiles` with `Tiles` selected, a label "Image type" and an info button named "About image type"; a range input with id `blend-width` with `min="10"`, `max="25"`, `step="1"` and value 25, a label "Blend width" and an info button named "About blend width"; the readout "25% of a tile"; the select is disabled when `busy` is true and not otherwise; the slider is disabled by default (Tiles is selected) and when `busy`; and that both controls come after the Threshold field

### Implementation for User Story 2

- [x] T012 [US2] In `frontend/src/utilities/validation.ts` add `IMAGE_TYPES` (an array of `{ value, label }` for `tiles`/`Tiles` and `blended`/`Blended tiles`), `DEFAULT_IMAGE_TYPE = "tiles"`, `imageTypeLabel(value)`, `validateImageType(value)`, `BLEND_WIDTH_RANGE = { min: 10, max: 25, step: 1 } as const`, `DEFAULT_BLEND_WIDTH = BLEND_WIDTH_RANGE.max`, `validateBlendWidth(value)` (finite number from 10 to 25, in the style of `validateThreshold`), `formatBlendWidth(value)` (`` `${n}% of a tile` `` with no floating-point noise) and `formatBlendWidthSummary(value)` (`` `${n}%` ``). Make T010 pass
- [x] T013 [US2] In `frontend/src/utilities/help.ts` add `imageTypeHelp` and `blendWidthHelp` built from the constants, as described in T011. Make the help part of T011 pass
- [x] T014 [P] [US2] In `frontend/src/api.ts` add `image_type: string` and `blend_width: number` to `JobResult` and `imageType: string` and `blendWidth: number` to `JobSettings`, and append `image_type` and `blend_width` to the form in `submitJob`
- [x] T015 [US2] In `frontend/src/components/SettingsForm.vue` add `imageType` (string ref, default `DEFAULT_IMAGE_TYPE`) and `blendWidth` (number ref, default `DEFAULT_BLEND_WIDTH`), errors from `validateImageType` and `validateBlendWidth` included in `canSubmit`, and emit `imageType` and `blendWidth`. After the Threshold field add an Image type `<select>` (`id="image-type"`, options from `IMAGE_TYPES`, `:disabled="busy"`, label "Image type", an `InfoPopover` labelled "image type" with `imageTypeHelp`) and a Blend width slider built like the Threshold slider (`id="blend-width"`, `THRESHOLD`-style range input from `BLEND_WIDTH_RANGE`, `:disabled="busy || imageType === 'tiles'"`, a readout `formatBlendWidth(blendWidth)`, an `InfoPopover` labelled "blend width" with `blendWidthHelp`, an inline error line). Make the rest of T011 pass
- [x] T016 [US2] In `frontend/src/App.vue` add the summary items `Image type: {{ imageTypeLabel(result.image_type) }}` and, only when `result.image_type === 'blended'`, `Blend width: {{ formatBlendWidthSummary(result.blend_width) }}` after Threshold (import the helpers). Run `npm test`, `npm run typecheck` and `npm run build` in `frontend/` and confirm all pass
  - Done: 290 frontend tests, typecheck and build pass; the form renders both controls (server-side render test), but see T022.

**Checkpoint**: The image type and blend width can be set on the page and are shown in the summary.

---

## Phase 5: User Story 3 - The new picture works with every other setting and stays practical (Priority: P3)

**Goal**: The blend is made from the finished colors for every combination of the other settings, and the pictures are served like the others (FR-004, FR-012; SC-003 to SC-005).

**Independent Test**: Quickstart "Story 3". With Saturation steps 20, Threshold 5 and smoothing 0.5 window 3 the middles of the blended tiles equal the tiles pictures' colors and the edges show fades.

- [x] T017 [P] [US3] In `backend/tests/test_frame_rendering.py` add interaction tests on `write_frames` (append; CRLF): for each of these option sets, the center pixel of every one of the 84 tiles in every blended frame equals the same tile's center pixel in the tiles frame made with the same options, and every blended pixel lies between the minimum and maximum of the tile colors in its 2 × 2 neighborhood in that frame (read the tile colors from the tiles frame): `smoothing=0.5, smoothing_window=3`; `brightness=4` with `energy_root=3`; `hue_step=36, saturation_step=10, value_step=20`; `threshold=5`; all of them together; also `hue_step=180, saturation_step=50, value_step=50` (few colors, strong edges). Add a test that a tile hidden by the threshold (black) next to a colored tile fades toward black at the shared edge in the blended frame (compute the expected mid-edge value from the two tile colors); and that the blend does not round to the level steps (a blended frame made with `saturation_step=50` contains saturations other than 0, 0.5 and 1 on its edges while the tile middles have only those)
  - Done. A mutation check (a wrong divisor in the weight on one side of each edge) made 11 tests fail, then was reverted.
- [x] T018 [P] [US3] In `backend/tests/test_image_type_api.py` add API tests: a served blended frame is an RGB PNG of 252 × 168 and a served tiles frame is still a palette PNG of the same size (open both with Pillow); both are served with `image/png` and the same `Cache-Control` header; the frame count and the response fields other than the two new ones are identical between a tiles request and a blended request for the same file and settings; one request with `smoothing=0.5`, `smoothing_window=3`, `saturation_step=20`, `brightness_step=50`, `threshold=5` and `image_type=blended` has, in the middle of every tile of a sample of frames, exactly the colors of the same request with `image_type=tiles`

**Checkpoint**: Combinations behave as specified. A failure here points at what `write_frames` passes to the blender.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T019 [P] Update `README.md`: add an **Image type** bullet (the two types and their names, the default; how a frame is turned into pixels for each; the blended tiles picture: a linear alpha-blend of the finished tile colors across every shared tile edge, tile middles exactly flat, even 50/50 at the edge, four-tile product weights at corners, the outer border not blended, rows not wrapping, black tiles blending like any other, true-color PNG files that are larger and slower than the tiles files, same size 252 × 168 and the same frame count and timing; the API field `image_type` with its 400 message and the response field) and a **Blend width** bullet (10 to 25 percent of the tile width of 21 pixels, default 25, the reach on each side of an edge in pixels = percent × 21 / 100 in both directions, only used by blended tiles, the page slider disabled for Tiles, the API field `blend_width` with its 400 message and the response field). Update the paragraph that describes the image (the tile grid) so it says that is the `tiles` type. Mention `specs/013-image-type-blended-tiles/data-model.md`
- [x] T020 Run everything: `pytest` in `backend/`, `npm test`, `npm run typecheck` and `npm run build` in `frontend/`; all must pass. Report the final test counts against the T001 baseline, and the reference script's hash with the default settings (it must still equal the recorded one)
  - Done: backend 957 → 1073 tests, frontend 257 → 290 tests, all passing; typecheck and build clean; reference hash unchanged.
- [x] T021 Measure performance (SC-006) on the real application: with a scratchpad script (adapt `perf.py` or `perf012.py` from the session scratchpad, written with the Write tool) create frames from the 60 s test file (1,800 frames) through the test client as `image_type=tiles` and as `image_type=blended` (also at blend widths 10 and 25), median of at least 7 interleaved runs, and report both times and the ratio. SC-006 asks for at most twice the tiles time. If the ratio is above 2, do not edit the spec: record the numbers here, mention it prominently in the report to the user with the proposed bound from research Decision 5 (for example a 60 s file at 30 fps within 5 seconds and at most four times the tiles job), and leave the decision to the user
  - Done, whole job on the 60 s test file (1,800 frames), 7 interleaved runs, medians. First version (frames blended and written one after the other): tiles 0.99 s, blended width 10 3.10 s (3.14 times), width 25 3.73 s (3.78 times), above the target of twice. Then the blending and PNG encoding of the frames was moved onto a small pool of threads (`_BLEND_WORKERS = min(4, cpu count)` in `frame_rendering.py`, blended type only; the tiles path is untouched; a test checks the files equal a plain blend and that a worker error is raised and the pool shut down): tiles 1.02 s, blended width 10 1.04 s (1.02 times), width 25 1.35 s (1.33 times). SC-006 is met on this machine (24 cores) without changing the spec; with fewer cores the gain is smaller.
- [ ] T022 Follow `specs/013-image-type-blended-tiles/quickstart.md` Stories 1 to 3 in the running application (a real browser, if one can be used), including the refused-request examples. If a browser cannot be used, say so explicitly in the report and leave this task unchecked with a note of what was verified through tests and direct API calls instead
  - NOT done: the walk-through in a real browser (choosing Blended tiles, moving the slider, the disabled state for Tiles, the popovers, the summary, watching the fades in the player). Verified instead through tests and direct API calls: the dropdown's options and start value, the slider's range, step, start value, readout and disabled states, the labels and info buttons and their order in the rendered form; the fields' validation and refusals; and the frames (size, format, tile middles, fades, edges, border, corners).

---

## Dependencies & Execution Order

- Phase 1 first. Phase 2 blocks the stories: T002, then T003 and T004 (T003 is a test file, T004 a scratchpad measurement; they are independent of each other).
- **US1 (Phase 3)** needs Phase 2. T005 and T006 are written first (they fail until T007 and T008); T007 before T008 (the router passes the new arguments); T009 last.
- **US2 (Phase 4)** can start after Phase 2 and run in parallel with US1 (frontend vs backend files); the end-to-end check in T016 needs the API fields from T008. T012 before T013 and T015; T014 before T015 and T016.
- **US3 (Phase 5)** needs T007 and T008. T017 and T018 are independent.
- **Polish** last; T019 can be done any time after T008 and T015.

### Parallel opportunities

- T003 and T004 after T002; T005 and T006 (different test files); the frontend track (T010 to T016) alongside the backend track after Phase 2; T017 and T018; T019 with T020's preparation.

## Implementation Strategy

- **MVP**: Phases 1 to 3 (US1). The API makes blended frames and the defaults leave the tiles output unchanged; the type can be tried with curl or the API docs.
- Then US2 puts the controls on the page and US3 locks in the interactions with the other settings and the served files.
- Keep the change reviewable: one new module, `write_frames` gains two optional arguments and one extra branch at the point where a file is saved, the tiles branch is not touched (that is what keeps its output byte-identical), and the note analysis, the color rules and the frame player are not changed.
- The performance target is the one thing that may need a decision from the user; find out early (T004), not at the end.
