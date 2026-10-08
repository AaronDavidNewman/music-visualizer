# Feature Specification: Note Threshold

**Feature Branch**: `011-note-threshold` (no git branch created; spec directory name only)

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "add a threshold slider for whether a note appears.  If the volume of that note is below the threshold, the tile will have HSV value of 0,0,0.  left on the slider represents no threshold (current value), right (max value) represents 50% of the largest harmonic value."

## Clarifications

### Session 2026-10-07

- Q: What should the right end of the slider be? → A: **10%** of the largest note value, not 50%. The threshold runs from 0 (off) to 10, in steps of 1 percentage point on the page. All other rules are unchanged: only notes strictly below the level are hidden, and the level is a share of the largest note value in the whole file.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Hide notes that are too quiet to matter (Priority: P1)

A user sees frames in which every note, however faint, colors its tile a little. Faint notes, such as leakage from neighboring notes, room noise and the tails of notes that have stopped, add clutter and make it hard to see which notes are really being played. They want to say "a note only counts if it is at least this loud". A new **Threshold** setting sets that level as a share of the **largest note value in the whole file** (the loudest value any note reaches in any frame, which is also the value that every other note is already measured against). At the lowest setting there is no threshold and the frames are exactly as they are today. At the highest setting the threshold is **10% of the largest note value**. A note whose value in a frame is **below** the threshold is not shown: its tile is plain black, HSV value (0, 0, 0). A note at or above the threshold is drawn exactly as before.

**Why this priority**: This is the whole feature: a cut-off for faint notes, applied to the tiles of every frame.

