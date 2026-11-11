# Research: Chromatic Decay Threshold

No `NEEDS CLARIFICATION` remains. The decisions below settle what the specification left to the design.

## Decision 1: The rule

- **Decision**: `apply_threshold(values, threshold)`: with `values` the `(frames, 84 or more)` smoothed note values (checked as `concentric._check_values`), `floor = threshold / 100 x values.max()` over **the whole array, every frame and every column** (0 for an empty array); every value **strictly below** `floor` becomes 0, every other is unchanged; with `threshold` 0 or `floor` 0 (a silent file) the array is returned unchanged (a copy). The input is not changed.
- **Rationale**: it is the rule of `frame_rendering.hidden_below` (strictly below `threshold / 100 x peak`, `peak` the largest smoothed value of the whole file over all columns), which the user's "the max of the other smoothed values passed into circle_points" describes for this function; one rule for all types.
- **Alternatives considered**: the maximum of the frame (a quiet passage would keep its faint notes: not what the user said); the maximum of the 84 note columns only (differs from `hidden_below` only when one of the 4 higher analysis notes is the loudest of the file, rare; the whole array is what "passed into" says).

## Decision 2: Where it acts

- **Decision**: in `_simulate`, on the note values **before** `_raw_gains` (so before the letter energies, the five loudest and the taper); `circle_points` and `circle_tapers` both go through `_simulate`, so both take the argument and stay consistent.
- **Rationale**: "set to 0 values below": a note treated as 0 does not count as sounding, so it cannot be the loudest octave of its letter nor one of the five loudest letters.
- **Alternatives considered**: on the letter energies after the max over the octaves (a faint octave could still decide the letter's energy from a quieter file region; the reference would also differ).

## Decision 3: The check of the number

- **Decision**: `check_threshold(value)` in `chromatic_decay.py` accepts what `frame_rendering._check_threshold` accepts (a real, finite, from 0 to 10, not a bool) and raises `ValueError("The threshold must be a number from 0 to 10.")`; a test compares the two on a table of values so that they cannot drift. It returns a `float`.
- **Rationale**: `frame_rendering` imports `chromatic_decay`, so `chromatic_decay` cannot import `frame_rendering`; moving the check into a third module would touch every type's code for no gain.
- **Alternatives considered**: moving `_check_threshold` and the constants to a shared module (a wider change than the feature); skipping the check in the library (the job already checks, but the library is public and tested on its own).

## Decision 4: The job and the request

- **Decision**: `write_frames` already receives `threshold` and has checked it; its `chromatic-decay` branch passes it to `chromatic_points(smoothed, beat, decay_rate, threshold)`. The request field, its validation, its echo and the message exist; nothing is added. The existing tests that list `threshold` among the settings that Chromatic Decay accepts and ignores are changed: it now applies.
- **Rationale**: the smallest change; one setting with one meaning.

## Decision 5: The page

- **Decision**: the group `chromatic-decay` lists `["chromatic-decay-rate", "threshold"]` (the control block `threshold` already renders wherever the type's group lists it); the summary line `Threshold:` is shown for `gridSettingsApply(type) || isChromaticType(type)`; `thresholdHelp` gets a sentence for Chromatic Decay (a note under the threshold does not charge its letter) and the Chromatic Decay paragraph of the image type help mentions it. `gridSettingsApply` stays false for this type (no Notes, Interpolate, Oversampling...).
- **Rationale**: no new control; a row of two in the group (Decay rate and Threshold), as the other groups.

## Open questions

None.
