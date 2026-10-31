# Feature Specification: Contour Beat Wave

**Feature Branch**: `028-contour-beat-wave` (no git branch created; spec directory name only)

**Created**: 2026-10-29

**Status**: Draft

**Revised 2026-10-30** (two changes the user made to `beat_wave.py` after the first implementation, for "more graceful transitions"; they replace the formula and the effect wherever the text below says otherwise):

1. **The sine runs over the square root of the relative distance**: `pattern = (sin(waves × 2π × sqrt(distance ÷ largest dimension)) + 1) ÷ 2`. The rings are close together near the center and the wave gets lower in frequency (the rings wider) towards the outside.
2. **The position in the beat is passed through a sine from 0 to π**: the modifier is `1 − pattern × sin(π × k)`. The effect is nothing at the minimum of the beat (`k = 0`), **strongest half way up the beat (`k = 0.5`)**, and fades again to (all but exactly) nothing at its maximum (`k = 1`), the same going up and coming down. It is no longer strongest at the top of the beat.

**Input**: User description: "allow the local maximum to be incorporated into the contour type, using a modifier for the place in the beat.  For each set of data Z, create a matrix with the same dimensions, with the formula Z1[x, y] = np.sin(p1*np.pi*2*(radius/maxdim))  Radius is sqrt(x**2+y**2) for each point, adjusted for the center, so that the center would be radius 0.  p1 is a parameter between 2 and 10.   maxdim is the largest dimension (x or y).  Map Z1 between 0 and 1 vs. -1 to 1.  Then:  Z1=np.ones(..Z1 shape) - Z1*k.  The k here is the distance from the next maxium.  Then the contour Z is Z=Z*Z1.   The idea is that the graph is unaffected when the beat is at a minimum since Z1 is all 1's.  As it gets closest to maximum, the influence of the wave effect increases.  The contour can be done with or without local maximum (without it is the same as it is currently)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The contour map ripples with the beat (Priority: P1)

