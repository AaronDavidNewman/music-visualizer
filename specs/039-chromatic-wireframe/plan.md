# Implementation Plan: Chromatic Wireframe

**Branch**: `039-chromatic-wireframe` (no git branch created; spec directory name only) | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/039-chromatic-wireframe/spec.md`

## Summary

A thirteenth image type, **Chromatic Wireframe** (`chromatic-wireframe`): the **points of the 12 letters of Chromatic Decay drawn as a 3D ridge plot**. Each frame is one line across the picture (12 bands side by side, each a short slice of `radius x sin((p x 2pi + x) / (64 + xmax))`), the current frame at the front and the earlier frames behind it, as many as fit, each line in one colormap color taken from its frame's place in the beat (peak = last color).

How it is done (research Decisions 1 to 9):

- **One new module, `chromatic_wireframe.py`**, beside `chromatic_decay.py`, which it **reuses unchanged** for everything about the data: `circle_points` (the points of every frame, with the decay rate and the Threshold), `circle_radii` (the radius of a circle for its points), `beat_distances` (the beat position stretched over the range of the file, as Peak Rings uses it). New in the module: `band_width`, `line_angles` / `line_heights` (the x-z function of one frame as a polyline, pure numpy), `line_geometry` (how many lines fit, the step, the shrink, the base), `line_colors` (one color per frame: table row `rint((1 - distance) x 255)`, peak = last), `project_line` (a line at depth `k` on the screen) and `write_wireframe_frames` (the pictures).
- **The drawing**: lines are drawn **back to front** on **black** (revised 2026-11-12: not the colormap's middle color as for the other types); before each line is stroked the area under it down to the picture's bottom is filled with the background (hidden-line removal); everything is drawn at **3 times the size and reduced by an exact box filter**, which gives smooth lines without a new dependency, with Pillow's `ImageDraw` (already used) and fully deterministic.
- **Wiring**: `IMAGE_TYPES` gets the name; `chromatic_decay.CHROMATIC_TYPES` names the two types that share the settings; `frame_rendering.write_frames` gets a branch like Chromatic Decay's (and its decay rate check); `jobs.py` measures the beat for the type and validates the decay rate as 1 to 10 for both types. **No new request or response field.** The frontend gets the option, a settings group with the same controls as Chromatic Decay (Threshold and Decay rate) and the Local peaks group, and a help paragraph.
- **Tests first**: the angle and heights against a loop oracle of the spec's formula, the line geometry (count, step, margins, nothing outside the picture), the colors (peak = last, one per line, different between lines), the picture (hidden lines, scrolling: picture `t` is picture `t - 1` shifted one place back plus a new front line, determinism), the job through the API (the points equal Chromatic Decay's, the decay rate refused outside 1 to 10 before the file is read, other types unchanged byte for byte), the frontend.
- **Documentation**: the README and the help text.

> **Revised 2026-11-12**: the line of a frame is now the **sum of the 12 letters' sines over the whole width** (one smooth function, no jump at the start of a letter), each letter's sine with its own frequency (from its points, 4 turns at 64), amplitude (its radius) and phase (its start); `line_angles` and `line_heights` changed accordingly (see the data model); everything else in this plan holds.

## Technical Context

**Language/Version**: Python 3.10 (backend, FastAPI); Vue 3 / TypeScript (frontend).

**Primary Dependencies**: numpy and Pillow (already used); `chromatic_decay` and `local_peaks`. Nothing new.

**Storage**: None.

**Testing**: pytest (`backend/tests`), vitest (`frontend`), as for features 032 to 038 (`python -B`, cleared `__pycache__`, the mutation helpers of the session scratchpad). **The working tree has the user's uncommitted edit of `chromatic_decay.PRETEND_NEIGHBORS` (4 in HEAD, 6 on disk): the new tests follow `chromatic_decay.circle_points` and the constants, never a hard-coded decay value, so they pass for either.**

**Target Platform**: The existing local web service.

**Project Type**: Web application (backend and frontend).

**Performance Goals**: one picture draws up to 56 polylines of about 1,200 vertices on a 1800 x 1200 canvas, reduced to 600 x 400: a few tens of milliseconds, in the worker pool (as the other types). A three-minute file at 10 frames a second in about the time Chromatic Decay needs or a little more.

**Constraints**: frames 600 x 400 with the count, names and timing of the other types; deterministic; the other twelve image types are unchanged byte for byte; no new request or response field.

**Scale/Scope**: one new module (about 250 lines), small edits in `image_types.py`, `chromatic_decay.py` (one constant), `frame_rendering.py` and `jobs.py`, and five frontend files; most of the work is tests.

## Constitution Check

The constitution file (`.specify/memory/constitution.md`) is still the unfilled template: no principles, no gates. The project's own practice is followed: tests first, an independent oracle, mutation checks, nothing changed outside the feature, documentation with the change.

Re-check after design: no violation.

## Project Structure

### Documentation (this feature)

```text
specs/039-chromatic-wireframe/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── chromatic-wireframe.md  # Phase 1 output: the library interface, the request and the picture
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── routers/jobs.py                    # CHANGED: the beat for the type; the decay rate 1..10 for both chromatic types
│   └── services/
│       ├── chromatic_wireframe.py         # NEW: band_width, line_angles, line_heights, line_geometry, line_colors, project_line, write_wireframe_frames
│       ├── chromatic_decay.py             # CHANGED: one constant, CHROMATIC_TYPES (nothing else)
│       ├── frame_rendering.py             # CHANGED: the chromatic-wireframe branch and the decay rate check
│       └── image_types.py                 # CHANGED: the name in IMAGE_TYPES and the docstring
└── tests/
    ├── test_chromatic_wireframe.py        # NEW: angles, heights, geometry, colors (oracles)
    ├── test_chromatic_wireframe_rendering.py  # NEW: the picture, hidden lines, scrolling
    ├── test_chromatic_wireframe_api.py    # NEW: the job, the decay rate, ignored settings, other types unchanged
    └── (others)                           # the tests that spell out the twelve image types (listed in tasks.md)

frontend/src/
├── utilities/validation.ts                # CHANGED: IMAGE_TYPES, isChromaticType covers both types
├── utilities/groups.ts                    # CHANGED: the group of the type
├── utilities/help.ts                      # CHANGED: the image type help
├── components/SettingsForm.vue            # CHANGED: the group id in TYPE_GROUP_IDS
└── (tests)                                # validation.test.ts, groups.test.ts, SettingsForm.test.ts, api.test.ts, help.test.ts

README.md                                  # CHANGED: Chromatic Wireframe paragraph
```

**Structure Decision**: The existing web-application layout; one service module beside `chromatic_decay.py`, wired like Chromatic Decay (same data, same settings, a different drawing).

## Complexity Tracking

No violations to justify.
