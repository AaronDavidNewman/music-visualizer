# Feature Specification: Peak Tile Colors

**Feature Branch**: `024-peak-tile-colors` (no git branch created; spec directory name only)

**Created**: 2026-10-27

**Status**: Clarified

**Input**: User description: "for tiles and blended tiles, update the colors of the tiles: 1/2 of the value comes from the harmonic energy as it is coded now, the other 1/2 comes from its place in the local energy peak.  A tile with the maximum energy that would have the right-most color in the colormap, will now  have the middle color if it is at the minimum of the local peak, and the right-most color at the maximum peak."

## Clarifications

### Session 2026-10-27

- Q: What is the "place in the local peak" measured against? -> A: **The local surroundings of the frame**: the interpolated energy of the local peaks measurement at the frame's time, between the smallest and the largest energy that the measurement records for the peaks around it (both interpolated the same way as the energy, between the previous and the next peak), held within 0 and 1.
- Q: How are the settings offered, and can the beat coloring be switched off? -> A: **A group of its own, "Local peaks"**, with a **checkbox that turns the beat coloring on or off** and the two settings of the measurement (minimum distance and prominence). **When it is off, the colors are 100% determined by the harmonic energy**, exactly as before this feature.
- Q: What happens with no beat, and for hidden or silent tiles? -> A: **With no known beat the position in the peak is 0** (the picture then uses only the lower half of the colormap); **every visible tile takes part in the formula, a silent one included**; **tiles that the threshold hides are drawn as before** (black for Tiles, the middle color of the colormap for Blended tiles).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tiles pulse with the beat of the music (Priority: P1)

Today the color of a tile says one thing: **how strong its note is** (the harmonic energy). The user wants the **Tiles** and **Blended tiles** pictures to be able to say a second thing as well (when the **beat coloring** is turned on, Story 2): **where the music is in its beat**, as measured by the local peaks measurement (feature 023: the periodic local maxima of the overall energy). Half of a tile's place on the colormap keeps coming from its note strength, exactly as now; the other half comes from the frame's **place in the local energy peak**: a position from 0 (the minimum of the local peak) to 1 (the maximum of the peak).

So, with the colormap read from its first color (left) to its last color (right):

- a tile whose note has the **maximum energy** (which today has the right-most color) now has the **middle color** when the frame is at the **minimum** of the local peak, and the **right-most color** when the frame is at the **maximum** of the peak;
- in between, its color moves smoothly from the middle to the right-most as the beat rises;
- a weaker tile moves the same way, over a smaller part of the colormap, because its note strength is only half of its place.

In short, with the beat coloring on, the place of a tile on the colormap is **half its note strength plus half the position in the local peak**, each from 0 to 1. The whole picture's brightness follows the **strength of the beats**: the position in the peak is worked out from the measurement's energy, which runs in a straight line from one peak's energy to the next (clarified for feature 023), so it rises and falls from beat to beat, not within a beat: between two equally strong beats it stays high, and it is low where the beats are weak relative to the range of their surroundings, and 0 before the first beat. The notes that are strongest still stand out.

**Why this priority**: This is the whole request. Everything else (the settings that tune the peaks) supports it.

**Independent Test**: Make a file with a steady strong note and a click every half second whose strength changes (a loud click, then a much softer one, then a loud one). Create Tiles frames with the beat coloring on: the tile of the strong note has a color near the right-most one in the frames around the loud clicks and a color nearer the middle in the frames around the soft ones, the colors in between change smoothly along the line from one click's strength to the next, and the frames before the first click have the middle color.

**Acceptance Scenarios**:

1. **Given** the beat coloring is on, a tile whose note has the maximum energy of the file and a frame at the **minimum** of the local peak, **When** the picture is made, **Then** the tile has the **middle color** of the colormap.
2. **Given** the same tile and a frame at the **maximum** of the local peak, **When** the picture is made, **Then** the tile has the **right-most color** of the colormap.
3. **Given** the same tile and a frame half way up the beat, **When** the picture is made, **Then** its color is the one three quarters of the way along the colormap.
4. **Given** a tile whose note energy is lower, **When** the picture is made, **Then** its place on the colormap is half of its note-strength position (as coded now: the square root of its share of the file's largest value) plus half of the frame's position in the local peak, so it is never later on the colormap than a stronger tile of the same frame.
5. **Given** two frames with the same note energies and different positions in the local peak, **When** the pictures are made, **Then** the frame with the higher position has every tile at the same color or later on the colormap, and at least one tile later when any tile can still move.
6. **Given** the **Blended tiles** picture, **When** it is made, **Then** its tiles take the same colors as the Tiles picture and the blending between neighbours works as before.
7. **Given** the **Contour**, **Circles** and **Circles paint** pictures, **When** they are made, **Then** they are identical, file for file, to those made before this feature.
8. **Given** the same file and settings, **When** the pictures are made twice, **Then** the files are identical.

---

### User Story 2 - Turn the beat coloring on, and choose how the beat is found (Priority: P2)

The beat coloring is a **choice**, kept in a settings group of its own, **Local peaks**, shown when the image type is **Tiles** or **Blended tiles** (the only pictures it applies to):

- a **checkbox** that turns the beat coloring **on or off**; it is **off** by default, so nothing changes until the user asks for it;
- **Minimum distance**: the minimum time between two peaks, 100 to 2,000 ms, default 100;
- **Prominence**: how much a bump must stand out, 0 to 100 percent, default 50.

(The two settings are those of the local peaks measurement, feature 023; they decide what counts as a beat. Slow music needs a longer distance, music with a soft pulse a lower prominence.)

**When the checkbox is off, the colors are 100% determined by the harmonic energy**: the frames are exactly those made before this feature, and the beat is not even measured. When it is on, the colors are half harmonic energy and half position in the local peak (Story 1).

**Why this priority**: Story 1 describes the look; this is how the user gets it, and how they keep the old look.

**Independent Test**: Make Tiles frames of a file with clicks 300 ms apart whose strength varies: with the checkbox off they are identical to the frames made before this feature; with it on and a minimum distance of 100 ms the colors follow the strength of every click; with 2,000 ms they follow only the strongest clicks, at least 2 seconds apart.

**Acceptance Scenarios**:

1. **Given** no value for the checkbox, **When** the pictures are made, **Then** the beat coloring is off and the Tiles and Blended tiles frames are identical, file for file, to those made before this feature.
2. **Given** the checkbox is off, **When** a minimum distance or prominence is given, **Then** they are checked and have no effect on the frames.
3. **Given** the checkbox is on and no other values, **When** the pictures are made, **Then** the minimum distance is 100 ms and the prominence 50.
4. **Given** a minimum distance or prominence that is not allowed, **When** the request is made, **Then** it is refused before any work is done, with the message of the local peaks measurement (whether the checkbox is on or off).
5. **Given** the checkbox is on and a different minimum distance or prominence, **When** the pictures are made, **Then** the beat that colors the tiles is that of the measurement made with those values.
6. **Given** the settings page, **When** the image type is Tiles or Blended tiles, **Then** a collapsible **Local peaks** group with the checkbox and the two settings is shown; for the other image types it is not, and the request still behaves as if the checkbox were off for them.

---

### User Story 3 - Quiet, hidden and beat-less moments look sensible (Priority: P3)

With the beat coloring on, the beat is not always known: before the first peak, in a file with no peaks (silence, or a very even sound). The rules are:

- **With no known beat the position in the peak is 0**: before the first peak, and in every frame of a file with no peaks. The picture then uses only the lower half of the colormap (a tile with the maximum energy has the middle color).
- **After the last peak** the position is that of the last peak's values (held).
- **Every visible tile takes part in the formula**, a tile with no energy at all included: it has half the position in the peak, so at the top of a beat it can reach the middle color.
- **Tiles that the threshold hides are drawn as before**: black for Tiles, the middle color of the colormap for Blended tiles. The beat does not change which tiles are hidden.

**Why this priority**: These are the corners of the feature; the main behavior does not depend on them, but the look of silence and of files without a pulse does.

**Independent Test**: With the beat coloring on, make frames of a silent file, of a file with a steady tone and no beat, and of a file with a threshold that hides some tiles: each makes pictures of the 600 × 400 frame size without failing, the hidden tiles drawn as before, and in the beat-less frames no tile later than the middle color.

**Acceptance Scenarios**:

1. **Given** a file with no local peaks, **When** the pictures are made, **Then** they are made without failing and every frame uses the position 0 in the peak.
2. **Given** a frame before the first peak of the file, **When** the picture is made, **Then** it uses the position 0.
3. **Given** a frame after the last peak, **When** the picture is made, **Then** it uses the position worked out from the last peak's energy and window minimum and maximum.
4. **Given** a tile hidden by the threshold, **When** the picture is made, **Then** it is drawn as before this feature (black for Tiles, the middle color of the colormap for Blended tiles).
5. **Given** a visible tile with no energy at all, **When** the picture is made, **Then** its place on the colormap is half the frame's position in the peak.
6. **Given** a silent file, **When** the pictures are made, **Then** they are made without failing.

---

### Edge Cases

- **The position in the peak, in detail**: it is the interpolated energy of the measurement at the frame's time, minus the interpolated smallest energy of the neighbouring peaks' windows, over the range between that and the interpolated largest energy of those windows, held within 0 and 1. It is 0 before the first peak and for a file with no peaks, and when the smallest and the largest energy are equal (there is no range).
- **Resolution above 1** (a finer grid by interpolation): every tile of a frame uses the frame's single position in the peak; each tile's note-strength half comes from its interpolated value as now.
- **Interpolate above 1** (only every n-th frame drawn): the drawn frames take their colors as above; the frames in between are made from their neighbours as now.
- **Threshold, note count, smoothing windows and frame rate** keep their meaning: they decide which notes are shown and what their strength is. The beat does not change which tiles are hidden.
- **Gaussian smoothing** is applied to the finished colored frame as now.
- **The checkbox off** is not a special look of the new code: the old computation is used as it was, so the frames are identical to those before this feature.
- **Colormaps**: every colormap works the same way; "the middle color" is the one in the middle of its table (the color at row 128 of 256, as used for the Blended tiles background).
- **Very short files** (shorter than the peaks window) are measured as one window.
- **A mono file** has the same beat as its stereo copy.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: For the **Tiles** and **Blended tiles** pictures, **when the beat coloring is on**, the position of a tile on the colormap MUST be **one half of its note-strength position plus one half of the frame's position in the local peak**, where the note-strength position is the one used today (the square root of the tile's value over the file's largest value, from 0 to 1) and the position in the local peak is from 0 to 1. The color is the colormap's table entry at that position, rounded as now (`rint(position × 255)`).
- **FR-002**: The **position in the local peak** of a frame MUST be 0 at the **minimum** of the local peak and 1 at its **maximum**, and MUST be worked out from the local peaks measurement of feature 023 at the frame's time (the interpolated energy between the smallest and largest energy of the neighbouring peaks' windows, as in the clarification), held within 0 and 1.
- **FR-003**: A tile with the maximum note energy MUST therefore have the **middle color** at position 0 of the peak and the **right-most color** at position 1.
- **FR-004**: Every tile of a frame MUST use the frame's one position in the peak. A tile with a lower note strength MUST NOT have a later color than a tile of the same frame with a higher strength.
- **FR-005**: A higher position in the peak MUST NOT give any tile of the frame an earlier color than a lower position does.
- **FR-006**: There MUST be a **beat coloring** setting, a checkbox, **off by default**, and the two settings of the measurement (**minimum distance**, 100 to 2,000 ms, default 100, and **prominence**, 0 to 100 percent, default 50), in a settings group of their own, **Local peaks**, shown for Tiles and Blended tiles. The two settings MUST be checked, with the messages of the measurement, before any work is done, whether the checkbox is on or off. When the checkbox is **off** the colors MUST be 100% determined by the harmonic energy (the frames identical to those made before this feature) and the beat MUST NOT be measured.
- **FR-007**: With the beat coloring on: with no known beat (before the first peak, a file with no peaks) the position in the peak MUST be 0; after the last peak it MUST be worked out from the last peak's values; every visible tile, with no energy at all included, MUST take part in the formula; tiles hidden by the threshold MUST be drawn as before.
- **FR-008**: With the beat coloring off, the Tiles and Blended tiles frames, and always the **Contour**, **Circles** and **Circles paint** pictures, the audio reading, the note analysis and the local peaks measurement itself MUST NOT change; their frames MUST be identical, file for file, to those made before this feature.
- **FR-009**: The frames of Tiles and Blended tiles MUST keep their size (600 × 400), count, names, timing, smoothing, resolution, interpolation and Gaussian smoothing behavior; only the colors of the tiles change.
- **FR-010**: The same file and settings MUST always give the same frames.
- **FR-011**: Making the pictures MUST NOT take noticeably longer: measuring the beat of a 60 second file and coloring its frames MUST add no more than a few seconds to the time to create the frames.
- **FR-012**: The documentation MUST describe how a tile's color is worked out (half note strength, half position in the peak), the checkbox and the settings.

