# Research: Interpolated Resolution

> **Amended 2026-10-14 (feature 020, grouped settings).** The **Resolution** control is now called **Oversampling** on the page, in its info text, in its validation message (`The oversampling must be a whole number from 1 to 5.`, on the client and the server) and in the result summary, and it sits in the **Image smoothing** group with Interpolate, which is not shown for Circles. The request field is still `resolution` and nothing about the interpolation changed. Where this document says Resolution (the control, the slider, the message), read Oversampling; see `specs/020-grouped-settings-ui/`.

No `NEEDS CLARIFICATION` items remain in the spec. The method (`np.linspace` positions and `np.interp` over the smoothed note values) was given by the user; the points the spec left as assumptions (whole-number steps, a picture that keeps its size, the Threshold on the drawn values) are kept as written. The decisions below were checked with a throwaway prototype on a synthetic 1,800-frame file (84 notes, matplotlib 3.10.9), not assumed.

## Measurements from the prototype

| Question | Result |
|----------|--------|
| `np.interp` over every row, then every column, 300 frames at 5× (60 × 35 values per frame) | 0.03 s (about 1.5 µs a call); 1,800 frames about 0.2 s |
| The same with one `np.interp` call per axis over all frames (positions offset per frame) | 0.046 s for 1,800 frames, identical values (`allclose` at 1e-12); not needed |
| Resolution 1 | exactly the original values (`np.array_equal`), because `np.linspace(0, 11, 12)` is exactly the integers 0 to 11 |
| Corners, and the range of the values | the four corners are the original corners, and every new value is between the smallest and largest original value of the frame, at 5× |
| Tile edges in 252 × 168 pixels at `round(linspace(0, size, count + 1))` | 1×: 21 × 24 px; 2×: 10 or 11 px wide, 12 px tall; 3×: exactly 7 × 8 px; 4×: 5 or 6 px wide, 6 px tall; 5×: 4 or 5 px wide and 4 or 5 px tall |
| Tiles at 5× (2,100 tiles) as a true-color PNG | 0.86 ms a frame at compress level 1 (4.3 KB), 0.98 ms at level 6 (2.4 KB), including the pixel gather; today's palette PNG is about 1 KB |
| Contour at 1×, 3× and 5× (drawing only) | 9.3, 8.6 and 8.5 ms a frame: `contourf` does not get slower with a finer grid |

## Decision 1: One module for the setting and the interpolation

- **Decision**: A new module `app/services/resolution.py` holds `MIN_RESOLUTION = 1`, `MAX_RESOLUTION = 5`, `DEFAULT_RESOLUTION = 1`, `check_resolution(value)` (a whole number from 1 to 5, not a bool, otherwise `ValueError("The resolution must be a whole number from 1 to 5.")`) and `interpolate_grid(values, columns, rows, resolution)`. It is pure numpy, knows nothing about the note analysis, and takes the grid shape as arguments, like `image_types.py` and `contour.py`.
- **Rationale**: The setting, its check and the interpolation are one concept that the writers, the router and the tests all use. The other settings each have a check function in the module that owns them.
- **Alternatives considered**: Putting it in `frame_rendering.py` (already the place for smoothing and the threshold): that file is the shared pipeline, and this adds a testable unit that is better on its own.

## Decision 2: The interpolation is `np.interp` over every row, then over every column

- **Decision**: For values of shape `(frames, rows * columns)` and a resolution `r`, reshape to `(frames, rows, columns)`; `xs = np.linspace(0, columns - 1, columns * r)` and `ys = np.linspace(0, rows - 1, rows * r)`; for every frame and every original row, `np.interp(xs, np.arange(columns), row)` gives a row of `columns * r` values; then for every frame and every new column, `np.interp(ys, np.arange(rows), column)` gives a column of `rows * r` values. The result is `(frames, rows * r * columns * r)` in row-major order (row `y` of the new grid, column `x`). At `r = 1` the values are returned as a copy without calling `np.interp`.
- **Rationale**: This is the user's method literally, so a test can compare with `np.interp` directly. Linear interpolation along one axis and then the other (bilinear) keeps every new value inside the range of the four original values around it, keeps the corners, and is the same in either order. The measured cost is 0.2 s for 1,800 frames at 5×, small beside the job (about 1 s for tiles), so the plain loops are kept.
- **Alternatives considered**: One `np.interp` call per axis over all frames with offset positions, or an interpolation matrix built from `np.interp` of unit vectors: both measured at or below 0.05 s but obscure; they stay in reserve if the loops ever matter. `scipy.ndimage.zoom` or `scipy.interpolate`: other algorithms and positions than the one requested.

## Decision 3: The pipeline: interpolate after smoothing, before color and threshold

- **Decision**: In `write_frames`: smooth (unchanged) → `peak = smoothed.max()` over all 88 notes (unchanged) → `values = interpolate_grid(smoothed[:, :84], 12, 7, r)` → `hidden = values < threshold / 100 * peak` → for Tiles and Blended: `colors = colorize(values, colormap, columns*r*rows*r, peak)` and `colors[hidden] = 0`; for Contour: `values[hidden] = 0`. `colorize` gets an optional `peak` argument (default: the largest value in its input, as now), because the interpolated array no longer holds the four undrawn notes that count for the peak. A new `hidden_below(values, peak, threshold)` does the comparison for any grid; `hidden_notes` stays and gives the same result at 1×.
- **Rationale**: The spec says smoothing comes first and the Threshold applies to the values that are drawn. The peak is the same at every resolution (linear interpolation never exceeds the original maximum, and the corners/notes are kept), so the colors' scale and the threshold's reference do not change with the resolution. At 1× every number equals today's, so the output is identical (checked by the reference hashes).
- **Alternatives considered**: Hiding the original notes before interpolating (a hidden note would fade out around itself): the spec's other reading, rejected as the default because the Threshold would then not mean "values below this are not shown" at 2× and above. Interpolating the colors instead of the values: the user asked for values, and a color mix of two colormap entries is not a colormap color.

