# Quickstart: checking the documentation work

Run from the repository root. Backend commands use `backend/.venv/Scripts/python.exe` with `-B`.

## 0. Before the first edit: the baseline (done once)

```text
backend/.venv/Scripts/python.exe -B specs/041-code-readability-docs/tools/verify_frames.py --write
```

Expected: writes `specs/041-code-readability-docs/tools/baseline-frames.json` with the SHA-256 of every frame of each of the 8 image types (and Contour with Beat coloring on) for the fixed generated input. **This must be done before any file of `backend/app` is edited.**

## 1. The scan (types)

```text
cd backend
.venv/Scripts/python.exe -B -m pytest tests/test_type_hints.py -q
```

Expected after the work: passes. Before the work it fails and lists the 135 functions (that list is the to-do list of the groups of research D8).

## 2. The presence check (the other two kinds)

```text
.venv/Scripts/python.exe -B -m pytest tests/test_documentation.py -q
```

Expected: passes: every module is placed in a list and has its "Order of operations" (or "No data processing") line, every array parameter is named in its docstring, every alias has a description, and the overview names all 8 types and the shared steps.

## 3. Is what is written true? (review with the tools)

```text
backend/.venv/Scripts/python.exe -B specs/041-code-readability-docs/tools/shape_probe.py
backend/.venv/Scripts/python.exe -B specs/041-code-readability-docs/tools/trace_pipeline.py
```

`shape_probe.py` prints, for one job of each image type, the shape and element kind of every array argument and return of each function of `backend/app`: compare with the docstrings you are reviewing (pick 20 at random: SC-002). `trace_pipeline.py` prints, for each image type, the order in which the functions of `backend/app/services` are first called: compare with the module's "Order of operations" and with the type's block in the overview (SC-003, SC-004).

## 4. Nothing moved

```text
backend/.venv/Scripts/python.exe -B specs/041-code-readability-docs/tools/verify_frames.py
cd backend
.venv/Scripts/python.exe -B -m pytest -q
cd ../frontend
npx vitest run
npx vue-tsc --noEmit
```

Expected: `verify_frames.py` reports every frame hash identical to the baseline; the backend suite passes (4719 before the new tests, plus the new ones); the frontend is untouched and still passes.

## 5. The constitution

Open `.specify/memory/constitution.md`: the three principles are there, each with how it is checked and the governance of their upkeep. Open `.specify/templates/plan-template.md`: the Constitution Check lists the three rules (SC-006).
