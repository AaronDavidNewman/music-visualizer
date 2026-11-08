# Feature Specification: Chord Interval Metric

**Feature Branch**: `031-chord-interval-metric` (no git branch created; spec directory name only)

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "create a new type of metric to measure in the audio data.  The data is based on the frequency bins in terms of the letter notes (the 84 piano notes).  A chord type is defined by a tuple that indicate intervals between notes in 1/2 steps (I will just call them steps, assume it means 1/2 steps).  There could be between 1 and 3 intervals.  The root isn't specified but it's implied, so 4 1/2 steps would just be '4' but assumed to be 0 and 4. We match them against the loudest notes.  They are normalized in a couple of ways: first, we bring them all to the same octave by dividing frequencies of the top notes by 2, if required,  until they are within an octave.  So for C3 and the E4, for instance, E4 frequency is divided by 2, E3 and and C3 form a third (or 4 )steps.  Second, we should identify any inversion by permuting the intervals.  So if the interval you are looking for is 4  steps, 0 to 4, and the notes are E4 and C5, that is 8 steps.  By adding an octave to the first note, it becomes 4 and 12, then subtract 4 from each, and you have 0 and 8.  So you could match it as a 3rd in 1st inversion.  2 intervals will contain 3 notes and so there are 3 possible inversions.  This data is also stored per minimum time interval like bins or local peaks.  For each chord, we record 1) the type of tuple, 2) the inversion, 3.  The intervals we are looking for will always be given as parameters.  For instance ((5), (7)) looks for intervals of 5 steps or 7 steps (diatonically, a 4th or a 5th).  Usually there will be ambiguity in matching - a 4th can be an inverted 5th for instance.   If there are multiple matches, we use the following rule to determine how to record it: 1) the longest interval wins.  Tuples (4, 7) will match over just (4).  Second, the widest interval wins, so if I am looking for (4) or (8), an (8) interval in root position would match over a (4) in first inversion.  Just create the code to record the data for now, we will use it later."

## Clarifications

### Session 2026-11-06

- Q: What is the third thing to record for each chord (the request stops at "3.")? -> A: **The original notes**: the notes that formed the chord, as they sound in the music (before they are brought into one octave).
- Q: Is the octave handling right, where the same letter in two octaves counts as one note and the chord type then does not match? -> A: **Yes, it is correct.**
- Q: Should there be a loudness threshold? -> A: **Only if the image type supports one.** A threshold applies only when the image type that will use the data has the Threshold setting, and, likewise, **if the image type lets you limit the number of notes (the Notes setting), only those notes are used in the interval search.** The measurement has no threshold or limit of its own.

### Session 2026-11-07 (revision: letters, and more notes considered)

Looking at a real file, the user found fewer chords than expected: the rule "the `n + 1` loudest notes" is defeated by a note doubled in two octaves, by overtones, and by one louder note that is not in the chord. The user decided:

- **Octaves are combined.** The notes of the same letter in all octaves are one note; the match is on the letters (pitch classes).
- **More notes are considered**: "for a single interval, we should consider 4 notes. For a 3-interval we should consider 6", **at most 6** because the number of permutations grows. (Two intervals: 5, the step in between.)
- **Mistaking an overtone for a real fifth is accepted** ("expected sometimes"): the chord information will be aggregated later, with regard to tonal center, modes and so on.

This replaces "the `n + 1` loudest notes" (FR-003, FR-004) and the "doubled notes" assumption; the rest is unchanged.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recognise which chord the loudest notes of a moment form (Priority: P1)

The application already reduces the music to the strength of each of the **84 piano notes** in every analysis window (the "bins"). The user wants a new **measurement**, built on those note strengths, that says **which chord is sounding** in each window, from a list of chord types that the caller asks for.

**A chord type** is a short list of **1 to 3 intervals**, each a number of **steps** (half steps) above an **implied root**. The root itself is never written: `(4)` means the notes 0 and 4 steps (a major third), `(4, 7)` the notes 0, 4 and 7 (a major triad), `(3, 7, 10)` the notes 0, 3, 7 and 10. A chord type with `n` intervals has `n + 1` notes and therefore `n + 1` positions, the **root position** and `n` **inversions**: number **0** is root position, number **1** is first inversion (the root, the lowest chord note, is moved up an octave), and so on up to `n`.