The **Contour** picture draws the 12 × 7 grid of note values as a filled contour map. The user wants it to be able to show **where the music is in its beat** (the local energy peaks of feature 023, with the frame's position in the peak from feature 024: 0 at the minimum of the local peak, 1 at its maximum) by laying a **ring-shaped wave** over the map:

- A **wave pattern** is made for the frame with the same shape as its grid of values. For every point of the grid it takes the distance from the **center of the grid** (the center is distance 0), divides it by the **largest dimension of the grid** (the larger of its width and height, in grid points), takes the **square root** of that share, and makes concentric rings: `sin(waves × 2π × sqrt(distance ÷ largest dimension))`, with `waves` the **wave count** (Story 2: from 2 to 10). The pattern is then **rescaled from the range −1 to 1 to the range 0 to 1**, so it is a set of rings that run from 0 to 1 and back, seen from the center outward; because of the square root the rings are close together near the center and wider towards the outside.
- The pattern is turned into a **modifier**: `1 − pattern × sin(π × k)`, where `k` is the frame's **place in the beat**, from 0 at the minimum of the local peak to 1 at its maximum. The user's description calls `k` the distance from the next maximum; what is meant is a position in the beat (0 to 1), and the sine from 0 to π makes the effect swell and fade smoothly over the beat: nothing at the minimum, strongest half way, nothing again at the maximum.
- The frame's values are **multiplied by the modifier** before the contour is drawn.

So **when the beat is at a minimum (`k = 0`) the modifier is 1 everywhere and the picture is exactly the plain contour**; as the beat rises the rings **cut deeper into the picture** (a point on a dark ring of the pattern, where the pattern is 1, is dimmed by the factor `1 − sin(π × k)`, down to zero half way up the beat; a point between the rings, where the pattern is 0, is never touched), and as the beat goes on to its maximum the rings **fade out again**, so the map pulses with the beat.

**Why this priority**: This is the whole request. The choices to turn it on and to set the wave count come with Story 2.

**Independent Test**: Make a file with a steady chord and a clear pulse. Create Contour frames with the beat wave on: the frames at the lowest point of the beat are identical to the plain Contour frames of the same file, the frames half way up a beat show the most pronounced concentric rings, centered on the middle of the picture, with the rings darkest there, and the frames at the top of the beat are (all but exactly) the plain frames again.

**Acceptance Scenarios**:

1. **Given** the beat wave is on and a frame at position 0 in the local peak (the minimum, or no known beat), **When** the picture is made, **Then** it is identical, file for file, to the plain Contour picture of that frame.
2. **Given** the beat wave is on and a frame at position `k` between 0 and 1, **When** the picture is made, **Then** the values of the grid have been multiplied, point by point, by `1 − pattern × sin(π × k)`, where `pattern` at grid point `(x, y)` is `(sin(waves × 2π × sqrt(distance ÷ largest dimension)) + 1) ÷ 2` and `distance` is the distance from the center of the grid to the point.
3. **Given** the center of the grid, **When** the pattern is worked out, **Then** the distance there is 0 (the center is the origin of the rings).
4. **Given** a larger wave count, **When** the picture is made, **Then** there are more rings across the picture.
5. **Given** a frame at position 0.5 (half way up the beat), **When** the picture is made, **Then** a grid point where the pattern is 1 has its value multiplied by 0, and a grid point where the pattern is 0 keeps its value; at positions 0 and 1 no point is changed (all but exactly, at 1), and positions `k` and `1 − k` give the same picture.
6. **Given** the same file and settings, **When** the pictures are made twice, **Then** the files are identical.
7. **Given** the other six image types, **When** they are made, **Then** they are identical, file for file, to those made before this feature.

---

### User Story 2 - Turn the beat wave on, and choose how many waves (Priority: P2)

The beat wave is a **choice**, **off by default**, so that **without it the contour is exactly as it is today**:

- The **Local peaks** group of the settings page (which today has the **Beat coloring** checkbox and the two measurement settings, **Minimum distance** and **Prominence**, for Tiles and Blended tiles) is also shown for **Contour**. Its checkbox, **Beat coloring**, turns the beat wave **on or off** for Contour as it turns the beat coloring on or off for the tiles; the two measurement settings decide what counts as a beat, as for the tiles (Minimum distance 100 to 2,000 ms, default 100; Prominence 0 to 100 percent, default 50).
- A new setting, the **Wave count** (the `p1` of the description), is a whole number from **2 to 10**, default **4**, in the Contour group beside Threshold and Notes. It only has an effect when the beat wave is on.

When the checkbox is off, the beat is not even measured and the Contour frames are identical, file for file, to those made before this feature, whatever the wave count is.

**Why this priority**: The picture exists without the page (through the API), but the user reaches it from the page.

**Independent Test**: On the page choose Contour: the Local peaks group appears with the checkbox and the two sliders, and the Contour group has Threshold, Notes and Wave count. Through the API `image_type=contour&beat_coloring=true&wave_count=6` makes 600 × 400 frames with the wave.

**Acceptance Scenarios**:

1. **Given** no value for the checkbox, **When** the Contour pictures are made, **Then** the beat wave is off and the frames are identical, file for file, to those made before this feature.
2. **Given** the checkbox is on, **When** the Contour job is made, **Then** the beat is measured from the audio of the file with the two Local peaks values and the wave count applies.
3. **Given** the checkbox is off, **When** the job is made, **Then** the beat is not measured, and the wave count (any allowed value) has no effect on the frames.
4. **Given** a wave count that is not a whole number from 2 to 10, **When** the job is requested, **Then** it is refused before any work is done, with a message that names the allowed range; when it is left out, 4 is used. The wave count is checked for every image type and has no effect on the others.
5. **Given** the Local peaks values are not allowed, **When** the job is requested for Contour, **Then** they are refused before any work is done, with the messages of the measurement.
6. **Given** the image type Contour on the page, **When** the settings are shown, **Then** the groups Analysis, Colormap, Image type, Contour (Threshold, Notes, Wave count), Local peaks (the checkbox and the two sliders), Data smoothing and Image smoothing are shown, in this order.
7. **Given** the result summary of a Contour job, **When** it is shown, **Then** it lists Beat coloring, and, when it is on, Minimum distance, Prominence and the Wave count.

---

### User Story 3 - Quiet, beat-less and flat moments look sensible (Priority: P3)

- **No known beat** (before the first peak, a file without peaks, a silent file): the position in the peak is 0, so the picture is the plain contour, as for the tiles.
- **A frame with nothing to draw** (every value the same, a silent frame, every note hidden): it is written as one flat color as today; the wave does not change it (multiplying a flat frame by the modifier would only make it uneven, so a flat frame stays flat).
- **The color scale** of a frame still runs from 0 to the largest value of that frame **before** the wave is applied (as the contour does today), so a point dimmed by the wave is shown darker than the same point would be without it; this is what makes the rings visible.
- **The hidden notes** (the threshold) are 0 before and after the wave.

**Why this priority**: These define the picture in the corners.

**Independent Test**: A silent file and a file without a beat give the same frames with the wave on as with it off; a flat frame stays one flat color at every position in the beat.

**Acceptance Scenarios**:

1. **Given** a silent file with the beat wave on, **When** the pictures are made, **Then** they are made without failing and are identical to the pictures made with it off.
2. **Given** a file in which no beat is found, **When** the pictures are made with the wave on, **Then** they are identical to those made with it off.
3. **Given** a frame whose values are all equal, **When** it is made with the wave on at any position in the beat, **Then** it is the same flat color as with the wave off.
4. **Given** a frame with the wave, **When** the color of a grid point is worked out, **Then** it is the colormap's color at the point's value after the wave, on the scale from 0 to the largest value of the frame before the wave.

---

### Edge Cases

- **Oversampling**: with the oversampling setting above 1 the grid of the frame is finer (7r × 12r values); the pattern is worked out on that grid, with its own center and its own largest dimension, so the rings look the same at every oversampling (a ring is the same fraction of the picture).
- **The grid is not square** (12 columns by 7 rows): the largest dimension is the 12 columns direction, so the rings are circles in grid points, not in the picture (the picture's cells are taller than they are wide, and the distance is counted in grid points, as described).
- **Wave count** at its ends: with 2 there are two rings across the largest dimension from the center to the edge of the grid's largest dimension, with 10 there are ten; a whole number of waves means the pattern at distance `largest dimension` is the same as at the center.
- **The center of an even-sized grid** lies between the grid points (the center of a 12-point axis is at 5.5), so no point has distance exactly 0 on an even axis; the distance is measured from the geometric center of the grid.
- **Interpolate and Gaussian smoothing** apply as before: the wave is part of the values from which a frame is drawn, and the frames that are made from their neighbours (Interpolate) or blurred (Gaussian) are made from the frames with the wave.
- **The beat is the same for every point of a frame**: only the pattern varies over the picture.
- **A very short file** (shorter than the peaks window) is measured as one window.
- **The frames are 600 × 400**, with the count, names and timing of the other pictures.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Contour MUST have an optional **beat wave**, **off** by default. When it is off, the Contour frames MUST be identical, file for file, to those made before this feature, and the beat MUST NOT be measured.
- **FR-002**: With the beat wave on, for every frame, a **pattern** of the same shape as the frame's grid of values MUST be made: for the grid point at column `x` and row `y` (counted from 0), `distance` is the distance from the geometric center of the grid (the center of a grid of `n` points along an axis is at `(n − 1) ÷ 2`) to the point, `largest` is the larger of the number of columns and the number of rows, and `pattern = (sin(waves × 2π × sqrt(distance ÷ largest)) + 1) ÷ 2`, a number from 0 to 1.
- **FR-003**: The **modifier** of the frame MUST be `1 − pattern × sin(π × k)`, with `k` the frame's position in the local energy peak (0 at the minimum, 1 at the maximum, 0 when no beat is known; the position of feature 024, read in the middle of each frame). The frame's values MUST be multiplied point by point by the modifier before the contour is drawn.
- **FR-004**: At `k = 0` the modifier MUST be 1 everywhere, so the frame is exactly the plain contour frame; at `k = 1` it is 1 to within rounding (`sin(π)` is not exactly 0), and the modifier at `k` and at `1 − k` are the same.
- **FR-005**: The **wave count** MUST be a whole number from **2 to 10**, default **4**, checked for every image type before any work is done (message: `The wave count must be a whole number from 2 to 10.`), used only by Contour with the beat wave on, and echoed in the response.
- **FR-006**: The Local peaks settings (**minimum distance** and **prominence**) MUST be available for Contour with the checks and messages of the measurement, checked before any work is done; the beat MUST be measured for a Contour job only when the beat wave is on.
- **FR-007**: The beat wave is switched by the request field that turns the beat coloring on or off for Tiles and Blended tiles (`beat_coloring`), which for Contour means the beat wave; for the other image types nothing changes.
- **FR-008**: The color scale of a frame (the colormap from 0 to the frame's largest value) MUST be that of the values **before** the wave; a frame with no contour to draw (all values equal, or a silent file) MUST be written as one flat color as today, whatever the position in the beat.
- **FR-009**: The page MUST show the **Local peaks** group (checkbox and the two sliders) for Contour, after the group of the type, and the **Wave count** slider (2 to 10, default 4) in the Contour group; the result summary MUST show Beat coloring for Contour, and Minimum distance, Prominence and Wave count when it is on.
- **FR-010**: The frames MUST be 600 × 400, with the frame count, names, timing and interpolation behavior of the other image types; the same file and settings MUST give the same frames; the other six image types MUST be identical, file for file, to those made before this feature (the reference hashes).
- **FR-011**: Creating the frames of a 60 second file at 30 frames a second with the beat wave on MUST NOT take more than a few seconds longer than for the plain Contour.
- **FR-012**: The documentation MUST describe the beat wave, its formula, its settings and its defaults.

### Key Entities *(include if feature involves data)*

- **Pattern**: A grid of numbers from 0 to 1, the shape of the frame's grid of values, a set of concentric rings centered on the grid with `waves` waves across the largest dimension.
- **Modifier**: `1 − pattern × sin(π × k)`, the grid by which the frame's values are multiplied; all 1 at the minimum of the beat, deepest half way up it, and all but exactly 1 again at its maximum.
- **Position in the local peak (`k`)**: A frame's position from 0 to 1 from the local peaks measurement (features 023 and 024).
- **Wave count**: A whole number from 2 to 10, the number of waves of the pattern across the largest dimension.
- **Beat wave**: The optional effect on the Contour picture; the Beat coloring checkbox for Contour.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the beat wave off, the Contour frames of the reference test files are identical, file for file, to those made before this feature, and so are the frames of the other six image types; with it on, the frames at position 0 are identical to the plain Contour frames.
- **SC-002**: For every grid size (the original 7 × 12 and every oversampling), every wave count from 2 to 10 and every position `k` in steps of 0.1, the grid values handed to the drawing equal the plain values times `1 − pattern × sin(π × k)` to within rounding, with the pattern as in FR-002 (a number from 0 to 1 that is 0.5 at the exact center of an odd-sized grid, where the distance is 0).
- **SC-003**: In a file with a clear pulse, the Contour frames show rings that grow more pronounced from the lowest point of the beat to half way up it and fade again towards the top: the difference between the frame and the plain frame increases with `k` up to 0.5, decreases after it, and is exactly 0 at the minimum.
- **SC-004**: A silent file, a file without a beat and a file shorter than the peaks window make Contour frames with the wave on without failing, identical to those made with it off.
- **SC-005**: A wave count outside 2 to 10 or not whole is refused 100% of the time before the file is read, with the message naming the range.
- **SC-006**: A 60 second file at 30 frames a second makes its Contour frames with the beat wave on in no more than a few seconds more than the plain Contour frames of the same file on the development machine.

## Assumptions

- **`k` is the position in the local peak**: the description calls `k` "the distance from the next maximum" but also says the effect must be nothing at the minimum and grow as the beat rises, so `k` is the position of feature 024 (0 at the minimum, 1 at the maximum). Since the revision of 2026-10-30 the modifier uses `sin(π × k)`, so the effect is strongest half way up the beat and is nothing again at the maximum.
- **The pattern is applied to the grid the contour is drawn from**: the 12 × 7 grid at oversampling 1, or the finer grid of values at a higher oversampling, after the threshold has hidden notes and before the frame is drawn; `x` and `y` are the column and row of the grid point, so the center is the middle of the grid (the same place in the picture at every oversampling).
- **Distance is in grid points**, as written (`sqrt(x² + y²)` with the origin moved to the center), and `maxdim` is the larger of the number of columns and the number of rows (12 for the original grid).
- **The pattern's center value**: at distance 0 the sine is 0, so the pattern there is 0.5 after the rescaling (the center is half way between the rings' dark and light), not 0 or 1.
- **Wave count is a whole number** (the description says "between 2 and 10"); whole numbers make the pattern end at the same phase it starts and are what a slider offers. The default of 4 is a reasonable middle.
- **The checkbox is the existing Beat coloring one**: for Contour it turns on the beat wave. It is off by default, as for the tiles. The Local peaks measurement and its two settings are those of feature 023.
- **The color scale keeps the unmodified maximum**: the colormap runs from 0 to the largest value of the frame before the wave, so the wave dims points visibly; scaling by the modified maximum would hide the effect.
- **The other contour behavior is unchanged**: the levels, the smoothing of the grid, the axis decorations, the flat frame for a frame with nothing to draw, Interpolate and Gaussian smoothing all work as today.
