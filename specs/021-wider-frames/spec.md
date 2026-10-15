# Feature Specification: Wider Frames (600 Pixels)

**Feature Branch**: `021-wider-frames` (no git branch created; spec directory name only)

**Created**: 2026-10-14

**Status**: Draft

**Input**: User description: "make the frame sizes 600px wide.  Right now they are too small and the images look blotchy."

## Clarifications

### Session 2026-10-14

- Q: How should the circles' Movement and Radius be measured now that the frame is 2.4 times wider? -> A: **Option A: the numbers stay and are measured against the old frame.** Movement (1 to 10) and Radius (4 to 8) keep their ranges, defaults, messages and request fields; they are measured in pixels of a **252-pixel-wide reference frame** and are scaled by 600 / 252 (about 2.38) when the picture is drawn, so the same settings give the same picture as before in proportion to the frame (a Radius of 4 is a circle about 9.5 pixels in radius on the 600-pixel frame), only sharper. The same scale applies to Resize by volume (a factor of 1 to 3 of the radius), to the place where the circles start (the middle of the picture) and to the wrap-around (the 600 × 400 edges).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every frame is 600 pixels wide and sharper (Priority: P1)

Today a frame is a small picture of **252 × 168 pixels**. The page shows it at up to about 660 pixels wide, so the browser blows each pixel up to more than two and a half screen pixels, and the picture looks **blotchy**: hard-edged blocks, stair-stepped contour lines and soft, stretched circles. The user wants the frames made at a larger size, **600 pixels wide**, so that what the page shows is a real picture of about that size and not a stretched small one.

The frames of **every image type** (Tiles, Blended tiles, Contour and Circles) become 600 pixels wide, and keep the same **3:2** shape as today, so **600 × 400 pixels**. The pictures are drawn at the new size, not enlarged afterwards: a contour line has the detail of a 600 pixel picture, a blended tile fades smoothly over 600 pixels, a circle has a smooth edge at its real size. The music, the notes, the colors, the smoothing, the frame count and the timing are exactly the same as before; only the size and the sharpness of the pictures change.

**Why this priority**: This is the request: bigger frames that do not look blotchy. Everything else (the player, the circles, the time it takes) follows from it.

**Independent Test**: Create frames from a short file for each image type. Every frame file is 600 × 400 pixels. Put the new frame of a contour or a blended picture next to the old one enlarged to the same size: the new one has finer detail and smoother edges, and its colors and shapes are the same.

**Acceptance Scenarios**:

1. **Given** any image type, resolution, interpolation, smoothing and colormap, **When** frames are created, **Then** every frame is 600 pixels wide and 400 pixels high.
2. **Given** the same file and settings as before this feature, **When** frames are created, **Then** the number of frames, their file names and their timing are the same as before, and each frame shows the same notes in the same places and colors, only at the larger size.
3. **Given** the image type Tiles, **When** a frame is drawn, **Then** it still shows the 12 columns by 7 rows of tiles (or the finer grid of the chosen oversampling) of flat colors, now spread over the 600 × 400 picture with every column of the same width and every row of the same height to within one pixel.
4. **Given** the image type Contour, **When** a frame is drawn, **Then** its contour regions and lines are drawn at the 600 × 400 size (the edges are not the stair-steps of an enlarged small picture).
5. **Given** the image type Blended tiles, **When** a frame is drawn, **Then** the soft edge between tiles is as wide, in proportion to a tile, as before, and is smooth at the new size.
6. **Given** the interpolate setting above 1, **When** frames are created, **Then** the in-between frames are made from the drawn frames at the new size and are also 600 × 400.
7. **Given** a frame made before this feature, **When** the page is used after the change, **Then** only newly created frames have the new size; nothing that exists is changed.

---

### User Story 2 - Circles keep their look at the larger size (Priority: P2)

The Circles image type works in pixels: a circle moves by a number of pixels (Movement, 1 to 10), has a radius in pixels (Radius, 4 to 8), and its place wraps around the edges of the picture. If these numbers were simply read as pixels of the new, larger frame, every circle would be less than half as big and move less than half as far *compared with the picture*, and the same settings would give a different picture from before.

The settings keep their numbers and are measured against the old 252-pixel frame, then scaled to the 600-pixel frame (see the Clarifications), so the same settings give the same picture as before, only sharper.

**Why this priority**: Circles are one of the four image types and the request says "the frame sizes", so they must work at 600 pixels; but the picture they make does not depend on the other stories.

**Independent Test**: Create circle frames with the same file and the same settings before and after, and compare them at the same displayed size: the circles are in the same places, with the same colors and fading, and the same relative size, and sharper.

