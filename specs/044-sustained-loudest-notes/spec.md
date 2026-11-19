# Feature Specification: Sustained loudest notes

**Feature Branch**: `044-sustained-loudest-notes` (no git branch created; spec directory name only)

**Created**: 2026-11-18

**Status**: Draft

**Input**: User description: "for image types that take the n-loudest notes, we want to change the way we consider which notes they are.  The issue right now is that we don't consider how long a note lasts, but that has a lot to do with how loud it is perceived.  Most notes start louder due to an attack, and then decay.  Notes that start later might be louder at the beginning, but we should consider the first note as still sounding.  So for n-loudest notes, we should consider n+k notes, k can be 1 <= k<=n.  If a note is still in the n loudest notes in window 1, in window 2  we should consider that note as still sounding if it is the loudest n+k notes. When a note is not as high as the n+k notes, another note is 'freed up'."

**How the user's words are read** (the terms used in the rest of this document):

- The **n loudest notes** of a frame are what the pictures call "the five loudest notes" (Decay, Decay Exp), "Notes shown" (Polar Chords, 5 to 8), "the five loudest letters" (Chromatic Decay, Chromatic Wireframe) and "Number of notes" (Polychord, 5 to 8). **n** is the number of notes the picture takes.
- The user's **window 1** and **window 2** are two frames that follow each other (the rows of note values that the pictures draw from; since feature 043 each is the average of the 60 ms frequency buffers that start in it). The selection is made frame by frame.
- A **held note** is a note the picture counts as *still sounding*: it was one of the n loudest notes in the previous frame and has not fallen out of the loudest **n + k** since. A held note keeps one of the n places. **k** is the number of extra ranks of grace: 1 to n.
- A **free place** is a place among the n that is not held by a note: at the start, when fewer than n notes sound, or when a held note has fallen below the loudest n + k (the user's "another note is freed up").
- A **newcomer** is a note that is not held. It can only take a free place.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A note that is still sounding keeps its place when louder notes start (Priority: P1)

A piano chord is struck: its notes are loud for a moment (the attack) and then fade, while they are still held. Right after, a new, very loud note is struck. Today the new note takes the place of the quietest of the five loudest and the faded chord note disappears from the picture, although it is still plainly sounding. After this feature the faded note **keeps its place** as long as it is still among the loudest **n + k** notes; the new, louder note has to wait until a place is free.

**Why this priority**: This is the whole point of the request: the picture follows how long a note lasts and not only how loud it is at that instant.

**Independent Test**: Make a frame list in which five notes sound in frame 0 and, in frame 1, a sixth note is louder than all of them while the five are still among the loudest 5 + k (with k = 2: all five are within the loudest 7). In frame 1 the five held notes are the five notes of the selection; the sixth is not.

**Acceptance Scenarios**:

1. **Given** n = 5, k = 2 and the notes A, B, C, D, E as the five loudest in frame 0, **When** in frame 1 a note F is the loudest and A to E are the 2nd to 6th loudest, **Then** the selection of frame 1 is still A, B, C, D, E (F is not in it).
2. **Given** the same start, **When** in frame 1 the note E has fallen to the 8th loudest (below the loudest 5 + 2 = 7) and F is the loudest, **Then** E loses its place (freed up) and the selection is A, B, C, D, F.
3. **Given** n = 5, k = 2 and a note held in frame 1 that is exactly the 7th loudest in frame 2, **When** the frame is made, **Then** it is still held (the 7th is within n + k); in frame 3, when it is the 8th loudest, it is not.
4. **Given** frame 0 (nothing is held yet), **When** the frame is made, **Then** the selection is the n loudest notes, as before this feature.
5. **Given** a held note whose strength falls to 0 (it has stopped), **When** the frame is made, **Then** it is not held, whatever its rank (a note that does not sound is never held).

---

### User Story 2 - A free place is taken by the loudest note that is not held (Priority: P1)

When a place is freed (a held note fell below the loudest n + k, or fewer than n notes were sounding), it is filled by the **loudest note that is not held**, in frame after frame, so the selection always has as many notes as there are notes that sound, up to n. A note that has lost its place and comes back later is a newcomer like any other.

**Why this priority**: Without a rule for who takes a free place the first story would leave the picture with fewer notes than it should show.

**Independent Test**: Make a frame list where, in frame 1, two held notes have fallen out of the loudest n + k and three other notes sound loudest-first F, G, H, I: the two free places go to F and G (the two loudest newcomers), not to H or I, and the other three held notes stay.

**Acceptance Scenarios**:

1. **Given** two free places and newcomers F, G, H with F louder than G louder than H, **When** the frame is made, **Then** F and G take the places and H does not.
2. **Given** fewer notes sound than n, **When** the frame is made, **Then** the selection has only the notes that sound (the rest of the places stay empty), as with the n loudest notes today.
3. **Given** a note that was held, dropped out and is sounding again after, **When** it is among the loudest n and a place is free, **Then** it can take the place as a newcomer; it has no claim from its earlier time.
4. **Given** two notes of the same strength, **When** they compete for the same free place (or for the same rank), **Then** the lower note wins, as today, so a file always gives the same pictures.

---

### User Story 3 - The user chooses how long a held note keeps its place (Priority: P2)

The page has a setting, **k** (the extra notes of grace), a whole number from 1 up to the number of notes n of the chosen picture. A small k holds a note only while it is very close to the loudest n; a large k holds a note through a long decay. The setting applies to the pictures that take the n loudest notes; the other pictures do not show it and ignore it.

**Why this priority**: The user wrote "k can be 1 <= k <= n", so the value is chosen, but the pictures are right with a default before the setting is on the page.

**Independent Test**: Open the page, choose Decay, and see the setting with its default; choose Energy graphs or Contour and see it is not there. Send a request with a k above n for a picture of n notes: it is refused with a message naming the range.

**Acceptance Scenarios**:

1. **Given** the page with Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe or Polychord chosen, **When** the user looks at the settings, **Then** the *Extra notes (k)* setting is shown with its default.
2. **Given** the page with Contour, Energy graphs or Rhythm Circles chosen, **When** the user looks at the settings, **Then** the setting is not shown, and a request that sends it is accepted and ignored.
3. **Given** a picture of n notes, **When** k is not a whole number from 1 to n, **Then** the page shows an error under the field and sends nothing, and the server refuses the request with the message "The extra notes must be a whole number from 1 to n." (with the number n of that picture).
4. **Given** a job that is finished, **When** its list of settings is shown, **Then** it shows k for the pictures that use it.

---

### User Story 4 - Every picture that takes the n loudest notes uses the held notes (Priority: P2)

The held-notes selection is used by **Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe and Polychord**, each in the unit it already ranks:

- **Decay and Decay Exp**: the points a circle gains in a frame (24, 20, 16, 12 and 8, and the beat bonus) go to the notes of the selection, the loudest of the selection first (the gains follow the loudness order of the held notes, so the loudest of the five still gains most).
- **Polar Chords**: the bars of the loudest notes (Notes shown, 5 to 8) are the held notes; each volume keeps its own bar as before, so a held note keeps its bar and a newcomer takes a freed bar.
- **Chromatic Decay and Chromatic Wireframe**: the five loudest **letters** (a letter's energy is its loudest octave) are held as letters.
- **Polychord**: the links of the figure are the held notes (their letters, loudest first); two held notes of the same letter in different octaves stay two links.

The pictures that do not take a number of loudest notes (Contour, Energy graphs, Rhythm Circles) and the Polar Chords chord bar (which comes from the chord measurement of each window) are not changed.

**Why this priority**: Each type is a separate piece of the work and a person sees the change in them, but the rule of Stories 1 and 2 is one rule for all of them.

**Independent Test**: For each of the six pictures, make a frame list like Story 1 and see in the picture that the faded held note is still drawn in frame 1 (its circle still gains points, its bar is still there, its letter still gains, its link is still in the figure) and that the louder newcomer is not.

**Acceptance Scenarios**:

1. **Given** a Decay job in which a note is struck and then another, louder one while the first still sounds, **When** the frames are made, **Then** the first note's circle keeps gaining points after the second note starts.
2. **Given** a Polar Chords job, **When** a held note stays among the loudest n + k, **Then** its bar stays at its arc instead of being replaced by the newcomer's.
3. **Given** a Chromatic Decay job, **When** one letter's note fades but stays within the loudest n + k letters, **Then** the letter still charges its circle.
4. **Given** a Polychord job, **When** a held note keeps its rank among the loudest, **Then** the figure of the frame still has its link.
5. **Given** a file in which every note starts at the same moment and none starts later (a steady chord), **When** the frames are made, **Then** the pictures are the same as before this feature (nothing is displaced, so nothing is held back).

---

### Edge Cases

- **The first frame**: nothing is held, so the selection is the n loudest notes (the same as before). So is any frame after a frame in which no note sounded.
- **A silent frame**: no note is held (a note that does not sound is never held); the selection is empty; the next frame starts again as the first.
- **Fewer than n notes sound**: the selection holds those notes only; the empty places are free and are filled as soon as a newcomer sounds.
- **A held note that is louder than every newcomer**: it stays, of course; held notes are only displaced when they fall below the loudest n + k.
- **A held note inside n + k but quieter than newcomers outside the n**: it stays; the newcomers wait (this is the case of Story 1).
- **k as large as n**: a note keeps its place while it is among the loudest 2n.
- **A note exactly at rank n + k**: it is still held (the rule is "within the loudest n + k"); at rank n + k + 1 it is freed.
- **Ties** in loudness: the lower note (or the lower letter for Chromatic Decay and Chromatic Wireframe) comes first, as in every picture today, in both the ranks used for n + k and the choice of newcomers.
- **Letters (Chromatic Decay and Chromatic Wireframe)**: n + k letters out of 12; with n = 5 and k = 5 that is 10 of 12 letters, so almost every letter that sounds is held.
- **A job at a high frame rate**: frames that repeat the latest buffer give the same rank order, so nothing changes between them; the selection is made frame by frame at any frame rate (a note is held for as many *frames* as it stays within n + k).
- **Other settings that already apply**: the Threshold of Chromatic Decay and Chromatic Wireframe (notes below a percentage of the loudest are set to 0 before the letters are charged) is applied first, so a note below the Threshold does not sound and is never held.
- **A request that sends k for a picture that does not use it**: accepted and ignored, as every setting of another picture is.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: For every picture that takes the n loudest notes, the notes (or letters) that the picture counts in a frame MUST be chosen as held notes: in the first frame, and in any frame after a frame in which nothing sounded, they are the n loudest; in every other frame they are the notes of the previous frame's selection that are still among the loudest **n + k** of this frame and still sound, plus the loudest notes that are not held, until the selection has n notes or no more notes sound.
- **FR-002**: A held note MUST keep its place while its rank in the frame, by loudness, is n + k or better (rank 1 is the loudest), and MUST lose it in the first frame in which its rank is below n + k or its strength is not above 0.
- **FR-003**: A note that is not held MUST NOT take a place from a held note, whatever its loudness; it MAY only take a free place.
- **FR-004**: A free place MUST be given to the loudest note that is not held (and that sounds); when several free places exist they are given to the loudest newcomers in order of loudness.
- **FR-005**: The selection MUST NOT hold more than n notes, and MUST hold fewer only when fewer than n notes sound.
- **FR-006**: Ties MUST be broken in favour of the lower note (the lower letter for letters), both for the rank used for n + k and for the choice of newcomers.
- **FR-007**: Within the selection the notes MUST be ordered by their loudness in the frame, the loudest first; that order, and not the order in which the notes were selected, decides the points a circle gains (Decay, Decay Exp, Chromatic Decay, Chromatic Wireframe), the volume a bar belongs to (Polar Chords) and the order of the links (Polychord).
- **FR-008**: The selection MUST be made on the same note values the picture draws from (the frames after the averaging of feature 043 and, for Chromatic Decay and Chromatic Wireframe, after the Threshold), frame by frame, and MUST NOT depend on the frame rate in any other way.
- **FR-009**: Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe and Polychord MUST use the selection; Contour, Energy graphs, Rhythm Circles and the chord bar of Polar Chords MUST NOT change.
- **FR-010**: There MUST be a setting **k** (shown as *Extra notes (k)*), a whole number from 1 to n, the number of notes of the chosen picture (5 for Decay, Decay Exp, Chromatic Decay and Chromatic Wireframe; 5 to 8 as chosen for Polar Chords and Polychord), with a default (see Assumptions), shown on the page only for the six pictures that use it.
- **FR-011**: A request with a k that is not a whole number from 1 to n MUST be refused before the file is read, with a message that names the range; a request that sends k for a picture that does not use it MUST be accepted and k MUST be ignored; the answer of a job MUST include k.
- **FR-012**: With a frame list in which no note ever starts after another and nothing falls (every frame has the same n loudest notes in the same order), the pictures MUST be the same as before this feature.
- **FR-013**: The documentation (the order of operations of the modules, the array documentation, the pipeline overview of the image types and the help texts of the page, as the project constitution requires) MUST describe the held notes and the setting k.

### Key Entities *(include if feature involves data)*

- **Selection (of a frame)**: the notes (or letters) that a picture counts as the loudest of that frame, at most n, ordered loudest first; it is made from the previous frame's selection and the frame's note values.
- **Held note**: a note of the previous frame's selection that is still within the loudest n + k and still sounds.
- **Free place**: a place of the n that no held note occupies; given to the loudest newcomer.
- **Extra notes (k)**: the setting, a whole number from 1 to n.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a frame list where five notes sound, then a sixth louder note starts while the five are still within the loudest 5 + k, the selection of the frame after contains the five held notes and not the sixth, for each of the six pictures and each k from 1 up to the value that keeps them within n + k.
- **SC-002**: In the first frame in which a held note's rank is below n + k, it is no longer in the selection, and its place is taken by the loudest note that is not held (checked for every k from 1 to n).
- **SC-003**: For every frame of every test list the selection has at most n notes, and exactly min(n, the number of notes that sound) notes.
- **SC-004**: With k at its largest (n), a note that stays among the loudest 2n keeps its place for every frame it does, however long.
- **SC-005**: For a list of frames in which every frame has the same n loudest notes in the same order, the pictures of all six types are identical to those made before the feature (the held notes change nothing when nothing is displaced).
- **SC-006**: For every value of k a job that is made with the setting at that value is accepted; a value outside 1 to n is refused before the file is read (the file is not read in the test) with a message that names the range.
- **SC-007**: The page shows the *Extra notes (k)* setting for exactly the six pictures that use it and for no other, and a finished job lists it for exactly those.
- **SC-008**: The documentation and the help texts mention the held notes and k, and the pipeline overview names the new step.

## Assumptions

- **k is a setting, shared by the six pictures, with a default of 2.** The user wrote "k can be 1 <= k <= n", so it is chosen, and one value for all six keeps the page simple; the default is my choice, a small amount of grace (a note stays while it is within the loudest n + 2), because the user gave none. It is not 0: a k of 0 would be the old behaviour, and the user's range starts at 1.
- **k is limited to the n of the picture**, as the user said: 1 to 5 for Decay, Decay Exp, Chromatic Decay and Chromatic Wireframe and 1 to the *Notes shown* / *Number of notes* of Polar Chords and Polychord. If the user lowers that number below the k they set, the page shows the error under k.
- **The selection is made per frame**, not per 60 ms buffer: "window 1" and "window 2" are read as two frames in a row, because the pictures draw from frames, the frame is the unit the pictures already see, and a held note is then held for a number of frames. Making it per buffer is possible but would change what a frame rate means for the setting.
- **Newcomers take a free place only**, even if they are louder than a held note (Story 1). This is what "we should consider the first note as still sounding" asks for.
- **The unit that is held is the unit the picture already ranks**: notes for Decay, Decay Exp, Polar Chords and Polychord; letters (the loudest octave of each) for Chromatic Decay and Chromatic Wireframe.
- **Within the selection the loudest comes first** (FR-007), so the largest point gain still goes to the loudest note of the selection and a bar of the first volume is still the loudest bar; only *which notes* are in the selection changes.
- **The chord of Polar Chords is not changed**: it comes from the chord measurement, which looks at the loudest letters of each analysis window, not at the frames, and is a separate measurement.
- **Contour's Notes setting, Energy graphs and Rhythm Circles** do not choose the loudest notes frame by frame, so they are out of scope.
- **Nothing is held across a silent frame** and the first frame has nothing held, so a file's pictures start as they did before this feature.
- **Pictures already made are not regenerated**; this applies to new jobs.
