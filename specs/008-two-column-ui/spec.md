# Feature Specification: Two-Column UI

**Feature Branch**: `008-two-column-ui` (no git branch created; spec directory name only)

**Created**: 2026-10-06

**Status**: Draft

**Input**: User description: "the UI is looking crowded and we will be adding lots more parameters.  Create a 2-column view for the UI.  The left column will have the audio file chooser at the top, with the preview window and related controls/text right below it.  The right pane will have the controls.  Combine the samples, frame rate, and spacing into a row.  Change the explanatory text to be an info button that shows the explanation in a popover, so the form controls can take up less width."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preview on the left, settings on the right (Priority: P1)

A user opens the page and sees two columns side by side. The **left column** is about the audio and what it produces: the audio file chooser is at the top, and directly below it are the preview window (the frame image), the playback controls, and the text that describes the result (file name, duration, sample rate, frame count and the other summary details, plus any notice about the result). The **right column** holds the settings that shape the frames (window size, frame rate, window spacing, brightness, smoothing and any added later) and the button that creates the frames.

Because the settings live in their own column, new parameters can be added there without pushing the preview down the page or off the screen. The user can change a setting, press "Create frames", and see the new preview without scrolling between them.

**Why this priority**: This is the core of the request. The page is already crowded and more parameters are coming, so the split layout is what makes room for them.

**Independent Test**: Open the page on a normal desktop-width window. The file chooser and preview area are in the left column and all the settings and the "Create frames" button are in the right column. Choose a file, create frames, and confirm the preview, playback controls and summary text appear under the file chooser in the left column while the settings stay in view on the right.

**Acceptance Scenarios**:

1. **Given** the page is open at desktop width, **When** it loads, **Then** two columns are shown side by side, with the audio file chooser at the top of the left column and the settings controls in the right column.
2. **Given** no frames have been created yet, **When** the page loads, **Then** the left column shows the file chooser (with its file name, size and any file error text) and an empty area where the preview will appear, and the right column shows every setting with its default value.
3. **Given** frames have been created, **When** the result arrives, **Then** the preview window, its playback controls (play/pause, loop, frame slider, time and frame position) and the result summary text appear directly below the file chooser in the left column, and nothing from them appears in the right column.
4. **Given** frames have been created, **When** the user changes a setting and creates frames again, **Then** the left column updates with the new preview and summary and the right column keeps the user's settings in place.
5. **Given** a job is running or has failed, **When** the progress message or the error message is shown, **Then** it appears in the left column with the preview and result text, so the user sees the outcome next to where the preview will appear.
6. **Given** more settings are added to the right column in future, **When** the column grows taller than the window, **Then** the preview stays in the left column and is not pushed down by the additional settings.

---

### User Story 2 - Frame rate, window size and spacing share a row (Priority: P2)

In the right column, the three settings that decide how the audio is cut into windows and frames sit in **one row** instead of three stacked fields: the number of samples (window size), the frame rate, and the window spacing. Each keeps its own label, its own value and its own error message, if any. The row saves vertical space and shows the three related settings together.

**Why this priority**: It reduces crowding in the settings column, but the page works without it, so it follows the two-column layout.

**Independent Test**: Open the page at desktop width. Window size ("samples"), frame rate and window spacing are side by side on one row of the right column. Enter an invalid frame rate and confirm its error appears with that field without breaking the row. Change the window size and confirm the spacing default still updates as before.

**Acceptance Scenarios**:

1. **Given** the page is open at desktop width, **When** the user looks at the settings column, **Then** window size, frame rate and window spacing appear next to each other on a single row, each with its label.
2. **Given** an invalid value in any of the three fields, **When** the error is shown, **Then** it is shown with that field, the other two fields still show their values, and "Create frames" stays unavailable as it is today.
3. **Given** the user changes the window size or the frame rate, **When** the default spacing is recalculated, **Then** the spacing field updates exactly as it did before this feature.
4. **Given** the spacing is below the minimum, **When** the notice is shown, **Then** it is shown with the spacing field and is still readable.

---

### User Story 3 - Explanations move into info popovers (Priority: P2)

