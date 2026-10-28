# Feature Specification: Spiral Note Layout

**Feature Branch**: `026-spiral-note-layout` (no git branch created; spec directory name only)

**Created**: 2026-10-27

**Status**: Clarified

**Input**: User description: "for tiled and concentric image types that list the notes in order, allow an alternate configuration of the notes.  Start with middle C roughly in the center of the screen (3rd row 6th column).  One to the right of C is the next note up, one to the left is the next note down.  Continue up in pitch clockwise and down in pitch counterclockwise."

## Clarifications

### Session 2026-10-27

- Q: How do the two arms share the grid? -> A: **Interleaved**, exactly the layout below: the arms take turns around middle C, the high notes winding clockwise and the low notes counterclockwise, each skipping cells that are off the grid or already taken. It has 13 steps between semitone neighbours that are not next to each other on the grid; that is accepted.
- Q: Which pictures get the choice, and what is the control? -> A: **Tiles, Blended tiles and Concentric**, with a **dropdown "Note layout"** (Rows, Spiral) in a **new group**, Rows by default. Contour, Circles and Circles paint are not affected.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The notes laid out as a spiral around middle C (Priority: P1)

Today the 84 drawn notes of the grid-like pictures are listed **in order, like text**: the lowest note (A1) at the top left, twelve notes to a row, the highest at the bottom right, so neighbouring notes in a row are neighbours in pitch but the rows are twelve notes (an octave) apart. The user wants an **alternate arrangement** of the same 84 cells, a **spiral around middle C**, so that notes close in pitch are close on the screen in every direction:

- **Middle C** (C4, the 28th of the 84 notes) sits **roughly in the center** of the grid, at the **3rd row and the 6th column** (counted from 1, from the top left).
- The note **one to the right of C** is the **next note up** (C#4) and the note **one to the left** is the **next note down** (B3).
- Notes **above C continue clockwise**, winding outward from C; notes **below C continue counterclockwise**, winding outward from C.
- Every one of the 84 cells holds **exactly one** note, and each note is in exactly one cell: it is a rearrangement of the cells, nothing is added, dropped or recolored.

Everything that is worked out for a note stays the same wherever the note sits: its value, its strength, its hiding by the threshold, its color. Only **where its tile or circle is drawn** changes.

**The layout** (the clarified arrangement). The number in a cell is the note's distance from middle C in semitones (negative below, `C` is middle C, `1` is C#4, `-1` is B3), with the first row at the top and the first column at the left:

```text
 49 -21 -13  11  12 -12 -11 -10  13  22  36  50
 48 -22 -14  -5   4  -4  -3   5  14  23  37  51
 47 -23 -15  -6  -1   C   1   6  15  24  38  52
 46 -24 -16  -7  -2   3   2   7  16  25  39  53
 45 -25 -17  -8  -9  10   9   8  17  26  40  54
 44 -26 -18 -19 -20  21  20  19  18  27  41  55
 43 -27  35  34  33  32  31  30  29  28  42  56
```

It is made like this: from middle C the **high notes** walk a clockwise square spiral (east, then south, then west, with legs of 1, 1, 2, 2, 3, 3, ... cells) and the **low notes** walk a counterclockwise square spiral (west, then south, then east, with the same legs); the two **take turns**, the high notes first, each taking the next cell of its own spiral that is on the grid and not yet taken; when one arm has run out of notes (the 27 low notes end first) the other keeps going. The table above is the result and is what counts.

**Why this priority**: This is the whole request. The setting and the pictures it applies to build on a correct arrangement.

**Independent Test**: Make the layout and check it as a table: the cell at row 3, column 6 is middle C; the cell to its right is C#4 and to its left B3; every one of the 84 cells has a different note; the notes above C wind clockwise and the notes below C wind counterclockwise, each note next to the one before it in pitch (as far as the clarified arrangement allows).

**Acceptance Scenarios**:

1. **Given** the spiral layout, **When** the cell of every note is listed, **Then** each of the 84 cells of the 12 × 7 grid holds exactly one note and each note is in exactly one cell.
2. **Given** the spiral layout, **When** the cell of middle C is looked up, **Then** it is row 3, column 6 (from 1, from the top left).
3. **Given** the spiral layout, **When** the cells next to middle C are looked up, **Then** the cell to its right is the next note up (C#4) and the cell to its left the next note down (B3).
4. **Given** the notes above middle C in pitch order, **When** their cells are followed one after the other, **Then** the path winds **clockwise** outward from C: the first three are east, south-east and south of C (cells 1, 2 and 3 of the table).
5. **Given** the notes below middle C in pitch order, **When** their cells are followed one after the other, **Then** the path winds **counterclockwise** outward from C: the first three are west, south-west and north-east of C (cells -1, -2 and -3 of the table: the low arm skips the south, south-east and east cells that the high arm has already taken).
6. **Given** two notes a semitone apart, **When** their cells are compared, **Then** they are next to each other on the grid (sharing an edge) except for the 13 pairs `(-21, -20)`, `(-13, -12)`, `(-10, -9)`, `(-5, -4)`, `(-3, -2)`, `(3, 4)`, `(4, 5)`, `(10, 11)`, `(12, 13)`, `(21, 22)`, `(35, 36)`, `(42, 43)` and `(49, 50)` (distances from middle C), where an arm skips a cell that is off the grid or taken.
7. **Given** the spiral layout, **When** it is worked out twice, **Then** it is identical (it does not depend on the music), and the cell of every note is the one in the table above.

---

### User Story 2 - Choose the layout for the pictures that list the notes in order (Priority: P2)

The layout is a **choice** with two values: the **rows** layout that exists today (the default, so nothing changes until the user asks) and the new **spiral** layout. It applies to the pictures that draw **one shape per note on the 12 × 7 grid**: **Tiles**, **Blended tiles** and **Concentric**.

The choice is a **dropdown named "Note layout"** with the two values **Rows** and **Spiral**, in a **group of its own** (titled "Note layout"), shown when the image type is **Tiles**, **Blended tiles** or **Concentric** and for no other type, after the group of the image type and before the Local peaks group. **Contour**, **Circles** and **Circles paint** do not have it.

**Why this priority**: The arrangement (Story 1) exists on its own, but the user reaches it through this choice.

**Independent Test**: Create Tiles, Blended tiles and Concentric frames of one file with the rows layout and with the spiral layout: the second pictures show the same colors and sizes in different places; the tile (or circle) of every note is where the layout table says; with the default the frames are identical to those made before this feature.

**Acceptance Scenarios**:

1. **Given** no value for the layout, **When** the pictures are made, **Then** the layout is rows and the frames are identical, file for file, to those made before this feature, for every image type.
2. **Given** the spiral layout and Tiles, Blended tiles or Concentric, **When** the pictures are made, **Then** the tile or circle of every note is drawn at the cell of the spiral layout, with the same color, size and rings as in the rows layout.
3. **Given** a layout that is not one of the two offered, **When** the request is made, **Then** it is refused before any work is done, with a message that lists the two.
4. **Given** an image type that has no choice (Contour, Circles, Circles paint), **When** the spiral layout is sent, **Then** it is checked and has no effect: the frames equal those of the rows layout.
5. **Given** the settings page, **When** the image type is Tiles, Blended tiles or Concentric, **Then** the group Note layout is shown with a dropdown whose choices are Rows and Spiral and whose first value, Rows, is selected; for the other types the group is not shown.
6. **Given** the result summary of a job, **When** it is shown for Tiles, Blended tiles or Concentric, **Then** it names the layout ("Note layout: Rows" or "Spiral").

---

### User Story 3 - The other settings keep their meaning (Priority: P3)

The layout only changes **where** a note is drawn. The other settings work on the notes, not on the cells, so they behave as before:

- **Threshold** hides the same notes (the ones below its share of the loudest), now wherever they sit.
- **Notes** (the number of notes used) still keeps the strongest notes of the file and spreads them over the 84 cells **in pitch order**, now along the spiral.
- **Oversampling** (a finer grid by interpolation) blends each tile with its **neighbours on the screen**: with the spiral layout those are notes close in pitch in several directions, not only in the row.
- **Smoothing** (over time), **Interpolate**, **Gaussian smoothing**, the **colormap** and the **beat** (Local peaks) are unchanged.

**Why this priority**: These define what "only the places change" means in practice.

**Independent Test**: With the spiral layout, the same notes are hidden by the threshold as with the rows layout (the same note indexes), and the Notes setting keeps the same strongest notes; the colors of each note are the same in both layouts.

**Acceptance Scenarios**:

1. **Given** the same file and settings, **When** the spiral layout and the rows layout are made, **Then** the set of hidden notes in every frame is the same (by note, not by cell).
2. **Given** a Notes value below 84, **When** the spiral layout is made, **Then** the notes shown are the same strongest notes as with the rows layout, spread in pitch order over the spiral.
3. **Given** the same file and settings, **When** the pictures are made twice, **Then** the files are identical.
4. **Given** Concentric with the spiral layout, **When** it is made, **Then** the circle of every note is centered on the cell of that note, with the full radius and the rings as in the rows layout.

---

### Edge Cases

- **The grid is fixed at 12 × 7**: the spiral cannot run off it. Where a turn of the spiral would leave the grid, the arrangement states what happens (the clarification).
- **The four highest notes** (the 88 notes less the 84 drawn) are not drawn in either layout.
- **27 notes below C and 56 above**: the two arms are not the same length; the longer arm keeps winding when the shorter one has ended.
- **Silent files, short files and files with no beat** work as before; the layout changes nothing about them.
- **Oversampling above 1** interpolates across the screen neighbours; at the edges of a lobe, where two cells are neighbours on the screen but far apart in pitch, the picture blends them anyway (it blends what is next to what).
- **Contour** does not have the choice: its map is always drawn from the grid in the rows layout.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: There MUST be an alternate **spiral** layout of the 84 drawn notes on the 12 × 7 grid, besides the existing **rows** layout, with exactly one note in each cell and each note in exactly one cell.
- **FR-002**: In the spiral layout middle C (C4, the 28th note) MUST be at the cell in the 3rd row and 6th column (counted from 1, from the top left); the cell to its right MUST hold the next note up and the cell to its left the next note down.
- **FR-003**: The notes above middle C MUST wind clockwise outward from it, and the notes below middle C counterclockwise outward from it, interleaved as in the table of Story 1, which is the normative arrangement.
- **FR-004**: The spiral layout MUST be a fixed arrangement, the same for every file and every setting, and MUST NOT change the value, strength, hiding, color or size of any note: only the cell where it is drawn.
- **FR-005**: There MUST be a **note layout** setting with two values, rows (the default) and spiral; any other value MUST be refused before any work is done, with a message that lists the two.
- **FR-006**: The note layout MUST apply to **Tiles**, **Blended tiles** and **Concentric** only; for Contour, Circles and Circles paint it MUST be checked and have no effect.
- **FR-007**: With the rows layout (the default) every image type MUST produce frames identical, file for file, to those made before this feature.
- **FR-008**: Threshold, Notes, Oversampling, smoothing, Interpolate, Gaussian smoothing, the colormap and the beat MUST work on the notes as before, in either layout; Oversampling blends screen neighbours.
- **FR-009**: The page MUST offer the note layout as a dropdown (Rows, Spiral) in a group of its own, titled "Note layout", shown for Tiles, Blended tiles and Concentric, after the group of the image type and before the Local peaks group, with Rows selected at the start, and MUST show it in the result summary for those pictures.
- **FR-010**: The frames MUST keep their size (600 × 400), count, names and timing, and the same file and settings MUST always give the same frames.
- **FR-011**: The documentation MUST describe the two layouts, where middle C sits and how the spiral runs.

### Key Entities *(include if feature involves data)*

- **Note layout**: Which note is drawn in which cell of the 12 × 7 grid: **rows** (note `n` at row `n // 12`, column `n % 12`, as before) or **spiral** (the arrangement around middle C).
- **Middle C cell**: The cell of the 28th note in the spiral layout: row 3, column 6 (from 1).
- **Arm**: The run of notes above middle C (clockwise) or below it (counterclockwise) in the spiral layout.
- **Note layout setting**: The choice between the two layouts, rows by default.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In the spiral layout every one of the 84 cells holds a different note (84 different notes, no cell empty), checked as a table.
- **SC-002**: In the spiral layout the cell of middle C is row 3, column 6, the cell to its right holds the note a semitone above it and the cell to its left the note a semitone below it.
- **SC-003**: Following the cells of the notes in pitch order, every semitone step is to a cell next to the previous one (sharing an edge) except the 13 pairs listed in Story 1; the path of the high notes turns clockwise (east, south-east, south of C first) and that of the low notes counterclockwise (west, south-west, north-east first).
- **SC-004**: For a test file, the color and size of the shape of every note in the spiral layout equal those in the rows layout (compared by note), and its place is the cell of the layout table.
- **SC-005**: With the default layout, the frames of all six image types for the reference test files are identical, file for file, to those made before this feature (the reference hashes).
- **SC-006**: The same notes are hidden by the threshold in both layouts, in every frame of a test file.
- **SC-007**: Creating the frames of a 60 second file takes no more than a second longer with the spiral layout than with the rows layout.

## Assumptions

- **The 84 drawn notes** are the notes A1 (the first, MIDI 33) to G#8 (the 84th, MIDI 116) as for the other pictures; **middle C is the 28th** (index 27, MIDI 60), so 27 notes are below it and 56 above it.
- **"3rd row 6th column"** is taken literally and counted from 1 from the top left (index row 2, column 5); a 12 × 7 grid has no single central cell (its center falls between columns 6 and 7 of row 4), and "roughly" covers that.
- **"Tiled and concentric image types"** means Tiles, Blended tiles (which are the same tiles drawn with soft edges) and Concentric; the other pictures do not draw one shape per note in a fixed place (Circles and Circles paint wander) and are not affected.
- **The layout is fixed** (it does not depend on the music), so it is a lookup table from a note to a cell, worked out once; the table of Story 1 is the layout.
- **The default stays rows**, so no existing picture, setting or test changes until the user chooses the spiral.
- **Where a pixel is drawn is the only thing that changes**: the geometry of a tile (50 × 57 or 58 pixels) or of a circle (its cell center and radius) is that of its cell.
