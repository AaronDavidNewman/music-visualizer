---

description: "Task list for Polar Chords (feature 032)"
---

# Tasks: Polar Chords

**Input**: Design documents from `/specs/032-polar-chords/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/polar-chords.md, quickstart.md

**Tests**: Written first for each story (the project's practice): the bars as numbers (with an independent calculation of the places and roots), the picture at the pixel level (the angle, the width, the tip and the color of each bar), the API, and the page's group, slider, summary and request (server-side rendering and source guards, as in features 025 to 030). The look in the player is the manual step of the quickstart.

**Revised 2026-11-06**: the Note layout (rows or spiral) was added to Polar Chords at the user's request (see the spec): `polar_bars(..., note_layout)`, the layout passed from `write_frames`, `noteLayoutApplies` true for the type, the Note layout group shown, tests for all of it. Where a task below says that the Note layout does not apply, this replaces it.

**Revised 2026-11-07 (fourth change)**: the chord ring has 84 arcs again: `7 × root letter + type`, the root being the letter of the lowest recorded note less the chord tone in the bass (`chord_root`); `CHORD_ARCS = 84`, `CHORD_ROOTS = 12`, `chord_place(chord_type, root)`, the chord arcs of the drawing are `360 / 84` degrees wide. Done test first (the place tests, the exhaustive 7 types × 12 roots × inversions check against the independent oracle and a root found from the chord tones, the rendering and API tests with the new arcs); 12 mutants of the root and the place all caught. This replaces the second change below.

**Revised 2026-11-06 (second change)**: the chord ring has 7 arcs, one for each chord type, with no root (see the spec): the place of a chord is the index of its type, `chord_root` is gone, `CHORD_ARCS = 7`, the chord arcs of the drawing are `360 / 7` degrees wide. Where a task below speaks of 84 chord places, of `type x 12 + root` or of the root, this replaces it.

**Revised 2026-11-06 (third change)**: the note bars follow their notes, one arc a frame (see the spec, FR-014 and FR-015): `note_targets`, `follow_arcs`, `polar_bars` hiding a covered bar, tests for the movement, the wrap-around, the silent volume, the covered bar and a tone that jumps. Where a task below says that a note bar is in the arc of its note in every frame, this replaces it.

**Organization**: By user story: US1 the note ring (P1), US2 the chord ring (P1), US3 the setting, the API and the page (P2), US4 the quiet and odd moments (P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- Paths are from the repository root. Edit files with their line endings preserved. Backend tests run from `backend/` (`.venv` active), frontend tests from `frontend/`. **Run mutation checks with `python -B` and clear the `__pycache__` folders afterwards** (a mutation of the same size can otherwise leave stale bytecode that is tested in place of the restored source).

---

## Phase 1: Setup

- [x] T001 Record the baseline before changing anything: `python -m pytest -q` in `backend/` and `npm test`, `npm run build` in `frontend/`, and note the counts (the last known: backend 5871 passed, frontend 773 passed). List the tests that name the image types or list the response keys, which will need `polar-chords` and `polar_notes` added: `grep -rn "decay-exp" backend/tests frontend/src` and `grep -rln "decay_low" backend/tests`. Read `backend/app/services/concentric.py` (`full_radius`, the middle color row, the saving on a thread pool), `backend/app/services/colormaps.py` (`check_beat`, `lookup_table`, `check_colormap`) and `backend/app/services/chords.py` (`measure_chords`, `ChordRecord`) to reuse them.

---

## Phase 2: Foundational: the setting and the image type name

**Purpose**: Every story needs the type registered, the Notes shown check and the module.

### Tests (write first, they fail)

- [x] T002 [P] Create `backend/tests/test_polar_chords.py` with the helpers used by all later tests (a `smoothed(**rows)`/`frames(...)` builder of `(F, 88)` arrays from `{note: strength}` rows; the note numbers `A1 = 0`, `C3 = 15`, `C4 = 27`, `E4 = 31`, `G4 = 34`, `C5 = 39`) and the tests for the setting (spec FR-010, data-model "Settings"): `check_polar_notes` accepts 5, 6, 7, 8 and `5.0`, `np.int64(6)` (returned as an `int`); refuses 4, 9, 0, -5, 6.5, `True`, `"6"`, `None`, `nan`, `inf`, `[6]` with `ValueError` and the message `The number of notes shown must be a whole number from 5 to 8.`; the constants `MIN_POLAR_NOTES = 5`, `MAX_POLAR_NOTES = 8`, `DEFAULT_POLAR_NOTES = 5`, `ARCS = 84`, and `POLAR_CHORD_TYPES == ((7,), (4, 7), (3, 7), (4, 10), (4, 11), (3, 7, 10), (4, 6))`; `IMAGE_TYPES[-1] == "polar-chords"` and `len(IMAGE_TYPES) == 9`.

### Implementation

- [x] T003 Create `backend/app/services/polar_chords.py` (module docstring: what the picture is, the two rings and their directions, the 84 arcs, the 7 chord types and the place formula, the length and color rules, that the bars are worked out first apart from the drawing, and that it knows nothing about audio, the router or the beat measurement). In this task only: the constants `ARCS = 84`, `MIN_POLAR_NOTES = 5`, `MAX_POLAR_NOTES = 8`, `DEFAULT_POLAR_NOTES = 5`, `POLAR_CHORD_TYPES`, `MIN_LENGTH = 0.5`, `MARGIN = 10`; `check_polar_notes(value) -> int` (a whole number 5..8; booleans, fractions, strings and non-finite refused; the message of the contract); the `PolarBars` frozen dataclass (fields of the data model: `note_slots`, `note_shares`, `chord_place`, `chord_share`, `length`) with `frame_count`. In `backend/app/services/image_types.py`: `"polar-chords"` last in `IMAGE_TYPES` and a ninth sentence in the module docstring. Run T002 and fix.

**Checkpoint**: The type name and the setting exist.

---

## Phase 3: User Story 1 - The loudest notes as bars around a circle, pulsing with the beat (Priority: P1) 🎯 MVP

**Goal**: The note ring: `polar_bars` for the notes and the length, `write_polar_frames` drawing them, and `write_frames(image_type="polar-chords", polar_notes=...)`.

**Independent Test**: `write_frames(values, ..., image_type="polar-chords", beat=...)` with one steady loud note and a pulse: one wedge at the note's angle, 4.29° wide, the tip moving between half and all of the radius.

### Tests for User Story 1 (write first, they fail)

- [x] T004 [P] [US1] Add to `backend/tests/test_polar_chords.py` the tests of the note bars (spec User Story 1, FR-003, FR-004, FR-007, FR-008 for notes, SC-001/SC-002 for notes) on `polar_bars(smoothed, beat, count)` with `count` 5 to 8: the loudest `count` notes of every frame get a slot (their note number 0 to 83), loudest first; with fewer sounding notes the other places are -1 and have share 0; a note with strength 0 never has a bar; ties go to the lower note (five equal notes and `count=5` use the five lowest); the 4 extra columns (84 to 87) never get a bar; `count` outside 5..8 is refused with the message; the strength share is `sqrt(value / peak)` with `peak` the largest value of the whole array including the columns 84 to 87, in 0..1, and 0 when the peak is 0; the length is `0.5 + 0.5 × position` for each frame: 0.5 with no beat, 1.0 at position 1, 0.75 at 0.5; the beat is checked (`check_beat`: a bad length or range refused with its message); the input is not changed; two runs equal; the shapes and dtypes of the data model. Create `backend/tests/test_polar_chords_rendering.py` (spec User Story 1 and Edge Cases) with helpers that read the pixel at a given angle (clockwise from straight up) and radius from a written frame (`center = (300, 200)`, `R = 190`), and the tests for the notes: one PNG per frame, 600 × 400 RGB, named from `frame_000000.png`; the background (a corner pixel, and a pixel outside the circle) is the colormap's middle color (table row 128) for every colormap; for several notes (0, 1, 27, 42, 83) the pixel at the middle angle of the note's arc `(note + 0.5) × Δ` and a radius of 0.3 × `R` is the note's color (table row `rint((0.5 − 0.5 × s) × 255)`), and the pixels at the middle angles of the arcs next to it are the background; the pixel just inside each side of the arc (a quarter of an arc from the middle) is the bar's color and just outside (a quarter of an arc beyond the edge) is not; the tip: along the middle angle the bar's color ends at `(0.5 + 0.5 × p) × R` within a pixel, for positions 0, 0.25, 0.5, 1; neighbouring notes (both among the loudest) touch with no gap and no seam (the pixels at the common edge are a mix of the two colors, never the background); all the bars of a frame have the same length; the bar fills the arc from the center (a pixel at a radius of 3 pixels at the note's angle is the bar's color); the first note's arc starts straight up and goes to the right (the pixel just right of up at 0.3 × `R` is the first note's color) and the last note's arc ends straight up (just left of up); the colors for the quietest and the loudest possible strengths are the middle color and the colormap's first color; `write_frames(..., image_type="polar-chords")` equals `write_polar_frames(polar_bars(...))` byte for byte; the settings that do not apply (`note_layout`, `threshold`, `note_count`, `resolution`, `interpolate`, `gaussian`, `blend_width`, the circle, decay and wave settings) are accepted and change no byte; a bad `polar_notes` or `decay_rate` is refused before anything is written, for every image type; `polar_notes` has no effect on the other eight types.

### Implementation for User Story 1

- [x] T005 [US1] In `backend/app/services/polar_chords.py` (research Decisions 1, 2, 4 and 5): `polar_bars(smoothed, beat=None, count=DEFAULT_POLAR_NOTES)` for the notes and the length (a stable `argsort` on the negative strength of columns 0 to 83, the first `count`, those with strength above 0; shares from `sqrt(value / peak)`; lengths from `check_beat`; the chord fields as `-1` and `0` until Story 2); `_geometry(width, height)` cached with `lru_cache`: the center `((width) / 2, (height) / 2)`, `R = min(width, height) / 2 − MARGIN`, for every pixel within `R + 1` of the center the distance, the clockwise angle from straight up `atan2(dx, −dy)` in `[0, 2π)`, the note arc `⌊angle ÷ Δ⌋`, the chord arc `⌊(2π − angle) ÷ Δ⌋ mod 84`, and for each kind the neighbouring arc and its share `clip(0.5 − d, 0, 1)` with `d = min(f, 1 − f) × Δ × distance` and `f` the fraction of the arc already passed; per arc the pixel indices where it is the own arc (weight `1 − share`) and where it is the neighbour (weight `share`), with the distances; `write_polar_frames(bars, colormap, directory, width, height)` checks the colormap and the bars, makes the directory, and for each frame (on a thread pool saving with `compress_level=1`, reusing `_SAVE_WORKERS` of `circles.py`) builds `alpha` and premultiplied `color` arrays on the pixels of the frame's bars only (coverage `clip(length × R − distance + 0.5, 0, 1)`, the own and the neighbour pixels summed with their weights), composites over the background (row 128 of the table) and rounds to `uint8`; colors from `lookup_table` rows `rint((0.5 − 0.5 × s) × 255)`. In `backend/app/services/frame_rendering.py`: import `check_polar_notes`, `polar_bars`, `write_polar_frames`, `DEFAULT_POLAR_NOTES`; `write_frames(..., polar_notes=DEFAULT_POLAR_NOTES)`; `polar_notes = check_polar_notes(polar_notes)` with the other checks; the beat is checked for every type already; a branch `if image_type == "polar-chords":` after the Decay Exp one that calls `write_polar_frames(polar_bars(smoothed, beat, polar_notes), colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT)` and returns; update the docstring and the comment at the `check_beat` line. Run T004 and fix.
- [x] T006 [US1] Mutation checks (as the earlier features; `python -B`, clear `__pycache__`), each caught by the tests and restored byte for byte (`cmp` with a copy): the arc width 85 or 83 arcs; the notes counterclockwise; the angle measured from the right instead of from the top; ties to the higher note; a silent note getting a bar; the columns 84 to 87 in the ranking or missing from the peak; the share without the square root; `0.5 + 0.5 × s` instead of `0.5 − 0.5 × s` for notes; the length `0.5 + p` or `p` or `1 − 0.5 × p`; the tip offset `+ 0.0` or `+ 1.0`; bars not filling to the center; the neighbour share 0 (hard edges) or 1; the background not row 128; `count` not used; the beat ignored.

**Checkpoint**: The note ring can be drawn through `write_frames`; everything else is unchanged.

---

## Phase 4: User Story 2 - The chord as a bar going the other way round (Priority: P1)

**Goal**: The chord ring: the recorded chord of every frame as one bar in its place, counterclockwise, with the colors of the second half of the colormap, over the notes.

**Independent Test**: A C major triad in any inversion and octaves gives the chord bar at place 15, 64.3° counterclockwise from the top.

### Tests for User Story 2 (write first, they fail)

- [x] T007 [P] [US2] Add to `backend/tests/test_polar_chords.py` the tests of the chords (spec User Story 2, FR-005, FR-006, SC-003): `chord_root(chord_type, inversion, notes)` against an **independent calculation** written in the test (the root is the chord tone that is `inversion` places up in the chord, found by playing: for each of the 7 types, each inversion, several octave placements and each of the 12 roots build the sounding notes from the root letter by adding the intervals, rotate to the inversion, and check that `chord_root` gives back the root letter); `chord_place(chord_type, root) == POLAR_CHORD_TYPES.index(chord_type) × 12 + root`, 0 to 83, all 84 places distinct and covered by the 7 × 12 chords; worked examples: C4 E4 G4 (27, 31, 34) gives `(4, 7)` root 3 place 15, E4 G4 C5 the same, G4 C5 E5 the same; C4 and G4 `(7)` root C place 3; C4 and F4 `(7)` inversion 1 root F (8) place 8; A1 and E2 `(7)` root A place 0; and in `polar_bars`: for each of the 7 types × 12 roots × every inversion × 3 octave placements (a seeded random choice, notes within 0..83 and loud, 2 to 4 of them), `chord_place` of the frame is the place of that type and root and no other (but where the measurement of feature 031 records a different type of the seven because of its rules (the longest, then the widest), the test follows the rule: compute the expected type with an independent brute-force oracle written in the test); a frame with no chord among the seven (a minor second, a diminished triad, C and F# `(6,)` is not one of the seven) has place -1 and share 0; the chord strength share is `sqrt(mean of the values of the chord's notes ÷ peak)`; the chord is found with no limits, on all 84 notes; the notes of a recorded chord are all among the drawn note bars (`count` 5 or more); the places are the same in every frame that has the same chord; two runs equal. In `backend/tests/test_polar_chords_rendering.py`: the chord bar is at place `p`: the pixel at the middle angle `360° − (p + 0.5) × Δ` (clockwise from the top) at 0.3 × `R` is the chord's color (table row `rint((0.5 + 0.5 × s) × 255)`) for several places (0, 1, 15, 42, 83), and the pixels of the arcs next to it are the background; place 0 starts straight up and goes to the **left**; the tip length is the same as the note bars'; the chord bar is drawn over a note bar that covers the same angles (put a note and a chord at the same angle: the pixel is the chord's color); the chord color is the second half of the colormap and the note colors the first half for a diverging colormap (for every colormap offered: the note row ≤ 128 and the chord row ≥ 128); no chord, no chord bar (the frame is the same as the note bars alone); a frame with a chord differs from the same frame without it only in the chord's arc.

