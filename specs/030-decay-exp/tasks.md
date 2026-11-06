---

description: "Task list for Decay Exp (feature 030)"
---

# Tasks: Decay Exp

**Input**: Design documents from `/specs/030-decay-exp/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/decay-exp.md, quickstart.md

**Tests**: Written first for each story (the project's practice): the gain and loss as numbers, the steps on the grid, the API, and the page's group, summary and request (server-side rendering and source guards, as in features 025 to 027). The look in the player is the manual step of the quickstart.

**Revised 2026-11-06**: the loss became `sin²(π/2 × p/64)` per neighbour (the user found the first formula `1 / (1 + e^(p/8))` backwards). The loss and step tests of T003, the settling and fading tests and the numbers in the quickstart were rewritten for it; the gain's 8 became a taper that moves from 8 to 12 and back (the second revision of the same day; see the spec, FR-004a); where a task below still quotes the old numbers, `backend/tests/test_decay_exp.py` and the spec are the current record.

**Organization**: By user story: US1 the points and the frames through `write_frames` (P1), US2 the image type value in the API and the page (P2), US3 the quiet cases (P3). Decay (`decay.py`) is only refactored in Phase 2, without a change of result.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- Paths are from the repository root. Edit files with their line endings preserved. Backend tests run from `backend/` (`.venv` active), frontend tests from `frontend/`.

---

## Phase 1: Setup

- [x] T001 Record the baseline before changing anything: run `python -m pytest -q` in `backend/` and `npm test`, `npm run build` in `frontend/`, and note the counts; note the reference hashes of the seven existing image types used by the earlier features (the hashes in `backend/tests/test_concentric_api.py`, `test_note_layout_api.py`, `test_decay_api.py`); list the tests that name the image types: `backend/tests/test_circles_api.py:53`, `test_concentric_api.py:39-40` (the `IMAGE_TYPES` tuple and `TYPE_MESSAGE` ending), `test_note_layout_api.py:15` and `test_note_layout_rendering.py:20` (`ALL_TYPES`), `test_contour_beat_wave_api.py:18,28` (`OTHER_TYPES` and a parametrize list), and the frontend tests of `IMAGE_TYPES`, `groupsFor` and the image type message (`grep -rn "circles_paint, concentric" backend/tests frontend/src`).

---

## Phase 2: Foundational: split the spreading out of `decay_step`

**Purpose**: Both Decay and Decay Exp need the part of a decay step after the amount given is known. This must not change any Decay result.

- [x] T002 In `backend/app/services/decay.py` move everything in `decay_step` after `give` is computed (the shape check stays in `decay_step`; the `share` array with a border of non-existent cells, the sum over the 8 directions, `np.clip(points - give + neighbours, 0.0, MAX_POINTS)` and the `NEGLIGIBLE` rule) into a new private function `_spread(points, give)` that takes the float64 `(7, 12)` points and the `(7, 12)` amount given by each circle and returns the new array (the input is not changed). `decay_step` keeps its signature, docstring and shape check and returns `_spread(points, np.minimum(points, NEIGHBOURS * frames * decay_per_frame(points, amounts)))`. Mention `_spread` in the `decay_step` docstring. Run `python -m pytest backend/tests/test_decay.py backend/tests/test_decay_rendering.py backend/tests/test_decay_api.py -q`: unchanged results (the same count of tests pass and the reference hashes match).

**Checkpoint**: Decay is exactly as before; `_spread` exists for Decay Exp.

---

## Phase 3: User Story 1 - Decay circles whose gain and loss follow an exponential curve (Priority: P1) 🎯 MVP

**Goal**: `decay_exp.py` (`exp_gains`, `exp_loss_per_frame`, `decay_exp_step`, `circle_points`) and `write_frames(image_type="decay-exp", ...)` drawing them with `write_decay_frames`.

**Independent Test**: `write_frames(values, ..., image_type="decay-exp", beat=None)` with one steady loud note: after frame 1 that note's circle has about 1.19 points (small, first colors), it grows more slowly than in Decay to about 18 to 19 points, and after the note stops it fades (slowly: see the spec).

### Tests for User Story 1 (write first, they fail)

- [x] T003 [P] [US1] Create `backend/tests/test_decay_exp.py` for the points (spec FR-003 to FR-006, SC-001, SC-002), with values `(frames, 84)` and `note_layout="rows"` unless said:
  - `exp_gains(values, beat)` (note order, shape `(frames, 84)`): with `beat=None` the five loudest notes gain `24·e^(−3)`, `20·e^(−2.5)`, `16·e^(−2)`, `12·e^(−1.5)` and `8·e^(−1)` (1.1949, 1.6417, 2.1654, 2.6776, 2.9430 to 4 places) in order of loudness and every other note 0; with `beat=[1.0]` the same notes gain `32·e^(−4)`, `28·e^(−3.5)`, `24·e^(−3)`, `20·e^(−2.5)`, `16·e^(−2)`; with `[0.5]` the tapered 28, 24, 20, 16, 12; ranking, ties (equal values rank the lower note first), notes with value 0 never gaining, a silent frame gaining nothing even with `beat=1`, columns after the 84th ignored, the input unchanged, bad values refused: all as `gains` of Decay (the same input gives `exp_gains == g * exp(-g / 8)` for `g = gains(...)` exactly).
  - `exp_loss_per_frame(points)`: 0 at 0 points; `sin²(π/2 × p/64)` at 1, 8, 24, 32, 48, 64 (0.0006, 0.0381, 0.3087, 0.5, 0.8536, 1 to 4 places; the formula was first `1 / (1 + e^(p/8))`, revised 2026-11-06); strictly increasing in `p`; the shape of the input is kept; no overflow warning for any `p` from 0 to 64 (run under `np.errstate(all="raise")`).
  - `decay_exp_step(points, frames=1)` on `(7, 12)` arrays (the shape is checked like Decay's step: `ValueError`): an interior cell with 8 points and all others 0 gives `8 × 0.2689 = 2.1514` in all, `0.2689` to each of its 8 neighbours, and keeps `8 − 2.1514`; an edge cell with 8 points (5 neighbours) loses the same 2.1514 in all, each of its 5 neighbours gets 0.2689 and the rest vanishes; a corner cell (3 neighbours) the same with 3; a cell with 64 points loses `8 × 0.000335 ≈ 0.00268` in all; with `frames=2` a cell gives twice as much (never more than it has: a cell with 1 point and `frames=4` gives at most 1 point and ends at 0); a cell with 0 points gives nothing; a cell left with under 0.01 points ends at exactly 0; simultaneity (two adjacent cells with 8 points each end at `8 − 2.1514 + 0.2689`, each from the points before the step); a receiving cell at 63.9999 does not go over 64; the grid does not wrap; over 200 random grids of 0 to 64 the total never grows and no cell is below 0 or above 64; the input is not changed.
  - `circle_points(values, beat, note_layout, decay_rate)` (shape `(frames, 84)`, float64): one loud note, no beat, `decay_rate=1`: frame 1 at that note's cell is `24·e^(−3)` minus the first step's loss (to 4 places, worked out in the test from the formulas), and the cells around it have what they received; with `decay_rate=4` there is no step in frames 1 to 3 (the cell has exactly `24·e^(−3)` after frame 1) and a step after frame 4; with `decay_rate=0.25` there are four steps a frame (use `steps_in_frame` of Decay as the oracle); the Spiral layout puts middle C (note 27) at cell (row 2, column 5) and spreads to the cells around it on the grid; the ranking is in note order (equal notes: the lower note wins in the spiral too); a bad `decay_rate` or `note_layout` is refused with the messages of Decay; determinism (two runs equal) and the input unchanged; Decay itself still gives `24` for the same input (a guard that the two types differ and that `circle_points` of Decay did not change).
- [x] T004 [P] [US1] Create `backend/tests/test_decay_exp_rendering.py` for `write_frames` (spec FR-002, FR-009): `write_frames(..., image_type="decay-exp")` for a synthetic stream gives `frame_000000.png` and up, 600 × 400 RGB, one per frame, byte for byte equal to `write_decay_frames(decay_exp.circle_points(...), ...)`; and different from the frames of `image_type="decay"` for the same stream (the points differ); with `note_layout="spiral"` the first circle appears in the cell of the table; `threshold`, `note_count`, `resolution`, `interpolate`, `gaussian`, `blend_width`, the circle settings and `decay_amounts` (any allowed values) do not change the frames (byte-identical); a bad `decay_rate` or `decay_amounts` is refused before anything is written, as for every image type; `decay_rate` and `decay_amounts` have no effect on the other seven types.

### Implementation for User Story 1

- [x] T005 [US1] Create `backend/app/services/decay_exp.py` (module docstring: what Decay Exp is, the two formulas and the 8, that the ranking, neighbours, drawing, rate check and step timing are Decay's, and that the loss is per neighbour per frame; it knows nothing about audio or the beat measurement). Contents, from research Decisions 1 to 3: `TAPER = 8`; `exp_gains(values, beat=None)`: `g = gains(values, beat)`, return `g * np.exp(-g / TAPER)`; `exp_loss_per_frame(points)`: `np.where(points > 0, 1.0 / (1.0 + np.exp(points / TAPER)), 0.0)` on a float64 array; `decay_exp_step(points, frames=1)`: float64 array, the shape check and message of `decay_step`, `give = np.minimum(points, NEIGHBOURS * frames * exp_loss_per_frame(points))`, return `_spread(points, give)`; `circle_points(values, beat=None, note_layout=DEFAULT_NOTE_LAYOUT, decay_rate=DEFAULT_DECAY_RATE)`: the same loop as `decay.circle_points` (`check_note_layout`, `check_decay_rate`, `arrange_notes(exp_gains(values, beat), note_layout).reshape(-1, GRID_ROWS, GRID_COLUMNS)`, `np.clip(points + gained[index], 0, MAX_POINTS)`, `steps_in_frame(index, decay_rate)` steps of `decay_exp_step(points, decay_rate)`, record), returning `(frames, 84)` float64. Import everything it shares (`gains`, `_spread`, `check_decay_rate`, `steps_in_frame`, `DEFAULT_DECAY_RATE`, `NEIGHBOURS`, `MAX_POINTS`, the grid constants, `arrange_notes`, `check_note_layout`, `DEFAULT_NOTE_LAYOUT`) from the modules that define them. In `backend/app/services/image_types.py`: add `"decay-exp"` to `IMAGE_TYPES` (after `"decay"`) and an eighth sentence in the module docstring. In `backend/app/services/frame_rendering.py`: import `circle_points as decay_exp_points` from `.decay_exp`; add a branch for `image_type == "decay-exp"` beside the Decay one that calls `write_decay_frames(decay_exp_points(smoothed, beat, note_layout, decay_rate), colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT)` and returns (`decay_amounts` is checked at the top as now and not passed); update the `write_frames` docstring and the comment at the `check_beat` line to name `decay-exp`. Run T003 and T004 and fix.
- [x] T006 [US1] Mutation checks, each caught by the tests and restored byte for byte: the taper constant 7 or 9 in the gain or in the loss; the gain without the minus (`e^(+g/8)`); the taper applied before the beat bonus; the gain taper applied to the circle's current points; the loss `1 / (1 + e^(−p/8))`; the loss as the total given away (not per neighbour: no factor 8); the loss using the Decay table; no cap at the points the circle has; the loss not 0 at 0 points; the step not scaled by `frames`; `_spread` reading updated points (not simultaneous); neighbours only 4; the grid wrapping; no clamp at 0 or 64; the `NEGLIGIBLE` rule dropped; the layout applied after ranking replaced by ranking in cell order; `exp_gains` taking the beat from a different place; `write_frames` using `decay.circle_points` for `decay-exp`.

**Checkpoint**: Decay Exp frames can be drawn through `write_frames`; everything else is unchanged.

---

## Phase 4: User Story 2 - Choose Decay Exp on the page and set the decay rate (Priority: P2)

**Goal**: `image_type=decay-exp` in the job request (beat measured, rate used, amounts checked and ignored), and the page's Decay Exp choice, Decay group with the rate only, request and summary.

**Independent Test**: Post a WAV with `image_type=decay-exp&decay_rate=2`: 200, `image_type` and `decay_rate` echoed, 600 × 400 frames; on the page choosing Decay Exp shows Analysis, Colormap, Image type, Decay (rate only), Note layout, Local peaks (no checkbox) and Data smoothing.

### Tests for User Story 2 (write first, they fail)

- [x] T007 [P] [US2] Backend API tests. Create `backend/tests/test_decay_exp_api.py` (spec Story 2 acceptance 1 to 6, FR-001, FR-006 to FR-009), in the style of `backend/tests/test_decay_api.py`: `image_type=decay-exp` accepted and echoed with 200; the frames are 600 × 400 and their count is that of the other types; `decay_rate` not sent → 1 echoed; `0.25`, `4` accepted; `0.2`, `1.1`, `4.25`, `5`, `abc`, empty refused with 400 and `The decay rate must be a number from 0.25 to 4 in steps of 0.25.` before the file is read; `decay_low`, `decay_medium`, `decay_high`, `decay_saturated` accepted, echoed and giving frames byte-identical whatever their values, and `decay_low=10` refused with `The low saturation decay must be a number from 0.5 to 3.`; a bad image type (also `decay_exp` and `decayexp`) is refused with `The image type must be one of tiles, blended, contour, circles, circles_paint, concentric, decay, decay-exp.`; the Local peaks values are checked with the messages of the measurement before the file is read and the beat is measured for every `decay-exp` job (a file with a clear pulse gives frames that differ when `peak_distance` changes, and `beat_coloring` true or false does not matter); `note_layout=spiral` works and is echoed; `threshold`, `note_count`, `resolution`, `interpolate`, `gaussian` and the circle fields are validated as before and ignored; the frames of `decay-exp` and of `decay` for the same file differ; the frames of the other seven types match the reference hashes of T001. Update the existing tests named by T001 so that they name eight types: `IMAGE_TYPES == (..., "concentric", "decay", "decay-exp")` and `TYPE_MESSAGE.endswith("concentric, decay, decay-exp.")` in `test_circles_api.py` and `test_concentric_api.py`; `"decay-exp"` appended to `ALL_TYPES` in `test_note_layout_api.py` and `test_note_layout_rendering.py`; to `OTHER_TYPES` and the parametrize list in `test_contour_beat_wave_api.py` (and the test in it that sends `decay_rate` still passes).
- [x] T008 [P] [US2] Frontend tests (vitest), written first: in `frontend/src/utilities/validation.test.ts` — `IMAGE_TYPES` has eight entries with `decay-exp` labelled "Decay Exp" last and the image type message lists the eight; `gridSettingsApply("decay-exp")` is false; `noteLayoutApplies("decay-exp")` is true; `isRingsType("decay-exp")` is true; `peakSettingsShown("decay-exp", false)` is true; `beatColoringApplies("decay-exp")` is false; `decayRateApplies("decay-exp")` is true. In `frontend/src/utilities/groups.test.ts` — `groupsFor("decay-exp")` is `["analysis", "colormap", "image-type", "decay-exp", "note-layout", "concentric-peaks", "data-smoothing"]`; `controlsIn("decay-exp")` is `["decay-rate"]`; `groupTitle("decay-exp")` is "Decay"; `groupOf("decay-rate", "decay-exp")` is "decay-exp"; `groupOf("decay-low", "decay-exp")` is undefined while `groupOf("decay-low", "decay")` is still "decay"; the groups of the other seven types are unchanged. In `frontend/src/api.test.ts` — choosing Decay Exp sends `image_type=decay-exp` and `decay_rate`. In `frontend/src/components/SettingsForm.test.ts` and `frontend/src/App.test.ts` (server-side rendering and source guards in the style of the earlier tests) — choosing Decay Exp shows the Decay group with the slider `decay-rate` (min 0.25, max 4, step 0.25, value 1) and none of the sliders `decay-low`, `decay-medium`, `decay-high`, `decay-saturated`, the Note layout group, the Local peaks group with Minimum distance and Prominence and no Beat coloring checkbox, and does not show Threshold, Notes, Oversampling, Interpolate or Gaussian; Decay still shows the five sliders; the summary of a Decay Exp result lists "Decay rate: 1 frame", Note layout, Minimum distance and Prominence and not Threshold, Notes, Interpolate, Oversampling, Gaussian smoothing, Beat coloring or any of the four saturation decays; a bad rate marks the group as having a problem and disables Create frames; the summary of a Decay result still lists the four saturation decays.

### Implementation for User Story 2

- [x] T009 [US2] Backend wiring in `backend/app/routers/jobs.py`: the beat is measured when `image_type_value in ("concentric", "decay", "decay-exp")` or the tiles/blended/contour rule as before (update the comment); nothing else changes (`decay_rate`, the four amounts and the response keys are already parsed, passed to `write_frames` and echoed for every type; the image type message is built from `IMAGE_TYPES`). Check that no other place in `backend/app` compares `image_type` with `"decay"` (the earlier grep found only `jobs.py` and `frame_rendering.py`). Run T007 and fix.
- [x] T010 [US2] Frontend wiring. In `frontend/src/utilities/validation.ts`: add `{ value: "decay-exp", label: "Decay Exp" }` to `IMAGE_TYPES` (update its doc comment); `isRingsType` is true for `decay-exp` too (this makes `gridSettingsApply`, `peakSettingsShown` and `noteLayoutApplies` follow; check `noteLayoutApplies` and `beatColoringApplies` and fix any that name the types one by one); `decayRateApplies` is true for `decay` and `decay-exp` (its doc comment says the four amounts are Decay's only; no separate helper was needed for them, since `App.vue` keeps its `result.image_type === 'decay'` test for those four lines and the form shows them by `inTypeGroup('decay-low')`). In `frontend/src/utilities/groups.ts`: a group `{ id: "decay-exp", title: "Decay", controls: ["decay-rate"] }` after `decay`, `"decay-exp"` in `TYPE_GROUPS`, the doc comments naming Decay Exp. In `frontend/src/components/SettingsForm.vue`: `"decay-exp"` in `TYPE_GROUP_IDS` (the sliders are shown by `inTypeGroup('decay-rate')` and `inTypeGroup('decay-low')`, so the four amounts disappear by themselves; verify, and change the `decayAmountErrors` check at the problem marker only if it counts them for Decay Exp). In `frontend/src/App.vue`: the Decay rate summary item shows for `decay` and `decay-exp` (use `decayRateApplies(result.image_type)`), the four amount items for `decay` only (unchanged). In `frontend/src/utilities/help.ts`: if `decayRateHelp` mentions the amounts or saturation levels, make the sentence true for both (or give Decay Exp a sentence of its own, shown by `SettingsForm.vue` for that type). Run T008 and fix; `npm run build` type check passes.

**Checkpoint**: Decay Exp can be chosen on the page and made through the API; Decay and the other types are unchanged.

---

## Phase 5: User Story 3 - Quiet, silent and beat-less moments look sensible (Priority: P3)

**Goal**: The corner cases of the spec behave as written (they follow from Decay's rules, but are proven here for the new curves).

**Independent Test**: A silent file gives 84 dots in the first color; one loud note followed by silence ends with every circle at 0 after enough steps.

- [x] T011 [US3] Add to `backend/tests/test_decay_exp.py` (spec Story 3, SC-003) and `backend/tests/test_decay_exp_rendering.py`, then fix `decay_exp.py` if any fails: a silent file gives points all 0 and frames of 84 smallest circles in the first color (pixel at a cell center is the colormap's table row 0, disc radius `25/12`); a frame with no beat has the five tapered gains of the spec; a silent frame in the middle adds nothing and only decays; fewer than 5 sounding notes gain only those; after a loud passage and then silence every circle is exactly 0 within a finite number of steps (loop at `decay_rate=1` up to 20,000 silent frames and assert the frame at which the maximum is 0, and that it is finite; record the number in the test as a comment); a file shorter than the peaks window works through `write_frames` and the API (as the Decay tests do).

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T012 [P] Documentation: `README.md` gets Decay Exp beside Decay (the value `decay-exp`, the two formulas with the 8, that the gain is largest for the lower ranks and the loss smallest for full circles, that the decay rate applies and the four saturation decays do not, and the settings shown); update the `image_types.py` docstring if not done; check `specs/030-decay-exp/quickstart.md` still matches what was built and fix it where it does not.
- [x] T013 Run the whole suite and the manual quickstart: `python -m pytest -q` in `backend/` (all pass: the baseline count of T001 plus the new tests), `npm test` and `npm run build` in `frontend/` (all pass), then scenarios 1 to 6 of `specs/030-decay-exp/quickstart.md` as far as they can be done without a person watching the player (Scenarios 1, 2 and 6 by script: the points of frame 1, the fading, the time of 1,800 frames); say plainly in the report which scenarios were not watched. Tick the boxes of this file.

---

## Dependencies & Execution Order

- Phase 1 first (baseline). Phase 2 (T002) before Phase 3, because `decay_exp.py` imports `_spread`.
- Phase 3: T003 and T004 [P] (different files), then T005, then T006. US1 alone is the MVP: frames of Decay Exp through `write_frames`.
- Phase 4 needs T005 (`"decay-exp"` in `IMAGE_TYPES`, the `write_frames` branch). T007 and T008 [P] before T009 and T010; T009 and T010 are independent of each other (backend/frontend) and can run in parallel.
- Phase 5 (T011) needs T005. Phase 6 last.

```text
T001 → T002 → T003 ┐
               T004 ┴→ T005 → T006 ┬→ T007 ┬→ T009 ┐
                                   │ T008 ┴→ T010 ┴→ T011 → T012 → T013
```

## Parallel Example: User Story 2

```text
Task: "T007 backend API tests (backend/tests/test_decay_exp_api.py + the existing tests naming the types)"
Task: "T008 frontend tests (validation, groups, api, SettingsForm, App)"
then
Task: "T009 jobs.py"      Task: "T010 frontend wiring"
```

## Implementation Strategy

1. **MVP**: Phases 1 to 3: the library and `write_frames` (Decay Exp frames exist, tested at the number level).
2. Add Phase 4: reachable from the API and the page.
3. Phase 5 for the quiet cases, Phase 6 for the docs and the full run.
4. Stop at each checkpoint to run the whole suite: Decay and the other seven types must stay byte-identical.
