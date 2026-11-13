# Feature Specification: Chromatic Wireframe

**Feature Branch**: `039-chromatic-wireframe` (no git branch created; spec directory name only)

**Created**: 2026-11-11

**Status**: Draft

**Revised 2026-11-12 (one function across the width, each letter with its own frequency; both chosen by the user)**: the 12 letters are **no longer 12 separate pieces with a jump at the start of each**, and the formula of the angle is no longer the one given in the input below. **Every letter adds its own sine to every point of the line**, so the line is one smooth function, and the 12 sines have **different frequencies, phases and amplitudes** and interfere: the height at a point `u` pixels from the left of the plot is `A / 12 x` the sum over the 12 letters of (the radius of the letter's circle as a share of the full radius) `x sin(2 pi x (p / 16) x u / width of the plot + 2 pi x start / width of the plot)`, where `p` is the letter's points, `start = b x xmax` is where the letter's share begins (`xmax` the width of the plot divided by 12, `b` from 0 for A) and `A` the highest swing, a fifth of the picture's height. So: **the frequency comes from the points** (`p / 16` turns across the whole width: none at 0 points and **4 at a fully charged letter**, 64 points; the user changed the denominator to a quarter of the maximum points for this), **the amplitude is the radius of the circle**, and **the phase is that of the start: 2 pi times its share of the axis, so a letter a quarter of the way along adds pi/2**. The sum is divided by 12 so that 12 full circles in phase give exactly `A` and the line never leaves the picture (my choice; the user did not say). The letters interfere, constructively and destructively, **in a way that need not mean anything musically, which the user said is fine**. Consequences: a letter with no points is a constant, so **a silent frame, and a frame in which all 12 letters have the same points, is a flat line** (equal frequencies, equal amplitudes, phases spread round the circle: they sum to nothing); the line only has shape where letters differ. Wherever the text below speaks of bands, joints, jumps, a letter's own piece of the line or the angle `(p x 2 pi + x) / (64 + xmax)`, read this.

**Revised 2026-11-12 (third change: sine squared, and the room used; the first by the user, the second asked for by the user, the numbers mine)**: the wave of a letter is now the **sine squared** of its angle (the user's change: the letters can only add to each other, never cancel; a letter makes two humps for each turn of its angle, so a fully charged letter makes 8 humps across the width), which halved the waves and made them never negative. So that the plot uses the picture: (1) **the base of the front line is at the bottom margin** (`height - 10`), not `A` above it, since a line is never below its base; (2) the number of lines is as many as fill the picture **up to the top margin**: `N = floor((base - 10 - 0.75 A) / step) + 1` (66 on 600 x 400, step 4 pixels; the oldest line is at 75 % of the size, hence `0.75 A`); (3) the highest height `A` is now **two fifths of the picture's height** (160 pixels on 400); (4) the sum of the 12 waves divided by 12 (`S`, 0 to 1) is **stretched**: `height = A x clip((S - 0.05) / (0.8 - 0.05), 0, 1)` (`FLOOR_SHARE`, `CEILING_SHARE`), because real music only reaches `S` of about 0.28 to 0.78 (measured on four files), so without the stretch the tallest waves leave a fifth of the room unused; the floor is low (0.05) so that one steady note, which makes `S` of 0.04 to 0.12, is not flattened. The floor of loud music (`S` about 0.28: the means of its waves add up) stays: louder music rides higher above the base, so some room is still left at the bottom of the picture for it. Everything else above holds; where the text says `A / 12 x` the sum, read the stretch, and where it says a fifth of the picture, read two fifths.

**Input**: User description: "create a new image type that uses information from chromatic decay with the in a 3d wireframe plot.  The 12 notes are spread evenly over the x axis.  The amplitude on the Z axis will be the radius of the circle * the sin function.  The y index will scroll historical data for as far as there's room, one line for each fft window.  The angle for sin at each note will be (points*2pi + x)/(64 + xmax), x being the index into the x axis from the start of the note, xmax being the full width of the note.  The index into the colormap for the whole function is determined by place in the beat, with the peak being the max index and the low point being the 0 index.  The color applies to the whole x-z function line, colors will differ between points on the y axis."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A 3D ridge plot of the twelve letters, one line per frame (Priority: P1)

The user wants another image type, **Chromatic Wireframe** (request value `chromatic-wireframe`), that shows the **same information as Chromatic Decay** (feature 035: the 12 letters, each with the points it has in a frame, 0 to 64, and the size its circle has for those points) as a **wireframe plot in three dimensions** instead of a ring of circles.

- **The data**: Chromatic Decay is run exactly as it is (letter energies, the five loudest letters gaining, decay to the letters 5 and 7 above, the decay rate of 1 to 10 whole frames, the threshold of feature 037). Nothing about how points are gained, lost or limited changes; this type only draws them differently. In each frame the plot needs, for each of the 12 letters, its **points** and the **radius its circle has** in Chromatic Decay for those points (one twelfth of the full radius at 0 points, the full radius from 24 points).
- **The x axis (across the picture)**: the **12 letters are spread evenly over the width**, each in a band of equal width, `xmax` pixels (the width of the plot divided by 12), side by side in the order of the letters (see Assumptions). `x` is the position in pixels from the start of a letter's band, from 0 to `xmax`.
- **The z axis (up)**: the height of the line above its base at position `x` in the band of a letter is **the radius of that letter's circle multiplied by the sine of an angle** (the angle is given in the clarification below: `(p × 2π + x) / (64 + xmax)`). A letter with 0 points has the radius of a point at 0 points (one twelfth of the full radius), so a silent letter has a small ripple, not a flat line, as the circle of Chromatic Decay is small, not absent, at 0 points.
- **One line, one function** (revised 2026-11-12, see the note at the top): the sum of the 12 letters' sines over the whole width is **one smooth line** (the x–z function of that frame), with no jump where a letter starts.
- **The y axis (depth)**: the picture shows **one such line for each frame (each fft window)**, the **current frame at the front (bottom) and older frames behind it**, each older line placed a fixed step further back (higher in the picture and, with the 3D view, further away), for **as many frames as there is room**: lines that would fall outside the picture are not drawn, so the plot **scrolls**, new lines entering at the front and the oldest leaving at the back as the music goes on. At the start of the file, before there are enough frames to fill the room, the older lines simply do not exist yet.
- **Color**: **each line has one color for its whole length** (the whole x–z function of that frame), taken from the colormap by the **place of that frame in the beat**: the local-peak position used by Peak Rings (feature 036), where a frame at a local peak is **the last (highest) index of the colormap** and the lowest point of the beat the **first (0) index**, with the positions between mapped in proportion. Since each line is a different frame, **the lines have different colors along the y axis** as the beat goes by, and a repeating beat shows as repeating bands of color going back through the plot. (This is the opposite way round to Peak Rings, where the peak is the start of the colormap.)

**Why this priority**: This is the whole picture: the lines, their shapes and their colors. Without it there is no new image type.

**Independent Test**: Make a file in which a single note such as C3 is steadily the loudest, with a regular beat. Create Chromatic Wireframe frames after a few seconds: the picture shows a stack of lines going back from the front; every line has the same shape (only C's band is ripply with a larger radius, the others stay small), and the color of the lines changes with the beat from line to line, the lines at local peaks having the last color of the colormap and the lowest points of the beat the first.

**Acceptance Scenarios**:

1. **Given** a frame in which letter `n` has `p` points, **When** its line is drawn, **Then** the line over the band of `n` has a height at every position `x` equal to the radius of its circle for `p` points times the sine of the angle of the clarification below, and the 12 bands are side by side, each `xmax` wide, one line across the whole picture.
2. **Given** a file that is longer than the room in the picture, **When** the frames are made, **Then** each picture shows the current frame's line at the front and the lines of the previous frames behind it, one line for each frame, up to as many as fit, never more, and the picture of frame `t` shows the same lines as that of frame `t - 1` moved one place back plus the new line in front.
3. **Given** a frame at the very start of the file, **When** it is drawn, **Then** only the lines of the frames that exist so far are drawn (a first frame has one line), without failing.
4. **Given** a frame that is at a local peak of the beat and another at its lowest point, **When** their lines are drawn, **Then** the first has the last color of the colormap and the second the first color, and each line has a single color over its whole length.
5. **Given** two lines of different frames in the same picture with different positions in the beat, **When** they are drawn, **Then** their colors differ.
6. **Given** the same file and settings, **When** it is made twice, **Then** the images are identical.
7. **Given** a letter with 0 points in every frame of a file with no sound, **When** frames are made, **Then** the lines are all the same small ripple and nothing fails.

**Clarified 2026-11-11 (the formula for the angle, chosen by the user)**: the angle of the sine for a position `x` in the band of a letter with `p` points is **exactly as written, `(p × 2π + x) / (64 + xmax)`** (`x` added, not multiplied). Over a band the angle therefore changes by only `xmax / (64 + xmax)` (under half a radian at the usual size): each band shows a short slice of a sine whose **starting phase is set by the points**, and the radius sets its height. How ripply a band is does not depend on the points, only where in the sine it starts. (The product form `(p × 2π × x) / (64 + xmax)`, in which the points would set the number of waves, was offered and **not** chosen.)

---

### User Story 2 - The depth, the view and the look of the lines (Priority: P2)

The plot is a **3D wireframe**: lines only, no filled surfaces, drawn on a **black** background (changed by the user, 2026-11-12, from the middle color of the colormap that the other types use) and seen from the front and slightly above, so the older lines are further back and higher in the picture.

- **The view is fixed** (no rotation by the user in this feature): a fixed oblique projection in which the same step in `y` moves a line up the picture by the same number of pixels, and the lines further back are slightly smaller, so that the plot reads as three-dimensional. How many lines fit follows from the picture's height and that step.
- **Lines nearer to the viewer hide the lines behind them** where they overlap: the area below each line, down to the picture's bottom, is filled with the background color before the line is drawn, so that the picture reads as a landscape of ridges and a peak in front is not crossed by the lines behind it. The lines are drawn from the back to the front.
- **Line width and look**: lines are thin (about 1 to 2 pixels at the usual size), smooth, with no marks at the points, and fit the picture's width with a small margin on each side; a large radius never takes a line out of the picture: the amplitude is scaled so that the **largest possible radius (a full circle) rises no more than about a fifth of the picture's height** above its base line.
- Frame sizes other than the usual one scale the picture (width, height, steps, line width and amplitude) as for the other image types.

**Why this priority**: The data is shown by Story 1; this story makes it read as a 3D picture and keeps it legible.

**Independent Test**: Make frames at 600 x 400 and at another size: the plot fills the width with a margin, the front line is near the bottom, lines get closer together and slightly smaller going back, a front line hides what is behind it, and no line leaves the picture.

**Acceptance Scenarios**:

1. **Given** a picture, **When** it is drawn, **Then** the front line is at the front (bottom), each older line is the same fixed step further back (higher), and older lines are drawn first so that nearer lines cover them where they overlap.
2. **Given** letters with the largest radius (24 or more points), **When** the lines are drawn, **Then** every line stays inside the picture and no more than about a fifth of the picture's height above its own base line.
3. **Given** a frame size other than 600 x 400, **When** frames are made, **Then** the plot fills the picture in the same proportions.

---

### User Story 3 - Choosing it and the settings that go with it (Priority: P3)

Chromatic Wireframe is chosen from the image type setting, with the label **Chromatic Wireframe**. Because it is Chromatic Decay drawn differently, it takes **the same settings as Chromatic Decay**: the colormap, the analysis settings, the **Threshold** (feature 037), the **local peaks** settings (they decide the beat both for the points the five loudest letters gain and for the color of the lines), the **data smoothing**, and the **decay rate as a whole number from 1 to 10** (default 1, anything else refused with a message before the file is read). The **Note layout** and the four decay amounts of Decay do not apply (accepted and ignored), as for Chromatic Decay. The frames have the usual size, count, names and timing, and can be made into a movie (feature 029).

**Why this priority**: It is the frame around the picture, and it follows the pattern of the other types.

**Independent Test**: Choose Chromatic Wireframe on the page: the Chromatic Decay group of settings is shown (decay rate 1 to 10, threshold, local peaks, smoothing), no note layout; make frames and a movie.

**Acceptance Scenarios**:

1. **Given** the image type setting, **When** the user opens it, **Then** Chromatic Wireframe is among the choices and, when chosen, the page shows the same settings as Chromatic Decay.
2. **Given** a request with `image_type=chromatic-wireframe` and a decay rate that is not a whole number from 1 to 10, **When** it is sent, **Then** it is refused with a message that says so, before the file is read and without leaving files behind.
3. **Given** the same file and settings in Chromatic Decay and in Chromatic Wireframe, **When** frames are made, **Then** the letters' points in every frame are the same in both (only the drawing differs).
4. **Given** the other image types, **When** frames are made, **Then** they are exactly what they were before this feature.

---

### Edge Cases

- The first frames of a file have fewer lines than the room allows; a first frame has a single line at the front.
- A file shorter than the room in the picture never fills it; a very long file only keeps the most recent lines.
- Before the first local peak is found there is no beat: the position in the beat is "far from a peak" (as in Peak Rings, feature 036), so those lines have the first color of the colormap.
- A frame with no sound: the points keep decaying (as in Chromatic Decay) and lines get the small ripple of letters with 0 points; nothing fails.
- The line is one continuous function: there is no jump where a letter's share starts (revised 2026-11-12). A silent frame, and a frame whose 12 letters all have the same points, is a flat line (the sines cancel); the line has shape where the letters' points differ.
- A letter at the end of the line (the last band) ends at the right margin; there is no 13th band.
- Colormaps in which the first and last colors are close to the background make some lines faint, as with the other types; no correction is made.
- Frame sizes other than the usual one scale the picture as for the other types.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST offer a new image type, **Chromatic Wireframe** (`chromatic-wireframe`), chosen the same way as the other types, producing one picture per frame, a plot of lines in an oblique 3D view.
- **FR-002**: The letters' points, their gains, decay, limits and the decay rate MUST be exactly those of Chromatic Decay (features 035 and 037), and this type MUST NOT change them; only the drawing differs.
- **FR-003**: The 12 letters MUST be spread **evenly over the width of the plot**, each with a share of equal width `xmax`, in the order of the letters; the letter `b` starts at `start = b x xmax`.
- **FR-004**: The height of a line above its base at the point `u` MUST be `A x clip((S - 0.05) / (0.8 - 0.05), 0, 1)` where `S` is `1 / 12 x` the **sum over the 12 letters** of the radius of the letter's circle (as in Chromatic Decay, for its points in that frame, as a share of the full radius) times `sin(2 pi x (p / 16) x u / width of the plot + 2 pi x start / width of the plot)` **squared**, `A` being two fifths of the picture's height: each letter's wave has its own **frequency** (`p / 16` turns of the angle across the width, from its points), **amplitude** (the radius share) and **phase** (that of its start); a letter with 0 points has the radius of a circle with 0 points.
- **FR-005**: The line of a frame MUST be one continuous function across the whole picture (no jump at the start of a letter), so that its height never changes by more than `A / 12 x` (the sum of the radius shares) `/ (64 + xmax)` a pixel.
- **FR-006**: The picture MUST show **one line for each frame**, the current frame in front and each older frame one fixed step further back, for **as many frames as there is room** in the picture, scrolling as the file goes on; frames that do not exist yet (the start of the file) MUST NOT be drawn.
- **FR-007**: Each line MUST be drawn in **one color over its whole length**, taken from the colormap by the position of its frame in the beat: **the last index of the colormap at a local peak and the first index at the lowest point of the beat**, in proportion between; the lines of different frames MUST therefore be able to have different colors.
- **FR-008**: Before the first local peak is found, the position in the beat MUST be "far from a peak" (the first color), as for Peak Rings.
- **FR-009**: The view MUST be a fixed oblique 3D projection in which older lines are further back (higher in the picture, slightly smaller), lines are drawn from the back to the front, and a nearer line MUST cover the lines behind it where they overlap (the area below each line filled with the background color).
- **FR-010**: No line MAY leave the picture: a line is between its base and `A` above it, the base of the front line MUST be at the bottom margin, and the number of lines MUST be as many as keep the highest height of the oldest line inside the top margin (so that the stack fills the picture), with a small margin at the left and right.
- **FR-011**: The Chromatic Decay settings MUST apply (colormap, analysis settings, Threshold, local peaks, data smoothing and the whole-number decay rate 1 to 10, default 1, refused otherwise before the file is read); the Note layout and the four decay amounts MUST be accepted and ignored.
- **FR-012**: Results MUST be repeatable: the same file and settings MUST give identical images.
- **FR-013**: The frames of this type MUST be usable for making a movie (feature 029) as the frames of the other types are, and the other image types (including Chromatic Decay and its rings) MUST be unchanged.

### Key Entities

- **Letter share**: the part of the width given to one of the 12 letters, `xmax` wide, starting at `start`; it sets the phase of the letter's sine (and where its `x` is 0), not a piece of the line.
- **Letter sine**: the radius of the letter's circle times the sine of its angle, over the whole width.
- **Frame line**: the sum of the 12 letter sines (times `A / 12`) over the whole width, one line, with one color from the beat.
- **History**: the frame lines of the current and previous frames that fit in the picture, the current one in front.
- **Position in the beat**: the local-peak position of a frame, 1 at a peak and 0 at the lowest point, used as the colormap index.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For any frame, the points and radii used for the 12 bands are identical to those of Chromatic Decay for the same file and settings, in 100% of the frames tested.
- **SC-002**: In a picture with room for `N` lines and at least `N` frames of history, exactly `N` lines are visible, one for each of the latest `N` frames; in a picture at the start of a file, exactly as many lines as frames so far.
- **SC-003**: In every picture, every line has one single color, a frame at a local peak has the last color of the colormap, a frame at the lowest point of the beat has the first, and lines of frames with different beat positions have different colors.
- **SC-004**: No pixel of any line lies outside the picture for any file, setting or frame size tried, and the height of any line above its base never exceeds about a fifth of the picture's height.
- **SC-005**: The same file and settings give identical images, and the frames of the other eleven image types are identical to what they were before this feature.
- **SC-006**: A user can choose Chromatic Wireframe, make frames and a movie of a three-minute file with no step beyond choosing the type, in about the time Chromatic Decay needs.

## Assumptions

- **Name**: the user did not name the type; "Chromatic Wireframe" (`chromatic-wireframe`) is my choice. It is the 13th type.
- **Order of the letters on the x axis**: the user said only that "the 12 notes are spread evenly". The letters are in **chromatic order counted from A** (A, A#, B, C, C#, D, D#, E, F, F#, G, G#), the order the application uses for letters elsewhere, **not** the circle-of-fifths order of the ring of Chromatic Decay. If the fifths order is wanted (so that the two letters a note decays to are its neighbours in the plot) it is a one-line change.
- **"The radius of the circle"** is the radius the circle of that letter has in Chromatic Decay for its points in the frame (one twelfth of the full radius at 0 points, the full radius from 24 points), **scaled** so that the full radius gives the largest amplitude of about a fifth of the picture's height.
- **"Points" in the angle** are the letter's points in that frame, 0 to 64; the 64 in the denominator is the maximum of the points.
- **"One line for each fft window"** is read as **one line for each frame** of the output (each frame is one window position), as the history of Peak Rings counts frames.
- **Position in the beat** is the local-peak position that Peak Rings uses (feature 036): 1 at a local peak, 0 at the farthest point from one, between linearly; this type maps it straight to the colormap index (peak = last), the reverse of Peak Rings.
- **The 3D view, the line step, line width, the fifth-of-the-height limit, the margins and the hiding of lines behind** are my defaults, since the user did not state them; they are the first things to change if the picture looks wrong.
- **Hidden lines**: the user said "wireframe", which can mean see-through lines; I chose to hide what is behind a nearer line because the lines of up to a hundred frames would otherwise cross and the picture would be unreadable. Changing this is a small change in the drawing.
- The view is fixed; no rotation, zoom or other interactive control is part of this feature.
- Depends on Chromatic Decay (035), its Threshold (037), Peak Rings (036) for the beat position, the local peaks analysis, the colormaps, the frame/movie pipeline (029) and the image type setting of the page.
