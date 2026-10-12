# Feature Specification: Interpolated Resolution

**Feature Branch**: `016-interpolated-resolution` (no git branch created; spec directory name only)

**Created**: 2026-10-12

**Status**: Draft

**Input**: User description: "allow the user to increase the resolution, up to 5x the original size of 12x7.   From the original dataset of the smoothed values, use np.linspace and np.interp to create an interpolated set of values of the desired size.  The result will be more and smaller tiles/contour steps."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A finer picture made from the same notes (Priority: P1)

Today every picture is built from a grid of 12 columns (the notes of an octave) by 7 rows (the octaves): 84 values per frame, one for each drawn note. The picture can only be as detailed as that grid: the tiles are 21 × 24 pixels and the contour is drawn from 84 points. The user wants to make the picture **finer** without changing the music: a **resolution** of 1 to 5 times the original grid, so that 1× is today's 12 × 7 and 5× is 60 × 35.

The finer grid is made from the original one, not from new analysis. For each frame, the 84 smoothed note values are **interpolated**: a new grid of 12 × r columns by 7 × r rows (r is the resolution) is made by spreading evenly spaced positions over the original grid, from its first column to its last and from its first row to its last, and reading the original values at those positions by linear interpolation between neighbors. The corner values stay exactly the original corner values, and every new value lies between the values of its neighbors, so it can never be louder than the loudest note or quieter than the quietest one. The picture is then made from the new grid in the way each image type already works: **more and smaller tiles** for Tiles and Blended tiles, and **more and finer contour steps** for Contour. The picture keeps its size (252 × 168 pixels), so a higher resolution means smaller tiles in the same picture.

**Why this priority**: This is the whole feature: the finer grid and the pictures made from it. The page control (Story 2) and the combination with the other settings (Story 3) build on it.

**Independent Test**: Make frames from a file in which two neighboring notes sound with very different strength. At resolution 1 the picture is as it is today. At resolution 3 the same picture has 36 × 21 tiles (Tiles), and the tiles between the two notes step gradually from the color of one to the color of the other instead of jumping. At resolution 3 with Contour, the contour is drawn from a 36 × 21 grid and its steps are finer.

**Acceptance Scenarios**:

1. **Given** the resolution 1, **When** frames are made with any image type, **Then** they are identical, file for file, to those made before this feature.
2. **Given** a resolution r from 2 to 5, **When** a frame is made as Tiles, **Then** the picture is a grid of 12 × r by 7 × r tiles, each tile with one flat color, and the picture is 252 × 168 pixels.
3. **Given** a resolution r from 2 to 5, **When** a frame is made as Blended tiles, **Then** it is the same grid of 12 × r by 7 × r tiles with the colors of neighboring tiles fading into each other across the edges they share, as for the original grid.
4. **Given** a resolution r from 2 to 5, **When** a frame is made as Contour, **Then** the contour is drawn from the grid of 12 × r by 7 × r interpolated values, so that it follows the notes with finer steps than at resolution 1.
5. **Given** a frame and a resolution r, **When** the interpolated grid is made, **Then** its four corner values are the original four corner values, and every interpolated value is between the smallest and the largest of the original values it is made from.
6. **Given** a frame in which every note has the same value, **When** it is made at any resolution, **Then** every value of the finer grid is that same value, so the picture is as flat as it is at resolution 1.
7. **Given** the same file and settings, **When** frames are created twice, **Then** the two sets of frames are identical.
8. **Given** the number of frames and the timing of the file, **When** frames are created at any resolution, **Then** they are the same as at resolution 1.

---

### User Story 2 - Choose the resolution on the page and through the server (Priority: P2)

The settings column has a new **Resolution** control: a slider from 1 to 5 in whole steps, starting at 1, with a readout that says what it means ("1×", "3× (36 × 21)"), and an info button that explains it. The result summary shows the resolution that was used. In requests the setting is the optional field `resolution`, a whole number from 1 to 5 (1 when not sent). A value that is not a whole number from 1 to 5 is refused with a clear message, and the response reports the resolution used. The control works with every image type.

