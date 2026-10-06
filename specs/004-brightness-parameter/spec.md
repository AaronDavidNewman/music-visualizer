# Feature Specification: Brightness Parameter

**Feature Branch**: `004-brightness-parameter` (no git branch created; spec directory name only)

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "create a new parameter called 'brightness' that an integer from 2 to 100. boost_levels will then do 255*np.pow(a/255, 1/x). So it will use the nth root rather than just the square root."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Choose how strongly quiet notes are brightened (Priority: P1)

A user creating frames sets a **brightness**, a whole number from 2 to 100. Each square in a frame is first scaled to a gray level from 0 to 255 against the loudest value in the file (as today), and the brightness then changes how much quiet values are lifted: the displayed level is 255 × (level ÷ 255) raised to the power 1 ÷ brightness, which is the brightness-th root of the level. With brightness 2 this is the square root used now. A higher brightness lifts quiet notes more, so dim frames show more detail in the quiet notes. Black stays black and the loudest value stays white at every setting.

**Why this priority**: The images are currently too dark to read on real music, and the single fixed square root is not enough for every file. This is the whole feature.

**Independent Test**: Submit the same file three times with brightness 2, 4 and 10. For a square at gray level 64 (about a quarter of full brightness) the displayed level is 128, 180 and 222. Compare the same frame in the three results: every square is at least as bright at 4 as at 2, and at 10 as at 4, and the average gray level of the frame rises each time.

**Acceptance Scenarios**:

1. **Given** brightness 2, **When** frames are created, **Then** they are identical to the frames the application produced before this parameter existed (the square-root boost).
2. **Given** a brightness of 4, **When** frames are created, **Then** each square's displayed level is 255 × (level ÷ 255)^(1/4) rounded to a whole gray level, so a level of 64 shows as 180.
3. **Given** any brightness from 2 to 100, **When** frames are created, **Then** a square at level 0 stays black (0) and a square at level 255 stays white (255).
4. **Given** two submissions of the same file and settings that differ only in brightness, **When** the frames are compared, **Then** no square is darker in the higher-brightness result, and the number of frames, the number of windows and the timing of each frame are the same.
5. **Given** a silent file at any brightness, **When** frames are created, **Then** every square is black.
6. **Given** a completed submission, **When** the user reads the results summary, **Then** it shows the brightness that was used.

---

### User Story 2 - A brightness control with clear limits (Priority: P2)

The form has a brightness field that accepts only whole numbers from 2 to 100, shows that range, starts at 2, and keeps its value after an error or a completed submission. A value that is not a whole number, or is outside the range, is refused with a message that says what is allowed. The server checks the same rule, so the field cannot be bypassed.

**Why this priority**: The core feature works from a script without the form, but users need a control that stops bad values before they wait for an upload, and a server that refuses them when the form is bypassed.

**Independent Test**: Enter 1, 101, 2.5, 0, -3, `abc` and an empty value: each shows a message naming the allowed range and blocks submission. Enter 2 and 100: both are accepted. Send a request directly with brightness 1 and 101: both are refused with the same message.

**Acceptance Scenarios**:

1. **Given** the page is opened, **When** the form is shown, **Then** the brightness field shows 2 and the allowed range (2 to 100).
2. **Given** a brightness of 1, 101, a decimal, a negative number, text or an empty value, **When** the user edits the field, **Then** a message says the brightness must be a whole number from 2 to 100, and submission is blocked until it is fixed.
3. **Given** a request sent directly to the server with an invalid brightness, **When** it is processed, **Then** it is refused with the same message before any analysis starts, and nothing is left stored.
4. **Given** a request with no brightness, **When** it is processed, **Then** brightness 2 is used.
5. **Given** a submission that failed for any reason, **When** the user looks at the form, **Then** the brightness they entered is still there, and a corrected resubmission works without reloading the page.
6. **Given** a submission is running, **When** the user looks at the form, **Then** the brightness field is disabled like the other fields.

---

### Edge Cases

