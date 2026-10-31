# Data Model: Contour Beat Wave

Nothing is stored. These are the values the feature works with.

## Settings

| Name | Type | Rule | Default |
|------|------|------|---------|
| `beat_coloring` | bool | as before (`true`, `false`, `1`, `0`); for `contour` it turns the beat wave on | off |
| `wave_count` | whole number | 2 to 10: the waves of the pattern across the largest dimension; used by Contour with `beat_coloring` on, checked for every type | 4 |
| `peak_distance`, `peak_prominence` | numbers | as in feature 024; used by Contour when `beat_coloring` is on | 100, 50 |

All other settings are as for Contour today (`threshold`, `note_count`, `resolution`, `interpolate`, `gaussian`, colormap, analysis and smoothing settings apply); `note_layout` and the circle fields are checked and ignored as before.

## Per frame (inputs)

| Value | Shape | Meaning |
|-------|-------|---------|
| `values` | `(frames, rows × columns)` | the grid of note values of every frame (`rows = 7r`, `columns = 12r` at oversampling `r`), notes below the threshold already 0 |
| `beat` | `None` or `(frames,)` 0..1 | `k`: the frame's position in the local peak (0 at the minimum, 1 at the maximum); `None` or 0 means no wave |

## Pattern (per grid size and wave count)

A float64 array of shape `(rows, columns)`, numbers from 0 to 1:

```text
distance[y, x] = hypot(x − (columns − 1) / 2, y − (rows − 1) / 2)
largest        = max(rows, columns)
pattern[y, x]  = (sin(waves × 2π × sqrt(distance[y, x] / largest)) + 1) / 2
```

- 0.5 at distance 0 (the center of an odd-sized axis), symmetric left–right and top–bottom; the rings are close together near the center and wider towards the edge.
- 1 at `distance = largest ÷ (16 × waves²) × (4n + 1)²`, 0 at `largest ÷ (16 × waves²) × (4n + 3)²` (the sine runs over `sqrt(distance ÷ largest)`, so the rings get wider towards the outside).

## Modifier (per frame)

`modifier = 1 − pattern × sin(π × k)`, from `1 − sin(π × k)` (where the pattern is 1) to 1 (where it is 0). All 1 at `k = 0`, deepest at `k = 0.5` (`1 − pattern`), and all but exactly 1 at `k = 1`; the same at `k` and at `1 − k`.

## The frame that is drawn

1. `Z` = the frame's grid, rows reversed (as today), smoothed in place (as today).
2. if `beat` is given and `k > 0`: `Z = Z × modifier`.
3. if `Z.min() == Z.max()`: the frame is one flat color, the colormap's color at that value on the scale from 0 to `top`; else `contourf` with 12 levels from `Z.min()` to `Z.max()`, color scale `vmin = 0`, `vmax = top`, with `top` the largest value of the unmodified frame.
4. a frame whose unmodified values are all equal (or a silent file) is flat as today, before any of this.

## Invariants

- `0 ≤ pattern ≤ 1`, `1 − sin(π × k) ≤ modifier ≤ 1`, so the wave never makes a value negative or larger.
- At `k = 0`, with the checkbox off, with no beat, and for every other image type, the frames are byte-identical to before.
- Deterministic.
