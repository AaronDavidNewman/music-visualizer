# Contract: The Circles paint image type (API and UI)

The change to the job endpoint and the settings page. Everything not listed here is as in the earlier contracts.

## `POST /api/jobs`

The existing optional field `image_type` accepts a fifth value, `circles_paint`. No new field is added: the circle fields are those of Circles.

| Field | Rule for `circles_paint` |
|-------|--------------------------|
| `image_type` | Exactly `tiles`, `blended`, `contour`, `circles` or `circles_paint` (lowercase, no spaces). Anything else, including empty: refused with `The image type must be one of tiles, blended, contour, circles, circles_paint.` (HTTP 400, before any audio is read). |
| `circle_unit`, `circle_radius`, `circle_resize`, `circle_notes` | As for `circles` (same ranges, defaults, parsing, messages); they have an effect. |
| `circle_memory` | Validated as for every image type (`The circle memory must be a whole number from 100 to 500.` if not), then **ignored**: the frames are the same whatever it is. |
| `interpolate`, `resolution`, `note_count`, `threshold`, `blend_width` | Validated as before, accepted and ignored. |
| `smoothing`, `smoothing_window`, `colormap` | Apply. |

The response is as for `circles`: `image_type` is `circles_paint` and the circle settings used are reported (including `circle_memory`, the value sent or its default).

## The frames

`GET /api/jobs/{job_id}/frames/{index}` (unchanged URL and names): for `circles_paint` the body is an RGB PNG of **600 × 400** pixels.

- Frame 0 is the background (the colormap's middle color) with the circles of frame 0 painted on it.
- Frame `t > 0` is frame `t − 1` with the circles of frame `t` painted on top, weakest first (the strongest on top). Every pixel that the circles of frame `t` do not touch equals the same pixel of frame `t − 1`.
- A circle is solid: the pixels well inside it have exactly its color; the pixels on its edge are a mix of its color and what was there. A circle past an edge is cut off by it (it is not painted again on the opposite side).
- Nothing fades and nothing is cleared. A frame without sound is an exact copy of the frame before.
- Which circles, where, with which color and radius: exactly as in `circles` for the same settings and music.

The number, names and timing of the frames are those of the other types. The four other image types are byte-identical to before.

## The page

| Part | Rule |
|------|------|
| Image type | the dropdown offers Tiles, Blended tiles, Contour, Circles and Circles paint; Tiles is selected at the start; its info text also describes Circles paint |
| Group after Image type | for Circles paint, a group titled **Circles paint** with Movement, Radius, Resize by volume and Notes (two to a row); no Memory |
| Data smoothing | shown; Image smoothing not shown |
| Other type groups | not shown; the values of controls that the chosen type does not use are kept and still sent |
| Result summary | names the image type and shows Movement, Radius, Resize by volume and Notes for Circles paint (Memory for Circles only); lines for settings the type does not use are not shown |
