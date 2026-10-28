# Feature Specification: Concentric

**Feature Branch**: `025-concentric-circles` (no git branch created; spec directory name only)

**Created**: 2026-10-27

**Status**: Clarified

**Input**: User description: "create a new visualization.  There is a circle for each of the 84 notes, with the centers evenly spaced in 12x7.  Each circle has a radius that will vary in 12 discrete increments.  All of the circles at their full size will be just touching, the circles at their smallest will be 1/12 full size.  Each level of the circle will be have a different color, so a full-size circle will look like the 12 concentric circles.  The size of the circle is based on the harmonic volume of that note, relative to the other notes.  The loudest will be full size, the quietest will be smaller.   The colors of each level of the circle will be determined by the position in the local peak, with a circle full size at the top of the peak will have all 12 colors from the left to the right of the colormap.  At the bottom, a full-size circle will only go 1/2 way around the color map.  Call this image type Concentric."

## Clarifications

### Session 2026-10-27

- Q: What is "the harmonic volume relative to the other notes", and how does it become a step? -> A: **Relative to the loudest note of each frame**, on the square-root scale of the tile colors: `step = max(1, ceil(12 × sqrt(value ÷ the loudest value of the frame's 84 notes)))`. Every frame with any sound has a full-size circle.
- Q: Which existing settings apply to Concentric? -> A: **Only the two Local peaks settings (Minimum distance, Prominence; no checkbox) and Data smoothing (Smoothing window, Smoothing).** No Threshold, Notes, Oversampling, Interpolate or Gaussian smoothing.
- Q: What is the background? -> A: **The colormap's middle color** (table row 128), as for the other circles pictures.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A grid of target-like circles whose size is the note's volume and whose colors follow the beat (Priority: P1)

The user wants a sixth image type, **Concentric** (request value `concentric`). Like the tiles it has **one shape for each of the 84 notes**, laid out on the same **12 × 7 grid** (the first note at the top left, twelve notes to a row, the lowest octave at the top), but each shape is a **circle** centered on its tile, drawn as up to **twelve concentric rings**:

- **Size**: a circle grows in **12 steps**. At its **full size** the circles of neighbouring notes are **just touching**; at its **smallest** a circle has **1/12 of the full radius** (one ring). The step of a note comes from the **harmonic volume of that note relative to the other notes**: the loudest note is full size, the quieter notes are smaller. Every note always has at least its smallest circle.
- **Rings**: every step of the circle is a ring of its own **color**, from the center out: a circle of 5 steps has the 5 inner rings of a full circle. A full-size circle therefore looks like **twelve concentric circles**.
- **Colors**: the color of a ring comes from the **colormap** and depends on **which ring it is** (1, the center, to 12, the outermost) and on the frame's **position in the local energy peak** (feature 023 and 024: 0 at the minimum of the local peak, 1 at its maximum). At the **top of the peak** (position 1) the twelve rings of a full circle run through **the whole colormap, from its left end (ring 1) to its right end (ring 12)**. At the **bottom of the peak** (position 0) they run only **half way along** the colormap (ring 12 is at its middle). In between, the colors stretch smoothly: the last ring is at `0.5 + 0.5 × position` of the way along the colormap.

So the picture shows two things at once: **how loud each note is** (how big its circle is), and **where the music is in its beat** (how far along the colormap the rings go, the same for every circle of a frame).

**Why this priority**: This is the whole request. Its own settings and the page come after.

**Independent Test**: Make a file with a few notes of very different volume and a clear pulse. Create Concentric frames: the loudest note's circle is the biggest and touches its neighbours' cells (all other circles are smaller), the quietest notes have a small dot (one ring), every circle's rings are in the same order of colors, and the frames at the strongest beat have circles whose outermost ring is the right-most color of the colormap, while the frames at the lowest point of the beat stop at the middle color.

**Acceptance Scenarios**:

1. **Given** the frame's note values, **When** the picture is made, **Then** there are 84 circles with their centers at the centers of the 84 tiles of the 12 × 7 grid.
2. **Given** the loudest note of a frame, **When** the picture is made, **Then** its circle is full size, with a radius such that it just touches the circles of its neighbouring cells (the full radius is half the width of a cell).
3. **Given** any note, **When** the picture is made, **Then** its circle has a radius of `step / 12` of the full radius, with `step` a whole number from 1 to 12; a note with no energy has step 1.
4. **Given** a circle of `step` s, **When** the picture is made, **Then** it is drawn as s rings, ring `k` (1 to s) filling the radii from `(k − 1) / 12` to `k / 12` of the full radius, and ring `k` has the same color in a circle of step s and in a full-size circle of the same frame (a smaller circle is a full one with the outer rings left off).
5. **Given** a frame at position 1 in the local peak, **When** the picture is made, **Then** ring 1 has the colormap's first color and ring 12 its last color, with the rings in between at even steps along the colormap.
6. **Given** a frame at position 0, **When** the picture is made, **Then** ring 1 has the first color and ring 12 the color at the middle of the colormap (half way), with the rings in between at even steps.
7. **Given** a frame between 0 and 1, **When** the picture is made, **Then** ring 12 is at `0.5 + 0.5 × position` of the way along the colormap and ring `k` is at `(k − 1) / 11` of that distance.
8. **Given** the same file and settings, **When** the pictures are made twice, **Then** the files are identical.
9. **Given** the other five image types, **When** they are made, **Then** they are identical, file for file, to those made before this feature.

---

### User Story 2 - Choose Concentric on the page and tune the beat (Priority: P2)

The settings page offers **Concentric** as a sixth choice of **Image type**. Because the colors always follow the beat, the **Local peaks** measurement is part of this picture: its two settings (**Minimum distance**, 100 to 2,000 ms, default 100, and **Prominence**, 0 to 100 percent, default 50) decide what counts as a beat, and there is no checkbox to turn the beat off for Concentric.

The settings of Concentric are, besides the file, the colormap and the analysis settings that every picture has: the two **Local peaks** settings and **Data smoothing** (**Smoothing window** and **Smoothing**, which smooth the note values over the frames as for the tiles). **Threshold, Notes, Oversampling, Interpolate and Gaussian smoothing do not apply**: they are accepted by the request and ignored, and not shown on the page or in the summary. The page therefore shows for Concentric the groups Analysis, Colormap, Image type, **Local peaks** (the two settings, no checkbox) and Data smoothing, and no group of its own.

**Why this priority**: The picture exists without the page (through the API), but the user reaches it from the page.

**Independent Test**: On the page choose Concentric: a group for it appears (and the Local peaks group with the two settings and no checkbox), the unused groups are gone, and Create frames makes frames. Through the API `image_type=concentric` makes 600 × 400 frames.

**Acceptance Scenarios**:

1. **Given** the Image type list, **When** the page is shown, **Then** it offers Tiles, Blended tiles, Contour, Circles, Circles paint and **Concentric**, and a request with `image_type=concentric` is accepted; any other value is refused with a message that lists the six names.
2. **Given** Concentric is chosen on the page, **When** the settings are shown, **Then** the groups Analysis, Colormap, Image type, Local peaks (Minimum distance and Prominence, without a Beat coloring checkbox) and Data smoothing are shown, in this order, and the groups of Threshold and Notes and Image smoothing are not.
3. **Given** a Concentric request, **When** the two Local peaks values are not allowed, **Then** they are refused before any work is done, with the messages of the measurement.
4. **Given** a Concentric request, **When** the job is made, **Then** the beat is measured from the audio of the file with those two values (the checkbox sent for another type has no effect here).
5. **Given** the result summary of a Concentric job, **When** it is shown, **Then** it lists the image type, the colormap, the smoothing settings, Minimum distance and Prominence, and not Threshold, Notes, Interpolate, Oversampling or Gaussian smoothing.

---

### User Story 3 - Quiet, silent and beat-less moments look sensible (Priority: P3)

- A **silent frame** (every note is 0) still shows the 84 smallest circles (one ring each).
- A frame with **no known beat** (before the first peak, a file without peaks, a silent file) has position 0, so its circles only use the first half of the colormap.
- A frame whose notes all have the **same** volume has every circle at the same size (full size, since the loudest of a frame is full size), unless that volume is 0.

