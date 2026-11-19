# Implementation Plan: Sustained loudest notes

**Branch**: `044-sustained-loudest-notes` (no git branch; spec directory name only) | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/044-sustained-loudest-notes/spec.md`

## Summary

Six pictures (Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe, Polychord) pick "the n loudest notes (or letters)" of each frame with the same line of code: a stable
`argsort` of the negative strengths, first n. This feature replaces that line by one shared function, `held_notes.hold_loudest(values, count, extra)`, which returns the same kind of array (the
index of the note at each of the n places, loudest first) but keeps a note in its place while it ranks within the loudest n + k of the frame and still sounds; a louder newcomer can only take a
free place. With k = 0 the function gives exactly the old n loudest, so every library function takes a new keyword `extra=0` and nothing changes for a caller that does not pass it. The job passes
the new request field `extra_notes` (a whole number from 1 to n, default 2); the page shows it in a new group, *Held notes*, for those six pictures.

Technical approach, one line each (details in [research.md](research.md)):

1. A new module `services/held_notes.py` with the selection (`hold_loudest`), its check (`check_extra_notes`) and the constants; one new array alias `LoudestIndices` in `array_types.py`.
2. Five call sites change one line and gain an `extra` keyword: `decay.gains`, `chromatic_decay._raw_gains` (and `letter_gains`, `circle_points`), `polar_chords._targets` (and `note_targets`, `polar_bars`),
   `polychord.loudest_letters` (and `write_polychord_frames`); `decay_exp` and the `circle_points` functions pass it through; `frame_rendering.write_frames` takes `extra_notes`.
3. `routers/jobs.py` reads `extra_notes`, refuses a wrong value before the file is read, passes it on and echoes it.
4. The page: group *Held notes* (id `held-notes`) with the control *Extra notes (k)* (id `extra-notes`), shown for the six types; the result list shows it.
5. Documentation, help text and tests are brought in line (constitution rule III in the same piece of work).

## Technical Context

**Language/Version**: Python 3.10 (backend), TypeScript with Vue 3 (frontend)

**Primary Dependencies**: FastAPI, NumPy, Pillow, matplotlib; Vue 3, Vite, Vitest. No new dependency.

**Storage**: none (files in the temp folders, as before).

**Testing**: pytest (`backend/tests`, run with `backend/.venv/Scripts/python.exe -m pytest`), Vitest. Known baseline: 32 failing backend tests after feature 043 (`DEFAULT_PROMINENCE` and `NEIGHBOURS`
ones, listed in `specs/043-decouple-frame-rate/baseline-failures-after.txt`); a fresh baseline is taken before the first edit and compared at the end by test id.

**Target Platform**: local web app (FastAPI + Vue page), developed on Windows. The PowerShell speckit scripts cannot run here (execution policy), so the steps are done by hand.

**Project Type**: web application (`backend/` + `frontend/`).

**Performance Goals**: the selection depends on the previous frame, so it is a loop over frames. Each step works on one row of 84 (or 12) numbers; at the largest job (30,000 frames) it must stay
under about 2 s ([research.md](research.md) decision 2). It is done once for each job and each picture, as the argsort is today.

**Constraints**: with `extra = 0` the selection MUST equal the old stable argsort for every input (FR-012, checked by a test against the old expression and by `verify_drawing.py`); the selection never
has more than n notes and has fewer only when fewer sound (FR-005).

**Scale/Scope**: 1 new module, 1 new alias; edits in 7 backend modules, `jobs.py`, `config`-free; 7 frontend source files; about 12 backend and 8 frontend test files edited, 3 new test files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Every function is typed**: every new function (`hold_loudest`, `check_extra_notes`, the helpers) and every changed signature (a new `extra: int = 0`) is fully typed; the array return is annotated
  with the alias `LoudestIndices`. `test_type_hints.py` will pass.
- [x] **II. Every array is documented with its meaning and shape**: one new kind of array, `LoudestIndices` `(frames, count)` (the index of the note or letter at each place of the selection, loudest first,
  padded with notes that do not sound), gets its alias and its one description (*Shape:*, *Meaning:*, *Made by:*) in `array_types.py` before it is used; every function that takes or returns it documents
  it in `Arrays:` / `Returns:`. `test_documentation.py` will pass.
- [x] **III. Every processing module states its order of operations**: `held_notes.py` is added to the processing list of `test_documentation.py` with its own `Order of operations:`; the modules whose
  steps change (`decay`, `decay_exp`, `chromatic_decay`, `polar_chords`, `polychord`, `frame_rendering`, `jobs`) get their lists updated, and the pipeline overview of `image_types.py` names the new step
  in the stages of the six pictures.

**Other gates**: `test_type_hints.py` and `test_documentation.py` pass; the whole suite is compared with the baseline by test id; `trace_pipeline.py` and `shape_probe.py` are run to compare the documented
order and shapes with the real ones. For "could this move a picture": `specs/043-decouple-frame-rate/tools/verify_drawing.py` (all nine types drawn from fixed note values with the library defaults,
`extra = 0`) MUST still report no difference, which proves that k = 0 changes nothing; `verify_frames.py` goes through the job (default k = 2) and may differ where a note is displaced, which is the
intended change (research decision 9).

**Post-design re-check**: no violation; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/044-sustained-loudest-notes/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── job-api.md       # Phase 1 output: the request field and answer key, the page contract
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── routers/
│   │   └── jobs.py                     # new form field extra_notes, its parser, the check against n, the answer key, docs
│   └── services/
│       ├── held_notes.py               # NEW: hold_loudest(), check_extra_notes(), DEFAULT/MAX constants
│       ├── array_types.py              # NEW alias LoudestIndices (+ "Made by" of the arrays that now come from it)
│       ├── decay.py                    # gains(..., extra=0), circle_points(..., extra=0)
│       ├── decay_exp.py                # exp_gains(..., extra=0), circle_points(..., extra=0)
│       ├── chromatic_decay.py          # _raw_gains / letter_gains / circle_points gain extra=0
│       ├── polar_chords.py             # _targets / note_targets / polar_bars gain extra=0
│       ├── polychord.py                # loudest_letters(..., extra=0), write_polychord_frames(..., extra_notes=0)
│       ├── frame_rendering.py          # write_frames(..., extra_notes=0): checks it, passes it to the six pictures
│       └── image_types.py              # overview: the new stage in the six pictures; no new type
└── tests/                              # see the task list; test_documentation.py module list

frontend/src/
├── api.ts                              # extraNotes / extra_notes
├── App.vue                             # result line "Extra notes (k)" for the six types
├── components/SettingsForm.vue         # group Held notes, control Extra notes (k), validation against n
└── utilities/
    ├── groups.ts                       # group "held-notes", control "extra-notes", the six types
    ├── validation.ts                   # EXTRA_NOTES_RANGE, DEFAULT_EXTRA_NOTES, validateExtraNotes, notesOf, usesHeldNotes
    └── help.ts                         # extraNotesHelp; the five type descriptions say "held"
specs/044-sustained-loudest-notes/tools/
└── reference_selection.py              # NEW: an independent, plain-Python version of the rule, for the tests and a random cross-check
```

**Structure Decision**: the existing web-application layout is kept. One new service module because the constitution gives every processing step a named function in a module with an `Order of
operations:`, and because the six pictures must share one implementation (a second copy of the rule in each module would drift).

## Complexity Tracking

No violations to justify.
