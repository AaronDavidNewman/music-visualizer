# Implementation Plan: Noise Floor

**Branch**: `033-noise-floor` (no git branch created; spec directory name only) | **Date**: 2026-11-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/033-noise-floor/spec.md`

## Summary

A fixed **noise floor** for the note strengths: a note strictly below one thousandth (−60 dB, as amplitudes) of the largest value of the whole file is **0**, for every image type, whether or not it has a Threshold, and the chord measurement holds to the same rule for any array it is given. No setting, no request field, no page change (FR-003, SC-006).

How it is done (research Decisions 1 to 7):

- **A new module, `noise_floor.py`**, with the constant (`NOISE_FLOOR_DB = -60`, `NOISE_FLOOR = 10 ** (-60 / 20)` = 0.001), `apply_noise_floor(values, peak=None)` (a cut copy; strictly below `NOISE_FLOOR × peak` becomes `0.0`; the peak defaults to the largest value of the array, all columns) and `floor_analysis(result)` (the same for an `AnalysisResult`). Pure numpy, no new dependency.
- **One call in the job**, in `backend/app/routers/jobs.py` right after `analyze_channels` and before `average_frames` / `write_frames`: the cut is made on the analysed windows, so the pictures, the Notes limit, the Threshold, the smoothing and the chords all see the same notes, and it is made once. The analysis module, `write_frames` and the pictures are not touched.
- **The chord measurement cuts first too**: `measure_chords` applies `apply_noise_floor` to the strengths it is given before the Notes limit, the Threshold and the combining of octaves into letters, so a letter is made of cut notes only and the guarantee does not depend on who calls it. Its own weaker floor from feature 031 (a millionth of the loudest letter of the window) is removed: the new one covers it entirely. The cut is idempotent, so on the job's already cut strengths it changes nothing.
- **The beat is untouched**: the local peaks are measured from the audio, not from the note strengths.
- **Tests first**: the cut on its own (the boundary, exactly at the floor, idempotence, input not changed, shapes, silent, bad input), the chord measurement (the examples of the spec, the oracle working on independently cut values), a job-level test for every image type with and without a Threshold, and the existing suites run to find the expectations that rested on leakage below the floor (listed in the tasks and the final report).
- **Documentation**: the README (a Noise floor paragraph; the chord paragraph without the millionth) and the 031 documents.

## Technical Context

**Language/Version**: Python 3.10 (backend, FastAPI); the frontend (Vue 3, TypeScript) is not touched.

**Primary Dependencies**: numpy only (already used); nothing new.

**Storage**: None. The cut values live in the job's memory for the length of the job, as the analysis does today.

**Testing**: pytest (`backend/tests`), run with `python -B` and cleared `__pycache__` for mutation checks; vitest for the frontend (unchanged, run to show it).

**Target Platform**: The existing local web service (Windows development, any platform for the service).

**Project Type**: Web application (backend and frontend); this feature is backend only.

**Performance Goals**: One comparison pass over `(windows, 88)` values; no measurable change to the job (SC-007: at most one second more on a 60 second file).

**Constraints**: No change to the request, the response, the page or the help text (FR-003, SC-006); a file with no note under the floor gives identical frames and chord records (SC-005); deterministic (FR-007).

**Scale/Scope**: A few dozen lines of code in one new module and two small edits (`jobs.py`, `chords.py`); the work is mostly tests, and the changed expectations of tests that rested on leakage.

## Constitution Check

The constitution file (`.specify/memory/constitution.md`) is still the unfilled template: it names no principles and no gates, so there is nothing to check against. The project's own practice is followed: tests first, an independent oracle, mutation checks, no change to what is outside the feature, documentation with the change.

Re-check after design: no violation.

## Project Structure

### Documentation (this feature)

```text
specs/033-noise-floor/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── noise-floor.md   # Phase 1 output: the library interface
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── routers/
│   │   └── jobs.py                  # CHANGED: floor_analysis(result) right after analyze_channels
│   └── services/
│       ├── noise_floor.py           # NEW: NOISE_FLOOR_DB, NOISE_FLOOR, apply_noise_floor, floor_analysis
│       └── chords.py                # CHANGED: measure_chords cuts first; the 1e-6 per-window floor is gone
└── tests/
    ├── test_noise_floor.py          # NEW: the cut, the boundary, idempotence, the analysis result
    ├── test_noise_floor_api.py      # NEW: every image type through the job, with and without a Threshold
    ├── test_chords.py               # CHANGED: the oracle works on cut values; the old floor tests become floor tests
    └── (others)                     # only where an expectation rested on a value under the floor (listed in tasks.md)

README.md                            # CHANGED: Noise floor paragraph; chord paragraph
specs/031-chord-interval-metric/     # CHANGED: the old per-window floor is replaced by this one
```

**Structure Decision**: The existing web-application layout; one new service module beside `local_peaks.py` and `chords.py` (the other measurements/limits), one call in the job, one change in the chord measurement. No frontend change.

## Complexity Tracking

No violations to justify.
