# Data Model: Octave Grid Layout

Only the changes to the frame image from features 002 and 004 are listed. Nothing else in the data model changes.

## Image geometry (constants in `frame_rendering.py`)

| Name | Value | Meaning |
|------|-------|---------|
| `GRID_COLUMNS` | 12 | Tiles across: one per note within an octave |
| `GRID_ROWS` | 7 | Tiles down: one per octave |
| `SHOWN_NOTES` | 84 | `GRID_COLUMNS × GRID_ROWS`: notes 0 to 83 are drawn |
| `TILE_WIDTH` | 21 px | Width of one tile |
| `TILE_HEIGHT` | 24 px | Height of one tile; `TILE_WIDTH / TILE_HEIGHT = 0.875` |
| `IMAGE_WIDTH` | 252 px | `GRID_COLUMNS × TILE_WIDTH` |
| `IMAGE_HEIGHT` | 168 px | `GRID_ROWS × TILE_HEIGHT` |

Checked by assertions at import: `TILE_WIDTH × 8 = TILE_HEIGHT × 7`, `IMAGE_WIDTH × 2 = IMAGE_HEIGHT × 3` (so (12 × 0.875) ÷ 7 = 1.5 exactly), and `GRID_COLUMNS × GRID_ROWS = SHOWN_NOTES`.

## Tile placement

| Rule | Definition |
|------|------------|
| Note at tile (row *r*, column *c*) | Note number `12 × r + c`, with row 0 at the top and column 0 at the left |
| Tile pixels | Columns `c × 21` to `c × 21 + 20`, rows `r × 24` to `r × 24 + 23`, all one gray level |
| Octave rule | The tile below tile (*r*, *c*) is (*r* + 1, *c*), note `12 × (r + 1) + c`, which has double the frequency. The bottom row has no tile below it. |
| Lowest note | Note 0 (55 Hz) is the top-left tile |
| Last drawn note | Note 83 (about 6645 Hz) is the bottom-right tile |
| Omitted notes | Notes 84 to 87 (7040, 7459, 7902 and 8372 Hz) are not drawn. They are still calculated, and they still count when the 0–255 scale is set. |

## Tile gray level (unchanged)

`level = round(255 × value / file_max)`, where `file_max` is the largest value of any of the 88 notes in any frame; the pixel is `round(255 × (level / 255)^(1 / brightness))`. A note's gray level is the same as in the previous layout.

## Frame Image file (changed)

`<frames_temp_dir>/<job_id>/frame_<f, 6 digits>.png`: 8-bit grayscale (a color PNG since feature 007, with the same positions and with the brightest color channel equal to the tile's gray level), **252 × 168 pixels**, 12 columns by 7 rows of 21 × 24 tiles (was 220 × 160, 11 columns by 8 rows of 20 × 20 squares).

## Function contract (changed signatures)

| Function | Change |
|----------|--------|
| `render_frame(levels, brightness=2)` | Takes at least 84 gray levels (normally 88) and draws the first 84. Fewer than 84 raises `ValueError`. Returns a 252 × 168 `L` image. |
| `write_frames`, `boost_levels`, `to_gray_levels` | Unchanged |
| `SQUARE_PIXELS` | Removed; replaced by `TILE_WIDTH` and `TILE_HEIGHT` |

## Client state

No change. The page displays the image from the same URL pattern, now with a declared 3:2 aspect ratio.