**What is matched** (revised 2026-11-07): first the notes of a window are **combined into the 12 letters**: the strengths of a letter in all its octaves are added up (C2, C3 and C4 are one note, C), and a letter stands for its **loudest octave** (the lower one on a tie). Then, for a chord type with `n` intervals, the window's **loudest letters** are looked at: **4 for one interval, 5 for two, 6 for three** (never more than 6; a letter with no strength does not count; ties go to the lower letter), and **every choice of `n + 1` of them** is tried. The notes of a choice are **normalised** in two ways:

1. **Into one octave.** The lowest of the notes stays where it is. Every higher note is moved **down by whole octaves** (its frequency divided by 2, as many times as needed) until it is **less than an octave above the lowest**. Example: C3 and E4: E4 is brought down to E3, and C3 to E3 is a third, **4 steps**.
2. **Into an inversion.** What is left is the set of steps above the lowest note. It is compared with the pattern of **every inversion** of the chord type. The inversions of a chord type are made by moving the lowest note up an octave, one note at a time, and counting from the new lowest note. For `(4)`: root position is 0, 4; first inversion is 4, 12, which counted from the new lowest note is **0, 8**. For `(4, 7)`: root position 0, 4, 7; first inversion 0, 3, 8; second inversion 0, 5, 9. Example: **E4 and C5** are 8 steps apart, so they match `(4)` in **first inversion**.

**Several types can match** the same notes (a 4th is an inverted 5th, a major third in first inversion is a minor sixth). When more than one requested chord type, or inversion, matches, **exactly one is recorded**, chosen by these rules, in this order:

1. **The longest wins**: the chord type with the most intervals. `(4, 7)` wins over `(4)`.
2. **Then the loudest wins** (added 2026-11-07; see Assumptions): among the choices of letters that form a chord of that length, the one whose letters are loudest together (their strengths added). With only the `n + 1` loudest notes there was one choice and this rule had nothing to decide; with several choices it keeps a faint note that happens to make a wide interval from beating the real chord.
3. **Then the widest wins**: the chord type whose largest interval is the biggest. If `(4)` and `(8)` are both asked for, notes 8 steps apart match `(8)` in root position and `(4)` in first inversion, and `(8)` is recorded. (For the same letters this is exactly the user's rule.)
4. If that still does not decide it (not mentioned by the user; see Assumptions): the **lowest inversion number** wins (root position first), then the first choice in the order of the louder letters.

**What is recorded** for a window with a chord: **1) the chord type** (the tuple as it was given), **2) the inversion** (0 for root position, 1, 2 or 3), and **3) the original notes**: the `n + 1` notes that formed the chord, as they sound in the window (the loudest octave of each letter, from lowest to highest), before they were brought into one octave. A window with no chord records that there is none.

**Why this priority**: This is the whole measurement. Storing it, the note limits, the parameters and the odd cases (Stories 2 to 4) all depend on getting this recognition and these rules right.

**Independent Test**: Build windows from known notes. Asking for `(4)` alone: C3 with E4 gives `(4)`, root position, and E4 with C5 gives `(4)`, first inversion. Asking for `(4)` and `(4, 7)`: C, E and G together (any octaves) give `(4, 7)`, root position, and E, G and C give `(4, 7)`, first inversion. Asking for `(5)` and `(7)`: two notes 7 steps apart give `(7)`, root position, and two notes 5 steps apart give `(7)` in first inversion, because the widest wins over `(5)` in root position. Asking for `(4)` and `(8)` together: notes 8 steps apart give `(8)` in root position, and, by the same rule, notes 4 steps apart give `(8)` in **first inversion** (a major third is an inverted minor sixth), not `(4)`.

**Acceptance Scenarios**:

1. **Given** the loudest notes C3 and E4 and the chord type `(4)`, **When** the window is measured, **Then** E4 is brought down an octave to E3, the notes are 4 steps apart, and `(4)` is recorded in root position (inversion 0), with the original notes C3 and E4 (not E3).
2. **Given** the loudest notes E4 and C5 and the chord type `(4)`, **When** the window is measured, **Then** the notes are 8 steps apart and `(4)` is recorded in first inversion (inversion 1), with the original notes E4 and C5.
3. **Given** the loudest notes C, E and G in any octaves, and the chord type `(4, 7)`, **When** the window is measured, **Then** `(4, 7)` is recorded in root position, with the three original notes as they sound (lowest to highest); the same three notes with E lowest are recorded as first inversion, and with G lowest as second inversion.
4. **Given** that `(4)` and `(4, 7)` are both asked for and the three loudest letters are C, E and G, **When** the window is measured, **Then** `(4, 7)` is recorded, not `(4)`, although two of the three would also match `(4)`.
5. **Given** that `(4)` and `(8)` are asked for and the loudest two notes are 8 steps apart, **When** the window is measured, **Then** `(8)` in root position is recorded, not `(4)` in first inversion. **Given** the two notes are 4 steps apart, **Then** `(8)` in first inversion is recorded, not `(4)` in root position (the widest wins both ways).
6. **Given** that `(5)` and `(7)` are asked for and the loudest two notes are a fifth (7 steps) apart, **When** the window is measured, **Then** `(7)` in root position is recorded (and `(5)` in first inversion matched too, but is not as wide). **Given** the two notes are a fourth (5 steps) apart, **Then** `(7)` in **first inversion** is recorded, because the widest wins over `(5)` in root position.
7. **Given** a chord type with 3 intervals, **When** the window is measured, **Then** four of the six loudest letters are matched and there are four positions, inversion 0 to 3.
8. **Given** the same note strengths and parameters, **When** the measurement is made twice, **Then** the records are identical.
9. **Given** C, E and G sounding with a louder F# (and `(4)` asked for), **When** the window is measured, **Then** `(4)` is recorded with C and E: a louder letter that fits no chord does not hide the chord.
10. **Given** a chord type of one interval and a third whose weaker letter is the 5th loudest letter of the window (or, for two intervals, a triad whose weakest letter is the 6th; for three, one whose weakest letter is the 7th), **When** the window is measured, **Then** no chord is recorded; with that letter one place louder it is.
11. **Given** C sounding in two octaves, **When** the window is measured, **Then** the two are one letter whose strength is the sum, and the letter is recorded as its louder octave (the lower on a tie).
12. **Given** two chords that share a note (C E G and G B D) of different loudness, **When** the window is measured, **Then** the louder one is recorded. **Given** a faint B that makes a wider interval `(4, 11)` with C and E than the triad `(4, 7)` C E G does, **Then** the louder triad is recorded.
13. **Given** a note more than 60 dB below the loudest value of the array (the noise floor of feature 033, which replaced the earlier floor of a millionth of the window's loudest letter), **When** the window is measured, **Then** it is 0 before the octaves are combined and is not part of any chord.

---

### User Story 2 - One record for every window, kept like the bins and the local peaks (Priority: P2)

The result is **stored per minimum time interval**, the same way the note strengths (the bins) are: **one record for every analysis window**, in the order of the windows, so that a later feature can look up the chord of any window or frame, as it already looks up the note strengths and the beat. Nothing is shown or used yet: as with Local Peaks (feature 023), this feature is **the measurement only**. How the chords are used (the request, the page, the pictures) will be defined later, so the job request, the response, the settings page and the existing pictures do not change.

**Why this priority**: The measurement is only useful later if it can be read back per window. It is a smaller step than the recognition itself.

**Independent Test**: Measure a file of 500 analysis windows with `(4, 7)` asked for. The result has exactly 500 records; record `i` is the chord of window `i`; windows that were silent have "no chord".

**Acceptance Scenarios**:

1. **Given** a file with `W` analysis windows, **When** the measurement is made, **Then** there are exactly `W` records, in window order, and the record for a window depends only on that window's note strengths and the parameters.
2. **Given** a window with no sound, **When** the measurement is made, **Then** its record says there is no chord.
3. **Given** the existing job request, response, settings page and pictures, **When** this feature is added, **Then** they behave and look exactly as before (the frames are identical, file for file).

---

### User Story 3 - Only the notes the image type would use (Priority: P2)

Some image types let the user **limit which notes count**: the **Notes** setting keeps only the notes with the most energy (chosen once for the whole file, feature 017), and the **Threshold** setting hides a note, in a window, when it is weaker than a percentage of the loudest note of the file (feature 011). The chord measurement has **no threshold or limit of its own**. It can be told, as optional parameters, to **use the same limits**, and then:

- With a **number of notes** given, **only those notes** are used in the interval search: every other note is treated as silent in every window, so it is never one of the loudest notes and never part of a chord. The notes are chosen exactly as the picture chooses them (the notes with the most total energy over the file, equal energy to the lower note).
- With a **threshold** given, a note weaker than that percentage of the loudest note of the file is treated as silent **in that window**, as the picture hides it.
- With **neither** given (an image type that does not have these settings), all 84 notes can be used.

The letters of a chord type are then built only from the notes that are allowed. Both limits are applied before the notes are combined into letters.

**Why this priority**: Without it the chords would be found in notes that the picture does not show. It is not needed to recognise a chord, so it comes after Story 1, with Story 2.

**Independent Test**: Make a file where the lowest three notes of a chord are quiet and two other notes are loud. With no limits the loud notes win; with a threshold above the quiet notes, or with a number of notes that leaves out the quiet ones, those quiet notes cannot form the chord, and a chord made only of allowed notes is found.

**Acceptance Scenarios**:

1. **Given** no limits, **When** a window is measured, **Then** all 84 notes can be used (as in Story 1).
2. **Given** a number of notes `N`, **When** the measurement is made, **Then** the notes used are exactly the `N` notes with the most total energy over the file (the picture's choice), the same in every window, and a note outside them is never in a recorded chord, however loud it is in a window.
3. **Given** a threshold of `T` percent, **When** a window is measured, **Then** a note strictly below `T` percent of the loudest note of the file is not counted in that window (one exactly at the threshold counts), and the letters are built from the others.
4. **Given** a threshold of 0, **When** the measurement is made, **Then** it is as if there were no threshold.
5. **Given** both a number of notes and a threshold, **When** the measurement is made, **Then** a note is used in a window only if it passes both.

---

### User Story 4 - The chord types come as parameters, and odd cases are handled (Priority: P3)

The chord types to look for are **always parameters** of the measurement: nothing is built in. A list of one or more chord types is given, for example `((5), (7))` for a 4th and a 5th. A chord type with a single interval may be written as a bare number: `(5)` is the same as the one-element tuple `5`.

Wrong parameters are refused with a clear message **before** any measuring: a list with no chord types, a chord type with no intervals or more than 3, an interval that is not a whole number from 1 to 11, intervals that are not in increasing order (`(7, 4)` is refused; it is the same chord as `(4, 7)` and the caller must write it that way), or the same chord type twice.

The odd cases:

- **Fewer sounding notes than the chord type needs** (for example one note, when a third is asked for): that chord type does not match.
- **The same letter in different octaves** (C2 and C3): one letter (revised 2026-11-07). C2 and C3 alone are one letter, fewer than the chord type needs, and it does not match; beside E they are a third.
- **Symmetrical chords**, such as `(4, 8)` (all three inversions look the same) or `(3, 6, 9)`: the pattern matches every inversion; the **lowest inversion number, root position,** is recorded.
- **Notes at the top of the analysis** (the four notes above the 84 piano notes) are not considered.
- A **number of notes** or a **threshold** that the picture's setting would not accept is refused with the same message, before any measuring.

**Why this priority**: These make the recording safe to use, but the recognition does not depend on them.

**Independent Test**: Ask for `[]`, `[()]`, `[(1, 2, 3, 4)]`, `[(0,)]`, `[(12,)]`, `[(7, 4)]`, `[(4,), (4,)]`, and `[(4.5,)]`: each is refused with a message that names the problem. Ask for `(4, 8)` with the notes C, E, G#: root position is recorded.

**Acceptance Scenarios**:

1. **Given** parameters that are not allowed, **When** the measurement is asked for, **Then** it is refused with a message naming the problem and nothing is measured.
2. **Given** the parameter `((5), (7))`, **When** it is read, **Then** it means the chord types `(5)` and `(7)`, in that order.
3. **Given** a window with only one sounding note and the chord type `(4)`, **When** the window is measured, **Then** no chord is recorded.
4. **Given** only the notes C2 and C3 and the chord type `(4)`, **When** the window is measured, **Then** no chord is recorded (they are one letter).
5. **Given** the chord type `(4, 8)` and the loudest three notes C, E and G#, **When** the window is measured, **Then** it is recorded in root position (inversion 0), however the notes are ordered in pitch.

---

### Edge Cases

- **Folding changes only the higher notes**: the lowest note of the chosen notes is the reference. Notes exactly an octave (or more) above fold onto it and count as the same note.
- **An interval of 12 or more is not a chord interval**: a chord type spans less than an octave; use the lower number (an octave is the same note).
- **Ties in loudness** go to the lower note, as for the other note-ranking features.
- **Quiet noise**: unless a threshold is given (Story 3), faint energy still forms a chord if it matches, except that a note more than 60 dB below the loudest value of the array is 0 (the noise floor of feature 033) and is no part of a chord.
- **Overtones and spurious chords**: looking at more letters than the chord has notes, and at the overtones (the fifth, the third...) of a single note, finds chords that the musician did not play (and wide or long chord types such as `(4, 11)` or a seventh can be found in a handful of loud letters). This is accepted; the chord information is for later aggregation.
- **Fewer allowed notes than a chord type needs** (for example 12 notes allowed, and one chord type of 4 notes, with only 3 of the 12 sounding in a window): no match for that chord type in that window.
- **A window where none of the loudest letters match a requested type** records "no chord", even if letters further down would match.
- **Several matches of the same type** (a symmetrical chord) record one inversion, the lowest.
- **The record for a window never depends on its neighbours**: no smoothing across windows is done here.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: There MUST be a measurement that, for every analysis window of a file, works out which of the requested chord types the window's loudest notes form, and in which inversion, and records the result (Story 1).
- **FR-002**: A **chord type** MUST be given as 1 to 3 intervals, each a whole number of steps from 1 to 11, in strictly increasing order, above an implied root; the notes of the chord are the root (0) and the intervals. A single interval MAY be given as a bare number.
- **FR-003** (revised 2026-11-07): The 84 piano notes of a window MUST be combined into the 12 letters: the strength of a letter is the sum of its octaves, and a letter with no strength does not sound (the notes have been through the noise floor of feature 033 first). A letter is represented by its loudest octave (the lower on a tie). For a chord type with `n` intervals the measurement MUST look at the `n + 3` loudest sounding letters (4, 5 or 6: never more than 6; ties to the lower letter) and MUST try every choice of `n + 1` of them. With fewer sounding letters than `n + 1`, the chord type MUST NOT match.
- **FR-004**: The notes of a choice MUST be brought into one octave: the lowest stays; each higher note is moved down by whole octaves until it is less than 12 steps above the lowest. (Different letters never fall on the same step.)
- **FR-005**: The steps of the folded notes above the lowest MUST be compared with every inversion of the chord type: inversion 0 is root position (0 and the intervals); inversion `k` is made by moving the `k` lowest notes up an octave and counting from the new lowest note (`(4)`: 0, 8 for inversion 1; `(4, 7)`: 0, 3, 8 for inversion 1 and 0, 5, 9 for inversion 2). A chord type with `n` intervals has inversions 0 to `n`. A match MUST be an exact equality of the steps.
- **FR-006**: When several chord types, or several inversions, match the same window, exactly one MUST be recorded, chosen by, in order: the most intervals; then the loudest letters (their strengths added up, from the lowest letter); then the largest interval; then the lowest inversion number; then the first choice in the order of the louder letters. (The user's own order is the most intervals, then the largest interval: the loudness comes between them, so that a faint note cannot win by making a wide interval; for the same letters the largest interval still decides.)
- **FR-007**: For each window with a chord, the record MUST hold the chord type as given, the inversion number and the original notes: the `n + 1` notes that formed the chord (the loudest octave of each letter), as they sound (before they are brought into one octave), from the lowest to the highest. A window with no chord MUST record that there is none.
- **FR-008**: There MUST be exactly one record per analysis window, in window order, each depending only on the note strengths of its own window and the parameters.
- **FR-009**: The chord types MUST always be parameters; no chord type is built in. Parameters that are not allowed (no chord types, no interval or more than 3, an interval that is not a whole number from 1 to 11, intervals not in increasing order, a chord type given twice) MUST be refused with a message naming the problem, before any measuring.
- **FR-010**: The measurement MUST be deterministic: the same note strengths and parameters give identical records.
- **FR-011**: This feature MUST NOT change the job request, the response, the settings page, the existing pictures, the frames or the existing measurements; it is the recording only.
- **FR-012**: The documentation MUST describe the measurement, the chord types, the inversions, the matching and selection rules and what is recorded.
- **FR-013**: The measurement MUST have no threshold or limit of its own. It MUST accept, as optional parameters, a **number of notes** and a **threshold**, which MUST work as the Notes setting (feature 017: the notes with the most total energy over the file, the same in every window, equal energy to the lower note) and the Threshold setting (feature 011: a note strictly below the given percentage of the loudest note of the file is hidden in that window) of the pictures, with the same ranges and messages. A note that is not allowed MUST be treated as silent in the window, before the notes are combined into letters. With neither parameter given, all 84 notes MUST be usable.

### Key Entities *(include if feature involves data)*

- **Chord type**: A list of 1 to 3 intervals in steps above an implied root, for example `(4)` (a third) or `(4, 7)` (a triad). Has `n + 1` notes and `n + 1` positions.
- **Inversion**: Which chord note is the lowest: 0 for root position, 1 for first inversion, and so on up to the number of intervals. Seen as a pattern of steps above the lowest note.
- **Chord record**: The result for one window: the chord type, the inversion and the original notes (as they sound), or "no chord".
- **Allowed notes**: The notes that the interval search may use: all 84 by default, or fewer when a number of notes or a threshold is given.
- **Chord series**: The records of a whole file, one per analysis window, in order, stored like the note strengths and the local peaks.
- **Requested chord types**: The parameter: the ordered list of chord types to look for.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every worked example of this specification (C3 with E4; E4 with C5; C, E and G in each inversion; `(4)` against `(4, 7)`; `(4)` against `(8)`; a 4th and a 5th against `((5), (7))`) gives exactly the chord type and inversion that is stated, 100% of them.
- **SC-002**: For every chord type of 1 to 3 intervals built from the steps 1 to 11, every inversion of it, played with its notes in any octaves within the 84 notes, and asked for on its own, the measurement records that chord type with that inversion, with no exception (symmetrical chords record the lowest inversion).
- **SC-003**: Whenever two or more requested chord types match, the one recorded is the one the selection rules give; checked for every pair among the example sets and a random sample of larger sets, 100% agree with an independent calculation.
- **SC-004**: A file of `W` windows always gives exactly `W` records, in order; silent windows always give "no chord".
- **SC-005**: With a number of notes or a threshold given, no recorded chord ever contains a note that the picture's setting would leave out, in 100% of windows; with neither given, the records are the same as with all 84 notes allowed. Every original note of a record is one of the notes that made the chord, as it sounds, in 100% of the windows tested.
- **SC-006**: Two runs on the same input give identical records, and the pictures and the job response are identical to before the feature, file for file.
- **SC-007**: Recording the chords of a 60 second file at the default analysis spacing, for a list of 10 chord types, takes no more than a few seconds beyond the analysis itself.

## Assumptions

- **"The frequency bins in terms of the letter notes (the 84 piano notes)"** means the note strengths the analysis already makes for each window: its first 84 notes, one step apart, starting at 55 Hz (A1). The four extra notes above them are not used. The strengths used are the analysis values as they are, not the display smoothing.
- **"Minimum time interval like bins or local peaks"** means the analysis window, the smallest step in time of the analysis: one record for each window. How windows map to picture frames is already solved elsewhere and is not part of this feature.
- **"Intervals" are measured from the implied root**, as in the user's examples (`(4)` is 0 and 4; `(4, 7)` is 0, 4 and 7). Strictly increasing, 1 to 11 steps, so that a chord spans less than an octave.
- **"The loudest notes"** (revised 2026-11-07, answered by the user): the notes are combined into letters and a chord type looks at the `n + 3` loudest letters, at most 6, trying every choice of `n + 1` of them. The user asked for 4 for one interval and 6 for three; **5 for two intervals is my interpolation**. The loudest letters are taken in a stable order, so equal strengths go to the lower letter. A longer chord can still win over a shorter one that also fits (rule 1).
- **Combining the octaves** (decided by the user on 2026-11-07, replacing the earlier "doubled notes" rule of 2026-11-06): a letter in two octaves is one letter whose strength is the sum of the octaves. The recorded note of a letter is its loudest octave (the lower on a tie); that is my choice, because the record holds one note for each letter of the chord. The inversion is counted from the lowest of the recorded notes.
- **Rounding noise** (my choice, replaced on 2026-11-07 by feature 033): the analysis leaves tiny non-zero values in the notes that do not sound, and with six letters looked at they would make chords of their own. This first meant a letter under a millionth of the loudest letter of its window; the fixed noise floor of feature 033 (60 dB below the loudest value) now does that job and more, inside `measure_chords`, and the weaker one was removed.
- **Loudness before the widest interval** (my choice, a change to the order of the user's rules): with several choices of letters, "the longest, then the widest" lets a faint note that makes a wide interval beat the real chord (C E G with a faint B: `(4, 11)` is wider than `(4, 7)`). So the loudest choice decides first among chords of the same length; for the same letters the widest still decides, as the user described. If this is not wanted it is one line in the order of the score.
- **Overtones** (the user, 2026-11-07): mistaking an overtone for a real fifth is expected sometimes; later features aggregate the chord information (tonal center, modes...).
- **"The widest interval wins"** is taken as the chord type whose largest interval is the biggest as written by the caller (for `(4)` and `(8)`: 8). The user's example (`(8)` in root position over `(4)` in first inversion) fits this reading.
- **Ties after both user rules** (same number of intervals and same widest interval, for instance `(3, 8)` and `(5, 8)`, or a symmetrical chord matching in several inversions) are not covered by the user's rules. The assumption is: the loudest letters, then (as the user said) the widest interval, then the lowest inversion number, then the first choice in the order of the louder letters. (Two different chord types never tie on all of these, so the order of the list given never decides.)
- **The third thing to record** (the request stops at "3.") is **the original notes** (answered by the user on 2026-11-06): the notes of the chord as they sound, before they are brought into one octave. They are stored as the note numbers of the 84 piano notes (0 is the lowest, A1 at 55 Hz), lowest to highest. The root is not stored, because the chord type, the inversion and the original notes together determine it.
- **Threshold and number of notes** (answered by the user on 2026-11-06): the measurement has no limit of its own. They apply only to an image type that supports them, and then the interval search uses only the notes the picture uses. Since nothing uses the data yet, they are optional parameters of the measurement, which a later feature fills in from the image type's settings. They use the same rules as the pictures: the Notes setting chooses the notes with the most total energy over the whole file (the same notes in every window, equal energy to the lower note), the Threshold hides a note in a window when it is strictly below the percentage of the loudest note of the file. Both are worked out on the note strengths that are given to the measurement (the caller gives the same values the picture works on).
- **With the Notes setting, the notes are not "spread"**: the picture spreads the chosen notes over the whole grid to fill it; for the interval search the chosen notes stay where they are, in their own pitch, because chords depend on the real intervals between the real notes.
- **Measurement only**: as for Local Peaks (feature 023), nothing is added to the job request, the response, the settings page or the pictures; the code to record the data is the whole deliverable, to be used by a later feature.
