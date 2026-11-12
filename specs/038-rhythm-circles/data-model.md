# Data Model: Rhythm Circles

`P` is the number of local peaks, `F` the number of frames, `K = 8` the circles.

## Peaks (existing)

`LocalPeaks.peaks` (tuple of `LocalPeak`, in order of `sample`), `file_rate`. Peak `i` has time `t_i = sample / file_rate` seconds (strictly increasing: the minimum distance is at least 100 ms) and `rate` beats per minute (60 for the first). The module reads only `sample`, `rate` and `file_rate`.

## Series (per peak)

`peak_series(times, tempos)` -> `(P, 8)` float64, revolutions per minute, columns in the order of the circles from the outer (1) to the innermost (8): four layers, the longest aggregation outermost, each a level and, after it, the rate of change of that level:

| Column | Circle | Value at peak `i` |
|--------|--------|-------------------|
| 0 | aggregate of 8 | `agg8[i]` = `aggregate(tempo[max(0, i-7) .. i], tempo[i])` |
| 1 | rate of change of the aggregate of 8 | `(agg8[i] - agg8[i-1]) / (t_i - t_{i-1})`, 0 for `i < 1` |
| 2 | aggregate of 4 | `agg4[i]` = `aggregate(tempo[max(0, i-3) .. i], tempo[i])` |
| 3 | rate of change of the aggregate of 4 | `(agg4[i] - agg4[i-1]) / (t_i - t_{i-1})`, 0 for `i < 1` |
| 4 | aggregate of 2 | `agg2[i]` = `aggregate(tempo[max(0, i-1) .. i], tempo[i])` |
| 5 | rate of change of the aggregate of 2 | `(agg2[i] - agg2[i-1]) / (t_i - t_{i-1})`, 0 for `i < 1` |
| 6 | tempo | `tempo[i]` |
| 7 | rate of change of the tempo | `(tempo[i] - tempo[i-1]) / (t_i - t_{i-1})`, 0 for `i < 1` |

`aggregate(window, current)` is `mean(window)` or `max(window)`, whichever is closer to `current` (`abs(mean - current) < abs(max - current)` takes the mean, so the **fastest wins a tie**, and a window of one tempo, or of equal tempos, is that tempo).

`times` is `(P,)` strictly increasing seconds, `tempos` `(P,)` positive numbers (ValueError otherwise, and for different lengths).

## Defaults before the first peak

`DEFAULT_SPEEDS = (60, 0, 60, 0, 60, 0, 60, 0)` (revolutions per minute): the tempo and its aggregated tempos are the default rate 60, the rates of change 0. A file with no peak has these speeds throughout.

## Speeds (a step function of time)

`circle_speeds(times, series, moments)` -> `(len(moments), 8)`: the row of `series` of the latest peak at or before each moment, `DEFAULT_SPEEDS` before the first peak and with no peaks.

## Angles

`angles(times, series, moments)` -> `(len(moments), 8)` float64, **turns**, unwrapped: `angle_c(t) = integral over [0, t] of speed_c(u) / 60 du`. With breakpoints `b = [0, t_0, ..., t_{P-1}]`, the speed on `[b_j, b_{j+1})` the default for `j = 0` and `series[j - 1]` for `j >= 1`: `angle(t) = cumulative[j] + speed_j x (t - b_j) / 60` for the last breakpoint `b_j <= t`. Continuous in `t`; the slope changes at each peak. If `t_0` is 0 the default interval is empty.

## RhythmData (`write_frames(rhythm=...)`)

Frozen dataclass: `angles` `(F, 8)` float64 turns (the angle of every circle at the middle of every frame), `frame_count` property. `rhythm_angles(peaks, frame_rate, frames)` builds it with the moments `(f + 0.5) / frame_rate`.

### Validation (`_check_data`, before anything is written)

`angles` 2-D with 8 columns, finite numbers (any size: the drawing takes them modulo 1).

## Picture geometry (per frame size)

Center `(w/2, h/2)`; `R = min(w, h) / 2 - 10`; `W = R / 8`; ring `k` (1..8): outer radius `R - (k - 1) W`, inner radius `R - k W + g` with `g = 4` pixels scaled with the picture (`4 x min(w, h) / 400`); ring color row `rint((k-1)/7 x 255)`, notch row `rint((1 - (k-1)/7) x 255)`; the notch is the arc of 1/8 of a turn centered at `theta = angle mod 1` turns clockwise from straight up.

## State

The angles are the only quantity that depends on the earlier frames, and they are computed for all frames at once from the peaks, so frames can be drawn in any order and in parallel.
