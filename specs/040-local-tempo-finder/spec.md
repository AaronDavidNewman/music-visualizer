# Feature Specification: Local Tempo Finder

**Feature Branch**: `040-local-tempo-finder`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User description: "I'd like to change the local peak into more of a local tempo finder, using the Rhythm Circles. The prominence can be hard-coded at 20%. The minimum distance should be defaulted to 350ms. The default tempo will be 120bpm. We will keep track of the following things: 1: n samples (default, 5), the current tempo (which starts default at 120), the current tempo / 2, and the current tempo/1.5. For each new sample, we consider 1) compare it to the current tempo, the current tempo/2 (e.g. 60bpm), and the current tempo/1.5. (90bpm). Take the closest of those 3 values and compare to the current tempo. If it is within 1 standard deviation of the last 5 samples, use the average between the sample and the mean (so, a weighted average). Otherwise, increase/decrease the current tempo by 1 standard deviation. If the current tempo is above 156, consider that the tempo is 78 (1/2). If the current tempo is below 60bpm, move it to 120bpm. I think when you do this, you need to throw out the samples and start over. So the tempo will always be between 60 and 156 bpm. The circles will be: inner circle is local peak and rate of change, just like now. Second set outwards is current tempo and rate of change of current tempo. Next 2 rings are tempo/2 and tempo/1.5, and rate of change of same. To test the algorithm, sonata.wav is about 116 bpm throughout, grouped by 3 so frequently we will detect 1.3s peaks. 'almost2.wav' is mostly around 180 bpm, grouped by fours so we should gravitate towards 90 bpm. For other image types, we will want to consider the current tempo rather than the local peak."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A steady current tempo that follows the music (Priority: P1)

A user visualizes a piece of music. Today the tempo shown is whatever the latest energy peak says, so it jumps whenever a peak falls on the wrong place: a peak that is missed (the tempo halves), a tied note (a peak between beats), a group of three beats (a peak every 1.3 seconds). The user wants a **current tempo** that starts at 120 beats per minute and is nudged by each new peak, so that one odd peak does not throw it, and that always stays between 60 and 156 beats per minute (the range a person calls "the tempo"). Peaks that sit at half the tempo, or at two thirds of it, count as evidence for the current tempo, not against it.

**Why this priority**: This is the heart of the change: the tempo finder itself. Everything else (the circles, the other image types) only displays it.

**Independent Test**: With a list of peak times alone (no audio), feed them in order and read the current tempo after each: for evenly spaced peaks at 116 beats per minute, it settles close to 116; for peaks spaced at half that rate, it still settles close to 116 (the peaks at half the tempo count as the tempo), and one stray peak moves it only slightly.

**Acceptance Scenarios**:

1. **Given** no peak yet, **When** the current tempo is read, **Then** it is 120 beats per minute (and half of it is 60, two thirds of it 80).
2. **Given** peaks at a steady 100 beats per minute, **When** the peaks are fed one by one, **Then** the current tempo moves from 120 toward 100 and stays near it.
3. **Given** a current tempo of 116 and a new peak whose tempo is 58 (half), **When** it is considered, **Then** it is taken as evidence for 116 (it is compared as the tempo it stands for), and the current tempo stays near 116.
4. **Given** a current tempo of 120 and a peak far from it and from all the related tempos, **When** it is considered, **Then** the current tempo moves by one standard deviation of the latest samples toward it, not all the way to it.
5. **Given** the current tempo would go above 156, **When** it is updated, **Then** the tempo becomes 78, the collected samples are thrown away and the finder starts over from that tempo.
6. **Given** the current tempo would go below 60, **When** it is updated, **Then** the tempo becomes 120, the collected samples are thrown away and the finder starts over from that tempo.
7. **Given** any file, **When** the whole measurement is read, **Then** the current tempo is never below 60 nor above 156 beats per minute at any moment.

---

### User Story 2 - Rhythm Circles show the tempo layers (Priority: P1)

The user opens Rhythm Circles and sees **four** concentric circles, in two pairs, from the innermost outwards: **the local peak** (as it is today: the tempo of the latest peak) and its rate of change; then **the current tempo** and its rate of change. (The first version of this feature had eight circles, adding half of the current tempo and two thirds of it, each with its rate of change; the user asked on 2026-11-14 for four because eight were hard to read, the inner ones especially.) The circles turn at the speeds of these tempos, so a viewer sees the stable tempo and the raw peaks that feed it at the same time.

