# Feature Specification: 3D export of Contour and Chromatic Wireframe (Wavefront OBJ files)

**Feature Branch**: `045-obj-export-mode` (no git branch created; spec directory name only)

**Created**: 2026-11-18

**Status**: Draft

**Input**: User description: "for the contour and chromatic wireframe image types, create a special export mode that exports to a set of wavefront object file.  Break the files up into .obj files per-frame.  each 4 adjacent points in the X, Y, Z direction will form a face.   For contour each frame occupies the XY plan.  For wireframe each frame will different points in the Y direction, and the vertices of each point.  The format of the vertices should include the color, e.g.: v 1 3 4 128 128 128.  Only the 12x7 points will be exported as vertices for contour, and only the 12 points for each note amplitude in the X direction will be exported for wireframe.  So it won't be 'curved' - the curve will be added using modifiers in blender.  If required, the files should be normalized such that axis is in roughly the same magnitude, e.g. values from 0-12."

**How the user's words are read** (the terms used in the rest of this document):

- **Export mode** is an option of a job, offered for the two pictures **Contour** and **Chromatic Wireframe**. When it is on, the job writes, besides the usual pictures, **one `.obj` file for each frame** of the job. The files are Wavefront OBJ files, a plain-text 3D format that Blender (and most 3D programs) can open.
- A **point** is one vertex: a line `v x y z r g b` with the position and the **color** of the point. The user's example is `v 1 3 4 128 128 128`; the user chose the color as **three decimals from 0 to 1** (for example `0.502 0.502 0.502`, the same grey), which is what Blender's own OBJ importer reads, not whole numbers up to 255.
- A **face** is made of **4 adjacent points**: the four corners of one cell of the grid of points (two neighbours in one direction and the two next to them in the other direction), so the points of a frame form a mesh of four-sided faces (quads). The surface is **not curved**: the exported points are the only points, joined by flat faces; any rounding or curve is added afterwards in Blender with modifiers (for example subdivision).
- **Contour** (an existing picture): every frame is a grid of **12 columns** (the 12 note names, A first) by **7 rows** (the 7 octaves), 84 values. In the export each value is a point, so a frame is **84 points** in a flat grid in the **XY plane** that stands up in **Z** by the value of the note (the loudness).
- **Chromatic Wireframe** (an existing picture, feature 039): every frame is one line across the picture made from 12 letters. In the export the line of a frame is **12 points**, one for each of the 12 letters, in order along **X**, and the height of each point (**Z**) is the **amplitude** of the letter (the share of the full radius that the letter's circle has in Chromatic Decay, the amplitude of the letter's sine in the picture). The line is not drawn as the sum of 12 sine waves: the sine, which is the curve, is left to Blender. **Different frames are at different places in the Y direction**, so a stack of lines forms a surface: the file of a frame holds the line of the frame in front (Y = 0) and the lines of the **11 frames before it** behind it, each one further along Y (Y = 1 for the frame before, up to Y = 11), as the picture shows the line of the current frame in front and the earlier ones behind it. At most 12 lines, so up to 12 x 12 = 144 points and 11 x 11 = 121 faces.
- **Normalized**: the positions are scaled to a common, small range, so that the three axes are about the same size when the files are opened in Blender (one unit is one grid cell, not a number of pixels or seconds): X from 0 to 11, Y from 0 to 6 (Contour) or 0 to 11 (Wireframe), Z from 0 to 12.
- **The user's answers** (asked when the specification was written): the file of a wireframe frame holds that frame and the 11 before it; the export is made **in addition to** the PNG pictures (the frame player and the video keep working); the colors are written as 0 to 1 decimals.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Export Contour as one surface per frame (Priority: P1)

A user makes a Contour picture of a piece of music with the export mode on. Besides the PNG frames they get one `.obj` file for each frame. Opening one in Blender shows the 12 x 7 values as a mesh lying in the XY plane, standing up in Z where the notes are loud, each point with the color that the picture gives that value.