### Implementation for User Story 2

- [x] T008 [US2] In `backend/app/services/polar_chords.py`: `chord_root(chord_type, inversion, notes) -> int` (`(notes[0] − (0, *chord_type)[inversion]) % 12`), `chord_place(chord_type, root) -> int`; in `polar_bars` run `chords.measure_chords(smoothed[:, :88], POLAR_CHORD_TYPES)` once for the whole file (no limits), then for every window with a record the place, and the share `sqrt(mean(smoothed[frame, notes]) ÷ peak)` (0 if the peak is 0); in `write_polar_frames` the chord bar over the note bars with the colors `rint((0.5 + 0.5 × s) × 255)` using the chord geometry (research Decision 4). Run T007 and fix.
- [x] T009 [US2] Mutation checks (as T006), each caught: the place `root × 7 + type`; the root as the bass note; the root taken from the folded notes; the inversion ignored in the root; the chord arc clockwise; type order changed; chord color `0.5 − 0.5 × s`; the mean replaced by the maximum or by the first note; the chord drawn under the notes; the chord length different from the notes'; a chord bar drawn when there is no record; the chord measurement limited (a note count or threshold given); the chord types list changed by one interval.

**Checkpoint**: Both rings are drawn; `polar-chords` frames can be made through `write_frames`.

