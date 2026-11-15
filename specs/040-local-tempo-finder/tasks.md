# Tasks: Local Tempo Finder

**Input**: Design documents from `/specs/040-local-tempo-finder/` (plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md)

**Prerequisites**: plan.md, spec.md

**Tests**: Included. The project works tests first, with oracles worked out by hand (not copied from the code under test) and mutation checks of the new rule. Backend: `backend/.venv/Scripts/python.exe -B -m pytest`; frontend: `npx vitest run` and `npx vue-tsc --noEmit` from `frontend/`.

**Organization**: By user story. The shared settings change (Prominence fixed at 20%, Minimum distance 350) is Foundational because Rhythm Circles (US2) and the other image types (US4) both depend on it.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- Paths are from the repository root

---

## Phase 1: Setup

- [X] T001 Run the whole backend suite and the frontend suite once and note the counts (baseline: backend 4673 passed, frontend 871 passed, `vue-tsc` clean) so that later failures are known to be this feature's

---

## Phase 2: Foundational (shared settings: Prominence fixed at 20%, Minimum distance 350)

**Purpose**: The Local peaks settings that every image type using the peaks shares. No user story can be judged on real files before these are in place.

**⚠️ CRITICAL**: Write the changed tests first and see them fail, then change the code.

- [X] T002 [P] Update `backend/tests/test_local_peaks.py`: the default minimum distance is 350 (`DEFAULT_MIN_DISTANCE == 350.0`, a measurement without arguments uses 350 and 20 as `min_distance`/`prominence` of its result); the range, the checks and their messages stay as they are
- [X] T003 [P] Update the request tests of every file that sends or checks `peak_prominence` (`backend/tests/test_peak_tile_colors_api.py`, `test_rhythm_circles_api.py`, `test_decay_api.py`, `test_decay_exp_api.py`, `test_polar_chords_api.py`, `test_chromatic_decay_api.py`, `test_chromatic_decay_peaks.py`, `test_chromatic_wireframe_api.py`, `test_contour_beat_wave_api.py`, `test_contour_api.py`, `test_colormap_api.py`, `test_noise_floor_api.py`, `test_energy_graphs_api.py`, `test_note_count_api.py`, `test_interpolation_api.py`, `test_resolution_api.py`): the response has no `peak_prominence`; a request that sends `peak_prominence` (any value, even an invalid one) is accepted and ignored (no 400, the measurement spy sees 20); the default `peak_distance` is 350; the 400 for an invalid distance is unchanged; tests that only checked the prominence's validation are removed (grep `peak_prominence` and `prominence` in `backend/tests` to find them all)
- [X] T004 [P] Update the frontend tests first: `frontend/src/utilities/validation.test.ts` (no `PEAK_PROMINENCE_RANGE`, `DEFAULT_PEAK_PROMINENCE`, `validatePeakProminence`, `formatPeakProminence`; `DEFAULT_PEAK_DISTANCE` is 350), `frontend/src/utilities/groups.test.ts` (the two Local peaks groups have no `peak-prominence`), `frontend/src/utilities/help.test.ts` (no `peakProminenceHelp`; the Minimum distance help mentions the 350 default and the fixed 20%), `frontend/src/components/SettingsForm.test.ts` (no Prominence control; Minimum distance starts at 350; the form still submits `peakDistance`), `frontend/src/api.test.ts` and `frontend/src/App.test.ts` (no `peak_prominence` in the body or the result; no "Prominence:" line)
- [X] T005 Change `backend/app/services/local_peaks.py`: `DEFAULT_MIN_DISTANCE = 350.0`, `DEFAULT_PROMINENCE = 20.0` (the checks stay), and update the module docstring where it names the defaults (depends on T002)
- [X] T006 Change `backend/app/routers/jobs.py`: remove the `peak_prominence` form field, its parsing (`_parse_peak_setting` for prominence), the `check_prominence`/`DEFAULT_PROMINENCE` import use and the `"peak_prominence"` response key; pass `DEFAULT_PROMINENCE` (20) to every `measure_local_peaks` call (the beat measurement and the rhythm measurement); update its docstrings (depends on T003, T005)
- [X] T007 [P] Change the frontend: `frontend/src/utilities/validation.ts` (remove the prominence range/default/message/validator/formatter, `DEFAULT_PEAK_DISTANCE = 350`, fix the comments that name Prominence), `frontend/src/utilities/groups.ts`, `frontend/src/utilities/help.ts`, `frontend/src/api.ts` (settings, form body and result without prominence), `frontend/src/App.vue` (remove the Prominence line and its import), `frontend/src/components/SettingsForm.vue` (remove the control, its ref, error, validity term and help; Minimum distance default from the constant) (depends on T004)

**Checkpoint**: backend and frontend suites pass; the page shows Minimum distance at 350 ms and no Prominence.

