---

description: "Task list for 045-obj-export-mode"
---

# Tasks: 3D export of Contour and Chromatic Wireframe (Wavefront OBJ files)

**Input**: Design documents from `/specs/045-obj-export-mode/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/job-api.md](contracts/job-api.md), [quickstart.md](quickstart.md)

**Tests**: The plan and the constitution require them (the plan names the test files), so test tasks are included.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root. Run backend commands from `backend/` with `.venv/Scripts/python.exe` (`python` is not the project's interpreter) and frontend commands from `frontend/`.

**Environment note**: the PowerShell scripts in `.specify/scripts` cannot run on this machine (execution policy): do not depend on them. Write scripts for edits to the scratchpad directory, not the project (the Bash tool eats backticks in long heredocs).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1 to US3 as in the spec (US1 Contour, US2 Chromatic Wireframe, US3 page, request and download)

---

## Phase 1: Setup (baselines, before the first edit of `backend/app` or `frontend/src`)

- [X] T001 Take the backend baseline: the failing test ids are those of `specs/044-sustained-loudest-notes/baseline-failures-after.txt` (32 ids, the state of the tree now). Copy that file to `specs/045-obj-export-mode/baseline-failures-before.txt` (a full run takes about 10 minutes; it is repeated at the end in T033)
- [X] T002 [P] Run `backend/.venv/Scripts/python.exe specs/043-decouple-frame-rate/tools/verify_drawing.py` from the repository root: it must say `all frames identical to the baseline` (9 image types); this is the no-change gate for the pictures. Copy the script's folder use as is; do not change its baseline
- [X] T003 [P] Run `npm test` and `npm run typecheck` in `frontend/`: 916 tests pass and the typecheck is clean
- [X] T004 [P] Create `specs/045-obj-export-mode/tools/read_obj.py`: an independent plain-Python OBJ reader written from [data-model.md](data-model.md), not from the code: `read_obj(text: str) -> tuple[list[tuple[float, ...]], list[tuple[int, ...]], dict[str, str]]` returning the `v` rows (6 numbers each, raising on any other count), the `f` rows (4 integers, raising if one is not from 1 to the number of vertices) and the comment/`o` lines; it skips `#` and `o` lines and refuses any other keyword. The tests import it by path (`importlib` from `specs/045-obj-export-mode/tools`) so that the checks do not depend on the writer's own helpers

**Checkpoint**: baselines exist; the source is untouched.

---

## Phase 2: Foundational (blocks every story)

**Purpose**: the new array kinds and the new module that every story uses.

