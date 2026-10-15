# Feature Specification: Circles Paint

**Feature Branch**: `022-circles-paint` (no git branch created; spec directory name only)

**Created**: 2026-10-14

**Status**: Draft

**Input**: User description: "create a version of the circles image type, called circles paint.  There is no memory, instead it just draws the circles on a copy of the previous image."

## Clarifications

### Session 2026-10-14

- Q: Should the paint ever fade or clear? -> A: **Option A: the paint stays until something covers it.** There is no fading and no clearing: a painted pixel keeps its color in every later frame until a later circle is painted over it. There is no setting for it.
- Q: Are the circles painted solid or partly see-through? -> A: **Option A: solid.** Every circle is painted in its own color at full opacity, covering what is under it (with the same smooth edge as the circles of Circles, so the pixels on its edge are a mix of its color and what was there); the newest circle is always fully visible, and in a frame the strongest note's circle is on top. There is no opacity setting and no fading by age.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A picture that is painted by the music, frame after frame (Priority: P1)

The **Circles** image type remembers the last few hundred circles and, in every frame, draws all of them again, the older ones fading with their age. The user wants a second version of it, **Circles paint**, that works like a painter: there is **no memory** of circles at all. Every frame starts from **a copy of the previous frame's picture** and the circles of this frame are **painted on top of it**. The picture is therefore a canvas that is built up by the music: what has been painted stays where it is until a later circle covers it.

Everything that decides *which* circles are painted and *where* is the same as in Circles: in every frame the strongest notes of that frame (5 to 12 of them) each put down one circle; the circle of rank r goes next to the place that rank r had in the previous frame, moved by an angle from the note's name and a distance from its octave (Movement); a note repeated at the same volume stays where it is; places wrap around the edges; the circle's color is the colormap's color for the note's strength; the radius is the setting Radius (with the optional Resize by volume); and the background is the middle color of the colormap. What is different is only how the picture is made: the first frame is the plain background with its circles painted on it, and every later frame is the previous picture with this frame's circles painted on top.

The paint never fades or clears and the circles are solid (see the Clarifications).

**Why this priority**: This is the request: a new image type with a canvas instead of a memory. The page controls (Story 2) and the combination with the other settings (Story 3) build on it.

**Independent Test**: Make frames from a file with one steady loud note that changes volume now and then. Choose the image type Circles paint. Frame 1 shows the background with one circle; every later frame shows the previous frame's picture with one more circle painted on top, so the trail of circles grows frame by frame and nothing that was painted disappears until it is covered.

**Acceptance Scenarios**:

