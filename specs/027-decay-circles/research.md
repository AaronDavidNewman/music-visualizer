# Research: Decay

No `[NEEDS CLARIFICATION]` remains; the interpretations the spec made are in its Assumptions. Facts about the code were read from the repository.

## What exists today

- `concentric.py` (feature 025): `_geometry(width, height)` (cached) builds the cell of every pixel from `tile_edges`; the full radius is half the narrower cell side (25 px); `_check_values`, the background `lookup_table(colormap)[MIDDLE_COLOR_ROW]`, and frames saved on a few threads with `compress_level=1`.
- `note_layout.py` (feature 026): `check_note_layout`, `arrange_notes(values, layout)` reorders the first 84 columns of `(frames, ≥84)` into cell order (identity for Rows).
- `write_frames` smooths the notes, checks every setting for every type, and has an early branch for `concentric` that draws `arrange_notes(smoothed, note_layout)` with `beat`; `jobs.py` measures the beat when the type is `concentric` (or tiles/blended with the box on) and echoes the settings.
- Frontend: `IMAGE_TYPES`, `gridSettingsApply`, `noteLayoutApplies`, the groups model (`GROUPS`, `TYPE_GROUPS`, `groupsFor`) with the shared `concentric-peaks` group, `SettingsForm.vue` sliders (for example Circle notes) and `App.vue`'s summary.

## Decision 1: Simulate all the points first, then draw

- **Decision**: `circle_points(values, beat, layout, decay_rate) -> (frames, 84)` runs the whole simulation before any picture is drawn: for each frame, add the gains, apply the decay step if the frame number (from 1) is a multiple of the rate, record the points. Drawing then needs only a row of points.
- **Rationale**: The state depends on the earlier frames, so frames cannot be made independently; but the state is 84 numbers, so one cheap sequential pass gives it for all frames, and the drawing stays parallel (as for Concentric) and pure. Everything about the rules can be tested without pictures.
- **Alternatives considered**: carrying the state through the drawing threads (serialises the drawing, mixes two concerns).

## Decision 2: The five loudest are picked in note order; the grid works in cell order

- **Decision**: `gains(values, beat)` ranks the 84 first columns of each frame with a stable sort on `-value` (so equal values keep the lower note first), skips notes with value 0, and gives 24, 20, 16, 12, 8 plus `8 × position` to the five ranks. The `(frames, 84)` gain array is then reordered with `arrange_notes(gains, note_layout)` into cell order; the decay works on the `7 × 12` grid of cells.
- **Rationale**: The spec ranks notes (ties to the lower note) but neighbours are cells, with the Spiral too. Ranking before the reordering keeps both statements true with the one existing permutation function.
- **Alternatives considered**: ranking in cell order (ties would go to the lower cell, not the lower note, only differing in the Spiral); reordering the values first and passing the layout inside (no benefit).

## Decision 3: The decay step is `p − give + 2 × Σ neighbours' share`

