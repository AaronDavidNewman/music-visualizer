# Feature Specification: Generative Circles

> **Amended 2026-10-14 (feature 020, grouped settings).** On the page the circles settings were renamed: **Unit** is now **Movement**, **Size** is now **Radius**, **Circles per frame** is now **Notes** (and the summary says Memory for the circle memory), all inside a **Circles** group that is shown only for Circles; the controls the type does not use are no longer greyed out but not shown. **The Size setting became a real radius**: a whole number of pixels from **4 to 8** (default 4), request field `circle_radius` with the message `The circle radius must be a whole number from 4 to 8.`, replacing the circumference of 25 to 50 pixels (`circle_size`, now ignored if sent; a radius of 3.98 to 7.96). The unit message is now `The circle movement must be a whole number from 1 to 10.`. Where this document, or its earlier amendments, say size, circumference, 25 to 50 or `circle_size`, the radius governs; the Resize by volume factor (1 to 3) applies to the radius. See `specs/020-grouped-settings-ui/`.

**Feature Branch**: `019-generative-circles` (no git branch created; spec directory name only)

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "create a new image type that is generative circles.  The color of the circle will be based on the smoothed energy of the note.  Sort the selected notes, and base the placement of the next circle based on its relationship with the last note at that index.  The relative angle will be determined by the column (0-11, representing the letter C, C# etc), with each slot representing 30 degrees.  The distance the circle moves will be determined by the row: 4 will move 1 'unit', and one additional unit for each octave subtracted from 4.  So for instance, if the loudest note is a f5, it will be placed next to the loudest note in the previous frame, it will move 150 degrees relative to the previous strongest notes, and it will move one unit in that direction since 4 is one greater than 4.  If the note were f3, it would move in the opposite direction (210 degrees) 1 unit since 3-4 is -1.  The number of notes for this image type should be between 5 and 12, to avoid clutter.  The system should remember previous notes and their colors in a circular buffer, so they can be drawn in the future frames.  The buffer allows 100-500 notes.  The interpolate function won't make sense for this image type so it can be disabled.  The parameters unique to this image type will be: the distance of a 'unit', from 1 to 10 px, the memory size, 100-500, and the number of notes pre frame will be 5-12 not 1-84."

## Clarifications

### Session 2026-10-13

- Q: How many units does an octave give? The request says "4 will move 1 unit, and one additional unit for each octave subtracted from 4", but its examples had F5 and F3 each moving one unit. -> A: **Option C, the literal rule: the user said the examples were wrong.** The distance of a circle is **1 + |octave - 4| units**: a note of octave 4 moves 1 unit, and every octave above or below 4 adds one more unit. So F5 moves **2 units** at 150 degrees, F3 moves **2 units** at 210 degrees, a note in octave 6 or octave 2 moves 3 units, and the notes go from octave 1 (4 units) to octave 8 (5 units). Octaves below 4 still turn the direction around (the angle is mirrored, F3: 210 degrees), as the request says; octaves above 4 keep the angle of the note name.

### Session 2026-10-13 (look and size, after delivery)

- Q: The user asked: "set the background to be the middle color of the colormap. Draw each circle with opacity based on how 'old' it is, so that before it moves off the buffer it is barely visible. Make a counter for the circle circumference, from whatever it is now (it is kind of small) to about 50px." -> A: **(1) Background**: the middle color of the selected colormap, the entry halfway along its 256-color table (row 128 of 0 to 255). **(2) Opacity**: a circle `age` places back in the memory (0 for the newest) is drawn with the opacity (m - age) / m of its color over what is under it, m being the memory size: the newest circle is opaque, the opacity falls in a straight line, and the oldest circle of a full memory (age m - 1, one place before it is dropped) has 1 / m (1 to 3 parts in 255), so it is barely visible. **(3) Size**: "a counter for the circle circumference" is read as a new setting, **Size**, a whole number of pixels from **25 to 50** for the circumference of a circle, default **25** (the radius is size / (2 pi), 4.0 to 8.0 pixels; the circles the first version drew at the default unit had a radius of 4 pixels, a circumference of about 25), and the size no longer comes from the unit: the **unit** is now only the length of a step. In requests it is the optional field `circle_size`, refused with "The circle size must be a whole number from 25 to 50." and reported in every response; on the page a fourth slider, after Unit, with the readout "25 px around".

