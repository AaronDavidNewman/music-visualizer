# Data Model: Note Smoothing

Only the changes and additions to features 001 to 005 are listed.

## Constants

| Name | Value | Meaning |
|------|-------|---------|
| `MIN_SMOOTHING` | 0.0 | Lowest allowed smoothing; also the default (`DEFAULT_SMOOTHING`): no smoothing |
| `MAX_SMOOTHING` | 0.8 | Highest allowed smoothing |

Fixed by the spec; not settings.

## Smoothing (request field)

| Field | Type | Rules |
|-------|------|-------|
| `smoothing` | text parsed as a number, optional | Field absent: 0.0. Present: must be a finite number from 0.0 to 0.8 inclusive. An empty string, blank text, `abc`, `nan`, `inf`, `-0.1`, `0.81` and `1` are refused. |

## The running average

For the frame values `x` (rows = frames in time order, columns = the 88 notes) and smoothing `s`:

| Step | Definition |
|------|------------|
| First frame | `y[0] = x[0]` (nothing before it, so it is not smoothed) |
| Later frames | `y[n] = s × y[n-1] + (1 − s) × x[n]`, for each note separately |
| `s = 0` | `y = x` exactly (a copy; nothing is computed) |
| One frame or none | Returned unchanged |

Properties (all tested): the first row is unchanged for every `s`; each note's output depends only on that note's own column; for `x = 0, 10, 0, 0` and `s = 0.5` the output is `0, 5, 2.5, 1.25`; after a note drops from 100 to 0 it is below 10 after 4 frames at `s = 0.5`, 11 frames at `s = 0.8` and 1 frame at `s = 0`.

## Pipeline order

`average_frames` → **`smooth_frames`** → `to_gray_levels` (scaled against the largest smoothed value across all 88 notes) → brightness root → tile hues (feature 007) → **hue smoothing** (the same recurrence, per tile, on the hues) → colors → octave grid drawing. Nothing before `smooth_frames` (analysis, window spacing, frame averaging, frame count, timing) changes.

## Submission result (addition)

| Field | Type | Meaning |
|-------|------|---------|
| `smoothing` | number | The smoothing used (0.0 when none was sent) |

## Client state (frontend additions)

| State | Meaning |
|-------|---------|
| `smoothing` | The slider value, a number from 0 to 0.8 in steps of 0.01. Starts at 0. Kept after errors and completed submissions. Not changed by other fields. |

`JobSettings` gains `smoothing: number`, rounded to two decimals before it is sent.
