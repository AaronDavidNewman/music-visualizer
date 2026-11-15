# Tasks: Code Readability Documentation

**Input**: Design documents from `/specs/041-code-readability-docs/` (plan.md, spec.md, research.md, data-model.md, contracts/documentation-standard.md, contracts/checks.md, quickstart.md)

**Prerequisites**: plan.md, spec.md

**Scope reminder**: types and documentation **only** (spec FR-010). No function, class or module is renamed, moved, split or merged; no logic is edited; an annotation never becomes a conversion or a check. The only new application code is `array_types.py` (names and descriptions). Backend: `backend/.venv/Scripts/python.exe -B -m pytest`; frontend is untouched.

**Tests**: Included for the two new checks (the scan and the presence check), written first and seen to fail. "No behaviour change" is proved by the existing suites **and** the frame hashes of `tools/verify_frames.py`.

**Organization**: By user story. Each story's implementation is done **group by group** (research D8: A foundation, B analysis and measurement, C frame handling, D image types, E the edge). A developer who is already in a module may do the three stories' work on it in one visit; tasks that touch the same file are never run at the same time.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- Paths are from the repository root. `backend/app/services/` is written `services/`.

## The groups (research D8)

- **A. Foundation**: `array_types.py` (new), `services/colormaps.py`, `image_processing.py`, `note_grid.py`, `note_layout.py`, `note_selection.py`, `window_spacing.py`, `resolution.py`, `gaussian.py`, `frame_interpolation.py`, `frame_saving.py`, `noise_floor.py`
- **B. Analysis and measurement**: `services/note_analysis.py`, `chords.py`, `local_peaks.py`, `tempo_finder.py`
- **C. Frame handling**: `services/frame_rendering.py`, `contour.py`, `beat_wave.py`
- **D. Image types**: `services/decay.py`, `decay_exp.py`, `polar_chords.py`, `energy_graphs.py`, `chromatic_decay.py`, `chromatic_wireframe.py`, `rhythm_circles.py`
- **E. The edge**: `routers/jobs.py`, `routers/video.py`, `routers/images.py`, `routers/hello.py`, `services/video.py`, `services/image_types.py`, `main.py`, `config.py`

---

## Phase 1: Setup (the baseline and the tools)

**Purpose**: Everything that proves "nothing moved" and "what is written is true", made **before any application file is edited**.

- [X] T001 Write `specs/041-code-readability-docs/tools/verify_frames.py` (research D7): it generates a short fixed stereo input in the script (seeded tones with clicks, 44.1 kHz, about 6 seconds), runs one job through the application's test client for each of the 8 image types with the default settings (plus Contour once with Beat coloring on), and either writes (`--write`) or compares with (default) the SHA-256 of every frame in `specs/041-code-readability-docs/tools/baseline-frames.json`; then **run it with `--write` now, before any edit to `backend/app`**, and run it again without `--write` to see that it reports identical (the tool itself is deterministic)
- [X] T002 [P] Write `specs/041-code-readability-docs/tools/trace_pipeline.py` (research D7): for one job of each of the 8 image types it uses `sys.setprofile` and prints the order in which the functions of `backend/app/services` are **first** called, with the module name, one list per type
- [X] T003 [P] Write `specs/041-code-readability-docs/tools/shape_probe.py` (research D6): for one job of each image type it uses `sys.setprofile` and records, for each function of `backend/app`, the shape and dtype of every array argument and of the returned value (including arrays inside a tuple or an attribute of a returned object), and prints a table per module
- [X] T004 Run the whole backend suite and the frontend suite once and note the counts (baseline: backend 4719 passed, frontend 871 passed, `vue-tsc` clean), so later failures are known to be this feature's

**Checkpoint**: `baseline-frames.json` exists and was made from the **unedited** application; the two review tools run.

---

## Phase 2: Foundational (the vocabulary every story uses)

**Purpose**: The array aliases must exist before a signature can use them.

**⚠️ CRITICAL**: No annotation or array documentation can use an alias before this phase is done.

- [X] T005 Create `backend/app/services/array_types.py` (research D1): a module docstring that says what it is (and "No data processing: the names and descriptions of the kinds of arrays the application passes around"), and one alias per kind from the table of `specs/041-code-readability-docs/data-model.md` (`Samples`, `NoteStrengths`, `WindowRanges`, `ImpulseEnergies`, `PeakTimes`, `PeakRates`, `Tempos`, `BeatPositions`, `CircleSeries`, `CircleAngles`, `Points`, `RingLevels`, `ColorTable`, `Pictures`, `Indices`), each `npt.NDArray[np.<element>]`, each **with its canonical description in a comment block next to it** (what the numbers are, unit or range, the usual shape with the meaning of each axis, and what produces it); imports only NumPy and `numpy.typing`; **add any further alias (polar bars, energy histograms, wireframe lines, grids of 7 by 12, masks) when its module is reached, with its row added to `data-model.md` first**

