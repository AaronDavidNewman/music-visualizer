# Data Model: Colormap Colors

Only what changes from the frame colors of the earlier features is listed. Features 010 (level steps), 009 and 004 to 007 (energy, saturation, harmonic hue) are replaced by this one.

## Constants

| Name | Value | Where | Meaning |
|------|-------|-------|---------|
| `COLORMAPS` | `("summer", "autumn", "hot", "cool")` | `colormaps.py` | The offered colormaps, matplotlib's names, lowercase |
| `DEFAULT_COLORMAP` | `"hot"` | `colormaps.py` | Used when none is given |
| `COLORMAP_STEPS` | 256 | `colormaps.py` | Entries of a lookup table (matplotlib's default) |

Frontend: `COLORMAPS = [{ value: "summer", label: "Summer" }, { value: "autumn", label: "Autumn" }, { value: "hot", label: "Hot" }, { value: "cool", label: "Cool" }]`, `DEFAULT_COLORMAP = "hot"` in `validation.ts`.

Removed constants: `MIN/MAX/DEFAULT_BRIGHTNESS`, `MIN/MAX/DEFAULT_ENERGY`, `DEFAULT_VALUE`, `DEFAULT_HUE`, `RELATED_DOWN`, `RELATED_UP`, `HUE_SCALE`, `UNIT_SCALE`, `HUE_STEPS`, `UNIT_STEPS` and their frontend counterparts (`BRIGHTNESS_RANGE`, `ENERGY_RANGE`, `HUE_STEPS`, `UNIT_STEPS`, `HUE_SCALE`, `UNIT_SCALE`, `NA_STEP`, `DEFAULT_STEP`, `DEFAULT_BRIGHTNESS`, `DEFAULT_ENERGY`).

## Lookup table

`lookup_table(name)` is a `(256, 3)` `uint8` array: row `i` is the 8-bit RGB color of matplotlib's colormap `name` at table index `i` (`matplotlib.colormaps[name](np.arange(256), bytes=True)[:, :3]`). Row 0 is the first color of the scale and row 255 the last. Read-only and cached. In `hot` and `cool` all 256 rows are different colors (a test asserts it), so a color can be decoded back to its row; matplotlib's own 8-bit conversion truncates, so a few neighboring rows of `summer` (253 distinct colors) and `autumn` (232) are the same color, and the table is kept as matplotlib makes it. Tests therefore compare colors with `table[row]` and decode a color to its row only for `hot`.

| Colormap | Scale (first → last) |
|----------|----------------------|
| `summer` | green → yellow |
| `autumn` | red → yellow |
| `hot` | very dark red (10, 0, 0) → red → yellow → white |
| `cool` | cyan → magenta |

## Strength to position to color

With `S` the smoothed note values of the whole file, shape `(frames, 88)` (after `smooth_frames` with the smoothing and its window):

```
peak     = max(S)                                  over every note (all 88) of every frame
share    = S[:, :84] / peak                        for the 84 drawn notes; all 0 if peak is 0
position = sqrt(share)                             0 .. 1
index    = rint(position * 255)                    0 .. 255 (halves to even)
color    = lookup_table(colormap)[index]           (frames, 84, 3) uint8
```

- A note with no strength has index 0 (the first color); the note whose value is `peak` has index 255 (the last color).
- The index is a non-decreasing function of the strength, so a stronger note never has an earlier color.
- A tile's color depends only on its own smoothed value and on `peak`: not on any other note, on the frame's loudness, or on the frame's number. Two tiles with the same smoothed value have the same color, in any frames.
- A silent file (`peak = 0`): every tile has index 0, the colormap's first color; the threshold hides nothing in it (no note is below a share of the zero largest value).
- `peak` is the same value that the threshold uses as its reference (`hidden_notes`).

### Worked examples

`peak = 100`. Strength 100 → share 1 → position 1 → index 255 (last color). Strength 25 → share 0.25 → position 0.5 → index 128 (`rint(127.5)` = 128). Strength 4 → share 0.04 → position 0.2 → index 51. Strength 1 → share 0.01 → position 0.1 → index 26 (`rint(25.5)` = 26). Strength 0 → index 0.

## Pipeline in `write_frames`

For the whole file, then each frame:

1. `smoothed = smooth_frames(frames, smoothing, smoothing_window)` (unchanged).
2. `colors = colorize(smoothed, colormap)`, shape `(frames, 84, 3)`.
3. `hidden = hidden_notes(smoothed, threshold)`, shape `(frames, 84)` (unchanged); `colors[hidden] = (0, 0, 0)`.
4. For each frame the 84 colors go to the writer of the image type: `tiles` → `_palette_frame(colors[f]).save(..., compress_level=6)`; `blended` → the blender on the thread pool (unchanged).

Nothing else about a frame depends on the colors: size 252 × 168, 12 × 7 tiles of 21 × 24 pixels, names, count and timing are unchanged.

## API and page

Request field `colormap` (`summer`, `autumn`, `hot`, `cool`; default `hot`); response field `colormap` (always). Removed from the request (ignored) and from the response: `energy`, `brightness`, `hue_step`, `saturation_step`, `brightness_step`. Page: `JobSettings.colormap: string`, `JobResult.colormap: string`; the removed settings and result fields are deleted; summary `Colormap: Hot` (the label of the value used).
