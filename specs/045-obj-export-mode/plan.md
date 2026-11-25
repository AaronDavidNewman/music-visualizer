# Implementation Plan: 3D export of Contour and Chromatic Wireframe (Wavefront OBJ files)

**Branch**: `045-obj-export-mode` (no git branch; spec directory name only) | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/045-obj-export-mode/spec.md`

## Summary

A new job option, **export mode** (form field `export_obj`, off by default), is offered for Contour and Chromatic Wireframe only. With it on the job writes, besides the PNG frames, one Wavefront OBJ
file per frame (`obj/frame_000000.obj` and up, in the job's frames folder) and offers all of them in one ZIP (`GET /api/jobs/{job_id}/obj`). The files are made from the same numbers as the pictures but
**without the drawing step**: Contour exports the 12 x 7 grid (after the grid smoothing and the beat wave, as the picture draws it) as 84 points and 66 quads in the XY plane, Z the note value scaled to
0-12; Chromatic Wireframe exports, for each frame, the 12 letter points of the frame and of the 11 frames before it (Y = 0 to 11), Z the letter's amplitude scaled to 1-12, no sine, with 144 points and
121 quads in a full file. Each point is `v x y z r g b` with the color as 0-1 decimals (the user's answer); faces are `f a b c d` counterclockwise seen from +Z.

Technical approach, one line each (details in [research.md](research.md)):

1. A new module `services/obj_export.py` (no matplotlib, no Pillow): builds the vertices and faces of a frame (`contour_mesh`, `wireframe_mesh`), formats them (`format_obj`), writes the files
   (`write_contour_obj`, `write_wireframe_obj`) and makes the ZIP (`zip_obj_files`). Three new array aliases in `array_types.py`: `MeshVertices`, `MeshFaces` and `LetterAmplitudes`.
2. `contour.py` gains one small public helper, `smoothed_grid()`, which is the lines of `write_contour_frames` that lay a frame out, flip it and smooth it; `write_contour_frames` calls it, so the
   pictures cannot change (a test and `verify_drawing.py` compare them byte for byte).
3. `frame_rendering.write_frames` takes `export_obj=False`: after the pictures it writes the OBJ files for `contour` and `chromatic-wireframe`; the contour export uses the 12 x 7 grid of the notes
   (note count and threshold applied, resolution not applied, gaussian and interpolate not applied: they change pictures only).
4. `routers/jobs.py` reads `export_obj`, refuses it for any other picture before the file is read, passes it on and answers `export_obj` and `obj_url`; a new route `GET /{job_id}/obj` builds the ZIP
   in the output folder on first request and returns it (404 with a clear message when the job has no export).
5. The page: a new group *3D export* (id `obj-export`) with one checkbox *Export 3D files (.obj)* (id `export-obj`), shown for the two pictures; the result list says whether the export was made and a
   *Download 3D files (.zip)* link appears.
6. Documentation (constitution rules II and III), help text, README and tests are brought in line in the same piece of work.

## Technical Context

**Language/Version**: Python 3.10 (backend), TypeScript with Vue 3 (frontend)

**Primary Dependencies**: FastAPI, NumPy, Pillow, matplotlib; Vue 3, Vite, Vitest. No new dependency (the ZIP uses the standard library).

**Storage**: files in the job's temp folders as before: `frames_temp_dir/<job>/obj/frame_NNNNNN.obj`; the ZIP in `output_dir/<job>/obj.zip` (as the video is in `output_dir/<job>/`).

**Testing**: pytest (`backend/tests`, `backend/.venv/Scripts/python.exe -m pytest`), Vitest. Known baseline: 32 failing backend tests (`DEFAULT_PROMINENCE`, `NEIGHBOURS` ones; ids in
`specs/044-sustained-loudest-notes/baseline-failures-after.txt`), compared by test id at the end; `specs/043-decouple-frame-rate/tools/verify_drawing.py` (all image types, library defaults) as the
no-change gate for the pictures.

**Target Platform**: local web app (FastAPI + Vue page), developed on Windows. The PowerShell speckit scripts cannot run here (execution policy), so the steps are done by hand.

**Project Type**: web application (`backend/` + `frontend/`).

**Performance Goals**: SC-009: the export adds at most 50% to the time of the same job. A contour frame costs one 7 x 12 smoothing pass (84 cells in Python, as the picture already does) and a
string of about 3 KB; a wireframe frame is numpy and a string of about 4 KB. The writing is done with plain `str.join`, one file write per frame.

**Constraints**: byte-identical files for the same input (FR-015: fixed decimals, `\n` line ends, no locale); the pictures with the option off byte-identical to before (FR-001, SC-006); every
file complete in itself.

**Scale/Scope**: up to `max_frames` files per job (a few thousand at the usual settings); each file a few kilobytes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Every function is typed**: every function added or changed in `backend/app` (`obj_export.*`, `contour.smoothed_grid`, `write_frames`, `_parse_export_obj`, the new route, the changed `create_job`)
  has a type on every parameter and its return value; the new arrays use the aliases of `array_types.py`; `test_type_hints.py` will pass (nothing is exempt).
- [x] **II. Every array is documented with its meaning and shape**: three new aliases, `MeshVertices` `(points, 6)`, `MeshFaces` `(faces, 4)` and `LetterAmplitudes` `(frames, 12)`, each with `Shape:`, `Meaning:` and `Made by:` in
  `array_types.py` before they are used in a signature; every array parameter and return of the new functions is named in its docstring with alias and shape (existing aliases reused: `FrameGrid`,
  `GridValues`, `CirclePoints`, `LineColors`, `BeatPositions`); `test_documentation.py` will pass (the new module is added to its list of modules).
- [x] **III. Every processing module states its order of operations**: `obj_export.py` starts with `Order of operations:` (choose the points and heights, scale to 0-12, color each point, join into
  faces, write the file, pack the files); `contour.py`'s list gets the new helper's step noted; `services/image_types.py` gets, for `contour` and `chromatic-wireframe`, an optional **EXPORT** stage
  (`obj_export.write_contour_obj()` / `write_wireframe_obj()`); `frame_rendering.py`'s list is updated.

No other gate in the constitution. No violation: Complexity Tracking is empty.

**Re-check after Phase 1 design**: unchanged, all three still answered by the design in [data-model.md](data-model.md) and [contracts/job-api.md](contracts/job-api.md).

## Project Structure

### Documentation (this feature)

```text
specs/045-obj-export-mode/
├── plan.md              # This file
├── research.md          # Phase 0: the decisions and the places where the spec left room
├── data-model.md        # Phase 1: the vertex and face tables, the ranges, the arrays
├── quickstart.md        # Phase 1: how to see the feature work
├── contracts/
│   └── job-api.md       # Phase 1: the request field, the answer keys, the new route, the OBJ file
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks, not made here)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── routers/jobs.py                  # export_obj field, refusal, answer keys, GET /{job_id}/obj
│   └── services/
│       ├── obj_export.py                # NEW: meshes, formatting, files, ZIP
│       ├── contour.py                   # smoothed_grid() extracted (pictures unchanged)
│       ├── frame_rendering.py           # write_frames(export_obj=False); docs
│       ├── array_types.py               # MeshVertices, MeshFaces
│       └── image_types.py               # overview: EXPORT stage for the two types
└── tests/
    ├── test_obj_export.py               # NEW: the meshes, the format, the ranges, a plain OBJ reader
    ├── test_obj_export_api.py           # NEW: the job field, the ZIP, the refusal, pictures unchanged
    ├── test_documentation.py            # the new module in its list
    └── test_*_api.py (5 key-set tests)  # the answer gains export_obj and obj_url

frontend/src/
├── api.ts                               # exportObj setting -> export_obj; JobResult export_obj, obj_url
├── App.vue                              # result line and the download link
├── components/SettingsForm.vue          # checkbox in the group obj-export
└── utilities/{groups,validation,help}.ts  # group, usesObjExport(), help text (and their tests)

specs/045-obj-export-mode/tools/         # a verify script and the baselines (as in 043 and 044)
README.md                                # a section for the export
```

**Structure Decision**: the existing web application layout (`backend/` + `frontend/`); the one new service module keeps the OBJ writing out of the drawing modules, which stay about pictures.

## Complexity Tracking

> Empty: the Constitution Check has no violations.
