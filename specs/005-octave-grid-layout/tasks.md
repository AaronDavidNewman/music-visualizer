---

description: "Task list for Octave Grid Layout"
---

# Tasks: Octave Grid Layout

**Input**: Design documents from `/specs/005-octave-grid-layout/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/image-layout.md, quickstart.md

**Tests**: Included, following the plan: pytest for the layout and the API; the frontend change is one CSS rule checked by typecheck, build and the quickstart.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 or US2

## Phase 1: Setup

- [x] T001 Run `pytest` in `backend/` and `npm test` in `frontend/` to confirm a green baseline before changing anything (216 backend and 107 frontend tests at the end of feature 004), and note the numbers

---

## Phase 2: User Story 1 - See the notes arranged by octave (Priority: P1) 🎯 MVP

**Goal**: Frames are drawn as 12 columns by 7 rows of 21 × 24 tiles (252 × 168, exactly 3:2), tile (row, column) is note `12 × row + column`, the tile below is the same note an octave up, and notes 84 to 87 are not drawn.

**Independent Test**: A steady note lights the same column as its octave neighbors, the tile below a lit note is the note at double the frequency, and the image is 252 × 168.

### Tests for User Story 1

- [x] T002 [P] [US1] In `backend/tests/test_frame_rendering.py` replace the imports of `SQUARE_PIXELS` and the old 11 × 8 expectations (`test_grid_layout_and_size`, the `(220, 160)` check in `test_write_frames_names_and_determinism`) with tests for the new layout, using `GRID_COLUMNS`, `GRID_ROWS`, `TILE_WIDTH`, `TILE_HEIGHT`, `SHOWN_NOTES`, `IMAGE_WIDTH` and `IMAGE_HEIGHT`: the constants are 12, 7, 21, 24, 84, 252 and 168; `IMAGE_WIDTH * 2 == IMAGE_HEIGHT * 3` and `TILE_WIDTH * 8 == TILE_HEIGHT * 7`; `render_frame` returns a mode `L` image of size (252, 168); every one of the 84 tiles is a single flat gray level of 21 × 24 pixels with no gaps; for every note `n` from 0 to 83 a frame with only that note lit (level 255) has exactly one lit tile at row `n // 12`, column `n % 12`; for every tile that has a tile below it, the note below is `n + 12` and its frequency (from `note_frequencies()`) is double the note above (to within 1e-9); the lowest note is the top-left tile and note 83 is the bottom-right tile; a frame with only notes 84 to 87 lit gives an all-black image; changing the values of notes 84 to 87 does not change the image; input of 88 values is accepted, 84 is accepted, 83 raises `ValueError`; each tile equals `boost_levels(levels, brightness)[n]` for a random 88-value frame at brightness 2 and 4 (so gray levels are unchanged from the previous layout); an all-zero frame is all black; `write_frames` writes PNGs of size (252, 168) and identical bytes on repeat
- [x] T003 [P] [US1] In `backend/tests/test_jobs_api.py` update the pixel-reading helper `frame_levels` to read the center pixel of each of the 84 tiles (row `r * 24 + 12`, column `c * 21 + 10`) and return 84 values in note order; update the image-size check in `test_frame_endpoint_serves_png` to `("L", (252, 168))`; change the tests that compare with `displayed(levels[index], b)` or `raw_levels(...)` so they compare only the first 84 notes (`levels[index][:84]`); keep every existing behavior check (brightest square, silent file, brightness mapping, spacing and error tests) passing; add API tests: a tone at the exact centre of the spectrum position of note 36, 48 and 60 at window 4096 (frequency `bin_indices[n] * 44100 / 4096` from `NoteBinAnalyzer`) lights the tile at row 3 column 0, row 4 column 0 and row 5 column 0 respectively as the brightest in at least 95% of frames, so the tile below a lit tile is the next octave; a tone at the centre of note 83 lights row 6, column 11; a tone at the centre of note 86 (one of the omitted notes) leaves no visible tile at full white (the maximum visible level is below 255); the image of any frame is 252 × 168 with width ÷ height exactly 1.5

### Implementation for User Story 1

