# Research: Decay Exp

No `NEEDS CLARIFICATION` remains in the spec; the questions below are about how to build it.

## Decision 1: A thin module that reuses Decay, with the spreading split out

- **Decision**: Add `decay_exp.py`. In `decay.py`, move the part of `decay_step` after `give` is known (the share to each neighbour, the border of non-existent cells, the sum over the 8 directions, the clip to 0..64 and the `NEGLIGIBLE` rule) into `_spread(points, give)`; `decay_step` becomes `_spread(points, np.minimum(points, 8 * frames * decay_per_frame(points, amounts)))`. `decay_exp.py` calls `_spread` with its own `give`. Drawing (`write_decay_frames`, `circle_radii`, `ring_colors`, geometry) and the rate/step timing (`check_decay_rate`, `steps_in_frame`) are imported.
- **Rationale**: The only differences in the spec are the gain and the loss; copying 130 lines of simulation would let the two drift (the edge rule and the hundredth-of-a-point rule especially). The refactor is mechanical and the existing Decay tests and reference hashes prove it changed nothing.
- **Alternatives considered**: (a) a `kind="exp"` switch inside `decay.py`'s functions: adds a parameter to the public signatures of `gains`, `decay_step` and `circle_points` and mixes two formulas in one place; (b) a copy of `decay.py`: duplication; (c) passing a function for the loss into `decay_step`: a smaller change but changes a signature of a tested public function for one caller.

## Decision 2: The gain is `g × e^(−g/8)` on Decay's gain, element-wise

- **Decision**: `exp_gains(values, beat)` takes `gains(values, beat)` (shape `(frames, 84)`, Decay's ranking, ties, zero exclusion and beat bonus) and returns `g * np.exp(-g / 8)`. Zero stays zero (`0 × 1`).
- **Rationale**: The spec says `p` is "the number of points we would add", i.e. Decay's gain including the beat bonus, so the taper is applied after the bonus. Reusing `gains` guarantees "the same system".
- **Alternatives considered**: tapering by the circle's current points (the other reading of `p`; recorded as an Assumption in the spec, not chosen because the request names the points added); tapering before the bonus (the bonus is part of what would be added).
- **Note**: the result is not in rank order (24 → 1.19, 8 → 2.94). The spec records that this is intended as written.

## Decision 3: The loss is the per-neighbour per-frame rate

- **Decision**: `exp_loss_per_frame(points) = sin(pi / 2 * points / 64) ** 2` where `points > 0`, else 0 (revised 2026-11-06: first written `1 / (1 + exp(points / 8))`, which fell as the points rose; the user wanted fuller circles to drain faster). `give = min(points, 8 * frames * exp_loss_per_frame(points))`, `frames` being the frames' worth of the step (the decay rate), exactly as `decay_step` builds its `give` from `decay_per_frame`.
- **Rationale**: It stands where `decay_per_frame` (per neighbour, per frame) stands in Decay, so edge loss (as if 8 neighbours), the "never more than it has" rule and the frames' worth of a step carry over. It is 0 at 0 points, 0.5 at 32 and exactly 1 at 64, rises smoothly and needs no overflow care. With at most 4 frames' worth the cap at the points the circle has never applies (`8 × 4 × sin² ≤ 32 < 64` at 64 points, and less below), but `decay_exp_step` accepts any number of frames and keeps the cap as a safeguard.
- **Alternatives considered**: the formula as the total given away per frame (then 1/8 of it per neighbour): at most 1 point a frame in all, a very slow decay that would not drain a circle in any useful time, and not what "replaces the amounts" suggests; recorded as an Assumption in the spec. The first formula `1 / (1 + e^(p/8))`: replaced, see above.

## Decision 4: Wiring and the page

- **Decision**: `IMAGE_TYPES` gets `"decay-exp"`; `write_frames` and `jobs.py` handle it wherever they handle `"decay"` (beat measured, note layout, decay rate) and call `decay_exp.circle_points` instead of `decay.circle_points`. No new request field and no new response key: the decay amounts remain checked, accepted and echoed for every type. On the page the group id is `decay-exp` (group ids equal image type values, see `TYPE_GROUPS`), titled "Decay", with the control `decay-rate` only; the four amount sliders are shown for `decay` only (`inTypeGroup('decay-low')` is false for `decay-exp`).
- **Rationale**: Smallest change that meets FR-001 to FR-009; keeping the echo means no API shape change and the existing tests that list the response keys keep working.
- **Alternatives considered**: not accepting the amounts for `decay-exp` (a request difference for one type; the spec says accepted and checked as always).

## Decision 5: The taper is a counter, moved after every frame

- **Decision**: The taper is `8 + 0.01 * n` with `n` a whole number from 0 to 400, and `n` is the state, with a direction. `next_taper(n, rising, circles)` returns the next state: more than 10 circles with more than 32 points sets `rising` to false; rising adds 1 (at most 400), falling subtracts 1 (at least 0) and turns `rising` on again at 0. It is moved at the end of each frame, from the points as recorded for that frame, so frame 1 is at 8 and the gains of a frame always use the taper that was decided before it.
- **Rationale**: A counter gives exactly 8 and 12 at the ends, where adding 0.01 to a float 400 times would not, and makes the bounds a clamp on integers. A direction that lasts until 8 is the literal reading of "start subtracting until you are back to 8". Moving it per frame, not per decay step, follows "at each cycle (frame)" and keeps the taper independent of the decay rate. Only the gain uses it: the loss has no 8 since the revision of the same day.
- **Alternatives considered**: subtracting only while more than 10 circles are over 32, and adding otherwise (a level trigger, simpler, hovers around the threshold instead of going back to 8); a float accumulator clamped to 8 and 12 (drifts); counting before the frame's gains (the count would not include what the frame just added).
