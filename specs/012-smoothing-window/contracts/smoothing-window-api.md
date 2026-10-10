# Contract: Smoothing Window (API and UI)

The change to the server's job endpoint and to the settings page. Everything not listed here is as in the earlier contracts.

## `POST /api/jobs`

One new optional multipart form field:

| Field | Type | Default | Rule |
|-------|------|---------|------|
| `smoothing_window` | whole number as text | `1` | 1 to 20. Not sent: 1. Sent but empty, not a number (`abc`, `nan`, `inf`), not a whole number (`2.5`), or outside 1 to 20 (`0`, `21`): refused. `5` and `5.0` are accepted. |

Refusal: HTTP 400 with `{"detail": "The smoothing window must be a whole number from 1 to 20."}`, before any audio is read or any job is created.

Success response (200) gains one field, an integer:

```json
{ "smoothing_window": 1 }
```

All other response fields are unchanged. The existing `smoothing` field keeps its range (0.0 to 0.8, default 0) but **its meaning changes** (see below).

## Smoothing

For each note value, each tile's hue and the frame brightness, frame *t* is `( A[t] + s·A[t−1] + … + s·A[t−w] ) / ( 1 + s·k )` with `k = min(t, w)` earlier frames, `s` the smoothing, `w` the smoothing window and `A` the unsmoothed values (see [data-model.md](../data-model.md)).

| Setting | Effect |
|---------|--------|
| `smoothing = 0` | Frames are byte-for-byte what they were before this feature, for every window |
| `smoothing > 0`, `smoothing_window = w` | Each frame is mixed with the `w` frames before it; a value that stops is gone exactly `w` frames later. Frames differ from those made before this feature with the same `smoothing` (the old smoothing was an endless running average). |

The gray levels, the Saturation and Brightness roots, the level steps and the threshold are applied after smoothing, to the smoothed values, as before. Frames for the same file and settings are identical on every request. Image format and size are unchanged.

## Settings page

- A new **Smoothing window (frames)** number field directly above the Smoothing slider: whole numbers 1 to 20, step 1, starting at 1, disabled while a job is running.
- An info button beside its label (accessible name "About smoothing window") opens a popover explaining that the window is how many earlier frames are mixed into each frame, that Smoothing says how strongly each of them counts compared with the current frame, and the allowed range.
- The Smoothing explanation is rewritten for the new meaning of the setting; its range and 0.01 steps are unchanged.
- An invalid value shows "The smoothing window must be a whole number from 1 to 20." under the field, makes "Create frames" unavailable, and nothing is sent.
- The form sends the value as the `smoothing_window` field.
- The result summary has a new item, "Smoothing window: n".
