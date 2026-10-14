# Data Model: Interpolated Frames

No stored data is added. These are the values that exist while a job is created, and the rules between them.

*(Amended 2026-10-13: the interpolation function was removed; in-between frames are always blends.)*

## Interpolate

| | |
|-|-|
| Values | whole numbers 1 to 5 (default 1) |
| Where it lives | `MIN_INTERPOLATE`, `MAX_INTERPOLATE`, `DEFAULT_INTERPOLATE`, `check_interpolate` in `backend/app/services/frame_interpolation.py`; `INTERPOLATE_RANGE`, `validateInterpolate`, `formatInterpolate` in `frontend/src/utilities/validation.ts` |
| Refusal | not a whole number from 1 to 5 (including empty): `The interpolate value must be a whole number from 1 to 5.` |
| Label on the page | `1 (every frame drawn)`, `n (one frame in n drawn)` |

## Per-job values

| Name | Definition |
|------|------------|
| `count` | the number of frames of the job (unchanged) |
| `drawn` | `sorted(set(range(0, count, n)) | {count - 1})` for `n = interpolate` (empty for `count == 0`); in the user's counting from 1: 1, n + 1, 2n + 1 and so on, and the last frame |
| gap | a pair of neighboring drawn frames `(a, b)`, `a < b`, with the length `g = b - a` (n, or less at the end of the file); its in-between frames are `a + 1 .. b - 1` |
| position | for the in-between frame `i` of the gap `(a, b)`: `k = i - a`, the weight `w = k / g` |
| `earlier`, `later` | the pictures of the drawn frames `a` and `b`, read from their files and converted to RGB |
| in-between frame `i` | `Image.blend(earlier, later, w)`: the earlier picture with weight `1 - w` and the later with `w` |

## Rules

- The drawn frames are made exactly as at interpolate 1 (the smoothing, the Threshold, the colors, the Resolution, the Notes and the image type apply to them as before), so their files are byte-identical to those of interpolate 1.
- The frame count, the file names (`frame_NNNNNN.png`), the size (252 × 168) and the timing are those of interpolate 1.
- In-between frames are 8-bit RGB PNGs; drawn frames keep their kind (indexed-colour for Tiles at the original grid, true-color for the other Tiles and Blended frames, RGBA for the contour).
- At interpolate 1 nothing is interpolated.
- Between two identical drawn frames every in-between frame equals them.
- The in-between frames of different gaps do not depend on each other; they are made on a few threads (runs of consecutive gaps, each drawn frame read once per run) and are the same whatever the number of threads.

## Response

One new key: `interpolate` (the whole number used, 1 when not sent). The removed `interpolate_function` is not in the response.
