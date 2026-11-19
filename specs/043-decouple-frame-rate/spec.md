# Feature Specification: Decouple the frame rate from the frequency buffers

**Feature Branch**: `043-decouple-frame-rate` (no git branch created; spec directory name only)

**Created**: 2026-11-18

**Status**: Draft

**Input**: User description: "decouple the frame rate and the rate of the frequency buffers.  We should always calculate frequency buffers as close as possible to 60 ms using window spacing, this is faster than a 32nd note at 120bpm, a very short note.  If the user wants say 10 frames per second, we can use data smoothing on the frequency buffers before creating image type.  So we don't need the smoothing parameters anymore, they are baked into the frame rate, and we don't need to set the window spacing any more, that will be set ahead of time."

**How the user's words are read** (the terms used in the rest of this document):

- A **frequency buffer** is what the app has so far called an *analysis window*: one measurement of the strength of each of the 88 notes, taken from a short piece of the audio. The **window spacing** is how far apart in time two buffers start.
- The **buffer interval** is the time from the start of one buffer to the start of the next. This feature fixes it at **60 ms** (about 16.7 buffers every second): a 32nd note at 120 beats per minute lasts 62.5 ms, so a buffer every 60 ms never skips over even a very short note.
- **Data smoothing** at a low frame rate means **combining the buffers that fall in one frame's time span into that frame** (their average), so that nothing that was measured is thrown away. This is "baked into the frame rate": the frame rate alone decides how much is combined.
- The **smoothing parameters** are the two settings called *Smoothing* and *Smoothing window* (the Data smoothing group of the page), which let the user blend each frame with the frames before it. They are removed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The notes are measured at the same rate whatever the frame rate (Priority: P1)

The user makes pictures of a song at 10, 24 and 30 frames per second. Today the choice of frame rate also changes how often the notes are measured (the default window spacing follows it), so the same song gives different note data at different frame rates, and a low frame rate can miss short notes. After this feature the notes are **always measured on a fixed 60 ms interval**, and the frame rate only decides how many pictures are made from that data.

**Why this priority**: This is the heart of the request. Everything else (the simpler page, the smoothing) follows from it.

**Independent Test**: Make a picture set of one file at 10 frames per second and another at 30; the measurements of the notes behind them are the same (one every 60 ms), and a note that lasts only 60 ms shows up in both.

**Acceptance Scenarios**:

1. **Given** the same audio file and settings other than the frame rate, **When** the user makes pictures at 10, 20 and 30 frames per second, **Then** the buffers measured are identical for the three, one every 60 ms (to within one sample of audio).
2. **Given** a very short note (a 32nd note at 120 beats per minute, 62.5 ms), **When** the user makes pictures at 5 frames per second, **Then** the note is still measured in at least one buffer and so still contributes to a frame.
3. **Given** any file the app accepts, **When** its buffers are made, **Then** the time between the starts of two neighbouring buffers is 60 ms, whatever the sample rate of the file, to within one sample of audio.

---

### User Story 2 - A low frame rate averages the buffers instead of skipping them (Priority: P1)

The user asks for 10 frames per second. A frame then lasts 100 ms, which is more than one buffer interval. The picture of each frame is made from **all the buffers that start in its time span, averaged**, so that every buffer counts once and in only one frame, and a frame is never made from a single buffer chosen by chance.

**Why this priority**: Without it a low frame rate would throw away most of the measurements, and the smoothing the user used to set by hand would have no replacement.

**Independent Test**: At 10 frames per second the strength of a note in a frame equals the mean of its strength in the buffers that start inside that frame's 100 ms; at 30 frames per second (33 ms, fewer than one buffer per frame) no frame is empty or invented from nothing.

**Acceptance Scenarios**:

1. **Given** a frame rate of 10 frames per second, **When** the frames are made, **Then** each frame's note strengths are the average of the buffers that start in that frame's time span, and every buffer is used in exactly one frame.
2. **Given** a frame rate at which a frame's time span holds no buffer start (any rate above about 16.7 frames per second), **When** the frames are made, **Then** that frame uses the most recent buffer that started before it (a frame is never blank because no buffer started in it).
3. **Given** the same file, **When** the user makes pictures at a lower and a higher frame rate, **Then** the lower rate's pictures change more gently (more is averaged into each) and the higher rate's follow the buffers closely.

---

### User Story 3 - The page and the request lose the settings that are now decided for the user (Priority: P2)