**Checkpoint**: `import app.services.array_types` works and the existing suite still passes.

---

## Phase 3: User Story 1 - Every function says what it takes and gives (Priority: P1) 🎯 MVP

**Goal**: A type on every parameter (except `self`, `cls`) and every return value of `backend/app`, nested functions included.

**Independent Test**: `pytest backend/tests/test_type_hints.py` passes (it lists none), and the existing suites and `verify_frames.py` are unchanged.

### Test for User Story 1 (write first, it MUST fail)

- [X] T006 [US1] Create `backend/tests/test_type_hints.py` as in `contracts/checks.md`: an `ast` scan of every `.py` file of `backend/app` (not `__pycache__`); for every function, method and nested function, every parameter except `self` and `cls` (positional-only, positional, keyword-only, `*args`, `**kwargs`) must be annotated and so must the return value; it reports **all** failures at once with file, line, function and the parameters without a type; also asserts that the scan saw more than 200 functions in more than 25 modules; run it and see it **fail listing about 135 functions**

### Implementation for User Story 1 (annotations only, group by group)

- [X] T007 [P] [US1] Group A: annotate every function in `services/colormaps.py`, `image_processing.py`, `note_grid.py`, `note_layout.py`, `note_selection.py`, `window_spacing.py`, `resolution.py`, `gaussian.py`, `frame_interpolation.py`, `frame_saving.py`, `noise_floor.py`; arrays use the aliases of `array_types.py` (add an alias and its description first if a kind is missing); then run the scan filtered to these files, their tests, and `verify_frames.py`
- [X] T008 [P] [US1] Group B: annotate every function in `services/note_analysis.py`, `chords.py`, `local_peaks.py`, `tempo_finder.py` (about 33 gaps); then the scan filtered to these files, their tests, and `verify_frames.py`
- [X] T009 [P] [US1] Group C: annotate every function in `services/frame_rendering.py`, `contour.py`, `beat_wave.py`; then the scan filtered to these files, their tests, and `verify_frames.py`
- [X] T010 [P] [US1] Group D: annotate every function in `services/decay.py`, `decay_exp.py`, `polar_chords.py`, `energy_graphs.py`, `chromatic_decay.py`, `chromatic_wireframe.py`, `rhythm_circles.py` (about 100 of the gaps); then the scan filtered to these files, their tests, and `verify_frames.py`
- [X] T011 [P] [US1] Group E: annotate every function in `routers/jobs.py`, `routers/video.py`, `routers/images.py`, `routers/hello.py`, `services/video.py`, `services/image_types.py`, `main.py`, `config.py`; for the FastAPI route functions keep the existing parameter defaults (`Form(None)`, `Depends(...)`) exactly; then the scan filtered to these files, their tests, and `verify_frames.py`
- [X] T012 [US1] Run the scan over everything: it passes with 0 functions without a type (from 135); run the whole backend suite (all passing) and `verify_frames.py` (all frame hashes identical to the baseline)

**Checkpoint**: User Story 1 done: SC-001 and SC-007 hold, and nothing moved.

---

## Phase 4: User Story 2 - Every array says what it means and what shape it has (Priority: P1)

**Goal**: Every function that takes or returns an array documents, for each array, its alias, its concrete shape with named axes, and what it represents; the same for data class fields and module-level tables.

**Independent Test**: `pytest backend/tests/test_documentation.py` (array parts) passes, and a random sample of 20 functions can be read without the code (SC-002).

### Test for User Story 2 (write first, it MUST fail)

- [X] T013 [US2] Create `backend/tests/test_documentation.py` with the array checks of `contracts/checks.md` (checks 2 and 3): for every top-level function and method whose annotations include an alias of `array_types.py` or `np.ndarray`, the docstring exists, names each array parameter in double backticks and, when the return is an array, has a `Returns:` line; every alias of `array_types.py` has a description comment and every alias used in an annotation is defined there; run it and see it **fail** (the arrays are not yet documented)

### Implementation for User Story 2 (docstrings only, group by group; shapes from `tools/shape_probe.py`)

