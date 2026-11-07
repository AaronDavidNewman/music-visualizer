# Feature Specification: Polar Chords

**Feature Branch**: `032-polar-chords` (no git branch created; spec directory name only)

**Created**: 2026-11-06

**Status**: Draft

**Revised 2026-11-06 (third change)**: the note bars **follow their notes**. Every volume (the loudest note, the second loudest, and so on up to Notes shown) keeps its own bar and its own angle. When the note of a volume changes from one frame to the next, the bar does not jump to the new note: it moves **one arc (2π ÷ 84) in a frame**, the shorter way round the circle, toward the arc of the new note, which gives a smoother animation. The chord bar and the lengths do not follow anything. Wherever the text below says that a note bar is in the arc of its note, it means this, once the bar has arrived.

**Revised 2026-11-07 (fourth change)**: the chords name the **root letter** again, and the chord ring is back to **84 arcs**: one for each of the **12 letters** (a letter is a note without its octave, with its accidental: A, A#, B, C, ...) and each of the **7 chord types**, in the order **letter 1, its 7 types, letter 2, its 7 types, and so on**, going counterclockwise from the top. The place of a chord is `7 × letter + type` (0 to 83), each arc `360° ÷ 84 ≈ 4.29°` wide, like a note's. The letter is the root the chord is built on; the octave and the inversion still do not matter. Wherever the text below speaks of 7 places, of the type alone or of the second change, this replaces it.

**Revised 2026-11-06 (second change, replaced by the fourth)**: the chords no longer name the **note** they are built on, only the **chord type**. The chord ring has **7 arcs, one for each chord type**, each `360° ÷ 7 ≈ 51.4°` wide, instead of 84 places (7 types × 12 roots) of 4.29°. The root, the octave and the inversion do not matter any more: a major triad on C and one on F# are the same bar. Wherever the text below speaks of 84 chord places, of `type × 12 + root` or of the root, it means this.

**Revised 2026-11-06** (the user asked for the Note layout): the notes can be arranged **Rows** or **Spiral**, the Note layout setting of the other pictures (feature 026). It says **in which arc each note is**: with Rows (the default, and what the picture was) the arc of a note is its number, in order of pitch; with Spiral the arc of a note is the cell in which the spiral layout draws it (middle C, note 27, is in arc 29, the next note up in arc 30 and the next one down in arc 28). The chords do not change: they are about the real notes. Wherever the text below says that the Note layout does not apply, or that the notes are in order of pitch, it means this.

**Input**: User description: "create a new image type called polar-chords.  It will map musical notes and chords on a polar bar graph.  Clockwise, the 84 notes will be divided into 84 arcs in the circle.  The first 5-8 notes will appear at their specified angle with uniform width, the length will be from 0.5 to max based on local maximum.  the color will be from middle to start of colormap.  In a counterclockwise direction, it will be a polar bar graph with the chord/chords.  It will use the same formula for length and the colors will run from the middle to the end of the color map.  We will look for 7 different types of chords: (7),(4, 7), (3,7),(4,  10), (4,11), (3, 7, 10),(4,6).  The 84 places counterclockwise will be the 7 chords * 12 root notes (the octave isn't used for this)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The loudest notes as bars around a circle, pulsing with the beat (Priority: P1)

The user wants a ninth image type, **Polar Chords** (request value `polar-chords`). It is a **polar bar graph**: bars that start at the center of the picture and reach outward, each at its own angle. This story is the first half of it, the **notes**.

- **The circle is divided into 84 equal arcs, one for each of the 84 piano notes**, going **clockwise from the top** of the picture in the order of the **Note layout**: with **Rows** (the default) in order of pitch, the lowest note (A1) having the first arc, which starts straight up, and the highest the last, which ends straight up again; with **Spiral** each note has the arc numbered like the cell of the 12 × 7 grid in which the spiral layout draws it. Each arc is 360° ÷ 84 ≈ 4.29° wide.
- **Only the loudest notes of a frame get a bar.** The number is a setting, **Notes shown, from 5 to 8** (default 5). The bar of a note sits at the **angle of its arc and fills the whole arc**, so every bar has the **same width**. A note with no strength never gets a bar.
- **Length**: a bar reaches out to between **0.5 and 1** (the maximum) of the full radius of the circle, depending on where the frame is in the **local energy peak** of the music (the beat, features 023 and 024): **0.5 at the bottom of the peak**, **1 at the top**, in a straight line between. All bars of a frame have the same length, so the picture breathes with the beat.
- **Color**: each bar is colored from the **first half of the colormap**, from the **middle** (for a faint note) to the **start** (for the loudest possible note), following the strength of the note in the same way as the other pictures (the square root of the note's strength as a share of the largest value of the whole file).

**Why this priority**: This is the base of the picture; without it there is nothing to add the chords to.

**Independent Test**: Make a file with one steady loud note and a clear pulse. Create Polar Chords frames: there is one bar, at the angle of that note, 4.29° wide, whose tip goes in and out between half the full radius and the full radius with the pulse, in a color from the first half of the colormap.

**Acceptance Scenarios**:

1. **Given** the 84 notes and the Rows layout, **When** the picture is made, **Then** note `k` (0 for A1) has the arc that starts `k × 360 ÷ 84` degrees clockwise from straight up and is `360 ÷ 84` degrees wide; the arcs do not overlap and together fill the circle.
2. **Given** a frame, **When** the picture is made, **Then** a bar is drawn for each of the `N` loudest notes (`N` the Notes shown setting, 5 to 8; ties go to the lower note; a note with no strength gets none), each filling its arc from the center to its length, and no other note has a bar.
3. **Given** a frame at position `p` in the local peak (0 to 1), **When** the picture is made, **Then** every bar of the frame reaches out to `0.5 + 0.5 × p` of the full radius: half way at the bottom of the peak, all the way at the top.
4. **Given** a note bar of strength share `s` (the square root of its strength over the largest value of the file, 0 to 1), **When** the picture is made, **Then** its color is the colormap's color at `0.5 − 0.5 × s` of the way along the scale: the middle color at `s = 0` and the first color at `s = 1`.
5. **Given** the same file and settings, **When** the pictures are made twice, **Then** the files are identical.
6. **Given** the Spiral layout, **When** the picture is made, **Then** the arc of note `k` is the number of the cell in which the spiral draws it (`rows` and `spiral` are the layouts of feature 026): middle C (note 27) has arc 29, the note above it arc 30, the one below it arc 28; every one of the 84 arcs is still used by exactly one note, and the bars of the loudest notes are the same notes, with the same colors and lengths, as with Rows, only in other arcs.
7. **Given** a note layout that is not offered, **When** a request is made, **Then** it is refused before any work is done with the message of the other pictures (`The note layout must be one of rows, spiral.`); when it is left out, Rows is used.
8. **Given** either layout, **When** the chord is drawn, **Then** it is at the same place: the chords do not depend on the layout, and the ties between equally loud notes still go to the lower note, not the lower arc.
9. **Given** the first frame, or a volume that has a note after a frame with none, **When** the picture is made, **Then** its bar is in the arc of its note.
10. **Given** a bar in arc 10 and a frame in which the note of its volume is in arc 20, **When** the pictures are made, **Then** the bar is in arc 11 in that frame, in arc 12 in the next, and so on, one arc a frame, until it is in arc 20, where it stays; with the note in arc 0 or 83 the bar goes round the top the shorter way (from arc 1 to 83 it goes 0, 83), and with a note exactly on the other side of the circle (42 arcs away) it goes clockwise.
11. **Given** a bar on its way, **When** the picture is made, **Then** its color is that of the note it is going to, at once, and its length is that of the frame.
12. **Given** the bars of two volumes in the same arc in a frame, **When** the picture is made, **Then** only the louder one is drawn there, and the other is drawn again when the two are in different arcs.
13. **Given** the Spiral layout, **When** a note changes, **Then** the bar moves one arc in the arcs of the layout, as for Rows (it does not move one note in pitch).

---

### User Story 2 - The chord as a bar going the other way round (Priority: P1)

The same circle carries a second set of bars for the **chords**, laid out **counterclockwise** from the top. The chords are found with the **chord interval measurement** (feature 031) in the loudest notes of each frame, looking for these **7 chord types**, in this order:

1. `(7)` — the interval of 7 steps (a fifth)
2. `(4, 7)` — a major triad
3. `(3, 7)` — a minor triad
4. `(4, 10)` — a major third with a minor seventh
5. `(4, 11)` — a major third with a major seventh
6. `(3, 7, 10)` — a minor seventh chord
7. `(4, 6)` — a major third with a tritone

- **84 places = 12 root letters × the 7 chord types** (fourth change, 2026-11-07). The **type** and the **root letter** of the chord count; the octave and the inversion do not. The letters are numbered 0 to 11 from A (the first note, A1, is an A: the letter of a note is its number mod 12) and the types 0 to 6 in the order above (type 0 is the fifth `(7)`, type 1 the major triad `(4, 7)`, ... type 6 is `(4, 6)`). The place is `7 × letter + type`: letter 0 has the places 0 to 6, letter 1 the places 7 to 13, and so on. They run **counterclockwise from the top**: place 0 starts straight up and goes to the left, and each of the 84 places is `360 ÷ 84` degrees wide (about 4.29°), as wide as a note's arc.
- **The root of a chord** is the chord tone that the bass is not: the chord has the notes `(0, *type)` above the root, and in inversion `k` the lowest note is the tone `k` of them, so the root is that many steps below the lowest recorded note. A fourth, C with F above it, is the fifth of F: the root is F.
- **Which chord has a bar:** the one chord that the measurement records for the frame (feature 031, revised 2026-11-07: the loudest letters of the frame, octaves combined, the longest type that fits, then the loudest choice of letters, then the widest): a **bar in the place of its root letter and type**. A frame whose loudest notes form none of the 7 types has no chord bar.
- **Length**: the same as for the notes: `0.5 + 0.5 × p` of the full radius with `p` the position in the local peak.
- **Color**: from the **second half of the colormap**, from the **middle** (a faint chord) to the **end** (the loudest possible), following the strength of the chord: the square root of the **average strength of the chord's notes** as a share of the largest value of the file.

So a C major triad, in any octaves and inversion, is a bar going out from the center in the place `3 × 7 + 1 = 22` (C is the letter 3; 94.3° to 98.6° counterclockwise from the top), while its three notes are bars at their own places clockwise. A **diverging colormap** shows the two sets in two color families (the notes toward the start, the chords toward the end).

**Why this priority**: The chords are the point of the image type, but they need the notes' circle and the length rule of Story 1.

**Independent Test**: Make a file where a C major triad sounds for a while. The frames show the note bars (the three notes, at their angles, clockwise) and one more bar, in the colors of the second half of the colormap, at the place of a major triad on C counterclockwise from the top.

**Acceptance Scenarios**:

1. **Given** the 7 chord types in the order above and the 12 letters from A, **When** the picture is made, **Then** the place of a chord is `7 × letter + type` (0 to 83): the 7 types of A first, then the 7 of A#, and so on to the 7 of G#; its arc starts `place × 360 ÷ 84` degrees **counterclockwise** from straight up and is `360 ÷ 84` degrees wide.
2. **Given** a frame in which the loudest notes are C, E and G (in any octaves and order), **When** the picture is made, **Then** the chord bar is the one for `(4, 7)` on C: place 22, whatever the octave and the inversion; the same triad on E (E, G#, B) is place 50, and on A (A, C#, E) place 1.
3. **Given** a frame with two notes a fifth apart, C and G, **When** the picture is made, **Then** the bar is the one for `(7)` on C: place 21; for C with F above it (a fourth) it is the fifth of F, place 56 (the fourth is an inverted fifth, as in feature 031, and the root is F).
4. **Given** a frame whose loudest notes form none of the 7 types, **When** the picture is made, **Then** there is no chord bar (the note bars are still drawn).
5. **Given** a frame at position `p` in the local peak, **When** the picture is made, **Then** the chord bar reaches out to `0.5 + 0.5 × p` of the full radius, the same as the note bars.
6. **Given** a chord of strength share `s`, **When** the picture is made, **Then** its color is the colormap's color at `0.5 + 0.5 × s` of the way along the scale: the middle color at `s = 0` and the last color at `s = 1`.
7. **Given** a note bar and the chord bar that cover the same angles, **When** the picture is made, **Then** the chord bar is drawn on top.

---

### User Story 3 - Choose Polar Chords on the page (Priority: P2)

The settings page offers **Polar Chords** as a ninth choice of **Image type**. Its own setting is **Notes shown**, a whole number from **5 to 8**, default **5**, in a group of its own, **Polar chords**. The page shows for Polar Chords the groups **Analysis**, **Colormap**, **Image type**, **Polar chords**, **Note layout** (Rows or Spiral: in which arc each note is), **Local peaks** (Minimum distance and Prominence, no checkbox, because the beat always sets the length) and **Data smoothing** (Smoothing window and Smoothing). **Threshold, Notes, Oversampling, Interpolate and Gaussian smoothing do not apply**: they are accepted by the request and ignored, and not shown on the page or in the summary. The result summary lists the image type, the colormap, the smoothing settings, Note layout, Minimum distance, Prominence and Notes shown.

**Why this priority**: The picture exists without the page (through the API), but the user reaches it from the page.

**Independent Test**: On the page choose Polar Chords: the groups listed above appear (with Notes shown from 5 to 8) and the others are gone, and Create frames makes frames. Through the API `image_type=polar-chords&polar_notes=7` makes 600 × 400 frames.

**Acceptance Scenarios**:

1. **Given** the Image type list, **When** the page is shown, **Then** it offers Tiles, Blended tiles, Contour, Circles, Circles paint, Concentric, Decay, Decay Exp and **Polar Chords**; a request with `image_type=polar-chords` is accepted and any other value is refused with a message that lists the nine names.
2. **Given** Polar Chords is chosen on the page, **When** the settings are shown, **Then** the groups of Story 3 are shown and the groups of Threshold and Notes and Image smoothing are not.
3. **Given** a request, **When** the number of notes shown is not a whole number from 5 to 8 (so 4, 9, 6.5 and `abc` are refused), **Then** it is refused before any work is done, with a message that names the range; when it is left out, 5 is used. It is checked for every image type and used by Polar Chords only.
4. **Given** a Polar Chords request, **When** the Local peaks values are not allowed, **Then** they are refused before any work is done, with the messages of the measurement; the beat is measured for every Polar Chords job.
5. **Given** a result summary of a Polar Chords job, **When** it is shown, **Then** it lists the image type, the colormap, the smoothing settings, Note layout, Minimum distance, Prominence and Notes shown, and not Threshold, Notes, Interpolate, Oversampling or Gaussian smoothing.

---

### User Story 4 - Quiet, silent and beat-less moments look sensible (Priority: P3)

- A **silent frame** (no note has any strength) is the empty background: no note bars and no chord bar.
- A frame with **fewer sounding notes than Notes shown** draws only the notes that sound.
- A frame with **no known beat** (before the first peak, a file without peaks) has position 0, so all bars reach half the full radius.
- A frame with a **single sounding note** has one note bar and no chord bar.
- A note whose bar color is **close to the middle of the colormap** (a faint note, or a faint chord) is close to the background color (the colormap's middle color, as in the other round pictures) and is hardly seen. That is the meaning of the color scale, not a fault.
- The **last note's arc ends exactly where the first begins**; the chord arcs likewise meet at the top.

**Why this priority**: These define the picture in the corners.

**Independent Test**: A silent file gives pictures of the background only; a file with a single steady note gives one bar; a file with a steady chord and no beat gives bars of half the full radius.

**Acceptance Scenarios**:

1. **Given** a silent file, **When** the pictures are made, **Then** they are made without failing and have no bars.
2. **Given** a file with no beat, **When** the pictures are made, **Then** every bar reaches half the full radius.
3. **Given** a frame with 3 sounding notes and Notes shown 5, **When** the picture is made, **Then** 3 note bars are drawn.

---

### Edge Cases

- **Antialiasing**: the straight sides of the bars and their tips are smooth (antialiased) like the circles of the other pictures; neighbouring arcs touch without a visible seam or gap.
- **Where the sets overlap**: a note bar and the chord bar can cover the same angles; the chord bar is drawn on top. There are at most 8 note bars and 1 chord bar in a frame, so the overlap is small.
- **The chord is not necessarily made of the notes that are drawn** (revised 2026-11-07): the chord measurement combines the octaves and looks at the 4 to 6 loudest letters, so a chord can use a letter whose loudest note is not among the `N` notes that have a bar. When a frame holds only the notes of a chord, every one of them has its bar.
- **Chords that are not in the list**: only the 7 types are ever looked for; a major triad is found, a diminished triad is not.
- **Frame size and rate**: the pictures are 600 × 400 like the others, with the same frame count, names and timing.
- **The bars lag behind the notes**: a bar needs up to 42 frames to reach a note on the other side of the circle (1.4 seconds at 30 frames a second), so for a quick passage the bars are still on their way when the notes have changed again; that is the smoothing the user asked for.
- **A volume that goes quiet**: its bar disappears at once (a frame without a note for the volume), and when the volume has a note again its bar appears in the arc of the note; it does not slide in from where it was.
- **Bars meet**: a bar that slides past another bar's arc is hidden in the frame in which they are in the same arc if the other volume is louder, and hides the other one if it is the louder.
- **Frame order**: because the bars follow their notes, the picture of a frame depends on the frames before it; the same file and settings still give the same pictures. Drawing a frame from its bars does not depend on the other frames.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: There MUST be a ninth image type, `polar-chords` (label **Polar Chords**), accepted by the job request and offered on the settings page; the list of image types in the refusal message MUST name all nine.
- **FR-002**: The picture MUST be a polar bar graph centered in the 600 × 400 frame on the colormap's middle color, with the full radius leaving a small margin, bars starting at the center.
- **FR-003**: The 84 piano notes MUST each have an arc of `360 ÷ 84` degrees, going **clockwise** from straight up in the order of the cells of the Note layout (Rows, the default: in order of pitch, note 0, A1, first; Spiral: the cell in which the spiral layout of feature 026 draws the note); arcs MUST NOT overlap and MUST fill the circle.
- **FR-004**: In every frame the `N` loudest notes (`N` = Notes shown, 5 to 8; ties to the lower note; a note with no strength excluded) MUST each have a bar that fills an arc: the arc of the note, or, while the bar is on its way to it, the arc it has reached (FR-014).
- **FR-005** (revised 2026-11-07): The chord ring MUST have 84 places, one for each of the 12 root letters (A first, a letter being the note number mod 12) and each of the chord types `(7)`, `(4, 7)`, `(3, 7)`, `(4, 10)`, `(4, 11)`, `(3, 7, 10)`, `(4, 6)` (in this order): the place is `7 × letter + the number of the type`, so the 7 types of a letter follow one another, each place `360 ÷ 84` degrees wide, going **counterclockwise** from straight up. The root letter and the type MUST decide the place; the octave and the inversion MUST NOT change it.
- **FR-006**: In every frame the chord recorded by the chord interval measurement (feature 031) for the 7 types MUST be drawn as one bar in the place of its root letter and type; a frame with no recorded chord MUST have no chord bar.
- **FR-007**: Every bar of a frame, note or chord, MUST reach out to `0.5 + 0.5 × p` of the full radius, `p` being the frame's position in the local energy peak (0 to 1, as in feature 024; 0 when no beat is known).
- **FR-008**: A note bar MUST be colored with the colormap at `0.5 − 0.5 × s`, `s` the square root of the note's strength as a share of the largest value of the file; a chord bar with the colormap at `0.5 + 0.5 × s`, `s` the square root of the average strength of the chord's notes as a share of the largest value of the file. The chord bar MUST be drawn over the note bars.
- **FR-009**: The settings that apply to Polar Chords, and only those (colormap, the analysis settings, Smoothing window, Smoothing, Note layout, Minimum distance, Prominence and Notes shown), MUST be shown on the page and in the result summary; Threshold, Notes, Oversampling, Interpolate and Gaussian smoothing MUST be accepted by the request, checked as always, and have no effect.
- **FR-010**: **Notes shown** MUST be a whole number from 5 to 8, default 5, checked for every image type before any work is done and refused with a message naming the range; it MUST be shown on the page for Polar Chords in a group of its own and in the result summary. The Local peaks settings MUST be available for Polar Chords (without a checkbox), with the checks and messages of the measurement, and the beat MUST be measured for every Polar Chords job.
- **FR-011**: The frames MUST be 600 × 400 with the frame count, names and timing of the other image types; the same file and settings MUST give the same frames; the other eight image types MUST be identical, file for file, to those made before this feature.
- **FR-012**: Creating the frames of a 60 second file at 30 frames a second MUST NOT take noticeably longer than for Concentric.
- **FR-013**: The documentation MUST describe Polar Chords, its two sets of bars, the 7 chord types and the places, the length and color rules, and its settings.
- **FR-014**: Every volume (the loudest, the second loudest, ...) MUST keep one bar and its arc from frame to frame. In the first frame, and in a frame in which a volume has a note again after a frame in which it had none, its bar MUST be in the arc of its note. In any other frame, when its note's arc is not the arc it is in, the bar MUST move one arc (2π ÷ 84) toward it, the shorter way round the circle (clockwise when both ways are as long), and not more; when it is in the arc of its note it stays, and when the note moves to a neighbouring arc it follows. The color and strength of a bar MUST be those of the note it is following, at once.
- **FR-015**: Where the bars of two volumes are in the same arc in a frame, only the bar of the louder volume MUST be shown. The chord bar and the length MUST NOT follow anything: they are those of the frame.

### Key Entities *(include if feature involves data)*

- **Polar Chords image type**: The new picture, value `polar-chords`: a polar bar graph with the notes clockwise and the chords counterclockwise.
- **Note arc**: One of 84 equal arcs, clockwise from the top, numbered like the cells of the Note layout (Rows: in order of pitch); the angle and width of a note's bar.
- **Chord place**: One of 84 equal arcs, counterclockwise from the top, for a chord type on a root letter (7 types × 12 letters): `7 × letter + type`, 0 to 83.
- **Bar**: A wedge from the center to a length of `0.5 + 0.5 × p` of the full radius, filling its arc.
- **Notes shown**: How many of the loudest notes get a bar, 5 to 8.
- **Chord record**: The result of the chord interval measurement for a frame: type, inversion and original notes, or none.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In every frame each bar occupies the angles of its arc to within one pixel of the edge at the full radius, and its tip is within one pixel of the length `0.5 + 0.5 × p` of the full radius, for every note (84 arcs) and every one of the 84 chord places.
- **SC-002**: The colors of the bars are the colormap's entries given by the rules (first half for notes, second half for chords) for every colormap offered, in 100% of the bars tested.
- **SC-003**: For every one of the 7 chord types on each of the 12 roots, played in each of its inversions in any octaves, the chord bar appears in the place of its root and type (`7 × letter + type`) and no other chord bar appears, in 100% of the cases tested; the same chord in any inversion and octaves gives the same place, and the 84 combinations of root and type give 84 different places.
- **SC-004**: A silent file, a file without a beat and a file shorter than the peaks window make Polar Chords frames without failing; a silent file has no bars.
- **SC-005**: The frames of the other eight image types for the reference test files are identical, file for file, to those made before this feature, and two runs of the same Polar Chords job are identical.
- **SC-006**: A 60 second file at 30 frames a second makes its Polar Chords frames in under 30 seconds on the development machine.
- **SC-007**: In every frame the arc of every bar is at most one arc (2π ÷ 84) away from its arc in the previous frame, for every volume that has a bar in both, in 100% of the frames of a file in which the notes change at random; a bar whose note stays in an arc is in that arc; a bar reaches a note `d` arcs away in `d` frames (or fewer than 43), if the note stays.

## Assumptions

- **"The first 5-8 notes"** means **the loudest 5 to 8 notes of the frame**, and the number is a **setting** (Notes shown, default 5), not a fixed number. The user wrote "first ... notes will appear" about the notes that appear in the picture; the loudest are the ones other pictures give prominence to (feature 027 counts the five loudest), and a range of 5 to 8 is what other settings look like. Another reading, the lowest 5 to 8 notes by pitch, is not taken.
- **"Local maximum"** is the **local energy peak** of the music, as in the contour beat wave and the decay picture (features 023, 024, 028): the frame's position in it, from 0 at the bottom to 1 at the top, sets the length. All bars of a frame therefore have the same length; the loudness of a note is shown by its color, not its length.
- **"Length from 0.5 to max"** means from half of the full radius to the full radius; bars start at the center. The full radius is the largest circle that fits the 600 × 400 frame with a small margin (about 190 pixels).
- **"Colors from middle to start of colormap"** is read as a scale of strength: the **quietest** note has the colormap's **middle** color and the **loudest possible** note its **first** color (and the chords: middle to last color). The strength is the same share as the tile colors use (the square root of the value over the largest value of the file). A **diverging colormap** (such as Cool Warm) gives the notes one color family and the chords another; with a one-sided colormap both sets still use their own half.
- **Chord strength** (not defined by the user) is the **average strength of the notes of the chord**, on the same scale as a note's.
- **"Chord/chords"** is taken as **the one chord** that the chord interval measurement records for a frame (it records exactly one, by the longest-then-widest rule). The user did not say whether several chord bars can show at once; with this reading there is one at most. Several bars (every type that fits) would need a different measurement.
- **The order of the chord places**: the 7 types in the order the user listed them, and, since the fourth change (2026-11-07), the 12 letters from A: the place is `7 × letter + type`. (The user first asked for 84 places, 7 types × 12 roots; on 2026-11-06 for the type only, 7 places; and on 2026-11-07 for the 84 places again, now explicitly in the order letter 1 with its types, letter 2 with its types, and so on.)
- **The root of a chord** is used again (fourth change, 2026-11-07; the user's order is letter 1 with its types, letter 2 with its types, and so on). **Which letter comes first is my choice: A**, the letter of the first note, A1, so that the letters run in the order of the notes and arc 0 of the chords sits at the same place as arc 0 of the notes; the other natural choice, C, is one constant away. The letters are `note mod 12`, the accidentals being the sharps (A, A#, B, C, C#, D, D#, E, F, F#, G, G#). (Before this change: the picture says which type of chord sounds, not on which note.) The measurement of feature 031 still records the original notes, from which the strength of the chord is worked out.
- **Where the circle starts**: both sets start at the **top** of the picture, notes going clockwise and chords counterclockwise. Where a note bar and a chord bar cover the same angles, the chord is drawn on top.
- **Chord search**: the 7 types are always these; they are not a setting. The chord search uses the loudest notes of the frame, with no threshold or note limit of its own, because the image type has neither setting. Since the chord measurement was revised (2026-11-07) a recorded chord is made of the loudest octave of each of 2 to 4 of the 4 to 6 loudest letters, which are not always among the drawn notes; the strength of the chord bar is still the average of those notes.
- **Background**: the colormap's middle color (table row 128), as for the other round pictures, so the faintest bars (close to the middle color) nearly disappear into it.
- **Settings that do not apply**: Threshold, Notes, Oversampling, Interpolate and Gaussian smoothing are accepted and ignored. The Note layout applies (see the revision at the top). The beat always counts, so there is no beat checkbox. The data smoothing applies (the smoothed values are what the bars and chords are made from).
- **How the Spiral layout is used** (added at the user's request): the layout of feature 026 names the note in each cell of the 12 × 7 grid, row by row; here the cell number is the arc number. The 84 arcs go round the circle, so with Spiral neighbouring arcs are not always neighbouring pitches, and a bar jumps in the circle where the spiral jumps in the grid. The ranking of the loudest notes is by note (ties to the lower note), and the chord is looked for in the real notes, so only the places of the note bars change.
- **"Keep track of the angle of each volume"** (added at the user's request): taken as one bar for each volume rank (the loudest note of every frame, the second loudest, ...), as the Circles picture does for its circles (feature 019), not one bar for each note. The movement is **one arc a frame**, not one arc a second: it depends on the frame rate. The "correct note" is the note that the volume has in the frame; the bar goes the shorter way round the circle, and clockwise when both ways are the same length. With the Spiral layout the angle of a note is the angle of its cell, so the movement is in the arcs of the layout. The chord bar is not smoothed (the user asked for the notes part).
- **Equal arcs**: two bars can be in the same arc only while they are on their way; the louder volume is shown (the user did not say).
- **The request field** for Notes shown is `polar_notes` (a whole number 5 to 8, default 5), echoed in the response like the other settings.