**Why this priority**: This is the core of the request and the simpler of the two pictures: a fixed grid of 84 points and 66 faces per frame. It delivers value on its own (a Contour animation that can be rebuilt and rendered in 3D).

**Independent Test**: Make a Contour job with the export on from a short file with a few notes and open the resulting files with a plain parser: count the files, the vertex lines (84), the face lines (66), check that every vertex line has a position and a color and every face refers to existing vertices.

**Acceptance Scenarios**:

1. **Given** a Contour job with F frames and the export mode on, **When** the job is made, **Then** there are exactly F `.obj` files, one for each frame, numbered like the pictures (`frame_0.obj` goes with `frame_0.png`, and so on).
2. **Given** any of those files, **When** it is read, **Then** it has exactly 84 vertex lines and 66 face lines (the 11 x 6 cells between neighbouring points), and no other points: no points of a finer or curved contour.
3. **Given** the point of the note in column `c` (0 to 11) and row `r` (0 to 6), **When** its vertex line is read, **Then** X is `c`, Y is the row placed so that the picture seen from above (looking down the Z axis) matches the contour picture, and Z is the value of the note scaled to 0 to 12.
4. **Given** a frame in which every value is 0 (a silent moment), **When** its file is read, **Then** it still has the 84 points and 66 faces, all in the plane Z = 0, in the color of the colormap for 0.
5. **Given** the beat wave or the smoothing of the grid is on in the job, **When** the points of a frame are written, **Then** their heights are the values the picture of that frame uses (the same grid), so that the surface is the one the picture shows from above.

---

### User Story 2 - Export Chromatic Wireframe as a stack of lines (Priority: P1)

A user makes a Chromatic Wireframe picture with the export mode on. For each frame they get an `.obj` file that holds the 12-point line of that frame in front and the lines of the 11 frames before it behind it, so the file is a surface across the letters and back in time. In Blender the user adds a modifier to turn the straight pieces into the curve.

**Why this priority**: This is the second picture named in the request. It is P1 because the request names both pictures, and it carries the two interpretation decisions (what is in the file and what Z means).

**Independent Test**: Make a Chromatic Wireframe job with the export on from a file with at least 12 frames and check the file of a frame from the 12th on: 144 vertices, 121 faces, X from 0 to 11, Y from 0 to 11, Z from 0 to 12, one color for each line of 12.

**Acceptance Scenarios**:

1. **Given** a Chromatic Wireframe job with F frames and the export mode on, **When** the job is made, **Then** there are exactly F `.obj` files, numbered like the pictures.
2. **Given** the file of frame `i` with `i >= 11`, **When** it is read, **Then** it has 144 vertex lines (12 letters in each of 12 lines) and 121 face lines, X is the letter number (0 for A to 11), and Y is 0 for the line of frame `i`, 1 for frame `i - 1`, and so on up to 11 for frame `i - 11`.
3. **Given** the file of frame `i` with `i < 11`, **When** it is read, **Then** it holds the lines of frames 0 to `i` only (`i + 1` lines, so 12 x (i + 1) vertices and 11 x i faces); the file of frame 0 has the 12 points and no faces.
4. **Given** the point of letter `b` in a line, **When** its vertex line is read, **Then** Z is the amplitude of that letter in that frame scaled so that the full radius is 12, and a letter with no points is not 0 but the smallest amplitude the picture gives it (a twelfth of the full radius, Z = 1), as in the picture.
5. **Given** the 12 points of one line, **When** their colors are read, **Then** all 12 have the same color, the color the picture gives that line (the colormap at the place of its frame in the beat), and the line of an earlier frame keeps the color of its own frame.
6. **Given** the points of a line, **When** they are written, **Then** only the 12 letter points are written: the sine curve across the width of the picture, its frequency and its contrast stretch are not applied.

---

