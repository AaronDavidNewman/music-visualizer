# Contract: the automated checks

Two test files under `backend/tests/`, standard library `ast` only, over every `*.py` file of `backend/app` (not `__pycache__`). They parse the files; they never import or run them, so they are fast (under a second for the 36 files) and cannot be broken by the application's own imports.

## `test_type_hints.py` (FR-001, FR-009, SC-001, SC-007)

For every `FunctionDef` and `AsyncFunctionDef` in each file, **nested ones and methods included**:

| Check | Failure message names |
|---|---|
| Every parameter (positional-only, positional, keyword-only, `*args`, `**kwargs`) except `self` and `cls` has an annotation | file, line, function, the parameters without one |
| The return value has an annotation (`-> None` counts) | file, line, function |

- **No exemptions**: no allow-list. A new function without types fails.
- Lambdas are not functions of this check (they cannot be annotated).
- The test reports **all** failures at once (a list), not just the first, so a developer can fix them in one pass.
- Also asserts that the scan itself sees the expected population (more than 200 functions in more than 25 modules), so a broken path cannot make it pass by scanning nothing.

## `test_documentation.py` (presence; SC-003, SC-006's lists, the overview)

1. **Module lists**: two explicit sets in the test, `PROCESSING_MODULES` and `EXEMPT_MODULES`. Every module file that has at least one function or class must be in exactly one of them (a new module fails until it is placed); a name in a set that has no file also fails.
   - A processing module's module docstring contains a line `Order of operations:` followed by a numbered item `1.`.
   - An exempt module's module docstring contains the text `No data processing:`.
2. **Arrays named**: for every top-level function and method (not nested) whose annotations include an alias from `array_types.py` or `np.ndarray` (as a parameter or in the return), the docstring exists and mentions each **array parameter** by name (double-backticked, ``` ``name`` ```); if the return is an array, it contains a `Returns:` line.
3. **Aliases described**: each alias defined in `array_types.py` is immediately preceded or followed by a comment (a description is required), and each alias that is **used** in an annotation somewhere is defined there.
4. **Overview complete**: the `image_types.py` module docstring contains `Pipeline overview:` and every name in `IMAGE_TYPES`, and each shared step name (READ, ANALYZE, FLOOR, MEASURE, AVERAGE, DRAW, SAVE).

## What the checks do not do (left to review and the feature's tools)

- Whether a description of an array is **true** or a shape is **right**.
- Whether the listed order of operations is **the real order**.
- Whether wording is **consistent** between functions (FR-004), beyond requiring one alias per kind.

These are reviewed against the output of `tools/shape_probe.py` and `tools/trace_pipeline.py` (research D6, D7), and the constitution says that a change to arrays or steps changes their documentation in the same piece of work.

## Failure messages

Each message says what is missing and where, in the words of the standard, for example:

```text
backend/app/services/rhythm_circles.py:122 circle_speeds: parameter(s) without a type: moments
backend/app/services/decay.py: module docstring has no "Order of operations:" list (documentation-standard.md section 3)
backend/app/services/tempo_finder.py:61 find_tempo: array parameter ``times`` is not named in the docstring (documentation-standard.md section 2)
```
