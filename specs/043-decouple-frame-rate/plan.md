# Implementation Plan: Decouple the frame rate from the frequency buffers

**Branch**: `043-decouple-frame-rate` (no git branch; spec directory name only) | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/043-decouple-frame-rate/spec.md`

## Summary

Every job analyzes the audio at a fixed step of **60 ms** (`sample_rate * 60 / 1000` samples) whatever the frame rate; the frame rate only decides how many frames are made from the buffers.
The window spacing, Smoothing and Smoothing window settings are removed from the page, the request, the job answer and the rendering code. The averaging of the buffers that start in
a frame (`frame_rendering.average_frames()`, which already exists) becomes the only smoothing of the note data. Nothing changes in the image types themselves.

Technical approach, in one line each (details in [research.md](research.md)):

1. A new module `services/buffer_interval.py` replaces `services/window_spacing.py`: one constant (60 ms) and one function that turns it into a step in samples.
2. `routers/jobs.py` no longer reads `window_spacing`, `smoothing` or `smoothing_window` (a form field that is not declared is ignored by the framework, which is what FR-012 asks) and
   always analyzes with the fixed step.
3. `frame_rendering.write_frames()` loses its `smoothing` and `smoothing_window` parameters and `smooth_frames()` is deleted; the shared step SMOOTH leaves the pipeline overview.
4. The page loses the Window spacing field, the Data smoothing group and its two controls, the spacing notices, and (because it existed only to compute the default spacing) the reading of
   the file's sample rate.
5. The documentation, the help texts and the tests are brought in line (constitution rule III: the documentation changes in the same piece of work).

## Technical Context

**Language/Version**: Python 3.10 (backend, per the `cpython-310` bytecode in `backend/`), TypeScript with Vue 3 (frontend)

**Primary Dependencies**: FastAPI, NumPy, Pillow, matplotlib (backend); Vue 3, Vite, Vitest (frontend). No new dependency.

**Storage**: files in the temp folders (`audio_temp_dir`, `frames_temp_dir`); no change.

**Testing**: pytest (`backend/tests`), Vitest (`frontend/src/**/*.test.ts`). Existing known failures: 25 from `DEFAULT_PROMINENCE=15` (spec 041 notes, listed in
`specs/041-code-readability-docs/tools/baseline-failures.txt`) and about 60 Decay / Decay Exp tests from `NEIGHBOURS=6` (feature 036 note); these are left alone and a baseline of the
failing tests is taken before the first edit so that the final run is compared with it.

**Target Platform**: local web app (FastAPI server + Vue page), developed on Windows.

**Project Type**: web application (`backend/` + `frontend/`).

**Performance Goals**: none new. The analysis now makes 16.7 windows per second of audio at every frame rate. The old default was one window per frame, so a job at the default 30 fps
has fewer windows than before (about 44% less) and a job below 16.7 fps has more (at 1 fps, 16.7 times as many); the analysis is the slow part of a job only for long files at low
frame rates, where it stays within the `max_windows` limit.

**Constraints**: the step is exact to within one sample (FR-001): `window_starts()` already rounds `k * step` to the nearest sample, so no start is more than half a sample from its exact
place and the step may be a fraction of a sample (11025 Hz gives 661.5). The limit of `max_windows` (60000) stays.

**Scale/Scope**: 1 new backend module, 1 deleted; edits in `jobs.py`, `frame_rendering.py`, `image_types.py`, `note_analysis.py` (docs), `array_types.py` (docs), `config.py` (comment) and the
docstrings of the modules that say "smoothed"; 7 frontend source files edited and 3 removed; about 12 backend test files and 8 frontend test files edited, 4 removed.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Every function is typed**: the one new function (`buffer_step(sample_rate: float) -> float`) is typed; the changed functions only lose parameters. `test_type_hints.py` will pass.
- [x] **II. Every array is documented with its meaning and shape**: no new kind of array. The `NoteStrengths` description in `array_types.py` mentions `smooth_frames` in its *Made by:*
  and is changed; the arrays described as "smoothed" in other modules are renamed in the same sweep ([research.md](research.md) decision 6). `test_documentation.py` will pass.
- [x] **III. Every processing module states its order of operations**: `buffer_interval.py` is added to the processing list of `test_documentation.py` (in place of `window_spacing.py`) with
  its own `Order of operations:`. `frame_rendering.py` (step 5 removed, steps renumbered), `jobs.py` (step 4), `note_analysis.py` and the overview in `image_types.py` (the shared step
  SMOOTH is removed and the text of AVERAGE says that it is the only smoothing) are updated; `SHARED_STEPS` in `test_documentation.py` loses `SMOOTH`.

**Other gates**: `test_type_hints.py` and `test_documentation.py` pass and the whole backend suite is run and compared with the baseline; `verify_frames.py` cannot be a pure no-change
check for this feature (the default analysis step changes, so the pictures change by design); the plan replaces it with a check that the *drawing* is unchanged
([research.md](research.md) decision 7, [quickstart.md](quickstart.md)).

**Post-design re-check**: no violation; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/043-decouple-frame-rate/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── job-api.md       # Phase 1 output: the request and answer of POST /api/jobs, before and after
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── config.py                       # comment on max_windows no longer mentions the window spacing
│   ├── routers/
│   │   └── jobs.py                     # drop 3 form fields, their parsers and 4 answer keys; fixed step; docs
│   └── services/
│       ├── buffer_interval.py          # NEW (replaces window_spacing.py): BUFFER_INTERVAL_MS, buffer_step()
│       ├── window_spacing.py           # DELETED
│       ├── frame_rendering.py          # drop smoothing constants, smooth_frames(), 2 write_frames parameters; docs
│       ├── image_types.py              # overview: drop step SMOOTH; AVERAGE text; per-type "smoothing" wording
│       ├── note_analysis.py            # docs only: the step is now always 60 ms
│       ├── array_types.py              # docs only: NoteStrengths "Made by"
│       └── (chromatic_decay, decay, decay_exp, polar_chords, polychord, note_selection, contour).py   # docs only: "smoothed" wording
└── tests/                              # see the task list; test_documentation.py lists change

frontend/src/
├── api.ts                              # drop smoothing, smoothingWindow, windowSpacing, window_spacing, spacing_raised ...
├── App.vue                             # drop 3 result lines and the spacing notice; drop the file sample rate
├── components/
│   ├── SettingsForm.vue                # drop the spacing field, the Data smoothing group, the sampleRate prop, the notices
│   └── FilePicker.vue                  # drop the sample rate reading
└── utilities/
    ├── groups.ts                       # drop the "data-smoothing" group
    ├── validation.ts                   # drop SMOOTHING_*, validateSmoothing*, formatSmoothing
    ├── help.ts                         # drop smoothingHelp, smoothingWindowHelp, spacingHelp; update frameRateHelp
    ├── spacing.ts                      # DELETED (with spacing.test.ts)
    └── wavHeader.ts                    # DELETED (with wavHeader.test.ts)
specs/043-decouple-frame-rate/tools/
└── verify_drawing.py                   # NEW: hashes write_frames() output for fixed note values, all image types
```

**Structure Decision**: the existing web-application layout is kept (`backend/app/services` for processing, `backend/app/routers` for the endpoint, `frontend/src` for the page). The only new
source file is `buffer_interval.py`; it is a module of its own (and not a function inside `jobs.py`) because the constitution gives every processing step a named function in a module with
an `Order of operations:`, and because the tests want to call it without the endpoint.

## Complexity Tracking

No violations to justify.
