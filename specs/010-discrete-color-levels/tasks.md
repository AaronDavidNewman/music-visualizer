---

description: "Task list for Discrete Color Levels"
---

# Tasks: Discrete Color Levels

**Input**: Design documents from `/specs/010-discrete-color-levels/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/color-levels-api.md, quickstart.md

**Tests**: Included, following the plan: pytest for the level count, the rounding rule, the rendering and the API, and vitest for the new validation helpers and explanation texts. Component behavior in the browser is checked by the quickstart steps.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root. Backend commands run in `backend/` with the venv's Python (`.venv/Scripts/python -m pytest`), frontend commands in `frontend/`. The API field names are `hue_step`, `saturation_step` and `brightness_step`; in backend rendering code the last one is `value_step` (the HSV name), see research Decision 4.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2 or US3

## Phase 1: Setup

- [x] T001 Run `pytest` in `backend/` and `npm test`, `npm run typecheck` and `npm run build` in `frontend/` to confirm a green baseline before changing anything, and note the test counts. Also create frames from one sample `.wav` through the running API (or a short script using the test client) and keep one frame PNG's bytes outside the repository (for example in the scratchpad) to compare against after the change (SC-001)
  - Done: 538 backend and 164 frontend tests passed, typecheck and build clean. Reference run kept in the scratchpad: 120 frames, combined hash `2688e9c2…`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The rounding rule and the allowed steps, in one tested place that rendering, the router and the tests all use.

- [x] T002 Create `backend/app/services/color_levels.py` per data-model.md and research Decisions 1 to 3: constants `HUE_SCALE = 360`, `UNIT_SCALE = 100`, `HUE_STEPS = (12, 36, 90, 180)`, `UNIT_STEPS = (5, 10, 20, 50)`; `level_count(step: int, scale: int) -> int` returning `floor((scale + step) / step + 0.5)`; `check_step(step, allowed, label)` that returns `None` for `None`, returns `int(step)` for a real whole number (bools refused) that is in `allowed`, and otherwise raises `ValueError(f"The {label} step must be N/A or one of {', '.join(map(str, allowed))}.")`; and `snap(values, step, scale)` taking a float array (or scalar) on the 0..1 scale and returning a new float64 array: with `step=None` an unchanged copy, otherwise `np.minimum(np.floor(values * scale / step + 0.5 + 1e-9) * step, scale) / scale` (never below 0). Module docstring: state that this is the last step for each property and that halves go up
- [x] T003 [P] Create `backend/tests/test_color_levels.py` for `app/services/color_levels.py`: `level_count` gives 31, 11, 5, 3 for hue steps 12, 36, 90, 180 on scale 360 and 21, 11, 6, 3 for steps 5, 10, 20, 50 on scale 100, and is never below 3 for any allowed step; `check_step` accepts `None`, each allowed value (also `20.0` and numpy integers) and refuses `0`, `-5`, `7`, `51`, `90` for the unit list, `2.5`, `True`, `"20"`, `nan`, `inf` with the exact message `The hue step must be N/A or one of 12, 36, 90, 180.` (use the label passed in); `snap` with step 20 on scale 100 maps 0.49 to 0.4, 0.5 to 0.6 (halves up), 0.1 to 0.2, 0.09 to 0.0, 0 to 0 and 1 to 1; with hue step 12 the fraction `6 / 360` maps to `12 / 360` even though `6 / 360 * 360` may not be exactly 6.0 in floating point; with hue step 180 only 0, 0.5 and 1.0 appear over a dense sweep of 0..1; with step 50 only 0, 0.5, 1.0; over a dense sweep of 0..1 for every allowed step the set of results has exactly `level_count` members, always includes 0 and 1, never exceeds 1, and is non-decreasing in the input; `snap(values, None, scale)` equals the input and is a copy (changing the result does not change the input); the input array is never modified; `snap` works on 1-D and 2-D arrays

**Checkpoint**: `pytest backend/tests/test_color_levels.py` passes; nothing else in the project has changed.

---

## Phase 3: User Story 1 - Reduce the colors to a few distinct steps (Priority: P1) 🎯 MVP

**Goal**: Each of hue, saturation and brightness can be rounded to its levels through the job API, with N/A as the default that changes nothing (FR-001 to FR-009, FR-011 to FR-013).

**Independent Test**: Quickstart "Story 1". The same file with Saturation steps N/A and 20 gives frames whose tile saturations are exactly 0, 20, 40, 60, 80 or 100, with hue and brightness unchanged.

### Tests for User Story 1

- [x] T004 [P] [US1] In `backend/tests/test_frame_rendering.py` add tests for rounding in the drawing code: `tile_colors(levels, brightness, hues, value, saturation_step=20)` gives tiles whose HSV saturation (computed from the RGB with `colorsys`, tolerance for 8-bit rounding) is one of 0, 0.2 … 1.0, while hue and value (brightest channel) are identical to the same call without the step; `saturation_step=None` equals the call without it; an unlisted step raises `ValueError` with the message from `check_step`; a tile with value 0 stays `(0, 0, 0)` with any saturation step; `write_frames(..., hue_step=90)` on a multi-frame input with varied notes writes PNGs where every tile's hue (from its RGB, for tiles with saturation and value above a floor so the hue is defined) is within tolerance of 0°, 90°, 180°, 270° or 360°, and the tiles' saturation and brightness equal those from a run with all steps N/A; `write_frames(..., value_step=50, energies=...)` gives frames whose brightest channel is 0, 128 (127.5 rounded) or 255 only, the loudest frame 255 and a zero-energy frame 0, and with no energies given and a `value_step` it still works (full brightness); each property changes alone: three runs with one step each differ from the all-N/A run only in that property (compare per-tile HSV); `write_frames` with all steps N/A, and with no step arguments at all, write byte-identical files (FR-002, SC-001); invalid steps in `write_frames` raise `ValueError`
- [x] T005 [P] [US1] In `backend/tests/test_jobs_api.py` add API tests for the three fields: each accepted value for each field (hue 12, 36, 90, 180; saturation and brightness 5, 10, 20, 50), also written as `20.0`, and `N/A`, `n/a`, ` N/A ` are accepted; a request that does not send the fields returns `null` for all three and the same frame bytes as a request that sends `N/A` for all three; the response carries the values used (`"hue_step": 90` and so on, `null` for N/A); refused with 400 and the exact message (including the list) for empty, `0`, `-12`, `7`, `51`, `90` on `saturation_step`, `5` on `hue_step`, `2.5`, `abc`, `nan`, `inf`; a refused request creates no job and reads no audio (the temp directories are unchanged); with `saturation_step=20` on a generated multi-note WAV every distinct tile color of every frame has an HSV saturation in {0, 0.2 … 1.0} (tolerance for 8-bit rounding), with `brightness_step=50` every frame's brightest channel is 0, 128 or 255, with `hue_step=180` every colored tile is red or cyan; the same request twice gives identical frame bytes (FR-013)
  - Done in a new file, `backend/tests/test_color_levels_api.py`, instead of `test_jobs_api.py`, so the shared `post` helper stays unchanged. `backend/tests/test_energy_api.py` was updated for the three new response keys.

### Implementation for User Story 1

- [x] T006 [US1] In `backend/app/services/frame_rendering.py` import `HUE_SCALE`, `HUE_STEPS`, `UNIT_SCALE`, `UNIT_STEPS`, `check_step` and `snap` from `color_levels.py`. Give `tile_colors` an optional keyword `saturation_step: int | None = None`: validate with `check_step(saturation_step, UNIT_STEPS, "saturation")` and, when set, replace the saturations (the boosted gray levels divided by 255) with `snap(saturations, step, UNIT_SCALE)` before the HSV conversion. Give `write_frames` optional keywords `hue_step`, `saturation_step`, `value_step` (all `None` by default): validate all three up front with `check_step` (labels `hue`, `saturation`, `brightness`; lists `HUE_STEPS`, `UNIT_STEPS`, `UNIT_STEPS`) before writing anything; after `hue_sequence` call `hues = snap(hues, hue_step, HUE_SCALE)`; after `value_sequence` call `values = snap(values, value_step, UNIT_SCALE)`; pass `saturation_step` to `tile_colors`. Rounding is the last step of each property (after smoothing and the roots). Update the docstrings of `write_frames` and `tile_colors` and the module docstring (one sentence: each property can be rounded to levels). Make T004 pass
- [x] T007 [US1] In `backend/app/routers/jobs.py` add `_parse_step(text, sent, allowed, label) -> int | None` in the style of `_parse_energy`: not sent gives `None`; sent and `text.strip().lower() == "n/a"` gives `None`; otherwise float-parse (failure, `nan`, `inf`, empty and non-whole numbers refused) and require membership of `allowed`, with `HTTPException(400, f"The {label} step must be N/A or one of {...}.")` (the same message `check_step` produces). Add the form fields `hue_step`, `saturation_step`, `brightness_step` (`str | None = Form(None)`) to `create_job`, parse them next to the other settings (before the file is read), pass `hue_step`, `saturation_step` and `value_step=brightness_step` to `write_frames`, add the three keys to the response (`None` serializes as `null`), and update the comment above `write_frames`. Make T005 pass
- [x] T008 [US1] Run `pytest` in `backend/` and confirm everything passes. Then repeat the sample-file job from T001 with no step fields and confirm the frame PNG is byte-identical to the one kept in T001 (SC-001)
  - Done: 665 backend tests passed at this point; the reference run gave the identical combined hash with no step fields and with all three set to `N/A`.

**Checkpoint**: The API rounds each property to its levels and, with the defaults, produces exactly the old frames.

---

## Phase 4: User Story 2 - Choose the steps on the page and see what they mean (Priority: P2)

**Goal**: Three dropdowns with level counts, explanations and summary lines on the page (FR-010, FR-012).

**Independent Test**: Quickstart "Story 2". Open the page, change each dropdown and see the level count, create frames, and see the three steps in the summary.

### Tests for User Story 2

- [x] T009 [P] [US2] In `frontend/src/utilities/validation.test.ts` add tests for the new helpers from `validation.ts` (written in T011): `HUE_STEPS` and `UNIT_STEPS` are exactly `[12, 36, 90, 180]` and `[5, 10, 20, 50]` and `DEFAULT_STEP` is `"N/A"`; `levelCount(step, scale)` gives 31, 11, 5, 3 for the hue steps and 21, 11, 6, 3 for the others and is never below 3; `levelLabel("N/A", scale)` is `"N/A (smooth)"` and `levelLabel("20", 100)` is `"20 (6 levels)"`, `levelLabel("90", 360)` is `"90 (5 levels)"`; `validateStep(value, allowed, label)` returns `null` for `"N/A"` and each allowed value (as text or number) and the message `The hue step must be N/A or one of 12, 36, 90, 180.` (with the right label and list) for `""`, `"0"`, `"7"`, `"51"`, `"abc"`, `"2.5"`, and for a value that is only valid for the other list (such as `"90"` for saturation); `stepToNumber("N/A")` is `null` and `stepToNumber("20")` is `20`
- [x] T010 [P] [US2] In `frontend/src/utilities/help.test.ts` add tests that `hueStepHelp`, `saturationStepHelp` and `brightnessStepHelp` mention N/A meaning smooth and list their allowed choices (built from the same constants), and that the hue text says both ends of the wheel are red

### Implementation for User Story 2

- [x] T011 [US2] In `frontend/src/utilities/validation.ts` add `HUE_SCALE = 360`, `UNIT_SCALE = 100`, `HUE_STEPS = [12, 36, 90, 180] as const`, `UNIT_STEPS = [5, 10, 20, 50] as const`, `NA_STEP = "N/A"`, `DEFAULT_STEP = NA_STEP`, `levelCount(step: number, scale: number)` (`Math.floor((scale + step) / step + 0.5)`), `levelLabel(value: string | number, scale: number)` returning `"N/A (smooth)"` or `` `${step} (${levelCount} levels)` ``, `validateStep(value: string | number, allowed: readonly number[], label: string): string | null` (null for `"N/A"` case-insensitively trimmed or a whole number in `allowed`; otherwise the message `The <label> step must be N/A or one of <list>.`), and `stepToNumber(value: string): number | null`. Make T009 pass
- [x] T012 [US2] In `frontend/src/utilities/help.ts` add `hueStepHelp`, `saturationStepHelp` and `brightnessStepHelp`, built from the constants: what the setting does (rounds the value to that many evenly spaced levels), that N/A means smooth, that a larger step gives fewer, bolder levels, and the allowed choices; the hue text also says that 0° and 360° are both red, so the largest step gives only red and cyan. Make T010 pass
- [x] T013 [P] [US2] In `frontend/src/api.ts` add `hue_step`, `saturation_step` and `brightness_step` (`number | null`) to `JobResult` and `hueStep`, `saturationStep`, `brightnessStep` (`number | null`) to `JobSettings`; in `submitJob` append `hue_step`, `saturation_step` and `brightness_step` to the form as the text `N/A` for `null` or `String(value)`. Fix any other code or test file that builds a `JobSettings` or `JobResult` literal so `npm run typecheck` passes
- [x] T014 [US2] In `frontend/src/components/SettingsForm.vue` add three state refs (strings, default `DEFAULT_STEP`), three `<select>` elements in a new `field-row` below the Brightness/Saturation row, in the order Hue steps, Saturation steps, Brightness steps (labels exactly those; ids `hue-step`, `saturation-step`, `brightness-step`; options `N/A` then the allowed numbers; `:disabled="busy"`), each with an `InfoPopover` (labels "hue steps", "saturation steps", "brightness steps") using the texts from T012, and a small readout beside it (a `<span class="level-count">` or `<output>`) showing `levelLabel(value, scale)`; include validation errors (`validateStep`) in `canSubmit` and show an inline `<small class="error">` if one is ever present; emit `hueStep`, `saturationStep`, `brightnessStep` as `stepToNumber(...)` in the submitted settings. Keep the existing style (grid `field-row`, `field-head`)
- [x] T015 [US2] In `frontend/src/App.vue` add three summary items after "Smoothing": `Hue steps: N/A | n`, `Saturation steps: …`, `Brightness steps: …` (null shown as `N/A`)
- [ ] T016 [US2] Run `npm test`, `npm run typecheck` and `npm run build` in `frontend/` and confirm all pass; then follow quickstart "Story 2" in the browser (dropdown contents and order, level readouts, info popovers, disabled while busy, summary lines)
  - Tests (205), typecheck and build pass, and a server-side render of the form (`frontend/src/components/SettingsForm.test.ts`) confirms the three dropdowns, their options and order, info buttons, the `N/A (smooth)` readouts and the disabled state. NOT done: the walk-through in a real browser (changing a dropdown, seeing the readout update, the popovers opening, the summary after a job).

**Checkpoint**: Steps can be chosen on the page and are shown in the summary.

---

## Phase 5: User Story 3 - Levels hold steady across frames and with smoothing (Priority: P3)

**Goal**: Rounding is applied last, after smoothing and the roots, and depends only on a frame's own values (FR-006, FR-007, FR-009).

**Independent Test**: Quickstart "Story 3". With Saturation steps 50 and smoothing 0.8 every saturation is 0, 50 or 100; a file with silence added at the end differs only in the frames that differ without any step.

- [x] T017 [P] [US3] In `backend/tests/test_frame_rendering.py` add interaction tests on `write_frames`: with smoothing 0.8 and each step set, the rounded values equal `snap` applied to the smoothed values computed independently in the test (smoothing is not applied to the rounded values: choose an input where smoothing then rounding differs from rounding then smoothing, and assert the former); with `saturation_step=50` and smoothing 0.8 every tile's saturation is 0, 0.5 or 1.0; the brightness root (`energy_root` 1 to 8) with `value_step=50`: the loudest frame is always 255 and a zero-energy frame always 0; the Saturation root (`brightness` 2 and 100) with `saturation_step=20` still yields only the six levels and a tile with level 0 stays unsaturated; writing a file of N frames and the same file with extra frames appended (extra notes and energies at the end) with the same steps gives identical PNGs for the first N frames, for each step; tiles with brightness 0 (silent frame) are black with any combination of the three steps; the largest steps (180, 50, 50) together give only red and cyan hues, saturations in {0, 0.5, 1} and brightness in {0, 0.5, 1}
- [x] T018 [P] [US3] In `backend/tests/test_jobs_api.py` add one API test: a generated multi-note WAV posted with `smoothing=0.8`, `saturation_step=50` and `brightness_step=50` gives only the allowed levels in every frame, and the same file with one second of silence appended gives identical first frames
  - Done in `backend/tests/test_color_levels_api.py`. Silence at the end changes the same frames with and without steps (only the last original frame, whose analysis window the end of the file cuts short; this also happens on the code from before this feature), so the test asserts exactly that. The spec wording (Story 3 scenario 4, FR-007, SC-006) was corrected to match.

**Checkpoint**: Interactions behave as specified; any failure here points at the order of rounding in `write_frames`.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T019 [P] Update `README.md`: describe the three step settings in the settings list (allowed values, N/A = smooth, levels `round((range + step) / step)`, both ends included, halves up, rounding is the last step after smoothing and the roots), add the three optional form fields and response fields to the API description (`hue_step`, `saturation_step`, `brightness_step`; `N/A` or a listed number; 400 with the listed choices otherwise), and note that the API's `brightness` and `energy` fields are unrelated to `brightness_step`. Keep the existing wording style and mention `specs/010-discrete-color-levels/data-model.md`
- [x] T020 Run everything: `pytest` in `backend/`, `npm test`, `npm run typecheck` and `npm run build` in `frontend/`; all must pass. Report the final test counts against the T001 baseline
  - Done: backend 538 → 684 tests, frontend 164 → 205 tests, all passing; typecheck and build clean.
- [x] T021 Measure performance (SC-009): time creating frames for the sample file with all steps N/A and with all three at their smallest step (the most levels: hue 12, saturation 5, brightness 5) through the test client, a few runs each; the difference must be within 10%. If not, profile `snap` and `tile_colors` and fix before finishing
  - Done: 60 s file (1800 frames), median of 5 interleaved runs: all N/A 0.95 s, no fields 0.94 s, smallest steps 1.01 s (+5.9%), largest steps 1.00 s (+4.9%). Within the 10% limit. The all-N/A run was not compared with the code from before this feature (it is the same path plus a copy of three arrays).
- [ ] T022 Follow the rest of `specs/010-discrete-color-levels/quickstart.md` (Story 1 and Story 3 steps in the running application, including the refused-request examples) and tick the checklist items you confirmed; report anything that differs from the spec
  - Partly done through tests and direct API calls: the level sets for each property, the refused values and the interactions with smoothing. NOT done: the in-browser steps of quickstart Stories 1 to 3.

---

## Dependencies & Execution Order

- Phase 1 first. Phase 2 (T002, then T003 in parallel) blocks all stories.
- **US1 (Phase 3)** needs Phase 2. T004 and T005 are written first (they fail until T006 and T007); T006 before T007; T008 last.
- **US2 (Phase 4)** needs the API fields from US1 only for the end-to-end check in T016; T009 to T013 can start as soon as Phase 2 is done and run in parallel with US1 (different files: frontend vs backend). T011 before T012 and T014; T013 before T014 and T015.
- **US3 (Phase 5)** needs T006 and T007. T017 and T018 are independent of each other.
- **Polish** last; T019 can be done any time after T007 and T014.

### Parallel opportunities

- T003 alongside T002's review; T004 and T005 (different test files); the whole frontend track (T009 to T015) alongside the backend track after Phase 2; T017 and T018; T019 with T020's preparation.

## Implementation Strategy

- **MVP**: Phases 1 to 3 (US1). The API rounds each property and the defaults leave frames unchanged; the steps can be tried with curl or the interactive API docs.
- Then US2 puts the dropdowns on the page, which is what users actually touch, and US3 locks in the interactions with smoothing and the roots.
- Keep the change reviewable: do not touch the energy measure, the note analysis or the PNG writing, and keep every new argument optional so existing callers and tests are unaffected.