---

## Phase 5: User Story 3 - Choose Polar Chords on the page and set Notes shown (Priority: P2)

**Goal**: The `polar_notes` field of the job request (and `image_type=polar-chords`), and the page's Polar chords group with the slider, the request and the summary.

**Independent Test**: Post a WAV with `image_type=polar-chords&polar_notes=7`: 200, both echoed, 600 × 400 frames; on the page choosing Polar Chords shows the groups Analysis, Colormap, Image type, Polar chords, Local peaks (no checkbox) and Data smoothing.

### Tests for User Story 3 (write first, they fail)

- [x] T010 [P] [US3] Backend API tests. Create `backend/tests/test_polar_chords_api.py` (spec User Story 3, FR-001, FR-009 to FR-011), in the style of `backend/tests/test_decay_exp_api.py`: `image_type=polar-chords` accepted and echoed with 200 for every colormap; the frames are 600 × 400 and their count is that of the other types; `polar_notes` not sent gives 5; 5, 6, 7, 8 and `" 6 "` accepted and echoed as numbers; `4`, `9`, `6.5`, `abc`, empty, `nan`, `inf`, `-5`, `1e1` refused with 400 and `The number of notes shown must be a whole number from 5 to 8.` **before the file is read** (a request with no file); a bad image type (also `polar_chords`, `polarchords`, `Polar-Chords`) is refused with the nine names; the Local peaks values are checked with the messages of the measurement before the file is read, and the beat is measured for every `polar-chords` job whatever `beat_coloring` says (use the `measured` fixture technique of `test_decay_exp_api.py`); `polar_notes` sent with another image type is accepted, echoed and has no effect (the frames are byte-identical to those without it); `polar_notes` changes the frames of a file with many notes; `note_layout`, `threshold`, `note_count`, `resolution`, `interpolate`, `gaussian`, `blend_width`, `beat_coloring`, the circle, wave and decay fields are validated as before and ignored (byte-identical frames); the smoothing applies; two runs give identical frames; a steady tone gives one note bar at its angle (find the angle of the bar from the served PNG), a silent file gives the background only, a file with no beat has bars at half the radius, a file shorter than the peaks window works. Update the existing tests that name the nine image types or list the response keys (the files found by the grep of T001): `polar-chords` appended to the lists and parametrizations of image types (`test_circles_api.py`, `test_concentric_api.py` including `TYPE_MESSAGE`, `test_contour_beat_wave_api.py`, `test_decay_api.py`, `test_decay_rendering.py`, `test_decay_exp_api.py`, `test_note_layout_api.py`, `test_note_layout_rendering.py`); `polar_notes` added to the exact lists of response keys (`test_circles_api.py`, `test_colormap_api.py`, `test_contour_api.py`, `test_interpolation_api.py`, `test_resolution_api.py`, `test_note_count_api.py`); check that the pictures' reference hashes in the existing tests are unchanged.
- [x] T011 [P] [US3] Frontend tests (vitest), written first: in `frontend/src/utilities/validation.test.ts` — `IMAGE_TYPES` has nine entries with `polar-chords` labelled "Polar Chords" last, the image type message lists the nine, `imageTypeLabel("polar-chords")`; `POLAR_NOTES_RANGE` is 5 to 8 step 1, `DEFAULT_POLAR_NOTES` 5; `validatePolarNotes` accepts 5 to 8 (numbers and numeric strings) and refuses 4, 9, 6.5, "", "abc", NaN with `The number of notes shown must be a whole number from 5 to 8.`; `formatPolarNotes(5)` is `5 notes`; `isPolarType` is true for `polar-chords` only; `gridSettingsApply("polar-chords")` is false; `noteLayoutApplies("polar-chords")` is false; `isRingsType("polar-chords")` is false; `beatColoringApplies("polar-chords")` is false; `peakSettingsShown("polar-chords", box)` is true for both values of the box; `decayRateApplies`, `waveCountApplies` are false for it. In `frontend/src/utilities/groups.test.ts` — `GROUPS` has the new group `{ id: "polar-chords", title: "Polar chords", controls: ["polar-notes"] }` (sixteen groups); `groupsFor("polar-chords")` is `["analysis", "colormap", "image-type", "polar-chords", "concentric-peaks", "data-smoothing"]`; `groupOf("polar-notes", type)` is "polar-chords" for it and undefined for every other type; `groupOf("note-layout", "polar-chords")`, `groupOf("threshold", ...)`, `groupOf("decay-rate", ...)` are undefined; the groups of the other eight types are unchanged; the `EXPECTED` controls of the type. In `frontend/src/utilities/help.test.ts` — `polarNotesHelp` exists and mentions the range 5 to 8 and "loudest"; `imageTypeHelp` has a "Polar Chords:" sentence that mentions the two rings, clockwise and counterclockwise, the 7 chord types and that the length follows the beat. In `frontend/src/api.test.ts` — the request body has `polar_notes` as text and `image_type=polar-chords` when chosen. In `frontend/src/components/SettingsForm.test.ts` and `frontend/src/App.test.ts` (server-side rendering and source guards in the style of the earlier tests) — the dropdown lists the nine types; `TYPE_GROUP_IDS` has `"polar-chords"`; choosing Polar Chords shows the Polar chords group with the slider `polar-notes` (min 5, max 8, step 1, value 5, a label "Notes shown" and an info button with `polarNotesHelp`), the Local peaks group with Minimum distance and Prominence and no Beat coloring checkbox, and does not show the Note layout group, Threshold, Notes, Oversampling, Interpolate, Gaussian, the decay or wave sliders; the other types do not show the slider; a bad value marks the group as having a problem and disables Create frames and the request carries `polarNotes`; the summary of a Polar Chords result lists "Notes shown: 5 notes", Minimum distance and Prominence and none of Note layout, Threshold, Notes, Interpolate, Oversampling, Gaussian smoothing, Beat coloring or the decay lines. Update the existing tests that list the image types, the groups or the sixteen/fifteen group count.

