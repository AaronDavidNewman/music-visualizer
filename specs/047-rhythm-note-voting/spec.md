# Feature Specification: Rhythm Circles Tempo Voting from Sustained Loudest Notes

**Feature Branch**: `047-rhythm-note-voting`

**Created**: 2026-11-25

**Status**: Implemented (2026-11-25); revised on 2026-11-25, 2026-11-26 and 2026-11-27 (five rounds), see the **Revision** paragraphs below

**Revision (2026-11-25, second round)**: two changes, both asked for by the user after trying the first version on `almost2.wav`. (1) **The points are not all 2**: a tempo that a length fits as a half, quarter, eighth or sixteenth note gets **2** votes, one that it fits only as a **dotted** note or a **triplet** gets **1** (a tempo gets the most of the values that fit, not their sum), so that when a measured length fits many tempos the plain ones rank above the dotted ones; FR-004 and the edge case below read "2 votes" for the plain note and "1 vote" for a dotted note or a triplet. A tempo that only a dotted note or a triplet fits can never rise above 1 vote while the spacing is steady (1 taken, 1 given). Triplets get 1 as well: the user named the dotted notes, I took the triplets with them (`TRIPLET_POINTS`, one constant to change). (2) **The starts come from the 60 ms analysis windows, not from the frames**, so the tempos no longer depend on the frame rate (spec 043: the frame rate only decides how many pictures are made): `note_starts()` is run on `AnalysisResult.frames` with 1000/60 rows a second and the time resolution is always 60 ms (a length fits within 30 ms). Measured results in research Decision 15.

**Revision (2026-11-26, third round)**: the **average tempo**, asked for by the user as a baseline before work on the starts. The first tempo jumps from start to start, so a new circle shows the **straight average of the first tempo after the latest start and after the 4 before it** (5 in all; fewer at the beginning of the file; `tempo_votes.average_tempos`, `AVERAGE_COUNT = 5`). The circles, from the outside in, are now: **(1) the average tempo, (2) its rate of change, (3) the raw first tempo, (4) its rate of change**, (5) the local peak, (6) its rate of change; the **second tempo is no longer drawn** (`ranked_tempos` still makes it). Wherever FR-008 to FR-010, SC-004 and the scenarios below say the first and the second tempo for the circles 1 to 4, read the average and the raw first tempo; the voting itself is unchanged. The user read "3rd and 4th circle the current raw tempo, the outer circle the average" as the layers' level-and-change pairs, so circle 2 is the rate of change of the average (my reading). See research Decision 16.

