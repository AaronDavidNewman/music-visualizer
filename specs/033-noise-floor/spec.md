# Feature Specification: Noise Floor

**Feature Branch**: `033-noise-floor` (no git branch created; spec directory name only)

**Created**: 2026-11-07

**Status**: Draft

**Input**: User description: "implement a noise floor for both notes and chords.   Any note that is below a fixed threshold, such as -60db, should be treated as 0.  Don't count it as a note or a chord, regardless of whether the image type supports a threshold."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A note that is practically silent is not a note (Priority: P1)

The note analysis gives every analysis window a strength for each note, and the strengths are never exactly zero: the spectrum always leaks a little into notes that nobody is playing, and recordings carry hiss and room noise. Today such a faint value is a value like any other: it can be one of "the loudest notes" of a quiet moment, it is drawn, and it is counted. The user wants a **noise floor**: a **fixed level, such as −60 dB**, under which a note is **treated as 0**, as if it did not sound. It is **not counted as a note**, whatever the picture.

**What is a faint note**: a note whose strength is more than 60 dB below the loudest note of the whole file, which is to say below one thousandth (0.1 percent) of the strength of the loudest note anywhere in the file. (Strengths are amplitudes, so −60 dB is a factor of 1,000.) A note exactly at the floor is still a note. Such a note has the strength 0 in every window of the file.

**Why this priority**: It is the whole feature for the notes, and the chords (Story 2) are built on it. Without it the pictures that pick "the loudest notes" fill the places they have with leakage whenever the music is quiet or sparse.

**Independent Test**: Make a file whose loudest note has strength 1.0 and add a note of strength 0.0009 and one of 0.001. With the floor, the first is 0 in every window; the second is unchanged. Measured with the pictures that choose the loudest notes (Decay's five loudest notes, the Circles' strongest notes, the Notes shown of Polar Chords): a note of strength 0.0009 never gets a circle or a bar, even when fewer notes than the picture could show are sounding.

**Acceptance Scenarios**:

1. **Given** a file whose loudest note has strength `P`, **When** the notes are analysed, **Then** every note whose strength is strictly below `P ÷ 1000` is 0 in every window; a note of exactly `P ÷ 1000` or more is unchanged.
2. **Given** a quiet moment in which only one note sounds clearly and every other note is more than 60 dB below the loudest note of the file, **When** a picture that shows the `N` loudest notes is made, **Then** it shows one note, not `N`.
3. **Given** a window in which every note is below the floor, **When** the picture is made, **Then** it is the picture of a silent window (no bars, circles or points added), however the values compare with each other.
4. **Given** a file with no sound at all (every strength 0), **When** the notes are analysed, **Then** nothing changes (there is no loudest note and nothing to compare).
5. **Given** the same file and settings, **When** it is made twice, **Then** the results are identical.

---

### User Story 2 - A note that is practically silent is not part of a chord (Priority: P1)

The chord measurement (features 031 and 032) works on the same note strengths. The noise floor must hold for it too: a note below the floor is **not a note of a chord and is never counted as a chord note**, and a window whose notes are all below the floor has **no chord**. This is true of the chord measurement itself, for any array of strengths it is given, and not only of the pictures that happen to use it.

**Why this priority**: The chord measurement looks at up to six letters of a window and tries every choice of them, so leakage in unplayed notes can complete a chord that nobody played. It is as important as Story 1 and is the same rule applied to the chords.

**Independent Test**: A window with C, E and G loud and a note of Bb 61 dB below the loudest note of the file: the chord is the major triad, not a seventh chord. A window whose only notes are below the floor: no chord. A faint G (61 dB down) with a loud C and E: the third `(4)`, not the triad `(4, 7)`.

**Acceptance Scenarios**:

1. **Given** the notes C, E, G at full strength and Bb 70 dB below them, **When** the chord is measured for the types `(4, 7)` and `(4, 7, 10)`, **Then** `(4, 7)` is recorded, with the notes C, E and G only.
2. **Given** C and E at full strength and G at a strength below the floor, **When** the chord is measured for `(4)` and `(4, 7)`, **Then** `(4)` is recorded; G is not in the chord and is not in the recorded notes.
3. **Given** a window in which every note is below the floor, **When** the chord is measured, **Then** no chord is recorded for it.
4. **Given** the octaves of one letter, each below the floor but adding up to more than the floor, **When** the chord is measured, **Then** the letter does not sound (the notes are 0 first, then the octaves are combined).
5. **Given** a picture that shows a chord (Polar Chords), **When** a chord bar is drawn, **Then** its strength is worked out from the notes of the chord, which are all at or above the floor.

---

### User Story 3 - It is fixed, for every picture, with or without a Threshold (Priority: P2)

The floor is **not a setting**. It has no field in the job request, no control on the page and no value to choose: it is always on, at the same level, for **every image type**, including the ones that have no Threshold setting. Where an image type does have a Threshold, the two work together: a note is hidden if it is below the floor **or** below the percentage the user chose; the stricter of the two decides, and a Threshold of 0 does not switch the floor off.

**Why this priority**: It states the scope of Stories 1 and 2 (fixed, universal, nothing for the user to configure), and it is small once they exist.

**Independent Test**: Make the same file with every image type, with and without a Threshold, and with a Threshold above and below 0.1 percent: in each, a note 70 dB below the loudest is not counted. The job request and the page are unchanged.

**Acceptance Scenarios**:

1. **Given** any image type, **When** a job is made without any new field, **Then** the floor applies.
2. **Given** an image type with a Threshold of 0 (hide nothing), **When** the picture is made, **Then** notes below the floor are still not counted or drawn.
3. **Given** a Threshold of 5 percent, **When** the picture is made, **Then** the notes below 5 percent are hidden as before (the floor, at 0.1 percent, adds nothing to it).
4. **Given** the settings page and the job request, **When** this feature is added, **Then** they are exactly as before: no new control, no new field, no new message.

---

### Edge Cases