- **High brightness flattens contrast**: Raising brightness lifts every non-zero level toward white. At brightness 100 a level of 1 (almost silent) shows as 241, and a level of 64 shows as 251, so quiet and loud notes look almost the same. This is the expected effect of a high setting, and the form says that higher values brighten more but show less contrast.
- **Rounding**: Each displayed level is rounded to the nearest whole gray level.
- **Brightness 2 is the minimum**: There is no setting darker than the current square-root look, and no setting that leaves the linear scale.
- **Whole numbers only**: 2.5 is refused. A whole number written with a decimal point (such as 5.0) is treated as that whole number.
- **Changing brightness needs a new submission**: Frames are made when the file is submitted, so a different brightness means submitting again. Nothing about the window or frame settings changes.
- **Other settings unaffected**: Window size, frame rate, window spacing and the 0–255 scaling against the loudest value are unchanged, and brightness changes only how the final gray levels look.
- **Very loud single peak**: Because levels are scaled against the loudest value in the file, one loud moment can make the rest of the file dim. Brightness lifts the whole picture but does not change that scaling.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The UI MUST provide a brightness field that accepts a whole number from 2 to 100, shows the allowed range, and defaults to 2.
- **FR-002**: The UI MUST refuse a brightness that is not a whole number from 2 to 100 with a message stating the allowed range, and MUST block submission until it is valid.
- **FR-003**: The server MUST accept a brightness with a submission, and MUST use 2 when none is given.
- **FR-004**: The server MUST refuse a brightness that is not a whole number from 2 to 100, with the same message as the UI, before any analysis, and MUST store nothing for the refused request.
- **FR-005**: For each square, the displayed gray level MUST be 255 × (level ÷ 255)^(1 ÷ brightness), rounded to the nearest whole gray level, where *level* is the square's existing 0–255 level scaled against the loudest value in the file.
- **FR-006**: At every brightness from 2 to 100, a level of 0 MUST display as 0 and a level of 255 MUST display as 255.
- **FR-007**: For any level, a higher brightness MUST never display darker than a lower brightness, and for any brightness a higher level MUST never display darker than a lower level.
- **FR-008**: With brightness 2, the frames MUST be identical to those produced before this parameter existed.
- **FR-009**: Brightness MUST NOT change the number of frames, the analysis windows, the frame timing, or the window and frame calculations. It affects only the gray levels in the images.
- **FR-010**: The results summary MUST show the brightness used.
- **FR-011**: The brightness field MUST be disabled while a submission is running, MUST keep its value after an error or a completed submission, and a corrected resubmission MUST work without reloading the page.
- **FR-012**: Given the same file and settings, including brightness, the system MUST produce the same images every time.
- **FR-013**: The form MUST tell the user that a higher brightness lifts quiet notes more but shows less contrast.

### Key Entities

- **Brightness**: A whole number from 2 to 100 chosen by the user. It is the root applied to each gray level: the brightness-th root. 2 means the square root.
- **Gray level**: The 0–255 value of a square after scaling against the loudest value in the file and before the brightness is applied.
- **Displayed level**: The 0–255 value actually drawn in the image after the brightness is applied.
- **Settings**: Now the window size, the frame rate, the window spacing and the brightness.
- **Submission Result**: Now also carries the brightness used.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With brightness 2, the images for the same file and settings are identical, pixel for pixel, to the images from before this parameter existed, in 100% of tested files.
- **SC-002**: For every whole brightness from 2 to 100 and every level from 0 to 255, the displayed level equals 255 × (level ÷ 255)^(1 ÷ brightness) rounded to a whole number. For example, level 64 shows as 128 at brightness 2, 180 at 4, 222 at 10, and 251 at 100.
- **SC-003**: Raising the brightness never makes any square darker, and on the sample music file, going from brightness 2 to 4 raises the average gray level of a typical frame by at least 25%.
- **SC-004**: Level 0 shows as black and level 255 shows as white at all 99 settings.
- **SC-005**: A brightness of 1, 101, a decimal, a negative number, text or an empty value is refused with a message naming the 2 to 100 range, in 100% of tested cases, both in the form and when sent directly to the server, with no crash and nothing stored.
- **SC-006**: Changing only the brightness does not change the frame count, the window count, or the time taken by more than 10%.
- **SC-007**: A user can change the brightness and see the new frames after one resubmission, with no page reload.

## Assumptions

- **Default**: The default is 2, the lowest allowed value. It gives exactly the look the application has now (the square-root boost), so existing behavior is unchanged unless the user raises it.
- **Direction**: A higher brightness means a brighter picture. The formula uses the brightness-th root, and roots of values between 0 and 1 rise toward 1 as the root gets higher.
- **Where it applies**: The formula is applied to the existing 0–255 levels (scaled against the loudest value in the file), as the user described for the boost step. It does not change how those levels are calculated.
- **Whole numbers only**: As requested, brightness is an integer. Fractional roots are not offered.
- **Fixed range**: 2 to 100 is fixed in this feature. The limits are not user-configurable. They can be changed later if needed.
- **New submission needed**: Changing the brightness means submitting again, because frames are made at submission time. Re-rendering existing frames without re-analyzing is out of scope.
- **Dependencies**: This feature changes the display step added to feature 002 (the square-root boost) and adds a field to the form and request from features 002 and 003.
- **Scope**: Only the brightness parameter is added. Per-frame scaling, logarithmic scales, and other volume normalization remain out of scope.
