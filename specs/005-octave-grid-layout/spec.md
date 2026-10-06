# Feature Specification: Octave Grid Layout

**Feature Branch**: `005-octave-grid-layout` (no git branch created; spec directory name only)

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "instead of squares, arrange the tiles into rectangles so that there are 7 rows of 12. scale the row height by .875 so the overall aspect ratio is 3/2, and each rectangle is above the note double the frequency (the next octave)"

## Clarifications

### Session 2026-10-05

- Q: How should the tile shape be set, given that scaling the row height by 0.875 does not give a 3:2 image? → A: Set the width of each of the 12 columns to 87.5% of the height of each of the 7 rows. (12 × 0.875) ÷ 7 = 1.5, so the image is exactly 3:2.
- Q: What happens to the 4 notes that do not fit in 7 rows of 12? → A: Leave out the last 4 (the highest). The grid is an 84-key piano: notes 0 to 83, from 55 Hz to about 6645 Hz.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the notes arranged by octave (Priority: P1)

A user looking at a frame sees the notes laid out as a grid with **12 columns and 7 rows**: an 84-key piano. Each row is one octave, each column is the same note in every octave, and each tile is a rectangle rather than a square, taller than it is wide. The tile directly below a note is the same note one octave higher, which is double the frequency. The whole picture has a 3:2 aspect ratio. The brightness of each tile is worked out exactly as before. The four highest notes of the 88-note series are not drawn.

**Why this priority**: The layout is the whole feature. Putting a note directly above its octave makes harmonic structure, such as a note and its octaves lighting up together, visible as vertical stripes.

**Independent Test**: Submit a file that plays one steady note. The bright tile and the tiles for the same note in the other octaves line up in one column, and the tile directly below the bright one is the note an octave higher. Check that the picture is 3:2 and that there are 12 tiles across and 7 down.

**Acceptance Scenarios**:

1. **Given** a completed submission, **When** a frame is displayed, **Then** it is a grid of 12 columns and 7 rows of equal rectangular tiles with no gaps or margins.
2. **Given** a tile at some row and column, **When** the tile directly below it is read, **Then** it shows the note with double the frequency (the same note one octave higher).
3. **Given** the lowest note (55 Hz), **When** the frame is displayed, **Then** it is the top-left tile, and notes rise one semitone per tile moving right, with the next octave starting on the row below.
4. **Given** the frame image, **When** its width is divided by its height, **Then** the result is exactly 3:2, because each tile is 87.5% as wide as it is tall and (12 × 0.875) ÷ 7 = 1.5.
5. **Given** the same file and settings as before this feature, **When** frames are created, **Then** the number of frames, their timing, and the brightness of each note (including the brightness setting and the silent-file result) are unchanged. Only where and how each note's tile is drawn changes.
6. **Given** a silent file, **When** frames are created, **Then** every tile is black.
7. **Given** the 88-note series, **When** a frame is displayed, **Then** only the first 84 notes (55 Hz up to about 6645 Hz) are drawn, and the four highest notes (7040, 7459, 7902 and 8372 Hz) do not appear anywhere in the image.

---

### User Story 2 - The page shows the new shape correctly (Priority: P2)

The frame player on the page shows the 3:2 image at its true proportions at any window width, without stretching or cropping, and the documentation of the image shape is updated.

**Why this priority**: The layout change is only useful if the page does not distort it. It depends on Story 1.

**Independent Test**: Open a completed submission at a wide window and at a narrow window. The image stays 3:2 in both, and the animation plays as before.

**Acceptance Scenarios**:

1. **Given** a completed submission, **When** the player is shown at any page width, **Then** the image keeps its 3:2 proportions with no stretching or cropping.
2. **Given** playback, **When** frames advance, **Then** the image size does not jump from frame to frame.
3. **Given** the written description of the image (in the project docs), **When** it is read, **Then** it states the 12 by 7 layout, the tile shape, the octave rule and the 3:2 ratio.

---

### Edge Cases

