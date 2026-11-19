---

description: "Task list for 043-decouple-frame-rate"
---

# Tasks: Decouple the frame rate from the frequency buffers

**Input**: Design documents from `/specs/043-decouple-frame-rate/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/job-api.md](contracts/job-api.md), [quickstart.md](quickstart.md)

**Tests**: The plan and the constitution require them (the quickstart names the test files), so test tasks are included. Existing tests that describe the removed settings are edited or deleted.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root. Run backend commands from `backend/` and frontend commands from `frontend/`.

**Environment note**: PowerShell scripts cannot be run on this machine (execution policy), so nothing here depends on the `.specify/scripts` files. Use `python -m pytest` and `npm`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1 to US4 as in the spec

---

## Phase 1: Setup (baselines, before the first edit of `backend/app` or `frontend/src`)

- [X] T001 Run the whole backend suite (`python -m pytest -q -p no:cacheprovider` in `backend/`) and save the failing test ids (the lines starting `FAILED`) to `specs/043-decouple-frame-rate/baseline-failures-before.txt`; they should be the known ones (about 25 from `DEFAULT_PROMINENCE=15` listed in `specs/041-code-readability-docs/tools/baseline-failures.txt`, and about 60 Decay / Decay Exp tests from `NEIGHBOURS=6`); do not fix them
- [X] T002 [P] Create `specs/043-decouple-frame-rate/tools/verify_drawing.py` in the style of `specs/041-code-readability-docs/tools/verify_frames.py`: build a fixed, seeded `NoteStrengths` `(60, 88)` (non-negative floats, a few louder notes, some zeros) and a fixed `BeatPositions` `(60,)`, call `frame_rendering.write_frames()` with only the arguments that exist both before and after this feature (`frames`, `directory`, `image_type`, `beat`, plus `energy`, `rhythm` and `polychord` made by small fixed arrays for `energy-graphs`, `rhythm-circles` and `polychord`) for every name in `IMAGE_TYPES`, take the SHA-256 of every PNG, and support `--write` (writes `specs/043-decouple-frame-rate/tools/baseline-drawing.json`) and a plain run (compares, exit 1 on any difference). Document the arrays in the docstring as the constitution asks for tools' functions that take arrays (type every function)
- [X] T003 Run `python specs/043-decouple-frame-rate/tools/verify_drawing.py --write` from the repository root, **before any edit of `backend/app`**, and commit nothing yet; check that the baseline file lists every image type
- [X] T004 [P] Run `python specs/041-code-readability-docs/tools/verify_frames.py` (compare mode, no `--write`) and note in `specs/043-decouple-frame-rate/baseline-verify-frames-before.txt` whether it passes today and how many frames each type makes (later features may already have moved it; do not rewrite `baseline-frames.json`)

**Checkpoint**: baselines exist; the source is untouched.

---

## Phase 2: Foundational (blocks every story)

**Purpose**: the one new module every story uses.

- [X] T005 Create `backend/app/services/buffer_interval.py` with a module docstring that starts with `Order of operations:` (1. Choose the step - `buffer_step()` - the 60 ms of the file's sample rate in samples, a float: not an array, so no alias), the constant `BUFFER_INTERVAL_MS: int = 60`, and `def buffer_step(sample_rate: float) -> float` returning `max(1.0, sample_rate * BUFFER_INTERVAL_MS / 1000)` (multiply before dividing so that 44100 gives exactly 2646.0 and 48000 exactly 2880.0); the docstring says why 60 ms (shorter than a 32nd note at 120 bpm, 62.5 ms) and that a step under one sample is raised to one (the guard is never reached for a rate the analyzer accepts)
- [X] T006 [P] Create `backend/tests/test_buffer_interval.py`: `buffer_step(44100) == 2646.0`, `buffer_step(48000) == 2880.0`, `buffer_step(22050) == 1323.0`, `buffer_step(11025) == 661.5`, `buffer_step(8000) == 480.0`; the step is independent of everything but the sample rate; `buffer_step(10) == 1.0` (the guard); `BUFFER_INTERVAL_MS == 60`; for the five rates the window starts from `note_analysis.window_starts(sample_count, buffer_step(rate))` differ from `k * step` by at most 0.5 sample (SC-002)

**Checkpoint**: `python -m pytest tests/test_buffer_interval.py -q` passes. (`test_documentation.py` will fail until T012 adds the module to its list; that is expected and fixed in the next phase.)

---

## Phase 3: User Story 1 - The notes are measured at the same rate whatever the frame rate (Priority: P1) 🎯 MVP

**Goal**: every job analyzes with the 60 ms step; changing only the frame rate changes no buffer.

**Independent Test**: post one file at frame rates 1, 10, 24, 30 and 60: `step_samples` and `window_count` are the same each time, and `step_samples == sample_rate * 60 / 1000`.

### Tests for User Story 1

- [X] T007 [P] [US1] Create `backend/tests/test_buffers_api.py` using the helpers of `backend/tests/test_jobs_api.py`: (a) `step_samples` and `window_count` are identical at frame rates 1, 10, 24, 30, 60 and with `window_size` 4096 and 16384, and equal `buffer_step(sample_rate)` and `note_analysis.window_count(samples, step)`; (b) a 62.5 ms burst of a tone (a 32nd note at 120 bpm) in silence is measured: with the same analysis the job makes (`floor_analysis(analyze_channels(..., step=job["step_samples"]))`) at least one buffer has the burst's note above 0 at 5 fps (SC-003); (c) files of 8000, 11025, 22050, 44100 and 48000 Hz give `step_samples == rate * 60 / 1000`; (d) the same file and settings at two frame rates give identical `step_samples` and identical *analysis* (the `AnalysisResult.frames` made as in (b)) (SC-001); (e) a file shorter than 60 ms gives `window_count == 1` and `frame_count >= 1`

### Implementation for User Story 1

- [X] T008 [US1] In `backend/app/routers/jobs.py`: delete `_parse_window_spacing()` and the `window_spacing` `Form` parameter; import `buffer_step` from `..services.buffer_interval` in place of `default_spacing, resolve_step` from `window_spacing`; replace the block that computes `requested_spacing`, `spacing, step, raised` with `step = buffer_step(file_rate)`; keep `windows = window_count(samples, step)`; change the refusal message to `"This would create {windows:,} windows; the limit is {settings.max_windows:,}. Use a shorter file."`; remove `"window_spacing": spacing` and `"spacing_raised": raised` from the answer (keep `step_samples` and `window_count`)
- [X] T009 [US1] In `backend/app/routers/jobs.py` module docstring: step 4 of `Order of operations:` names `buffer_interval.buffer_step()` and `note_analysis.window_count()` (not the two `window_spacing` functions); say the step is fixed
- [X] T010 [P] [US1] Update the docs of `backend/app/services/note_analysis.py` (the "Choose the windows" step and the `analyze_channels()` docstring: the job always passes the 60 ms step; a larger or smaller step stays possible for callers) and the comment on `max_windows` in `backend/app/config.py` (no mention of a window spacing; say it protects against a very long file)
- [X] T011 [US1] Delete `backend/app/services/window_spacing.py` and `backend/tests/test_window_spacing.py`
- [X] T012 [US1] In `backend/tests/test_documentation.py` replace `"services/window_spacing.py"` by `"services/buffer_interval.py"` in the processing-module set (keep the list in alphabetical order, so before `services/chords.py` where it belongs)
- [X] T013 [US1] Edit `backend/tests/test_jobs_api.py`: delete or rewrite the tests of section "window spacing (feature 003)" (about lines 255 to 400: the spacing tests, the "too many windows" tests, `test_spacing_larger_than_the_file_gives_one_window`) as tests of the fixed step: the "too many windows" test sets `monkeypatch.setattr(settings, "max_windows", 10)`, expects the message to contain `"windows"`, `"limit is 10"` and `"shorter file"` and checks that `analyze_channels` was not called; the "huge count refused quickly" test sets `max_windows` to 5 on a 5 s file; remove `"window_spacing"` from the key list near line 492; fix the assertions near lines 310, 317, 441 and 569 for the new window count; make `post()` in this file and in the other test files stop sending `spacing` (`grep -rn "spacing=" backend/tests`)
- [X] T014 [US1] Run `python -m pytest -q -p no:cacheprovider` in `backend/`; for every failure not in `specs/043-decouple-frame-rate/baseline-failures-before.txt` that mentions `window_count`, `step_samples`, `window_spacing`, `spacing` or an expected number of windows, edit the test for the fixed step (files seen with spacing or window-count mentions: `test_chords.py`, `test_chords_audio.py`, `test_note_analysis.py`, `test_noise_floor_api.py`, `test_rhythm_circles_api.py`, `test_energy_graphs_api.py`, `test_*_api.py`); do not edit a test that was already failing

**Checkpoint**: `python -m pytest tests/test_buffer_interval.py tests/test_buffers_api.py tests/test_jobs_api.py tests/test_documentation.py -q` passes. User Story 1 works on its own: the job analyzes every 60 ms (the removed *smoothing* settings still exist at this point).

---

## Phase 4: User Story 2 - A low frame rate averages the buffers instead of skipping them (Priority: P1)

**Goal**: a frame is the mean of the buffers that start in it, every buffer once; a frame with none uses the latest earlier buffer.

**Independent Test**: at 10 fps each frame row equals the mean of its buffers; at 30 and 60 fps no frame is zero for want of a buffer.

*No production code changes are expected* (`frame_count`, `frame_windows`, `average_frames` already do this, see research decision 3); this story is the proof, and a fix if the proof fails.

- [X] T015 [P] [US2] Add to `backend/tests/test_frame_rendering.py` tests with a fabricated `AnalysisResult` whose `step` is the 60 ms step of 44100 Hz (2646 samples) and `frames` are distinct known rows: at 10 fps (frame period 4410 samples) every frame equals the mean of `frames[first:stop]` as `frame_windows()` gives them, and `sum(stop - first) == window_count` (every buffer owned once, SC-004); at 5 fps frames own 8 or 9 buffers each; at 30 fps and at 60 fps every frame row equals the latest earlier buffer when it owns none and is never all zero when the audio is not silent; the number of frames is `ceil(duration * frame_rate)` for 1, 10, 30, 60 fps
- [X] T016 [P] [US2] Add a test through the endpoint in `backend/tests/test_buffers_api.py` (same file as T007, add after it): a file with a loud tone for the first second and silence after, at 10 fps and at 30 fps: the frame at the middle of the tone is not blank at either rate (the picture of the default type has more than one color) and the frames after the tone are blank
- [X] T017 [US2] If T015 or T016 fail, fix `frame_windows()` / `average_frames()` in `backend/app/services/frame_rendering.py` and say what was wrong in a comment of the test; otherwise write nothing

**Checkpoint**: `python -m pytest tests/test_frame_rendering.py tests/test_buffers_api.py -q` passes.

---

## Phase 5: User Story 3 - The page and the request lose the settings that are now decided for the user (Priority: P2)

**Goal**: no Window spacing, Smoothing or Smoothing window anywhere (page, request, answer, rendering code); the old fields are ignored.

**Independent Test**: the page has no such fields and no Data smoothing group; a request carrying them gives the same frames as one without.

### Tests for User Story 3

- [X] T018 [P] [US3] Create `backend/tests/test_removed_settings_api.py`: a job with `smoothing=banana`, `smoothing_window=99` and `window_spacing=-1` returns 200, and its frames (the PNG bytes of frames 0, 5 and the last) equal those of the same job without the three fields; the answer has none of the keys `smoothing`, `smoothing_window`, `window_spacing`, `spacing_raised`; empty values (`smoothing=`) are also accepted (FR-012)
- [X] T019 [P] [US3] Delete `backend/tests/test_smoothing_window.py` and `backend/tests/test_smoothing_window_api.py`; remove the `smoothing=` / `smoothing_window=` arguments and the `smoothing` / `smoothing_window` keys from the other backend tests (`grep -rnE "smoothing|smooth_frames" backend/tests`: `test_frame_rendering.py` has the most; `test_polychord_api.py` imports `smooth_frames` and must now compute its expected values from `average_frames()` alone; `test_resolution_api.py` line ~111 key list; `test_resolution_rendering.py`, `test_threshold_api.py`, `test_rhythm_circles_api.py`, `test_note_count_*`, `test_interpolation_*`, `test_colormap_api.py`, `test_contour_api.py`, `test_chromatic_*_api.py`, `test_decay*_api.py`, `test_polar_chords_api.py`, `test_energy_graphs_api.py`, `test_gaussian.py`, `test_contour.py`, `test_frame_rendering_polychord.py`, `test_note_layout_rendering.py`); the grid and Gaussian smoothing tests (`gaussian`, `directionalSmoothing`) stay untouched
- [X] T020 [P] [US3] Edit `frontend/src/api.test.ts`, `frontend/src/App.test.ts`, `frontend/src/components/SettingsForm.test.ts`, `frontend/src/utilities/groups.test.ts`, `frontend/src/utilities/help.test.ts` and `frontend/src/utilities/validation.test.ts`: remove every expectation about spacing, Smoothing, Smoothing window and the `data-smoothing` group; add: the settings object and the request body have no `windowSpacing` / `window_spacing` / `smoothing` / `smoothing_window`; the rendered form has no element with the id `window-spacing`, `smoothing` or `smoothing-window` and no group `data-smoothing` for any image type; the Frame rate and Window size fields are still there and a job can be started with them alone (SC-005); the result list shows no Smoothing, Smoothing window or Window spacing line and no "raised to" notice. Delete `frontend/src/utilities/spacing.test.ts` and `frontend/src/utilities/wavHeader.test.ts`

### Implementation for User Story 3 - backend

- [X] T021 [US3] In `backend/app/services/frame_rendering.py`: delete `MIN_SMOOTHING`, `MAX_SMOOTHING`, `DEFAULT_SMOOTHING`, `MIN_SMOOTHING_WINDOW`, `MAX_SMOOTHING_WINDOW`, `DEFAULT_SMOOTHING_WINDOW`, `_check_smoothing_window()` and `smooth_frames()` and the `import numbers` / `math` lines only if nothing else uses them; delete the parameters `smoothing` and `smoothing_window` of `write_frames()` and their paragraph in its docstring; replace `smoothed = smooth_frames(...)` by using `frames` directly (`peak = float(frames.max()) if frames.size else 0.0`, and the later uses of `smoothed` use `frames`); keep every `Arrays:` entry true (``frames``: the strength of each note in each frame, averaged from the buffers)
- [X] T022 [US3] In `backend/app/routers/jobs.py`: delete `_parse_smoothing()`, `_parse_smoothing_window()` and their imports (`DEFAULT_SMOOTHING`, `DEFAULT_SMOOTHING_WINDOW`, `MIN_*`, `MAX_*`), the `smoothing` and `smoothing_window` `Form` parameters, the two lines that call the parsers, the two arguments passed to `write_frames()` and the keys `smoothing` and `smoothing_window` of the answer; update the comment above `_sent_fields` / the "sent" parsers that mentions `smoothing=` (keep the mechanism: other settings use it); update the comment "before the frames are averaged and smoothed" (jobs.py ~ line 535) and the comment above `write_frames()` (~ line 556) that says it smooths
- [X] T023 [US3] Update `backend/app/services/frame_rendering.py` module docstring: the first paragraph, and `Order of operations:` without step 5 *Smooth over the earlier frames* (renumber: the peak step and the draw step move up; the references "steps AVERAGE, SMOOTH and DRAW" become "AVERAGE and DRAW"); update `backend/app/services/image_types.py`: remove the `SMOOTH` shared step from the pipeline overview, say in AVERAGE that it is the only smoothing of the note data (the mean of the buffers each frame owns, the frame rate decides how many), and replace "smoothing" wording about the data in the per-type blocks (Settings that apply: Contour keeps *Gaussian smoothing*, which is the picture blur and stays); update `SHARED_STEPS` in `backend/tests/test_documentation.py` to `("READ", "ANALYZE", "FLOOR", "MEASURE", "AVERAGE", "DRAW", "SAVE")`; update the two lines of `specs/041-code-readability-docs/contracts/checks.md` (line 26) and `specs/041-code-readability-docs/contracts/documentation-standard.md` (line 62) that list the shared steps
- [X] T024 [P] [US3] The "smoothed" sweep of docstrings and comments (research decision 6): in `backend/app/services/array_types.py` (the *Made by:* of `NoteStrengths`: `average_frames` only, and the lines near 49 to 56 and 84), `chromatic_decay.py`, `decay.py`, `decay_exp.py`, `polar_chords.py`, `polychord.py`, `note_selection.py`, `contour.py`, `jobs.py` and `frame_rendering.py`, change wording that calls the **note values of a frame** "smoothed" (and mentions `smooth_frames`) to "the strength of each note in each frame" / "averaged"; **do not change** wording about the grid smoothing of Contour (`directionalSmoothing`, "the smoothed value of the cell" in `array_types.py` line ~84 and `contour.py`) or the Gaussian blur; list the places changed with `grep -rn "smoothed\|smooth_frames" backend/app --include=*.py` before and after to check that only grid / Gaussian wording is left
- [X] T025 [US3] Run `python -m pytest tests/test_type_hints.py tests/test_documentation.py tests/test_removed_settings_api.py -q` in `backend/` and then the whole backend suite; the failing ids must be a subset of `baseline-failures-before.txt`

### Implementation for User Story 3 - frontend

- [X] T026 [P] [US3] `frontend/src/api.ts`: remove `smoothing`, `smoothing_window`, `window_spacing`, `spacing_raised` (and `step_samples` only if nothing reads it) from the result type and `smoothing`, `smoothingWindow`, `windowSpacing` from the settings type and from the `body.append(...)` calls (lines ~9, 13, 46, 49, 57 to 62, 98 to 102)
- [X] T027 [P] [US3] `frontend/src/utilities/validation.ts`: delete `SMOOTHING_RANGE`, `DEFAULT_SMOOTHING`, `smoothingMessage`, `validateSmoothing`, `formatSmoothing`, `SMOOTHING_WINDOW_RANGE`, `DEFAULT_SMOOTHING_WINDOW`, `smoothingWindowMessage`, `validateSmoothingWindow`; fix the comments that say "the data smoothing" (line ~246) to say the type draws from its own measurement; `frontend/src/utilities/groups.ts`: delete the `data-smoothing` group (line 40), its push in the list of shown groups (line 70) and the sentences about Data smoothing in the doc comment (lines 60 to 61)
- [X] T028 [P] [US3] `frontend/src/utilities/help.ts`: delete `smoothingHelp`, `smoothingWindowHelp`, `spacingHelp` and their imports of `SMOOTHING_WINDOW_RANGE`; rewrite `frameRateHelp` (now `1 to 60. How many pictures are made for each second of the song. The notes are measured every 60 ms whatever this is: a picture longer than that shows the average of the measurements it covers, a shorter one repeats the latest.`; use `FRAME_RATE_RANGE`); check the window size help (the long lines 18, 45, 51, 64 of the file) for mentions of the spacing or the smoothing and fix them
- [X] T029 [US3] `frontend/src/components/SettingsForm.vue`: remove the imports from `../utilities/spacing` and the smoothing imports, `smoothing`, `smoothingWindowText`, `spacingText`, `defaultSpacingText()`, the `watch` that recomputes the spacing, `spacingError`, `smoothingError`, `smoothingWindowError`, `showDataSmoothing`, `dataSmoothingProblem`, `belowMinimum`/`stepHint` computeds and their notices, the three fields of the settings built for the request, the Window spacing field block (lines ~340 to 352) and the whole `v-if="showDataSmoothing"` group (lines ~660 to 705); remove the `sampleRate` prop; `analysisProblem` is now `windowError || frameRateError`; keep the Image smoothing group untouched
- [X] T030 [US3] `frontend/src/components/FilePicker.vue`: remove the `readSampleRate` call, the `update:sampleRate` event and the `DEFAULT_SAMPLE_RATE` import; `frontend/src/App.vue`: remove `fileSampleRate`, the `:sample-rate` binding and its `update:sampleRate` handler, the import of `DEFAULT_SAMPLE_RATE` and `formatSpacing`, the three result lines (Smoothing, Smoothing window, Window spacing, lines ~81, 82, 103) and the `spacing_raised` notice (lines ~107 to 109); delete `frontend/src/utilities/spacing.ts` and `frontend/src/utilities/wavHeader.ts`
- [X] T031 [US3] Run `npm run typecheck` and `npm test` in `frontend/`; both pass; then `grep -rniE "window.spacing|smoothing window|spacing_|wavHeader|sampleRate" frontend/src` finds nothing, and `grep -rn "Smoothing" frontend/src` finds only *Gaussian smoothing* / *Image smoothing*

**Checkpoint**: the page and the request no longer know the three settings; the backend suite and the frontend suite pass (apart from the baseline failures).

---

## Phase 6: User Story 4 - Every picture type works with the fixed buffers (Priority: P2)

**Goal**: all nine image types still make their pictures at any frame rate, with the same number of frames, and draw exactly as before from the same note values.

**Independent Test**: `verify_drawing.py` reports no difference; a job of every type at 10, 16 and 30 fps is made.

- [X] T032 [US4] Run `python specs/043-decouple-frame-rate/tools/verify_drawing.py` from the repository root; it must exit 0 (no difference from the baseline of T003). If a type differs, the removal changed its drawing: find and fix it (do not rewrite the baseline)
- [X] T033 [P] [US4] Create `backend/tests/test_frame_rate_independence_api.py`: for every name in `IMAGE_TYPES` (use the helpers for the extra settings of other tests where a type needs them) post a 3 s generated stereo file at 10, 16 and 30 fps; each answer is 200, `frame_count == ceil(3 * fps)`, `step_samples` and `window_count` equal across the three rates, and the first and last frame URLs return PNGs (SC-006). Mark nothing as skipped
- [X] T034 [P] [US4] Add to `backend/tests/test_buffers_api.py` (or the file of T033): for types that measure the whole file (`decay`, `polychord`, `rhythm-circles`, `energy-graphs`) the measurement does not depend on the buffers: the answer of the same file at 10 fps is made with the same `render.json` frame rate and the beat positions (`LocalPeaks.frame_positions(fps, frames)` for the same peaks) are the same function of the frame rate as before (compare with a direct call of `measure_local_peaks(...).frame_positions(10, frames)`)
- [X] T035 [US4] Run `python specs/041-code-readability-docs/tools/verify_frames.py` and compare with T004: record in `specs/043-decouple-frame-rate/baseline-verify-frames-after.txt` that it now reports differences for the types (expected: the default step changed), and that each type still makes the same number of frames (the hashes are not rebuilt)

**Checkpoint**: all four stories work.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T036 Run the constitution gates from `backend/`: `python -m pytest tests/test_type_hints.py tests/test_documentation.py -q` passes; the whole suite's failing ids are a subset of `specs/043-decouple-frame-rate/baseline-failures-before.txt` (save the new list as `baseline-failures-after.txt` and compare)
- [X] T037 [P] Run `python specs/041-code-readability-docs/tools/trace_pipeline.py` and `python specs/041-code-readability-docs/tools/shape_probe.py` from the repository root: the order printed for each image type has no `smooth_frames` step and no `window_spacing` call, and `jobs.py` calls `buffer_step()` before `analyze_channels()`; fix any documentation that disagrees (rule III)
- [X] T038 [P] Check SC-007: `grep -rniE "window.spacing|smoothing window|smooth_frames|resolve_step|default_spacing" backend/app frontend/src README.md` finds nothing (the history under `specs/` is not edited, except the two 041 contract lines of T023); update `README.md` if it describes the removed settings
- [X] T039 (done except the by-hand run of section 6, which needs a person at the page; sections 1 to 5 ran as commands, see the notes below) Walk through the checks of [quickstart.md](quickstart.md) sections 1 to 6 (section 6 by hand: start the app, make pictures at 10 and 30 fps) and report which passed; a failure goes back to the task that owns the code
- [X] T040 [P] Update the memory note `decouple-frame-rate-decisions.md` (status: implemented, with the date, the known baseline failures left, and any deviation from the plan)

---

## Dependencies & Execution Order

- **Phase 1** (T001 to T004) before any edit of the source; T002 before T003; T001, T002 and T004 can overlap.
- **Phase 2** (T005, T006) needs Phase 1; blocks everything below.
- **US1** (T007 to T014) needs Phase 2. T008 needs T005; T011 and T012 go together (the documentation test needs the module list to match the files); T013 and T014 need T008.
- **US2** (T015 to T017) needs US1's step (T008) to be meaningful; its tests are independent of US3.
- **US3** needs US1 (T008 touches `jobs.py` first; T021 to T023 touch `frame_rendering.py` and `jobs.py` again, so do T008 before T022). The backend part (T018 to T025) and the frontend part (T020, T026 to T031) are independent of each other.
- **US4** needs US3 (it proves the removal changed no drawing) and the baseline of T003.
- **Polish** last.

### Parallel opportunities

- Phase 1: T002 and T004 with T001.
- Phase 3: T007 and T010 (different files) while T008 is done.
- Phase 5: T018, T019, T020 (three test groups), T024 (docstrings), and the frontend tasks T026, T027, T028 (separate files) in parallel; T029 and T030 after them (they use the removed imports).
- Phase 6: T033 and T034.
- Polish: T037, T038 and T040.

```text
# Example: the frontend half of User Story 3, in parallel
T026 frontend/src/api.ts   T027 frontend/src/utilities/validation.ts + groups.ts   T028 frontend/src/utilities/help.ts
# then
T029 SettingsForm.vue      T030 FilePicker.vue + App.vue
```

## Implementation Strategy

- **MVP = Phase 1 + 2 + User Story 1**: the job analyzes every 60 ms whatever the frame rate. The page still has the old controls at that point (the spacing field would then be ignored by the
  backend), so do US3's frontend half before showing it to anyone.
- **Then** US2 (proof of the averaging), US3 (the removals, the biggest part: about 40 test files and 12 source files change), US4 (proof that nothing was drawn differently), Polish.
- **Stop and check** at each checkpoint with the command in it.
- Commit only when the user asks; this plan does not create a branch.


## Implementation notes (2026-11-18)

- **Results**: backend suite 32 failed / 4855 passed, and the 32 failing ids are exactly the ids of `baseline-failures-before.txt` (the known `DEFAULT_PROMINENCE` and `NEIGHBOURS` failures; none new, none fixed). Frontend: 876 tests and `vue-tsc` pass. `tools/verify_drawing.py`: 9 image types, 216 frames identical to the baseline made before the first edit. `test_type_hints.py` and `test_documentation.py` pass. `trace_pipeline.py` shows `buffer_step()` before `analyze_channels()` and no smoothing step.
- **T035**: `verify_frames.py` differs for 8 of 9 cases, as expected (the analysis step changed); same frame counts; see `baseline-verify-frames-after.txt`.
- **Deviations**: (1) the baseline was taken in a git worktree of HEAD (the first run was in the working tree and would have read edited sources); (2) the endpoint refuses sample rates under 16745 Hz, so 8000 and 11025 Hz are tested on `buffer_step()` only (T006), and `test_jobs_api.py` uses 22050, 32000, 48000 and 96000 Hz; (3) tests that assumed one window per frame and a last window that just fits were changed to check a frame made only from whole windows (research decision 11); (4) T034 was reduced to the beat for Decay (`measure_local_peaks(...).frame_positions`), the types that measure other things are covered by T033; (5) `git rm` was avoided, the deletions are unstaged.
- **Not done**: the by-hand check of quickstart section 6 (start the app and make pictures at 10 and 30 fps). Nothing is committed.
