# Feature Specification: Smoothing Window

**Feature Branch**: `012-smoothing-window` (no git branch created; spec directory name only)

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "change how smoothing works.  Define a new smoothing window `w` as a constant between 1 and 20, default 1, and the existing smoothing parameter `s`.    For each frame A, the image is the average of A[t]+A[t-1]*s +... A[t-w]*s.  So you need to keep a buffer of the last `w` frames."

## Clarifications

### Session 2026-10-10

- Q: Is the formula read correctly: every earlier frame in the window has the same weight `s`, and the weighted sum is divided by the sum of the weights? → A: Yes, confirmed.
- Q: Is the smoothing window `w` a fixed constant of the program, or a setting? → A: A setting. "Constant" in the request meant "integer": `w` is an integer variable, a whole number from 1 to 20 with a default of 1, chosen by the user.
- Q: Should smoothing average the underlying values (each note's strength, each tile's hue, each frame's brightness) or the finished picture pixel by pixel? → A: The underlying values (option A). The Threshold and the level steps then keep working on the smoothed values, as they do now.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Smooth over a fixed number of earlier frames (Priority: P1)

Today smoothing is a running average that never forgets: every frame is mixed with the whole smoothed history before it, so a note that stops keeps a fading trace for a long time (at the highest smoothing value it takes about 11 frames to fall below 10%, and it never reaches exactly zero). The user wants smoothing that looks back over a **fixed number of earlier frames** and then forgets them. A new **smoothing window** `w` is the number of earlier frames that are looked at. The existing **smoothing** value `s` is how much each of those earlier frames counts compared with the current one.

For frame number *t*, the smoothed value is the **average** of the current frame at full weight and each of the previous `w` frames at weight `s`:

`( A[t] + s·A[t−1] + s·A[t−2] + … + s·A[t−w] ) / ( 1 + s·w )`

The weights are divided by their sum, so the result is a true weighted average. A value that is the same in all these frames stays that value, and with `s = 0` (the default) the frame is exactly its own, unsmoothed, value. For the first frames of the file, which have fewer than `w` earlier frames, only the frames that exist are used and the weights are divided by the sum of the weights actually used, so the first frame is always left as it is.

The window `w` is a whole number from **1 to 20** and the default is **1**. The smoothing `s` keeps its range, from 0 to 0.8, and its default of 0.

**Why this priority**: This is the whole feature: a different, bounded form of smoothing. The control for `w` (Story 2) and the combination with the other settings (Story 3) depend on it.

**Independent Test**: Make frames from a file in which one note sounds in a single frame (later than the first `w` frames) and is silent before and after. With `w = 3` and `s = 0.5` the note's value in that frame is 1/(1 + 0.5·3) of its unsmoothed value, in each of the next three frames it is 0.5/(1 + 0.5·3) of it, and in the fourth frame after it has stopped it is exactly 0.

**Acceptance Scenarios**:

1. **Given** `s = 0` and any `w`, **When** frames are created, **Then** every frame is exactly as it is without smoothing, and identical to the frames made before this feature with smoothing 0.
2. **Given** `w = 2`, `s = 0.5` and a note whose values in three consecutive frames are 8, 4 and 2, **When** frames are drawn, **Then** its smoothed values are 8 (the first frame is unchanged), 5.33 (4 + 0.5·8, divided by 1.5) and 4 (2 + 0.5·4 + 0.5·8, divided by 2).
3. **Given** a note whose value is 1 in one frame and 0 in all others, `w` and `s` above 0, **When** frames are drawn, **Then** it is non-zero in that frame and in the following `w` frames, and exactly 0 from the frame after that, whatever `s` is (the memory is finite).
4. **Given** a note whose value is the same in every frame, **When** frames are drawn with any `w` and `s`, **Then** its smoothed value is that same value in every frame.
5. **Given** `s > 0`, **When** the smoothed values of any frame are worked out, **Then** only that frame and the frames before it are used, never later frames, and the smoothed values of a frame do not depend on frames after it.
6. **Given** `w = 1` and `s > 0`, **When** frames are drawn, **Then** each frame is its own value plus `s` times the previous frame's **unsmoothed** value, divided by `1 + s` (it is not mixed with an earlier smoothed value, as the old smoothing did).
7. **Given** the same file and settings, **When** frames are drawn twice, **Then** the two sets of frames are identical.

---

### User Story 2 - Choose the smoothing window on the page (Priority: P2)

The settings column gets a **Smoothing window** control for `w`, next to Smoothing. It accepts whole numbers from 1 to 20, starts at 1, has an info button with a short explanation and is disabled while a job is running, like the other settings. The Smoothing explanation is updated to describe the new meaning of `s`. The result summary shows the window that was used.

**Why this priority**: The effect (Story 1) works for a request that includes the window, but users need to set it on the page, as with the other settings.

**Independent Test**: Open the page, set the Smoothing window to 5 and Smoothing to 0.5, create frames, and confirm the result summary lists both and that a note which stops disappears after 5 frames.

**Acceptance Scenarios**:

1. **Given** the page is opened, **When** the settings are shown, **Then** there is a Smoothing window control with the value 1, next to the Smoothing slider.
2. **Given** a value that is not a whole number from 1 to 20 (empty, 0, 21, 2.5, text), **When** the user enters it, **Then** the page shows an error under the field, "Create frames" is unavailable, and nothing is sent; a request that bypasses the page with such a value is refused with a clear message that states the range.
3. **Given** the user activates the info button, **When** the popover opens, **Then** it explains that the window is the number of earlier frames that are mixed into each frame, that Smoothing is how strongly each of them counts compared with the current frame, and the allowed range.
4. **Given** a job is running, **When** the user looks at the field, **Then** it is disabled like the other settings.
5. **Given** frames have been created, **When** the result is shown, **Then** the result summary includes the window that was used.
6. **Given** a request that does not send a window, **When** the server receives it, **Then** it uses 1.

---

### User Story 3 - Smoothing applies to everything it applied to before, and comes first (Priority: P3)

The new smoothing is applied wherever the old smoothing was: to each note's value, to each tile's hue (as a plain number from 0° to 360°) and to each frame's brightness (from the sound's energy), all with the same `w` and `s`. It is still done **before** everything that follows it: the gray levels, the Saturation and Brightness roots, the level steps (Hue, Saturation and Brightness steps) and the Threshold, which all work on the smoothed values exactly as before.