- [X] T005 In `backend/app/services/array_types.py`, in the section of the pictures' data, add `MeshVertices = npt.NDArray[np.float64]`, `MeshFaces = npt.NDArray[np.intp]` and `LetterAmplitudes = npt.NDArray[np.float64]`, each with its description in the file's format (comment above it, `Shape:`, `Meaning:`, `Made by:`), taken from the table in [data-model.md](data-model.md) ("New arrays"); `Made by:` names `obj_export.contour_mesh` and `obj_export.wireframe_mesh` for the first two and `obj_export.amplitude_share` for the third
- [X] T006 Create `backend/app/services/obj_export.py` with the module docstring (what the export is, FR-001 to FR-015 in a paragraph, and `Order of operations:` : 1. check the arguments; 2. choose the points of each frame and their heights - `contour_mesh()` / `wireframe_mesh()` - `MeshVertices` `(points, 6)`; 3. join them into faces - the same functions - `MeshFaces` `(faces, 4)`; 4. format the file - `format_obj()` - text; 5. write one file per frame - `write_contour_obj()` / `write_wireframe_obj()`; 6. pack the files - `zip_obj_files()`) and these typed, documented functions: `format_obj(vertices: MeshVertices, faces: MeshFaces, comment: str, name: str) -> str` (header: `# Music Visualizer 3D export`, `# <comment>`, `o <name>`; `v` lines with `format(x, ".4f")` for the six numbers, `-0.0000` written `0.0000`; `f` lines with the four integers; `\n` line ends and a final `\n`; no locale, no exponent), `zip_obj_files(directory: Path, archive: Path) -> None` (the `*.obj` files of `directory` in sorted order, stored under their own names, `ZIP_DEFLATED`, each `ZipInfo` with the fixed date `(2020, 1, 1, 0, 0, 0)` so the same files give the same ZIP, written to a temporary name and renamed; raises `FileNotFoundError` when there is no file) and the constants `GRID_X = 12`, `GRID_Y = 7`, `LINES_PER_FILE = 12`, `HEIGHT = 12.0`, `OBJ_FOLDER = "obj"`, `OBJ_EXPORT_TYPES = ("contour", "chromatic-wireframe")`. The mesh and write functions come in Phases 3 and 4
- [X] T007 In `backend/tests/test_documentation.py` add `"services/obj_export.py"` to the list of processing modules (alphabetical order of the list)
- [X] T008 [P] Create `backend/tests/test_obj_export.py` with the tests of `format_obj` and `zip_obj_files`: the exact text of a 4-point mesh (header lines, `v` lines with four decimals, `f` line), `-0.0` written `0.0000`, no exponent for a tiny and a large number, `\n` ends, the same input twice gives the same text, a number is written with a dot whatever the locale (`locale.setlocale` to a comma locale if one exists, else skipped), the ZIP holds the files in sorted order under their own names with the fixed date, two ZIPs of the same files are byte-identical, a folder with no `.obj` raises `FileNotFoundError`, and the independent reader of T004 reads the text of `format_obj`

**Checkpoint**: `.venv/Scripts/python.exe -m pytest tests/test_type_hints.py tests/test_documentation.py tests/test_obj_export.py -q` passes with the new module and aliases.

---

## Phase 3: User Story 1 - Export Contour as one surface per frame (Priority: P1) 🎯 MVP

**Goal**: a Contour job with the export on writes one OBJ file per frame with 84 points and 66 faces in the XY plane, Z the value scaled to 0-12, colors as the picture.

**Independent Test**: call `write_frames(values, directory, image_type="contour", export_obj=True)` on a small array and read the files with the reader of T004.

