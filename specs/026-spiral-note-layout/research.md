# Research: Spiral Note Layout

No `[NEEDS CLARIFICATION]` remains (answered on 2026-10-27). Facts about the code were read from the repository; the layout was prototyped (`scratchpad/spiral_proto.py`) and is the table of the spec.

## What exists today

- `write_frames` takes `(frames, 88)` note values, smooths them, and for the grid types calls `spread_notes(smoothed[:, :84], note_count)` (the strongest notes of the file spread over 84 values in pitch order), then `interpolate_grid(shown, 12, 7, resolution)` (value `i` of a frame is the tile at row `i // 12`, column `i % 12`; a finer grid is made by interpolating across rows and down columns), then the threshold on the values, then `colorize` and the writing of tiles (`tiles`, `blended`) or `write_contour_frames` (`contour`).
- `concentric.write_concentric_frames(values, ...)` treats the first 84 columns as notes `n` at cell `n` (row `n // 12`, column `n % 12`) and draws the circle of note `n` there; the steps depend on each frame's loudest value only.
- `circles` and `circles_paint` do not use the grid at all.
- The 28th note (index 27, MIDI 60) is middle C: the notes start at A1 = MIDI 33.
- Frontend: the groups model has one group per concept (`groupsFor` lists the groups of an image type in order), the form keeps each value in a ref and sends it in the request, the summary lists the settings that apply to the type.

## Decision 1: The layout is a permutation of the 84 values, applied before the picture is made

- **Decision**: `note_order(layout)` is an array of 84 note indices, one for each cell in row-major order: `note_order("rows")` is `0 … 83`; `note_order("spiral")` gives the note drawn in each cell of the table. `arrange_notes(values, layout)` returns `values[:, order]` for the first 84 columns. For Tiles and Blended tiles it is applied to the spread notes just before `interpolate_grid`; for Concentric to the 84 smoothed values just before the circles are drawn.
- **Rationale**: Every later step (interpolation, threshold, colors, the blend, the circles' geometry) works on cells, so reordering the values is the whole change: Oversampling blends screen neighbours, the threshold hides the same notes, the colors are the note's own. With Rows it is the identity, so the frames cannot change.
- **Alternatives considered**: moving the geometry (each circle's center, each tile's box) by layout (touches the renderers and the blend, and every picture would need its own code); reordering the output frames (would need the image machinery).

## Decision 2: The table is generated from its rule and pinned by the spec's literal table

- **Decision**: The module builds the spiral from the rule of the spec (the two arms take turns, the high notes first; the high notes walk a clockwise square spiral east, south, west, north with legs 1, 1, 2, 2, 3, 3, …, the low notes a counterclockwise one west, south, east, north; each arm takes the next cell of its own spiral that is on the grid and not yet taken; the arm that has more notes keeps going). The tests compare the result cell by cell with the table written out in the spec, so that a change of the rule is caught, and check the structure (every cell once, C at row 3, column 6, neighbours, the 13 jumps).
- **Rationale**: A rule is shorter and reviewable; a literal table in the tests is the independent oracle. The prototype produced the table of the spec and the 13 jumps.
- **Alternatives considered**: a hand-typed table in the module (no rule to explain it, easy to mistype one cell); a generator without the literal table in the tests (the rule could drift without a failing test).

## Decision 3: Where it applies, and what ignores it

- **Decision**: `write_frames(..., note_layout="rows")` checks the value for every image type (a message that lists the two) and applies it for `tiles`, `blended` and `concentric`; `contour`, `circles` and `circles_paint` ignore it.
- **Rationale**: The clarification: only the pictures with one shape per note get the choice; checked values that a type does not use are accepted and ignored, as for the other settings.
- **Alternatives considered**: refusing the value for the other types (the other unused settings are accepted and ignored).

## Decision 4: The request field and the page

- **Decision**: The optional field `note_layout`, exactly `rows` or `spiral` (lowercase, no trimming), default `rows`; anything else, including empty, is a 400 `The note layout must be one of rows, spiral.` before the file is read; the response echoes it for every type. On the page a group `note-layout` titled "Note layout" with the dropdown `note-layout` (options "Rows" and "Spiral"), listed after the group of the image type (after Image type for Concentric, which has none) and before Local peaks, shown for `tiles`, `blended` and `concentric`; the summary line "Note layout: Rows" or "Spiral" for the same types; a help text that explains the spiral and where middle C is.
- **Rationale**: The pattern of the other settings (`image_type`, `circle_resize`); a group of its own is what the clarification says.
- **Alternatives considered**: putting the dropdown in the Image type group (the clarification says a group of its own).

## Decision 5: The tests do not depend on the music

- **Decision**: The layout is tested as a table; the pictures with synthetic note values in which each note has a distinct value (so that each tile's color tells which note it is), compared by cell.
- **Rationale**: The layout is independent of the audio, and distinct values make "this note is at that cell" a direct pixel check.

## Prototype

`spiral_proto.py` builds the arrangement with two square spirals that take turns and prints the table of the spec (12 × 7, C at row 3, column 6) and the 13 semitone steps that are not between grid neighbours: `(-21, -20)`, `(-13, -12)`, `(-10, -9)`, `(-5, -4)`, `(-3, -2)`, `(3, 4)`, `(4, 5)`, `(10, 11)`, `(12, 13)`, `(21, 22)`, `(35, 36)`, `(42, 43)`, `(49, 50)`.
