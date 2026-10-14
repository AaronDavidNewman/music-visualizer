---

description: "Task list for the grouped, collapsible settings (feature 020)"
---

# Tasks: Grouped, Collapsible Settings

**Input**: Design documents from `/specs/020-grouped-settings-ui/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/settings-ui.md, quickstart.md

**Tests**: Written first for each story (the project's practice): the pure group model, the server-side rendering of the form for every image type, source guards for the layout and accessibility markup, and the backend tests of the radius. There is no DOM test library and none is added (research Decision 4); the visual check is the manual step of the quickstart.

**Organization**: By user story (spec): US1 the collapsible two-per-row groups with the always-present groups (P1), US2 the groups of the chosen image type (P2), US3 the smoothing groups and the new names (P3). The Radius change (backend and the frontend's vocabulary for it) is foundational because the Circles group of US2 needs it.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- Paths are from the repository root. Backend checks run with the user's colormap lists possibly still inconsistent: use the temporary-default runner (`scratchpad/run_with_default.py`) and restore the file, and report the one expected list-mismatch failure.

---

## Phase 1: Setup

- [x] T001 Record the baseline before changing anything: run the backend suite (temporary default colormap, file restored) and the frontend suite, typecheck and build; record the four reference hashes with `scratchpad/hashes019.py`; save the list of control ids and labels that the current form renders (server-side render of `frontend/src/components/SettingsForm.vue`) into the notes of this task, so that "every control exactly once" can be checked against what existed.
  - Done: Baseline: backend 2,843 passed plus the one expected failure (the user's colormap lists do not match: `test_the_frontends_list_matches_this_one_name_for_name_in_the_same_order`, run with the temporary default colormap `coolwarm`, file restored); frontend 383 tests, typecheck and build clean; the four reference hashes `1fb17963…`, `f6f336a1…`, `fce777da…`, `886b2e42…`. The form rendered these controls, in one flat list: window-size, frame-rate, window-spacing, colormap, smoothing-window, smoothing, threshold, notes, image-type, blend-width, resolution, interpolate (and, for circles, the five circle controls).

---

## Phase 2: Foundational (the radius and the renamed vocabulary)

**Purpose**: The Radius replaces Size in the backend and the request; the messages of the renamed settings change; the frontend gets the radius range, validators, readout, help and API field. The form template is not touched yet.

**⚠️ CRITICAL**: The Circles group (US2) and the summary (US3) use these.

- [x] T002 [P] Update the backend tests first (they fail until T003): in `backend/tests/test_circles.py` replace the size constants, `check_circle_size`, `SIZE_MESSAGE`, `circle_radius()` tests by the radius (`MIN/MAX/DEFAULT_CIRCLE_RADIUS` 4/8/4, `check_circle_radius`, message `The circle radius must be a whole number from 4 to 8.`, accepted `[4, 6, 8, np.int64(5), 7.0]`, refused `[0, 3, 9, 4.5, 100]`) and change `UNIT_MESSAGE` to `The circle movement must be a whole number from 1 to 10.`; in `backend/tests/test_circles_rendering.py` the disc radius must be exactly the radius that was set (and 1 to 3 times it with the resize), the covered-area tests use the radius (area of a disc of that radius to within 8%, nine times with the resize on), the refusals and the extreme-settings test use `circle_radius`; in `backend/tests/test_circles_api.py` the field `circle_radius` (default 4, `4.0` and ` 6 ` accepted, refusals `["", " ", "0", "3", "9", "5.5", "abc", "nan", "inf", "1e9", "-4"]`, checked before the file is read, for every image type, echoed as an integer, changes the frames, `circle_size` sent is ignored and absent from the response); in the five exact-response-key tests (`test_colormap_api.py`, `test_contour_api.py`, `test_resolution_api.py`, `test_note_count_api.py`, `test_interpolation_api.py`) and in `test_circles_api.py` replace `circle_size` by `circle_radius`; in the resolution tests (`test_resolution*.py`, `test_note_count*.py`, `test_interpolation*.py` where they state the message) change the message to `The oversampling must be a whole number from 1 to 5.`
  - Done: Backend tests changed (function counts kept: 35, 32 and 21 plus one new API test): radius constants 4/8/4 and `check_circle_radius` with its refusals, disc radius exactly the radius that was set whatever the movement, covered area for radii 4 to 8, the resize tests on the radius (1 to 3 times it), the refusals, the extreme settings, `circle_radius` through the API (default, `4.0` and ` 6.0 ` accepted, refusals, checked before the file is read, every image type, an integer, changes the frames), a request that still sends `circle_size` accepted and ignored, the five exact-response-key tests, the two renamed messages (movement, oversampling).
- [x] T003 Implement the backend radius and the messages: `backend/app/services/circles.py` (constants, `check_circle_radius`, drop `circle_radius(size)` and the size constants and message, `write_circle_frames(..., radius=...)` drawing discs of exactly that radius times the resize factor, docstrings), `backend/app/services/frame_rendering.py` (`circle_radius` argument and its early check, docstring), `backend/app/routers/jobs.py` (`_parse_circle_radius`, the form field `circle_radius`, the call, the response key `circle_radius`, no `circle_size`; the messages of the circle unit and of the resolution parsers and of `check_resolution` in `backend/app/services/image_types.py`/where it lives). Run the circle, resolution, note-count, interpolation, colormap and contour tests, then the whole suite; the four reference hashes must be unchanged.
  - Done: `circles.py` (radius constants and check, `circle_radius(size)` removed, `write_circle_frames(..., radius=...)` draws discs of exactly that radius), `frame_rendering.py`, `jobs.py` (`_parse_circle_radius`, field and response key `circle_radius`, the movement and oversampling messages) and `resolution.py` (the oversampling message). Backend 2,850 tests passed plus the one expected failure; the four reference hashes unchanged.
- [x] T004 [P] Update the frontend tests first: `frontend/src/utilities/validation.test.ts` (`CIRCLE_RADIUS_RANGE` 4 to 8 step 1, `DEFAULT_CIRCLE_RADIUS` 4, `validateCircleRadius` accepts `[4, 6, 8, "5", " 7 ", 6.0]` and refuses `[0, 3, 9, 4.5, "", "abc", "NaN", "Infinity", "1e9", NaN, Infinity]` with `The circle radius must be a whole number from 4 to 8.`, `formatCircleRadius(4)` is `4 px`, the unit message is `The circle movement must be a whole number from 1 to 10.`, the resolution message is `The oversampling must be a whole number from 1 to 5.`, no `CIRCLE_SIZE_RANGE`, no `formatCircleSize`), `frontend/src/utilities/help.test.ts` (`circleRadiusHelp` mentions 4 to 8 and "radius", `circleUnitHelp` says Movement and not Unit, `resolutionHelp` says Oversampling and not Resolution, `circleNotesHelp` is about the notes of Circles).
  - Done: `validation.test.ts` (radius range 4 to 8, default 4, validator and `4 px` readout, the renamed messages, no `CIRCLE_SIZE_RANGE`/`formatCircleSize`), `help.test.ts` (radius help, Movement and Oversampling in the texts, none of Unit/Resolution as words).
- [x] T005 Implement the frontend vocabulary: `frontend/src/utilities/validation.ts` (radius range, default, validator, readout; the renamed messages), `frontend/src/utilities/help.ts` (`circleRadiusHelp` replaces `circleSizeHelp`; the help of Movement, Notes and Oversampling use the new names), `frontend/src/api.ts` (`circle_radius` / `circleRadius`, form field `circle_radius`, no `circle_size`). The template still uses the old control until T010; keep it compiling by pointing the existing Size slider at the radius range (it is replaced in T010).
  - Done: `validation.ts`, `help.ts` (`circleRadiusHelp` replaces `circleSizeHelp`; the Movement, Notes and Oversampling texts; the resize text speaks of the radius), `api.ts` (`circle_radius` / `circleRadius`). The old template was pointed at the radius so that it kept compiling until T010.

**Checkpoint**: backend and frontend tests pass; the radius works end to end in the API.

---

## Phase 3: User Story 1 - The settings are arranged in labelled groups that can be collapsed (Priority: P1) 🎯 MVP

**Goal**: A reusable collapsible group, the group model, and the always-present groups (Analysis, Colormap, Image type) in two-per-row layout.

**Independent Test**: Render the form: the sections Analysis, Colormap and Image type are `<details open>` elements with titles; Window size and Frame rate share a row and Window spacing has its own; collapsing one section changes nothing else (model test); the layout CSS has the two-per-row basis and the odd-last-full rule.

### Tests for User Story 1 (write first, they fail)

- [x] T006 [P] [US1] Create `frontend/src/utilities/groups.test.ts` for the pure model: `GROUPS` lists the nine groups of data-model.md with their control ids in order; `groupsFor(type)` returns the ordered ids for each of the four image types (and refuses an unknown one); for every type every control id appears in exactly one shown group and the union equals the controls that apply to that type; `rowsOf(n)` is `[1]`, `[2]`, `[2, 1]`, `[2, 2]`, `[2, 2, 1]` for 1 to 5 and `[]` for 0 (and refuses negatives); the rows of every group of every type have no row above two and, when odd, exactly one single last row; `isOpen` is true for a group that was never toggled, `toggle` flips only that group and returns a new state without touching the others, and toggling twice restores it.
  - Done: `frontend/src/utilities/groups.test.ts`: the nine groups, `groupsFor` for each type, every control exactly once and the expected controls written out independently, `rowsOf` for 0 to 6 and its refusals, no row above two and an odd last row of one, the open state helpers (never-touched is open, `toggle` and `setOpen` touch one group and do not mutate). Note: `groupsFor` for a type that is not one of the four returns no type group (it does not throw, so a bad value cannot break the page); the task text said "refuses".
- [x] T007 [P] [US1] Extend `frontend/src/components/SettingsForm.test.ts` (server-side rendering): the form has `<details>` groups with `<summary>` titles; the first three are Analysis, Colormap and Image type in that order, all `open`; Analysis contains `window-size`, `frame-rate`, `window-spacing` in that order and Colormap and Image type their one control each; Create frames follows the last group; the old tests that depended on the order (Threshold after Smoothing, Resolution after Interpolate and so on) are rewritten for the new order or removed with a note; source guards on `SettingsGroup.vue` and the form's style: `flex-wrap: wrap`, a cell basis of half the width minus half the gap, `min-width: 0`, the `:last-child:nth-child(odd)` rule giving `flex-basis: 100%`, a narrow-viewport media query giving one cell per row, the `<summary>` containing the title and the text "needs attention" shown by a `problem` prop (text, not colour alone), no `v-show`/`v-if` on a group's body (a collapsed body keeps its inputs).
  - Done: `SettingsGroup.test.ts` (new: details/summary, open and collapsed rendering with the controls kept, the "needs attention" mark, the flex body, source guards of the CSS) and the new group tests in `SettingsForm.test.ts`; the old tests that assumed the old order, the disabling by type and the old labels were rewritten (13 of them: the old threshold, blend width, resolution, notes and circles tests).

### Implementation for User Story 1

- [x] T008 [US1] Create `frontend/src/utilities/groups.ts` (research Decisions 4, 5, 8): the typed `GROUPS` table, `groupsFor`, `groupTitle`, `controlsIn`, `groupOf`, `rowsOf`, `isOpen`, `toggle`; the control ids are the form's real ids (data-model.md). No Vue import.
  - Done: `frontend/src/utilities/groups.ts` (no Vue import).
- [x] T009 [US1] Create `frontend/src/components/SettingsGroup.vue` (research Decisions 1, 2, 6, 7): props `id`, `title`, `open`, `problem`; a `<details :open>` with a `<summary>` (title, and "needs attention" when `problem`), emitting `toggle` with the new open state from the element's `toggle` event; the slot is a flex body whose direct children are laid out two to a row with the odd last one at full width; the narrow-viewport rule; the shared cell styles (`.field`, `.field-head`, slider rows with the readout in the label row, `small.error`, `small.notice`) move here from `SettingsForm.vue`'s scoped style where the cells are now rendered.
  - Done: `frontend/src/components/SettingsGroup.vue` (native `<details>`; non-scoped style because the cells are passed through the slot; the readout rule and cell styles live in the form's own scoped style).
- [x] T010 [US1] Edit `frontend/src/components/SettingsForm.vue`: an optional prop `initialImageType` (default Tiles; only to start the form with another type, used by the tests), one `reactive` open-state map using `isOpen`/`toggle`, one computed `problem` flag per group, the three groups Analysis, Colormap and Image type wrapping their controls in `SettingsGroup`, and the remaining controls (still in their old order for now) inside a temporary `SettingsGroup` titled by their final group so nothing is outside a group; the form's own `.settings` style keeps only the list layout and the button.
  - Done: `SettingsForm.vue` rewritten: six `SettingsGroup`s, one open-state map, six problem flags, the optional `initialImageType` prop, the readout of every slider moved into the label row. **Deviation from the staging of the tasks**: the form was written once with all six groups, so T013 and T016 were done inside this step; their tests (T012, T015) had been written first and failed before it (13 failed, 436 passed at the first run, the failures being the old tests and two of the new ones: the server-side render adds a scope attribute to the label tags and fragment markers around slots).
- [x] T011 [US1] Verify: vitest, vue-tsc and build pass; mutation checks, each caught and restored: the odd-last rule removed, the group body hidden with `v-if` (values lost), `toggle` changing all groups, `rowsOf(3)` giving `[1, 2]`, a control id in two groups of one type, the open default false.
  - Done: Frontend 452 tests, typecheck and build clean. Mutation checks, all 20 caught and restored (`scratchpad/mutate_020_front.py`): the odd-last rule, the body hidden with v-if, `rowsOf(3)` as `[1, 2]`, `toggle` changing every group, a control in two groups, the open default false, Blend width in Tiles, Threshold in Circles, Circles without Resize by volume, the type group's id fixed, a type-dependent `disabled`, Image smoothing for Circles, Threshold in Data smoothing, a label back to Resolution, the summary's Circle size, the problem mark never shown, the starting type ignored, cells without `min-width: 0`, the narrow-screen rule removed, the browser's open state not reported.

**Checkpoint**: US1 works: titled collapsible groups, two to a row, Analysis/Colormap/Image type in place.

---

## Phase 4: User Story 2 - The groups after the image type depend on the type that is chosen (Priority: P2)

**Goal**: Exactly one of Tiles, Contour, Blended Tiles and Circles follows Image type, with the controls of the table, and controls that do not apply are not shown.

**Independent Test**: Render the form with each image type (starting-type prop): the group after Image type and its controls are those of the table; no control for another type is in the document; the values kept per type are in the model.

### Tests for User Story 2 (write first)

- [x] T012 [P] [US2] In `frontend/src/components/SettingsForm.test.ts` (using `initialImageType`): for Tiles and Contour the group after Image type has `threshold` and `notes` (and no `blend-width`, no circle ids); for Blended tiles `threshold`, `notes`, `blend-width` (Blend width last, alone on its row by the model); for Circles `circle-unit`, `circle-radius`, `circle-resize`, `circle-memory`, `circle-notes` in that order and none of `threshold`, `notes`, `blend-width`; the group title is Tiles, Contour, Blended Tiles or Circles; there is exactly one type group; no input has `disabled` because of the image type any more (only while busy); a source guard that the form has no `gridSettingsApply`/`blendWidthApplies` disabling. In `frontend/src/utilities/groups.test.ts`: the group ids per type are `tiles`, `contour`, `blended`, `circles`, and an unknown type has none.
  - Done: In `SettingsForm.test.ts` and `groups.test.ts`: for each type the group after Image type and its controls, one type group only, Tiles and Contour with the same controls and their own titles, Blend width and Notes alone on the last row, nothing disabled by type (only while busy), no `gridSettingsApply`/`blendWidthApplies` greying, the values of the other types' controls kept in refs and sent, the starting-type prop.

### Implementation for User Story 2

- [x] T013 [US2] Edit `frontend/src/components/SettingsForm.vue`: the type group is rendered from `groupsFor(imageType)` (one `SettingsGroup` with the id of the image type), its controls with `v-if` from `controlsIn`; remove the `disabled` conditions that depended on the image type; the Circles controls are Movement (`circle-unit`), Radius (`circle-radius`, the radius range and `formatCircleRadius`), Resize by volume (`circle-resize`), Memory and Notes (`circle-notes`) with their labels; Threshold and Notes of Tiles/Contour/Blended are one set of controls shared by the three groups; the type group's `problem` flag covers its visible controls; values are kept in the form's refs so switching types keeps them.
  - Done: Done in T010 (the type group is rendered from `groupsFor` with `v-if` per control from `controlsIn`).
- [x] T014 [US2] Verify: vitest, vue-tsc and build pass; mutations caught and restored: the blend width shown for Tiles, Threshold shown for Circles, the Circles group missing Resize by volume, the type group's id not changing with the type (open state shared), a type-dependent `disabled` left in.
  - Done: Covered by the 20 mutation checks of T011 (type-group ones included).

**Checkpoint**: US1 and US2 work.

---

## Phase 5: User Story 3 - Two smoothing groups, and clearer names (Priority: P3)

**Goal**: Data smoothing and Image smoothing in their place; the four renames everywhere the user reads.

**Independent Test**: Data smoothing is in every render and holds Smoothing window and Smoothing; Image smoothing holds Oversampling and Interpolate for the three grid types and is absent for Circles; no old name appears in the form, the info texts, the messages or the summary.

### Tests for User Story 3 (write first)

- [x] T015 [P] [US3] In `frontend/src/components/SettingsForm.test.ts`: for every image type the last groups are Data smoothing (`smoothing-window`, `smoothing`) then, except for Circles, Image smoothing (`resolution`, `interpolate`); labels are "Oversampling", "Movement", "Radius", "Notes", "Smoothing window (frames)" and "Smoothing"; a scan of the rendered HTML for every type and of the source of `SettingsForm.vue`, `help.ts`, `validation.ts` and `App.vue` for the old labels as words (Unit, Size, Circles per frame, Resolution) finding none (the request field names `resolution` and `circle_unit` in code are not labels); in `frontend/src/App.test.ts`: the circles summary lines are Movement, Radius, Resize by volume, Memory and Notes with their formatters (`formatCircleUnit`, `formatCircleRadius`, `formatCircleResize`, `formatCircleMemory`, `formatCircleNotes`), the grid lines are Threshold, Notes, Interpolate, Oversampling (with `formatResolution` kept for the value), and the Oversampling line is shown only by `gridSettingsApply`; `frontend/src/utilities/help.test.ts` for the info texts of the renamed controls.
  - Done: Data smoothing for every type and Image smoothing for the grid types only, the labels Movement/Radius/Resize by volume/Memory/Notes/Oversampling and the `aria-label`s, a scan of every rendered label and of the form's own source labels for the old names, and in `App.test.ts` the summary lines and their order, with the old names absent (these failed before `App.vue` was changed: 4 failures).

### Implementation for User Story 3

- [x] T016 [US3] Edit `frontend/src/components/SettingsForm.vue` (Data smoothing and Image smoothing groups, `v-if` for Image smoothing by `gridSettingsApply`, labels and `aria-label`s of the info buttons renamed, the temporary group of T010 gone), `frontend/src/App.vue` (the summary lines renamed: Movement, Radius, Memory, Notes, Oversampling), and the readout helpers in `frontend/src/utilities/validation.ts` that print the old names (their comments and any text).
  - Done: Smoothing groups and the renamed labels were part of T010; `App.vue` summary lines now say Movement, Radius, Resize by volume, Memory, Notes and Oversampling; two comments in `validation.ts` that said the old names were fixed.
- [x] T017 [US3] Verify: vitest, vue-tsc and build pass; mutations caught and restored: Image smoothing shown for Circles, Threshold left in Data smoothing, a label back to "Resolution", the summary line "Circle size" back.
  - Done: 452 frontend tests, typecheck, build; the mutation checks of T011 cover the story 3 cases; a scan of `frontend/src` (not tests) for Circles per frame, Unit, circle size and Resolution finds none.

**Checkpoint**: all three stories work.

---

## Phase 6: Polish & Cross-Cutting

- [x] T018 [P] Update `README.md` (the settings page: the groups, the order, the collapse, two to a row, hidden inapplicable controls; the circles paragraph: Movement, Radius 4 to 8 default 4 with `circle_radius`, the renamed messages, Notes; the Resolution paragraph: the control is now called Oversampling, the field is still `resolution`) and add amendment notes (not rewrites) to the documents of features 016 and 019 that name Resolution, Unit, Size or Circles per frame (`specs/016-interpolated-resolution/`, `specs/019-generative-circles/` spec, plan, data-model, contract, quickstart, tasks), saying the names and the radius changed in feature 020.
  - Done: README: a new paragraph for the settings page after Circles, the Circles paragraph (Movement, Radius 4 to 8 with `circle_radius`, Notes, Memory, the messages, hidden instead of greyed out), the Oversampling paragraph (called Resolution until this feature; the field is still `resolution`); amendment notes at the top of the documents of features 016 and 019 (14 files).
- [x] T019 Final verification: backend suite (temporary default, file restored; only the user's list-mismatch failure may remain), the list-tolerance run (`scratchpad/tolerance.py`), the four reference hashes equal to T001, frontend vitest, vue-tsc and build; a scan of `frontend/src`, `README.md` and the new spec for the old labels; the backend mutation checks of the radius (limits, router ignoring the field, response key, disc radius, resize factor on the radius) each caught and restored.
  - Done: Backend 2,850 passed plus the user's list-mismatch failure; the list-tolerance run 2,602 passed and only `test_the_frontends_default_matches_this_one` failed (the same unsettled default: backend `hot`, frontend `coolwarm`), both files restored byte for byte; the four reference hashes equal to T001; frontend 452 tests, typecheck and build clean; 12 backend mutation checks all caught (router ignoring the radius, omitting the key, accepting 3, a wrong default, limits 3 to 9, a disc one pixel too large or sized by the movement, `write_frames` dropping it, the three old messages).
- [x] T020 Walk the quickstart: sections 1 to 3 through the test client and the suites; section 4 (the page in a browser) cannot be done with this tooling: say so in the report, list what the rendered-form tests and source guards do cover, and what only a person can check (half-width sliders, wrapped labels, the 1366 × 768 fit). Render the circles at radius 4, 6 and 8 and send the picture to the user.
  - Done: Quickstart 1 to 3 done (suites, hashes, the radius through the test client and the rendered pictures at radius 4, 6 and 8, sent to the user). **Step 4 (the page in a browser) was not done**: this tooling has no browser. What is covered: the group model, server-side rendering of the form for the four image types, the layout rules read from the styles, the accessibility markup. What only a person can check: how the half-width sliders and wrapped labels look, whether the readouts overlap, the 1366 x 768 fit with every group folded, a real click and keyboard toggle.

---

## Dependencies & Execution Order

- **Setup (T001)** first. **Foundational (T002 to T005)** next: T002 before T003, T004 before T005; the backend pair and the frontend pair are independent of each other ([P]).
- **US1 (T006 to T011)** needs T005 (the form compiles). T006 and T007 first, then T008 (the model) before T009 and T010; T009 before T010.
- **US2 (T012 to T014)** needs US1; **US3 (T015 to T017)** needs US2 (the form's structure). All three edit `SettingsForm.vue`, so they run in order.
- **Polish (T018 to T020)** after the stories; T018 can run alongside T019.

### Parallel opportunities

- T002 with T004 (backend tests, frontend tests); T003 with T005 once their tests are written.
- T006 with T007 (different files).
- T018 with T019.

## Implementation Strategy

1. T001 baseline, Phase 2 (the radius and the vocabulary), then US1 as the MVP: the collapsible two-per-row groups with the always-present groups. Stop and run the quickstart's automatic checks.
2. US2, then US3, each verified on its own with mutation checks.
3. Documentation, the full verification and the quickstart walk, an honest report of what a browser would have to confirm.

## Notes

- A hidden control keeps its value and is still sent; collapsing never discards a value (FR-011).
- The four reference hashes must not change; circles files change only through the radius (default 4 against the old 3.98).
- Edit files with line endings preserved (the CRLF files of the frontend and backend); avoid `sed -i`; scripts with backticks or non-ASCII go in files written with the Write tool, not in shell heredocs.
- Never replace a test function by a regex that can span several blocks (an earlier accident deleted tests); use block-based replacement and check test counts before and after.