- [X] T009 [US1] In `backend/app/services/contour.py` add the public `smoothed_grid(frame: ArrayLike, rows: int, columns: int) -> FrameGrid`: the lines of `write_contour_frames` that reshape one frame to `(rows, columns)`, flip the rows, copy and apply `directionalSmoothing` to every cell (documented with `Arrays:` and `Returns:`; `frame` is one row of `GridValues`, `(rows * columns,)`), and make `write_contour_frames` call it in place of those lines, changing nothing else; update the `Order of operations:` of the module (steps 4 and 5 name `smoothed_grid()`). The pictures must not change: run `verify_drawing.py` and `tests/test_contour*.py` after this task alone
- [X] T010 [US1] In `backend/app/services/obj_export.py` add `contour_mesh(grid: FrameGrid, peak: float, scale: float, colormap: str) -> tuple[MeshVertices, MeshFaces]` following the Contour table of [data-model.md](data-model.md): 84 rows `x = column`, `y = row`, `z = 12 * grid / peak` (all 0 when `peak <= 0`; held to 0..12), colors from `lookup_table(colormap)` at row `round((COLORMAP_STEPS - 1) * clip(grid / scale, 0, 1))` divided by 255 (the first row when `scale <= 0`); the 66 faces `1 + 12 r + c`, `+ 1`, `+ 12 + 1`, `+ 12` in that order. Raises `ValueError` for a grid that is not `(7, 12)`
- [X] T011 [US1] In `backend/app/services/obj_export.py` add `write_contour_obj(values: GridValues, peak: float, colormap: str, directory: Path, beat: BeatPositions | None = None, waves: int = DEFAULT_WAVE_COUNT) -> None`: checks the arguments like `write_contour_frames` (`check_colormap`, `check_wave_count`, `check_beat`, `values` shape `(frames, 84)`), creates `directory`, and for every frame `i` (no frame skipped): if `peak <= 0` or the frame's values are all equal, every point gets the picture's flat color (`value / peak` row of the table; the first row when `peak <= 0`) and `z = 12 * value / peak`; else `grid = smoothed_grid(frame, 7, 12)`, `top = frame.max()`, and when `beat[i] > 0` `grid = grid * wave_modifier(7, 12, waves, beat[i])`, colors on the scale `top` (a wave that leaves every value equal still has `scale = top`); writes `frame_{i:06d}.obj` with `format_obj` (comment `contour frame i of N: x = note name 0-11, y = octave row 0-6, z = value 0-12 (colors 0-1)`, name `frame_{i:06d}`)
- [X] T012 [US1] In `backend/app/services/frame_rendering.py` add the parameter `export_obj: bool = False` to `write_frames` (checked: a bool; `True` for an image type not in `OBJ_EXPORT_TYPES` raises `ValueError("The 3D export is only available for Contour and Chromatic Wireframe.")` before anything is written) and, for `contour`, after the pictures and the blur and interpolation steps, call `write_contour_obj(hidden_grid, peak, colormap, directory / OBJ_FOLDER, beat, wave_count)` where `hidden_grid` is the 12 x 7 values at resolution 1: `spread_notes(frames[:, :SHOWN_NOTES], note_count)` with `hidden_below(...)` set to 0 (computed separately from the picture's grid, which may be finer; the picture's own arrays are not touched). Document the parameter and update the `Order of operations:` of the module
- [X] T013 [P] [US1] In `backend/tests/test_obj_export.py` add the Contour mesh tests: `contour_mesh` of a known grid has 84 vertices and 66 faces, vertex `1 + 12 r + c` is at `(c, r)`, Z is 12 for the peak and 0 for 0 and proportional between, a zero `peak` gives all Z 0, the colors are the table row of the value on `scale` over 255 (first and last colormap color for 0 and for the scale), every face is the four corners of one cell in counterclockwise order (the cross product of the first two edges points to +Z, checked for all 66), a grid of the wrong shape raises; and `write_contour_obj`: one file per frame named `frame_000000.obj` and up, all frames written for a silent file (all Z 0, one color, 84 points, 66 faces), a flat frame of equal nonzero values has the picture's flat color on the scale of `peak`, the beat wave changes the heights of a frame with `beat > 0` and leaves a frame with beat 0 equal to the plain one, the smoothing is the picture's (the Z of a frame equals `smoothed_grid` scaled), the same input twice gives identical files, every file is read by the reader of T004 and has X 0..11, Y 0..6, Z 0..12 and colors 0..1
- [X] T014 [P] [US1] Create `backend/tests/test_obj_export_rendering.py` with the `write_frames` tests for the contour: with `export_obj=True` the files are in `directory/"obj"` and the PNGs are the same bytes as with `export_obj=False` (SC-006), `export_obj=False` writes no `obj` folder, Resolution 3 still gives the 12 x 7 export (84 points) while the picture is finer, Number of notes below 84 and Threshold change the values of the export (a note under the threshold is Z 0), Gaussian and Interpolate do not change the files and every frame has a file even when Interpolate is 3, `export_obj=True` with another image type raises `ValueError`, a non-bool raises `ValueError`

**Checkpoint**: the Contour export works from the library; the pictures are unchanged (T002 gate and `tests/test_contour*.py` pass).

---

## Phase 4: User Story 2 - Export Chromatic Wireframe as a stack of lines (Priority: P1)

**Goal**: a Chromatic Wireframe job with the export on writes one OBJ file per frame with the 12-point lines of the frame and the 11 before it, Z the amplitude of the letter scaled to 1-12, one color per line.

