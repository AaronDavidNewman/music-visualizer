# Feature Specification: Interpolated Frames

**Feature Branch**: `018-interpolated-frames` (no git branch created; spec directory name only)

**Created**: 2026-10-12

**Status**: Implemented; amended 2026-10-13 (the interpolation function was removed, only blend is made)

**Input**: User description: "allow for interpolated frames , with integer values from 1 to 5.  Interpolated frames are blended between values, effectively dividing the number of frames that are generated.  For instance, if interpolate is 5 and frame rate is 25, frame 1 and frame 6 are generated, frames 2-5 are interpolated using PIL library functions.  Default function is blend, other functions allowed are soft_light, hard_light, overlay, screen, subtract.  These are all implemented using the python Pillow image library."

## Clarifications

### Session 2026-10-12

- Q: How do soft_light, hard_light, overlay, screen and subtract use the position between the two drawn frames, when they combine two pictures without a weight? -> A: Option B: `f(earlier, blend(earlier, later, k / n))`. (Superseded: see the next session.)

### Session 2026-10-13

- Q: Should the interpolation function stay a choice? -> A: **No. The interpolation function is removed and `blend` is hard-coded.** The user, after seeing the rendered frames: "The others don't really work." Measured, the five other functions (`soft_light`, `hard_light`, `overlay`, `screen`, `subtract`, applied as `f(earlier, blend)`) gave frames that pulsed back to the plain drawn frame at every drawn frame (screen lightened, the others darkened), and `subtract` gave almost black frames. So: there is no Interpolation function dropdown and no `interpolate_function` field or response key; every frame between two drawn frames is the Pillow blend of its neighbors. The earlier requirements about the other functions (FR-005 and Story 3 of the first version) no longer exist. A request that still sends `interpolate_function` is accepted and the field is ignored, like the other removed fields of earlier features.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fewer pictures drawn, the frames in between made by blending (Priority: P1)

Today every frame of the animation is drawn from the note values of its own moment. Drawing is the slow part of a job (a contour picture takes about 15 milliseconds, against well under one millisecond for a tile picture), and a quickly changing animation does not need a freshly drawn picture for every frame. The user wants to draw only **every n-th frame** and make the frames in between by **blending the two drawn frames on either side**, with n a whole number from **1 to 5**, called **interpolate**. With interpolate 1 every frame is drawn, as today.

The frame rate, the number of frames and the timing do not change: the animation still has one frame for every frame period. With interpolate 5 and a frame rate of 25, the frames numbered 1, 6, 11, 16 and so on are **drawn** (five a second), and frames 2 to 5 lie between frames 1 and 6, frames 7 to 10 between frames 6 and 11, and so on; each of those in-between frames is **interpolated** from the two drawn frames next to it, with the Pillow library's blend: an in-between frame is a mix of the drawn frame before it and the drawn frame after it, weighted by how far along the way it is (frame 2 is closest to frame 1, frame 5 closest to frame 6). The drawn frames are the frames that would have been made without interpolation, unchanged.

**Why this priority**: This is the whole feature: drawing fewer frames and making the rest from them. The page control (Story 2) builds on it.

**Independent Test**: Make frames from a file with interpolate 1 and again with interpolate 5. Frames 1, 6, 11 and so on are identical in the two jobs; frames 2 to 5, 7 to 10 and so on, which at interpolate 1 were drawn from the music, are at interpolate 5 gradual mixes of their two neighbors, and the job draws about one fifth as many pictures.

**Acceptance Scenarios**:

1. **Given** interpolate 1, **When** frames are made with any image type and settings, **Then** they are identical, file for file, to those made before this feature.
2. **Given** an interpolate value n from 2 to 5, **When** frames are made, **Then** the frames at positions 1, n + 1, 2n + 1 and so on, and the last frame of the file, are drawn from the music exactly as they would be at interpolate 1, and no other frame is drawn.
3. **Given** the drawn frames before and after an in-between frame, **When** that frame is made, **Then** every pixel is the mix of the two drawn frames' pixels weighted by the frame's position between them: at position k of n the weight of the later frame is k / n and the weight of the earlier frame is 1 − k / n (frame 2 of 5 is four fifths of frame 1 and one fifth of frame 6).
4. **Given** the number of frames of the job, **When** frames are made at any interpolate value, **Then** the number of frames, their file names, their size and their timing are the same as at interpolate 1.
5. **Given** a file whose number of frames does not fit the pattern (the last drawn frame would fall beyond the end), **When** frames are made, **Then** the last frame of the file is drawn as well, and the frames between the last two drawn frames are interpolated between them (the final gap is shorter, and the position is counted within it).
6. **Given** two neighboring drawn frames that are identical, **When** the frames between them are made, **Then** they are identical to them.
7. **Given** the same file and settings, **When** frames are created twice, **Then** the two sets of frames are identical.
8. **Given** any image type (Tiles, Blended tiles or Contour), **When** frames are made at an interpolate value above 1, **Then** the drawn frames are those of that image type and the in-between frames are blends of them.

---

### User Story 2 - Choose the interpolation on the page and through the server (Priority: P2)

