# Quickstart: Validating Concentric

Prerequisites: the repository as it is, the backend `.venv`, `npm install` done in `frontend/`. If the backend suite fails only at `test_the_frontends_list_matches_this_one_name_for_name_in_the_same_order` (or at import because the default colormap is not in the user's list), that is the user's colormap edit, not this feature; earlier features were verified with a temporary default (`scratchpad/run_with_default.py`).

## 1. Automatic checks

```text
cd backend && .venv\Scripts\python -m pytest -q
cd frontend && npx vitest run && npx vue-tsc --noEmit && npm run build
```

Expected: everything passes. New coverage includes: the steps (exact ratios `k² / 144` give `k`, the loudest is 12, a silent frame is 1, never below 1, monotone within a frame, per frame); the ring colors (every colormap, positions 0, 0.5 and 1); the geometry (centers, radius 25, neighbours touching, nothing outside a cell, the ring radii); the pixels (flat ring colors, the background between circles, a smaller circle equal to the first rings of a full one, equal to a brute-force drawing on a 4 × 4 canvas); `write_frames` and the API (six image types, ignored settings, the beat measured for every Concentric job, settings checked first, smoothing applies, silent and short and beat-less files, mono equals stereo, determinism); the page's group, controls (no checkbox), summary and help.

## 2. The other image types did not change

```text
cd backend && .venv\Scripts\python <scratchpad>\hashes019.py
```

Expected: the four reference hashes equal `6819990556fd4095` (tiles), `f32a99c59fcb87fc` (blended), `92b3a27dee73e223` (Blues/smoothing/threshold) and `400cc93e1bfca03d` (contour).

## 3. The type through the API

Post a short WAV (a few notes and clicks of changing strength) with `image_type=concentric`: 200, `"image_type": "concentric"`, every frame a 600 × 400 PNG; the loudest note's circle has a radius of 25 pixels, the other circles are smaller, the background is the colormap's middle color, and the rings of a frame at the strongest beat run to the right-most color. `image_type=concentrics`: 400 with the message that lists six names. `peak_distance=50` or `peak_prominence=101`: 400 with the measurement's message (no file needed).

## 4. Time and room (60 second file, 1,800 frames)

Expected: under 30 seconds (the prototype measured about 9 s on four threads), frames of about 60 KB.

## 5. The page (manual: this tooling has no browser)

Start the backend and the frontend and check:

1. The Image type dropdown offers six choices; choosing Concentric shows the groups Analysis, Colormap, Image type, **Local peaks** (Minimum distance and Prominence only, no checkbox) and Data smoothing, and no Threshold, Notes or Image smoothing.
2. Switching to Tiles shows the Local peaks group with the checkbox again; switching to Contour or Circles hides it.
3. Create frames and play: 84 circles on the grid; louder notes have bigger circles with more rings; the colors move along the colormap with the beat (the rings reach the right-most color at strong beats and only the middle at the lowest point); the summary says "Image type: Concentric" with Minimum distance and Prominence.
