# Research: Code Readability Documentation

No `NEEDS CLARIFICATION` remains (the one question, documentation only or also restructuring, was answered: documentation and types only). The questions below are about how to do it so that it lasts.

## D1. How an array is typed

**Decision**: Annotate arrays with **named aliases** defined once in a new module, `backend/app/services/array_types.py`, each built on `numpy.typing.NDArray` with the right element kind, for example `NoteStrengths = npt.NDArray[np.float64]`. Beside each alias, in the same module, one comment block gives the **canonical description**: what the numbers are (quantity, unit or range), the usual shape with the meaning of each axis, and where they are produced. Signatures then say `values: NoteStrengths`, and a reader who forgets what that is searches the name and lands on the one description (FR-004). The module imports only NumPy, so it cannot create an import cycle, and annotations stay evaluated at import as now.

**Rationale**: The type of an array carries neither meaning nor shape. A *named* alias is the only way to put the meaning in the signature itself, and one description per kind is what stops 144 docstrings from describing the same array in 144 ways. It adds names only: no function is renamed, moved or changed.

**Alternatives considered**: Plain `np.ndarray` everywhere (cheap, but the signature then says nothing and every docstring would have to repeat the meaning); `NDArray[np.float64]` spelled out in each signature (says the element kind, still not the meaning); a shape-checking library such as `jaxtyping` or `nptyping` (names the axes in the type, but adds a dependency and a runtime check or a type checker that the project does not use; the user asked for documentation); `Annotated[...]` with the shape as metadata (nothing reads it).

## D2. How an array is documented in a docstring

**Decision**: Each function that takes or returns an array has, in its docstring, one **line per array** in the form given in [contracts/documentation-standard.md](contracts/documentation-standard.md): the parameter name, the alias, the **concrete shape for this function** written with named axes (`(frames, 88)`), and a sentence on what it represents (quantity, unit or range, and what each axis indexes); the same for the returned value. A shape that depends on a setting lists each case. Data classes with array fields get the same lines in an "Attributes" block; module-level tables get a comment with the same two things.

**Rationale**: It is what the user asked for (meaning and shape), it can be written in the existing docstring style (the project's docstrings are prose with double-backtick names), and a fixed form makes a presence check possible (the array's parameter name must appear in the docstring).

**Alternatives considered**: NumPy-style `Parameters`/`Returns` sections for everything (a different style from the 250 docstrings that already exist; changing them all is restructuring of the text); only the alias in the signature (no concrete shape); shape comments next to each use in the body (the user wants it where the function is called from, not inside).

## D3. The order of operations of a module

**Decision**: Every module under `backend/app/services` that transforms data starts its module docstring with an **"Order of operations"** numbered list in the form of the standard: each item names the step, the function that does it, and what the data is after it (alias, shape, meaning). A module that only holds constants, settings or routing says so in one line (**"No data processing: ..."**). Existing good descriptions (the newer image types already describe their layers or their steps) are **moved into the common form, not rewritten**.

**Rationale**: It is the user's main complaint (following a type through the code is cumbersome because each visit starts from nothing). A fixed heading is also what the presence check looks for.

**Alternatives considered**: A separate architecture document (it drifts from the code and is not seen when a module is opened, the user said they "will forget"); comments in the body only (not visible from outside the module).

## D4. The overview of the eight image types

