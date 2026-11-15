# Feature Specification: Code Readability Documentation

**Feature Branch**: `041-code-readability-docs`

**Created**: 2026-11-15

**Status**: Draft

**Input**: User description: "I'd like to take a moment and refactor the code to make it more readable by humans. We should have type hints in all the python functions. We started having them, but the more recent modules don't have them. Also, for functions that take ndarrays, we should document 1) what the data represents, e.g. is it pitch amplitudes, indices into something, energy levels, etc. and 2) what the expected shape is. Also for each module, especially the ones containing processing for image types, we should know what the order of operations is, which transformations to the data are done in which order. It is pretty cumbersome to follow the logic over all the different types, for a person, because we will forget what the types are and have to revisit all the functions to remember it. Having this type of documentation should be made part of the speckit constitution."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every function says what it takes and gives (Priority: P1)

A maintainer opens any function of the backend and can see, from its signature alone, what kind of value each parameter is and what the function returns. Today this is true for the older modules and false for most of the newer ones (a scan of the backend finds 135 of its 255 functions with a parameter or a return value that has no type).

**Why this priority**: It is the cheapest and most objective part of the request, it can be checked by a program, and the other two stories build on it (an array's meaning and shape are documented next to its type).

**Independent Test**: Run a scan over the backend code that lists every function with a parameter or a return value that has no type; the list is empty.

**Acceptance Scenarios**:

1. **Given** any function in the backend application code, **When** a maintainer reads its signature, **Then** every parameter (except the instance or class parameter of a method) and the return value have a type.
2. **Given** the functions that take or return arrays, **When** a maintainer reads their signatures, **Then** the type says that it is an array (and, where a function has a more specific kind of number, which one).
3. **Given** the whole backend after the change, **When** the existing tests are run, **Then** they all pass without change to what they check, and the pictures made from a fixed set of files are identical to those made before.

---

### User Story 2 - Every array says what it means and what shape it has (Priority: P1)

A maintainer reading a function that takes or returns an array finds, in its documentation, **what the numbers represent** (for example: the strength of each of the 88 piano notes in each window, indices into the list of notes, the energy of each 32-sample impulse window, the angle of each circle in turns, the position of each frame in the beat from 0 to 1) and **the shape it must have** (for example: `(frames, 88)`, with the meaning of each axis). Nobody has to read the body of the function, or of its callers, to find out.

**Why this priority**: This is what the user says costs the time: forgetting what a number stands for, and revisiting every function to remember it.

**Independent Test**: Pick 20 functions at random among those that take or return an array; for each, a reader who has not seen the code can state from the documentation alone what each array holds, in what unit or range, and its shape with the meaning of its axes.

**Acceptance Scenarios**:

1. **Given** a function that takes an array, **When** its documentation is read, **Then** it states what the data represents (the quantity, its unit or range, and what indexes each axis) and the expected shape.
2. **Given** a function that returns an array or a group of arrays, **When** its documentation is read, **Then** it states the same two things for what it returns.
3. **Given** an array with the same meaning in several functions (for example the 88-note strengths of every frame), **When** the documentation of those functions is read, **Then** they describe it the same way (same words for the same thing).
4. **Given** a function whose array can have several shapes depending on a setting (for example the number of notes drawn), **When** its documentation is read, **Then** each case is stated.

---

### User Story 3 - Every processing module says its order of operations (Priority: P1)

A maintainer opens a module that processes data, especially one that makes the picture of an image type, and finds at the top an **ordered list of what happens to the data**: which transformation comes first, which next, what the data represents and what shape it has after each step, and which module or function does each step. There is also **one overview of the eight image types** that lists, for each type, the modules and steps from the uploaded file to the saved picture, so that following one type through the code, or comparing two types, does not mean opening every module.

**Why this priority**: The user's main complaint is that following the logic across the types is cumbersome and that the types are forgotten between visits. This is the answer to it.

**Independent Test**: For each of the eight image types, a reviewer, using only the overview and the top of each module it points to, writes down the steps from file to picture in order; the list matches what the code does when checked by running it (for example by stepping through the job for that type).

**Acceptance Scenarios**:

1. **Given** a module that processes data, **When** its first documentation is read, **Then** it lists the transformations in the order in which they are applied, with the meaning and shape of the data after each.
2. **Given** an image type, **When** the overview is read, **Then** it lists, in order, the steps from the uploaded file to the saved frames: the analysis, the settings that change the data, the beat or tempo measurement if the type uses it, the smoothing, the drawing.
3. **Given** two image types that share a step (for example the smoothing of the note values, or the measurement of the local peaks), **When** both are read, **Then** the shared step is named the same way and points to the same place.
4. **Given** a module whose order of operations changes (a new setting, a new step), **When** the change is made, **Then** the list at the top of the module is changed in the same piece of work (see story 4).

---

### User Story 4 - The project constitution requires it for all future work (Priority: P2)

The project constitution states, as rules that every later feature must follow, the three kinds of documentation above: types on every function, meaning and shape of every array, and the order of operations of every processing module (plus the overview of the image types when a type is added or changed). A person who reads the constitution knows what a feature must leave behind, and the plan and review of a feature check against it.

**Why this priority**: It makes the first three stories last. It is smaller than they are and depends on their wording.

**Independent Test**: Read the constitution: each of the three rules is there, with how it is checked. Take a future feature plan: its constitution check lists the three rules.

**Acceptance Scenarios**:

1. **Given** the constitution, **When** it is read, **Then** it has the three rules, each stated so that a reviewer can tell whether a change follows it.
2. **Given** a new feature that adds or changes a function, **When** it is reviewed, **Then** the review can tick or fail each of the rules by looking at the changed code and the scan of story 1.
3. **Given** a change that adds a function without types, **When** the automated scan is run, **Then** it reports that function.

---

### Edge Cases

- A function that takes an array only to pass it on unchanged: it still states what the array is and its shape (a short reference to where the meaning is defined is enough).
- Arrays inside a data class or a returned group of arrays (for example the local peaks of a file, or the angles of the circles): each field is documented, not only the class.
- A function that works for several shapes (a single number or a list of numbers, one row or many): the documentation lists them.
- Very small helpers (a one-line check or a conversion): they get types, and the array documentation if they take an array, but not a long description.
- Module-level constants that are arrays or tables (colormaps, tile edges): the meaning and shape are documented where they are defined.
- Dynamically typed places that no type can describe well (a value that can be a number or an array, or a function passed to another): the type is the widest honest one and the documentation says what it is in practice.
- Generated or third-party code: none is in the backend; only the project's own code is covered.
- The tests: they are not changed by this feature, except where a test reads a text that this feature rewrites (a docstring).
- A step of a pipeline that is shared by all types (the note analysis) but whose order is already documented in its own module: the overview points to it and does not repeat it.
- The documentation must not become wrong: the order of operations is checked against the code, and the scan keeps types from being forgotten, but the meaning of an array is a human statement, so it is also covered by review (story 4).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every function and method in the backend application code MUST have a type for every parameter (except the instance or class parameter) and for its return value. A scan of the code MUST list none that lack one.
- **FR-002**: Every function that takes or returns an array (directly, in a group, or in a field of a returned object) MUST document, for each such array, (1) **what the data represents**: the quantity, its unit or range, and what each axis indexes; and (2) **its shape**, with the meaning of each axis and the cases when the shape depends on a setting.
- **FR-003**: Arrays and tables that are defined at module level, and the fields of data classes that hold arrays, MUST be documented with the same two things where they are defined.
- **FR-004**: The same kind of data MUST be described in the same words everywhere it appears (one description per kind of array, referred to from the other places), so that a reader can search for a phrase and find all the places.
- **FR-005**: Every module under the backend services that transforms data MUST start with an **ordered list of its transformations**: the order in which they are applied, the meaning and shape of the data after each, and which function does each. A module that only holds constants, settings or routing is exempt, but MUST say so in one line.
- **FR-006**: There MUST be **one overview of the eight image types** that lists, for each type, in order, the steps and modules from the uploaded file to the saved frames, naming the shared steps in the same way for every type and marking which type uses which step (the beat or tempo measurement, the smoothing, the threshold, the grid, and so on). It MUST be kept next to the code (not in a separate place that can be forgotten) and MUST say, for each step, what the data is and its shape.
- **FR-007**: The change MUST NOT alter behaviour: all existing tests MUST pass, and the frames made from a fixed set of files with each image type and the default settings MUST be byte-identical before and after.
- **FR-008**: The constitution MUST state the rules of FR-001, FR-002 and FR-005 (and the upkeep of the overview of FR-006) as requirements that every later feature MUST meet, with how each is checked.
- **FR-009**: The check for FR-001 MUST be repeatable by one command (an automated scan that is also part of the tests), so that a function added later without types fails it.
- **FR-010**: This feature MUST add types and documentation **only** (answered by the user on 2026-11-15: "types and documentation only right now"): no function, class or module is renamed, moved, split or merged, and no code is restructured. Where the documentation shows that a structure is awkward to follow, that is noted for a later feature, not fixed here. (Structural refactoring of the image-type pipelines is out of scope.)

### Key Entities *(include if feature involves data)*

- **Array description**: For one kind of array, what it represents (quantity, unit or range) and its shape with the meaning of each axis; one description per kind, referred to wherever the array appears.
- **Order of operations**: For one module, the ordered list of transformations, with the data's meaning and shape after each and the function that does it.
- **Image-type overview**: For each of the eight image types, the ordered list of steps and modules from the uploaded file to the saved frames, with the shared steps marked.
- **Constitution rule**: A requirement every feature must meet, with how a reviewer or a program checks it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The scan of the backend code finds 0 functions with a parameter or a return value that has no type (from 135 of 255 today).
- **SC-002**: For 100% of the functions that take or return an array, the documentation states what the data represents and its shape; a spot check of 20 functions chosen at random passes for all 20 (a reader who has not seen the code can state both from the documentation alone).
- **SC-003**: 100% of the data-processing modules start with an ordered list of their transformations (the modules without data processing say so in one line).
- **SC-004**: For each of the 8 image types, a reviewer can list the steps from file to picture, in order, from the overview alone, and the list matches the code when checked by running one job of that type.
- **SC-005**: The existing tests all pass, and the frames of each of the 8 image types for the same input files are byte-identical before and after the change.
- **SC-006**: The constitution contains the three rules and how each is checked; the plan template's constitution check names them.
- **SC-007**: A change that adds a function without types fails the automated scan in under one minute.

## Assumptions

- **Scope of "all the python functions"**: the backend application code under `backend/app` (36 modules: services, routers and the application entry points). The test code is not included, and the frontend, which is TypeScript and already type-checked, is not either.
- **What counts as a type for an array**: that the value is a NumPy array (and its element kind where one kind is meant); the shape and meaning are in the documentation, because the type of an array does not carry them.
- **Where the documentation lives**: in the docstrings next to the code (function, class and module level), not in a separate manual, so that it is changed together with the code. The overview of the image types is in the module that already describes them.
- **Wording of shapes**: a shape is written with named axes, for example `(frames, 88)`, and each axis name is explained once.
- **Existing documentation is kept**: where a module already has a good description of its order of operations (the newer image types have one), it is brought to the common form and not rewritten from scratch.
- **The constitution** is today an unfilled template. This feature fills in only what the user asked for (the documentation rules and how they are changed), and does not invent other principles; the user can add more with the constitution command later.
- **Automated check**: the scan for missing types is part of the test suite (it is cheap and objective). The meaning and shape of arrays and the order of operations are checked by review, and the constitution says so, because a program cannot tell whether a description is right.
- **No behaviour change**: this feature changes no result, setting, request, response or picture, and no code structure; it changes only types (annotations) and documentation (docstrings and comments), plus the automated scan, the constitution and the overview. A later feature may restructure the code, using the documentation written here.
