# Feature Specification: Energy Saturation

**Feature Branch**: `009-energy-saturation` (no git branch created; spec directory name only)

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "create another measure.  The measure will on overall energy, not just tonal energy.  We define an internal window of 32 samples at 44.1 KHz.  Lower sampling rates use a proportionally smaller value.   We define energy as the average std deviation between the left and right channel for that interval.   Use the energy  to determine the saturation at that interval.  The saturation can be set from this, with the highest value being 100% saturation.  Like with brightness, energy can also be normalized by using an nth root between 1 and 8."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Colors get richer when the music is energetic (Priority: P1)

A user looks at the frames and sees how *intense* the sound is, not only which notes are present. Brightness and hue still come from the notes, as today. The **saturation** of the colors, how vivid versus how washed out they are, now comes from the **overall energy** of the audio in that frame. Energy counts everything in the signal: noise, drums and other sound that has no clear note, as well as tones. A loud, busy passage gives vivid, fully colored tiles. A quiet passage gives pale, whitish tiles. The loudest frame in the file is at 100% saturation, and every other frame is a fraction of that.

**How energy is measured.** The audio is looked at in very short *internal windows* of 32 samples at 44.1 kHz. For a file at a lower or higher sample rate the window is proportionally shorter or longer (22,050 Hz uses 16 samples, 48,000 Hz uses 35), so a window always covers about the same slice of time (about 0.73 ms). In each internal window the *spread* of the signal (its standard deviation) is found for the left channel and for the right channel and the two are averaged. The energy of a frame is the average of that value over the internal windows in the frame's own time period. Silence and a steady constant level have no spread and so no energy.

**Why this priority**: This is the whole feature: a second measure of the sound, shown through color saturation, that is independent of the note analysis.

**Independent Test**: Make a file in which one stretch is loud noise and another is a quarter as loud, with a quiet gap between. With the default settings, the frame in the loud stretch has saturation 100% (a fully saturated color), the frame in the quarter-loud stretch has saturation 25%, and the frame in the gap has saturation 0% (a gray or white tile).

**Acceptance Scenarios**:

1. **Given** a frame whose internal windows each hold alternating samples of +0.5 and −0.5 in both channels, **When** its energy is measured, **Then** the energy is 0.5 (each channel has a spread of 0.5, and the average of the two is 0.5).
2. **Given** a frame in which the left channel alternates between +0.5 and −0.5 and the right channel is silent, **When** its energy is measured, **Then** the energy is 0.25 (the left spread of 0.5 averaged with the right spread of 0).
3. **Given** a frame whose samples are all the same constant value in both channels, **When** its energy is measured, **Then** the energy is 0 (a steady level has no spread, however large the level).
4. **Given** a mono file (the same signal in both channels), **When** energy is measured, **Then** it is the spread of that single signal, so mono files work in the same way as stereo ones.
5. **Given** several frames with different energies and the energy root at its default (1), **When** the frames are drawn, **Then** each frame's saturation is its energy divided by the largest energy of any frame in the file: the frame with the largest energy has saturation 100% and a frame with half of it has 50%.
6. **Given** every frame's tiles, **When** a frame is drawn, **Then** all 84 tiles of that frame share that frame's saturation, while each tile keeps its own brightness (value) and its own hue.
7. **Given** a tile with saturation 100%, **When** it is drawn, **Then** its darkest color channel is 0. **Given** a tile with saturation 0%, **When** it is drawn, **Then** all three channels are equal (a gray or white tile).
8. **Given** a silent file (every frame has energy 0), **When** frames are drawn, **Then** every pixel is black and nothing fails (there is no loudest frame to divide by, so saturation is 0).
9. **Given** a smoothing value above 0, **When** frames are drawn, **Then** the saturation is smoothed over the frames with the same running average as the hue and the note values, so that it does not flicker from frame to frame. With smoothing 0 the saturation of each frame is exactly the value above.
10. **Given** the same file, **When** it is drawn twice, **Then** the two sets of frames are identical.

