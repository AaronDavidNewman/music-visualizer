# Feature Specification: Polychord

**Feature Branch**: `042-polychord` (no git branch created; spec directory name only)

**Created**: 2026-11-15

**Status**: Draft

**Input**: User description: "create a new image type called polychord.  Parameters are: the number of notes, from 5-8, min and max number of segments, rotation in degrees/second.   use LineCollection to create line segments.  The first line segment is from the center, for the loudest note.  Then rotate a number of degrees based on where the second strongest tone fits in the circle of 5ths.  So a 4th or a 5th away would be -30 degrees or +30 degrees.  The same chromatic note is straight, a tritone away goes backwards.  Each segment goes from the end of the previous segment.  Each segment should have a smaller ending width than starting width, and that ending width is the starting width of the next segment.  After 5-8 segments have been drawn, rotate 30 degrees and draw the same segment between min and max times, depending on where in the current peak you are.  The color of each segment will be based on the tempo, starting in the center.  The color gets toward 0 as the tempo gets slower and towards the end as it gets faster.  Every frame, start the next figure at an angle offset by the rotation in degrees/second.  The background color should be black/transparent."

**How the user's words are read** (the terms used in the rest of this document):

- A **link** is one straight line piece, which the user calls a "segment" when it is part of the chain. The user uses "segment" for two things; here they are two words.
- A **chord figure** (or just *figure*) is a chain of **links**, one for each of the loudest notes of the frame: "After 5-8 segments have been drawn" is the end of one figure. The number of links in a figure is the **number of notes**, 5 to 8.
- The figure is then **repeated**, each copy turned a further 30 degrees from the one before, "between min and max times": the **number of copies** is the user's "min and max number of segments", which in this document is **Copies (minimum)** and **Copies (maximum)**. (This is the reading that makes the three parameters different from each other: notes 5 to 8 is the size of one figure, and min and max is how many copies of it make the picture.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A figure drawn from the loudest notes, turning by the circle of fifths (Priority: P1)

