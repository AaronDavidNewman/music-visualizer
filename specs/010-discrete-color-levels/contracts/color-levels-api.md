# Contract: Color Level Steps (API and UI)

The change to the server's job endpoint and to the settings page. Everything not listed here is as in the earlier contracts.

## `POST /api/jobs`

Three new optional multipart form fields. They are named after the labels the page shows, which are not the names of the older `brightness` and `energy` fields (those are the page's Saturation and Brightness *roots* and are unchanged).

| Field | Page label | Allowed values | Default |
|-------|------------|----------------|---------|
| `hue_step` | Hue steps | `N/A`, `12`, `36`, `90`, `180` | N/A |
| `saturation_step` | Saturation steps | `N/A`, `5`, `10`, `20`, `50` | N/A |
| `brightness_step` | Brightness steps | `N/A`, `5`, `10`, `20`, `50` | N/A |

Rules, for each field:

- Not sent: N/A (no rounding).
- `N/A`, in any letter case and with surrounding spaces: N/A.
- A whole number in the list, written as `20` or `20.0`: accepted.
- Anything else is refused: empty, `0`, negative, a number not in that field's list (such as `7`, `51`, or `90` for saturation), `2.5`, text, `nan`, `inf`.

Refusal: HTTP 400, before any audio is read or any job is created, with one of

```json
{ "detail": "The hue step must be N/A or one of 12, 36, 90, 180." }
{ "detail": "The saturation step must be N/A or one of 5, 10, 20, 50." }
{ "detail": "The brightness step must be N/A or one of 5, 10, 20, 50." }
```

Success response (200) gains three fields, each `null` for N/A or the number used:

```json
{ "hue_step": null, "saturation_step": 20, "brightness_step": 50 }
```

All other response fields are unchanged.

## Frames

`GET /api/jobs/{job_id}/frames/{index}` is unchanged in format and size: an indexed-colour PNG of 252 × 168 pixels. With every step N/A the frames are byte-for-byte what they were before this feature.

For a step `s` on a scale `R` (360 for hue, 100 for saturation and brightness) the property takes only the values `0, s, 2s … R` (`R / s + 1` levels, 3 at the largest step). Rounding is to the nearest level, halves up, and is applied after smoothing and the root settings; a frame's result does not depend on other frames. Details and examples are in [data-model.md](../data-model.md).

| Setting | Effect on a frame |
|---------|-------------------|
| `hue_step` | Each tile's hue is one of the hue levels (degrees) |
| `saturation_step` | Each tile's saturation is one of the saturation levels |
| `brightness_step` | The frame's brightness (shared by all tiles) is one of the brightness levels; the loudest frame stays at 100 and silence at 0 (black) |

Frames for the same file and settings are identical on every request.

## Settings page

- Three **dropdown lists** in the settings column, in a row below Saturation/Brightness, in the order **Hue steps**, **Saturation steps**, **Brightness steps**. Options are the allowed values above, starting at N/A, and each is disabled while a job is running.
- Beside each dropdown, a readout of the level count: `N/A (smooth)`, or the chosen value and its level count such as `20 (6 levels)` (hue: 12 → 31, 36 → 11, 90 → 5, 180 → 3; the others: 5 → 21, 10 → 11, 20 → 6, 50 → 3).
- An info button beside each label (accessible names "About hue steps", "About saturation steps", "About brightness steps") opens a popover explaining the setting, that N/A means smooth, that a larger step gives fewer, bolder levels, and the allowed choices. The Hue text also says that the two ends of the wheel are both red.
- The form sends the selected option as text (`N/A` or the number) in the three fields above. Only the listed options can be selected, so there is no inline error message for these fields; if the state were somehow invalid the page would block submission, as for other settings.
- The result summary gains three items: "Hue steps: N/A" or "Hue steps: 36", and likewise for "Saturation steps" and "Brightness steps".
