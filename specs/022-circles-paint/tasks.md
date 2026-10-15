---

description: "Task list for Circles paint (feature 022)"
---

# Tasks: Circles Paint

**Input**: Design documents from `/specs/022-circles-paint/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/circles-paint.md, quickstart.md

**Tests**: Written first for each story (the project's practice): the plan reuse, the canvas and the circles at the pixel level, the API, and the page's group and summary (server-side rendering and source guards, since there is no browser or DOM library here). The look of the canvas building up in the player is the manual step of the quickstart.

**Organization**: By user story: US1 the painted canvas itself (P1), US2 choosing it on the page and through the server (P2), US3 the same look as Circles and the limits (P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- Paths are from the repository root. Backend checks run with the user's colormap lists possibly still inconsistent: use the temporary-default runner (`scratchpad/run_with_default.py`, file restored) and report the one expected list-mismatch failure. Edit files with their line endings preserved; avoid `sed -i`; scripts with backticks or non-ASCII go in files written with the Write tool; replace test functions only block by block and compare test counts before and after (an earlier accident deleted tests).

---

## Phase 1: Setup

- [x] T001 Record the baseline before changing anything: the backend suite (temporary default colormap, file restored), the frontend suite, typecheck and build; the four reference hashes (`scratchpad/hashes019.py`: tiles `6819990556fd4095`, blended `f32a99c59fcb87fc`, Blues/smoothing/threshold `92b3a27dee73e223`, contour `dff443e80f5eed3f`); the per-file test counts of the backend (`scratchpad/count_tests.py`); the tests that mention the list of image types (they derive from `IMAGE_TYPES` or name the four types: `test_image_types.py`, `test_image_type_api.py`, `test_circles*.py`, `groups.test.ts`, `validation.test.ts`, `SettingsForm.test.ts`, `App.test.ts`), because the fifth type will touch them.
  - Done: Baseline: the four reference hashes as recorded for feature 021 (`68199905…`, `f32a99c5…`, `92b3a27d…`, `dff443e8…`), backend 2,917 tests collected (it was 2,920 at the end of feature 021: the count follows the length of the user's colormap lists), frontend 463 tests, typecheck and build clean; the per-file counts saved (`scratchpad/counts_022_before.txt`).

---

## Phase 2: User Story 1 - A picture that is painted by the music, frame after frame (Priority: P1) 🎯 MVP

**Goal**: A writer that paints the circles of each frame onto a canvas that carries over from frame to frame, with the circles of `plan_circles` and no memory.

**Independent Test**: Write frames for `circles_paint` from a file with a steady note that changes volume now and then: frame 0 is the background with one circle, every later frame equals the previous one outside the new circle, and nothing that was painted disappears until it is covered.

### Tests for User Story 1 (write first, they fail)

- [x] T002 [P] [US1] Create `backend/tests/test_circles_paint.py` for the writer and the plan (spec scenarios 1 to 7 of Story 1, FR-003 to FR-007, FR-009, SC-002 to SC-005, SC-008): (a) `plan_circles(..., memory=None)` adds exactly the circles that the plan with a memory adds, frame by frame, for random values and several settings, and its `remembered` is empty; a bad memory other than `None` is still refused; (b) the canvas: frame 0 is the background (the colormap's middle color, every colormap) with the circles painted on it; for every later frame every pixel outside the clipped patch boxes of that frame's circles equals the same pixel of the previous frame, exactly; a frame with no sound is an exact copy of the previous one; two runs give identical files; (c) the circles: the pixel at the center and the pixels just inside the radius are exactly the colormap's color for the note's strength, whatever was painted there before, for every colormap; the pixels on the edge are mixes of the circle's color and what was under it (and a ring of such pixels exists); where two circles of a frame overlap the strongest note's color is on top; a circle near an edge is cut off and nothing appears on the opposite side; the radius is `Radius × 600 / 252` and the step `Movement × units × 600 / 252` (and `1 to 3 times` the radius with the resize); (d) no memory: after 600 frames (more than Circles' largest memory) the pixels of the first frame's circle are still there where nothing was painted over them; (e) equal to Circles: the circles of the paint (centers from the plan) are the circles that Circles draws newest (the `added` lists are equal), and the center color of Circles' newest circle equals the paint's; (f) the settings are checked before anything is written (each bad value of Movement, Radius, Resize, Notes refused with the messages of Circles, a bad colormap refused, nothing created); (g) an error while saving a picture is raised and the threads are shut down.
  - Done: `backend/tests/test_circles_paint.py`: the plan with no memory adds exactly the circles of the plan with a memory (three settings) and keeps nothing; a memory that is given is still checked; the first frame for every colormap; every pixel outside the clipped patch boxes of a frame's circles equal to the previous frame's, exactly (40 frames of a melody); silent frames exact copies; byte-identical runs; saved frames are independent copies; solid inside for every colormap (even where a circle overlaps its own trail); a ring of in-between colors on the edge; the strongest on top; a circle past the right edge cut off and nothing on the left; radius and place scaled to 600 x 400; the resize up to three times the radius; no memory (the quiet circle of frame 0 survives 600 later circles); the circles are Circles' (the same centroid and area for three settings); settings refused before anything is written; wrong shapes; an empty file; a saving error. Three of my first tests were wrong, not the code: a repainted circle does change (its one-pixel edge mixes again and hardens), so the spec's edge case was corrected and the test now checks that only the edge changes and only toward the color; the edge test needed 40 frames to reach the edge; the helper took the maximum of an empty array.

### Implementation for User Story 1

- [x] T003 [US1] Edit `backend/app/services/circles.py`: `plan_circles` accepts `memory=None` (no check, a buffer that keeps nothing, `remembered` empty), docstring updated. Create `backend/app/services/circles_paint.py`: `write_paint_frames(values, peak, colormap, directory, notes, unit, radius, width, height, resize)` (research Decisions 2 to 4): checks, the background canvas, per circle the whole-pixel patch, the supersampled coverage mask (the far end of the box minus one, as in `write_circle_frames`), clipped to the canvas, `canvas.paste(color, box, mask)`, `canvas.copy()` saved on the few-thread pool as `frame_000000.png` and up, the first worker error raised. Register the type: `IMAGE_TYPES` in `backend/app/services/image_types.py` (and its docstring) and a branch in `write_frames` of `backend/app/services/frame_rendering.py` (every circle setting is still checked for every type, `circle_memory` included and then ignored; the branch returns before the grid pipeline; docstring).
  - Done: `circles.py` (`plan_circles(memory=None)` keeps nothing), new `circles_paint.py` (`_paint_circle`: a whole-pixel patch, the disc on a 4 times larger `L` mask averaged down, clipped to the canvas, `canvas.paste(color, box, mask)`; `write_paint_frames`: the canvas carried over, a copy saved on the few-thread pool per frame), `IMAGE_TYPES` and its docstring, a branch in `write_frames`.
- [x] T004 [US1] Run the whole backend suite (temporary default colormap) and fix the existing tests that the fifth type touches (lists of image types, loops over `IMAGE_TYPES` that assumed the grid pipeline, the refusal message with five names), keeping each test's meaning; the test counts must not drop. Mutation checks, each caught and restored: the canvas not carried over (a fresh background each frame), a copy of the previous frame not taken (saved pictures change later), the circles painted weakest last, the mask without the far-end minus one, the mask averaged with the wrong factor, no clipping (a patch past the edge wraps or errors), the circle painted at half opacity, the radius not scaled, the step not scaled, `memory=None` still limiting circles, a frame with no circle not saved, the plan of the paint using another note order than Circles.
  - Done: The whole backend suite after the registration: only two existing tests failed, both asserting the tuple of four types (updated); the counts did not drop (`test_image_types.py` and `test_image_type_api.py` gained one parametrized case each). Mutation checks, all 15 caught and restored (`scratchpad/mutate_022_back.py`): the canvas not carried over, no copy for saving, weakest painted last, a hard-edged mask, half see-through circles, the radius not scaled, the resize ignored, wrapping past the right edge, no-memory keeping a circle, a frame with no circle not saved, the colors scaled to half the peak, a black background, a setting not checked, a swallowed saving error, and the mask without the far end minus one (this one first survived: a quarter pixel more is inside the area tolerance of one circle, so a test of the average area over 20 radii and places was added, bias under 0.6 %).

**Checkpoint**: `write_frames(..., image_type="circles_paint")` paints a canvas; the other types are unchanged.

---

## Phase 3: User Story 2 - Choose Circles paint on the page and through the server (Priority: P2)

**Goal**: The type is accepted by the server (with its settings, `circle_memory` validated and ignored) and offered on the page with its own group and summary lines.

**Independent Test**: Post `image_type=circles_paint`: 200 and 600 × 400 frames; refusals list five names. Render the form with the new type: a group "Circles paint" with Movement, Radius, Resize by volume and Notes and no Memory.

### Tests for User Story 2 (write first, they fail)

- [x] T005 [P] [US2] In `backend/tests/test_circles_paint.py` (the API part, using the helpers of `test_circles_api.py`): the type is accepted with the default settings for every colormap; the response reports `circles_paint` and the circle settings (including `circle_memory`); every frame is a 600 × 400 RGB PNG, the count equals that of tiles; a bad type (`circle_paint`, `Circles_paint`, ` circles_paint`, empty) is refused with the message that lists the five names; the circle fields are refused as for Circles (every bad value, before the file is read, nothing created); `circle_memory=99` refused, `circle_memory=500` accepted and the frames equal those without it; `interpolate`, `resolution`, `note_count`, `threshold`, `blend_width` accepted and ignored (equal frames); smoothing and the colormap apply; each circle setting that is sent changes the frames (Movement, Radius, Resize, Notes); two identical requests give identical frames; the other types do not change when the circle settings are sent.
  - Done: The API part of `test_circles_paint.py`: the type with every colormap (the response, 600 x 400 RGB PNGs, the count of tiles), nine bad type names refused with the five names, each bad circle setting refused as for Circles before the file is read and without a job, `circle_memory` 100 and 500 accepted with equal frames, the ignored settings, each circle setting changing the frames, smoothing and the colormap (only the colors differ), the canvas only growing in the player, identical runs, the other types unchanged; and at the `write_frames` level the memory checked before anything is written and without effect (added after the mutation "circle_memory not validated" survived the API tests, because the router checks it too).
- [x] T006 [P] [US2] Frontend tests: `frontend/src/utilities/validation.test.ts` (the five image types and their labels, `isCirclesType` for `circles` and `circles_paint` only, `gridSettingsApply` false for both), `frontend/src/utilities/groups.test.ts` (the group `circles_paint`, "Circles paint", controls `circle-unit`, `circle-radius`, `circle-resize`, `circle-notes`, rows `[2, 2]`; `groupsFor("circles_paint")` is the top groups, the type group, Data smoothing and no Image smoothing; every control exactly once; Memory in `circles` only; the expected lists of the existing tests extended), `frontend/src/components/SettingsForm.test.ts` (the dropdown offers five choices; the form rendered with the starting type `circles_paint` has the group in place and no `circle-memory`, nothing disabled but while busy; the values of Movement, Radius, Resize and Notes are shared with Circles in the source), `frontend/src/App.test.ts` (the circle lines for both types and the Memory line only for `circles`), `frontend/src/utilities/help.test.ts` (the Image type help describes Circles paint: no memory, a copy of the previous picture, solid, nothing fades).
  - Done: `validation.test.ts` (five types and labels, the refusal with the five names for 14 bad values, `isCirclesType`, `gridSettingsApply`), `groups.test.ts` (the ten groups, Circles paint without Memory, rows `[2, 2]`, no Image smoothing), `SettingsForm.test.ts` (five choices, the group after Image type for the new type, no Memory and no grid controls, the shared values, Image smoothing only for the grid types), `App.test.ts` (the circle lines for both circle types, Memory for `circles` only), `help.test.ts` (no memory, a copy of the previous picture, solid, never fades). 29 failed before T007.

### Implementation for User Story 2

- [x] T007 [US2] Edit `frontend/src/utilities/validation.ts` (the fifth choice after Circles, `isCirclesType`, `gridSettingsApply` through it), `frontend/src/utilities/groups.ts` (the group and `TYPE_GROUPS`), `frontend/src/components/SettingsForm.vue` (`TYPE_GROUP_IDS`), `frontend/src/App.vue` (the circle lines for either type, Memory for `circles` only), `frontend/src/utilities/help.ts` (the Image type help). Fix the existing frontend tests that name four types.
  - Done: `validation.ts` (the fifth choice, `isCirclesType`, `gridSettingsApply` through it), `groups.ts` (the group and `TYPE_GROUPS`), `SettingsForm.vue` (`TYPE_GROUP_IDS`), `App.vue` (the circle lines for either type, Memory for Circles only), `help.ts`. The existing frontend tests needed their expectations extended (counted above in T006).
- [x] T008 [US2] Verify: backend and frontend suites, typecheck and build pass; mutation checks, each caught and restored: Memory shown for Circles paint, the group missing Resize by volume, the group not listed in the form's type ids (open state shared), `gridSettingsApply` true for the new type (Image smoothing shown), the summary showing Memory for the new type, the label wrong, `isCirclesType` false for the new type, the new type missing from the backend tuple, `circle_memory` not validated for the new type, `circle_memory` changing the frames.
  - Done: Frontend 479 tests, typecheck and build clean. Mutation checks, all 9 frontend ones and the 3 backend ones caught and restored: Memory shown for Circles paint, the group without Resize by volume, the group missing from the form's type ids or from the model's, `isCirclesType` false for the new type, the summary showing Memory for it, the summary circle lines for Circles only, a wrong label, the help text without Circles paint, the type missing from the backend tuple, `circle_memory` not validated, the paint branch's arguments out of order.

**Checkpoint**: US1 and US2 work.

---

## Phase 4: User Story 3 - It keeps the look of Circles and stays practical (Priority: P3)

**Goal**: The same colors, smoothing, scaling and size as Circles, and the limits of time and room.

**Independent Test**: Frames of the paint and of Circles for the same file and settings have the same circles (place, color, radius); a 60 second job is within the limits.

### Tests for User Story 3 (write first)

- [x] T009 [P] [US3] In `backend/tests/test_circles_paint.py`: every colormap gives the circles its colors (the center color equals the tiles' color for the same strength, `lookup_table(name)[round(sqrt(share) * 255)]`), smoothing before the choice of the strongest notes (a click kept alive by smoothing is painted, raw it is not), the colormap changes only the colors and not the places, a very quiet file paints in the colors of its own peak, the extreme settings work (Movement 1 and 10, Radius 4 and 8, Notes 5 and 12, the resize on), 300 frames at the largest settings finish within a bound, and the four other types' output equals the reference hashes (the existing reference test).
  - Done: In `test_circles_paint.py`: the colors (every colormap, the solid test), smoothing before the choice of the strongest notes (frame 1 differs raw and smoothed), the colormap changing only the colors, a very quiet file in the colors of its own peak, four extreme settings (Movement 1 and 10, Radius 4 and 8, Notes 5 and 12, the resize on) neither blank nor one color, 300 frames at the largest settings within a minute; the other types' reference hashes are unchanged.

### Implementation for User Story 3

- [x] T010 [US3] Measure time and room (`scratchpad/paint_proto.py` adapted to the real writer, through `write_frames` and through the API) for the 60 second, 1,800 frame job at the default and the largest settings, against Circles: within one minute and no slower than Circles; record the figures in this task's notes (the prototype gave 4.4 s and 2.5 s for the paint, and 17 s and 176 s for Circles, with 332 and 78 MB against 113 and 130 MB); if the room is a problem, try a higher PNG compression level for this type first. Note in the report the finding that Circles with the resize on at the largest settings is above the two-minute limit of feature 021 (outside this feature).
  - Done: 60 s, 1,800 frames of 600 x 400 through `write_frames` (`scratchpad/paint_perf.py`): Circles paint 4.4 s and 300 MB at the defaults, 2.2 s and 73 MB at the largest settings with the resize on (3.6 s and 181 MB with it off); Circles 16.6 s and 109 MB at the defaults and 44.6 s and 220 MB at the largest with the resize off. Within one minute and no slower than Circles. The room of Circles paint at the defaults is 2.8 times that of Circles (the canvas keeps all its detail): of the same order, so no change of the PNG compression level. Finding outside this feature: Circles with the resize on at the largest settings took 176 s in the prototype, above the two-minute limit that feature 021 set (its own measurement had the resize off); not changed here.

**Checkpoint**: all three stories work.

---

## Phase 5: Polish & Cross-Cutting

- [x] T011 [P] Update `README.md` (the Image type paragraph names five types; a Circles paint paragraph after Circles: no memory, the canvas, solid and never fading, the same circles as Circles, the settings and what is ignored, the request value `circles_paint`, the page's group, the measured times and room, the code in `backend/app/services/circles_paint.py`, the spec directory) and add amendment notes (not rewrites) at the top of the `spec.md` of features 019 and 020 saying that there are five image types since feature 022 and what the fifth is.
  - Done: README: the Image type paragraph names five types, a Circles paint paragraph after Circles, the settings page paragraph and the dropdown sentence; amendment notes at the top of the specs 019 and 020.
- [x] T012 Final verification: the backend suite (temporary default, file restored; only the user's list-mismatch failure may remain), the list-tolerance run (`scratchpad/tolerance.py`), the four reference hashes equal to T001, the frontend suite, typecheck and build, the per-file test counts not lower than T001's, the backend mutation checks and the frontend ones of T004 and T008 rerun.
  - Done: Backend 3,021 tests, all passed with the temporary default colormap (the user's lists now match each other; what remains is that the backend default `hot` is not in its own list and the frontend's is `coolwarm`, which the colormap tests catch without the temporary default); the list-tolerance run 2,769 passed and only `test_the_frontends_default_matches_this_one` failed (that same default); the four reference hashes equal to T001; frontend 479 tests, typecheck and build clean; no per-file count lower than T001's.
- [x] T013 Walk the quickstart: sections 1 to 4 through the suites, the test client and the prototype; render a picture of the canvas building up (frames 1, 20, 40 and 80 of a melody, next to Circles at the same settings) and send it to the user; section 5 (the page in a browser) cannot be done with this tooling: say so, list what the tests cover, and what only a person can check.
  - Done: Quickstart 1 to 4 done through the suites and the prototypes; a picture of the canvas at frames 6, 21, 41 and 80 of a melody, beside Circles at the same settings (the paint keeps every circle solid, Circles fades the old ones), was sent to the user. **Step 5 (the page in a browser) was not done**: this tooling has no browser. Covered: the group, the dropdown, the summary and the help text by server-side rendering and source guards. Only a person can check: how the canvas looks building up in the player, and whether the dense layering on a long file is pleasing.

---

## Dependencies & Execution Order

- **Setup (T001)** first. **US1** next: T002 (tests) before T003; T004 after T003.
- **US2** needs US1 (the type must exist in the backend): T005 and T006 can be written any time; T007 before T008; T005 needs T003.
- **US3** after US1: T009 with the same file as T002 (so after it), T010 last of the story.
- **Polish (T011 to T013)** after the stories; T011 can run alongside T012.

### Parallel opportunities

- T002 with T006 (a backend test file and the frontend test files).
- T005 with T006.
- T011 with T012.

## Implementation Strategy

1. T001, then the painter (US1) as the MVP: tests, the module, the registration, the existing tests that the fifth type breaks, the mutation checks.
2. The server and the page (US2), then the look and the limits (US3).
3. Documentation, the full verification, and an honest report of what only a browser can confirm and of the Circles timing finding.

## Notes

- Frames of the four other image types must not change (the four reference hashes).
- The paint writer must never wrap a circle around an edge: a circle past an edge is cut off.
- Verify mutation checks restore the files byte for byte (the temporary default colormap included).