The settings column has a new **Interpolate** control: a slider from 1 to 5 in whole steps starting at 1, whose readout says what it means ("1 (every frame drawn)", "5 (one frame in 5 drawn)"), with an info button that explains it. The result summary shows the interpolate value. In requests the setting is the optional field `interpolate` (a whole number from 1 to 5, 1 when not sent). A value that is not allowed is refused with a clear message, and the response reports the value used.

**Why this priority**: The feature (Story 1) can be asked for through the server, but users need to choose it on the page.

**Independent Test**: Open the page, move Interpolate to 5, create frames, and see the animation play at the same speed with "Interpolate: 5" in the summary. Set Interpolate back to 1: the animation is as before.

**Acceptance Scenarios**:

1. **Given** the page is opened, **When** the settings are shown, **Then** Interpolate is at 1 with the readout "1 (every frame drawn)" and an info button.
2. **Given** the slider is moved above 1, **When** the user looks at the control, **Then** the readout shows how many frames are drawn ("3 (one frame in 3 drawn)").
3. **Given** the user activates the info button, **When** the popover opens, **Then** it explains that only every n-th frame is drawn and the frames between are made by blending their neighbors (so a job is faster).
4. **Given** frames have been created, **When** the result is shown, **Then** the summary includes "Interpolate: 1" or the value used.
5. **Given** a request with `interpolate` set to a whole number from 1 to 5, **When** the server receives it, **Then** it creates the frames and the response reports `interpolate`.
6. **Given** a request without the field, **When** the server receives it, **Then** the interpolate value is 1 and the frames are those of today.
7. **Given** a request with an interpolate value that is empty, not a number, not a whole number, below 1 or above 5, **When** the server receives it, **Then** it is refused before a job is created, with a message that says it must be a whole number from 1 to 5.
8. **Given** a job is running, **When** the control is shown, **Then** it is disabled, like the other settings.
9. **Given** a request that still sends `interpolate_function` (the removed field), **When** the server receives it, **Then** the request is accepted, the field is ignored and the response has no such key.

---

### User Story 3 - It works with every image type and setting, and saves time where drawing is slow (Priority: P3)

Interpolation works with every image type and with every other setting (smoothing, the Threshold, the colormap, the Resolution, the Notes, the Blend width), because it only decides which frames are drawn and how the others are made from them. A job with interpolation takes correspondingly less time when drawing is the slow part: the contour. For Tiles and Blended tiles, which are cheap to draw, making a blended frame costs about as much as drawing one, so there is nothing to save there.

**Why this priority**: These are the interactions with the existing settings and the practical gain. They are secondary to the main behavior.

**Independent Test**: A contour job with interpolate 5 takes at most half as long as the same job with interpolate 1; the drawn frames are identical in both jobs.

**Acceptance Scenarios**:

1. **Given** smoothing, the Threshold, the colormap, the Resolution or the Notes, **When** frames are made with interpolation, **Then** they apply to the drawn frames exactly as they do without interpolation.
2. **Given** any image type, **When** frames are made with interpolation, **Then** every frame is a picture of the same size (252 × 168) and the player plays them like any other.
3. **Given** a silent file or a file in which the drawn frames are all alike, **When** frames are made, **Then** nothing fails and the in-between frames are the same flat picture.
4. **Given** a file of 10 seconds at 30 frames per second (300 frames), **When** frames are created with a contour at interpolate 5, **Then** the job finishes in at most half the time of the same job at interpolate 1; for Tiles and Blended tiles a job at any interpolate value takes no more than a quarter longer than at interpolate 1.

---

### Edge Cases

