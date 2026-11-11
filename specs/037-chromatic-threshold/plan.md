# Implementation Plan: Chromatic Decay Threshold

**Branch**: `037-chromatic-threshold` (no git branch created; spec directory name only) | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/037-chromatic-threshold/spec.md`

## Summary

The **Threshold** setting (0 to 10 percent, 0 off) starts to work for **Chromatic Decay**: in `circle_points` (and `circle_tapers`, which shares the simulation) every smoothed note value **strictly below `threshold / 100` of the largest value of the whole array passed in** is set to 0 **before** the octaves are combined into letters, so a faint note adds nothing to its letter, a letter with nothing above the floor does not count among the five loudest, and the points, the taper and the picture follow.

How it is done (research Decisions 1 to 5):

- **A `threshold` argument** (default 0) on `circle_points`, `circle_tapers` and the shared `_simulate` in `chromatic_decay.py`, applied by one small function, `apply_threshold(values, threshold)`, written in the module (the existing `frame_rendering.hidden_below` cannot be imported there without a circular import; the rule is the same and a test compares the two). The check of the number is the existing one (`The threshold must be a number from 0 to 10.`).
- **The job and `write_frames`** already carry `threshold` (validated for every type, ignored for this one); the `chromatic-decay` branch of `write_frames` passes it on with the smoothed values. **No new request or response field.**
- **The page**: the Threshold control already exists and shows wherever a type's group lists the control `threshold`: the group `chromatic-decay` gets it (the controls are listed in the order the page draws them: Threshold, then Decay rate), the summary shows the threshold for the type, and the help says what it does for Chromatic Decay.
- **Tests first**: the rule against a loop oracle (strictly below, exactly at, the whole-file reference, all columns), the effect on gains/points/taper (a faint letter stays at 0, the other letters unchanged, a threshold of 0 identical to none), the job (the field changes the frames, a bad value is refused, no field means identical frames, the other types unchanged byte for byte), the frontend (group, summary, help).
- **Documentation**: the README and the help texts.

## Technical Context

**Language/Version**: Python 3.10 (backend, FastAPI); Vue 3 / TypeScript (frontend).

**Primary Dependencies**: numpy (already used). Nothing new.

**Storage**: None.

**Testing**: pytest (`backend/tests`), vitest (`frontend`), as for features 032 to 036 (`python -B`, cleared `__pycache__`, the mutation helpers of the scratchpad).

**Target Platform**: The existing local web service.

**Project Type**: Web application (backend and frontend).

**Performance Goals**: one comparison pass over `(frames, 88)` values; no measurable change.

**Constraints**: a threshold of 0 (the default, or no field) gives results identical to before; the decay, the beat and the rings do not depend on the threshold; the other image types give identical output; deterministic.

**Scale/Scope**: about 25 lines in `chromatic_decay.py`, one in `frame_rendering.py`, small frontend edits; most of the work is tests.

## Constitution Check

The constitution file (`.specify/memory/constitution.md`) is still the unfilled template: no principles, no gates. The project's own practice is followed: tests first, an independent oracle, mutation checks, nothing changed outside the feature, documentation with the change.

Re-check after design: no violation.

## Project Structure

### Documentation (this feature)

```text
specs/037-chromatic-threshold/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── chromatic-threshold.md  # Phase 1 output: the library interface and the request
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/services/
│   ├── chromatic_decay.py            # CHANGED: apply_threshold, check_threshold, the threshold argument of circle_points / circle_tapers / _simulate
│   └── frame_rendering.py            # CHANGED: the chromatic-decay branch passes the threshold; docstring
└── tests/
    ├── test_chromatic_threshold.py   # NEW: the rule, its effect on gains / points / tapers
    ├── test_chromatic_decay_api.py   # CHANGED: threshold applies (it was in the list of ignored settings); the request, refusal, echo
    └── (others)                      # only where a test says Chromatic Decay ignores the threshold

frontend/src/
├── utilities/groups.ts               # CHANGED: the chromatic-decay group lists the threshold control
├── utilities/help.ts                 # CHANGED: the threshold help and the Chromatic Decay help
├── App.vue                           # CHANGED: the summary shows the threshold for Chromatic Decay
└── (tests)                           # groups.test.ts, SettingsForm.test.ts, App.test.ts, help.test.ts, validation.test.ts

README.md                             # CHANGED: Chromatic Decay paragraph
```

**Structure Decision**: The existing layout; the rule belongs to the Chromatic Decay module beside the other number functions, and the page reuses its existing control.

## Complexity Tracking

No violations to justify.