The **step of a note** is `max(1, ceil(12 × sqrt(value ÷ the loudest value of the frame)))`, with `value` the note's smoothed harmonic value and the loudest taken over the 84 drawn notes of that frame: the loudest note is step 12, a note with a quarter of its energy is step 6, and a note with almost no energy is step 1. A frame with no sound at all has every circle at step 1.

**Why this priority**: These define the picture in the corners.

**Independent Test**: A silent file gives frames of 84 dots; a file with all notes equal gives 84 full-size circles; a file without a beat uses only the first half of the colormap.

**Acceptance Scenarios**:

1. **Given** a silent file, **When** the pictures are made, **Then** they are made without failing and every note has a circle of step 1.
2. **Given** a file or frame with no beat, **When** the pictures are made, **Then** the position in the peak is 0 for those frames.
3. **Given** a note whose value is higher than another's in the same frame, **When** the picture is made, **Then** its circle is never smaller.
4. **Given** a frame, **When** the picture is made, **Then** the loudest note has step 12 and every other note has the step `max(1, ceil(12 × sqrt(value ÷ loudest)))`.

---

### Edge Cases

- **Circles never overlap**: at full size neighbouring circles just touch (horizontally, where the cells are the narrowest); a smaller circle leaves a gap. A circle is never drawn outside its own cell.
- **The cells are not square**: on the 600 × 400 frame a cell is 50 pixels wide and 57 or 58 high (as for the tiles), so the full radius is **25 pixels** and circles in the same row touch while the rows are about 7 pixels apart.
- **Edges of the circles** are smooth (drawn at a higher resolution and averaged down, as the other circles are), so the rings are clean at every size.
- **At position 0 the outermost ring of a full circle is the color of the background**: ring 12 is at the middle of the colormap and so is the background (both are table row 128), so a full circle at the bottom of the peak seems to end at ring 11 (table row 116). This follows from the clarified colors and background.
- **Very small circles**: the smallest circle (one ring) has a radius of about 2 pixels.
- **A file with very few notes sounding**: the quiet notes are step 1; the picture does not disappear.
- **Different frame rates and window sizes** work as for the other pictures; the frame count, names, size (600 × 400) and timing do not change.
- **A very short file** (shorter than the peaks window) is measured as one window.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: There MUST be a sixth image type, `concentric` (label **Concentric**), accepted by the job request and offered on the settings page; the list of image types in the refusal message MUST name all six.
- **FR-002**: A Concentric frame MUST draw **84 circles**, one for each drawn note, centered on the centers of the tiles of the original 12 × 7 grid of the 600 × 400 frame (note `n` at row `n // 12` from the top and column `n % 12`).
- **FR-003**: The **full radius** MUST be such that circles at full size in neighbouring cells just touch: half the width of a cell, 25 pixels on the 600 × 400 frame.
- **FR-004**: A circle MUST have a **step** from 1 to 12 and a radius of `step / 12` of the full radius; it MUST never be smaller than step 1, so every note is always drawn.
- **FR-005**: The **step of a note** MUST be `max(1, ceil(12 × sqrt(value ÷ loudest)))`, with `value` the note's smoothed harmonic value (the one the tiles use) and `loudest` the largest value of the frame's 84 drawn notes; with `loudest = 0` every note is step 1. The loudest note is therefore step 12, and a louder note never has a smaller step than a quieter one of the same frame.
- **FR-006**: The background MUST be the colormap's middle color (table row 128). A circle of step `s` MUST be drawn as `s` **rings**; ring `k` (from 1 at the center to `s`) MUST fill the radii from `(k − 1) / 12` to `k / 12` of the full radius, and MUST have the same color as ring `k` of a full-size circle of the same frame.
- **FR-007**: Ring `k` MUST have the colormap's color at the position `(k − 1) / 11 × (0.5 + 0.5 × position)` along the colormap (table entry `rint(that × 255)`), where `position` is the frame's position in the local peak, from 0 to 1, as for feature 024 (the middle of the frame's interval, from the local peaks measurement of the whole file, 0 when no beat is known). At position 1 ring 1 is the first color and ring 12 the last; at position 0 ring 12 is the middle of the colormap.
- **FR-008**: Every circle of a frame MUST use the frame's one position in the peak, so every circle of the frame has the same rings and colors for the same step.
- **FR-009**: The local peaks settings (**minimum distance** and **prominence**) MUST be available for Concentric (in the Local peaks group, which for Concentric has no checkbox), with the checks and messages of the measurement, checked before any work is done; the beat always colors Concentric, so the measurement is made for every Concentric job.
- **FR-010**: The settings that apply to Concentric, and only those (colormap, the analysis settings, Smoothing window, Smoothing, Minimum distance and Prominence), MUST be shown on the page and in the result summary; Threshold, Notes, Oversampling, Interpolate and Gaussian smoothing MUST be accepted by the request, checked as always, and have no effect on Concentric.
- **FR-011**: The frames MUST be 600 × 400, with the frame count, names, timing and interpolation behavior of the other image types; the same file and settings MUST give the same frames; the other five image types MUST be identical, file for file, to those made before this feature (the reference hashes).
- **FR-012**: Creating the frames of a 60 second file at 30 frames a second MUST NOT take more than a few seconds longer than for Tiles.
- **FR-013**: The documentation MUST describe Concentric, its size, rings and colors, and its settings.

### Key Entities *(include if feature involves data)*

- **Circle**: The drawing of one note: centered on its tile, with a step from 1 to 12 and as many rings.
- **Step**: A whole number from 1 to 12; the radius is `step / 12` of the full radius. It comes from the note's volume relative to the other notes.
- **Ring**: One band of a circle, ring `k` between `(k − 1) / 12` and `k / 12` of the full radius; its color depends on `k` and on the frame's position in the peak.
- **Position in the local peak**: As in feature 024, a frame's position from 0 to 1 from the local peaks measurement.
- **Concentric image type**: The new picture, value `concentric`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In every Concentric frame the circle of the loudest note has a radius of 25 pixels (to within a pixel) and every other circle has a radius of `step / 12 × 25` pixels to within a pixel, with `step` a whole number from 1 to 12.
- **SC-002**: At position 1 the twelve ring colors of a full circle are the colormap's table entries at `rint((k − 1) / 11 × 255)`; at position 0 they are those at `rint((k − 1) / 11 × 127.5)`, for every colormap, checked at the ring centers.
- **SC-003**: Neighbouring full-size circles in a row touch (the distance between their centers equals the sum of their radii to within a pixel) and no circle extends outside its cell.
- **SC-004**: A circle of step `s` has the same colors in its `s` rings as the first `s` rings of a full circle of the same frame, and nothing is drawn outside its outer ring but the background.
- **SC-005**: A silent file, a file without a beat and a file shorter than the peaks window make Concentric frames without failing; in the silent file every circle is step 1.
- **SC-006**: The frames of Tiles, Blended tiles, Contour, Circles and Circles paint for the reference test files are identical, file for file, to those made before this feature, and two runs of the same Concentric job are identical.
- **SC-007**: A 60 second file at 30 frames a second makes its Concentric frames in under 30 seconds on the development machine.

## Assumptions

- **The grid and the centers** are those of the original 12 × 7 grid on the 600 × 400 frame, as for the tiles: columns 50 pixels wide, rows 57 or 58 high; the full radius is half the narrower side of a cell (25 pixels), so neighbours in a row touch and the rows have a small gap. The user said "evenly spaced in 12 × 7" and "just touching"; with the cells not square, "just touching" holds in the rows.
- **The 84 notes** are the drawn notes of the other pictures (the 88 notes less the top four), after the note smoothing as for the tiles (the "harmonic volume" is the same value that the tiles use). The step of a note comes from that value.
- **The position in the peak** is the one of feature 024 (the interpolated energy between the interpolated minimum and maximum of the neighbouring peaks' windows, held within 0 and 1, read in the middle of each frame, 0 before the first peak and without peaks).
- **Smooth edges**: rings are drawn with antialiased edges (supersampled as for the other circles), so a pixel on the border of two rings is a mix of their colors.
- **The background** is the colormap's middle color (the clarification), the same color that the Circles pictures and the Blended tiles use.
- **Colors of the rings are not blurred or interpolated**: each ring is one flat color; Gaussian smoothing does not apply to Concentric.
- **The beat coloring checkbox of Tiles and Blended tiles** is not used here: the beat always colors Concentric, and the two Local peaks settings are sent and checked as they are for those types.
