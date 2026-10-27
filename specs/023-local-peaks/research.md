# Research: Local Peaks

No `[NEEDS CLARIFICATION]` remains (the three questions were answered on 2026-10-27). Facts about the code were read from the repository; the numbers come from a prototype (`scratchpad/peaks_proto.py`) on seeded click tracks (quiet noise, 40-sample bursts, 44.1 kHz).

## What exists today

- `note_analysis.read_wav(path, display_name) -> (file_rate, left, right)`: mono is duplicated into both channels, at most two channels, `AudioAnalysisError` (a `ValueError`) for unreadable input. The new measurement takes the arrays and the rate, so it also works on any data, and `measure_wav` is a thin convenience over `read_wav`.
- Settings are checked by small functions that return the value as a `float` or raise `ValueError` with a message saying what is allowed (`gaussian.check_gaussian`, `resolution.check_resolution`); booleans and non-finite numbers are refused. The new checks follow that pattern.
- `scipy>=1.11` is already declared in `requirements.txt`; `find_peaks(x, distance=…, prominence=…)` is stable API.

## Decision 1: The impulse energy is the per-channel standard deviation, averaged

- **Decision**: Reshape each channel's first `n × 32` samples to `(n, 32)`, take `std` (population, `ddof=0`) along the rows for left and right, and average the two. A last partial window is dropped.
- **Rationale**: This is the user's definition (and their correction: not the channels averaged first). It is a single vectorised call, so it costs a few milliseconds for a minute of audio.
- **Alternatives considered**: averaging the channels first (the user said no; two channels in opposite phase would cancel); overlapping windows (not asked for, doubles the work); sample variance `ddof=1` (a constant factor only, and the population value is the natural "spread of this window").

## Decision 2: The peaks window slides by half its length and each window owns its central half

- **Decision**: Window size 4,096 impulse samples, step 2,048. Window `k` starting at `s` *owns* `[s + 1024, s + 3072)`; the first window also owns from 0 and the last also to its end. A peak that `find_peaks` finds in a window is kept only if it is in that window's zone. The zones tile the energy list, so no peak is found twice and none is dropped.
- **Rationale**: `find_peaks` judges a peak's prominence only inside the array it is given, so a peak near a window's edge is judged with less context (the prominence base cannot go beyond the edge). Owning only the central half guarantees at least 1,024 impulse samples (about 0.75 s at 44.1 kHz) on each side. It also removes the need to compare duplicates between overlapping windows (FR-004).
- **Alternatives considered**: non-overlapping windows (a peak at a boundary is judged with half its context, and a peak pair split by a boundary loses its distance rule); overlapping windows with deduplication by position (works but needs a tolerance and a rule for conflicting verdicts); a streaming deque (the same windows, harder to test, no gain: the whole file is available).
- **Prototype**: windows of 2,048, 4,096 and 8,192 gave identical peaks on all three click tracks (SC-007).

## Decision 3: The minimum distance is enforced again across zone borders

- **Decision**: After the windows, one pass walks the kept peaks in order; a peak closer than the distance to the previous kept peak replaces it if its energy is higher and is dropped otherwise.
- **Rationale**: `find_peaks` removes the weaker of two close peaks only inside a window; two peaks on either side of a zone border come from different windows and can be closer than the distance (the longest distance, 2,000 ms, is about 2,756 impulse samples, longer than a quarter window). Replacing the earlier peak by a later, stronger one cannot bring it closer to its own predecessor (the new one is farther along), so one pass is enough. FR-003 and SC-003 hold for the whole file.
- **Alternatives considered**: a window of at least four times the distance (does not remove the border case, and changes the window size with a setting); a second `find_peaks` over the peaks (it would need an energy array with gaps).

## Decision 4: The peak's sample is the first sample of its impulse window; energy and min/max come from the window

- **Decision**: Position `= index × 32`; energy `= energies[index]`; minimum and maximum `= window.min()` and `window.max()` of the peaks window in which the peak was found (the clarification), as floats.
- **Rationale**: Exactly the user's clarified definition; the position is exact to 32 samples as the spec says. A plateau gives one peak at its middle (`find_peaks`).
- **Alternatives considered**: the centre of the impulse window (`+16`), which hides that the position is a window start and breaks "within 32 samples" nowhere but is a guess the user did not make.

## Decision 5: The rate, and what is returned before the first peak

- **Decision**: `rate[i] = 60 × file_rate / (sample[i] − sample[i−1])` in peaks per minute; the first peak and every point before it use `DEFAULT_RATE = 60.0` (1 per second). `rate_at(point)` is the rate of the last peak at or before the point (`searchsorted(..., side="right") − 1`), not interpolated.
- **Rationale**: The clarification. The rate of a peak describes the gap that ended at it, so "the rate at the previous peak" is the best known tempo for the stretch that follows.
- **Alternatives considered**: giving the first peak the rate of the gap after it (the first draft; the user chose a default instead).

## Decision 6: Interpolation is `numpy.interp`

- **Decision**: `energy_at(point) = np.interp(point, peak_samples, peak_energies, left=0.0, right=peak_energies[-1])`; no peaks gives 0 everywhere. A time in seconds is converted with the file's rate (`energy_at_time`, `rate_at_time`). Scalars return a `float`, sequences an array of the same shape. Non-finite points raise `ValueError`; negative and past-the-end points are valid and answered as before the first and after the last peak.
- **Rationale**: This is exactly "a line between the previous and next peak, 0 before, the last value after" in one vectorised call, which suits asking for a whole file's frames at once.
- **Alternatives considered**: a hand-written bisect per call (slower for arrays, more code); returning the energy of the nearest peak (not the spec).

## Decision 7: Settings are checked by two functions, with the ranges in constants

- **Decision**: `MIN/MAX/DEFAULT_MIN_DISTANCE` = 100 / 2000 / 100 (milliseconds) and `MIN/MAX/DEFAULT_PROMINENCE` = 0 / 100 / 50 (percent); `check_min_distance` and `check_prominence` return floats and raise `ValueError("The minimum distance must be a number from 100 to 2000 milliseconds.")` and `ValueError("The prominence must be a number from 0 to 100 percent.")`; booleans, strings, NaN and infinity are refused. `measure_local_peaks` checks both before touching the audio.
- **Rationale**: Same pattern, messages and rejection rules as the other settings, so wiring them to the job request later is a few lines.
- **Alternatives considered**: whole-number-only distance (the spec says "a time"); clamping out-of-range values (the spec says refuse).

## Prototype results

30 s click tracks, seeded noise at 0.005 and bursts of 40 samples at about 0.5, 44.1 kHz:

| Clicks every | Window | Distance (impulse samples) | Peaks / clicks | Clicks found within 64 samples | Mean rate | Largest rate error |
|--------------|--------|-----------------------------|----------------|--------------------------------|-----------|--------------------|
| 0.5 s | 2,048 / 4,096 / 8,192 | 138 | 59 / 59 | 59 | 120.0 | 0.15% |
| 0.75 s | 2,048 / 4,096 / 8,192 | 138 | 39 / 39 | 39 | 80.0 | 0.06% |
| 0.3 s | 2,048 / 4,096 / 8,192 | 138 | 99 / 99 | 99 | 200.0 | 0.14% |

Minimum distance on the 0.3 s track: 100 ms gives 99 peaks (smallest gap 299.7 ms), 500 ms gives 42 (600.1 ms), 2,000 ms gives 11 (2,100 ms). A 60 s file takes 0.023 s.