### User Story 3 - Choose the export on the page and download the files (Priority: P2)

A user who chooses Contour or Chromatic Wireframe sees an option to export the 3D files, turns it on, makes the frames, and then downloads all the `.obj` files in one go next to the pictures.

**Why this priority**: Without it nobody can ask for or get the files, but the files themselves (Stories 1 and 2) are the substance, and the page is a thin layer over them.

**Independent Test**: Choose Contour, turn the option on, make a job, press the download and check that the downloaded package holds one `.obj` file for each frame; choose another picture and check the option is not offered.

**Acceptance Scenarios**:

1. **Given** the page with Contour or Chromatic Wireframe chosen, **When** the settings are shown, **Then** an option to export 3D files (off by default) is shown, with a short help text that says what the files are, what the axes mean and the range 0 to 12.
2. **Given** any other picture chosen, **When** the settings are shown, **Then** the option is not shown.
3. **Given** the option is on and a job has finished, **When** the result is shown, **Then** the summary says that the export was made, and there is one download of all the files together (a single package, so that a few thousand small files are not downloaded one by one), in addition to the frame player and the video, which work as before.
4. **Given** the option is off (the default), **When** a job is made, **Then** no `.obj` file is made, the pictures are exactly what they were, and no download for the files is offered.
5. **Given** the request names the export for a picture that has no export, **When** it is sent, **Then** it is refused with a clear message that says which pictures have it (and no job is made).

---

### Edge Cases

