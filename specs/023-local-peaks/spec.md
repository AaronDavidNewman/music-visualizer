# Feature Specification: Local Peaks

**Feature Branch**: `023-local-peaks` (no git branch created; spec directory name only)

**Created**: 2026-10-27

**Status**: Clarified

**Input**: User description: "create a new measurement called local_peaks.  It will measure a periodic local maximum in the overall energy (not just the harmonic energy).  We will use scipy.signal.find_peaks to determine this.   There are 2 windows to consider: the impulse window (32 samples) and the peaks window (4096 impulse samples, but it can vary and exact size isn't important).  Get the impulse energy by averaging the left and right std_dev for 32-sample windows from the input.  Keep a running buffer of impulse samples in the peaks window.   find_peaks will be called over peaks window.  To get the parameters for find_peaks, there are 2 user-modifiable parameters: min_distance and prominence.  min_distance is a time and defaults to 100ms.  You will convert min_distance for the number of impulse samples, since distance is a number of samples.  It can be increased to 2000ms.  prominence is a percentage and defaults to 50.  The prominence for the find_peaks call is calculated by getting the max energy from the peaks window and multiplying it by the prominence percentage.  find_peaks will return a set of indices, these indices indicate the local maximum.  For each maximum, record 3 things: the sample where the maximum occurs, the min and max energy at that sample, and the rate in peaks-per-minute.  The application should be able to ask for the interpolated energy at any point in the file.  The energy and rate can be used as an extra dimension in music visualizations."

## Clarifications

### Session 2026-10-27

- Q: What is interpolated, and what happens before the first and after the last peak? -> A: The **energy** is a straight line between the energy of the **previous** peak and that of the **next** peak; **before the first peak it is 0**, and **after the last peak it is the last peak's energy** (there is nothing to interpolate with). The **rate** is not interpolated: it is always the rate recorded at the **previous** peak, and **before the first peak it is a default of 1 per second** (60 peaks per minute).
- Q: What are "the min and max energy at that sample"? -> A: The **minimum and maximum impulse energy within the current peaks window** (the window in which the peak is found); they need not equal the window's trough. The impulse energy stays as first described: the **standard deviation of each channel** over the 32 samples is worked out separately and the **two are averaged** (an earlier reading, averaging the channels sample by sample before the standard deviation, was corrected by the user).
- Q: How far does the feature reach? -> A: **The measurement only.** How it is used (the job request, the response, the settings page, the pictures) will be defined later.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find the beats of a piece: where its energy peaks, and how often (Priority: P1)

The application already measures **which notes** are sounding (the note analysis, which looks at the harmonic content of the music). The user wants a second, different measurement, **local_peaks**, that follows the **overall loudness** of the music (all of its energy, not only the energy of the notes) and finds the **periodic local maxima** in it: the beats, hits and pulses that come round again and again. For every peak it records **where** in the file it is, **how strong** it is and **how fast** the peaks are coming (in peaks per minute), so that the pulse of the music can be used like an extra dimension next to the notes.

The measurement is made in two steps, with two windows:

1. **The impulse energy.** The audio is cut into very short **impulse windows of 32 samples**. For each one the spread of the sound is worked out separately for the **left** and the **right** channel (the standard deviation of its 32 samples), and the two are **averaged**: that is the energy of that impulse. A file therefore becomes a long list of impulse energies, one for every 32 samples (about 0.7 ms at CD quality).
2. **The peaks window.** A running **buffer** keeps the most recent impulse energies, **4096 of them** at a time (about 3 seconds of music; the exact size is not important and may change). Over the whole buffer the maxima of the energy are found with `scipy.signal.find_peaks`. A peak counts only if it is **far enough** from the previous peak (the **minimum distance**, a time) and **stands out enough** from its surroundings (the **prominence**, a percentage of the loudest impulse energy in the window).

For every peak that is found, these are recorded: **the sample of the file where the maximum is**, **its energy** together with the **minimum and maximum energy of the peaks window** it was found in, and **the rate in peaks per minute** at that point.

**Why this priority**: This is the whole measurement. Everything else (asking for the energy at any point, the settings, showing it) builds on a correct list of peaks.

**Independent Test**: Make a file of a quiet noise with one loud click every half second for 30 seconds. Run the measurement: it reports a peak at each click (about 60), each within one impulse window of the true click, none twice, and a rate of about 120 peaks per minute at every peak after the first.

**Acceptance Scenarios**:

