# Data Model: Peak Tile Colors

No stored data. This describes how a frame's position in the peak and a tile's color are worked out, and the new settings.

## Settings

| Setting | Request field | Page control | Range and default | Used by |
|---------|---------------|--------------|-------------------|---------|
| Beat coloring | `beat_coloring` | checkbox "Beat coloring" (id `beat-coloring`) | `true`, `false`, `1`, `0` (any case); default `false` | Tiles, Blended tiles |
| Minimum distance | `peak_distance` | slider "Minimum distance" (id `peak-distance`), 100 to 2000, step 50, shown as "100 ms" | milliseconds, 100 to 2000, default 100 | Tiles, Blended tiles, only when the beat coloring is on; checked always |
| Prominence | `peak_prominence` | slider "Prominence" (id `peak-prominence`), 0 to 100, step 5, shown as "50%" | percent, 0 to 100, default 50 | as above |

Group: id `local-peaks`, title "Local peaks", controls `["beat-coloring", "peak-distance", "peak-prominence"]`; shown for `tiles` and `blended` only, after their type group.

Messages: `The beat coloring must be true or false.`; `The minimum distance must be a number from 100 to 2000 milliseconds.`; `The prominence must be a number from 0 to 100 percent.` (HTTP 400, before any audio work).

## The position of a frame in the local peak

For frame `i` of `F` frames at `fps` frames per second, with the measurement `M` (feature 023) of the file:

| Quantity | Definition |
|----------|------------|
| `t[i]` | `(i + 0.5) / fps` seconds, `p[i] = t[i] × file_rate` samples |
| `E[i]` | `M.energy_at(p[i])`: the line between the previous and the next peak's `energy`; 0 before the first peak; the last peak's `energy` after the last |
| `lo[i]`, `hi[i]` | the same line through the peaks' `window_min` and `window_max`; 0 before the first peak; the last peak's values after the last |
| `position[i]` | `clip((E[i] − lo[i]) / (hi[i] − lo[i]), 0, 1)` when `hi[i] > lo[i]`, else `0` |

With no peaks, `position[i] = 0` for every frame. Every tile of frame `i` uses `position[i]`.

## The color of a tile

For a visible tile with (smoothed, possibly interpolated) value `v` in frame `i`, `peak` the file's largest note value and `share = min(v / peak, 1)` (0 when `peak` is 0):

| Beat coloring | Table index (0 to 255) |
|---------------|------------------------|
| off (or any other image type) | `rint(sqrt(share) × 255)` (as before) |
| on, Tiles or Blended tiles | `rint((0.5 × sqrt(share) + 0.5 × position[i]) × 255)` |

The color is the colormap's table entry at that index. A tile hidden by the threshold is not colored by this: black for Tiles, table row 128 for Blended tiles, as before.

Consequences: the file's loudest tile is at row 128 (the middle) at position 0 and row 255 (the right-most) at position 1; a tile with no energy is at `rint(127.5 × position)`, up to row 128; the row never decreases when `share` or `position` rises; with `position = 0` for the whole file no row is above 128.

## What is passed where

| Place | Value |
|-------|-------|
| `LocalPeaks.position_at(point)` / `position_at_time(seconds)` | The position (float, or an array for a sequence) at a sample / a time |
| `LocalPeaks.frame_positions(frame_rate, frames)` | `position_at_time((arange(frames) + 0.5) / frame_rate)`: a float64 array of `frames` numbers |
| `write_frames(..., beat=None)` | `None` or a 1-D array of one number from 0 to 1 per frame (checked; used for `tiles` and `blended`, ignored otherwise) |
| `colorize(..., beat=None)` | `None` or a 1-D array of one number from 0 to 1 per row of `smoothed` |
| response of `POST /api/jobs` | adds `beat_coloring` (bool), `peak_distance` (number), `peak_prominence` (number) |

## Validation

| Input | Rule | Message |
|-------|------|---------|
| `beat` (in `write_frames`, `colorize`) | a 1-D array of finite numbers from 0 to 1, one per frame / row | `The beat must be one number from 0 to 1 for each of the N frames.` |
| the three request fields | as in Settings | as in Settings |
