# Contract: the documentation standard

This is the form of the three kinds of documentation. It is what the constitution will require, what the presence check looks for, and what a reviewer compares a change with. Examples use names from the real code.

## 1. Types on every function

Every `def` in `backend/app` (functions, methods, nested functions; not lambdas) annotates **every parameter** except `self` and `cls`, and **the return value** (`-> None` when nothing is returned). Rules:

- Use the narrowest honest type. A value that can be a number or a list of numbers is `float | Sequence[float]`, not `Any`; if no honest narrow type exists, use the widest honest one and say in the docstring what it is in practice.
- An array is annotated with **a named alias** from `array_types.py` (for example `NoteStrengths`), never a bare `np.ndarray` when an alias for its kind exists; a group of arrays is a `tuple[...]` of aliases. A kind with no alias yet gets one (with its description) before it is used.
- No behaviour changes: an annotation is never changed into a conversion or a check.

```python
def average_frames(result: AnalysisResult, frame_rate: float, frames: int) -> NoteStrengths:
```

## 2. Arrays: meaning and shape

Every function that takes or returns an array (directly, in a tuple, or in a field of a returned object) says, in its docstring, for **each array**: the **name**, the **alias**, the **concrete shape** with named axes, and **what it represents** (the quantity, its unit or range, and what each axis indexes). A shape that depends on a setting lists each case. The arrays are listed in a block headed `Arrays:` after the description; the returned array(s) on a line starting `Returns:`.

```text
Arrays:
    ``windows``: ``NoteStrengths`` ``(windows, 88)`` - the strength of each of the 88 notes in each analysis window (0 or more); axis 0 is the window in time order, axis 1 the note from 55 Hz upward by semitones.
Returns:
    ``NoteStrengths`` ``(frames, 88)`` - the same strengths averaged into one row per frame; never negative.
```

- **Names**: the same words for the same kind of array everywhere (the description of the kind lives in `array_types.py`; the docstring may shorten it but must not contradict it).
- **Pass-through**: a function that only passes an array on still names it and its alias and shape (one line is enough).
- **Several cases**: `shape ``(frames, 84)`` for 84 notes, ``(frames, k)`` when ``note_count`` is k`.
- **Data classes** (a class with array fields): an `Attributes:` block in the class docstring with the same line per array field.
- **Module-level tables** (arrays defined as constants): a comment on the line above with the same two things.
- **Nested helper functions** inherit the meaning from the enclosing function and may refer to it ("the same ``values`` as above").

## 3. Order of operations (module docstring)

The module docstring of every module that **transforms data** starts, after its first sentence, with a numbered list headed `Order of operations:`:

```text
Order of operations:
    1. <step> - ``function()`` - <the data after it: alias, shape, meaning>
    2. ...
```

- The steps are in the order in which they are applied **when a job runs**, not the order in which the functions are defined in the file.
- The order is the order in which **the data is transformed**. A step that is done by a helper which the function of another step calls (so that the helper is not the first call of a job) says so: ``(called by ``other()``)``. The check of a list against ``tools/trace_pipeline.py`` is by that rule: only an inversion that is not a call from one step into another is a mistake.
- Each step names the function that does it and what the data is after it (alias and shape), so a reader can follow the data without opening the functions.
- A step that is optional or that depends on a setting says on which.
- A step that happens in another module says which (`-> see ``local_peaks``).
- A module whose order was already described (the newer image types) keeps its wording, moved into this form.

A module that only holds constants, settings, routing or a single pure check says instead, as the first line after the summary:

```text
No data processing: <what it holds, in a sentence>.
```

## 4. The overview of the image types (`image_types.py`)

The module docstring of `image_types.py` contains, under the heading `Pipeline overview:`:

1. **The shared steps** in job order, each named once with its function and the data after it (alias, shape), with the vocabulary of [data-model.md](../data-model.md): READ, ANALYZE, FLOOR, MEASURE, AVERAGE, DRAW, SAVE.
2. **One block per image type** (all of `IMAGE_TYPES`), in the order of `IMAGE_TYPES`: which shared steps it uses and which it skips (and why in a few words), then **its own DRAW stages in order**, each with the module and function and the data after it.
3. A rule at the end: **when an image type is added or changed, its block is changed in the same piece of work**.

## 5. Line width of comments

Comments and docstrings in `backend/app` are wrapped so that no line is longer than **120 columns**, so that a long
comment reads as a block of even rows. A continuation line of a numbered item, a bullet or a labelled line
(`Shape:`, `Meaning:`, `Made by:`) is indented under its text. Code lines are not reformatted by this rule. There is
no test for it yet.

## 6. Keeping it true

- The types: the scan (`test_type_hints.py`) fails when one is missing.
- The presence of the other two kinds: `test_documentation.py` (see [checks.md](checks.md)).
- The truth of a shape: the shape probe of the feature folder prints the real shapes of a job; a reviewer compares.
- The truth of an order: the pipeline trace prints the real order of the calls of a job for each type; a reviewer compares.
- A change to a function's arrays or a module's steps changes its documentation in the same piece of work (the constitution says so).