---

### User Story 2 - Choose how energy is normalized with a root from 1 to 8 (Priority: P2)

Like the brightness setting, the user can lift quiet passages by taking a root. A new **Energy** setting is a whole number from **1 to 8**. The saturation of a frame is its energy as a fraction of the loudest frame's energy, raised to the power 1 divided by that number. The default is 1, which leaves the fraction as it is (a straight proportion). Higher numbers make quieter frames more colorful. The loudest frame is always 100% and a silent frame is always 0%, whatever the setting. The setting is in the settings column of the page with the others and, like them, has an info button with a short explanation.

For a frame with a quarter of the loudest energy, the saturation is 25% with root 1, 50% with root 2, about 63% with root 3 and about 84% with root 8.

**Why this priority**: The measure and its mapping (Story 1) work with the default, but quiet recordings and busy ones need different amounts of lift to look right, as with brightness.

**Independent Test**: Create frames from the same file with the Energy setting at 1, 2 and 8. A frame whose energy is a quarter of the loudest has saturation 25%, 50% and about 84% respectively, and the loudest frame is at 100% every time.

**Acceptance Scenarios**:

1. **Given** the Energy setting is not changed, **When** frames are created, **Then** the root is 1 and saturation is the straight proportion of the loudest frame.
2. **Given** a frame with a quarter of the loudest energy, **When** the root is 2, 3 and 8, **Then** its saturation is 50%, about 63% (0.25^(1/3) = 0.630) and about 84% (0.25^(1/8) = 0.841).
3. **Given** any root from 1 to 8, **When** frames are drawn, **Then** the loudest frame is at 100% saturation, a frame with no energy is at 0%, and a higher root is never less saturated than a lower one for the same frame.
4. **Given** a value that is not a whole number from 1 to 8 (empty, 0, 9, 2.5, text), **When** the user enters it, **Then** the page shows an error under the field, "Create frames" is unavailable, and nothing is sent; a request that bypasses the page with such a value is refused with a clear message.
5. **Given** frames have been created, **When** the result is shown, **Then** the result summary includes the Energy value that was used.
6. **Given** the Energy setting, **When** the user activates its info button, **Then** a popover explains what it does and the range (a whole number from 1 to 8), in the same way as the other settings.
7. **Given** a job is running, **When** the user looks at the Energy field, **Then** it is disabled like the other settings.

---

### User Story 3 - The measure behaves the same at any sample rate or channel layout (Priority: P3)

The internal window follows the file's sample rate, so the same sound gives about the same energy whether it was recorded at 44.1 kHz, 48 kHz or a lower rate, and the saturation of a frame does not depend on the file's bit depth. Mono and stereo files are both accepted. Very short frames, a frame at the end of a file that is shorter than the others, and the lowest sample rates the page already accepts all give sensible values without errors.

**Why this priority**: These are the conditions under which a fixed number of samples would give inconsistent results. They are secondary to the main behavior, but the measure should not depend on them.

**Independent Test**: Make the same noise at 44.1 kHz and at 22.05 kHz and compare the saturation of the frames: it is the same to within a small tolerance. Make a file whose last frame is only a few samples long and confirm frames are created without an error.

**Acceptance Scenarios**:

1. **Given** a file at 44.1 kHz, **When** the internal window is chosen, **Then** it is 32 samples. At 22,050 Hz it is 16 samples, at 11,025 Hz it is 8, and at 48,000 Hz it is 35 (32 × 48,000 / 44,100 = 34.8, rounded to the nearest whole sample).
2. **Given** the same sound sampled at two different rates, **When** frames are drawn, **Then** the saturation of matching frames agrees to within 5 percentage points.
3. **Given** the same audio stored as 8-bit, 16-bit, 24-bit or floating-point samples, **When** frames are drawn, **Then** the saturation of each frame is the same to within rounding, because energy is measured on a common scale and then taken as a fraction of the loudest frame.
4. **Given** a frame period that holds more than one internal window, **When** its energy is measured, **Then** the internal windows are laid end to end from the frame's first sample, a shorter leftover at the end of the period is ignored, and the energy is the average of the full windows.
5. **Given** a final frame that holds fewer samples than one internal window (or a frame period that is shorter than one window), **When** its energy is measured, **Then** the samples it does have are measured as one window, and a frame with only one sample has energy 0. No error occurs.

