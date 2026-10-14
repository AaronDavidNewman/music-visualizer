# Quickstart: Validating the grouped settings

Prerequisites: the repository as it is, the backend `.venv`, `npm install` done in `frontend/`. The colormap lists may still be mid-edit by the user: if the backend suite fails at the one test `test_the_frontends_list_matches_this_one_name_for_name_in_the_same_order` (or at import because the default is not in the list), that is the user's edit, not this feature (the earlier features were verified with a temporary default).

## 1. Automatic checks

```text
cd backend && .venv\Scripts\python -m pytest -q
cd frontend && npx vitest run && npx vue-tsc --noEmit && npm run build
```

Expected: everything passes. New coverage includes: the group model (every control in exactly one group for each image type, the order of the groups, the rows of two and the odd last control, open and closed state), the rendered form for each of the four image types (which groups and controls are in it, which are absent), the new names and the absence of the old ones, the radius setting (limits, refusals, the disc radius, the resize factor, the response), the renamed messages, and source guards for the layout and accessibility markup.

## 2. The frames did not change

```text
cd backend && .venv\Scripts\python <scratchpad>\hashes019.py
```

Expected: the four reference hashes of tiles, blended, Blues/smoothing/threshold and contour are the same as before this feature. A circles job at the default settings has discs of radius 4 (before: 3.98), so its files are not byte-identical to the earlier ones.

## 3. The radius through the API

Post a short WAV with `image_type=circles` and `circle_radius=6`: 200, `"circle_radius": 6`, and the frames show discs of radius 6 (12 pixels across). `circle_radius=3`, `9`, `5.5`, `abc` or empty: 400 with `The circle radius must be a whole number from 4 to 8.`, and no job is created. Send `circle_size=40` with it: accepted and ignored.

## 4. The page (manual: this tooling has no browser)

Start the backend and the frontend (`npm run dev`), open the page, and check each of these. They are the visual part of the spec that the automatic checks cannot see:

1. The form is a list of titled sections: Analysis, Colormap, Image type, Tiles, Data smoothing, Image smoothing, then Create frames. In Analysis, Window size and Frame rate are side by side and Window spacing is alone on the row below, full width. Colormap and Image type are single full-width controls.
2. Click each title: only that section folds and unfolds. Change a value, fold the section, unfold it: the value is still there. Fold everything: the six titles and the button are all visible at once on a 1366 × 768 screen without scrolling.
3. Choose Blended tiles: the Tiles section becomes Blended Tiles with Threshold, Notes and, alone on its row, Blend width. Choose Contour: the section is Contour with Threshold and Notes. Choose Circles: the section is Circles with Movement and Radius, Resize by volume and Memory, then Notes alone; Image smoothing is gone. Go back to Tiles: the values entered for each type are still there.
4. In the half-width cells the sliders are usable and their readouts (`4 px`, `300 circles`, `1 (every frame drawn)`) are not cut off or overlapping the labels or info buttons. Narrow the window below about 26 rem: the controls go one to a row.
5. Type a bad Frame rate (for example `abc`), fold Analysis: its title shows "needs attention" and Create frames is disabled.
6. Create frames and read the summary: it uses Movement, Radius, Notes and Oversampling where it said Unit, Size, Circles per frame and Resolution, and shows only the lines the image type uses. Press Tab to a section title and press Enter: it toggles.

Record any visual problem found here; the layout rules are in `contracts/settings-ui.md`.
