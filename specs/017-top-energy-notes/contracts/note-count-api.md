# Contract: Number of notes (API and UI)

The change to the server's job endpoint and to the settings page. Everything not listed here is as in the earlier contracts.

## `POST /api/jobs`

One new optional multipart form field:

| Field | Type | Default | Rule |
|-------|------|---------|------|
| `note_count` | text | `84` | A whole number from 12 to 84 (`36` and `36.0` are accepted). Not sent: `84`. Sent but empty, not a number, fractional (`36.5`), below 12 (`11`) or above 84 (`85`), or not finite (`nan`): refused. |

Refusal: HTTP 400, before any audio is read or any job is created:

```json
{ "detail": "The number of notes must be a whole number from 12 to 84." }
```

The setting works with every `image_type` (`tiles`, `blended`, `contour`) and with `smoothing`, `smoothing_window`, `threshold`, `colormap`, `blend_width` and `resolution`. All other fields are unchanged.

Success response (200): one field is added, the number of notes used:

```json
{ "note_count": 36 }
```

All other response fields are unchanged. The frame count, the `frame_url_template` and the frame size (252 × 168 PNG) are the same for every number of notes. With `note_count` 84, or not sent, the frames are exactly those made before this feature.

## Page

| Element | Behavior |
|---------|----------|
| Notes slider | 12 to 84 in steps of 1, starting at 84, after the Threshold control; disabled while a job runs. |
| Readout | `All 84 notes` at 84; otherwise `36 of 84 notes`. |
| Info button | The popover explains that only the notes with the most energy in the whole file are used, that the picture is spread from them, that fewer notes make bigger features (and can make the picture steadier or not), and the range 12 to 84. |
| Result summary | A line `Notes: All 84` or `Notes: 36 of 84`. |
| Frame player | Unchanged. |