- [x] T004 [US1] In `backend/app/services/frame_rendering.py` replace `GRID_COLUMNS = 11`, `GRID_ROWS = 8` and `SQUARE_PIXELS = 20` with `GRID_COLUMNS = 12`, `GRID_ROWS = 7`, `SHOWN_NOTES = GRID_COLUMNS * GRID_ROWS`, `TILE_WIDTH = 21`, `TILE_HEIGHT = 24`, `IMAGE_WIDTH = GRID_COLUMNS * TILE_WIDTH` and `IMAGE_HEIGHT = GRID_ROWS * TILE_HEIGHT`; replace the old `assert GRID_COLUMNS * GRID_ROWS == NOTE_COUNT` with assertions that `SHOWN_NOTES <= NOTE_COUNT`, `TILE_WIDTH * 8 == TILE_HEIGHT * 7` and `IMAGE_WIDTH * 2 == IMAGE_HEIGHT * 3`; change `render_frame` to raise `ValueError` for fewer than `SHOWN_NOTES` values, take the first `SHOWN_NOTES` gray levels, apply `boost_levels`, reshape to `(GRID_ROWS, GRID_COLUMNS)` and repeat rows `TILE_HEIGHT` times and columns `TILE_WIDTH` times; update the module and function docstrings (12 × 7 grid of 21 × 24 tiles, each row an octave, the highest four notes not drawn); leave `to_gray_levels`, `boost_levels` and `write_frames` unchanged
- [x] T005 [US1] Run `pytest` from `backend/` and fix failures in T002 and T003 and the existing tests

**Checkpoint**: Frames use the new layout and every earlier behavior still holds.

---

## Phase 3: User Story 2 - The page shows the new shape correctly (Priority: P2)

**Goal**: The page displays the 3:2 image at its true proportions at any width, without size jumps, and the docs describe the new layout.

**Independent Test**: Resize the page from 320 to 1920 pixels wide: the image stays 3:2, and playback never changes its size.

### Implementation for User Story 2

- [x] T006 [US2] In `frontend/src/components/FramePlayer.vue` add `aspect-ratio: 3 / 2` to the `.frame` rule (keeping `width: min(100%, 660px)` and `image-rendering: pixelated`) with a comment that it matches the 252 × 168 image, so the space is reserved before a frame loads and the image never changes size between frames
- [x] T007 [US2] Run `npm test`, `npm run typecheck` and `npm run build` in `frontend/` and fix errors
- [x] T008 [P] [US2] Update the written description of the image to the new layout: `README.md` (12 × 7 grid of 21 × 24 tiles, 252 × 168, 3:2, each row an octave with the tile below a note being the octave above it, the highest four notes not drawn, gray scaling still against all 88 notes), and in `specs/002-audio-frames-ui/` the spec (FR-009 and the "Image layout" and "Image size" assumptions), `contracts/http-api.md` (the image size line and the image content contract), `data-model.md` (Frame Image), `research.md` (the image decision), `plan.md` (the summary), `quickstart.md` (the "11 × 8 grid" step) and `checklists/requirements.md` (the note about the 11 by 8 grid); each change says the layout was replaced by feature 005 and gives the new numbers, and the old numbers do not remain as current statements anywhere

**Checkpoint**: The page and the docs match the new layout.

---

## Phase 4: Polish & Cross-Cutting Concerns

- [x] T009 Run the whole backend suite and the frontend checks (`pytest` in `backend/`; `npm test`, `npm run typecheck`, `npm run build` in `frontend/`) and confirm all pass
- [x] T010 Using `backend/audio/fotr-intro1-echo.wav`, check on real data: (a) SC-004: for many frames at brightness 2, 4 and 10 compute each note's tile pixel from `render_frame` and compare it with the previous layout's value for that note (`boost_levels` of the same gray levels, which is what the old squares showed) across all 84 notes; (b) the scaling caveat: report whether the loudest value in the file is among notes 0 to 83 or in the omitted notes 84 to 87, and how many frames, if any, have one of the omitted notes louder than every shown note; (c) SC-005: start the backend on an unused port from `backend/` with the venv (check the port first; do not stop or reuse a server the user is running), run the default `POST /api/jobs` twice, compare frame count, window count and time with the earlier results (10,224 frames, 10,224 windows, about 5 to 6.5 s), confirm a returned frame is 252 × 168, then stop the server and delete only the job folders created in this run; (d) save a picture of the same frame in the old square layout and the new layout side by side and look at it
- [x] T011 Report that the browser walkthrough in `quickstart.md` (step 3, in particular resizing from 320 to 1920 pixels and watching playback for size changes) was not run if no browser can be driven from this session. **Not run: no browser could be driven from this session.** The CSS rule (`aspect-ratio: 3 / 2` on the frame image) is confirmed present in the built stylesheet, and the served images are exactly 252 × 168, but how the page lays out at 320 to 1920 pixels wide, and that playback does not change the image size, have not been seen in a browser and need a manual check.
- [x] T012 Mark completed tasks `[x]` in this file

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 (US1) → Phase 3 (US2) → Phase 4.
- T002 and T003 are independent of each other (different files). T004 follows both. T008 is documentation only and can be done any time after T004, in parallel with T006.
- Write T002 and T003 first and see them fail before T004.

## Implementation Strategy

- **MVP**: Phases 1 and 2: the new layout is drawn and every test passes.
- **Then**: Phase 3 reserves the correct shape on the page and brings the docs in line, and Phase 4 checks the real file, the scaling caveat and timing.