1. **Given** the image type Circles paint, **When** frames are created, **Then** every frame is a 600 × 400 picture, there is one frame for each frame time of the file as for the other types, and the first frame is the background with the circles of the first frame painted on it.
2. **Given** a frame other than the first, **When** it is drawn, **Then** it is exactly the previous frame's picture with this frame's circles painted on top (every pixel that this frame's circles do not touch is the same as in the previous frame).
3. **Given** the same file and settings, **When** the notes, ranks, places, colors and radii of the circles are worked out, **Then** they are the same as in Circles for the same settings (the same circle is put down in the same place with the same color and radius in the same frame).
4. **Given** the circles of one frame that overlap each other, **When** they are painted, **Then** the strongest note's circle is on top of the weaker ones, as in Circles.
5. **Given** a circle that is painted over an earlier one, **When** the frame is shown, **Then** the earlier one is covered where they overlap and visible where they do not; nothing is removed or faded by the passing of frames.
5a. **Given** a circle that is painted, **When** it is drawn, **Then** it is solid: the pixels well inside it have exactly the circle's color, whatever was under them, and only the pixels on its edge are a mix of its color and the canvas.
6. **Given** a silent stretch of the file, **When** frames are drawn, **Then** nothing is painted and each such frame is a copy of the one before.
7. **Given** the same file and settings, **When** frames are created twice, **Then** the two sets of frames are identical.
8. **Given** the image type Circles (not paint), **When** frames are created, **Then** they are exactly as before this feature.

---

### User Story 2 - Choose Circles paint on the page and through the server (Priority: P2)

The Image type control offers a fifth choice, **Circles paint**, with an explanation of what it looks like. While it is chosen, the page shows a group **Circles paint** after the Image type group, with the circle settings that still mean something: **Movement**, **Radius**, **Resize by volume** and **Notes** (the number of strongest notes of each frame that put down a circle), two to a row as the other groups. **Memory is not shown**, because there is no memory. Data smoothing (Smoothing window, Smoothing) and Colormap apply as for Circles; the controls for grids of tiles and for skipped frames (Threshold, the 12 to 84 Notes, Blend width, Oversampling, Interpolate) are not shown, as for Circles, because the circles of a frame depend on the frames before it. The result summary names the image type and shows the circle settings that were used, without Memory. In requests the type is a new name for the image type and the circle settings are the same optional fields as for Circles; the memory field is not used by this type (a request that sends it is accepted and the value has no effect).

**Why this priority**: The new picture (Story 1) can be asked for through the server, but users need to pick it on the page and set it.

**Independent Test**: Open the page, choose Circles paint: the group Circles paint appears with Movement, Radius, Resize by volume and Notes (no Memory) and the grid controls are not shown; create frames and see the canvas build up and "Image type: Circles paint" in the summary. Choose Circles: the group is Circles with Memory again.

**Acceptance Scenarios**:

1. **Given** the page is opened, **When** the settings are shown, **Then** the Image type control offers Tiles, Blended tiles, Contour, Circles and Circles paint, and Tiles is selected.
2. **Given** Circles paint is chosen, **When** the user looks at the settings, **Then** the group after Image type is titled Circles paint and has Movement, Radius, Resize by volume and Notes, with their readouts and info buttons, and no Memory control; Data smoothing is shown and Image smoothing is not.
3. **Given** the user changes the image type between Circles and Circles paint, **When** the settings are shown again, **Then** the values of the settings that both use (Movement, Radius, Resize by volume, Notes) are kept, and Memory has its value again for Circles.
4. **Given** frames created as Circles paint, **When** the result is shown, **Then** the summary names the image type and shows Movement, Radius, Resize by volume and Notes, and no Memory line.
5. **Given** a request for the new image type, **When** the server receives it, **Then** it creates frames of that type, and the response reports the image type and the circle settings used; a value of a circle setting that is not allowed is refused with the same message as for Circles.
6. **Given** a request for an image type that is not one of the five names, **When** the server receives it, **Then** it is refused with a message that lists the five names.
7. **Given** the image type Circles paint, **When** the user opens the info text of the Image type control, **Then** it describes Circles paint as well.

---

### User Story 3 - It keeps the look of Circles and stays practical (Priority: P3)

Circles paint is drawn at the same size and with the same quality as Circles: 600 × 400 pixels, smooth circle edges, the Movement and Radius measured against the old 252-pixel reference frame and scaled to the 600-pixel frame, the same colors for the same strengths. Smoothing and the colormap apply. Because only the circles of the current frame are drawn (not hundreds), a job is **not slower** than the same job as Circles, and the room the frames take is of the same order.

**Why this priority**: These keep the new type consistent with the old one and inside the limits; they are secondary to the picture itself.

**Independent Test**: Create frames from a 60 second file at 30 frames per second as Circles and as Circles paint with the same settings: both finish within the limits, Circles paint no slower than Circles, and the circles of Circles paint are the same as the newest circles of Circles in color, place and size.

**Acceptance Scenarios**:

1. **Given** any colormap, **When** circles are painted, **Then** their colors are the colormap's colors for the notes' strengths on the same scale as Circles and the tiles.
2. **Given** smoothing above 0, **When** frames are drawn, **Then** the strength that gives a circle its color and its rank is the smoothed value of its note.
3. **Given** a 60 second file at 30 frames per second (1,800 frames), **When** frames are created as Circles paint at the default settings and at the largest settings, **Then** the job finishes within one minute and no later than the same job as Circles.
4. **Given** the other image types, **When** frames are created, **Then** they are identical, file for file, to those made before this feature.

---

### Edge Cases

- **A canvas that fills up**: with no fading and no memory, a long file paints over the same places many times; the picture becomes a layering of the latest circles over the older ones, and its look depends on how far the circles move (small Movement and a long file give a dense mass, large Movement spreads the paint). This is how a painted canvas behaves and is not an error.
- **Circles at the edges**: a circle that is moved past an edge comes back in at the opposite edge as in Circles; a circle near an edge is cut off by it and is not painted a second time on the opposite side.
- **Fewer sounding notes than asked for**: only the notes with energy paint a circle, as in Circles.
- **A note that repeats at the same volume** stays in the same place, so the circle is painted again on the same place: its solid inside does not change; only its one-pixel smooth edge changes, and only toward the circle's color (an edge that is mixed again becomes a little harder with every repaint, never softer).
- **Very short and silent files**: one frame, or frames of the plain background, nothing fails.
- **Frames made before this feature** are not changed; only new submissions can use the type.
- **The settings that do not apply** (Threshold, Notes of 12 to 84, Blend width, Oversampling, Interpolate, Memory) are accepted and ignored by the server for this type, and are not shown on the page.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to choose a fifth image type, **Circles paint**, in addition to tiles, blended, contour and circles; Tiles MUST remain the default; the server MUST refuse an image type that is not one of the five names, with a message that lists them.
- **FR-002**: With the image types tiles, blended, contour and circles, frames MUST be identical, file for file, to those made before this feature.
- **FR-003**: In Circles paint, which circles are put down in a frame (the strongest notes of the frame, their ranks), where (relative to the rank's previous place, by the angle of the note's name and the distance of its octave, with the stay-in-place rule and the wrap-around), in which color and with which radius (Radius, Movement, Resize by volume, and the scaling to the 600 × 400 frame) MUST be exactly as in Circles for the same settings and music.
- **FR-004**: Circles paint MUST have **no memory of circles**: no buffer, no limit on how many circles have been painted, and no circle that is dropped or faded because of its age.
- **FR-005**: The first frame of Circles paint MUST be the plain background (the colormap's middle color) with the first frame's circles painted on it, and every later frame MUST be a copy of the previous frame's picture with this frame's circles painted on top of it; a pixel that this frame's circles do not touch MUST be the same as in the previous frame.
- **FR-006**: Within a frame the circles MUST be painted weakest first, so that the strongest note's circle is on top.
- **FR-006a**: Every circle MUST be painted **solid** (its own color at full opacity, with a smooth edge), and the paint MUST **never fade or be cleared**: a painted pixel keeps its color until a later circle covers it.
- **FR-007**: The painted circles MUST have smooth edges and the same size, color scale and background as the circles of Circles; frames MUST be 600 × 400 pixels, with the same count, file names and timing as the other image types.
- **FR-008**: The settings that apply to Circles paint are Movement, Radius, Resize by volume and Notes (5 to 12), with the same ranges, defaults, messages and request fields as for Circles, plus Smoothing, Smoothing window and the Colormap; the Memory setting MUST NOT apply and MUST NOT be shown. Interpolate, Oversampling, Threshold, the 12 to 84 Notes and Blend width MUST have no effect and MUST NOT be shown.
- **FR-009**: The same file and settings MUST always give identical frames.
- **FR-010**: A job of Circles paint MUST finish within one minute for a 60 second file at 30 frames per second at the default and at the largest settings, and MUST NOT take longer than the same job as Circles.
- **FR-011**: The page MUST offer Circles paint in the Image type control and describe it in the control's explanation; while it is chosen it MUST show a group titled Circles paint with the controls of FR-008, laid out as the other groups; the result summary MUST show the image type used and, for it, the circle settings without Memory.
- **FR-012**: The documentation's description of the image types and settings MUST be updated for Circles paint.

### Key Entities *(include if feature involves data)*

- **Canvas**: The picture of the frame that was just made, kept only as the starting point of the next frame; every frame is the canvas with the new circles painted on it.
- **Circle**: One note's mark: a place, a radius and a color, made in one frame from one of its strongest notes; once painted it is part of the canvas and is not tracked any more.
- **Rank**: As in Circles: the position of a note among the frame's strongest, whose circle goes next to the rank's previous place.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the image types tiles, blended, contour and circles, 100% of the frames of a test file are identical, file for file, to those made before this feature.
- **SC-002**: For a test file, in every frame after the first, every pixel outside the circles of that frame equals the same pixel of the previous frame (checked exactly), for every colormap.
- **SC-003**: For a test file, the center and the color of every circle painted in a frame equal those of the newest circles of Circles for the same settings (same frame, same rank), and the radius equals the radius of Circles' circle.
- **SC-004**: After a number of frames larger than the memory that Circles would have, Circles paint still shows the first frame's circles wherever nothing was painted over them (nothing is dropped), 100% of the time.
- **SC-004a**: For every circle painted in a frame, the pixels at its center (and well inside its radius) have exactly the circle's color for the colormap, whatever was painted there before, in 100% of the frames and for every colormap.
- **SC-005**: A silent stretch of a file gives frames that are exact copies of the frame before them.
- **SC-006**: A job of 1,800 frames at the default and at the largest settings finishes within one minute and no later than the same job as Circles.
- **SC-007**: A user can choose Circles paint on the page, see the group with Movement, Radius, Resize by volume and Notes (and no Memory), and see the canvas build up in the player, without leaving the settings column.
- **SC-008**: Two runs of the same file and settings give identical frames.

## Assumptions

- **The new type is a fifth image type named "Circles paint"**, in addition to Circles (which keeps its memory); it is not a setting of Circles.
- **The image type is separate from Circles so that both can be used.** The request says "a version of the circles image type".
- **Where, which and what color are exactly as in Circles**, including the stay-in-place rule, the wrap-around and the rank behavior, because the request changes only how the picture is made ("no memory ... draws the circles on a copy of the previous image").
- **The background is the colormap's middle color**, as in Circles, and the first frame is that background with the first circles painted on it.
- **Frames depend on the frames before them**, so they are made one after the other and no frame can be skipped; that is why Interpolate does not apply.
- **The settings of Circles that need a memory (Memory) are not used**; the others keep their ranges and defaults (Movement 1 to 10 default 4, Radius 4 to 8 default 4, Resize by volume off, Notes 5 to 12 default 8) so that a user can switch between the two types.
- **The size and quality of the frames are those of the other types** (600 × 400, smooth edges), and the circle settings are measured against the 252-pixel reference frame as for Circles.
- This feature is about one new image type. The audio analysis, smoothing, the other four image types, the player and the page layout (apart from one choice and one conditional group) are unchanged.
