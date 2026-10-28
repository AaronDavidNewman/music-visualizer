# Data Model: Spiral Note Layout

No stored data. This describes the two layouts, the setting and how the values are reordered.

## The setting

| Setting | Request field | Page control | Values and default | Used by |
|---------|---------------|--------------|--------------------|---------|
| Note layout | `note_layout` | dropdown "Note layout" (id `note-layout`), options "Rows" (`rows`) and "Spiral" (`spiral`) | exactly `rows` or `spiral`; default `rows` | Tiles, Blended tiles, Concentric; checked for every type, ignored by the others |

Group: id `note-layout`, title "Note layout", controls `["note-layout"]`; shown for `tiles`, `blended` and `concentric`, after the group of the image type (after Image type for Concentric) and before Local peaks.

Message (HTTP 400, before any audio work): `The note layout must be one of rows, spiral.`

## The layouts

The 84 drawn notes are note indexes `0 … 83` (A1 = MIDI 33 to G#8 = MIDI 116); middle C is index **27** (MIDI 60). The cells of the 12 × 7 grid are numbered row by row from the top left: cell `row * 12 + column`.

| Layout | The note drawn in cell `i` (`note_order[i]`) |
|--------|----------------------------------------------|
| `rows` | `i` (the identity: note `n` at row `n // 12`, column `n % 12`) |
| `spiral` | the note of the table below |

The spiral, as the offset of the note from middle C in semitones (negative below, `C` is index 27):

```text
 49 -21 -13  11  12 -12 -11 -10  13  22  36  50
 48 -22 -14  -5   4  -4  -3   5  14  23  37  51
 47 -23 -15  -6  -1   C   1   6  15  24  38  52
 46 -24 -16  -7  -2   3   2   7  16  25  39  53
 45 -25 -17  -8  -9  10   9   8  17  26  40  54
 44 -26 -18 -19 -20  21  20  19  18  27  41  55
 43 -27  35  34  33  32  31  30  29  28  42  56
```

Middle C is at row 3, column 6 (from 1). The note index of a cell is `27 + offset`.

### The rule that makes the table

Two walkers start at middle C's cell, row index 2, column index 5.

- **High notes** (offsets 1 to 56): a clockwise square spiral that starts by going east: legs of 1, 1, 2, 2, 3, 3, … cells in the directions east, south, west, north, east, … (a right turn after each leg).
- **Low notes** (offsets -1 to -27): a counterclockwise square spiral that starts by going west: the same legs in the directions west, south, east, north, west, … (a left turn after each leg).
- The walkers take turns, the high one first. Each takes the next cell of its own spiral that is **on the grid and not yet taken** and puts its next note there (+1, +2, … and -1, -2, …). When the low notes have all been placed the high walker goes on alone.

## Arranging the values

For a frame with the 84 note values `v[0 … 83]` (the spread notes for the grid types), the values in **cell order** are `w[i] = v[note_order[i]]`. `arrange_notes(values, layout)` does this for every frame; columns after the 84th (the four undrawn notes) are not part of the result.

| Picture | What receives the cell-order values |
|---------|-------------------------------------|
| Tiles, Blended tiles | `interpolate_grid(w, 12, 7, resolution)`, then threshold, colors, hiding, drawing, as before |
| Concentric | `write_concentric_frames(w, ...)`: the circle of cell `i` is the circle of note `note_order[i]` |
| Contour, Circles, Circles paint | the note values as before (not arranged) |

## Validation

| Input | Rule | Message |
|-------|------|---------|
| `note_layout` | exactly one of the two values | `The note layout must be one of rows, spiral.` |
| the values given to `arrange_notes` | a 2-D array with at least 84 columns | `At least 84 note values per frame are needed (got shape ...).` |

## Summary shown after a job

For Tiles, Blended tiles and Concentric a line "Note layout: Rows" or "Note layout: Spiral"; none for the other types.