## Decision 4: Tile geometry at any grid size, with edges at the nearest pixel

- **Decision**: A function builds the pixel-to-tile index for a grid of `columns × rows` in `width × height` pixels with the tile edges at `np.rint(np.linspace(0, size, count + 1))`. At 1× this gives the 21 × 24 pixel tiles of today (the edges are exact multiples), so the index image is the same as `_TILE_INDEX_BYTES`. Tiles are written as a palette PNG when the grid has at most 256 tiles (1×, 84 tiles: exactly as today, level 6), and otherwise as a true-color PNG of `colors[i][index]` at compress level 6 (2× has 336 tiles, so every higher resolution is true color).
- **Rationale**: The picture keeps 252 × 168 (spec assumption), which only divides evenly at 1× and 3×; rounding edges gives tiles that differ by at most one pixel. A palette PNG is limited to 256 colors, so it cannot hold the 336 to 2,100 tile colors of a finer picture; level 6 costs about 0.1 ms a frame more than level 1 and makes files 45% smaller (2.4 against 4.3 KB at 5×).
- **Alternatives considered**: Growing the picture so that tiles stay 21 × 24 (252r × 168r): contradicts "smaller tiles" and the frame player's size. Choosing a palette PNG per frame when the frame happens to have 256 colors or fewer: files in one job would be of two kinds for no gain a viewer notices.

## Decision 5: The blend works on the generalized tile edges

- **Decision**: `image_types.py` gets `make_grid_blender(blend_width, columns, rows, width, height)`: the tile edges are the rounded ones of Decision 4, a pixel's own tile and the distances to its tile's start and end edge come from those edges, and the reach is `blend_width / 100 × (width / columns)` pixels (the mean tile width) in both directions. `axis_weights` is rewritten on top of an edge-based function with uniform edges, and `make_blender(blend_width, columns, rows, tile_width, tile_height)` calls `make_grid_blender` with `width = columns * tile_width`, so every existing caller, test and byte of 1× output stays the same.
- **Rationale**: FR-007: the blend width stays a share of a tile, so at 5× the reach is 25% of 4.2 px = 1.05 px and the fade is about one pixel wide at each edge. The two fades on opposite sides of the smallest tile (4 px) never meet (1.05 against half of 4). The cost of a blended frame is unchanged (the same arrays over the same 252 × 168 pixels, measured about 1.3 ms in feature 013).
- **Alternatives considered**: A fixed reach in pixels: the spec says it is a share of the tile. Not blending above some resolution: a surprise.

## Decision 6: Contour uses the finer grid with no change to its drawing

- **Decision**: `write_frames` passes `columns = 12r`, `rows = 7r` and the interpolated, threshold-zeroed values to `write_contour_frames`, which already takes the grid shape as arguments. The coordinates are `linspace(0, top, 12r)` by `linspace(0, top, 7r)` with `top` the frame's largest value (feature 015, as changed on 2026-10-12). No change to `contour.py` is needed.
- **Rationale**: The measurement shows the drawing cost does not depend on the grid size at these sizes (about 8.5 ms at 5×). The contour levels stay matplotlib's choice; a finer grid makes the contour smoother because more points follow the same shape.
- **Alternatives considered**: None needed.

## Decision 7: API and page

- **Decision**: The router gets the optional form field `resolution` with a parser like `_parse_smoothing_window` (not sent: 1; sent: text that is a whole number from 1 to 5, so `"3"` and `"3.0"` are accepted and `""`, `"abc"`, `"2.5"`, `"0"`, `"6"`, `"nan"` are refused with a 400 `The resolution must be a whole number from 1 to 5.`, before the file is read), passes it to `write_frames`, and reports `resolution` in the response. The frontend gets a slider (1 to 5, step 1, starting at 1) built like the other sliders, with the readout from a pure function (`1×`, `3× (36 × 21)`), a help text, a summary line, and the field in `api.ts`.
- **Rationale**: The same shape as every earlier setting, so the code and the tests follow patterns already in the project; the readout answers "what does 3 mean" with the grid size.
- **Alternatives considered**: A dropdown of the five sizes: the slider matches the other numeric settings and the spec says slider.

## Decision 8: Tests for resolution use no colormap names and no level counts

- **Decision**: The tests follow the rules of features 014 and 015: colormap names come from `colormap_names.py`, nothing counts contour levels, and the interpolation is tested against `np.interp` itself (equal within 1e-12) and against its defining properties (identity at 1×, corners, range, constants, monotone along a ramp, shape for every resolution). Rendering is tested by decoding the picture: the tile grid is read back by sampling the middle of every tile and counting the distinct column and row boundaries, and each tile's color is compared with the colormap's color for its interpolated value. The 1× output is compared with the reference hashes recorded before the change (tiles, blended, a smoothed and thresholded job, and contour).
- **Rationale**: The user will change the colormap list by hand, and the contour's levels are not ours; the properties above hold for any of them.
- **Alternatives considered**: Pixel-exact expectations for the fades at 2× and above: they would restate the implementation.
