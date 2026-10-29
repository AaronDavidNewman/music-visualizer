# Feature Specification: Decay

**Feature Branch**: `027-decay-circles` (no git branch created; spec directory name only)

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "create another visualization with the concentric circles in the same location/configuration as the concentric image type.  Each circle will logically keep a point value from 0 to 64.  The size of the circle goes from smallest at 0, to largest at 24.  The colors go from left-most at 0 to right-most at 32.  This means the circle can be 'saturated' with more points than 32.  Only 5 highest-volume notes are counted, the highest note's circle gets 24 points, second highest 20, and so on down to 8.  Add additionally based on the local peak value 8 for the top, down to 0 for the bottom, linearly.  A circle can't have more than 64 points or fewer than 0.  At some rate from 1-10 frames, each circle will 'decay' by giving up 2 points to each adjacent circle.  The decay rate is the paramter or this image type.  For circles on the edge that don't have 8 neighbors, subtract extra so that each circle loses 16 points each interval.  The image type is called 'decay'"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Circles that charge up on loud notes and bleed into their neighbours (Priority: P1)

The user wants a seventh image type, **Decay** (request value `decay`). It has **one circle for each of the 84 notes**, in the **same places and layout as Concentric**: centered on the tiles of the 12 × 7 grid, with the same full radius (neighbouring circles just touch at full size), the same background and the same choice of note layout (Rows or Spiral). Unlike Concentric, a circle in Decay **remembers** what happened to it in the earlier frames: it keeps a **point value from 0 to 64** that goes up when its note is loud and drains away, partly into the neighbouring circles, as time passes. The picture therefore shows the music as glowing spots that flare up on the loudest notes and then **spread out and fade** over the grid.

- **Size**: the size of a circle follows its points, from the **smallest circle at 0 points** to the **full-size circle at 24 points**. A circle with more than 24 points stays full size.
- **Color**: the color of a circle follows its points along the colormap, from the **left-most color at 0 points** to the **right-most color at 32 points**. From 32 to 64 points the circle gets **rings**: it is made of the **12 concentric rings** of Concentric (ring 1 at the center, ring 12 at the edge). At 32 points every ring is the right-most color, so the circle looks flat; as the points rise the outer rings run further back along the colormap, until at **64 points the 12 rings run across the whole colormap from the last color (the center) to the first (the edge)**. As the points fall again the outer rings come back to the last color first, so the decay can be seen all the way down from 64 instead of sitting at one color.
- **Gaining points**: in every frame only the **5 loudest notes** count. The loudest gets **24 points**, the second **20**, the third **16**, the fourth **12** and the fifth **8**. On top of that, each of those five gets a **beat bonus** from the frame's position in the local energy peak (features 023 and 024): **8 points at the top of the peak, 0 at the bottom**, linearly in between. The points are **added** to what the circle already has. A circle never has more than 64 points or fewer than 0.
- **Decay**: every **N frames** (the **decay rate**, a whole number from 1 to 10, the one setting of this image type) every circle gives up **2 points to each of its adjacent circles** (the up to 8 cells around it, diagonals included). A circle on an edge or in a corner has fewer than 8 neighbours but still **loses 16 points** in the interval: it gives 2 points to each neighbour it has, and the rest of the 16 is lost. So the points of a loud note spread out over its surroundings and drain away at the edges of the grid.

**Why this priority**: This is the whole request. Its page controls and corner cases come after.

**Independent Test**: Make a file with one steady loud note. Create Decay frames: the circle of that note grows to full size and to the right-most color within a few frames and stays there (the 24 to 32 points it gains each frame outweigh the decay); the circles around it become larger and brighter one interval after it; when the note stops, its circle shrinks and loses its color over the following intervals while its neighbours first rise and then also fade; a circle in a corner fades faster than one in the middle of the grid.

**Acceptance Scenarios**:

