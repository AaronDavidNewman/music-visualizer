# Data Model: Peak Rings

`F` is the number of frames, `K = 12` the rings.

## Beat (existing)

`beat`: `(F,)` float64 from 0 to 1, the position of the middle of each frame in the local energy peak (0 far from a peak or between peaks, 1 at the top of a peak); `None` when not measured. Checked with `colormaps.check_beat(beat, F)`.

## Distance from the peak

`peak_distances(beat)`: `(F,)` float64, `1 - beat`; 0 at the top of a peak, 1 far from one.

## Stretched distance (third change, 2026-11-10)

`beat_distances(beat)`: `(F,)` float64 from 0 to 1. With `inside = beat > 0` (the frames inside a peak): if there is none, `1 - beat`; otherwise `low = percentile(beat[inside], 1)` (`PEAK_BOTTOM_PERCENTILE`) and `high = max(beat[inside])`; if `high - low <= 0`, `1 - beat`; else `clip((high - beat) / (high - low), 0, 1)`. So the highest position is 0 (the first color), the 1st percentile of the positions inside the peaks and everything below it (including a frame outside every peak, position 0) is 1 (the last color). On real music the positions inside the peaks run from about 0.55 to 1, so without this the distance only reached 0.45.

## Ring levels

`ring_levels(beat)`: `(F, 12)` float64 from 0 to 1. With `d = beat_distances(beat)` (the stretched distance, above) and `d[i] = 1` for `i < 0`:

- `levels[t, 0] = d[t]` (ring 1, the center: the present)
- `levels[t, k - 1] = (d[t - (2k - 3)] + d[t - (2k - 2)]) / 2` for `k = 2 .. 12` (ring `k`: the average of the 2 frames just before the previous ring's)

So ring 2 is frames `t-1` and `t-2`, ring 12 frames `t-21` and `t-22`. Empty `beat` (0 frames) gives a `(0, 12)` array.

## Ring colors

`ring_colors_of(levels, colormap)` (name as built): `(F, 12, 3)` uint8: `lookup_table(colormap)[rint(level x 255)]`: level 0 is the first color of the table, level 1 the last.

## Geometry (drawing only)

For a picture `w x h` (`R, full = ring_geometry(w, h)` as in feature 035):

- center: `(w / 2, h / 2)`
- `radius = min(70 x min(w, h) / 400, R - full - 1)` (70.0 on 600 x 400)
- `ring_width = radius / 12` (5.83 on 600 x 400), ring 1 at the center
- a pixel at distance `d` from the center: outer coverage `clip(radius - d + 0.5, 0, 1)`; ring shares from the shared ring-weight rule: the ring it is in (`clip(ceil(d / ring_width) - 1, 0, 11)`), less the shares of the ring inside and outside that reach into the pixel (0.5 at an edge between two rings, falling to 0 half a pixel away), the outside of the circle counting with the last ring

## State

Nothing is kept between frames beyond the beat array: every frame's levels come from the beat of the frames before it, computed for all frames at once.
