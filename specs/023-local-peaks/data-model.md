# Data Model: Local Peaks

No stored data. This describes what the measurement works out, in order, and the objects it returns.

## Constants

| Name | Value | Meaning |
|------|-------|---------|
| `IMPULSE_SAMPLES` | 32 | Samples per impulse window |
| `PEAKS_WINDOW` | 4096 | Impulse samples per peaks window (default; the size is a parameter) |
| `MIN_MIN_DISTANCE`, `MAX_MIN_DISTANCE`, `DEFAULT_MIN_DISTANCE` | 100, 2000, 100 | Minimum distance, milliseconds |
| `MIN_PROMINENCE`, `MAX_PROMINENCE`, `DEFAULT_PROMINENCE` | 0, 100, 50 | Prominence, percent |
| `DEFAULT_RATE` | 60.0 | Peaks per minute before the first peak and for the first peak (1 per second) |

## From audio to peaks

For a file with sample rate `R` and `N` samples per channel:

| Quantity | Definition |
|----------|------------|
| `n` | `N // 32` impulse samples (a last partial window is dropped) |
| `energy[i]` | `(std(left[32i : 32i+32]) + std(right[32i : 32i+32])) / 2`, `i` in `0 … n−1`; population standard deviation per channel, then averaged. For a mono file both channels are the same. |
| `distance` | `max(1, round(min_distance / 1000 × R / 32))` impulse samples |
| window `k` | `energy[s : e]` with `s = k × W/2`, `e = min(s + W, n)`, `W` the window size; the last window is the first with `e = n` |
| zone of window `k` | `[lo, hi)` with `lo = 0` for `k = 0` else `s + W/4`; `hi = e` for the last window else `s + 3W/4` (the zones tile `0 … n`) |
| `top` | `max(window)`; a window with `top = 0` (silence) has no peaks |
| `prominence` | `prominence_percent / 100 × top` |
| candidates | `find_peaks(window, distance=distance, prominence=prominence)`; kept if `s + index` is in the window's zone |
| merge | In order of position: a candidate closer than `distance` to the last kept peak replaces it if its energy is higher, else is dropped |

## The objects returned

### `LocalPeak` (frozen)

| Field | Type | Meaning |
|-------|------|---------|
| `sample` | `int` | `32 × index`: the first sample of the impulse window where the maximum is |
| `energy` | `float` | `energy[index]` |
| `window_min` | `float` | Smallest impulse energy of the peaks window in which it was found |
| `window_max` | `float` | Largest impulse energy of that window |
| `rate` | `float` | Peaks per minute: `60 × R / (sample − previous sample)`; `DEFAULT_RATE` for the first peak |

### `LocalPeaks` (frozen)

| Field | Type | Meaning |
|-------|------|---------|
| `peaks` | `tuple[LocalPeak, …]` | Ordered by `sample`, none twice |
| `file_rate` | `int` | Sample rate `R` of the file |
| `sample_count` | `int` | `N` |
| `min_distance` | `float` | The setting used, milliseconds |
| `prominence` | `float` | The setting used, percent |

Methods (all total for finite input; see [contracts/local-peaks.md](contracts/local-peaks.md)):

| Method | Result |
|--------|--------|
| `energy_at(point)` | Straight line between the previous and next peak's `energy`; `0.0` before the first peak; the last peak's `energy` after the last; `0.0` with no peaks |
| `rate_at(point)` | `rate` of the last peak at or before the point; `DEFAULT_RATE` before the first and with no peaks |
| `energy_at_time(seconds)`, `rate_at_time(seconds)` | The same at `seconds × file_rate` |

`point` is a sample number (int or float, negative or past the end allowed) or a sequence/array of them.

## Validation

| Input | Rule | Message |
|-------|------|---------|
| `min_distance` | A real number (not a bool), finite, 100 ≤ v ≤ 2000 | `The minimum distance must be a number from 100 to 2000 milliseconds.` |
| `prominence` | A real number (not a bool), finite, 0 ≤ v ≤ 100 | `The prominence must be a number from 0 to 100 percent.` |
| `file_rate` | A positive whole number | `The sample rate must be a positive whole number.` |
| channels | Two 1-D arrays of the same length | `The left and right channels must be one-dimensional and of the same length.` |
| `window` | A whole number ≥ 8 (even) | `The peaks window must be a whole number of at least 8 impulse samples.` |
| `point` | Finite | `The point must be a finite number.` |

All errors are `ValueError`. Settings are checked before any audio is touched.

## State transitions

None: a measurement is made once and is immutable.
