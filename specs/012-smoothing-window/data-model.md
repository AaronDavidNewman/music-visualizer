# Data Model: Smoothing Window

Only what changes from the earlier features is listed.

## Constants

| Name | Value | Where | Meaning |
|------|-------|-------|---------|
| `MIN_SMOOTHING_WINDOW` / `MAX_SMOOTHING_WINDOW` | 1 / 20 | `frame_rendering.py` | Allowed smoothing window, a whole number of frames |
| `DEFAULT_SMOOTHING_WINDOW` | 1 | `frame_rendering.py` | Window used when none is given |
| `MIN_SMOOTHING` / `MAX_SMOOTHING` / `DEFAULT_SMOOTHING` | 0.0 / 0.8 / 0.0 | `frame_rendering.py` | Unchanged range of `s` |

Frontend: `SMOOTHING_WINDOW_RANGE = { min: 1, max: 20 }`, `DEFAULT_SMOOTHING_WINDOW = 1` in `validation.ts`. `SMOOTHING_RANGE` is unchanged.

## Smoothing window `w` and smoothing `s`

- `w`: whole number, 1 to 20, default 1: how many earlier frames are mixed into each frame.
- `s`: number, 0.0 to 0.8, default 0: the weight of each earlier frame in the window; the current frame has weight 1.

## Smoothed value

For an unsmoothed series `A[0 … T−1]` (one series per note, per tile hue, and one for the frame brightness):

```
k(t)        = min(t, w)                          earlier frames available
S[t]        = A[t] + s · ( A[t−1] + … + A[t−k(t)] )
smoothed[t] = S[t] / ( 1 + s · k(t) )
```

- `smoothed[0] = A[0]` (no earlier frames).
- `s = 0`: `smoothed[t] = A[t]` for every `t` and every `w`; the function returns an exact copy.
- A constant series stays constant (up to one rounding of the division).
- Only `A[t]` and the `k(t)` earlier frames are used: no later frame, and no earlier *smoothed* value. A value `A[i]` therefore contributes to frames `i … i + w` only (weight 1 at `i`, `s` after) and is gone from frame `i + w + 1` on.
- Each series is smoothed on its own: a note's value never mixes with another note's, a tile's hue never with another tile's.
- Hue is a plain 0..1 number (0° to 360°), not a circle, as before.

### Worked examples

`w = 2`, `s = 0.5`, values 8, 4, 2:

| t | terms | sum of weights | result |
|---|-------|----------------|--------|
| 0 | 8 | 1 | 8 |
| 1 | 4 + 0.5·8 = 8 | 1.5 | 5.333 |
| 2 | 2 + 0.5·4 + 0.5·8 = 8 | 2 | 4 |

`w = 3`, `s = 0.5`, a note that has value 1 in one frame `k ≥ 3` and 0 elsewhere:

| frame | smoothed value |
|-------|----------------|
| `k` | 1 / 2.5 = 0.4 |
| `k+1`, `k+2`, `k+3` | 0.5 / 2.5 = 0.2 |
| `k+4` and later | exactly 0 |

## Pipeline

In `write_frames`, with the same `s` and `w` for all three:

1. Note values: `smoothed = smooth_frames(frames, s, w)` → gray levels (scaled against the largest smoothed value), hidden-note mask (threshold, feature 011): unchanged use.
2. Hues: `hue_sequence(levels, root, s, w)` computes each frame's tile hues from the gray levels and smooths them with `smooth_frames` (then the hue step rounds them, feature 010).
3. Frame brightness: `value_sequence(energies, energy_root, s, w)` → brightness step rounding.
4. Everything after (roots, level steps, threshold, drawing) is as before.

## API and page

Request field `smoothing_window` (whole number 1 to 20, default 1) and response field `smoothing_window` (the integer used). Page: `JobSettings.smoothingWindow: number`, `JobResult.smoothing_window: number`; summary `Smoothing window: n`.
