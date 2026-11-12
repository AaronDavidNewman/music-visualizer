# Research: Rhythm Circles

No `NEEDS CLARIFICATION` remains (the three questions of the specification were answered on 2026-11-11: a notch of 1/8 on every circle, each ring its own color with the notch at the opposite end of the colormap, the rates of change per second turning at that many revolutions per minute). The decisions below settle what the specification left to the design.

## Decision 1: The samples are the peaks, and the tempo is the rate of a peak

- **Decision**: with `LocalPeaks` (`peaks`, each with `sample` and `rate`) and the file's sample rate, the **time of peak `i`** is `t_i = sample_i / file_rate` seconds and its **tempo** is `rate_i` beats per minute (60 times the sample rate over the samples since the previous peak; 60 for the first peak): the measurement already computes it. The tempo at a moment is the rate of the latest peak at or before it (`LocalPeaks.rate_at`); before the first peak, and with no peaks, it is `DEFAULT_RATE` (60).
- **Rationale**: it is "the current rate of time between local peaks" of the user's description, and the existing definition of the rate for the beat; the "samples" of "the difference in the tempo divided by the time between the samples" are then the peaks, the "periods" the intervals between them.
- **Alternatives considered**: the tempo re-measured at every frame from the time since the last peak (a number that changes continuously and has no beats to compare); the interpolated rate (the measurement deliberately does not interpolate it).

## Decision 2: The eight series, per peak

- **Decision** (all per peak `i`, in revolutions per minute, `tempo` in beats per minute; the circles as **revised by the user on 2026-11-11**, three times, see the spec):
  - `tempo[i] = rate_i`; `agg_n[i] = aggregate(tempo[max(0, i - n + 1) .. i], tempo[i])` for `n` = 2, 4 and 8 (of those that exist while there are fewer than `n`), where `aggregate(window, current)` is `mean(window)` or `max(window)`, **whichever is closer to `current`** (the max when equally close: `abs(mean - current) < abs(max - current)` takes the mean)
  - the rate of change of a level `x` (the tempo, `agg2`, `agg4`, `agg8`): `(x[i] - x[i - 1]) / (t_i - t_{i-1})` for `i >= 1`, else 0 (per second)
  - the columns, **outer to inner**: `agg8`, its change, `agg4`, its change, `agg2`, its change, `tempo`, its change (the longest aggregation outermost)
- **Rationale**: the user's fourth revision: for the aggregated samples, "instead of always taking the fastest of the previous values, choose either the average or the fastest, whichever is closest to the current tempo". The current tempo is the one of the peak itself, which is one of the values of its window, so the choice is made against the tempo of the peak the layer is being worked out for. The fastest is the highest rate, the shortest interval between peaks, the one closest to the minimum distance; the user's reason for it (third revision) is that peaks are sometimes multiples of the beat. A tempo that is the fastest of its window is its own aggregate (distance 0), a tempo that has fallen is followed by the average (which is nearer to it than the old fastest), and a window with a very fast peak and a tempo near it takes the fastest. The tie (equally close) is not decided by the user: the fastest, which is what the layers took in the version before. The rate of change of an aggregate is taken exactly as the one of the tempo. The scale (per second, taken as revolutions per minute) was chosen by the user. Each rate circle stays just inside the level it measures.
- **Alternatives considered**: the first version of the feature (a secondary rate of change and averages over 2, 4 and 8); the version with the mean only; the version with the fastest only (third revision); the average on a tie; the median of the window; comparing with the tempo before the current peak (the user said "the current tempo"); reversing every circle, so that a rate of change would be outside its level; a mode setting for average, fastest or nearest (it would add a request field; the user asked for the nearest only); per minute (the user chose per second).

## Decision 3: Speeds are steps, angles are their running total

