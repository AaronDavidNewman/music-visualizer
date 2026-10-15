# Quickstart: Validating the 600-pixel frames

Prerequisites: the repository as it is, the backend `.venv`, `npm install` done in `frontend/`. If the backend suite fails only at `test_the_frontends_list_matches_this_one_name_for_name_in_the_same_order` (or at import because the default colormap is not in the user's list), that is the user's colormap edit, not this feature; earlier features were verified with a temporary default (`scratchpad/run_with_default.py`).

## 1. Automatic checks

```text
cd backend && .venv\Scripts\python -m pytest -q
cd frontend && npx vitest run && npx vue-tsc --noEmit && npm run build
```

Expected: everything passes. New coverage includes: every frame of every image type at every oversampling (1 to 5) and every interpolate value (1 to 5) is exactly 600 × 400; the app's constants against the literal 600 × 400; the tile columns and rows within one pixel and the tile colors equal to the old ones; the blended and contour frames equal to the old ones after reducing (the same low-level writers called at 252 × 168 and at 600 × 400); the circles at `width=600` against `width=252` (centers and radii differ by exactly 600 / 252, wrap-around at 600 × 400, the resize factor); the player's styles and the help texts.

## 2. The frame sizes through the API

Post a short WAV for each `image_type` and fetch the first frame:

```text
tiles, blended, contour, circles  ->  every PNG is 600 x 400
resolution=5, interpolate=5        ->  600 x 400, including the in-between frames
```

## 3. Content did not change

Render the same short file at the old and the new size with the low-level writers (the equivalence tests do this) and compare: the tile centers have the old colors, the contour and blended frames reduced to 252 × 168 are close to the old ones, and circle frames show the same circles in the same places in proportion to the frame.

## 4. Time and room (60 second file, 1,800 frames)

```text
.venv\Scripts\python <scratchpad>\size_proto.py        (the prototype; times and PNG sizes per job)
```

Expected: every default-settings job finishes within one minute and every costliest-settings job within two (the prototype measured at most about 34 s); the frames of every job take at most 4 times the room they took at 252 × 168 (the largest measured ratio was 3.6, for blended tiles).

## 5. The page (manual: this tooling has no browser)

Start the backend and the frontend, create frames for each image type and look:

1. The frame appears at about 600 pixels wide on a wide window, sharp (no blocky enlargement), in 3:2, and the controls under it are as wide.
2. Narrow the window below 600 pixels: the frame scales down to fit, keeps 3:2 and is not cropped; the controls stay usable.
3. Tiles are crisp flat blocks (50 × 57 pixels at the default grid); Blended tiles have a soft edge about a quarter of a tile wide; Contour has smooth lines; Circles have smooth edges and look like the old circles in proportion (a Radius of 4 is about as large as before, relative to the frame).
4. The help texts of Movement and Radius say that they are measured against a 252-pixel-wide frame.
5. Play, pause, step and the speed control work as before.

Record any visual problem found here; the rules are in `contracts/frame-size.md`.
