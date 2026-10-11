# Data Model: Image Type (Blended Tiles)

Only what changes from the frame images of the earlier features is listed.

## Constants

| Name | Value | Where | Meaning |
|------|-------|-------|---------|
| `IMAGE_TYPES` | `("tiles", "blended")` | `image_types.py` | The offered image types, exact lowercase |
| `DEFAULT_IMAGE_TYPE` | `"tiles"` | `image_types.py` | Used when none is given |
| `MIN_BLEND_WIDTH` / `MAX_BLEND_WIDTH` | 10 / 25 | `image_types.py` | Allowed blend width, percent of the tile width |
| `DEFAULT_BLEND_WIDTH` | 25 | `image_types.py` | Used when none is given |

Frontend: `IMAGE_TYPES = [{ value: "tiles", label: "Tiles" }, { value: "blended", label: "Blended tiles" }]`, `DEFAULT_IMAGE_TYPE = "tiles"`, `BLEND_WIDTH_RANGE = { min: 10, max: 25, step: 1 }`, `DEFAULT_BLEND_WIDTH = 25` in `validation.ts`.

## Geometry (unchanged)

12 columns × 7 rows of tiles, each 21 × 24 pixels; picture 252 × 168. Tile `(row, column)` is note `12·row + column`; only the 84 drawn notes are tiles. Inner edges: vertical edges at `x = 21·k` for `k = 1 … 11`, horizontal edges at `y = 24·k` for `k = 1 … 6`. The picture's border is not an inner edge.

## Blend width and reach

`B = blend width / 100 × 21` pixels, the reach on each side of an inner edge, the same in both directions.

| Blend width | 10 | 15 | 20 | 25 |
|-------------|----|----|----|----|
| `B` (pixels) | 2.1 | 3.15 | 4.2 | 5.25 |
| Total band across an edge (2·B) | 4.2 | 6.3 | 8.4 | 10.5 |
| Standard deviation of the feather (σ = B / 4) | 0.525 | 0.79 | 1.05 | 1.31 |

Because `2B ≤ 10.5` is less than both tile dimensions, the bands of two opposite edges of a tile never meet: at least half of every tile's width and height is flat color, and only the nearest edge matters for any pixel.

## Weights along one axis

For a pixel with center `u = index + 0.5` on an axis with tile size `T` (21 or 24), let `tile = floor(index / T)`, `d_before = u − tile·T` (distance to the edge at the tile's start) and `d_after = (tile+1)·T − u` (distance to the edge at its end).

- If `tile > 0` and `d_before < B`: neighbor = `tile − 1`, own weight `a = F(d_before)`.
- Else if `tile < last` and `d_after < B`: neighbor = `tile + 1`, own weight `a = F(d_after)`.
- Else: neighbor = `tile`, own weight `a = 1`.

`F` is the Gaussian feather: a Gaussian-blurred step edge, cut off at the reach `B` and renormalised, with `σ = B / 4`:

```
F(d) = ( Φ(4d / B) − Φ(−4) ) / ( 1 − 2·Φ(−4) )        Φ = the standard normal cumulative distribution
```

(Changed on 2026-10-10 from the straight ramp `0.5 + d / (2B)`, which looked too blurry on real frames.)

The neighbor's weight is `1 − a`. At the edge itself `a` would be 0.5; the two pixels beside an edge have `d = 0.5` and the average of their weights is exactly 0.5 (the weight is 0.5 + something for one pixel and 0.5 − the same for the other). `F` rises from 0.5 at the edge to exactly 1 at `d = B`, steeply near the edge and flattening toward the reach, so the fade is continuous, the edge itself stays sharper than with a straight ramp, and only the tails are soft. These arrays depend only on the blend width.

## Pixel color

With `C[r, c]` the finished color of the tile at row `r`, column `c`, and for pixel `(x, y)` the column pair `(c, c')` with own weight `a_x` and the row pair `(r, r')` with own weight `a_y`:

```
color = a_y·a_x·C[r, c] + a_y·(1 − a_x)·C[r, c'] + (1 − a_y)·a_x·C[r', c] + (1 − a_y)·(1 − a_x)·C[r', c']
```

per channel, rounded to the nearest 8-bit value (halves to even). Properties: the four weights add up to 1 (a convex combination, so a channel never leaves the range of the colors mixed); outside every band `a_x = a_y = 1` and the pixel is exactly `C[r, c]`; if all four colors are equal the result is that color; at a corner of four tiles the weights are 25% each (the average of the four pixels around it); a black tile is just a tile whose color is `(0, 0, 0)`.

## Examples

Two tiles side by side, left `(200, 0, 0)` and right `(0, 100, 0)`, blend width 25 (`B = 5.25`), along one row: pixels more than 5.25 from the edge are exactly `(200, 0, 0)` / `(0, 100, 0)`; the two pixels beside the edge each have own weight `F(0.5) = Φ(0.381) = 0.648`, giving `(129.6, 35.2, 0)` on the left and `(70.4, 64.8, 0)` on the right before rounding (`(130, 35, 0)` and `(70, 65, 0)` as 8-bit colors); their average is `(100, 50, 0)`, the even mix. Three and a half pixels from the edge the neighbor's weight is already below 0.4 percent (a straight ramp would still be about 17 percent).

## Frame files

| Image type | File | Format |
|-----------|------|--------|
| `tiles` | `frame_000000.png` … | Indexed-colour PNG, at most 84 palette entries, compression level 6 (unchanged) |
| `blended` | `frame_000000.png` … | RGB PNG, 8 bits per channel, compression level 1 |

Both are 252 × 168 pixels and are served the same way (`image/png`, same cache header).

## API and page

Request fields `image_type` (`tiles` or `blended`, default `tiles`) and `blend_width` (number 10 to 25, default 25); response fields `image_type` and `blend_width` (always both). Page: `JobSettings.imageType: "tiles" | "blended"`, `JobSettings.blendWidth: number`, `JobResult.image_type`, `JobResult.blend_width`; readout `n% of a tile`; summary `Image type: Tiles | Blended tiles`, and `Blend width: n%` for blended.
