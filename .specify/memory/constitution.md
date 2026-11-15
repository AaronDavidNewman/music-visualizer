# Music Visualizer Constitution

## Core Principles

### I. Every function is typed

Every function, method and nested function of the backend (`backend/app`) has a type on every parameter (except `self` and `cls`) and on its return value (`-> None` when
nothing is returned). An array is annotated with the **named alias** of its kind from `backend/app/services/array_types.py` (for example `NoteStrengths`), never a bare
`np.ndarray`. A type is never turned into a conversion or a check, and a function that cannot be typed narrowly gets the widest honest type and says in its docstring what it
is in practice.

*How it is checked:* `backend/tests/test_type_hints.py` scans every file of `backend/app` and fails for any function without a complete type. It has no list of exceptions:
a function added without types fails it.

### II. Every array is documented with its meaning and its shape

A function that takes or returns an array (directly, in a tuple or in a field of a returned object) says, in its docstring, for **each array**: its name, its alias, the
**concrete shape with named axes** (for example `(frames, 88)`, and each case when the shape depends on a setting), and **what the numbers represent** (the quantity, its unit or
range, and what each axis indexes). A class with array fields documents each field in an `Attributes:` block; an array defined at module level has a comment with the same two
things. **One description for each kind of array**: it lives in `array_types.py` next to the alias, the docstrings refer to it, and the same kind is described in the same
words everywhere. A new kind of array gets its alias and description before it is used in a signature.

*How it is checked:* `backend/tests/test_documentation.py` checks that the documentation is **there** (every array parameter is named in the docstring, a `Returns:` line, an
`Attributes:` block, a description with `Shape:`, `Meaning:` and `Made by:` for every alias). Whether a description is **true** is checked in review with
`specs/041-code-readability-docs/tools/shape_probe.py`, which prints the shapes that a job really passes.

### III. Every processing module states its order of operations, and the image types have one overview

The module docstring of every module that transforms data starts with an `Order of operations:` numbered list: the order in which the data is transformed, the function that
does each step, and what the data is after it (alias and shape). A module that only holds constants, settings, names or routing says `No data processing:` and what it holds.
`backend/app/services/image_types.py` holds the **pipeline overview**: the shared steps of a job (READ, ANALYZE, FLOOR, MEASURE, AVERAGE, SMOOTH, DRAW, SAVE) and, for each image
type, which of them it uses and its own drawing stages, in order. **A change to the steps of a module, or to an image type, changes this documentation in the same piece of
work.**

*How it is checked:* `test_documentation.py` checks that every module with code is in one of its two lists and has its `Order of operations:` (or `No data processing:`), and
that the overview names all image types and all shared steps. Whether the order is **the real order** is checked in review with
`specs/041-code-readability-docs/tools/trace_pipeline.py`, which prints the order in which a job first calls the functions of each image type (a step done by a helper that the
function of another step calls says `called by`).

## The documentation standard

The forms of the three rules (the annotation rule, the array line, the order-of-operations list, the overview, the exempt-module line) are written in
`specs/041-code-readability-docs/contracts/documentation-standard.md`; what the two checks test is in `specs/041-code-readability-docs/contracts/checks.md`. The aim is that a
person who has forgotten what a type of picture does, or what an array holds, can find out from the module and the signature without reading every function.

## Quality gates

- Every plan answers the three rules in its Constitution Check (`.specify/templates/plan-template.md`); a violation is justified in its Complexity Tracking or fixed.
- `test_type_hints.py` and `test_documentation.py` pass before a feature is finished; so do the whole backend suite and, for a change that could move a picture,
  `specs/041-code-readability-docs/tools/verify_frames.py` against a baseline made before the change.
- A change that adds or changes a function, an array or the steps of a module leaves its documentation true: the reviewer compares it with the two tools above.

## Governance

This constitution holds only the principles above; it does not record the project's other working habits. It supersedes other practice where they differ. An amendment edits this
file, changes the version (a new or removed principle is a major or minor change, a clarification of wording a patch) and the date of the last amendment, and, if a rule is
added or removed, the Constitution Check of the plan template and the checks in `backend/tests` in the same piece of work.

**Version**: 1.0.0 | **Ratified**: 2026-11-15 | **Last Amended**: 2026-11-15
