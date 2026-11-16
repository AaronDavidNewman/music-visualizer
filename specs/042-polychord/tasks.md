# Tasks: Polychord

**Input**: Design documents from `/specs/042-polychord/` (plan.md, spec.md, research.md, data-model.md, contracts/polychord.md,
quickstart.md)

**Prerequisites**: plan.md, spec.md; the backend runs with `backend/.venv\Scripts\python.exe`, run tests with
`-p no:cacheprovider`.

**Tests**: included, and written **before** the code they test (the practice of every feature of this repository). Use an
independent oracle for numbers (a loop that follows the spec's words, not the formula of the code), and a mutation check at the
end. Tests follow `local_peaks.DEFAULT_PROMINENCE` and never hard-code its value. **Baseline**: 25 backend tests fail before
any change (`specs/041-code-readability-docs/tools/baseline-failures.txt`); "no regression" means exactly those.

**Standard** (constitution v1.0.0, applies to every task that writes code): every function typed, arrays by the aliases of
`array_types.py` with `Arrays:`/`Returns:`/`Attributes:` docstring lines, an `Order of operations:` list in the module
docstring, the image type's block in the pipeline overview of `image_types.py`, comments and docstrings wrapped at 120
columns.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1 (the figure), US2 (copies, rotation, tempo color), US3 (settings, job and page)

## Phase 1: Setup

**Purpose**: a baseline to compare against, and the vocabulary of the new arrays.

- [X] T001 Run the whole backend suite and `specs/041-code-readability-docs/tools/verify_frames.py` before any edit; confirm that exactly the 25 tests of `specs/041-code-readability-docs/tools/baseline-failures.txt` fail and that all 540 frames are identical to the baseline (write the result down in the notes of this file's last section).
- [X] T002 Add the eight new aliases to `backend/app/services/array_types.py`, each with its `Shape:`, `Meaning:` and `Made by:` comment as in `specs/042-polychord/data-model.md`: `LoudLetters`, `LinkTurns`, `CopyCounts`, `FrameTempos`, `StartAngles`, `FigureColors`, `LinkSegments`, `LinkWidths` (follow the form of the existing 76 aliases; `test_documentation.py` checks it).

---

## Phase 2: Foundational (blocks every story)

**Purpose**: the module, its settings and their checks, which every story uses.

- [X] T003 [P] Write `backend/tests/test_polychord.py` part 1, the settings: `check_polychord_notes` accepts 5, 6, 8, `6.0`, refuses 4, 9, `5.5`, True, `"6"`, None, nan, inf; `check_polychord_copies` accepts 1, 12, 3.0 and refuses 0, 13, 2.5, True, nan; `check_polychord_rotation` accepts -360, 0, 15.5, 360 and refuses -360.1, 361, nan, inf, True, text; `check_polychord_settings` refuses a maximum under the minimum and accepts equal; `DEFAULT_POLYCHORD_SETTINGS` is `(6, 3, 12, 15.0)`; the messages equal the ones in `specs/042-polychord/contracts/polychord.md`.
- [X] T004 Create `backend/app/services/polychord.py` with the module docstring (what the picture is, the `Order of operations:` list written for the functions of this plan, see the data model) and the settings: constants (`MIN_NOTES = 5`, `MAX_NOTES = 8`, `MIN_COPIES = 1`, `MAX_COPIES = 12`, `MAX_ROTATION = 360`, the defaults, `COPY_TURN = 30`, `TURN_PER_STEP = 30`, the messages), `PolychordSettings` (frozen dataclass with an `Attributes:` block), `DEFAULT_POLYCHORD_SETTINGS`, `check_polychord_notes`, `check_polychord_copies`, `check_polychord_rotation`, `check_polychord_settings`; make T003 pass.
- [X] T005 Add `polychord.py` to `PROCESSING_MODULES` in `backend/tests/test_documentation.py` and run `test_type_hints.py` and `test_documentation.py` (they fail until the `Order of operations:` list exists and matches; keep the list a draft until Phase 5 and run them again then).

**Checkpoint**: the settings exist and are tested.

---

## Phase 3: User Story 1 - A figure drawn from the loudest notes, turning by the circle of fifths (Priority: P1) 🎯 MVP

**Goal**: for any frame of smoothed note values, the chain of links: the loudest letters, the turns, the tapering links as
pieces of a `LineCollection`, drawn on black.

**Independent Test**: from a hand-made array of note values, `figure_segments` gives links that start at the center, join end
to start and turn by the table; a picture made from them is black with lit pixels only where links are, inside the margins.

### Tests for User Story 1 (write first, see them fail)

- [X] T006 [P] [US1] `backend/tests/test_polychord.py` part 2, the letters: with an oracle that sorts by `(-value, note)` in a loop, `loudest_letters` gives the `count` loudest of the first 84 columns reduced to `note mod 12`, loudest first, ties to the lower note, `-1` for values not above 0 and for missing notes; a frame of zeros is all `-1`; columns 84 to 87 are never used; the input is not changed; the same letter in two octaves appears twice; refuses a wrong shape or a count outside 5 to 8.
- [X] T007 [P] [US1] `backend/tests/test_polychord.py` part 3, the turns: for all 12 letters after a C (and a spot check from other letters) `link_turns` gives 0, +30, +60, +90, +120, +150, +180, -150, -120, -90, -60, -30 in the order C, G, D, A, E, B, F#, C#, G#, D#, A#, F (an oracle written as a plain table of intervals in semitones, not with `ring_position`); the first link's turn is 0; a turn is measured from the previous link's letter, not the loudest; a `-1` letter gives 0 and ends the chain; the result is between -150 and +180 for every pair (all 144).
- [X] T008 [P] [US1] `backend/tests/test_polychord.py` part 4, the segments: with an oracle that walks the links one by one with `math.sin`/`math.cos`, `figure_segments` for one copy starts at `(width / 2, height / 2)`, each link's end is the next link's start, links have length `link_length`, the direction is the start angle plus the running sum of the turns, clockwise from straight up (`y` down); each link is 6 pieces; the widths of the pieces fall along the figure from `height / 60` to `height / 60 / 5` and the end width of the last piece of a link equals the start width of the first piece of the next (checked with the straight-line formula at the piece boundaries); never under 1 pixel; `n` links of fewer than `notes` still end at `W_END`; no letters gives zero pieces; for every size in (600, 400), (300, 200), (200, 600), (1800, 1200) and for random letters, every end point and every stroke edge (point +- width/2) is inside the picture by at least `MARGIN`.
- [X] T009 [P] [US1] `backend/tests/test_polychord_rendering.py` part 1, `_frame`: the picture is `(height, width, 3)` `uint8`, black (`(0, 0, 0)`) wherever no piece is, a frame with no letters is all black, the lit pixels are inside the margins, the lit pixels are all of the given color or a blend of it with black (antialiasing), the first link's start (the center) is lit, and drawing the same frame twice gives identical arrays.

### Implementation for User Story 1

- [X] T010 [US1] In `backend/app/services/polychord.py` implement `loudest_letters` (stable `argsort` of the negated first 84 columns, `-1` for values not above 0), `link_turns` (using `chromatic_decay.ring_position`, `((pos[b] - pos[a] + 5) % 12) - 5`, times 30), `link_length`, `figure_segments` (one copy first; the pieces and the widths of the data model) with full types and docstrings; make T006 to T008 pass.
- [X] T011 [US1] In `backend/app/services/polychord.py` implement `_frame` (the `Figure` and `FigureCanvasAgg`, the axes in pixels with `y` down, one `LineCollection` with the widths in points `pixels x 72 / 100`, round caps and joins, black figure; the color passed in) and `write_polychord_frames` for one copy and one fixed color for now (it is completed in US2); make T009 pass.

**Checkpoint**: from note values alone, the figure is drawn correctly (MVP of the picture, not yet wired to a job).

---

## Phase 4: User Story 2 - Copies turned 30 degrees, the beat, the rotation and the tempo color (Priority: P2)

**Goal**: the rosette: the number of copies from the beat, the starting angle from the rotation, the color from the tempo.

**Independent Test**: from a beat array, a tempo array and a rotation, the numbers of copies, the angles and the colors are as
specified, and the frames drawn from them show the copies, the turning and the color.

### Tests for User Story 2 (write first, see them fail)

- [X] T012 [P] [US2] `backend/tests/test_polychord.py` part 5, copies and angles: `copy_counts` with an oracle loop: the frame at the top of the beat of the file has the maximum, the bottom of the beat and every frame outside a peak the minimum, in between proportional and rounded with `floor(x + 0.5)`, `None` gives the minimum for `frames` frames (required then), minimum equal to maximum gives that number, always within bounds, refuses a beat outside 0 to 1; `start_angles` is `rotation x t / frame_rate` (a negative rotation, 0, 360 at 1 frame a second gives multiples of 360), consecutive frames differ by `rotation / frame_rate` to within 1e-9, refuses a frame rate that is not positive.
- [X] T013 [P] [US2] `backend/tests/test_polychord.py` part 6, tempos and colors: `frame_tempos` with a small `LocalPeaks` made by hand (or a fake with `peaks` and `file_rate`): 120 for every frame with no peak and before the first peak, the tempo after the latest peak at or before the middle of the frame afterwards (an oracle that loops over the moments and the `find_tempo` result), all between 60 and 156; `tempo_colors`: 60 gives the first row of the colormap, 156 the last, 108 the middle (row 128 by `rint`), a tempo outside 60 to 156 is held at the ends, a slower tempo never has a later row than a faster one for 60 to 156 in steps of 1, one color per frame, refuses an unknown colormap.
- [X] T014 [P] [US2] `backend/tests/test_polychord_rendering.py` part 2, the rosette: with copies 1 the lit pixels are a subset of those with copies 12; copy `k` is the figure turned `30 k` degrees (compare the segments of copy `k` with the segments of copy 0 rotated about the center by an independent rotation matrix); a frame with a larger copy count has strictly more lit pixels for a figure that does not overlap itself (two links, a fifth apart); the whole picture at rotation 30 degrees a second and frame rate 10 is the picture at rotation 0 turned 3 degrees (compare the segments, not the pixels); every lit pixel has the frame's tempo color (up to blending with black), and two frames with different tempos have different colors; `write_polychord_frames` saves `frame_000000.png` and up with the same bytes on two runs, and the files made by the thread pool equal the files made one at a time; it refuses a tempo array, a beat or note values with a different number of frames, a frame rate that is not positive, a colormap that does not exist, and a picture too small, before writing anything.

### Implementation for User Story 2

- [X] T015 [US2] In `backend/app/services/polychord.py` implement `copy_counts` (with `chromatic_decay.beat_distances`), `start_angles`, `tempo_colors` (with `colormaps.lookup_table`, `tempo_finder.LOW_LIMIT` and `HIGH_LIMIT`), `frame_tempos` (with `tempo_finder.find_tempo`, `START_TEMPO`, `numpy.searchsorted`), and the `PolychordData` dataclass (`tempos`, `frame_rate`, with an `Attributes:` block), fully typed and documented; make T012 and T013 pass.
- [X] T016 [US2] Extend `figure_segments` to all copies (copy `k` at `start + 30 k`, copy 0 first) and complete `write_polychord_frames(values, beat, tempos, settings, frame_rate, colormap, directory, width, height)`: check everything first, compute the letters, turns, copies, angles and colors once, then draw each frame in the worker pool (`frame_saving.SAVE_WORKERS`) and save `frame_<index>.png` as the other types do; make T014 pass; re-run T008 (the figure of one copy is unchanged).

**Checkpoint**: from values, a beat, tempos and settings, the whole picture sequence is made and saved.

---

## Phase 5: User Story 3 - Choosing it and the four settings (Priority: P3)

**Goal**: the type is selectable on the page and through the API, with its four settings, refused before the file is read,
and the other types untouched.

**Independent Test**: choose Polychord on the page and through `POST /api/jobs`; every setting at, below and above its limits;
a refusal leaves no files; frames and a movie are made; the frames of the other types equal the baseline.

### Tests for User Story 3 (write first, see them fail)

- [X] T017 [P] [US3] `backend/tests/test_polychord_api.py`: with the fixtures of `test_chromatic_wireframe_api.py` (a small generated wav, a temporary frames folder): a job with `image_type=polychord` and no new field makes the frames and answers with the defaults (`polychord_notes` 6, `polychord_min_copies` 3, `polychord_max_copies` 12, `polychord_rotation` 15.0); every one of the four fields at its lowest and highest allowed value is accepted and echoed; each field just outside its limits (4 and 9, 0 and 13, 0 and 13, -360.5 and 361), non-numbers, empty, `nan`, `inf` and a maximum under the minimum is a 400 with the exact message of `contracts/polychord.md`, **before the file is read** (a file that is not a wav gives the settings message and not the audio message) and with no folder left in the audio and frames temp folders; the four fields sent with another type are checked and ignored (an invalid one is refused, a valid one changes nothing in that type's frames); `threshold`, `decay_rate`, `note_layout` and `polar_notes` sent with Polychord are accepted and ignored; the number of frames and their size are those of the other types; the frames written equal what `write_polychord_frames` gives for the same inputs (the job measures the local peaks once: assert with a spy that `measure_local_peaks` is called once for this type); a movie can be made from the frames (as in the other types' tests).
- [X] T018 [P] [US3] Change the tests that spell out the list of image types so that they expect the ninth name and the new message `The image type must be one of contour, decay, decay-exp, polar-chords, energy-graphs, chromatic-decay, rhythm-circles, chromatic-wireframe, polychord.`: `backend/tests/test_image_types.py` (the `IMAGE_TYPES` tuple), `backend/tests/test_decay_api.py` and `backend/tests/test_polar_chords_api.py` (the message), add `polychord` to the parametrized lists of `test_image_type_api.py` (line 89) and `test_frame_size.py` (line 45); see them fail first.
- [X] T019 [P] [US3] `backend/tests/test_frame_rendering_polychord.py` (or a section of `test_polychord_rendering.py`): `write_frames(image_type="polychord", ...)` smooths the notes (a smoothing of 0.5 over a window of 2 changes the letters that sound in the frame after a loud one) and calls the drawing; it is refused without `polychord`, with tempos of the wrong length, and with settings that are not a valid `PolychordSettings`; the other types ignore `polychord` and `polychord_settings`; its output equals `write_polychord_frames` called on `smooth_frames` of the same values.
- [X] T020 [P] [US3] Frontend tests, written first and failing: `frontend/src/utilities/validation.test.ts` (the four validators and the option `polychord` in the image types, the messages mirror the backend), `frontend/src/utilities/groups.test.ts` (the groups shown for `polychord`: the polychord group and the Local peaks group, not Threshold or Decay rate), `frontend/src/components/SettingsForm.test.ts` (the option, the four controls with their defaults, their errors, the submit disabled for a bad value, the values sent as `polychord_notes`, `polychord_min_copies`, `polychord_max_copies`, `polychord_rotation`), `frontend/src/api.test.ts` (the fields appended to the request body, and in the result type), `frontend/src/App.test.ts` (the result list shows them for this type only), `frontend/src/utilities/help.test.ts` (the help texts exist).

### Implementation for User Story 3

- [X] T021 [US3] `backend/app/services/image_types.py`: add `"polychord"` to `IMAGE_TYPES` (last), update the docstring (nine kinds, the sentence for `polychord`) and add the **polychord block** to the `Pipeline overview:` (MEASURE: BEAT and tempo from one local-peaks measurement; the DRAW steps in order: `polychord.loudest_letters()`, `link_turns()`, `copy_counts()`, `tempo_colors()`, `figure_segments()`, `write_polychord_frames()`), keeping the layout of the other blocks and the 120-column width; make T018 (the `image_types` part) pass.
- [X] T022 [US3] `backend/app/services/frame_rendering.py`: add `polychord: PolychordData | None = None` and `polychord_settings: PolychordSettings = DEFAULT_POLYCHORD_SETTINGS` to `write_frames`, document them (`Arrays:`/`Attributes` lines, the docstring paragraph for the type, the module docstring's list), check them (required for this type: tempos have one value per frame, `check_polychord_settings`), and add the `polychord` branch after `smooth_frames` (before the final contour branch) that calls `write_polychord_frames(smoothed, beat, polychord.tempos, polychord_settings, polychord.frame_rate, colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT)`; make T019 pass; the other branches are not touched.
- [X] T023 [US3] `backend/app/routers/jobs.py`: four `Form` fields and `_parse_polychord_*` functions (not sent means the default; refused with the messages of the contract; the maximum-under-minimum check after both), all parsed before the file is read; for `polychord` measure the local peaks **once** and derive `beat = peaks.frame_positions(fps, frames)` and `polychord = PolychordData(frame_tempos(peaks, fps, frames), fps)`; pass `polychord` and `polychord_settings` to `write_frames`; echo the four values in the response; update the comments that list the types that measure the beat; make T017 and the rest of T018 pass.
- [X] T024 [P] [US3] `frontend/src/utilities/validation.ts` and `frontend/src/utilities/help.ts`: the option `{ value: "polychord", label: "Polychord" }`, the four ranges and defaults, the four validators with the messages of the backend, the help texts (what the notes, the copies and the rotation do; that the tempo sets the color and the beat the copies).
- [X] T025 [US3] `frontend/src/utilities/groups.ts`, `frontend/src/components/SettingsForm.vue`, `frontend/src/api.ts` and `frontend/src/App.vue`: the `polychord` group with its four controls (number of notes, copies minimum, copies maximum, rotation) shown for this type only together with the Local peaks group, the type in `TYPE_GROUPS` / `TYPE_GROUP_IDS`, the settings in the request body and in the result type, and a line in the result list for this type; make T020 pass.

**Checkpoint**: Polychord can be chosen, made and played; the other types are as before.

---

## Phase 6: Polish and cross-cutting

- [X] T026 [P] Documentation: the README (the image type, its four settings, what the picture shows), the help text if not done in T024, and `specs/041-code-readability-docs/contracts/documentation-standard.md` is not changed.
- [X] T027 Documentation standard: run `test_type_hints.py` and `test_documentation.py` (the `Order of operations:` list of `polychord.py` is finished and true: compare it with the real order of the calls with `specs/041-code-readability-docs/tools/trace_pipeline.py` if it supports the new type, or by reading), check that the new aliases are used and that every line of comment and docstring in the changed files is at most 120 columns.
- [X] T028 Mutation check of the new tests: temporarily change, one at a time, the turn per step (30 to 29), the sign of the turn, the tritone's 180, the order of the letters, the rounding of the copy count, the beat distance (use the raw position), the tempo bounds (60 or 156), the start angle (`t` to `t + 1`), the end width of a piece, the number of pieces, the position of the first link (not the center), the margin; each must fail at least one test; put each change back.
- [X] T029 Run the whole backend suite and `verify_frames.py`: only the 25 baseline tests fail and all 540 frames of the other types are identical to the baseline; run `npm run test` in `frontend` (all pass) and `npm run build` or the type check of the frontend if the project has one.
- [X] T030 Run the quickstart: make frames and a movie from `backend/audio/sonata.wav` and `almost2.wav` through the API (look at some frames: arms open on the beat, one color a frame, almost2 later in the colormap than sonata, rotation 0 and -15, notes 5 and 8, copies 12 and 12), and record what was seen and the time a three-minute file takes.

---

## Dependencies & Execution Order

- **Phase 1** first (T001 before any edit). **Phase 2** needs T002. **US1** needs Phase 2; **US2** needs US1 (`figure_segments`, `_frame`); **US3** needs US2 for T022/T023 (the library), but its tests (T017 to T020) and the frontend work (T024, T025) can start after Phase 2. **Phase 6** last.
- Within a story: tests, see them fail, then the code. `polychord.py` is one file: its tasks (T004, T010, T011, T015, T016) are sequential; test files differ, so T006 to T009, T012 to T014 and T017 to T020 are parallel to each other where marked [P] (T006 to T008 and T012, T013 share `test_polychord.py`: write them one after the other, they are independent in content).
- The frontend tasks T024 and T025 are independent of the backend tasks T021 to T023 (they share only the field names).

## Parallel example

```text
# After T005: the tests of US1 together (different files / independent parts)
T006 loudest_letters   T007 link_turns   T008 figure_segments   T009 _frame

# After T020: backend and frontend in parallel
T021 T022 T023 (backend)        T024 T025 (frontend)
```

## Implementation Strategy

1. **MVP**: Phases 1 to 3: the figure from the loudest notes, correct and tested, drawn from the library.
2. Add US2: the copies, the rotation and the tempo color: the whole picture sequence.
3. Add US3: the job, the four settings and the page: usable by the user.
4. Polish: documentation, the standard, mutation check, the whole suite and the frames of the other types, the quickstart.

## Notes

- Baseline recorded in T001 (2026-11-15): the whole suite gave 4706 passed and 25 failed, the same 25 as `baseline-failures.txt`, run just before this feature (after the 120-column rewrap and the repair of the `image_types.py` overview, whose only change since is documentation); `verify_frames.py`: all 540 frames identical.
- The spec's three readings are fixed: link = a straight piece; copy = a repeat of the figure; one color a frame from the tempo (option A).
- Nothing is committed by these tasks; the working tree already has the uncommitted work of features 040 and 041.
