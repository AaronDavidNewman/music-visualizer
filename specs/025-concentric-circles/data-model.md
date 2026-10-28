# Data Model: Concentric

No stored data. This describes how a Concentric frame is made from the smoothed note values and the frame's position in the local peak.

## The image type

| Request value | Label on the page | Group |
|---------------|-------------------|-------|
| `concentric` | Concentric | none of its own; the group `concentric-peaks`, "Local peaks" (below) |

`IMAGE_TYPES = ("tiles", "blended", "contour", "circles", "circles_paint", "concentric")`; the refusal message is `The image type must be one of tiles, blended, contour, circles, circles_paint, concentric.`

## What a frame is

For frame `f` with the smoothed values `v[f, 0..83]` of the 84 drawn notes and the position `p[f]` (0 to 1) in the local peak (`0` when none is given):

| Quantity | Definition |
|----------|------------|
| `loudest[f]` | `max(v[f, :])` |
| `step[f, n]` | `clip(ceil(12 × sqrt(v[f, n] ÷ loudest[f]) − 1e-9), 1, 12)`; `1` for every note when `loudest[f] = 0` |
| `row[f, k]` | `rint((k − 1) / 11 × (0.5 + 0.5 × p[f]) × 255)`, `k = 1 … 12` |
| `color[f, k]` | the colormap's table entry at `row[f, k]` |
| `background` | the colormap's table entry at row 128 (`MIDDLE_COLOR_ROW`) |
| circle of note `n` | center at the center of the tile of note `n` (note `n` at row `n // 12` from the top, column `n % 12`); full radius `R = min(smallest cell width, smallest cell height) / 2` = 25 px on the 600 × 400 frame |
| ring `k` of the circle | the points at distance `d` from the center with `(k − 1) R / 12 < d ≤ k R / 12` |
| drawn circle | rings `1 … step[f, n]`, each flat with `color[f, k]`; everything else the background |
| frame file `f` | the 600 × 400 RGB picture, edges smooth (a pixel is the average of its 4 × 4 sub-pixels) |

Consequences: ring `k` has the same color in every circle of a frame whatever its step; the loudest circle has all 12 rings; at `p = 1` rings 1 and 12 are table rows 0 and 255; at `p = 0` ring 12 is row 128, the background's color; a circle never leaves its cell (`R` is at most half of both cell sides) and neighbours in a row touch.

## The geometry (cached, the same for every frame)

For the frame size and grid: `cell[y, x]` (0 to 83), `ring_a[y, x]` and `ring_b[y, x]` (0 = outside the circle, 1 to 12) the two most frequent classes among the 16 sub-pixels of the pixel, and `weight_b[y, x] = count(b) / (count(a) + count(b))`. A pixel has at most two classes (asserted). Per frame the picture is `T[cell, ring_a] × (1 − weight_b) + T[cell, ring_b] × weight_b` with `T[n, 0] = background` and `T[n, k] = color[f, k]` if `k ≤ step[f, n]` else `background`, rounded to a whole number per channel.

## Settings

| Setting | Request field | Concentric |
|---------|---------------|------------|
| Colormap, window size, frame rate, window spacing | as before | applies |
| Smoothing window, Smoothing | `smoothing_window`, `smoothing` | applies (the values are smoothed over the frames as for the tiles) |
| Minimum distance, Prominence | `peak_distance`, `peak_prominence` | applies; always (no checkbox); checked before the file is read |
| Beat coloring | `beat_coloring` | accepted, echoed, no effect |
| Threshold, Notes, Oversampling, Interpolate, Gaussian smoothing, blend width, the circle settings | as before | accepted and ignored |

Group `concentric-peaks`: title "Local peaks", controls `["peak-distance", "peak-prominence"]`, shown for `concentric` only, after Image type and before Data smoothing. Order of groups for Concentric: Analysis, Colormap, Image type, Local peaks, Data smoothing.

## Validation

| Input | Rule | Message |
|-------|------|---------|
| `image_type` | one of the six names | `The image type must be one of tiles, blended, contour, circles, circles_paint, concentric.` |
| `peak_distance`, `peak_prominence`, `beat` | as in feature 024 | as in feature 024 |
| the note values | a 2-D array with at least 84 columns, 0 or more | `At least 84 note values per frame are needed (got shape ...).` (as `write_frames` already says) |

## Summary shown after a job (Concentric)

Duration, sample rate, window size, frame rate, frames, colormap, smoothing, smoothing window, Image type "Concentric", Minimum distance, Prominence, window spacing, step, windows analyzed; no Threshold, Notes, Interpolate, Oversampling, Gaussian smoothing or Beat coloring.
