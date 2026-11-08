# Contract: The noise floor (library only)

This feature has **no HTTP, page or picture interface** (spec FR-003, SC-006): the job request, the response, the settings page and the help text are unchanged. The interface is a small library module, called by the job and by the chord measurement. Rules and values: [data-model.md](../data-model.md).

## Module `app/services/noise_floor.py`

```python
NOISE_FLOOR_DB = -60
NOISE_FLOOR = 10 ** (NOISE_FLOOR_DB / 20)       # 0.001, a ratio of amplitudes

apply_noise_floor(values, peak=None) -> np.ndarray      # a float copy of values with every value strictly below NOISE_FLOOR * peak set to 0.0
floor_analysis(result: AnalysisResult) -> AnalysisResult # the same result with its frames cut (a new object; window starts, rate, step, sample count are kept)
```

### `apply_noise_floor(values, peak=None)`

| Parameter | Rule |
|-----------|------|
| `values` | An array (any shape) of finite numbers that are not negative. Not changed. Anything else: `ValueError` `The note values must be finite numbers that are not negative.` |
| `peak` | `None` (the largest value of `values`; 0 for an empty array) or a finite number that is not negative. Anything else: `ValueError` `The peak must be a finite number that is not negative.` |

Returns a new `float64` array of the shape of `values`. A value `v` is set to `0.0` when `v < NOISE_FLOOR * peak`; every other value is kept as it is. With `peak` 0, or no sound, nothing is changed. Idempotent. Two calls with the same arguments give equal results.

### `floor_analysis(result)`

`apply_noise_floor(result.frames)` as the frames of a new `AnalysisResult` with the other fields as they were. The reference is the largest value of all windows and all columns.

### Changed behaviour: `chords.measure_chords`

The signature is unchanged. Before anything else it cuts `values[:, :84]` with `apply_noise_floor`, using the largest value of the whole array given (all columns) as the peak, so that a note below the floor is neither a note of a chord nor a recorded note, a letter is made only of notes that were not cut, and a window with no note left has no chord. The `NOISE_FLOOR = 1e-6` relative-to-the-window constant of feature 031 is removed. The Notes limit and the Threshold work on the cut strengths. On strengths that are already cut it changes nothing.

## Examples

With a loudest value of 1.0 in the array:

| Strength of a note | Result |
|--------------------|--------|
| 1.0 | 1.0 |
| 0.001 (exactly the floor) | 0.001, kept |
| 0.00099999 | 0.0 |
| 0.0 | 0.0 |

Chord measurement with the types `((4, 7), (4, 7, 10))`: C, E, G at 1.0, 0.9, 0.8 and Bb at 0.0009 → `(4, 7)` with the notes C, E, G (Bb is cut, so the seventh chord does not match). Bb at 0.001 → `(4, 7, 10)`.

## What does not change

`POST /api/jobs` and its response, the settings page and its help text, every picture's drawing code, the Threshold and Notes settings, the beat (local peaks) measurement, and the frames of any file in which every note is at or above the floor or silent.