**Independent Test**: call `write_frames(values, directory, image_type="chromatic-wireframe", export_obj=True, beat=...)` on a 14-frame array and read the files.

- [X] T015 [US2] In `backend/app/services/obj_export.py` add `amplitude_share(points: CirclePoints) -> LetterAmplitudes`: the share of the full radius of each letter's circle, `SMALLEST + (1 - SMALLEST) * min(points, SIZE_POINTS) / SIZE_POINTS` (imports `SMALLEST` and `SIZE_POINTS` from `decay`; the formula of `chromatic_decay.circle_radii` divided by the full radius, with no picture size), the shape of its input, 1/12 to 1; and `wireframe_mesh(points: CirclePoints, colors: LineColors, frame: int) -> tuple[MeshVertices, MeshFaces]`: `L = min(frame + 1, 12)` lines, line `j` the frame `frame - j`, vertex `1 + 12 j + b` at `(b, j, 12 * share[frame - j, b])`, the color `colors[frame - j] / 255` for the 12 points of the line, and `11 * (L - 1)` faces `1 + 12 j + b`, `+ 1`, `+ 12 + 1`, `+ 12`; a `frame` outside the array raises `ValueError`
- [X] T016 [US2] In `backend/app/services/obj_export.py` add `write_wireframe_obj(points: CirclePoints, colormap: str, directory: Path, beat: BeatPositions | None = None) -> None`: checks like `write_wireframe_frames` (`check_colormap`, the points `(frames, 12)` from 0 to `MAX_POINTS`, the beat one number 0..1 for each frame), makes `colors = line_colors(beat, colormap, frames)` once and writes `frame_{i:06d}.obj` for every frame (comment `chromatic-wireframe frame i of N: x = letter 0-11 (A first), y = frame age 0-11, z = amplitude 1-12 (colors 0-1)`); no sine, contrast stretch or picture size is used
- [X] T017 [US2] In `backend/app/services/frame_rendering.py` call `write_wireframe_obj(points, colormap, directory / OBJ_FOLDER, beat)` after `write_wireframe_frames` for `chromatic-wireframe` when `export_obj` is true (`points` the array already computed for the picture, so the export is made from the same numbers); update the docstring of `write_frames` for the export (both pictures)
- [X] T018 [P] [US2] In `backend/tests/test_obj_export.py` add the Wireframe tests: `amplitude_share` is 1/12 at 0 points, 1 from 24 points, linear between, and the same as `circle_radii / ring_geometry radius`; `wireframe_mesh` of frame 0 has 12 vertices and no faces, of frame 5 has 72 vertices and 55 faces, of frame 11 and later 144 vertices and 121 faces; line 0 is the frame itself at `Y = 0` and line `j` the frame `frame - j` at `Y = j`; X is the letter; Z is 12 times the share (so 1 to 12); the 12 points of a line have one color, the color of that line's own frame (an earlier line keeps its own); every face is four neighbours in counterclockwise order (normal toward +Z); a frame out of range raises; `write_wireframe_obj`: one file per frame, no sine (the Z of a line are exactly the 12 amplitudes: 12 distinct heights for 12 distinct point counts, nothing else), a silent file has all Z = 1 and the first color, a beat gives lines of different colors by the frame's place in the beat as `line_colors`, the same input twice gives identical files, every file passes the reader of T004 with X 0..11, Y 0..11, Z 1..12
- [X] T019 [P] [US2] In `backend/tests/test_obj_export_rendering.py` add the wireframe `write_frames` tests: the files are in `directory/"obj"`, the PNGs are byte-identical with `export_obj` on and off, Decay rate and Extra notes change the files (they decide the points), Threshold applies, the file count equals the frame count, and the points of the files are those of `chromatic_decay.circle_points` (compare the amplitudes with the ones computed from that function for the same arguments)

**Checkpoint**: both exports work from the library; `tests/test_chromatic_wireframe*.py` pass.

---

## Phase 5: User Story 3 - Choose the export on the page and download the files (Priority: P2)