**Why this priority**: The finer picture (Story 1) can be asked for through the server, but users need to choose it on the page.

**Independent Test**: Open the page, move the Resolution slider to 3, create frames, and see the finer picture play and "Resolution: 3× (36 × 21)" in the summary. Move it back to 1 and create again: the picture is the original one.

**Acceptance Scenarios**:

1. **Given** the page is opened, **When** the settings are shown, **Then** the Resolution control is there, set to 1, with its readout "1×" and an info button.
2. **Given** the slider is moved, **When** the user looks at the readout, **Then** it shows the chosen multiple and the grid size it gives (for example "3× (36 × 21)").
3. **Given** the user activates the Resolution info button, **When** the popover opens, **Then** it explains that the picture is made finer by interpolating between the notes, that 1× is the original 12 × 7 and the highest is 5×, and that tiles get smaller (or contour steps finer) at the same picture size.
4. **Given** frames have been created, **When** the result is shown, **Then** the summary includes the resolution used, for example "Resolution: 3× (36 × 21)".
5. **Given** a request with `resolution` set to a whole number from 1 to 5, **When** the server receives it, **Then** it creates frames at that resolution and the response reports `resolution`.
6. **Given** a request without `resolution`, **When** the server receives it, **Then** the resolution is 1 and the frames are those of today.
7. **Given** a request with a resolution that is empty, not a number, not a whole number, below 1 or above 5, **When** the server receives it, **Then** it is refused before a job is created, with a message that says it must be a whole number from 1 to 5.
8. **Given** the resolution slider, **When** a job is running, **Then** the control is disabled, like the other settings.

---

### User Story 3 - It works with smoothing, the threshold, the colormap and the other image settings, and stays practical (Priority: P3)

The finer grid is made from the smoothed values, so Smoothing and its window, the Threshold, the Colormap and the Blend width all keep working with it. The Threshold hides a tile (or lowers the contour) wherever the value there is below it, so at a higher resolution the hidden region follows the interpolated values and has a finer edge. A job at the highest resolution still finishes in a practical time with every image type, and the frame files stay a sensible size.

**Why this priority**: These are the interactions with the existing settings and the practical limits. They define the result when features are combined but are secondary to the picture itself.

**Independent Test**: Create frames at resolution 5 with smoothing 0.5 and window 3, a Threshold of 5 and the `hot` colormap, once for each image type, for a 10 second file at 30 frames per second. Each job finishes in under a minute, the pictures use the colormap, and the finer edge of the hidden region is visible.

**Acceptance Scenarios**:

1. **Given** smoothing above 0, **When** frames are made at a higher resolution, **Then** the interpolation is made from the smoothed values (the same ones the tiles are colored from at resolution 1).
2. **Given** a Threshold above 0, **When** a value of the finer grid is below the threshold (a share of the loudest note value in the file), **Then** its tile is black (Tiles and Blended tiles) or it is treated as 0 (Contour); values at or above it keep their color.
3. **Given** any colormap that the page offers, **When** frames are made at a higher resolution, **Then** they use that colormap with the same scale as at resolution 1 (the strongest note of the file is still the last color), and changing the colormap changes only the colors.
4. **Given** the Blend width, **When** Blended tiles are made at a higher resolution, **Then** it still means a share of a tile's width, so the fades get narrower in pixels as the tiles get smaller, and the middle of each tile stays flat.
5. **Given** a silent file, **When** it is made at any resolution, **Then** the pictures are as at resolution 1: every tile the colormap's first color (Tiles and Blended tiles), or one uniform picture (Contour), and nothing fails.
6. **Given** a file of 10 seconds at 30 frames per second (300 frames), **When** frames are created at resolution 5 with any image type, **Then** the job finishes within one minute on the development machine.

---

### Edge Cases