- **Decision**: the eight speeds in revolutions per minute are the series values from peak `i` until peak `i + 1`; before the first peak they are `[60, 0, 60, 0, 60, 0, 60, 0]` (the defaults: tempo and aggregated tempos 60, no change). The angle of circle `c` at time `t` (in **turns**) is `integral over [0, t] of speed_c(u) / 60 du`: piecewise linear in `t` with its slope changing at each peak, computed with the cumulative turns at the breakpoints `[0, t_0, t_1, ...]` and one `searchsorted` for all frames. Frames are at the middle of each frame, `(f + 0.5) / frame_rate` (as `frame_positions`). The angle is kept unwrapped (it can be large); the drawing uses it modulo 1.
- **Rationale**: "the circles rotate ... at the tempo rate"; the running total is the only way a circle whose speed changes can turn smoothly (feature spec FR-007); at 120 beats per minute the tempo circle advances 720 degrees a second, 24 degrees a frame at 30 frames a second.
- **Alternatives considered**: an angle that is `speed x t` (jumps whenever the speed changes); the angle updated per frame by `speed x dt` (the same up to the frame's own rounding at a peak: the exact integral keeps the peak time exact and does not depend on the frame rate); doubles are enough: a day of audio at 600 rpm is 864,000 turns, far inside the precision.

## Decision 4: Notch and rotation direction

- **Decision**: the notch of a circle is an arc of **1/8 of a turn (45 degrees)** centered at the angle `theta`, measured **clockwise from straight up**; `theta = angle mod 1` (turns). Positive speeds increase `theta` (clockwise on the picture), negative speeds decrease it. At the start of the file `theta = 0`: every notch at the top.
- **Rationale**: clockwise positive as the user said; the same convention as the polar chords and the chromatic ring (angles from straight up, clockwise).

## Decision 5: The picture

- **Decision**: 600 x 400 on the colormap's middle color. Eight rings centered at the middle of the picture; the outer radius `R = min(w, h) / 2 - 10` (190 px), each ring `R / 8` wide (23.75 px) less a **gap of 4 pixels** between rings (and none at the outer edge): ring `k` (1 outer, 8 innermost) covers radii `(R - k W + g, R - (k - 1) W]` (the innermost starts at `g` from its inner radius, leaving a small hole in the middle, `W = R / 8`). Ring `k` has the colormap row `rint(p x 255)` with `p = (k - 1) / 7` and its notch the row `rint((1 - p) x 255)`. Edges are smooth: the ring's coverage `clip(r_out - d + 0.5, 0, 1) x clip(d - r_in + 0.5, 0, 1)`; the notch's edges blend over half a pixel of **arc length** on each side (`clip((1/16 - |delta|) x 2 pi d + 0.5, 0, 1)` with `delta` the signed distance in turns of the pixel's angle from the notch's center).
- **Rationale**: the user's "single set of concentric circles" and the answers on notch and colors; equal widths make the speeds comparable by eye; the gap keeps the rings apart (with the colormap's middle color between ring and notch for the two middle rings, the contrast is low: `p` 0.4 and 0.6 for ring 3, 0.6 and 0.4 for ring 4, near the middle color, as the user's rule gives).
- **Alternatives considered**: stacked discs (the inner colors would hide the outer notches); a ring order from the inside (the user said the outer circle is the tempo).

## Decision 6: Drawing

- **Decision**: the pixel box of the picture's rings, for each pixel its distance, its angle (turns, clockwise from the top), its ring index and the ring's coverage are worked out **once for the frame size** (cached); a frame computes the notch coverage of all rings in one vectorized pass (`theta` per pixel from the ring index), mixes ring color, notch color and background, and is written in the worker pool, `compress_level=1`, as the other types.
- **Rationale**: about 140,000 pixels of a few float operations per frame; no loop over rings in Python in the hot path.

## Decision 7: Wiring and what is not used

- **Decision**: `jobs.py` measures `measure_local_peaks(left, right, file_rate, peak_distance_value, peak_prominence_value)` for `rhythm-circles` (instead of the beat's `frame_positions`, which this type does not use) and builds `rhythm_angles(peaks, fps, frames)`; `write_frames` gets `rhythm: RhythmData | None = None` (required for the type, `ValueError` otherwise, its frame count must equal the frames given; ignored by the others); every other setting is checked and ignored. No request or response field is added; the settings that are validated before the file is read are as ever (so a bad Minimum distance is refused as for every type).
- **Rationale**: the same shape as Energy Graphs (feature 034).

## Decision 8: The page

- **Decision**: `IMAGE_TYPES` gets `{ value: "rhythm-circles", label: "Rhythm Circles" }` at the end; no group of its own; `peakSettingsShown` is true for it (the group `concentric-peaks`, no checkbox, as Decay Exp and Chromatic Decay); the Data smoothing group is not shown (the notes are not used), `gridSettingsApply` false; the image type help gets a paragraph.
- **Rationale**: the user named only the two Local peaks settings as parameters.

## Open questions

None.