1. **Given** the frame's note values, **When** the picture is made, **Then** there are 84 circles with their centers at the same places as in Concentric (including the Spiral note layout when it is chosen), on the same background, with the same full radius.
2. **Given** a circle with `p` points, **When** the picture is made, **Then** its radius is the smallest radius (one twelfth of the full radius, as for the smallest Concentric circle) at `p = 0`, the full radius at `p ≥ 24`, and grows linearly with `p` in between.
3. **Given** a circle with `p` points, **When** the picture is made, **Then** its center (ring 1) is the colormap's table entry at `rint(min(p, 32) / 32 × 255)`, the first color at 0 points and the last color at 32 or more; up to 32 points the whole circle is that one color.
4. **Given** a frame with sound, **When** the points are added, **Then** the 5 notes with the highest values of the frame (the 84 drawn notes) get 24, 20, 16, 12 and 8 points in that order of loudness, plus `8 × position` points each, with `position` the frame's position in the local peak (0 to 1); all other circles gain nothing.
5. **Given** a circle that would end with more than 64 or fewer than 0 points, **When** its points are worked out, **Then** it has 64 or 0 points.
6. **Given** a decay rate of N, **When** frame number `i` is made (numbering from 1), **Then** after the frame's points are added the decay is applied if `i` is a multiple of N, and the picture of the frame shows the points after that.
7. **Given** a decay step and a circle with 8 neighbours and at least 16 points, **When** the decay is applied, **Then** it loses 16 points and each of its neighbours receives 2 points from it.
8. **Given** a decay step and a circle at an edge (5 neighbours) or in a corner (3 neighbours) with at least 16 points, **When** the decay is applied, **Then** it loses 16 points in all: 2 for each neighbour it has and the rest (6 at an edge, 10 in a corner) is lost.
9. **Given** the same file and settings, **When** the pictures are made twice, **Then** the files are identical.
10. **Given** the other five image types and Concentric, **When** they are made, **Then** they are identical, file for file, to those made before this feature.

---

### User Story 2 - Choose Decay on the page and set the decay rate (Priority: P2)

The settings page offers **Decay** as a seventh choice of **Image type**. Its own setting is the **Decay rate**: a whole number from **1 to 10** (the number of frames between two decay steps; default **5**), in a group of its own. The page shows for Decay what it shows for Concentric: the groups Analysis, Colormap, Image type, **Local peaks** (Minimum distance and Prominence, no checkbox, because the beat always adds points), **Data smoothing** (Smoothing window and Smoothing) and **Note layout** (Rows or Spiral), plus the Decay group. **Threshold, Notes, Oversampling, Interpolate and Gaussian smoothing do not apply**: they are accepted by the request and ignored, and not shown on the page or in the summary.

**Why this priority**: The picture exists without the page (through the API), but the user reaches it from the page.

**Independent Test**: On the page choose Decay: the Decay group with the Decay rate appears together with the groups listed above, the unused groups are gone, and Create frames makes frames. Through the API `image_type=decay&decay_rate=3` makes 600 × 400 frames.

**Acceptance Scenarios**:

1. **Given** the Image type list, **When** the page is shown, **Then** it offers Tiles, Blended tiles, Contour, Circles, Circles paint, Concentric and **Decay**, and a request with `image_type=decay` is accepted; any other value is refused with a message that lists the seven names.
2. **Given** Decay is chosen on the page, **When** the settings are shown, **Then** the groups Analysis, Colormap, Image type, Local peaks (without a Beat coloring checkbox), Data smoothing, Note layout and Decay are shown, and the groups of Threshold and Notes and Image smoothing are not.
3. **Given** a Decay request, **When** the decay rate is not a whole number from 1 to 10, **Then** it is refused before any work is done, with a message that names the allowed range; when it is left out, 5 is used.
4. **Given** a request of another image type, **When** a decay rate is sent, **Then** it is accepted (if allowed) and has no effect.
5. **Given** a Decay request, **When** the Local peaks values are not allowed, **Then** they are refused before any work is done, with the messages of the measurement; the beat is measured for every Decay job.
6. **Given** the result summary of a Decay job, **When** it is shown, **Then** it lists the image type, the colormap, the smoothing settings, the note layout, Minimum distance, Prominence and the Decay rate, and not Threshold, Notes, Interpolate, Oversampling or Gaussian smoothing.

---

### User Story 3 - Quiet, silent and beat-less moments look sensible (Priority: P3)

- The first frame starts from **all circles at 0 points**; a **silent file** therefore gives frames of 84 smallest circles in the first color.
- A frame with **no known beat** (before the first peak, a file without peaks) has position 0, so the five loudest notes gain only 24, 20, 16, 12 and 8 points.
- A **silent frame** in the middle of a file adds nothing; the circles only decay.
- A frame in which fewer than 5 notes have any energy only counts the notes with energy: a note whose value is 0 gets no points. **Ties** are broken in favour of the lower note.
- Points that a neighbour would receive beyond 64 are lost, and a circle never gives away more points than it has: a circle with `p` points, with `p` less than 16, gives away only `p` points, spread over its neighbours and the loss in the same proportions as the full 16, so it ends at 0 and no points appear from nothing.
- All circles give and receive **at the same time** in a decay step: the amounts are worked out from the points before the step.

**Why this priority**: These define the picture in the corners.

**Independent Test**: A silent file gives 84 dots in the first color; a file with one loud note followed by silence ends with every circle at 0 points after enough intervals; the total of the points never grows in a decay step.

**Acceptance Scenarios**:

