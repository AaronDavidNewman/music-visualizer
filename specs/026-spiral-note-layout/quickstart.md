# Quickstart: Validating the spiral note layout

Prerequisites: the repository as it is, the backend `.venv`, `npm install` done in `frontend/`. If the backend suite fails only at `test_the_frontends_list_matches_this_one_name_for_name_in_the_same_order` (or at import because the default colormap is not in the user's list), that is the user's colormap edit, not this feature; earlier features were verified with a temporary default (`scratchpad/run_with_default.py`).

## 1. Automatic checks

```text
cd backend && .venv\Scripts\python -m pytest -q
cd frontend && npx vitest run && npx vue-tsc --noEmit && npm run build
```

Expected: everything passes. New coverage includes: the layout (the spec's table cell by cell, every cell once, C at row 3 column 6 with C# to its right and B3 to its left, the clockwise and counterclockwise arms, exactly the 13 jumps, Rows the identity, determinism); `arrange_notes`; `write_frames` (Rows identical to omitting it, Spiral puts each note's tile or circle at its cell with the same color, the same hidden notes, Notes below 84, Oversampling, Contour and the circles ignoring it, a bad value refused before anything is written); the API (field, default, refusal, echo, ignored for other types); the page (the group and dropdown for three types only, order, summary, request, help).

## 2. Nothing changed with the default

```text
cd backend && .venv\Scripts\python <scratchpad>\hashes019.py
```

Expected: the four reference hashes equal `6819990556fd4095` (tiles), `f32a99c59fcb87fc` (blended), `92b3a27dee73e223` (Blues/smoothing/threshold) and `400cc93e1bfca03d` (contour).

## 3. The layout through the API

Post a short WAV with `image_type=tiles&note_layout=spiral` (and `blended`, `concentric`): 200, `"note_layout": "spiral"`, 600 × 400 frames; the strongest note (say a single tone) is drawn at the cell the table gives it. `note_layout=Spiral` or empty: 400 `The note layout must be one of rows, spiral.` (no file needed). `image_type=contour&note_layout=spiral`: 200 and frames equal to those with rows.

## 4. Look at it

`scratchpad/layout_pictures.py` makes Tiles and Concentric pictures of the same note values in both layouts (each note a different color or size) for a look.

## 5. The page (manual: this tooling has no browser)

Start the backend and the frontend and check:

1. With Tiles, Blended tiles or Concentric chosen, a group "Note layout" with a dropdown (Rows, Spiral) follows the image type's group (after Image type for Concentric) and comes before Local peaks; with Contour, Circles or Circles paint it is not shown.
2. Choose Spiral and create frames: middle C is at row 3, column 6, the note above it to its right and the note below it to its left; the lowest note (A1) is on the bottom row, second column, and the highest drawn note (G#8) in the bottom right corner.
3. The summary says "Note layout: Spiral".
