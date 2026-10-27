# Quickstart: Validating the beat coloring

Prerequisites: the repository as it is, the backend `.venv`, `npm install` done in `frontend/`. If the backend suite fails only at `test_the_frontends_list_matches_this_one_name_for_name_in_the_same_order` (or at import because the default colormap is not in the user's list), that is the user's colormap edit, not this feature; earlier features were verified with a temporary default (`scratchpad/run_with_default.py`).

## 1. Automatic checks

```text
cd backend && .venv\Scripts\python -m pytest -q
cd frontend && npx vitest run && npx vue-tsc --noEmit && npm run build
```

Expected: everything passes. New coverage includes: the position in the peak (0 before the first peak and without peaks, the formula at peaks and between them with the interpolated minimum and maximum, held at 0..1, no range, arrays, frame times); `colorize` with a beat (half and half to one table step, the middle and right-most colors for every colormap, monotone in both inputs, `beat=None` as before); `write_frames` with a beat (the strong tile at positions 0, 0.5 and 1, hidden tiles as before for both types, other types ignoring it, resolution and interpolate above 1, a bad beat refused); the API (defaults, parsing and messages, checked when off, off identical, on different, response keys); the page's group, controls, summary and payload.

## 2. Nothing changed when the checkbox is off

```text
cd backend && .venv\Scripts\python <scratchpad>\hashes019.py
```

Expected: the four reference hashes equal `6819990556fd4095` (tiles), `f32a99c59fcb87fc` (blended), `92b3a27dee73e223` (Blues/smoothing/threshold) and `400cc93e1bfca03d` (contour); they are made without the beat.

## 3. The coloring through the API

Post a short WAV (a steady note and clicks of changing strength) with `image_type=tiles` and `beat_coloring=true`: 200, `"beat_coloring": true`, `"peak_distance": 100`, `"peak_prominence": 50`; the strong note's tile has the middle color before the first click and a color near the right-most one around a loud click. With `beat_coloring=false` (or not sent) the frames equal those of a job without the field. `beat_coloring=maybe`: 400 with its message; `peak_distance=50` or `peak_prominence=101`: 400 with the measurement's message even with `beat_coloring=false`. `image_type=contour` with `beat_coloring=true`: 200 and frames equal to those without it.

## 4. Time (60 second file)

Expected: with the beat coloring on, no more than a few seconds more than with it off (the measurement takes about 0.03 s).

## 5. The page (manual: this tooling has no browser)

Start the backend and the frontend and check:

1. With Tiles or Blended tiles chosen, a collapsible group "Local peaks" follows the type's group, with the checkbox "Beat coloring" (unchecked), "Minimum distance" (100 ms) and "Prominence" (50%), two controls per row, the last alone. With Contour, Circles or Circles paint it is not shown.
2. Check the box and create frames of music with a clear beat: the picture's brightness follows the strength of the beats (not a dip between equally strong beats); unchecked, the pictures are as before.
3. The summary says "Beat coloring: Off", or "On" with the two values.