### Implementation for User Story 3

- [x] T012 [US3] Backend wiring. In `backend/app/routers/jobs.py`: `_parse_polar_notes(text, sent)` in the style of `_parse_circle_notes` (not sent gives `DEFAULT_POLAR_NOTES`; a whole number 5..8, else 400 with the message of the contract); the form field `polar_notes: str | None = Form(None)` parsed with the other fields before the file is read; the beat is measured when `image_type_value in ("concentric", "decay", "decay-exp", "polar-chords")` or the tiles/blended/contour rule as before (update the comment); `polar_notes=polar_notes_value` passed to `write_frames`; `"polar_notes": polar_notes_value` echoed in the response. Check that no other place in `backend/app` compares the image type with a list of names. Run T010 and fix.
- [x] T013 [US3] Frontend wiring. In `frontend/src/utilities/validation.ts`: `{ value: "polar-chords", label: "Polar Chords" }` last in `IMAGE_TYPES` (update its comment); `POLAR_NOTES_RANGE`, `DEFAULT_POLAR_NOTES`, `validatePolarNotes`, `formatPolarNotes`, `isPolarType`; `gridSettingsApply` false and `peakSettingsShown` true for it (`gridSettingsApply` is `!isCirclesType && !isRingsType && !isPolarType`; `peakSettingsShown` is rings or polar or the beat-coloring rule); `noteLayoutApplies` unchanged (it must stay false for Polar Chords; check that it does not go through `gridSettingsApply`). In `frontend/src/utilities/groups.ts`: the group `{ id: "polar-chords", title: "Polar chords", controls: ["polar-notes"] }`, `"polar-chords"` in `TYPE_GROUPS`, the `concentric-peaks` group for it (`groupsFor` adds it when the type is rings or polar), no `note-layout`, no `image-smoothing`. In `frontend/src/components/SettingsForm.vue`: `polarNotes` ref, the error computed, the problem marker `(inTypeGroup("polar-notes") && !!polarNotesError.value)`, the disabled state, the slider (id `polar-notes`, label "Notes shown", output `5 notes`, info button), `"polar-chords"` in `TYPE_GROUP_IDS`, `polarNotes` in the request. In `frontend/src/api.ts`: `polarNotes` in `JobSettings`, `polar_notes` in `JobResult`, `body.append("polar_notes", String(settings.polarNotes))`. In `frontend/src/App.vue`: the summary line `Notes shown: {{ formatPolarNotes(result.polar_notes) }}` for `isPolarType(result.image_type)`. In `frontend/src/utilities/help.ts`: `polarNotesHelp` and the "Polar Chords:" sentence in `imageTypeHelp`. Run T011 and fix; `npm run build` passes.

