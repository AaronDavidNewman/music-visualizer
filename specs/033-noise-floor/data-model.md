# Data Model: Noise Floor

No stored data and no new fields. This describes the values and the rule.

## Constants

| Name | Value | Meaning |
|------|-------|---------|
| `NOISE_FLOOR_DB` | −60 | The level of the floor below the loudest note of the file, in dB of amplitude |
| `NOISE_FLOOR` | `10 ** (NOISE_FLOOR_DB / 20)` = 0.001 | The same as a ratio of strengths |

## The cut

For an array `A` of note strengths `(windows, columns)` (finite, not negative; the analysis gives 88 columns):

- `peak` = the largest value of `A` anywhere (all columns, drawn or not); 0 for an empty array or one with no sound.
- A value `v` is **below the floor** when `v < NOISE_FLOOR × peak` (strictly; with `peak` 0 nothing is).
- The result is a **copy** of `A` with every value below the floor set to exactly `0.0`; every other value is unchanged; the shape and type of `A` are kept (a float array). `A` itself is not changed.
- Properties: idempotent (`cut(cut(A)) == cut(A)`, because the largest value is never cut and what is cut is below the floor of the array it came from); never creates a value; monotone (a louder note is never cut when a quieter one in the same file is kept).

The reference may be given instead of worked out (`peak=`), for the case where the caller knows the largest value of a wider set. The job does not use it.

## Where it is applied

| Place | What is cut | Reference |
|-------|-------------|-----------|
| The job, right after the analysis (`floor_analysis`) | `AnalysisResult.frames`, `(windows, 88)`: the strengths of every analysis window | The largest value of all windows and all 88 columns |
| `measure_chords` (first thing, before the Notes limit and the Threshold) | The first 84 columns of the strengths given | The largest value of the whole array given (all columns) |

Both therefore agree for the strengths of the analysis, and the second is a no-op on strengths the job has already cut. Nothing is cut after smoothing or in the pictures.

## Effect on the chords

`measure_chords` combines the octaves of the **cut** notes into letters (feature 031): a letter is the sum of its cut octaves, so a letter whose octaves are all below the floor has the strength 0 and does not sound, and the recorded note of a letter is its loudest cut octave. The relative floor of feature 031 (a millionth of the loudest letter of the window) no longer exists.

## Relation to the other limits

| Limit | Order | Effect |
|-------|-------|--------|
| Noise floor | first | The faint notes are 0 |
| Notes (`note_count`, feature 017) | after | The notes with the most total energy are chosen from the cut strengths |
| Threshold (feature 011) | after | A note is hidden when strictly below the chosen percentage of the largest value; the percentage below 0.1 adds nothing to the floor, one above it decides |
| Smoothing | after | Works on cut strengths; its result is not cut again |

## State and errors

No state. The cut raises no error of its own: the arrays that reach it are already checked (the analysis's own values; `measure_chords` checks its `values` before cutting). `apply_noise_floor` takes an array of any shape, checks that its values are finite numbers that are not negative, and raises `ValueError("The note values must be finite numbers that are not negative.")`, the message the chord measurement uses, otherwise. A `peak` given must be a finite number that is not negative (the same message with "peak" is not needed: `ValueError("The peak must be a finite number that is not negative.")`).
