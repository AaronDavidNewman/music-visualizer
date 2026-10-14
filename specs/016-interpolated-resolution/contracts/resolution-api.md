# Contract: Resolution (API and UI)

> **Amended 2026-10-14 (feature 020, grouped settings).** The **Resolution** control is now called **Oversampling** on the page, in its info text, in its validation message (`The oversampling must be a whole number from 1 to 5.`, on the client and the server) and in the result summary, and it sits in the **Image smoothing** group with Interpolate, which is not shown for Circles. The request field is still `resolution` and nothing about the interpolation changed. Where this document says Resolution (the control, the slider, the message), read Oversampling; see `specs/020-grouped-settings-ui/`.

The change to the server's job endpoint and to the settings page. Everything not listed here is as in the earlier contracts.

## `POST /api/jobs`

One new optional multipart form field:

| Field | Type | Default | Rule |
|-------|------|---------|------|
| `resolution` | text | `1` | A whole number from 1 to 5 (`3` and `3.0` are accepted). Not sent: `1`. Sent but empty, not a number, fractional (`2.5`), below 1 (`0`) or above 5 (`6`), or not finite (`nan`): refused. |

Refusal: HTTP 400, before any audio is read or any job is created:

```json
{ "detail": "The resolution must be a whole number from 1 to 5." }
```

The resolution works with every `image_type` (`tiles`, `blended`, `contour`) and with `smoothing`, `smoothing_window`, `threshold`, `colormap` and `blend_width`. All other fields are unchanged.

Success response (200): one field is added, the resolution used:

```json
{ "resolution": 3 }
```

All other response fields are unchanged. The frame count, the `frame_url_template` and the frame size (252 × 168 PNG) are the same at every resolution. With `resolution` 1, or not sent, the frames are exactly those made before this feature.

## Page

| Element | Behavior |
|---------|----------|
| Resolution slider | 1 to 5 in steps of 1, starting at 1; disabled while a job runs. |
| Readout | `1×` at 1; otherwise the multiple and the grid size, for example `3× (36 × 21)`. |
| Info button | The popover explains that the picture is made finer by interpolating between the notes, 1× is the original 12 × 7 grid, the highest is 5×, and tiles get smaller (or contour steps finer) in the same picture size. |
| Result summary | A line `Resolution: 3× (36 × 21)` (`Resolution: 1×` at 1). |
| Frame player | Unchanged; it plays any 252 × 168 PNG. |