---

### Edge Cases

- A single very loud sound (a click or a clipped peak) sets the loudest energy, so the rest of the file is pale. This is the same behavior as the gray levels, which are also scaled against the loudest value. The Energy root lifts the quiet frames in that case.
- A file with a constant level or a DC offset has no energy and is pale or gray, even if a note is detected.
- A file whose channels are identical (mono, or stereo with the same signal in both) is measured like any other.
- A file with only one loud channel: the quiet channel adds nothing, so its energy is half that of the same signal in both channels.
- Frames shorter than the internal window (high frame rates on low-rate files) and the shorter final frame are covered above.
- The loudest frame's energy is 0 (silent file): saturation is 0 for every frame and every pixel is black.
- Smoothing near 0.8 spreads a loud frame's saturation into the frames after it, as it does for hue.
- Results from before this feature (frames already created) are not changed. Only new submissions use the energy.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST measure an **energy** for every frame of a file from the audio samples in that frame's own time period, independent of the note analysis and the window size and spacing settings.
- **FR-002**: Energy MUST be measured in internal windows of 32 samples at a sample rate of 44.1 kHz, scaled in proportion to the file's sample rate and rounded to the nearest whole number of samples (16 at 22,050 Hz, 8 at 11,025 Hz, 35 at 48,000 Hz).
- **FR-003**: For each internal window, the system MUST find the standard deviation of the samples of the left channel and of the right channel and take the average of the two. A mono file MUST be treated as having the same signal in both channels.
- **FR-004**: A frame's energy MUST be the average of that value over the full internal windows laid end to end from the frame's first sample. A shorter leftover at the end of the frame's period MUST be ignored, unless the frame holds no full window, in which case the samples it has MUST be measured as one window (and a frame with a single sample has energy 0).
- **FR-005**: Energy MUST be measured on a scale that does not depend on the sample format of the file (the same audio at a different bit depth gives the same saturation).
- **FR-006**: The saturation of every tile in a frame MUST be that frame's energy divided by the largest energy of any frame in the file, raised to the power 1 divided by the Energy root. The loudest frame MUST have saturation 100% and a frame with no energy MUST have saturation 0%. This MUST replace the fixed 50% saturation used until now.
- **FR-007**: If no frame has any energy, every frame MUST have saturation 0 and every pixel MUST be black, without error.
- **FR-008**: Each tile MUST keep its own brightness (value) and hue as they are computed today; only the saturation changes. A tile with value 0 MUST remain black.
- **FR-009**: When smoothing is above 0, the saturation of the frames MUST be smoothed over the frames with the same running average and the same smoothing value that is applied to the hue, so that with smoothing 0 the saturation is exactly as defined in FR-006.
- **FR-010**: Users MUST be able to set an **Energy** value, a whole number from **1 to 8**, with a default of 1, in the settings of the page. It MUST be disabled while a job is running and have an info button with a short explanation, like the other settings.
- **FR-011**: The page MUST refuse a value that is not a whole number from 1 to 8 with a message under the field and MUST not send the job. The server MUST refuse such a value, or an empty value that was sent, with a clear message, and MUST use the default when the setting is not sent at all.
- **FR-012**: The result summary MUST show the Energy value that was used, and the server's response to a job MUST include it.
- **FR-013**: The same file and settings MUST always give identical frames.
- **FR-014**: Nothing else about the frames MUST change: the layout, size, frame count and timing, the note analysis, the brightness (value) of every tile, its hue and the way the other settings work, and the images' format. The documentation's description of the image MUST be updated to say that saturation now follows the energy.

