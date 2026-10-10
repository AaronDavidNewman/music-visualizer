---

description: "Task list for Smoothing Window"
---

# Tasks: Smoothing Window

**Input**: Design documents from `/specs/012-smoothing-window/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/smoothing-window-api.md, quickstart.md

**Tests**: Included, following the plan: pytest for the formula, the window, the API and the combinations, and vitest for the new validation, texts and the rendered field. Behavior in a real browser is checked by the quickstart steps.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root. Backend commands run in `backend/` with the venv's Python (`.venv/Scripts/python -m pytest`), frontend commands in `frontend/`. The API field is `smoothing_window` (whole number 1 to 20, default 1); the existing `smoothing` keeps its range 0.0 to 0.8.

**Working notes** (learned in features 010 and 011): do not use `git stash` to compare with old code (it emptied the index once; use the saved reference run instead); keep each existing file's line endings (many files are CRLF) when editing from a script; write helper scripts to files with the Write tool rather than shell heredocs that contain backticks (the shell runs them as commands).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2 or US3

## Phase 1: Setup

- [x] T001 Run `pytest` in `backend/` and `npm test`, `npm run typecheck` and `npm run build` in `frontend/` to confirm a green baseline before changing anything (790 backend and 233 frontend tests at the end of feature 011), and note the numbers. Run the reference script `baseline.py` from the session scratchpad (it creates frames for a fixed 4 s multi-note file through the test client and prints a combined hash of all frames; with the default smoothing 0 the hash was `2688e9c214af0555e279e1171ce578b468b29fda5847c11df19b1a70049d88b2`) and confirm the same hash, so the smoothing-off output can be compared with it later (SC-001)
  - Done: 790 backend and 233 frontend tests passed, typecheck and build clean; the reference hash was `2688e9c2…` as recorded.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Replace the running average with the windowed average in one tested place, pass the window through the drawing code, and bring every existing test that encodes the old behavior up to the new definition, so the suite is green again before any story starts.

- [x] T002 In `backend/app/services/frame_rendering.py` add `MIN_SMOOTHING_WINDOW = 1`, `MAX_SMOOTHING_WINDOW = 20`, `DEFAULT_SMOOTHING_WINDOW = 1` (comment: how many earlier frames are mixed into each frame), `_check_smoothing_window(window) -> int` (an `int` or numpy integer from 1 to 20; bools, floats, strings and `None` refused with `ValueError("The smoothing window must be a whole number from 1 to 20.")`), and rewrite `smooth_frames(frames, smoothing=DEFAULT_SMOOTHING, window=DEFAULT_SMOOTHING_WINDOW)` per data-model.md "Smoothed value" and research Decisions 1 to 4: keep the existing validation and message for `smoothing`; validate `window`; `out = np.array(frames, dtype=np.float64, copy=True)`; if `smoothing == 0` or fewer than 2 rows, return `out`; otherwise `acc = out.copy()` (the raw values stay in `out`), for each offset `j` from 1 to `min(window, rows - 1)` do `acc[j:] += s * out[:-j]`, then divide row `t` by `1 + s * min(t, window)` (a column vector shaped to broadcast); the earlier frames added are always the raw values, never earlier results; the input is never modified. Replace the docstring: the formula `( A[t] + s*A[t-1] + ... + s*A[t-w] ) / ( 1 + s*k )`, `k = min(t, w)`, finite memory of exactly `w` frames, each column from its own history only, first row unchanged. Then give `hue_sequence`, `value_sequence` and `write_frames` an optional `smoothing_window: int = DEFAULT_SMOOTHING_WINDOW` argument (validated up front in `write_frames` next to the other checks, before anything is written) and pass it to every `smooth_frames` call (notes in `write_frames`, hues in `hue_sequence`, brightness in `value_sequence`); update the module docstring and the docstrings of those three functions (smoothing is a windowed average now, no longer a running average)
  - Done. Also fixed a stale "0 to 50" in the `write_frames` docstring (the threshold maximum became 10 in feature 011) and the same stale number in two frontend comments (`api.ts`, `validation.ts`).
- [x] T003 [P] Create `backend/tests/test_smoothing_window.py` for `smooth_frames` and the constants: a plain reference loop written in the test (`for t: acc = a[t] + s*sum(a[t-j] for j in 1..min(t,w)); out[t] = acc / (1 + s*min(t,w))`) agrees (to 1e-12) with the function for random `(30, 5)` data at several `(w, s)` pairs including `(1, 0.5)`, `(3, 0.8)`, `(20, 0.8)`, `(7, 0.1)` and a window longer than the file; the worked example from the spec: `w=2, s=0.5` on [8, 4, 2] gives [8, 5.3333, 4] (within 0.001); the first row is always unchanged; the frame before the window is full uses `1 + s*t` as divisor (check row 1 and row 2 with `w=5`); an impulse (value 1 in one row `k >= w` and 0 elsewhere) is `1/(1+s*w)` at row `k`, `s/(1+s*w)` at rows `k+1 .. k+w` and **exactly** `0.0` from row `k+w+1`, for every `w` from 1 to 20 and `s` in (0.1, 0.5, 0.8); a constant column is unchanged (within 1e-12) for every `w` and `s`; `s = 0` returns an equal new array (not the same object, input untouched) for every `w`; the input array is never modified; causality: smoothing the first N rows of a longer array gives the same N rows as the first N rows of smoothing the whole array (exact equality); each column uses only its own history (changing one column changes no other column's output); single-row, zero-row and single-column inputs work; the result is `float64`; validation: `smoothing` outside 0.0 to 0.8, bool, `nan`, `inf` keep the old `ValueError` message; `window` of 0, 21, -1, 2.5, `True`, `"3"`, `None`, `nan` raises `ValueError` with the exact window message, and 1, 20 and `np.int64(5)` are accepted; constants are 1, 20, 1
  - Done: 124 tests. One test of mine had an off-by-one (the last raw value at frame 2 with a window of 2 reaches frame 4, so frame 5 is already exactly 0); fixed.
- [x] T004 In `backend/tests/test_frame_rendering.py` rewrite the tests that encode the old running average so they check the new definition (keep their intent, delete only what no longer makes sense): `reference_smooth` becomes the windowed reference (or is replaced by the loop from T003); `test_the_first_frame_is_never_changed`, `test_matches_the_formula_for_random_data`, `test_smoothing_zero_returns_equal_values_in_a_new_array`, `test_the_input_is_never_modified`, `test_each_note_uses_only_its_own_history`, `frames_until` with `test_a_note_that_stops_fades_over_more_frames_at_higher_smoothing` and `test_a_note_that_starts_rises_over_more_frames_at_higher_smoothing` (now: a stopped note is gone after exactly `w` frames and a larger `w` keeps it longer; a new note reaches its full value after `w` frames), `test_short_inputs_come_back_unchanged`, `test_output_stays_between_zero_and_the_input_maximum`, the limits tests; the hue tests built on `ref_hue_sequence` (`test_hue_sequence_without_smoothing_is_exactly_the_hues_of_each_frame`, `test_the_first_frames_hues_are_never_smoothed`, `test_the_hue_of_a_tile_is_a_running_average_of_its_own_hue`, `test_hue_smoothing_matches_the_reference_for_random_frames`, `test_each_tiles_hue_is_smoothed_only_from_its_own_history`, `test_hue_sequence_rejects_a_smoothing_outside_the_range`) with the new reference and a window argument; `test_written_frames_have_smoothed_values_and_smoothed_hues` and `test_write_frames_without_smoothing_does_not_change_the_hues`. Pass `window` where a test is about the window. Keep the file's CRLF line endings
  - Done. Rewritten: the worked example, the formula test (now with windows), the stopped/started note tests (a stopped note is exactly gone after the window, a new note reaches its full value after the window), the hue reference and its tests, the written-frames test, and the feature 010/011 tests (see T007).
- [x] T005 [P] In `backend/tests/test_frame_brightness.py` rewrite `test_brightness_is_smoothed_like_the_notes_and_hues` and `test_write_frames_smooths_the_brightness_with_the_same_smoothing` (and any other test there whose expected numbers come from the old formula) for the new definition, including a case with a window above 1; `value_sequence` takes and validates `smoothing_window`
- [x] T006 [P] In `backend/tests/test_jobs_api.py` rewrite the smoothing tests that depend on the old behavior: `test_half_smoothing_gives_the_running_average_of_each_note` (now the windowed average with the default window 1: each frame is `(own + 0.5 * previous raw) / 1.5`, computed independently in the test), `test_a_stopped_note_fades_more_slowly_at_higher_smoothing`, `test_the_loudest_smoothed_value_still_reaches_white`, the hue-smoothing tests near `test_the_hues_in_the_served_frames_are_smoothed_with_the_same_parameter` and `test_hue_smoothing_does_not_change_saturation_counts_or_timing`, `test_brightness_and_smoothing_still_set_the_tile_saturation`, and any other test whose expected values were computed from the old formula; keep the tests that only use smoothing 0, the validation tests (`test_bad_smoothing_is_refused` and the like) and the counts/timing/determinism tests. Keep the file's CRLF line endings
  - Done. Most of these tests use the helpers `ref_smooth`, `ref_smoothed_hue_rows` and `expected_pixels`; those now implement the windowed average (with a `window` argument), which fixed the tests that only depended on them. `test_a_stopped_note_fades_more_slowly_at_higher_smoothing` was replaced: with the default window a stopped note is exactly gone two frames after its last frame.
- [x] T007 In `backend/tests/test_frame_rendering.py` (after T004) adjust the tests of features 010 and 011 that rely on the old smoothing, without changing what they prove: `test_rounding_is_applied_after_smoothing` (energies 1, 0, 0 with smoothing 0.5 and a window: pick values where smoothing then rounding differs from rounding then smoothing under the new formula and check the brightest channel), `test_smoothed_saturations_are_rounded_to_the_levels`, `test_a_fading_note_turns_black_in_the_first_frame_whose_smoothed_value_is_below_the_threshold` (use a larger window, say 8, and the threshold 10, and compute the first hidden frame independently), `test_adding_silence_at_the_end_changes_no_earlier_frame` and the like; also check `test_color_levels_api.py` and `test_threshold_api.py` where they post `smoothing=0.8` (their assertions are about levels, black tiles and byte equality with and without trailing silence; adjust only if they fail). Then run `pytest` in `backend/` and confirm everything passes
  - Done. `test_color_levels_api.py`: the comparison with trailing silence is now "the steps add no difference of their own" (a subset of the frames that differ without steps), because rounding can hide the one frame that differs. 918 backend tests passed at the end of Phase 2.

**Checkpoint**: The windowed average is in place and tested, the window reaches the drawing code, and the whole backend suite is green. The API does not take the window yet.

---

## Phase 3: User Story 1 - Smooth over a fixed number of earlier frames (Priority: P1) 🎯 MVP

**Goal**: The smoothing window can be chosen through the job API; the smoothing replaces the running average; smoothing 0 changes nothing (FR-001 to FR-005, FR-007 to FR-009).

**Independent Test**: Quickstart "Story 1". A note that sounds in one short stretch disappears exactly `w` frames after it stops, and with smoothing 0 the frames are identical to those before this feature for every window.

### Tests for User Story 1

- [x] T008 [P] [US1] Create `backend/tests/test_smoothing_window_api.py` for the field, in the style of `test_threshold_api.py` (import `client`, `frame_rgb`, `leftovers`, `wav_bytes` from `test_jobs_api`): `smoothing_window` values `1`, `5`, `20`, `5.0`, ` 7 ` are accepted and echoed as integers (`5.0` returns `5`); a request that does not send the field returns `1`; refused with 400 and the exact detail `The smoothing window must be a whole number from 1 to 20.` for empty, ` `, `0`, `-1`, `21`, `100`, `2.5`, `abc`, `nan`, `inf`, `1e9`, with no job created (the temp directories are unchanged); a bad window is refused before the file is read (a non-audio body with `smoothing_window=99` gets the window message); with smoothing 0 the frames are byte-identical for windows 1, 5 and 20 and to a request without the field; with a generated WAV of a tone that sounds for a short stretch (frequency on the centre of the analysis bin of its note, as in `test_threshold_api.py`) and smoothing 0.5, a larger window keeps the note's tile visible for exactly the expected number of extra frames (compute the expected frame range independently from the smoothing-0 run: the visible range of the unsmoothed note extended by `w` frames, tolerating that the analysis windows already spread the tone), and the tile is exactly gone after that; the same request twice gives identical frame bytes
  - Done in `backend/tests/test_smoothing_window_api.py` (25 tests; the helper `expected_pixels` in `test_jobs_api.py` gained a `window` argument).

### Implementation for User Story 1

- [x] T009 [US1] In `backend/app/routers/jobs.py` add `_parse_smoothing_window(text, sent) -> int` in the style of `_parse_energy`: not sent gives `DEFAULT_SMOOTHING_WINDOW`; sent must parse as a finite float that is a whole number from `MIN_SMOOTHING_WINDOW` to `MAX_SMOOTHING_WINDOW` (empty, text, `nan`, `inf`, fractions and out-of-range refused with `HTTPException(400, "The smoothing window must be a whole number from 1 to 20.")`); return an `int`. Add the form field `smoothing_window: str | None = Form(None)` to `create_job`, parse it next to the other settings (before the file is read), pass `smoothing_window=...` to `write_frames`, add `"smoothing_window"` to the response, and update the comment above `write_frames` (smoothing is now a windowed average). Make T008 pass
- [x] T010 [US1] In `backend/tests/test_energy_api.py` add `"smoothing_window"` to the expected response keys in `test_the_other_response_fields_are_unchanged` (an intended addition). Run `pytest` in `backend/` and confirm everything passes. Then run the reference script from T001 with no `smoothing_window` field and again with `smoothing_window=20` (smoothing stays 0) and confirm both hashes are identical to the one recorded (SC-001)
  - Done: 943 backend tests passed at this point; the reference script gave the identical hash with no field, with `smoothing_window=1`, `=20`, and `=20` with `smoothing=0`.

**Checkpoint**: The API smooths over a window and, with smoothing 0, produces exactly the old frames.

---

## Phase 4: User Story 2 - Choose the smoothing window on the page (Priority: P2)

**Goal**: A Smoothing window field with an explanation and a summary line, and a rewritten Smoothing explanation (FR-006, FR-007, FR-008).

**Independent Test**: Quickstart "Story 2". Open the page, set the window, see the validation, create frames, see the window in the summary.

### Tests for User Story 2

- [x] T011 [P] [US2] In `frontend/src/utilities/validation.test.ts` add tests for the new helpers from `validation.ts` (written in T013; keep CRLF): `SMOOTHING_WINDOW_RANGE` is `{ min: 1, max: 20 }` and `DEFAULT_SMOOTHING_WINDOW` is 1; `validateSmoothingWindow` returns `null` for 1, 5, 20, `"1"`, `"20"`, `"7"`, `" 7 "` and the message `The smoothing window must be a whole number from 1 to 20.` for 0, 21, -1, 2.5, `""`, `"  "`, `"abc"`, `"NaN"`, `"Infinity"`, `"1e9"`
- [x] T012 [P] [US2] In `frontend/src/utilities/help.test.ts` replace the test that pins the old Smoothing wording with one for the new text, and add a test that `smoothingWindowHelp` says the window is the number of earlier frames mixed into each frame, that Smoothing says how strongly each counts compared with the current frame, and gives the range 1 to 20; in `frontend/src/components/SettingsForm.test.ts` add tests (using the existing `render` helper) that the rendered form has a number input with id `smoothing-window` with `min="1"`, `max="20"`, `step="1"` and value 1, a label "Smoothing window (frames)" and an info button named "About smoothing window", that the input is disabled when `busy` is true and not otherwise, and that it comes before the Smoothing slider

### Implementation for User Story 2

- [x] T013 [US2] In `frontend/src/utilities/validation.ts` add `SMOOTHING_WINDOW_RANGE = { min: 1, max: 20 } as const`, `DEFAULT_SMOOTHING_WINDOW = SMOOTHING_WINDOW_RANGE.min` and `validateSmoothingWindow(value: string | number): string | null` (a whole number from 1 to 20 using `parseNumber`, in the style of `validateEnergy`). Make T011 pass
- [x] T014 [US2] In `frontend/src/utilities/help.ts` add `smoothingWindowHelp`, built from `SMOOTHING_WINDOW_RANGE` (whole number, 1 to 20: how many earlier frames are mixed into each frame; 1 looks back one frame; a value or note is forgotten that many frames after it stops), and rewrite `smoothingHelp` for the new meaning (0 is no smoothing; otherwise each frame in the window counts this fraction as much as the current frame, so higher values blend more and fade notes more slowly). Make T012's help part pass
- [x] T015 [P] [US2] In `frontend/src/api.ts` add `smoothing_window: number` to `JobResult` and `smoothingWindow: number` to `JobSettings`, and append `smoothing_window` to the form in `submitJob`
- [x] T016 [US2] In `frontend/src/components/SettingsForm.vue` add `smoothingWindowText` (string ref, default `String(DEFAULT_SMOOTHING_WINDOW)`), `smoothingWindowError` (`validateSmoothingWindow`), include it in `canSubmit`, and emit `smoothingWindow: Number(smoothingWindowText.value)`. Add the field directly above the Smoothing slider, built like the Brightness number field (`field`, `field-head` with a label "Smoothing window (frames)" for `smoothing-window` and an `InfoPopover` labelled "smoothing window" using `smoothingWindowHelp`, a number input `id="smoothing-window"` with `step="1"`, `:min`/`:max` from `SMOOTHING_WINDOW_RANGE`, `inputmode="numeric"`, `:disabled="busy"`, and an inline error line). Make the rest of T012 pass
- [x] T017 [US2] In `frontend/src/App.vue` add the summary item `Smoothing window: {{ result.smoothing_window }}` after Smoothing. Run `npm test`, `npm run typecheck` and `npm run build` in `frontend/` and confirm all pass
  - Done: 257 frontend tests, typecheck and build pass; the form renders the new field (server-side render test), but see T023.

**Checkpoint**: The window can be set on the page and is shown in the summary.

---

## Phase 5: User Story 3 - Smoothing applies to everything it applied to before, and comes first (Priority: P3)

**Goal**: The same window and weight smooth the note values, the hues and the frame brightness, before the gray levels, roots, level steps and threshold (FR-004, FR-005).

**Independent Test**: Quickstart "Story 3". With a window of 8, smoothing 0.8, threshold 10 and Saturation steps 20, a note that stops fades, turns black once under 10% of the loudest smoothed value, and every tile's saturation is one of the six levels.

- [x] T018 [P] [US3] In `backend/tests/test_frame_rendering.py` add interaction tests on `write_frames` (append; CRLF): the three smoothed quantities use the same window and weight (an impulse in the note values, in the energies and in a hue-producing partner note all vanish exactly `w` frames later; check with `smoothing_window` 1, 4 and 20); smoothing is applied before the level steps and the threshold (a faded value that is rounded or hidden is the smoothed one, computed independently with `smooth_frames`); the gray levels are scaled against the largest smoothed value (the loudest smoothed note is fully saturated, as before); a hidden or silent frame stays black with every window; with `smoothing=0` the written files are byte-identical for windows 1 and 20 and to a call without the argument; appending silent frames at the end changes no earlier frame's bytes (smoothing looks only backwards; the peak does not change)
  - Done. A mutation check (dividing every row by the full `1 + s*w` instead of the weights actually used) made 59 tests fail, then was reverted.
- [x] T019 [P] [US3] In `backend/tests/test_smoothing_window_api.py` add one API test: a generated multi-note WAV posted with `smoothing=0.8`, `smoothing_window=8`, `threshold=10`, `saturation_step=20` and `brightness_step=50` gives frames in which every tile's saturation (for tiles bright enough to read) is one of the six levels and every tile is black or the tile of the same request with `threshold=0`, and the same file with one second of silence appended differs only in the frames that also differ without any step (at most the last original frame)

**Checkpoint**: Combinations behave as specified. A failure here points at the order of smoothing and the later steps in `write_frames`.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T020 [P] Update `README.md`: rewrite the **Smoothing** bullet for the new method (the formula `( A[t] + s*A[t-1] + ... + s*A[t-w] ) / ( 1 + s*k )`, `k = min(t, w)` earlier frames; weights divided by their sum; the first frame unchanged; finite memory of exactly `w` frames; applies to the note values, the tiles' hues as plain 0 to 360 numbers and the frame brightness, before the gray levels, roots, level steps and threshold; smoothing 0 = no smoothing for every window; the old endless running average and its numbers, such as "a note that stops falls below 10% after 11 frames", are gone), add the **Smoothing window** setting (whole number 1 to 20, default 1, the page field above Smoothing with its info button and summary line, the API field `smoothing_window` with its 400 message and response field), and mention `specs/012-smoothing-window/data-model.md`. Search the README for any other sentence that describes the old smoothing and fix it
- [x] T021 Run everything: `pytest` in `backend/`, `npm test`, `npm run typecheck` and `npm run build` in `frontend/`; all must pass. Report the final test counts against the T001 baseline, and the reference script's hash with the default settings (it must still equal the recorded one)
  - Done: backend 790 → 957 tests, frontend 233 → 257 tests, all passing; typecheck and build clean; reference hash unchanged.
- [x] T022 Measure performance (SC-008): with the `perf.py` script from the session scratchpad adapted to send `smoothing_window` and `smoothing` (or an equivalent timing through the test client on a 60 s file, median of at least 15 interleaved runs), compare smoothing 0 (window 1), smoothing 0 (window 20), and smoothing 0.8 with window 20; the first two must not differ measurably and the last must be within 25% of the first. If not, profile `smooth_frames` and fix before finishing
  - Done: 60 s file (1800 frames), 15 interleaved runs, medians: smoothing 0 window 1 1.04 s, smoothing 0 window 20 1.03 s, smoothing 0.8 window 1 0.98 s, smoothing 0.8 window 20 0.98 s; minimums 0.94 to 0.96 s in every case. The smoothing costs nothing measurable (within noise), well inside the 25% limit.
- [ ] T023 Follow `specs/012-smoothing-window/quickstart.md` Stories 1 to 3 in the running application (a real browser, if one can be used), including the refused-request examples. If a browser cannot be used, say so explicitly in the report and leave this task unchecked with a note of what was verified through tests and direct API calls instead
  - NOT done: the walk-through in a real browser (entering the window, the validation messages, the popovers, the summary after a job, watching a note disappear after `w` frames in the animation). Verified instead through tests and direct API calls: the field's range, step, start value, label, info button, disabled state and position in the rendered form; the field's validation and refusals; and the frames, including a stopped note being exactly gone after the window.

---

## Dependencies & Execution Order

- Phase 1 first. Phase 2 blocks the stories: T002 first; then T003, T005 and T006 in parallel (different files); T004 and T007 are sequential in the same file (T004 then T007) and need T002.
- **US1 (Phase 3)** needs Phase 2. T008 is written first (it fails until T009); T009 before T010.
- **US2 (Phase 4)** can start after Phase 2 and run in parallel with US1 (frontend vs backend files); the end-to-end check in T017 needs the API field from T009. T013 before T014 and T016; T015 before T016 and T017.
- **US3 (Phase 5)** needs T002 and T009. T018 and T019 are independent.
- **Polish** last; T020 can be done any time after T009 and T016.

### Parallel opportunities

- T003, T005, T006 after T002; the frontend track (T011 to T017) alongside the backend track after Phase 2; T018 and T019; T020 with T021's preparation.

## Implementation Strategy

- **MVP**: Phases 1 to 3 (US1). The API smooths over a window and smoothing 0 leaves frames unchanged; the window can be tried with curl or the API docs.
- Then US2 puts the field on the page and US3 locks in the interactions with the level steps, the threshold and the other smoothed quantities.
- Keep the change reviewable: one function is replaced, three functions gain one optional argument, no new module, and do not touch the note analysis, the energy measure, the hue calculation, the level-step code or the threshold code.
- The largest part of the work is bringing the existing tests that encode the old running average up to the new definition (T004 to T007); they are listed in research Decision 8 so none is missed.
