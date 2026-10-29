# Data Model: Decay

Nothing is stored. These are the values the feature works with.

## Settings

| Name | Type | Rule | Default |
|------|------|------|---------|
| `image_type` | text | now also `decay` | `tiles` |
| `decay_rate` | whole number | 1 to 10: the number of frames between decay steps | 5 |

All other settings are as for Concentric: colormap, analysis settings, `smoothing`, `smoothing_window`, `peak_distance`, `peak_prominence` and `note_layout` apply; `threshold`, `note_count`, `resolution`, `interpolate`, `gaussian`, `blend_width`, `beat_coloring` and the circle fields are checked and ignored.

## Per frame (inputs)

| Value | Shape | Meaning |
|-------|-------|---------|
| `values` | `(frames, ≥84)` | the smoothed note values in note order; the first 84 count |
| `beat` | `None` or `(frames,)` 0..1 | the frame's position in the local peak (0 when `None`) |

## Gain (per frame, per note)

Rank the 84 values by value, highest first, ties to the lower note, notes with value 0 left out. The first five ranks gain `24, 20, 16, 12, 8`, plus `8 × position`. Every other note gains 0. The result is reordered from note order to cell order (`arrange_notes`).

## Points (per frame, per cell)

A float from 0 to 64, kept from frame to frame, 0 before the first frame.

For frame `i` (from 1):

1. `points = clip(points + gain, 0, 64)`
2. if `i % decay_rate == 0`: `give = min(points, 16)`, `share = give / 16`, `points = clip(points − give + 2 × Σ neighbours' share, 0, 64)`, with the neighbours the up to 8 cells around (no wrap); then any cell with less than 0.01 points is set to 0
3. the frame is drawn from `points`.

State transitions: only forward, one frame at a time; nothing is kept between jobs.

## Neighbours

| Cell | Neighbours | Of the 16 lost: sent / vanished |
|------|-----------|---------------------------------|
| interior | 8 | 16 / 0 |
| edge | 5 | 10 / 6 |
| corner | 3 | 6 / 10 |

(The grid is 12 columns × 7 rows, so there are 50 interior cells, 30 edge cells and 4 corners.)

## Circle (per frame, per cell)

| Property | Rule |
|----------|------|
| center | the center of the cell, as in Concentric |
| radius | `R × (1/12 + 11/12 × min(points, 24) / 24)`, `R` = half the narrower cell side (25 px) |
| color of ring `k` (1 at the center to 12 at the edge) | the colormap's table entry at `rint((b − s × (k − 1) / 11) × 255)`, with `b = min(points, 32) / 32` and `s = max(0, points − 32) / 32`: every ring at `b` up to 32 points (a flat disc), ring 1 the last color and ring 12 the first at 64 points |
| rings | ring `k` covers the radii `(k − 1) / 12` to `k / 12` of the full radius, as in Concentric; the edges between rings are smooth |
| edge | one pixel wide, antialiased |
| background | the colormap's middle color (table row 128) |

## Invariants

- 0 ≤ points ≤ 64 after every step.
- A decay step never increases the sum of all points.
- Deterministic: the same inputs give the same points and frames.
