---

description: "Task list for 047-rhythm-note-voting"
---

# Tasks: Rhythm Circles Tempo Voting from Sustained Loudest Notes

**Input**: Design documents from `/specs/047-rhythm-note-voting/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/rhythm-voting.md](contracts/rhythm-voting.md), [quickstart.md](quickstart.md)

**Tests**: The plan and the constitution require them (the plan names the test files), so test tasks are included.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root. Run backend commands from `backend/` with `.venv/Scripts/python.exe` (`python` is not the project's interpreter) and frontend commands from `frontend/`.

**Environment note**: the PowerShell scripts in `.specify/scripts` may not run on this machine (execution policy): do not depend on them. Write scripts for edits to the scratchpad directory, not the project (the Bash tool eats backticks in long heredocs). Files with CRLF line ends stay CRLF (read bytes, edit, write bytes; `array_types.py` is CRLF).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1 to US5 as in the spec (US1 the voting, US2 the six circles, US3 the starts from the sustained loudest notes, US4 the vote limit setting and the page, US5 the other types unchanged)

---

## Phase 1: Setup (baselines, before the first edit of `backend/app` or `frontend/src`)

- [X] T001 Check the backend baseline: `specs/047-rhythm-note-voting/baseline-failures-before.txt` (copied from `specs/046-spirograph/baseline-failures-after.txt` during planning) has 32 ids, the state of the tree now. A full run takes about 10 minutes; it is repeated at the end in T040
- [X] T002 [P] Make the drawing baseline of the other types: copy `specs/046-spirograph/tools/verify_drawing.py` and `baseline-drawing.json` to `specs/047-rhythm-note-voting/tools/`; the baseline file already has a hash for every type, so change the script only to **leave `rhythm-circles` out of the comparison** (its pictures change by design) and to print which types were compared. Run it once before any edit: it must say every compared type matches
- [X] T003 [P] Save the old angles of the two local-peak circles for T031: write `specs/047-rhythm-note-voting/tools/old_peak_angles.py` that builds, with the code **as it is now**, `rhythm_angles()` for a fixed list of peaks (a `LocalPeaks` made from 12 peaks at irregular times and rates, over a 20 s file at 30 frames a second) and saves columns 2 and 3 of `RhythmData.angles` to `specs/047-rhythm-note-voting/tools/old_peak_angles.npy`. Run it now
- [X] T004 [P] Run `npx vitest run` and `npx vue-tsc --noEmit` in `frontend/`: note the number of tests that pass (1004 at the last run) and that the typecheck is clean

**Checkpoint**: baselines exist; the source is untouched.

---

## Phase 2: Foundational (blocks every story)

**Purpose**: the new array kinds, the new module with its constants and the setting check, and the held-notes change that stories 3 and 4 use.

- [X] T005 In `backend/app/services/array_types.py` (CRLF) add the aliases `StartTimes`, `TempoVotes`, `FitMatrix` and `RankedTempos` with the descriptions of [data-model.md](data-model.md) ("Arrays", each with `Shape:`, `Meaning:` and `Made by:` in the format of the neighbouring aliases; `FitMatrix` is `npt.NDArray[np.bool_]`, `TempoVotes` `np.int64`, `StartTimes` and `RankedTempos` `np.float64`), and re-describe `CircleSeries`, `CircleSpeeds` and `CircleAngles` for any number of circles (the width is that of the series: 4 for the vote circles, 2 for the peak circles, 6 once joined) in their one place (their `Shape:` becomes `(events, circles)` / `(moments, circles)`)
- [X] T006 Create `backend/app/services/tempo_votes.py` with the module docstring (what the voting is, the user's rule in words, the fit rule, the ranking, in the manner of `tempo_finder.py`; 120 columns) and its `Order of operations:` (1. check the setting - `check_vote_limit()`; 2. find the starts - `note_starts()` - `StartTimes` `(starts,)`; 3. find the tempos that fit each note length - `fitting_tempos()` - `FitMatrix` `(cycles, 18)`; 4. vote - `vote_tempos()` - `TempoVotes` `(starts, 18)`; 5. rank - `ranked_tempos()` - `RankedTempos` `(starts, 2)`; 6. make the circle series - `vote_series()` - `CircleSeries` `(starts, 4)`), the constants of [data-model.md](data-model.md) ("Constants", each with its comment: `TEMPOS = tuple(72 + 4 * n for n in range(1, 19))`, `NOTE_BEATS`, `HALF_BIN`, `SLACK`, `DEFAULT_VOTE_LIMIT`, `MIN_VOTE_LIMIT`, `MAX_VOTE_LIMIT`, `VOTE_LIMIT_MESSAGE`, `NO_VOTES_TEMPO = tempo_finder.START_TEMPO`) and `check_vote_limit(value: object) -> int` (a whole number 1 to 100; a bool, a string, a fraction, a non-finite number or `None` is refused with `ValueError(VOTE_LIMIT_MESSAGE)`; numpy integers and `20.0` are accepted and returned as `int`). The functions of later tasks are added where each task says
- [X] T007 [P] In `backend/tests/test_documentation.py` add `services/tempo_votes.py` to `PROCESSING_MODULES` (next to `services/spirograph.py`), and in `backend/tests/test_held_notes.py` change the test `test_the_types_that_take_the_n_loudest_notes_are_seven_and_include_spirograph` to eight types that also include `"rhythm-circles"` (rename it), and add a test that `notes_of("rhythm-circles", 8, 8, 12)` is 5
- [X] T008 In `backend/app/services/held_notes.py` add `"rhythm-circles"` to `HELD_NOTES_TYPES` (eight types, n = 5 through `LOUDEST_COUNT`), and update the comments and docstrings that count the types ("seven" -> "eight", the list of types in `check_extra_notes`' docstring and the module docstring) in the same edit
- [X] T009 [P] Create `backend/tests/test_tempo_votes.py` with the tests of `check_vote_limit`: accepts 1, 20, 100, `20.0`, `np.int64(7)`; refuses 0, 101, 2.5, `True`, `"20"`, `None`, `nan`, `inf`, `-1` with exactly `The vote limit must be a whole number from 1 to 100.`; returns `int`; and of the constants (18 tempos from 76 to 144 in steps of 4; 120 among them; `NOTE_BEATS` has 10 values: 2, 1, 1/2, 1/4, 3, 3/2, 3/4, 3/8, 1/3, 2/3). Run: green (T006 and T008 are done)

**Checkpoint**: aliases, module skeleton, setting check and the eight held-notes types exist.

---

## Phase 3: User Story 1 - A tempo found by voting on the spacing of the loudest notes (Priority: P1) 🎯 MVP

**Goal**: from start times alone, the votes of the 18 tempos after each start, the first and second tempo, and the vote series.

**Independent Test**: `tests/test_tempo_votes.py` with start times only (no audio).

### Tests for User Story 1

- [X] T010 [P] [US1] In `backend/tests/test_tempo_votes.py` add the tests of `fitting_tempos(lengths, resolution)` (scenarios 3 and the fit rule): shape `(cycles, 18)` and dtype `bool`; for the length 0.5 with resolution 0 exactly the tempos 80, 88, 92 and 120 fit (a hand-written expected array, the inclusive 2 bpm edge at the implied 90 included); the length 0.4167 (an eighth note at 72) with resolution 0 fits the tempos where `60 b / L` is within 2 of a bin, computed by a plain double loop in the test; for the length 0.25 with resolution 0.06 sixteen of the 18 tempos fit; a length of 5 seconds and one of 0.01 with resolution 0 fit none; the half-bin rule and the resolution rule each alone add tempos (a length that fits only by the resolution term at resolution 0.06 and by none at 0); several lengths at once give one row each; a bad input is refused (negative or zero length, `nan`, not 1-D, a negative or non-finite resolution)
- [X] T011 [P] [US1] In `backend/tests/test_tempo_votes.py` add the tests of `vote_tempos(start_times, resolution, limit)` (scenarios 1 to 7): shape `(starts, 18)`, dtype integer; no start -> shape `(0, 18)`; one start -> one row of 0; starts 0 and 0.5 (resolution 0): row 1 has 2 at 80, 88, 92, 120 and 0 elsewhere; `k + 1` votes after `k` cycles for those tempos, 20 after 19 cycles and still 20 after 30 (limit 20); with limit 5 they stop at 5; a tempo that fitted the first spacing and not the next loses exactly one a cycle and never goes below 0 (spacing 0.5 for 10 cycles then 0.4 for 12: 80 falls from 11 to 0 in 11 cycles, never negative); a length that fits one tempo with several note values gives 2 once (a length that fits a tempo as both a quarter and a triplet: the increase is 1 net, not 3); every entry is a whole number from 0 to the limit for random start lists (a property test over 50 seeded lists, limits 1, 7, 20, 100); the input is not changed; a limit outside 1..100, non-increasing start times, a negative resolution are refused
- [X] T012 [P] [US1] In `backend/tests/test_tempo_votes.py` add the tests of `ranked_tempos(votes)` and `vote_series(start_times, ranked)`: shape `(starts, 2)`; the most votes first, the next second; a tie goes to the lower tempo (two tempos at 3 votes: the lower is first); a place with 0 votes holds 120 (all zero rows give `[120, 120]`; one tempo with votes and the rest 0 gives `[that tempo, 120]`; if 120 itself is first and the second has no votes the row is `[120, 120]`); a hand-made votes array for 4 starts gives the expected table; `vote_series`: shape `(starts, 4)`, columns first tempo, its change, second tempo, its change; the change is `(level_i - level_{i-1}) / (s_i - s_{i-1})` and 0 in row 0 (a first tempo that goes 120 -> 124 over 0.5 s gives 8.0); no starts gives shape `(0, 4)`; refusals (a ranked array whose rows differ from the number of starts, non-finite numbers)

### Implementation for User Story 1

- [X] T013 [US1] In `backend/app/services/tempo_votes.py` add `fitting_tempos(lengths: ArrayLike, resolution: float) -> FitMatrix` (research Decision 3: `abs(60 b / L - T) <= HALF_BIN + SLACK or abs(60 b / T - L) <= resolution / 2 + SLACK`, any over `NOTE_BEATS`, vectorized to `(cycles, 18, 10)` then reduced; refuse anything that is not a 1-D array of finite lengths above 0 and a finite resolution of 0 or more, with `ValueError` messages) with its docstring (`Arrays:` and `Returns:`)
- [X] T014 [US1] In `backend/app/services/tempo_votes.py` add `vote_tempos(start_times: ArrayLike, resolution: float, limit: int) -> TempoVotes` (research Decision 4: check the starts - finite, 1-D, strictly increasing - and the limit with `check_vote_limit`; the lengths are `np.diff(start_times)`, the fit array is made once, then the loop `votes = np.maximum(votes - 1, 0); votes = np.where(fit[i], np.minimum(votes + 2, limit), votes)`; row 0 is all 0) with its docstring
- [X] T015 [US1] In `backend/app/services/tempo_votes.py` add `ranked_tempos(votes: ArrayLike) -> RankedTempos` (research Decision 5: `np.argsort(-votes, axis=1, kind="stable")` over the ascending tempos, the first two columns, a place with 0 votes replaced by `NO_VOTES_TEMPO`) and `vote_series(start_times: ArrayLike, ranked: ArrayLike) -> CircleSeries` (the four columns of [data-model.md](data-model.md); the change is `np.diff(level) / np.diff(start_times)` in rows 1 on) with their docstrings
- [X] T016 [US1] Run `tests/test_tempo_votes.py`, `tests/test_type_hints.py` and `tests/test_documentation.py`: green

**Checkpoint**: the voting works from start times alone (user story 1).

---

## Phase 4: User Story 3 - The notes that start are the sustained loudest notes (Priority: P1)

**Goal**: the start times of a file from its note strengths, with the held loudest notes and Extra notes k.

**Independent Test**: synthetic note strengths with a sustained note, a chord, a returning note and silence.

### Tests for User Story 3

- [X] T017 [P] [US3] In `backend/tests/test_tempo_votes.py` add the tests of `note_starts(values, extra, frame_rate)` (scenarios 1 to 4): returns `StartTimes` `(starts,)` float64 strictly increasing; a note that sounds for 60 frames gives one start at `(f + 0.5) / frame_rate` of its first frame; two notes that enter in the same frame give one start; a note that stops (strength 0), is absent for a frame and sounds again gives a second start; a note that stays among the loudest never starts again even when louder notes come and go (with extra 2, as in feature 044's held notes: build a case where the sustained note falls to rank 6 or 7 and stays held, and one where it falls beyond n + k and returns: one start, then two); the first frame's sounding notes are the first start; silence or all zeros gives no start (shape `(0,)`); a frame whose selection has only places padded with strength 0 gives no start; only the first 84 columns count (a sound in columns 84 to 87 gives no start); the input is not changed; the same input gives the same output; `extra` outside 1..5 (n is 5), a values array that is not 2-D with 88 columns, negative or non-finite, or a frame rate that is not positive are refused with `ValueError`; with extra 1 and extra 5 the starts of a crafted case differ (the held note makes the difference)

### Implementation for User Story 3

- [X] T018 [US3] In `backend/app/services/tempo_votes.py` add `note_starts(values: NoteStrengths, extra: int, frame_rate: float) -> StartTimes` (research Decision 2: check the inputs; `selection = held_notes.hold_loudest(values[:, :84], LOUDEST_COUNT, extra)`; `sounding` a boolean `(frames, 84)` made by `put_along_axis` of `values[row, selection] > 0`; `entering = sounding & ~previous` with `previous` the shifted array and a row of False before the first frame; a start where any note enters; time `(frame + 0.5) / frame_rate`) with its docstring; `extra` is checked with `held_notes.check_extra_notes(extra, LOUDEST_COUNT)`
- [X] T019 [US3] Run `tests/test_tempo_votes.py`, `tests/test_held_notes.py`, `tests/test_type_hints.py`, `tests/test_documentation.py`: green

**Checkpoint**: the starts come from the sustained loudest notes (user story 3, without the page and the job).

---

## Phase 5: User Story 2 - Rhythm Circles shows six circles (Priority: P1)

**Goal**: six rings from the outside in: first tempo, its change, second tempo, its change, local peak, its change.

**Independent Test**: `tests/test_rhythm_circles*.py`: the series and angles of the six columns, and the pictures.

### Tests for User Story 2 (rewrite the tests of the four-ring picture first; they change meaning)

- [X] T020 [P] [US2] Rewrite `backend/tests/test_rhythm_circles.py` for six circles: `CIRCLES == 6`, `LAYERS == 3`, `DEFAULT_SPEEDS == (120.0, 0.0, 120.0, 0.0, 60.0, 0.0)`; `peak_series(times, tempos)` gives `(peaks, 2)`: the peak's rate and its change `(x[i] - x[i - 1]) / (t[i] - t[i - 1])`, 0 for the first, refusals as before (not increasing, not finite, tempos not above 0, a shape mismatch), no peaks gives `(0, 2)`, **the tempo finder is not used** (the series does not depend on `tempo_finder`: a test that patches `tempo_finder.find_tempo` to raise and still gets the series); `circle_speeds` and `circle_angles` with `defaults` (a `defaults` tuple of 4 and one of 2 give widths 4 and 2; the step function, the running total of `speed / 60`, continuous at each event, as the old tests but for both widths; a series whose width differs from `len(defaults)` is refused); `rhythm_angles(peaks, frame_rate, frames, values, extra_notes, vote_limit)` gives `RhythmData` with `angles` `(frames, 6)`: columns 4 and 5 equal the angles that the peak circles had (`circle_angles(peak_times, peak_series, moments, (60, 0))`), columns 0 to 3 equal `circle_angles(start_times, vote_series, moments, (120, 0, 120, 0))` for a synthetic values array whose starts are known (notes entering every 0.5 s); with no peaks the last two columns turn at 60 and 0; with no starts the first four turn at 120, 0, 120, 0 (silent values); a first tempo that changes from 120 to 124 at a start gives a change column of 8 rpm for the 0.5 s between it and the next start; bad frame rate, frames, values shape, extra or limit are refused; the old tests of the current tempo circles are deleted (the finder is still tested in `test_tempo_finder.py`)
- [X] T021 [P] [US2] Rewrite `backend/tests/test_rhythm_circles_rendering.py` for six rings: `ring_colors_rows()` gives 6 rows at `rint((k - 1) / 5 x 255)` and the notch rows at the opposite positions; `_geometry` has 6 rings, `ring_width = outer / 6`, no ring touches the 10-pixel margin; a picture of angles `(6,)` has six visible rings in the stated order (sample the pixels at the radius of each ring at the angle of its notch and away from it: ring color vs notch color); the notch is an eighth of the circle; determinism and threads = serial; frames named `frame_000000.png`... of 600 x 400; a `RhythmData` whose angles are not `(frames, 6)` is refused with the message that names six; the time for 100 frames is within 5 seconds (as the old test)
- [X] T022 [P] [US2] Add to `backend/tests/test_rhythm_circles.py` the comparison with the old peak circles: load `specs/047-rhythm-note-voting/tools/old_peak_angles.npy` (T003) and check that columns 4 and 5 of `rhythm_angles()` for the same peaks are **equal** to the old columns 2 and 3 (the same fixed `LocalPeaks` as `old_peak_angles.py`; skip the test with a clear message if the file is missing)

### Implementation for User Story 2

- [X] T023 [US2] In `backend/app/services/rhythm_circles.py` change the constants and the series: `LAYERS = 3`, `CIRCLES = 6`, `VOTE_DEFAULTS = (START_TEMPO, 0.0, START_TEMPO, 0.0)`, `PEAK_DEFAULTS = (DEFAULT_RATE, 0.0)`, `DEFAULT_SPEEDS = VOTE_DEFAULTS + PEAK_DEFAULTS`, the import of `find_tempo` removed (`START_TEMPO` kept from `tempo_finder`), and `peak_series()` rewritten to return `CircleSeries (peaks, 2)` (the peak's rate and its change) with its docstring; `_series()` takes the width from the `defaults` it is given
- [X] T024 [US2] In `backend/app/services/rhythm_circles.py` give `circle_speeds(times, series, moments, defaults=DEFAULT_SPEEDS)` and `circle_angles(times, series, moments, defaults=DEFAULT_SPEEDS)` the `defaults` parameter (`tuple[float, ...]`, typed), take the width from `len(defaults)` in place of `CIRCLES` (`np.zeros((1, len(defaults)))`), and update their docstrings and the `_series` check message
- [X] T025 [US2] In `backend/app/services/rhythm_circles.py` change `rhythm_angles(peaks: LocalPeaks, frame_rate: float, frames: int, values: NoteStrengths, extra_notes: int, vote_limit: int) -> RhythmData`: check the frame rate and frames as now, `check_vote_limit`, make the moments, the starts (`tempo_votes.note_starts(values, extra_notes, frame_rate)`; `values` must have `frames` rows, else `ValueError`), the resolution `max(1 / frame_rate, BUFFER_INTERVAL_MS / 1000)`, `votes = vote_tempos(...)`, `ranked = ranked_tempos(votes)`, `vote_series(...)`, the two angle groups with `circle_angles(..., VOTE_DEFAULTS)` and `circle_angles(..., PEAK_DEFAULTS)` and join them with `np.hstack` into `CircleAngles (frames, 6)`; update `RhythmData`'s docstring (`(frames, 6)`; the columns), `_check_data`, `ring_colors_rows` (`p = (k - 1) / 5` through `CIRCLES - 1`), `_geometry`, `_frame` and `write_rhythm_frames` docstrings and the messages that say four
- [X] T026 [US2] Rewrite the module docstring of `backend/app/services/rhythm_circles.py` (six circles, the three layers, the starts and the votes in a paragraph, the peak circles unchanged, the speeds constant between events: starts for the first four rings and peaks for the last two) and its `Order of operations:` list in the same edit (1. the peak times and rates; 2. the peak circles' series - `peak_series()`; 3. the starts, the votes and the vote circles' series - `tempo_votes.note_starts()` ... `vote_series()`; 4. the moments; 5. the angles of the two groups and their join - `circle_angles()` - `CircleAngles (frames, 6)`; 6 to 8 as before with six rings)
- [X] T027 [US2] Run `tests/test_rhythm_circles.py`, `tests/test_rhythm_circles_rendering.py`, `tests/test_type_hints.py`, `tests/test_documentation.py`: green

**Checkpoint**: the picture has six rings from the starts and the peaks (user story 2, without the job).

---

## Phase 6: User Story 4 - The vote limit setting, the request and the page (Priority: P2)

**Goal**: the setting through the request, the response and the page, and Extra notes for Rhythm Circles.

**Independent Test**: `tests/test_rhythm_circles_api.py`; the frontend tests.

### Tests for User Story 4

- [X] T028 [P] [US4] Rewrite the parts of `backend/tests/test_rhythm_circles_api.py` that assume four circles or one measurement: the job makes the averaged frames once and `rhythm_angles` gets `(peaks, fps, frames, values, extra_notes, vote_limit)` (patch `rhythm_angles` as the file does now and check its arguments: the frame count rows of `values`, `extra_notes` 2 by default, `vote_limit` 20 by default); the local peaks are still measured **once** with the request's Minimum distance and `DEFAULT_PROMINENCE`; add: `vote_limit` sent as `5` is passed and echoed as `5`; not sent is `20` in the answer; `0`, `101`, `2.5`, `abc`, an empty string and `nan` are refused with 400 and `The vote limit must be a whole number from 1 to 100.` **before the file is read** and with no job folder left; the setting is checked and echoed for every image type (a `contour` job with `vote_limit=7` answers 7 and a bad value is refused for it too); `extra_notes=5` is accepted and `6` refused with `The extra notes must be a whole number from 1 to 5.` for `rhythm-circles` while `6` is still accepted for `contour`; a different `vote_limit` changes the pictures of a file with notes (a limit of 1 vs 20 on a synthetic sound whose spacing changes makes different frames); the real pipeline makes six rings (an end-to-end file of 3 s)
- [X] T029 [P] [US4] Add the key `vote_limit` to the tests that spell out the exact keys of the answer or list the settings of every image type: `backend/tests/test_colormap_api.py`, `test_contour_api.py`, `test_interpolation_api.py`, `test_note_count_api.py`, `test_resolution_api.py`, `test_spirograph_api.py`, `test_extra_notes_api.py` (grep for `spirograph_fade` and `extra_notes` in `backend/tests` to find every place) and `frontend/src/api.test.ts`, `frontend/src/App.test.ts`
- [X] T030 [P] [US4] Frontend tests: in `frontend/src/utilities/validation.test.ts` add `validateVoteLimit` (accepts 1, 20, 100, `"20"`, `" 7 "`; refuses 0, 101, 2.5, `"abc"`, `""`, `"nan"`, with `The vote limit must be a whole number from 1 to 100.`), `formatVoteLimit`, the range constant `VOTE_LIMIT_RANGE` (1 to 100, default 20), `usesHeldNotes("rhythm-circles")` true (and the list in its test), `heldNotesCount("rhythm-circles", 8, 8, 12)` is 5, `isRhythmType` unchanged; in `groups.test.ts` the groups of `rhythm-circles` are `analysis`, `colormap`, `image-type`, `rhythm`, `held-notes`, `concentric-peaks` (the old test says no group of its own), the `vote-limit` control is in the `rhythm` group, `extra-notes` in `held-notes`, `peak-distance` in `concentric-peaks`, and no other type has the `rhythm` group or the control; in `help.test.ts` the help text of Vote limit (it says 1 to 100, default 20, Only used by Rhythm Circles, that a low limit lets the tempo change quickly and a high one makes it stay), and the texts of the image type, of Extra notes and of Minimum distance name Rhythm Circles for the voting (the image type text mentions six circles, the two highest-voted tempos and no longer the current tempo); in `SettingsForm.test.ts` the Rhythm Circles group with the slider `vote-limit`, its readout, its help, its place before Held notes, and the other types without it; in `api.test.ts` the form field `vote_limit` sent for every type and the result type; in `App.test.ts` the result summary line for Rhythm Circles shows the vote limit and the other types do not

### Implementation for User Story 4

- [X] T031 [US4] In `backend/app/routers/jobs.py`: import `check_vote_limit`, `DEFAULT_VOTE_LIMIT`, `VOTE_LIMIT_MESSAGE` from `tempo_votes`; add the form field `vote_limit: str | None = Form(None)` (as `spirograph_fade` is declared) and `_parse_vote_limit(text, sent)` (not sent: the default; otherwise `check_vote_limit(float(text or ""))`, any `ValueError` a 400 with `VOTE_LIMIT_MESSAGE`; a non-number text is refused the same way); call it with the other parsers **before the file is read**; make `values = average_frames(result, fps, frames)` once; call `rhythm_angles(measure_local_peaks(...), fps, frames, values, extra_notes_value, vote_limit_value)`; pass `values` to `write_frames` in place of its inline `average_frames(...)`; add `"vote_limit": vote_limit_value` to the answer; update the docstrings and comments (the Rhythm Circles comment in step 6: the local peaks for the two inner rings **and** the held loudest notes for the voting; the endpoint's list of settings)
- [X] T032 [US4] In `backend/app/services/frame_rendering.py` update the docstrings only (the Rhythm Circles lines of the module docstring, of `write_frames` and of the branch comment: six rings, `RhythmData` `(frames, 6)`, made by `rhythm_circles.rhythm_angles` from the local peaks and the sustained loudest notes), and the message of the frame-count check if it names four
- [X] T033 [P] [US4] In `frontend/src/utilities/validation.ts` add `VOTE_LIMIT_RANGE = { min: 1, max: 100, default: 20 }` (in the form of the other ranges), `validateVoteLimit`, `formatVoteLimit`, add `"rhythm-circles"` to `usesHeldNotes` and its doc comment (eight pictures), update `heldNotesCount`'s comment, and the doc comment of `isRhythmType` and of the image type list (six rings turned by the two highest-voted tempos found from the sustained loudest notes, and the local peak)
- [X] T034 [P] [US4] In `frontend/src/utilities/groups.ts` add the group `rhythm` (title `Rhythm Circles`, control `vote-limit`) for the type, ordered after the image type group and before Held notes, make `groupsFor("rhythm-circles")` `analysis`, `colormap`, `image-type`, `rhythm`, `held-notes`, `concentric-peaks` and `groupOf("vote-limit", type)`, and update the comments that say Rhythm Circles has no group of its own
- [X] T035 [P] [US4] In `frontend/src/api.ts` add `vote_limit` to the request settings (sent for every type as the other settings, as text) and to the result type; in `frontend/src/App.vue` keep the settings state with `voteLimit` (default 20), send it, and show `Vote limit` in the result summary for Rhythm Circles only; in `frontend/src/components/SettingsForm.vue` add the Rhythm Circles group with the slider `vote-limit` (1 to 100, step 1, the readout, the info button, the validation message) for this type only, in the markup order of `groups.ts`
- [X] T036 [P] [US4] In `frontend/src/utilities/help.ts` add `voteLimitHelp` (1 to 100, default 20; Only used by Rhythm Circles; what the votes are: every time a new note starts each tempo loses one vote and each tempo at which the time since the previous note could be a half, quarter, eighth or sixteenth note, dotted or a triplet gains two, up to this limit; a low limit lets the tempo change quickly, a high one makes it stay; no apostrophes), rewrite the Rhythm Circles part of the image type help (six rings from the outside in: the two highest-voted tempos each with its rate of change, then the local peak and its rate of change; the tempo of 76 to 144 found from the starts of the sustained loudest notes; the current-tempo rings of the tempo finder are gone), and name Rhythm Circles in the help texts of Extra notes and Minimum distance
- [X] T037 [US4] Run `backend/tests/test_rhythm_circles_api.py`, the tests of T029 and, in `frontend/`, `npx vue-tsc --noEmit` and `npx vitest run`: green

**Checkpoint**: the job, the response and the page work with the setting (user story 4).

---

## Phase 7: User Story 5 - The other image types are unchanged (Priority: P2)

**Goal**: nothing but Rhythm Circles moved.

- [X] T038 [P] [US5] Run `specs/047-rhythm-note-voting/tools/verify_drawing.py` (T002): every compared type matches its baseline hash. Run `specs/041-code-readability-docs/tools/verify_frames.py` against its baseline: the other types match; and run `tests/test_tempo_finder.py`, `tests/test_tempo_files.py`, `tests/test_polychord*.py`, `tests/test_local_peaks.py`: green and unchanged. Any difference is a regression to fix, not to record
- [X] T039 [P] [US5] In `backend/tests/test_rhythm_circles_api.py` (or a new section of it) add the test that the pictures of `decay`, `contour` and `polychord` for one synthetic sound are the same with `vote_limit=1` and `vote_limit=100` (the setting is only used by Rhythm Circles), and that the frames of `polychord` with `extra_notes` unchanged are the same as made by calling `write_frames` directly

**Checkpoint**: the other types are unchanged (user story 5).

---

## Phase 8: Documentation, the sample files and the final checks

- [X] T040 [P] Create `specs/047-rhythm-note-voting/tools/verify_votes.py` (research Decision 11): from the repository root with the backend's interpreter it reads `backend/audio/sonata.wav` and `almost2.wav` the way the job does (`read_wav`, `analyze_channels` with the 60 ms step, `floor_analysis`, `average_frames` at 30 frames a second), makes `note_starts` (extra 2), `vote_tempos` (resolution `max(1 / 30, 0.06)`, limit 20) and `ranked_tempos`, and prints for each file: the number of starts, the share of the starts after the first 10 seconds at which the first or the second tempo is within 10% of 116 (sonata) / 90 (almost2), how many times the first tempo changes, a hash of the vote table and whether a second run gives the same hash; with the limits 5, 20 and 100 as a second table. Run it and keep the output in `specs/047-rhythm-note-voting/verify_votes-output.txt`
- [X] T041 Create `backend/tests/test_tempo_votes_files.py` (as `test_tempo_files.py` is): for `sonata.wav` and `almost2.wav` (skipped with a message when the file is missing) run the same path as T040 and **report** the numbers with `print`/`record_property`, asserting only the invariants: 18 tempos, every vote a whole number from 0 to the limit, the ranked tempos in 76 to 144 or 120, two runs identical
- [X] T042 Rewrite the Rhythm Circles block of the `Pipeline overview:` in `backend/app/services/image_types.py` for six circles (MEASURE: the local peaks and the held loudest notes - `held_notes.hold_loudest()` through `tempo_votes.note_starts()`; DRAW stages: the starts, `fitting_tempos`, `vote_tempos`, `ranked_tempos`, `vote_series`, the peak series, `circle_angles` of the two groups, the rings) and update the counts, the lists of types that take the held notes (eight) and any line that says four circles or the tempo finder; check `tests/test_documentation.py` and run `specs/041-code-readability-docs/tools/trace_pipeline.py` and `shape_probe.py` for the Rhythm Circles job to see that the order and the shapes written are the real ones (fix the text, not the tool)
- [X] T043 [P] Update `README.md`: the Rhythm Circles paragraph (six circles, the voting rule in a few sentences with the 18 tempos, the note values, the minus one and plus two, the Vote limit, the starts from the sustained loudest notes, the Extra notes setting and the Vote limit slider, the local peak circles unchanged, the tempo finder no longer drawn, the numbers measured in T040), the request field `vote_limit` and the answer key, the test files; and add a line to `specs/047-rhythm-note-voting/spec.md` Status: `Implemented` when everything is done
- [X] T044 [P] Run the quickstart's sections 1 to 4 ([quickstart.md](quickstart.md)): the voting tests, the circle tests, `verify_votes.py` and the whole backend suite (about 10 minutes, in the background with the output to `specs/047-rhythm-note-voting/full-run.txt`): the failing ids must be **exactly** those of `baseline-failures-before.txt` (compare with a script, save `baseline-failures-after.txt`), and the frontend `npx vue-tsc --noEmit` and `npx vitest run` pass
- [X] T045 Save the decisions to the memory file `rhythm-note-voting-decisions.md` (update it: implemented, the measured numbers of T040, the traps found) and mark every task of this file `[X]`

---

## Dependencies & Execution Order

- **Phase 1** (baselines) first, before any edit of `backend/app` or `frontend/src`.
- **Phase 2** blocks everything: the aliases (T005) and the module skeleton (T006) before any function of the module; T008 before T018 and T028.
- **Phase 3 (US1)** needs Phase 2. Tests T010 to T012 first (they fail), then T013 to T015 in order (same file), then T016.
- **Phase 4 (US3)** needs T006 and T008 (it is independent of Phase 3 in code but writes to the same file: do it after T016).
- **Phase 5 (US2)** needs Phases 3 and 4 (`rhythm_angles` calls their functions) and T003 (the old angles saved before the first edit of `rhythm_circles.py`).
- **Phase 6 (US4)** needs Phase 5 for T031; the frontend tasks T033 to T036 only need Phase 2's decisions and can run beside the backend work; T029 and T030 (tests) before their implementation.
- **Phase 7 (US5)** and **Phase 8** after Phase 6.

### Parallel opportunities

- Setup: T002, T003 and T004 together.
- Foundational: T007 and T009 after T006; T005 and T006 are different files (T005 first by the rule that an alias exists before its first use in a signature).
- Phase 3 tests: T010, T011 and T012 together (the same file, so write them one after the other and run once).
- Phase 5 tests: T020, T021 and T022 together (three files and one new test).
- Phase 6: T028, T029, T030 together; T033 to T036 together (different files).

## Implementation Strategy

### MVP first (User Story 1 and 3 together are the data; User Story 2 is how it is seen)

1. Phases 1 and 2.
2. Phase 3: the voting from start times (the heart of the change). **Stop and validate** with `test_tempo_votes.py`.
3. Phase 4: the starts from the held notes. Validate with the synthetic sounds.
4. Phase 5: the six circles. Look at a render by eye.
5. Phase 6: the setting and the page. Phase 7: the other types. Phase 8: the report on the sample files, the documents, the full run.

### Notes

- The tolerance of the fit rule (spec FR-006) is the most uncertain choice: T040 reports how well the voting separates tempos on the two real files; if it does badly, the levers are `HALF_BIN`, the resolution term, `NOTE_BEATS` and the vote limit, each one constant or argument, and the change is a documented revision, not a silent one.
- Never hard-code `local_peaks.DEFAULT_PROMINENCE` in a new test.
- `array_types.py` is CRLF. `write_frames` gets no new parameter.

## Outcome (2026-11-25)

All 45 tasks done. Differences from the plan, none of them a change of the rule: the page group id is `rhythm-circles` (research Decision 14); T039 is covered by `test_the_other_image_types_make_the_same_pictures_whatever_the_vote_limit` in `test_rhythm_circles_api.py`; `specs/041-code-readability-docs/tools/verify_frames.py` was not run (its baseline predates feature 043, so it cannot be a no-change check; `tools/verify_drawing.py` of this feature was used, with Rhythm Circles skipped by design); the page was not looked at in a browser (quickstart section 5). Results: whole backend suite 32 failed / 5727 passed, the failing ids exactly those of `baseline-failures-before.txt` (saved as `baseline-failures-after.txt`); frontend 1030 tests pass and `vue-tsc` is clean; sample files in `verify_votes-output.txt` (sonata 64% near 116, almost2 14 to 19% near 90).

