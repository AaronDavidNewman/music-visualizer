---

description: "Task list for Note Threshold"
---

# Tasks: Note Threshold

**Input**: Design documents from `/specs/011-note-threshold/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/threshold-api.md, quickstart.md

**Tests**: Included, following the plan: pytest for the hidden-notes rule, the drawing and the API, and vitest for the new validation helpers, explanation text and the rendered slider. Behavior in a real browser is checked by the quickstart steps.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root. Backend commands run in `backend/` with the venv's Python (`.venv/Scripts/python -m pytest`), frontend commands in `frontend/`. The API field is `threshold` (percent, 0 to 50, default 0).

**Working notes** (learned in feature 010): do not use `git stash` to compare with old code (it emptied the index once; use the saved reference run instead); keep each existing file's line endings (many files are CRLF) when editing from a script; write helper scripts to files with the Write tool rather than shell heredocs that contain backticks.

**Change on 2026-10-07**: after these tasks were completed, the threshold's maximum was changed from 50 to **10** (percent of the largest note value; still steps of 1 on the page). The numbers 30, 40, 50 and 20 below, and the thresholds in the recorded timings, are those of the original version; the code, tests, README and the other documents use 0 to 10 (see the Clarifications section of `spec.md`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2 or US3

## Phase 1: Setup

- [x] T001 Run `pytest` in `backend/` and `npm test`, `npm run typecheck` and `npm run build` in `frontend/` to confirm a green baseline before changing anything (684 backend and 205 frontend tests at the end of feature 010), and note the numbers. Run the reference script `baseline.py` from the session scratchpad (it creates frames for a fixed 4 s multi-note file through the test client and prints a combined hash of all frames; at the end of feature 010 the hash was `2688e9c214af0555e279e1171ce578b468b29fda5847c11df19b1a70049d88b2`) and confirm the same hash, so the threshold-off output can be compared with it later (SC-001)
  - Done: 684 backend and 205 frontend tests passed, typecheck and build clean; the reference hash was `2688e9c2…` as recorded.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The constants and the pure rule that decides which notes are hidden, tested in isolation.

- [x] T002 In `backend/app/services/frame_rendering.py` add `MIN_THRESHOLD = 0`, `MAX_THRESHOLD = 50`, `DEFAULT_THRESHOLD = 0` (comment: percent of the largest note value, 0 is off) and `hidden_notes(smoothed: np.ndarray, threshold: float = DEFAULT_THRESHOLD) -> np.ndarray` per data-model.md "Hidden notes": `smoothed` is the `(frames, 88)` array of smoothed note values; validate `threshold` (bool and non-numbers refused, must be finite and `MIN_THRESHOLD <= threshold <= MAX_THRESHOLD`, else `ValueError("The threshold must be a number from 0 to 50.")`); `peak = smoothed.max()` over the whole array (0 for an empty array); return a new boolean array of shape `(frames, SHOWN_NOTES)` that is `smoothed[:, :SHOWN_NOTES] < threshold / 100 * peak` (strictly below; no special case for 0 or for peak 0); raise `ValueError` if `smoothed` has fewer than 84 columns. Docstring: the reference is the whole file's largest smoothed note value (all 88 notes, as `to_gray_levels` uses); hiding is strict
- [x] T003 [P] In `backend/tests/test_frame_rendering.py` add tests for `hidden_notes` (append to the end; keep the file's CRLF line endings): with values [100, 40, 20] on three notes of one frame (other columns 0) and thresholds 30, 40, 50 the hidden sets are {20}, {20} (40 is exactly at the threshold and shown) and {40, 20}; the note with the peak is never hidden for every whole threshold 0 to 50; threshold 0 hides nothing even for a matrix containing zeros; the reference is the peak of the whole matrix and not of each frame (a quiet frame next to a loud one is hidden entirely at 30) and it includes notes 84 to 87 (a loud undrawn note raises the reference); an all-zero matrix hides nothing and does not fail; an empty `(0, 88)` matrix returns an empty `(0, 84)` array; the result has shape `(frames, 84)`, dtype bool, is a new array and the input is not modified; `ValueError` with the exact message for -1, 51, `nan`, `inf`, `True`, `"20"`, `None`; `ValueError` for fewer than 84 columns; floating-point safety: a value built as exactly 0.3 times the peak is shown (not hidden)
  - Done. The first version of these tests forgot that notes with no value at all are below any positive threshold (so they are hidden too); fixed, and a test now pins that behavior.

**Checkpoint**: `pytest tests/test_frame_rendering.py -k hidden` passes; nothing else has changed.

---

## Phase 3: User Story 1 - Hide notes that are too quiet to matter (Priority: P1) 🎯 MVP

**Goal**: A threshold hides faint notes' tiles in the frames, through the job API, with 0 (the default) changing nothing (FR-001 to FR-008, FR-010 to FR-012).

**Independent Test**: Quickstart "Story 1". A file with a loud note and a faint one (a quarter of its value): with the threshold off both tiles are colored; at 30% the faint note's tile is black and the loud one is unchanged.

### Tests for User Story 1

- [x] T004 [P] [US1] In `backend/tests/test_frame_rendering.py` add tests for drawing (append; CRLF): `tile_colors(levels, brightness, hues, value, hidden=mask)` makes exactly the masked tiles `(0, 0, 0)` and leaves every other tile equal to the call without `hidden`; `hidden=None` and an all-False mask equal the call without it; an all-True mask gives an all-black result; a mask of the wrong shape or dtype raises `ValueError`; the hues of the unmasked tiles are not changed by masking another tile (a hidden partner still shifts its neighbor's hue: tiles 24 and 28 lit, 28 hidden, tile 24's color equals its color without the mask); `write_frames(frames, directory, ..., threshold=0)` and the call with no threshold write byte-identical files, also with smoothing, energies and all three steps set; `write_frames` with a threshold on a hand-built matrix (a loud note, a note at 0.25 of it, silence elsewhere): at 30 the faint note's tile is exactly black in every frame in which it is below 30% of the peak and its colored tile is identical to the threshold-off one in the others; at 20 nothing differs from the threshold-off files; for every whole threshold from 1 to 50, every tile of every frame is either exactly `(0, 0, 0)` or equal to the same tile with the threshold off (SC-003); the note with the peak is colored in at least one frame at every threshold; an all-zero matrix with zero energies is entirely black at any threshold; `write_frames` refuses a threshold of -1, 51 or `nan` with `ValueError` before writing anything
- [x] T005 [P] [US1] Create `backend/tests/test_threshold_api.py` for the field, in the style of `test_color_levels_api.py` (reuse its helpers where they exist, import `client`, `frame_rgb`, `leftovers`, `wav_bytes` from `test_jobs_api`): `threshold` values `0`, `1`, `30`, `50`, `12.5`, `30.0`, ` 20 ` are accepted and echoed (`30.0` and `30` return the integer `30`, `12.5` returns `12.5`); a request that does not send the field returns `0` and frames byte-identical to a request that sends `0`; refused with 400 and the exact detail `The threshold must be a number from 0 to 50.` for empty, `-1`, `-0.5`, `50.1`, `51`, `100`, `abc`, `nan`, `inf`, `1e9`, with no job created (the temp directories are unchanged); a bad threshold is refused before the file is read (a request with a non-audio body and `threshold=99` gets the threshold message); with a generated WAV of a loud tone and a faint tone at about a quarter of its amplitude playing together, a threshold of 30 makes the faint tone's tile black (read the centre pixel of its tile) in the frames and leaves the loud tone's tile equal to its threshold-0 color, and a threshold of 10 leaves both unchanged; at every threshold the frames contain only black or threshold-0 tiles; the same request twice gives identical frame bytes
  - Done. The test tones are placed exactly on the FFT bin the analysis reads for each note: a tone between bins is measured far too low (a first version measured a quarter-amplitude tone at 95% of the loud one because the loud tone was almost a whole bin off).

### Implementation for User Story 1

- [x] T006 [US1] In `backend/app/services/frame_rendering.py` give `tile_colors` an optional keyword `hidden: np.ndarray | None = None`: when given it must be a boolean array of shape `(SHOWN_NOTES,)` (else `ValueError`); after the RGB values are formed set the rows where it is true to `(0, 0, 0)`. Hues are computed as before, from all levels (a hidden note still counts as a related note, research Decision 3). Give `write_frames` an optional keyword `threshold: float = DEFAULT_THRESHOLD`: validate it up front with the same check as `hidden_notes` (before anything is written), compute `smoothed = smooth_frames(frames, smoothing)` once, use it for `to_gray_levels(smoothed)` (as now) and for `hidden = hidden_notes(smoothed, threshold)`, and pass `hidden[i]` to `tile_colors` for each frame. Update the docstrings of `write_frames`, `tile_colors` and the module docstring (one sentence). Make T003 and T004 pass
- [x] T007 [US1] In `backend/app/routers/jobs.py` add `_parse_threshold(text, sent) -> int | float` in the style of `_parse_smoothing`: not sent gives `DEFAULT_THRESHOLD`; sent must parse as a finite float from `MIN_THRESHOLD` to `MAX_THRESHOLD` (empty, text, `nan`, `inf` and out-of-range refused with `HTTPException(400, "The threshold must be a number from 0 to 50.")`); return an `int` for a whole number and the float otherwise. Add the form field `threshold: str | None = Form(None)` to `create_job`, parse it next to the other settings (before the file is read), pass `threshold=...` to `write_frames`, add `"threshold"` to the response, and update the comment above `write_frames`. Make T005 pass
- [x] T008 [US1] In `backend/tests/test_energy_api.py` add `"threshold"` to the expected response keys in `test_the_other_response_fields_are_unchanged` (an intended addition). Run `pytest` in `backend/` and confirm everything passes. Then run the reference script from T001 with no `threshold` field and confirm the hash is identical to the one recorded (SC-001)
  - Done: 853 backend tests passed at this point, and the reference script gave the identical hash with no `threshold` field and with `threshold=0`.

**Checkpoint**: The API hides faint notes' tiles and, with the defaults, produces exactly the old frames.

---

## Phase 4: User Story 2 - Set the threshold with a slider on the page (Priority: P2)

**Goal**: A Threshold slider with a readout, explanation and summary line on the page (FR-001, FR-009, FR-011).

**Independent Test**: Quickstart "Story 2". Open the page, move the slider, see the readout, create frames, see the threshold in the summary.

### Tests for User Story 2

- [x] T009 [P] [US2] In `frontend/src/utilities/validation.test.ts` add tests for the new helpers from `validation.ts` (written in T011; keep CRLF): `THRESHOLD_RANGE` is `{ min: 0, max: 50, step: 1 }` and `DEFAULT_THRESHOLD` is 0; `validateThreshold` returns `null` for 0, 1, 25, 50, `"30"`, `"12.5"` and the message `The threshold must be a number from 0 to 50.` for -1, 51, 100, `""`, `"  "`, `"abc"`, `"NaN"`, `"Infinity"`, `"1e9"`; `formatThreshold(0)` is `"Off"`, `formatThreshold(1)` is `"1% of the loudest note"`, `formatThreshold(50)` is `"50% of the loudest note"`, `formatThreshold(12.5)` is `"12.5% of the loudest note"`; `formatThresholdSummary(0)` is `"Off"` and `formatThresholdSummary(30)` is `"30%"`
- [x] T010 [P] [US2] In `frontend/src/utilities/help.test.ts` add a test that `thresholdHelp` says a note below the threshold is drawn black, that it is a share of the loudest note in the file, that the left end is off and that the right end is 50%; in `frontend/src/components/SettingsForm.test.ts` add tests (using the existing `render` helper) that the rendered form has a range input with id `threshold` with `min="0"`, `max="50"`, `step="1"` and value 0, a label "Threshold" and an info button named "About threshold", the readout "Off", that the input is disabled when `busy` is true and not otherwise, and that the Threshold comes after Smoothing

### Implementation for User Story 2

- [x] T011 [US2] In `frontend/src/utilities/validation.ts` add `THRESHOLD_RANGE = { min: 0, max: 50, step: 1 } as const`, `DEFAULT_THRESHOLD = THRESHOLD_RANGE.min`, `validateThreshold(value: string | number): string | null` (finite number from 0 to 50, in the style of `validateSmoothing`), `formatThreshold(value: number): string` (`"Off"` at 0, else `` `${value}% of the loudest note` `` with no floating-point noise) and `formatThresholdSummary(value: number): string` (`"Off"` or `` `${value}%` ``). Make T009 pass
- [x] T012 [US2] In `frontend/src/utilities/help.ts` add `thresholdHelp`, built from `THRESHOLD_RANGE`: a note whose volume is below the threshold is drawn black; the threshold is a share of the loudest note in the whole file; the left end (0) is off and the right end (50) is 50% of the loudest note; louder notes are never changed. Make the help part of T010 pass
- [x] T013 [P] [US2] In `frontend/src/api.ts` add `threshold: number` to `JobResult` and to `JobSettings`, and append `threshold` to the form in `submitJob`
- [x] T014 [US2] In `frontend/src/components/SettingsForm.vue` add `thresholdValue` (number ref, default `DEFAULT_THRESHOLD`), `thresholdError` (`validateThreshold`), include it in `canSubmit`, and emit `threshold` in the submitted settings. Add the Threshold field after Smoothing, built like the Smoothing slider (`field`, `field-head` with a label for `threshold` and an `InfoPopover` labelled "threshold" using `thresholdHelp`, a `slider-row` with the range input `id="threshold"` using `THRESHOLD_RANGE`, `:disabled="busy"`, and a `<output class="slider-value" for="threshold">` showing `formatThreshold(thresholdValue)`; allow the output to be wider than the Smoothing one), and an inline error line like the others. Make T010 pass
- [x] T015 [US2] In `frontend/src/App.vue` add the summary item `Threshold: {{ formatThresholdSummary(result.threshold) }}` after Smoothing (import the helper). Run `npm test`, `npm run typecheck` and `npm run build` in `frontend/` and confirm all pass
  - Done: 233 frontend tests, typecheck and build pass; the form renders the slider (server-side render test), but see T021.

**Checkpoint**: The threshold can be set on the page and is shown in the summary.

---

## Phase 5: User Story 3 - The threshold works together with the other settings (Priority: P3)

**Goal**: The threshold is applied after smoothing, before the root, and does not disturb the other settings (FR-005 to FR-007).

**Independent Test**: Quickstart "Story 3". With smoothing 0.8 and a threshold of 20 a note that stops fades, then turns black at the first frame under 20% of the file's loudest value and stays black.

- [x] T016 [P] [US3] In `backend/tests/test_frame_rendering.py` add interaction tests on `write_frames` (append; CRLF): a note whose value falls to zero with smoothing 0.8 and a threshold of 20 turns black in exactly the first frame whose smoothed value (computed independently in the test with `smooth_frames`) is below 20% of the peak, and stays black; the hidden set is identical for the Saturation root (`brightness`) 2 and 100, for every Brightness root (`energy_root`) 1 to 8, with and without energies, and with each of the three steps set (read which tiles are exactly black, with frame brightness high enough that no colored tile is black); a hidden tile is `(0, 0, 0)` with every combination of the three steps (largest and smallest); the shown tiles' hue, saturation and brightness equal those of the threshold-off run (compare HSV with the tolerance used in the feature 010 tests); a frame whose notes are all hidden is entirely black while its neighbors are not; adding silence at the end of the matrix changes the hidden set of no earlier frame (the peak does not change)
  - Done. A mutation check (changing the strict `<` to `<=` in `hidden_notes`) made 59 tests fail, then was reverted.
- [x] T017 [P] [US3] In `backend/tests/test_threshold_api.py` add one API test: a generated multi-note WAV posted with `smoothing=0.8`, `threshold=20`, `saturation_step=20` and `brightness_step=50` gives frames in which every tile is black or a tile of the same file posted with the same settings and `threshold=0`, and a second post with the saturation root changed has the same set of black tiles in every frame

**Checkpoint**: Interactions behave as specified. A failure here points at the order of smoothing, comparison and the roots in `write_frames`.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T018 [P] Update `README.md`: add a **Threshold** bullet after the Smoothing one (and the level-steps one): a slider from Off (0) to 50 in steps of 1; a note whose smoothed value in a frame is strictly below that percentage of the file's largest note value gets a black tile; the comparison is before the Saturation root and does not depend on the roots, steps, hue or frame brightness; a hidden note still counts as a related note for other tiles' hues; the loudest note is never hidden; the API field `threshold` (0 to 50, leave out for 0, refused with a 400 otherwise) and the response field; mention `specs/011-note-threshold/data-model.md`
- [x] T019 Run everything: `pytest` in `backend/`, `npm test`, `npm run typecheck` and `npm run build` in `frontend/`; all must pass. Report the final test counts against the T001 baseline
  - Done: backend 684 → 869 tests, frontend 205 → 233 tests, all passing; typecheck and build clean; reference hash unchanged.
- [x] T020 Measure performance (SC-008): with the `perf.py` script from the session scratchpad adapted to send `threshold` (or an equivalent timing through the test client on a 60 s file, median of several interleaved runs), compare the threshold off and at 50; the difference must be within 10%. If not, profile `hidden_notes` and `tile_colors` and fix before finishing
  - Done: 60 s file (1800 frames), 15 interleaved runs, medians: threshold 0 1.01 s, no field 1.00 s, threshold 20 1.03 s (+1.9%), threshold 50 1.02 s (+0.4%); minimums identical (0.97 s). Within the 10% limit. (A first run of 5 repetitions showed +9.8% for threshold 20; it was noise: two identical configurations differed by 5%.)
- [ ] T021 Follow `specs/011-note-threshold/quickstart.md` Stories 1 to 3 in the running application (a real browser, if one can be used), including the refused-request examples. If a browser cannot be used, say so explicitly in the report and leave this task unchecked with a note of what was verified through tests and direct API calls instead
  - NOT done: the walk-through in a real browser (moving the slider, the readout, the popover, the summary after a job, seeing black tiles in the animation). Verified instead through tests and direct API calls: the slider's range, step, start value, label, info button, disabled state and position in the rendered form; the field's validation and refusals; and the frames.

---

## Dependencies & Execution Order

- Phase 1 first. Phase 2 (T002, then T003) blocks the stories.
- **US1 (Phase 3)** needs Phase 2. T004 and T005 are written first (they fail until T006 and T007); T006 before T007; T008 last.
- **US2 (Phase 4)** can start after Phase 2 and run in parallel with US1 (frontend vs backend files); the end-to-end check in T015 needs the API field from T007. T011 before T012 and T014; T013 before T014 and T015.
- **US3 (Phase 5)** needs T006 and T007. T016 and T017 are independent.
- **Polish** last; T018 can be done any time after T007 and T014.

### Parallel opportunities

- T004 and T005 (different test files); the frontend track (T009 to T015) alongside the backend track after Phase 2; T016 and T017; T018 with T019's preparation.

## Implementation Strategy

- **MVP**: Phases 1 to 3 (US1). The API hides faint notes and the default leaves frames unchanged; the threshold can be tried with curl or the API docs.
- Then US2 puts the slider on the page and US3 locks in the interactions with smoothing, the roots and the steps.
- Keep the change reviewable: no new module, every new argument optional, do not touch the note analysis, the energy measure, the hue code or the PNG writing.