---

## Phase 3: User Story 1 - A steady current tempo that follows the music (Priority: P1) 🎯 MVP

**Goal**: A pure tempo finder, `find_tempo(times)`, that follows the rule of research D1 and keeps the tempo between 60 and 156.

**Independent Test**: `pytest backend/tests/test_tempo_finder.py` (peak times alone, no audio).

### Tests for User Story 1 (write first, they MUST fail)

- [X] T008 [US1] Create `backend/tests/test_tempo_finder.py` with oracles worked out by hand: no peaks and one peak give the tempo 120 (one tempo per peak, `restarts == 0`); the first peak gives no sample; a worked sequence of 4 to 6 peaks with the expected tempo after each computed by hand from the rule (matching by ratio, window mean, population standard deviation with the minimum step 1, the weighted average, the move by one standard deviation and never past the sample); steady 100 and 116 settle exactly on themselves (also with every second peak: 50 and 58, which are matched as the tempo's half); steady 70 settles at 105 (two thirds); steady 150 settles at 150; a stray peak moves a settled tempo by less than 10%; a step that would pass 156 gives 78 with the window emptied (the sample count starts again: check the next step uses a one-sample window), one below 60 gives 120 with the window emptied; every tempo of random peak sequences (seeded) is from 60 to 156 inclusive; the result is the same on two runs; invalid times (not 1-D, NaN/inf, not strictly increasing, not numbers) raise `ValueError("The peak times must be a 1-D array of finite numbers in strictly increasing order.")`; the inputs are not changed

### Implementation for User Story 1

- [X] T009 [US1] Create `backend/app/services/tempo_finder.py` with the constants of data-model.md (`START_TEMPO`, `LOW_LIMIT`, `HIGH_LIMIT`, `HIGH_RESTART`, `WINDOW`, `MIN_STEP`, `RATIOS`), a frozen `TempoTrack(tempos, restarts)` and `find_tempo(times)` following the state transitions of data-model.md; a module docstring that states the rule in words and says what it is for (depends on T008)
- [X] T010 [US1] Mutation-check the finder with the scratchpad `mutate.py` approach: each of these mutations must make at least one test of `test_tempo_finder.py` fail: matching by absolute instead of ratio, no minimum step, `<=` to `<`, sample dropped from the window before the statistics, moving past the sample, no window reset on a restart, `HIGH_RESTART` 78 to 156/2 of the value, limits `>`/`>=` swapped, the window of 5 changed; fix the tests (not the code) for any survivor

**Checkpoint**: User Story 1 works on peak times alone.

---

## Phase 4: User Story 2 - Rhythm Circles show the tempo layers (Priority: P1)

**Goal**: Rhythm Circles has eight circles: two thirds of the tempo, its rate of change, half of the tempo, its rate, the tempo, its rate, the local peak, its rate (outer to inner).

**Independent Test**: `pytest backend/tests/test_rhythm_circles.py backend/tests/test_rhythm_circles_api.py`

### Tests for User Story 2 (write first, they MUST fail)

- [X] T011 [P] [US2] Rewrite the series tests in `backend/tests/test_rhythm_circles.py`: `peak_series(times, tempos)` is `(peaks, 8)` with the columns of data-model.md, computed by hand from a short list of peak times and rates (levels `T/1.5`, `T/2`, `T`, the peak's rate; rates of change `(x[i]-x[i-1])/(t[i]-t[i-1])`, 0 for the first peak, the spike at a restart); `DEFAULT_SPEEDS == (80, 0, 60, 0, 120, 0, 60, 0)`; before the first peak and with no peaks the speeds are the defaults; speeds and angles (`circle_speeds`, `circle_angles`, `rhythm_angles`) at chosen moments against hand-computed numbers (the tempo ring at 120 rpm, the half ring at 60, the two-thirds ring at 80 at the start); remove the tests of the aggregated circles (`aggregate_tempo`, the 8/4/2 layers) with their helpers; the picture tests (8 rings, colormap positions `(k-1)/7`) are unchanged
- [X] T012 [P] [US2] Update `backend/tests/test_rhythm_circles_api.py`: a Rhythm Circles job measures the peaks once with `peak_distance` and 20, the response has no `peak_prominence`, the frames are eight rings; the settings that do not apply are still ignored; the 400 for an invalid distance is unchanged

### Implementation for User Story 2

- [X] T013 [US2] Change `backend/app/services/rhythm_circles.py`: remove `AGGREGATE_PERIODS`, `LAYERS`-from-aggregates and `aggregate_tempo`; `peak_series(times, tempos)` calls `find_tempo(times)` and builds the eight columns of data-model.md (levels outer to inner `T/1.5`, `T/2`, `T`, `tempos[i]`, each followed by its rate of change); `DEFAULT_SPEEDS = (80, 0, 60, 0, 120, 0, 60, 0)`; rewrite the module and function docstrings for the new layers; `rhythm_angles` and the drawing code are unchanged (depends on T009, T011)
- [X] T014 [US2] Mutation-check the series (columns swapped, `T/1.5` and `T/2` swapped, rate of the wrong level, no spike at a restart, first-peak rate not 0, defaults changed): each must make a test fail (depends on T013)

**Checkpoint**: Rhythm Circles of any file shows the new layers; the series is verified without audio.

---

## Phase 5: User Story 3 - The two sample files (Priority: P1)

**Goal**: The finder measured on `sonata.wav` and `almost2.wav`, reported, with the invariants asserted (the thresholds are reported, not gated: research D2).

**Independent Test**: `pytest backend/tests/test_tempo_files.py -s`

- [X] T015 [US3] Create `backend/tests/test_tempo_files.py`: for each of `backend/audio/sonata.wav` (target 116) and `backend/audio/almost2.wav` (target 90): `measure_wav(path, 350, 20)`, `find_tempo` over the peak times, print the peaks, the restarts, the share of time after 10 seconds within 10% of the target and the tempo every 10 seconds; assert one tempo per peak, every tempo from 60 to 156, two runs identical; skip with a message if the file is missing (depends on T009)
- [X] T016 [US3] Run it with `-s`, and write the measured numbers (peaks, restarts, share near the target) into `specs/040-local-tempo-finder/research.md` D2 if they differ from the prototype's (22% / 40 restarts and 7% / 22 restarts), and say so in the final report with the one-line variant (`RATIOS`) for the user to decide (depends on T015)

**Checkpoint**: The user has the numbers for both files.

---

## Phase 6: User Story 4 - The other image types keep the local peak (Priority: P2)

**Goal**: Nothing changes for the other types except the shared settings.

**Independent Test**: the existing tests of those types pass unchanged apart from T003.

- [X] T017 [US4] Add to `backend/tests/test_peak_tile_colors_api.py` (or the nearest existing file for beat positions) a test that for Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe and Contour with Beat coloring the beat handed to the drawing is `measure_local_peaks(left, right, rate, 350, 20).frame_positions(fps, frames)` of the file (an independent oracle: measured by the test itself), and that Energy Graphs and Contour without the box do not measure at all (depends on T006)
- [X] T018 [US4] Check the frontend: the Local peaks group of those types shows Minimum distance and, for Contour, the Beat coloring box; no Prominence anywhere (covered by T004/T007; confirm by `grep -ri prominence frontend/src` listing only comments that explain history)

---

## Phase 7: Polish & Cross-Cutting

- [X] T019 [P] Update `README.md`: the Rhythm Circles paragraph (eight circles of the tempo finder, the rule in plain words, the limits 60 and 156, restarts at 78 and 120, the sample files and their measured numbers), the Local peaks paragraph (Prominence fixed at 20%, Minimum distance default 350, `peak_prominence` no longer in the request or the response), the settings page paragraph (no Prominence), and a line for feature 040 in the same style as the others
- [X] T020 [P] Save the user's choices to memory (`local-tempo-finder-decisions.md` already exists: add the final series layout, the measured numbers and the variant offered) and keep `MEMORY.md` current
- [X] T021 Run the whole backend suite, the frontend suite and `vue-tsc --noEmit`; everything passes; fix any other test that mentioned the aggregated circles or the prominence
- [X] T022 Look at the real picture: render Rhythm Circles frames of `sonata.wav` with the scratchpad `look.py` and check by eye that the eight rings are there and turn
- [X] T023 Run the checks of `quickstart.md` and tick every task above in this file as it is done

---

## Dependencies & Execution Order

- Phase 1 first. Phase 2 (T002-T004 in parallel, then T005, T006, T007) before Phases 4-6; Phase 3 (the finder) needs only T001 and can run in parallel with Phase 2.
- US1 (T008-T010) → US2 (T011-T014, needs T009) → US3 (T015-T016, needs T009 and T005) → US4 (T017-T018, needs T006/T007) → Polish.
- Within a story: tests before code (see them fail), code, then the mutation check.

### Parallel opportunities

- T002, T003, T004 (different files); T011 and T012; T019 and T020.
- Phase 3 beside Phase 2.

## Implementation Strategy

### MVP first

Phases 1-3: the finder on peak times alone. Then Phase 4 to see it in Rhythm Circles, Phase 2 so the settings match, and Phase 5 for the numbers.

### Notes

- The finder is built exactly as the user wrote it, with the ratios in one constant; the two sample files are measured and reported, not gated, because the rule as written cannot reach the hoped-for share of time on them (research D2). Report that plainly at the end and let the user decide on the variant.
- Do not commit; the user asks for commits.
