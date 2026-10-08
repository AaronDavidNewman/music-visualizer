# Contract: Threshold Setting (API and UI)

The change to the server's job endpoint and to the settings page. Everything not listed here is as in the earlier contracts.

## `POST /api/jobs`

One new optional multipart form field:

| Field | Type | Default | Rule |
|-------|------|---------|------|
| `threshold` | number as text | `0` | 0 to 10 (percent of the largest note value). Not sent: 0. Sent but empty, not a number (`abc`, `nan`, `inf`), below 0 or above 10: refused. Decimals such as `2.5` are accepted. |

Refusal: HTTP 400 with `{"detail": "The threshold must be a number from 0 to 10."}`, before any audio is read or any job is created.

Success response (200) gains one field, the number used (a whole number is returned as an integer):

```json
{ "threshold": 5 }
```

All other response fields are unchanged.

## Frames

`GET /api/jobs/{job_id}/frames/{index}` is unchanged in format and size: an indexed-colour PNG of 252 × 168 pixels.

| Threshold | Effect |
|-----------|--------|
| `0` | Frames are byte-for-byte what they were before this feature |
| `t > 0` | A drawn note (tiles 0 to 83) whose smoothed value in a frame is **below** `t` percent of the largest smoothed note value in the whole file has a black tile (RGB 0, 0, 0). Every other tile is identical to the tile with the threshold off. |

The comparison is made before the Saturation root and does not depend on it, on the Saturation/Brightness/Hue steps or on the frame brightness. A hidden note still counts as a related note when other tiles' hues are worked out. The note with the largest value is shown at every threshold. Frames for the same file and settings are identical on every request. Details are in [data-model.md](../data-model.md).

## Settings page

- A new **Threshold** slider in the settings column, after Smoothing: left end "Off" (value 0), right end 10, steps of 1, starting at the left end, disabled while a job is running.
- A readout beside it: `Off` at 0, otherwise `n% of the loudest note`.
- An info button beside its label (accessible name "About threshold") opens a popover that explains that a note below the threshold is drawn black, that the threshold is a share of the loudest note in the file, that the left end is off and the right end is 10%.
- The form sends the value as the `threshold` field. A value outside 0 to 10 cannot be chosen with the slider; if the state were somehow invalid the page would block submission, as for other settings.
- The result summary has a new item: `Threshold: Off` or `Threshold: n%`.