- **A silent file or a frame without a sound**: every file is still written, with all the points at their lowest height (Contour Z = 0; Wireframe Z = 1) and the colors of the lowest values. No file is skipped, so that file numbers and picture numbers always match.
- **The first 11 frames of a Wireframe job**: fewer than 12 lines exist; the file holds the lines there are (see Story 2, scenario 3); with one line there are points and no faces.
- **One frame only**: one file; for Contour 84 points and 66 faces; for Wireframe 12 points and no faces.
- **Loudness scale over the whole file**: heights are scaled by the loudest value of the whole file (not the loudest of each frame), so that the heights of different frames can be compared and an animation does not flicker in height; the colors are as in the pictures.
- **Many frames**: a file is small (a few kilobytes), but a long piece at a high frame rate means thousands of files; they are made with the frames and offered in one package.
- **Other settings**: the colormap, the frame rate and, for Contour, the beat wave and the grid smoothing apply as to the pictures; the picture size does not change the files (the points are in grid units, not pixels).
- **Number format**: every number is written the same way on every machine (a dot as the decimal point, no thousands separator, no exponent), so the files open in any program in any language setting.
- **A job made before the option existed, or with the option off**: it has no export and asking for the files is answered with a clear "no export was made for this job".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST offer an **export mode** (off by default) for the pictures Contour and Chromatic Wireframe. With it on, a job MUST write, besides the usual pictures, one Wavefront OBJ file for each frame, numbered like the pictures. With it off nothing is exported and the pictures MUST NOT change in any way.
- **FR-002**: Each file MUST be a plain-text OBJ file that is complete in itself: its points are numbered from 1 within the file, its faces refer only to its own points, and it needs no other file (no material or texture file).
- **FR-003**: Each point MUST be a line `v x y z r g b`: the position, then the color as three numbers from 0 to 1 (red, green, blue). Numbers MUST be written with a dot as the decimal point and without an exponent, with enough digits that the same input always gives the same text.
- **FR-004**: Each face MUST be a line `f a b c d` of **four adjacent points** (the corners of one cell of the grid, in the order round the cell) whose normal points up (toward +Z, for Contour and for Wireframe), so that the surface is lit from above in Blender. No face MUST use points that are not neighbours.
- **FR-005** (Contour): A frame's file MUST hold exactly the **12 x 7 = 84 points** of the grid the picture draws (after the grid smoothing and the beat wave, if they are on), one per note, in the XY plane, with Z the height of the value; and the **11 x 6 = 66 faces** between neighbouring points. It MUST NOT hold the points of the contour lines, the filled levels or any interpolation.
- **FR-006** (Contour): X MUST be the column (the note name, 0 to 11, A first), Y the row (the octave, 0 to 6), placed so that the surface seen from above has the orientation of the picture (the first row of notes at the top of the picture is the highest Y). Z MUST be the value of the cell (after the smoothing the picture applies) scaled so that the loudest value of the whole file is 12 (0 stays 0). The picture's smoothing averages a note with its neighbours, so the smoothed height of a lone loud note is lower than 12; Z never goes above 12.
- **FR-007** (Contour): The color of a point MUST be the colormap's color at the point's value on the same scale the picture of that frame uses (0 to the frame's largest value), so the loudest note of a frame is at the end of the colormap.
- **FR-008** (Wireframe): A frame's file MUST hold the line of the frame and the lines of the up to 11 frames before it. Every line MUST be **12 points**, one for each letter, in order along X (0 for A to 11), at the Y of its frame: 0 for the frame of the file, 1 for the frame before, up to 11. The faces MUST join each point to its neighbour along X and the point of the same letter in the next line along Y: `(12 - 1) x (lines - 1)` faces.
- **FR-009** (Wireframe): Z of a point MUST be the **amplitude of its letter** in its frame (as the picture's sine uses it: the radius of the letter's circle over the full radius, from a twelfth to 1), scaled so that the full radius is 12. The points MUST NOT be curved: the sine of the letters, its frequency and the contrast stretch of the picture MUST NOT be applied or sampled, only the 12 amplitudes of each line are exported.
- **FR-010** (Wireframe): The 12 points of a line MUST have one color, the color of the picture's line for that frame (from the colormap, by the frame's place in the beat), and an earlier line keeps its own color.
- **FR-011**: The positions MUST be normalized so that the three axes are about the same size: in grid units, X from 0 to 11, Y from 0 to 6 (Contour) or 0 to 11 (Wireframe), Z from 0 to 12, whatever the picture size, the frame rate, the length of the file or the loudness of the music.
- **FR-012**: The files of a job MUST be made with its frames, with the same frame numbering as the pictures, and be available to download **together** in one package from the job. Asking for the package of a job that has none MUST be answered with a clear message.
- **FR-013**: The page MUST offer the export option only for Contour and Chromatic Wireframe, with a help text, and the result summary MUST say whether the files were made; with it on, the frame player and the video MUST keep working.
- **FR-014**: A request for the export for any other picture MUST be refused with a clear message before any work is done; a value that is not a yes or a no MUST be refused the same way.
- **FR-015**: The same music and settings MUST give byte-identical files every time.

### Key Entities *(include if feature involves data)*

