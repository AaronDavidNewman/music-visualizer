# Implementation Plan: Polar Chords

**Branch**: `032-polar-chords` (no git branch created; spec directory name only) | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/032-polar-chords/spec.md`

## Summary

A ninth image type, **Polar Chords** (`polar-chords`): a polar bar graph in the 600 × 400 frame. The 84 piano notes have 84 equal arcs **clockwise from the top** in order of pitch; the `N` loudest notes of a frame (the new setting **Notes shown**, 5 to 8, default 5) get a bar that fills its arc. The chord that the chord interval measurement (feature 031) records for the frame, among the 7 types `(7)`, `(4, 7)`, `(3, 7)`, `(4, 10)`, `(4, 11)`, `(3, 7, 10)`, `(4, 6)`, gets one bar in its place `type × 12 + root` in 84 arcs **counterclockwise from the top**. Every bar reaches out to `0.5 + 0.5 × p` of the full radius, `p` being the frame's place in the local energy peak (0 to 1). Notes are colored from the middle of the colormap (faint) to its start (loud), the chord from the middle to its end. The Note layout (rows or spiral) says in which arc each note is; the chords do not depend on it (research Decision 7).

How it is done (research Decisions 1 to 6):

- **A new module `polar_chords.py`** with two parts that are independent of each other: the **bars** of every frame worked out in one pass over the file (`polar_bars`: the notes, the chord with its place, the strength shares, the lengths), and the **drawing** (`write_polar_frames`). The bars are small arrays `(frames, N)` and `(frames,)`, testable without any drawing.
- **The note bars follow their notes (research Decision 8).** `note_targets` ranks the loudest notes and gives the arc of each; `follow_arcs` keeps the arc of each volume from frame to frame and moves it one arc a frame toward its target the shorter way round; `polar_bars` hides a bar that is in the same arc as a louder volume's. Drawing is unchanged.
- **The chords come from feature 031 unchanged**: `measure_chords(smoothed, POLAR_CHORD_TYPES)` once for the whole file. Its place is simply the index of the recorded type (the root is not used, revised 2026-11-06).
- **Drawing by arcs, not by a loop over pixels.** For the frame size, once, every pixel inside the circle gets its note arc (clockwise), its chord arc (counterclockwise), its distance from the center, and the neighbouring arc with the share of the pixel that reaches into it (the way the rings of Concentric are smoothed). Per arc, the lists of pixels are kept. A frame then touches only the pixels of its (at most 8 + 1) bars: the coverage of a bar is `clip(length − distance + 0.5, 0, 1)` along its length and the arc edges are smooth. The notes are composited over the background, the chord over the notes.
- **Settings.** `IMAGE_TYPES` gets `polar-chords`; `write_frames(..., polar_notes=5)` checks the number for every type and draws Polar Chords from the smoothed values and the beat; `jobs.py` gets the optional field `polar_notes`, measures the beat for `polar-chords` as for `concentric`, and echoes the number. `note_layout` (rows or spiral, already a field of every job) gives the arc of each note; Threshold, Notes, Oversampling, Interpolate and Gaussian smoothing are checked and ignored.
- **Frontend.** `polar-chords` joins `IMAGE_TYPES`; `POLAR_NOTES_RANGE`, `DEFAULT_POLAR_NOTES`, `validatePolarNotes`, `isPolarType`; a type group `polar-chords` titled "Polar chords" with one slider (Notes shown, 5 to 8); the grid settings do not apply, the note layout and the Local peaks (no checkbox) do; the request, the summary line, help text; tests.
- **Tests**: the places (all 7 types × 12 roots × every inversion against an independent calculation of the type recorded: the place is the type, whatever the root), the arcs and angles, the lengths, the colors, the loudest notes (ties, silence, fewer than N), the chord (none, one, inversions, a fourth as an inverted fifth), the drawing at the pixel level, `write_frames` and the API (field, default, refusals, echo, ignored by the other types, the reference hashes of the other eight types), and the page.
- **Docs**: README, `quickstart.md`.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: numpy, FastAPI, Pillow; Vue, vitest. No new dependency.

**Storage**: None.

**Testing**: pytest (`test_polar_chords.py` for the bars, `test_polar_chords_rendering.py` for the drawing and `write_frames`, `test_polar_chords_api.py` for the endpoint, and the API tests that list the response keys and the image type names) and vitest (validation, groups, SettingsForm, App, help, api).

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: A 60 second file at 30 frames a second (1,800 frames) in under 30 seconds (SC-006), and no noticeable difference from Concentric (FR-012). The chord measurement for the whole file is milliseconds (feature 031); a frame touches about 9 arcs of about 1,400 pixels each, plus the PNG.

**Constraints**: Deterministic; the other eight image types byte-identical to before (the existing reference-hash tests); 600 × 400 frames, counts and names unchanged.

**Scale/Scope**: One new backend module (about 250 lines), about 15 lines in `image_types.py`, `frame_rendering.py` and `jobs.py`; frontend edits to about eight files plus tests; README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/032-polar-chords/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── polar-chords.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks (not created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/services/
│   ├── polar_chords.py          # NEW: polar_bars, chord_place, check_polar_notes, write_polar_frames
│   ├── image_types.py           # IMAGE_TYPES gets "polar-chords"; module docstring
│   └── frame_rendering.py       # write_frames(..., polar_notes=5), the polar-chords branch
├── app/routers/jobs.py          # the field polar_notes; the beat is measured for polar-chords
└── tests/
    ├── test_polar_chords.py            # NEW
    ├── test_polar_chords_rendering.py  # NEW
    ├── test_polar_chords_api.py        # NEW
    └── (the API tests that list the response keys and the image type names)

frontend/
└── src/
    ├── utilities/validation.ts  # the type, the notes-shown range, validation, isPolarType and the applies-functions
    ├── utilities/groups.ts      # the group polar-chords and groupsFor
    ├── utilities/help.ts        # the help texts
    ├── api.ts                   # the field
    ├── App.vue                  # the summary line
    └── components/SettingsForm.vue  # the slider and the group (+ tests of each)
README.md
```

**Structure Decision**: Existing web-application layout. `polar_chords.py` is its own module like `concentric.py` and `decay.py`: it knows nothing about the note analysis, the beat measurement or the router; the smoothed values (in note order), the beat positions, the colormap and the size are passed in. It uses `chords.measure_chords` (feature 031) and the colormap helpers.

## Complexity Tracking

> No Constitution Check violations to justify.