**Acceptance Scenarios**:

1. **Given** the circles image type and the settings that were used before, **When** frames are created, **Then** the circles are in the same places and have the same colors, fading and sizes as before in proportion to the frame (a Radius of 4 is about 9.5 pixels in radius on the 600-pixel frame, a Movement of 4 moves a circle about 9.5 pixels per unit), and the picture is 600 × 400.
2. **Given** a circle near an edge, **When** it moves past it, **Then** it still wraps around to the opposite edge of the 600 × 400 picture.
3. **Given** the circles settings at their smallest and largest values, **When** frames are created, **Then** every circle stays inside the picture's bounds in the way it did before and the picture is clear (not blank, not covered by one color).

---

### User Story 3 - The page shows the frames at their real size, and the job stays practical (Priority: P3)

The frame player on the page shows a frame at **up to its full 600 pixels** when there is room, without stretching it, and scales it down to fit a narrower screen, always keeping the 3:2 shape and never cropping. The player's behaviour (play, pause, step, speed) is as before. Making a frame 2.4 times wider means about 2.4 times as many pixels to draw and to store, so the time to create frames and the room they take must stay practical: a 60 second file at 30 frames per second must still finish in a reasonable time for every image type at the default settings and at the settings that cost the most.

**Why this priority**: The larger frames must be shown properly and must not make the application unusable, but this is secondary to the frames themselves.

**Independent Test**: Open the page with new frames: the frame appears at about 600 pixels wide on a wide window, scales down on a narrow one, keeps 3:2, and playback works. Create frames from a 60 second file at 30 frames per second for each image type at the default and at the costliest settings and note the times.

**Acceptance Scenarios**:

1. **Given** frames of 600 × 400 and a window wide enough, **When** the player shows a frame, **Then** it is shown at 600 pixels wide, with no enlargement, and the image is not cropped or distorted.
2. **Given** a window narrower than 600 pixels, **When** the player shows a frame, **Then** it is scaled down to fit, keeping 3:2, and the controls are still usable.
3. **Given** a 60 second file at 30 frames per second (1,800 frames), **When** frames are created for each image type at the default settings, **Then** the job finishes within one minute on the development machine.
4. **Given** the same file at the settings that cost the most for each image type (the largest oversampling for tiles, blended tiles and contour; the largest movement, radius, memory and notes for circles), **When** frames are created, **Then** the job finishes within two minutes.
5. **Given** a created job, **When** the room its frames take is measured, **Then** it is no more than 4 times what the same job took before this feature.

---

### Edge Cases

