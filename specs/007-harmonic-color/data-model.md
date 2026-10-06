# Data Model: Harmonic Color

Only the changes to the frame image from features 002 and 004 to 006 are listed.

## Constants (in `frame_rendering.py`)

| Name | Value | Meaning |
|------|-------|---------|
| `SATURATION` | 0.5 | HSV saturation of every tile (50%), fixed |
| `DEFAULT_HUE` | 0.5 | HSV hue with no related note lit: 180° of 360° (cyan) |
| `RELATED_DOWN` | `(4, 5, 7)` | Note offsets whose brightness pulls the hue down |
| `RELATED_UP` | `(3, 6, 8, 11)` | Note offsets whose brightness pushes the hue up (the lists may differ in length) |

## Inputs

The final gray levels of all 88 notes in a frame: `level[k]` for `k = 0..87`, integers 0..255, after scaling to the loudest value, smoothing and the brightness root. Brightness on a 0 to 1 scale is `L[k] = displayed(level[k]) / 255`, where `displayed` is the output of the brightness boost. `L[k] = 0` for `k < 0` or `k > 87`.

## Tile color (for each drawn tile `n = 0..83`)

| Step | Definition |
|------|------------|
| Down sum | `D = L[n+4] + L[n+5] + L[n+7]` (the sum of `L[n+o]` for `o` in `RELATED_DOWN`; nothing is averaged) |
| Up sum | `U = L[n+3] + L[n+6] + L[n+8] + L[n+11]` (for `o` in `RELATED_UP`) |
| Hue | `h = clip(0.5 + 0.5 × (U − D), 0, 1)`. In degrees: `180 + 180 × (U − D)`, clipped to 0..360. 0 and 1 are the same red. |
| Saturation | 0.5 |
| Value | `v = L[n]`, the tile's own displayed gray level ÷ 255 |
| RGB | `colorsys.hsv_to_rgb(h, 0.5, v)`, each channel `rint(255 × channel)` as 0..255 |

Properties (all tested): `v = 0` gives (0, 0, 0); the largest of the three channels equals the displayed gray level of the tile; the smallest is about half of it; no related note lit gives hue 180° and, at full brightness, (128, 255, 255); a single "down" note at full brightness gives hue 0° and (255, 128, 128); a single "up" note at full brightness gives hue 360° and the same red; a partner at half brightness (gray level 128) gives about 89.6° or 270.4°; two partners add (their shift is the sum of their shifts); a sum beyond the wheel is clipped to red; on dim music-like frames more than 90% of hues are not clipped.

## Frame Image file (changed)

`<frames_temp_dir>/<job_id>/frame_<f, 6 digits>.png`: a color PNG, 252 × 168 pixels, 12 columns by 7 rows of 21 × 24 tiles, each tile one flat color (was 8-bit grayscale). The file is an indexed-colour PNG whose 84-entry palette holds the tile colors; it decodes to exactly the RGB pixels of `render_frame` (see research Decision 9). Tile placement is unchanged: note `n` at row `n // 12`, column `n % 12`, notes 84 to 87 not drawn.

## Function contract (changes in `frame_rendering.py`)

| Function | Change |
|----------|--------|
| `tile_hues(levels)` (new) | Takes the final gray levels (at least 84, normally 88) and returns the 84 hues as a float array between 0 and 1 |
| `tile_colors(levels, brightness=2, hues=None)` (new) | Boosts the levels, takes the hues (computed with `tile_hues` unless 84 hues are given) and returns an `(84, 3)` `uint8` array of RGB colors |
| `hue_sequence(levels, brightness=2, smoothing=0.0)` (new) | The hues of every tile in every frame, shape `(frames, 84)`, smoothed over the frames with the same running average as the note values (first frame unchanged; hue treated as a plain 0 to 1 number) |
| `render_frame(levels, brightness=2)` | Returns a 252 × 168 `RGB` image (was `L`) |
| `write_frames(frames, directory, brightness=2, smoothing=0.0)` | New `smoothing` argument: smooths the note values and then each tile's hue with it (the router no longer smooths separately). Saves indexed-colour PNGs (palette of the 84 tile colors, compression level 6) that decode to exactly the pixels of `render_frame` |
| `boost_levels`, `to_gray_levels`, `smooth_frames` | Unchanged |

## API and client state

No change. The response fields, the frame URL and the page are unchanged; the served PNG is RGB.