- **Resolution 1** gives the original grid, so nothing changes: the interpolation of a grid onto itself is the identity.
- **Positions that do not fall on an original note**: with the evenly spaced positions from the first to the last column and row, only the grid's edges are guaranteed to be at original notes; the other values are between notes (this is what "interpolated" means here).
- **Tile sizes that are not a whole number of pixels**: 252 and 168 do not divide evenly by every number of columns and rows (60 columns are 4.2 pixels wide, 35 rows 4.8 pixels tall). The picture keeps its size, and each tile's edges are at the nearest whole pixel, so tiles differ by at most one pixel in width or height.
- **The loudest note between sample positions**: the new grid's positions are evenly spread from the first to the last column and row, so beyond the corners they usually do not land exactly on an original note. The loudest note of a frame can therefore fall between two positions, and the largest value of the finer grid can be a little below the original one (never above it). The colors' scale and the Threshold's reference are the file's largest *original* smoothed value at every resolution, so at a higher resolution the strongest tile can be a step short of the colormap's last color; only a note that lies exactly on a sample position (always the four corners) keeps its exact value.
- **A very quiet or very loud note next to silence**: the values between them step down smoothly, so the picture shows a ramp, not a jump, and nothing exceeds the loudest note.
- **The four highest notes (84 to 87)**, which are not drawn, still count when the largest value of the file is found, as for every image type, and are not part of the grid that is interpolated.
- **Hidden notes**: the Threshold works on the values of the grid that is drawn (see Assumptions), so at resolution 1 it is exactly what it is today.
- **Results from before this feature** (frames already created) are not changed. Only new submissions can use the setting.
- **File size**: finer tiles mean many more colors in a Tiles picture than the 84 of today, so those files are larger than at resolution 1.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to choose a **resolution** that is a whole number from 1 to 5, **1** being the default on the page and when a request does not say. The grid of values that a frame is drawn from is 12 × r columns by 7 × r rows at resolution r.
- **FR-002**: At resolution 1, frames of every image type MUST be identical, file for file, to those made before this feature.
- **FR-003**: For a resolution r above 1, the grid MUST be made from each frame's smoothed values of the 84 drawn notes by interpolation: evenly spaced positions made with `np.linspace` from the first to the last column (12 × r of them) and from the first to the last row (7 × r of them), with the values read by linear interpolation (`np.interp`) between the original neighbors, along the columns and along the rows. The four undrawn notes are not part of this grid.
- **FR-004**: Every value of the interpolated grid MUST lie between the smallest and the largest value of the original values it is made from, and the grid's corner values MUST equal the original corner values, so the file's largest value (and therefore every color scale) is the same at every resolution.
- **FR-005**: With the image types Tiles and Blended tiles, a frame MUST be a grid of 12 × r by 7 × r tiles, each colored from its own interpolated value exactly as a tile is colored today (the same colormap and the same scale), in a picture of 252 × 168 pixels with each tile edge at the nearest whole pixel.
- **FR-006**: With the image type Contour, the contour MUST be drawn from the interpolated grid (12 × r by 7 × r values) in the way it is drawn from the original grid.
- **FR-007**: The Blend width MUST keep meaning a percentage of a tile's width, so that at a higher resolution the fade reaches a proportionally shorter distance in pixels, the middle of each tile stays flat, and the outer border is not blended, as today.
- **FR-008**: The Threshold MUST apply to the values of the grid that is drawn: a value below the chosen share of the file's largest value gives a black tile (Tiles, Blended tiles) or is treated as 0 (Contour). Smoothing and its window MUST be applied before the interpolation.
- **FR-009**: A frame whose values are all the same, and a silent file, MUST give the same kind of picture at every resolution as at resolution 1, without error.
- **FR-010**: The frame count, the timing of the frames, the picture size and the file names MUST be the same at every resolution, and the same file and settings MUST always give identical frames.
- **FR-011**: The page MUST offer the **Resolution** control (a slider from 1 to 5 in whole steps, starting at 1) with a readout of the multiple and the grid size it gives, an info button that explains it, and a result summary line that shows the resolution used; the control MUST be disabled while a job runs.
- **FR-012**: The server MUST accept the optional field `resolution`, refuse a value that is not a whole number from 1 to 5 (including an empty value) with a clear message, before any job is created, and report the resolution used in its response.
- **FR-013**: A job at resolution 5 MUST finish in a practical time for every image type (SC-005).
- **FR-014**: The documentation's description of the settings MUST be updated to describe the resolution.

