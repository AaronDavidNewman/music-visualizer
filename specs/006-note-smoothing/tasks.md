---

description: "Task list for Note Smoothing"
---

# Tasks: Note Smoothing

**Input**: Design documents from `/specs/006-note-smoothing/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/http-api-changes.md, quickstart.md

**Tests**: Included, following the plan: pytest for the backend and vitest for the frontend validation helper. The slider is checked with `vue-tsc`, the build and the quickstart.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 or US2

## Phase 1: Setup

- [x] T001 Run `pytest` in `backend/` and `npm test` in `frontend/` to confirm a green baseline before changing anything (316 backend and 107 frontend tests at the end of feature 005), and note the numbers

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The running average itself, which both stories use.

### Tests first

- [x] T002 [P] In `backend/tests/test_frame_rendering.py` add tests for `smooth_frames(frames, smoothing)`, using a small reference implementation written in the test (a plain Python loop over frames and notes, independent of the function under test): with 88 columns all holding the sequence 0, 10, 0, 0 and smoothing 0.5 the output is 0, 5, 2.5, 1.25; the first row is unchanged for every smoothing in 0, 0.25, 0.5, 0.8; for random 40-frame by 88-note data and smoothing 0.0, 0.1, 0.3, 0.5, 0.8 the output equals the reference to within one part in a million; smoothing 0 returns equal values and a new array (modifying it does not change the input); the input array is never modified; each note is independent (changing one column of the input changes only that column of the output); the fade length after a drop from 100 to 0 (value below 10 for the first time) is 1 frame at 0, 4 frames at 0.5 and 11 frames at 0.8, and the same count for a rise measured by the value reaching 90; one frame and zero frames (`shape (0, 88)`) are returned unchanged; the output is never negative for non-negative input and never exceeds the input's maximum; the range limits are accepted (0.0 and 0.8) and `-0.01`, `0.81`, `1`, `nan`, `inf`, `True` and `"0.5"` raise `ValueError` mentioning "smoothing"

### Implementation

- [x] T003 In `backend/app/services/frame_rendering.py` add the constants `MIN_SMOOTHING = 0.0`, `MAX_SMOOTHING = 0.8` and `DEFAULT_SMOOTHING = 0.0`, and `smooth_frames(frames, smoothing=DEFAULT_SMOOTHING)`: validate that `smoothing` is a real number (not a bool) that is finite and from 0.0 to 0.8 inclusive, otherwise raise `ValueError("The smoothing must be a number from 0.0 to 0.8.")`; return a copy when the smoothing is 0 or there are fewer than two frames; otherwise copy the input, then for each later frame `n` set `out[n] = s * out[n-1] + (1 - s) * frames[n]` (one vector operation over the 88 notes per frame) so the first frame stays unchanged and each note uses only its own history; write the docstring in terms of the running average
- [x] T004 Run `pytest` from `backend/` and fix failures in T002 and the existing tests

**Checkpoint**: The running average works and is exact at 0.

---

## Phase 3: User Story 1 - Smooth each note over time (Priority: P1) 🎯 MVP

**Goal**: A smoothing value travels from the request to the frames, notes fade gradually, and the results show which value was used.

**Independent Test**: A note that sounds briefly fades over several frames at 0.5 and more slowly at 0.8, while 0 gives the previous images.

### Tests for User Story 1

- [x] T005 [P] [US1] In `backend/tests/test_jobs_api.py` extend the `post` helper with a `smoothing` argument (sent as the `smoothing` form field when not `None`) and add tests: a request with no `smoothing` returns 200 with `smoothing == 0.0` and frame pixels equal to the pipeline without smoothing (computed independently of `smooth_frames` from `read_wav`, `analyze_channels`, `average_frames`, `to_gray_levels` and the brightness root); `smoothing=0` and `smoothing=0.0` give byte-identical frames to the request with no field; `smoothing=0.5` returns `smoothing == 0.5` and the frame pixels equal the reference pipeline in which the frame values are smoothed with a loop written in the test before scaling (so the scale follows the smoothed maximum), for several frames, using a file whose note changes partway (for example a 440 Hz tone for the first second and silence for the second, so the fade is visible); at 0.8 the tile of that note is brighter than at 0.5 a few frames after the tone stops, and at 0 it is black; the first frame is identical at smoothing 0 and 0.8; `frame_count`, `window_count`, `step_samples` and `window_spacing` are the same at 0, 0.5 and 0.8; a silent file is black at 0 and at 0.8; the same file and settings at 0.5 submitted twice give byte-identical frames; the loudest tile still reaches 255 somewhere at 0.8; `smoothing=0.8` and `smoothing=-0.0` are accepted

### Implementation for User Story 1

- [x] T006 [US1] In `backend/app/routers/jobs.py` accept `smoothing: str | None = Form(None)`; add `_parse_smoothing(text, sent)` returning `DEFAULT_SMOOTHING` when the field was not sent, otherwise a finite float from `MIN_SMOOTHING` to `MAX_SMOOTHING` inclusive (use the existing `_sent_fields` result so an empty or blank value counts as sent and is refused with 400 `The smoothing must be a number from 0.0 to 0.8.`, as do `abc`, `nan`, `inf`, `-0.1`, `0.81` and `1`), called with the other parameter checks before the file is stored; after `average_frames` call `smooth_frames(values, smoothing)` and pass the result to `write_frames`; add `"smoothing": smoothing` to the response (a float, 0.0 when none was sent)
- [x] T007 [US1] Run `pytest` from `backend/` and fix failures in T005
- [x] T008 [P] [US1] In `frontend/src/api.ts` add `smoothing: number` to `JobSettings` and to `JobResult`, and send `smoothing` as a form field in `submitJob`
- [x] T009 [US1] In `frontend/src/components/UploadForm.vue` add a "Smoothing" slider (`<input type="range">` with `min` 0, `max` 0.8, `step` 0.01, starting at 0, disabled while `busy`) bound to a `smoothing` number, include `smoothing` rounded to two decimals (`Math.round(value * 100) / 100`) in the emitted `JobSettings`; in `frontend/src/App.vue` add "Smoothing: {{ result.smoothing.toFixed(2) }}" to the results summary
- [x] T010 [US1] Run `npm test`, `npm run typecheck` and `npm run build` in `frontend/` and fix errors

**Checkpoint**: Smoothing can be set, is applied, and is reported.

---

## Phase 4: User Story 2 - A smoothing slider with clear limits (Priority: P2)

**Goal**: The slider spans exactly 0.00 to 0.80, shows its value, keeps its position, and the server refuses everything outside the range.

**Independent Test**: Slider fully right shows 0.80 and fully left 0.00; the server refuses -0.1, 0.81, abc, nan and an empty value.

### Tests for User Story 2

- [x] T011 [P] [US2] In `backend/tests/test_jobs_api.py` add error tests (these confirm the strict rule written in T006, so they are expected to pass as soon as they are added): `smoothing` of `-0.1`, `0.81`, `1`, `1e9`, `abc`, `nan`, `inf`, `-inf`, an empty string and a blank string each return 400 with the `detail` `The smoothing must be a number from 0.0 to 0.8.` and leave nothing in either temp root (use the existing `assert_rejected` helper); a refused smoothing never reads the file (patch `read_wav` in `app.routers.jobs` to fail if called, and check the 400 still comes back); `0`, `0.8`, `0.35` and `0.123456` return 200 and report the value; a refused request followed by a valid one succeeds
- [x] T012 [P] [US2] In `frontend/src/lib/validation.test.ts` add vitest tests: `SMOOTHING_RANGE` is `{ min: 0, max: 0.8, step: 0.01 }`, `DEFAULT_SMOOTHING` is 0, and the slider has 81 positions (`Math.round((max - min) / step) + 1 === 81`) with its right end equal to 0.8 exactly (`Math.round(0.8 * 100) / 100 === 0.8`); `validateSmoothing` accepts 0, 0.8, "0.35", "0", "0.80", 0.01 and rejects -0.01, 0.81, 1, "", "  ", "abc", "NaN", "Infinity" with the exact message `The smoothing must be a number from 0.0 to 0.8.`; `formatSmoothing` gives "0.00", "0.30", "0.80" and "0.35" for 0, 0.3, 0.8 and 0.35 (and "0.30" for the float 0.30000000000000004)

### Implementation for User Story 2

- [x] T013 [P] [US2] In `frontend/src/lib/validation.ts` add `SMOOTHING_RANGE = { min: 0, max: 0.8, step: 0.01 }`, `DEFAULT_SMOOTHING = 0`, `validateSmoothing(value: string | number): string | null` (trim, empty is invalid, parse with `Number`, require a finite number from 0 to 0.8) and `formatSmoothing(value: number): string` (`toFixed(2)`); run `npm test`
- [x] T014 [US2] In `frontend/src/components/UploadForm.vue` take the slider's `min`, `max`, `step` and starting value from `SMOOTHING_RANGE` and `DEFAULT_SMOOTHING`, show the current value beside it with `formatSmoothing` (an `<output>` element), add a hint "0 is no smoothing; higher values fade notes more slowly.", make `validateSmoothing` part of `canSubmit`, and make sure the slider is neither reset nor changed by changes to the other fields or by a finished or failed submission; run `npm test`, `npm run typecheck` and `npm run build` in `frontend/` and fix errors

**Checkpoint**: Both stories work.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T015 Run the whole backend suite and the frontend checks (`pytest` in `backend/`; `npm test`, `npm run typecheck`, `npm run build` in `frontend/`) and confirm all pass
- [x] T016 Using `backend/audio/fotr-intro1-echo.wav`, check on real data without a browser: (a) SC-001: frames at smoothing 0 equal the previous pipeline's frames pixel for pixel across many frames; (b) SC-002 and SC-004 on a real note: pick a note that stops sounding, count the frames its value takes to fall below 10% of its starting value at smoothing 0.5 and 0.8, and compare with the geometric prediction (**result: not possible on this file.** `fotr-intro1-echo.wav` is sustained and echo-heavy, and no note drops to below 5% of its peak and stays there for 12 frames, so there is no clean real decay to measure. The fade lengths 4 and 11 are verified on constructed data in the unit tests. As a substitute on the real file, the mean frame-to-frame change of the tiles, a measure of flicker, fell to 69%, 51% and 23% of its unsmoothed value at smoothing 0.3, 0.5 and 0.8); (c) SC-008: start the backend on an unused port from `backend/` with the venv (check the port first; do not stop or reuse a server the user is running), time the same `POST /api/jobs` at smoothing 0 and 0.8 (two runs each), confirm the responses report `smoothing` and the same frame and window counts, then stop the server and delete only the job folders created in this run; (d) save a picture of the same run of consecutive frames at smoothing 0 and 0.8 side by side and look at it
- [x] T017 Report that the browser walkthrough in `quickstart.md` (step 3, the slider's ends, its readout, its keyboard steps and its disabled state) was not run if no browser can be driven from this session. **Not run: no browser could be driven from this session.** The range constants, the validation helper and the formatting are unit-tested (including 81 positions and the right end being exactly 0.8), and the form builds and type-checks, but the slider itself (dragging it to both ends, the readout, arrow-key steps, the disabled state and keeping its position after an error) has not been exercised in a browser and needs a manual check.
- [x] T018 [P] Update `README.md` (describe the smoothing slider, the formula, the default of 0, the range 0.0 to 0.8, the order in the pipeline, the API field and the response field) and add a note to `specs/002-audio-frames-ui/data-model.md` (the Frame section) that frame values are smoothed before scaling since feature 006
- [x] T019 Mark completed tasks `[x]` in this file

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → Phase 5.
- US2 builds on the field and request plumbing from US1.
- Within a phase, backend and frontend tasks are independent (T005 with T008; T011 with T012 and T013).
- T006, and no other task, edits `backend/app/routers/jobs.py`; T009 and T014 both edit `frontend/src/components/UploadForm.vue`, so they are sequential.
- Write each group's tests first and see them fail before implementing, except T011, which confirms behavior implemented in T006.

## Implementation Strategy

- **MVP**: Phases 1 to 3: a smoothing value that is applied and reported, with strict server validation and a working slider.
- **Then**: Phase 4 adds the value readout, the shared range constants, the form guard and the explicit refusal tests, and Phase 5 checks the real file, the timing target and the docs.

## Change after implementation (2026-10-06)

- At the user's request (after feature 007 added color) the smoothing also applies to each tile's **hue** over the frames, with the same recurrence and the same parameter. `write_frames` now takes a `smoothing` argument and smooths the note values and then the hues; the router passes the value through instead of calling `smooth_frames` itself. See FR-014, FR-015 and SC-010 in the spec. The tasks above describe the original scope and are left as written.
