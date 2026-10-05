# Feature Specification: Window Spacing Parameter

**Feature Branch**: `003-window-spacing` (no git branch created; spec directory name only)

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "add another parameter to the visualizer that indicates the sample spacing. It will be expressed as a coefficient with respect to the window. So for instance, if the spacing is 0.25, and the window size is 8192, the second window will start at sample 2048. The default value should be based on the frame rate and the window size, so that each frame has a unique sample. The spacing default should be recalculated whenever these other parameters change. It should be rounded up if it is lower than 1 sample for the selected file. It can be larger than 1."

## Clarifications

### Session 2026-10-05

- Q: What sample rate should the default spacing assume before a file has been chosen? → A: 44.1 kHz (44,100 Hz), because almost all files use that rate. The default is recalculated from the file's actual rate as soon as a file is chosen.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Choose how far apart analysis windows start (Priority: P1)

A user creating frames from an audio file can set a **window spacing**: a number that says how far the start of each analysis window is from the start of the previous one, as a fraction of the window size. With a window size of 8192 and a spacing of 0.25, windows start at samples 0, 2048, 4096, and so on. A spacing of 1 means windows follow each other with no overlap, which is how the application behaved before this feature. Below 1 the windows overlap. Above 1 there are gaps between them, and the audio in the gaps is not analyzed.

**Why this priority**: This is the new capability. It controls how finely the analysis follows the music over time, independently of the window size, which sets how finely it separates notes.

**Independent Test**: Submit a file that is silent except for a tone that starts at sample 2048, with window size 8192 and spacing 0.25. Check that the results summary reports a window step of 2048 samples, and that the second window (which starts exactly where the tone starts) sees the tone exactly as if the tone alone had been analyzed, while the first window, which holds 2048 samples of silence before the tone, does not. Repeat with spacing 1 and check that the step is 8192 samples.

**Acceptance Scenarios**:

1. **Given** a window size of 8192 and a spacing of 0.25, **When** the user submits a file, **Then** the analysis uses windows starting at samples 0, 2048, 4096, and so on, and the results summary shows the spacing (0.25) and the step in samples (2048).
2. **Given** a spacing of 1, **When** the user submits a file, **Then** windows start at multiples of the window size, with no overlap and no gaps.
3. **Given** a spacing greater than 1 (for example 2), **When** the user submits a file, **Then** frames are still produced for the whole file, and the results summary shows the larger step in samples.
4. **Given** any accepted spacing, **When** the same file and settings are submitted twice, **Then** the frames are identical both times.
5. **Given** a completed submission, **When** the user reads the results summary, **Then** it shows the window spacing used, the step in samples, and the number of windows analyzed.

---

### User Story 2 - A default spacing that follows the other settings (Priority: P2)

The spacing field is filled in automatically with a value chosen so that every animation frame gets its own window. That value is calculated from the frame rate, the window size, and the sample rate of the chosen file. Whenever the user changes the window size, the frame rate, or the file, the field is recalculated and updated at once. The user can still type a different value.

**Why this priority**: Without a sensible default, users would have to work out the spacing by hand every time they change the frame rate or window size. It depends on Story 1.

**Independent Test**: Choose a 44,100 Hz file, set the frame rate to 30 and the window size to 4096. The field shows about 0.3589 (one frame is 1,470 samples, and 1,470 ÷ 4096). Change the frame rate to 60 and the field changes to about 0.1794. Change the window size to 8192 and it changes to about 0.0897. Submit with the untouched default and check that every frame has a window that starts within its own period.

**Acceptance Scenarios**:

1. **Given** a file is chosen, **When** the user changes the frame rate, **Then** the spacing field is recalculated immediately and shows the new default.
2. **Given** a file is chosen, **When** the user changes the window size, **Then** the spacing field is recalculated immediately and shows the new default.
3. **Given** the user has typed a custom spacing, **When** they then change the frame rate, the window size, or the file, **Then** the field goes back to the newly calculated default.
4. **Given** the default spacing and a submitted file, **When** frames are created, **Then** each frame's time period contains the start of at least one window, and no window belongs to more than one frame.
5. **Given** two files with different sample rates (for example 44,100 Hz and 48,000 Hz), the same frame rate and the same window size, **When** each is chosen, **Then** the defaults differ, because one frame holds a different number of samples in each file.
6. **Given** no file has been chosen yet, **When** the page is shown, **Then** the spacing field shows the default for a 44,100 Hz file, and it updates when a file is chosen.

