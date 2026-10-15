# Contract: The size of the frames (files and player)

The change to the frames that a job produces and to how the page shows them. The request fields and the response fields of `POST /api/jobs` do **not** change; neither does the URL of a frame.

## The frame files

`GET /api/jobs/{job_id}/frames/{index}` (unchanged URL and names `frame_000000.png` and up):

| Property | Value |
|----------|-------|
| Width × height | **600 × 400 pixels**, for every image type (`tiles`, `blended`, `contour`, `circles`), every `resolution` (1 to 5), every `interpolate` (1 to 5), every other setting. Before: 252 × 168. |
| Shape | 3:2 |
| Count, names, order, timing | exactly as before for the same file and settings |
| Format | PNG. Tiles at `resolution` 1: indexed colour (the 84-color palette per frame). Blended, finer tiles, contour: true color (RGB) or as before (contour RGBA if it was). Circles: RGB. The mode of each image type does not change. |
| Content | the same notes, in the same places in proportion to the frame, with the same colors, as a frame of the old size; drawn at the new size, not enlarged |

Tiles: the tile columns and rows are spread over the frame, every column the same width and every row the same height to within one pixel (at the default grid: columns of 50 px, rows of 57 or 58 px).

Blended tiles: the soft edge is `blend_width` percent of a tile wide on each side of an edge (a tile is 50 px wide at the default grid), as before in proportion.

Circles: `circle_unit` (Movement) and `circle_radius` (Radius) keep their ranges and meaning as numbers but are measured in pixels of a 252-pixel-wide reference frame and are scaled by 600 / 252 when drawn (a Radius of 4 is a disc of radius about 9.5 pixels; a Movement of 4 moves a circle 4 × 2.38 pixels per unit); the circles start at the middle of the 600 × 400 frame and wrap around its edges.

Results made before this change are unchanged (their frames stay 252 × 168).

## The page (frame player)

| Part | Rule |
|------|------|
| The frame | shown at its own width up to **600 px**: `width: 100%` with `max-width: 600px`, `aspect-ratio: 3 / 2`; on a window narrower than the frame it is scaled down to fit, keeping 3:2, never cropped or distorted |
| Scaling | the browser's default smooth scaling (the old `image-rendering: pixelated` is gone) |
| The controls | the same maximum width as the frame (600 px) |
| Behaviour | play, pause, step, speed and the frame counter are unchanged |

## The help texts of the circles

- **Movement**: "...the length of one step of a circle, measured against a frame 252 pixels wide (it is drawn 2.4 times larger on the 600-pixel frame)..." (the readout stays "4 px").
- **Radius**: "...the radius of a circle, measured against a frame 252 pixels wide (it is drawn 2.4 times larger on the 600-pixel frame)...".
