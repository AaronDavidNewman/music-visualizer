# Research: Peak Rings

No `NEEDS CLARIFICATION` remains (the three questions of the specification were answered on 2026-11-09: history in time, 12 rings, peak at the start of the colormap). The decisions below settle what the specification left to the design.

## Decision 1: The levels of the rings

- **Decision**: with `d[f] = 1 - beat[f]` the distance of frame `f` from the local peak (`beat[f]` is the position in the local peak, 0 to 1, the same array that charges the circles) and `t` the current frame, ring 1 (the center) has level `d[t]` and ring `k` from 2 has the **mean of `d[t - (2k - 3)]` and `d[t - (2k - 2)]`**: ring 2 is frames `t-1, t-2`, ring 3 `t-3, t-4`, ..., ring 12 `t-21, t-22`. A frame index below 0 counts as **far from a peak (`d = 1`)**.
- **Rationale**: the user's "each level will be an average of the previous 2 samples, to the outside of the circle" read as a history, newest inside, answered "history in time" when asked; the moments before the file starts have no beat, and "far from a peak" is what position 0 means everywhere else in the project (no beat gives position 0).
- **Alternatives considered**: each ring the average of the two rings just inside it (a blur of the center; offered, not chosen); repeating the first frame before the start (would show a peak that never was).

## Decision 8 (third change, 2026-11-10): the distance is stretched over the range of the beat

- **Decision**: the user saw the rings only reach the middle color. Measured on `sonata.wav`, `female-voice.wav` and `fotr-intro1-echo.wav` at 10 frames a second: the position inside the peaks has a median of 0.71 to 0.76 and its 1st percentile is 0.52 to 0.58 (a handful of frames go lower, down to 0.02 to 0.14), so `1 - position` is almost always 0 to 0.45 and the colormap is used to its middle. The distance is now stretched: the highest position inside the peaks is 0 and the **1st percentile** of the positions inside the peaks is 1 (frames outside every peak, and below the bottom, are 1). Implemented in `beat_distances`; `peak_distances` stays the plain `1 - position`.
- **Rationale**: a plain minimum and maximum would not do (one outlier frame at 0.02 would keep the scale at 0.98 and leave the rings in the first half again); a low percentile ignores such frames. The same idea as the rest of the project, which scales colors by the share of the largest value of the whole file.
- **Alternatives considered**: min and max (squashed by outliers, as measured); the 5th percentile (more frames held at the last color, a harder contrast: the constant `PEAK_BOTTOM_PERCENTILE` is one line to change); stretching each ring separately (would break the link between the rings, which are averages of the same distances).

## Decision 2: Color

- **Decision**: a ring's color is the colormap table row `rint(level x 255)` (`lookup_table(colormap)`): level 0 (at the peak) is the first color, level 1 (far) the last, in between at the same share. The user chose "peak = start (left)".
- **Rationale**: the same table and rounding that `decay.ring_colors` uses (`rint(position x (COLORMAP_STEPS - 1))`); one rule for both kinds of rings.

## Decision 3: The geometry of the target

- **Decision**: centered at the middle of the picture; **radius 70 pixels on 600 x 400** (140 across), scaled with the picture as `70 x min(width, height) / 400`, and never more than `R - full - 1` (inside the ring of letters, whose free middle on 600 x 400 is `R - full = 111.9` pixels in radius, 224 across); 12 rings of equal width `radius / 12` (5.83 pixels), ring 1 at the center. The edges are drawn as the circles' rings are: coverage `clip(radius - distance + 0.5, 0, 1)` at the outer edge and the 0.5-pixel smooth blend between two rings.
- **Rationale**: the user said "about 140 px"; the proportional scale keeps the look on other sizes; the clamp only matters for tiny pictures.
- **Alternatives considered**: 140 pixels at every size (overlaps the letters on small pictures); a radius from the ring radius (not what the user said).

## Decision 4: One ring-weight helper

- **Decision**: the formula that turns a pixel's distance from a center into the shares of the 12 rings (the ring it is in, less the shares of the ring inside and outside that reach into the pixel) is moved out of `_geometry` into `_ring_weights(distance, ring_width)` and used by both the circles and the target.
- **Rationale**: one rule, already tested (the ring-weight tests of feature 035 keep running on it); a copy would drift. It is in this module, so no other type is touched.
- **Alternatives considered**: a second copy (the one I made from `decay._geometry` already is a copy).

## Decision 5: The beat reaches the picture through an optional argument

- **Decision**: `write_chromatic_frames(points, colormap, directory, width, height, beat=None)`; with `beat=None` no rings are drawn, with a `(frames,)` array of 0 to 1 (checked as `colormaps.check_beat`, one number for each row of `points`) the rings are drawn. `frame_rendering.write_frames` passes the `beat` it already has; the job always measures it for this type, so the API always shows the rings.
- **Rationale**: every existing call and test keeps working unchanged; no request or response field.
- **Alternatives considered**: `None` meaning position 0 everywhere (every library call without a beat would grow rings of the last color: changes all earlier picture tests for nothing).

## Decision 6: Drawing order and cost

- **Decision**: per frame, the picture is the background, then the target (a 140 x 140 box: `weights @ ring colors`, blended with the outer coverage), then the 12 circles as before; the target's pixel box, distances and weights are worked out once per frame size (cached with the rest of the geometry); the 12 ring colors of every frame are `(frames, 12, 3)` from the levels, computed once.
- **Rationale**: the middle of the ring is empty, so the target and the circles never overlap (checked by a test); one box per frame is cheap.

**Revised 2026-11-10 (second note)**: Chromatic Decay has its own constant `chromatic_decay.PRETEND_NEIGHBORS = 6`; `decay.NEIGHBOURS` is back to 8 for Decay and Decay Exp. Read `PRETEND_NEIGHBORS` where this document says `NEIGHBOURS` for Chromatic Decay.

## Decision 7: The `NEIGHBOURS` constant is now 6

- **Decision**: the user changed `decay.NEIGHBOURS` from 8 to 6 (uncommitted, announced "BTW"). Facts found: about 25 tests of Decay and Decay Exp fail (their formulas and the invariant "the total never grows" assume 8: with 6, `_spread` gives each of up to 8 neighbour cells `give / 6`, so an interior circle hands on 8/6 of what it gives and points appear from nothing); and Chromatic Decay, which reads the constant, now gives away `6 x frames x loss` and sends `1/6` to each receiver (the per-receiver amount is unchanged and 4/6 is lost instead of 6/8). **This feature changes nothing about it.** Task T002 makes the tests and documents of feature 035 follow the constant (so they say `NEIGHBOURS` and `(NEIGHBOURS - 2) / NEIGHBOURS`, and pass for 6 or 8); the failures of Decay and Decay Exp are listed in the report to the user and left alone, because whether 6 is intended for the grid types (where there are 8 neighbour cells) is the user's decision.
- **Rationale**: the user's change; the grid tests encode the user's earlier specifications, and altering either side silently would hide a possible mistake.
- **Alternatives considered**: reverting the constant (not mine to do); updating the Decay tests to 6 (would bless the point creation).

## Open questions

None.
