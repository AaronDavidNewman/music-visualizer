---
description: "Task list for the Chromatic Decay Threshold feature"
---

# Tasks: Chromatic Decay Threshold

**Input**: Design documents from `/specs/037-chromatic-threshold/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/chromatic-threshold.md](contracts/chromatic-threshold.md), [quickstart.md](quickstart.md)

**Tests**: Tests are written first (they fail where behaviour is missing), against an independent rule written out in the test (plain Python loops); a mutation check follows each implementation task (the helpers `mutate.py` and `mutate_front.py` of the session scratchpad, `python -B`, `__pycache__` cleared). Backend commands in `backend/` with `.venv/Scripts/python.exe`; frontend in `frontend/` with `npx vitest run` and `npx vue-tsc --noEmit`; long runs in the background. Heredocs with quotes can fail in the shell tool: put scripts in files. Do not edit `decay.py`: the user's `NEIGHBOURS` line is theirs.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependencies)
- **[Story]**: US1 the rule in the points calculation, US2 the request and the page

## Path Conventions

Web application: `backend/app/...`, `backend/tests/...`, `frontend/src/...`.

---

## Phase 1: Setup

- [X] T001 Record the baseline: clear `__pycache__` under `backend/` (not `.venv`), run `python -B -m pytest -q` in `backend/` (background, about 7 minutes; the run may patch `decay.NEIGHBOURS` to 8 in memory with `/tmp/run_all8.py` if `decay.py` still reads 6, to separate the user's pending change from this feature) and `npx vitest run` and `npx vue-tsc --noEmit` in `frontend/`; write the counts and the failures by file at the end of this task. Expected: backend 0 failures with the patch (6860 passed at the end of feature 036), 60 Decay and Decay Exp failures without it; frontend 889 passed.
  **Done 2026-11-10**: baseline backend **6860 passed, 0 failed** (the user had saved `NEIGHBOURS = 8` in `decay.py`, so no in-memory patch was needed), frontend 889 passed, `vue-tsc` clean; features 035 to 037 are uncommitted.

---

## Phase 2: User Story 1 - The rule in the points calculation (Priority: P1) 🎯 MVP

**Goal**: `threshold` on `circle_points` and `circle_tapers` (spec US1, FR-001 to FR-005, FR-009; SC-001 to SC-003).

**Independent Test**: values with a loud note on C (100) and a faint one on E (3), threshold 5: only C gains; threshold 2 or 0: both.

- [X] T002 [P] [US1] Create `backend/tests/test_chromatic_threshold.py` (spec US1 scenarios 1 to 6; data-model; contract section 1), written to fail first (the functions and the argument do not exist): `check_threshold`: accepts 0, 1, 5, 10, 2.5, `5.0`, numpy numbers, and refuses -0.1, 10.0001, 11, True, "5", None, NaN, inf with `ValueError` of exactly `The threshold must be a number from 0 to 10.`, and gives the **same accept/refuse answers and value as `frame_rendering._check_threshold` on a table of at least 25 values** (the two cannot drift); `apply_threshold`: against a **loop oracle** (a value strictly below `t / 100 x max` of the whole array, all frames and all columns, is 0; every other value unchanged) on random arrays of 84 and 88 columns for every `t` in 0, 1, 2.5, 5, 10; a value **exactly at** the floor is kept (a hand-made array with 100 and 5.0 at `t = 5`); the reference is the **largest value of the whole array, not of the frame** (a frame whose own largest is 4 is all 0 at `t = 5` when another frame has 100) and includes the columns after the 84th (a loud value in column 86 raises the floor); `t = 0` returns an equal copy (not the same object) and a silent array and an empty `(0, 88)` array are returned unchanged without error; the input is not changed; the result is float64 and has the shape of the input; bad values (1-D, fewer than 84 columns, negative, NaN, inf) refused as `letter_energies` refuses them; a bad threshold refused with the message. **The effect**: `circle_points(values, beat, rate, threshold)` against the **existing oracle of `test_chromatic_decay_step.py`** (`oracle_simulation`, extended in this test file to threshold the values first with the loop of `apply_threshold`) for random values, rates 1, 3, 10 and thresholds 0, 1, 5, 10, with and without a beat: equal to 1e-12, and the same for `circle_tapers`; a **faint letter** (E at 3 against C at 100) has 0 points in every frame at `t = 5` and more than 0 at `t = 2` and at `t = 0`, and the points of C are the same whether or not the faint note exists above the threshold (the faint note does not change C's rank or gain, as C is the loudest either way; use a case with six letters so that the faint one would take the fifth place without the threshold and show that the sixth, a louder letter, takes it instead); a letter whose octaves are **all** under the floor does not count among the five loudest; **two faint octaves of one letter do not add up** to pass the floor (each is checked alone); a **frame where only faint notes sound** has no gains (the circles only decay) while the loud frames of the file do; **`threshold` 0 and the argument left out give exactly the same arrays** (`np.array_equal`) for random values, as the arrays of feature 035 (compare with an unchanged copy of the loop oracle); the decay and the rings do not depend on the threshold (the beat array is not read or changed: with a threshold, `write_chromatic_frames` of the same points and beat gives the same bytes: not needed, but `circle_points` with and without a threshold on values where no note is under the floor are equal); a bad threshold or decay rate is refused before anything is computed; the input values and beat are not changed; deterministic.
- [X] T003 [US1] Implement in `backend/app/services/chromatic_decay.py` (research Decisions 1 to 3): the constants `MIN_THRESHOLD`, `MAX_THRESHOLD`, `DEFAULT_THRESHOLD`, `THRESHOLD_MESSAGE`, `check_threshold`, `apply_threshold`, the `threshold` argument (default 0, after `decay_rate`) on `circle_points`, `circle_tapers` and `_simulate`, which applies it to the values first (and checks it with the decay rate, before any computing); update the module docstring and the docstrings (the threshold in a sentence of the list at the top). Run T002 and the whole of the Chromatic Decay tests (they must not change: threshold 0 is the earlier result), then the mutation check (non-strict comparison `<=`; the reference the maximum of the frame; the reference the maximum of the first 84 columns; the threshold applied to the letter energies after the max over the octaves; the floor `threshold x max` without the `/ 100`; threshold 0 not returning the input unchanged (a 1 percent floor); `circle_tapers` not given the argument; the check removed).
  **Done 2026-11-10**: 77 tests in `test_chromatic_threshold.py`; mutation check: 11 mutants, 10 caught, the survivor (`if threshold > 0 and values.size` without the `threshold > 0`) is equivalent (with a threshold of 0 the floor is 0 and no value is below it). One test premise was wrong and was corrected: a faint letter is never charged by **gains**, but can still receive points through the decay of the loud letters next to it on the ring (E gives to A and B), so the test checks the first frame, the gains, and that its points are lower with the threshold.

**Checkpoint**: the rule and its effect on the points are right on their own.

---

## Phase 3: User Story 2 - The request and the page (Priority: P2)

**Goal**: the existing Threshold setting works for Chromatic Decay in the job and on the page (spec US2, FR-006 to FR-008; SC-002 to SC-005).

**Independent Test**: Chromatic Decay with a loud and a faint note, threshold 5 (the faint letter's circle stays smallest) and without; the group shows Decay rate and Threshold.

- [X] T004 [P] [US2] Extend `backend/tests/test_chromatic_decay_api.py` (spec US2 scenarios 2 to 4; contract section 2), written to fail first: remove `threshold` from the `SETTINGS` list of the settings that do not apply (`{"threshold": "5", "note_count": "20"}` becomes `{"note_count": "20"}`) and from the other places of that file that treat it as ignored; new tests: a file with a **loud tone (C4) and a faint one (E4 at a hundredth of the amplitude: 1 percent, so the 5 percent threshold removes it)** shows, at `threshold` 5, the circle of E at its smallest size and unchanged by the second tone (the frames equal those of the loud tone alone), and at no threshold (and at `0`) the circle of E grows (frames differ); `threshold` `1` and `10` accepted and echoed, **not sent** gives frames identical to `threshold` 0; `-1`, `11`, `x`, `""`, `nan` refused with 400 `The threshold must be a number from 0 to 10.` before the file is read and with `leftovers() == []`; the response keys are those of before; `write_frames(..., image_type="chromatic-decay", threshold=t)` equals `write_chromatic_frames(circle_points(values, beat, rate, t), ..., beat=beat)` byte for byte for `t` in 0, 5, 10 and `write_frames` refuses a bad threshold as before; the Data smoothing applies before the threshold (a smoothed tail that lingers after a tone stops stays above the floor for the frames the smoothing keeps it: compare with a direct call on the smoothed values); the other types' behaviour with `threshold` is unchanged (their own tests).
  **Done 2026-11-10**: `SETTINGS` of the API tests no longer lists the threshold as ignored; 9 new API tests. A real-audio detail: a tone at a hundredth of the loud one measures just under 1 percent after the int16 quantisation, so the test uses 2 percent (the exact-boundary case is on arrays).
- [X] T005 [US2] Wire it in `backend/app/services/frame_rendering.py`: the `chromatic-decay` branch passes `threshold` to `chromatic_points(smoothed, beat, decay_rate, threshold)` and the docstring of `write_frames` says that for Chromatic Decay the threshold applies (a note under it is treated as 0 before the letters are charged). Run T004 and the earlier Chromatic Decay API tests, then the mutation check (the threshold not passed; passed as 0; passed instead of the decay rate).
  **Done 2026-11-10**: wiring mutations (threshold not passed, passed as 0, wrong array, wrong argument position): all 4 caught.
- [X] T006 [P] [US2] Frontend tests first (`frontend/src/utilities/groups.test.ts`, `components/SettingsForm.test.ts`, `App.test.ts`, `utilities/help.test.ts`, `utilities/validation.test.ts`), written to fail: `controlsIn("chromatic-decay")` is `["chromatic-decay-rate", "threshold"]` (two controls, `rowsOf` gives `[2]`), `groupsFor("chromatic-decay")` is unchanged, `groupOf("threshold", "chromatic-decay")` is `"chromatic-decay"` and the other types' group of `threshold` is as before (Tiles, Contour and Blended tiles; none for the others), the `EXPECTED` control order of the type becomes `[...COMMON_TOP, "chromatic-decay-rate", "threshold", "peak-distance", ...]`; the form renders, for Chromatic Decay, the `threshold` slider (min 0, max 10, step 1, value 0, readout Off, the label and the info button) after the Decay rate and before Local peaks, with no `notes`, `resolution`, `interpolate`, `gaussian`, `note-layout` control; the threshold error blocks the form for the type (the source check of `typeGroupProblem` is already generic: assert that a threshold error counts for Chromatic Decay through `inTypeGroup("threshold")`); the summary line `Threshold:` is shown when `gridSettingsApply(type) || isChromaticType(type)` (a source check as the existing ones) and the Notes, Interpolate, Oversampling and Gaussian lines are not; the help: `thresholdHelp` has a sentence for Chromatic Decay (a note under the threshold is treated as silent: it does not charge its letter or count among the five loudest) and the Chromatic Decay paragraph of `imageTypeHelp` names the threshold, with no character the page would escape; the old Tiles sentence of `thresholdHelp` is kept.
  **Done 2026-11-10**: frontend tests: the group list and the `EXPECTED` order, the slider, the summary line, the help; one thing found: the page draws the Threshold block before the Decay rate block for every type, so the group lists `["threshold", "chromatic-decay-rate"]` (the order the page draws them).
- [X] T007 [US2] Implement the frontend: `frontend/src/utilities/groups.ts` (the group `chromatic-decay` lists `["chromatic-decay-rate", "threshold"]`, its comment), `frontend/src/App.vue` (the `Threshold:` summary line shown for `gridSettingsApply(result.image_type) || isChromaticType(result.image_type)`), `frontend/src/utilities/help.ts` (`thresholdHelp` and the Chromatic Decay paragraph), and `frontend/src/components/SettingsForm.vue` only if a test shows something is needed (the threshold block is generic). Run `npx vitest run` and `npx vue-tsc --noEmit`, then the mutation check with `mutate_front.py` (the control removed from the group; the summary condition without `isChromaticType`; the help sentence removed).
  **Done 2026-11-10**: frontend **897 passed** (889 + 8), `vue-tsc` clean; 4 mutations (control removed from the group, summary condition, the two help sentences) all caught.
- [X] T008 [P] [US2] Document: `README.md` (the Chromatic Decay paragraph: the Threshold now applies, 0 to 10 percent of the largest smoothed value of the whole file, strictly below is 0 before the letters are charged, off at 0, reuses the existing field; the Threshold paragraph's list of the types that use it) and the feature 035 documents' list of ignored settings (`specs/035-chromatic-decay/` `spec.md` Story 4 and the contract: Threshold is no longer ignored: a revision note); `specs/037-chromatic-threshold/checklists/requirements.md` untouched.

**Checkpoint**: the setting works in the job and on the page, documented.

---

## Phase 4: Polish & Cross-Cutting

- [X] T009 Run the whole suites: clear `__pycache__`, backend (with the in-memory `decay.NEIGHBOURS = 8` patch if `decay.py` still reads 6, and report both the patched and, if cheap, the unpatched failure list) and `npx vitest run`, `npx vue-tsc --noEmit`; compare with T001: only new tests added, no old test removed or weakened (list every existing test whose expectation was changed and why: the `SETTINGS` entry of the API test and the `EXPECTED` and group tests of the frontend).
  **Done 2026-11-10**: backend **6958 passed, 0 failed** (6860 + 98 new), frontend 897 passed, `vue-tsc` clean. Existing tests changed: the `SETTINGS` entry of `test_chromatic_decay_api.py` (the threshold now applies) and the Chromatic Decay expectations of `groups.test.ts` and `SettingsForm.test.ts`; none removed or weakened.
- [X] T010 Check the other image types are unchanged byte for byte: `hash_types10.py` of the scratchpad run in a `git worktree` of `HEAD` and in the working tree (with `decay.NEIGHBOURS` at 8 in a scratch copy, as for feature 036, so that Decay and Decay Exp are comparable); and that a Chromatic Decay job without `threshold` gives the same frames as before this feature (hash the frames of a fixed file with the working tree before the feature's edits is not possible now: use the library equality of T002 and the API equality of T004 as the evidence, and say so); remove the worktree.
  **Done 2026-11-10**: the frames of the ten older types at decay rates 1 and 2 (20 combinations) are byte for byte identical to a `git worktree` of `HEAD` (Decay and Decay Exp included now that `NEIGHBOURS` is 8 on disk); worktree removed. For Chromatic Decay itself, a threshold of 0 or none gives exactly the earlier arrays (`np.array_equal` against the feature 035 oracle in `test_chromatic_threshold.py`) and the same frames (`test_no_threshold_and_a_threshold_of_0_give_the_same_frames`).
- [X] T011 Look at it and measure: render `backend/audio/sonata.wav` and `female-voice.wav` (coolwarm) with the threshold off, 5 and 10 into the scratchpad directory, open a few frames with the Read tool, compare how many circles are lit; count, from `circle_points`, the share of (frame, letter) pairs with gains at thresholds 0, 1, 5, 10; time the job (no change expected); report honestly, including a threshold of 10 that leaves most frames with no gain, if it does.
  **Done 2026-11-10**: letters gaining per frame at thresholds 0 / 1 / 5 / 10: sonata 4.8 / 4.8 / 3.8 / 1.9, female-voice 4.4 / 3.9 / 3.1 / 1.7, vibraslap 5.0 / 4.1 / 3.4 / 3.1, white noise 5.0 / 5.0 / 5.0 / 5.0 (its notes are all alike); a sonata frame with the threshold off and at 10 compared by eye: at 10 several circles drop to small blue ones and the leaders stay, the beat rings in the middle are identical; the job takes about the same time (6.9 s and 6.7 s with the test suite running alongside). Not checked: the page in a browser.
- [X] T012 Write the memory note `chromatic-threshold-decisions` (a file in `C:\Users\Daddy\.claude\projects\d--github-music-visualizer\memory\` and a line in `MEMORY.md`): the readings (reuses the existing Threshold field and control; the reference is the largest value of the whole array over all columns; strictly below; applied to the note values before the octaves are combined; 0 is off; the page control included), and check first that no existing memory covers it.
  **Done 2026-11-10**: `chromatic-threshold-decisions.md` in the memory folder and its line in `MEMORY.md`.

---

## Dependencies & Execution Order

- **T001** first. **US1**: T002 then T003. **US2**: T004 and T006 can be written in parallel with T002/T003 (different files; T004's job tests need T003 and T005 to pass); T005 after T003; T007 after T006; T008 any time after T003.
- **Phase 4** after everything.

## Parallel Example

```text
After T001:  T002 (test_chromatic_threshold.py)  ||  T004 (test_chromatic_decay_api.py)  ||  T006 (frontend tests)  ||  T008 (README)
```

## Implementation Strategy

- **MVP**: T001 to T003 (the rule in the points calculation) plus T005 (the job passes it on).
- Then the page (T006, T007), the documentation, and the polish (T009 to T012).
- Every implementation task ends with its tests green and a mutation check; a failing old test is reported, never silently changed.
