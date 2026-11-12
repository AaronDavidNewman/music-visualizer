# Implementation Plan: Rhythm Circles

**Branch**: `038-rhythm-circles` (no git branch created; spec directory name only) | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/038-rhythm-circles/spec.md`

## Summary

A twelfth image type, **Rhythm Circles** (`rhythm-circles`): **eight concentric notched rings** in the middle of the frame, each rotating at a speed that comes from the **local peaks** of the sound (four layers, the longest aggregation outermost: the aggregated tempo of the latest 8 periods and its rate of change, the same for 4 and for 2 periods, and the tempo and its rate of change). Its only settings are the **Minimum distance** and **Prominence** of the local peaks (already in the request and on the page); the picture does not use the notes.

How it is done (research Decisions 1 to 8):

- **One new module, `rhythm_circles.py`**, in the style of `energy_graphs.py` and `chromatic_decay.py`: `peak_series(peaks)` (per peak: the aggregated tempo of 8 and its rate of change, of 4 and its rate of change, of 2 and its rate of change, the tempo and its rate of change, in revolutions per minute), `circle_speeds(...)` (the speed of the eight circles at any moment: a step function that changes at each peak, the defaults before the first), `rhythm_angles(peaks, frame_rate, frames)` (the **angle of every circle at the middle of every frame**, as the running total of the speed, so a notch never jumps), `RhythmData`, and `write_rhythm_frames` (the picture: eight rings of equal width, each one color with a notch of 1/8 of the circle in the color at the opposite end of the colormap, drawn with smooth edges from a geometry worked out once for the frame size).
- **The numbers are all pure functions of the peaks** (`LocalPeaks` already gives each peak its sample and its rate in beats per minute, 60 for the first; the rate at any moment is the latest peak's), so they are tested on hand-made peaks without any audio.
- **Wiring**: `IMAGE_TYPES` gets the name; `jobs.py` measures the local peaks with the request's Minimum distance and Prominence for this type and builds the `RhythmData`; `write_frames` gets a keyword `rhythm` (like `energy`) and draws it. **No new request or response field.** The frontend gets the option (no group of its own, the Local peaks group without the checkbox, no Data smoothing or Image smoothing) and a help text.
- **Tests first**: each series against a loop oracle on hand-made peaks (steady tempo, speeding up, slowing down, fewer than 8 peaks, no peaks), the angles (continuity across a peak, 720 degrees a second at 120 beats per minute, the sign of the rate circles), the picture (ring geometry, colors, the notch at the right angle and of 1/8, rotation between frames, determinism), the job (a click track at a known tempo through the API, the settings that do not apply ignored, other types unchanged byte for byte), the frontend.
- **Documentation**: the README and the help text.

## Technical Context

**Language/Version**: Python 3.10 (backend, FastAPI); Vue 3 / TypeScript (frontend).

**Primary Dependencies**: numpy and Pillow (already used); the existing `local_peaks`. Nothing new.

**Storage**: None.

**Testing**: pytest (`backend/tests`), vitest (`frontend`), as for features 032 to 037 (`python -B`, cleared `__pycache__`, the mutation helpers of the session scratchpad).

**Target Platform**: The existing local web service.

**Project Type**: Web application (backend and frontend).

**Performance Goals**: the peaks are measured once; the angles are one `searchsorted` over the frames; a frame draws 6 rings from precomputed arrays (about a 380 x 380 box): a few milliseconds, in the worker pool. A three-minute file at 10 frames a second in about the time Chromatic Decay needs or less.

**Constraints**: frames 600 x 400 with the count, names and timing of the other types; deterministic; the other eleven image types are unchanged byte for byte; no new request or response field.

**Scale/Scope**: one new module (about 300 lines), small edits in `image_types.py`, `frame_rendering.py` and `jobs.py` and four frontend files; most of the work is tests.

## Constitution Check

The constitution file (`.specify/memory/constitution.md`) is still the unfilled template: no principles, no gates. The project's own practice is followed: tests first, an independent oracle, mutation checks, nothing changed outside the feature, documentation with the change.

Re-check after design: no violation.

## Project Structure

### Documentation (this feature)

```text
specs/038-rhythm-circles/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── rhythm-circles.md  # Phase 1 output: the library interface, the request and the picture
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── routers/jobs.py                 # CHANGED: measures the local peaks for the type and builds the rhythm data
│   └── services/
│       ├── rhythm_circles.py           # NEW: peak_series, circle_speeds, rhythm_angles, RhythmData, write_rhythm_frames
│       ├── frame_rendering.py          # CHANGED: write_frames(rhythm=...) and the rhythm-circles branch
│       └── image_types.py              # CHANGED: the name in IMAGE_TYPES and the docstring
└── tests/
    ├── test_rhythm_circles.py          # NEW: the series, the speeds, the angles (hand-made peaks)
    ├── test_rhythm_circles_rendering.py# NEW: the picture
    ├── test_rhythm_circles_api.py      # NEW: the job (click tracks), ignored settings, other types unchanged
    └── (others)                        # the tests that spell out the eleven image types (listed in tasks.md)

frontend/src/
├── utilities/validation.ts             # CHANGED: IMAGE_TYPES, isRhythmType, peakSettingsShown
├── utilities/groups.ts                 # CHANGED: no Data smoothing for the type
├── utilities/help.ts                   # CHANGED: the image type help
└── (tests)                             # validation.test.ts, groups.test.ts, SettingsForm.test.ts, api.test.ts, help.test.ts

README.md                               # CHANGED: Rhythm Circles paragraph
```

**Structure Decision**: The existing web-application layout; one service module beside `chromatic_decay.py` and `energy_graphs.py`, wired the same way as Energy Graphs (an extra data argument to `write_frames`, no setting of its own).

## Complexity Tracking

No violations to justify.
