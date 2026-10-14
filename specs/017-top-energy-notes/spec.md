# Feature Specification: Top-Energy Notes

**Feature Branch**: `017-top-energy-notes` (no git branch created; spec directory name only)

**Created**: 2026-10-12

**Status**: Draft

**Input**: User description: "allow the user to pick the n highest-energy notes instead of all 84.  This will make the images less jittery in some cases, and can represent the music more accurately in a sense.  The user should be able to pick anywhere from 12 to 84 notes.  The smoothed values are still interpolated to the same size values (at least 12x7) but over fewer values."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A picture made from only the strongest notes (Priority: P1)

Today every picture shows all 84 drawn notes, so the quiet notes that carry little of the music (leakage from loud notes, background noise, notes that hardly ever sound) flicker in and out and make the picture jittery. The user wants to keep only the **n notes with the most energy** and build the picture from those, with n chosen from **12 to 84** (84 meaning all of them, as today).

A note's **energy** is how much sound it carries in the whole file: the sum of its smoothed values over all frames. The n notes with the highest energy are chosen once for the whole file, so **the same notes are used in every frame** (the choice never flips from frame to frame, which is itself a source of steadiness). The chosen notes keep their order from the lowest pitch to the highest. For each frame the n values of those notes are then **interpolated** to the same number of values that the picture has today (one for each cell of the 12 × 7 grid, or of the finer grid if the Resolution setting is above 1), by spreading evenly spaced positions over the n values and reading them by linear interpolation. The picture is made from that grid as before, for every image type. With fewer values to spread, each chosen note covers a larger part of the picture: fewer, bigger features instead of 84 small ones.

**Why this priority**: This is the whole feature: choosing the notes and the picture built from them. The page control (Story 2) and the combination with the other settings (Story 3) build on it.

**Independent Test**: Make frames from a file in which a handful of notes sound strongly and many others carry only faint noise. At 84 notes the picture is as it is today. At 12 notes the picture is made from the 12 strongest notes only: the faint notes no longer appear, the strong notes are larger in the picture, and the picture changes less from frame to frame.

**Acceptance Scenarios**:

1. **Given** 84 notes, **When** frames are made with any image type, **Then** they are identical, file for file, to those made before this feature.
2. **Given** a number n of notes from 12 to 83, **When** frames are made, **Then** the notes used are the n drawn notes with the largest total of smoothed values over the file, the same notes in every frame, in their order of pitch.
3. **Given** two notes with the same energy at the edge of the choice, **When** one of them must be left out, **Then** the one with the higher pitch is left out (the choice is the same every time).
4. **Given** the chosen notes, **When** a frame is made, **Then** its n smoothed values are spread over the full grid by linear interpolation: the first chosen note is at the first position of the grid, the last chosen note at the last position, and every other value is between the values of its neighbors, so no value in the picture is louder than the loudest chosen note.
5. **Given** a number n below 84, **When** a frame is made, **Then** a note that is not among the n chosen contributes nothing to the picture in any frame, even in a frame in which it is loud.
6. **Given** a file in which no note has any energy (silence), **When** frames are made at any n, **Then** the pictures are as flat as they are at 84 notes, and nothing fails.
7. **Given** the same file and settings, **When** frames are created twice, **Then** the two sets of frames are identical.
8. **Given** the number of frames and the timing of the file, **When** frames are created with any number of notes, **Then** they are the same as with 84 notes.

---

### User Story 2 - Choose the number of notes on the page and through the server (Priority: P2)

The settings column has a new **Notes** control: a slider from 12 to 84 in whole steps, starting at 84, with a readout that says what it means ("All 84 notes", "36 of 84 notes") and an info button that explains it. The result summary shows the number of notes used. In requests the setting is the optional field `note_count`, a whole number from 12 to 84 (84 when not sent). A value that is not a whole number from 12 to 84 is refused with a clear message, and the response reports the number used. The control works with every image type.

**Why this priority**: The new picture (Story 1) can be asked for through the server, but users need to choose it on the page.

**Independent Test**: Open the page, move the Notes slider to 24, create frames, and see the picture made from the 24 strongest notes and "Notes: 24 of 84" in the summary. Move it back to 84 and create again: the original picture.

**Acceptance Scenarios**:

1. **Given** the page is opened, **When** the settings are shown, **Then** the Notes control is there, set to 84, with its readout "All 84 notes" and an info button.
2. **Given** the slider is moved, **When** the user looks at the readout, **Then** it shows how many notes are used out of 84 (for example "36 of 84 notes").
3. **Given** the user activates the Notes info button, **When** the popover opens, **Then** it explains that only the notes with the most energy in the whole file are used, that fewer notes make bigger and steadier features, and that the range is 12 to 84.
4. **Given** frames have been created, **When** the result is shown, **Then** the summary includes the number of notes used (for example "Notes: 24 of 84", or "Notes: All 84").
5. **Given** a request with `note_count` set to a whole number from 12 to 84, **When** the server receives it, **Then** it creates frames from that many notes and the response reports `note_count`.
6. **Given** a request without `note_count`, **When** the server receives it, **Then** all 84 notes are used and the frames are those of today.
7. **Given** a request with a value that is empty, not a number, not a whole number, below 12 or above 84, **When** the server receives it, **Then** it is refused before a job is created, with a message that says it must be a whole number from 12 to 84.
8. **Given** the slider, **When** a job is running, **Then** the control is disabled, like the other settings.