- **Rows that do not divide evenly**: 400 pixels do not divide into 7 whole rows of equal height (57.14). The rows (and the finer rows at higher oversampling) are spread so that no two differ by more than one pixel; the same holds for columns, which divide evenly at the default grid (600 / 12 = 50 pixels).
- **Highest oversampling and interpolation**: the finest grid (60 columns by 35 rows) has tiles of 10 × 11 pixels at the new size; every grid size and every interpolate value gives frames of exactly 600 × 400.
- **Very short and silent files**: a file with one frame or no sound gives 600 × 400 frames as before in shape (one frame, or frames of the plain background).
- **Frames already created** (earlier jobs still on the page) are not changed; only new submissions use the new size.
- **The file chooser, the settings form, the audio player and the other parts of the page** are unchanged.
- **Disk room**: more pixels per frame means larger files; very long files take proportionally more room, as before.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every frame of every image type MUST be **600 pixels wide and 400 pixels high** (3:2), whatever the oversampling, interpolation, smoothing, threshold, colormap or other setting.
- **FR-002**: The number of frames, their file names, their order and their timing MUST be exactly as before this feature; each frame MUST show the same notes in the same places (grid positions or circle positions, in proportion to the picture) and the same colors as before.
- **FR-003**: Pictures MUST be drawn at the 600 × 400 size, not enlarged from a smaller picture: contour edges and lines, the soft edge of blended tiles and the edges of circles MUST be smooth at the new size.
- **FR-004**: For Tiles, Blended tiles and Contour, the tile grid (12 × 7 at the default, finer with oversampling) MUST be spread over the whole 600 × 400 picture, every column the same width and every row the same height to within one pixel.
- **FR-005**: The soft edge of Blended tiles MUST keep its width in proportion to a tile (the Blend width setting means the same as before) at the new size.
- **FR-006**: For Circles, Movement and Radius MUST keep their ranges, defaults, messages and request fields and MUST be measured in pixels of a 252-pixel-wide reference frame, scaled by 600 / 252 at the new size (the circles' places, the start in the middle, the wrap-around of the 600 × 400 edges and the Resize by volume factor included), so that the same settings give the same picture in proportion to the frame.
- **FR-007**: The interpolated (in-between) frames MUST also be 600 × 400 and made from the drawn frames of that size.
- **FR-008**: The frame player MUST show a frame at its full width (up to 600 pixels) when there is room, scale it down on a narrower screen keeping 3:2, never crop or distort it, and keep its controls working as before.
- **FR-009**: A 60 second file at 30 frames per second MUST finish within one minute for every image type at the default settings and within two minutes at the settings that cost the most, and the room taken by the frames of a job MUST be no more than 4 times what it was before this feature.
- **FR-010**: Frames and results created before this feature MUST NOT be changed; the other parts of the page MUST be unchanged.
- **FR-011**: The documentation's statements of the frame size (252 × 168, 12 × 7 tiles of 21 × 24 pixels) MUST be updated.

### Key Entities *(include if feature involves data)*

- **Frame**: One picture of a job: 600 × 400 pixels, 3:2, one per frame time of the file, with the same name, order and timing as before.
- **Reference frame**: The old 252-pixel-wide frame against which the circles' Movement and Radius are measured; 600 pixels is 600 / 252 times as wide.
- **Grid of tiles**: The 12 columns by 7 rows of notes (or the finer grid of the chosen oversampling), spread over the frame with columns and rows of equal size to within one pixel.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the frames created, for every image type, oversampling (1 to 5), interpolate value (1 to 5) and the other settings, are exactly 600 × 400 pixels.
- **SC-002**: For every image type, the number, names, order and timing of the frames of a test file are identical to those made before this feature.
- **SC-003**: For Tiles, every tile column and row of a frame has its size within one pixel of every other, at every oversampling, and the colors of the tiles are exactly those of before (the color at the center of each tile equals the color of the same tile at the old size).
- **SC-004**: A viewer comparing a new contour or blended frame with the old one enlarged to 600 pixels sees finer detail and smoother edges and the same colors and shapes (checked by the edges having more than the stair-step detail of an enlarged picture, and by the same positions of the shapes to within a few pixels).
- **SC-005**: A 60 second, 1,800 frame job finishes within one minute at the default settings and within two minutes at the costliest settings, for each of the four image types, on the development machine.
- **SC-006**: The room taken by the frames of a job is at most 4 times what it was before this feature, for every image type.
- **SC-007**: For circles, the same settings and file give circles at the same places in proportion to the frame (to within one pixel of the old position scaled to 600 pixels, where nothing wraps) and with a radius equal to the old radius times 600 / 252, to within a quarter of a pixel.
- **SC-008**: On a window at least 700 pixels wide the page shows a frame at 600 pixels (no enlargement); on a narrower window the frame fits without cropping and keeps 3:2.

## Assumptions

- **600 × 400 is the one frame size.** The request says "600px wide"; it does not say the height or ask for a choice, so the 3:2 shape of today is kept (600 × 400) and the size is **not a setting**: all frames are this size.
- **All four image types are resized**, and the settings and the notes mean the same as before; only the size and the sharpness change.
- **The rows are spread evenly, not made whole pixels**: 600 divides into 12 columns of exactly 50 pixels, but 400 does not divide into 7 rows (57.14), so rows are 57 or 58 pixels high; the old tiles (21 × 24) were whole pixels, the new ones are not always. This is why the requirement is "within one pixel".
- **Tiles stay flat tiles.** The Tiles image type is flat-colored blocks by design; at 600 pixels they are larger blocks, drawn crisply, but still blocks. The smooth looks are the other types (Blended tiles, Contour, Circles).
- **The player already scales a frame to the page** (up to about 660 pixels); the change is that the frame is now about that size, so the browser no longer enlarges a small picture. The player's controls and behaviour are unchanged.
- **The time and room limits** (one and two minutes for a 60 second job, 4 times the room) are chosen from the present figures (a few seconds to about 10 seconds for most jobs, and up to about 16 seconds for the costliest contour job), with the picture 2.4 times larger; they are the bounds this feature must stay inside.
- **Older results are not converted.** Frames that exist stay as they are.
- **The Circles settings and their help texts are unchanged** (numbers, ranges, readouts in pixels): the readout "4 px" keeps meaning pixels of the reference frame. Whether the help texts should say so is left to the plan.
- This feature is about the size of the frames and how they are drawn. The audio analysis, smoothing, the settings form, the file chooser and the page layout are unchanged.