---

### User Story 3 - Sensible limits and clear feedback (Priority: P3)

If the user enters a spacing that would be less than one sample, the value is raised to exactly one sample and the user is told. Values that are not positive numbers are refused with a message. A spacing small enough to create an unreasonable number of windows is refused before any work is done, with a message that suggests a larger value.

**Why this priority**: The main flow works without these, but the new parameter makes it easy to ask for something impossible or very slow.

**Independent Test**: With window size 4096, enter a spacing of 0.00001 (less than one sample): the field changes to the smallest allowed value (1 ÷ 4096) with a short explanation, or if submitted directly, the results show the step as 1 sample. Enter 0, -1, and "abc": each is refused with a message. Enter a tiny spacing that would create millions of windows: the submission is refused with the window count and the limit.

**Acceptance Scenarios**:

1. **Given** a spacing that gives a step below 1 sample for the chosen window size, **When** the user submits, **Then** the spacing is raised so the step is exactly 1 sample, the raised value is shown in the results summary, and the user is told it was raised.
2. **Given** a spacing of 0, a negative number, or text that is not a number, **When** the user edits the field or submits, **Then** a message says the spacing must be a number greater than 0, and submission is blocked until it is fixed.
3. **Given** a spacing that would create more than the maximum number of windows, **When** the user submits, **Then** the submission is refused before the analysis starts, with a message giving the window count and the limit and suggesting a larger spacing.
4. **Given** a spacing larger than 1, **When** the user enters it, **Then** it is accepted without complaint.
5. **Given** a rejected submission, **When** the user corrects the spacing, **Then** a new submission works without reloading the page.

---

### Edge Cases

- **Step is not a whole number of samples**: Spacing 0.3 with window size 4096 gives a step of 1,228.8 samples. Each window's start is the nearest whole sample to its exact position, counted from the start of the file, so rounding errors do not build up over a long file.
- **Spacing larger than the file**: If the step is longer than the audio, only one window (starting at sample 0) is analyzed, and every frame uses it.
- **Gaps between windows (spacing above 1)**: A frame period that has no window starting inside it uses the most recent window that started before the period. Audio that falls between windows contributes nothing, which is expected.
- **Overlap (spacing below 1)**: Each window is still the full window size. Several windows may start inside one frame period, and the frame shows their average.
- **Which frame a window belongs to**: A window belongs to the frame whose period contains its exact position (window number × step), not its rounded start sample. This keeps the frame guarantee in FR-008 true when a frame period is not a whole number of samples (for example 44,100 Hz at 11 frames per second).
- **Final frame**: If the audio ends within half a sample of the only window position in the last frame, that window would start past the end of the audio and hold only silence, so the last frame uses the previous window instead.
- **Final windows**: Windows keep starting every step until the start would pass the end of the audio. A window that runs past the end is padded with silence, as before.
- **Very short step with a long window**: A one-sample step with a 32768-sample window would need one transform per sample of audio. That is refused by the window limit.
- **Changing settings after a file is chosen**: Only the spacing field is recalculated, and the other fields keep what the user set.
- **Unreadable file**: If the sample rate of the chosen file cannot be determined, the file's own error is shown, and the default is calculated as for 44,100 Hz.
- **Custom value typed, then the file changed**: The typed value is replaced by the default for the new file.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The UI MUST provide a window spacing field, a number expressed as a multiple of the window size, which may be less than, equal to, or greater than 1.
- **FR-002**: The analysis MUST start window *k* (counting from 0) at the sample nearest to `k × spacing × window size`, for every *k* whose start is before the end of the audio. For example, with spacing 0.25 and window size 8192, the second window starts at sample 2048.
- **FR-003**: Each window MUST be the full window size, and a window that runs past the end of the audio MUST be padded with silence.
- **FR-004**: A spacing of 1 MUST give the same windows as before this feature (consecutive, non-overlapping).
- **FR-005**: The frames MUST be built by averaging, for each frame period, the windows that start inside it. If none starts inside it, the frame MUST use the most recent window that started before the period began. This keeps the earlier frame-averaging behavior and extends it to any spacing.
- **FR-006**: The spacing field MUST be filled with a default equal to the length of one frame period in samples, divided by the window size. The frame period in samples is the file's sample rate divided by the frame rate. The default is shown to at least 4 decimal places, rounded down, so that the step is never longer than one frame period.
- **FR-007**: The default MUST be recalculated, and the field updated, immediately when the window size, the frame rate, or the chosen file changes, and any value the user had typed MUST be replaced by the new default.
- **FR-008**: With the default spacing, every frame period MUST contain the start of at least one window, and no window may start in more than one frame period.
- **FR-009**: Before a file is chosen, the default MUST be calculated as if the file's sample rate were 44,100 Hz (the rate almost all files use). As soon as a file is chosen, the default MUST be recalculated from that file's actual sample rate (FR-007).
- **FR-010**: If the spacing gives a step of less than 1 sample for the chosen window size, the system MUST raise it so the step is exactly 1 sample (the spacing becomes 1 ÷ window size), and MUST tell the user the value was raised.
- **FR-011**: The system MUST refuse a spacing that is not a number or is not greater than 0, with a message saying the spacing must be a number greater than 0.
- **FR-012**: The system MUST refuse a request that would create more than the maximum number of windows, before any analysis is done, with a message giving the number of windows the request would create, the limit, and a suggestion to use a larger spacing.
- **FR-013**: The results summary MUST show the spacing actually used, the step in samples, and the number of windows analyzed.
- **FR-014**: Given the same file and settings, including spacing, the system MUST produce the same frames every time.
- **FR-015**: The new spacing field MUST follow the same rules as the other fields: it is disabled while a submission is running, it keeps its value after an error, and a corrected resubmission works without a page reload.

