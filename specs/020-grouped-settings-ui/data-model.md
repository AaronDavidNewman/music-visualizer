# Data Model: Grouped, Collapsible Settings

There is no stored data. This describes the form's structure and the one changed setting.

## The groups

Shown from top to bottom. "Controls" are in the order they are laid out (left to right, then the next row); a control that is not shown for the chosen image type is not in the document at all.

| # | Group id | Title | Shown when | Controls (control id: label) | Rows |
|---|----------|-------|------------|------------------------------|------|
| 1 | `analysis` | Analysis | always | `window-size`: Window size (samples); `frame-rate`: Frame rate (frames per second); `window-spacing`: Window spacing (× window size) | 2 + 1 |
| 2 | `colormap` | Colormap | always | `colormap`: Colormap | 1 |
| 3 | `image-type` | Image type | always | `image-type`: Image type | 1 |
| 4 | `tiles` | Tiles | image type Tiles | `threshold`: Threshold; `notes`: Notes | 2 |
| 4 | `contour` | Contour | image type Contour | `threshold`, `notes` (the same controls as Tiles) | 2 |
| 4 | `blended` | Blended Tiles | image type Blended tiles | `threshold`, `notes`, `blend-width`: Blend width | 2 + 1 |
| 4 | `circles` | Circles | image type Circles | `circle-unit`: Movement; `circle-radius`: Radius; `circle-resize`: Resize by volume; `circle-memory`: Memory; `circle-notes`: Notes | 2 + 2 + 1 |
| 5 | `data-smoothing` | Data smoothing | always | `smoothing-window`: Smoothing window (frames); `smoothing`: Smoothing | 2 |
| 6 | `image-smoothing` | Image smoothing | image type Tiles, Contour or Blended tiles (not Circles) | `resolution`: Oversampling; `interpolate`: Interpolate | 2 |

Exactly one of the four group-4 rows is shown. Every control id appears in exactly one group id **for a given image type** (the id `threshold` and `notes` appear in `tiles`, `contour` and `blended`, which are never shown together). The labels of the old names are gone: Unit (now Movement), Size (now Radius), Circles per frame (now Notes), Resolution (now Oversampling).

## Group state

| Field | Meaning |
|-------|---------|
| open | Whether the group's body is shown. Default `true`. Kept in memory per group id for the life of the page; not stored. Collapsing never changes a setting's value. |
| problem | Whether any control of the group has a value that is not allowed (computed from the validation of its controls). Shown on the title; Create frames is disabled while any problem exists. |

## Row arithmetic (the layout rule)

`rowsOf(n)` is `[2, 2, ..., 2]` for even `n`, and the same followed by `1` for odd `n`: 1 control: `[1]`; 2: `[2]`; 3: `[2, 1]`; 5: `[2, 2, 1]`. In a row of two the cells have the same width; the single last cell of an odd group takes the full width.

## The Radius setting (replaces Size)

| Field | Form control id | Request field | Values | Default | Refusal message |
|-------|-----------------|---------------|--------|---------|-----------------|
| Radius | `circle-radius` | `circle_radius` | whole number of pixels 4 to 8 (`4` and `4.0` accepted) | 4 | `The circle radius must be a whole number from 4 to 8.` |

- The disc of a circle has exactly this radius; with Resize by volume on it is multiplied by `1 + 2 c / 255` (c the color index), so from 1 to 3 times the radius (up to 24 px).
- Readout on the page: `4 px`.
- `circle_size` no longer exists. A request that still sends it is accepted and the field ignored; the response has `circle_radius` and no `circle_size`.
- The default circle (radius 4) is within 0.02 px of the old default (circumference 25, radius 3.98), so it looks the same, but the files are not byte-identical to those made before this feature.

## The renamed settings (names only)

| Was | Now | Request field (unchanged) | Client and server message |
|-----|-----|---------------------------|---------------------------|
| Unit | Movement | `circle_unit` | `The circle movement must be a whole number from 1 to 10.` |
| Circles per frame | Notes (inside Circles) | `circle_notes` | `The number of circle notes must be a whole number from 5 to 12.` (unchanged) |
| Resolution | Oversampling | `resolution` | `The oversampling must be a whole number from 1 to 5.` |
| Circle memory (summary) | Memory | `circle_memory` | `The circle memory must be a whole number from 100 to 500.` (unchanged) |

## Result summary lines

For circles: Movement, Radius, Resize by volume, Memory, Notes (each with its readout); for the grid types: Threshold, Notes, Interpolate, Oversampling, and Blend width for blended tiles. Lines for settings that the image type does not use are not shown (as today). No line says Unit, Size, Circles per frame or Resolution.
