# Feature Specification: Contour Image Type

**Feature Branch**: `015-contour-image-type` (no git branch created; spec directory name only)

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description: "create a new image type: contour.  Use matplotlib contourf function.  The scales will always be from the 0 to max smoothed value.  XY will be created with np.linspace from 0to max value, with the number of steps being the number of 12x7 for x and y.  The Z values will just be the smoothed note values.  Use the selected colormap, set the axis decorations off (a.set_axis_off).  Use pyplot.savefig to create the PNG of the file."

## Clarifications

### Session 2026-10-11

- Q: How many contour levels (bands) should the picture have? -> A: Not fixed by this feature. The levels are chosen by matplotlib itself (its automatic choice for the data of each frame); nothing about the number or the positions of the levels is hard-coded. The color scale stays fixed from 0 to the largest smoothed value of the file, so the color of a given strength does not depend on which levels matplotlib picks.
- Q: What range should the X and Y coordinates cover? -> A (asked 2026-10-11, after the first implementation): from 0 to the largest smoothed value **of the current frame**, worked out again for every frame, instead of the file's largest value. The color scale is not affected: it still runs from 0 to the file's largest value, so a strength keeps its color in every frame. Because the axes are not shown and X and Y scale together, this changes the coordinates `contourf` receives but not a pixel of the picture.
- Q: Is the colormap list fixed? -> A: No. The user corrected the colormap names and may add or change them by hand. Contour works with whatever names the Colormap setting offers, so long as each one is a valid matplotlib colormap name (matplotlib's names are case-sensitive, for example `Greys`) and the server's list and the page's list are the same. Nothing in the feature, and none of its tests, depends on a particular colormap or on how many are offered.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A contour picture of the notes (Priority: P1)

Today a frame is a grid of tiles, flat or with soft edges. The user wants a third kind of picture, **contour**, that shows the same 12 × 7 grid of notes as a **filled contour map**: instead of one square per note, the strength of the notes is drawn as bands of color that flow from one note to the next, like the elevation map of a landscape in which every note is a point on a 12 × 7 grid and its strength is the height at that point. Strong notes appear as peaks of the colormap's far end and quiet areas as the start of the scale, and neighboring notes of similar strength merge into one smooth region.

The picture is made with matplotlib's filled contour drawing. The grid is the same as for the tiles: one value for each of the 84 drawn notes, arranged by octave (rows) and note name (columns), where each value is the note's **smoothed value** in that frame. The coordinates of the grid are `np.linspace` from 0 to the largest smoothed value **of the frame being drawn** (worked out again for every frame), with 12 steps across and 7 steps up, and the color scale always runs from **0 to the largest smoothed value** of the whole file, so a given strength has the same color in every frame. The picture uses the colormap that the user selected, shows no axes, ticks, labels or frame (the axis decorations are switched off) so that the contour fills the whole picture, and is saved as a PNG with matplotlib's `savefig`.

Which kind of picture is made is chosen by name, as for the other types: **tiles** (the default), **blended** and the new **contour**.

**Why this priority**: This is the whole feature: a third kind of picture and the way to choose it. The page control (Story 2) and the combination with the other settings (Story 3) build on it.

**Independent Test**: Make frames from a file in which one note sounds strongly in a stretch of the file and all others are quiet. Choose the image type contour and the colormap `hot`. In those frames the picture has a single bright region (the end of the scale) around the position of that note, fading through the colormap's colors to its start in the areas far from it, with no axes or border; the same strength has the same color in other frames of the file.

**Acceptance Scenarios**:

1. **Given** the image type contour, **When** a frame is drawn, **Then** it is a filled contour picture of the 7 × 12 grid of the frame's smoothed note values (row = octave, column = note name), with the colormap that was chosen.
2. **Given** a file, **When** its frames are drawn as contour, **Then** the color scale is the same for every frame: it runs from 0 to the largest smoothed note value anywhere in the file (all 88 notes count), so a note of the same strength has the same color in any frame.
3. **Given** a frame, **When** it is drawn as contour, **Then** the picture shows only the contour: no axes, no tick marks, no labels, no border and no margin, and it has the same size as the other image types (252 × 168 pixels).
4. **Given** two notes of different strength, **When** the colors at their own grid points are compared, **Then** the stronger note has a color at the same or a later position on the colormap, never an earlier one.
5. **Given** the note with the largest smoothed value in the file, **When** its frame is drawn, **Then** the area at its grid point has the last color band the picture uses (the band that contains the end of the scale), and a grid point whose value is 0 has the first band; how many bands there are between is decided by matplotlib.
6. **Given** the same file and settings, **When** frames are created twice, **Then** the two sets of frames are identical.
7. **Given** the number of frames and the timing of the file, **When** frames are created as contour, **Then** they are the same as for the other image types made with the same settings.

---

### User Story 2 - Choose the contour image type on the page and through the server (Priority: P2)

The Image type control on the page offers a third choice, **Contour**, next to Tiles and Blended tiles, with a short explanation of what it looks like in its info text. The **Blend width** slider is only for Blended tiles, so it stays disabled for Contour (as it is for Tiles). The result summary shows the image type that was used ("Contour"). In requests the name is `contour`. The frame player plays contour pictures like any other.

**Why this priority**: The new picture (Story 1) can be asked for through the server, but users need to pick it on the page.

**Independent Test**: Open the page, choose Contour, create frames, see the contour pictures play and "Image type: Contour" in the summary. Choose Tiles again: the flat tiles come back and the Blend width slider is disabled in both cases.

**Acceptance Scenarios**:

1. **Given** the page is opened, **When** the settings are shown, **Then** the Image type control offers Tiles, Blended tiles and Contour, and Tiles is selected.
2. **Given** Contour is chosen, **When** the user looks at the Blend width slider, **Then** it is disabled (it has no effect on a contour picture); it is enabled only while Blended tiles is chosen.
3. **Given** the user activates the Image type info button, **When** the popover opens, **Then** it also describes what Contour looks like.
4. **Given** frames have been created as Contour, **When** the result is shown, **Then** the result summary includes "Image type: Contour" and does not show a blend width.
5. **Given** a request with `image_type=contour`, **When** the server receives it, **Then** it creates contour frames and the response reports `image_type` as `contour`; a `blend_width` sent with it is accepted and has no effect.
6. **Given** a request with an image type that is not one of the offered names (empty, unknown, wrong capitalization), **When** the server receives it, **Then** it is refused with a clear message that lists the three allowed names.

---

### User Story 3 - Contour works with the colormap, smoothing and the threshold, and stays practical (Priority: P3)

The contour picture is made from the same smoothed note values as the other types, so Smoothing and its window, the Threshold and the Colormap all apply to it: smoothing shapes the values that form the contour, the chosen colormap colors it, and the Threshold hides notes below it. A note hidden by the Threshold is treated as having no strength, so it does not raise the contour. A silent file gives a picture of one uniform color. The existing image types are not changed at all. Drawing a contour with matplotlib takes longer than drawing flat tiles, but a job still finishes in a practical time.

**Why this priority**: These are the interactions with the existing settings and the practical limits. They define the result when features are combined but are secondary to the picture itself.

**Independent Test**: Create contour frames with smoothing 0.5 and window 3, a Threshold of 5 and the `hot` colormap for a file with a loud and a quiet note. The note below 5% of the loudest does not appear in the contour; the quiet note above it does. Switch to Tiles with the same settings and the tile pictures are exactly what they were before this feature.

**Acceptance Scenarios**:

1. **Given** smoothing above 0, **When** frames are drawn as contour, **Then** the values that form the contour are the smoothed values (the same ones that the tiles are colored from), so the picture changes gradually while a note fades or rises.
2. **Given** a Threshold above 0, **When** a note's smoothed value is below the threshold (a share of the loudest note value in the file), **Then** it is treated as 0 in the contour and does not raise it; notes at or above the threshold keep their values.
3. **Given** any colormap that the page offers, **When** frames are drawn as contour, **Then** they use that colormap, and changing the colormap changes only the colors.
4. **Given** a silent file (every note has no strength), **When** frames are drawn as contour, **Then** every frame is one uniform color, the colormap's first color, and nothing fails.
5. **Given** the image types tiles and blended, **When** frames are created, **Then** they are identical, file for file, to those made before this feature.
6. **Given** a file of 10 seconds at 30 frames per second (300 frames), **When** frames are created as contour, **Then** the job finishes within one minute on the development machine and uses no window or display.

---

### Edge Cases

- **Strongest note**: the largest value is where the scale ends, so the strongest note's area has the last band of the colormap in the frame where it sounds; in other frames it is lower, because the scale is fixed for the whole file.
- **A frame in which every value is 0** (a quiet moment in the middle of a file, or all notes hidden by the Threshold) is one uniform picture of the colormap's first color, as for a silent file; matplotlib has no contour to draw there.
- **Only one note sounds**: the picture is a single peak around that note's grid point that spreads over the nearby grid points, because the contour is drawn between grid points.
- **Notes at the edge of the grid**: the contour reaches the picture's edges, since there are no axes, margins or border.
- **The four highest notes (84 to 87)**, which are not drawn, still count when the largest value is found, as for the other types, but are not part of the grid.
- **Blend width** is not used by Contour; a value sent with it is accepted and ignored, as for Tiles.
- **Results from before this feature** (frames already created) are not changed. Only new submissions can use the new type.
- **Future image types**: the choice is by name, so more can be added later without changing how the choice is made.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to choose the image type **contour** in addition to **tiles** and **blended**. **Tiles** MUST remain the default, on the page and when a request does not say.
- **FR-002**: With the image types tiles and blended, frames MUST be identical, file for file, to those made before this feature.
- **FR-003**: With the image type contour, each frame MUST be a filled contour picture (matplotlib's `contourf`) of a 7 × 12 grid of Z values, where the Z values are the smoothed note values of the 84 drawn notes arranged as in the tiles picture (note `n` at row `n // 12`, column `n % 12`). The X coordinates MUST be `np.linspace(0, top, 12)` and the Y coordinates `np.linspace(0, top, 7)`, where `top` is the largest smoothed note value of the frame being drawn, worked out again for every frame (clarified 2026-10-11). The color scale is separate (FR-004) and uses `max`, the largest smoothed note value anywhere in the file (all 88 notes count).
- **FR-004**: The color scale MUST always run from 0 to `max`, the same for every frame of a file, so that a given strength has the same color in every frame (the scale is fixed explicitly; it does not follow the levels that matplotlib happens to choose for a frame). The colors MUST be those of the colormap that the user selected, with a higher strength never at an earlier position on the colormap than a lower one.
- **FR-004a**: The contour levels MUST be chosen by matplotlib itself (its automatic level selection); the number and the positions of the levels MUST NOT be hard-coded.
- **FR-005**: The contour picture MUST show no axis decorations (the axes are switched off with `set_axis_off`): no axes, ticks, labels, border or margin, so that the contour fills the whole picture. It MUST be saved as a PNG with matplotlib's `savefig` on a backend that opens no window, and have the size of the other image types (252 × 168 pixels).
- **FR-006**: The contour picture MUST be oriented as the tiles picture is: the lowest octave at the top and the lowest note name at the left, so that the same note is in the same place in all image types.
- **FR-007**: Notes hidden by the Threshold (a smoothed value below the chosen share of `max`) MUST be given the value 0 in the contour grid. Smoothing and its window MUST be applied before the contour is made, as for the other types.
- **FR-008**: A file in which no note has any strength, and any single frame in which every value is 0, MUST give a picture of one uniform color, the colormap's first color, without error.
- **FR-009**: The Blend width MUST have no effect on contour pictures; the page MUST disable the Blend width slider for Contour and for Tiles, and the server MUST accept and ignore a blend width sent with `image_type=contour`.
- **FR-010**: The page MUST offer Contour in the Image type control and describe it in the control's explanation, and the result summary MUST show the image type used. The server MUST refuse an image type that is not one of the three offered names with a clear message that lists them, and the response MUST report the image type used.
- **FR-011**: The frame count and the timing of the frames MUST be the same for all image types.
- **FR-012**: The same file and settings MUST always give identical frames.
- **FR-013**: The documentation's description of the image types and settings MUST be updated to describe the contour type.
- **FR-014**: Contour MUST work with every colormap that the Colormap setting offers, with no code or test that depends on a particular name; the tests for the colormap setting and for contour MUST derive the names from the list itself, so that names added, removed or changed by hand keep them passing as long as each name is a valid matplotlib colormap and the server's and the page's lists match.

### Key Entities *(include if feature involves data)*

- **Image type**: The kind of picture made from a frame's note values: **tiles**, **blended** or **contour**, chosen by name for each job.
- **Contour grid**: The 7 × 12 array of smoothed note values (zero for notes hidden by the Threshold) of one frame, with X and Y coordinates `linspace(0, top, 12)` and `linspace(0, top, 7)`, `top` being the largest value of that frame; the contour levels over it are chosen by matplotlib.
- **Contour scale**: The range from 0 to the largest smoothed note value in the file, the same for every frame, over which the colormap is spread.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the image types tiles and blended, 100% of the frames of a test file are identical, file for file, to those made before this feature.
- **SC-002**: Contour frames have the same size (252 × 168) and the same count as tiles frames for the same file, and show no axes or border: the pixels along every edge of the picture are contour colors, not the white or black of a figure background.
- **SC-003**: At the grid point of each note, the color of a contour frame is the colormap's color for that note's value on the scale from 0 to the file's largest value, to within the width of one contour band (the bands are chosen by matplotlib); across the 84 notes of a frame a stronger note never has an earlier color than a weaker one.
- **SC-004**: A note of the same strength has the same color at its grid point in every frame of a file (the scale does not change from frame to frame).
- **SC-005**: With a Threshold above 0, a note below it leaves no peak in the contour (its grid point has the color of the value 0), for every colormap offered; a note above it does.
- **SC-006**: A silent file, and any frame in which every value is 0, gives a uniform picture of the colormap's first color for every colormap offered.
- **SC-007**: A job of 300 frames (10 seconds at 30 frames per second) as contour finishes within one minute on the development machine; no window or display is needed.
- **SC-008**: 100% of invalid image types (empty, unknown, wrong capitalization) are refused before a job is created, with a message that lists tiles, blended and contour.
- **SC-009**: A user can choose Contour on the page, read its explanation, and see the contour pictures in the player without leaving the settings column.

## Assumptions

- **A picture is made for every frame**, so a contour job takes longer than a tiles job. The target in SC-007 is a first estimate to be checked in planning with real measurements; if it cannot be met with matplotlib's drawing and `savefig`, planning will report the measured figure and propose a bound instead of dropping the requested approach.
- **The contour levels are chosen by matplotlib** (clarified 2026-10-11), not hard-coded: the request fixes the color scale (0 to `max`) but not the levels, and for now matplotlib's automatic choice is wanted. If a fixed number of levels is wanted later, it is a single value to add.
- **The picture has the same size as the other types** (252 × 168 pixels), because the frame player and the rest of the page expect it, and it is made by giving matplotlib a figure of exactly that size (a figure size in inches times a dots-per-inch value) with one axes that fills the whole figure.
- **The orientation follows the tiles picture** (lowest octave at the top, lowest note name at the left), not matplotlib's default of putting the first row of a grid at the bottom, so that the same note is in the same place in every image type. This is a detail the request does not state.
- **Hidden notes become 0 in the contour grid.** The request does not say how the Threshold applies to the contour. Treating a hidden note as having no strength is the closest equivalent of "its tile is black" for a picture that has no tiles.
- **The coordinates are `linspace` from 0 to the current frame's largest value, as requested (clarified 2026-10-11).** Because the axes are not shown, they only decide the proportions of the picture; the contour fills the picture whatever `max` is.
- **A silent file** has `max = 0`, and a frame whose values are all 0 has nothing to contour, which would give matplotlib no levels. Both are drawn as one uniform picture of the colormap's first color instead, which matches what the tiles picture shows for a silent file.
- **The colormap list is whatever the Colormap setting offers.** This spec only says that Contour uses the selected colormap. The list can be changed by hand (clarified 2026-10-11): a name must be a valid matplotlib colormap name and the same on the server and on the page, and nothing else is assumed about it, including how many colormaps there are, whether a scale starts or ends at black or white, or whether its first and last colors differ (a cyclic scale such as `hsv` starts and ends on the same color).
- **matplotlib draws on a backend without a window** (the non-interactive Agg backend), because the application runs on a server.
- **The image type is chosen when frames are created**, like every other setting; changing it means submitting again.
- This feature is about how frames are drawn. Audio playback, the note analysis, the frame player and the page layout (apart from adding one choice to an existing control and a rule for the Blend width slider) are unchanged.