### Key Entities

- **Window Spacing**: The user-chosen coefficient (a positive number, a multiple of the window size) that sets the distance between the starts of consecutive windows.
- **Step**: The distance in samples between consecutive window starts, equal to spacing × window size, never less than 1 sample.
- **Default Spacing**: The calculated value that gives each frame its own window, from the frame rate, the window size and the file's sample rate.
- **Window Start**: The sample where a window begins, equal to the nearest whole sample to *k* × step.
- **Settings**: Now the window size, the frame rate, and the window spacing.
- **Submission Result**: Now also carries the spacing used, the step in samples and the number of windows analyzed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For window size 8192 and spacing 0.25, the second window starts at sample 2048, and the results summary reports a step of 2048 samples, in 100% of tested files.
- **SC-002**: A spacing of 1 produces exactly the same frames as the previous version of the application for the same file, window size and frame rate.
- **SC-003**: For every tested combination of frame rate (1 to 60), window size (4096 to 32768) and sample rate (44,100 and 48,000 Hz), the default spacing gives every frame period at least one window start, and no frame period shares a window with another.
- **SC-004**: After the user changes the window size, frame rate, or file, the spacing field shows the new default in under 1 second, with no submission needed.
- **SC-005**: A spacing that gives a step below 1 sample is always raised to exactly 1 sample, never rejected and never used as it was typed.
- **SC-006**: A spacing of 0, a negative number, or text is refused with a message that names the problem, in 100% of tested cases, with no crash.
- **SC-007**: With the default spacing, a 3-minute file at 30 frames per second still finishes within the earlier 60-second target for the whole submission.
- **SC-008**: A request that would create more than the window limit is refused in under 2 seconds, without starting the analysis.

## Assumptions

- **"Unique sample per frame" means each frame gets its own window.** The default step equals one frame period, so each frame period contains exactly one window start, or occasionally two because the default is rounded down. No window is shared between frames.
- **The default is recalculated from the exact file sample rate**, which the browser reads from the chosen file. Because the spec asks that the default follow the file, this feature requires the UI to know the file's sample rate before the file is submitted.
- **Typed values do not survive a change**: following the request that the default be recalculated whenever the other parameters change, any change to window size, frame rate or file replaces a custom spacing. A typed value is kept only until one of those changes.
- **Rounding**: The default is rounded down to 4 decimal places or more, so using it never leaves a frame without a window. "Rounded up" in the request is read as applying to the 1-sample minimum, as the request says.
- **No upper limit on spacing** other than that it is a finite number. A spacing so large that only one window fits in the file is allowed.
- **Window limit**: At most 60,000 windows per submission, which is twice the existing 30,000-frame limit. It is a server setting and can be changed. The default spacing never reaches it for files that already pass the frame limit.
- **Window size and frame rate** keep the rules from feature 002 (window size from the dropdown of 4096 to 32768, frame rate 1 to 60).
- **Dependencies**: This feature extends the window analysis from feature 001 (windows were consecutive and non-overlapping) and the upload and frame workflow from feature 002.
- **Scope**: Only the spacing parameter is added. The image layout, the brightness scale, and playback are unchanged.