**Why this priority**: It is how the tempo finder is seen, and the way the user wants to judge it (by eye, on real files).

**Independent Test**: Make Rhythm Circles for a file and check, with a time in the file, that the two pairs turn at the speeds of the local peak and the current tempo, and that each rate-of-change circle turns at the change of its tempo per second.

**Acceptance Scenarios**:

1. **Given** Rhythm Circles of a file, **When** the pictures are made, **Then** there are four circles: the current tempo, its rate of change, the local peak, its rate of change, from the outside in.
2. **Given** a moment where the current tempo is 120, **When** the picture is made, **Then** the tempo circle turns at 120 revolutions per minute.
3. **Given** a moment where the current tempo changes, **When** the picture is made, **Then** the rate-of-change circle of the tempo turns at the change per second, in the same direction convention as today (clockwise when it speeds up).
4. **Given** the settings, **When** the page is opened for Rhythm Circles, **Then** Minimum distance defaults to 350 ms and there is no Prominence control (it is fixed at 20%).

---

### User Story 3 - It finds the right tempo on the two sample files (Priority: P1)

The tempo finder is judged on two files in `backend/audio`: **sonata.wav** is a steady tempo of about 116 beats per minute throughout, but its beats come in groups of three, so peaks about 1.3 seconds apart are frequent; the current tempo must stay near 116 anyway. **almost2.wav** is mostly around 180 beats per minute in groups of four; the current tempo must not stay at 180 (that is above the 156 limit) but gravitate toward 90.

**Why this priority**: These are the only real-music checks the user gave, and they cover both of the failures that the finder is meant to cure.

**Independent Test**: Measure each file and look at the current tempo over time: for sonata, most of the time within a few beats per minute of 116; for almost2, most of the time near 90.

**Acceptance Scenarios**:

1. **Given** sonata.wav, **When** the current tempo is followed over the whole file, **Then** the share of time (after the first 10 seconds) that it is within 10% of 116 beats per minute, and the number of restarts, are measured and reported, and the tempo is never outside 60 to 156.
2. **Given** almost2.wav, **When** the current tempo is followed over the whole file, **Then** the share of time (after the first 10 seconds) that it is within 10% of 90 beats per minute, and the number of restarts, are measured and reported, and it is never above 156.

*Why these are reported and not pass/fail (planning, 2026-11-14)*: a first run of the rule exactly as written, on the peaks of the two files at Minimum distance 350 ms and Prominence 20%, gave **22%** of the time near 116 with 40 restarts for sonata.wav and **7%** near 90 with 22 restarts for almost2.wav. The peaks of both files are mostly at 100 to 170 beats per minute, and the rule has no way to take a sample **above** the tempo as evidence for it (it only maps samples to the tempo, its half and its two thirds), so those samples push the tempo up to 156 and it restarts. The thresholds the user cares about are therefore a result to look at (see `research.md`), not something the rule as written can be made to pass by tests.
3. **Given** either file, **When** the tempo finder is run twice, **Then** the results are identical.

---

### User Story 4 - The other image types keep the local peak for now (Priority: P2)

The image types that follow the beat today (Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe, and Contour with Beat coloring) use the position of a frame in the local energy peak. The user wants them to consider the current tempo in the end ("we will want to"), but **not in this feature**: here only Rhythm Circles shows the tempo, and the other types keep reading the local peak, so the finder can be judged on Rhythm Circles first. Moving the other types to the tempo is a later feature.

**Why this priority**: It keeps this change small and safe; the only effects on the other types are the two settings changes (Minimum distance now defaults to 350 ms, and Prominence is fixed at 20%), which they share with Rhythm Circles because they use the same measurement.

**Independent Test**: Make the pictures of an image type that follows the beat before and after, with Minimum distance set to the same value and Prominence at 20%: they are identical.

**Acceptance Scenarios**:

1. **Given** an image type that follows the beat, **When** its pictures are made with the same Minimum distance and a Prominence of 20%, **Then** they are identical to those made before this feature.
2. **Given** an image type that follows the beat, **When** the page is opened, **Then** its Local peaks group shows Minimum distance (default 350 ms) and no Prominence control.

