# Implementation Plan: Top-Energy Notes

**Branch**: `017-top-energy-notes` (no git branch created; spec directory name only) | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/017-top-energy-notes/spec.md`

## Summary

A new setting, **number of notes** n (a whole number from 12 to 84, default 84), builds the picture from only the n drawn notes with the most energy. A note's energy is the sum of its smoothed values over the whole file; the n notes are chosen once, so the same notes are used in every frame (ties go to the lower note), and they keep their order of pitch. For each frame their n values are spread over the 84 values of the original 12 × 7 grid with `np.linspace` positions and `np.interp`; that grid then goes through everything that exists today unchanged: the Resolution setting's interpolation, the Threshold, the colors and the three image types. The colors' scale and the Threshold's reference stay the file's largest smoothed value over all 88 notes. At n = 84 the spread is the identity, so the output is exactly today's.

Work by area:

- **Backend**: a new module `app/services/note_selection.py` (the setting, its check, `top_energy_notes`, `spread_notes`); `write_frames` gains `note_count` and applies the spread between smoothing and the Resolution step; the router gets the `note_count` field and response key. Nothing else changes: the writers, the blender, the contour and the colormaps are untouched.
- **Frontend**: a slider with a readout (`36 of 84 notes`), a help text, a summary line and the field in `api.ts`, with their tests.
- **Tests**: the choice against an independent ranking; the spread against `np.interp` and its invariants; a non-chosen note changing no pixel; the pictures for the three image types and with Resolution; the API; the page. At 84 notes the output must equal the reference hashes recorded before the change.
- **Docs**: README.

Prototypes (research.md) measured the whole choice-and-spread at 0.012 s for 6,000 frames, so the job time is unchanged. They also measured something the spec now says plainly: dropping notes does **not** always make the picture steadier. The average frame-to-frame change of the raw values grows as notes are dropped (each remaining note covers more of the picture); in color space it falls only for sustained notes in strong noise (about 23% at 12 notes). The user asked for the feature "in some cases" and will judge the look: the implementation ends by rendering a strip of consecutive frames at several numbers of notes for them.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing numpy, Pillow, matplotlib, FastAPI; Vue, vitest. No new dependency.

**Storage**: N/A. Same temp directories, file names and PNG kinds.

**Testing**: pytest and vitest. New: `test_note_selection.py` (check function, choice, spread), rendering tests of the setting for the three image types in a new `test_note_count_rendering.py`, `test_note_count_api.py`; the existing exact-response-keys tests gain `note_count`. vitest: range, validation, readout, help, rendered slider, summary. The colormap-list-tolerant helpers are used; no test states a number of contour levels.

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: A 300-frame job at resolution 5 within one minute for every image type, whatever the number of notes (SC-005); jobs at 84 notes are not slower.

**Constraints**: At 84 notes the output is byte-identical to before for every image type (reference hashes in quickstart.md); deterministic output; the same size, frame count, timing and file names for every number of notes.

**Scale/Scope**: One new backend module (~60 lines), a few lines in `frame_rendering.py` and `jobs.py`; frontend edits to five files plus tests; README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/017-top-energy-notes/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── note-count-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── services/
│   │   ├── note_selection.py        # NEW: MIN/MAX/DEFAULT_NOTE_COUNT, check_note_count(), top_energy_notes(), spread_notes()
│   │   └── frame_rendering.py       # write_frames(note_count=): spread between smoothing and the resolution step
│   └── routers/jobs.py              # + note_count field, parser, response key
└── tests/
    ├── test_note_selection.py       # NEW
    ├── test_note_count_rendering.py # NEW
    ├── test_note_count_api.py       # NEW
    └── test_resolution_api.py, test_colormap_api.py, test_contour_api.py   # exact response keys + note_count

frontend/src/
├── api.ts                           # + note_count (settings, result, form field)
├── App.vue                          # + summary line
├── components/
│   ├── SettingsForm.vue             # + Notes slider after the Threshold
│   └── SettingsForm.test.ts
└── utilities/
    ├── validation.ts                # + NOTE_COUNT_RANGE, DEFAULT_NOTE_COUNT, validateNoteCount, formatNoteCount, formatNoteCountSummary
    ├── validation.test.ts
    ├── help.ts                      # + noteCountHelp
    └── help.test.ts

README.md                            # Notes documented
```

**Structure Decision**: The setting, the choice and the spread live in their own pure-numpy module with no knowledge of pictures, like `resolution.py`; `write_frames` only calls it. Because the spread produces an array of exactly the shape that the rest of the pipeline already takes (84 values per frame), no writer, blender or contour code changes, which is what keeps the 84-note output byte-identical.

## Complexity Tracking

No constitution violations. Nothing to justify.
