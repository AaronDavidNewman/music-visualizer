# Contract: The circles image type (API and UI)

The change to the server's job endpoint and to the settings page. Everything not listed here is as in the earlier contracts.

## `POST /api/jobs`

The existing optional field `image_type` accepts a fourth value, `circles`, and four new optional multipart form fields are added:

| Field | Type | Default | Rule |
|-------|------|---------|------|
| `image_type` | text | `tiles` | Exactly `tiles`, `blended`, `contour` or `circles` (lowercase, no spaces). Anything else, including an empty value: refused. |
| `circle_unit` | text | `4` | A whole number from 1 to 10 (`4` and `4.0` accepted). Empty, not a number, fractional, out of range or not finite: refused. |
| `circle_size` | text | `25` | A whole number from 25 to 50 (the circumference of a circle in pixels). Same rules. |
| `circle_resize` | text | `false` | `true`, `false`, `1` or `0`, any case, surrounding spaces ignored. Anything else, including empty: refused (`The circle resize must be true or false.`). When true, a circle's radius is scaled from 1 (faintest, never smaller than the size) to 3 (loudest) by its note's strength. |
| `circle_memory` | text | `300` | A whole number from 100 to 500. Same rules. |
| `circle_notes` | text | `8` | A whole number from 5 to 12. Same rules. |

Refusals: HTTP 400, before any audio is read or any job is created:

```json
{ "detail": "The image type must be one of tiles, blended, contour, circles." }
{ "detail": "The circle unit must be a whole number from 1 to 10." }
{ "detail": "The circle size must be a whole number from 25 to 50." }
{ "detail": "The circle resize must be true or false." }
{ "detail": "The circle memory must be a whole number from 100 to 500." }
{ "detail": "The number of circle notes must be a whole number from 5 to 12." }
```

The four circle fields are validated whatever the image type is, and have no effect unless it is `circles`. With `image_type=circles` the fields `interpolate`, `resolution`, `note_count`, `threshold` and `blend_width` are still validated as before and are accepted and ignored (the frames are the same whatever they are). `smoothing`, `smoothing_window` and `colormap` apply.

Success response (200): four fields are added, the values used:

```json
{ "image_type": "circles", "circle_unit": 4, "circle_size": 25, "circle_resize": false, "circle_memory": 300, "circle_notes": 8 }
```

All other response fields are unchanged; the frame count, the `frame_url_template` and the frame size (252 × 168 PNG) are the same as for the other image types. For `tiles`, `blended` and `contour` the frames are exactly those made before this feature.

## `GET` of a frame

The URL is as before. For `circles` the body is an RGB PNG of 252 × 168 pixels: a background in the colormap's middle color with the circles of the memory, each with an opacity that falls with its age.

## Page

| Element | Behavior |
|---------|----------|
| Image type dropdown | Offers **Tiles**, **Blended tiles**, **Contour**, **Circles**, in that order; starts at Tiles. |
| Unit, Size, Memory, Circles per frame | Four sliders (1 to 10 with the readout `4 px`; 25 to 50 with `25 px around`; 100 to 500 with `300 circles`; 5 to 12 with `8 notes`), each with an info button, shown only while Circles is chosen. |
| Interpolate, Resolution, Notes, Threshold, Blend width | Disabled while Circles is chosen (Blend width is also disabled for Tiles and Contour, as before); enabled again for the other types. |
| Image type info button | The popover also describes Circles. |
| Result summary | For circles: `Image type: Circles`, `Circle unit: 4 px`, `Circle memory: 300`, `Circles per frame: 8`; the lines for Threshold, Resolution, Notes, Interpolate and Blend width are not shown. |
| Frame player | Unchanged. |