- **Export mode**: the on/off option of a job, available for two pictures; on means that a set of OBJ files is written besides the pictures.
- **OBJ file**: the 3D description of one frame: a list of points (position and color) and a list of four-point faces.
- **Point (vertex)**: a position in grid units with an RGB color from 0 to 1. For Contour a point is one of the 84 notes of the frame; for Wireframe a point is one letter in one line.
- **Face (quad)**: four neighbouring points of the mesh. A Contour frame has 66; a full Wireframe frame has 121.
- **Line (Wireframe)**: the 12 points of one frame, at one Y, in one color.
- **Package of the job**: all the OBJ files of a job, to download at once.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a job with F frames and the export on, there are exactly F OBJ files, numbered like the pictures, in 100% of the jobs tried (Contour and Wireframe, short and long files, one frame, silence).
- **SC-002**: In 100% of the Contour files there are exactly 84 points and 66 faces; in 100% of the Wireframe files of frame 11 or later there are exactly 144 points and 121 faces; earlier frames have `12 x (i + 1)` points and `11 x i` faces.
- **SC-003**: In 100% of the files every coordinate is inside its range (X 0 to 11, Y 0 to 6 or 0 to 11, Z 0 to 12), and Z never goes above 12; in Wireframe a letter with 24 or more points is exactly 12, in Contour the heights are in proportion to the values of the picture's smoothed grid (so a note half as loud is half as high).
- **SC-004**: A plain OBJ reader (written for the tests, following the format) reads 100% of the files without error: every point line has six numbers, the three colors are between 0 and 1, every face has four existing, neighbouring points and no point is used by no face (except the 12 points of a one-line file).
- **SC-005**: The colors of the points agree with the pictures of the same frames: for Contour the color of the point of the loudest note of a frame is the last color of the colormap, and a silent frame is the first color; for Wireframe all 12 points of a line have the color the picture gives the line.
- **SC-006**: A job with the export off gives the same files as before the feature, picture for picture and byte for byte, and none of the OBJ files, in 100% of the pictures.
- **SC-007**: Making the same job twice gives identical OBJ files (byte for byte).
- **SC-008**: A user goes from choosing Contour or Chromatic Wireframe to having all the OBJ files of a job in one download with one extra setting and one extra click after the job.
- **SC-009**: Making the export adds no more than 50% to the time of making the frames of the same job (the files are tiny compared with the pictures).

## Assumptions

- **The export is an extra**: the pictures are still made (the answer chosen), so the frame player, the video and the frame count work as before; the export does not replace them.
- **Heights are scaled by the whole file**: Contour Z and Wireframe Z use the loudest value (Contour) or the full radius (Wireframe) of the whole job as 12, so frames can be compared. The colors of Contour follow the picture, which uses the largest value of each frame, so a quiet frame still shows the whole colormap while its surface stays low.
- **The grid for Contour is the picture's grid**: after the grid smoothing and the beat wave of the job (the picture is made from those values), which is the surface the picture shows from above. The picture's contour levels are not exported.
- **The amplitude for Wireframe is the letter's radius share**: in Chromatic Decay a letter with 0 points still has a small circle (a twelfth of the full radius) and a letter with 24 or more points has the full radius; the wireframe's sine uses this as its amplitude. This is the value exported, so Z is from 1 to 12. The letter's point count, which sets the frequency of its sine in the picture, is not exported, since the curve is made in Blender.
- **Y direction of the Wireframe**: the frame of the file is at Y = 0 and earlier frames at larger Y (further behind), as the picture shows earlier lines behind the current one; 12 lines (the current and 11 before) is the window, a fixed number that does not depend on the picture size, unlike the number of lines the picture shows.
- **Orientation**: Z is up, X to the right and Y away from the viewer, the arrangement Blender's OBJ importer uses by default (Y forward, Z up); faces are ordered counterclockwise when seen from above.
- **File names and package**: `frame_<index>.obj` in an export folder of the job, with the same index as `frame_<index>.png`; the package is a single ZIP file. Frame numbering starts where the pictures' numbering starts.
- **One scale for the files**: the Contour X and Y are the cell numbers (0 to 11 and 0 to 6) and Z is 0 to 12; these are not stretched to one cube, so one unit is the same length on every axis and Contour is wider than deep.
- **Other pictures and old jobs**: the export is not offered for the other pictures and a request for them is refused (not ignored), so a user is never told they got files they did not get.
- **Out of scope**: materials, textures, normals, smooth shading, curved surfaces, one file for the whole animation, any other 3D format (STL, PLY, glTF), exporting the other picture types, and importing the files into Blender or building the Blender modifiers.
- **Dependencies**: the existing Contour grid and its smoothing and beat wave (features 015 and 028), the 12 letters, points and amplitudes of Chromatic Decay and the line colors of Chromatic Wireframe (features 035 and 039), the frame rate and the fixed 60 ms buffers (feature 043), and the way a job keeps its frames and offers downloads (the video download, feature 029).
