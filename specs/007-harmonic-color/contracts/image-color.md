# Contract: Frame image color

Extends [the layout contract of feature 005](../../005-octave-grid-layout/contracts/image-layout.md). The HTTP interface is unchanged: `POST /api/jobs` and `GET /api/jobs/{job_id}/frames/{index}` keep their paths, fields, errors and caching. Only the picture served by the frame endpoint changes: it is now in color.

## Image

- **Color PNG**, 252 × 168 pixels (was 8-bit grayscale). The file is an indexed-colour PNG (a palette of the tile colors, at most 84 per frame) that decodes to exactly the RGB values below, so a viewer shows true color; programs that read it should convert it to RGB first. 12 columns by 7 rows of 21 × 24 tiles, laid out exactly as before: note `n` at row `n // 12`, column `n % 12`, notes 84 to 87 not drawn.
- Each tile is a single flat color given by hue, saturation and value:
  - **Value**: the tile's final gray level (after scaling to the loudest value, smoothing and the brightness root) divided by 255. The largest of the tile's three channels equals that gray level, and the smallest is about half of it.
  - **Saturation**: 50%, fixed.
  - **Hue**: `180° + 180° × (U − D)`, clipped to 0° to 360°, where `D` is the *sum* of the brightness (0 to 1) of notes `n+4`, `n+5` and `n+7` (the "down" group), and `U` is the sum of the brightness of notes `n+3`, `n+6`, `n+8` and `n+11` (the "up" group). The brightnesses are added, not averaged. Notes outside 0 to 87 count as silent (they add nothing). Notes 84 to 87 count as partners although they are not drawn. A sum beyond the wheel is clipped at 0° or 360° (the same red), not wrapped. The two lists are the constants `RELATED_DOWN` and `RELATED_UP` in `frame_rendering.py`.
- The HSV color is converted to RGB with the standard conversion and each channel is rounded to a whole number from 0 to 255 (halves go to the even number).
- A tile with value 0 is black. A silent file gives an all-black image.

## Worked examples

| Situation (tile at full brightness) | Hue | RGB |
|-------------------------------------|-----|-----|
| No related note lit | 180° | (128, 255, 255) |
| Only note `n+4` (a "down" note) at full brightness | 0° (red) | (255, 128, 128) |
| Only note `n+3` (an "up" note) at full brightness | 360° (the same red) | (255, 128, 128) |
| Only a "down" note at half brightness (gray level 128) | about 89.6° | (192, 255, 128) |
| Only an "up" note at half brightness (gray level 128) | about 270.4° | (192, 128, 255) |
| A "down" note and an "up" note equally bright | 180° | (128, 255, 255) |
| Many partners of one group at full brightness | clipped to 0° or 360° (red) | (255, 128, 128) |
| Tile at half brightness (gray level 128), no related note lit | 180° | (64, 128, 128) |
| Tile at brightness 0 | any | (0, 0, 0) |

## Response fields

No change. `frame_count`, `window_count`, timing and all other fields are as in features 002 to 006.

## Stored images

Images created before this change are not rewritten and keep their grayscale look.

## UI contract (what the user sees)

| Element | Behavior |
|---------|----------|
| Frame image | Shown in color at the same size and 3:2 proportions as before; playback works as before |
| Controls | No new control. Saturation and the related-note groups are fixed. |
