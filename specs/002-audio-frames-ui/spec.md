# Feature Specification: Audio Upload and Frame Visualization UI

**Feature Branch**: `002-audio-frames-ui` (no git branch created; spec directory name only)

**Created**: 2026-10-04

**Status**: Draft

**Input**: User description: "create the UI for selecting an audio file and setting the window size, and visualizing the audio. When submitted, the file will be uploaded to the python server and put in a temporary directory. The application will create a certain number of images from the audio file, that can be made into an animation. So the UI should also have the frame rate. The python application should average the windows over that period, and create an image. For now the image can just be a grayscale rectangle with a square for each of the 88 notes, the brightness determined by the relative loudness at that frequency in that bin. Don't worry about normalizing volume right now, we're just trying to get the UI and workflow set up. The images will go into a different temporary directory."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Submit an audio file and see its frames (Priority: P1)

A user opens the application, picks a `.wav` file from their computer, sets the window size and the frame rate, and submits. The file is sent to the server and stored in a temporary location. The server analyzes it and produces one image per animation frame (grayscale originally; colored since feature 007). When it finishes, the user sees the first frame, along with how many frames were made and how long the audio is.

**Why this priority**: This is the whole workflow end to end: select, submit, analyze, produce images, display. Nothing else is useful until it works.

**Independent Test**: Submit a WAV file that plays one steady note, with a window size and frame rate. Check that the number of images matches the file's length times the frame rate, and that the displayed frame has one bright square and the rest dark.

**Acceptance Scenarios**:

1. **Given** the form is empty, **When** the user chooses a `.wav` file, enters a window size and a frame rate, and submits, **Then** the file is uploaded, the user sees a progress or busy indication, and on completion the first frame is displayed.
2. **Given** a completed submission, **When** the results appear, **Then** the user can see the frame count, the audio duration, and the window size and frame rate that were used.
3. **Given** a WAV file with one steady note, **When** a frame is displayed, **Then** the square for that note is clearly brighter than every other square.
4. **Given** a silent WAV file, **When** a frame is displayed, **Then** all 88 squares are black.
5. **Given** a user who has not yet chosen a file, **When** they try to submit, **Then** submission is prevented and the form says a file is needed.
6. **Given** the user submits a second file, **When** it completes, **Then** the results from the first file are replaced by the new ones.

---

### User Story 2 - Play the frames as an animation (Priority: P2)

After a submission completes, the user can play the frames in order at the frame rate they chose, pause, and drag a position control to any frame, so they see how the notes change over time as an animation.

**Why this priority**: Turning the frames into an animation is the purpose of choosing a frame rate. It needs the frames from Story 1.

**Independent Test**: Submit a file that changes note partway through. Play the animation and check that the bright square moves at the right moment, and that dragging to a frame shows that frame.

**Acceptance Scenarios**:

1. **Given** a completed submission, **When** the user presses play, **Then** frames advance in order at the chosen frame rate and stop on the last frame (or loop, if the user turns looping on).
2. **Given** playback is running, **When** the user presses pause, **Then** the current frame stays on screen.
3. **Given** a completed submission, **When** the user moves the position control, **Then** the matching frame is shown along with its time in the audio.
4. **Given** a file whose note changes at about 2 seconds, **When** the user views frames just before and after 2 seconds, **Then** the bright square differs between them.

---

### User Story 3 - Clear feedback when something is wrong (Priority: P3)

If the file or the settings can't be used, or the server fails, the user gets a plain message saying what is wrong and what to change, and can fix it and try again without reloading the page.

**Why this priority**: The core flow works without this, but real use quickly hits bad files and bad settings.

**Independent Test**: Submit a text file renamed to `.wav`, then a window size of 0, then a window size too large for the file's sample rate. Each shows a clear message, and a correct resubmission succeeds afterward.

**Acceptance Scenarios**:

1. **Given** a file that isn't a valid WAV, **When** it is submitted, **Then** the user sees a message that the file could not be read as WAV audio.
2. **Given** a window size or frame rate outside the allowed range, **When** the user edits the field, **Then** the form shows the allowed range and blocks submission until it is fixed.
3. **Given** settings the analysis rejects (for example a sample rate too low for the highest note), **When** submitted, **Then** the server's explanation is shown to the user.
4. **Given** a file larger than the allowed upload size, **When** submitted, **Then** the user sees a message with the size limit.
5. **Given** the server is unreachable or fails part way, **When** the user submits, **Then** the user sees a failure message and the form stays filled in for retry.