1. **Given** a stereo file, **When** the impulse energy is worked out, **Then** it is the average of the standard deviation of the left channel and that of the right channel over every consecutive, non-overlapping window of 32 samples (for a mono file the two channels are the same).
2. **Given** a file with a loud click every 500 ms in a quiet background, **When** the measurement is run with the default settings, **Then** a peak is reported for at least 98% of the clicks, no click is reported twice, and every reported peak lies within 32 samples of its click.
3. **Given** the same file, **When** the rates are read, **Then** every peak after the first has a rate of 120 peaks per minute to within 2%.
4. **Given** two loud bursts less than the minimum distance apart, **When** the measurement is run, **Then** only the stronger one is reported.
5. **Given** a loud peak and quieter bumps that are lower than the prominence share of the window's loudest impulse energy, **When** the measurement is run, **Then** the quiet bumps are not reported and the loud peak is.
6. **Given** a peak that falls inside two overlapping peaks windows, **When** the measurement is run, **Then** it is reported once.
7. **Given** a silent file, **When** the measurement is run, **Then** it reports no peaks and nothing fails.
8. **Given** the same file and settings, **When** the measurement is run twice, **Then** the two results are identical.

---

### User Story 2 - Ask for the energy and the rate at any point of the file (Priority: P2)

Only a few points of a file are peaks, but a visualization needs a value for **every frame**. The application must therefore be able to ask the finished measurement for the **interpolated energy at any point of the file** (a sample number, or a time), and for the **rate** at that point, so that the pulse of the music can drive a picture continuously:

- **Energy**: a straight line between the energy of the **previous** peak and that of the **next** peak. **Before the first peak** it is **0**; **after the last peak** it stays at **the last peak's energy**, since there is nothing to interpolate with.
- **Rate**: always the rate recorded at the **previous** peak (it is not interpolated). **Before the first peak** it is a default of **1 per second (60 peaks per minute)**.


**Why this priority**: This is how the measurement becomes usable by the pictures ("an extra dimension in music visualizations"), but it can only be built once the peaks are right.