---

### Edge Cases

- No peak at all (silence, or a very high Minimum distance): the current tempo is 120 for the whole file, and the circles turn at the defaults (peak circle at the default rate 60 as today, tempo layers at 120, 60 and 80).
- A standard deviation of 0 (fewer than 2 samples, or all samples identical, as in a perfectly steady beat): a **minimum step of 1 beat per minute** is used in place of the standard deviation, both for the "within one standard deviation" test and for the move, so the tempo is never stuck (a steady 116 moves the tempo from 120 down by 1 per peak, never overshooting the sample).
- A move that would pass the sample: the tempo stops at the compared sample; a move by a standard deviation (or the minimum step) never goes beyond it.
- Fewer than 5 samples at the start, or right after a restart: the mean and the standard deviation are those of the samples that exist.
- A peak that is exactly as close to two of the three values (the tempo, half of it, two thirds of it): the nearest in ratio is chosen; on a tie the plain tempo is chosen.
- Moving by one standard deviation that would pass 156 or 60: the limits apply after the move (the tempo goes to 78 or 120 and the samples are thrown away); it never stays outside 60 to 156.
- Very long gaps between peaks (several seconds): the tempo of the sample is very low; it is matched to the nearest of the three values and normally moves the current tempo by one standard deviation only.
- Restart: after the samples are thrown away, the next peak starts the count of samples at 1 again; the tempo that was set stays.
- Minimum distance (100 to 2000 ms) keeps its range and its error message; only its default changes, from 100 to 350.
- A request that still sends a Prominence value (an older client): it is accepted and ignored, as other settings that do not apply are.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST measure the local peaks with a fixed Prominence of 20% (no longer a setting) and a Minimum distance that defaults to 350 ms (still 100 to 2000 ms).
- **FR-002**: The system MUST keep a **current tempo** that starts at 120 beats per minute and is updated, in order, by each peak after the first (the tempo of a peak is 60 divided by the seconds since the previous peak). The system MUST also expose the current tempo divided by 2 and the current tempo divided by 1.5 at every moment.
- **FR-003**: The system MUST keep the latest **5 samples** (fixed) and compute their mean and standard deviation; fewer samples while fewer exist. Where the standard deviation is 0, a minimum of 1 beat per minute MUST be used in its place.
- **FR-004**: For each new sample, the system MUST compare it with the current tempo and the related tempos (**revised 2026-11-14**: half of it, two thirds of it, **and now also twice it and one and a half times it**: the user asked to consider faster tempos if they are more suitable), choose the closest in ratio, and, **only when the sample is within 15 percent of that related tempo (otherwise it stands for itself: the user noticed that steady peaks at 150 beats per minute must lead the tempo to 150, not to 100)**, take the sample as standing for the current tempo at that ratio (a sample closest to the half is doubled, to the two thirds multiplied by 1.5, to the double halved, to one and a half times it multiplied by 2/3, to the tempo kept) before comparing it with the current tempo.
- **FR-005**: If the compared sample is within one standard deviation of the latest samples, the current tempo MUST become the average of the sample and the mean of the latest samples; otherwise the current tempo MUST be increased or decreased by one standard deviation (toward the sample).
- **FR-006**: If the current tempo is above 156 beats per minute it MUST become 78, and if it is below 60 it MUST become 120; in both cases the collected samples MUST be thrown away and the sample count starts again, so the current tempo is always from 60 to 156.
- **FR-007**: The current tempo MUST be known for every moment of the file (a step function of time that changes at each peak), and the changes of it and of the local peak's tempo per second (the difference between two consecutive peaks divided by the seconds between them) MUST be available.
- **FR-008**: Rhythm Circles MUST draw **four** circles, from the inside out: the local peak's tempo and its rate of change (as now), the current tempo and its rate of change. The aggregated tempo circles of 8, 4 and 2 peaks, and (revised 2026-11-14) the circles of half and two thirds of the current tempo, MUST NOT be drawn. The speed, direction and notch conventions of Rhythm Circles do not change.
- **FR-009**: The settings page MUST not show Prominence, MUST default Minimum distance to 350 ms, and the request MUST ignore a Prominence that is sent.
- **FR-010**: The tempo finder MUST be deterministic and MUST NOT make the pictures noticeably slower to make.
- **FR-011**: The image types other than Rhythm Circles MUST keep reading the local peak (user story 4); the current tempo is only shown by Rhythm Circles in this feature, and the pictures of the other types are unchanged apart from the shared settings of FR-001 and FR-009.
- **FR-012**: The finder MUST be tested with peak times alone (no audio) and with the two sample files, sonata.wav and almost2.wav, as in stories 1 and 3.

