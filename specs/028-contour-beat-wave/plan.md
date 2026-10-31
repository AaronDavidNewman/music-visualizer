# Implementation Plan: Contour Beat Wave

**Branch**: `028-contour-beat-wave` (no git branch created; spec directory name only) | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/028-contour-beat-wave/spec.md`

## Summary

An optional **beat wave** for the **Contour** picture: when the existing **Beat coloring** checkbox is on, every frame's grid of values is multiplied, before the contour is drawn, by a **modifier** `1 − pattern × sin(π × k)`. The `pattern` is a set of concentric rings, `(sin(waves × 2π × sqrt(distance ÷ largest dimension)) + 1) ÷ 2`, with `distance` measured in grid points from the geometric center of the grid and `largest dimension` the larger of the grid's columns and rows (the square root makes the rings wider towards the outside); `k` is the frame's position in the local energy peak (0 at the minimum, 1 at the maximum), passed through a sine from 0 to π so that the effect swells and fades smoothly (revision of 2026-10-30): nothing at `k = 0`, deepest at `k = 0.5`, all but nothing again at `k = 1`. At `k = 0` the modifier is 1 everywhere, so the frame is the plain contour; with the checkbox off nothing changes at all. The **Wave count** (2 to 10, default 4) is a new setting of the Contour group.

How it is done (research Decisions 1 to 5):

- **A small pure module, `beat_wave.py`**, holds the rule: `check_wave_count`, `wave_pattern(rows, columns, waves)` (cached, float64, the same pattern for every frame of a job) and `wave_modifier(rows, columns, waves, k)`. It needs neither matplotlib nor audio, so it is tested on numbers alone and `contour.py` keeps its lazy matplotlib import.
- **Applied inside `write_contour_frames`**, to the frame's `Z` grid after the existing grid smoothing and just before the levels are chosen. The color scale stays `vmin=0, vmax=top` with `top` the frame's largest value *before* the wave, so a dimmed point is drawn darker (that is what makes the rings visible); a frame that has no contour to draw (all values equal) is still written flat as today. If the wave leaves nothing to draw (every point equal after the multiplication), the frame is written flat at that value.
- **`k = 0` is skipped, not multiplied**, so the frames at the minimum of the beat are byte-identical to the plain ones by construction (and so is a job with no beat, or with the checkbox off).
- **Wiring.** `write_frames(…, wave_count=4)` checks the count for every type and, for `contour`, hands `beat` and `wave_count` to the drawing (the other types still ignore the count). `jobs.py` gets the optional field `wave_count` (checked before the file is read, echoed in the response), and measures the beat for Contour exactly when `beat_coloring` is true, as for Tiles and Blended tiles.
- **Frontend.** `beatColoringApplies` becomes true for Contour (so the Local peaks group with the checkbox and the two sliders, the summary lines and the existing rules all follow); `WAVE_COUNT_RANGE` (2 to 10), `DEFAULT_WAVE_COUNT` 4, `validateWaveCount`, `formatWaveCount`, `waveCountApplies`; the Contour group gets the control `wave-count` after Threshold and Notes; the request, the summary line "Wave count" (when the beat coloring is on), help texts; tests.
- **Tests**: the rule on numbers (the pattern at known points, the center value, the range 0 to 1, symmetry, the number of rings, the modifier at `k = 0`, 0.5, 1, no change to the input), `write_contour_frames` (k = 0 byte-identical to no beat, the grid actually handed to matplotlib equals plain × modifier, scale from the unmodified maximum, a flat frame stays flat, a frame the wave flattens is written flat, oversampling, interpolate, Gaussian), the API (the field, defaults, refusals, echo, the beat measured only when the box is on, ignored by the other types, the reference hashes of the other types and of plain Contour), and the page (the groups, the slider, the checkbox for Contour, the summary, the request, the help).
- **Docs**: README, `quickstart.md`.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: numpy, matplotlib (Contour, lazily), FastAPI, Pillow; Vue, vitest. No new dependency.

**Storage**: None.

**Testing**: pytest (`test_beat_wave.py` for the rule, `test_contour_beat_wave.py` for the drawing and `write_frames`, `test_contour_beat_wave_api.py` for the endpoint, and the API tests that list the response keys) and vitest (validation, groups, SettingsForm, App, help, api).

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: The wave costs a multiply of an array of at most a few hundred values per frame, compared with matplotlib's drawing of the same frame; FR-011 (a few seconds more than the plain Contour for a 60 second file at 30 frames a second) is checked by a test.

**Constraints**: Deterministic; with the checkbox off, at position 0, and for the other six image types the frames are byte-identical to before (the reference hashes `6819990556fd4095`, `f32a99c59fcb87fc`, `92b3a27dee73e223`, `400cc93e1bfca03d` and those of the earlier features); 600 × 400 frames, counts and names unchanged.

**Scale/Scope**: One new backend module (about 60 lines), about 20 lines in `contour.py`, `frame_rendering.py` and `jobs.py`; frontend edits to about eight files plus tests; README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/028-contour-beat-wave/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── contour-beat-wave.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks (not created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/services/
│   ├── beat_wave.py          # NEW: check_wave_count, wave_pattern, wave_modifier
│   ├── contour.py            # write_contour_frames(..., beat=None, waves=DEFAULT_WAVE_COUNT)
│   └── frame_rendering.py    # write_frames(..., wave_count=4): checked for every type, used by contour
├── app/routers/jobs.py       # the field wave_count; the beat is measured for contour with the box on
└── tests/
    ├── test_beat_wave.py                # NEW
    ├── test_contour_beat_wave.py        # NEW
    ├── test_contour_beat_wave_api.py    # NEW
    └── (the API tests that list the response keys, and those of the groups of Contour)

frontend/
└── src/
    ├── utilities/validation.ts  # the wave count, the applies-functions
    ├── utilities/groups.ts      # the Contour group gets wave-count; Local peaks for Contour
    ├── utilities/help.ts        # the help texts
    ├── api.ts                   # the field
    ├── App.vue                  # the summary line
    └── components/SettingsForm.vue  # the slider (+ tests of each)
README.md
```

**Structure Decision**: Existing web-application layout. `beat_wave.py` is its own small pure module like `note_layout.py`: the rule of the pattern and the modifier, knowing nothing about matplotlib, images, audio or the beat measurement.

## Complexity Tracking

> No Constitution Check violations to justify.
