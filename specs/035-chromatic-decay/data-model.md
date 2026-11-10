# Data Model: Chromatic Decay

All arrays are numpy arrays. `F` is the number of frames, `L = 12` the letters.

## Letter

An integer 0 to 11, counted from A: A 0, A# 1, B 2, C 3, C# 4, D 5, D# 6, E 7, F 8, F# 9, G 10, G# 11. Note `j` of the 84 has letter `j mod 12`.

Receivers of letter `n`: `(n + 5) mod 12` and `(n + 7) mod 12` (distinct from each other and from `n`). The receivers of `n` are each other's givers the other way round: `n` gives to `m = n + 7` and `m` gives to `n = m + 5`.

## Ring position

`ring_position(n) = 7 (n - 3) mod 12` (0 to 11) and `letter_at(k) = (3 + 7 k) mod 12`: C (3) is at position 0, the top; then clockwise G, D, A, E, B, F#, C#, G#, D#, A#, F. Position `k + 1` holds the letter 7 above that of `k` and position `k - 1` the letter 5 above it.

## Letter energies

`letter_energies(values)`: `values` is `(F, 84 or more)` smoothed note values (finite, not negative); the result is `(F, 12)` float64, `energy[f, n] = max_o values[f, 12 o + n]` over `o = 0..6`. The input is not changed.

## Letter gains

`letter_gains(values, beat=None, taper=8)`: `(F, 12)` float64: for each frame the five letters with the largest energy (stable: ties to the lower letter; energy 0 does not count) get `g = (24, 20, 16, 12, 8)[rank] + 8 x position`, each multiplied by `exp(-g / taper)` (`taper` a number above 0 or one for each frame); every other letter 0. `beat` is `None` or one number from 0 to 1 for each frame.

## Points

`(F, 12)` float64 in letter order, each from 0 to 64, 0 before the first frame; what `circle_points` returns (the points **after** the gains and the decay steps of the frame).

### Validation (`_check_points`, before anything is written)

`points` is 2-D with 12 columns, finite, from 0 to 64.

## Decay step

`chromatic_step(points, frames)`: `points` is `(12,)`, `frames` a whole number 1 to 10 (the frames' worth). With `p = points` and `loss(p) = sin^2(pi/2 x p/64)` (0 for `p = 0`):

- `give[n] = min(p[n], 8 x frames x loss(p[n]))` (the total Decay Exp gives, split as if the circle had 8 neighbours)
- `received[m] = give[(m - 5) mod 12] / 8 + give[(m - 7) mod 12] / 8` (one eighth to each receiver; the other six eighths of `give[n]` are lost)
- `after = clip(p - give + received, 0, 64)`, and `after < 0.01` becomes 0.

All from the points before the step.

**Revised 2026-11-10**: `decay.NEIGHBOURS` is now 6 (changed by the user); read `NEIGHBOURS` for the 8 and the eighths above: each receiver gets `1 / NEIGHBOURS` of what the circle gives away and the rest, `(NEIGHBOURS - 2) / NEIGHBOURS`, is lost.

**Revised 2026-11-10 (second note)**: Chromatic Decay has its own constant `chromatic_decay.PRETEND_NEIGHBORS = 6`; `decay.NEIGHBOURS` is back to 8 for Decay and Decay Exp. Read `PRETEND_NEIGHBORS` where this document says `NEIGHBOURS` for Chromatic Decay.

## Simulation

`circle_points(values, beat=None, decay_rate=1)`: for frame `i = 0 .. F - 1`: `points = clip(points + letter_gains(...)[i] at taper_i, 0, 64)`; if `(i + 1) mod decay_rate == 0`: `points = chromatic_step(points, decay_rate)`; record `points`; then the next taper from `next_taper` (the number of circles above 32 points, `FULL_CIRCLES = 10`). `circle_tapers(...)` returns the taper of every frame (8 for the first).

## Decay rate

`check_chromatic_rate(value)`: an `int` 1 to 10; a real that is a whole number (3.0) is accepted and returned as 3; refused (`ValueError("The decay rate must be a whole number from 1 to 10.")`): a bool, a string, None, NaN, infinity, a real that is not whole, under 1 or over 10. Default 1.

## Ring geometry (drawing only)

For a picture `w x h`: `R = (min(w, h) / 2 - 10) / (1 + sin(pi/12))`, `full = R sin(pi/12)`, the center of the circle at position `k` is `(w/2 + R sin(k pi/6), h/2 - R cos(k pi/6))`. A circle of `p` points has radius `full x (1/12 + 11/12 x min(p, 24)/24)` and the colors/rings of `decay.ring_colors(p)`.

## State and lifecycle

The points are the only quantity with memory (and the taper); they are computed for all frames in one pass, then frames are drawn independently and in parallel. Nothing is stored between jobs.
