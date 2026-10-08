# Feature Specification: Discrete Color Levels

**Feature Branch**: `010-discrete-color-levels` (no git branch created; spec directory name only)

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "For hue, saturation, and luminance, we should be able to make the levels more discrete.  So for each value of saturation, hue, and brightness, create a % slider with values up to 50, and calculate the discrete number of colors/saturation values from that.  There should always be at least 2 values for each (hence the 50%), even if the math indicates 1."

## Clarifications

### Session 2026-10-07

- Q: Should the setting be a percentage, or a specific set of step values? → A: Specific step values (a "divisor") replace the percentage. Hue: N/A (all values), 12, 36, 90, 180. Saturation and Brightness (0–100 scales): N/A (all values), 5, 10, 20, 50.
- Q: Should each step setting on the page be a dropdown list or a slider that snaps to the choices? → A: A dropdown list, with the number of levels shown beside it (like the existing Window size setting).
- Q: How is the number of levels worked out from the step? → A: Levels = round((range + step) / step), where the range is 360 for hue and 100 for saturation and brightness. The levels are evenly spaced from 0 to the range, both ends included, so the maximum is always reachable and the count is never below 3 (hue 31, 11, 5, 3; saturation and brightness 21, 11, 6, 3). This replaces the earlier "100 / percentage" rule and the separate "at least 2 values" rule, which can no longer arise.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reduce the colors to a few distinct steps (Priority: P1)

A user sees frames whose hue, saturation and brightness vary smoothly, so neighboring tiles and consecutive frames often differ only slightly and the picture looks muddy. They want bolder, poster-like images in which each of the three color values can take only a handful of distinct levels. For each of **Hue**, **Saturation** and **Brightness** the settings column gets a **step** setting with a short list of choices:

- **Hue** (a scale of 0° to 360°): **N/A**, **12**, **36**, **90**, **180**.
- **Saturation** and **Brightness** (a scale of 0 to 100): **N/A**, **5**, **10**, **20**, **50**.

The step is the distance between one level and the next on that scale. The value is rounded to the nearest level, and the number of levels is **round((range + step) / step)**, with the range being 360 for hue and 100 for the other two. Because the range is added before dividing, both ends of the scale are always levels, so the highest value can always be reached and the lowest level is always 0. A step of 50 on saturation gives 3 levels (0, 50 and 100), a step of 10 gives 11 levels (0, 10, 20 … 100), and a hue step of 90 gives 5 levels (0°, 90°, 180°, 270° and 360°). **N/A** leaves that value smooth ("all" values are allowed), exactly as it is today, and is where each setting starts.

**Why this priority**: This is the whole feature: the three settings and the rounding to levels they control. Everything else in this spec refines it.

**Independent Test**: Create frames from the same file with the Saturation step at N/A and then at 20. With N/A the tiles show many different saturations. With 20 every tile's saturation is one of exactly six values (0, 20, 40, 60, 80 and 100), and the tiles' hues and the frame's brightness are the same as with N/A.

**Acceptance Scenarios**:

1. **Given** all three steps are at N/A, **When** frames are created, **Then** the frames are identical to those made before this feature.
2. **Given** a step *s* chosen from the lists above, **When** frames are drawn, **Then** the value it controls can take only *N* distinct levels, where *N* is round((range + *s*) / *s*), and the levels are the multiples of *s* from 0 up to and including the range.
3. **Given** the Saturation or Brightness step is 5, 10, 20 or 50, **When** frames are drawn, **Then** the value can take 21, 11, 6 or 3 levels respectively. **Given** the Hue step is 12, 36, 90 or 180, **Then** the hue can take 31, 11, 5 or 3 levels respectively.
4. **Given** a step of 20 on Saturation, **When** a tile has a saturation in the middle of two levels (such as 50), **Then** it is shown at the nearest level, and a value exactly half-way between two levels goes to the higher one (50 goes to 60).
5. **Given** the largest step (180 for hue, 50 for the others), **When** frames are drawn, **Then** the value is one of its lowest, middle or highest values and nothing else (3 levels), and the highest value (360° or 100) is reachable.
6. **Given** the step is changed for one of Hue, Saturation or Brightness, **When** frames are drawn, **Then** only that property is rounded to levels. The other two behave as their own settings say, and the layout, the note analysis, and the image size and format do not change.
7. **Given** the same file and settings, **When** frames are drawn twice, **Then** the two sets of frames are identical.

