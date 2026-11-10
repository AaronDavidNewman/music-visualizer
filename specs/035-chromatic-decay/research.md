# Research: Chromatic Decay

No `NEEDS CLARIFICATION` remains (the two questions of the specification were answered on 2026-11-09: the ring in circle-of-fifths order, and the same amount to each receiver). The decisions below settle what the specification left to the design.

## Decision 1: Letters, and the ring that shows them

- **Decision**: a note `j` (0 to 83, A1 is 0) belongs to **letter `j mod 12`**, letters counted from A as 0 (A, A#, B, C, C#, D, D#, E, F, F#, G, G#), whatever the Note layout is. The points are kept **in letter order**; only the drawing uses the ring: letter `n` is at **ring position `k = 7 (n - 3) mod 12`** (C = 3 is at position 0, the top; then, clockwise, G, D, A, E, B, F#, C#, G#, D#, A#, F, 30 degrees apart). The letter at position `k` is `(3 + 7 k) mod 12`, so position `k + 1` is the letter 7 above (the next one clockwise) and position `k - 1` the letter 5 above (the next one counterclockwise): the receivers of a circle are the two neighbours of its place.
- **Rationale**: the decay rule is in letters (`n + 5`, `n + 7` mod 12), and keeping the simulation in letter order keeps it independent of the picture and testable by hand; `7 x 7 = 49 = 1 mod 12`, so 7 is its own inverse and the two mappings are the same formula.
- **Alternatives considered**: simulating in ring order (the receivers would be `k +/- 1`, simpler arithmetic, but every test would have to translate letters into positions); a chromatic ring (the receivers would be 5 and 7 places apart: scattered).

## Decision 2: The energy of a letter

- **Decision**: `energy[f, n] = max over the 7 octaves of smoothed[f, 12 * o + n]`, from the first 84 of the note values after smoothing (the same values the other types are drawn from). Octaves are not added.
- **Rationale**: the user said "the highest energy of all the octaves"; the noise floor (feature 033) has been applied before, so an octave under the floor is 0 and a letter of only floored octaves is silent.
- **Alternatives considered**: the sum or the RMS of the octaves (not what was asked; a letter with several faint octaves would beat one loud note).

## Decision 3: Gains

- **Decision**: the five letters with the highest energy of a frame (stable sort, ties to the lower letter; energy 0 does not count) gain `24, 20, 16, 12, 8 + 8 x position` (position = the beat, 0 to 1, 0 without one), each multiplied by `exp(-g / taper)`, the taper being the dynamic taper of Decay Exp (`decay_exp.taper_of`, `next_taper`: 8 to 12 by 0.01 a frame; it falls when more than 10 circles have more than 32 points). Constants `GAINS`, `BEAT_BONUS`, `MAX_POINTS`, `FULL_POINTS`, `FULL_CIRCLES` are imported from `decay` and `decay_exp`, not copied.
- **Rationale**: "keep the same point levels"; sharing the code keeps the two types in step. With 12 circles the falling condition (more than 10 above 32 points) is practically unreachable, so the taper rises to 12 and stays; the user said to keep the levels for now, and this is recorded in the specification's Assumptions as a candidate for a later change.
- **Alternatives considered**: scaling the falling condition to 12 circles (more than 1): changes the behaviour the user asked to keep; made a candidate, not done.

## Decision 4: One decay step

- **Decision (revised 2026-11-09, after the user chose how the points fade)**: with `p` the points before the step and `r` the decay rate in frames: each circle gives away `min(p, 8 r loss(p))` in all, where `loss(p) = sin^2(pi/2 x p/64)` is Decay Exp's loss per neighbour per frame (0 with no points), split **as if it had 8 neighbours**: **one eighth to each of the letters `(n + 5) mod 12` and `(n + 7) mod 12`, and six eighths lost**; all circles give and receive at the same time from the points before the step; the result is held between 0 and 64 and a circle under 0.01 point has none (`decay.NEGLIGIBLE`). This is Decay Exp's rule for an edge or corner circle, the ring having no edges of its own.
- **Rationale**: "the same amount to each receiver" (the user's answer: each receiver gets what each of the 8 neighbours got in Decay Exp, `r loss(p)`, capped as there). On a closed ring of 12 where each circle gives only to two others nothing would ever vanish (the points circulate and settle to an even level, so the ring would drift to being all lit); the user chose the Decay Exp rule for missing neighbours ("what the missing neighbours would have received is lost"), so the giver loses the same total as in Decay Exp and only 2/8 of it arrives. The capping is as in Decay Exp, `min(p, 8 r loss)`.
- **Alternatives considered**: the lossless version (`min(p, 2 r loss)` in all, half to each receiver: the first answer of 2026-11-09, which conserved the points and never faded); a fixed share of each transfer lost (needs one more number): offered, not chosen.

**Revised 2026-11-10**: `decay.NEIGHBOURS` is now 6 (changed by the user); read `NEIGHBOURS` for the 8 and the eighths above: each receiver gets `1 / NEIGHBOURS` of what the circle gives away and the rest, `(NEIGHBOURS - 2) / NEIGHBOURS`, is lost.

**Revised 2026-11-10 (second note)**: Chromatic Decay has its own constant `chromatic_decay.PRETEND_NEIGHBORS = 6`; `decay.NEIGHBOURS` is back to 8 for Decay and Decay Exp. Read `PRETEND_NEIGHBORS` where this document says `NEIGHBOURS` for Chromatic Decay.

## Decision 5: When a step falls

- **Decision**: with a whole-number rate `r`, a step falls in frame `i` (counted from 0) when `(i + 1) mod r == 0` and moves `r` frames' worth (the factor `r` above). So 1 is a step every frame, 10 one every tenth frame.
- **Rationale**: the same rule as Decay Exp's (`steps_in_frame` at the times `r, 2r, ...`) for integers, without its quarter-frame arithmetic, which needs rates up to 4 only (`check_decay_rate` refuses more); the average rate does not depend on `r`.

## Decision 6: The decay rate, validated for the type

- **Decision**: the request field stays `decay_rate`. `check_chromatic_rate(value)` (in `chromatic_decay.py`) accepts a real number that is a whole number from 1 to 10 (so `3`, `3.0` and the text `"3"`, `"3.0"` after parsing; a bool, a string, NaN, infinity, 0.5, 2.5, 0, 11, negative are refused), returns an `int`, and raises `ValueError("The decay rate must be a whole number from 1 to 10.")`. `jobs._parse_decay_rate(text, sent, image_type)` uses it for `chromatic-decay` and the existing 0.25 to 4 check (and message) for every other type; `write_frames` does the same. The response echoes `decay_rate` (an integer for Chromatic Decay).
- **Rationale**: no new field; existing requests and tests keep working (a `decay_rate` of 5 for `tiles` is still refused, for `chromatic-decay` it is valid); `image_type` is already parsed before `decay_rate` in the job.
- **Alternatives considered**: a new field `chromatic_decay_rate` (a second field to validate and echo, and the page would send two; the user spoke of "the decay rate"); one range for all types (would change the other types).

## Decision 7: The picture

- **Decision**: 600 x 400 on the colormap's middle color. The ring is centered in the picture; with `m = 10` pixels of margin the ring radius is `R = (min(w, h) / 2 - m) / (1 + sin(15 degrees))` (150.9 px on 600 x 400) and the **full radius is `R sin(15 degrees)`** (39.1 px): half the distance between two neighbouring centers, so two neighbouring full circles just touch. The center of position `k` is `(w/2 + R sin(30k degrees), h/2 - R cos(30k degrees))`. The size, color and rings of a circle follow its points as in Decay (`decay.ring_colors`; radius `full x (1/12 + 11/12 x min(p, 24)/24)`; twelve rings each `full / 12` wide from 32 points), with the same smooth edges (`clip(radius - distance + 0.5, 0, 1)`). The geometry of the 12 circles (the pixel box, the distances and the ring weights) is worked out once for the frame size; a frame blends each circle over the background; frames are written in the worker pool, `compress_level=1`.
- **Rationale**: "the same size" means the same points-to-size scale; the touching radius is the same rule as `concentric.full_radius`; 12 circles are cheap, so every circle is drawn with its ring weights (no flat shortcut).
- **Alternatives considered**: a larger full radius (circles would overlap at 24 points and more); a fixed 25 px radius like the grid (small on a ring of 150 px).

## Decision 8: Settings that apply

- **Decision**: the colormap, the analysis settings, the data smoothing, the local peaks (`peak_distance`, `peak_prominence`: the beat is always measured for this type, as for Decay Exp) and the decay rate apply; the Note layout, the four decay amounts and every grid setting (threshold, notes, oversampling, interpolate, Gaussian, blend width, wave count, circle settings, Notes shown) are accepted, checked as for every type and ignored. The frontend shows the groups Analysis, Colormap, Image type, **Chromatic Decay** (one control: the decay rate, 1 to 10), Local peaks (no checkbox) and Data smoothing.
- **Rationale**: as Decay Exp (feature 030) minus the Note layout, which has no meaning for a ring of letters.

## Decision 9: The page keeps the value of each decay rate separately

- **Decision**: the page has a second value, `chromaticRate` (default 1, whole numbers 1 to 10, its own control `chromatic-decay-rate` in its own group `chromatic-decay`), beside the existing `decayRate` (0.25 to 4). The request sends `decay_rate` = `chromaticRate` when the type is Chromatic Decay and `decayRate` otherwise, so the value of one type is kept when the user switches to the other and is always valid for the type it is sent with.
- **Rationale**: one shared value cannot be valid for both ranges (0.25 is not a rate of Chromatic Decay; 7 is not one of Decay); the page's existing convention is that every value stays in its own ref, is kept when the type changes and is still sent.
- **Alternatives considered**: one control whose range follows the type, resetting the value on a switch (loses the user's value and needs a reset rule).

## Open questions

None.
