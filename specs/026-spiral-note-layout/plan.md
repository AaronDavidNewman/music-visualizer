# Implementation Plan: Spiral Note Layout

**Branch**: `026-spiral-note-layout` (no git branch created; spec directory name only) | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/026-spiral-note-layout/spec.md`

## Summary

A **Note layout** choice, **Rows** (today, the default) or **Spiral**, for the pictures that draw one shape per note on the 12 × 7 grid: **Tiles**, **Blended tiles** and **Concentric**. The spiral is a fixed arrangement of the 84 drawn notes around middle C (the 28th note, row 3, column 6): the high notes wind clockwise and the low notes counterclockwise, the two arms taking turns, exactly as the table in the spec (13 semitone steps are not between grid neighbours).

How it is done (research Decision 1): the layout is a **permutation of the 84 columns**. A new module holds the table (`note_order(layout)`: for each cell, which note is drawn there; the identity for Rows) and `arrange_notes(values, layout)`, which reorders the 84 values of every frame into **cell order** before the picture is made. The grid pipeline already treats value `i` of a frame as the tile at row `i // 12`, column `i % 12`, and Concentric treats note `n` as the circle on the cell `n`, so **nothing about drawing, coloring, interpolation, blending, threshold, smoothing, the beat or the geometry changes**: only the order of the values handed to them. With Rows the permutation is the identity and the frames are byte-identical to today's.

Work by area:

- **Backend, layout** (new `app/services/note_layout.py`): `LAYOUTS = ("rows", "spiral")`, `DEFAULT_NOTE_LAYOUT`, `check_note_layout`, the spiral built from its rule (and checked against the spec's literal table by the tests), `note_order`, `arrange_notes`.
- **Backend, wiring**: `write_frames(..., note_layout="rows")` checks it for every type and applies it (`arrange_notes` after the note selection, before the grid is interpolated) for `tiles` and `blended`, and before the circles are drawn for `concentric`; Contour, Circles and Circles paint ignore it. `jobs.py` gets the optional field `note_layout` (lowercase `rows` or `spiral`, checked before the file is read) and echoes it.
- **Frontend**: `NOTE_LAYOUTS` (Rows, Spiral), `DEFAULT_NOTE_LAYOUT`, `validateNoteLayout`, `noteLayoutApplies` (Tiles, Blended tiles, Concentric); a new group `note-layout` titled "Note layout" with one dropdown, after the group of the image type and before Local peaks; the form, the request, the summary line "Note layout: Rows|Spiral", a help text; tests.
- **Tests**: the layout (the spec's table cell by cell, every cell once, C at row 3 column 6, its right and left neighbours, the arms' directions, the 13 jumps and no others, Rows is the identity, determinism), `arrange_notes` (a permutation of columns, extra columns untouched, input unchanged), `write_frames` (Rows byte-identical to omitting it; Spiral puts each note's tile at its cell with the same color, for tiles and blended, for several colormaps; hidden notes are the same notes; Notes below 84 spread in pitch order along the spiral; resolution above 1 blends screen neighbours; Concentric circles centered on the note's cell with the same rings; Contour, Circles and Circles paint ignore it), the API (the field, defaults, refusals with the message, echo, ignored for the other types, the reference hashes), and the page (the group and dropdown for the three types only, order of groups, summary, request, help).
- **Docs**: README, `quickstart.md`.

Worth knowing: with the spiral layout **Oversampling blends screen neighbours**, which are notes that are close in pitch in more than one direction, but also, at the 13 jumps and at the edges of the arms, notes that are not (the picture blends what is next to what); the spiral also makes a note's circle in Concentric sit next to notes close in pitch. The four highest notes (not drawn) stay undrawn in both layouts.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing only: numpy, FastAPI, Pillow; Vue, vitest. No new dependency.

**Storage**: None.

**Testing**: pytest (`test_note_layout.py` for the layout, `test_note_layout_rendering.py` for `write_frames`, `test_note_layout_api.py` for the endpoint, the six API tests that list the response keys) and vitest (validation, groups, SettingsForm, App, help, api).

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: No visible cost: one column reorder of an `(frames, 84)` array.

**Constraints**: Deterministic; with Rows (the default) and for Contour, Circles and Circles paint the frames are byte-identical to before (the four reference hashes `6819990556fd4095`, `f32a99c59fcb87fc`, `92b3a27dee73e223`, `400cc93e1bfca03d`); 600 × 400 frames, counts and names unchanged.

**Scale/Scope**: One new backend module (~70 lines), about 15 lines in `frame_rendering.py` and `jobs.py`; frontend edits to about eight files plus tests; README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/026-spiral-note-layout/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── note-layout.md
└── tasks.md             # /speckit-tasks (not created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/services/
│   ├── note_layout.py          # NEW: LAYOUTS, check_note_layout, the spiral, note_order, arrange_notes
│   └── frame_rendering.py      # write_frames(..., note_layout="rows")
├── app/routers/jobs.py         # the field note_layout
└── tests/
    ├── test_note_layout.py            # NEW
    ├── test_note_layout_rendering.py  # NEW
    ├── test_note_layout_api.py        # NEW
    └── (the six API tests that list the response keys)

frontend/
└── src/
    ├── utilities/validation.ts  # layouts, validation, noteLayoutApplies
    ├── utilities/groups.ts      # the group note-layout and groupsFor
    ├── utilities/help.ts        # the help text
    ├── api.ts                   # the field
    ├── App.vue                  # the summary line
    └── components/SettingsForm.vue  # the dropdown and the group (+ tests of each)
README.md
```

**Structure Decision**: Existing web-application layout. The layout is its own small module that knows nothing about images: a note-to-cell table and a column reorder.

## Complexity Tracking

> No Constitution Check violations to justify.
