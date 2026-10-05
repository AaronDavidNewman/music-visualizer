# Contract changes: HTTP API

Changes to `POST /api/jobs` from [feature 002](../../002-audio-frames-ui/contracts/http-api.md). Everything not listed there is unchanged, including the frame endpoint.

## Request: new field

| Field | Type | Notes |
|-------|------|-------|
| `window_spacing` | text, optional | A number greater than 0, as a multiple of `window_size`. Omit or leave empty to use the default (one frame period in samples ÷ window size, rounded down to 6 decimals). |

Examples with `window_size=8192`: `window_spacing=0.25` gives windows starting at samples 0, 2048, 4096. `window_spacing=1` gives consecutive windows. `window_spacing=2` leaves gaps.

## Response: new fields

```json
{
  "window_spacing": 0.25,
  "step_samples": 2048,
  "window_count": 7412,
  "spacing_raised": false
}
```

| Field | Meaning |
|-------|---------|
| `window_spacing` | The spacing used. Equals the request unless `spacing_raised` is true, in which case it is `1 / window_size`. |
| `step_samples` | Samples between window starts (may be fractional, such as 1228.8). Each start is rounded to the nearest whole sample. |
| `window_count` | Windows analyzed |
| `spacing_raised` | True when the requested spacing gave a step under 1 sample and was raised to exactly 1 sample |

## New errors

| Status | When | `detail` |
|--------|------|----------|
| 400 | `window_spacing` is not a number, is not finite, or is 0 or negative | "The window spacing must be a number greater than 0." |
| 400 | The request would create more windows than `max_windows` (60,000) | "This would create 2,000,000 windows; the limit is 60,000. Use a larger window spacing." |

The window-count error is returned after the file is read and before any analysis. The existing errors keep their meaning and order.

## Behavior notes

- A step below 1 sample is never an error. It is raised and reported.
- With `window_spacing=1`, the frames are identical to those produced before this feature for the same file, window size and frame rate.
- An omitted `window_spacing` now means the default described above. Before this feature, requests used spacing 1.

## UI contract additions

| Element | Behavior |
|---------|----------|
| Window spacing field | A number input. Shows the default for the current file, frame rate and window size, and is replaced by the new default whenever any of those change. |
| Step hint | Under the field: the step in samples and in milliseconds for the current value, using the file's sample rate. |
| Minimum hint | Shown while the value is below `1 / window size`: tells the user it will be raised to that value. |
| Validation | Blocks submission with "The window spacing must be a number greater than 0." for empty, zero, negative or non-numeric text. |
| Before a file is chosen | The default assumes 44,100 Hz. |
| Results summary | Adds spacing used, step in samples, windows analyzed, and a notice when `spacing_raised` is true. |
