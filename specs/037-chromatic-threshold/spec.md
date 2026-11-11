# Feature Specification: Chromatic Decay Threshold

**Feature Branch**: `037-chromatic-threshold` (no git branch created; spec directory name only)

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "For chromatic decay, add a threshold parameter that allows us to set to 0 values below a certain % between 1 and 10.  The % is calculated relative to the max of the other smoothed values passed into circle_points"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Faint notes are set to 0 before the letters are charged (Priority: P1)

The user wants a **threshold** for **Chromatic Decay** (feature 035): a percentage **from 1 to 10** under which a note value is **set to 0**. The percentage is taken **relative to the largest of the smoothed note values that are given to the points calculation** (`circle_points`): a note whose smoothed value is **strictly below `threshold` percent of the largest smoothed value** is treated as 0, as if it did not sound. **0 means off**: no value is changed (the way the Threshold of the other image types works), and the default is off, so existing results do not change.

- **Where it acts**: on the **note values**, before the energy of each letter is worked out (the largest of its octaves) and before the five loudest letters are chosen. A note under the threshold therefore adds nothing to its letter's energy; a letter whose octaves are all under the threshold has no energy, **does not count among the five loudest** and gains nothing in that frame; and a faint note can no longer be the loudest octave of its letter (if the louder octave is also under the threshold the letter is silent, if not the louder one decides as before).
- **What the reference is**: the **largest value among all the smoothed values passed in**, in every frame (the whole file, as the Threshold of the other types does), not the largest of the frame. A passage that is quiet compared with the loudest passage of the file is therefore silent for the picture, whereas a quiet note next to a loud one in the same frame is dropped only if it is also quiet compared with the whole file.
- **The same simulation**: the threshold changes the gains, so the points, the taper (which depends on the circles over 32 points) and the picture follow; the decay (the receivers, the rate) and the rings of the beat are not changed by it.

**Why this priority**: It is the whole request: leakage and faint notes stop charging circles, so only the real notes light the ring.

**Independent Test**: Make values in which the letter C has a loud note (strength 100) and the letter E a faint one (strength 3), with a threshold of 5: E is under 5 percent of 100, so only C gains points; with a threshold of 2 or off, both gain.

**Acceptance Scenarios**:

1. **Given** a threshold of `t` percent and smoothed values whose largest is `M`, **When** the points are worked out, **Then** every note value strictly below `t / 100 x M` is treated as 0 and every other value is unchanged; a value exactly at `t / 100 x M` is kept.
2. **Given** a threshold of 0, **When** the points are worked out, **Then** the result is exactly what it is without a threshold.
3. **Given** a frame in which only faint notes sound (all under the threshold of the whole file), **When** the points are worked out, **Then** no letter gains in that frame (the circles only decay).
4. **Given** a letter whose loudest octave is under the threshold and another octave louder than the others but also under it, **When** the points are worked out, **Then** the letter has no energy and does not count among the five loudest.
5. **Given** more than five letters above the threshold, **When** the points are worked out, **Then** the five loudest gain as before (the threshold only removes notes, it does not change the ranking of the rest).
6. **Given** the same values and settings, **When** the points are worked out twice, **Then** the results are identical.

---

### User Story 2 - The setting can be chosen for Chromatic Decay on the page and in the request (Priority: P2)

The Threshold setting already exists for the other image types (the request field `threshold`, a number from 0 to 10, 0 being off, and the Threshold slider on the page); for Chromatic Decay it is **accepted and ignored** today. The user wants it to **work for Chromatic Decay**: the job passes the field to the points calculation, with the values smoothed by the Data smoothing settings, and the **page shows the Threshold control in the group of Chromatic Decay** (next to its Decay rate). Its range, its readout (Off, then the percentage), its info text and its validation are those of the existing setting; the help says what it does for this type. The summary of the result shows it for Chromatic Decay too. The other image types are not changed.

**Why this priority**: The calculation is useful on its own (Story 1); this makes it reachable without code.

**Independent Test**: Choose Chromatic Decay: the group has Decay rate and Threshold; set the threshold to 5 and make frames of a file with a loud and a faint note: the circle of the faint note's letter stays at its smallest size; with the threshold off it grows.

**Acceptance Scenarios**:

1. **Given** the page with Chromatic Decay chosen, **When** it is shown, **Then** the Threshold control is in the Chromatic Decay group (0 to 10, Off at 0, default Off) and is not shown for the types that do not use it, whose groups are unchanged.
2. **Given** a request with `image_type=chromatic-decay` and a `threshold` of 5, **When** frames are made, **Then** the circles are charged from the note values with the faint ones set to 0, and the response echoes the threshold.
3. **Given** a `threshold` outside 0 to 10 or not a number, **When** it is sent, **Then** it is refused with the existing message before the file is read.
4. **Given** no `threshold`, **When** frames are made, **Then** the frames are exactly what they were before this feature.

---

### Edge Cases

- A file with no sound at all: the largest value is 0, so nothing is below `t / 100 x 0`: nothing changes (the same as the other types: "when the reference is 0, nothing is hidden").
- A value exactly at the threshold is kept (only strictly below is set to 0).
- The columns after the 84th (the four higher analysis notes) are part of the "values passed in" and so of the largest value, as for the Threshold of the other types, but are never notes of a letter.
- The threshold is a share of the **smoothed** values (after the Data smoothing), not of the raw ones.
- The beat (Local peaks) and the rings in the middle do not depend on the threshold.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The points calculation of Chromatic Decay MUST take a **threshold**, a number from 0 to 10 (percent; 0 is off and the default), checked as the Threshold of the other image types is.
- **FR-002**: With a threshold `t` above 0, every note value strictly below `t / 100` of the **largest of all the smoothed values passed in** (every frame, every column) MUST be treated as 0 before the letters' energies are worked out; a value at or above it MUST be unchanged; with `t` of 0, or a largest value of 0, nothing is changed.
- **FR-003**: A letter whose octaves are all treated as 0 in a frame MUST have no energy, MUST NOT count among the five loudest letters and MUST gain nothing in that frame.
- **FR-004**: The threshold MUST NOT change the decay (the receivers, the rate, the loss), the beat or the rings; it acts only through the gains.
- **FR-005**: The tapers of the simulation (`circle_tapers`) MUST be those of the same thresholded simulation, so that the two functions stay consistent.
- **FR-006**: The `threshold` field of the request MUST apply to Chromatic Decay (validated as it is for every type, with the existing message), be passed on with the smoothed values, and be echoed in the response as before; without it the frames MUST be identical to those before this feature.
- **FR-007**: The page MUST show the Threshold control in the Chromatic Decay group (and the summary MUST show the threshold for this type), with the existing range, readout and validation; the other image types' groups MUST NOT change.
- **FR-008**: The help of the Threshold and of Chromatic Decay MUST say what the threshold does for this type.
- **FR-009**: Results MUST be repeatable: the same values and settings MUST give identical results.

### Key Entities

- **Threshold**: a number from 0 to 10, a percent of the largest smoothed note value of the file; 0 is off.
- **Floor**: `threshold / 100 x (the largest smoothed value passed in)`; a note value strictly below it is treated as 0.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For any values and any threshold from 1 to 10, every value below the floor is 0 for the letters and every other value is unchanged, checked for all the values of random arrays against a plain loop.
- **SC-002**: With a threshold of 0 (or not given) the points, the tapers and the frames are identical to what they were before this feature, for every file tried.
- **SC-003**: With a loud note and a faint one whose strengths are `a` percent apart, the faint note's circle is charged for thresholds below `a` and not charged for thresholds above `a`, on the points and on the picture.
- **SC-004**: A value outside 0 to 10, or not a number, is refused in 100% of the requests tried, with the existing message and nothing left behind.
- **SC-005**: The frames of every other image type are identical to what they were before this feature.

## Assumptions

- **The existing Threshold setting is reused**, not a new field: the request field `threshold` (0 to 10, 0 off), the page control and the message already exist and are ignored by Chromatic Decay; making them apply is the smallest change and keeps one setting with one meaning across the types. The user's "between 1 and 10" is read as the range 1 to 10 with 0 meaning off, as for the other types (0 is not a percentage that sets anything to 0).
- "**The max of the other smoothed values passed into circle_points**" is read as the largest value of the whole `values` array given to `circle_points` (all frames, all columns), the way the Threshold of the other types uses the largest smoothed value of the whole file; and "below" is read as strictly below, as there.
- The threshold is applied to the **note values** (the smoothed values) before the octaves are combined into letters, not to the letter energies after the combination, so that a faint octave cannot be the loudest of its letter's octaves.
- The **page control and the request field** are included in this feature, although the user spoke of a parameter of `circle_points`, because both already exist and only need to be switched on for this type.
- This feature changes Chromatic Decay only; Decay, Decay Exp and the others are unchanged. The beat and the rings are measured from the audio and do not depend on the note values.
