# Data Model: Musical Note Bin Analysis

## Constants

| Name | Value | Meaning |
|------|-------|---------|
| `NOTE_COUNT` | 88 | Number of notes per window |
| `BASE_FREQUENCY` | 55.0 Hz | Frequency of note index 0 (A0 in this project's convention) |

Note *n* has frequency `55 * 2**(n/12)`, for n = 0 to 87.

## Note Bin Analyzer

Holds the configuration and the precomputed note mapping.

| Field | Type | Rules |
|-------|------|-------|
| `sample_rate` | positive number (Hz) | Must be greater than 0 |
| `window_size` | positive integer (samples) | Must be an integer of at least 1 |
| `frequencies` | array of 88 floats | `55 * 2**(n/12)` |
| `bin_indices` | array of 88 ints | `int((window_size / sample_rate) * frequencies[n])` |

**Validation at construction**: `sample_rate > 0`, `window_size` is a positive integer, and `max(bin_indices) <= window_size // 2`. Any failure raises `AudioAnalysisError`.

**Operation `analyze(left, right)`**:
1. Both buffers are 1-D, the same length, with length at most `window_size`. Otherwise `AudioAnalysisError`.
2. Compute the real FFT of each buffer, zero-padded to `window_size`.
3. `spectrum = (abs(left_fft) + abs(right_fft)) / 2`.
4. Return `spectrum[bin_indices]`, an array of 88 floats, ordered lowest note to highest.

## Window Result

One row of the result: 88 floats. Its start time is `window_index * window_size / sample_rate` seconds.

## Analysis Result

| Field | Type | Meaning |
|-------|------|---------|
| `sample_rate` | number | Sample rate supplied by the caller |
| `window_size` | int | Window size used |
| `frames` | float array, shape `(window_count, 88)` | One row per window, in time order |
| `window_count` | int (derived) | `frames.shape[0]` |
| `window_start_times()` | float array (derived) | Start time in seconds of each window |

`window_count = ceil(total_samples / window_size)`. An empty file gives `window_count = 0`, with shape `(0, 88)`.

## Audio File (input)

Read with `analyze_wav`. Channels: 1 (mono, duplicated to both sides) or 2. More than 2 channels is rejected. The file's own sample rate is compared with the supplied one, and a `UserWarning` is issued on mismatch. The file's samples are scaled to about [-1, 1] float values.

## State transitions

None. All objects are immutable once built.