1. **Given** a silent file, **When** the pictures are made, **Then** they are made without failing and every circle has 0 points.
2. **Given** a file or frame with no beat, **When** the points are added, **Then** the beat bonus is 0 for those frames.
3. **Given** two notes with the same value, **When** they compete for a place in the five, **Then** the lower note is ranked higher.
4. **Given** any decay step, **When** it is applied, **Then** the total of the points after it is never greater than before it, and no circle has fewer than 0 or more than 64 points.
5. **Given** a long silence after a loud passage, **When** enough intervals have passed, **Then** every circle is back at 0 points.

---

### Edge Cases

- **Circles never overlap and never leave their cell**: at full size neighbours in a row just touch; a smaller circle leaves a gap (as for Concentric).
- **Edges of the circles** are smooth (antialiased), as for the other circles.
- **A decay rate of 1** applies the decay after every frame; **10** after every tenth frame (frames 10, 20, 30 and so on).
- **A loud note held for a long time** reaches 64 points and stays there (12 rings from the last color to the first); after the note stops, its outer rings come back to the last color first, and the circle is flat again at 32 points before its color starts to move back along the colormap.
- **Neighbours are neighbours on the grid**, not in pitch: with the Spiral note layout the neighbours of a circle are the circles around its cell, whatever notes they hold.
- **Different frame rates and window sizes** work as for the other pictures; the frame count, names, size (600 × 400) and timing do not change. The decay rate counts frames, so at a higher frame rate the picture decays faster in time.
- **A very short file** (shorter than the peaks window) is measured as one window.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: There MUST be a seventh image type, `decay` (label **Decay**), accepted by the job request and offered on the settings page; the list of image types in the refusal message MUST name all seven.
- **FR-002**: A Decay frame MUST draw **84 circles** in the places, with the full radius and on the background of Concentric, and MUST respect the Note layout setting (Rows or Spiral) as Concentric does.
- **FR-003**: Every circle MUST have a **point value from 0 to 64**, kept from frame to frame: all circles start at 0 before the first frame and the value after one frame is the starting point of the next.
- **FR-004**: The **radius** of a circle MUST be one twelfth of the full radius at 0 points, the full radius at 24 points or more, and linear in the points in between: `full × (1/12 + 11/12 × min(points, 24) / 24)`.
- **FR-005**: The **color** of a circle MUST be one flat color, the colormap's table entry at `rint(min(points, 32) / 32 × 255)`, up to 32 points. Above 32 points the circle MUST be drawn as the 12 concentric rings of Concentric (ring `k` between `(k − 1) / 12` and `k / 12` of the full radius, 1 at the center): ring `k` (1 at the center to 12 at the edge) is at `min(p, 32) / 32 − (p − 32) / 32 × (k − 1) / 11` of the way along the colormap (with `p − 32` taken as 0 below 32 points), table entry `rint(that × 255)`, so ring 1 is always the color above and at 64 points ring 12 is the first color. At 32 points all rings are the last color.
- **FR-006**: In every frame the **5 notes with the highest value** (the smoothed harmonic value the tiles use, among the 84 drawn notes, ties to the lower note, notes with value 0 excluded) MUST gain 24, 20, 16, 12 and 8 points in order of loudness, plus a beat bonus of `8 × position` points each, where `position` is the frame's position in the local peak (0 to 1, as for Concentric; 0 when no beat is known). The gain MUST be added to the circle's points and the result held within 0 and 64.
- **FR-007**: The **decay rate** `N` (a whole number from 1 to 10, default 5) MUST be a parameter of the image type. Frames MUST be numbered from 1, and a decay step MUST be applied after the points of frame `i` are added whenever `i` is a multiple of `N`; the frame's picture MUST show the points after that step.
- **FR-008**: In a decay step every circle MUST give **2 points to each adjacent circle** (the up to 8 cells around it on the grid, diagonals included) and lose **16 points in all**, the part of the 16 that has no neighbour to go to being lost. A circle with fewer than 16 points gives only what it has, in the same proportions. All circles MUST give and receive at the same time, from the points before the step, and the result MUST be held within 0 and 64 (points received above 64 are lost); a circle left with less than 0.01 points after a step MUST have 0, so that a faded circle really reaches 0.
- **FR-009**: The local peaks settings (**minimum distance** and **prominence**) MUST be available for Decay (in the Local peaks group without a checkbox), with the checks and messages of the measurement, checked before any work is done; the measurement is made for every Decay job.
- **FR-010**: The **decay rate** MUST be checked before any work is done and refused with a message naming the allowed range when it is not a whole number from 1 to 10; it MUST be shown on the page for Decay in a group of its own and in the result summary.
- **FR-011**: The settings that apply to Decay, and only those (colormap, the analysis settings, Smoothing window, Smoothing, Minimum distance, Prominence, Note layout and Decay rate), MUST be shown on the page and in the result summary; Threshold, Notes, Oversampling, Interpolate and Gaussian smoothing MUST be accepted by the request, checked as always, and have no effect on Decay.
- **FR-012**: The frames MUST be 600 × 400, with the frame count, names and timing of the other image types; the same file and settings MUST give the same frames; the other six image types MUST be identical, file for file, to those made before this feature (the reference hashes).
- **FR-013**: Creating the frames of a 60 second file at 30 frames a second MUST NOT take more than a few seconds longer than for Concentric.
- **FR-014**: The documentation MUST describe Decay, its points, size, colors, gain and decay, and its settings.

