# Contract changes: HTTP API

Changes to `POST /api/jobs` from [feature 002](../../002-audio-frames-ui/contracts/http-api.md) and features 003 to 005. Everything not listed is unchanged, including the frame endpoint and the image layout.

## Request: new field

| Field | Type | Notes |
|-------|------|-------|
| `smoothing` | text, optional | A number from 0.0 to 0.8 inclusive. Leave the field out to use 0.0 (no smoothing). |

For each note, every frame after the first becomes `smoothing × (previous smoothed value) + (1 − smoothing) × (this frame's value)`. The first frame is not changed. Example with `smoothing=0.5` and note values 0, 10, 0, 0 in consecutive frames: 0, 5, 2.5, 1.25.

## Response: new field

```json
{
  "smoothing": 0.5
}
```

| Field | Meaning |
|-------|---------|
| `smoothing` | The smoothing used. 0.0 when the request had no `smoothing` field. |

## New error

| Status | When | `detail` |
|--------|------|----------|
| 400 | `smoothing` is present but is not a finite number from 0.0 to 0.8 (including an empty or blank value, `abc`, `nan`, `inf`, `-0.1`, `0.81` and `1`) | "The smoothing must be a number from 0.0 to 0.8." |

It is returned with the other parameter errors, before the file is stored, so a refused request leaves nothing behind. A missing field is not an error.

## Behavior notes

- With `smoothing=0` (or no field) the frames are identical to those produced before this feature.
- Smoothing changes only the note values and (since feature 007) the tile hues in the frames; each tile's hue is also smoothed over the frames with the same running average (first frame unchanged, hue treated as a plain number from 0 to 1). `frame_count`, `window_count`, `step_samples`, `window_spacing` and the timing of each frame are the same at every smoothing.
- Smoothing acts before the values are scaled to gray levels, so the loudest smoothed value in the file is white. Brightness and the octave layout then apply as before. Since feature 007 the tile's gray level is its HSV value (the brightest channel of its color), and the hue is worked out from the smoothed, scaled and brightened levels of its related notes.

## UI contract additions

| Element | Behavior |
|---------|----------|
| Smoothing slider | A slider from 0.00 (left end) to 0.80 (right end) in steps of 0.01, starting at 0.00. The current value is shown beside it with two decimals. Disabled while a submission runs. Keeps its position after errors and completed submissions. |
| Results summary | Adds the smoothing used, with two decimals. |