**Decision**: One overview in the module docstring of `image_types.py` (it already describes each type in prose and "knows nothing about the note analysis", so it becomes the one map). It has (a) a **vocabulary of shared steps**, in the order of a job, named once: read the file, analyze the notes into 88 note strengths per window, apply the noise floor, measure the local peaks (beat, tempo, or the energy of the frames), average the windows into frames, smooth the frames, draw (per type), save the frames; and (b) **one row for each type**: which shared steps it uses (for example the beat is measured for Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe and Contour's beat wave; the peaks and the tempo finder for Rhythm Circles; the energy of the frames for Energy Graphs), then the type's own stages in order with module and function names. Each step names the data after it as an alias with its shape.

**Rationale**: The shared pipeline of a job (in `routers/jobs.py` and `frame_rendering.write_frames`) is the same for all types up to the drawing, so naming the steps once lets two types be compared in a glance, which is what the user cannot do now.

**Alternatives considered**: A section in every type's module only (no way to compare types, and the shared steps would be described eight times); a README section (separate from the code).

## D5. The automated checks

**Decision**: Two new tests, both built on the standard library `ast`, run over every `.py` file of `backend/app`:

- `test_type_hints.py` (FR-001, FR-009, SC-001, SC-007): fails for any function or method, **nested ones included**, with a parameter (except `self` and `cls`) or a return value that has no annotation. No exemptions; `-> None` is required where nothing is returned.
- `test_documentation.py` (a presence check; what a program can tell): (1) every **processing module** (an explicit list in the test) has a module docstring with an "Order of operations" section, and every **exempt module** (a second explicit list) has the one-line "No data processing" statement; so a module that is added must be put in one list or the other, which the test reports; (2) every top-level function or method whose signature has an array alias or `ndarray` has a docstring that names each of its array parameters; (3) the aliases in `array_types.py` each have a description comment; (4) the overview in `image_types.py` names all 8 types of `IMAGE_TYPES`.

What a program **cannot** check (whether a description is true, whether the order is the real order) is left to review and to two tools in the feature folder (D6, D7).

**Rationale**: The type check is objective and cheap; the presence checks catch the common failure (a new module or function with nothing) without pretending to judge the content. Nested helper functions are exempt from the array-documentation check only (they inherit the meaning of the enclosing function), never from the type check.

**Alternatives considered**: `mypy` or `pyright` in strict mode (checks types more deeply but adds a tool, will report many findings in numeric code that have nothing to do with readability, and would make this feature a type-correctness project); a pre-commit hook (the project has none); checking the content of docstrings with patterns (brittle, the failure mode would be docstrings written to satisfy the pattern).

## D6. Writing the shapes from facts, not from memory

**Decision**: While documenting, use a throwaway **shape probe** to read the real shapes and element kinds: run one job for each image type under `sys.setprofile`, and record, for each function of `backend/app`, the shape and dtype of every array argument and the returned value. The documents are written from that table (and from reading the code for meaning, ranges and units), so a shape in a docstring is one that was seen. The probe stays in the feature folder (`tools/shape_probe.py`) so a reviewer can run it again.

**Rationale**: The array documentation is the largest and most error-prone part (about 144 functions). A wrong shape is worse than none. The probe turns "what shape does this have" from an opinion into an observation for every function that a job reaches; the rest are small and read directly.

**Alternatives considered**: Reading the code only (slow and it is how wrong shapes get written); adding runtime asserts (changes behaviour, forbidden here).

## D7. Proving that nothing moved, and that the overview is true

**Decision**: Two tools in `specs/041-code-readability-docs/tools/`, both run **before the first edit** for the baseline and **after the last** for the comparison:

1. `verify_frames.py` makes a short fixed input (generated in the script with a seeded generator: a few seconds of tones with clicks, stereo, 44.1 kHz), runs one job through the application for **each of the 8 image types with the default settings** (and Contour once more with Beat coloring on), and writes the **SHA-256 of every frame** to `baseline-frames.json` (or compares with it). Identical hashes are FR-007 and SC-005.
2. `trace_pipeline.py` runs one job for each type under `sys.setprofile` and prints the **order in which the functions of `backend/app/services` are first called**. That is an independent oracle for the overview and for each module's order of operations (SC-003, SC-004): a reviewer compares the printed order with the written list.

The existing tests (4719 backend, 871 frontend) are the second proof of no behaviour change; the frame hashes are the first, because they include the drawing.

**Rationale**: Annotations and docstrings cannot change a result unless an edit slips (a stray character in code, an alias that does not exist at import). Hashing the pictures before and after catches any such slip in the drawing paths that the tests cover only indirectly.

**Alternatives considered**: Relying on the test suite alone (it is strong but several drawing tests compare to oracles with tolerances, not bytes); committing the hashes as a test (they depend on the Pillow and matplotlib versions of the machine, so the test would fail on a version bump without anything being wrong: keep it a tool).

## D8. The groups of modules (the order of work)

**Decision**: The work goes in groups, each ending with the scan and the tests green for the files it touched, so a mistake is found near where it was made:

| Group | Modules | Why together |
|---|---|---|
| A. Foundation | `array_types.py`, `colormaps`, `image_processing`, `note_grid`, `note_layout`, `note_selection`, `window_spacing`, `resolution`, `gaussian`, `frame_interpolation`, `frame_saving`, `noise_floor` | The small shared pieces whose arrays the others reuse |
| B. Analysis and measurement | `note_analysis`, `chords`, `local_peaks`, `tempo_finder` | The first stages of every job; they define `NoteStrengths`, `Samples`, the peaks and the tempo |
| C. Frame handling | `frame_rendering`, `contour`, `beat_wave` | The shared averaging and smoothing and the first image type |
| D. Image types | `decay`, `decay_exp`, `polar_chords`, `energy_graphs`, `chromatic_decay`, `chromatic_wireframe`, `rhythm_circles` | The newest and least annotated modules (about 100 of the 135 gaps) |
| E. The edge | `routers/jobs.py`, `routers/video.py`, `routers/images.py`, `routers/hello.py`, `services/video.py`, `main`, `config`, `image_types` (the overview) | Request handling, video, and the overview that ties the groups together |

**Rationale**: Group A first because the aliases and their descriptions are needed by all the others; D is where most of the missing types are; E last because the overview needs the other groups' wording.

## D9. The constitution and the templates

**Decision**: Fill `.specify/memory/constitution.md` with **three principles** (I. Every function is typed; II. Every array is documented with its meaning and shape, one description per kind; III. Every processing module states its order of operations, and the image types have one overview), each with how it is checked (the scan, the presence check, review), plus a governance section (how the principles change; they are reviewed in every plan; version 1.0.0, ratified 2026-11-15). Unused template sections are removed, not filled with invented rules. Update the Constitution Check of `.specify/templates/plan-template.md` to list the three rules, so each plan has to answer them (SC-006). The constitution command (`/speckit-constitution`) may be used to write it, or the file edited directly with the same content.

**Rationale**: The user asked for exactly these rules in the constitution; inventing others would speak for them.

**Alternatives considered**: Also recording the project's working habits (tests first, README per feature) in the constitution: they are real but were not asked for, and the user can add them with the constitution command.


## Spot check (SC-002, task T020, 2026-11-15)

A seeded draw (`random.seed(41)`) of 20 functions among those that take or return an array and that a job reaches, compared with what `tools/shape_probe.py` saw:
`energy_graphs._background`, `decay.ring_positions`, `colormaps.lookup_table`, `chromatic_wireframe._frame`, `rhythm_circles.ring_colors_rows`,
`rhythm_circles.write_rhythm_frames`, `energy_graphs._check_data`, `local_peaks._window_peaks`, `rhythm_circles.rhythm_angles`, `note_analysis.window_starts`,
`decay.circle_points`, `local_peaks._times`, `decay._spread`, `rhythm_circles._series`, `note_selection._check_values`, `polar_chords._frame`, `chords._greater`,
`polar_chords._targets`, `contour.write_contour_frames`, `note_analysis.note_frequencies`.

**Result:** for 19 of the 20 the documented shape, element kind and meaning agree with the probe. **One mistake was found, and it was in the text that was there before this
feature:** the docstring of `chromatic_wireframe._frame` said `heights` is `(frames, 12 x n)`, while the probe saw `(60, 1161)`, that is `(frames, n)`; the new `Arrays:` line of
the same function already said `(frames, n)`, and the old sentence was corrected. That is the kind of error the probe is for.

## For later (what the documentation showed about the structure; nothing was changed, spec FR-010)

- `rhythm_circles` and the other drawing modules each repeat the same pattern (check, geometry once, one function for a frame, write with a few threads); a common helper could
  hold it, which would be a structural change.
- `frame_rendering.write_frames` has 19 parameters and one long `if image_type == ...` chain; one entry point for each image type would make the pipeline overview shorter.
- The analysis windows are called `frames` in `AnalysisResult` (`result.frames`) although they are windows, not the frames of the animation; the documentation says so, a rename was
  out of scope.
- `local_peaks.LocalPeaks` caches five arrays that are only used by its methods; `contour.py` and `directionalSmoothing` use another indentation (two spaces) than the rest.
