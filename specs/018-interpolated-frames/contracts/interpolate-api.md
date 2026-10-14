# Contract: Interpolate (API and UI)

The change to the server's job endpoint and to the settings page. Everything not listed here is as in the earlier contracts.

*(Amended 2026-10-13: the first version also had an `interpolate_function` field and a function dropdown; they were removed and only blend is made.)*

## `POST /api/jobs`

One new optional multipart form field:

| Field | Type | Default | Rule |
|-------|------|---------|------|
| `interpolate` | text | `1` | A whole number from 1 to 5 (`3` and `3.0` are accepted). Not sent: `1`. Sent but empty, not a number, fractional (`2.5`), below 1 (`0`) or above 5 (`6`), or not finite (`nan`): refused. |

Refusal: HTTP 400, before any audio is read or any job is created:

```json
{ "detail": "The interpolate value must be a whole number from 1 to 5." }
```

**Removed field.** `interpolate_function` is no longer part of the endpoint. A request that still sends it (with any value, an invalid one included) is accepted and the field is ignored: the frames are identical to those of the same request without it, and the response has no such key.

The setting works with every `image_type` and with `smoothing`, `smoothing_window`, `threshold`, `colormap`, `blend_width`, `resolution` and `note_count`. All other fields are unchanged.

Success response (200): one field is added, the value used:

```json
{ "interpolate": 5 }
```

All other response fields are unchanged. The frame count, the `frame_url_template` and the frame size (252 × 168 PNG) are the same at every interpolate value. With `interpolate` 1, or not sent, the frames are exactly those made before this feature.

## `GET` of a frame

The URL is as before. Every frame number up to the count exists. At interpolate n above 1 the frames 1, n + 1, 2n + 1 and so on (counted from 1) and the last frame are the pictures of the music, byte-identical to those of interpolate 1; the others are RGB PNGs made by blending their neighbors with weight k / g in their gap.

## Page

| Element | Behavior |
|---------|----------|
| Interpolate slider | 1 to 5 in steps of 1, starting at 1, after the Resolution control; disabled while a job runs. |
| Readout | `1 (every frame drawn)` at 1; otherwise `3 (one frame in 3 drawn)`. |
| Info button | Only every n-th frame is drawn, the frames between are made by blending their neighbors, so a contour job is faster. |
| Result summary | `Interpolate: 1`, or `Interpolate: 5`. |
| Frame player | Unchanged. |