Today each setting has a line of explanatory text under it (for example "Larger windows separate low notes better but blur changes over time."). This text makes each field wide and tall. Each setting now has a small **info button** beside its label instead. When the user clicks (or taps, or focuses and activates with the keyboard) the button, a **popover** opens next to it and shows the same explanation. The explanation is no longer printed under the field, so the form controls can use that width and height.

Problems the user must act on are not explanations and stay visible: validation errors and the "spacing below the minimum" notice remain shown with their field, not hidden in a popover.

**Why this priority**: It frees up width and height in the settings column and makes it possible to add many more parameters with their own explanations. It is independent of the column split, so it follows the layout.

**Independent Test**: In the settings column, no explanatory sentence is printed under any field. Each setting has an info button. Activating it shows that setting's explanation in a popover, and pressing Escape or clicking elsewhere closes it. Enter an invalid value and confirm the error text is still shown under the field without opening any popover.

**Acceptance Scenarios**:

1. **Given** the page is open, **When** the user looks at the settings, **Then** no setting shows a line of explanatory text under its field, and each setting that had one shows an info button next to its label.
2. **Given** an info button, **When** the user activates it with the mouse, touch or the keyboard, **Then** a popover appears next to the button with the explanation that used to be printed under the field.
3. **Given** a popover is open, **When** the user presses Escape, clicks or taps outside it, or activates the info button again, **Then** the popover closes.
4. **Given** a popover is open, **When** the user opens another setting's popover, **Then** the first one closes, so only one explanation is open at a time.
5. **Given** a setting has a validation error, **When** the error appears, **Then** it is shown under that field as before, whether or not its popover is open.
6. **Given** the window is narrow, **When** a popover opens near an edge, **Then** it stays fully inside the visible window and its text is readable.
7. **Given** a user who relies on a keyboard or a screen reader, **When** they reach an info button, **Then** it has a name that says what it explains (for example "About window size"), it can be operated without a mouse, and the popover text is announced or reachable when it opens.

---

### User Story 4 - Narrow windows fall back to one column (Priority: P3)

When the window is too narrow for two columns to be comfortable (a phone or a small browser window), the page shows a single column: the file chooser and preview first, then the settings. Nothing is cut off and no horizontal scrolling is needed.

**Why this priority**: The request is about the desktop layout. A sensible fallback keeps the page usable elsewhere without being part of the main ask.

**Independent Test**: Narrow the browser window to phone width. The two columns stack, the left column's content comes first, and every control and popover can still be used without scrolling sideways.

**Acceptance Scenarios**:

1. **Given** a narrow window, **When** the page is shown, **Then** the columns are stacked with the left column's content first and the settings after it.
2. **Given** a narrow window, **When** the three-in-a-row settings do not fit, **Then** they wrap onto more than one line, and each stays readable and usable.

---

### Edge Cases