### Key Entities *(include if feature involves data)*

- **Resolution**: The whole number from 1 to 5 by which the grid is made finer, chosen for each job. 1 is the original 12 × 7 grid.
- **Original grid**: The 7 × 12 array of one frame's smoothed values of the 84 drawn notes (row = octave, column = note name).
- **Interpolated grid**: The 7r × 12r array made from the original grid by interpolation, from which a frame is drawn at resolution r. Its corners are the original corners, and its values stay between the original values.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At resolution 1, 100% of the frames of a test file are identical, file for file, to those made before this feature, for every image type.
- **SC-002**: At resolution r, a Tiles picture of a test file shows exactly 12 × r by 7 × r tiles in 252 × 168 pixels, with every tile's color equal to the colormap's color for its own interpolated value, for every r from 1 to 5.
- **SC-003**: For every frame and every resolution, the corner values of the interpolated grid equal the original corner values, and no interpolated value is below the smallest or above the largest original value; the file's largest value is the same at every resolution.
- **SC-004**: Between two neighboring notes of very different strength, the tiles of a higher-resolution picture step gradually from one color's position on the scale to the other's, in order, with no tile outside the range of the two.
- **SC-005**: A job of 300 frames (10 seconds at 30 frames per second) at resolution 5 finishes within one minute on the development machine for each of the three image types.
- **SC-006**: 100% of invalid resolutions (empty, not a number, fractional, below 1, above 5) are refused before a job is created, with a message that says the resolution must be a whole number from 1 to 5.
- **SC-007**: A user can set the resolution on the page, read what it does, and see the finer pictures in the player without leaving the settings column.
- **SC-008**: Two runs of the same file and settings give frames that are identical, at every resolution.

## Assumptions

- **Whole-number multiples only.** The request says "up to 5x the original size" and "the desired size". A whole number from 1 to 5 (five choices) is the simplest control and gives grids of 12 × 7, 24 × 14, 36 × 21, 48 × 28 and 60 × 35. Finer steps (a fractional multiple, or choosing columns and rows separately) can be added later without changing how the grid is made.
- **The picture keeps its size** (252 × 168 pixels), because the frame player and the rest of the page expect it and the request says the result is "smaller tiles". Because 252 and 168 do not divide evenly by every grid size, tile edges are at the nearest whole pixel and neighboring tiles can differ by one pixel in width or height.
- **The interpolation spans the original grid from its first to its last column and row.** The request names `np.linspace` and `np.interp`; evenly spaced positions from the first to the last original column and row make the corner values the original ones. Interpolation is linear, and it is done along the columns and along the rows (the same result in either order), so a value never goes beyond the values it is made from. Rows (octaves) and columns (note names) are interpolated separately, so the end of one row of the grid and the start of the next are never treated as neighbors, because they do not touch in the picture.
- **The Threshold works on the finer grid's values**, because those are what is drawn: a tile or contour point whose interpolated value is below the threshold's share of the file's largest value is hidden. This is an interpretation: the threshold could instead hide the original notes before the interpolation, which would make a hidden note's surroundings fade gradually to nothing. The first reading keeps the Threshold meaning "values below this are not shown" at every resolution and is exactly today's behavior at resolution 1.
- **Colors use the same rules as today.** A tile's color is the colormap's color for its own value on the same square-root scale as now (Tiles and Blended tiles), and the contour uses its own scale as defined by the contour feature; the interpolation changes the values, not the colors' meaning.
- **A Tiles picture at a higher resolution has more than 84 colors**, so it is stored in a way that can hold them, which makes the files larger than today's. The size is not otherwise bounded by this spec.
- **The setting is chosen when frames are created**, like every other setting; changing it means submitting again.
- This feature is about how a frame's values are turned into a picture. Audio playback, the note analysis, smoothing, the frame player and the page layout (apart from adding one control and one summary line) are unchanged.
