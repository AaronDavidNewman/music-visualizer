# Data Model: Interpolated Resolution

No stored data is added. These are the values that exist while a job is created, and the rules between them.

## Resolution

| | |
|-|-|
| Values | whole numbers 1, 2, 3, 4, 5 (default 1) |
| Where it lives | `MIN_RESOLUTION`, `MAX_RESOLUTION`, `DEFAULT_RESOLUTION`, `check_resolution` in `backend/app/services/resolution.py`; `RESOLUTION_RANGE`, `DEFAULT_RESOLUTION`, `validateResolution`, `formatResolution` in `frontend/src/utilities/validation.ts` |
| Refusal | not a whole number from 1 to 5, including empty: `The resolution must be a whole number from 1 to 5.` |
| Grid it gives | `12 r` columns by `7 r` rows: 12 × 7, 24 × 14, 36 × 21, 48 × 28, 60 × 35 |

## Per-job values

| Name | Definition |
|------|------------|
| `S` | the smoothed note array of the file, `(frames, 88)` (unchanged) |
| `peak` | `S.max()` over all 88 notes (unchanged; the same at every resolution) |
| `shown` | `S[:, :84]`, the original grid of each frame: note `n` at row `n // 12`, column `n % 12` |
| `xs`, `ys` | `np.linspace(0, 11, 12 r)` and `np.linspace(0, 6, 7 r)`: positions over the original columns and rows, first to last |
| `values` | `interpolate_grid(shown, 12, 7, r)`, `(frames, 84 r²)`: for each frame, `np.interp(xs, arange(12), row)` over every original row, then `np.interp(ys, arange(7), column)` over every new column; row-major (new row `y`, new column `x` at index `y * 12 r + x`). At `r = 1` equal to `shown` |
| `hidden` | `values < threshold / 100 * peak`, same shape as `values` (`hidden_notes` gives the same mask at 1×) |
| Tile colors | `colorize(values, colormap, 84 r², peak)`, then `0` (black) where `hidden`; Tiles and Blended tiles only |
| Contour values | `values` with `0` where `hidden`; Contour only |
| Tile edges | `np.rint(np.linspace(0, 252, 12 r + 1))` across and `np.rint(np.linspace(0, 168, 7 r + 1))` down; at 1× the multiples of 21 and 24 |
| Blend reach | `blend_width / 100 × (252 / (12 r))` pixels, both directions |

## Invariants of the interpolation

- At `r = 1` the result is exactly the input.
- The four corners of the new grid are the four corners of the original grid.
- Every new value is between the smallest and the largest original value of its frame (a convex combination of original values), so `values.max()` of a frame never exceeds the largest `shown` value, and `peak` is unchanged.
- A frame whose original values are all equal gives a new grid of the same value.
- Along any row or column that lies between two original notes, the new values are monotone from one to the other.

## Rules

- Smoothing and its window come before the interpolation; the Threshold and the colors come after it, on the values that are drawn.
- Tiles are written as a palette PNG when the grid has at most 256 tiles (1× only), otherwise as a true-color PNG. Blended frames are true-color PNGs at every resolution. Contour frames are written by matplotlib (RGBA), or as a flat RGB picture for a frame without a contour.
- The picture is 252 × 168 pixels, the frame count, the timing and the file names are those of the job at 1×.

## Response

One new key: `resolution` (the whole number used, 1 when not sent).