- A file is not chosen and the user opens the page: the left column shows the chooser and the "Choose a .wav file." prompt, and the preview area is empty, not broken.
- A very long file name: it is shortened or wrapped inside the left column and does not widen the column or overlap the settings.
- The result summary has many items: it wraps inside the left column, and the preview keeps its proportions.
- The user opens a popover and then the job starts (controls become disabled): the popover can still be opened and closed, since reading an explanation is not an editing action.
- A popover is open when the window is resized or the layout switches between one and two columns: the popover stays attached to its button or closes. It never stays stranded in the wrong place.
- Many more settings are added in future: the right column grows (and scrolls with the page if needed) without changing the left column's layout.
- Validation messages (error and notice) are long: they wrap within their field's width and do not break the single row of three settings.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: At desktop width the page MUST show two columns side by side: a left column for the audio and its result, and a right column for the settings.
- **FR-002**: The left column MUST have the audio file chooser at the top, with its file name and size text, its "Choose a .wav file." prompt and its file error, followed directly below by the preview window, the playback controls and the result text (the summary details and any notice about the result).
- **FR-003**: The progress message and the error message for a job MUST appear in the left column with the preview and result text.
- **FR-004**: The right column MUST contain every setting that shapes the frames (window size, frame rate, window spacing, brightness and smoothing) and the "Create frames" button, and no preview or result text.
- **FR-005**: The window size, frame rate and window spacing settings MUST be shown together on a single row in the right column at desktop width, each with its own label and its own validation message.
- **FR-006**: Each setting that now has a line of explanatory text MUST instead show an info button next to its label, and the explanation MUST NOT be printed under the field.
- **FR-007**: Activating an info button (mouse, touch or keyboard) MUST open a popover next to it that shows that setting's existing explanation text, unchanged in meaning.
- **FR-008**: A popover MUST close on Escape, on a click or tap outside it, and when its info button is activated again. At most one popover MUST be open at a time.
- **FR-009**: Validation errors and the below-minimum spacing notice MUST remain visible with their field and MUST NOT be moved into a popover.
- **FR-010**: Info buttons and popovers MUST be usable with the keyboard and with a screen reader: each button MUST have a name that identifies its setting, and the popover text MUST be reachable when it is open.
- **FR-011**: A popover MUST remain fully inside the visible window, including near the window's edges and at narrow widths.
- **FR-012**: Below a narrow-window width the columns MUST stack into one column, with the left column's content first, and no horizontal scrolling MUST be required.
- **FR-013**: Adding a further setting to the right column MUST NOT move or resize the left column's contents.
- **FR-014**: Behavior MUST NOT change apart from layout and the explanatory text: the same settings, defaults, ranges, validation rules and messages, the default-spacing recalculation, the submission of a job, the generated frames, the playback behavior and the result text MUST all work as they did before this feature.
- **FR-015**: Controls MUST stay disabled while a job is running as they are today, except that info buttons and popovers MUST still work.

### Key Entities *(include if feature involves data)*

- **Setting**: One adjustable parameter (window size, frame rate, window spacing, brightness, smoothing, and others added later). It has a label, a control, an optional validation message and an optional explanation. The explanation is shown on request in a popover. The label, value and message are always visible.
- **Explanation**: The short text that says what a setting does. It is the text that used to be printed under the field, now shown on request next to the setting's info button.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At a desktop window width of 1280 pixels, the file chooser, the preview and the "Create frames" button are all visible together without scrolling, with the current five settings.
- **SC-002**: A user can change any setting and view the resulting new preview without scrolling the page up or down between them, at 1280 pixels width.
- **SC-003**: The settings column is at least 30% shorter than the current single-column form with the same five settings, measured at the same window width.
- **SC-004**: Window size, frame rate and window spacing share one row, so the settings column takes three fewer stacked field rows than today.
- **SC-005**: Adding a sixth through tenth setting to the right column leaves the position and size of the preview unchanged.
- **SC-006**: Every explanation that was shown before is readable by activating its info button, and 100% of the info buttons can be opened and closed with the keyboard alone.
- **SC-007**: At a 360-pixel window width, every control, message and popover can be reached and used without sideways scrolling.
- **SC-008**: Creating frames from the same file and settings gives the same frames and the same result text as before this feature (no change in outputs).

## Assumptions

- "Samples" in the request means the existing **window size (samples)** setting.
- "The preview window and related controls/text" means the frame image, its playback controls and the result summary that appear after frames are created. The progress and error messages for a job are grouped with them in the left column, so outcomes appear next to the preview.
- The "Create frames" button belongs to the settings, so it is placed at the bottom of the right column, where the user finishes entering settings.
- "Explanatory text" means the helper line under each setting (for window size, frame rate, brightness and smoothing, and the step hint under window spacing). Short prompts that tell the user what to do, such as "Choose a .wav file." and the chosen file's name and size, are not explanations and stay visible in the left column.
- Validation errors and the below-minimum spacing notice are things the user must act on, so they stay visible with their field instead of moving into a popover. The step-between-windows hint under spacing is treated as an explanation and moves into that setting's popover.
- Where a setting's helper line included a range (for example "1 to 60" for frame rate), that range stays in the popover text, and the field still enforces and reports it as before.
- The layout is for desktop first; the stacked one-column fallback is the simple, usual behavior for narrow windows, and its exact breakpoint is a design choice.
- This feature changes layout and presentation only. It does not add, remove or change any setting, the analysis, the frames, or the data sent for a job.
- The page keeps its current look in other respects (fonts, colors, tile preview, and so on).
