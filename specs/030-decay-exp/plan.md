# Implementation Plan: Decay Exp

**Branch**: `030-decay-exp` (no git branch created; spec directory name only) | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/030-decay-exp/spec.md`

## Summary

An eighth image type, **Decay Exp** (`decay-exp`): the circles, points, drawing, decay rate, neighbours and settings of **Decay** (feature 027), with two amounts replaced by exponential curves. A circle that would gain `g` points (24, 20, 16, 12 or 8 by rank plus `8 × position`) gains `g × e^(−g/8)`; a circle with `p` points before a decay step gives each neighbour `sin²(π/2 × p/64)` per frame's worth of the step (0 when `p` is 0; revised 2026-11-06, the first formula `1 / (1 + e^(p/8))` drained fuller circles more slowly), never more than it has. The four saturation-level decay amounts do not apply and are not shown.

How it is done (research Decisions 1 to 4):

- **Reuse Decay, do not copy it.** `decay.py` already separates the three things that differ: the gains (`gains`), the per-neighbour per-frame loss (`decay_per_frame`) and the spreading of what is given (`decay_step`). The spreading is split out of `decay_step` into a private `_spread(points, give)` with no change of behaviour, and the new module `decay_exp.py` supplies only `exp_gains`, `exp_loss_per_frame`, `decay_exp_step` and `circle_points` (the same loop as Decay's, calling its own gains and step). Size, color, rings, geometry and `write_decay_frames` are used as they are.
- **Gain is the Decay gain, tapered.** `exp_gains(values, beat, taper=8) = g * exp(-g / taper)` on the array `gains(values, beat)` returns (`taper` one number or one for each frame), so the ranking, ties, zero-value exclusion and beat bonus are Decay's; entries that are 0 stay 0.
- **The taper is state of the simulation (revised 2026-11-06).** `circle_points` works it out frame by frame: it starts at 8 (`taper_of(0)`), and after every frame `next_taper(steps, rising, circles_over_32)` gives the steps (a whole number from 0 to 400, the taper being `8 + 0.01 * steps`, so 8 and 12 are exact and nothing drifts) and the direction for the next frame. The gains of a frame are then `g * exp(-g / taper)`, worked out inside the loop; `circle_tapers` returns the taper of every frame for the tests.
- **Loss replaces the saturation-level table.** `give = min(points, 8 * frames * sin(pi / 2 * points / 64) ** 2)` for points above 0, else 0; the rest of the step is `_spread`, so edge/corner loss, simultaneity, clamping to 0..64 and the hundredth-of-a-point rule are shared.
- **Wiring.** `IMAGE_TYPES` gets `"decay-exp"`; `write_frames` draws it like `decay` with `exp` points (same beat, note layout, `decay_rate`; `decay_amounts` still checked and ignored); `jobs.py` measures the beat for `decay-exp` as for `decay`. No new request field; the decay amounts are still parsed and echoed.
- **Frontend.** `decay-exp` joins `IMAGE_TYPES` (label "Decay Exp"); `gridSettingsApply`, `beatAlwaysApplies` (the Concentric/Decay check) and `noteLayoutApplies` treat it like Decay; `decayRateApplies` covers it, but the four amounts are shown for `decay` only; a type group `decay-exp` titled "Decay" with the one control `decay-rate`; the summary line shows the Decay rate only; help text; tests.
- **Tests**: the exp gains (values with and without beat, ranking and ties preserved, zeros stay 0), the loss curve (values at 1, 8, 24, 32, 48, 64; 0 at 0; rising), `decay_exp_step` (interior, edge, corner, fewer points than the total, simultaneity, total never grows, clamping), `circle_points` (first frame ≈ 1.19 for a lone note, the level a steady note settles at, the slow fade, determinism), `write_frames` and the API (value accepted, refusal message lists eight names, decay rate checks, amounts ignored, other seven types' reference hashes unchanged, Decay unchanged), and the page (group, groups shown, summary, request).
- **Docs**: README; `quickstart.md`.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: numpy, FastAPI, Pillow; Vue, vitest. No new dependency.

**Storage**: None.

**Testing**: pytest (`test_decay_exp.py` for the points, `test_decay_exp_api.py` for the endpoint and drawing path, and the API tests that list the image type names) and vitest (validation, groups, SettingsForm, App, help).

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: As Decay: a 60 second file at 30 frames a second in under 30 seconds (SC-005). The simulation adds two `exp` evaluations over an 84-element array per step; drawing is the Decay drawing.

**Constraints**: Deterministic; the other seven image types byte-identical to before (the reference hashes of the earlier features, Decay included); 600 × 400 frames, counts and names unchanged. Refactoring `decay_step` into `decay_step` + `_spread` must not change any Decay result.

**Scale/Scope**: One new backend module (about 80 lines), a small refactor of `decay.py`, a few lines in `image_types.py`, `frame_rendering.py` and `jobs.py`; frontend edits to about six files plus tests; README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/030-decay-exp/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── decay-exp.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks (not created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/services/
│   ├── decay.py                # decay_step split: the spreading becomes _spread (no change of result)
│   ├── decay_exp.py            # NEW: exp_gains, exp_loss_per_frame, decay_exp_step, circle_points
│   ├── image_types.py          # IMAGE_TYPES gets "decay-exp"; module docstring
│   └── frame_rendering.py      # the decay-exp branch (points from decay_exp, drawn by write_decay_frames)
├── app/routers/jobs.py         # the beat is measured for decay-exp
└── tests/
    ├── test_decay_exp.py        # NEW
    ├── test_decay_exp_api.py    # NEW
    └── (the API tests that list the image type names)

frontend/
└── src/
    ├── utilities/validation.ts  # the type, the applies-functions
    ├── utilities/groups.ts      # the group decay-exp and groupsFor
    ├── utilities/help.ts        # the help text of the group, if the rate help needs a variant
    ├── App.vue                  # the summary line
    └── components/SettingsForm.vue  # the group; the four amounts stay for decay only (+ tests of each)
README.md
```

**Structure Decision**: Existing web-application layout. `decay_exp.py` is a thin module beside `decay.py`: it knows nothing about audio analysis, the note layout or the beat measurement, and takes everything it does not compute (drawing, rate check, step timing, spreading) from `decay.py`.

## Complexity Tracking

> No Constitution Check violations to justify.
