# Implementation Plan: Chromatic Decay

**Branch**: `035-chromatic-decay` (no git branch created; spec directory name only) | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/035-chromatic-decay/spec.md`

## Summary

An eleventh image type, **Chromatic Decay** (`chromatic-decay`): Decay Exp with **12 circles** (one for each letter) on a **ring in circle-of-fifths order**, whose points decay only to the letters **5 and 7 above** (the two neighbours on the ring), with a **decay rate of a whole number of frames from 1 to 10**.

How it is done (research Decisions 1 to 9):

- **One new module, `chromatic_decay.py`**, in the style of `decay_exp.py`, which it uses for everything that is the same: the taper rule (`taper_of`, `next_taper`), the loss formula (`exp_loss_per_frame`), the points range, and `decay.ring_colors` / `decay.circle_radii`-style size and ring rules. It adds: `letter_energies` (the largest of the 7 octaves of each of the 12 letters), `letter_gains` (the five loudest letters gain 24, 20, 16, 12, 8 plus the beat bonus, cut by `exp(-g / taper)`), `chromatic_step` (each circle gives away `8 x frames x loss(p)`, never more than it has, **one eighth to each** of the letters `n + 5` and `n + 7` mod 12 and six eighths lost, as an edge circle of Decay Exp), `circle_points` (the simulation over frames: `(frames, 12)` in letter order), and `write_chromatic_frames` (the ring picture).
- **The ring** is a layout of the drawing only: the points are kept in letter order (A = 0), and the picture puts letter `n` at ring position `7 (n - 3) mod 12` (C at the top, then G, D, A, ... clockwise, 30 degrees apart), so the receivers of a circle are the two neighbours of its place. The full radius is the one that lets two neighbouring full circles just touch; the geometry (pixels, distances and the ring weights of each circle) is worked out once for the frame size.
- **The decay rate** keeps its request field `decay_rate` but is **validated for the chosen type**: a whole number from 1 to 10 for `chromatic-decay` (default 1), the existing 0.25 to 4 in steps of 0.25 for every other type. One step falls at every `r`-th frame and moves `r` frames' worth (the average rate does not depend on `r`).
- **Wiring**: `IMAGE_TYPES` gets the name (at the end); `jobs.py` validates `decay_rate` knowing the image type, measures the beat for the type like Decay Exp, and `write_frames` draws it from the smoothed note values. The response has no new field. The frontend gets the option, a group **Chromatic Decay** with one control (**Decay rate**, 1 to 10, whole numbers), the Local peaks group and Data smoothing; no Note layout and no Image smoothing.
- **Tests first**: every rule of the numbers against loop oracles (letter energies, gains, one step for each of the 12 letters, mass conservation, decay to zero, the taper, the rate-r timing), the picture (ring positions, sizes, colors, touching radius, determinism), the job (type, per-type rate validation, ignored settings, other types unchanged byte for byte), the frontend.
- **Documentation**: the README and the help texts.

## Technical Context

**Language/Version**: Python 3.10 (backend, FastAPI); Vue 3 / TypeScript (frontend).

**Primary Dependencies**: numpy and Pillow (already used); matplotlib only through `colormaps.lookup_table`. Nothing new.

**Storage**: None; frames are PNGs in the job's directory as for the other types.

**Testing**: pytest (`backend/tests`), vitest (`frontend`), run as for features 032 to 034 (`python -B`, cleared `__pycache__` for mutation checks).

**Target Platform**: The existing local web service.

**Project Type**: Web application (backend and frontend).

**Performance Goals**: simulation over `(frames, 12)` (a loop over frames of 12 values: negligible next to the 84 of Decay Exp); drawing 12 circles per frame from precomputed geometry, in the worker pool: a three-minute file in about the time Decay Exp takes or less (SC-006).

**Constraints**: Frames 600 x 400 with the count, names and timing of the other types; deterministic; the other ten types give identical output (byte for byte); the `decay_rate` of the other types keeps its range and message.

**Scale/Scope**: One new module (about 300 lines), small edits in `frame_rendering.py`, `image_types.py`, `jobs.py` and five frontend files; most of the work is tests.

## Constitution Check

The constitution file (`.specify/memory/constitution.md`) is still the unfilled template: no principles, no gates. The project's own practice is followed: tests first, an independent oracle, mutation checks, nothing changed outside the feature, documentation with the change.

Re-check after design: no violation.

## Project Structure

### Documentation (this feature)

```text
specs/035-chromatic-decay/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── chromatic-decay.md  # Phase 1 output: the library interface, the request and the picture
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── routers/
│   │   └── jobs.py                       # CHANGED: decay_rate validated for the image type; the beat for the new type
│   └── services/
│       ├── chromatic_decay.py            # NEW: letter_energies, letter_gains, chromatic_step, circle_points, ring layout, write_chromatic_frames
│       ├── frame_rendering.py            # CHANGED: the chromatic-decay branch; the decay rate checked for the type
│       └── image_types.py                # CHANGED: the name in IMAGE_TYPES and the docstring
└── tests/
    ├── test_chromatic_decay.py           # NEW: letters, gains, steps, simulation (oracles)
    ├── test_chromatic_decay_rendering.py # NEW: the ring picture
    ├── test_chromatic_decay_api.py       # NEW: the job, the per-type decay rate, ignored settings, other types unchanged
    └── (others)                          # only where a list of the image types is spelled out (listed in tasks.md)

frontend/src/
├── utilities/validation.ts               # CHANGED: IMAGE_TYPES, isChromaticType, the chromatic rate range, validation and format
├── utilities/groups.ts                   # CHANGED: the chromatic-decay group, its peaks group, no note layout
├── utilities/help.ts                     # CHANGED: image type help, chromatic rate help
├── components/SettingsForm.vue           # CHANGED: the chromatic rate control and value
├── App.vue                               # CHANGED: the decay rate line of the summary
└── (tests)                               # validation.test.ts, groups.test.ts, SettingsForm.test.ts, api.test.ts, App.test.ts

README.md                                 # CHANGED: Chromatic Decay paragraph
```

**Structure Decision**: The existing web-application layout; one service module beside `decay_exp.py` that reuses it, the same kind of wiring as features 030 and 032, plus a per-type check of the one setting whose range differs.

## Complexity Tracking

No violations to justify.