**Checkpoint**: Polar Chords can be chosen on the page and made through the API; the other types are unchanged.

---

## Phase 6: User Story 4 - Quiet, silent and beat-less moments look sensible (Priority: P3)

**Goal**: The corner cases of the spec behave as written.

**Independent Test**: A silent file gives the background only; one steady note gives one bar; a steady chord with no beat gives bars of half the radius.

- [x] T014 [US4] Add to `backend/tests/test_polar_chords.py` and `test_polar_chords_rendering.py` (spec User Story 4, SC-004), then fix `polar_chords.py` if any fails: a silent file gives frames that are the background only (every pixel the middle color) and no slots and no chord; a frame with 3 sounding notes and `polar_notes=5` has 3 note bars; a frame with one sounding note has one note bar and no chord bar; no beat gives length 0.5 for all frames and bars of half the radius; a faint bar (share near 0) is nearly the background color (its table row within a few of 128); the last note's arc and the first note's arc, and chord place 83 and place 0, meet at the top with no gap and no overlap; a file shorter than the peaks window works through `write_frames` and the API; an `(F, 84)` array (without the four extra columns) works for the bars; zero frames give no files; all 84 notes loud at once with `polar_notes=8` draws 8 bars and one chord at most; the bars of a frame do not depend on the neighbouring frames.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T015 [P] Documentation: a paragraph in `README.md` after the Decay Exp one: Polar Chords (`polar-chords`, `backend/app/services/polar_chords.py`), the two rings and their directions, the 84 arcs from the top, Notes shown 5 to 8 (request field `polar_notes`, checked for every image type, the message), the 7 chord types and the place `type × 12 + root` with the root letters from A, the length `0.5 + 0.5 × p` of the full radius from the beat, the colors (notes from the middle toward the start of the colormap, the chord toward the end), the chord measurement of feature 031 being used, the settings shown and the ones that are ignored, and that the other eight pictures are unchanged. Check `specs/032-polar-chords/quickstart.md` still matches what was built and fix it where it does not.
- [x] T016 Run the whole suite and the manual quickstart: clear the `__pycache__` folders, then `python -m pytest -q` in `backend/` (all pass: the baseline of T001 plus the new tests), `npm test` and `npm run build` in `frontend/` (all pass); `git status` shows only the intended files; time the frames of 1,800 frames (a 60 second file at 30 frames a second) for Polar Chords and Concentric and report the numbers against SC-006; quickstart scenarios 1 to 6 as far as they can be done by script (state which ones were not watched in the player). Tick the boxes of this file.