**Independent Test**: Run the measurement on the click file. Ask for the energy at a click: it is that peak's energy. Ask for the energy half way between two clicks: it lies between the two peaks' values. Ask at the very start of the file (energy 0, 60 peaks per minute), at its very end (the last peak's energy) and at a point that is not a whole sample: each answers without an error.

**Acceptance Scenarios**:

1. **Given** the result of a measurement, **When** the energy is asked for at the sample of a recorded peak, **Then** it is that peak's recorded energy.
2. **Given** two consecutive peaks, **When** the energy is asked for at a point between them, **Then** it is between their two values and changes smoothly (it is the straight-line interpolation) as the point moves from one to the other.
3. **Given** a point before the first peak, **When** the energy and rate are asked for, **Then** the energy is 0 and the rate is 60 peaks per minute; **Given** a point after the last peak, **Then** the energy is the last peak's energy and the rate is the last peak's rate; neither ever fails.
4. **Given** a point that is not a whole sample, or a time in seconds, **When** the energy is asked for, **Then** it answers, with the same value as the equal sample position.
5. **Given** the result of a file with no peaks, **When** the energy is asked for at any point, **Then** the energy is 0 and the rate 60 peaks per minute, and nothing fails.
6. **Given** a point outside the file (negative, or after its end), **When** the energy is asked for, **Then** it answers as for a point before the first peak (a negative point) or after the last (a point past the end), and nothing fails.
7. **Given** a point of the file, **When** the rate is asked for, **Then** it is the rate recorded at the last peak at or before the point (it is not interpolated).

---

### User Story 3 - Choose how close and how prominent peaks must be (Priority: P3)

Two settings tune what counts as a peak, and whoever makes the measurement can change them (this feature adds no control for them on the page):

- **Minimum distance**: a time, **100 ms** by default, up to **2,000 ms**. Peaks closer together than this are not both reported. It is converted to a number of impulse samples for the search, using the file's sample rate (at 44.1 kHz 100 ms is about 138 impulse samples).
- **Prominence**: a percentage, **50** by default. A peak must stand out from its surroundings by at least this share of the loudest impulse energy in the peaks window.

A value that is not allowed (a distance outside 100 to 2,000 ms, a prominence outside 0 to 100, not a number) is refused with a clear message that says what is allowed. Changing a setting changes which peaks are found: a longer distance gives fewer peaks and a lower rate, a lower prominence gives more.

**Why this priority**: The defaults already give a useful measurement; the settings tune it to different music and are secondary to the measurement itself.

**Independent Test**: Run the measurement on a file of clicks 300 ms apart with a minimum distance of 100 ms and then of 500 ms: the first reports every click, the second about every second click or fewer. Run it with a prominence of 80 on a file whose bumps are half the height of the loudest: the bumps disappear.

**Acceptance Scenarios**:

1. **Given** no settings, **When** the measurement is run, **Then** the minimum distance is 100 ms and the prominence 50.
2. **Given** a minimum distance of D ms and a file whose sample rate is R, **When** the measurement is run, **Then** two reported peaks are never closer than D ms (to within one impulse window) and the distance handed to the search is the number of impulse samples that D ms is at rate R.
3. **Given** a prominence of P, **When** the measurement is run, **Then** a bump is reported only if it stands out by at least P percent of the loudest impulse energy in its peaks window.
4. **Given** a minimum distance below 100 or above 2,000, a prominence below 0 or above 100, or a value that is not a number, **When** the settings are given, **Then** they are refused before anything is measured, with a message that says what is allowed.

---

### Edge Cases

- **A file shorter than the peaks window** (about 3 seconds): the window is as long as the file; the measurement works on what there is.
- **The start and the end of the file**: a maximum needs a lower point on each side to be a peak, so a loud sound that begins exactly at the first sample, or is still going at the last, may not be a reported peak; this is how the peak finder works and is not an error.
- **Peaks near the edge of a window**: a peak that cannot be judged in one peaks window (it is too close to the window's end) is left to the next window; it is never lost and never reported twice.
- **Plateaus**: several equal impulse energies in a row are one peak, reported once at the middle of the plateau.
- **Different sample rates** (for example 22.05, 44.1 or 48 kHz): the minimum distance is a time, so it means the same duration at every rate; a peak's position is a sample number of the file.
- **Mono files**: both channels are the same, so the energy is just that channel's standard deviation.
- **A very quiet file**: the prominence is a share of the window's own loudest energy, so a quiet file still has peaks; a **silent** window has none.
- **A minimum distance longer than the file** gives at most one peak.
- **Peaks that are not regular**: the rate is worked out from the actual gap to the previous peak, so it changes from peak to peak; music need not be metronomic.
- **The settings of the other measurements** (the note analysis, smoothing, the images) do not change and do not affect this measurement.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: There MUST be a measurement named **local_peaks** that finds the periodic local maxima of the **overall** energy of a file (the energy of the sound as a whole, not only of its harmonic content).
- **FR-002**: The energy MUST be worked out per **impulse window of 32 consecutive, non-overlapping samples**: the standard deviation of the left channel's samples in the window and that of the right channel's, averaged. For a mono file the two channels are the same.
- **FR-003**: The measurement MUST keep a running buffer of impulse energies, the **peaks window** (4096 impulse energies by default; the size may vary and its exact value is not important), and MUST find the local maxima of that window with `scipy.signal.find_peaks`, window after window, until the whole file has been covered.
- **FR-004**: A peak MUST be reported **once**, however many peaks windows contain it, and a peak that cannot be judged in one window MUST be left to the next window rather than lost.
- **FR-005**: The **distance** given to the peak finder MUST be the **minimum distance** (a time) converted to a number of impulse samples using the file's sample rate and the 32-sample impulse window (at least 1).
- **FR-006**: The **prominence** given to the peak finder MUST be the **prominence percentage** of the largest impulse energy in the peaks window being searched.
- **FR-007**: For every peak the measurement MUST record: **(a)** the sample of the file where the maximum is; **(b)** its **energy**, and the **minimum and maximum energy of the peaks window** in which it was found; **(c)** the **rate in peaks per minute** at that peak, worked out from the time since the previous peak (the first peak, which has no previous peak, takes the default of 60).
- **FR-008**: The result MUST be ordered by sample and MUST list no peak twice; the same file and settings MUST always give the same result.
- **FR-009**: The application MUST be able to ask a finished measurement for the **interpolated energy at any point of the file**, given as a sample number or a time, and for the **rate** at that point; the energy MUST be the straight-line interpolation between the previous and the next peak, 0 before the first peak and the last peak's energy after the last, and the rate MUST be that of the previous peak (60 peaks per minute before the first); an answer MUST be given for every point, including for a file with no peaks.
- **FR-010**: **Minimum distance** MUST be a time from 100 to 2,000 milliseconds, default 100; **prominence** MUST be a number from 0 to 100 (percent), default 50. A value outside these, or not a number, MUST be refused with a clear message before anything is measured.
- **FR-011**: A silent file or window MUST give no peaks and no failure; a short file MUST be measured with a window as long as the file.
- **FR-012**: The measurement MUST NOT change the note analysis, the smoothing or any picture: it is an additional measurement, and the frames of every image type MUST be identical, file for file, to those made before this feature.
- **FR-013**: Measuring a 60 second file MUST take no more than a few seconds (SC-006).
- **FR-014**: The documentation MUST describe the measurement, its two settings, what it records and how to ask for the interpolated energy.

### Key Entities *(include if feature involves data)*

- **Impulse sample**: The energy of one 32-sample window of the file: the average of the standard deviations of its left and right samples. One per 32 samples of the file.
- **Peaks window**: The running buffer of the most recent impulse samples (4096 by default) over which the peaks are searched.
- **Local peak**: One reported maximum: the sample where it occurs, its energy, the minimum and maximum energy of the peaks window it was found in, and the rate in peaks per minute at it.
- **Local peaks measurement**: The ordered list of the local peaks of one file, with the settings it was made with (minimum distance, prominence), the file's sample rate and length, and the ability to answer **the interpolated energy and the rate at any point** of the file.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a 30 second test file of a quiet background with one loud click every 500 ms, the measurement reports a peak for at least 98% of the clicks, none twice, each within 32 samples of its click.
- **SC-002**: For the same file, the rate at every peak after the first is 120 peaks per minute to within 2%; for a file with clicks every 750 ms it is 80 to within 2%.
- **SC-003**: Two bursts closer than the minimum distance give one peak (the stronger), at every minimum distance from 100 to 2,000 ms tested, and no two reported peaks are ever closer than the minimum distance to within one impulse window.
- **SC-004**: Bumps lower than the prominence share of the loudest energy in the window are never reported, and a click above it always is, for prominence values of 10, 50 and 90.
- **SC-005**: The interpolated energy at the sample of every recorded peak equals that peak's recorded energy; at any point between two peaks it lies between their two values, it is 0 before the first peak and the last peak's energy after the last; every query, on every test file (including a silent one and the file's first and last sample), returns an answer.
- **SC-006**: Measuring a 60 second stereo file takes under 5 seconds.
- **SC-007**: A result does not depend on the size of the peaks window: for a click file whose clicks are well separated, windows of 2,048 and of 8,192 impulse samples report the same peaks.
- **SC-008**: Two runs of the same file and settings give identical results, and the frames of every existing image type for a test file are identical, file for file, to those made before this feature.

## Assumptions

- **The standard deviation is taken per channel, then averaged** (never the channels averaged first), so two channels in opposite phase still count as energy.
- **"Overall energy" is the loudness of the sound as a whole**, measured as the spread (standard deviation) of the samples, so it follows the music's beats whatever notes are playing; it is independent of the note analysis.
- **Impulse windows do not overlap**, are 32 samples long (about 0.7 ms at 44.1 kHz) and are counted from the first sample of the file; a last window with fewer than 32 samples is dropped. A peak's sample is the **first sample of its impulse window**, so positions are exact to 32 samples.
- **The peaks window slides through the file** in steps of about half its length so that every part of the file is judged with samples on both sides; a peak is accepted from the window in which it is far enough from both of that window's edges, and the last window judges the end of the file. The exact window size, step and edge margin are not important (the request says so) and may vary, provided the results of Story 1 hold.
- **The rate at a peak is 60 divided by the seconds since the previous peak.** The first peak has no previous peak, so it takes the default of 1 per second (60 peaks per minute), which is also the rate before the first peak.
- **The minimum and maximum energy of a peak** are the lowest and highest impulse energy in the peaks window in which the peak was found (they need not be the window's trough). The peak's own energy is recorded as well, because the interpolation needs it.
- **The distance in impulse samples** is `round(minimum distance in seconds × sample rate / 32)`, at least 1.
- **The two settings are checked when the measurement is made** (numbers, refused with a clear message when not allowed); the ranges are 100 to 2,000 ms and 0 to 100 percent.
- **The measurement is separate from the pictures.** This feature produces the measurement and the way to ask for its energy and rate; using it as an extra dimension in the images is a later feature.
- **This feature is the measurement only**: the two settings are parameters of the measurement, and nothing changes in the job request or response, the endpoints or the settings page. How the measurement is used is defined later.
- This feature does not change the audio reading, the note analysis, smoothing, the frames or the page layout.