### Session 2026-10-13 (smooth edges)

- Q: The user said the circles look blotchy and asked for them to be smoother, even if drawing takes longer. -> A: The edges were hard (a disc drawn pixel by pixel with no blending, so stair-steps) and a circle could only sit on whole pixels. Each frame is now drawn at **4 times its size** and averaged down to 252 × 168, so an edge pixel is a mix of the circle and what is under it, and circles sit at fractional places. The colors inside a circle and the background are unchanged. 8 times was tried and is much slower (the largest settings take 31 s for a 60 s file against 9.5 s) for hardly any visible gain. The shape is kept to about a quarter of a pixel (the area of a circle is within 8% of the disc of its circumference).

### Session 2026-10-14 (a note that repeats stays)

- Q: The user asked: "I would like the note to stay in the same place if the octave and pitch are the same as the previous note at the same volume." -> A: A rank whose note is the **same note at the same volume** as the last note of that rank does **not move**: its new circle is put on the same place as the last one (it is still added to the memory, so the older circle under it is covered by the newer, opaque one). "The same note" is the same note index (so the same name and octave); "the same volume" is the same color index, the volume as the picture shows it, 0 to 255 on the tiles' square-root scale, so two values that round to one color count as the same and exact equality of the floating-point values is not needed. The last note of a rank is kept across frames in which the rank has no note, and the first circle of a rank has no note before it, so it moves. Before, a steady note walked a straight line of circles; now a note that is held at one volume stays on one place (the picture shows one circle there) and walks again when its volume or its note changes. Because the volume has 256 steps on the square-root scale, a note with natural variation (a real instrument, or smoothing that is off) changes color often and will still move most of the time; a heavier smoothing keeps the color steady and so makes more notes stay.

### Session 2026-10-14 (resize by volume)