---

### Edge Cases

- **Window longer than one frame period**: At 30 frames per second a frame covers about 33 ms, which is shorter than even the smallest window, 4096 samples at 44.1 kHz (about 93 ms). Most frame periods then contain no window start (about two in three at a 4096 window, and more at larger windows). The frame uses the window that covers the start of its period, so every frame has data.
- **Very long audio or very high frame rate**: A request that would produce more frames than the allowed maximum is rejected before any work is done, with a message showing the count and the limit.
- **Audio length not a whole number of frame periods**: The last frame covers the remaining partial period. No audio is dropped.
- **Mono and stereo files**: Both are accepted. Files with more than two channels are rejected with a message.
- **Empty audio (no samples)**: The user sees a message that the file contains no audio, and no frames are made.
- **Loud and quiet files**: Brightness is scaled to the loudest value in that file, so a quiet file and a loud file both reach full white at their loudest moment. Because of this, brightness cannot be compared between different files. Proper volume normalization is deferred.
- **Two users or two submissions at once**: Each submission has its own files and images, so one cannot overwrite another's.
- **Leaving the page**: Reloading or closing the page loses the on-screen results, and the user can submit again. Temporary files are the server's to clean up and are not user-visible.
- **Unusual file names**: Names with spaces, other characters, or paths do not affect where the server stores the file.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The UI MUST let the user choose an audio file from their device, restricted to `.wav` files, and show the chosen file's name and size.
- **FR-002**: The UI MUST provide a window size dropdown offering only 4096, 8192, 16384 and 32768 samples (the powers of 2 from 4096 to 32768) with a default of 4096, and a frame rate input (frames per second) with a default of 30 that shows its allowed range. The server MUST reject any other window size.
- **FR-003**: The UI MUST block submission, with an explanatory message, when no file is chosen or either setting is invalid.
- **FR-004**: On submit, the system MUST upload the file to the server and store it in a temporary directory reserved for uploaded audio, in a location unique to that submission.
- **FR-005**: The server MUST read the sample rate from the WAV file itself and use it for the analysis. The user does not enter it.
- **FR-006**: The server MUST analyze the audio into 88 note values per window using the existing note analysis (feature 001) with the chosen window size.
- **FR-007**: The server MUST divide the audio into frame periods of length 1 ÷ frame rate seconds, starting at time 0. For each frame period it MUST average the 88-value results of all windows that start within the period. If no window starts within the period, it MUST use the window that covers the start of the period.
- **FR-008**: The server MUST produce one image per frame period, in time order (grayscale originally; colored since feature 007). The number of images is the audio duration times the frame rate, rounded up.
- **FR-009**: Each image MUST be a rectangle made of equally sized tiles, one per note, with no gaps or margins. *Superseded by feature 005:* the tiles are now 84 rectangles in a grid of 12 columns and 7 rows (21 × 24 pixels each, 252 × 168 overall, exactly 3:2). Tile (row *r*, column *c*) is note 12 × *r* + *c*, so each row is an octave and the tile below a note is the same note one octave higher. The lowest note is the top-left tile, and the four highest notes are not drawn. (Originally this was 88 squares in 11 columns and 8 rows.)
- **FR-010**: Each square's brightness MUST be based on its note value divided by the largest note value anywhere in the file, then brightened with the brightness-th root (`255 * (level / 255) ** (1 / brightness)` on the 0–255 scale) so quiet notes are visible. The brightness is a whole number from 2 to 100 chosen by the user (feature 004); the default, 2, is the square root. A value of 0 is black, and the loudest value in the file is white. No other volume normalization is applied. *Since feature 007* this brightness is the tile's HSV value: the tile is colored (saturation 50%, hue from related notes), its brightest color channel equals the gray level above, and the loudest tile's brightest channel is 255 (a pastel white), not pure gray white.
- **FR-011**: The server MUST save the images in a temporary directory that is separate from the uploaded-audio directory, in a location unique to that submission, named so their order is clear.
- **FR-012**: The server MUST report back the number of frames, the audio duration, the sample rate, and the window size and frame rate used, and MUST make each image retrievable by the UI.
- **FR-013**: The UI MUST show a busy or progress indication from submission until the results arrive, and MUST prevent a second submission while one is running.
- **FR-014**: The UI MUST display the frames: the first frame on completion, a frame position control covering all frames, the current frame's time in seconds, and play and pause controls.
- **FR-015**: Playback MUST advance at the chosen frame rate, and MUST stop on the last frame unless looping is turned on.
- **FR-016**: The system MUST reject the request, before doing the analysis, when the file is not a readable WAV, has more than two channels, has no audio, exceeds the maximum upload size, or would create more than the maximum number of frames. Each rejection MUST come back with a message saying what is wrong, and the UI MUST show it.
- **FR-017**: The system MUST show analysis errors (such as a sample rate too low for the window size) to the user, using the explanation from the analysis.
- **FR-018**: The uploaded file name MUST NOT control where files are stored on the server.
- **FR-019**: Submitting a new file MUST replace the displayed results, and MUST NOT change images from earlier submissions on the server that are still being used.
- **FR-020**: Given the same file and settings, the system MUST produce the same images every time.