---

### User Story 3 - It works with smoothing, resolution, the threshold, the colormap and every image type (Priority: P3)

The choice is made on the smoothed values, so Smoothing and its window apply first. The Resolution setting then makes the grid finer from the n interpolated values as it does from 84. The Threshold, the Colormap and the Blend width keep working on the finished grid, and the colors keep the scale they have today, so the same strength has the same color whatever number of notes is chosen. A job with few notes still finishes in a practical time.

**Why this priority**: These are the interactions with the existing settings and the practical limits. They define the result when features are combined but are secondary to the picture itself.

**Independent Test**: Create frames with 24 notes, smoothing 0.5 and window 3, resolution 3, a Threshold of 5 and each colormap, once for each image type, for a 10 second file at 30 frames per second. Each job finishes within a minute, the pictures use the colormap, and the choice of notes is the same in every frame.

**Acceptance Scenarios**:

1. **Given** smoothing above 0, **When** frames are made with fewer notes, **Then** the energy and the values are those of the smoothed note values (the same ones the tiles are colored from at 84 notes).
2. **Given** a Resolution above 1, **When** frames are made with fewer notes, **Then** the n values are first spread over the original 12 × 7 grid (84 values) and that grid is then made finer by the Resolution setting as it is for 84 notes.
3. **Given** a Threshold above 0, **When** a value of the finished grid is below the threshold (a share of the loudest note value in the file), **Then** its tile is black (Tiles, Blended tiles) or it is treated as 0 (Contour); the reference is the same file-wide loudest value as with 84 notes.
4. **Given** any colormap that the page offers, **When** frames are made with fewer notes, **Then** they use that colormap with the same scale as with 84 notes, and changing the colormap changes only the colors.
5. **Given** the three image types, **When** frames are made with fewer notes, **Then** each of them draws the same grid of values in its own way.
6. **Given** a file of 10 seconds at 30 frames per second (300 frames), **When** frames are created with any number of notes and Resolution 5, **Then** the job finishes within one minute on the development machine for each image type.

---

### Edge Cases

- **84 notes** is all of them: nothing is left out and nothing is interpolated, so it is exactly today's behavior.
- **12 notes**, the smallest choice: the 12 strongest notes are spread over the whole grid, so each note covers about 7 cells of the original 84.
- **A file with fewer than n sounding notes**: the notes with no energy are still counted among the n (they have the value 0), so the choice always has exactly n notes; their zeros appear in the picture as quiet areas.
- **A silent file**: no note has energy, so the choice falls back to the order rule (lower pitch first); every value is 0 and the picture is as flat as at 84 notes.
- **The four highest notes (84 to 87)**, which are not drawn, do not take part in the choice (only the 84 drawn notes can be chosen) but still count when the file's largest value is found, as for every setting.
- **A loud note that is not among the n**: it is left out of the picture in every frame, even where it is the loudest note of the moment. The colors' scale and the Threshold's reference are still the file's largest value, so a picture without that note can look dimmer than with it.
- **Notes with equal energy**: ties are broken by pitch (the lower note is kept), so the choice is the same every time.
- **Results from before this feature** (frames already created) are not changed. Only new submissions can use the setting.
- **Steadiness is not guaranteed**: fewer notes remove the flicker of faint notes, but every remaining note covers more of the picture, so a note that changes now changes a larger area. The picture is steadier mainly for sustained notes in noise, and can be less steady for notes that start and stop quickly.
- **Position in the picture**: with fewer than 84 notes a position in the picture no longer stands for one fixed note: the picture is a stretched view of the chosen notes from the lowest pitch to the highest.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to choose the **number of notes** n, a whole number from 12 to 84, **84** being the default on the page and when a request does not say. At 84 every image type MUST give frames identical, file for file, to those made before this feature.
- **FR-002**: For n below 84, the notes used MUST be the n of the 84 drawn notes with the largest **energy**, where the energy of a note is the sum of its smoothed values over all frames of the file. The same n notes MUST be used in every frame of the file. Ties MUST be broken in favor of the lower note, so that the choice is repeatable.
- **FR-003**: The chosen notes MUST keep their order of pitch. For each frame their n smoothed values MUST be spread over 84 values by interpolation: evenly spaced positions made with `np.linspace` from the first to the last chosen note (84 of them), with the values read by linear interpolation (`np.interp`) between the chosen notes. The first chosen note keeps its value at the first position, the last at the last, and every value is between the values of its neighbors.
- **FR-004**: The 84 interpolated values MUST then be used exactly as the 84 note values are today (the grid of 12 columns by 7 rows, then the Resolution setting, the Threshold, the colors and the image type), so each image type draws them in its own way.
- **FR-005**: A note that is not chosen MUST have no effect on any picture of the file, whatever its value in a frame.
- **FR-006**: The colors' scale and the Threshold's reference MUST be the largest smoothed note value of the whole file over all 88 notes, as today, so the same strength has the same color whatever number of notes is chosen.
- **FR-007**: Smoothing and its window MUST be applied before the energy is found and before the interpolation. A file in which no note has any energy MUST give the same flat pictures as at 84 notes, without error.
- **FR-008**: The frame count, the timing of the frames, the picture size and the file names MUST be the same for every number of notes, and the same file and settings MUST always give identical frames.
- **FR-009**: The page MUST offer the **Notes** control (a slider from 12 to 84 in whole steps, starting at 84) with a readout of how many of the 84 notes are used, an info button that explains it, and a result summary line that shows the number used; the control MUST be disabled while a job runs.
- **FR-010**: The server MUST accept the optional field `note_count`, refuse a value that is not a whole number from 12 to 84 (including an empty value) with a clear message, before any job is created, and report the number used in its response.
- **FR-011**: A job with any number of notes, with the Resolution at its highest, MUST finish in a practical time for every image type (SC-005).
- **FR-012**: The documentation's description of the settings MUST be updated to describe the number of notes.