### Key Entities *(include if feature involves data)*

- **Circle**: The drawing of one note: centered on its cell, with a point value from 0 to 64 that decides its size and color.
- **Points**: A number from 0 to 64 that a circle keeps from frame to frame; it grows when the note is among the five loudest and shrinks by decay.
- **Gain**: The points a circle receives in a frame: 24, 20, 16, 12 or 8 by rank plus the beat bonus of 0 to 8.
- **Decay step**: The exchange every N frames in which each circle gives 2 points to each neighbour and loses 16 points in all.
- **Decay rate**: The number of frames N, from 1 to 10, between two decay steps.
- **Decay image type**: The new picture, value `decay`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In every Decay frame the radius of every circle is within a pixel of the radius given by its points (`25 × (1/12 + 11/12 × min(points, 24) / 24)` pixels on the 600 × 400 frame) and its color is the colormap's table entry given by its points, for every colormap.
- **SC-002**: For a file with one steady loud note and no beat, the circle of that note is full size and in the right-most color from the frame at which it has accumulated 32 points, and stays so while the note lasts.
- **SC-003**: In every decay step no circle has fewer than 0 or more than 64 points afterwards, the total of all points never grows, and an interior circle with at least 16 points loses exactly 16 while an edge circle and a corner circle also lose exactly 16 (receiving less than an interior one).
- **SC-004**: After a loud passage followed by silence, every circle is back at 0 points within 200 decay steps.
- **SC-005**: A silent file, a file without a beat and a file shorter than the peaks window make Decay frames without failing; in the silent file every circle has 0 points.
- **SC-006**: The frames of the other six image types for the reference test files are identical, file for file, to those made before this feature, and two runs of the same Decay job are identical.
- **SC-007**: A 60 second file at 30 frames a second makes its Decay frames in under 30 seconds on the development machine.

## Assumptions

- **"The concentric image type" location and configuration** means the places, full radius, background and note layout choice of Concentric (feature 025 and the Spiral layout of feature 026): the same function that places the circles is used, and Decay inherits the Note layout setting.
- **Flat up to 32 points, rings above**: a Decay circle is a single flat disc whose size and color follow its points up to 32 points; from 32 to 64 it gets the 12 rings of Concentric, which open up from the last color (the center) towards the first (the edge). The user asked for the rings to run "from last to first"; the assumption is that the center is the last color and the edge the first (the other way round would put the dark colors in the middle).
- **Smallest circle**: "smallest at 0" means the same smallest circle as Concentric (one twelfth of the full radius), so a circle with no points is still a small dot in the first color; every note stays visible. The size grows linearly with the points (not in 24 jumps).
- **The beat bonus goes to the five counted notes** ("only 5 highest-volume notes are counted"); circles outside the five get nothing from the beat. The bonus is not rounded, so points can be fractional.
- **Volume** is the smoothed harmonic value of a note, the one Concentric and the tiles use; the Data smoothing settings apply as for Concentric.
- **Position in the peak** is the one of feature 024, read in the middle of each frame, 0 before the first peak and for a file without peaks.
- **Adjacent circles** are the up to 8 surrounding cells of the 12 × 7 grid (diagonals included); the grid does not wrap around.
- **Giving points** works as written in the request for circles that have enough points; for circles with fewer than 16 points the assumption is that they give only what they have (in the same proportions), so that no points are created. The user did not say what happens then.
- **A hundredth of a point is nothing**: because a circle with fewer than 16 points gives only what it has, the points of a fading area halve again and again and would never quite reach 0; after a decay step a circle with less than 0.01 points (a fraction of a pixel of radius) has none. The user did not say this; without it "back at 0" would never be exactly true.
- **Timing of the decay** is by frame number counted from 1 in the picture sequence; the starting state is all circles at 0 points.
- **Default decay rate** is 5, in the middle of the allowed range.
- **Settings that do not apply**: as for Concentric, Threshold, Notes, Oversampling, Interpolate and Gaussian smoothing are accepted and ignored; the beat always counts, so there is no beat checkbox.
