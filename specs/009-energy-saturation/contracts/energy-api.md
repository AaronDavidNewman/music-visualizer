# Contract: Energy Setting (API and UI)

The change to the server's job endpoint and to the settings page. Everything not listed here is as in the earlier contracts.

## `POST /api/jobs`

One new optional multipart form field:

| Field | Type | Default | Rule |
|-------|------|---------|------|
| `energy` | whole number as text | `1` | 1 to 8. Not sent: 1. Sent but empty, not a whole number (`2.5`, `abc`), or outside 1 to 8 (`0`, `9`): refused. |

Refusal: HTTP 400 with `{"detail": "The energy must be a whole number from 1 to 8."}`, before any audio is read or any job is created. Whole numbers written as `2` or `2.0` are accepted.

Success response (200) gains one field:

```json
{ "energy": 1 }
```

All other response fields are unchanged: `job_id`, `file_name`, `sample_rate`, `duration_seconds`, `window_size`, `frame_rate`, `frame_count`, `brightness`, `smoothing`, `window_spacing`, `step_samples`, `window_count`, `spacing_raised`, `frame_url_template`.

## Frames

`GET /api/jobs/{job_id}/frames/{index}` is unchanged in format and size: an indexed-colour PNG of 252 × 168 pixels. Each frame's 84 tiles share one saturation derived from that frame's energy (see [data-model.md](../data-model.md)), and keep their own value (brightness) and hue.

| Input | Saturation of the frame |
|-------|-------------------------|
| Loudest frame of the file | 100% |
| Frame with energy `x` times the loudest, root `r` | `x ** (1 / r)` (smoothed over frames when smoothing is above 0) |
| Frame with no energy, or a silent file | 0% (a silent file is entirely black) |

Frames for the same file and settings are identical on every request.

## Settings page

- A new **Energy** field in the settings column, in the same row as Brightness. Number input, whole numbers 1 to 8, default 1, disabled while a job is running.
- An info button beside its label (accessible name "About energy") opens a popover with the explanation, as for the other settings.
- An invalid value shows "The energy must be a whole number from 1 to 8." under the field, makes "Create frames" unavailable, and nothing is sent.
- The form sends the value as the `energy` field.
- The result summary has a new item, "Energy: n".