- **Decision**: On the `7 × 12` array `p` (the points before the step): `give = min(p, 16)`, `share = give / 16`; the new points are `p − give + 2 × (sum of the shares of the up to 8 neighbours)`, then clipped to at most 64. The neighbour sum is the sum of the eight shifted copies of a zero-padded `share` (the grid does not wrap). The gain step clips the points to 0 and 64 as well.
- **Rationale**: This is exactly the spec: an interior circle with at least 16 points sends 2 to each of 8 neighbours and loses 16; an edge circle (5 neighbours) sends 10 and loses 6 more; a corner (3) sends 6 and loses 10 more; a circle with fewer than 16 gives the proportion `p / 16` of all of it, so it ends at 0 and creates nothing. Everything uses `p` from before the step (simultaneous). The total never grows (only edge loss and the 64 cap remove points, nothing adds). **Found while testing:** with the proportional giving the points of a fading area shrink geometrically and never reach exactly 0 (about 1e-10 after 300 steps), so the step also sets a cell with less than 0.01 points to 0 (`NEGLIGIBLE`); that is under a hundredth of a pixel of radius and makes "every circle is back at 0 within 200 decay steps" true. The result can never be below 0 since `give ≤ p`.
- **Note**: the cap at 64 after a step can never act (a circle with 16 or more points gives 16 and receives at most 16; one with fewer ends with at most 16), so the mutation that removes it is an equivalent mutant; the clip stays as a safeguard.
- **Alternatives considered**: a circle always gives the full 2 points per neighbour and is clipped at 0 (points appear from nothing, and an empty grid would not stay empty at the edges' neighbours); giving the neighbours first-come-first-served (order-dependent).

## Decision 4: Draw a disc of rings with analytic coverage

- **Decision**: Cached for the frame size: the cell of every pixel, and the distance from the pixel's center to the center of its cell (`float32`, same centers and cells as `concentric._geometry`). A frame has per cell a radius `R × (1/12 + 11/12 × min(p, 24) / 24)` and twelve ring colors `lookup_table[rint((b − s × (k − 1) / 11) × 255)]` (`b = min(p, 32) / 32`, `s = max(0, p − 32) / 32`; all twelve equal up to 32 points, so the disc is flat there); also cached: the ring of every pixel (`ceil(distance / (R / 12))`) and the shares `before` and `after` of the ring on either side that reach into the pixel (`clip(0.5 − distance to that edge, 0, 1)`). Each pixel's coverage is `clip(radius[cell] − distance + 0.5, 0, 1)`, its color is the ring's color mixed with its neighbouring rings' by those shares, and the pixel is `background × (1 − coverage) + color × coverage`, rounded. A brute-force picture (8 × 8 samples a pixel) is within a mean of 2.5 levels of it (tested).
- **Rationale**: The radius takes any value from 2.08 to 25 pixels, so Concentric's table of fixed ring classes does not apply. Coverage from the distance gives a one-pixel antialiased edge for every radius at a few array operations per frame (a gather of three per-cell values, and arithmetic on 240,000 pixels). A circle never leaves its cell: the largest radius is 25 and the cell is at least 50 pixels wide, and 1/2 pixel of edge reaches at most 25.5 from the center.
- **Alternatives considered**: a 4 × 4 supersampled mask per radius (the two-class trick of Concentric needs fixed radii; 84 masks per frame at 16× resolution is slow); drawing with Pillow `ellipse` on a 4× canvas (the other circles do, but 1,800 frames × 84 ellipses at 4× is slower than the numpy blend, and the result would not be more accurate).

## Decision 5: The rate is a whole number 1 to 10, handled like the other whole-number settings

- **Decision**: `check_decay_rate` (a whole number from 1 to 10, rejecting bools and non-integers) in `decay.py`; `jobs.py` has `_parse_decay_rate` in the style of `_parse_circle_notes` (not sent means 5, the message `The decay rate must be a whole number from 1 to 10.`), checked before the file is read; `write_frames` checks it for every type; the response echoes `decay_rate`.
- **Rationale**: The same shape as the other settings of a type that other types accept and ignore, and the same message style.
- **Alternatives considered**: refusing a rate for the other types (the other settings are accepted and ignored).

## Decision 6: The page treats Decay like Concentric, plus its own group

- **Decision**: `groupsFor("decay")` is `analysis, colormap, image-type, decay, note-layout, concentric-peaks, data-smoothing`. A new group `decay` titled "Decay" with the control `decay-rate`, added to `TYPE_GROUPS`; `noteLayoutApplies` is true for Decay; `gridSettingsApply` is false for Decay; the peaks group `concentric-peaks` (two sliders, no checkbox) is shown for Decay as for Concentric; `peakSettingsApply` (and the server's decision to measure the beat) is true for Decay. The slider is shown with the value in frames, and the summary shows "Decay rate: N frames".
- **Rationale**: The group model maps a group id to a fixed control list; the decay rate has no home in the existing groups, and the other types with settings of their own (Circles) have a type group the same way.
- **Alternatives considered**: putting the rate in the Image type group (that group has only the image type).

## Prototype expectations

Not prototyped; the arithmetic is that of Concentric's frame (a gather and a blend) and the simulation is 1,800 steps of a few `7 × 12` numpy operations. The first task builds the performance check of SC-007.
