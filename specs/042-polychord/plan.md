# Implementation Plan: Polychord

**Branch**: `042-polychord` (no git branch created; spec directory name only) | **Date**: 2026-11-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/042-polychord/spec.md`

## Summary

A ninth image type, **Polychord** (`polychord`): the loudest notes of each frame drawn as a **chain of tapering links that
starts at the center and bends by the circle of fifths**, repeated as **copies turned 30 degrees**, the number of copies
following the **beat**, the whole picture **turning** with a rotation in degrees a second, every link in **one color taken
from the current tempo**, on black.

How it is done (research Decisions 1 to 12):

- **One new module, `backend/app/services/polychord.py`**, with pure numpy functions for everything that is a number
  (`loudest_letters`, `link_turns`, `copy_counts`, `frame_tempos`, `start_angles`, `tempo_colors`, `link_length`,
  `figure_segments`) and the drawing (`_frame`, `write_polychord_frames`). It **imports and does not change**
  `chromatic_decay.ring_position` (the order of the letters on the circle of fifths), `chromatic_decay.beat_distances` (the
  stretched beat), `tempo_finder` (the tempo) and `colormaps.lookup_table`.
- **The turn** is `22.5 x ((pos(next) - pos(previous) + 5) mod 12 - 5)` degrees from the previous link's letter (30 in the first
  version; the user limited the 12 steps to 270 degrees): a fifth +22.5, a fourth -22.5, the same letter 0, the tritone 135. The first link points along the **starting angle**
  `rotation x t / frame_rate`; copy `k` adds `30 k`.
- **The drawing** is one `matplotlib` `LineCollection` for the whole frame on a `Figure` (no `pyplot`): each link is cut
  into 6 pieces whose widths step down, so the end width of a link is the start width of the next; round caps hide the
  seams. A probe took 10 ms a picture and was identical drawn by several threads.
- **The measurement**: `jobs.py` measures the local peaks **once** for this type and derives both the beat (the number of
  copies) and the per-frame tempo (the color) from it (`frame_tempos` is new; it uses `tempo_finder.find_tempo`).
- **The settings**: four new form fields (`polychord_notes`, `polychord_min_copies`, `polychord_max_copies`,
  `polychord_rotation`), parsed and refused before the file is read like `polar_notes`, echoed in the response; a frozen
  `PolychordSettings` and a `PolychordData(tempos, frame_rate)` carry them into `write_frames`.
- **The page**: the option, a group with the four controls (shown for this type only), the Local peaks group, a help text,
  a line in the result list, and the mirror validators.
- **Tests first**: the turn table for all twelve intervals, the letters (ties, silence, fewer notes), the copy counts, the
  tempos and colors, the segments (continuity, widths, nothing outside the picture at any size), the picture (black frame
  for silence, one color, rotation, copies visible, threads = serial), the job through the API (all four settings at and
  beyond their limits, refusal before the file is read with no files left, the response, other types unchanged), the
  frontend. The other eight types are checked against the baseline frames of feature 041.
- **Documentation**: the module docstring (`Order of operations:`), the new aliases in `array_types.py`, the Polychord block
  in the pipeline overview of `image_types.py`, the README, the help text.

## Technical Context

**Language/Version**: Python 3.10 (backend, FastAPI); Vue 3 / TypeScript (frontend).

**Primary Dependencies**: numpy, matplotlib 3.10 (already used by the contour type; `LineCollection`, `Figure`,
`FigureCanvasAgg`), Pillow (to save the PNG as the other types do); `chromatic_decay`, `local_peaks`, `tempo_finder`,
`colormaps`. Nothing new to install.

**Storage**: None (PNG frames in the job's temporary folder, as for every type).

**Testing**: pytest (`backend/tests`, run with `backend/.venv\Scripts\python.exe`, `-p no:cacheprovider`), vitest
(`frontend`), as for features 032 to 041. **The working tree has 25 tests that fail before any change** (the user's
`DEFAULT_PROMINENCE = 15`, listed in `specs/041-code-readability-docs/tools/baseline-failures.txt`): "no regression" means
exactly those and nothing else, and the new tests follow `local_peaks.DEFAULT_PROMINENCE`, never a hard-coded value.

**Target Platform**: The existing local web service.

**Project Type**: Web application (backend and frontend).

**Performance Goals**: about 10 ms a picture on 600 x 400 for the largest figure (12 copies x 8 links x 6 pieces = 576
segments), in the same worker pool as the other types; a three-minute file at 10 frames a second in a few seconds more than
the analysis itself.

**Constraints**: frames 600 x 400 with the count, names and timing of the other types; deterministic (also threaded); the
other eight image types unchanged byte for byte; no change to the response of other types beyond the four new echoed
fields; every function typed and every array documented (feature 041).

**Scale/Scope**: one new module (about 300 lines), small edits in `image_types.py`, `array_types.py`, `frame_rendering.py`,
`jobs.py`, and the frontend's `api.ts`, `SettingsForm.vue`, `groups.ts`, `validation.ts`, `help.ts`, `App.vue`; most of the
work is tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* (Constitution v1.0.0, 2026-11-15.)

- [X] **I. Every function is typed**: every function of `polychord.py`, and every function added to `jobs.py` and
  `frame_rendering.py`, is typed (parameters and return, arrays by alias, `PolychordSettings` and `PolychordData` as
  classes); `test_type_hints.py` scans them and will pass.
- [X] **II. Every array is documented with its meaning and shape**: the eight new kinds of array (`LoudLetters`,
  `LinkTurns`, `CopyCounts`, `FrameTempos`, `StartAngles`, `FigureColors`, `LinkSegments`, `LinkWidths`) get their alias
  with `Shape:`, `Meaning:` and `Made by:` in `array_types.py` first (see [data-model.md](data-model.md)); every function's
  docstring has its `Arrays:` and `Returns:` lines; `PolychordData` has an `Attributes:` block; `test_documentation.py` will
  pass.
- [X] **III. Every processing module states its order of operations**: `polychord.py` is a processing module and is added to
  `PROCESSING_MODULES` in `test_documentation.py`; its docstring starts the `Order of operations:` list (check, letters,
  turns, copies, tempos and colors, angles, segments, drawing); the **polychord block** is added to the `Pipeline overview:`
  in `image_types.py` (and the count and the list of the types in that docstring), and the touched `jobs.py` and
  `frame_rendering.py` keep theirs true.
- [X] **Line width** (`documentation-standard.md` section 5): comments and docstrings wrap at 120 columns.

Re-check after design: no violation; no Complexity Tracking entry is needed.

## Project Structure

### Documentation (this feature)

```text
specs/042-polychord/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── polychord.md     # Phase 1 output: the request, the response, the library, the picture
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── routers/jobs.py                 # CHANGED: the four fields, the one local-peaks measurement for polychord (beat + tempos), the echo
│   └── services/
│       ├── polychord.py                # NEW: settings checks, letters, turns, copies, tempos, colors, segments, picture, write_polychord_frames
│       ├── array_types.py              # CHANGED: eight new aliases with their descriptions
│       ├── frame_rendering.py          # CHANGED: the polychord branch of write_frames (+ its two parameters)
│       └── image_types.py              # CHANGED: the name in IMAGE_TYPES, the overview block
└── tests/
    ├── test_polychord.py               # NEW: settings, letters, turns (12 intervals), copies, tempos, colors, segments
    ├── test_polychord_rendering.py     # NEW: the picture (black, one color, rotation, copies, threads = serial)
    ├── test_polychord_api.py           # NEW: the job, the four settings, refusals, response, other types unchanged
    ├── test_documentation.py           # CHANGED: polychord.py in PROCESSING_MODULES
    └── (others)                        # the tests that spell out the list of image types (test_image_types.py, test_image_type_api.py, test_frame_size.py, ...: listed in tasks.md)

frontend/src/
├── api.ts                              # CHANGED: the four settings in the request and the result
├── App.vue                             # CHANGED: the result list shows them for this type
├── components/SettingsForm.vue         # CHANGED: the option and the group of four controls
└── utilities/
    ├── groups.ts                       # CHANGED: which groups show for polychord
    ├── validation.ts                   # CHANGED: mirror validators
    └── help.ts                         # CHANGED: the help texts
```

**Structure Decision**: the web application layout of the repository (backend `services` for pure functions and drawing,
`routers/jobs.py` for the request, `frontend/src` for the page), exactly as for Chromatic Wireframe (feature 039) and
Rhythm Circles (feature 038): one new service module, a few small wiring edits, tests beside the existing ones.

## Complexity Tracking

No violations; nothing to justify.
