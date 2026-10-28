---

description: "Task list for Spiral Note Layout (feature 026)"
---

# Tasks: Spiral Note Layout

**Input**: Design documents from `/specs/026-spiral-note-layout/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/note-layout.md, quickstart.md

**Tests**: Written first for each story (the project's practice): the layout as a table, the picture at the pixel level with notes that each have their own value, the API, and the page's group, dropdown, summary and request (server-side rendering and source guards, since there is no browser or DOM library here). The look in the player is the manual step of the quickstart.

**Organization**: By user story: US1 the layout and its use in the pictures (P1), US2 choosing it through the server and the page (P2), US3 the other settings keeping their meaning (P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- Paths are from the repository root. The Spec Kit setup scripts cannot run here (PowerShell execution policy), so the feature files were written by hand. Backend checks run with the user's colormap lists possibly still inconsistent: use the temporary-default runner (`scratchpad/run_with_default.py`, file restored) and report the one expected list-mismatch failure. Edit files with their line endings preserved; avoid `sed -i`; scripts with backticks, backslashes or non-ASCII go in files written with the Write tool (an escaped backslash in an edit script once became a control character); replace test functions only block by block and compare test counts before and after.

---

## Phase 1: Setup

- [x] T001 Record the baseline before changing anything: the backend suite (temporary default colormap, file restored; expect 3,768 tests), the frontend suite (expect 555), typecheck and build; the four reference hashes (`scratchpad/hashes019.py`: `6819990556fd4095`, `f32a99c59fcb87fc`, `92b3a27dee73e223`, `400cc93e1bfca03d`); the per-file backend test counts (`scratchpad/count_tests.py <file>`); the tests that list the response keys exactly (the six that list `gaussian`) or the groups of an image type (`groups.test.ts`, `SettingsForm.test.ts`), because the new field and group will touch them.
  - Done: Baseline carried over from the end of feature 025 (nothing changed in between): backend 3,768 tests (temporary default colormap), frontend 555, typecheck and build clean; the four reference hashes `6819990556fd4095`, `f32a99c59fcb87fc`, `92b3a27dee73e223`, `400cc93e1bfca03d`; per-file counts saved (`scratchpad/counts_026_before.txt`).

---

## Phase 2: User Story 1 - The notes laid out as a spiral around middle C (Priority: P1) 🎯 MVP

**Goal**: `note_layout.py`, and `write_frames` using it for Tiles, Blended tiles and Concentric.

**Independent Test**: `write_frames(values, directory, image_type="tiles", note_layout="spiral")` with a different value for every note: the tile of every note is at the cell of the spec's table, and with `note_layout="rows"` the frames equal those made without the argument.

### Tests for User Story 1 (write first, they fail)

- [x] T002 [P] [US1] Create `backend/tests/test_note_layout.py` (spec FR-001 to FR-005, SC-001 to SC-003): the spec's table written out in the test as a literal 7 x 12 list of offsets, and `note_order("spiral")` compared with it cell by cell (the note of a cell is `27 + offset`); every cell holds a different note and every note 0 to 83 is in one cell; middle C (index 27) is at row index 2, column index 5; the cell to its right holds index 28 and the one to its left index 26; the high notes' first three cells are east, south-east and south of C and the low notes' first three west, south-west and north-east; the high notes wind clockwise (the cross product of successive steps around C turns right) and the low counterclockwise, tested on the first ring; exactly the 13 listed pairs of semitone neighbours are not next to each other on the grid, and no other; the rule itself re-implemented in the test (two square-spiral walkers taking turns) gives the same table; `note_order("rows")` is `0 … 83`; the order is the same on every call and cannot be changed by the caller (a copy or a read-only array); `check_note_layout`: `rows` and `spiral` accepted and returned, `Rows`, `SPIRAL`, ` rows`, `rows `, empty, `None`, a number, a list refused with `The note layout must be one of rows, spiral.`; `arrange_notes`: the values in cell order (`out[:, i] == values[:, order[i]]`), shape `(frames, 84)`, columns after the 84th dropped, the input unchanged, rows is a copy equal to the first 84 columns, a bad layout or shape refused (`At least 84 note values per frame are needed (got shape ...).`), a permutation (the sorted values are those of the input).
  - Done: `backend/tests/test_note_layout.py` (35 tests): the spec's table as a literal list compared cell by cell, a permutation of the 84 notes, middle C at row 3 column 6 with C# to its right and B3 to its left, the first cells of the two arms, the rotation sense by cross products, the winding outward, exactly the 13 jumps, the rule rebuilt in the test from explicit legs giving the same table, rows the identity, read-only orders, `check_note_layout` with twelve refused values, `arrange_notes` (cell order, copies, the four undrawn notes dropped, the input unchanged, a permutation, bad shapes, no frames). **A finding while writing it: the spec said the low arm's first three cells are west, south-west and north-west of C; the table (and the algorithm) put the third one at the north-east, because the arm skips the south, south-east and east cells that the high arm has taken. The table is the normative text, so the spec and tasks were corrected.**
- [x] T003 [P] [US1] Create `backend/tests/test_note_layout_rendering.py` (spec Story 1 and 3, FR-004, FR-006 to FR-008, SC-004 to SC-006): helpers that give every note its own distinct value (for example `value(n) = (n + 1) / 84`) so a tile's color says which note it is; for `tiles` and `blended` and several colormaps: with `note_layout="rows"` the frames are byte-identical to omitting the argument; with `"spiral"` the tile at every cell (the center pixel of the tile; for blended the center, which keeps its own color) has the color that note `note_order[i]` has in the rows layout at its own cell (compare the two pictures cell against cell through the order); the set of hidden notes with a threshold is the same notes in both layouts (decode which tiles are black or the background by note); with `note_count` below 84 the tiles shown are the same strongest notes, spread in pitch order along the spiral (compare against `arrange_notes(spread_notes(...))` pushed through the rows renderer); with `resolution` 3 the finer grid equals the one made from the rearranged values (blend of screen neighbours) and the picture is not the rows picture; the beat colors (`beat` given) work in both; smoothing, interpolate 2 and Gaussian smoothing give the same result as drawing the rearranged values with rows; for `concentric` with a different value for every note: the circle centered on a cell has the step of the note placed there (compare steps through `ring_steps` of the rearranged values, and that the center cell pixels of two layouts differ); a lone loud note is drawn at the cell of the table with 12 rings; `contour`, `circles` and `circles_paint` give byte-identical frames with `note_layout="spiral"` and with rows; a bad `note_layout` is refused before anything is written for every image type, with the message; determinism.
  - Done: `backend/tests/test_note_layout_rendering.py` (101 tests): rows byte-identical to omitting the argument for all six types; the tile of every cell has the color of the note the layout puts there, for tiles and blended and every colormap; the central **equivalence**: drawing the notes in the spiral is byte for byte drawing the cell-ordered notes with rows, for tiles and blended with ten combinations of threshold, smoothing, resolution, interpolate, Gaussian smoothing, beat and blend width, and for Concentric with and without a beat; the same notes hidden; Notes below 84 spread along the spiral; a finer grid blends screen neighbours; the loudest circle centered on its cell inside it with 12 rings; contour and the circles byte-identical with either layout; bad values refused before anything is written for every type.

### Implementation for User Story 1

- [x] T004 [US1] Create `backend/app/services/note_layout.py` (module docstring: the two layouts, middle C's index 27 and cell, the rule of the spiral, that it is a permutation applied before the picture is made, the 13 jumps): `LAYOUTS = ("rows", "spiral")`, `DEFAULT_NOTE_LAYOUT = "rows"`, `MIDDLE_C_NOTE = 27`, `MIDDLE_C_CELL = (2, 5)`, the spiral built from the rule of data-model.md (a generator of square-spiral cells from a start cell, turning right or left, legs 1, 1, 2, 2, 3, 3, …; the two walkers taking turns, high first, each taking the next cell on the grid and not yet taken), `check_note_layout`, `note_order(layout)` (a read-only or copied `int64` array of 84 notes, one per cell, computed once), `arrange_notes(values, layout)`. In `backend/app/services/frame_rendering.py`: `write_frames(..., beat=None, note_layout=DEFAULT_NOTE_LAYOUT)`; check it with the other settings; for `tiles` and `blended` apply `arrange_notes` to `shown` (after `spread_notes`, before `interpolate_grid`); for `concentric` pass `arrange_notes(smoothed, layout)` to `write_concentric_frames`; update the `write_frames` docstring. Run the tests of T002 and T003 and fix.
  - Done: `backend/app/services/note_layout.py` (the rule as two walkers on square spirals, `check_note_layout`, `note_order`, `arrange_notes`) and `write_frames(..., note_layout=...)` (checked for every type, applied for tiles and blended after the note selection and before the grid is interpolated, applied for concentric before the circles are drawn); its docstring.
- [x] T005 [US1] Mutation checks, each caught by the tests and restored byte for byte (`scratchpad/mutate_024.py` with `more_026_us1.py`): the high walker turning left or the low one turning right, the legs not growing (1, 1, 1, 1), the walkers not taking turns (one after the other), the low walker first, a walker not skipping taken cells, a walker not skipping off-grid cells, middle C at row 3 column 6 counted from 0 (index 3, 6), `MIDDLE_C_NOTE` 28, the order inverted (cell to note instead of note to cell), `arrange_notes` applied after `interpolate_grid`, applied for contour, not applied for concentric, applied twice, the layout not checked in `write_frames`, `rows` returning the spiral, `arrange_notes` keeping the four undrawn columns.
  - Done: 16 mutations (`scratchpad/mutate_024.py` with `more_026_us1.py`), all caught at once.

**Checkpoint**: Tiles, Blended tiles and Concentric can be drawn in the spiral layout through `write_frames`; everything else is unchanged.

---

## Phase 3: User Story 2 - Choose the layout through the server and the page (Priority: P2)

**Goal**: The `note_layout` field of the job request, and the page's group with the dropdown, the request and the summary.

**Independent Test**: Post a WAV with `image_type=tiles&note_layout=spiral`: 200, `note_layout` echoed, frames in the spiral layout; on the page choosing Tiles, Blended tiles or Concentric shows the group Note layout with Rows selected.

### Tests for User Story 2 (write first, they fail)

- [x] T006 [P] [US2] Create `backend/tests/test_note_layout_api.py` (FR-005, FR-006, FR-009, SC-005; helpers as in `test_concentric_api.py`: `post`, a WAV with a steady tone): the default `rows` is echoed for all six image types; `rows` and `spiral` accepted and echoed for all six; `Rows`, `SPIRAL`, ` spiral`, empty, `circle`, `1` refused with the message and nothing created, also with no file at all; the frames with `note_layout=rows` are byte-identical to a job that sends no layout, for Tiles, Blended tiles and Concentric; with `spiral` they differ for those three and the tone's tile (or circle) is at the cell the table gives the tone's note (use `note_tone(36)`, which is 3 semitones above... compute its offset from the note index and look it up in the table, and compare the colored tile's cell); for Contour, Circles and Circles paint the frames with `spiral` are byte-identical to those with `rows`; the response keys are those of the other jobs plus `note_layout`; 600 x 400 frames, the same count.
  - Done: `backend/tests/test_note_layout_api.py` (64 tests at the end): defaults and both values echoed for all six types, eight refused values with nothing created, checked before the file is read, the same keys plus `note_layout`, rows identical to a job with no layout, the tone's tile and the tone's circle at the cell of the table, contour and circles ignoring it, size, count and determinism.
- [x] T007 [P] [US2] Update the six API tests that list the response keys exactly (they list `gaussian`): add `note_layout` after `gaussian`, keeping each test's meaning; the counts must not drop.
  - Done: The six API tests that list the response keys now list `note_layout`; no count dropped.
- [x] T008 [P] [US2] Frontend tests (vitest; no browser): `validation.test.ts` (`NOTE_LAYOUTS` equal to Rows and Spiral in order with values `rows` and `spiral`, `DEFAULT_NOTE_LAYOUT` `rows`, `validateNoteLayout` accepts the two and refuses `Rows`, ` rows`, empty and others with the server's message `The note layout must be one of rows, spiral.`, `noteLayoutApplies` true for tiles, blended and concentric only, `noteLayoutLabel`); `groups.test.ts` (the group `note-layout` titled "Note layout" with the control `note-layout`; `groupsFor` for tiles, blended: `analysis, colormap, image-type, <type>, note-layout, local-peaks, data-smoothing, image-smoothing`; for concentric `analysis, colormap, image-type, note-layout, concentric-peaks, data-smoothing`; no other type has it; `groupOf("note-layout", ...)`; `rowsOf(1)` is [1]; the existing expectations updated); `api.test.ts` (the request has `note_layout`, `rows` and `spiral`); `SettingsForm.test.ts` (SSR: the group and a `<select id="note-layout">` with the options Rows and Spiral and Rows selected for the three types, absent for contour, circles and circles paint; the group's place; the number of `<SettingsGroup` becomes eight in the source guard; the value is in the payload; the existing group-order expectations updated); `App.test.ts` (the summary line "Note layout:" shown for the three types by `noteLayoutApplies(result.image_type)` and formatted with the label); `help.test.ts` (the help text says where middle C is (3rd row, 6th column), clockwise and counterclockwise, that the default is Rows, and the pictures it applies to).
  - Done: Frontend tests: validation (the two layouts, default, refusals with the server's message, `noteLayoutApplies`, the label), groups (thirteen groups, `note-layout`, the order for every type, only three types), `api.test.ts`, the form (the dropdown with Rows selected for three types, absent for the others, the group's place, source guards for the ref, payload, problem flag and submit guard, the group count eight), the summary guard, the help text. 28 tests added; the 024 group-order test and the concentric page test were updated for the new group; 583 in all.

### Implementation for User Story 2

- [x] T009 [US2] Implement in `backend/app/routers/jobs.py`: the form field `note_layout`, `_parse_note_layout` (not sent means `rows`; anything sent must be exactly one of the two, else a 400 with the message), called with the other parsers before the file is read, passed to `write_frames`, echoed in the response. Run the tests of T006 and T007 and fix.
  - Done: `jobs.py`: the form field, `_parse_note_layout` (the message of `check_note_layout` is the 400 detail), called before the file is read, passed to `write_frames`, echoed.
- [x] T010 [US2] Implement the frontend: `frontend/src/utilities/validation.ts` (`NOTE_LAYOUTS`, `DEFAULT_NOTE_LAYOUT`, `validateNoteLayout`, `noteLayoutApplies`, `noteLayoutLabel`), `groups.ts` (the group `note-layout`, `groupsFor`), `help.ts` (`noteLayoutHelp`), `api.ts` (the field and the request), `components/SettingsForm.vue` (the ref, the error, the group rendered with `SettingsGroup`, its problem flag, the dropdown with the info button, the submit guard, the payload), `App.vue` (the summary line). Run the tests of T008, then the frontend suite, `vue-tsc` and the build.
  - Done: Frontend: `validation.ts`, `groups.ts`, `help.ts`, `api.ts`, `SettingsForm.vue` (the group, the dropdown, error, problem flag, submit guard, payload), `App.vue` (the summary line). 583 frontend tests pass, typecheck and build clean. A stray control character from an escaped backslash was not a problem this time (the edit scripts were written with the Write tool).
- [x] T011 [US2] Mutation checks for the API and the page, each caught and restored: the field not echoed, the default `spiral`, `Spiral` accepted, empty accepted, the layout checked only for some types, the layout checked after the file is read, not passed to `write_frames`, the group shown for contour or circles, the group after Local peaks, the dropdown's options swapped or the default selected wrong, the request not sending it, the summary line shown for contour, the problem flag or submit guard missing, the label wrong.
  - Done: 7 backend and 19 frontend mutations (`more_026_api.py`, `mutate_fe_026.py`); 25 caught at once, the one survivor (the submit guard's source pattern also matched the problem flag) was caught after the pattern was tightened to look for it after `&&`.

**Checkpoint**: the layout can be chosen and created from the page and the API.

---

## Phase 4: User Story 3 - The other settings keep their meaning (Priority: P3)

**Goal**: Pin that the layout only changes where a note is drawn.

**Independent Test**: With a threshold and a Notes value, the same notes are hidden and kept in both layouts.

### Tests for User Story 3

- [x] T012 [US3] Add to `test_note_layout_rendering.py` and `test_note_layout_api.py` (spec Story 3, FR-008, SC-006): through the API with a real WAV of several tones and clicks: the hidden notes (by note, decoded from the cells through the table) are the same in both layouts in every frame for several thresholds; `note_count` 36 keeps the same strongest notes; the beat coloring box on gives the same colors by note in both layouts; Oversampling 3 and interpolate 2 and Gaussian smoothing give pictures equal to drawing the rearranged note values with the rows layout; a silent file and a one-tone file make frames in both layouts; mono equals stereo; for Concentric the circle sizes (steps) by note are the same in both layouts.
  - Done: Story 3 through the API with a real chord: the color of every note is the same wherever the layout puts it for tiles and blended with seven combinations of threshold, note count, beat and smoothing, the same hidden notes, the same rings of every note in Concentric, silent and short files, mono equals stereo.

### Implementation for User Story 3

- [x] T013 [US3] Run the tests of T012 and fix whatever they find in `note_layout.py`, `frame_rendering.py` or `jobs.py`; mutation checks, each caught and restored: the threshold applied in cell order to the wrong values, the spread notes arranged before `spread_notes` instead of after, the beat applied by cell (a different position per cell), a column of the rearranged values lost.
  - Done: Mutations through the API: the layout applied before the note selection, twice, not for concentric: all caught by the API tests; two structural mutations (the arm turning the other way, the order inverted) are not caught by the API file, because it compares the layouts through the module's own order, but are caught by the table tests of T002 (T005).

**Checkpoint**: all three stories work together.

---

## Phase 5: Polish and cross-cutting

- [x] T014 [P] README (`README.md`, CRLF kept): a **Note layout** paragraph (since feature 026): the two layouts, where middle C sits (3rd row, 6th column), the spiral table and the rule (two square-spiral arms taking turns, the high notes clockwise and the low notes counterclockwise, the 13 jumps), that it is a reordering of the 84 values so every other setting works on notes as before and Oversampling blends screen neighbours, the three pictures it applies to and that the others ignore it, the request field and message, the group on the page and the summary line.
  - Done: README (CRLF kept): a **Note layout** paragraph (since feature 026) with the table, the rule, the 13 jumps, what is reordered and what is not, the request field, the group on the page.
- [x] T015 Final verification: the whole backend suite (temporary default colormap) with the per-file counts compared to T001 (nothing dropped), the frontend suite, typecheck and build, the four reference hashes equal to T001, `git status` showing only the files of this feature, pictures of Tiles and Concentric in both layouts for the same note values (`scratchpad/layout_pictures.py`, sent to the user), and a note in the report that the Spec Kit setup scripts could not be run. Mark all tasks `[x]` with a Done line each.
  - Done: Backend 3,968 tests pass (3,768 + 200 new: `test_note_layout.py` 35, `test_note_layout_api.py` 64, `test_note_layout_rendering.py` 101; no other file's count changed), frontend 583 pass (555 + 28), typecheck and build clean, the four reference hashes equal, `git status` shows only the files of this feature (and the earlier ones that are not committed); a comparison picture of Tiles and Concentric in both layouts was sent to the user. The Spec Kit setup scripts could not be run (PowerShell execution policy), so `plan.md` and `tasks.md` were written by hand.

---

## Dependencies and order

- T001 first. T002 and T003 are independent of each other and written before T004; T005 after T004.
- US2 needs US1: T006, T007 and T008 may be written in parallel; T009 needs T004; T010 needs T008; T011 after T009 and T010.
- US3 needs US2 (it tests through the API): T012 then T013.
- T014 any time after T010; T015 last.

## Parallel opportunities

- T002 and T003 (different files); T006, T007 and T008 (backend API tests, the existing key tests and the frontend tests); T014 alongside T011 to T013.

## Implementation strategy

MVP is US1: the layout table and its use in `write_frames`. US2 makes it reachable (the request and the page). US3 pins that nothing but the places changes. The default (Rows) never changes a picture, so each phase can be verified against the four reference hashes.