### Key Entities *(include if feature involves data)*

- **Note-strength position**: A tile's position on the colormap from 0 to 1 as coded today: the square root of its value over the largest value of the file.
- **Position in the local peak**: A frame's position from 0 (the minimum of the local peak) to 1 (its maximum), from the local peaks measurement at the frame's time.
- **Tile color position**: Half the note-strength position plus half the position in the local peak; it selects the color in the colormap.
- **Beat coloring setting**: The checkbox (off by default) and the two settings of the measurement, in the Local peaks group.
- **Local peaks measurement**: The existing measurement (feature 023) that supplies the peaks, their energies, the minimum and maximum energy of their windows, and the interpolated energy at any time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a tile with the file's maximum note energy, the color is the colormap's middle color (to within one table step) in every frame at position 0 and the right-most color in every frame at position 1, for every colormap.
- **SC-002**: For every tile and frame of a test file, the color position equals half the note-strength position plus half the frame's position in the peak (to within one table step).
- **SC-003**: Across the frames of a click-track test file with a strong steady note and clicks of varying strength, the strong tile's color position is half its note strength plus half the frame's position in the peak: at the loudest click of its surroundings the position in the peak is at least 0.95, so the tile is at color position 0.975 or more; before the first click the position in the peak is 0, so the strong tile has the middle color; and a click that is weak against the range of its window gives a position in the peak below 0.5.
- **SC-004**: The frames of the Contour, Circles and Circles paint pictures, and those of Tiles and Blended tiles with the beat coloring off (the default), for the reference test files are identical, file for file, to those made before this feature (the reference hashes).
- **SC-005**: With the beat coloring on, the Tiles and Blended tiles pictures of a silent file, a file with no peaks and a file shorter than the peaks window are made without failing.
- **SC-006**: Two runs of the same file and settings give identical frames.
- **SC-007**: With the beat coloring on, creating the frames of a 60 second file takes no more than 5 seconds longer than before this feature; with it off, no longer at all.

