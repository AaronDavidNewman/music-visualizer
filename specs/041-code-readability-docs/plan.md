# Implementation Plan: Code Readability Documentation

**Branch**: `041-code-readability-docs` | **Date**: 2026-11-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/041-code-readability-docs/spec.md`

## Summary

Make the backend (`backend/app`, 36 modules, 253 functions of which 135 lack a complete type) readable without rereading it: (1) a **type on every parameter and return value**; (2) for every array, **what it represents and its shape**, where one **named alias per kind of array** (`NoteStrengths`, `BeatPositions`, `Pictures`, ...) carries the meaning in the signature and has one canonical description in one new module (`array_types.py`), and each docstring adds the concrete shape; (3) at the top of every processing module an **"Order of operations"** list, plus **one overview of the 8 image types** from uploaded file to saved frames in `image_types.py`; (4) these rules **written into the constitution** (and into the plan template's constitution check), with an automated scan for missing types and a presence check for the other two, so a later feature that forgets them fails a test. Per the user's answer, **only types and documentation change**: no function or class is renamed, moved, split or merged, and no logic changes. A frame-hash baseline taken **before** any edit and compared **after** proves it.

## Technical Context

**Language/Version**: Python 3.10 (backend, virtual environment `backend/.venv`); NumPy 2.2 (`numpy.typing.NDArray` is available)

**Primary Dependencies**: no new dependency (the scan uses the standard library `ast`; the type aliases use `numpy.typing`)

**Storage**: Files only; one new module (`array_types.py`), two new test files, a baseline file for the frame hashes

**Testing**: pytest (`python -B`); the existing 4719 backend and 871 frontend tests must pass unchanged; new tests are the scan (types) and the presence check (docs)

**Target Platform**: The existing local web app (Windows development)

**Project Type**: Web application (backend and frontend); this feature touches the backend and the project's spec-kit files only

**Performance Goals**: None (annotations and docstrings only). The scan must run in under a minute (SC-007): it parses 36 files.

**Constraints**: No behaviour change: all existing tests pass, and every frame of every image type is byte-identical before and after; no logic is edited; annotation expressions are evaluated at import time (no `from __future__ import annotations`, as now), so an alias must exist before it is used and `array_types.py` imports only NumPy (no import cycles)

**Scale/Scope**: 36 modules (about 27 with functions), 253 functions (8 nested), about 144 that touch arrays, 10 classes with array fields, one module-level array table (`note_layout._ORDERS`), 8 image types, and the constitution (an unfilled template today)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is today the unfilled template, so there is no principle to violate. **This feature writes the first principles** (typed functions, documented arrays, documented order of operations), so the gate for this feature is its own spec: FR-008 (they are written into the constitution) and SC-006 (the plan template's check names them). The project's working habits (tests first, README per feature, memory notes, no commit unless asked) are followed but not made constitutional by this feature, because the user asked only for the documentation rules. **Re-check after design: the design follows the three rules it creates (checked by the scan and the presence check on its own new files).**

## Project Structure

### Documentation (this feature)

```text
specs/041-code-readability-docs/
├── plan.md                              # This file
├── research.md                          # Phase 0: decisions (aliases, docstring form, the checks, how to prove "no behaviour change")
├── data-model.md                        # Phase 1: the kinds of arrays (the vocabulary) and the pipeline steps, as first drafted
├── contracts/
│   ├── documentation-standard.md        # the formats: annotation, array line, order of operations, overview, exempt modules
│   └── checks.md                        # what the scan and the presence check test, and their exemptions
├── quickstart.md                        # how to run the checks and prove nothing moved
├── checklists/requirements.md
├── tools/                               # (made by the implementation) verify_frames.py, trace_pipeline.py, baseline-frames.json
└── tasks.md                             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── services/
│   │   ├── array_types.py            # NEW: one alias per kind of array, each with its canonical meaning and shape (only NumPy is imported)
│   │   ├── image_types.py            # CHANGED (docstring only): the overview of the 8 types from file to frames
│   │   └── (about 27 other modules)  # CHANGED (annotations and docstrings only): see the groups in research D7
│   └── routers/                      # CHANGED (annotations and docstrings only): jobs.py, video.py, images.py, hello.py
└── tests/
    ├── test_type_hints.py            # NEW: the scan: no function without a complete type (all of backend/app, nested ones too)
    └── test_documentation.py         # NEW: the presence check: order of operations in processing modules, arrays documented, aliases used

.specify/
├── memory/constitution.md            # CHANGED: the first principles (the three rules) and the governance of their upkeep
└── templates/plan-template.md        # CHANGED: the Constitution Check lists the three rules

README.md                             # CHANGED: one line about the documentation standard and the checks
```

**Structure Decision**: Nothing moves. The only new code is a module of type aliases (names, no behaviour) and two tests; every other change is an annotation or a docstring in an existing file. The tools that prove "no behaviour change" and "the overview is true" live in the feature folder (`tools/`), not in the application.

## Complexity Tracking

No constitution violations to justify. One judgment call is recorded in research D1: adding `array_types.py` is a new module, but it only holds names and descriptions, and it is what lets one description serve every function (FR-004) without moving or renaming anything.
