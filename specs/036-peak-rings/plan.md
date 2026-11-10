# Implementation Plan: Peak Rings

**Branch**: `036-peak-rings` (no git branch created; spec directory name only) | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/036-peak-rings/spec.md`

## Summary

A target of **12 concentric rings, 140 pixels across, in the empty middle of the Chromatic Decay ring**, showing the beat: the **center** is the current frame's distance from the local peak (`1 - position`), and ring `k` outward is the **average of the distances of frames `t - (2k - 3)` and `t - (2k - 2)`**, a history in time, newest inside. A ring's color is the colormap at its distance, **start (left) at the peak, end (right) far from it**.

How it is done (research Decisions 1 to 6):

- **Small additions to `chromatic_decay.py`**, in the style of the module: `peak_distances(beat)` (the distance of every frame), `ring_levels(beat)` (the `(frames, 12)` level of every ring of every frame, moments before the start counting as far from a peak), `peak_circle_geometry(width, height)` (the radius, 70 pixels on 600 x 400, scaled with the picture, and the 12 ring widths), and the drawing of the rings in `write_chromatic_frames`, which gets an optional `beat` argument (**`None` draws no rings**, so every existing call and test is unchanged).
- **The drawing reuses the ring-weight rule of the circles** (the smooth edge between rings and the smooth outer edge): the formula of `_geometry` is moved into one helper used by both, so the rings of the target and the rings of a full circle are blended the same way. The rings are drawn first, then the 12 circles over the picture (they never overlap).
- **No new setting, request field or response field.** `write_frames` already receives the beat that the job measures for this type; it passes it on. The beat is measured with the Local peaks settings, which therefore change the rings. The page needs only the help text.
- **Tests first**: the levels against a loop oracle (the averages, the start of the file, a short file), the colors (both ends and the middle), the geometry (140 pixels across, centered, 12 rings of equal width, clear of the circles, other sizes), `None` meaning no rings, the job (a pulsed file shows the rings following the beat; the Local peaks settings change them; the other types byte for byte unchanged).
- **The `NEIGHBOURS` constant**: the user changed it from 8 to 6 in `decay.py` while this feature was being specified. It breaks about 25 existing Decay and Decay Exp tests and my Chromatic Decay step tests, which hard-code 8. This feature does not depend on it, but the Chromatic Decay tests and documents of feature 035 are made to follow the constant (task T002), and the Decay and Decay Exp failures are reported to the user, not "fixed" here (research Decision 7).
- **Documentation**: the README and the help text.

## Technical Context

**Language/Version**: Python 3.10 (backend, FastAPI); Vue 3 / TypeScript (frontend, the help text only).

**Primary Dependencies**: numpy and Pillow (already used). Nothing new.

**Storage**: None.

**Testing**: pytest (`backend/tests`), vitest (`frontend`), run as for features 032 to 035 (`python -B`, cleared `__pycache__`, the mutation helper of the scratchpad).

**Target Platform**: The existing local web service.

**Project Type**: Web application (backend; one frontend help text).

**Performance Goals**: the rings add one small box (140 x 140 pixels) with a matrix product per frame; the job stays about as fast as Chromatic Decay (about 6 s for a three-minute file at 10 frames a second).

**Constraints**: Frames 600 x 400 with the count, names and timing of the other types; deterministic; the other ten image types give identical output; the 12 circles of Chromatic Decay and their decay are unchanged (the circles' pixels do not change when the rings are added).

**Scale/Scope**: about 80 lines in `chromatic_decay.py`, one line in `frame_rendering.py`, a help text and the README; most of the work is tests.

## Constitution Check

The constitution file (`.specify/memory/constitution.md`) is still the unfilled template: no principles, no gates. The project's own practice is followed: tests first, an independent oracle, mutation checks, nothing changed outside the feature, documentation with the change.

Re-check after design: no violation.

## Project Structure

### Documentation (this feature)

```text
specs/036-peak-rings/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── peak-rings.md    # Phase 1 output: the library interface and the picture
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   └── services/
│       ├── chromatic_decay.py              # CHANGED: peak_distances, ring_levels, peak_circle_geometry, the rings in write_chromatic_frames(beat=None), a shared ring-weight helper
│       └── frame_rendering.py              # CHANGED: passes the beat to write_chromatic_frames
└── tests/
    ├── test_chromatic_decay_peaks.py       # NEW: the levels, the colors and the geometry of the rings
    ├── test_chromatic_decay_rendering.py   # CHANGED: a few tests for the rings in the picture (None = none, beat = rings, circles unchanged)
    ├── test_chromatic_decay_api.py         # CHANGED: the job shows the rings; the write_frames comparison passes the beat
    ├── test_chromatic_decay_step.py        # CHANGED (T002): follows NEIGHBOURS instead of the number 8
    └── (others)                            # only where the NEIGHBOURS constant is spelled out as 8 for Chromatic Decay

frontend/src/utilities/help.ts              # CHANGED: the Chromatic Decay help says what the rings show
README.md                                   # CHANGED: Chromatic Decay paragraph
specs/035-chromatic-decay/                  # CHANGED (T002): the documents say "NEIGHBOURS" where they say 8 and six eighths
```

**Structure Decision**: The existing layout; the rings belong to the Chromatic Decay module that draws the picture, behind an optional argument so that nothing else changes.

## Complexity Tracking

No violations to justify.