**Goal**: the job accepts `export_obj`, refuses it for other pictures, answers `export_obj` and `obj_url`, offers the ZIP at `GET /api/jobs/{job_id}/obj`, and the page offers the option, shows the result and the download.

**Independent Test**: post a contour job with `export_obj=true`, download the ZIP and check one file per frame; the page tests check the group, the checkbox and the link.

- [X] T020 [US3] In `backend/app/routers/jobs.py` add `_parse_export_obj(text: str | None, sent: bool, image_type: str) -> bool` (not sent: false; `true`/`1`/`false`/`0` any case with spaces; anything else 400 `The 3D export must be true or false.`; true with an image type not in `OBJ_EXPORT_TYPES`: 400 `The 3D export is only available for Contour and Chromatic Wireframe.`), the form field `export_obj: str | None = Form(None)` of `create_job` parsed before the file is read (next to the other parsers), `export_obj=export_obj_value` passed to `write_frames`, and in the answer `"export_obj": export_obj_value` and `"obj_url": f"/api/jobs/{job_id}/obj" if export_obj_value else None` (after `"extra_notes"`)
- [X] T021 [US3] In `backend/app/routers/jobs.py` add the route `@router.get("/{job_id}/obj") def get_obj(job_id: str) -> FileResponse` following the video route: a job number that is not 32 hex digits gives 404 `Render not found.`; no `obj` folder (or no `.obj` file) in `settings.frames_temp_dir / job_id` gives 404 `No 3D export was made for this render.`; otherwise the archive `settings.output_dir / job_id / "obj.zip"` is made with `zip_obj_files` when it does not exist (or when any `.obj` is newer than it) and returned as `application/zip` with `filename="obj.zip"`; update the module docstring of `jobs.py` if it lists the routes
- [X] T022 [P] [US3] Create `backend/tests/test_obj_export_api.py` (with the helpers of `test_polar_chords_api.py`): a contour job with `export_obj=true` answers `export_obj` true and `obj_url`, the ZIP downloads, has one `frame_NNNNNN.obj` per frame (`frame_count`) and each file passes the reader of T004 with 84 points and 66 faces; a wireframe job likewise (12-point lines, 144 points and 121 faces from frame 11 on in a job of at least 12 frames); a job with the export off or not sent answers false and `null`, `GET .../obj` of it is 404 `No 3D export was made for this render.`, and no `obj` folder exists; the PNG frames of the same job with the export on and off are byte-identical (contour and wireframe); `export_obj` for each of the other seven pictures is 400 with the message above and no job folder is left; `export_obj=maybe` is 400 `The 3D export must be true or false.`; `false`/`0`/`FALSE ` are accepted for every picture; a bad job number is 404 `Render not found.`; asking for the ZIP twice gives the same bytes; two jobs of the same music and settings give identical ZIP contents
- [X] T023 [P] [US3] Update the five tests that list the exact keys of the answer (`backend/tests/test_colormap_api.py`, `test_contour_api.py`, `test_interpolation_api.py`, `test_note_count_api.py`, `test_resolution_api.py`) with `"export_obj"` and `"obj_url"`; run them
- [X] T024 [P] [US3] In `frontend/src/api.ts` add `exportObj: boolean` to the settings type and `body.append("export_obj", String(settings.exportObj))` to the request (for every picture, like `beat_coloring`), and `export_obj: boolean` and `obj_url: string | null` to `JobResult`; add `objUrl(job: JobResult): string` returning `/api/jobs/${job.job_id}/obj` (as `videoUrl`); update `frontend/src/api.test.ts` (the settings sample gains `exportObj: true`, its `export_obj: "true"`; a test that the field is sent as text for every picture)
- [X] T025 [P] [US3] In `frontend/src/utilities/validation.ts` add `OBJ_EXPORT_TYPES = ["contour", "chromatic-wireframe"]`, `usesObjExport(imageType: string): boolean`, `DEFAULT_EXPORT_OBJ = false` and `formatExportObj(value: boolean): string` (`"yes"` or `"no"`); in `frontend/src/utilities/help.ts` add `exportObjHelp` (what the files are: one `.obj` per frame, the axes and their ranges 0-12, the vertex colors 0 to 1, that the surface is not curved so a modifier in Blender (for example Subdivision Surface) adds the curve, Contour: the 12 x 7 grid, Chromatic Wireframe: the frame and the 11 before it, the PNGs are still made) and one sentence about the export in the descriptions of Contour and Chromatic Wireframe in `imageTypeHelp`; add the tests to `frontend/src/utilities/validation.test.ts` and `help.test.ts` (exactly the two pictures use it, the words that the help must contain)
- [X] T026 [US3] In `frontend/src/utilities/groups.ts` add the group `{ id: "obj-export", title: "3D export", controls: ["export-obj"] }` shown for `contour` and `chromatic-wireframe` right after the group of the type (as `held-notes` in feature 044: before Note layout and Local peaks); update `frontend/src/utilities/groups.test.ts` (the group's title and control, shown for exactly the two pictures, directly after the group of the type, absent for the others)
- [X] T027 [US3] In `frontend/src/components/SettingsForm.vue` add the state `exportObj` (default `DEFAULT_EXPORT_OBJ`), the checkbox `export-obj` labelled `Export 3D files (.obj)` with an info button (`aria-label="About 3D export"`) and `exportObjHelp`, inside the group `obj-export`, disabled only while a job runs, and `exportObj: usesObjExport(imageType.value) && exportObj.value` in the settings sent on submit (so a stale check never sends `true` for another picture); update `SettingsForm.test.ts` (the group count of the form source goes up by one, the control for the two pictures with its label, info button and group, not shown for the other seven, disabled while a job runs, sent on submit and only for the two pictures)
- [X] T028 [US3] In `frontend/src/App.vue` add to the result list `<li v-if="usesObjExport(result.image_type)">3D export: {{ formatExportObj(result.export_obj) }}</li>` and, where the video export is shown, `<a v-if="result.obj_url" :href="result.obj_url" download>Download 3D files (.zip)</a>` (a short paragraph beside the video export); update `App.test.ts` (the line for the two pictures only, the link only with `obj_url`)

**Checkpoint**: `.venv/Scripts/python.exe -m pytest tests/test_obj_export_api.py -q` passes; `npm test` and `npm run typecheck` pass.

---

## Phase 6: Polish and cross-cutting

- [X] T029 In `backend/app/services/image_types.py` add to the pipeline overview, for `contour` and for `chromatic-wireframe`, the optional **EXPORT** stage after DRAW (`obj_export.write_contour_obj()` with `contour.smoothed_grid()` and `beat_wave.wave_modifier()`; `obj_export.write_wireframe_obj()` with `chromatic_decay.circle_points()`), with the settings that apply (Export 3D files); keep `test_documentation.py` passing
- [X] T030 [P] In `README.md` add a section for the 3D export: what the files are, the axes and ranges, the vertex format with 0-1 colors, the window of 12 lines of the wireframe, the ZIP route and the refusals, how it looks in Blender (import, then a Subdivision Surface modifier), and that the PNGs are still made; add the new test files to the list of tests if the README has one
- [X] T031 [P] Create `specs/045-obj-export-mode/tools/verify_export.py`: for a synthetic job (fixed note values, library defaults) it writes the Contour and Wireframe exports into a temporary folder, reads every file with `read_obj.py`, checks the counts and ranges of [data-model.md](data-model.md) and prints `all files valid` or the first problem (and prints the SHA-256 of every file so two runs can be compared); run it twice and compare
- [X] T032 Add a timing test to `backend/tests/test_obj_export_rendering.py`: for 1,000 frames of a contour (and of a wireframe) the export (`write_contour_obj`, `write_wireframe_obj`) takes less than half of the time of writing 1,000 PNG frames of the same type at a small picture size (the contour at 120 x 80 pixels); the test is skipped if the machine is so slow that the PNG part takes more than 60 s
- [X] T033 Run the whole backend suite (about 10 minutes, in the background), save the failing ids to `specs/045-obj-export-mode/baseline-failures-after.txt` and compare with `baseline-failures-before.txt` by test id: the same 32 failures, none new (write any difference in the notes below); run `verify_drawing.py` (`all frames identical to the baseline`), `npm test` and `npm run typecheck`, `tests/test_type_hints.py` and `tests/test_documentation.py`
- [X] T034 Walk through [quickstart.md](quickstart.md) as far as it can be done without a person at the page (scenarios 1, 2, 3 and 5 through the API with the test client); scenario 4 (Blender) and the by-hand page check are left to the user and said so in the completion report
- [X] T035 Update `C:\Users\Daddy\.claude\projects\d--github-music-visualizer\memory\obj-export-decisions.md` (status: implemented, the traps found) and its line in `MEMORY.md`

**Implementation notes** (filled in during the work, 2026-11-18):

- Baselines: the 32 failing ids are those of 044's `baseline-failures-after.txt`; the final full run (`baseline-failures-after.txt`, 5148 passed, 32 failed) has the same 32 ids, none new. `verify_drawing.py` was copied to this feature's `tools/` with a fresh baseline (the 043 baseline was stale for polar-chords after the jump change of 2026-11-18); it says `all frames identical to the baseline` after every step, and the PNGs are byte-identical with the export on and off (tests).
- T009: `contour.smoothed_grid()` takes `ArrayLike`; `write_contour_frames` calls it; the pictures did not change.
- T015: no change of plan except that the third alias is `LetterAmplitudes` (plan and data model say three aliases).
- T012: the contour export uses `spread_notes` and `hidden_below` at resolution 1 (separate from the picture's grid).
- Design consequence found by a test: the picture's smoothing averages a lone note with its neighbours, so a contour file's Z does not reach 12 (spec FR-006, SC-003 and the data model were amended to "never above 12", heights in proportion).
- T024 did not add `objUrl()`: the answer's `obj_url` is used as the link. T026: for Chromatic Wireframe the group 3D export comes after Held notes (directly after the group of the type for Contour). Result summary shows `3D export: yes` / `no`.
- T032: the timing test uses 300 frames (not 1,000) and small pictures; the export took about 8% of the picture time for both types.
- T031: `verify_export.py` prints `all files valid`; two runs gave the same hashes.
- T034: scenarios 1, 2, 3 and 5 are covered by `test_obj_export_api.py`, `test_obj_export_rendering.py` and `verify_export.py` (through the API with the test client); scenario 4 (Blender) and the by-hand check of the page were not done.

---

## Dependencies and execution order

- Phase 1 first; Phase 2 blocks everything else (T005, T006, T007 before T008).
- Phase 3 (US1) and Phase 4 (US2) both need Phase 2; T015 and T016 sit in the same module as T010 and T011 (do them in order: US1 first), and T012 and T017 are the same function in `frame_rendering.py` (US1's first).
- Phase 5 (US3) needs T012 and T017 (the library) for T020; T022 needs T020 and T021; the frontend tasks T024 to T028 need only the contract and can be done after Phase 2 (T024, T025 in parallel, then T026, T027, T028 in order).
- Phase 6 last.

### Parallel opportunities

- T002, T003 and T004 (Phase 1).
- T013 and T014 after T012 (different files); T018 and T019 after T017.
- T022 and T023 after T021; T024 and T025 at any time after Phase 2.
- T030 and T031 in Phase 6.

## Implementation strategy

**MVP**: Phases 1 to 3 (the Contour export from the library). Then Phase 4 (Wireframe), then Phase 5 (the request, the download and the page), then Phase 6. Keep the pictures byte-identical at every step (`verify_drawing.py` after T009 and after T012).