The user opens the page. **Window spacing**, **Smoothing** and **Smoothing window** are no longer there: the page has no **Data smoothing** group, and the window spacing is no longer a field that follows the frame rate. The user asks only for the window size, the frame rate and the settings of the picture, and the app does the rest. The result list of a finished job no longer shows the smoothing, the smoothing window or the window spacing. The window size stays a setting.

**Why this priority**: It follows from the first two stories and is what the user sees, but the pictures are right even before the page is tidied.

**Independent Test**: Open the page: there are no fields called Window spacing, Smoothing or Smoothing window, and no group called Data smoothing. Make a picture set with a request that carries none of them: it is accepted and made.

**Acceptance Scenarios**:

1. **Given** the page is open, **When** the user looks at the settings of any image type, **Then** there is no Window spacing field and no Smoothing or Smoothing window setting, and the page still allows a job to be started with only the window size, the frame rate and the settings that remain.
2. **Given** a job made without the removed settings, **When** it finishes, **Then** its list of settings shows no smoothing, smoothing window or window spacing.
3. **Given** a request that still carries the removed settings, **When** it is received, **Then** they have no effect on the pictures (see Assumptions).
4. **Given** the user lowers the frame rate, **When** nothing else is changed, **Then** the page shows no sign that a spacing was recalculated and no warning that a spacing was raised to one sample.

---

### User Story 4 - Every picture type works with the fixed buffers (Priority: P2)

Every image type (Contour, Decay, Decay Exp, Polar Chords, Energy graphs, Chromatic Decay, Rhythm Circles, Chromatic Wireframe, Polychord) is made as before, from frames averaged from buffers every 60 ms. The types that draw one picture for each frame and then fade or move things from frame to frame (the decay types, the rotating figures, the rings that follow the beat and the tempo) keep their own settings and behaviour in time: they depend on the **frame rate** and the **time**, and not on the buffer interval.

**Why this priority**: The change must not leave an image type broken, but the type-specific looks are unchanged.

**Independent Test**: Make one picture set of each type before and after the change at a frame rate of about 16 frames per second, and see that the pictures are made without error and that the things measured from the whole file (the beat, the tempo, the energy graphs) still line up with the music.

**Acceptance Scenarios**:

1. **Given** each image type in turn, **When** a job is made at 10, 16 and 30 frames per second, **Then** every type makes its pictures with no error and the number of pictures is the duration times the frame rate, rounded up, as before.
2. **Given** a type that measures something over the whole file (the beat of the local peaks, the tempo, the loudness of Energy graphs), **When** the frame rate is changed, **Then** what is measured is the same and is only read at the middle of each frame, as before.

---

### Edge Cases

- **A file shorter than one buffer interval** (under 60 ms of audio): still one buffer and one frame, as today for a short file.
- **A frame rate above the buffer rate** (the page allows up to 60 frames per second, the buffers come about 16.7 times a second): several frames in a row come from the same buffer, so the pictures of the types that draw only from the note values hold still for those frames (see Assumptions).
- **The window size is longer than the buffer interval** (the largest sizes are longer than 60 ms): the buffers then overlap, as they do today with a small spacing. This is allowed and is not an error.
- **The window size is shorter than the buffer interval**: there are gaps in the audio between buffers; this is allowed.
- **Sample rates of any value the app accepts** (the buffer interval is 60 ms of time, not a fixed number of samples): a 60 ms interval is never less than one sample.
- **A very long file**: the limit on the number of buffers still protects the app; since the buffers are now fixed at 60 ms, the message tells the user to use a shorter file (it can no longer suggest a larger window spacing). The limit on the number of frames and its message are unchanged.
- **A job request from an older page or script that still sends Smoothing, Smoothing window or Window spacing**: it is not refused for that reason (see Assumptions).
- **The note noise floor** (feature 033), which makes notes more than 60 dB below the loudest note 0, is applied to the buffers as before.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST measure the strength of the notes (the frequency buffers) at a fixed interval of **60 ms** between the starts of neighbouring buffers, for every job, whatever the frame rate and the sample rate of the file; the interval MUST be as close to 60 ms as the audio's samples allow (within one sample).
- **FR-002**: The buffer interval MUST NOT depend on the frame rate, and changing only the frame rate MUST NOT change any buffer.
- **FR-003**: The user MUST NOT be asked for, and MUST NOT be able to set, the window spacing.
- **FR-004**: When a frame's time span is longer than the buffer interval, the frame's note strengths MUST be the average of all the buffers that start inside its time span, and every buffer MUST be counted in exactly one frame.
- **FR-005**: When a frame's time span holds no buffer start, the frame MUST use the most recent buffer that started before it (the first buffer if none did), so that no frame is blank for want of a buffer.
- **FR-006**: The two smoothing settings (**Smoothing** and **Smoothing window**) MUST be removed: they MUST NOT appear on the page, in the request, in the description of a finished job, or in the settings a picture type is given; the **Data smoothing** group MUST no longer be shown for any image type.
- **FR-007**: The averaging of FR-004 MUST be the only smoothing of the note data between the buffers and the pictures; the frames MUST NOT be blended with earlier frames.
- **FR-008**: The number of frames MUST still be the duration times the frame rate, rounded up, and the frame rate MUST keep its range, its default and its validation (Assumptions says which).
- **FR-009**: Every image type MUST still be made without error, with its own settings unchanged, from frames made as in FR-004 and FR-005. What the types measure over the whole file (the beat, the tempo, the energy) and the things that depend on time (decay rates, rotation per second, the rings) MUST keep following the frame rate and the time, not the buffer interval.
- **FR-010**: The page's note on the analysis of a job (the sentence and the warning about a spacing raised to one sample, the spacing field's hint of milliseconds) MUST be removed together with the window spacing; the window size MUST stay a setting.
- **FR-011**: The check that a job does not make too many buffers MUST stay, and its message MUST no longer tell the user to use a larger window spacing.
- **FR-012**: A request that still carries the removed settings MUST NOT be refused because of them and MUST NOT be affected by them.
- **FR-013**: The documentation of the app (the order of operations of the modules, the array documentation, the image-type overview and the help texts of the page, as the project constitution requires) MUST describe the fixed buffer interval and the averaging, and MUST NOT describe the removed settings.

