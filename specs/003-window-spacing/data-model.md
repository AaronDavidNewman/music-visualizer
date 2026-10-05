# Data Model: Window Spacing Parameter

Only the changes and additions to features 001 and 002 are listed.

## Settings (server configuration)

| Field | Default | Meaning |
|-------|---------|---------|
| `max_windows` | 60,000 | Most analysis windows one submission may create |

## Window spacing (request field)

| Field | Type | Rules |
|-------|------|-------|
| `window_spacing` | text parsed as a number, optional | If omitted or empty: the default spacing for the file, window size and frame rate. If given: finite and greater than 0. There is no upper limit. |

## Derived values

| Name | Formula | Notes |
|------|---------|-------|
| `default_spacing` | `floor(10^6 × (sample_rate / frame_rate) / window_size) / 10^6` | One frame period in samples, divided by the window size, rounded down to 6 decimals. Never makes the step longer than a frame period. |
| `step` (samples) | `spacing × window_size`, but at least 1 | If `spacing × window_size < 1`, the step is 1 and `spacing_used = 1 / window_size`. |
| `spacing_raised` | `spacing × window_size < 1` | True when the minimum was applied. |
| window start *k* | `rint(k × step)` | For every *k* with start below the sample count. Window 0 always starts at sample 0. |
| `window_count` | number of window starts below the sample count | Computed in closed form before any analysis. Must not exceed `max_windows`. |
| window position *k* | `k × step` (exact, not rounded) | Used to decide which frame a window belongs to. The rounded start only decides which audio is read. |
| frame period *f* | samples `[f × sr / fps, (f + 1) × sr / fps)` | As before. |
| frame *f* values | mean of the windows whose position is in its period, else the last window that started before the period | Replaces "window that covers the start of the period". Identical at spacing 1. |

## Submission result (additions)

| Field | Type | Meaning |
|-------|------|---------|
| `window_spacing` | number | The spacing actually used (equals the request unless raised) |
| `step_samples` | number | Step in samples used between window starts |
| `window_count` | integer | Number of windows analyzed |
| `spacing_raised` | boolean | True if the 1-sample minimum was applied |

All fields from feature 002 remain.

## Analysis result (change to feature 001's type)

`AnalysisResult` gains `starts`: an integer array with the start sample of each window, in order, and `step`: the exact distance in samples between window positions. If `starts` is absent (results built by hand), starts are taken as `window index × window size`, which is the old behavior. `window_start_times()` is `starts / sample_rate`. Frame averaging uses `window_positions`, which is `index × step` when `step` is known and the starts otherwise.

## Client state (frontend additions)

| State | Meaning |
|-------|---------|
| `fileSampleRate` | Sample rate read from the chosen file's header, or 44,100 when no file is chosen or it cannot be read |
| `spacingText` | The text in the spacing field. Reset to the default whenever the window size, frame rate or `fileSampleRate` changes. |

The existing `idle | busy | done | error` states are unchanged.
