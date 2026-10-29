# Implementation Plan: Decay

**Branch**: `027-decay-circles` (no git branch created; spec directory name only) | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/027-decay-circles/spec.md`

## Summary

A seventh image type, **Decay** (`decay`): the 84 circles of Concentric in the same places, but each circle is **a disc** that keeps a **point value from 0 to 64** from frame to frame. The points set the size (1/12 of the full radius at 0, full at 24 and above) and the color (first color at 0, last at 32, a flat disc up to there; from 32 to 64 the 12 concentric rings of Concentric open up from the last color at the center to the first at the edge). Each frame the five loudest notes add 24, 20, 16, 12, 8 points plus `8 × position` (the beat); every N frames (the new **Decay rate**, 1 to 10, default 5) every circle gives 2 points to each neighbour among the up to 8 around it and loses 16 in all.

How it is done (research Decisions 1 to 4):

- **State is a small simulation, apart from the drawing.** A new module `decay.py` works out the points of every circle in every frame in one pass over the frames (`(frames, 84)` floats), then draws each frame from its row of points. The simulation is 7 × 12 numpy arithmetic per frame; no drawing code is involved, so it is testable on its own.
- **Gains are worked out in note order, the simulation runs in cell order.** The top five are ranked among the notes (ties to the lower note, as the spec says), the gains are placed in cells with the existing `arrange_notes(…, note_layout)`, and the neighbours of a circle are the cells around its cell. Rows and Spiral therefore both work and nothing about the layout is duplicated.
- **Decay is a conservative shift.** With `give = min(points, 16)` and `share = give / 16`, a circle sends `2 × share` to each neighbour; the part of the 16 with no neighbour is lost. A circle with at least 16 points gives exactly what the spec says; one with fewer gives proportionally less, so nothing is created. All circles use the points before the step.
- **Drawing reuses the Concentric cell geometry.** The cell of every pixel and its distance to the cell center are worked out once for the frame size; a frame is the blend of the background and the circle color with the analytic coverage `clip(radius − distance + 0.5, 0, 1)`, which gives the same one-pixel smooth edge for any radius, so a size that varies continuously costs no more than a fixed one.
- **Wiring.** `IMAGE_TYPES` gets `decay`; `write_frames(…, decay_rate=5)` checks the rate for every type and draws Decay like Concentric (same beat, same note layout, same ignored settings); `jobs.py` gets the optional field `decay_rate`, measures the beat for `decay` as for `concentric`, and echoes the rate.
- **Frontend.** `decay` joins `IMAGE_TYPES`; `DECAY_RATE_RANGE`, `DEFAULT_DECAY_RATE`, `validateDecayRate`; a type group `decay` titled "Decay" with one slider; `gridSettingsApply`, `noteLayoutApplies` and the peaks group treat Decay like Concentric; the request, the summary line, a help text; tests.
- **Tests**: the point rules (gains and ranking, ties, the beat bonus, clamping at 0 and 64, the decay of an interior cell, an edge cell and a corner cell, a circle with fewer than 16 points, simultaneity, the total never growing, the interval, a silent file), the radius and color of a circle from its points, `write_frames` and the API (the field, defaults, refusals, echo, ignored for the others, Rows and Spiral, the reference hashes of the other six types), and the page (the group, the groups shown, the request, the summary, the help).
- **Docs**: README, `quickstart.md`.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: numpy, FastAPI, Pillow; Vue, vitest. No new dependency.

**Storage**: None.

**Testing**: pytest (`test_decay.py` for the points, `test_decay_rendering.py` for the drawing and `write_frames`, `test_decay_api.py` for the endpoint, and the API tests that list the response keys) and vitest (validation, groups, SettingsForm, App, help, api).

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: A 60 second file at 30 frames a second (1,800 frames) in under 30 seconds (SC-007), and not more than a few seconds more than Concentric (FR-013). The simulation is about 1,800 tiny array steps (milliseconds); a frame is a few array operations over 240,000 pixels plus the PNG, as for Concentric.

**Constraints**: Deterministic; the other six image types byte-identical to before (the reference hashes `6819990556fd4095`, `f32a99c59fcb87fc`, `92b3a27dee73e223`, `400cc93e1bfca03d` and the Concentric hash); 600 × 400 frames, counts and names unchanged.

**Scale/Scope**: One new backend module (about 150 lines), about 15 lines in `image_types.py`, `frame_rendering.py` and `jobs.py`; frontend edits to about eight files plus tests; README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/027-decay-circles/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── decay.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks (not created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/services/
│   ├── decay.py                # NEW: gains, the decay step, the points of all frames, radii and colors, write_decay_frames
│   ├── image_types.py          # IMAGE_TYPES gets "decay"
│   └── frame_rendering.py      # write_frames(..., decay_rate=5), the decay branch
├── app/routers/jobs.py         # the field decay_rate; the beat is measured for decay
└── tests/
    ├── test_decay.py            # NEW
    ├── test_decay_rendering.py  # NEW
    ├── test_decay_api.py        # NEW
    └── (the API tests that list the response keys and the image type names)

frontend/
└── src/
    ├── utilities/validation.ts  # the type, the rate range, validation, the applies-functions
    ├── utilities/groups.ts      # the group decay and groupsFor
    ├── utilities/help.ts        # the help text
    ├── api.ts                   # the field
    ├── App.vue                  # the summary line
    └── components/SettingsForm.vue  # the slider and the group (+ tests of each)
README.md
```

**Structure Decision**: Existing web-application layout. `decay.py` is its own module like `concentric.py`: it knows nothing about audio analysis, the note layout or the beat measurement; the smoothed values (already in note order), the layout name, the beat positions, the rate and the size are passed in.

## Complexity Tracking

> No Constitution Check violations to justify.
