# Data Model: Wider Frames (600 Pixels)

No stored data. This describes the frame geometry and how the circles' settings relate to it.

## Frame geometry

| Name | Value | Meaning |
|------|-------|---------|
| `IMAGE_WIDTH` | 600 | Width in pixels of every frame, every image type. |
| `IMAGE_HEIGHT` | 400 | Height in pixels of every frame (3:2). |
| `REFERENCE_WIDTH` | 252 | Width of the old frame: the unit in which the circles' Movement and Radius are measured. |
| `REFERENCE_HEIGHT` | 168 | Height of the old frame. |
| `FRAME_SCALE` | 600 / 252 = 400 / 168 = 2.380952… | Frame size over reference size; the one number that scales the circles. |

Invariants (asserted in the code): `IMAGE_WIDTH * 2 == IMAGE_HEIGHT * 3` and `IMAGE_WIDTH * REFERENCE_HEIGHT == IMAGE_HEIGHT * REFERENCE_WIDTH`. The constants `TILE_WIDTH` (21) and `TILE_HEIGHT` (24) no longer exist.

## The grid of tiles on the frame

For a grid of `columns × rows` tiles (12 × 7 at oversampling 1, 12 r × 7 r at oversampling r from 1 to 5), the tile edges on an axis of `size` pixels are the nearest whole pixels to an even split (`tile_edges(count, size)`), so every tile of an axis differs from every other by at most one pixel.

| Oversampling | Grid | Columns (600 px) | Rows (400 px) |
|--------------|------|------------------|---------------|
| 1 | 12 × 7 | 50 px each | 57 or 58 px (57, 57, 57, 58, 57, 57, 57) |
| 2 | 24 × 14 | 25 px each | 28 or 29 px |
| 3 | 36 × 21 | 16 or 17 px | 19 or 20 px |
| 4 | 48 × 28 | 12 or 13 px | 14 or 15 px |
| 5 | 60 × 35 | 10 px each | 11 or 12 px |

The indexed-colour PNG of the original grid is a 600 × 400 index image with the same 84-entry palette per frame.

## Frame by image type

| Image type | Size | What changes besides the size |
|------------|------|-------------------------------|
| Tiles | 600 × 400 | Tile edges as above. Colors unchanged. |
| Blended tiles | 600 × 400 | The feather reach is `blend width % × 50 px` (10 to 25% gives 5 to 12.5 px; before, 10 to 25% of 21 px); the same in proportion to a tile. |
| Contour | 600 × 400 | Drawn as a 600 × 400 figure; the shapes are those of the old frame, with the detail of the larger size. |
| Circles | 600 × 400 | See below. |

The in-between frames of Interpolate (1 to 5) are blends of drawn frames and have the same size.

## The circles at the new size

Let `scale = width / REFERENCE_WIDTH` (2.380952… for a 600-pixel frame; exactly 1 for a 252-pixel frame).

| Quantity | Setting | Pixels on the frame |
|----------|---------|---------------------|
| Step of a note | `units × unit` (Movement 1 to 10, `units` from the octave) | `units × unit × scale` in the direction of the note's angle |
| Radius | `radius` (4 to 8) | `radius × scale` (about 9.5 to 19 px) |
| Radius with Resize by volume | `radius × (1 + 2 c / 255)` | `radius × scale × (1 + 2 c / 255)` (up to about 57 px) |
| Start of every rank | the middle of the picture | `(width / 2, height / 2)` = (300, 200) |
| Wrap-around | the edges of the picture | modulo `width` and `height` (600 and 400) |
| Opacity, color, memory, smoothing of edges | unchanged | unchanged |

The settings, their ranges, defaults, messages and request fields (`circle_unit`, `circle_radius`, `circle_memory`, `circle_notes`, `circle_resize`) do not change; the readouts ("4 px") keep their text and now mean pixels of the 252-pixel reference frame, which the help texts say.

## Time and room

Per 60 second job (1,800 frames), measured before the change as the prototype's figures in `research.md`: at most about 34 s of time, and 1.3 to 3.6 times the room, at the new size. The limits are one minute at the default settings, two minutes at the costliest, and 4 times the room.
