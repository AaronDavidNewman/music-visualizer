---

description: "Task list for Chord Interval Metric (feature 031)"
---

# Tasks: Chord Interval Metric

**Input**: Design documents from `/specs/031-chord-interval-metric/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/chords.md, quickstart.md

**Tests**: Written first for each story (the project's practice). The checks use an **independent oracle** written in the tests, which works from frequencies (dividing by 2 until within an octave) and from explicit permutations of the notes, not from the masks the module uses, so that the two can disagree if the module is wrong.

**Organization**: By user story: US1 the recognition and the selection rules (P1), US2 the stored result, one entry per window (P2), US3 the note limits of the pictures (P2), US4 the parameters and the odd cases (P3). The module is backend only; there is no frontend, request or picture work.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- Paths are from the repository root. Edit files with their line endings preserved. Backend tests run from `backend/` (`.venv` active). **Run mutation checks with `python -B` and clear the `__pycache__` folders afterwards**: a mutation that does not change the size of the file can otherwise leave stale bytecode that is tested in place of the restored source.

---

## Phase 1: Setup

- [x] T001 Record the baseline before changing anything: `python -m pytest -q` in `backend/` and `npm test`, `npm run build` in `frontend/`, and note the counts (the last known: backend 5731 passed, frontend 773 passed). Check that no file named `chords.py` or `test_chords*.py` exists yet (`ls backend/app/services backend/tests`). Read `backend/app/services/note_selection.py` (`top_energy_notes`, `check_note_count`) and `backend/app/services/frame_rendering.py` (`hidden_below`, `_check_threshold`) so the limits can be reused, not copied.

---

## Phase 2: Foundational: the chord types and their inversions

**Purpose**: Every story needs a checked list of chord types and the inversion patterns.

### Tests (write first, they fail)

- [x] T002 [P] Create `backend/tests/test_chords.py` with the helpers below and the tests for the chord types (spec FR-002, FR-005, FR-009; data-model "Chord type"):
  - Helpers used by all later tests: `window(**notes)` / `windows(...)` that build a `(W, 88)` array of zeros with given strengths at given note numbers; the note numbers `C3 = 15`, `C4 = 27`, `E4 = 31`, `G4 = 34`, `C5 = 39`; an **oracle** `oracle_inversions(chord_type)` that makes each inversion by the physical method (list the notes `0, t1, ..., tn`, then `k` times take the lowest, add 12, sort, and subtract the new minimum) and `oracle_fold(notes)` that works from frequencies (`55 * 2 ** (note / 12)`, divide every note above the lowest by 2 while it is `>= 2 *` the lowest, and read the steps as `round(12 * log2(f / lowest))`).
  - `inversion_patterns`: `(4,)` gives `((0, 4), (0, 8))`; `(5,)` gives `((0, 5), (0, 7))`; `(7,)` gives `((0, 7), (0, 5))`; `(4, 7)` gives `((0, 4, 7), (0, 3, 8), (0, 5, 9))`; `(4, 8)` gives three equal patterns; `(3, 6, 9)` gives four equal patterns; `(3, 7, 10)` gives `(0, 3, 7, 10)`, `(0, 4, 7, 9)`, `(0, 3, 5, 8)`, `(0, 2, 5, 9)`; for every one of the 231 valid chord types the result equals the oracle, has `n + 1` patterns, each starting at 0, increasing and below 12.
  - `check_chord_type`: `(4,)`, `[4]`, `(4, 7)`, `[3, 6, 9]`, a bare `5` (gives `(5,)`), numpy integers (`np.int64(4)`) are accepted and returned as a tuple of Python ints; refused with `ValueError` and the message `A chord type must be 1 to 3 intervals, each a whole number of steps from 1 to 11, in increasing order (got <value>).` for `()`, `(1, 2, 3, 4)`, `(0,)`, `(12,)`, `(-4,)`, `(7, 4)`, `(4, 4)`, `(4.5,)`, `(4.0,)`, `(True,)`, `("4",)`, `None`, `(None,)`, `"47"`, `(4, 12)`.
  - `check_chord_types`: `((5), (7))` (which in Python is `(5, 7)`, two bare numbers) gives `((5,), (7,))`; `[(5,), (7,)]` the same; `[(4, 7), (4,)]` keeps the order given; `[]`, `()`, `None`, `4`, `"ab"` refused with `The chord types must be a list of one or more chord types.`; `[(4,), (4,)]` and `[(4,), [4]]` refused with `The chord type (4,) is given more than once.`; a generator is accepted; the input is not changed.

### Implementation

- [x] T003 Create `backend/app/services/chords.py` (module docstring: what the measurement is, the chord types, the folding, the inversions, the selection rules, what is recorded, that it knows nothing about audio, frames or the router, and that nothing uses it yet, as for `local_peaks.py`). In this task only: the constants `MIN_INTERVALS = 1`, `MAX_INTERVALS = 3`, `MAX_STEP = 11`, `NOTES = 84` (import from `concentric` if it already defines it, as `decay.py` does); `check_chord_type(value) -> tuple[int, ...]` and `check_chord_types(types) -> tuple[tuple[int, ...], ...]` with the messages of the contract (a boolean, a float even if whole, a string and `None` are refused; numpy integers accepted; a bare whole number is a one-interval type; strictly increasing; 1 to 11; the list not empty and without repeats); `inversion_patterns(chord_type)` made from the data-model rule `(c[k], ..., c[n], c[0] + 12, ..., c[k-1] + 12) - c[k]`. Run T002 and fix.

**Checkpoint**: The chord types can be checked and their inversions listed.

---

## Phase 3: User Story 1 - Recognise which chord the loudest notes of a moment form (Priority: P1) 🎯 MVP

**Goal**: `measure_chords(values, chord_types)` records, for every window, the one chord that the rules choose.

**Independent Test**: The worked examples of the spec (C3 with E4, E4 with C5, C E G in each inversion, `(4)` against `(4, 7)`, `(4)` against `(8)`, `(5)` against `(7)`) give exactly the stated type and inversion.

### Tests for User Story 1 (write first, they fail)

- [x] T004 [US1] Add to `backend/tests/test_chords.py` (spec User Story 1, FR-001, FR-003 to FR-007, SC-001 to SC-003, SC-005 to SC-006), using `measure_chords(values, chord_types)` and `series.record(i)`:
  - Each acceptance scenario of the spec as a test with its note numbers: C3 (15) with E4 (31) and `[(4,)]` gives `(4,)`, inversion 0, notes `(15, 31)` (not 16 steps: the original notes); E4 (31) with C5 (39) and `[(4,)]` gives inversion 1, notes `(31, 39)`; C4 E4 G4 (27, 31, 34) with `[(4, 7)]` inversion 0, E4 G4 C5 (31, 34, 39) inversion 1, G4 C5 E5 (34, 39, 43) inversion 2, each with the original notes lowest to highest, also in other octaves (C2 E4 G3: the notes are recorded as `(3, 22, 40)` style numbers in order, and the inversion follows from the lowest); `[(4,), (4, 7)]` with C E G gives `(4, 7)`; `[(4,), (8,)]` with notes 8 steps apart gives `(8,)` inversion 0 and with notes 4 steps apart gives `(8,)` inversion 1; `[(5,), (7,)]` with a fifth gives `(7,)` inversion 0 and with a fourth `(7,)` inversion 1; a 3-interval type `[(3, 7, 10)]` uses the four loudest notes and has inversions 0 to 3 (play each); two runs give equal results.
  - The folding: the notes C3 (15) and E4 (31) fold to a step of 4; a note exactly an octave above the lowest (C3, C4, E4 with `[(4,)]`) counts as the lowest again, so the two loudest are C3 and C4 only if they are the two loudest, and then no chord; octave doubling: the loudest two are C2 (3) and C3 (15) with `[(4,)]` gives no chord; the three loudest C2, C3, E3 with `[(4, 7)]` gives no chord and with `[(4,)]` and the two loudest being C2 and E3 gives `(4,)`.
  - Which notes: a note with strength 0 never counts (one sounding note with `[(4,)]` gives no chord; three sounding notes with a 3-interval type gives no chord); equal strengths go to the lower note (five notes of equal strength with `[(4,)]` use the two lowest); for a type with `n` intervals the `n + 1` loudest decide, so a fourth quiet note does not stop a triad (C E G loud, D faint: `(4, 7)` is recorded) and a louder foreign note does (C E loud, F# louder: `(4,)` no longer matches).
  - The selection rules against an **independent brute-force oracle** in the test file: `oracle_measure(values, types)` that for each window tries every type and inversion with `oracle_fold` and `oracle_inversions` and picks the winner by sorting the matches with the key `(-intervals, -widest, inversion, position)`. Compare it with `measure_chords` for: every pair of chord types among the 231 that can match the same notes (generate the notes for one and test both orders in the list); 300 random lists of 2 to 8 types with random windows of 2 to 5 sounding notes; the symmetrical types `(4, 8)` and `(3, 6, 9)` (always inversion 0, the notes in any order and octave); two types that tie on length and width, for example `(3, 8)` and `(5, 8)` (the earlier in the list wins), and the same pattern from the same type in several inversions (the lowest inversion wins).
  - Exhaustive: for each of the 231 chord types and each inversion `k`, play the chord with the bass `c[k]` and the other notes at random octaves above it (a fixed seed, several placements, all within notes 0 to 83) and ask for that type alone: the record is that type, with the lowest inversion whose pattern equals the played one (the oracle), and the original notes are the played notes in order of pitch.
  - Only the 84 piano notes: strengths in columns 84 to 87 are never in a chord and never decide a chord.
- [x] T005 [US1] Create the following in `backend/app/services/chords.py` from the data-model and research Decisions 2 to 4 and 6: the frozen dataclasses `ChordRecord(chord_type, inversion, notes)` and `ChordSeries(chord_types, type_index, inversion, notes)` with `window_count`, `record(i)` and `records()` (the full behaviour is tested in US2, but `measure_chords` needs the class now); `measure_chords(values, chord_types, note_count=None, threshold=None)`, in this task **without** the two limits (accept the arguments, `None` only is working; the limits are Story 3): check the types with `check_chord_types`; check `values` (2-dimensional, at least 84 columns, finite, not negative, with the messages of the contract); take columns 0 to 83; find the four loudest notes of every window once (stable `argsort` on `-strength`, so ties go to the lower note), with their strengths; for each chord type with `n` intervals take the first `n + 1` of the four, require strength above 0, sort the note numbers, make the window mask (`1 << ((note - lowest) % 12)` summed), require `n + 1` bits and look the mask up in the type's inversion masks (the lowest inversion that matches); score every match as `(((n * 16 + widest) * 8 + (3 - inversion)) * 1024) + (1023 - position)`; take the maximum over the types; fill `type_index`, `inversion` and the original notes (the winning type's `n + 1` notes, sorted, padded with -1 to 4). All with array operations over the windows, not a loop over windows. Run T004 and fix.
- [x] T006 [US1] Mutation checks (run with `python -B`, clear `__pycache__` after), each caught by the tests and restored byte for byte (`cmp` with a copy): the inversion formula adding the octave to the wrong notes; inversion counted from 1; the fold using `% 11` or `% 13`; the fold relative to the highest note instead of the lowest; no bit-count test (octave doubling matching); `n` loudest instead of `n + 1`; ties going to the higher note; a note with strength 0 counting; the original notes recorded folded; the original notes not sorted; the score ignoring the number of intervals, or the widest interval, or preferring the higher inversion, or preferring the later type; the lowest inversion not taken for a symmetrical chord; columns 84 and above included; the type index off by one.

**Checkpoint**: Windows can be measured and the right chord is recorded for every example, pair and chord type.

---

## Phase 4: User Story 2 - One record for every window, kept like the bins and the local peaks (Priority: P2)

**Goal**: The result is stored as arrays with one entry per window, read back with `record(i)`.

**Independent Test**: 500 windows with a triad in the middle give 500 entries, `None` in the silent ones.

### Tests for User Story 2 (write first, they fail)

- [x] T007 [US2] Add to `backend/tests/test_chords.py` (spec User Story 2, FR-007, FR-008, FR-010, FR-011, SC-004, SC-006): `window_count` equals the number of rows; `type_index` is `int16` of shape `(W,)`, `inversion` `int8` of shape `(W,)`, `notes` `int16` of shape `(W, 4)`; `-1` marks no chord in all three, and the unused places of `notes` (a 2-note chord has two `-1` places); `chord_types` holds the checked tuple of tuples in the order given; `record(i)` gives a `ChordRecord` whose fields equal the arrays (`notes` as a tuple of Python ints without the padding) and `None` for no chord; `record(-1)` gives the last; `record(W)` and `record(-W - 1)` raise `IndexError`; `records()` has `W` entries and equals `[record(i) for i in range(W)]`; **order and independence**: shuffling the rows of the input shuffles the records the same way (the record of a window depends on its row only), a silent row gives `None` wherever it stands, and 500 windows with a C major triad in rows 200 to 299 and silence elsewhere give `(4, 7)` inversion 0 in exactly those rows; zero windows (`(0, 88)`) gives an empty series; the input array is not changed and the result does not share memory with it; two calls are equal (compare arrays and types); the result is frozen (assigning an attribute raises). **Nothing else changes**: `git diff --stat` shows no file other than `chords.py`, the tests and the README touched; `python -m pytest -q` still has the baseline counts of T001 plus the new tests (the pictures' reference-hash tests pass).
- [x] T008 [US2] Make T007 pass: any gap in `ChordSeries` (the read methods, the dtypes, the padding, the `IndexError` for an index out of range, `frozen=True`, copies of the arrays so that the input is not shared) in `backend/app/services/chords.py`. Run T007 and fix.

**Checkpoint**: The result can be stored and read back per window.

---

## Phase 5: User Story 3 - Only the notes the image type would use (Priority: P2)

**Goal**: The optional `note_count` and `threshold` limit the notes of the interval search exactly as the pictures' Notes and Threshold settings do.

**Independent Test**: With the loud notes outside the allowed set, the quiet allowed notes form the chord; with no limits the loud ones win.

### Tests for User Story 3 (write first, they fail)

- [x] T009 [US3] Add to `backend/tests/test_chords.py` (spec User Story 3, FR-013, SC-005): with neither limit the records equal those of a call with `threshold=0` and with `note_count=84`; **number of notes**: the allowed notes are exactly `note_selection.top_energy_notes(values[:, :84], count)` (build windows where the notes with the most total energy are known, equal energy to the lower note), the same in every window: a loud chord made of notes outside the allowed set is never recorded and an allowed quiet chord is; the chosen notes keep their own pitch (a chord of allowed notes C2 E3 G4 is found with its real intervals, and a chord that would only form after spreading the notes over the grid is not found); **threshold**: a note strictly below `threshold` percent of the largest value anywhere in the array does not count in that window (use `frame_rendering.hidden_below(values[:, :84], values.max(), threshold)` as the oracle), one exactly at the threshold counts, the largest value includes the columns 84 to 87, the threshold is per window (the same note counts in a loud window and not in a quiet one), `threshold=0` hides nothing, and with every note hidden the window has no chord; **both**: a note counts only if it passes both; the `n + 1` loudest are picked among the allowed ones (a louder forbidden note does not take a place); the messages: `note_count` 11, 85, 20.5, `True`, `"20"` give `The number of notes must be a whole number from 12 to 84.`, and `threshold` -1, 11, `nan`, `True`, `"5"` give `The threshold must be a number from 0 to 10.`, both before any window is measured. For 200 random arrays and random limits, `measure_chords` equals the same call made on a copy in which every not allowed strength has been set to 0 by the oracle (which uses the two functions of the pictures).

### Implementation for User Story 3

- [x] T010 [US3] In `backend/app/services/chords.py` add the limits to `measure_chords` (research Decision 5): `note_count` checked with `note_selection.check_note_count` and used through `note_selection.top_energy_notes(values[:, :84], count)` (every other column set to 0 in every window); `threshold` used through `frame_rendering.hidden_below(values[:, :84], float(values.max()), threshold)` (imported inside the function, not at the top of the module; its `_check_threshold` gives the message), hidden strengths set to 0; applied to a copy, never to the caller's array; both applied before the loudest notes are found; a threshold of 0 or `None` and `note_count` of `None` change nothing. Both parameters checked before any measuring. Run T009 and fix.
- [x] T011 [US3] Mutation checks (as T006), each caught: the threshold using `<=`; the peak taken from the first 84 columns only; the peak per window instead of the file; `note_count` using the energy of the window instead of the file; ties of energy to the higher note; the chosen notes spread over the grid; the limits applied after the loudest notes are found; only one of the two limits applied when both are given; the caller's array changed; the threshold check skipped.

**Checkpoint**: The measurement can be told to use exactly the notes of the picture's settings.

---

## Phase 6: User Story 4 - The chord types come as parameters, and odd cases are handled (Priority: P3)

**Goal**: Wrong parameters and odd inputs are refused or handled as the spec says.

**Independent Test**: Each refusal of the spec gives its message; the odd cases give "no chord" or the lowest inversion.

### Tests for User Story 4 (write first, they fail where behaviour is missing)

- [x] T012 [US4] Add to `backend/tests/test_chords.py` (spec User Story 4, FR-004, FR-009): `measure_chords` refuses the bad chord types of T002 with the same messages, **before** anything else is checked or measured (pass invalid `values` together with a bad type list and expect the type message; pass valid `values` with a bad `note_count` and a bad type list and expect the type message); values: a 1-dimensional array, a `(W, 83)` array, `nan`, `inf`, a negative strength, strings refused with `Each window needs at least 84 note values (got shape ...).` or `The note values must be finite numbers that are not negative.`; an `(W, 84)` array and an `(W, 88)` array are both accepted; integer and float arrays accepted; the odd cases of the spec: fewer sounding notes than a type needs gives no chord for that type but another type of the list can still match; two of the loudest notes the same letter in two octaves give no chord (C2 and C3 with `[(4,)]`, and the three loudest C2 C3 E3 with `[(4, 7)]`); the notes 84 to 87 are ignored; the symmetrical `(4, 8)` with C E G# in any order and octave is inversion 0, and so is `(3, 6, 9)` with C D# F# A; when fewer notes are allowed than the type needs (12 notes allowed, one 4-note type, only 3 of them sounding) there is no chord in that window; a window where the loudest notes match no requested type has no chord although other notes would match; a list of 231 types works (the most there are) and is quick; a list of the types in any order gives the same records except where the rules say that the order decides.
- [x] T013 [US4] Fix whatever T012 shows in `backend/app/services/chords.py` (the order of the checks, the messages, the shapes accepted, 231 types fitting the score). Run T012 and fix.

**Checkpoint**: Bad parameters are refused with clear messages and the odd cases behave as written.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T014 [P] Create `backend/tests/test_chords_audio.py` (quickstart scenario 5, SC-001 with real audio): synthesize a C major triad (three sine tones at the frequencies of notes 27, 31 and 34, using the tone helper of `backend/tests/test_jobs_api.py` or `numpy`), a silent stretch before and after it, run `analyze_channels` (the real note analysis) and `measure_chords(result.frames, [(4,), (4, 7)])`; the windows in the middle of the chord record `(4, 7)` inversion 0 with the notes 27, 31, 34 and the silent windows record no chord; an E-G-C voicing records inversion 1; a file with one tone records no chord for `(4,)`; with `note_count` and `threshold` given the call works on the analysis frames. Choose strengths and window sizes so that the harmonics of the tones do not decide (use `window_size` 8192 and tones at moderate level) and say in a comment what was assumed about the analysis.
- [x] T015 [P] Documentation: a paragraph in `README.md` after the Local Peaks / measurement paragraphs: what the measurement is, the chord types, the folding and inversions with the `(4)` and `(4, 7)` examples, the selection rules (longest, widest, then lowest inversion, then earliest), what is recorded (type, inversion, original notes), the optional `note_count` and `threshold`, that it has no setting of its own and that nothing uses it yet (module `backend/app/services/chords.py`). Check `specs/031-chord-interval-metric/quickstart.md` still matches what was built and fix it where it does not.
- [x] T016 Run the whole suite and the manual quickstart: clear the `__pycache__` folders, then `python -m pytest -q` in `backend/` (all pass: the baseline of T001 plus the new tests), `npm test` and `npm run build` in `frontend/` (unchanged), `git status` shows only `chords.py`, the three test files, the README and the spec folder as new or changed; quickstart scenarios 1 to 6 as far as they can be done by script (state which ones were not watched); time `measure_chords` on 4,000 random windows with 10 types and on a 60 second file's worth of windows with 231 types and report the numbers against SC-007. Tick the boxes of this file.

---

## Phase 8: Revision of 2026-11-07 - letters, and more notes considered

**Goal**: The user found too few chords in real music (22 to 23 percent of the windows) and asked that the octaves be combined and more notes considered: 4 for one interval, 6 for three, 6 at most; overtones taken for fifths are accepted.

- [x] T017 Update the oracle in `backend/tests/test_chords.py` (written first; the old tests fail): the letters (octaves added up from the lowest, loudest octave as the note, lowest on a tie, a letter at or under a millionth of the loudest is silent), the `n + 3` loudest letters (ties to the lower letter), every choice of `n + 1` of them, the key `(n, loudness, widest, -inversion, -choice)`.
- [x] T018 Change the tests whose meaning changed (the same letter in two octaves is one letter; equal strengths go to the lower letter; a louder foreign note no longer hides a chord; the faint-note, threshold and note-limit examples) and add tests for: the octaves being added up, the loudest octave being the recorded note, the reach of 4 / 5 / 6 letters for 1 / 2 / 3 intervals (the weakest letter of the chord one place inside and one place outside the reach), the louder of two chords sharing a note, loudness before the widest interval (and the widest still deciding for the same letters), the noise floor (2e-6 counts, 1e-6 and 1e-9 do not).
- [x] T019 Rewrite `measure_chords` in `backend/app/services/chords.py`: `_letters`, the six loudest letters once per window, the loop over the choices of letters (`itertools.combinations`), the score of five kinds compared by `_greater`. Run `tests/test_chords.py` (142 pass).
- [x] T020 Mutation checks (`python -B`, `__pycache__` cleared): 28 mutants of the new logic (reach, noise floor, summing, the representative octave, ties, every kind of the score, the order of the kinds, the sounding test); 25 caught; 3 are no mutants: the cap of 6 was dead code (a type has at most 3 intervals, so `n + 3` is at most 6; it is now `MAX_LETTERS = WINDOW_NOTES + EXTRA_LETTERS` and the `min` is gone) and `>=` for `==` in `_greater` is equivalent (the result is already decided).
- [x] T021 Adjust `tests/test_chords_audio.py` (the windows where a lone tone starts and stops leak a few percent into the neighbouring notes, enough for a third among 4 letters: only the windows inside the tone are asserted) and check `test_polar_chords*.py` (unchanged and green).
- [x] T022 Documentation: spec (clarification session of 2026-11-07, matching, selection rules, FR-003, FR-004, FR-006, FR-007, assumptions), plan, research (Decisions 2 to 4), data model, contract, quickstart (scenario 7), checklist note, README; the Polar Chords documents (a chord can now use letters that are not among the drawn notes).

---

- [x] T023 Update of 2026-11-07 (feature 033, noise floor): `measure_chords` applies the fixed noise floor (a note strictly below a thousandth of the largest value of the array given is 0) first, and the per-window floor of a millionth of the loudest letter (`NOISE_FLOOR = 1e-6`, T019/T020) is removed; the oracle of `tests/test_chords.py` works on values cut by an independent `floored` helper and the boundary tests of the old floor became tests of the new one. See `specs/033-noise-floor/`.

---

## Dependencies & Execution Order

- Phase 1 first. Phase 2 (T002 then T003) before any story, because every story uses the checked types and the inversion patterns.
- US1 (T004, T005, T006) is the MVP. T005 also creates `ChordSeries`, so US2 only adds the tests and the gaps (T007, T008).
- US3 (T009 to T011) needs `measure_chords` from T005. US4 (T012, T013) needs T005; it can run in parallel with US3 only if the two do not edit `chords.py` at once (they do; do them in order).
- Polish after the stories: T014 and T015 [P], then T016.

```text
T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012 → T013 → ┬→ T014 ┐
                                                                                            └→ T015 ┴→ T016
```

## Parallel Example

```text
Task: "T002 tests for the chord types (backend/tests/test_chords.py)"   # only one test file is written until T014/T015
...
Task: "T014 end-to-end test with real audio (backend/tests/test_chords_audio.py)"
Task: "T015 README paragraph"
```

## Implementation Strategy

1. **MVP**: Phases 1 to 3: the recognition and the selection rules, tested against an independent oracle and exhaustively.
2. Add Phase 4 (the stored result), Phase 5 (the picture's limits), Phase 6 (parameters and odd cases).
3. Polish: the audio test, the README, the full run and the timings.
4. Stop at each checkpoint to run `python -m pytest -q`: the pictures and the existing measurements must stay as they were.
