# Implementation Plan: Energy Graphs

**Branch**: `034-energy-graphs` (no git branch created; spec directory name only) | **Date**: 2026-11-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/034-energy-graphs/spec.md`

**Revised 2026-11-08**: the pies are removed (and with them the measurement of the rest of the spectrum: `analyze_channels(rest=...)`, `AnalysisResult.rest_rms` and `note_analysis.py` are **not changed** by this feature), and the histogram gets a second data set, the amplitude as accumulated quasi-decibels, drawn as the softmax of each data set's totals divided by its largest total (see [spec.md](spec.md), [data-model.md](data-model.md) and [contracts/energy-graphs.md](contracts/energy-graphs.md), which are current). Where the Summary and the structure below, and [research.md](research.md), speak of pies, shares, the rest of the spectrum or the 600 x 400 layout of the first version, this note replaces them; the wiring (`write_frames(energy=...)`, `frame_windows`, the job, the frontend) is unchanged.

## Summary

A tenth image type, **Energy Graphs** (`energy-graphs`): every frame is one picture of three graphs on the colormap's middle color (FR-001, FR-010): a **running histogram** of the 84 notes along the bottom, and two **pies** side by side above it (harmonic against non-harmonic energy; this window's loudness against the loudest window of the file). It has **no setting of its own**: no request field, no response field (the analysis settings, the colormap and the image type are all it uses).

How it is done (research Decisions 1 to 9):

- **One new module, `energy_graphs.py`**, in the style of `polar_chords.py`: the numbers of every frame are worked out first, in small arrays that can be tested on their own (`frame_energy`: the histogram, the harmonic share, the loudness share), then each frame is drawn independently (`write_energy_frames`), by Pillow, from a background that is drawn once, in the thread pool the other types use.
- **The histogram** ranks the 84 notes of every analysis window by strength (ties: the lower note first), gives 84 to the loudest down to 1, and 0 to a silent note and to every note below it in rank; a cumulative sum over the windows gives the histogram of every frame at once. Each window is counted **exactly once**, in the frame it starts in (so the last frame holds the sum over all windows, SC-002). The bars are drawn relative to the tallest bar.
- **The non-harmonic energy needs the whole spectrum**, which the note analysis threw away: `analyze_channels` gets a keyword `rest=False`; with `True` it also records, for every window, **the RMS magnitude of the spectrum outside the 84 note positions** (`AnalysisResult.rest_rms`, shape `(windows,)`), from the same transform it already does (one squared magnitude and one dot product with a 0/1 weight vector per window: no new transform). Only this image type asks for it, so the others cost nothing more (SC-005).
- **Pies**: harmonic share = `H / (H + R)` with `H` the RMS of the 84 note strengths (after the noise floor, FR-012) and `R` the RMS of the rest of the spectrum; loudness share = `H` of the frame over the largest `H` of any window of the file. A frame that holds several windows uses the RMS over them; a frame with none uses the last window before it, as `average_frames` does (that mapping is shared by a small refactor).
- **Wiring**: `IMAGE_TYPES` gets the name; `jobs.py` asks the analysis for the rest only for this type, builds the `frame_energy` data after `floor_analysis` and passes it to `write_frames` (new keyword `energy`); `write_frames` draws it. The beat is not measured. The frontend gets the option, a help text and no type group; the Data smoothing group is not shown for it.
- **Tests first**: oracle-based tests of the ranks and the accumulation, of the rest RMS against numpy on a synthetic signal, of the shares, of the drawing (tallest bar height, empty pies, determinism, picture size), the job (every field, silent file, a file of one tone), the frontend groups; the existing suites to show nothing else changed.
- **Documentation**: the README (an Energy Graphs paragraph, the image type list) and the help text.

## Technical Context

**Language/Version**: Python 3.10 (backend, FastAPI); Vue 3 / TypeScript (frontend, small changes).

**Primary Dependencies**: numpy and Pillow (already used; Pillow >= 10.4 gives `ImageFont.load_default(size=...)`); matplotlib is used only through `colormaps.lookup_table`, as the other types do. Nothing new.

**Storage**: None. The frames are PNGs in the job's frame directory like the other types.

**Testing**: pytest (`backend/tests`), vitest (`frontend`), run as for features 032 and 033 (`python -B`, cleared `__pycache__` for mutation checks).

**Target Platform**: The existing local web service.

**Project Type**: Web application (backend and frontend).

**Performance Goals**: the extra spectrum measurement at most doubles the analysis time (SC-005); a frame draws in a few milliseconds (a static background copied, two small pies supersampled, up to 84 rectangles), in the worker pool.

**Constraints**: Frames 600 x 400 with the count, names and timing of the other types; deterministic (FR-013); the other nine types give identical output and the analysis of a job that does not ask for the rest is unchanged; no new request or response field.

**Scale/Scope**: One new module (about 250 lines), small edits in `note_analysis.py`, `frame_rendering.py`, `image_types.py`, `jobs.py` and four frontend files; most of the work is tests.

## Constitution Check

The constitution file (`.specify/memory/constitution.md`) is still the unfilled template: no principles, no gates. The project's own practice is followed: tests first, an independent oracle, mutation checks, nothing changed outside the feature, documentation with the change.

Re-check after design: no violation.

## Project Structure

### Documentation (this feature)

```text
specs/034-energy-graphs/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── energy-graphs.md # Phase 1 output: the library interface, the request and the picture
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── routers/
│   │   └── jobs.py                    # CHANGED: asks the analysis for the rest, builds the energy data, passes it to write_frames (energy-graphs only)
│   └── services/
│       ├── energy_graphs.py           # NEW: rank_scores, frame_energy, EnergyGraphData, write_energy_frames
│       ├── note_analysis.py           # CHANGED: analyze_channels(rest=...), AnalysisResult.rest_rms
│       ├── frame_rendering.py         # CHANGED: frame_windows shared with average_frames; write_frames(energy=...) and the energy-graphs branch
│       └── image_types.py             # CHANGED: the name in IMAGE_TYPES and the docstring
└── tests/
    ├── test_energy_graphs.py          # NEW: ranks, accumulation, shares, frame mapping (oracle)
    ├── test_energy_graphs_rendering.py# NEW: the picture
    ├── test_energy_graphs_api.py      # NEW: the job end to end
    ├── test_note_analysis.py          # CHANGED: rest_rms against numpy; unchanged output without it
    └── (others)                       # only where a list of the image types is checked (listed in tasks.md)

frontend/src/
├── utilities/validation.ts            # CHANGED: IMAGE_TYPES, isEnergyType
├── utilities/groups.ts                # CHANGED: no Data smoothing group for the type
├── utilities/help.ts                  # CHANGED: the image type help
└── (tests)                            # groups.test.ts, validation.test.ts, SettingsForm.test.ts, api.test.ts

README.md                              # CHANGED: Energy Graphs paragraph
```

**Structure Decision**: The existing web-application layout; one service module beside `polar_chords.py`, the same kind of wiring as feature 032 (image type name, `write_frames` branch, frontend list), minus the type's own setting.

## Complexity Tracking

No violations to justify.
