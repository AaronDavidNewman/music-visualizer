# Data Model: Chromatic Wireframe

`F` is the number of frames, `W x H` the picture (600 x 400), `L = 12` the letters.

## Input (existing)

- `points` `(F, 12)` float64 from `chromatic_decay.circle_points`: column `n` is letter `n` (A = 0 .. G# = 11), values 0 to 64.
- `beat` `None` or `(F,)` from 0 to 1 (the place of each frame in the local peak; `LocalPeaks.frame_positions`).
- `colormap` name; the background is **black** (revised 2026-11-12: first the colormap's first row, then black at the user's request; not the middle row of the other types).

## Constants

| Name | Value | Meaning |
|------|-------|---------|
| `MARGIN` | 10 | px left, right, top and bottom |
| `AMPLITUDE_SHARE` | 1/5 | of the height: the highest swing of a full circle (`A`) |
| `STEP` | `4 x H / 400` | px a line is higher than the one in front of it |
| `DEPTH_SHRINK` | 0.25 | the oldest line's scale is `1 - 0.25` |
| `SAMPLES_PER_PIXEL` | 2 | vertices per pixel along a band |
| `LINE_WIDTH` | `1.5 x H / 400`, at least 1 | px |
| `SUPERSAMPLE` | 3 | the canvas is drawn this much larger and reduced |

> **Revised 2026-11-12**: the line is the **sum of the 12 letters' sines over the whole width** (one function, no jump), not 12 pieces joined. The "Band" and "Line" sections below are replaced by the next section; the rest holds.

## The line as one function (current)

`span = W - 2 x MARGIN`, `xmax = span / 12`, `n = ceil(SAMPLES_PER_PIXEL x span) + 1` samples at `u_i = i x span / (n - 1)` pixels from the left of the plot, `start_b = b x xmax`.

- `angle[b, i] = 2 pi x (p_b / (64 / 4)) x u_i / span + 2 pi x start_b / span`: the **frequency** comes from the points (`p / 16` turns across the whole width, `CYCLES_AT_FULL_POINTS = 4` turns at 64 points, none at 0), the **phase** is that of the start (pi/2 a quarter of the way along). `line_angles` -> `(12, n)`.
- `S[i] = 1 / 12 x sum over b of (r_b / full) x sin(angle[b, i]) squared` (`line_sums`, 0 to 1), `r_b = circle_radii(p_b)`, `full = ring_geometry(W, H)[1]`.
- `X[i] = MARGIN + u_i`; `Z[i] = A x clip((S[i] - FLOOR_SHARE) / (CEILING_SHARE - FLOOR_SHARE), 0, 1)`, `A = AMPLITUDE_SHARE x H` (two fifths of the height), `FLOOR_SHARE = 0.05`, `CEILING_SHARE = 0.8`. `line_heights` -> `(X, Z)`, each `(n,)`, `0 <= Z <= A`.
- `0 <= Z <= A` by the clip; the line moves by at most `A / (12 x (CEILING_SHARE - FLOOR_SHARE)) x sum((r_b / full) x 2 pi x (p_b / 16) / span)` a pixel. 12 letters with the same points have the same frequency and amplitude and phases `2 pi b / 12`, and the sines squared of those add up to 6 whatever the point: `S` is a constant (half the radius share), so equal letters, silent ones included, make a flat line. Real music makes `S` of about 0.28 to 0.78.

## Band (superseded)

`plot_width = W - 2 x MARGIN`; `xmax = plot_width / 12`. Band `b` covers `[MARGIN + b x xmax, MARGIN + (b + 1) x xmax]`; `x` runs from 0 to `xmax` inclusive in it, `n = ceil(xmax x SAMPLES_PER_PIXEL) + 1` samples.

## Line (of one frame)

`line_heights(points_row, W, H)` -> `(X, Z)`, two arrays of `12 x n` floats:

- `X[b, i] = MARGIN + b x xmax + x_i`, `x_i = i x xmax / (n - 1)`.
- `angle[b, i] = (p_b x 2 pi + x_i) / (64 + xmax)` (**x added**).
- `Z[b, i] = A x (r_b / full) x sin(angle[b, i])` with `A = AMPLITUDE_SHARE x H`, `r_b = circle_radii(p_b)`, `full = ring_geometry(W, H)[1]`; positive is up.
- The last sample of a band and the first of the next have the same `X`: a vertical segment between them.

`Z` stays within `[-A, A]` because `r / full <= 1`.

## Geometry of the view

- `base_0 = H - MARGIN` (a line is never under its base); `base_k = base_0 - k x STEP`.
- `N = floor((base_0 - MARGIN - A x (1 - DEPTH_SHRINK)) / STEP) + 1` lines (66 on 600 x 400, 61 on 300 x 200): as many as fill the picture up to the top margin, at least 1 (`line_geometry(W, H)` -> `(N, base_0, step)`; a picture too small for `N >= 1` raises `ValueError`).
- `s_k = 1 - DEPTH_SHRINK x k / (N - 1)`, 1 when `N = 1`.
- Screen point of the line at depth `k`: `x_s = W/2 + (X - W/2) x s_k`, `y_s = base_k - Z x s_k`.

## Colors

`line_colors(beat, colormap)` -> `(F, 3)` uint8: `table[rint((1 - beat_distances(beat)) x 255)]`; `beat=None` -> every row is `table[0]`.

## Picture of frame `t`

Lines for `k = 0 .. min(N - 1, t)` (frame `t - k`, depth `k`), drawn for `k` from the largest to 0: fill the polygon (line + bottom corners) with the background, stroke the line in `colors[t - k]`. Result: `(H, W, 3)` uint8 after the 3x reduction.

## State and validation

No state across frames beyond the input arrays (every picture is drawn independently from `points` and `colors`). `write_wireframe_frames` checks before writing anything: `points` is `(F, 12)` with values in 0..64 (as `chromatic_decay._check_points`), `beat` is `None` or `(F,)` in 0..1, the colormap name, the size two whole numbers large enough for one line.