**Revision (2026-11-26, fourth round)**: the **starts** are found in a new way, after the experiments on the seven single-note piano samples and the five test files (`specs/047-rhythm-note-voting/research.md`, Decision 17). A start is now **the moment a note begins**: the peaks of the summed **rise** of the 84 notes in the 60 ms windows (a window is a start when its rise is the largest within 2 windows either side and at least 20% of the largest within 2 s either side; two starts under 120 ms apart are one), each **placed on the waveform** (the largest rise of the root-mean-square level of the two channels, from 0.10 s before to 0.05 s after the window's middle; starts that land within 30 ms of each other are one). The **time resolution of the fit** is 40 ms (it was 60 ms). The held loudest notes no longer decide the starts, so **Extra notes plays no part in Rhythm Circles** and its page control (group Held notes) is removed; the request still accepts 1 to 8 and ignores it, as for Contour. FR-001 (the starts), FR-006 (the resolution) and FR-011 (the Extra notes control) are replaced by this paragraph; the rest, the average of 5 and the six circles included, is as in the third round. The other image types are unchanged. Measured on the five files: see the README.

**Revision (2026-11-27, fifth round)**: after the user listened to `Thunderer.wav` (a march, 120 to 124 bpm) and the pop songs, five changes, all for Rhythm Circles only (`research.md`, Decision 18). (1) **Trills are left out**: a trill (a flurry of very short notes 1 or 2 semitones apart, heard as out of time) is found on the waveform (two neighbouring semitones that both sound and take turns 6 to 20 times a second), and within it, widened by 0.24 s at each end, the notes from one semitone below its lowest note upward make no starts; the lower instruments still do, and with nothing below, the tempo holds. (2) **A start votes with its time since each of the last 2 starts**, each tempo taking the better of the two points, so a note between two beats does not hide the beat. (3) **The votes are kept for a beat divided in 2 and for a beat divided in 3** (the beat a dotted quarter: two beats, a beat, a quarter, an eighth, a sixteenth 2 points; a dotted eighth, two quarters, three beats 1), and the meter whose best tempo has more votes gives the tempo (an equal best keeps the meter). (4) **A tie keeps the tempo already shown** (it went to the lower tempo). (5) **The default Vote limit is 40** (it was 20). FR-006 (one length per start), FR-007 (the note values, now for each meter), the ranking rule and the Vote limit default are replaced by this paragraph. Not solved: syncopated pop (`02_Mean_.wav`) is read as a beat divided in 3. Measured on nine files: see the README.

**Input**: User description: "update the rhythm circles image type to include sustained loudest notes in the rhythm calculation. Based on the difference in times of the beginning notes, we will try to find a consistent tempo based on the distances in starting time between the loudest notes. We will try to find a tempo between 76 and 144 beats per minute. We will consider that a note could be grouped in terms of 3 or 2. A note lasting between .208 and .416 seconds could be a 1/8 note in a tempo between 144 and 76. A note lasting twice as long could be a 1/4 note (1 beat) in that tempo. It could also be a dotted 1/4, lasting 1.5 beats. We should consider all of these, and use a voting system: the possible tempo with the most votes is the current tempo. To make this tractable, we will bin according to the standard metronome markings: 72+4n, between 76 and 144. Give a vote to all possible tempos based on if the note can be 1/2, 1/4, 1/8, 1/16, any of those dotted (1.5 times), or a triplet 1/3, 2/3. For the rhythm circles UI, keep the center 2 circles local peak and rate of change of local peak. For the rings outside of that, use the 1st and 2nd highest tempo, and their rates of change. So there will be 6 circles. The voting will work like this: each cycle (whenever a new note starts, after the first), subtract 1 from all tempos, and give 2 votes to each possible tempo. Vote totals can't go higher than some parameter that defaults to 20, and can't go lower than 0. This allows tempos to change over time. For now, leave all local peak logic in other image types the same."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A tempo found by voting on the spacing of the loudest notes (Priority: P1)

A user visualizes a piece of music. The tempo that Rhythm Circles shows today comes from the local energy peaks, and a peak is not always on a beat. The user wants the tempo to come from the **notes themselves**: every time a new one of the loudest notes starts, the time since the previous start is a note length, and that length could be a half, a quarter, an eighth or a sixteenth note, any of those dotted, or a triplet note, in any of a set of tempos. Each tempo that the length could fit gets votes; the tempos with the most votes are the tempos of the music, and because old votes fade (one is taken from every tempo at every new note) the tempo can change as the music does.

**Why this priority**: This is the heart of the change: the voting itself. The circles and the setting only display it.

**Independent Test**: With a list of note start times alone (no audio), feed them in order and read the votes of the 18 tempos and the first and second highest after each start: for starts spaced so that one tempo fits every spacing, that tempo's votes climb to the limit and it is first; when the spacing changes to fit another tempo, the first tempo loses votes (one per start) while the new one gains (one per start), and the order changes.

**Acceptance Scenarios**:

1. **Given** no note has started, **When** the votes are read, **Then** all 18 tempos (76, 80, 84 ... 144, that is `72 + 4n`) have 0 votes.
2. **Given** the first note starts, **When** the votes are read, **Then** they are still all 0 (a cycle needs a previous start; the first start gives no length).
3. **Given** a second note that starts exactly 0.5 seconds after the first (start times exact, so no time resolution is added to the tolerance), **When** the cycle runs, **Then** one vote is taken from every tempo (not below 0) and two are given to each tempo at which 0.5 seconds can be a note: 120 (a quarter note), 80 (a triplet quarter, 2/3 of a beat) and 88 and 92 (a dotted eighth, 3/4 of a beat, at the implied 90, which is half a bin from both); those four have 2 votes and the other 14 have 0.
4. **Given** a tempo with 20 votes (the default limit), **When** another note starts at a spacing that fits it, **Then** it stays at 20 (one is taken, two are given, and it is held at the limit).
5. **Given** a tempo with votes and a spacing that does not fit it, **When** a note starts, **Then** it loses one vote, and never goes below 0.
6. **Given** a spacing of a quarter of a second between starts and then a spacing of 0.4 seconds, **When** the cycles run, **Then** the tempos that fit only the first spacing lose votes one at a time while the tempos that fit the second gain, so the first and second highest change over time.
7. **Given** any list of starts, **When** the whole run is read, **Then** every vote total is a whole number from 0 to the limit at every moment.

---

### User Story 2 - Rhythm Circles shows six circles: two tempos from the vote and the local peak (Priority: P1)

The user opens Rhythm Circles and sees **six** concentric circles, in three pairs, from the outside in: **the highest-voted tempo** and its rate of change; **the second-highest-voted tempo** and its rate of change; then, unchanged, **the local peak** (the tempo of the latest peak) and its rate of change in the center. (Today there are four circles: the tempo finder's current tempo and its rate, then the local peak and its rate; the current tempo pair is replaced by the two voted tempos.) The circles turn at the speeds of these tempos, so a viewer sees at once the two tempos that the notes support best and the raw peak tempo.

**Why this priority**: It is how the voting is seen, and the way the user wants to judge it, by eye on real files.

**Independent Test**: Make Rhythm Circles for a file and check, for chosen times, that the six circles turn at the speeds of the first tempo, its rate of change, the second tempo, its rate of change, the local peak and its rate of change, from the outside in.

**Acceptance Scenarios**:

1. **Given** Rhythm Circles of a file, **When** the pictures are made, **Then** there are six circles: first tempo, its rate of change, second tempo, its rate of change, local peak, its rate of change, from the outside in.
2. **Given** a moment where the first tempo is 120, **When** the picture is made, **Then** its circle turns at 120 revolutions per minute (clockwise being positive), as the other tempo circles do.
3. **Given** a moment where the first tempo changes from 120 to 124 after a cycle that took 0.5 seconds, **When** the picture is made, **Then** the rate-of-change circle of the first tempo turns at 8 revolutions per minute (4 divided by 0.5), clockwise, from that cycle to the next.
4. **Given** the local peak circles, **When** a picture is made, **Then** they turn exactly as they do today.
5. **Given** the colormap, **When** the six circles are drawn, **Then** ring `k` (1 outer to 6 inner) has the color at position `(k - 1) / 5` and its notch the opposite color, the notch is an eighth of the circle, and the notch never jumps when a speed changes, as for the other Rhythm Circles conventions.

---

### User Story 3 - The notes that start are the sustained loudest notes (Priority: P1)

The notes whose starts are used are the **loudest notes of each frame, held while they last** (the "sustained loudest notes" of spec 044): a note starts when it **enters** the selection of loudest notes, and it does not start again every frame while it sustains. So a long note is one start, and a quiet note that is hidden by louder ones does not start until it is among the loudest. Rhythm Circles therefore uses the existing **Extra notes (k)** setting, like the other pictures that follow the loudest notes, and shows it on the page.

**Why this priority**: It is what makes the starts a rhythm of notes and not of every wiggle in the sound.

**Independent Test**: With a sound file with a sustained note and a series of short notes over it, count the starts: the sustained note is one start; each short note that becomes one of the loudest is one more. With two different Extra notes values, the starts can differ.

**Acceptance Scenarios**:

1. **Given** a note that sounds for 2 seconds among the loudest, **When** the starts are found, **Then** it gives one start, at the frame in which it first enters the selection.
2. **Given** several notes that enter the selection in the same frame (a chord), **When** the starts are found, **Then** they give one start for that frame, not several of zero length.
3. **Given** a request for Rhythm Circles, **When** it is made, **Then** the Extra notes value (default 2, as for the other pictures) takes part in choosing the loudest notes, and the page shows the Extra notes control for Rhythm Circles.
4. **Given** a silent file or a file in which no note ever starts, **When** the pictures are made, **Then** all votes stay 0 and the circles show the defaults (see Edge Cases).

---

### User Story 4 - A vote limit the user can set (Priority: P2)

The votes of a tempo cannot go higher than a **vote limit**, which defaults to 20. A low limit lets the tempo change quickly (a tempo is forgotten after few notes); a high one makes the tempo stay (it takes many notes to forget). The user can change the limit on the page when Rhythm Circles is chosen.

**Why this priority**: The voting works with the default; the setting lets the user tune how fast the tempo follows the music.

**Independent Test**: With the same list of starts, run the voting with limits of 5 and 20 and compare how many starts it takes for a tempo that has been leading for a long time to be overtaken after the music changes: it is faster with 5.

**Acceptance Scenarios**:

1. **Given** the page with Rhythm Circles chosen, **When** it is opened, **Then** a Vote limit control shows with the value 20 and an explanation.
2. **Given** another image type chosen, **When** the page is opened, **Then** the Vote limit control is not shown.
3. **Given** a request with a vote limit that is not a whole number from 1 to 100, **When** it is sent, **Then** it is refused with a message that says so, before the file is read and without leaving files behind.
4. **Given** a request without a vote limit, **When** it is made, **Then** the limit is 20.

---

### User Story 5 - The other image types are unchanged (Priority: P2)

The image types that follow the beat (Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe, Polychord, Spirograph, and Contour with Beat coloring) keep the local peak logic exactly as it is; the local peak circles of Rhythm Circles do too. Only the tempo pair that Rhythm Circles took from the tempo finder is replaced.

**Why this priority**: It keeps the change contained, as the user said ("for now, leave all local peak logic in other image types the same").

**Independent Test**: Make the pictures of any other image type before and after with the same settings: they are identical.

**Acceptance Scenarios**:

1. **Given** any image type other than Rhythm Circles, **When** its pictures are made with the same file and settings as before this feature, **Then** they are identical to those made before.
2. **Given** Rhythm Circles, **When** the pictures are made, **Then** the two local-peak circles are identical to the same circles made before this feature.

---

### Edge Cases

- **No starts, or only one**: all votes are 0 and no cycle has run. The first and second tempo circles then show the **starting tempo of 120 beats per minute** with a rate of change of 0, as the tempo circle did before the first peak (120 is one of the 18 tempos, `72 + 4 x 12`).
- **Fewer than two tempos with votes**: a place with no votes (a total of 0) shows 120 with no change, as above; the highest tempo with votes is first, and the second is the next with votes, or 120 if there is none. If 120 itself is the first, a place without votes shows 120 as well (the same value on both circles is allowed).
- **Ties**: tempos with the same number of votes are ranked by the lower tempo first. A tie never makes the tempo shown flicker (the order only changes when votes change).
- **A note length that fits no tempo** (very short, such as a chord's notes a frame apart, or very long, such as a silence of several seconds): the cycle still runs (one vote is taken from every tempo) and no tempo gets two.
- **A length that fits one tempo in several ways** (for example a length that is both a dotted eighth and, within the tolerance, a triplet quarter of the same tempo): the tempo gets 2 votes once per cycle, however many note values fit.
- **Notes that start in the same frame**: one start, so no length of 0 and one cycle.
- **A note that sounds again after dropping out of the selection**: a new start; a note that stays among the loudest never starts again (sustained notes are held, spec 044).
- **Vote limit of 1**: a tempo that fits goes to 1 and stays; the others stay 0.
- **Very short files and files that end between starts**: the tempos after the last start stay as they were; a frame before the first cycle shows the defaults.
- **The rate of change when two cycles are very close** (a few milliseconds): the rate is computed from the change and the seconds between the cycles as for the peaks (it can be large but is defined); two starts are never at the same time (one start for each frame).
- **Request fields**: a request that still sends settings that Rhythm Circles ignores (Threshold, decay rates, note layout) is accepted as before.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST find the **starts** of the sustained loudest notes of a file: a note **starts** in the frame in which it enters the selection of the loudest notes as chosen with **Extra notes (k)** (the held notes of spec 044); notes that start in the same frame make one start, and a note that stays in the selection does not start again.
- **FR-002**: The system MUST keep a **vote total for each of 18 tempos**, the metronome markings `72 + 4n` from 76 to 144 beats per minute (76, 80, 84 ... 144), all 0 before the first cycle.
- **FR-003**: The system MUST run a **cycle** at every start after the first. The **note length** of the cycle is the time from the previous start to this one, in seconds.
- **FR-004**: In each cycle, the system MUST **first subtract 1 from the votes of every tempo** (not below 0), **then give 2 votes to each possible tempo** (not above the vote limit): the vote totals are always whole numbers from 0 to the limit.
- **FR-005**: A tempo is **possible** for a note length if the length can be one of these notes at that tempo, where a beat is a quarter note and the length of a note of `b` beats at tempo `T` is `60 b / T` seconds: a half note (`b` = 2), a quarter (1), an eighth (1/2), a sixteenth (1/4), each of those dotted (1.5 times: 3, 1.5, 3/4, 3/8), or a triplet (`b` = 1/3 or 2/3). (For example, an eighth note is between 0.208 and 0.416 seconds at the tempos from 144 down to 72; a quarter note twice as long; a dotted quarter 1.5 beats.) A tempo gets its 2 votes **once per cycle**, however many of the note values fit.
- **FR-006**: A note length `L` **fits** a tempo bin `T` and a note value `b` (in beats) when **either** (a) the tempo that the length implies for that note value, `60 b / L`, is within **half a bin (2 beats per minute)** of `T`, **or** (b) the length of that note at `T`, `60 b / T`, differs from `L` by no more than **half the time resolution of the starts**. The time resolution is the larger of one frame of the picture and the 60 ms analysis step (a start can only be placed to a frame), and is an input of the voting so that start times given exactly can be voted with a resolution of 0. Both comparisons are inclusive.
- **FR-007**: The **vote limit** MUST be a setting, a whole number from **1 to 100**, with the default **20**, used for every tempo; a value that is not allowed MUST be refused with a message that says so, before the file is read and without leaving files behind. A request without the setting uses 20.
- **FR-008**: The system MUST rank the tempos by votes after every cycle: the **first** tempo is the one with the most votes, the **second** the next; ties are ranked by the lower tempo first. A place with 0 votes holds the starting tempo of 120 (see Edge Cases). The first and second tempo, and their changes, MUST be known at every moment of the file as step functions of time that change at each cycle.
- **FR-009**: The **rate of change** of the first tempo and of the second tempo MUST be, at each cycle, the difference between the tempo now and at the previous cycle divided by the seconds between the cycles (beats per minute per second, drawn as revolutions per minute), the same convention as the rate of change of the local peak and of the tempo that Rhythm Circles has today. Before the first cycle it is 0.
- **FR-010**: Rhythm Circles MUST draw **six** circles, from the outside in: the first tempo, the rate of change of the first tempo, the second tempo, the rate of change of the second tempo, the local peak's tempo and the local peak's rate of change. The tempo finder's current tempo and its rate of change MUST no longer be drawn. The speed, direction and notch conventions of Rhythm Circles (a tempo turns at as many revolutions per minute as its beats per minute, clockwise positive; the notch is an eighth of the circle; the angle is the running total of the speed so that a notch never jumps) do not change, and the ring `k` (1 outer to 6 inner) is at colormap position `(k - 1) / 5`.
- **FR-011**: Rhythm Circles MUST use the **Extra notes (k)** setting (request, default 2) to choose the loudest notes, and the page MUST show the Extra notes control for Rhythm Circles, in its Held notes group, as for the other image types that follow the loudest notes. Rhythm Circles still uses the Minimum distance of the local peaks (its local peak circles) with the prominence fixed as now.
- **FR-012**: The page MUST show a **Vote limit** control for Rhythm Circles only, with its explanation, and the job's answer MUST include the limit used. The notes' selection and the voting MUST be deterministic: the same file and settings give the same pictures.
- **FR-013**: The local peak logic MUST be unchanged for every image type, and the pictures of the image types other than Rhythm Circles, and the two local-peak circles of Rhythm Circles, MUST be identical to those made before this feature with the same settings.
- **FR-014**: The voting and the starts MUST be testable without audio (a list of start times in, the votes and the ranked tempos out) and with the two sample files, `sonata.wav` and `almost2.wav` in `backend/audio`, as in the success criteria.
- **FR-015**: Making Rhythm Circles MUST NOT take noticeably longer than before (finding the starts and the votes are small calculations on the frames of a file).

### Key Entities *(include if feature involves data)*

- **Start**: The time of a frame in which one or more of the sustained loudest notes enter the selection of loudest notes. The first start only begins the run.
- **Note length (cycle)**: The seconds from the previous start to this start. One cycle for each start after the first.
- **Tempo bin**: One of the 18 metronome markings `72 + 4n`, from 76 to 144 beats per minute, with its **votes** (a whole number from 0 to the vote limit).
- **Note value**: A length in beats a note can have: 2, 1, 1/2, 1/4, each times 1.5 for the dotted note, and the triplets 1/3 and 2/3. A tempo is possible for a length if some note value at that tempo has that length, within the tolerance.
- **Vote limit**: The highest number of votes a tempo can have; a setting, default 20.
- **First and second tempo**: The two tempos with the most votes after each cycle, each with a rate of change (the change of its value per second between cycles).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every file and at every moment, each of the 18 tempos has a whole number of votes from 0 to the vote limit, and there are exactly 18 tempos from 76 to 144 beats per minute in steps of 4.
- **SC-002**: For note starts given exactly, with no frame rounding, every cycle subtracts one vote from every tempo (not below 0) and then gives two to each possible tempo (not above the limit): for a list of starts the total of votes after a cycle can be predicted by hand and is reproduced exactly (the voting is tested with tables of lengths and the tempos that fit them).
- **SC-003**: With starts exactly 0.5 seconds apart (resolution 0), the tempos 80, 88, 92 and 120 are the only ones with votes, each has `k + 1` votes after `k` cycles and 20 after 19 cycles (the default limit) and then stays at 20, with 80 first and 88 second (ties go to the lower tempo); when the spacing then changes to one that fits other tempos, a tempo that fitted only the old spacing falls to 0 within 20 cycles (it loses one per cycle).
- **SC-004**: Rhythm Circles has six circles in the stated order, and at any moment the first and second tempo circles turn at exactly the revolutions per minute of the first and second tempo, their rate-of-change circles at the rates of change, and the local peak circles at the speeds they had before the feature.
- **SC-005**: A sustained note gives one start however long it sounds, a chord gives one start, and a note that sounds again after leaving the selection gives a new start (tested with synthetic sound files and with the starts found without the voting).
- **SC-006**: On `sonata.wav` (about 116 beats per minute, in groups of three) and on `almost2.wav` (about 180 beats per minute in groups of four, to be read as about 90), the share of time that the first or the second tempo is within 10% of 116 and of 90 beats per minute respectively, and the number of times the first tempo changes, are **measured and reported**, as for the tempo finder (the thresholds are a result to look at, not a gate), and the result is the same on every run.
- **SC-007**: The pictures of every other image type, and the local-peak circles of Rhythm Circles, are byte-for-byte the same as before the feature with the same settings.
- **SC-008**: The time to make Rhythm Circles for a 5-minute file does not grow by more than 5%.
- **SC-009**: A request with a vote limit that is not a whole number from 1 to 100 is refused every time, before the file is read, with no files left behind; the default is used when it is not sent.

## Assumptions

- **The note length is the time between starts**, as the user wrote ("the distances in starting time between the loudest notes"), not how long the note's sound actually lasts, which a sustained note makes unreliable; the "note lasting 0.208 to 0.416 seconds" is the time until the next start.
- **A start is the entry of a note into the selection of the loudest notes** (the held loudest notes of spec 044, with the five loudest notes as for Decay and the Chromatic types and the Extra notes setting k, default 2). The first start gives no length; a cycle runs at each start after it, as the user wrote.
- **Notes that start together are one start** (a chord or two notes entering in the same frame), so a length is never 0.
- **The note values are the user's list**: half (2 beats), quarter (1), eighth (1/2), sixteenth (1/4), each of those dotted (times 1.5), and the triplets 1/3 and 2/3 of a beat; a whole note and note values longer than that are not considered; a beat is a quarter note.
- **The tolerance (FR-006) is my choice**: the user binned the tempos at 4 beats per minute (half a bin is 2) but starts are only known to a frame (and the analysis step is 60 ms), so the half bin alone would almost never match a measured length. I add the second way to fit (within half the time resolution), which makes many tempos possible for a length (a short length such as 0.25 seconds fits most of the 18 tempos in one way or another): the voting works by the tempos that fit most lengths, over time. It can be tightened or widened later; the measurements of SC-006 are reported for it.
- **Several tempos can tie for the same length**: one length fits several tempos (for 0.5 seconds, 120 as a quarter and 80 as a triplet quarter, for instance), and a steady spacing cannot tell them apart; only a mix of lengths makes one tempo lead. This is a property of the user's rule, not a defect to fix here.
- **Ranking ties go to the lower tempo**, and a place with no votes shows 120: both are my choices, the user did not say.
- **The Vote limit** is a setting with the range 1 to 100 (my range) and the default 20 (the user's); the same limit applies to every tempo.
- **The tempo finder's current tempo (spec 040) is replaced in Rhythm Circles** by the two voted tempos, as "the rings outside of that" says; the tempo finder is not used by the other image types, and the code of the finder and of the local peaks is left as it is.
- **The rates of change** follow the convention of the existing circles: a step function that changes at each event (here, at each cycle), revolutions per minute equal to the beats per minute per second.
- **Starting tempo 120** (the tempo finder's start) is kept as the default for the voted tempos before there are votes.
- **Dependencies**: the held notes (spec 044), the Rhythm Circles of specs 038 and 040 (conventions and the local peak circles), and the sample files `sonata.wav` and `almost2.wav`.
- **Out of scope**: moving the other image types to the voted tempo; changing the local peak logic; a setting for the number of loudest notes; the note values longer than a half (whole note) or shorter than a sixteenth.