- [X] T014 [P] [US2] Group A: for every function in the group A modules that takes or returns an array, add the `Arrays:` lines and `Returns:` line of `contracts/documentation-standard.md` section 2 (name, alias, concrete shape with named axes, meaning, unit or range, cases that depend on a setting); document `note_layout._ORDERS` with a comment (meaning and shape); read each shape in the output of `shape_probe.py`, not from memory
- [X] T015 [P] [US2] Group B: the same for `services/note_analysis.py` (including the `Attributes:` block of `AnalysisResult` and the fields of the other data classes), `chords.py`, `local_peaks.py` (including `LocalPeak` and `LocalPeaks` and their cached arrays), `tempo_finder.py` (including `TempoTrack`)
- [X] T016 [P] [US2] Group C: the same for `services/frame_rendering.py` (the three index arrays of `frame_windows`, `average_frames`, `smooth_frames`, `hidden_below`, `write_frames` with its optional `beat`, `energy`, `rhythm`), `contour.py`, `beat_wave.py`
- [X] T017 [P] [US2] Group D: the same for the seven image-type modules (the points, ring levels, polar bars, energy histograms, wireframe lines and heights, the circle series and angles, the pictures); add the aliases they need to `array_types.py` first, each with its row in `data-model.md`
- [X] T018 [P] [US2] Group E: the same for `routers/jobs.py` (where arrays are held between steps), `services/video.py`, `services/image_types.py` where applicable
- [X] T019 [US2] Consistency pass (FR-004): for every alias, search the docstrings that use it and make the words agree with its description in `array_types.py` (one description per kind, no contradictions, no second name for a kind); list the kinds found that have no alias and add them
- [X] T020 [US2] Spot check (SC-002): pick 20 functions at random among those that take or return an array (a seeded draw, recorded in `specs/041-code-readability-docs/research.md` under "Spot check") and for each write down from the documentation alone what each array holds and its shape, then compare with `shape_probe.py` output; fix any mismatch; run the presence check (array parts), the whole backend suite and `verify_frames.py`

**Checkpoint**: User Story 2 done: SC-002 holds, and nothing moved.

---

## Phase 5: User Story 3 - Every processing module says its order of operations (Priority: P1)

**Goal**: An "Order of operations" list at the top of every processing module, a "No data processing" line in the others, and one overview of the 8 image types in `image_types.py`.

**Independent Test**: `pytest backend/tests/test_documentation.py` (module and overview parts) passes, and for each of the 8 types the steps listed in the overview match the order printed by `tools/trace_pipeline.py`.

### Test for User Story 3 (write first, it MUST fail)

- [X] T021 [US3] Extend `backend/tests/test_documentation.py` with the module and overview checks of `contracts/checks.md` (checks 1 and 4): the explicit sets `PROCESSING_MODULES` and `EXEMPT_MODULES` (every module with a function or class is in exactly one; a name without a file fails), the "Order of operations:" list with a numbered item in each processing module, the "No data processing:" text in each exempt module, and in the `image_types.py` docstring `Pipeline overview:`, all names of `IMAGE_TYPES` and the shared step names READ, ANALYZE, FLOOR, MEASURE, AVERAGE, SMOOTH, DRAW, SAVE; run it and see it **fail**

### Implementation for User Story 3 (module docstrings only; orders checked with `tools/trace_pipeline.py`)