**Independent Test**: Create frames from a file in which a loud note sounds together with a faint one (say 5% of the loud one's value). With the threshold off, both tiles are colored. With the threshold at 8% the loud note's tile is unchanged and the faint note's tile is black, in every frame in which the faint note is below 8% of the loudest note of the file.

**Acceptance Scenarios**:

1. **Given** the threshold is at its lowest setting, **When** frames are created, **Then** the frames are identical to those made before this feature.
2. **Given** a threshold of *t* percent (from 1 to 10), **When** a note's value in a frame, as a share of the file's largest note value, is below *t* percent, **Then** that note's tile in that frame is black: red, green and blue all 0, which is HSV (0, 0, 0).
3. **Given** a threshold of *t* percent, **When** a note's value in a frame is *t* percent of the largest note value or more, **Then** its tile is drawn exactly as it would be with the threshold off.
4. **Given** the threshold is at its highest setting (10%), **When** frames are drawn, **Then** only notes with at least a tenth of the largest note value are shown. The note with the largest value is always shown, because it is 100% of itself, at every setting.
5. **Given** a threshold above the lowest setting, **When** frames are drawn, **Then** a note can be shown in one frame and hidden in another, depending on its value in each frame, and the threshold is the same fixed level for the whole file (it does not follow each frame's own loudest note).
6. **Given** a file in which no note has any value (silence), **When** frames are drawn at any threshold, **Then** every pixel is black and nothing fails.
7. **Given** the same file and settings, **When** frames are drawn twice, **Then** the two sets of frames are identical.

---

### User Story 2 - Set the threshold with a slider on the page (Priority: P2)

The user sets the threshold on the page, in the settings column with the other settings. **Threshold** is a slider. At the **left end** the threshold is off ("Off", the value today). Moving it to the right raises the threshold in steps of 1 percentage point, up to the **right end**, which is **10%** of the largest note value. A readout beside the slider shows the current position ("Off", or for example "5% of the loudest note"). The slider has an info button with a short explanation, is disabled while a job is running, like the other settings, and starts at the left end. The result summary shows the value that was used.

**Why this priority**: The effect (Story 1) works for a request that includes the threshold, but users need to set it on the page and see what a position means, as with the other settings.

**Independent Test**: Open the page, move the slider through its range and watch the readout ("Off" at the left end, "10% of the loudest note" at the right end), create frames, and confirm the result summary lists the threshold that was chosen.

**Acceptance Scenarios**:

1. **Given** the page is opened, **When** the settings are shown, **Then** there is a Threshold slider, at its left end, whose readout says "Off".
2. **Given** the slider is moved, **When** its position changes, **Then** the readout shows the percentage straight away, from "Off" at the left end to "10%" at the right end, in steps of 1.
3. **Given** the user activates the info button, **When** the popover opens, **Then** it explains that a note below the threshold is drawn black, that the threshold is a share of the loudest note in the file, that the left end is off, and that the right end is 10%, in the same way as the other settings.
4. **Given** a job is running, **When** the user looks at the slider, **Then** it is disabled like the other settings.
5. **Given** frames have been created, **When** the result is shown, **Then** the result summary includes the threshold that was used ("Off" or the percentage).
6. **Given** a request that bypasses the page with a threshold that is not a number from 0 to 10 (negative, above 10, empty, text, not a number), **When** the server receives it, **Then** it is refused with a clear message that states the allowed range. A request that does not send a threshold at all uses 0 (off).

---

### User Story 3 - The threshold works together with the other settings (Priority: P3)

The threshold decides only whether a note's tile is shown. It does not change how notes are measured, how the other tiles look or how the frames are timed. It is applied to the note values as they are used for drawing, after smoothing, so that a note fading away under smoothing disappears when its smoothed value drops below the threshold. The Saturation and Brightness roots, the level steps and the hue calculation work as before for every note that is shown. A black tile stays black whatever those settings are.

**Why this priority**: These are the interactions with the existing settings. They define the result when features are combined, but are secondary to the threshold itself.

**Independent Test**: With a threshold of 10% and smoothing at 0.8, a note that stops fades from its tile, then turns black in the first frame whose smoothed value is below 10% of the file's largest note value, and stays black after that.

**Acceptance Scenarios**:

1. **Given** smoothing above 0 and a threshold above the lowest setting, **When** frames are drawn, **Then** the comparison uses the smoothed note value, so a note that fades turns black once its smoothed value is below the threshold.
2. **Given** the threshold, **When** it is compared with a note's value, **Then** the comparison is made on the note's value as a share of the largest note value, before the Saturation root, so the Saturation setting never changes which notes are hidden.
3. **Given** a hue step, a saturation step or a brightness step, **When** a tile is hidden by the threshold, **Then** it is black (0, 0, 0) whatever the steps are, and tiles that are shown are rounded to levels as before.
4. **Given** a note is hidden, **When** other tiles' hues are worked out, **Then** the hidden note still counts as a related note exactly as before: the threshold changes only the hidden note's own tile.
5. **Given** any threshold, **When** frames are drawn, **Then** the frame's brightness, its timing, its size and its layout are as before, and the other tiles' colors are as they would be with the threshold off.

---

### Edge Cases

- **A single very loud note** sets the file's largest note value, so at higher thresholds more of the rest of the file is hidden. This is the same behavior as the gray levels, which are also scaled against the file's largest value.
- **Notes exactly at the threshold** are shown (hidden only when strictly below).
- **The four highest notes of the 88 (not drawn)** still count when the file's largest note value is found, as they do for the gray levels today.
- **Frame brightness (from the sound's energy)** is not affected: a hidden tile is black, and the other tiles of the frame keep the frame's brightness.
- **A frame in which every note is hidden** is entirely black. This is a normal result, not an error.
- **Silent file**: every frame is black at every threshold.
- **Results from before this feature** (frames already created) are not changed. Only new submissions use the threshold.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to set a **Threshold** from a slider in the settings of the page. The slider's left end MUST mean no threshold (off) and its right end MUST mean 10% of the largest note value, in steps of 1 percentage point. It MUST start at the left end.
- **FR-002**: With the threshold off, the frames MUST be identical to those made before this feature.
- **FR-003**: The reference for the threshold is the **largest note value anywhere in the file**: the largest of all note values in all frames, after smoothing, which is also what the gray levels are measured against. A threshold of *t* percent means the level *t* percent of that value.
- **FR-004**: A note whose value in a frame is below the threshold MUST have a black tile in that frame: red, green and blue all 0 (HSV (0, 0, 0)). A note whose value is equal to the threshold or higher MUST be drawn exactly as it would be with the threshold off.
- **FR-005**: The comparison MUST use the note's value as a share of the largest note value, after smoothing and before the Saturation root, so that the Saturation root, the level steps, the hue calculation and the frame brightness have no effect on which notes are hidden.
- **FR-006**: A hidden tile MUST stay black whatever the Saturation, Brightness and Hue steps and the roots are. The tiles that are shown MUST keep their own hue, saturation and brightness as they would have them with the threshold off.
- **FR-007**: Hiding a note MUST change only its own tile: a hidden note MUST still count as a related note when other tiles' hues are worked out, exactly as before.
- **FR-008**: The note with the largest value MUST be shown at every threshold. If no note has any value (silence), every frame MUST be entirely black and nothing may fail.
- **FR-009**: The page MUST show the slider with a label, an info button with a short explanation, and a readout of the current position ("Off" at the left end, otherwise the percentage). The slider MUST be disabled while a job is running.
- **FR-010**: The server MUST refuse a threshold that is not a number from 0 to 10 (negative, above 10, empty when sent, text, not a number) with a clear message that states the range, and MUST use 0 (off) when a threshold is not sent at all.
- **FR-011**: The result summary and the server's response to a job MUST include the threshold that was used.
- **FR-012**: The same file and settings MUST always give identical frames.
- **FR-013**: Nothing else about the frames MUST change: the layout, size, frame count and timing, the note analysis, the way the other settings work, and the images' format. The documentation's description of the image and settings MUST be updated to describe the threshold.

### Key Entities *(include if feature involves data)*

- **Threshold**: A number from 0 to 10 chosen by the user: 0 means off and any other value is that percentage of the file's largest note value.
- **Largest note value**: The largest value that any note reaches in any frame of the file (after smoothing). It is the reference both for the gray levels and for the threshold.
- **Hidden note**: A note whose value in a frame is below the threshold; its tile in that frame is black.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the threshold off, 100% of the frames of a test file are identical, pixel for pixel, to those made before this feature.
- **SC-002**: In a test file with a loud note and a faint note at 5% of its value, a threshold of 8% makes the faint note's tile exactly black in every frame in which it is below 8% of the file's largest note value, and leaves the loud note's tile unchanged; a threshold of 3% leaves both tiles as they were with the threshold off.
- **SC-003**: For every threshold from 1 to 10, every tile in every frame is either exactly black (because its note is below the threshold) or identical to the tile with the threshold off (never a different color).
- **SC-004**: At every threshold, the note with the largest value is shown in at least one frame, and in a silent file all frames are entirely black.
- **SC-005**: Changing only the threshold changes no shown tile's hue, saturation or brightness.
- **SC-006**: 100% of invalid thresholds (negative, above 10, empty, text) are refused before a job is created, with a message that states the allowed range.
- **SC-007**: A user can find and read the explanation of the threshold from its info button, and move the slider and see the percentage, without leaving the settings column.
- **SC-008**: Creating the same frames takes no more than 10% longer than before this feature.

## Assumptions

- **"Volume of that note"** is the note's measured value in the frame (the same value that sets its saturation), compared as a share of the file's largest note value. The page already calls the loudness-derived value of a note its level; this feature uses the unrounded value, after smoothing and before the Saturation root.
- **"Largest harmonic value"** is read as the largest note value anywhere in the file. It is the reference that every note value is already scaled against, so a threshold of 10% is a tenth of the value that makes a tile fully saturated.
- **Hidden means strictly below**: a note exactly at the threshold is shown. At the lowest setting nothing is below the threshold (every value is 0 or more), which agrees with "no threshold".
- **The threshold is one fixed level for the whole file**, not one per frame, so a note that is quiet throughout the file is hidden in every frame and a note that is loud enough in some frames shows only in those.
- **The slider moves in whole percentage points** from 0 to 10 (11 positions). The server accepts any number in that range. The unit is percent of the largest note value, shown in the readout.
- **Only the note's own tile is hidden.** A hidden note still counts as a related note for other tiles' hues, because the request only says what happens to "the tile". If the intent is that a hidden note should stop influencing other tiles, the spec needs a change before planning (this is the one point most worth confirming in `/speckit-clarify`).
- **Smoothing is applied first**, then the threshold, so that a fading note disappears when its smoothed value falls below the threshold.
- **The API** gets one new optional form field for the threshold, treated like the other numeric settings, and the response includes it; the page, the frame image format and size and everything else about the API stay as they are.
- This feature is about the image color only. Audio playback, analysis of notes, and the page layout (apart from adding one slider and one summary item) are unchanged.
