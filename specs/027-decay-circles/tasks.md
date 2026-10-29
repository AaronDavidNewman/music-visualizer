---

description: "Task list for Decay (feature 027)"
---

# Tasks: Decay

**Input**: Design documents from `/specs/027-decay-circles/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/decay.md, quickstart.md

**Tests**: Written first for each story (the project's practice): the point rules as numbers, the picture at the pixel level, the API, and the page's group, slider, summary and request (server-side rendering and source guards, as in features 025 and 026). The look in the player is the manual step of the quickstart.

**Organization**: By user story: US1 the points, the drawing and `write_frames` (P1), US2 the server field and the page (P2), US3 the corner cases (P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- Paths are from the repository root. Edit files with their line endings preserved. Backend tests run from `backend/` (`.venv` active), frontend tests from `frontend/`.

---

## Phase 1: Setup

- [x] T001 Record the baseline before changing anything: run `python -m pytest -q` in `backend/` and `npm test`, `npm run build` in `frontend/`, and note the counts; compute the reference hashes of the six existing image types for the test file used by the earlier features (the four hashes `6819990556fd4095`, `f32a99c59fcb87fc`, `92b3a27dee73e223`, `400cc93e1bfca03d` and the Concentric and Spiral hashes in `backend/tests/test_concentric_api.py` and `backend/tests/test_note_layout_api.py`); `grep -rn "circles_paint, concentric\|concentric\"" backend/tests frontend/src` to list the tests that name the image types or the response keys (they will need `decay` and `decay_rate` added).

---

## Phase 2: User Story 1 - Circles that charge up on loud notes and bleed into their neighbours (Priority: P1) 🎯 MVP

**Goal**: `decay.py` (gains, decay step, the points of all frames, radius, color, the frames) and `write_frames(image_type="decay", decay_rate=...)`.

**Independent Test**: `write_frames(values, ..., image_type="decay", decay_rate=5, beat=None)` with one steady loud note: that note's circle reaches full size and the last color and stays; after the note stops it fades; corner circles fade faster than interior ones.

### Tests for User Story 1 (write first, they fail)

- [x] T002 [P] [US1] Create `backend/tests/test_decay.py` for the points (spec FR-003, FR-006 to FR-008, SC-002 to SC-004), with values `(frames, 84)` and the `note_layout="rows"` unless said:
  - `check_decay_rate`: 1 to 10 whole numbers accepted (also `5.0` returned as `5`); `0`, `11`, `2.5`, `True`, `"5"`, `None`, `nan`, `inf` refused with `The decay rate must be a whole number from 1 to 10.`; `DEFAULT_DECAY_RATE` is 5.
  - `gains(values, beat)` (note order, shape `(frames, 84)`): the five loudest notes get exactly 24, 20, 16, 12, 8 with `beat=None`; with `beat=[1.0]` they get 32, 28, 24, 20, 16 and with `[0.5]` 28, 24, 20, 16, 12; all other notes 0; ties: equal values rank the lower note first; notes with value 0 never gain (a frame with 3 sounding notes gains 24, 20, 16 only); a silent frame gains nothing even with `beat=1`; columns after the 84th are ignored; the input is not changed; negative or non-finite values and a bad shape refused.
  - `circle_points` with a single frame: the gain lands on the loudest note's cell (rows: cell = note); points are held at 64 (a note kept loud at 24+8 per frame reaches 64 and stays 64) and never below 0.
  - The decay step (use a rate of 1 and one frame with the points set up by a first frame of gains; or test the step function it is built from directly — name it `decay_step(points_7x12)` and have the tests call it): an interior cell with 30 points and all others 0 ends at 14 and each of its 8 neighbours at 2; an edge cell with 30 points (5 neighbours) ends at 14, each neighbour 2 (10 sent, 6 vanished); a corner cell with 30 points (3 neighbours) ends at 14 and each neighbour 2 (6 sent, 10 vanished); a cell with 8 points (fewer than 16) ends at 0 and each interior neighbour gets 1 (half of 2) and the sum sent is 8 for an interior cell, 5 for an edge (5 × 1), 3 for a corner; a cell with exactly 16 ends at 0 and neighbours get 2; simultaneity: two adjacent cells with 30 and 30 points end at `30 − 16 + 2 = 16` each (a cell receives from its neighbour the 2 points worked out from the points before the step); a receiving cell at 63 with a neighbour sending 2 ends at 64, never above; the sum of all points never grows over random grids (200 random 7 × 12 grids of 0 to 64); no cell is below 0 or above 64 after a step over the same random grids; the grid does not wrap (the right edge cell does not give to the left edge cell).
  - The interval: with `decay_rate=3` and a single gain in frame 1 (then silence), the points are unchanged in frames 1 and 2, decay after frame 3, unchanged in 4 and 5, decay after 6; with rate 1 it decays every frame; with rate 10 first at frame 10; frames are counted from 1.
  - Spiral: `circle_points(..., note_layout="spiral")` puts the gain of middle C (note 27) at cell (row 2, column 5), and a gain next to it spreads to the cells around it on the grid, whatever notes those hold; the **ranking** is in note order (two equal notes: the lower note wins, also in the spiral).
  - Long silence: after a loud passage and then 300 silent frames at rate 1 every cell is exactly 0 within 200 decay steps; determinism (two runs equal); the input is not changed.
  - `circle_radii(points)`: 0 → `25/12` px, 24 → 25, 30 → 25, 12 → `25 × (1/12 + 11/12 × 0.5)`, linear between; `circle_colors(points, colormap)`: 0 → table row 0, 32 and 64 → row 255, 16 → row `rint(127.5) = 128`, for several colormaps.
- [x] T003 [P] [US1] Create `backend/tests/test_decay_rendering.py` for the pictures (spec FR-002, FR-004, FR-005, FR-012, SC-001, SC-005, SC-006): PNG files `frame_000000.png` and up, 600 × 400 RGB, one per frame; background pixels (a cell corner) are the colormap's middle color; for a frame whose points are known (use `write_decay_frames(points, ...)` directly with chosen points), the pixel at the center of cell `(r, c)` is the color for its points and the width of the disc measured along the cell's middle row is `2 × radius` within a pixel, for points 0, 6, 12, 24, 40, 64 and several colormaps; no pixel outside a cell's disc (distance from the center greater than the radius plus 1) differs from the background; edges are antialiased (some pixel on the border is neither the background nor the circle color); the full-size circle (24 points) just touches its row neighbours (radius 25, centers 50 apart) and never leaves its cell; the picture is the same for the same points on two runs; `write_frames(..., image_type="decay")` for a synthetic stream equals `write_decay_frames(circle_points(...))` byte for byte; with `note_layout="spiral"` the first circle appears at the cell of the table; `write_frames` ignores `threshold`, `note_count`, `resolution`, `interpolate`, `gaussian`, `blend_width`, the circle settings (frames byte-identical whatever their values); a bad `decay_rate` or `note_layout` is refused before anything is written, for every image type; `decay_rate` has no effect on the other six types (byte-identical frames); the other six types give byte-identical frames to those made before (compare Concentric and Tiles with the reference hashes from T001).

### Implementation for User Story 1

- [x] T004 [US1] Create `backend/app/services/decay.py` (module docstring: what a Decay picture is, the points, the gains, the decay step with its edge rule, why the points are worked out first, that the ranking is in note order and the neighbours in cell order; it knows nothing about audio or the beat measurement). Contents, from research Decisions 1 to 5: `MIN_DECAY_RATE = 1`, `MAX_DECAY_RATE = 10`, `DEFAULT_DECAY_RATE = 5`, `MAX_POINTS = 64`, `GAINS = (24, 20, 16, 12, 8)`, `BEAT_BONUS = 8`, `GIVE = 2`, `LOSS = 16`, `SIZE_POINTS = 24`, `COLOR_POINTS = 32`; `check_decay_rate(value) -> int` (whole number 1 to 10; booleans, non-integers, non-finite and non-numbers refused with `The decay rate must be a whole number from 1 to 10.`); `gains(values, beat)` (stable `argsort` on `-value`, notes with value 0 skipped, positions from `check_beat`, `None` = 0); `decay_step(points)` on a `(7, 12)` array: `give = np.minimum(points, 16)`, `share = give / 16`, the eight shifted copies of the zero-padded `share` summed, `np.clip(points − give + 2 × neighbours, 0, 64)`, returning a new array; `circle_points(values, beat, note_layout, decay_rate)`: `arrange_notes(gains(values, beat), note_layout)` reshaped to `(frames, 7, 12)`, then for each frame `i` from 1: `points = clip(points + gain, 0, 64)`, `decay_step` if `i % decay_rate == 0`, record; return `(frames, 84)` float64; `circle_radii(points)` → `FULL × (1/12 + 11/12 × min(points, 24) / 24)` with `FULL` the full radius of Concentric (import the radius rule from the geometry shared with `concentric.py`: factor `_full_radius(width, height)` out of `concentric._geometry` if it is not already a function, without changing Concentric's output); `circle_colors(points, colormap)` → table rows `rint(min(points, 32) / 32 × 255)`; `_geometry(width, height)` (cached): `cell` index and `distance` (float32) per pixel, from `tile_edges` and the cell centers as in `concentric._geometry`; `write_decay_frames(points, colormap, directory, width, height)`: per frame `radius`, `color` per cell, `coverage = clip(radius[cell] − distance + 0.5, 0, 1)`, `rint(background × (1 − coverage) + color[cell] × coverage)`, saved with Pillow on the same thread pool and `compress_level=1` as Concentric (reuse `_SAVE_WORKERS`). In `backend/app/services/image_types.py`: add `"decay"` to `IMAGE_TYPES` (after `"concentric"`) and mention it in the docstring. In `backend/app/services/frame_rendering.py`: `write_frames(..., note_layout=DEFAULT_NOTE_LAYOUT, decay_rate=DEFAULT_DECAY_RATE)`; `decay_rate = check_decay_rate(decay_rate)` with the other checks; a branch `if image_type == "decay":` after the Concentric one that calls `write_decay_frames(circle_points(smoothed, beat, note_layout, decay_rate), colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT)` and returns; update the `write_frames` docstring. Run T002 and T003 and fix.
- [x] T005 [US1] Mutation checks, each caught by the tests and restored byte for byte: gains 24, 20, 16, 12, 7; the gains not sorted stably (ties to the higher note); zero-valued notes receiving gains; the beat bonus 4 or applied to all notes; the beat bonus rounded; no clamp at 64; no clamp at 0; decay `GIVE` 1 or 3; `LOSS` 15 or 17 (the share `/16` changed); neighbours only 4 (no diagonals); the grid wrapping around; the step reading the points already updated (not simultaneous); no cap at 64 after receiving; `give = 16` always (points from nothing for a cell with fewer than 16); frames counted from 0 (`i % rate` with a 0-based `i`); the decay applied before the gains in the frame; the interval `rate + 1`; the layout applied after ranking replaced by ranking in cell order (the spiral tie test must fail); size reaching full at 12 or 32 points; the smallest radius 0 or `1/24`; the color scale ending at 24 or 64; the coverage edge offset `+ 0.0` or `+ 1.0`; the beat not passed.

**Checkpoint**: Decay frames can be drawn through `write_frames`; everything else is unchanged.

---

## Phase 3: User Story 2 - Choose Decay on the page and set the decay rate (Priority: P2)

**Goal**: The `decay_rate` field of the job request (and `image_type=decay`), and the page's Decay group with the slider, the request and the summary.

**Independent Test**: Post a WAV with `image_type=decay&decay_rate=3`: 200, `image_type` and `decay_rate` echoed, 600 × 400 frames; on the page choosing Decay shows the groups Analysis, Colormap, Image type, Decay, Note layout, Local peaks (no checkbox) and Data smoothing.

### Tests for User Story 2 (write first, they fail)

- [x] T006 [P] [US2] Create `backend/tests/test_decay_api.py` (spec Story 2 acceptance 1 to 6, FR-001, FR-009 to FR-012), in the style of `backend/tests/test_concentric_api.py` and `test_note_layout_api.py`: `image_type=decay` accepted and echoed with 200; the frames are 600 × 400 and their count is that of the other types; `decay_rate` not sent → 5 echoed; 1, 10, `" 3"` per the other parsers' rules; `0`, `11`, `2.5`, `abc`, empty refused with 400 and `The decay rate must be a whole number from 1 to 10.` **before the file is read** (use the same technique as the other API tests, for example an invalid file that would fail later); a rate sent with another image type is accepted, echoed and has no effect (the frames are byte-identical to those without it); a bad image type is refused with `The image type must be one of tiles, blended, contour, circles, circles_paint, concentric, decay.`; the Local peaks values are checked with the messages of the measurement before the file is read, and the beat is measured for every decay job (a file with a clear pulse gives frames that differ from the same job with `peak_distance` changed, and from `beat_coloring` sent true or false they do not differ); `note_layout=spiral` works for decay and is echoed; `threshold`, `note_count`, `resolution`, `interpolate`, `gaussian` and the circle fields are validated as before and ignored; the response of every image type has the key `decay_rate` (update the API tests that list the response keys exactly: those named by T001's grep, such as `test_circles_api.py`, `test_colormap_api.py`, `test_contour_api.py`, `test_interpolation_api.py`, `test_note_count_api.py`, `test_resolution_api.py`, `test_note_layout_api.py`, `test_concentric_api.py`), and the tests that name the six image types in the refusal message now name seven; the reference hashes of the other six types are unchanged.
- [x] T007 [P] [US2] Frontend tests (vitest), written first: in `frontend/src/utilities/validation.test.ts` — `IMAGE_TYPES` has seven entries with `decay` labelled "Decay" last; `DECAY_RATE_RANGE` is 1 to 10 step 1, `DEFAULT_DECAY_RATE` 5; `validateDecayRate` accepts 1 to 10 whole numbers (numbers and numeric strings as the other validators do) and refuses 0, 11, 2.5, empty, `abc`, `NaN` with `The decay rate must be a whole number from 1 to 10.`; `formatDecayRate(1)` is `1 frame` and `formatDecayRate(5)` is `5 frames`; `gridSettingsApply("decay")` is false; `noteLayoutApplies("decay")` is true; `beatColoringApplies("decay")` is false; `peakSettingsShown("decay", false)` is true; `decayRateApplies` is true for `decay` only. In `frontend/src/utilities/groups.test.ts` — `groupsFor("decay")` is `["analysis", "colormap", "image-type", "decay", "note-layout", "concentric-peaks", "data-smoothing"]`; `controlsIn("decay")` is `["decay-rate"]`; `groupTitle("decay")` is "Decay"; `groupOf("decay-rate", "decay")` is "decay" and undefined for the other types; `groupOf("peak-distance", "decay")` is "concentric-peaks"; `groupOf("threshold", "decay")` and `groupOf("gaussian", "decay")` are undefined; the groups of the other six types are unchanged. In `frontend/src/utilities/help.test.ts` — `decayRateHelp` exists, is non-empty, and mentions frames and the range 1 to 10. In `frontend/src/api.test.ts` — the request body has `decay_rate` with the number as text and `image_type=decay` when chosen. In `frontend/src/components/SettingsForm.test.ts` and `frontend/src/App.test.ts` (server-side rendering and source guards in the style of the earlier tests) — choosing Decay shows the Decay group with the slider `decay-rate` (min 1, max 10, step 1, value 5), the Note layout group, the Local peaks group with Minimum distance and Prominence and no Beat coloring checkbox, and does not show Threshold, Notes, Oversampling, Interpolate or Gaussian; the other types do not show the slider; the summary of a Decay result lists "Decay rate: 5 frames", Note layout, Minimum distance and Prominence and not Threshold, Notes, Interpolate, Oversampling, Gaussian smoothing or Beat coloring; a bad rate marks the group as having a problem and disables Create frames.

### Implementation for User Story 2

- [x] T008 [US2] Backend wiring. In `backend/app/routers/jobs.py`: `_parse_decay_rate(text, sent)` in the style of `_parse_circle_notes` (not sent → `DEFAULT_DECAY_RATE`; whole numbers 1 to 10; 400 with `The decay rate must be a whole number from 1 to 10.` otherwise); the form field `decay_rate: str | None = Form(None)`; parse it with the other fields before the file is read; the beat is measured when `image_type_value in ("concentric", "decay")` or the tiles/blended rule as before (update the comment); pass `decay_rate=decay_rate_value` to `write_frames`; echo `"decay_rate": decay_rate_value` in the response. Run T006 and fix.
- [x] T009 [US2] Frontend. In `frontend/src/utilities/validation.ts`: add `{ value: "decay", label: "Decay" }` to `IMAGE_TYPES` (update its comment to seven); `DECAY_RATE_RANGE = { min: 1, max: 10, step: 1 } as const`, `DEFAULT_DECAY_RATE = 5`, `validateDecayRate`, `formatDecayRate`, `decayRateApplies`; `gridSettingsApply` false for `decay`; `peakSettingsShown` true for `decay`; `noteLayoutApplies` true for `decay`. In `frontend/src/utilities/groups.ts`: the group `{ id: "decay", title: "Decay", controls: ["decay-rate"] }` after `circles_paint`, `"decay"` in `TYPE_GROUPS`, `groupsFor` pushes `concentric-peaks` for `decay` as well as `concentric` (update the comments and the docstring). In `frontend/src/utilities/help.ts`: `decayRateHelp` (1 to 10 frames, default 5; how often every circle gives 2 points to each neighbour and loses 16; a small number spreads and fades fast, a large one lets the spots stay; counted in frames, so a higher frame rate decays faster in time). In `frontend/src/api.ts`: `decayRate: number` in the settings type and `body.append("decay_rate", String(settings.decayRate))`. In `frontend/src/components/SettingsForm.vue`: `decayRate` ref (default `DEFAULT_DECAY_RATE`), `decayRateError`, included in the form validity, `decayRateProblem` for the group, the slider with the label "Decay rate", `InfoPopover`, `formatDecayRate` output, `id="decay-rate"`, in a group block with the id `decay` in the style of the Circles group, `decayRate` in the emitted settings. In `frontend/src/App.vue`: the summary line `Decay rate: {{ formatDecayRate(result.decay_rate) }}` shown when `result.image_type === 'decay'` (add `decay_rate` to the result type in `frontend/src/api.ts`). Run T007 and fix.
- [x] T010 [US2] Mutation checks (catch and restore): the rate not checked before the file is read; the rate accepting 0 or 11 or 2.5; the default 1 or 10; `decay` missing from `TYPE_GROUPS`; the Beat coloring checkbox shown for Decay; Image smoothing shown for Decay; the beat not measured for Decay; `decay_rate` missing from the response or from the request; the summary showing Threshold for Decay; the rate sent as a float string.

**Checkpoint**: Decay can be chosen on the page, tuned, and created through the API with the rate checked and echoed.

---

## Phase 4: User Story 3 - Quiet, silent and beat-less moments look sensible (Priority: P3)

**Goal**: The corner cases of the spec hold end to end.

**Independent Test**: A silent file gives 84 smallest dots in the first color; a file without peaks works with the beat bonus 0; after a loud passage and silence every circle is back to 0.

- [x] T011 [P] [US3] Add to `backend/tests/test_decay_rendering.py` and `backend/tests/test_decay_api.py` (most unit cases are in T002; these are end to end): a silent WAV and a silent array give frames of 84 identical smallest dots in the colormap's first color, with no error; a WAV without peaks (a steady tone) works with `beat` all 0 (the frames equal those of `write_frames(..., beat=None)`); a WAV shorter than the peaks window works; a loud passage then silence returns to the smallest dots within the expected number of decay steps (the last frame has no circle larger than the smallest dot); two runs of the same job give identical files; a rate of 1 and of 10 on the same file give different frames; a frame rate of 30 and 60 give the frame counts of the other types; `interpolate`, `gaussian` and `resolution` do not change Decay frames; the timing check of SC-007: 1,800 synthetic frames of random values through `write_frames(image_type="decay")` take under 30 seconds, and not more than 5 seconds more than Concentric for the same input (mark the timing tests so that they are skipped when an environment variable such as `SKIP_TIMING` is set, if the project already has such a convention in `test_concentric.py`; otherwise follow what that test does).
- [x] T012 [US3] Run T011 and fix anything it finds (in `backend/app/services/decay.py` only, unless the failure is outside it).

**Checkpoint**: All three stories work.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T013 [P] Documentation: in `README.md` add Decay to the list of image types with its points, size, colors, gain and decay, its settings (Decay rate, Local peaks, Data smoothing, Note layout) and the settings that do not apply, and `decay_rate` to the API field table; in `specs/027-decay-circles/quickstart.md` fix anything that turned out different while building. Update the docstrings that count the image types ("six" → "seven") in `image_types.py`, `frame_rendering.py`, `groups.ts` and `validation.ts`.
- [x] T014 Full verification: `python -m pytest -q` in `backend/` (all green, counts higher than the baseline of T001 by the new tests), `npm test` and `npm run build` in `frontend/` (green, no type errors); the reference hashes of the other six image types unchanged; run quickstart scenarios 1 to 6 by hand where a browser is available (note in the report which were done by hand and which only by the automated tests); `git status` shows only the intended files.

---

## Dependencies & Execution Order

- Phase 1 first. US1 (Phase 2) is the MVP and needs nothing else. US2 depends on US1's `write_frames(decay_rate=...)`. US3 depends on US1 and the API of US2 (T011's end-to-end cases), but its unit-level cases are already in T002.
- Inside a story: tests (T002/T003, T006/T007) before the implementation (T004, T008/T009); the mutation checks (T005, T010) after.
- T006 and T007 are different files (backend and frontend) and run in parallel; T008 (backend) and T009 (frontend) can run in parallel once their tests exist.

### Parallel example: User Story 1

```text
Task: "Create backend/tests/test_decay.py"            (T002)
Task: "Create backend/tests/test_decay_rendering.py"  (T003)
```

## Implementation Strategy

1. MVP: Phases 1 and 2. Decay works through `write_frames` with the default rate; validate with T002/T003 and the reference hashes.
2. Add US2: the API field and the page; validate with the quickstart scenario 3.
3. Add US3: the corner cases and the timing; then the polish.
