# Data Model: Local Tempo Finder

All of it is in memory during one job; nothing is stored.

## Constants (`tempo_finder.py`)

| Name | Value | Meaning |
|---|---|---|
| `START_TEMPO` | 120.0 | The tempo before the first sample and after a restart from below |
| `LOW_LIMIT` | 60.0 | Below it: the tempo becomes `START_TEMPO` and the samples are thrown away |
| `HIGH_LIMIT` | 156.0 | Above it: the tempo becomes `HIGH_RESTART` and the samples are thrown away |
| `HIGH_RESTART` | 78.0 | The tempo after a restart from above (156 halved, as the user wrote) |
| `WINDOW` | 5 | The number of samples kept (fixed; not a setting) |
| `MIN_STEP` | 1.0 | The smallest standard deviation used (beats per minute) |
| `HARMONIC_TOLERANCE` | 0.15 | A sample stands for a related tempo only within this share of it; farther, it stands for itself (added 2026-11-14) |
| `RATIOS` | `(1.0, 2.0, 1.5, 0.5, 2/3)` | A sample close to `T`, `T/2`, `T/1.5`, `2T` or `1.5T` stands for `s * ratio` (the faster ones were added on 2026-11-14) |

## Entities

- **Sample**: `s = 60 / (time[i] - time[i-1])` for peak `i >= 1` (beats per minute, above 0 because the times strictly increase); after matching, `s * ratio`. The window holds the latest `WINDOW` matched samples.
- **TempoTrack** (the result of the finder): `tempos` is a float64 array with one tempo per peak (`tempos[0] = 120`, `tempos[i]` the current tempo after peak `i` was considered), and `restarts` the number of times the tempo was restarted. Invariant: every tempo is from `LOW_LIMIT` to `HIGH_LIMIT` inclusive.
- **Related tempos**: `T / 2`, `T / 1.5`, `2 T` and `1.5 T`: the other values a sample is compared with (not drawn).
- **Series** (`rhythm_circles.peak_series`): float64 array `(peaks, 4)` in revolutions per minute, columns outer to inner (the first version had 8 columns: two thirds and half of the tempo as well):

  | Column | Content |
  |---|---|
  | 0 | level of `tempos[i]`, the current tempo |
  | 1 | its rate of change: `(x[i] - x[i-1]) / (time[i] - time[i-1])`, 0 for the first peak |
  | 2 | level of the local peak: `peak.rate[i]` (60 for the first peak) |
  | 3 | its rate of change |

- **Defaults before the first peak and with no peaks** (`DEFAULT_SPEEDS`): `(120, 0, 60, 0)`.

## State transitions of the finder

```text
start: T = 120, window = []
for each peak i >= 1:
    s  = 60 / (t[i] - t[i-1]);  s *= ratio (of RATIOS) nearest in ratio to T          # match
    window = (window + [s])[-5:]
    sd = max(population std of window, 1);  mean = mean(window)
    if |s - T| <= sd:  T = (s + mean) / 2
    else:              T += sign(s - T) * min(sd, |s - T|)
    if T > 156:  T = 78;   window = []        # restart
    if T < 60:   T = 120;  window = []        # restart
    tempos[i] = T
```

## Validation rules

- The peak times must be a 1-D array of finite numbers in strictly increasing order (the same check as `rhythm_circles._times`).
- No tempo may be outside 60 to 156 (checked by the tests as an invariant, not at run time).
