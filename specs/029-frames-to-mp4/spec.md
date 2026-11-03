# Feature Specification: Frames to MP4

**Feature Branch**: `029-frames-to-mp4` (no git branch created; spec directory name only)

**Created**: 2026-11-02

**Status**: Draft

**Input**: User description: "when an image type has been rendered, there should be an option to convert it into an mp4 from the images.  Use ffmpeg and put the output file in a directory in backend/output.   Don't put the audio in the video, just the silent video."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Turn the rendered pictures into a silent video (Priority: P1)

After the user has uploaded a file and the pictures (frames) of any image type have been made and can be played on the page, a **Create video** option appears beside them. Choosing it joins the frames of that render, in order, into a single **MP4 video** at the same frame rate the frames were made with, so the video lasts as long as the music did. The video has **no audio track**: it is the pictures only. The finished file is saved in a **new directory under `backend/output`** (one directory for this render, so videos from different renders never overwrite each other), and the page tells the user it is done and where the file was saved.

**Why this priority**: This is the whole request. The pictures can only be watched on the page today; the user wants a video file they can keep and use elsewhere (for example to combine with the music in a video editor).

**Independent Test**: Render any image type from a short audio file, choose **Create video**, then open the file the page reports in `backend/output`: it plays, shows the same pictures in the same order as the page's player, lasts as long as the frames at the render's frame rate (frame count ÷ frame rate), and has no audio stream.

**Acceptance Scenarios**:

1. **Given** a finished render of any of the image types, **When** the user chooses **Create video**, **Then** an MP4 file is created in a directory under `backend/output` and the page shows that it is done and where the file is.
2. **Given** the video was created, **When** it is opened, **Then** its pictures are the render's frames in order, its frame rate is the render's frame rate, and its duration is the frame count divided by the frame rate (within one frame).
3. **Given** the video was created, **When** its streams are inspected, **Then** it has one video stream and **no audio stream**.
4. **Given** the uploaded audio file, **When** the video is created, **Then** none of the audio is used or copied into the video.
5. **Given** frames of any image type (Tiles, Blended tiles, Contour, Circles, Concentric circles, Decay circles, and the others), **When** the video is created, **Then** it works the same way for each.
6. **Given** no render has been made yet, **When** the page is shown, **Then** there is nothing to convert and the **Create video** option is not offered (or is disabled).

---

### User Story 2 - Clear progress and clear failures (Priority: P2)

Making a long video can take a while, so while it is being made the page shows that it is **working** and the option cannot be pressed a second time for the same render. If the video cannot be made (for example the video tool is not installed on the machine, the frames are no longer there, or the disk is full), the page shows a **plain message saying what went wrong**, and no half-written or empty video file is left in `backend/output`. The user can try again.

**Why this priority**: The video itself is Story 1; this makes the option trustworthy but is not needed for the first working version.

**Independent Test**: Choose **Create video** on a long render and see the working state and then the finished state. Then make the video tool unavailable and choose it again: a clear error shows and `backend/output` holds no partial file for that attempt.

**Acceptance Scenarios**:

1. **Given** the video is being made, **When** the page is looked at, **Then** it shows that work is in progress and does not allow a second request for the same render at the same time.
2. **Given** the video tool is not available on the machine, **When** the user chooses **Create video**, **Then** the page shows a message that says so, and nothing is written to `backend/output`.
3. **Given** the frames of the render have been cleaned up and no longer exist, **When** the user chooses **Create video**, **Then** the page shows a message that the render is no longer available and asks the user to render again.
4. **Given** making the video fails part way, **When** the failure is reported, **Then** no incomplete file is left behind.

---

### User Story 3 - Find and reuse the video (Priority: P3)

The user can **download or open the video from the page** as well as find it on disk. Choosing **Create video** again for the same render replaces that render's video rather than adding another copy, so `backend/output` does not fill up with duplicates.

**Why this priority**: A convenience on top of the saved file.

**Independent Test**: Create the video, use the link on the page to get the file, create it again, and check that the render's directory still holds one video.

**Acceptance Scenarios**:

1. **Given** the video was created, **When** the user uses the link on the page, **Then** the same MP4 file can be played or saved.
2. **Given** the video for a render already exists, **When** the user creates it again, **Then** the render's directory holds one video and it is the newest.

---

### Edge Cases

- A render of a single frame: a valid, very short video is made (or a clear message is shown if a one-frame video cannot be made).
- A very large render (up to the maximum number of frames the app allows): the video is still made; the page stays responsive while it works.
- Pictures with an odd width or height (some image types and resolutions may produce them): the video is still made and plays in common players.
- The frame rate is not a whole number (for example 24.5): the video's frame rate matches it, so the length of the video still matches the music.
- The user starts another render while a video is being made from the earlier one: the earlier video is still made from the earlier frames, or the user is told that the render changed; frames of different renders are never mixed in one video.
- `backend/output` does not exist yet: it is created when the first video is made.
- The frames are removed by the app's cleanup after the video was made: the video file in `backend/output` stays.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: After a render has been made, the page MUST offer a **Create video** option for that render, for every image type.
- **FR-002**: Choosing it MUST join all frames of that render, in order, into one MP4 video using ffmpeg.
- **FR-003**: The video's frame rate MUST equal the frame rate the frames were made with, so that its duration equals frame count ÷ frame rate (within one frame).
- **FR-004**: The video MUST contain no audio stream; the uploaded audio MUST NOT be used.
- **FR-005**: The video MUST be saved in a directory under `backend/output`, one directory per render, created when needed.
- **FR-006**: Videos of different renders MUST NOT overwrite each other; creating the video again for the same render MUST replace that render's video.
- **FR-007**: The page MUST show when the video is being made, and MUST NOT allow a second simultaneous request for the same render.
- **FR-008**: When the video is done, the page MUST tell the user it is done and where the file was saved, and MUST give a way to open or download it.
- **FR-009**: If the video cannot be made, the page MUST show a plain message saying why (ffmpeg missing, frames gone, or another failure) and no incomplete file MUST be left in `backend/output`.
- **FR-010**: The video MUST play in common players (it uses a widely supported video encoding and handles pictures of any size).
- **FR-011**: Making a video MUST NOT change the frames, the render's settings, or any other feature's output.
- **FR-012**: Files in `backend/output` MUST NOT be added to version control.

### Key Entities

- **Render**: a finished set of numbered frame pictures made from one uploaded file with one set of settings; it has an image type, a frame count and a frame rate.
- **Video**: the silent MP4 made from one render's frames; it belongs to exactly one render and lives in that render's directory under `backend/output`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every image type, a user can go from a finished render to a playable video file in one action (one click on **Create video**).
- **SC-002**: In 100% of videos made, the duration equals the render's frame count ÷ frame rate within one frame, and the frame order matches the page's player.
- **SC-003**: In 100% of videos made, no audio stream is present.
- **SC-004**: A render of 1,000 frames is turned into a video in under 60 seconds on an ordinary computer.
- **SC-005**: When the video cannot be made, 100% of attempts show a message that names the cause, and none leaves a partial file in `backend/output`.
- **SC-006**: Making a video twice for one render leaves exactly one video for that render.

## Assumptions

- ffmpeg is installed on the machine that runs the backend and can be found by the app (it is at `C:\ffmpeg\bin` on the user's machine); installing it is the user's job, and its absence is reported as in Story 2.
- The video is made from the render's frames as they are on disk; "rendered" means the frames exist and play on the page, so no new rendering is done.
- The video is made on request only, never automatically after a render, and only one video per render is kept.
- The video uses the frames' own size (rounded to an even size if the encoder needs it) and a common, widely playable video encoding; the user has no settings for quality or size in this version.
- `backend/output` is created next to the existing `backend/uploads`, with each render's directory named after the render (its job identifier), and is excluded from version control.
- Adding the music to the video, choosing a different frame rate, and deleting old videos are out of scope; the user can combine the silent video with the audio in their own tools.
- The app is a single-user local tool, so no sign-in or access control is added for the video.
