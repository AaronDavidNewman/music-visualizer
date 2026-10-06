# Feature Specification: Note Smoothing

**Feature Branch**: `006-note-smoothing` (no git branch created; spec directory name only)

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "make each tile be a running average of itself and previous values of the same frequency. create a new 'smoothing' parameter, a float between 0.0 and 0.8. Smoothing parameter s operates on note x[n] : (s*x[n-1] + (1-s)*x[n] where x[n-1] is the previous example of this note. Obviously we skip the first sample. Use a slider to represent the float value so that the furthest-right value is 0.8."

## Clarifications

### Session 2026-10-06

- Q: Should smoothing also apply to the colors added by feature 007? → A: Yes. Each tile's **hue** is smoothed over the frames with the same smoothing: each tile's hue becomes *s* × (that tile's hue in the previous frame, already smoothed) + (1 − *s*) × (its hue in this frame). The first frame's hue is not changed. The hue is treated as a plain number from 0° to 360° (it is clipped to that range, not wrapped), so a tile whose hue jumps between the two red ends passes through the colors in between while it is being smoothed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Smooth each note over time (Priority: P1)

A user creating frames sets a **smoothing** value *s* from 0.0 to 0.8. For every note, each frame's value becomes a running average of that note's current value and its value in the previous frame: **new value = s × previous value + (1 − s) × current value**. The first frame has no previous frame, so it is left as it is. With smoothing 0 nothing changes. With a higher smoothing a tile no longer jumps on and off, but rises and fades gradually, so the animation looks calmer and flicker from short bursts is reduced. Each note is smoothed on its own, using only its own earlier values. Since feature 007 the tiles are colored, and the same smoothing is also applied to each tile's **hue**: each tile's hue becomes *s* × (that tile's hue in the previous frame, already smoothed) + (1 − *s*) × (its hue in this frame), with the first frame's hue left as it is, so colors change gradually too.

**Why this priority**: The tiles currently follow the music frame by frame and can flicker. Smoothing is the whole feature.

**Independent Test**: Use a file where one note is loud for a short moment and silent otherwise. At smoothing 0 the note's tile is bright in the frames where it sounds and black in the others. At smoothing 0.5 the tile rises over a frame or two and fades away over several frames after the note stops, instead of switching off at once. At smoothing 0.8 it fades more slowly still.

**Acceptance Scenarios**:

1. **Given** smoothing 0, **When** frames are created, **Then** they are identical to the frames the application produced before this parameter existed.
2. **Given** a note whose values in four consecutive frames are 0, 10, 0, 0 and smoothing 0.5, **When** frames are created, **Then** its smoothed values are 0, 5, 2.5 and 1.25. The first frame is unchanged, and each later value uses the previous smoothed value.
3. **Given** any smoothing, **When** frames are created, **Then** the first frame's values are the same as without smoothing.
4. **Given** a note that stops sounding, **When** smoothing is higher, **Then** its tile takes more frames to fade: with smoothing 0.5 the note's value falls below 10% of its starting value after 4 frames, with 0.8 after 11 frames, and with 0 in the first frame.
5. **Given** a note that starts sounding, **When** smoothing is higher, **Then** its tile takes more frames to reach full strength, by the same measure.
6. **Given** one note's values, **When** another note is loud or quiet, **Then** the first note's smoothed values do not change (each note is smoothed only from its own history).
7. **Given** a silent file at any smoothing, **When** frames are created, **Then** every tile is black.
8. **Given** the same file and settings, **When** frames are created twice, **Then** the images are identical.
9. **Given** a completed submission, **When** the user reads the results summary, **Then** it shows the smoothing used.

---

### User Story 2 - A smoothing slider with clear limits (Priority: P2)

The form has a **slider** for smoothing. Its left end is 0.0 and its right end is 0.8, and the user sees the current value as a number while dragging. It starts at 0.0 (no smoothing), moves in small steps (0.01), is disabled while a submission is running, and keeps its position after an error or a completed submission. The server accepts only numbers from 0.0 to 0.8 and refuses anything else with a clear message, so the limit cannot be bypassed.

**Why this priority**: The core feature works from a script without the form, but a slider keeps users inside the useful range and lets them try values quickly. It depends on Story 1.

**Independent Test**: Drag the slider fully left (0.0 shown) and fully right (0.8 shown). Neither end goes beyond its limit. Send requests directly to the server with 0.81, -0.1, `abc`, `nan` and an empty value: each is refused with the same message.

**Acceptance Scenarios**:

1. **Given** the page is opened, **When** the form is shown, **Then** the smoothing slider is at 0.0 and shows the value.
2. **Given** the slider, **When** it is dragged fully to the right, **Then** its value is exactly 0.8, and it cannot go higher.
3. **Given** the slider, **When** it is dragged fully to the left, **Then** its value is exactly 0.0, and it cannot go lower.
4. **Given** the slider is moved, **When** the user looks at the form, **Then** the number next to it shows the current value, rounded to two decimal places.
5. **Given** a request sent directly to the server with a smoothing below 0.0, above 0.8, or not a number, **When** it is processed, **Then** it is refused with a message that smoothing must be a number from 0.0 to 0.8, before any analysis starts, and nothing is left stored.
6. **Given** a request with no smoothing, **When** it is processed, **Then** smoothing 0.0 is used.
7. **Given** a submission that failed for any reason, **When** the user looks at the form, **Then** the slider is where they left it, and a corrected resubmission works without reloading the page.
8. **Given** a submission is running, **When** the user looks at the form, **Then** the slider is disabled like the other fields.

---

### Edge Cases

- **Only one frame**: A file with one frame has nothing to smooth, so it is unchanged at any smoothing.
- **Smoothing 0.8 is the highest**: A value of 1.0 would freeze the first frame forever, and values near it react far too slowly to be useful, so 0.8 is the limit.
- **Frame rate matters**: Smoothing is applied from one animation frame to the next. At a higher frame rate there are more frames per second, so the same smoothing fades faster in real time than at a lower frame rate.
- **Peaks look lower**: A short burst is spread over several frames, so its brightest frame is less bright than without smoothing. Because brightness is scaled against the loudest value in the file (now the loudest smoothed value), the whole picture is rescaled to match, so the loudest tile still reaches full white.
- **Float values**: The slider moves in steps of 0.01, so a value such as 0.3 is 0.30 and never shows rounding noise. A value typed or sent directly may have any number of decimals within the range.
- **Omitted notes**: The four highest notes are not drawn, but they are smoothed like every other note and still count when brightness is scaled.
- **Frames from the start of the file**: The first frame is never smoothed, even if the music is already loud, so there is no "fade-in from nothing" at the start.
- **Timing and counts**: Smoothing changes only the values in the frames. The number of frames, windows and the timing of each frame are the same as without it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST apply a smoothing value *s*, a number from 0.0 to 0.8 inclusive, to every note separately across the sequence of animation frames: for each frame after the first, the note's new value is *s* × (the note's new value in the previous frame) + (1 − *s*) × (the note's value in this frame, before smoothing).
- **FR-002**: The first frame MUST NOT be changed by smoothing.
- **FR-003**: With smoothing 0.0 the frames MUST be identical to those produced before this parameter existed.
- **FR-004**: Each note MUST be smoothed using only its own earlier values. Other notes MUST have no effect on it.
- **FR-005**: Smoothing MUST be applied to the note values of each frame before they are scaled to gray levels. The scaling against the loudest value in the file, the brightness setting, the octave grid layout and everything after them MUST work as before, on the smoothed values.
- **FR-006**: The system MUST accept a smoothing value with a submission, and MUST use 0.0 when none is given.
- **FR-007**: The server MUST refuse a smoothing value that is not a number, is not finite, or is below 0.0 or above 0.8, including an empty value, with a message saying that smoothing must be a number from 0.0 to 0.8. It MUST refuse before any analysis starts and MUST store nothing for the refused request.
- **FR-008**: The UI MUST provide a slider for smoothing whose left end is 0.0 and whose right end is 0.8, with steps of 0.01, starting at 0.0.
- **FR-009**: The UI MUST show the slider's current value as a number with two decimal places.
- **FR-010**: The slider MUST be disabled while a submission is running, MUST keep its position after an error or a completed submission, and a corrected resubmission MUST work without reloading the page.
- **FR-011**: The results summary MUST show the smoothing used.
- **FR-012**: Smoothing MUST NOT change the number of frames, the analysis windows, the window spacing or the timing of the frames.
- **FR-013**: Given the same file and settings, including smoothing, the system MUST produce the same images every time.
- **FR-014**: The same smoothing value MUST also be applied to each tile's hue over the frames: for every frame after the first, the tile's hue is *s* × (its smoothed hue in the previous frame) + (1 − *s*) × (its hue in this frame, worked out from the already smoothed brightness). The first frame's hues MUST NOT be changed, each tile MUST be smoothed only from its own hue history, and hue MUST be treated as a number between 0° and 360° (not as a circle).
- **FR-015**: With smoothing 0.0 the hues MUST be exactly the unsmoothed hues, so the images are identical to those produced before hue smoothing existed.

### Key Entities

- **Smoothing**: A number *s* from 0.0 to 0.8. 0.0 means no smoothing, and higher values make each note's tile follow its own history more and the current frame less.
- **Note value**: The averaged strength of one note in one frame, before it is scaled to a gray level.
- **Smoothed value**: The note value after the running average. The first frame's smoothed value is its note value. Each later one is *s* × the previous smoothed value + (1 − *s*) × the note value.
- **Settings**: Now the window size, the frame rate, the window spacing, the brightness and the smoothing.
- **Submission Result**: Now also carries the smoothing used.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With smoothing 0.0, the images for the same file and settings are identical, pixel for pixel, to the images from before this parameter existed, in 100% of tested files.
- **SC-002**: For note values 0, 10, 0, 0 and smoothing 0.5, the smoothed values are exactly 0, 5, 2.5 and 1.25. For any other tested sequence and any smoothing from 0.0 to 0.8, each smoothed value equals *s* × the previous smoothed value + (1 − *s*) × the note value to within one part in a million.
- **SC-003**: In every tested case the first frame's note values are the same with and without smoothing.
- **SC-004**: After a note stops, its value falls below 10% of its starting value after 4 frames at smoothing 0.5, after 11 frames at smoothing 0.8, and in the first frame at smoothing 0.0.
- **SC-005**: Changing one note's values changes no other note's smoothed values, in 100% of tested cases.
- **SC-006**: The slider's right end is 0.8 and its left end is 0.0, every position between them shows its value to two decimal places, and no position outside the range can be reached.
- **SC-007**: A smoothing of -0.1, 0.81, 1, `abc`, `nan`, `inf` and an empty value are each refused with a message naming the 0.0 to 0.8 range, both when sent directly to the server and (for values that can be entered) in the form, with no crash and nothing stored.
- **SC-008**: Changing only the smoothing does not change the frame count, the window count, or the time to create the frames by more than 10%.
- **SC-009**: A silent file gives all-black frames at every smoothing value.
- **SC-010**: Each tile's smoothed hue equals *s* × its previous smoothed hue + (1 − *s*) × its hue in this frame, to within one part in a million, for any tested sequence and any smoothing from 0.0 to 0.8. For example, a tile whose hue goes 180°, 0°, 0° at smoothing 0.5 has the smoothed hues 180°, 90°, 45°. On the sample music file the average frame-to-frame hue change of bright tiles falls to 40% of its already-smoothed-values-only size at smoothing 0.8 (to 71% at 0.3 and 58% at 0.5).

## Assumptions

- **Running average**: "Running average of itself and previous values" and "x[n-1] is the previous example of this note" are read so that the previous value is the note's *smoothed* value from the previous frame, which makes each frame depend on all earlier frames with weights that fade geometrically. Example, smoothing 0.5: note values 0, 10, 0, 0 give 0, 5, 2.5, 1.25. The other possible reading is to use the previous frame's *unsmoothed* value; it would give 0, 5, 5, 0 for the same input and could only ever blend two neighboring frames. The running-average reading is used because it matches the words "running average" and is what a limit of 0.8 suggests.
- **Default**: The default is 0.0, which leaves existing behavior unchanged unless the user raises it.
- **Slider step**: 0.01, so the slider has 81 positions from 0.00 to 0.80 and the right end is exactly 0.8.
- **Where it is applied**: To the averaged note values of each frame, before they are scaled to gray levels. Because the scaling then uses the loudest smoothed value in the file, the loudest tile still reaches full white. The alternative of scaling against the unsmoothed maximum is not used.
- **Per frame, not per second**: Smoothing works from one animation frame to the next and is not adjusted for the frame rate.
- **Hue smoothing is on top of value smoothing**: The note values are smoothed first, the hues are then worked out from the smoothed and scaled brightness, and the hues are smoothed again with the same parameter. The tile's brightness (its HSV value) is not smoothed a second time. Hue is smoothed as a plain number from 0° to 360°, as the user's clipped hue is a line and not a circle, so no special handling of the red ends is added.
- **Changing smoothing needs a new submission**: Frames are made at submission time, so a different smoothing means submitting again. Re-rendering stored frames is out of scope.
- **Dependencies**: This extends the frame pipeline from features 002 to 005 and adds a field to the form and request.
- **Scope**: Only the smoothing parameter is added. The analysis, window spacing, brightness and layout are unchanged.
