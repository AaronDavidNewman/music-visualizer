# Implementation Plan: Peak Tile Colors

**Branch**: `024-peak-tile-colors` (no git branch created; spec directory name only) | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/024-peak-tile-colors/spec.md`

## Summary

For the **Tiles** and **Blended tiles** image types, an optional **beat coloring** (a checkbox in a new settings group **Local peaks**, off by default) changes the place of a tile on the colormap from `sqrt(share)` to **`0.5 × sqrt(share) + 0.5 × position`**, where `position` (0 to 1) is the frame's place in the local energy peak, taken from the local peaks measurement of feature 023. With the checkbox off nothing changes at all (the colors are 100 % harmonic and the beat is not even measured), so every existing picture, hash and test stays valid.

How a frame's position is worked out (the clarifications): at the frame's time (the middle of the interval it covers) take the measurement's **interpolated energy** `E` and the **interpolated smallest and largest energy** `lo` and `hi` of the neighbouring peaks' windows (the same straight line between the previous and the next peak; before the first peak all three are 0; after the last peak they are the last peak's values) and let `position = clip((E − lo) / (hi − lo), 0, 1)`, or 0 when `hi ≤ lo`. Every tile of the frame uses that one number. Hidden tiles are drawn as before; the threshold is untouched.

Work by area:

- **Backend, measurement** (`app/services/local_peaks.py`): `LocalPeaks.position_at(point)`, `position_at_time(seconds)` and `frame_positions(frame_rate, frames)` (the positions of the middle of every frame). Nothing existing changes.
- **Backend, colors** (`app/services/colormaps.py`): `colorize(..., beat=None)`: with `beat` (one position per frame) the table index is `rint((0.5 × sqrt(share) + 0.5 × beat) × 255)`; without it, exactly as now.
- **Backend, frames** (`app/services/frame_rendering.py`): `write_frames(..., beat=None)` takes the per-frame positions (so it still knows nothing about audio), checks them (a 1-D array of one finite number from 0 to 1 per frame), and hands them to `colorize` for `tiles` and `blended` only; every other type ignores them.
- **Backend, API** (`app/routers/jobs.py`): three optional fields `beat_coloring` (true/false/1/0), `peak_distance` (ms) and `peak_prominence` (percent), parsed and checked with the measurement's own messages **before any work, whether the checkbox is on or off**; when it is on and the type is tiles or blended the job measures the beat (`measure_local_peaks(left, right, file_rate, …)`) and passes `frame_positions(fps, frames)` to `write_frames`; the response reports the three values.
- **Frontend**: a new group `local-peaks` ("Local peaks": the checkbox, Minimum distance, Prominence) shown after the Tiles / Blended Tiles group; ranges, validation, formatting and help texts in `validation.ts` / `help.ts`; `api.ts` sends the three fields and types them; the form's refs, errors, group problem flag and payload; `App.vue`'s summary lines for the two types; tests.
- **Tests**: position (before the first peak, at peaks, between, after the last, the interpolated min and max, clipped, no range, arrays, frame times); `colorize` with and without `beat` (formula to one table step, middle and right-most colors for every colormap, monotone in both inputs, `beat=None` identical to before); `write_frames` (off identical to the reference hashes, the strong tile's colors at positions 0, 0.5 and 1, hidden tiles as before for both types, other types ignore `beat`, resolution above 1, interpolate above 1, a bad `beat`); the API (defaults, parsing, messages, off identical frames, on different frames, checked when off, response keys); the page (group shown for the two types only, controls, summary, payload) with SSR and source guards.
- **Docs**: README (the beat coloring) and `quickstart.md`.

Worth knowing (research Decision 2): the measurement's energy is a **straight line from peak to peak**, so for evenly strong beats the position stays near 1 between them. The coloring therefore follows the **strength of the beats** (a click-track prototype: equal clicks give a position of 0.71 to 1.0, median 0.996; clicks of varying strength give 0 to 0.999, median 0.79), not a rise and fall within each beat. That is what the clarification defines; a within-beat pulse would need the measured energy curve and is noted in the spec as a different, later change.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: numpy, scipy (via feature 023), FastAPI, Pillow; Vue, vitest. No new dependency.

**Storage**: None new.

**Testing**: pytest (`test_local_peaks.py` additions, `test_colormaps.py` additions, new `test_peak_tile_colors.py` and `test_peak_tile_colors_api.py`, the six API tests that list the response keys) and vitest (validation, groups, SettingsForm, api, App, help).

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: With the beat coloring on, no more than 5 s added for a 60 s file (SC-007); measured: the measurement takes 0.03 s per minute of audio; with it off, no change.

**Constraints**: Deterministic; with the checkbox off (the default) and for contour, circles and circles paint the frames are byte-identical to before (the four reference hashes `6819990556fd4095`, `f32a99c59fcb87fc`, `92b3a27dee73e223`, `400cc93e1bfca03d`); 600 × 400 frames, counts and names unchanged.

**Scale/Scope**: ~60 lines in `local_peaks.py`, ~15 in `colormaps.py`, ~25 in `frame_rendering.py`, ~70 in `jobs.py`; frontend edits to about eight files plus tests; README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/024-peak-tile-colors/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── beat-coloring.md
└── tasks.md             # /speckit-tasks (not created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/services/
│   ├── local_peaks.py          # position_at, position_at_time, frame_positions
│   ├── colormaps.py            # colorize(..., beat=None)
│   └── frame_rendering.py      # write_frames(..., beat=None) for tiles and blended
├── app/routers/jobs.py         # beat_coloring, peak_distance, peak_prominence
└── tests/
    ├── test_local_peaks.py             # + the position tests
    ├── test_colormaps.py               # + colorize with beat
    ├── test_peak_tile_colors.py        # NEW: write_frames level
    ├── test_peak_tile_colors_api.py    # NEW
    └── (the six API tests that list the response keys)

frontend/
└── src/
    ├── utilities/validation.ts   # ranges, defaults, validators, formatters
    ├── utilities/groups.ts       # the group local-peaks and groupsFor
    ├── utilities/help.ts         # three help texts
    ├── api.ts                    # the three fields
    ├── App.vue                   # summary lines
    └── components/SettingsForm.vue  # the controls and the group (+ tests of each)
README.md
```

**Structure Decision**: Existing web-application layout. `write_frames` keeps taking plain arrays (the per-frame positions), the router owns the audio, and the measurement stays a separate module that this feature only extends with the position.

## Complexity Tracking

> No Constitution Check violations to justify.
