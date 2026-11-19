---

description: "Task list for 044-sustained-loudest-notes"
---

# Tasks: Sustained loudest notes

**Input**: Design documents from `/specs/044-sustained-loudest-notes/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/job-api.md](contracts/job-api.md), [quickstart.md](quickstart.md)

**Tests**: The plan and the constitution require them (the quickstart names the test files), so test tasks are included.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root. Run backend commands from `backend/` with `.venv/Scripts/python.exe` (`python` is not the project's interpreter) and frontend commands from `frontend/`.

**Environment note**: the PowerShell scripts in `.specify/scripts` cannot run on this machine (execution policy): do not depend on them. Write scripts for edits to the scratchpad directory, not the project.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1 to US4 as in the spec

---

## Phase 1: Setup (baselines, before the first edit of `backend/app` or `frontend/src`)

- [X] T001 Run the whole backend suite (`.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider -rf` in `backend/`; about 10 minutes, run it in the background) and save the failing test ids (the lines starting `FAILED`, without the text after ` - `, sorted) to `specs/044-sustained-loudest-notes/baseline-failures-before.txt`; they must be the 32 ids of `specs/043-decouple-frame-rate/baseline-failures-after.txt` (compare with `comm`); do not fix them
- [X] T002 [P] Run `backend/.venv/Scripts/python.exe specs/043-decouple-frame-rate/tools/verify_drawing.py` from the repository root: it must say `all frames identical to the baseline` (9 image types, 216 frames); this is the no-change gate for the whole feature
- [X] T003 [P] Run `npm test` and `npm run typecheck` in `frontend/`: 876 tests pass and the typecheck is clean
- [X] T004 [P] Create `specs/044-sustained-loudest-notes/tools/reference_selection.py`: an independent, plain-Python (no NumPy in the algorithm) version of the rule, written from [spec.md](spec.md) and not from the code: `def reference_selection(values: list[list[float]], count: int, extra: int) -> list[list[int]]` returns for each frame the selected note indices, loudest first, only notes whose value is above 0 (no padding). For each frame: `ranked = sorted(range(len(row)), key=lambda note: (-row[note], note))`; `rank = {note: r}`; `held = [note for note in previous if rank[note] < count + extra and row[note] > 0]`; then add notes of `ranked` that are not in `held` and have `row[note] > 0` while `len(held) < count`; the result is `held` sorted by `rank`; `previous` is the result of the frame before (empty for the first frame and after a frame whose result is empty). Type every function; the module docstring says what the arrays are (`values`: `(frames, notes)` strengths, each row a list)

**Checkpoint**: baselines exist; the source is untouched.

---

## Phase 2: Foundational (blocks every story)

**Purpose**: the one new array kind and the one new module that every story uses.

- [X] T005 In `backend/app/services/array_types.py`, in the section of the notes, add the alias `LoudestIndices = npt.NDArray[np.intp]` with its description in the file's format (comment above it): `Shape: (frames, count)` (`count` is n: 5 for Decay, Decay Exp, Chromatic Decay and Chromatic Wireframe, 5 to 8 for Polar Chords and Polychord); `Meaning:` for each frame the index of the note (0 to 83; of the letter, 0 to 11, for the two Chromatic pictures) at each of the `count` places of the selection, loudest first, with notes whose value is 0 in the last places when fewer than `count` notes sound (so `values[order] > 0` says "empty"); `Made by: held_notes.hold_loudest`. Add the alias to the module's `__all__` if it has one
- [X] T006 Create `backend/app/services/held_notes.py`. Module docstring: what a held note is (spec "How the user's words are read"), then `Order of operations:` (1. Rank the notes of every frame - `hold_loudest()` - stable argsort of the negative strengths, ties to the lower note, and its inverse: `NoteStrengths`-shaped ranks `(frames, notes)`; 2. Keep the notes of the previous selection that still rank within the loudest `n + k` and still sound; 3. Fill the free places with the loudest notes that are not held; 4. Order by loudness and pad with notes of value 0 - `LoudestIndices` `(frames, count)`). Constants: `MIN_EXTRA_NOTES = 1`, `MAX_EXTRA_NOTES = 8`, `DEFAULT_EXTRA_NOTES = 2`. `def check_extra_notes(value: object, limit: int = MAX_EXTRA_NOTES) -> int` returns the whole number when it is a whole number from 1 to `limit` (a bool, a string, a float that is not whole or a non-finite number is refused) else raises `ValueError(f"The extra notes must be a whole number from {MIN_EXTRA_NOTES} to {limit}.")`. `def hold_loudest(values: ArrayLike, count: int, extra: int = 0) -> LoudestIndices` implementing the algorithm of [research.md](research.md) decision 2: the values must be a 2-D array of finite numbers not below 0 (else `ValueError("The note values must be finite numbers that are not negative.")`), `count` a whole number from 1 to the number of columns, `extra` a whole number from 0 to `count` (else `ValueError(f"The extra notes must be a whole number from 0 to {count}.")`); the ranks of all frames are made at once with `np.argsort(-values, axis=1, kind="stable")` and `np.put_along_axis`; only the update of the selection from frame to frame is a Python loop; the input is never modified; the result is a new `intp` array. Document `Arrays:` (values: `ArrayLike` `(frames, columns)` strengths) and `Returns:` (`LoudestIndices`). Fully typed
- [X] T007 In `backend/tests/test_documentation.py` add `"services/held_notes.py"` to `PROCESSING_MODULES` (alphabetical, after `services/gaussian.py`)

**Checkpoint**: `.venv/Scripts/python.exe -m pytest tests/test_type_hints.py tests/test_documentation.py -q` passes with the new module and alias.

---

## Phase 3: User Story 1 - A note that is still sounding keeps its place when louder notes start (Priority: P1) 🎯 MVP

**Goal**: a held note keeps one of the n places while it ranks within the loudest n + k and still sounds; a louder newcomer cannot displace it.

**Independent Test**: n = 5, k = 2, A to E sound in frame 0; in frame 1 F is the loudest and A to E are the 2nd to 6th: the selection of frame 1 is A to E.

- [X] T008 [P] [US1] Create `backend/tests/test_held_notes.py` with the tests of this story, using small hand-made arrays (`np.zeros((frames, 84))` with chosen values): the five acceptance scenarios of Story 1 by name (louder newcomer does not displace; a note at rank 8 with n + k = 7 is freed and F takes the place; a note at exactly rank 7 is still held and at rank 8 in the next frame is not; frame 0 is the plain n loudest; a held note whose value falls to 0 is not held whatever its rank); `extra=0` equals the old expression `np.argsort(-values, axis=1, kind="stable")[:, :count]` for random data, for data with ties (values rounded to 3 distinct numbers) and for data with zeros and fewer than `count` notes sounding (compare the places whose value is above 0, and that the padded places have value 0); the reference cross-check: `hold_loudest` agrees with `reference_selection` of `specs/044-sustained-loudest-notes/tools/reference_selection.py` (import it with `importlib` from its path, as `backend/tests` has no package for it) on random data of 60 frames with 84 columns for every `count` 5 to 8 and every `extra` 0 to `count`, and with 12 columns for `count` 5 and every `extra` 0 to 5 (compare only the places whose value is above 0, in order); the first and last frame, and a silent frame in the middle (the next frame starts from nothing: it equals the plain n loudest)
- [X] T009 [US1] Run `.venv/Scripts/python.exe -m pytest tests/test_held_notes.py -q`; fix `hold_loudest` (not the tests, unless a test misreads the spec) until the Story 1 tests pass

**Checkpoint**: Story 1 works on its own: the rule keeps a note in its place.

---

## Phase 4: User Story 2 - A free place is taken by the loudest note that is not held (Priority: P1)

**Goal**: a place that is free (a held note fell below n + k, or fewer than n notes sounded) is filled by the loudest note that is not held; the selection has min(n, sounding) notes.

**Independent Test**: two held notes fall out of the loudest n + k and F, G, H, I sound loudest-first: F and G take the two places.

- [X] T010 [P] [US2] In `backend/tests/test_held_notes.py` add the tests of this story: the four acceptance scenarios of Story 2 by name (two free places go to the two loudest newcomers F and G and not to H; fewer than n notes sound: only those are selected and the padded places have value 0; a note that was held, dropped and sounds again takes a free place as a newcomer with no claim from before; two notes of equal strength compete: the lower note wins, for the rank and for the free place); and the properties for random data of every `count` 5 to 8 and `extra` 0 to `count`: no note twice in a row of the result among the places whose value is above 0, at most `count` such places, exactly `min(count, notes that sound)` such places for k = 0 and for every k when the previous selection is empty, the places above 0 come first, they are ordered by loudness (a non-increasing value, ties by the lower note), the result dtype is `intp` and the shape `(frames, count)`, the input array is unchanged, a held note is never displaced by a louder note that is not held while it is within n + k (the property of FR-003, checked against `reference_selection`); the argument checks: a bool, a float, a string, a negative number and a number above `count` for `extra`; `count` 0 and above the columns; a 1-D array, NaN, infinity and a negative value in the strengths all raise `ValueError` with the messages of T006, and `check_extra_notes` accepts 1 to 8 and 5 (limit 5), refuses 0, 9, 6 (limit 5), `True`, `"2"`, `2.5`, `nan`
- [X] T011 [US2] Run `.venv/Scripts/python.exe -m pytest tests/test_held_notes.py -q`; fix `held_notes.py` until it passes; also time `hold_loudest` for 30,000 frames of 84 random notes with `count` 8 and `extra` 8 in a test that asserts under 5 seconds (the plan's performance goal is under about 2 s)

**Checkpoint**: Stories 1 and 2 work: the rule is complete and tested on its own.

---

## Phase 5: User Story 4 - Every picture that takes the n loudest notes uses the held notes (Priority: P2)

**Goal**: Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe and Polychord choose their notes (letters) with the held-notes rule; with `extra=0` nothing changes.

**Independent Test**: for each picture a fabricated frame list like Story 1: the faded held note is still drawn in frame 1 (its circle gains points, its bar stays, its letter gains, its link stays) with `extra` above 0 and is replaced with `extra=0`.

*Do these before the setting (Phase 6), whose request passes the value to them.*

- [X] T012 [P] [US4] `backend/app/services/decay.py`: import `hold_loudest`; `gains(values, beat=None, extra: int = 0)` takes `order = hold_loudest(shown, len(GAINS), extra)` in place of the `np.argsort(...)[:, : len(GAINS)]` line (the code after it is unchanged); `circle_points(..., extra: int = 0)` passes it to `gains`; document the new parameter and update the module's `Order of operations:` step 2 (the five loudest are the held notes: see `held_notes`) and the docstrings that say "the five loudest notes" (held, when `extra` is above 0); the default `0` keeps the old behaviour
- [X] T013 [US4] `backend/app/services/decay_exp.py` (after T012): `exp_gains(values, beat=None, taper=TAPER, extra: int = 0)` passes `extra` to `decay.gains`; `circle_points(..., decay_rate=DEFAULT_DECAY_RATE, extra: int = 0)` passes it to `exp_gains`; docs and the `Order of operations:` step 2 as in T012
- [X] T014 [P] [US4] `backend/app/services/chromatic_decay.py`: `_raw_gains(values, beat=None, extra: int = 0)` uses `hold_loudest(energy, len(GAINS), extra)` in place of its argsort line (energy is `LetterEnergies` `(frames, 12)`, so the held unit is the letter); `letter_gains(..., extra: int = 0)` and `circle_points(..., threshold=DEFAULT_THRESHOLD, extra: int = 0)` pass it on (the Threshold is applied first, as today); docs and `Order of operations:` step 4
- [X] T015 [P] [US4] `backend/app/services/polar_chords.py`: `_targets(values, peak, count, note_layout, extra: int = 0)` uses `hold_loudest(drawn, count, extra)` in place of its argsort line (keep `top = take_along_axis(drawn, order, axis=1)`, `sounding = top > 0`); `note_targets(strengths, count, note_layout, extra: int = 0)` and `polar_bars(strengths, beat, count, note_layout, extra: int = 0)` pass it on; docs and `Order of operations:` step 2
- [X] T016 [P] [US4] `backend/app/services/polychord.py`: `loudest_letters(values, count, extra: int = 0)` uses `hold_loudest(shown, count, extra)` in place of its argsort line (keep the `sounding` test and `order % LETTERS`); `write_polychord_frames(..., height, extra_notes: int = 0)` passes `extra_notes` to `loudest_letters` (it is the last parameter, after `height`, with a default, so existing callers are unchanged); docs and `Order of operations:` step 2
- [X] T017 [US4] `backend/app/services/frame_rendering.py` (after T012 to T016): `write_frames(..., polychord_settings=..., extra_notes: int = 0)`: check it first with the other settings (`check_extra_notes` allows 1 to 8; here a whole number from 0 to 8 is allowed as 0 means off: write a small `_check_extra_notes(value, image_type, polar_notes, polychord_settings)` that accepts 0, and otherwise calls `check_extra_notes(value, n)` with n = 5 for `decay`, `decay-exp`, `chromatic-decay`, `chromatic-wireframe`, `polar_notes` for `polar-chords`, `polychord_settings.notes` for `polychord` and 8 for the other types, raising the `ValueError` of `check_extra_notes`), and pass `extra=extra_notes` to `circle_points` (decay and decay_exp and chromatic), `polar_bars`, and `extra_notes=extra_notes` to `write_polychord_frames`; document the argument in the `write_frames` docstring and add the step to the module's `Order of operations:` (the selection of the held notes happens inside the gains, targets and letters of step 6)
- [X] T018 [P] [US4] `backend/app/services/image_types.py`: in the stages of Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe and Polychord of the pipeline overview, name the held-notes step before the gains / targets / letters (``held_notes.hold_loudest()`` - ``LoudestIndices`` ``(frames, count)``), say once in the shared text that it uses the Extra notes (k) setting, and in the settings that apply of each of the six add Extra notes (k); in `array_types.py` update the `Made by:` lines of `PointGains`, `BarArcs` and `LoudLetters` (and the one of `LetterEnergies` if it mentions the argsort) to say that the notes in them are chosen by ``held_notes.hold_loudest``
- [X] T019 [P] [US4] Create `backend/tests/test_held_notes_pictures.py` with fabricated frame lists (`np.zeros((frames, 88))` with chosen values; the constants of each module: `decay.GAINS`, `polar_chords.ARCS`) and one section for each picture: Decay: `decay.gains(values, extra=2)` gives the held, faded note a gain above 0 in frame 1 and the newcomer 0, while `extra=0` gives the newcomer the gain and the faded note 0; the gains of the held notes follow their loudness order (the loudest held note gains 24); `decay_exp.exp_gains` and both `circle_points` the same; Chromatic Decay: `_raw_gains` and `letter_gains` for letters (a letter of a faded note keeps charging); Polar Chords: `note_targets(values, 5, "rows", extra=2)` keeps the arc of the held note in its volume and `polar_bars` still has its bar; Polychord: `loudest_letters(values, 6, extra=2)` keeps the held letter and two held notes of one letter in two octaves stay two links; **steady chord (SC-005)**: for every picture the output with `extra` 1 to 5 equals the output with `extra=0` when every frame has the same loudest notes in the same order; **end to end**: `write_frames(values, directory, image_type=type, extra_notes=2)` for each of the six types writes different PNGs from `extra_notes=0` for the displacement list and identical PNGs for the steady list; the three other types (`contour`, `energy-graphs`, `rhythm-circles`, with the `energy` and `rhythm` arguments of `specs/043-decouple-frame-rate/tools/verify_drawing.py`) are identical for any `extra_notes`; `write_frames` refuses `extra_notes=6` for Decay, 9 for any type, `True`, `2.5`, and `extra_notes=7` for Polychord with 6 notes (checked before anything is written: the directory does not exist)
- [X] T020 [US4] Run `.venv/Scripts/python.exe -m pytest tests/test_held_notes_pictures.py tests/test_held_notes.py tests/test_decay.py tests/test_decay_exp.py tests/test_chromatic_decay.py tests/test_polar_chords.py tests/test_polychord.py tests/test_frame_rendering.py -q` (every pre-existing test in those files must still pass or be one of the baseline failures of `baseline-failures-before.txt`), then `backend/.venv/Scripts/python.exe specs/043-decouple-frame-rate/tools/verify_drawing.py` from the repository root: it must still say `all frames identical to the baseline` (the library default is `extra=0`)

**Checkpoint**: Story 4 works at the library level.

---

## Phase 6: User Story 3 - The user chooses how long a held note keeps its place (Priority: P2)

**Goal**: the setting Extra notes (k) is in the request, the answer and the page, for the six pictures.

**Independent Test**: choose Decay on the page: the setting is there with default 2; choose Contour: it is not; a request with k above n is refused.

### Tests for User Story 3

- [X] T021 [P] [US3] Create `backend/tests/test_extra_notes_api.py` (helpers of `backend/tests/test_jobs_api.py`: `client`, `wav_bytes`, `tone`; the file made with `np.zeros(22050)` is enough): not sent gives `extra_notes == 2` in the answer for every image type; 1 to 5 accepted for the four 5-note pictures and the answer echoes it; 6 refused with `The extra notes must be a whole number from 1 to 5.`; Polar Chords: `polar_notes=5` accepts 5 and refuses 6, `polar_notes=8` accepts 8; Polychord: `polychord_notes=5` refuses 6 with `... from 1 to 5.`, `polychord_notes=8` accepts 8; for `contour`, `energy-graphs`, `rhythm-circles` 1 to 8 is accepted and ignored (the frames are byte-identical for k = 1 and k = 8); `0`, `9`, `-1`, `2.5`, `abc`, `nan`, `inf`, `""` and `"  "` are refused with `The extra notes must be a whole number from 1 to 8.` for every picture; every refusal happens before the file is read (monkeypatch `jobs.read_wav` to raise) and leaves nothing behind (`leftovers() == []`); the job passes the value to `write_frames` (spy on `jobs.write_frames` as `test_noise_floor_api.py` does: `kwargs["extra_notes"]` is the request's value, 2 by default); a request that is refused is followed by an accepted one (it recovers)

### Implementation for User Story 3 - backend

- [X] T022 [US3] `backend/app/routers/jobs.py`: import `DEFAULT_EXTRA_NOTES`, `MAX_EXTRA_NOTES`, `check_extra_notes` from `..services.held_notes`; add the form parameter `extra_notes: str | None = Form(None)` and `_parse_extra_notes(text: str | None, sent: bool) -> int` (not sent: the default; sent: `check_extra_notes(float(text or ""), MAX_EXTRA_NOTES)` with the `ValueError` and a text that is not a number turned into `HTTPException(400, detail=str(error))`, like `_parse_polar_notes`); after `polar_notes_value` and `polychord_settings_value` are known, for `image_type_value` in the six types check `check_extra_notes(extra_notes_value, n)` with n = 5, `polar_notes_value`, or `polychord_settings_value.notes` and answer 400 with its message; pass `extra_notes=extra_notes_value` to `write_frames`; add `"extra_notes": extra_notes_value` to the answer; update the module docstring's step 1 of `Order of operations:` (the setting is read and checked with the others) and the comment above `write_frames`. All of it before the file is read (the checks sit with the other `_parse_*` calls at the top of `create_job()`)
- [X] T023 [US3] Run `.venv/Scripts/python.exe -m pytest tests/test_extra_notes_api.py -q` and fix until it passes

### Implementation for User Story 3 - frontend

- [X] T024 [P] [US3] `frontend/src/api.ts`: `extra_notes: number` in `JobResult` and `extraNotes: number` in `JobSettings` (doc comment: 1 to n, default 2), and `body.append("extra_notes", String(settings.extraNotes))` in `submitJob`
- [X] T025 [P] [US3] `frontend/src/utilities/validation.ts`: `EXTRA_NOTES_RANGE = { min: 1, max: 8, step: 1 } as const`, `DEFAULT_EXTRA_NOTES = 2`, `usesHeldNotes(imageType: string): boolean` (true for `decay`, `decay-exp`, `polar-chords`, `chromatic-decay`, `chromatic-wireframe`, `polychord`), `heldNotesCount(imageType: string, polarNotes: number, polychordNotes: number): number` (5, `polarNotes` for `polar-chords`, `polychordNotes` for `polychord`, 8 for any other type), `validateExtraNotes(value: string | number, notes: number): string | null` (null when a whole number from 1 to `notes`, else `The extra notes must be a whole number from 1 to ${notes}.`), `formatExtraNotes(value: number): string`; `frontend/src/utilities/groups.ts`: the group `{ id: "held-notes", title: "Held notes", controls: ["extra-notes"] }` placed after the six type groups and before `note-layout`, and in `groupsFor` push `"held-notes"` after the type group when `usesHeldNotes(imageType)` (so it comes before `note-layout` and the Local peaks group), update the doc comment of `groupsFor`; `frontend/src/utilities/help.ts`: `extraNotesHelp` (what a held note is, k, the range 1 to the number of notes, that a note stays while it is among the loudest n + k, that a louder new note waits for a free place) and in `imageTypeHelp` add to Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe and Polychord that the notes they take are held notes (the Extra notes setting applies)
- [X] T026 [US3] `frontend/src/components/SettingsForm.vue` (after T024, T025): `const extraNotes = ref<number>(DEFAULT_EXTRA_NOTES)`, `heldCount = computed(() => heldNotesCount(imageType.value, polarNotes.value, polychordNotes.value))`, `extraNotesError = computed(() => usesHeldNotes(imageType.value) ? validateExtraNotes(extraNotes.value, heldCount.value) : null)` (the error only counts for the six types, so a high k left over does not block Contour), include it in `canSubmit`, add `showHeldNotes = computed(() => shownGroups.value.includes("held-notes"))`, `heldNotesProblem`, the `<SettingsGroup v-if="showHeldNotes" id="held-notes" ...>` with the slider `id="extra-notes"` (`:min="EXTRA_NOTES_RANGE.min"`, `:max="heldCount"`, `step` 1, a `<output class="slider-value">`, the info popover with `extraNotesHelp`, the error line) placed after the type group (before the Note layout group) with `:open`, `:problem`, `@toggle` like the other groups, and `extraNotes: extraNotes.value` in the settings the form emits; `frontend/src/App.vue`: the result line `<li v-if="usesHeldNotes(result.image_type)">Extra notes (k): {{ formatExtraNotes(result.extra_notes) }}</li>` with the imports
- [X] T027 [P] [US3] Frontend tests: `frontend/src/utilities/validation.test.ts` (`EXTRA_NOTES_RANGE`, default 2, `usesHeldNotes` true for exactly the six types and false for `contour`, `energy-graphs`, `rhythm-circles`, `heldNotesCount` for each type, `validateExtraNotes` accepts 1, 5, 8 with notes 8 and refuses 0, 9, 6 with notes 5, 2.5, "", "abc", NaN with the message), `frontend/src/utilities/groups.test.ts` (the group `held-notes` after the type group and before `note-layout` for the six types and absent for the other three; update the expected group lists of all nine types and the list of groups; the title; the control), `frontend/src/utilities/help.test.ts` (`extraNotesHelp` says held, k, the range and the free place; the six type descriptions say held), `frontend/src/api.test.ts` (`extraNotes` becomes `extra_notes` in the body, the SETTINGS fixture has it), `frontend/src/components/SettingsForm.test.ts` (the group and slider for the six types, none for Contour/Energy graphs/Rhythm Circles, `max` of the slider is 5 for Decay and follows Notes shown for Polar Chords, the error for a k above n only for the six types, the emitted settings have `extraNotes`, the group order, `SettingsGroup` counts: the number of `<SettingsGroup` in the form source becomes 8 and the `:open`, `:problem`, `@toggle` counts 8), `frontend/src/App.test.ts` (the summary line for the six types only)
- [X] T028 [US3] Run `npm test` and `npm run typecheck` in `frontend/`: both pass

**Checkpoint**: all four stories work.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T029 Run the whole backend suite in the background and compare by id with `baseline-failures-before.txt` (save the new list as `baseline-failures-after.txt`; `comm -13 before after` must print nothing). Existing tests that fail only because a job now gets the default `extra_notes` 2 (a test that rebuilds a picture from the arguments the job gave the spied `write_frames`: `test_polychord_api.py`, `test_chromatic_wireframe_api.py`, `test_frame_rendering_polychord.py`, `test_chromatic_decay_api.py`; or a test with a pulse or fading tone whose hard-coded expectation a held note changes) are fixed in the test: pass `extra_notes=kwargs["extra_notes"]` to the library call, or restore its premise (a steady tone), never weaken an assertion; a test that was already failing is left alone
- [X] T030 [P] Run `.venv/Scripts/python.exe -m pytest tests/test_type_hints.py tests/test_documentation.py -q`; run `backend/.venv/Scripts/python.exe specs/041-code-readability-docs/tools/trace_pipeline.py` and `shape_probe.py` from the repository root: for each of the six pictures the order printed has `held_notes.hold_loudest` before the gains / targets / letters and its output is `intp (frames, count)`; fix any documentation that disagrees (rule III)
- [X] T031 [P] Run `backend/.venv/Scripts/python.exe specs/043-decouple-frame-rate/tools/verify_drawing.py` again (identical), and `specs/041-code-readability-docs/tools/verify_frames.py`: record in `specs/044-sustained-loudest-notes/verify-frames-after.txt` which types differ (the jobs use k = 2, so only a file with a displaced note differs; the generated file of the tool has changing tones) and that every type still makes 60 frames
- [X] T032 [P] `README.md`: one bullet like the one feature 043 added (**Held notes** and the **Extra notes (k)** setting: what a held note is, k from 1 to n, default 2, the six pictures, the request field `extra_notes` and the answer key, the errors); update any README sentence that says "the five loudest notes" or "Notes shown" for these pictures only if it now says something false
- [X] T033 (done except section 5, the by-hand check, which needs a person at the page) Walk through the checks of [quickstart.md](quickstart.md) sections 1 to 5 (section 5 by hand: start the app and make Decay pictures at k 1 and 5) and report which passed; a failure goes back to the task that owns the code. Add an "Implementation notes" section at the end of this file (results, deviations, what was not done) and tick the tasks
- [X] T034 [P] Write the memory note `sustained-loudest-notes-decisions.md` (status: implemented with the date, the results, the baseline failures left, any deviation) and update its line in `MEMORY.md`

---

## Dependencies & Execution Order

- **Phase 1** (T001 to T004) before any edit of the source; T001 runs in the background while T004 and the other baselines run.
- **Phase 2** (T005 to T007) needs Phase 1 (the baseline must be taken before the first edit); blocks everything below.
- **US1** (T008, T009) and **US2** (T010, T011) need Phase 2; they test one function in one file, so do US1 first, then US2.
- **US4** (T012 to T020) needs Phase 2 (the function) and is best done after US1 and US2 pass. T012 before T013 (Decay Exp calls Decay); T014, T015, T016 are in different files and independent of each
  other and of T012; T017 needs T012 to T016; T018 and T019 can be written while the code is done; T020 last.
- **US3** (T021 to T028) needs US4 (the job passes the value to `write_frames`): the backend part (T021 to T023) and the frontend part (T024 to T028) are independent of each other; T026 needs T024 and T025.
- **Polish** last (T029 needs everything).

### Parallel opportunities

- Phase 1: T002, T003, T004 with T001.
- Phase 5: T014, T015, T016 together (three modules), then T018 and T019.
- Phase 6: T021 with T024 and T025; the frontend tests T027 while the backend task T022 is done.
- Polish: T030, T031, T032 and T034.

```text
# Example: the three independent picture modules of User Story 4
T014 chromatic_decay.py     T015 polar_chords.py     T016 polychord.py
```

## Implementation Strategy

- **MVP = Phase 1 + 2 + User Stories 1 and 2**: the rule exists, is correct and tested; nothing yet uses it.
- **Then** US4 (the pictures use it, with `extra=0` as the library default so nothing moves: `verify_drawing.py` is the proof), then US3 (the request and the page set k; the job default of 2 makes the
  change visible), then Polish. Only after US3 do pictures change for a user.
- **Stop and check** at each checkpoint with the command in it.
- Commit only when the user asks; this plan does not create a branch.


## Implementation notes (2026-11-18)

- **Results**: backend suite, first full run 37 failed / 5045 passed; the 5 extra failures were the "the answer has exactly these keys" tests, which did not list the new `extra_notes` key. They were
  updated and the five files pass (301 tests); the other 32 failing ids are exactly the ids of `baseline-failures-before.txt` (the known `DEFAULT_PROMINENCE` and `NEIGHBOURS` ones). The full suite was
  not rerun after that one change to five test files, so `baseline-failures-after.txt` is the first run's list minus those 5 ids (the first run's own list is `baseline-failures-after-first-run.txt`).
  Frontend: 916 tests and `vue-tsc` pass. `verify_drawing.py` (library default `extra = 0`): 9 image types, 216 frames identical to the baseline. `test_type_hints.py` and `test_documentation.py` pass.
  `trace_pipeline.py` shows `hold_loudest` called inside the gains, targets and letters of exactly the six pictures; `shape_probe.py` shows `int64 (60, 5)` and `(60, 6)` for Polychord.
- **A bug the tests found**: `write_frames` passed `extra_notes` to the Chromatic Decay branch but not to the Chromatic Wireframe branch (a second call of `chromatic_points`). `test_held_notes_pictures.py`
  caught it (the wireframe picture did not change with k) and it is fixed.
- **Deviations**: (1) the baseline run was made on a copy of `backend/` (the 043 changes are not committed, so a git worktree of HEAD would not have them); the copy lacks `frontend/`, so it shows 2 extra
  ids of `test_colormaps.py` that are an artifact; the baseline used is the 32 ids of feature 043's final run (`baseline-notes.txt`); (2) a helper `held_notes.notes_of()` and the constants
  `HELD_NOTES_TYPES` / `LOUDEST_COUNT` were added so that `write_frames` and the job share the picture's n; (3) `verify_frames.py` is not informative here (its baseline is from feature 041; see
  `verify-frames-after.txt`); (4) the Chromatic Wireframe branch bug above; (5) tasks T008/T010 and T019 are in `tests/test_held_notes.py` and `tests/test_held_notes_pictures.py` as planned.
- **Not done**: the by-hand check of quickstart section 5 (start the app, make Decay pictures at k 1 and 5). Nothing is committed.