---

## Dependencies & Execution Order

- Phase 1 first. Phase 2 (T002 then T003) before the stories (the module and the type name).
- US1 (T004 to T006) is the MVP: the note ring through `write_frames`. US2 (T007 to T009) adds the chord to the same module and drawing. US3 (T010 to T013) needs `write_frames` from US1 (and US2 for the chord in the API tests). US4 (T014) needs US1 and US2.
- T010 and T011 are [P] (backend and frontend tests); T012 and T013 are independent of each other.
- Polish after the stories: T015 [P], then T016.

```text
T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → ┬→ T010 → T012 ┐
                                                                └→ T011 → T013 ┴→ T014 → T015 → T016
```

## Parallel Example: User Story 3

```text
Task: "T010 backend API tests (backend/tests/test_polar_chords_api.py + the existing tests naming the types)"
Task: "T011 frontend tests (validation, groups, help, api, SettingsForm, App)"
then
Task: "T012 jobs.py"      Task: "T013 frontend wiring"
```

## Implementation Strategy

1. **MVP**: Phases 1 to 3: the note ring in the module and through `write_frames`.
2. Add Phase 4 (the chord ring), then Phase 5 (the API and the page), then Phase 6 (the quiet cases).
3. Polish: the README and the full run with timings.
4. Stop at each checkpoint to run the whole suite: the other eight image types must stay byte-identical.