### Key Entities

- **Submission (job)**: One upload plus its settings. It has an identifier, the original file name, window size, frame rate, sample rate (from the file), duration, frame count, and a status (running, done, failed with a message).
- **Uploaded Audio**: The user's `.wav` file as stored in the temporary upload directory for its submission.
- **Frame**: One animation step: its index, its start time, and 88 averaged note values.
- **Frame Image**: The picture for one frame (grayscale originally, colored since feature 007), stored in the temporary image directory for its submission.
- **Settings**: The window size and the frame rate chosen by the user.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can go from opening the application to seeing the first frame of their file in under 1 minute for a file of up to 5 minutes, excluding the time spent choosing the file.
- **SC-002**: For a 3-minute file at 30 frames per second and the default window size, all frames are ready in under 60 seconds on an ordinary laptop.
- **SC-003**: The number of images equals the audio duration in seconds times the frame rate, rounded up, for every tested combination of file length and frame rate.
- **SC-004**: For a test file playing one steady note, in at least 95% of frames the square for that note is the brightest square.
- **SC-005**: A silent file produces frames in which every square is black, and the loudest note in any file reaches full white in at least one frame.
- **SC-006**: Playback holds the chosen frame rate to within 10% over 30 seconds of playback on an ordinary laptop, up to 30 frames per second.
- **SC-007**: Every invalid input listed under User Story 3 gives a message that names the problem, with no crash and no blank screen, and a corrected resubmission works without a page reload.
- **SC-008**: Uploaded audio and generated images are never stored in the same directory, and two submissions never share files.

## Assumptions

- **Sample rate**: The user enters only the window size and frame rate. The sample rate comes from the WAV file header, so the sample-rate mismatch case from feature 001 does not arise here.
- **Defaults and ranges**: Window size is chosen from a dropdown of 4096, 8192, 16384 and 32768 and defaults to 4096 (changed from the original 256–32768 free entry at the user's request). Frame rate defaults to 30 and must be from 1 to 60. These can be adjusted later.
- **Limits**: The upload limit is 200 MB, because the sample WAV in the project is about 90 MB and the current 20 MB limit would reject normal songs. The frame limit is 30,000 frames per submission. Both are server settings.
- **Brightness scaling**: "Relative loudness" is read as each note's value relative to the loudest value in the whole file, on a linear scale, followed by a root boost that the user requested after seeing the images were too dark: first a fixed square root, now the brightness-th root with brightness 2 as the default (feature 004). One scale for the whole file keeps brightness comparable between frames in the animation. Other scales (logarithmic, per-frame, across files) are the volume normalization the user said to defer.
- **Image layout**: Replaced by feature 005. The original layout was an 11 by 8 grid of squares that was not aligned to octaves; it is now a 12 by 7 grid of 21 × 24 pixel tiles with one octave per row (see FR-009 and the feature 005 spec). The workflow is unchanged.
- **Image size**: Each tile is large enough to see clearly on screen, and the UI scales the image for display. Originally 20 by 20 pixel squares gave a 220 by 160 image; the images are now 252 × 168 pixels (feature 005).
- **Animation**: "Made into an animation" means the UI plays the frames in order. Producing a video or animated file for download is out of scope for this feature.
- **Temporary storage**: "Temporary directory" means locations under the server's temporary file area, with a separate one for uploaded audio and a separate one for images, and a unique subfolder for each submission. Automatic clean-up of old submissions is out of scope for now. The OS temporary-file clean-up applies.
- **Users and access**: This is a single-user local tool. There are no accounts, and no access controls on the images beyond hard-to-guess submission identifiers.
- **Workflow**: A submission is handled in one request or as one background job. The user waits for it to finish, and results are not kept across page reloads.
- **Dependencies**: This feature builds on the note analysis from feature 001 and on the existing backend and frontend projects.