### Key Entities *(include if feature involves data)*

- **Frequency buffer**: the strength of each of the 88 notes at one moment of the file. One every 60 ms, whatever the frame rate. Previously called an analysis window.
- **Frame**: one picture's worth of time, 1 / frame rate seconds. Its note strengths are the average of the buffers that start in it, or the latest earlier buffer if none does.
- **Buffer interval**: the fixed 60 ms between the starts of two buffers. No longer a setting.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For any file, the buffers measured are the same at every frame rate the page allows (1 to 60): changing the frame rate alone changes none of them.
- **SC-002**: The time between the starts of any two neighbouring buffers is 60 ms to within one sample of the audio, for every sample rate the app accepts.
- **SC-003**: A note that lasts 62.5 ms (a 32nd note at 120 beats per minute) appears in the note data at every frame rate from 1 to 60 frames per second.
- **SC-004**: At a frame rate whose frame is longer than 60 ms, every buffer contributes to exactly one frame, and a frame's note strengths equal the mean of the buffers it owns.
- **SC-005**: A job at any frame rate from 1 to 60 is made with the page's remaining settings alone: the page has no Window spacing, Smoothing or Smoothing window field, and a request without them is accepted.
- **SC-006**: All nine image types make their pictures, at 10, 16 and 30 frames per second, with the same number of pictures as before the change.
- **SC-007**: The documentation and the help texts mention none of the removed settings, and the parts that describe the pipeline state the fixed 60 ms buffer interval.

## Assumptions

- **The frame rate keeps its range of 1 to 60 and its default of 30.** The user did not ask to change it. Above about 16.7 frames per second there are fewer buffers than frames, so neighbouring frames repeat the latest buffer (FR-005; this is the behaviour a frame with no buffer start already has today). The types that move things from frame to frame (decay, rotation, rings) still look smooth at those rates; the types that only draw the note values hold still between buffers. If the user prefers, the range could instead be capped at the buffer rate; that is a separate decision.
- **"As close as possible to 60 ms"** is read as: the interval in samples is the 60 ms of time at the file's sample rate, taken exactly where the audio allows it. It is not a window-size multiple chosen by the user.
- **The window size stays a user setting.** The user only asked about the spacing and the smoothing. A window size longer than 60 ms gives overlapping buffers, which is allowed.
- **The removed smoothing was a blend of each frame with the frames before it** (a weighted running average). Its default was 0 (off), so a job made with the defaults looks the same as before except for the changes from the fixed interval. Anyone who used it to make notes fade out more slowly gets that from the per-type decay settings instead.
- **The old settings are ignored, not refused, if a request still sends them**, so that an older page or script keeps working. The extra values are not stored in the result.
- **The limit on the number of buffers stays**, as a protection against very long files; at 60 ms it is reached only by files of about an hour or more.
- **Measurements made from the raw audio** (the local peaks that give the beat, the tempo and the rhythm rings) are not made from the buffers and are unchanged.
- **The pictures of a file made before this change are not regenerated**; this applies to new jobs only.