---

### User Story 2 - Choose the steps on the page and see what they mean (Priority: P2)

The user sets the three steps on the page, in the settings column with the other settings. Each setting has a label (**Hue steps**, **Saturation steps**, **Brightness steps**), an info button with a short explanation, and a **dropdown list** of the choices from Story 1, starting at N/A. Next to the dropdown, the page shows the number of levels it gives, for example "20 (6 levels)", or "N/A (smooth)". The labels use the same names that the page already shows to the user for the three properties. The settings are disabled while a job is running, like the other settings. The result summary shows the values that were used.

**Why this priority**: The rounding (Story 1) works for a request that includes the steps, but users need the settings on the page and a clear indication of what each choice gives, or they would have to do the arithmetic themselves.

**Independent Test**: Open the page, change each setting and watch the number of levels shown (Hue 90 → 5 levels, Saturation 10 → 11 levels, N/A → smooth), create frames, and confirm the result summary lists the three steps that were chosen.

**Acceptance Scenarios**:

1. **Given** the page is opened, **When** the settings are shown, **Then** there are three dropdown lists, one each for hue, saturation and brightness, each offering exactly the choices listed in Story 1 and each starting at N/A.
2. **Given** a choice is made, **When** the selection changes, **Then** the number of levels it gives is shown straight away (31, 11, 5 or 3 for hue; 21, 11, 6 or 3 for the others).
3. **Given** the user activates the info button of a setting, **When** the popover opens, **Then** it explains what the setting does, that N/A means smooth (no steps), that a larger step gives fewer, bolder levels, and the allowed choices, in the same way as the other settings.
4. **Given** a job is running, **When** the user looks at the three settings, **Then** they are disabled like the other settings.
5. **Given** frames have been created, **When** the result is shown, **Then** the result summary includes the three steps that were used (N/A for a smooth value).
6. **Given** a request that bypasses the page with a step that is not one of the allowed choices for that property (such as 7, 0, a negative number, 51, or text), **When** the server receives it, **Then** it is refused with a clear message that lists the allowed choices. A request that does not send a step at all uses N/A.

---

### User Story 3 - Levels hold steady across frames and with smoothing (Priority: P3)

Rounding to levels is the last step for each value, after everything else that is applied to it. Smoothing (the running average over frames), the root settings and the related-note hue shifts all work as before and the rounding is then applied to the finished value. Because of this, consecutive frames that are close together show the *same* level rather than flickering between neighboring shades, and a user who combines smoothing with discrete levels gets calm, banded colors. The rounding of one frame depends only on that frame's own finished values, not on the other frames in the file.

**Why this priority**: These are the interactions with the existing settings. They define the result when features are combined but are secondary to the settings themselves.

**Independent Test**: With the Saturation step at 50 and smoothing at 0.8, every tile of every frame has a saturation of exactly 0, 50 or 100. Re-create the same file with a second of silence added at its end and confirm that the frames that differ are exactly those that differ without any step (at most the last original frame).

**Acceptance Scenarios**:

1. **Given** smoothing above 0 and a step other than N/A, **When** frames are drawn, **Then** each value is first smoothed exactly as today and then rounded to its levels, so with smoothing 0.8 the smoothed value is the one that is rounded.
2. **Given** the root settings for brightness and saturation, **When** a step is chosen, **Then** the root is applied first and its result is then rounded to the levels. The loudest frame still gets the highest brightness level (100) and a silent frame the lowest (0, black).
3. **Given** a hue step other than N/A, **When** hues are drawn, **Then** the hue of each tile after the related-note shifts and the smoothing is rounded to the levels of the 0° to 360° range.
4. **Given** any setting, **When** silence is added to the end of a file (which does not change the loudest value in it), **Then** the rounding adds no change to earlier frames: they are as they would be without a step, and the steps never make two runs differ where the unrounded runs do not. (As before this feature, colors are scaled against the loudest value in the file, and the last frame of the original file can change because its analysis window is cut short by the end of the file; both happen whether or not a step is chosen.)
5. **Given** a tile whose brightness is 0, **When** it is drawn with any hue and saturation levels, **Then** it stays black. Rounding hue or saturation never makes a black tile visible.

---

### Edge Cases

- **Three levels for hue** (step 180) are 0°, 180° and 360°: red, cyan and red again, since both ends of the wheel are red. The picture is therefore made of red and cyan only. This follows from the rule applied to every property; a smaller step gives more colors. The info text for Hue notes this.
- **Brightness at 3 levels** (step 50) makes every frame black, half bright or fully bright. A quiet recording can therefore be mostly black or dim, and the Brightness root setting (which lifts quiet frames) matters more.
- **Saturation at 3 levels** (step 50) makes each tile gray/white, half colored or fully colored.
- **Half-way values** round up to the higher level (a hue of 6° with step 12 shows as 12°).
- **Silent file**: every frame is black, whatever the settings are, and nothing fails.
- **Results from before this feature** (frames already created) are not changed. Only new submissions use the steps.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to choose three separate steps, one each for **hue**, **saturation** and **brightness**, in the settings of the page. For hue the choices MUST be N/A, 12, 36, 90 and 180 (degrees on a scale of 0 to 360). For saturation and brightness the choices MUST be N/A, 5, 10, 20 and 50 (on a scale of 0 to 100). The default for each MUST be N/A.
- **FR-002**: A step of N/A for a property MUST leave that property exactly as it was before this feature (no rounding). With all three at N/A the frames MUST be identical to those made before this feature.
- **FR-003**: A step *s* other than N/A MUST give a number of levels *N* = round((*range* + *s*) / *s*), where *range* is 360 for hue and 100 for saturation and brightness. Because every allowed step divides its range exactly, *N* is a whole number (hue 31, 11, 5, 3; saturation and brightness 21, 11, 6, 3) and is never fewer than 3.
- **FR-004**: When *N* levels are in effect for a property, the finished value of that property MUST be rounded to the nearest of the levels 0, *s*, 2*s*, … up to and including *range*. A value half-way between two levels MUST go to the higher one. The highest value of the range MUST always be reachable.
- **FR-005**: The scale of each property is: hue, the whole color wheel from 0° to 360°; saturation, from 0 (gray or white) to 100 (fully colored); brightness, from 0 (black) to 100 (full brightness).
- **FR-006**: Rounding MUST be applied as the last step for each property, after smoothing, after the root settings and after the related-note hue shifts. Smoothing itself MUST keep working on the unrounded values.
- **FR-007**: Rounding of a frame MUST depend only on that frame's own finished values, so that rounding adds no dependence on other frames: appending silence changes no frame by rounding (any difference, such as in the last original frame, is one that also occurs without a step).
- **FR-008**: Rounding MUST apply to each property separately: changing one step MUST NOT change the other two properties of any tile or frame.
- **FR-009**: A tile with brightness 0 MUST remain black whatever hue and saturation levels are in effect. The loudest frame MUST receive the highest brightness level, and a frame with no energy the lowest.
- **FR-010**: The page MUST show, for each property, a label, an info button with a short explanation, a dropdown list of the allowed choices (and no other input), and the number of levels the current choice gives (or "smooth" for N/A). The settings MUST be disabled while a job is running.
- **FR-011**: The server MUST refuse a step that is not one of the allowed choices for its property (including 0, negative numbers, a number that is not in the list, empty when sent, and text) with a clear message that lists the allowed choices, and MUST use N/A when a step is not sent at all.
- **FR-012**: The result summary and the server's response to a job MUST include the three steps that were used.
- **FR-013**: The same file and settings MUST always give identical frames.
- **FR-014**: Nothing else about the frames MUST change: the layout, size, frame count and timing, the note analysis, the way the other settings work, and the images' format. The documentation's description of the image and settings MUST be updated to describe the three new settings.

