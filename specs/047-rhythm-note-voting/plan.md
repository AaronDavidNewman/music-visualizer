# Implementation Plan: Rhythm Circles Tempo Voting from Sustained Loudest Notes

**Branch**: `047-rhythm-note-voting` (no git branch created; spec directory name only) | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/047-rhythm-note-voting/spec.md`

## Summary

**Rhythm Circles** gets a tempo found by **voting on the spacing of the sustained loudest notes**. A **start** is a frame in which a sounding note enters the held selection of the
five loudest notes (feature 044, Extra notes k); at every start after the first, the time since the previous start is a note length, one vote is taken from each of the 18 tempos
(`72 + 4n`, 76 to 144; not below 0) and each tempo at which that length can be a half, quarter, eighth or sixteenth note gets 2 (1 if it fits only as a dotted note or a triplet)
(1/3, 2/3 of a beat), up to a **Vote limit** (a new setting, default 20). The picture has **six** rings from the outside in: the **first** and **second** highest-voted tempos, each
followed by its rate of change, then the **local peak** and its rate of change (unchanged). The tempo finder's current-tempo pair is dropped from the picture.

How it is done (research Decisions 1 to 12):

- **One new pure module, `backend/app/services/tempo_votes.py`**: `check_vote_limit`, `note_starts`, `fitting_tempos`, `vote_tempos`, `ranked_tempos`, `vote_series`: numbers only,
  testable without audio. It imports `held_notes.hold_loudest` and `tempo_finder.START_TEMPO` and **changes neither**.
- **`rhythm_circles.py`** grows from four to six circles: `CIRCLES = 6`, `DEFAULT_SPEEDS = (120, 0, 120, 0, 60, 0)`, rings at `(k - 1) / 5`; `circle_speeds` and `circle_angles`
  take a `defaults` tuple so that the four vote circles (events: the starts) and the two peak circles (events: the peaks) each have their own step function, then are joined;
  `peak_series` gives the two peak columns and no longer calls the tempo finder; `rhythm_angles` takes the note values, Extra notes and the Vote limit.
- **The job**: makes the averaged frames once, passes them to `rhythm_angles` (with the one local-peaks measurement it already makes) and to `write_frames`; parses, refuses
  before the file is read, and echoes `vote_limit`; Rhythm Circles joins `held_notes.HELD_NOTES_TYPES` (Extra notes 1 to 5).
- **The page**: the Vote limit slider in a Rhythm Circles group (this type only), then Held notes and Local peaks; the mirror validator, help texts, the result line.
- **Tests first**: the fit table and the exact 0.5 s case (80, 88, 92, 120), the vote rules (subtract, add, caps, never below 0), ranking and the 120 default, the starts of
  synthetic sounds (sustained, chord, returning note, silence), the six-ring series and angles, the pictures, the job (the setting at and beyond its limits, refusal before
  the file is read, the response, Extra notes 1 to 5), the frontend; the two sample files **reported**, not gated.
- **Documentation**: the `tempo_votes.py` docstring (`Order of operations:`), the five new aliases and the widened ones in `array_types.py`, the Rhythm Circles block of the
  pipeline overview in `image_types.py`, `rhythm_circles.py`, `held_notes.py`, `frame_rendering.py` and `jobs.py` docstrings, the README, the help text.

## Technical Context

**Language/Version**: Python 3.10 (backend, FastAPI); Vue 3 / TypeScript (frontend).

**Primary Dependencies**: numpy, Pillow (already used by `rhythm_circles.py`); `held_notes`, `tempo_finder` (a constant only), `buffer_interval` (the 60 ms), `local_peaks`.
Nothing new to install.

**Storage**: None (PNG frames in the job's temporary folder, as for every type).

**Testing**: pytest (`backend/tests`, run with `backend/.venv/Scripts/python.exe`, `-p no:cacheprovider`), vitest (`frontend`), as for features 032 to 046. **The working tree has 32
tests that fail before any change** (`specs/046-spirograph/baseline-failures-after.txt`, copied as this feature's `baseline-failures-before.txt`): "no regression" means exactly
those ids and nothing else. New tests never hard-code `local_peaks.DEFAULT_PROMINENCE`. The tests of the four-ring picture (`test_rhythm_circles*.py`) change meaning and are
rewritten; `test_tempo_finder*.py` and the Polychord tests are untouched.

**Target Platform**: The existing local web service.

**Project Type**: Web application (backend and frontend).

**Performance Goals**: the starts, the fit array and the votes for a 5-minute file (a few thousand starts at most) in milliseconds; Rhythm Circles for a 5-minute file does not take
more than 5% longer than before (SC-008; the drawing of six rings costs what four did).

**Constraints**: frames 600 x 400 with the count, names and timing of the other types; deterministic; every other image type unchanged byte for byte (FR-013); the local peaks
logic untouched; every function typed and every array documented (feature 041); the response of the other types changes only by the new echoed `vote_limit`.

**Scale/Scope**: one new module (about 150 lines), edits in `rhythm_circles.py`, `array_types.py`, `held_notes.py`, `image_types.py`, `jobs.py` and `frame_rendering.py` (docstring), and
the frontend's `api.ts`, `SettingsForm.vue`, `groups.ts`, `validation.ts`, `help.ts`, `App.vue`; most of the work is tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* (Constitution v1.0.0, 2026-11-15.)

- [X] **I. Every function is typed**: every function of `tempo_votes.py`, and every function added or changed in `rhythm_circles.py`, `jobs.py`, `held_notes.py` and
  `frame_rendering.py`, has a type on every parameter and its return (arrays by alias); `test_type_hints.py` scans them and will pass.
- [X] **II. Every array is documented with its meaning and shape**: the four new kinds of array (`StartTimes`, `TempoVotes`, `FitMatrix`, `RankedTempos`) get their alias with
  `Shape:`, `Meaning:` and `Made by:` in `array_types.py` first (see [data-model.md](data-model.md)); `CircleSeries`, `CircleSpeeds` and `CircleAngles` are re-described for any
  number of circles (the width of the series) in their one place; every function's docstring has its `Arrays:` and `Returns:` lines; `test_documentation.py` will pass.
- [X] **III. Every processing module states its order of operations**: `tempo_votes.py` is a processing module and is added to `PROCESSING_MODULES` in `test_documentation.py`;
  its docstring starts the `Order of operations:` list (check, starts, fit, votes, rank, series); `rhythm_circles.py`'s list is rewritten for six circles; the **Rhythm Circles
  block** of the `Pipeline overview:` in `image_types.py` is rewritten (its MEASURE line now also names the note values and the starts), and the touched `jobs.py`,
  `held_notes.py` and `frame_rendering.py` keep theirs true.
- [X] **Line width** (`documentation-standard.md` section 5): comments and docstrings of the new module wrap at 120 columns (the older files keep their own habit).

Re-check after design: no violation; no Complexity Tracking entry is needed.

## Project Structure

### Documentation (this feature)

```text
specs/047-rhythm-note-voting/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── rhythm-voting.md # Phase 1 output: the request, the response, the library, the picture
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── routers/jobs.py                 # CHANGED: vote_limit parse/echo, averaged frames made once, rhythm_angles with the notes
│   └── services/
│       ├── tempo_votes.py              # NEW: the limit check, the starts, the fit, the votes, the ranking, the vote series
│       ├── rhythm_circles.py           # CHANGED: six circles, defaults per group of events, peak_series (2 columns), rhythm_angles with the notes
│       ├── array_types.py              # CHANGED: four new aliases; CircleSeries/Speeds/Angles re-described for any width
│       ├── held_notes.py               # CHANGED: "rhythm-circles" in HELD_NOTES_TYPES (8 types), docs
│       ├── frame_rendering.py          # CHANGED: docstrings (six circles, RhythmData (frames, 6)); no new parameter
│       └── image_types.py              # CHANGED: the Rhythm Circles block of the overview
└── tests/
    ├── test_tempo_votes.py             # NEW: limit, starts, fit, votes, ranking, series
    ├── test_tempo_votes_files.py       # NEW: sonata.wav / almost2.wav, reported
    ├── test_rhythm_circles.py          # CHANGED: six series and angles
    ├── test_rhythm_circles_rendering.py# CHANGED: six rings
    ├── test_rhythm_circles_api.py      # CHANGED: the setting, Extra notes 1..5, the response
    ├── test_held_notes.py              # CHANGED: eight types
    ├── test_documentation.py           # CHANGED: tempo_votes.py in PROCESSING_MODULES
    └── (others)                        # tests that spell out the response keys or the held-notes types (listed in tasks.md)

frontend/src/
├── api.ts                              # CHANGED: vote_limit in the request and the result
├── App.vue                             # CHANGED: the result list shows it for this type
├── components/SettingsForm.vue         # CHANGED: the Rhythm Circles group with the slider
└── utilities/
    ├── groups.ts                       # CHANGED: the rhythm group, held notes for the type
    ├── validation.ts                   # CHANGED: validateVoteLimit, usesHeldNotes, the Rhythm Circles description
    └── help.ts                         # CHANGED: the help texts (Vote limit; the image type; Extra notes; Minimum distance)

specs/047-rhythm-note-voting/tools/verify_votes.py   # NEW: the report on the two sample files
```

**Structure Decision**: the web application layout of the repository (backend `services` for pure functions and drawing, `routers/jobs.py` for the request, `frontend/src` for the
page), as for Spirograph (feature 046) and Rhythm Circles (038, 040): one new service module, edits to the Rhythm Circles module, small wiring edits, tests beside the existing ones.

## Complexity Tracking

No violations; nothing to justify.
