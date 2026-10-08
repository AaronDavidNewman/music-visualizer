# Data Model: Note Threshold

Only what changes from the frame colors of the earlier features (including 010) is listed.

## Constants

| Name | Value | Where | Meaning |
|------|-------|-------|---------|
| `MIN_THRESHOLD` / `MAX_THRESHOLD` | 0 / 10 | `frame_rendering.py` | Allowed threshold, percent of the largest note value |
| `DEFAULT_THRESHOLD` | 0 | `frame_rendering.py` | Off |

Frontend: `THRESHOLD_RANGE = { min: 0, max: 10, step: 1 }`, `DEFAULT_THRESHOLD = 0` in `validation.ts`.

## Threshold

One number `t` per job, from 0 to 10. `t = 0` means off. Otherwise it is `t` percent of the largest note value.

## Largest note value

`peak = max(smoothed)` over every note (all 88) of every frame, where `smoothed = smooth_frames(note values, smoothing)`. This is the value that `to_gray_levels` scales against.

## Hidden notes

For frame `f` and a drawn note `n` (0..83):

```
hidden[f, n]  =  smoothed[f, n] < (t / 100) * peak
```

- Strictly below hides; a value equal to the threshold is shown.
- `t = 0`: `smoothed < 0` is never true (values are never negative), so nothing is hidden.
- The note whose value is `peak` is never hidden (`t ≤ 10`).
- `peak = 0` (no note has a value): `0 < 0` is false, so nothing is hidden by the mask and there is no division.
- It depends only on the note's own smoothed value and the file's `peak`, not on the Saturation root, the steps, the hue or the frame brightness.

## Pipeline

For each frame, in `write_frames`:

1. `smoothed = smooth_frames(frames, smoothing)`; gray levels = `to_gray_levels(smoothed)` (unchanged).
2. **`hidden = hidden_notes(smoothed, t)`**, shape `(frames, 84)`.
3. Hues, saturations, brightness and level steps are worked out for all 84 tiles exactly as before, **including the hue shifts that hidden notes cause in other tiles**.
4. `tile_colors(..., hidden=hidden[f])` sets the RGB of the hidden tiles to `(0, 0, 0)`.
5. Palette PNG as before.

## Examples

A file whose largest smoothed note value is 100. A note at 8 and another at 4, with the threshold at 6 (hide below 6): the note at 4 is black; the note at 8 is drawn as with the threshold off. At 8 (the note at 8 is exactly at the threshold) the note at 8 is shown and the one at 4 is hidden. At 10 the note at 8 is hidden too, and only notes of 10 or more remain.

## API and page

Request field `threshold` (percent, 0 to 10, default 0) and response field `threshold` (the number used; `0` for off). Page: `JobSettings.threshold: number`, `JobResult.threshold: number`; readout `Off` at 0, else `n% of the loudest note`; summary `Threshold: Off` or `Threshold: n%`.