- [X] T022 [P] [US3] Group A: add to the module docstring of each of the group A modules either the numbered **Order of operations** (step, function, data after it with alias and shape; in the order a job applies them) or the line **No data processing: ...** (for example `image_processing.py`, `frame_saving.py`, `window_spacing.py` if they only hold a check or a constant), following `contracts/documentation-standard.md` section 3
- [X] T023 [P] [US3] Group B: the same for `services/note_analysis.py`, `chords.py`, `local_peaks.py` (the impulse windows, the peaks windows, the zones, the border pass, the energy line and the position), `tempo_finder.py` (match, window, step, limits and restart)
- [X] T024 [P] [US3] Group C: the same for `services/frame_rendering.py` (average, smooth, then the type's drawing; what each setting changes and when), `contour.py`, `beat_wave.py`
- [X] T025 [P] [US3] Group D: the same for the seven image-type modules, **moving the existing description of each module's layers or steps into the common form instead of rewriting it**; check each list against the output of `trace_pipeline.py` for that type
- [X] T026 [P] [US3] Group E: the same for `routers/jobs.py` (the order of a job: read, check settings, analyze, floor, measure, average, draw, save, with the errors that stop it), `routers/video.py`, `services/video.py`, `main.py`, `config.py`, `routers/images.py`, `routers/hello.py` (mostly "No data processing")
- [X] T027 [US3] Write the **Pipeline overview** in the module docstring of `services/image_types.py` (`contracts/documentation-standard.md` section 4): the shared steps in job order with function and data after each (alias and shape), then one block per type in the order of `IMAGE_TYPES` giving the shared steps it uses and skips and its own DRAW stages in order with module and function and the data after each, and the closing rule that a changed type changes its block in the same piece of work; for each of the 8 types compare the block with the printed order of `trace_pipeline.py` and fix any difference (SC-004)
- [X] T028 [US3] Run the presence check (all parts), the scan, the whole backend suite and `verify_frames.py` (all identical)

**Checkpoint**: User Story 3 done: SC-003 and SC-004 hold, and nothing moved.

---

## Phase 6: User Story 4 - The constitution requires it for all future work (Priority: P2)

**Goal**: The three rules, how each is checked, and their governance are in the constitution and in the plan template's check.

**Independent Test**: Reading the constitution shows the three principles and how each is checked; the plan template's Constitution Check lists them.

- [X] T029 [US4] Write `.specify/memory/constitution.md` (research D9; the `/speckit-constitution` command may be used, or edit the file directly with the same content): the project name; **I. Every function is typed**, **II. Every array is documented with its meaning and shape (one description per kind, in `array_types.py`)**, **III. Every processing module states its order of operations, and the image types have one overview**; each with its rule in the words of `contracts/documentation-standard.md` and **how it is checked** (`test_type_hints.py`, `test_documentation.py`, review with `tools/shape_probe.py` and `tools/trace_pipeline.py`); a governance section (the principles are checked in every plan; a change to arrays or steps changes their documentation in the same piece of work; how a principle is amended; version 1.0.0, ratified 2026-11-15); the unused template sections are removed and **no other principle is invented**
- [X] T030 [P] [US4] Update the Constitution Check of `.specify/templates/plan-template.md` so that it lists the three rules as the gates every plan answers (typed functions, arrays documented with meaning and shape, order of operations and the image-type overview updated)
- [X] T031 [US4] Check the loop closes: read the constitution and the plan template as a reviewer would; confirm each of the three rules is stated so that a change can be ticked or failed (spec story 4 scenarios 1 and 2) and that a function added without types fails `test_type_hints.py` (add one temporarily to a scratch copy or a temporary function in a test run, confirm the failure message, remove it)

**Checkpoint**: User Story 4 done: SC-006 holds.

---

## Phase 7: Polish & Cross-Cutting

- [X] T032 [P] Add a short section to `README.md` on the documentation standard: the three rules, where `array_types.py` is, the two checks, and the two review tools of the feature folder
- [X] T033 [P] Update the memory note `readability-docs-decisions.md` (and `MEMORY.md` if needed) with what was done: the final alias list, the checks, the tools and the result of the baseline comparison
- [X] T034 Final run: both new tests pass; the whole backend suite passes; the frontend suite and `vue-tsc --noEmit` pass (untouched); `verify_frames.py` reports every frame hash identical to the baseline; run the checks of `quickstart.md` (sections 1 to 5); tick every task in this file as it is done

---

## Dependencies & Execution Order

- Phase 1 (T001 first, **before any edit of `backend/app`**; T002 and T003 in parallel) → Phase 2 (T005) → the stories.
- US1 (T006-T012) can start after T005; US2 (T013-T020) after US1 (the alias annotations are in place) and T005; US3 (T021-T028) after US2 for the data descriptions its steps name; US4 (T029-T031) can be written any time after the standard is settled but is ticked last, because it must say what was really built.
- Within a story, the failing test first, then the groups (A before the others when aliases are needed; B, C, D, E in parallel if different files), then the full check.
- The same file is touched by US1, US2 and US3 in turn (annotations, then array docs, then the order of operations); those tasks are sequential, never at the same time.

### Parallel opportunities

- T002 and T003; the five group tasks within one story (T007-T011, T014-T018, T022-T026); T030 beside T029; T032 and T033.

## Implementation Strategy

### MVP first

Phases 1-3: the baseline, the vocabulary and the types (the scan green). Then US2 and US3 group by group, then the constitution.

### Notes

- **Do not edit `backend/app` before T001 has written the baseline.** A baseline taken after an edit proves nothing.
- After every group, run the scan, that group's tests and `verify_frames.py`; a mistake is then found near where it was made.
- If documenting a function shows that the code is awkward to follow, **write it in the docstring or in a "for later" list in `research.md`; do not change the code** (spec FR-010).
- If a shape cannot be observed by the probe (the function is not reached by a job), read the code and mark the docstring with the places the shape comes from.
- Do not commit; the user asks for commits.