### Key Entities *(include if feature involves data)*

- **Sample**: The tempo, in beats per minute, of one interval between two peaks (60 divided by the seconds between them). The latest 5 of them are kept, with their mean and standard deviation.
- **Current tempo**: The tempo the finder believes at a moment of the file; starts at 120, always from 60 to 156 beats per minute; changes at each peak.
- **Related tempos**: Half the current tempo, two thirds of it, twice it and one and a half times it, the other values that a sample is compared with (they are not drawn).
- **Rate of change**: For a tempo, the difference between its value at a peak and at the previous peak, divided by the seconds between them (beats per minute per second, drawn as revolutions per minute).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every file and at every moment, the current tempo is from 60 to 156 beats per minute.
- **SC-002**: For evenly spaced peaks at a steady tempo from 70 to 150 beats per minute (and at half that tempo), the current tempo settles, after 40 peaks, at a value from 60 to 156 where the steady tempo is the tempo, or one of the related tempos of it, within 5% (for 100, 116, 150 and 155 beats per minute the tempo settles at the steady tempo itself; 70 settles at 105, because 70 is two thirds of 105: the rule cannot tell those apart).
- **SC-003**: For evenly spaced peaks, once the tempo has settled it no longer changes (it is a fixed point of the rule), and a single stray peak moves it by less than 10% of its value.
- **SC-004**: On sonata.wav and on almost2.wav, the share of time near 116 and near 90 beats per minute, the number of restarts and the tempo over time are measured and reported (see user story 3); the tempo is never outside 60 to 156 beats per minute and the result is the same on every run.
- **SC-005**: With the faster tempos considered and the 15 percent tolerance (revised 2026-11-14) the finder scores 49% (sonata.wav, 4 restarts) and 35% (almost2.wav, 0 restarts); before the tolerance 27% (2 restarts) and 49% (1 restart); the rule with only the tempo, its half and its two thirds scored 22% (40 restarts) and 7% (22 restarts). The numbers are reported by the sample-file test, not gated.
- **SC-006**: A single stray peak (a peak at a tempo far from all three values) moves the current tempo by less than 10% of its value.
- **SC-007**: Rhythm Circles has four circles in the stated order, and the tempo circle turns at exactly the speed of the current tempo and the peak circle at that of the local peak at any moment.
- **SC-008**: The time to make Rhythm Circles for a 5-minute file does not grow by more than 5%.

## Assumptions

- The samples are the tempos of the intervals between peaks, as in Rhythm Circles today (60 divided by the interval in seconds); the first peak has no interval, so it gives no sample and the tempo stays 120 until the second peak.
- "The mean" in the weighted average is the mean of the latest 5 samples, taken as the tempos they stand for after FR-004; the standard deviation is that of the same samples (population standard deviation).
- "Within one standard deviation" is inclusive: a difference equal to the deviation is within.
- "Increase/decrease by 1 standard deviation" moves toward the compared sample.
- Above 156 the tempo becomes **78**, exactly as written (156 halved), not the half of the actual value; below 60 it becomes 120.
- The aggregated-tempo circles (8, 4, 2 peaks) of Rhythm Circles are replaced, not kept beside the new ones; of the first version's circles of half and two thirds of the current tempo only the tempo itself stays, so the picture has four circles and the colormap spread `(k - 1) / 3`.
- The local peak circle (innermost) keeps its present meaning: the tempo of the latest peak (the default rate 60 before the first), and its rate of change.
- The number of samples kept (n) is fixed at 5: it is not a setting, and there is no new control or request field. The minimum distance keeps its control.
- The minimum step of 1 beat per minute (for a standard deviation of 0) is my choice of a number; the user chose the rule, not the value.
- Prominence is removed from the page for every image type that showed it and a value sent in a request is ignored.
- Existing tests of the local peaks measurement itself (finding peaks, the energy line) keep their meaning; tests of the removed aggregated circles are replaced.
