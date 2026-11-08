---
description: "Task list for the Noise Floor feature"
---

# Tasks: Noise Floor

**Input**: Design documents from `/specs/033-noise-floor/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/noise-floor.md](contracts/noise-floor.md), [quickstart.md](quickstart.md)

**Tests**: Tests are written first (they fail where behaviour is missing), against the independent rule written in the tests; mutation checks follow each implementation task (`python -B`, `__pycache__` cleared, see below). Backend commands are run in `backend/` with `.venv/Scripts/python.exe`; long runs go to the background.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependencies)
- **[Story]**: the user story of the spec (US1 the cut, US2 the chords, US3 fixed for every picture)

## Path Conventions

Web application: `backend/app/...`, `backend/tests/...`; no frontend change.

---

## Phase 1: Setup

- [x] T001 Record the baseline before any change: clear the `__pycache__` folders under `backend/` (not `.venv`), run `python -B -m pytest -q` in `backend/` and `npx vitest run` in `frontend/`; write the counts at the end of this task in `tasks.md` (expected at the start: backend 6263 passed, frontend 820 passed). Run `git status` and note that the features 030 to 032 files are still uncommitted, so this feature's changes must be told apart from them by file name (`noise_floor.py`, `test_noise_floor*.py`, and the named edits below).
  **Done 2026-11-07**: baseline backend 6263 passed, frontend 820 passed (the runs at the end of the previous feature, on the same code); `git status` showed a clean tree (features 030 to 032 had been committed) except `specs/033-noise-floor/`. **Final**: backend 6332 passed (6263 + 69 new), frontend 820 passed (untouched).

**Checkpoint**: the baseline is green and written down.

---

## Phase 2: Foundational - the cut itself

**Purpose**: `apply_noise_floor` and `floor_analysis` exist and are right on their own; every story uses them.

- [x] T002 Create `backend/tests/test_noise_floor.py` (spec FR-001, FR-002, FR-007, SC-001; data-model "The cut"; contract), with an independent oracle (a Python loop over the values, written in the test, using the ratio `1 / 1000` written out and not `10 ** (-60 / 20)`), expecting these to fail first (the module does not exist): the constants (`NOISE_FLOOR_DB == -60`; `NOISE_FLOOR == 0.001` and `== 10 ** (-60 / 20)`); the examples of the contract with a peak of 1.0 (1.0 kept, `0.001` exactly at the floor kept, `0.00099999` cut to exactly `0.0`, 0.0 stays 0.0, 0.5 kept); the reference being the largest value anywhere in the array (a loud value in one window cuts the quiet values of the other windows; a loud value in column 87, one of the four undrawn notes, counts); a note is judged on its own window (the same note above the floor in one window and below it in another); `peak=` given overrides the array's own (a peak of 10 cuts 0.5; a peak of 0 cuts nothing); silent array (all 0) and empty arrays `(0, 88)` and `(0,)` unchanged; any shape (1-d, 2-d, 3-d); integer input comes back as `float64`; the input is not changed and the result does not share memory with it; idempotence on random arrays (`cut(cut(a)) == cut(a)`); never a new or larger value (`result <= input` everywhere and equal where kept); monotone (if a smaller value is kept then every larger one is kept); random arrays and random peaks against the oracle, with tie values at exactly the floor built from exactly representable numbers (peak 1.0, 0.5, 0.25... and the floor 0.001 written as the same literal); the refusals with their exact messages (`nan`, `inf`, a negative value, strings, `None`: `The note values must be finite numbers that are not negative.`; a bad `peak`: negative, `nan`, `inf`, a string, a bool: `The peak must be a finite number that is not negative.`); `floor_analysis` returns a new `AnalysisResult` whose `frames` are the cut of the old ones (reference over all windows and columns) and whose `sample_rate`, `window_size`, `sample_count`, `starts` and `step` are the same objects/values, and does not change the result it was given; two runs give equal results.
- [x] T003 Create `backend/app/services/noise_floor.py`: `NOISE_FLOOR_DB = -60`, `NOISE_FLOOR = 10 ** (NOISE_FLOOR_DB / 20)`, `apply_noise_floor(values, peak=None)` and `floor_analysis(result)` as in the contract (a module docstring that says what the floor is, what it is measured against, that it is fixed, strictly below, idempotent; messages as in T002). Run T002 and fix.
- [x] T004 Mutation checks for the cut (as in features 031/032: a script in the scratchpad that applies one change at a time to `noise_floor.py`, clears `__pycache__`, runs `tests/test_noise_floor.py -x` with `python -B`, and restores the file): `<` to `<=`; the factor 1000 to 100 and to 10000; the peak taken from the first 84 columns only; the peak per window instead of per file; the peak of the cut values (instead of the original); no copy (the input changed); the result kept as the input's type; `peak=` ignored; `peak=0` cutting everything; cut to the floor value instead of 0; the check of negative values skipped; `floor_analysis` dropping `starts` or `step`; each must be caught. Record any survivor and why (equivalent or a missing test).

**Checkpoint**: `tests/test_noise_floor.py` is green and the mutants are caught.

---

## Phase 3: User Story 1 - A note that is practically silent is not a note (Priority: P1) 🎯 MVP

**Goal**: In a job, the analysed windows are cut before anything else sees them, for every image type.

**Independent Test**: A file with one loud tone and, in another run, the same plus a second tone 70 dB below it: the note values that reach `write_frames` are 0 in the faint note's column in every window, for each of the nine image types, and the loud tone is untouched.

### Tests for User Story 1 (write first)

- [x] T005 [US1] Create `backend/tests/test_noise_floor_api.py` (spec Story 1 and FR-001, FR-004; quickstart scenario 2). Use the helpers of `test_jobs_api.py` / `test_peak_tile_colors_api.py` (`note_tone`, `wav_bytes`, `post`, `all_frames`, `client`) and a wrapper installed with `monkeypatch` on `jobs.write_frames` that records its first argument (the averaged note values, `(frames, 88)`) and then calls the original. A file with a loud tone at a note and a second tone 70 dB below it (amplitude ratio about 0.0003) at a note whose spectrum bin it does not share, for each of the nine image types (`tiles`, `blended`, `contour`, `circles`, `circles_paint`, `concentric`, `decay`, `decay-exp`, `polar-chords`; the shortest file and settings that make the job quick, a window size at which the two notes have bins of their own, as `test_chords_audio.py` does): the recorded values in the faint tone's column are exactly 0 in every frame, the loud tone's column is greater than 0 in the frames it sounds in, and every recorded value is either 0 or at least `0.001 ×` the largest recorded value over the file... (the cut of the averaged values: because the cut is made on the windows the frames average, a recorded frame value may be a window average below the floor only where some of the averaged windows were cut; assert only "no value is below the floor of its windows": compare the recorded array with `average_frames(floor_analysis(analyze_channels(...)), ...)` computed in the test with the same arguments, array for array, equal); the same file with the second tone only 50 dB down keeps a non-zero value in its column (so the test would notice a floor that is too high); a silent file gives the same frames as before the feature (all 0). Expected to fail first (the job does not cut).
- [x] T006 [US1] Add to `backend/tests/test_noise_floor_api.py` the pictures themselves for the cases where the observable is simple (spec Story 1 scenarios 2 and 3): `polar-chords` with Notes shown 8 and one loud tone plus a faint one: exactly one note bar (the picture of the file without the faint tone has the same bar and nothing else in the faint note's arc); `tiles`: the colour of the faint note's tile is exactly the first row of the colormap (silence), as for a note that does not sound; a window made only of faint notes (a short stretch where only the faint tone sounds, with a loud tone before and after it) is drawn as a silent frame for `decay-exp` (no points added).

### Implementation for User Story 1

- [x] T007 [US1] In `backend/app/routers/jobs.py` import `floor_analysis` and call it on the result of `analyze_channels` (`result = floor_analysis(analyze_channels(...))`, a comment that says what and why, before the beat and `write_frames`). Run T005 and T006 and fix.
- [x] T008 [US1] Mutation checks for the wiring: the call removed; the call after `average_frames`; the call on the wrong object (a copy that is not used); the floor applied only for some image types; the reference per window; each must be caught by T005/T006.

**Checkpoint**: the notes that reach every picture are cut; the beat is unchanged (checked: it is measured from the audio).

---

## Phase 4: User Story 2 - A note that is practically silent is not part of a chord (Priority: P1)

**Goal**: `measure_chords` honours the floor for any array, cuts before combining octaves, and no longer has the 1e-6 per-window floor.

**Independent Test**: C, E, G at 1.0, 0.9, 0.8 and Bb at 0.0009: `(4, 7)`; with Bb at 0.001: `(4, 7, 10)`.

### Tests for User Story 2 (write first)

- [x] T009 [US2] Update `backend/tests/test_chords.py` (spec Story 2, FR-005, SC-003; contract "Changed behaviour"): add an independent `floored(values)` helper (a loop: the largest value of the whole array, a value strictly below `peak / 1000` set to 0) and use it where the oracle gets its rows: `assert_like_the_oracle`, `assert_limited_like_the_oracle` / `allowed_by_the_pictures` (the order is floor, then the Notes limit, then the Threshold), the oracle `oracle_letters` (it loses its relative `1e-6` rule and works on rows that were already cut); replace `test_a_letter_much_weaker_than_the_loudest_does_not_sound` (the 2e-6 / 1e-6 / 1e-9 cases) by tests of the new floor: Bb at 0.0009 gives the triad and at 0.001 the seventh chord (exactly at the floor counts), with the other notes at 1.0, 0.9, 0.8; a faint G (0.0009) with loud C and E records `(4,)` and G is not in the notes; a window whose notes are all below the floor of a loud note elsewhere in the array has no chord; the reference is the largest value of the whole array including the columns 84 to 87; the octaves of a letter that are each below the floor but add up to more than it do not sound (the notes are cut before the letters are added: two octaves of 0.0006 beside a loud note); idempotence (`measure_chords` on cut values gives the same records as on the uncut values); the input is not changed. Adjust any other test of the file whose faint notes are below a thousandth of the loudest value (the random windows with `** 4` strengths, `random_windows`, the threshold tests) so that it is the oracle on cut values that decides. Expected to fail first.
- [x] T010 [P] [US2] Add to `backend/tests/test_polar_chords.py` and `backend/tests/test_polar_chords_api.py` (spec Story 2 scenarios 1 and 5): a triad with a faint extra note (Bb at 0.0009) through `polar_bars` gives the triad's chord place (22 for C), not the seventh chord's; through a job (a triad plus a faint tone 70 dB down) the chord bar is the triad's, as `test_a_triad_makes_three_note_bars_and_the_chord_bar...` expects.

### Implementation for User Story 2

- [x] T011 [US2] In `backend/app/services/chords.py`: import `apply_noise_floor`; in `measure_chords` cut `values[:, :NOTES]` first (peak = the largest value of the whole array given, all columns), before the Notes limit and the Threshold; remove the `NOISE_FLOOR = 1e-6` constant and the relative floor in `_letters`; update the module docstring (the noise floor paragraph, no "millionth"). Run T009 and T010 and fix.
- [x] T012 [US2] Mutation checks for the chords: the cut skipped; the cut after the Notes limit; the cut after the letters are combined; the peak from the first 84 columns only; the peak per window; `<=` for `<`; the old relative floor kept as well and the cut made weaker (factor 100); each must be caught. Record any survivor and why.

**Checkpoint**: no recorded chord contains a note under the floor; Polar Chords shows the triad, not an invented seventh chord.

---

## Phase 5: User Story 3 - It is fixed, for every picture, with or without a Threshold (Priority: P2)

**Goal**: The floor works with the Threshold, adds no setting, and changes nothing for a file with nothing under it.

**Independent Test**: The same file with every image type, with a Threshold of 0 and of 5: the faint note is 0 in both; the request and the response have no new field.

### Tests for User Story 3 (write first)

- [x] T013 [US3] Add to `backend/tests/test_noise_floor_api.py` (spec Story 3, FR-003, FR-006, SC-004, SC-005, SC-006): for each image type with and without `threshold` (0, 5 and the highest the page allows, 10), the values that reach `write_frames` are the same in the faint note's column (0) whatever the Threshold is (the Threshold is applied inside `write_frames`, after the cut: the recorded input is independent of it); a job request that has no new field is accepted and a job made with a field called `noise_floor` (or any made-up name) is handled as every unknown field is today (its response has no `noise_floor` key: compare the set of keys of the response with the keys of the job response in an existing test, or with a response snapshot taken in the test from a plain job); the stricter of the Threshold and the floor decides (with a Threshold of 5 percent a note at 2 percent is hidden, as before; with 0 a note 70 dB down is still not counted); a file in which every sounding note is at or above the floor (tones of equal strength, a window size at which their leakage is below the floor... or a synthetic analysis passed through `floor_analysis` equal to itself) gives frames identical to the frames made without the cut (SC-005: compare the recorded `write_frames` input with and without a stubbed `floor_analysis`, or run `write_frames` on both).
- [x] T014 [US3] Make the tests of T013 pass (they should need no new code; if one fails, the cause is fixed in `noise_floor.py` or `jobs.py`, not by changing the test).

**Checkpoint**: nothing in the request, the response or the page changed (the frontend suite is untouched and green).

---

## Phase 6: The rest of the suite

**Purpose**: find, understand and update the expectations that rested on values under the floor; change nothing else.

- [x] T015 Clear the `__pycache__` folders and run the whole backend suite in the background (`python -B -m pytest -q`, output to a file in the scratchpad). For every failing test write down, here, the test, why it failed, and its category: (a) the expectation rested on a leaking or faint value under the floor (a colour or a bar computed from a value under a thousandth of the loudest, a faint neighbour of a synthesized tone) - update the expectation to the new rule and say how; (b) a real fault of the implementation - fix the implementation; nothing else is allowed. List (T015, 2026-11-07): the full run found **17 failures, all category (a), all one cause**: the tests rebuild the expected pictures from the raw analysis (`analyze_channels` then `average_frames`), without the floor. They are `test_colormap_api.py::test_every_tile_of_every_served_frame_is_the_table_colour_of_its_own_strength` (10 colormaps), `test_jobs_api.py::test_spacing_one_matches_consecutive_window_analysis`, `::test_half_smoothing_gives_the_windowed_average_of_each_note`, `::test_a_stopped_note_is_gone_one_frame_after_it_stops_with_the_default_window`, and `test_smoothing_window_api.py::test_frames_are_the_windowed_average_of_each_note_and_a_stopped_note_is_exactly_gone` (3 cases) and `::test_the_threshold_works_on_the_smoothed_values`. No fault of the implementation.
- [x] T016 (done: the two places that rebuild the reference pipeline, `frame_values` and `test_spacing_one_matches_consecutive_window_analysis` in `tests/test_jobs_api.py`, now apply `floor_analysis` like the job, with a comment; the other 15 failures used `frame_values`; 291 tests of the three files pass, then the whole suite) Update the tests of category (a) from T015, one by one, each with a comment that says that the faint value is now 0 because of the noise floor; re-run them and the whole suite. No picture, measurement or test helper is changed to keep an old expectation.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T017 [P] Documentation: in `README.md` a "Noise floor" paragraph (the level, −60 dB as a factor of 1,000 in strength, what it is measured against (the loudest note of the file, the four undrawn notes included), fixed with no setting, every picture, the chords, strictly below, exactly at the floor counts, that a very loud click can silence quiet music around it, where it is applied (right after the analysis) and that the beat does not change), and the chord paragraph without "under a millionth of the loudest letter of the window"; in `specs/031-chord-interval-metric/` replace the per-window floor (spec FR-003/assumptions, plan, research Decision 3, data model "The letters", contract) by a reference to this feature, and add a line to its `tasks.md` Phase 8 that says so; check `quickstart.md` of this feature still matches what was built and fix it where it does not; tick the boxes of the `checklists/requirements.md` notes that were assumptions if the user has confirmed them (not before).
- [x] T018 Final run: clear `__pycache__`, `python -B -m pytest -q` in `backend/` and `npx vitest run` in `frontend/` (the frontend is untouched; say so); `git status` shows only `noise_floor.py`, `jobs.py`, `chords.py`, the new and changed test files, the README and the spec folders as this feature's changes (besides the uncommitted work of 030 to 032); time `apply_noise_floor` on 4,000 windows of 88 notes and a whole job against the baseline of T001 and report against SC-007; run quickstart scenarios 1 to 5 as far as they can be done by script and say which were not watched. Re-run the two real files (`audio/sonata.wav`, `audio/fotr-intro1-echo.wav`) through `floor_analysis` and `measure_chords` and report how many note values the floor cuts and how the chord rates change (for the user; the floor does not change what is tonal and what is not). Tick the boxes of this file and write the counts at the end of T001's line.

---

## Dependencies & Execution Order

- T001 first. Phase 2 (T002 to T004) before any story: every story uses the cut.
- US1 (T005 to T008) is the MVP. US2 (T009 to T012) needs only the cut, not the job change, so it could follow Phase 2 directly; they edit different files except that T010 and T005 both use the job path, so do them in order. US3 (T013, T014) needs T007.
- T015 and T016 after all the code. T017 [P] can be done at any time after the behaviour is fixed; T018 last.

```text
T001 → T002 → T003 → T004 → ┬→ T005 → T006 → T007 → T008 ─┬→ T013 → T014 ─┐
                             └→ T009 → T010 → T011 → T012 ─┘                ├→ T015 → T016 → T018
                                                                 T017 [P] ────┘
```

## Parallel Example

```text
Task: "T010 chords through Polar Chords (backend/tests/test_polar_chords*.py)"
Task: "T017 README and the 031 documents"
```

## Implementation Strategy

1. **MVP**: Phases 1 to 3: the cut and its place in the job, for every picture (the notes).
2. Add Phase 4 (the chords, and the removal of the weaker floor) and Phase 5 (fixed, with the Threshold).
3. Phase 6 is where the cost of the change shows: the tests that rested on faint values. Each is understood before it is changed.
4. Stop at each checkpoint to run the new tests; run the whole suite at the end of Phase 3 as well, to learn the extent of Phase 6 early.
