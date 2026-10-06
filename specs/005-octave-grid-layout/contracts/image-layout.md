# Contract: Frame image layout

Replaces the image content contract in [feature 002](../../002-audio-frames-ui/contracts/http-api.md). The HTTP interface is unchanged: `POST /api/jobs` and `GET /api/jobs/{job_id}/frames/{index}` keep their paths, fields, errors and caching. Only the picture served by the frame endpoint changes.

## Image

- 8-bit grayscale PNG (a color PNG since feature 007; see [the color contract](../../007-harmonic-color/contracts/image-color.md)), **252 × 168 pixels**. Width ÷ height is exactly 3:2.
- **12 columns by 7 rows** of equal tiles, no gaps and no margins. Each tile is **21 pixels wide by 24 pixels tall**, so a tile's width is 87.5% of its height, and (12 × 0.875) ÷ 7 = 1.5.
- Tile at row *r*, column *c* (counted from 0, row 0 at the top, column 0 at the left) shows note `12 × r + c` of the 88-note series (note 0 = 55 Hz, one semitone per note).
- The tile directly below any tile shows the note with double the frequency (one octave up). The lowest note is the top-left tile, the highest drawn note (83, about 6645 Hz) is the bottom-right tile.
- Notes 84 to 87 (7040, 7459, 7902, 8372 Hz) are not drawn.
- Each tile has a single gray level (since feature 007 it is the tile's HSV value, drawn as the brightest color channel of a flat color): `round(255 × (level / 255)^(1 / brightness))`, where `level = round(255 × value / file_max)` and `file_max` is the largest value among all 88 notes in the file. Gray levels are the same as in the previous layout for the same file and settings.
- A silent file gives an all-black image.

## Response fields

No change. `frame_count`, `window_count`, timing and all other fields are as in features 002 to 004.

## Stored images

Images created before this change are not rewritten and keep the old 220 × 160, 11 × 8 square layout.

## UI contract (what the user sees)

| Element | Behavior |
|---------|----------|
| Frame image | Shown at 3:2 at every page width from 320 to 1920 pixels, scaled uniformly (no stretching or cropping), never wider than the page, with no horizontal scrolling |
| Size during playback | The image does not change size from frame to frame, including while a frame is loading |