- **Interpolate 1** draws every frame: the setting is accepted and the output is exactly today's.
- **The first frame** is always drawn, and so is **the last frame of the file**, so every in-between frame has a drawn frame on each side.
- **A file shorter than the interpolate step** (for example 3 frames at interpolate 5): the first and the last frame are drawn and the one frame between them is interpolated; a file of 1 frame draws that frame.
- **Quickly changing music**: frames in between are mixes of their neighbors, so an event that happens between two drawn frames (a note that starts and stops within five frames) is not drawn at all. This is the price of drawing fewer frames.
- **Pictures of different kinds**: Tiles pictures of the original grid are indexed-colour images, contour pictures have an alpha channel; blending is done on ordinary color pictures, so the in-between frames are true-color pictures whatever kind the drawn frames are (the drawn frames are written exactly as today).
- **The removed interpolation function**: requests that still send `interpolate_function` are accepted and the field is ignored.
- **Results from before this feature** (frames already created) are not changed. Only new submissions can use the setting.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to choose an **interpolate** value that is a whole number from 1 to 5, **1** being the default on the page and when a request does not say. At interpolate 1 frames of every image type MUST be identical, file for file, to those made before this feature.
- **FR-002**: At an interpolate value n above 1, only the frames at positions 1, n + 1, 2n + 1 and so on (counting from 1), and the last frame of the file, MUST be **drawn** from the music, exactly as they would be at interpolate 1 (smoothing, the Threshold, the colormap, the Resolution, the Notes and the image type apply to them as before). Every other frame MUST be **interpolated** from the nearest drawn frame before it and the nearest drawn frame after it.
- **FR-003**: The number of frames, their file names, their size (252 × 168) and their timing MUST be the same at every interpolate value, and the same file and settings MUST always give identical frames.
- **FR-004**: An interpolated frame at position k of n between two drawn frames MUST be the mix of the two with the weight k / n for the later frame and 1 − k / n for the earlier one, pixel by pixel (the Pillow function `Image.blend`). Where the last gap is shorter than n, the position is counted within that gap (position k of the gap's length). Blend is the only way in-between frames are made.
- **FR-005** *(removed 2026-10-13)*: The other functions that the first version offered (`soft_light`, `hard_light`, `overlay`, `screen`, `subtract`) and the choice of function no longer exist.
- **FR-006**: The interpolation MUST be implemented with the Pillow image library, not by the application's own pixel arithmetic, and the drawn frames MUST NOT be changed by it.
- **FR-007**: The page MUST offer the **Interpolate** control (a slider from 1 to 5 in whole steps, starting at 1) with a readout of how many frames are drawn, an info button that explains it, and a result summary line that shows the value used; the control MUST be disabled while a job runs.
- **FR-008**: The server MUST accept the optional field `interpolate`, refuse a value that is not allowed (including an empty value) with a clear message, before any job is created, and report the value used in its response. A request that sends the removed `interpolate_function` field MUST be accepted with the field ignored.
- **FR-009**: A job with interpolation MUST draw only the frames of FR-002: the number of pictures drawn at interpolate n for a file of F frames is the number of positions 1, n + 1, 2n + 1 and so on up to F, plus the last frame if it is not one of them.
- **FR-010**: The documentation's description of the settings MUST be updated to describe the interpolation.

### Key Entities *(include if feature involves data)*

- **Interpolate**: The whole number from 1 to 5 chosen for each job: only every n-th frame is drawn. 1 means every frame.
- **Drawn frame**: A frame made from the music's note values, as before. With interpolate n these are the frames at positions 1, n + 1, 2n + 1 and so on, and the last frame.
- **Interpolated frame**: A frame between two drawn frames, the weighted blend of them.
- **Gap**: The run of interpolated frames between two neighboring drawn frames (n − 1 frames, fewer at the end of the file).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At interpolate 1, 100% of the frames of a test file are identical, file for file, to those made before this feature, for every image type.
- **SC-002**: At interpolate n, the drawn frames of a test file (positions 1, n + 1, 2n + 1 and so on, and the last) are identical to the frames at the same positions made at interpolate 1, for every image type.
- **SC-003**: Every pixel of every interpolated frame equals the weighted mix of the two neighboring drawn frames' pixels with the weights of FR-004, to within one level of 255.
- **SC-004**: The frame count, file names and size are the same at every interpolate value, and the number of pictures drawn equals the count of FR-009 (for example 61 of 300 frames at interpolate 5).
- **SC-005**: A contour job of 300 frames at interpolate 5 finishes in at most half the time of the same job at interpolate 1. A Tiles or Blended tiles job at any interpolate value takes no more than 25% longer than at interpolate 1: drawing those pictures costs about as little as blending them, so interpolation saves nothing for them, and the spec does not promise it does.
- **SC-006**: 100% of invalid interpolate values (empty, not a number, fractional, below 1, above 5) are refused before a job is created, with a message that says it must be a whole number from 1 to 5.
- **SC-007**: Between two identical drawn frames, the interpolated frames are identical to them.
- **SC-008**: A user can set the interpolation on the page, read what it does, and see the animation in the player at the same speed without leaving the settings column.

## Assumptions

- **The drawn frames are the frames that would have been made anyway.** Frame values are analyzed and smoothed for every frame as today (that is cheap); interpolation skips the *drawing*, which is the slow part. So the drawn frames are identical to those at interpolate 1, and smoothing, the Threshold and the other settings behave as before.
- **Counting is from 1 as in the request** ("frame 1 and frame 6 are generated"): with interpolate 5 the drawn frames are 1, 6, 11 and so on, which is positions 0, 5, 10 in the zero-based file names `frame_000000.png` and up.
- **The last frame of the file is always drawn**, so that every interpolated frame has a drawn frame on each side; the last gap is then shorter when the number of frames does not fit the pattern.
- **Interpolated frames are true-color pictures** written as PNG files like the drawn ones; the drawn frames are written exactly as before (indexed-colour for Tiles at the original grid, with alpha for contour). The player plays any 252 × 168 PNG.
- **All interpolation arithmetic is Pillow's** (`Image.blend`), as the request says. The application chooses the pictures and the weights, never computes a pixel itself.
- **Interpolation does not change the Resolution, Notes, smoothing or colors**: it works on finished pictures.
- **The setting is chosen when frames are created**, like every other setting; changing it means submitting again.
- This feature is about which frames are drawn and how the others are made. Audio playback, the note analysis, smoothing, the image types, the frame player and the page layout (apart from adding one control and one summary line) are unchanged.