- Q: The user asked: "Add a boolean parameter to allow for the resize of the circles based on volume. If checked, the circles' radii change by 1/2 for energy 0 to 2x for max energy." -> A: **Resize by volume** (the optional setting `circle_resize`, a boolean, **off** by default): when on, the radius of each circle is multiplied by a factor that goes in a straight line from **1 for the faintest note to 3 for the loudest note of the file** (it was first 1/2 to 2; the user changed it to 1 to 3 so that a circle is never smaller than the size setting) (factor = 1 + 2 c / 255, c being the circle's color index on the tiles' square-root scale, so the energy and the color follow the same scale; a note of no energy puts no circle down at all). A circle keeps the size it was given when it was put down, so a trail shows the volume of the music as a trail of sizes; places, colors and opacities do not change, and the *size* setting is the smallest radius a circle gets (and the scale is the square root of the share, which lifts quiet notes: a note with a quarter of the file's loudest value has a color index of 128 and a factor of about 2, one with 1% of it about 1.2). In the API it is the optional field `circle_resize` (`true`, `false`, `1` or `0`, any case; anything else is refused with "The circle resize must be true or false."), reported in every response as a boolean; on the page a checkbox "Resize by volume" after Size, with the readout "Off" or "On" and an info button. The range is taken as a straight line (not a doubling per step); it was first 1/2 to 2 and was changed to 1 to 3 on 2026-10-14, and the energy as the same strength that gives the color.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A picture of circles that wander as the music plays (Priority: P1)

The existing image types show the notes in fixed places: tiles in a grid, or a contour map over it. The user wants a fourth kind, **circles**, in which the notes are **circles that move**. In every frame the few strongest notes each put down a circle; where a circle goes depends on the note's name and octave, relative to where the previous frame's circle for the same rank was put, so that the picture is traced by the music itself: a melody walks a path, a repeated note stays near where it was. The circles of earlier frames stay in the picture (the picture **remembers** the last circles that were drawn) so that the animation builds up a trail of colored circles. (Amended: the circles are drawn on a background of the colormap's middle color and fade with their age, see the Clarifications.)

For one frame the picture is made like this:

1. **The notes**: the n notes with the most energy in this frame (n from 5 to 12), where a note's energy is its **smoothed** value in the frame. They are sorted from the strongest to the weakest, so each has a **rank**: 1 for the strongest, 2 for the next, and so on.
2. **The color**: each circle has the color of the selected colormap at the strength of its note (the same color scale as the tiles), so a stronger note has a color further along the colormap.
3. **The place**: the circle for rank r is put next to **the circle that rank r had in the previous frame** ("the last note at that index"). It is moved from there by an **angle** and a **distance** that come from the note itself. The angle comes from the note name: C is 0, C# 1, D 2, and so on up to B 11, and every slot is **30 degrees**, so C is 0 degrees, F is 150 degrees, B is 330 degrees. The distance comes from the octave (octave 4 is one unit, and every octave above or below 4 adds one more unit) and is counted in **units**, a unit being a few pixels (the user chooses it, from 1 to 10 pixels). In the very first frame there is no previous circle, so every rank starts from the middle of the picture.
4. **The memory**: the circle (its place, its size and its color) is added to a **memory** that holds the most recent circles, 100 to 500 of them (the user chooses). When it is full, the oldest circle is dropped. The picture of a frame shows all the circles in the memory, the oldest first and the newest on top.

The example from the request, with the distances as the user corrected them: if the strongest note of a frame is an F in octave 5, its circle is put **150 degrees** from the previous frame's strongest circle, **two units** away (one for octave 4 and one more for the octave above it). If it were an F in octave 3, the circle goes **210 degrees** from the previous strongest circle, also two units away (octaves below 4 turn the direction around, see the Assumptions). An A in octave 4 goes 270 degrees, one unit.

(Amended 2026-10-14: a rank whose note is the same note at the same color as the last note of that rank does not move, see the Clarifications.)

**Why this priority**: This is the whole feature: the new picture and the way it is built. The page controls (Story 2) and the combination with the other settings (Story 3) build on it.

**Independent Test**: Make frames from a file with one steady loud note. Choose the image type circles. The circles of that note go step by step in the direction of its name by the distance of its octave, one new circle each frame, and the earlier circles stay in the picture as a trail; the circles are the color of the note's strength.

**Acceptance Scenarios**:

1. **Given** the image type circles, **When** a frame is drawn, **Then** it is a picture of 252 × 168 pixels showing circles on a background of the colormap's middle color, made from the memory of the most recent circles.
2. **Given** a frame, **When** its notes are chosen, **Then** they are the n notes (5 to 12) with the largest smoothed value in that frame, sorted from the largest to the smallest, ties going to the lower note.
3. **Given** a frame and the previous frame's circle of the same rank, **When** the new circle is placed, **Then** it is at the angle of its note name (30 degrees for each of C, C#, D, … B) and the distance of its octave from the previous circle of that rank; for the first frame the previous place of every rank is the middle of the picture.
4. **Given** the strongest note is F5 and the previous strongest circle was at a place P, **When** the frame is drawn, **Then** the new circle is two units away from P in the direction of 150 degrees.
5. **Given** the strongest note is F3, **When** the frame is drawn, **Then** the new circle is two units away from the previous strongest circle in the direction of 210 degrees.
6. **Given** a circle, **When** it is drawn, **Then** its color is the colormap's color for its note's strength on the same scale as the tiles (square root of the share of the file's loudest value), so the same strength has the same color in every frame.
7. **Given** a memory size m, **When** more than m circles have been put down, **Then** the picture shows exactly the last m circles and the older ones are gone, and the newest circles are drawn over the older ones.
7a. **Given** the circles of a frame, **When** they are drawn, **Then** each has the opacity (m - age) / m, age being 0 for the newest circle: the newest is opaque and the oldest of a full memory is barely visible (1 to 3 parts in 255).
7b. **Given** any colormap, **When** a frame is drawn, **Then** the background is that colormap's color at the middle of its scale (row 128 of the 256-entry table), also for a silent input.
7c. **Given** the size s (25 to 50), **When** a circle is drawn, **Then** it is a disc whose circumference is s pixels (radius s / (2 pi)), whatever the unit.
8. **Given** the same file and settings, **When** frames are created twice, **Then** the two sets of frames are identical.
9. **Given** the number of frames and the timing of the file, **When** frames are created as circles, **Then** they are the same as for the other image types.

---

### User Story 2 - Choose circles and its settings on the page and through the server (Priority: P2)

The Image type control offers a fourth choice, **Circles**, with a short explanation in its info text. When Circles is chosen, four settings that belong only to it appear, each with an info button: **Unit** (the length of a unit in pixels, a slider from 1 to 10), **Size** (the circumference of a circle in pixels, a slider from 25 to 50), **Memory** (how many circles are remembered, a slider from 100 to 500) and **Circles per frame** (how many of the strongest notes put down a circle, a slider from 5 to 12). The settings that do not make sense for circles are disabled while Circles is chosen: **Interpolate** (the circles of a frame depend on the frames before it, so frames cannot be skipped), and the ones that describe a grid of notes: **Resolution**, **Notes** (the 12 to 84 choice of the other types), **Threshold** and **Blend width**. The result summary shows the image type "Circles" and the three settings. In requests the type is `circles` and the settings are the optional fields `circle_unit`, `circle_size`, `circle_memory` and `circle_notes`; a value that is not allowed is refused with a clear message, and the response reports the values used.

**Why this priority**: The new picture (Story 1) can be asked for through the server, but users need to pick it on the page and set it.

**Independent Test**: Open the page, choose Circles, see the four settings appear and the five grid settings become disabled, set Unit 6, Size 30, Memory 300 and Circles per frame 8, create frames, see the circles play and "Image type: Circles" with the three values in the summary. Choose Tiles again: the three settings disappear and the others are enabled.

**Acceptance Scenarios**:

1. **Given** the page is opened, **When** the settings are shown, **Then** the Image type control offers Tiles, Blended tiles, Contour and Circles, and Tiles is selected; the three circle settings are not shown.
2. **Given** Circles is chosen, **When** the user looks at the settings, **Then** Unit (1 to 10 pixels), Size (25 to 50 pixels around), Memory (100 to 500 circles) and Circles per frame (5 to 12) are shown with their readouts and info buttons, and Interpolate, Resolution, Notes, Threshold and Blend width are disabled.
3. **Given** Circles is not chosen, **When** the user looks at the settings, **Then** the three circle settings are hidden and the others behave as before (Blend width enabled only for Blended tiles).
4. **Given** the user activates the Image type info button, **When** the popover opens, **Then** it also describes what Circles looks like.
5. **Given** frames have been created as Circles, **When** the result is shown, **Then** the summary includes the image type and the four values (and no values for the settings that do not apply).
6. **Given** a request with `image_type=circles`, **When** the server receives it, **Then** it creates circle frames and the response reports `image_type` as `circles` and `circle_unit`, `circle_size`, `circle_memory` and `circle_notes`; a request without the four fields uses their defaults.
7. **Given** a request with `circle_unit` not a whole number from 1 to 10, `circle_size` not a whole number from 25 to 50, `circle_memory` not a whole number from 100 to 500, or `circle_notes` not a whole number from 5 to 12 (empty, not a number, fractional, out of range), **When** the server receives it, **Then** it is refused before a job is created with a message that says what is allowed.
8. **Given** a request with `image_type=circles` that also sends `interpolate`, `resolution`, `note_count`, `threshold` or `blend_width`, **When** the server receives it, **Then** it is accepted and those values have no effect on the circles (the response still reports them as sent or by default).
9. **Given** a request with an image type that is not one of the four names, **When** the server receives it, **Then** it is refused with a message that lists the four names.

---

### User Story 3 - It works with smoothing and the colormap, with quiet music, and in a practical time (Priority: P3)

The circles are made from the same smoothed note values as the other types, so **Smoothing and its window** and the **Colormap** apply: smoothing makes the colors and the choice of the strongest notes steadier from frame to frame. A frame in which a note has no energy at all puts no circle down for it. A job of circles with the largest settings still finishes in a practical time, and the existing image types are not changed at all.

**Why this priority**: These are the interactions with the existing settings and the practical limits. They define the result when features are combined but are secondary to the picture itself.

**Independent Test**: Create circle frames with smoothing 0.5 and window 3 and each colormap for a 10 second file at 30 frames per second with Circles per frame 12 and Memory 500: the job finishes within a minute, the circle colors follow the colormap, and a silent stretch of the file adds no circles while the earlier ones stay.

**Acceptance Scenarios**:

1. **Given** smoothing above 0, **When** circle frames are drawn, **Then** the strength that gives a circle its color and its rank is the smoothed value of its note.
2. **Given** any colormap that the page offers, **When** circles are drawn, **Then** they use that colormap, and changing the colormap changes only the colors, not the places.
3. **Given** a frame in which fewer than n notes have any energy, **When** it is drawn, **Then** only the notes with energy put circles down (a silent frame puts none), and the circles already in the memory stay in the picture.
4. **Given** a silent file, **When** frames are drawn, **Then** every frame is the plain background (the colormap's middle color) and nothing fails.
5. **Given** the image types tiles, blended and contour, **When** frames are created, **Then** they are identical, file for file, to those made before this feature.
6. **Given** a file of 10 seconds at 30 frames per second (300 frames), **When** frames are created as circles with 12 circles per frame and a memory of 500, **Then** the job finishes within one minute on the development machine.

---

### Edge Cases

- **Circles leaving the picture**: because each circle moves from the previous one, a rank can walk out of the picture. The picture is treated as wrapping around: a place beyond one edge comes back in at the opposite edge, so the circles always stay visible (see the Assumptions).
- **Ranks and the previous frame**: the circle of rank 3 moves from the previous frame's circle of rank 3, even if that was a different note. If the previous frame had fewer circles than this frame, the extra ranks start from the middle of the picture; if a rank had no circle in the previous frame because the music was silent, it moves from where that rank last was.
- **The loudest note not being the same each frame**: the ranks follow the energy order in each frame, so a change of the strongest note changes which "trail" the new strongest circle continues.
- **Octaves far from 4**: the notes go from octave 1 to octave 8, so the distance is from one unit (octave 4) to five units (octave 8; octave 1 is four units).
- **Many circles on the same place**: circles overlap; the newest is drawn on top.
- **Small and large units**: at 1 pixel a unit is almost nothing and the circles overlap into a blob; at 10 pixels a circle can move up to 50 pixels in one frame.
- **The settings that do not apply** (Interpolate, Resolution, Notes, Threshold, Blend width) are accepted and ignored for circles; the existing image types ignore the circle settings in the same way.
- **Results from before this feature** (frames already created) are not changed. Only new submissions can use the type.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to choose the image type **circles** in addition to tiles, blended and contour. **Tiles** MUST remain the default, on the page and when a request does not say. The server MUST refuse an image type that is not one of the four names with a clear message that lists them.
- **FR-002**: With the image types tiles, blended and contour, frames MUST be identical, file for file, to those made before this feature.
- **FR-003**: For every frame, the **notes** of the circles MUST be the n notes (n from 5 to 12, the setting "circles per frame") with the largest smoothed value in that frame among the 84 drawn notes, sorted from the largest to the smallest (ties to the lower note); a note whose smoothed value is 0 MUST NOT put a circle down.
- **FR-004**: The **color** of a circle MUST be the color of the selected colormap at the same position that a tile of the same strength has (the share of the file's largest smoothed value over all 88 notes, on the square-root scale), so that the same strength has the same color in every frame.
- **FR-005**: The circle of rank r MUST be placed relative to the **circle that rank r had in the previous frame**: from that place it moves by an **angle** and a **distance** that come from the note. The angle is the note's name counted from C (C = 0, C# = 1, … B = 11) times **30 degrees**. The distance is **1 + |octave - 4| units**, where a unit is the setting "unit" in pixels (octave 4 moves 1 unit, octaves 3 and 5 move 2, octaves 2 and 6 move 3, and so on). Notes below octave 4 move in the direction turned around (F3: 210 degrees instead of 150).
- **FR-005a** (amended 2026-10-14): A rank whose note has the same note index and the same color index as the last note of that rank MUST NOT move: its circle is put on the previous place of the rank (and is added to the memory as usual).
- **FR-008a** (amended 2026-10-14): With the optional boolean setting `circle_resize` on (default off), the radius of a circle MUST be the radius of the size setting times 1 + 2 c / 255, c being the circle's color index (0 to 255); off, every circle has the radius of the size setting.
- **FR-006**: In the first frame, and for a rank that has never had a circle, the previous place MUST be the middle of the picture. A place beyond an edge of the 252 × 168 picture MUST wrap around to the opposite edge.
- **FR-007**: The picture MUST remember the most recent circles (their places, sizes and colors) in a **circular memory** of m circles (m from 100 to 500, the setting "memory"): when it is full, the oldest circle is replaced. Every frame MUST show all the circles in the memory, the oldest first and the newest on top, on a background of the colormap's middle color, each circle with an opacity that falls with its age: (m - age) / m, so the oldest is barely visible just before it is dropped.
- **FR-008**: The size of a circle MUST be the same for all circles (the setting "size", see FR-010) and the picture MUST be 252 × 168 pixels, with the same frame count, file names and timing as the other image types.
- **FR-009**: Smoothing and its window MUST be applied before the notes are chosen, as for the other types. The Colormap MUST apply. The settings Interpolate, Resolution, Notes (12 to 84), Threshold and Blend width MUST have no effect on circles; the page MUST disable those controls while Circles is chosen.
- **FR-010**: The setting **unit** MUST be a whole number of pixels from 1 to 10 (the length of a step only), **size** a whole number of pixels from 25 to 50 (the circumference of a circle, default 25), **memory** a whole number from 100 to 500 and **circles per frame** a whole number from 5 to 12. On the page they MUST be shown only while Circles is chosen, each with a readout and an info button; in requests they are the optional fields `circle_unit`, `circle_size`, `circle_memory` and `circle_notes`, with defaults when not sent, and a value that is not allowed MUST be refused before a job is created, with a clear message, and MUST be reported in the response.
- **FR-011**: The page MUST offer Circles in the Image type control and describe it in the control's explanation, and the result summary MUST show the image type used and, for circles, the four settings.
- **FR-012**: The same file and settings MUST always give identical frames.
- **FR-013**: A job of circles MUST finish in a practical time (SC-006).
- **FR-014**: The documentation's description of the image types and settings MUST be updated to describe circles.

### Key Entities *(include if feature involves data)*

- **Circle**: One note's mark in the picture: a place (in pixels), a size and a color, made in one frame from one of its strongest notes.
- **Rank**: The position of a note among a frame's selected notes, sorted from the strongest (1) to the weakest. The circle of a rank is placed relative to the previous frame's circle of the same rank.
- **Unit**: The length in pixels (1 to 10) by which the distance of an octave is counted.
- **Size**: The circumference of a circle in pixels (25 to 50); its radius is size / (2 pi).
- **Age**: How many circles ago a circle was put down (0 for the newest); it sets the circle's opacity.
- **Memory**: The circular buffer of the most recent circles (100 to 500); the picture shows them all.
- **Circles per frame**: How many of the strongest notes of a frame put a circle down (5 to 12).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the image types tiles, blended and contour, 100% of the frames of a test file are identical, file for file, to those made before this feature.
- **SC-002**: For a test file in which one note is the strongest in every frame, the center of each frame's new circle is exactly the previous frame's center moved by the angle of the note's name and the distance of its octave (F5: 150 degrees and two units, F3: 210 degrees and two units, A4: 270 degrees and one unit, included), to within one pixel, for every note name.
- **SC-003**: The number of circles drawn in a frame is the number of notes with energy among the n strongest of the frames so far, up to the memory size m: after more than m / n frames the picture shows exactly m circles, and a circle that was put down m circles ago is gone.
- **SC-004**: The color of every circle equals the colormap's color for its note's strength on the tiles' scale, for every colormap offered, in every frame.
- **SC-005**: 100% of invalid values (unit not a whole number from 1 to 10, size not from 25 to 50, memory not from 100 to 500, circles per frame not from 5 to 12, or an unknown image type) are refused before a job is created, with a message that says what is allowed.
- **SC-006**: A job of 300 frames (10 seconds at 30 frames per second) as circles with 12 circles per frame and a memory of 500 finishes within one minute on the development machine.
- **SC-007**: A user can choose Circles on the page, see its four settings appear and the five unrelated settings become disabled, read the explanations, and see the circles in the player without leaving the settings column.
- **SC-008**: Two runs of the same file and settings give identical frames.

## Assumptions

- **Note names and octaves are the notes' real names.** The request counts the columns from C (0 to 11 for C to B) and the octave as in scientific pitch notation (F5 is the F above middle C's octave start, A4 is 440 Hz). The application's grid starts at A (its first column is A, 55 Hz), so for circles the angle and the distance are taken from the note's real name and octave, not from its grid cell: for example, the grid cell of F5 is column 8 of row 3, but its circle moves 150 degrees (F is 5 from C). The 84 drawn notes run from A1 to G#8, octaves 1 to 8.
- **An angle of 0 degrees points right, and angles grow counter-clockwise** as seen in the picture (90 degrees is up). The request gives only the numbers of the angles. This turns the whole picture mirror-wise if the other convention is wanted.
- **The direction is turned around below octave 4 as in the request's example**: an F3 moves 210 degrees (the angle is mirrored: 360 − 150), not 330 degrees (the exact opposite of 150) and not 150. The angle is a fixed direction from the previous circle, not a turn from the previous heading.
- **A circle's size is its own setting** (amended): the first version made a circle one unit in radius; the user found the circles small and asked for the circumference to be settable up to about 50 pixels. The **size** is that circumference in pixels, 25 to 50, default 25 (radius 4.0 to 8.0, the default the same as the first version at the default unit), and no longer depends on the unit. "A counter for the circle circumference" was read as a slider like the other settings.
- **The background is the middle color of the colormap** (amended; the first version was black): the color at row 128 of the colormap's 256-entry table, the entry at 0.5 of the way along its scale (0.5 times 255 rounds to 128), so it changes with the colormap.
- **The opacity of a circle is linear in its age** (amended): (m - age) / m of full opacity, the newest age 0. "Barely visible before it moves off the buffer" is taken as 1 / m for the oldest circle a full memory holds (1 to 3 parts in 255). Overlapping translucent circles blend their colors, newest on top.
- **The picture wraps around** at its edges, so that a rank that keeps moving in one direction comes back into the picture instead of leaving it. Only the circle's place wraps: a circle near an edge is cut off by the edge and is not drawn a second time on the opposite side.
- **Within a frame the weakest circle goes into the memory first**, so the strongest circle of a frame is drawn on top of the others and is the last of them to be dropped when the memory is full. The alternatives (stop at the edge, bounce back) are possible later without changing the rest.
- **Defaults of the four settings**: unit 4 pixels, size 25 pixels, memory 300 circles, 8 circles per frame (the middles of their ranges, rounded, except the size, whose default is the first version's circle). The request gives only the ranges.
- **The chosen notes are per frame, not per file.** Unlike the Notes setting of the other types (which chooses the strongest notes of the whole file), circles take the strongest notes of each frame, because the request relates a frame's strongest note to the previous frame's strongest note.
- **Frames depend on the earlier frames** (the memory and the places), so they are made one after the other and no frame can be skipped; that is why Interpolate does not apply.
- **Resolution, Notes, Threshold and Blend width describe a grid of tiles** and have no meaning for circles, so they are ignored and disabled; the Threshold's job (hiding quiet notes) is done by the rule that a note with no energy puts no circle down.
- **The setting is chosen when frames are created**, like every other setting; changing it means submitting again.
- This feature is about how frames are drawn. Audio playback, the note analysis, smoothing, the other image types, the frame player and the page layout (apart from adding one choice, four conditional controls and the disabling of five) are unchanged.
