# Contract: Image Type and Blend Width (API and UI)

The change to the server's job endpoint and to the settings page. Everything not listed here is as in the earlier contracts.

## `POST /api/jobs`

Two new optional multipart form fields:

| Field | Type | Default | Rule |
|-------|------|---------|------|
| `image_type` | text | `tiles` | Exactly `tiles` or `blended` (lowercase, no spaces). Not sent: `tiles`. Sent but empty or anything else (`Blended`, ` tiles`, `gradient`): refused. |
| `blend_width` | number as text | `25` | 10 to 25 (percent of the tile width, which is 21 pixels). Not sent: 25. Sent but empty, not a number (`abc`, `nan`, `inf`), below 10 or above 25: refused. Decimals such as `12.5` are accepted. With `image_type=tiles` it is accepted and has no effect on the pictures. |

Refusals: HTTP 400, before any audio is read or any job is created, with one of

```json
{ "detail": "The image type must be one of tiles, blended." }
{ "detail": "The blend width must be a number from 10 to 25." }
```

Success response (200) gains two fields: the image type used and the blend width used (a whole number is returned as an integer), always both, also for `tiles`:

```json
{ "image_type": "blended", "blend_width": 25 }
```

All other response fields are unchanged.

## Frames

`GET /api/jobs/{job_id}/frames/{index}` is unchanged in URL, media type (`image/png`), cache header and picture size (252 × 168 pixels).

| `image_type` | Picture |
|--------------|---------|
| `tiles` | Exactly the picture made before this feature: an indexed-colour PNG of 12 × 7 flat tiles. Identical for every `blend_width`. |
| `blended` | The same grid with the same finished tile colors, but with a Gaussian feather (a Gaussian blur of the edge, cut off at the reach) across every edge shared by two tiles, reaching `blend_width` percent of the tile width (21 px) on each side of the edge, the same distance in pixels in both directions. Pixels outside the bands have exactly their tile's color; the outer border of the picture is not blended. A true-color (RGB) PNG. |

The finished tile colors are decided by everything else (analysis, smoothing and window, the roots, the level steps, the threshold, the hue and the frame brightness) and are the same for both types. Details and the exact weights are in [data-model.md](../data-model.md). Frames for the same file and settings are identical on every request.

## Settings page

- An **Image type** dropdown offering **Tiles** and **Blended tiles**, starting at Tiles, with an info button (accessible name "About image type") whose popover says in a few words what each type looks like. Disabled while a job is running.
- A **Blend width** slider from 10 to 25 in steps of 1, starting at 25, with the readout `n% of a tile` and an info button (accessible name "About blend width") explaining that it is how far the fade reaches on each side of an edge. Disabled while a job is running and while Tiles is selected (its value is still sent).
- The form sends `image_type` and `blend_width`.
- The result summary has a new item `Image type: Tiles` or `Image type: Blended tiles` and, for blended, `Blend width: n%`.