**Why this priority**: These are the interactions with the existing settings. They define the result when features are combined, but are secondary to the smoothing itself.

**Independent Test**: With `w = 4`, `s = 0.6`, Saturation steps 20 and a Threshold of 5, every tile's saturation is one of the six levels, a note that stops turns black no later than the frame at which its smoothed value falls below 5% of the largest smoothed value, and the frames before smoothing was changed are not affected.

**Acceptance Scenarios**:

1. **Given** `w` and `s > 0`, **When** frames are drawn, **Then** the note values, the hues and the frame brightnesses are smoothed with the same window and weight, each from its own history only (a tile's hue or a note's value is never mixed with another tile's).
2. **Given** a Threshold above 0, **When** a note fades because of smoothing, **Then** it turns black once its smoothed value is below the threshold, and stays black until its smoothed value rises to the threshold again.
3. **Given** a level step, **When** frames are drawn, **Then** the rounding to levels is applied to the smoothed values, as before.
4. **Given** the file's largest value, **When** the gray levels are worked out, **Then** they are scaled against the largest **smoothed** value, as before.
5. **Given** any `w` and `s`, **When** frames are drawn, **Then** the layout, size, frame count and timing of the frames, the note analysis, and the image format are unchanged.

---

### Edge Cases

- **A window longer than the file** is allowed: the frames simply use all the earlier frames there are.
- **First frames**: frame 0 is always its own value. Frame *t* with *t* < `w` uses the *t* earlier frames, and the weights are divided by `1 + s·t`.
- **Maximum settings** (`w = 20`, `s = 0.8`): the current frame has weight 1 and each of the 20 earlier frames 0.8, so the picture is a nearly even average of 21 frames. It is calm but it lags: a new note takes several frames to reach its full value.
- **A note that appears suddenly** is reduced in the frame where it appears (it is averaged with earlier, quieter frames) and rises over the next frames; this is the same kind of delay as before but it ends after `w` frames at full value instead of approaching it forever.
- **Hue** is smoothed as a plain number from 0° to 360°, not as a circle, as before.
- **Silent file**: every frame is black, whatever `w` and `s` are.
- **Results from before this feature** (frames already created) are not changed. Only new submissions use the new smoothing. Because the way smoothing works changes, new frames made with Smoothing above 0 look different from frames made before this feature with the same value.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The smoothed value of frame *t* MUST be `( A[t] + s·A[t−1] + … + s·A[t−w] ) / ( 1 + s·w )` where `A[i]` are the unsmoothed values of the earlier frames, `w` is the smoothing window and `s` the smoothing. For frames that have fewer than `w` earlier frames, only the existing earlier frames MUST be used and the sum of the weights MUST be the sum of the weights used (`1 + s·k` for `k` earlier frames), so the first frame is unchanged.
- **FR-002**: Only the current frame and earlier frames MUST be used; the earlier frames MUST be the **unsmoothed** values (not earlier smoothed results), so a value is forgotten exactly `w` frames after it last occurred.
- **FR-003**: The smoothing window MUST be a whole number from 1 to 20 with a default of 1. The smoothing `s` MUST keep its range of 0.0 to 0.8 and its default of 0. With `s = 0` the frames MUST be identical to those without smoothing, whatever `w` is.
- **FR-004**: The new smoothing MUST replace the old running average everywhere the old one was used: each note's value, each tile's hue (as a plain number, not as a circle) and each frame's brightness. All three MUST use the same `w` and `s`, and each value MUST be smoothed from its own history only.
- **FR-005**: Smoothing MUST be applied before the gray levels, the Saturation and Brightness roots, the level steps and the Threshold, which MUST work on the smoothed values as they do now. The gray levels MUST be scaled against the largest smoothed value.
- **FR-006**: Users MUST be able to set the smoothing window on the page, with the value 1 at the start. The field MUST be disabled while a job is running and have an info button with a short explanation, and the Smoothing explanation MUST be updated to describe the new meaning of `s`.
- **FR-007**: The page MUST refuse a window that is not a whole number from 1 to 20 with a message under the field and MUST not send the job. The server MUST refuse such a value, or an empty value that was sent, with a clear message that states the range, and MUST use 1 when the window is not sent at all.
- **FR-008**: The result summary and the server's response to a job MUST include the smoothing window that was used.
- **FR-009**: The same file and settings MUST always give identical frames.
- **FR-010**: Nothing else about the frames MUST change: the layout, size, frame count and timing, the note analysis, the way the other settings work, and the images' format. The documentation's description of smoothing MUST be updated to describe the new method.

### Key Entities *(include if feature involves data)*

- **Smoothing window (`w`)**: A whole number from 1 to 20: how many earlier frames are mixed into each frame.
- **Smoothing (`s`)**: A number from 0 to 0.8: the weight of each earlier frame in the window, compared with a weight of 1 for the current frame.
- **Frame history**: The unsmoothed values of the last `w` frames, per note, per tile hue and for the frame brightness, which is all that is needed to work out the next frame.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the smoothing at 0 (the default), 100% of the frames of a test file are identical, pixel for pixel, to those made before this feature, for every window from 1 to 20.
- **SC-002**: For a note that sounds in exactly one frame, at least `w` frames after the start of the file, with `w` = 3 and `s` = 0.5, its smoothed value is 1/2.5 = 0.4 of the unsmoothed value in that frame, 0.2 in each of the next three frames and exactly 0 in the fourth frame after it; the same shape holds for every `w` from 1 to 20 (non-zero for exactly `w` frames after the note, then exactly 0).
- **SC-003**: Hand-computed smoothed values for the worked example (8, 4, 2 with `w` = 2 and `s` = 0.5 give 8, 5.33 and 4) match the system's to within 0.001.
- **SC-004**: A value that is constant over the file is unchanged by smoothing for every `w` and `s`.
- **SC-005**: Adding frames at the end of a file changes no earlier smoothed frame (smoothing looks only backwards).
- **SC-006**: 100% of invalid windows (0, 21, 2.5, empty, text) are refused before a job is created, with a message that states the allowed range.
- **SC-007**: A user can find and read the explanation of the Smoothing window from its info button, and change it, without leaving the settings column.
- **SC-008**: Creating the same frames takes no more than 25% longer than before this feature at the largest window (20) and smoothing (0.8), and no longer than before at smoothing 0.

## Assumptions

- **"Average" means a weighted average** (confirmed): the weights (1 for the current frame and `s` for each of the `w` earlier frames) are divided by their sum, `1 + s·w`. Dividing by the number of frames (`w + 1`) instead would make the picture darker for the default settings, and with `s = 0` would not give back the unsmoothed frame, which the default must do.
- **Every earlier frame in the window has the same weight `s`** (confirmed), as written (`A[t−1]·s + … + A[t−w]·s`), not a weight that falls with distance (`s²`, `s³` …). A falling weight would be a different method.
- **The window `w` is an integer setting** (confirmed; "constant" in the request meant "integer"), not a fixed constant of the program: a whole number from 1 to 20 with a default of 1. It is shown on the page and sent to the server like the other settings.
- **"The image" is read as the same quantities as before** (confirmed): the note values, the tiles' hues and the frames' brightness are smoothed, not the final colored pixels. Averaging final pixels would mix black (hidden) and colored tiles and would undo the Threshold and the level steps, which are meant to work on smoothed values. The words "the last `w` frames are kept" are read as the history these quantities need.
- **Earlier frames are used unsmoothed** (the formula is on `A`, the raw frames), so the method has a finite memory of exactly `w` frames, which is what the buffer in the request implies.
- **The smoothing range stays 0 to 0.8**, as before. The meaning of a given value changes (it is now a weight relative to the current frame), so frames made with Smoothing above 0 will differ from older ones.
- **Whole-number input** for the window: a number field with the range 1 to 20 (or an equivalent control), like the other whole-number settings.
- **The API** gets one new optional form field for the window, treated like the other numeric settings, and the response includes it; the page, the frame image format and size and everything else about the API stay as they are.
- This feature is about the image color only. Audio playback, analysis of notes, and the page layout (apart from adding one field and one summary item) are unchanged.