### Key Entities *(include if feature involves data)*

- **Number of notes**: The whole number from 12 to 84 chosen for each job: how many of the 84 drawn notes make up the picture. 84 means all of them.
- **Energy**: For one note, the sum of its smoothed values over all frames of the file; the measure by which notes are ranked.
- **Chosen notes**: The n drawn notes with the largest energy, in order of pitch, the same for every frame of a file.
- **Spread grid**: The 84 values of one frame made from the chosen notes' n values by interpolation; it takes the place of the 84 note values in everything that follows.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With 84 notes, 100% of the frames of a test file are identical, file for file, to those made before this feature, for every image type.
- **SC-002**: With n notes, the notes used are exactly the n drawn notes with the largest total smoothed value over the file (ties to the lower note), and they are the same in 100% of the frames.
- **SC-003**: With n notes, a note outside the chosen n changes no pixel of any frame: two files that differ only in the values of non-chosen notes give identical frames.
- **SC-004**: For every frame and every n, the spread values start at the first chosen note's value and end at the last chosen note's value, and none is below the smallest or above the largest chosen value.
- **SC-005**: A job of 300 frames (10 seconds at 30 frames per second) with the highest Resolution finishes within one minute on the development machine for each of the three image types, whatever the number of notes.
- **SC-006**: 100% of invalid numbers of notes (empty, not a number, fractional, below 12, above 84) are refused before a job is created, with a message that says the number must be a whole number from 12 to 84.
- **SC-007**: The faint notes no longer appear (SC-003), and on a test file of sustained notes with strong broadband noise the average frame-to-frame change of the picture's colors (the change in position along the colormap scale, averaged over all cells) is smaller with 12 notes than with 84. This is not promised for every file: measured on synthetic files, the average change of the raw values *grows* as notes are dropped (each remaining note covers more of the picture), and for quickly changing notes or little noise the colors can change more, not less. The user's "in some cases" is the honest scope.
- **SC-008**: A user can set the number of notes on the page, read what it does, and see the pictures in the player without leaving the settings column.

## Assumptions

- **Energy is measured over the whole file**, not frame by frame: the request says to pick "the n highest-energy notes" and hopes for less jitter, and a choice that is made once for the file cannot flicker from frame to frame, while a choice made in every frame would. A note's energy is the sum of its smoothed values; the sum of squares (power) would favor loud notes more, and could be used later without changing the rest.
- **Chosen notes are dropped, not zeroed**: the request says the values are "interpolated ... over fewer values", so the n chosen values are spread over the whole grid (each chosen note covering more of the picture), rather than the other notes being set to 0 inside an unchanged grid.
- **The spread is made in one dimension, in order of pitch, to the 84 values of the original grid**: the chosen n values (a sequence from the lowest to the highest pitch) are resampled to 84 values, which are arranged as the original 12 × 7 grid (row = octave position, column = note position, filled row by row); the Resolution setting then makes that grid finer as it does today. This keeps every later step unchanged, and gives exactly today's picture at 84 notes. The request's "(at least 12x7)" is read as the size of the finished grid, which is 12 × 7 at Resolution 1 and larger above it.
- **Only the 84 drawn notes can be chosen**; the four highest, undrawn notes do not compete but count for the file's largest value, as they do everywhere.
- **The colors' scale and the Threshold are not changed by the choice**: they use the file's largest value over all notes, so a strength keeps its color at every n. The alternative, scaling to the loudest chosen note, would brighten the picture when a loud note is left out.
- **The setting is chosen when frames are created**, like every other setting; changing it means submitting again.
- This feature is about which values a frame is drawn from. Audio playback, the note analysis, smoothing, the Resolution and the image types themselves, the frame player and the page layout (apart from adding one control and one summary line) are unchanged.
