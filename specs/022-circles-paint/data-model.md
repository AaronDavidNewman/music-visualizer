# Data Model: Circles Paint

No stored data. This describes how a Circles paint frame is made from the circle plan and the canvas, and the new image type's settings and group.

## The image type

| Request value | Label on the page | Group id and title |
|---------------|-------------------|--------------------|
| `circles_paint` | Circles paint | `circles_paint`, "Circles paint" |

`IMAGE_TYPES = ("tiles", "blended", "contour", "circles", "circles_paint")`; the refusal message is `The image type must be one of tiles, blended, contour, circles, circles_paint.`

## What a frame is

For frame `t` (0-based) of a job:

| Quantity | Definition |
|----------|------------|
| `added[t]` | The circles put down in frame `t`, weakest first, exactly as `plan_circles` yields them for Circles: each `(x, y, color index)`; the place from the rank's previous place, the note's angle and distance (Movement times `width / 252`), the stay-in-place rule, the wrap; the color index is the square root of the note's share of the file's loudest smoothed value, 0 to 255. Only notes with energy; at most `notes` (5 to 12). |
| `radius(circle)` | `Radius × (width / 252) × resize_factor(color index)` in pixels, where `resize_factor` is 1 (off) or `1 + 2 c / 255`. |
| `canvas[-1]` | The plain background: the colormap's color at row 128 of its table, 600 × 400. |
| `canvas[t]` | `canvas[t-1]` with the circles of `added[t]` painted on it, in order (weakest first, so the strongest is on top). |
| frame file `t` | `canvas[t]` as an RGB PNG. |

There is **no memory**: nothing is kept but the canvas; no circle is dropped, counted or faded.

## Painting one circle

Given `(x, y)`, `r`, the color `c` and the canvas:

1. The patch is the whole-pixel box `[floor(x - r) - 1, ceil(x + r) + 1)` by `[floor(y - r) - 1, ceil(y + r) + 1)`.
2. The coverage mask is the disc `(x - r .. x + r, y - r .. y + r)` drawn on an `L` image of the patch at `SUPERSAMPLE` (4) times the size (the far end of the box minus one, as in Circles), averaged down by 4: 0 outside, 255 well inside, in between on the edge.
3. The patch and mask are clipped to the canvas (a circle past an edge is cut off; it is not painted on the opposite side).
4. Each canvas pixel in the patch becomes `canvas × (1 − m / 255) + c × (m / 255)` with `m` the mask value (Pillow's `paste` with a color and a mask).

Consequences: a pixel well inside a circle has exactly the circle's color whatever was under it; a pixel the mask does not touch (`m = 0`) is unchanged; a pixel outside every circle's patch is unchanged.

## Settings

| Setting | Request field | Range and default | Used by Circles paint |
|---------|---------------|-------------------|-----------------------|
| Movement | `circle_unit` | 1 to 10, 4 | yes |
| Radius | `circle_radius` | 4 to 8, 4 | yes |
| Resize by volume | `circle_resize` | true/false, false | yes |
| Notes | `circle_notes` | 5 to 12, 8 | yes |
| Memory | `circle_memory` | 100 to 500, 300 | no: validated like every circle setting and ignored; not shown on the page |
| Smoothing, Smoothing window, Colormap | as before | as before | yes (smoothing before the choice of the strongest notes; the colormap for colors and the background) |
| Interpolate, Oversampling, Threshold, Notes 12 to 84, Blend width | as before | as before | no: accepted and ignored; not shown |

Messages, ranges and the scaling of Movement and Radius against the 252-pixel reference frame are those of Circles.

## The page

The group after Image type for `circles_paint`:

| Group id | Title | Controls in order (rows) |
|----------|-------|--------------------------|
| `circles_paint` | Circles paint | `circle-unit` (Movement), `circle-radius` (Radius); `circle-resize` (Resize by volume), `circle-notes` (Notes) (2 + 2) |

Data smoothing is shown; Image smoothing is not (as for Circles). The values of Movement, Radius, Resize by volume and Notes are the form's, shared with Circles, so switching between the two types keeps them; Memory keeps its value for Circles.

Result summary for the type: Movement, Radius, Resize by volume, Notes (each with its readout), and no Memory line.
