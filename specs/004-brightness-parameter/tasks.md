---

description: "Task list for Brightness Parameter"
---

# Tasks: Brightness Parameter

**Input**: Design documents from `/specs/004-brightness-parameter/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/http-api-changes.md, quickstart.md

**Tests**: Included, following the plan: pytest for the backend and vitest for the frontend validation helper. Components are checked with `vue-tsc`, the build and the quickstart.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 or US2

## Phase 1: Setup

- [x] T001 Run `pytest` in `backend/` and `npm test` in `frontend/` to confirm a green baseline before changing anything (175 backend and 87 frontend tests at the end of feature 003), and note the numbers

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The brightness mapping itself, which both stories use.

### Tests first

- [x] T002 [P] In `backend/tests/test_frame_rendering.py` add tests for `boost_levels(levels, brightness)` and the rendering path: for every brightness from 2 to 100 and every level from 0 to 255 the result equals `round(255 * (level / 255) ** (1 / brightness))` (computed independently in the test with Python's `round` on the exact value); level 0 gives 0 and level 255 gives 255 at every brightness; the result never decreases as the level rises, and never decreases as the brightness rises (check all pairs of adjacent brightness values over all 256 levels); brightness 2 equals `round(255 * sqrt(level / 255))` for all 256 levels (the old behavior, SC-001); the examples level 64 → 128, 161, 180, 222, 251 at brightness 2, 3, 4, 10, 100; the default brightness is 2 and `boost_levels(levels)` equals `boost_levels(levels, 2)`; the result is `uint8` and keeps the input shape; `render_frame(levels, brightness=4)` for 88 squares all at level 64 gives pixels all 180; `write_frames(frames, directory, brightness=10)` writes the same number of files as with brightness 2, with different pixel values, and writing twice gives identical bytes

### Implementation

- [x] T003 In `backend/app/services/frame_rendering.py` add the constants `MIN_BRIGHTNESS = 2`, `MAX_BRIGHTNESS = 100` and `DEFAULT_BRIGHTNESS = 2`; replace `boost_levels` with `boost_levels(levels, brightness=DEFAULT_BRIGHTNESS)` that applies a cached 256-entry `uint8` table (build it with `functools.lru_cache` from `np.rint(255.0 * np.power(np.arange(256) / 255.0, 1.0 / brightness))`) by indexing, and raises `ValueError` for a brightness that is not an integer from 2 to 100; add a `brightness` argument (default 2) to `render_frame` and `write_frames` and pass it through; update the docstrings to describe the nth root
- [x] T004 Run `pytest` from `backend/` and fix failures in T002 and the existing tests (the earlier boost tests must pass unchanged at the default)

**Checkpoint**: The mapping works for all brightness values and equals the old look at 2.

---

## Phase 3: User Story 1 - Choose how strongly quiet notes are brightened (Priority: P1) 🎯 MVP

**Goal**: A brightness value travels from the request to the frames, and the results show which value was used.

**Independent Test**: The same file at brightness 2, 4 and 10 gives images where level 64 shows as 128, 180 and 222, with the same frame and window counts.

### Tests for User Story 1

- [x] T005 [P] [US1] In `backend/tests/test_jobs_api.py` add tests: a request with no `brightness` field returns 200 with `brightness == 2`, and its frame pixels equal `round(255 * sqrt(level / 255))` of the levels computed directly with `read_wav`, `analyze_channels`, `average_frames` and `to_gray_levels` (compute the expected pixels independently of `boost_levels`); `brightness=4` returns 200 with `brightness == 4` and pixels equal to the fourth-root mapping of the same levels; the same file at brightness 2, 4 and 10 gives the same `frame_count`, `window_count`, `step_samples` and `window_spacing`, every square at 4 is at least as bright as at 2 and every square at 10 is at least as bright as at 4, and the mean gray level of the first frame rises each time; a silent file gives all-black frames at brightness 2 and at 100; the loudest note is still the brightest square at brightness 2 and 10; the same file and settings at brightness 4 submitted twice give byte-identical frames; `brightness=5.0` is accepted as 5

### Implementation for User Story 1

- [x] T006 [US1] In `backend/app/routers/jobs.py` accept `brightness: str | None = Form(None)`; add `_parse_brightness(text)` returning 2 when the field is absent, otherwise a whole number from `MIN_BRIGHTNESS` to `MAX_BRIGHTNESS` (parse with `float`, require `is_integer()` and the range, so `5.0` is accepted and `2.5`, `abc`, `nan`, `inf`, an empty string, 1 and 101 give 400 `The brightness must be a whole number from 2 to 100.`), called with the other parameter checks before the file is stored; pass it to `write_frames(..., brightness=brightness)`; add `"brightness": brightness` to the response
- [x] T007 [US1] Run `pytest` from `backend/` and fix failures in T005
- [x] T008 [P] [US1] In `frontend/src/api.ts` add `export interface JobSettings { windowSize: number; frameRate: number; windowSpacing: number; brightness: number }`, change `submitJob` to `submitJob(file, settings)` (sending `brightness` as well), and add `brightness: number` to `JobResult`
- [x] T009 [US1] In `frontend/src/components/UploadForm.vue` add a "Brightness" number input (`step="1"`, `min="2"`, `max="100"`, default text `2`, disabled while `busy`) bound to `brightnessText`, and change the `submit` event to emit `(file, settings: JobSettings)`; in `frontend/src/App.vue` pass the settings object to `submitJob` and add "Brightness: {{ result.brightness }}" to the results summary
- [x] T010 [US1] Run `npm test`, `npm run typecheck` and `npm run build` in `frontend/` and fix errors

**Checkpoint**: Brightness can be set, is applied, and is reported.

---

## Phase 4: User Story 2 - A brightness control with clear limits (Priority: P2)

**Goal**: The field refuses bad values with a clear message in the form and on the server, shows its range, and keeps its value.

**Independent Test**: 1, 101, 2.5, 0, -3, `abc` and an empty value are each refused with the range message in the form and by a direct request; 2 and 100 are accepted.

### Tests for User Story 2

- [x] T011 [P] [US2] In `backend/tests/test_jobs_api.py` add error tests (these confirm the strict rule written in T006, so they are expected to pass as soon as they are added): `brightness` of `1`, `101`, `0`, `-3`, `2.5`, `abc`, `nan`, `inf`, `-inf`, `1e9` and an empty string each return 400 with a `detail` containing "brightness", "whole number", "2" and "100", and leave nothing in either temp root (use the existing `assert_rejected` helper); the file is never read for a refused request (patch `read_wav` in `app.routers.jobs` to fail if called, and check the 400 still comes back); `brightness=2` and `brightness=100` return 200; a refused request followed by a valid one succeeds
- [x] T012 [P] [US2] In `frontend/src/lib/validation.test.ts` add vitest tests: `BRIGHTNESS_RANGE` is 2 to 100 and `DEFAULT_BRIGHTNESS` is 2; `validateBrightness` accepts "2", "3", "50", "100", 7, "5.0"; rejects "1", "101", "0", "-3", "2.5", "", "  ", "abc", "NaN", "Infinity", "1e9" with the exact message `The brightness must be a whole number from 2 to 100.`

### Implementation for User Story 2

- [x] T013 [P] [US2] In `frontend/src/lib/validation.ts` add `BRIGHTNESS_RANGE = { min: 2, max: 100 }`, `DEFAULT_BRIGHTNESS = 2` and `validateBrightness(value: string | number): string | null` (trim, empty is invalid, parse with `Number`, require `Number.isInteger` and the range); run `npm test`
- [x] T014 [US2] In `frontend/src/components/UploadForm.vue` validate the brightness with `validateBrightness`, show the error message when invalid and otherwise the hint "Whole number, 2 to 100. Higher values lift quiet notes more but show less contrast." (using `BRIGHTNESS_RANGE`), include it in `canSubmit`, initialize `brightnessText` from `DEFAULT_BRIGHTNESS`, and make sure it is neither reset nor changed by changes to the other fields or by a finished or failed submission; run `npm test`, `npm run typecheck` and `npm run build` in `frontend/` and fix errors

**Checkpoint**: Both stories work.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T015 Run the whole backend suite and the frontend checks (`pytest` in `backend/`; `npm test`, `npm run typecheck`, `npm run build` in `frontend/`) and confirm all pass
- [x] T016 Using the sample file `backend/audio/fotr-intro1-echo.wav`, check on real data without a browser: (a) SC-001: render frames at the default settings with brightness 2 and compare every pixel with an independent `round(255 * sqrt(level / 255))` of the same levels, for several frames; (b) SC-003: compute the average gray level of a typical frame (and the mean over a spread of frames) at brightness 2 and at 4 and report the percentage rise against the 25% target; (c) SC-004: levels 0 and 255 across all 99 brightness values; (d) SC-006: start the backend on an unused port from `backend/` with the venv (check the port first; do not stop or reuse a server the user is running) and time the same `POST /api/jobs` at brightness 2 and 10, then stop the server and delete the job folders it created in the temp directories; (e) save a side-by-side image of the same frame at brightness 2, 4, 10 and 100 and look at it
- [x] T017 Report that the browser walkthrough in `quickstart.md` (step 3, the form field, its validation messages and its disabled state) was not run if no browser can be driven from this session. **Not run: no browser could be driven from this session.** The validation helper is unit-tested and the form builds and type-checks, but the field itself (its hint, error message, disabled state while busy, and keeping its value) has not been exercised in a browser and needs a manual check.
- [x] T018 [P] Update `README.md` (describe the brightness field, the formula, the default of 2 and the API field) and change the "square root" wording in the feature 002 docs (`specs/002-audio-frames-ui/spec.md` FR-010 and the brightness assumption, `data-model.md`, `research.md`, `contracts/http-api.md`) so they point to the brightness parameter and say the square root is the default (brightness 2)
- [x] T019 Mark completed tasks `[x]` in this file

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → Phase 5.
- US2 builds on the field and request plumbing from US1.
- Within a phase, backend and frontend tasks are independent (T002 with nothing else; T005 with T008; T011 with T012 and T013).
- T006 and nothing else edits `backend/app/routers/jobs.py`; T009 and T014 both edit `frontend/src/components/UploadForm.vue`, so they are sequential.
- Write each group's tests first and see them fail before implementing, except T011, which confirms behavior implemented in T006.

## Implementation Strategy

- **MVP**: Phases 1 to 3: a brightness value that is applied and reported, with the strict rule on the server and a working field.
- **Then**: Phase 4 adds the form validation, the range hint and the explicit refusal tests, and Phase 5 checks the real file, the 25% and 10% targets, and updates the docs.
