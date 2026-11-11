# Feature Specification: Chromatic Decay

**Feature Branch**: `035-chromatic-decay` (no git branch created; spec directory name only)

**Created**: 2026-11-09

**Status**: Draft

**Revised 2026-11-10 (the user changed `NEIGHBOURS`)**: `decay.NEIGHBOURS`, the number of neighbours that a circle's total is split between, was changed by the user from 8 to 6. Wherever the text below says 8 neighbours, "one eighth" or "six eighths", read `NEIGHBOURS`: with 6 a circle gives away **6 times** the loss per frame in all, each receiver gets **one sixth** of it (the same amount per receiver as before) and **four sixths** are lost. The rule is unchanged: it follows the constant.

**Revised 2026-11-10 (second note)**: the user restored `decay.NEIGHBOURS` to 8 for Decay and Decay Exp and gave Chromatic Decay **its own constant, `PRETEND_NEIGHBORS = 6`**, in `chromatic_decay.py`. Wherever these documents say `NEIGHBOURS` for Chromatic Decay, read `PRETEND_NEIGHBORS` (6: a circle gives away 6 times the loss per frame, one sixth to each receiver, four sixths lost). Decay and Decay Exp are unchanged.

**Revised 2026-11-10 (feature 037)**: the **Threshold** setting is no longer ignored by Chromatic Decay: it applies (see `specs/037-chromatic-threshold/`), and the Chromatic Decay group on the page has the Threshold control (before the Decay rate). Wherever this document lists the Threshold among the settings that are accepted and ignored, read that it now applies.

**Input**: User description: "Create a new flavor of Decay Exp image type that only has the 12 chromatic tones.  The 'points' are added based on highest energy of all the octaves.  The 'decay' goes to the same rate but it only goes to the notes that are 5 and 7 above the note, mod 12.  So C would decay to F and G, F to Bb and C (So a note does decay to itself to some extent).  Keep the same point levels, size and colors for now, but make the decay rate to between 1 and 10 frames, integer-only.  Call the image type 'Chromatic Decay'."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Twelve circles, one for each letter, charged by the loudest octave of each (Priority: P1)