### Key Entities *(include if feature involves data)*

- **Step**: The distance between two neighboring levels of a property, chosen by the user from a short list (hue: 12, 36, 90, 180; saturation and brightness: 5, 10, 20, 50), or N/A for no steps.
- **Range**: The size of a property's scale: 360 for hue, 100 for saturation and brightness.
- **Number of levels**: The count of distinct values the property can take: round((range + step) / step). It is shown to the user next to the choice and is not entered separately.
- **Level**: One of the evenly spaced values 0, step, 2 × step … range, to which a finished hue, saturation or brightness is rounded.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With all three steps at N/A, 100% of the frames of a test file are identical, pixel for pixel, to those made before this feature.
- **SC-002**: With a step of 20 on saturation or brightness, every tile (or frame, for brightness) in a test file takes one of exactly the six values 0, 20, 40, 60, 80 and 100, and no other value appears. The same holds for each other allowed step with its own levels (hue step 90: 0°, 90°, 180°, 270° and 360°).
- **SC-003**: For each allowed step, the number of distinct values that appears in a rich test file is never greater than the number of levels given by the formula, and the highest value of the scale (360° or 100) is reachable. The number shown on the page is the same number.
- **SC-004**: At the largest step the saturation of every tile is exactly 0, 50 or 100, the brightness of every frame is exactly 0, 50 or 100, and the hue of every tile is exactly 0°, 180° or 360°.
- **SC-005**: Changing only one step changes none of the other two properties of any tile or frame (measured as the hue, saturation and brightness of each tile).
- **SC-006**: Adding a second of silence at the end of a file changes the same frames with a step as without one (none but the last original frame, as before this feature).
- **SC-007**: 100% of steps that are not in the allowed list for their property (0, negative, 7, 51, 90 for saturation, empty, text) are refused before a job is created, with a message that lists the allowed choices.
- **SC-008**: A user can find and read the explanation of each setting from its info button, and change the choice and see the resulting number of levels, without leaving the settings column.
- **SC-009**: Creating the same frames takes no more than 10% longer than before this feature.

## Assumptions

- **The "value" in the formula is the range** of the property (360 for hue, 100 for saturation and brightness), and the step is the "divisor". With both ends included, the formula equals range / step + 1, so the highest value is always one of the levels. This reading matches the examples given: hue 12 … 180 divide 360 evenly, and 5 … 50 divide 100 evenly.
- **N/A means "all" values** and leaves the property smooth. It is the starting choice for each, so existing behavior is the default.
- **Only the listed steps are allowed.** The page offers these choices and the server refuses any other number, so every level count is a whole number and no rounding of the count is needed in practice. The "round" in the formula is kept as written for safety.
- **"Luminance" and "brightness" are the same setting**: the request names both. The page has Hue, Saturation and Brightness, where Brightness is the frame's overall brightness (from the energy of the sound), and this is what the third setting controls. Saturation is each tile's own color intensity.
- **Hue is a bounded range, not a circle**: the existing hue is limited to 0° to 360° and not wrapped, so the two ends are treated as two different levels that look the same (both red).
- **Rounding is the last step** and runs after smoothing, so that the smoothing keeps its full precision between frames and does not collect rounding errors. The levels then also steady up the result of smoothing.
- **Rounding to nearest, half up** is used, so that results can be worked out by hand.
- **The API** gets three new optional form fields, one per property, treated like the other settings, and the response includes them; the page, the frame image format and size and everything else about the API stay as they are.
- This feature is about the image color only. Audio playback, analysis of notes, and the page layout (apart from adding three settings and a summary item) are unchanged.