- **Notes that do not fit**: There are 88 notes but 12 columns by 7 rows hold only 84. The highest four (7040 to 8372 Hz) are left out of the picture. The analysis still calculates all 88 values, so nothing about the analysis or its timing changes, and the omitted notes have no effect on any tile.
- **Earlier submissions**: Images already stored from before this change keep the old square layout. Only new submissions use the new one. No old images are rewritten.
- **Whole-pixel tiles**: Each tile is a whole number of pixels wide and tall, so the grid has no blurry or uneven tile edges, and the 3:2 ratio holds exactly.
- **Very narrow windows**: The image scales down with the page and never overflows or scrolls sideways.
- **Quiet and loud notes**: Only the position and shape of the tiles change. A note has the same gray level as before for the same settings.
- **Octave edges**: The last row has no octave above it, so there is no tile below it. The rule that the tile below is double the frequency applies to every tile that has a tile below it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each frame image MUST arrange the note tiles in a grid of 12 columns and 7 rows, with equal-sized rectangular tiles, no gaps and no margins.
- **FR-002**: The tile at row *r* and column *c* (both counted from 0, row 0 at the top and column 0 at the left) MUST show note number 12 × *r* + *c* of the existing 88-note series, which starts at 55 Hz and rises one semitone per note. So the lowest note is the top-left tile, and each row is one octave.
- **FR-003**: For every tile that has a tile directly below it, the tile below MUST show the note with double the frequency, which is the same note one octave higher.
- **FR-004**: Each tile MUST be a rectangle whose width is 87.5% of its height (for example 21 pixels wide by 24 tall), so the 12 columns together are 12 × 0.875 = 10.5 row-heights wide and the 7 rows together are 7 row-heights tall.
- **FR-005**: The overall image MUST have an aspect ratio of exactly 3:2 (width : height), which follows from FR-004 because (12 × 0.875) ÷ 7 = 1.5, using whole-pixel tile sizes.
- **FR-006**: The grid MUST show 84 notes, numbers 0 to 83 (55 Hz up to about 6645 Hz). The four highest notes of the 88-note series, numbers 84 to 87 (7040, 7459, 7902 and 8372 Hz), MUST NOT be drawn. All 88 values continue to be calculated.
- **FR-007**: Gray levels MUST be calculated exactly as before: scaled against the loudest value in the file, then brightened with the brightness setting. A note's gray level MUST be the same as in the previous layout for the same file and settings. Silent frames MUST be black.
- **FR-008**: The number of frames, the frame timing, the analysis windows and the window spacing MUST NOT change. Given the same file and settings, the system MUST produce the same images every time.
- **FR-009**: The page MUST show each frame at its true 3:2 proportions at any page width, without stretching or cropping, and the displayed image MUST NOT change size from frame to frame during playback.
- **FR-010**: The project's written description of the image (size, grid, tile shape, octave rule, aspect ratio) MUST be updated to match the new layout.
- **FR-011**: Images stored by earlier submissions MUST NOT be changed.

### Key Entities

- **Frame Image**: The picture for one animation frame: a 3:2 grid of 12 columns by 7 rows of equal rectangular tiles of gray.
- **Tile**: One rectangle in the grid, showing the brightness of one note.
- **Note**: One of the 88 pitches, numbered from 0 (55 Hz) upward, one semitone apart. The note one octave up (number + 12) has double the frequency.
- **Octave row**: One row of the grid, holding 12 consecutive notes. The first row is the lowest octave.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of generated frames the image has 12 tiles across and 7 down, all tiles are the same size, and width ÷ height is exactly 1.5.
- **SC-002**: For every tile that has a tile below it, the note on the tile below has exactly double the frequency of the note above it, for all notes shown.
- **SC-003**: For a file that plays one steady note, the same note in every octave is in the same column, and the loudest tile is in the column of that note.
- **SC-004**: For the same file and settings, each note's gray level in the new layout equals its gray level in the previous layout for 100% of notes shown, in every tested frame.
- **SC-005**: The number of frames, the number of windows, and the time to create the frames are unchanged within 10% compared with the previous layout.
- **SC-006**: A silent file gives all-black frames at every brightness setting.
- **SC-007**: At page widths from 320 to 1920 pixels the displayed image has a width-to-height ratio within 1% of 1.5, with no horizontal scrolling.

## Assumptions

- **"Above" is read literally**: "each rectangle is above the note double the frequency" is taken to mean that the tile for a note sits directly above the tile for the same note one octave higher. So the lowest octave is the top row and octaves rise going down. This keeps the lowest note in the top-left corner, as in the current layout. If the intended reading is the opposite (higher octaves on top, as on a piano roll), it only reverses the order of the rows.
- **Columns start at 55 Hz**: Column 0 is the note at 55 Hz in every octave, because the project's 88-note series starts there. Columns are not labeled with conventional note names.
- **Layout only**: The analysis, the frame averaging, the gray-level scaling and the brightness setting are unchanged. Only the drawing of each frame changes.
- **Image size**: Tile sizes are whole pixels in the ratio 7 wide to 8 tall so that the 3:2 ratio is exact. A tile of 21 by 24 pixels gives a 252 by 168 image. The exact pixel size is not fixed by this spec, and the page scales the image to fit.
- **84 keys**: With the highest four notes left out, the grid holds exactly seven complete octaves. The omission is only in the picture; the 88-value analysis and every earlier feature are unchanged.
- **No new setting**: The layout is not a user option in this feature. The old square layout is replaced.
- **Dependencies**: This changes the frame image defined in feature 002 and its brightening in feature 004. It depends on the existing 88-note series from feature 001.