The user wants another image type, **Chromatic Decay** (request value `chromatic-decay`). It is **Decay Exp** (feature 030) with **12 circles instead of 84**: one for each of the **12 chromatic tones** (the 12 letters: A, A#, B, C, C#, D, D#, E, F, F#, G, G#, a note without its octave and with its accidental, as feature 032 calls them).

- **How a letter's energy is measured**: the energy of a letter in a frame is the **highest energy of any of its octaves**, that is, the **largest of the up to 7 values** the 84 notes have for that letter in the frame (A1, A2, ... A7 for A). Octaves are not added, the loudest one decides.
- **Points are added as in Decay Exp**, with the 12 letters taking the place of the 84 notes: in every frame the **five loudest letters** (ties go to the lower letter, a letter with no energy does not count) **gain points in order of loudness**, the amounts of Decay Exp (24, 20, 16, 12 and 8 plus `8 × position` for the beat bonus, each cut back by the exponential taper of Decay Exp, which moves between 8 and 12 as that feature says). **The point levels, the size of a circle, the colors and the rings are those of Decay Exp** (0 to 64 points; the size full from 24 points; the first color of the colormap at 0 points and the last at 32; the twelve rings from 32 to 64), and the circles are drawn on the colormap's middle color.
- **Where the 12 circles are** (decided by the user, 2026-11-09): the 12 circles are on a **ring in circle-of-fifths order**, going **clockwise from the top**: C at the top, then G, D, A, E, B, F#, C#, G#, D#, A# and F, 30 degrees apart. The ring is centered in the picture and as large as the picture's height allows. The two letters a circle decays to (Story 2) are therefore **the two neighbours of its place on the ring**: the letter 7 above it is the next one clockwise and the letter 5 above it the next one counterclockwise (C's neighbours are G and F). **The size of a circle**: as in Decay Exp, a circle is one twelfth of the full radius at 0 points and the full radius from 24 points, and **the full radius is the largest that lets two neighbouring full circles just touch** (half the distance between two neighbouring centers). The Note layout (rows or spiral) has no meaning for it.

**Why this priority**: This is the base of the picture: without the 12 circles and their charging there is nothing to decay.

**Independent Test**: Make a file in which one note, such as C3, is steadily the loudest and nothing else sounds, with no beat. Create Chromatic Decay frames: only the circle of C gains points, by the amount of the loudest note in Decay Exp (about 1.19 points in the first frame at the starting taper), so it starts small; and the same file one octave higher (C5) charges the same circle in exactly the same way. A file in which C3 and C5 sound at once charges C as the louder of the two, not as their sum.

**Acceptance Scenarios**:

1. **Given** a frame in which the notes C3 and C5 have different strengths, **When** the letter energies are worked out, **Then** the energy of C is the larger of the two, and the energy of every other letter is the largest of its own octaves.
2. **Given** a frame in which more than five letters have energy, **When** the points are added, **Then** only the five loudest letters gain, by the amounts of Decay Exp in order of loudness, and ties go to the lower letter.
3. **Given** a letter with no energy in a frame (all its octaves are silent, for instance under the noise floor of feature 033), **When** the points are added, **Then** it gains nothing and does not count among the five.
4. **Given** the same file in Decay Exp and in Chromatic Decay, **When** a note sounds in one octave only, **Then** its letter's circle in Chromatic Decay charges exactly as the circle of that note would in Decay Exp (the same gain, taper and beat bonus), because the letter's energy is that note's energy.
5. **Given** the same file and settings, **When** it is made twice, **Then** the images are identical.

---

### User Story 2 - The points decay to the notes a fourth and a fifth above (Priority: P1)

In Decay Exp a circle gives points to the up to 8 cells around it. In Chromatic Decay a circle gives points only to **two letters: the letter 5 semitones above it and the letter 7 semitones above it, counting around the 12 letters (modulo 12)**: C gives to F (C + 5) and G (C + 7); F gives to A# (F + 5) and C (F + 7); G gives to C and D; and so on for all 12. Counting the letters from A as 0 (A, A#, B, C, C#, D, D#, E, F, F#, G, G#), letter `n` gives to letters `(n + 5) mod 12` and `(n + 7) mod 12`.

- **How much is given** follows Decay Exp: the amount that a circle with `p` points gives to **each** of the letters it gives to, per frame, is **`sin²(π/2 × p/64)`** (0 with no points), and a circle never gives more than it has. **"The same rate" means the same amount to each receiver** (decided by the user, 2026-11-09): each of the two receivers gets what each of the 8 neighbours got in Decay Exp. **Revised 2026-11-09 (the user chose how the points fade)**: the ring has no edges, and in Decay Exp points only vanish at the edges and corners of the grid, where a circle "decays as if it had 8 neighbours" and what the missing neighbours would have received is lost. Chromatic Decay does the same: a circle **gives away the same total as in Decay Exp** (8 times the formula per frame, never more than it has), **split as if it had 8 neighbours, of which only the two receivers exist**: each receiver gets one eighth of it (what a neighbour got in Decay Exp), and **the other six eighths are lost**. So the glow spreads to the two receivers and also fades, at the speed of Decay Exp. (Without this, nothing would ever vanish on a closed ring: the points would circulate and settle to an even level, and the ring would drift to being all lit.)
- **The points go round**: a fourth up and a fifth up add to an octave (5 + 7 = 12), so the receivers are each other's givers in the opposite direction: C gives to F and F gives to C, C gives to G and G gives to C. A letter therefore gets back part of what it gave, which is what the user means by "a note does decay to itself to some extent". There is no direct transfer from a circle to itself.
- Everything else about a decay step is as in Decay Exp: all circles give and receive **at the same time**, from the points they had before the step; the points are held between 0 and 64; a circle left with less than a hundredth of a point has none; a step moves `decay rate` frames' worth, so that the average rate is the same whatever the setting.

**Why this priority**: This is what makes the flavor, the music's own intervals (fourths and fifths) deciding where the glow spreads, instead of the neighbouring cells of a grid.

**Independent Test**: Give the C circle 40 points and every other 0, and take one decay step: only C, F and G have points afterwards, F and G have the same amount, and C has less than 40; take more steps and the points reach A#, D and the others, and come back to C.

**Acceptance Scenarios**:

1. **Given** only the circle of C has points, **When** one decay step is taken, **Then** only the circles of C, F and G have points, F and G equally.
2. **Given** only the circle of F has points, **When** a step is taken, **Then** it gives to A# and C (not to F's grid neighbours).
3. **Given** any circle `n`, **When** a step is taken, **Then** it gives only to `(n + 5) mod 12` and `(n + 7) mod 12`, 5 and 7 above it counting round the 12 letters.
4. **Given** a circle with `p` points, **When** a step of one frame is taken, **Then** it gives away `8 x sin^2(pi/2 x p/64)` points in all (never more than it has), of which each of its two receivers gets one eighth (what a neighbour gets in Decay Exp) and six eighths are lost.
5. **Given** a step, **When** it is taken, **Then** no points appear from nothing: the total after the step is the total before the step minus the six eighths of what was given away (and what the 64 cap and the rounding of a tail to 0 remove).
6. **Given** points that decay for many steps with no new gains, **When** the steps are taken, **Then** every circle reaches 0.

---

### User Story 3 - A decay rate of a whole number of frames, from 1 to 10 (Priority: P2)

The decay rate setting (how many frames between decay steps) of Chromatic Decay is a **whole number from 1 to 10 frames**, instead of the 0.25 to 4 in steps of 0.25 of Decay and Decay Exp. At 1 there is a decay step every frame; at 10 every tenth frame, with 10 frames' worth of decay in it (so the average rate is the same whatever the setting, as in Decay Exp). The default is **1**. A value that is not a whole number, or is under 1 or over 10, is refused with a message. The setting is on the page for Chromatic Decay like the decay rate of the other two, with the new range.

**Why this priority**: The user asked for it explicitly, but it only changes the range and the type of the number of the existing setting.

**Independent Test**: Choose Chromatic Decay: the decay rate offers the whole numbers 1 to 10 only; 2.5, 0, 11 and "x" are refused. With a rate of 10, the circles drain in steps one every tenth frame.

**Acceptance Scenarios**:

1. **Given** the page with Chromatic Decay chosen, **When** the decay rate is set, **Then** only whole numbers from 1 to 10 are accepted, the default is 1, and the other image types keep their own range (0.25 to 4 in steps of 0.25).
2. **Given** a request with `image_type=chromatic-decay` and a `decay_rate` that is not a whole number from 1 to 10, **When** it is sent, **Then** it is refused with a message that says so, before the file is read and without leaving files behind.
3. **Given** a decay rate of `r`, **When** the frames are made, **Then** one decay step falls at every `r`-th frame and moves `r` frames' worth, so that over a long time the circles lose the same total as with a rate of 1.

---

### User Story 4 - Choosing it and the settings that go with it (Priority: P3)

Chromatic Decay is chosen from the image type setting, with the label **Chromatic Decay**. It uses the **colormap**, the analysis settings, the **local peaks** settings (the beat adds up to 8 points to the five loudest letters, as in Decay Exp) and the **data smoothing**; the **Note layout** (rows or spiral) does **not** apply, because the 12 letters are not notes in cells (it is accepted and ignored). The four **decay amounts** of Decay do not apply (it has none, as Decay Exp). The frames have the usual size, count, names and timing, and can be made into a movie (feature 029).

**Why this priority**: It is the frame around the picture.

**Independent Test**: Choose Chromatic Decay on the page: the Decay rate control shows 1 to 10; Note layout is not shown; make frames and a movie.

**Acceptance Scenarios**:

1. **Given** the image type setting, **When** the user opens it, **Then** Chromatic Decay is among the choices and, when chosen, the page shows the decay rate (1 to 10), the local peaks settings and the data smoothing, and no note layout.
2. **Given** the other image types, **When** frames are made, **Then** they are exactly what they were before this feature.

---

### Edge Cases

- A letter that is silent in every octave in a frame does not gain and does not count among the five loudest; a frame with fewer than five sounding letters has fewer gains.
- The letter energy is the largest of the octaves **after** the noise floor, so an octave under the floor is silent for its letter, and a letter with only floored octaves is silent.
- A frame with no sound at all adds nothing; the circles go on decaying.
- The ring has no edges, but a circle loses the share a missing neighbour would have had (six eighths of what it gives away), so the points fade as at the edge of the grid of Decay Exp, and a file with no sound ends with every circle at 0.
- A decay rate of 10 with a file shorter than 10 frames: the first decay step falls after the file ends, so the picture only gains and never decays; nothing fails.
- Frame sizes other than the usual one scale the picture as for the other types.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST offer a new image type, **Chromatic Decay** (`chromatic-decay`), chosen the same way as the other types, producing one picture per frame with **12 circles**, one for each of the 12 letters.
- **FR-002**: The energy of a letter in a frame MUST be the **largest** of the strengths its octaves have in that frame (after the noise floor); octaves MUST NOT be added.
- **FR-003**: In every frame the five loudest letters (ties to the lower letter; a letter with no energy does not count) MUST gain points by the amounts, the beat bonus and the exponential taper of Decay Exp, in order of loudness.
- **FR-004**: The points of a circle MUST be held between 0 and 64, and its size, color and rings MUST follow its points exactly as in Decay Exp.
- **FR-005**: A circle MUST give points in a decay step **only** to the letters 5 and 7 semitones above its own, counting round the 12 letters (letter `n` to `(n + 5) mod 12` and `(n + 7) mod 12`), never to itself directly.
- **FR-006**: The amount given in a step MUST follow the loss of Decay Exp: a circle gives away `8 x sin²(π/2 × p/64)` points per frame (never more than it has), as settled by the clarifications of Story 2, **one eighth of it to each of its two receivers and six eighths lost**; all circles MUST give and receive at the same time from the points before the step, and the result MUST be held between 0 and 64 with a circle under a hundredth of a point set to 0.
- **FR-007**: The decay rate of this type MUST be a **whole number from 1 to 10** (frames between decay steps), default 1; anything else MUST be refused before the file is read, with a message that says so; a step MUST move as many frames' worth of decay as the rate, so that the average rate does not depend on it; the other image types MUST keep their own range.
- **FR-008**: The Note layout and the four decay amounts MUST NOT apply to this type (they are accepted and ignored); the colormap, the analysis settings, the local peaks and the data smoothing MUST apply.
- **FR-009**: The 12 circles MUST be laid out in the picture as settled by the clarification of Story 1, on the colormap's middle color, in the usual frame size.
- **FR-010**: Results MUST be repeatable: the same file and settings MUST give identical images.
- **FR-011**: The frames of this type MUST be usable for making a movie (feature 029) as the frames of the other types are, and the other image types MUST be unchanged.

### Key Entities

- **Letter**: one of the 12 chromatic tones, a note without its octave, counted from A as 0 to G# as 11.
- **Letter energy**: for a letter in a frame, the largest strength of its octaves.
- **Circle**: one for each letter, holding points from 0 to 64.
- **Receivers of a letter**: the letters 5 and 7 above it, modulo 12.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a file with a single sounding note, only the circle of that note's letter gains points, and it gains exactly what the circle of that note gains in Decay Exp, whatever the octave of the note.
- **SC-002**: After one decay step from a state in which one circle has points, exactly three circles have points (the giver and its two receivers), the two receivers have equal amounts, and the total after the step is the total before minus six eighths of what was given away, for each of the 12 letters.
- **SC-003**: Points that are not fed decay to 0 in every circle, and the points are never above 64 or below 0 at any frame of any file.
- **SC-004**: A decay rate that is a whole number from 1 to 10 is accepted and every other value is refused in 100% of the requests tried (2.5, 0, 11, negative, empty, text), without files left behind.
- **SC-005**: The same file and settings give identical images, and the frames of the other nine image types, Energy Graphs and every other setting are identical to what they were before this feature.
- **SC-006**: A user can choose Chromatic Decay, make frames and a movie of a three-minute file with no step beyond choosing the type and, if wanted, the decay rate, in about the time Decay Exp needs.

## Assumptions

- The **12 letters** are counted from A (A as 0), as in Polar Chords (feature 032), because the 84 notes start at A1; the intervals 5 and 7 are counted round the 12 letters, so they do not depend on where the counting starts.
- "**Points are added based on the highest energy of all the octaves**" is read as the **largest** of a letter's octave strengths, which then ranks the 12 letters: the five loudest gain, as the five loudest of 84 notes do in Decay Exp. "The same point levels" is read as the gains of Decay Exp (24, 20, 16, 12, 8 plus the beat bonus), the same 0 to 64 range and the same exponential taper.
- **The taper rule is kept as it is** ("the taper falls when more than 10 circles have more than 32 points"): with 12 circles, 11 of them would have to be above 32 points, which is hardly ever, so in practice the taper rises from 8 to 12 over 400 frames and stays there; it was set for 84 circles. The user asked to keep the point levels for now; this is a candidate for a later change.
- "A note does decay to itself to some extent" is read as the **round trip** through the receivers (C gives to F and F gives back to C), not as a direct share kept by the giver.
- The **size** of a circle is "the same" in the sense of the same points-to-size scale (small at 0 points, full at 24); what "full" is in the picture depends on the layout (see the clarification of Story 1).
- The decay rate keeps its **request field** (`decay_rate`) and is validated for the chosen type: 1 to 10 whole numbers for Chromatic Decay, 0.25 to 4 in steps of 0.25 for the others, so that existing requests keep working; the default for Chromatic Decay is 1, the same as for Decay and Decay Exp.
- The **beat** (local peaks) works as in Decay Exp: it always adds its bonus to the gains.
- This feature adds an image type only; Decay, Decay Exp, the analysis and the other pictures are unchanged.