### Key Entities *(include if feature involves data)*

- **Internal window**: A very short stretch of audio, 32 samples at 44.1 kHz (proportionally more or fewer at other rates), in which the spread of each channel is measured.
- **Energy**: One number per frame: the average, over the frame's internal windows, of the average of the left and right channels' standard deviations. It is a measure of overall signal intensity, not of pitch.
- **Energy root**: The whole number from 1 to 8 chosen by the user; the saturation is the frame's relative energy raised to 1 divided by this number.
- **Saturation**: One value per frame from 0% to 100%, shared by all tiles of the frame, derived from the energy.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a test file with a loud stretch, a stretch a quarter as loud and a silent gap, the three frames have saturation 100%, 25% and 0% with the default setting, and 100%, 50% and 0% with the Energy setting at 2.
- **SC-002**: In every file, the loudest frame is at exactly 100% saturation (and a silent file is entirely black), for every Energy value from 1 to 8.
- **SC-003**: The same sound at 44.1 kHz and at 22.05 kHz gives saturation within 5 percentage points for matching frames.
- **SC-004**: Changing only the Energy setting changes no tile's brightness or hue (measured as the brightest channel and the hue of each tile), only its saturation.
- **SC-005**: Hand-computed energies for the three small examples in Story 1 (0.5, 0.25 and 0) match the system's to within 0.001.
- **SC-006**: 100% of invalid Energy values (0, 9, 2.5, empty, text) are refused before a job is created, with a message that states the allowed range.
- **SC-007**: Creating the same frames takes no more than 25% longer than before this feature.
- **SC-008**: A user can find and read the explanation of the Energy setting from its info button, and change the setting, without leaving the settings column.

## Assumptions

- **Reading of "average std deviation between the left and right channel"**: the standard deviation is found for each channel separately over the internal window (the spread of that channel's own samples), and the left and right values are averaged. This is read as "overall energy" because it is loudness-like: it ignores a constant level and works on mono files. The other possible reading, the difference between the channels at each instant, would give zero for every mono file, so it is not used. The worked examples in the spec allow any mismatch to be spotted.
- **Which "interval" a frame uses**: the energy of a frame is measured over the frame's own time period (the same period that its note values are averaged over), not over the analysis window. This makes the measure independent of the window size and spacing settings.
- **Standard deviation** is the population standard deviation of the samples in the window (divide by the window length, not the length minus one). Samples are converted to a common scale of about −1 to 1 first, so file bit depth does not matter.
- **Rounding of the internal window**: the number of samples is 32 × (sample rate / 44,100) rounded to the nearest whole number, applied to higher rates too, not only lower ones. Sample rates the page already accepts all give a window of at least 2 samples.
- **Frame boundaries** fall on the nearest whole sample to the frame's exact start (frame number divided by the frame rate, times the sample rate), the same convention the windows use.
- **The Energy root is a whole number**, as brightness is, with a default of 1 (straight proportion). The default is 1 rather than 2 because the request describes the root as an optional extra ("can also be normalized"). The setting's label on the page is "Energy".
- **Saturation is shared by all tiles of a frame**, since energy is a measure of the whole sound and not of a note. Hue and brightness remain per tile.
- **Smoothing** applies to the saturation in the same way as to the hue, since both are per-frame color values; the request does not say, and a flickering saturation would undo the smoothing the user chose.
- **Fixed 50% saturation is replaced**, so existing images look different after this feature: tiles are fully saturated in the loudest frames and paler elsewhere. Worked colors in earlier feature specs that assume 50% saturation no longer hold.
- **The API** gets one new optional form field for the Energy value, treated like the brightness field, and the response includes it; the page, the frame image format and size and everything else about the API stay as they are.
- This feature is about the image color only. Audio playback, analysis of notes, and the page layout (apart from adding one field and one summary item) are unchanged.
