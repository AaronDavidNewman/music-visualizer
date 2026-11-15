# Implementation Plan: Local Tempo Finder

**Branch**: `040-local-tempo-finder` | **Date**: 2026-11-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/040-local-tempo-finder/spec.md`

## Summary

Add a **tempo finder** that turns the peaks of the Local peaks measurement into a **current tempo** that always lies between 60 and 156 beats per minute, and show it in Rhythm Circles: the eight circles become four (the user cut them from eight on 2026-11-14 because the inner ones were hard to read): outer to inner, the current tempo and its rate of change, and the local peak's tempo and its rate (the aggregated-tempo circles of 8, 4 and 2 peaks, and the circles of half and two thirds of the tempo, go). Also on 2026-11-14 the finder was made to consider **faster tempos** too (a sample can stand for the tempo as twice it or one and a half times it), which cut the restarts on the two sample files from 40 and 22 to 2 and 1. The finder is a small pure function of the peak times, built exactly on the user's rule (start at 120; keep the latest 5 samples; match each sample to the tempo, its half or its two thirds; move by the weighted average if within one standard deviation, else by one standard deviation; restart at 78 above 156 and at 120 below 60). The measurement's Prominence becomes a fixed 20% (the control and the request field go) and Minimum distance defaults to 350 ms. The other image types keep reading the local peak.

A prototype of the rule on the real peaks of `sonata.wav` and `almost2.wav` (see [research.md](research.md)) shows that the rule as written does not give the hoped-for results on them (22% and 7% of the time near 116 and 90), because the peaks of both files are mostly at 100 to 170 beats per minute and the rule cannot take a sample above the tempo as evidence for it. The plan therefore builds the rule as written, with the set of ratios in one constant, and **measures and reports** the two files instead of gating on them; the one-line change that fixes most of it is recorded for the user to decide.

## Technical Context

**Language/Version**: Python 3 (backend, virtual environment `backend/.venv`); TypeScript with Vue 3 (frontend)

**Primary Dependencies**: FastAPI, NumPy, SciPy (`find_peaks`, already used by the measurement), Pillow (already used by Rhythm Circles); no new dependency

**Storage**: Files only (the uploaded `.wav` and the frames of a job); no new storage

**Testing**: pytest (`python -B`, backend), vitest and `vue-tsc --noEmit` (frontend); tests first, independent oracles, mutation checks of the new rule

**Target Platform**: The existing local web app (FastAPI backend, Vue frontend, Windows development)

**Project Type**: Web application (backend and frontend)

**Performance Goals**: The finder runs over the peaks only (a few hundred to a few thousand numbers): negligible beside the measurement and the drawing; Rhythm Circles of a 5-minute file no more than 5% slower

**Constraints**: Deterministic; the tempo never outside 60 to 156 at any moment; Minimum distance keeps its range 100 to 2000 ms and its message; a request that still sends `peak_prominence` is accepted and ignored; the other image types' pictures unchanged for the same Minimum distance

**Scale/Scope**: One new module of about 100 lines (`tempo_finder.py`), changes to `rhythm_circles.py`, `local_peaks.py` (defaults), `jobs.py` (prominence out), six small frontend files, and the tests of all of them (the prominence tests are the many)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is the unfilled template (no principle is defined), so there are no gates to fail. The project's working rules are followed instead: tests first with independent oracles, README updated per feature, memory notes of the user's choices, and nothing committed without being asked. **Re-check after design: no violation.**

## Project Structure

### Documentation (this feature)

```text
specs/040-local-tempo-finder/
├── plan.md              # This file
├── research.md          # Phase 0: the rule made exact, the prototype measurements, decisions
├── data-model.md        # Phase 1: the tempo state, the series and the eight circles
├── quickstart.md        # Phase 1: how to see and check the result
├── contracts/
│   └── api.md           # Phase 1: the request/response change (prominence out, distance default 350)
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── services/
│   │   ├── tempo_finder.py       # NEW: the rule: samples, ratio matching, step, limits and restarts -> the tempo after each peak
│   │   ├── rhythm_circles.py     # CHANGED: peak_series now has tempo/1.5, tempo/2, tempo, peak levels and their rates; docstrings
│   │   └── local_peaks.py        # CHANGED: DEFAULT_MIN_DISTANCE 350, FIXED prominence 20 as the default (the checks stay)
│   └── routers/jobs.py           # CHANGED: no peak_prominence field/response; the measurement uses the fixed 20
└── tests/
    ├── test_tempo_finder.py      # NEW: the rule on peak times alone (oracles by hand), limits, restarts, determinism
    ├── test_tempo_files.py       # NEW: sonata.wav and almost2.wav measured and reported, invariants asserted
    ├── test_rhythm_circles.py    # CHANGED: the eight circles of the new layers
    ├── test_rhythm_circles_api.py        # CHANGED
    ├── test_local_peaks.py       # CHANGED: the new default distance
    └── test_*_api.py (peak_prominence users)  # CHANGED: prominence no longer sent/echoed

frontend/src/
├── api.ts, api.test.ts                      # peakProminence out of the settings and the form body, out of the result
├── App.vue, App.test.ts                     # the "Prominence:" line of the result out
├── components/SettingsForm.vue (+ test)     # the Prominence control, its validation and help out; distance default 350
└── utilities/
    ├── validation.ts (+ test)               # PEAK_PROMINENCE_*, validatePeakProminence, formatPeakProminence out; DEFAULT_PEAK_DISTANCE 350
    ├── groups.ts (+ test)                   # "peak-prominence" out of the two Local peaks groups
    └── help.ts (+ test)                     # peakProminenceHelp out; the Rhythm Circles and Minimum distance texts updated

README.md                                    # the Rhythm Circles, Local peaks and Minimum distance paragraphs
```

**Structure Decision**: The existing web application layout (`backend/app/services` for pure functions, `routers/jobs.py` for the request, `frontend/src` for the page) is kept. The finder gets its own small module so that it can be tested with peak times alone (no audio) and so that `rhythm_circles.py` only draws; the Local peaks measurement itself is not changed beyond its defaults.

## Complexity Tracking

No constitution violations to justify.