- **Exactly at the floor** (strength `P ÷ 1000`): counted (the floor hides notes *strictly below* it, like the Threshold setting).
- **A silent file** (the loudest strength is 0): nothing is below anything, nothing changes.
- **A file with one very loud moment** (a click, a clap): the floor is measured against the loudest note of the whole file, so the quiet music around a loud click can fall below it and disappear. That is what a file-wide level means; the Threshold setting already behaves like this.
- **The four notes above the 84 piano notes** are not drawn, but they are analysed: a strength there counts for the loudest note of the file (as in the Threshold setting), so a loud note there raises the floor for all.
- **Several windows with the same note**: each window is judged by its own strength; a note can be above the floor in one window and below it in another.
- **A chord whose weakest note is just above the floor**: it is a chord; the floor never changes which chord is recorded for notes that are all above it.
- **Smoothing**: the pictures smooth the note strengths over time; a note that is below the floor in the analysis is 0 before the smoothing, so it can no longer reach above the floor by being mixed into the next frames with a louder note's strength. (The smoothed values themselves are not cut again.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The note strengths of every analysis window MUST be cut by a fixed noise floor: a note whose strength is strictly below one thousandth (−60 dB, as amplitudes) of the largest strength anywhere in the file MUST have the strength 0 in every window, and every picture and every measurement MUST work from these cut strengths. A strength at or above the floor MUST be unchanged.
- **FR-002**: The largest strength of the file that the floor is measured against MUST be the largest of all the analysed notes, including the four notes above the 84 piano notes that are not drawn, the same reference as the Threshold setting. With no sound (largest strength 0) nothing MUST change.
- **FR-003**: The floor MUST NOT be a setting: no field in the job request, no control on the settings page, no response key, no new message. It MUST be applied for every image type, whether or not the image type supports a Threshold.
- **FR-004**: A note below the floor MUST NOT be counted as a note: it MUST NOT take a place among "the loudest notes" of any picture (Notes shown, the strongest notes, the five loudest notes, the Notes setting's energy), and a window with no note at or above the floor MUST be the same as a silent window.
- **FR-005**: The chord measurement MUST ignore a note below the floor, whatever array of strengths it is given: the note MUST NOT be part of a chord or of the recorded notes, a letter MUST be made only of notes at or above the floor (the notes are cut before the octaves are combined), and a window with no note at or above the floor MUST record no chord.
- **FR-006**: Where an image type has a Threshold, a note MUST be hidden if it is below the floor or below the Threshold; the stricter MUST decide, and a Threshold of 0 MUST NOT switch the floor off.
- **FR-007**: The result MUST be deterministic: the same audio and settings give identical frames and identical chord records.
- **FR-008**: The documentation MUST state the level of the floor, what it is measured against, that it is fixed, that it applies to every picture and to the chords, and that a note exactly at the floor still counts.

### Key Entities *(include if feature involves data)*

- **Noise floor**: The fixed level, 60 dB below the loudest note of the file (one thousandth of its strength), under which a note's strength is 0.
- **Note strength**: The strength of one of the notes in one analysis window, as analysed; after the floor, either its analysed value or 0.
- **Loudest note of the file**: The largest note strength anywhere in the file (all analysed notes, drawn or not); the reference of the floor and of the Threshold setting.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In every file tested, 100 percent of the note strengths strictly below the loudest strength ÷ 1000 are 0 in the strengths the pictures work from, and 100 percent of the others are unchanged.
- **SC-002**: For a quiet or sparse passage (fewer clearly sounding notes than a picture shows), the picture shows exactly the sounding notes and no leakage notes, for every picture that picks the loudest notes.
- **SC-003**: In 100 percent of the chord windows tested, no recorded chord contains a note below the floor, and a window whose notes are all below it records no chord.
- **SC-004**: The result is the same for every image type with and without a Threshold, in 100 percent of the cases tested: the same notes are counted whatever the Threshold is, as long as it is at most the floor.
- **SC-005**: A file whose notes are all at or above the floor (or silent) gives exactly the same frames and chord records as before this feature, file for file.
- **SC-006**: The job request, the response and the settings page are identical to before the feature.
- **SC-007**: Measuring a 60 second file takes no more than one second longer than before.

## Assumptions

- **−60 dB means a factor of 1,000 in strength.** The note strengths are the magnitudes of the spectrum (amplitudes), and 60 dB below an amplitude is 1/1000 of it (20·log10(0.001) = −60). If the strengths were powers it would be 1/1,000,000; they are not.
- **The reference is the loudest note of the file, not an absolute level.** The strengths of the analysis are not on a decibel scale tied to the recording level (they depend on the window size and on how the file was recorded), so "−60 dB" is taken as 60 dB below the loudest note of the file, the same kind of reference as the Threshold setting. "A fixed threshold" is read as a fixed ratio, not an adjustable one. An absolute level (dB below full scale) would need the strengths to be scaled to it first and is not done here.
- **One cut for everything.** The floor is applied once to the note strengths of the analysis, before smoothing and before anything is drawn or measured, so the pictures, the beat, the notes' energy and the chords all see the same notes. It is a change to what the existing pictures show for files with notes below the floor (those notes become the colour of silence, or are not counted); for a file whose notes are all above the floor nothing changes (SC-005).
- **The chord measurement applies the floor too**, so that it holds for any array it is given and not only for the analysed strengths: a note below the floor is cut at the start of the measurement. The chord measurement of feature 031 has its own much weaker noise floor (a letter under a millionth of the loudest letter of its window), made to hide rounding noise; this fixed floor covers it entirely (a letter that a millionth of its window's loudest letter lets through but a thousandth of the file's loudest note does not would need a window louder than the file), so the weaker one is removed (plan, research Decision 3).
- **Strictly below.** A note exactly at the floor counts, as in the Threshold setting ("strictly below hides").
- **The beat does not change.** The local energy peaks are measured from the audio itself, not from the note strengths, so the floor cannot reach them (checked in the plan).
- **Out of scope**: telling tonal from non-tonal sound (noise, speech, percussion): a loud noise is above the floor and is a note, and so are its leakage and its chords. Also a floor that follows the music (per window or per passage), an adjustable floor, and an absolute dB scale.