## Assumptions

- **"Value" means the place on the colormap, from 0 to 1.** "Half from the harmonic energy as it is coded now" is the current square-root position; the other half is the position in the peak. The two halves are fixed at one half each (they are not a setting).
- **The position in the peak** is as the clarification says: against the local surroundings of the frame (the smallest and largest energy that the measurement records for the neighbouring peaks, interpolated like the energy).
- **A frame's time** is the middle of the interval of the file that the frame covers.
- **The measurement uses the audio of the file** as it is read for the note analysis (left and right channels, the file's sample rate), with the window sizes of the measurement as they are (32 and 4,096).
- **Only Tiles and Blended tiles can change, and only when the beat coloring is on.** The other pictures use the harmonic energy only, as before; the threshold, the note count and the smoothing keep working on the harmonic energy only.
- **The beat coloring is off by default** (the clarification says the colors are 100% harmonic when it is off, and does not say which state is the default; off keeps every existing picture, setting and test as it is). It can be changed to on by default later.
- **The group Local peaks is a group of the settings page like the others** (collapsible, two settings per row, the checkbox first), shown for Tiles and Blended tiles.
- **The position follows beat strength, not the shape of a beat.** The energy of the measurement is a straight line from one peak to the next, so for equal beats the position stays near 1 between them (it does not fall in the gaps); it changes with the strength of the beats relative to the smallest and largest energy of their windows. If a dip between beats is wanted, it needs the measured energy curve and not the peaks' line; that would be a different, later change.
- **The middle color** of a colormap is the table entry at row 128 of 256, as used for the Blended tiles background.
