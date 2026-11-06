# Data Model: Decay Exp

Entities of [spec.md](spec.md). Everything not listed is as in [Decay](../027-decay-circles/data-model.md).

## Circle points (state)

- A `(7, 12)` array of floats, 0 to 64, one per cell; 0 before the first frame; recorded after each frame as a row of 84 in cell order (`(frames, 84)`), exactly as Decay.

## Tapered gain

| Name | Definition |
|------|------------|
| `g` | Decay's gain of a note in a frame: `24, 20, 16, 12` or `8` by rank (ties to the lower note; value 0 excluded) plus `8 × position` (position 0 to 1; 0 with no beat) |
| `t` | The taper of the frame: `8 + 0.01 × n`, `n` a whole number from 0 to 400 (see Taper) |
| `gain` | `g × e^(−g/t)`; 0 where `g` is 0 |

Examples with no beat at a taper of 8 (the first frame): 24 → 1.1949, 20 → 1.6417, 16 → 2.1654, 12 → 2.6776, 8 → 2.9430. With the full beat bonus the top note: 32 → 0.5861.

At a taper of 12: 24 → 3.248, 20 → 3.778, 16 → 4.218, 12 → 4.415, 8 → 4.107.

Added to the circle's points, then held between 0 and 64.

## Taper

| Name | Definition |
|------|------------|
| `n` | Whole number of steps from 0 to 400; the taper is `8 + 0.01 × n`, so exactly 8 at 0 and exactly 12 at 400 |
| `rising` | Whether the taper goes up (true at the start) or down |
| `circles` | The number of the 84 circles with more than 32 points at the end of the frame |

After every frame (from the points as recorded): if `circles > 10`, `rising` becomes false. If `rising`, `n` becomes `min(n + 1, 400)`. Otherwise `n` becomes `max(n − 1, 0)` and, when it is 0, `rising` becomes true again. The first frame has `n = 0`. The decay rate does not change this.

## Exponential loss

| Name | Definition |
|------|------------|
| `r(p)` | Points given to each neighbour per frame by a circle with `p` points before the step: `sin²(π/2 × p/64)` for `p > 0`, 0 for `p = 0` (revised 2026-11-06) |
| `give` | `min(p, 8 × frames × r(p))`, `frames` being the frames' worth of the step (the decay rate) |

Examples: `r(1)` = 0.0006, `r(8)` = 0.0381, `r(24)` = 0.3087, `r(32)` = 0.5, `r(48)` = 0.8536, `r(64)` = 1 (so a full circle gives 8 in all, a circle with 32 points 4).

## Decay step

As Decay: `give / 8` goes to each of the up to 8 neighbours that exist (no wrap), the rest is lost; all circles use the points before the step; the result is clipped to 0..64 and a circle under 0.01 points becomes 0. Steps are taken at the times `decay_rate`, `2 × decay_rate`, ... frames; frame `i` has the steps in `(i − 1, i]` (`steps_in_frame`).

## Validation rules

- `decay_rate`: a number 0.25 to 4 in steps of 0.25 (as Decay).
- `decay_low`, `decay_medium`, `decay_high`, `decay_saturated`: checked as always (0.5 to 3), no effect.
- Points given to `write_decay_frames`: `(frames, 84)`, 0 to 64 (as Decay).

## State transitions (one frame)

`points ← clip(points + arrange_notes(gains) × exp(−gains / taper), 0, 64)` with the taper of the frame, then `decay_exp_step` for each step in the frame, then record.
