# Implementation Plan: Energy Saturation

**Branch**: `009-energy-saturation` (no git branch created; spec directory name only) | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-energy-saturation/spec.md`

## Summary

Frame colors get a second, note-independent measure. For every frame the backend measures an **energy** straight from the audio samples of that frame's period: the audio is cut into internal windows of `round(32 × sample_rate / 44100)` samples (at least 2) laid end to end from the frame's first sample, the population standard deviation of the left and of the right channel is found in each window and the two are averaged, and the frame's energy is the mean over its full windows (a leftover shorter than a window is ignored; a frame with no full window measures what samples it has as one window). The frame's **saturation**, shared by all 84 tiles, is `(energy / largest energy in the file) ** (1 / energy_root)`, then smoothed over the frames with the same running average as the hue. This replaces the fixed 50% saturation in `tile_colors`; brightness (value) and hue are unchanged.

A new setting, **Energy** (whole number 1 to 8, default 1), is added to the settings form and the job API (optional form field `energy`, handled like `brightness`), and the result summary and response report it.

Technically: a new service module `energy.py` holds `internal_window` and `frame_energies`; `frame_rendering.py` gains `saturation_sequence` and a `saturation` argument on `tile_colors`; `write_frames` and `create_job` pass the energies through. The frontend adds the validated field, its explanation and a summary line. No new dependency.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: numpy, scipy (WAV reading), Pillow, FastAPI; Vue, vitest. No new packages.

**Storage**: N/A. Same temp directories; PNGs stay indexed-colour (a frame still has at most 84 flat colours).

**Testing**: pytest: the energy definition against hand-computed values (0.5, 0.25, 0), constant level, mono, one loud channel, leftover and short final frames, bit-depth independence, rate invariance, `internal_window` at several rates; the saturation rule (proportion, roots 1 to 8, peak 0, bounds, monotonic in the root, smoothing); `tile_colors` with a given saturation (darkest channel 0 at 100%, equal channels at 0%, value and hue untouched); a three-frame file through `write_frames` and through the API (loud, quarter, silent); the new form field's validation and response; determinism. The two job-level tests that assume 50% saturation are updated. vitest: `validateEnergy`, the energy explanation text.

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: Time to create the same frames no more than 25% longer than before (SC-007). Energy is one pass over the samples (about 12 numpy calls per frame). It is measured while implementing on the sample file; if it misses the budget, frames that share an integer period are processed in one vectorized batch (research Decision 3).

**Constraints**: Energy is measured on the file's own samples at the file's sample rate; deterministic output; image size, layout, frame count, timing, hue and brightness unchanged; no change to results already created.

**Scale/Scope**: One new backend module, edits to `frame_rendering.py` and `jobs.py`, one new test module plus edits to two existing ones, frontend edits to five files (`validation.ts`, `help.ts`, `api.ts`, `SettingsForm.vue`, `App.vue`) with tests, and documentation.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. The plan adds one small module and no dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/009-energy-saturation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── energy-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── services/
│   │   ├── energy.py                 # NEW: internal_window(), frame_energies()
│   │   └── frame_rendering.py        # saturation_sequence(); tile_colors/render path take a saturation; write_frames takes energies + root
│   └── routers/jobs.py               # new optional "energy" form field, energies computed, "energy" in the response
└── tests/
    ├── test_energy.py                # NEW: energy definition, window scaling, edge cases
    ├── test_frame_rendering.py       # saturation_sequence, tile_colors with saturation, write_frames with energies
    └── test_jobs_api.py              # energy field validation and response; 50%-saturation assertions updated

frontend/src/
├── api.ts                            # JobSettings.energy, JobResult.energy, form field
├── App.vue                           # "Energy: n" in the result summary
├── components/SettingsForm.vue       # Energy field (row of two with Brightness) and info popover
└── utilities/
    ├── validation.ts                 # ENERGY_RANGE, DEFAULT_ENERGY, validateEnergy
    ├── validation.test.ts
    ├── help.ts                       # energyHelp
    └── help.test.ts

README.md and specs/007 docs          # image description: saturation now follows the energy
```

**Structure Decision**: Energy is a property of the audio, not of the note analysis, so it gets its own small module (`energy.py`) beside `note_analysis.py` and `window_spacing.py` rather than being added to either. Mapping energy to saturation is a rendering decision and lives in `frame_rendering.py` next to the hue code it parallels (`saturation_sequence` mirrors `hue_sequence`). The helpers keep a default saturation of 0.5 when called without one, so direct helper callers and their tests are unaffected, while the job path always supplies the energy-derived value. In the frontend the new field follows the pattern of Brightness exactly.

## Complexity Tracking

No constitution violations. Nothing to justify.
