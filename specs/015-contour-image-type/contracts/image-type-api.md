# Contract: Image type `contour` (API and UI)

The change to the server's job endpoint and to the settings page. Everything not listed here is as in the earlier contracts.

## `POST /api/jobs`

The existing optional form field `image_type` accepts a third value:

| Field | Type | Default | Rule |
|-------|------|---------|------|
| `image_type` | text | `tiles` | Exactly `tiles`, `blended` or `contour` (lowercase, no spaces). Not sent: `tiles`. Sent but empty or anything else (`Contour`, ` contour`, `contours`): refused. |

Refusal: HTTP 400, before any audio is read or any job is created:

```json
{ "detail": "The image type must be one of tiles, blended, contour." }
```

`blend_width` is validated as before (a number from 10 to 25, otherwise 400), and has no effect with `image_type=contour`, as with `tiles`.

All other fields are unchanged: `file`, `window_size`, `frame_rate`, `window_spacing`, `smoothing`, `smoothing_window`, `threshold`, `colormap`.

Success response (200): no new key. `image_type` is `contour`. The frame count and the `frame_url_template` are the same as for the other types.

## `GET` of a frame

The URL is as before. For `contour` the body is a PNG of exactly 252 × 168 pixels (RGBA, all pixels opaque), made by matplotlib's `savefig`. For `tiles` and `blended` the bytes are exactly what they were before this feature.

## Page

| Element | Behavior |
|---------|----------|
| Image type dropdown | Offers **Tiles**, **Blended tiles**, **Contour**, in that order; starts at Tiles. |
| Image type info button | The popover also describes Contour. |
| Blend width slider | Enabled only while **Blended tiles** is chosen (and no job is running); disabled for Tiles and for Contour. |
| Result summary | "Image type: Contour"; no Blend width line (that line is shown for Blended tiles only). |
| Frame player | Unchanged; it plays any 252 × 168 PNG. |
