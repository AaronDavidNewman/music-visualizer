# Data Model: Chromatic Decay Threshold

## Threshold

A real number from 0 to 10 (percent), 0 off (the default). `check_threshold(value)`: a bool, a string, None, NaN, infinity, a negative number or a number above 10 is refused with `ValueError("The threshold must be a number from 0 to 10.")`; returns a `float`.

## Floor

`floor = threshold / 100 x M`, `M` the largest of all the smoothed values passed to the points calculation (every frame, every column); `M = 0` for an empty or silent array.

## Thresholded values

`apply_threshold(values, threshold)`: `values` is `(frames, 84 or more)` (finite, not negative); the result is a float64 array of the same shape: a value strictly below the floor is 0, every other value is the same; for `threshold` 0 or `M == 0` the result equals the input. The input is not changed.

## Effect on the simulation

`_simulate(values, beat, decay_rate, threshold)`: `values = apply_threshold(values, threshold)` first; everything after is as in feature 035 (letter energies from the thresholded values, the five loudest letters, the taper, the gains, the decay step, the recording). The decay, the beat and the rings are not touched. `circle_points` and `circle_tapers` take the same `threshold` argument (default 0) after `decay_rate`.

## Request

The existing form field `threshold` (0 to 10, not sent means 0), validated before the file is read with the message of every type, echoed as `threshold`; for `image_type=chromatic-decay` it is passed to the points calculation with the smoothed values.
