# Implementation Plan: Spirograph

**Branch**: `046-spirograph` (no git branch created; spec directory name only) | **Date**: 2026-11-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/046-spirograph/spec.md`

## Summary

A tenth image type, **Spirograph** (`spirograph`): the loudest notes of each frame are kept as a **history entry** (their values
and their indices), and the picture of a frame draws **one 1000-point spirograph curve for every note of each of the last
History length entries** (oldest first), each curve in one of **13 reduced colors** of the colormap picked by the note's value,
on black. The curve is the user's: `X = val x (rc cos c1 + loops cos c2)`, `Y` with sines, `c1` over 0 to 2 pi, `c2` over
0 to 2 pi `turns`, `loops = (index mod 12) val`; since 2026-11-24 `turns = 14 pct + 6` and `rc` 5 or 4 by the place `pct` of the entry's frame in the local peak (research Decision 14).

How it is done (research Decisions 1 to 11):

- **One new module, `backend/app/services/spirograph.py`**, with pure numpy functions for everything that is a number
  (`tracked_notes`, `reduced_colors`, `color_numbers`, `spiro_curves`, `file_extent`, `pixels_per_unit`, `window_curves`) and
  the drawing (`_frame`, `write_spirograph_frames`). It **imports and does not change** `held_notes.hold_loudest` (the
  tracked notes) and `colormaps.lookup_table` (the colors).
- **The history is a sliding window over per-frame arrays**, not a stored deque: `tracked_notes()` makes `TrackedValues` and
  `LoudestIndices` for all frames at once (`(frames, count)`), and the picture of frame `t` slices rows
  `max(0, t - history + 1)` to `t` (oldest first, loudest first inside a row), which is exactly the user's two loops, with the
  value and the index of a step both from entry `i`, slot `j`.
- **One fixed scale for the whole file**: the farthest point of any curve is the first one (`c1 = c2 = 0`, both cosines 1),
  at `val x (rc + (index mod 12) x val)`, so the file's extent is the maximum of that over every tracked note, exactly and without
  sampling; the scale (pixels a unit) makes that extent fit the picture, centered and round.
- **The drawing** is one `matplotlib` `LineCollection` for the whole frame on a `Figure` (no `pyplot`), one 1000-point polyline
  for each curve with a value above 0, in the order of the loops, drawn by a few threads like Polychord.
- **The beat (since 2026-11-24)**: Spirograph uses the beat (not the tempo), so the job measures the local peaks for it
  (with the Minimum distance of the request) and the page shows the Local peaks group (Minimum distance only) for it.
- **The settings**: two new form fields (`spirograph_notes`, `spirograph_history`), parsed and refused before the file is read
  like `polychord_notes`, echoed in the response; a frozen `SpirographSettings(notes, history)` carries them into
  `write_frames`. **Extra notes** (feature 044) applies: `held_notes` learns the new type, and because its setting stops at 8
  while this type can track 12 notes, k is **1 to the smaller of the number of notes and 8** (research Decision 6).
- **The page**: the option, a group with the two controls (shown for this type only, followed by Held notes), a help text, a
  line in the result list, and the mirror validators.
- **Tests first**: the curve against the formula (a million-th), the reduced colors and the color numbers, the tracked notes
  (silence, fewer notes, ties, held), the window (counts, first frames, sharing between consecutive frames, step `(i, j)` uses
  entry `i` only), the scale (nothing outside the picture at any size), the picture (black for silence, determinism,
  threads = serial), the job through the API (both settings at and beyond their limits, refusal before the file is read with no
  files left, the response, other types unchanged), the frontend. The other nine types are checked against the baseline
  frames of the earlier tools.
- **Documentation**: the module docstring (`Order of operations:`), the four new aliases in `array_types.py`, the Spirograph
  block in the pipeline overview of `image_types.py` (and the counts and lists of types), `held_notes.py`, `frame_rendering.py`
  and `jobs.py` docstrings, the README, the help text.

## Technical Context

**Language/Version**: Python 3.10 (backend, FastAPI); Vue 3 / TypeScript (frontend).

**Primary Dependencies**: numpy, matplotlib 3.10 (already used by the contour and polychord types; `LineCollection`,
`Figure`, `FigureCanvasAgg`), Pillow (to save the PNG as the other types do); `held_notes`, `colormaps`,
`frame_saving.SAVE_WORKERS`. Nothing new to install.

**Storage**: None (PNG frames in the job's temporary folder, as for every type).

**Testing**: pytest (`backend/tests`, run with `backend/.venv/Scripts/python.exe`, `-p no:cacheprovider`), vitest (`frontend`), as
for features 032 to 045. **The working tree has 32 tests that fail before any change** (`specs/045-obj-export-mode/baseline-failures-after.txt`; the 25
of feature 041 and 7 more): "no regression" means exactly those ids and nothing else. New tests never hard-code
`local_peaks.DEFAULT_PROMINENCE` (Spirograph does not use it anyway).

**Target Platform**: The existing local web service.

**Project Type**: Web application (backend and frontend).

**Performance Goals**: under 2 seconds a picture at the largest settings (12 notes, history 12: 144 curves of 1000 points on
600 x 400), expected well under 0.5 s (research Decision 9 measures it first); a 300-frame job at the defaults (64 curves a
picture) finishes in the same order of time as Polychord's.

**Constraints**: frames 600 x 400 with the count, names and timing of the other types; deterministic (also threaded); the
other nine image types unchanged byte for byte; no change to the response of other types beyond the two new echoed fields;
every function typed and every array documented (feature 041); no import of `pyplot`.

**Scale/Scope**: one new module (about 250 lines), small edits in `image_types.py`, `array_types.py`, `held_notes.py`,
`frame_rendering.py`, `jobs.py`, and the frontend's `api.ts`, `SettingsForm.vue`, `groups.ts`, `validation.ts`, `help.ts`,
`App.vue`; most of the work is tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* (Constitution v1.0.0, 2026-11-15.)

- [X] **I. Every function is typed**: every function of `spirograph.py`, and every function added or changed in `jobs.py`,
  `frame_rendering.py` and `held_notes.py` (`notes_of` gets a fourth typed parameter), is typed (parameters and return,
  arrays by alias, `SpirographSettings` as a class); `test_type_hints.py` scans them and will pass.
- [X] **II. Every array is documented with its meaning and shape**: the four new kinds of array (`TrackedValues`,
  `ColorNumbers`, `ReducedColors`, `SpiroCurves`) get their alias with `Shape:`, `Meaning:` and `Made by:` in `array_types.py`
  first (see [data-model.md](data-model.md)); the tracked indices reuse `LoudestIndices` (one description for one kind of
  array); every function's docstring has its `Arrays:` and `Returns:` lines; `test_documentation.py` will pass.
- [X] **III. Every processing module states its order of operations**: `spirograph.py` is a processing module and is added to
  `PROCESSING_MODULES` in `test_documentation.py`; its docstring starts the `Order of operations:` list (check, track,
  colors, extent and scale, window, curves, drawing); the **spirograph block** is added to the `Pipeline overview:` in
  `image_types.py` (and the count and list of types in that docstring, and "the seven types that take the n loudest notes"), and
  the touched `jobs.py`, `frame_rendering.py` and `held_notes.py` keep theirs true.
- [X] **Line width** (`documentation-standard.md` section 5): comments and docstrings wrap at 120 columns in the new module
  (the older files keep their own habit).

Re-check after design: no violation; no Complexity Tracking entry is needed.

## Project Structure

### Documentation (this feature)

```text
specs/046-spirograph/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── spirograph.md    # Phase 1 output: the request, the response, the library, the picture
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── routers/jobs.py                 # CHANGED: the two fields, the parse, the extra-notes limit, the echo (no measurement)
│   └── services/
│       ├── spirograph.py               # NEW: settings checks, tracked notes, colors, curves, extent, window, picture, write_spirograph_frames
│       ├── array_types.py              # CHANGED: four new aliases with their descriptions
│       ├── held_notes.py               # CHANGED: "spirograph" in HELD_NOTES_TYPES, notes_of() 4th parameter, docs
│       ├── frame_rendering.py          # CHANGED: the spirograph branch of write_frames (+ its parameter), _check_extra_notes, docs
│       └── image_types.py              # CHANGED: the name in IMAGE_TYPES, the overview block, the counts
└── tests/
    ├── test_spirograph.py              # NEW: settings, tracked notes, colors, curves, extent, window
    ├── test_spirograph_rendering.py    # NEW: the picture (black, colors, history, determinism, threads = serial, size, timing)
    ├── test_spirograph_api.py          # NEW: the job, the two settings, refusals, response, other types unchanged
    ├── test_documentation.py           # CHANGED: spirograph.py in PROCESSING_MODULES
    └── (others)                        # the tests that spell out the list of image types or the response keys (listed in tasks.md)

frontend/src/
├── api.ts                              # CHANGED: the two settings in the request and the result
├── App.vue                             # CHANGED: the result list shows them for this type
├── components/SettingsForm.vue         # CHANGED: the option and the group of two controls
└── utilities/
    ├── groups.ts                       # CHANGED: the spirograph group, held notes for it, no local peaks
    ├── validation.ts                   # CHANGED: the option, the mirror validators, usesHeldNotes, heldNotesCount
    └── help.ts                         # CHANGED: the help texts
```

**Structure Decision**: the web application layout of the repository (backend `services` for pure functions and drawing,
`routers/jobs.py` for the request, `frontend/src` for the page), exactly as for Polychord (feature 042) minus its
measurement: one new service module, a few small wiring edits, tests beside the existing ones.

## Complexity Tracking

No violations; nothing to justify.
