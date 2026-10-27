# Implementation Plan: Local Peaks

**Branch**: `023-local-peaks` (no git branch created; spec directory name only) | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/023-local-peaks/spec.md`

## Summary

A new measurement, **local_peaks**, that follows the **overall** loudness of a file (not the notes) and reports its periodic local maxima. It is a backend module only, `app/services/local_peaks.py` (the clarification: *the measurement only*; the job request, the response, the settings page and the pictures do not change).

The measurement, as the spec states it:

1. **Impulse energy**: the left and right samples are cut into consecutive, non-overlapping windows of 32 samples; the energy of a window is the **average of the left and the right standard deviation** (computed per channel, then averaged).
2. **Peaks window**: a running window of 4,096 impulse energies slides through the energy list in steps of half its length. `scipy.signal.find_peaks(window, distance=…, prominence=…)` is called on every window. `distance` is the minimum distance (a time, default 100 ms, 100 to 2,000) converted to impulse samples, `round(ms / 1000 × rate / 32)` and at least 1; `prominence` is the prominence percentage (default 50, 0 to 100) of the window's largest energy.
3. **Which peaks are kept**: each window *owns* its central half (the first window also owns its start, the last its end), so the owned zones tile the file and **every peak is judged once, in a window that sees at least a quarter of a window of energy on each side of it**. A last pass enforces the minimum distance across the zone borders (the stronger of two close peaks stays), because `find_peaks` can only enforce it inside a window.
4. **A record per peak**: the sample (the first sample of its impulse window), its energy, the minimum and maximum impulse energy of the window it was found in, and the rate in peaks per minute (`60 × file rate / samples since the previous peak`; the first peak, with no predecessor, gets the default of 60).
5. **Asking the result**: `energy_at(point)` is the straight line between the previous and the next peak's energy, 0 before the first peak, the last peak's energy after the last; `rate_at(point)` is the rate of the previous peak, 60 before the first. Both accept a sample number, a time in seconds or a sequence (for a whole file's frames at once) and never fail for a finite point.

Work by area:

- **Backend**: one new module `app/services/local_peaks.py` (constants, `check_min_distance`, `check_prominence`, `impulse_energy`, `measure_local_peaks`, `measure_wav`, the `LocalPeak` and `LocalPeaks` types). `note_analysis.read_wav` is reused; nothing existing is edited.
- **Frontend**: none. **API**: none.
- **Tests**: `tests/test_local_peaks.py` and `tests/local_peaks_signals.py` (click tracks and bursts): the impulse energy against a direct calculation, the click track (count, positions, rates), the minimum distance (converted and kept), the prominence (the value handed to `find_peaks` and the effect), windows (overlap dedupe, zone borders, short files, independence of the window size), the interpolation (at peaks, between, before, after, fractional, in seconds, arrays, no peaks), the settings checks, determinism, performance, and that the existing image types are unchanged (the reference hashes).
- **Docs**: README (a Local peaks paragraph), `quickstart.md` here.

A prototype (research.md) measured the scheme on 30 s click tracks of 0.5, 0.75 and 0.3 s periods and window sizes 2,048, 4,096 and 8,192: every click found, none twice, the rate within 0.15% of the true one, identical results at all three window sizes, and 0.023 s for a 60 s file.

Worth knowing: positions are exact to one impulse window (32 samples, 0.7 ms); a peak cannot be at the very first or last impulse sample (a `find_peaks` property); the first peak's rate is the default 60 because nothing precedes it; the peaks window is a slice of the energy list rather than a streaming buffer (the same windows, simpler to test); this feature changes nothing a user can see.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`)

**Primary Dependencies**: Existing only: numpy and scipy (`scipy.signal.find_peaks`; `scipy>=1.11` is already in `requirements.txt`, 1.15.3 installed). No new dependency.

**Storage**: None. The result is an in-memory object; nothing is written to disk.

**Testing**: pytest (`test_local_peaks.py`), synthetic click tracks and bursts generated with a seeded numpy generator; no audio files needed.

**Target Platform**: Local developer machine (backend library code).

**Project Type**: Web application: existing `backend/` project; this feature touches only it, and only by adding files.

**Performance Goals**: A 60 s stereo file in under 5 s (SC-006); measured 0.023 s.

**Constraints**: Deterministic; the existing image types and the note analysis unchanged (reference hashes `6819990556fd4095`, `f32a99c59fcb87fc`, `92b3a27dee73e223`, `400cc93e1bfca03d`).

**Scale/Scope**: One new module (~200 lines), one new test module and helper; README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/023-local-peaks/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── local-peaks.md
└── tasks.md             # /speckit-tasks (not created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/services/
│   └── local_peaks.py          # NEW: the measurement and its result
└── tests/
    ├── local_peaks_signals.py  # NEW: seeded click tracks and bursts
    └── test_local_peaks.py     # NEW
README.md
```

**Structure Decision**: Existing web-application layout. A module of its own in `app/services/`, like `gaussian.py`; it knows nothing about the note analysis, the frames or the router, and takes plain arrays (so a later feature can call it from the job code).

## Complexity Tracking

> No Constitution Check violations to justify.