The user wants another image type, **Polychord** (request value `polychord`), in which the music of each frame is drawn as a **chain of straight links that starts at the center of the picture** and bends according to how the loudest notes of the frame are related to each other in the **circle of fifths** (the twelve letters C, G, D, A, E, B, F#, C#, G#, D#, A#, F, one step being a fifth, as in Chromatic Decay, feature 035).

- **The notes**: in each frame the **loudest notes** are taken, as many as the **number of notes** setting (5 to 8, see Story 3), in order from the loudest to the quietest. Each note is reduced to its **letter** (its chromatic tone, whatever its octave), so that two of the loudest notes can be the same letter in different octaves.
- **The first link** starts at the **center** of the picture and is for the **loudest** note. Its direction is the figure's **starting angle** (Story 2).
- **Each next link** is for the next loudest note. It **starts at the end of the previous link**, and its direction is the previous link's direction **turned by an angle that depends on where its letter lies from the previous link's letter in the circle of fifths: 30 degrees for every step of a fifth**, a step toward the sharps (a fifth up) being **+30 degrees** and a step toward the flats (a fourth up, a fifth down) being **-30 degrees**:
  - the **same letter** (for example C and the C an octave higher): 0 degrees, the link goes **straight on**;
  - a **fifth or a fourth** away (G or F after C): +30 or -30 degrees;
  - a **whole tone** away (D or A#/Bb after C): +60 or -60 degrees, a minor third away (A or D#/Eb): +90 or -90, and so on, 30 degrees for each step round the circle;
  - the **tritone** (F# after C), six steps away, **goes backwards**: 180 degrees (it is the same turning either way).
- **The look of the links** (the user asked that the links be drawn as line segments of a collection): every link has a **width at its start and a narrower width at its end**, and **the end width of a link is the start width of the next one**, so that the whole figure is a chain that **gets thinner** from the center outward, with no step in width where two links meet.
- **Background**: black.

**Why this priority**: This is the picture's core: the chain, how it bends, and how it thins. Without it there is no new image type.

**Independent Test**: Make a file in which the notes C, G and D (in that order of loudness) sound steadily, and look at the first links of a frame: the first link points to the starting angle, the second is turned 30 degrees to the plus side (G is a fifth above C), the third a further 30 degrees (D is a fifth above G); with C, F# the second link goes back along the first.

**Acceptance Scenarios**:

1. **Given** a frame whose loudest note is C, **When** the figure is drawn, **Then** the first link starts at the center of the picture.
2. **Given** a frame whose second loudest note has the same letter as the loudest (one octave up), **When** the figure is drawn, **Then** the second link continues in the same direction as the first.
3. **Given** a frame whose second loudest note is a fifth above the loudest (C then G), **When** it is drawn, **Then** the second link is turned +30 degrees from the first; **given** a fourth above (C then F), **then** -30 degrees.
4. **Given** a frame whose second loudest note is a tritone from the loudest (C then F#), **When** it is drawn, **Then** the second link goes back the way the first came (turned 180 degrees).
5. **Given** a third and later notes, **When** the figure is drawn, **Then** each link's turn is measured from the **previous link's letter** (not from the loudest) and is added to the previous link's direction, and each link starts where the previous one ended.
6. **Given** any figure, **When** its links are looked at in order from the center, **Then** each link ends narrower than it starts and starts exactly as wide as the previous one ends.
7. **Given** the same file and settings, **When** it is made twice, **Then** the images are identical.

---

### User Story 2 - Copies turned 30 degrees, a number set by the beat, and a figure that turns over time (Priority: P2)

The figure of Story 1 is not drawn once but as a **rosette**, and the rosette moves.

- **Copies**: after the links of one figure are drawn, the **same figure is drawn again, turned 30 degrees** from the one before, around the **same center**, and again, **between Copies (minimum) and Copies (maximum) times in all**. How many copies a frame gets depends on **where the frame is in the current local energy peak** (the beat position of Peak Rings and Chromatic Wireframe, features 036 and 039, found by the local peaks): **at the top of a peak the figure is drawn Copies (maximum) times and at the lowest point of the beat Copies (minimum) times**, in proportion in between (rounded to a whole number). So the rosette **opens up with each beat and closes between beats**. Before the first local peak is found there is no beat: the frame gets Copies (minimum).
- **The starting angle**: the first copy of a frame starts at an angle that **moves every frame by the rotation setting, in degrees a second**: the starting angle of frame `t` is `rotation x t` degrees, `t` being the time of the frame in seconds, so a positive rotation turns the whole picture one way, a negative one turns it the other way, and 0 holds it still. Each later copy is 30 degrees further than the one before it.
- **Color** (clarified 2026-11-15, option A chosen by the user): the **colormap** of the job is used, and the **tempo** (the current tempo of the tempo finder, feature 040, from 60 to 156 beats a minute, 120 before the second peak) chooses where in it the color is taken from: **the slower the tempo the nearer the start (index 0) of the colormap, and the faster the nearer its end**. **Every link of a frame has the same color**, the one at the current tempo's place in the colormap (60 beats a minute = the first color, 156 = the last), so the whole rosette changes color as the tempo changes and does not differ from the center to the edge. (The two other readings that were offered, a color that steps along the colormap from the center outward and a color that shows earlier tempos outward from the center, were **not** chosen.)

**Why this priority**: The first picture of Story 1 is a single chain; the copies, the beat and the turning make it a moving picture that follows the rhythm. It builds on Story 1 and does not change it.

**Independent Test**: Make a file with a regular beat. Frames at the peak of a beat have more copies than the frames at its low points; with a rotation of 30 degrees a second at 10 frames a second the picture of each frame is turned 3 degrees from the previous one; a file with a slow tempo has links nearer the first color of the colormap than a file with a fast tempo.

**Acceptance Scenarios**:

1. **Given** a figure, **When** the picture is drawn with `c` copies, **Then** copy `k` (`k = 0` to `c - 1`) is the figure turned `30 x k` degrees from copy 0, all with the same center.
2. **Given** a frame at the top of a local peak and another at its lowest point, **When** they are drawn, **Then** the first has Copies (maximum) copies and the second Copies (minimum).
3. **Given** a frame between the two, **When** it is drawn, **Then** its number of copies is between the minimum and the maximum, in proportion to its place in the peak, rounded to a whole number.
4. **Given** frames before the first local peak, **When** they are drawn, **Then** each has Copies (minimum) copies and nothing fails.
5. **Given** a rotation of `r` degrees a second and a frame rate of `f` frames a second, **When** two consecutive frames are drawn, **Then** the starting angle of the second is the first's plus `r / f` degrees; with `r = 0` every frame has the same starting angle.
6. **Given** the same settings and a slow tempo and a fast tempo, **When** frames are drawn, **Then** all the links of the slow one have a color nearer the start of the colormap and all those of the fast one a color nearer its end; **and given** one frame, **then** all its links (every copy) have the same color.
7. **Given** a frame whose Copies setting would draw more figures than 12 (a full turn), **When** it is requested, **Then** it is refused before the file is read (Story 3), so that no copy ever lies exactly over another.

---

### User Story 3 - Choosing it and the four settings that go with it (Priority: P3)

Polychord is chosen from the image type setting, with the label **Polychord**. It has four settings of its own, each shown only when Polychord is chosen:

| Setting | Meaning | Allowed | Default |
|---|---|---|---|
| **Number of notes** | the number of links in one figure: how many of the loudest notes are used | a whole number from 5 to 8 | 6 |
| **Copies (minimum)** | the number of figures drawn at the lowest point of the beat | a whole number from 1 to 12 | 3 |
| **Copies (maximum)** | the number of figures drawn at the top of a peak | a whole number from 1 to 12, not less than the minimum | 12 |
| **Rotation** | how fast the whole picture turns, in degrees a second (a negative number turns the other way, 0 holds still) | a number from -360 to 360 | 15 |

A value that is not allowed is **refused with a message that says which setting and what is allowed, before the file is read and without leaving files behind**, as for the other image types. The **colormap**, the **analysis settings**, the **local peaks** settings (they decide the beat position and the tempo) and the **data smoothing** apply as they do for the other types; the settings of the other image types (the threshold, the decay rate and amounts, the note layout and so on) are accepted and ignored. The frames have the usual size, count, names and timing, and can be made into a movie (feature 029). The other image types are exactly what they were before.

**Why this priority**: It is the frame around the picture, and it follows the pattern of the other types.

**Independent Test**: Choose Polychord on the page: its four settings are shown with the defaults and the settings of the other image types that do not apply are hidden; send each setting at, below and above its limits and check that only the allowed values are accepted and that a refusal leaves no files; make frames and a movie.

**Acceptance Scenarios**:

1. **Given** the image type setting, **When** the user opens it, **Then** Polychord is among the choices and, when chosen, the page shows Number of notes, Copies (minimum), Copies (maximum) and Rotation, each with its default.
2. **Given** a request with `image_type=polychord` and a number of notes that is not a whole number from 5 to 8, **When** it is sent, **Then** it is refused with a message that says so, before the file is read and without leaving files behind.
3. **Given** a request with a minimum or maximum number of copies that is not a whole number from 1 to 12, or a maximum below the minimum, **When** it is sent, **Then** it is refused in the same way.
4. **Given** a request with a rotation that is not a number from -360 to 360 (including text and not-a-number), **When** it is sent, **Then** it is refused in the same way.
5. **Given** a request without these four settings, **When** it is sent, **Then** the defaults apply.
6. **Given** the other image types, **When** frames are made, **Then** they are exactly what they were before this feature.
7. **Given** a request with `image_type=polychord`, **When** frames are made and then a movie, **Then** both succeed as for the other types.

---

### Edge Cases

- **Fewer sounding notes than the number of notes** (a very quiet frame, or one in which only two notes sound): the figure has as many links as there are sounding notes; a frame with **no sound at all** is a black picture and nothing fails.
- **Ties in loudness** are broken the same way in every run (the lower note first), so that the same file always gives the same picture.
- **A figure that would leave the picture**: a link is 40 percent longer than the room that would just fit a figure of the most links all going straight on (the user's change, after seeing frames that used about half of the picture), so such a figure is cut off at the edge; a figure bends at almost every link, so this is rare, and a long file never makes the figure larger.
- **Copies that overlap**: copies 30 degrees apart overlap near the center, where every figure starts; this is expected, and the later copies are drawn over the earlier ones.
- **A tempo at its limits** (60 or 156) takes the first or the last color of the colormap; a tempo outside that range does not occur (the tempo finder keeps it between 60 and 156).
- **A restart of the tempo** (156 to 78, 60 to 120) changes the colors from one frame to the next: this is the tempo finder's own behavior and is not smoothed here.
- **A rotation of exactly 0** gives a picture that does not turn; **a rotation that makes a whole turn between frames** (for example 360 at 1 frame a second) gives the same angle every frame, which is as asked.
- **Colormaps in which the first or last color is close to black** make some links faint on the black background, as with the other types; no correction is made.
- Frame sizes other than the usual one scale the picture (link lengths, widths) as for the other types.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST offer a new image type, **Polychord** (`polychord`), chosen the same way as the other types, producing one picture per frame on a **black** background (the pictures have no transparency; black is the background).
- **FR-002**: In each frame the system MUST take the **loudest notes** of the frame, as many as the **Number of notes** setting, in order from the loudest, each reduced to its letter, with ties broken the same way in every run; if fewer notes than that are sounding, only those are used, and a frame with no sound MUST be a black picture.
- **FR-003**: The first link of a figure MUST start at the **center** of the picture, for the loudest note; every next link MUST start at the end of the previous link.
- **FR-004**: The direction of every link after the first MUST be the previous link's direction turned by **22.5 degrees for every step of a fifth** (revised from 30, so that the 12 steps make 270 degrees) from the previous link's letter to its own, taking the shorter way round the circle of twelve letters: a fifth up +22.5, a fourth up (a fifth down) -22.5, the same letter 0, a tritone 135; the full table of the twelve intervals is part of the acceptance scenarios and tests.
- **FR-005**: The figure MUST be a chain of links drawn as **line segments of one collection** (the user's instruction: matplotlib's `LineCollection`), each link **narrower at its end than at its start**, with the **end width of a link equal to the start width of the next**, so that the figure thins from the center outward without steps.
- **FR-006**: After the links of a figure the system MUST draw the **same figure again, turned a further 30 degrees from the previous copy, around the same center**, so that the picture holds `c` copies, copy `k` being turned `30 x k` degrees from copy 0.
- **FR-007**: The number of copies `c` MUST be the **Copies (maximum)** at the top of the local peak and the **Copies (minimum)** at the lowest point of the beat, in proportion between (rounded to a whole number); before the first local peak is found it MUST be the Copies (minimum).
- **FR-008**: The starting angle of copy 0 in frame `t` MUST be `Rotation x t` degrees, `t` being the time of the frame in seconds, so that it changes between consecutive frames by `Rotation / frame rate`.
- **FR-009**: The color of the links MUST be taken from the job's colormap by the **current tempo** (the tempo finder's tempo for the frame, 60 to 156 beats a minute): **the slowest tempo takes the first color and the fastest the last color**, in proportion between; **all the links of a frame, in every copy, have that one color**.
- **FR-010**: The system MUST offer the settings **Number of notes** (whole number 5 to 8, default 6), **Copies (minimum)** (whole number 1 to 12, default 3), **Copies (maximum)** (whole number 1 to 12, not less than the minimum, default 12) and **Rotation** (number from -360 to 360 degrees a second, default 15), shown on the page only when Polychord is chosen; a value that is not allowed MUST be refused with a message that says so, before the file is read and without leaving files behind.
- **FR-011**: The colormap, analysis settings, local peaks settings and data smoothing MUST apply as for the other types; the settings that belong to other image types MUST be accepted and ignored.
- **FR-012**: The picture MUST use the frame well: the length of a link MUST be 1.4 times the length that would just fit the longest possible figure (all links going straight on) inside the picture, at any frame size (a figure that goes straight on is cut off at the edge), and the lengths and widths MUST scale with the frame size.
- **FR-013**: Results MUST be repeatable: the same file and settings MUST give identical images.
- **FR-014**: The frames of this type MUST be usable for making a movie (feature 029) as the frames of the other types are, and the other image types MUST be unchanged.

### Key Entities

- **Link**: one straight piece of a figure, for one of the loudest notes of a frame: a start point, a direction, a length and a start and an end width.
- **Figure (chord figure)**: the chain of links of one frame, the first from the center for the loudest note; it has as many links as the number of notes (or fewer, if fewer notes sound).
- **Copy**: the figure turned a multiple of 30 degrees around the center; the picture holds between Copies (minimum) and Copies (maximum) of them.
- **Turn**: the change of direction from one link to the next, 22.5 degrees for every step of a fifth between their letters (revised from 30: see the revision note at the end), from -112.5 to +135 degrees.
- **Starting angle**: the direction of the first link of copy 0, which moves with the Rotation setting and the time of the frame.
- **Beat position**: the place of the frame in the local energy peak, 1 at a peak and 0 at the lowest point, which sets the number of copies.
- **Current tempo**: the tempo finder's tempo for the frame, 60 to 156 beats a minute, which sets the color.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For all 12 intervals between two letters, the turn between the second and the first link is the one the table of Story 1 gives, with 22.5 degrees for a step instead of 30 (-112.5 to +135 degrees in steps of 22.5), in 100 % of the checked cases.
- **SC-002**: In a picture, every link starts exactly where the previous one ends and is exactly as wide at its start as the previous one is at its end, in 100 % of the checked figures.
- **SC-003**: On a file with a regular beat, frames at the top of a peak have the maximum number of copies and frames at the lowest point have the minimum, in at least 95 % of the checked beats.
- **SC-004**: With a rotation `r` and a frame rate `f`, the starting angle of consecutive frames differs by `r / f` degrees (to within a hundredth of a degree), for any `r` from -360 to 360.
- **SC-005**: Every value of the four settings outside its limits is refused before the file is read with a message that names the setting, and leaves no files behind, in 100 % of the checked cases; every value inside the limits is accepted.
- **SC-006**: A figure never leaves the picture: for every frame of the test files, at the usual size and at another size, no link lies outside the picture.
- **SC-007**: Two runs on the same file and settings give identical images, and the pictures of the other image types are identical to those made before this feature, in 100 % of the checked frames.
- **SC-008**: Looking at a slow file and a fast file with the same colormap, a person can tell by color alone which is the faster in at least 9 of 10 pairs.

## Assumptions

- **Notes and letters**: "the notes" are the loudest notes of the frame as the other types measure them (the same selection that Decay uses for its five loudest notes, here as many as the Number of notes setting), reduced to their letter for the circle of fifths. Two of the loudest notes can therefore be the same letter, which is what makes "the same chromatic note is straight" possible.
- **The turn is measured from the previous link's letter**, not from the loudest note, for every link after the second (the user described only the second; extending it note by note is the natural chain). The first link's own direction is the starting angle, and the loudest note's letter does not set an absolute direction.
- **The tritone** turns by 135 degrees (backwards, but not all the way) whichever way it is counted; the other intervals take the shorter way round the circle, so the turns lie from -112.5 to +135 degrees.
- **"Min and max number of segments" is the number of copies of the figure** (see the top of this document), 1 to 12 (12 copies of 30 degrees make a full turn; more would lie exactly over earlier copies). The defaults (3 to 12) are mine.
- **Number of notes** 6, **Rotation** 15 degrees a second, and the widths (the first link starts at about 1/60 of the picture's height and the last ends at about a fifth of that) are mine; the user did not give them.
- **"Where in the current peak"** is the local peak position of features 036 and 039 (1 at a peak, 0 at the lowest point), so that the top of the beat is the most copies. The mapping is proportional and rounded; the user did not give another curve.
- **"The tempo"** is the current tempo of the tempo finder (feature 040), which is always between 60 and 156 beats a minute and 120 before the second peak; the colormap position is `(tempo - 60) / (156 - 60)`.
- **"Black/transparent"**: the frames are pictures with three color channels, as for every other type, so **black** is used; a transparent background would need a four-channel picture, which no other type has and the movie would not keep, so it is left out unless asked for.
- **Link length** is the same for every link of a figure and is 1.4 times the length that would just fit a figure of the most links going straight on inside the picture (the user asked for 40 percent more, because the figures used only about half of the area; the user did not say how long a link is; a length that follows the note's strength is a possible later change, and is not part of this feature).
- **LineCollection**: the user asked for it; it is the drawing means for the links, and is a plan-time decision rather than something the picture shows. The taper (one width at each end of a link) is drawn by cutting each link into short pieces whose widths step down.
- **Scope**: only the new image type, its four settings and their page controls. No other type changes. The documentation standard of feature 041 (types on every function, arrays documented, an `Order of operations:` list in the module, the new type's block in the pipeline overview of `image_types.py`) applies to the new code.
- **Dependencies**: the loudest notes of a frame (the analysis and the data smoothing already done for every type), the local peaks and the tempo finder (features 023, 036, 040), the colormaps (feature 014) and the movie feature (feature 029), and the Chromatic Decay circle of fifths (feature 035).

## Revision note (2026-11-16)

After seeing frames, the user asked for three changes; the story text above keeps the first wording, the numbers in
Functional Requirements, Entities and Success Criteria are the current ones:

- **Links 40 percent longer** (the figures used only about half of the area).
- **Turns limited to 270 degrees**: 22.5 degrees for every step of a fifth instead of 30, so the 12 steps make 270 and
  not 360 (the figure looked squished because the angles were so sharp). I read "limit the angles for each turn to be
  270" as the circle of fifths mapped onto 270 degrees, which keeps the order of the turns and their proportions
  (a tritone is 135 instead of 180). The copies are still 30 degrees apart.
- **Every link squeezed to 2/3 of its width and 1/2 of its height**, because of the aspect ratio of the pictures (3:2):
  the figure, and with it every copy, is an ellipse 4/3 as wide as it is high that follows the shape of the picture. I
  applied it to every link of every copy (the first included), after the copies are turned.
