# Feature Specification: Musical Note Bin Analysis

**Feature Branch**: `001-note-bin-analysis` (no git branch created; spec directory name only)

**Created**: 2026-10-04

**Status**: Draft

**Input**: User description: "The python application will take an audio .wav file and analyze it, storing information about the file at different times into bins. First, create an object that takes the left and right stereo buffer from the wav file, finds the FFT based on a window size for that data, and averages them. For each value in the array, pick the bins associated with musical notes using this formula to calculate the index into the FFT: int((fftWindowSize / sampleRate) * freq). 'freq' here is the note, starting with A0=55Hz. So A1 will be 110Hz, B0 will be pow(pow(2, 1/12), 2), C0 will be pow(pow(2, 1/12), 2) etc. So at the end there will be 88 values for each window. The parameters, along with the audio file, will be the sample rate and desired window size."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Turn one window of stereo audio into 88 note values (Priority: P1)

A developer building the music visualizer has a short slice of stereo audio (a left buffer and a right buffer) that is exactly one analysis window long. They give both buffers, plus the sample rate and window size, to the analysis object. They get back 88 numbers, one per musical note, showing how much energy the audio has at each note. The two channels are combined, so the result reflects the whole stereo image and not just one side.

**Why this priority**: This is the core transformation. Every other part of the visualizer depends on a correct 88-value note profile for a window, and it can be built and verified without any file handling.

**Independent Test**: Generate a left/right buffer that holds a pure tone at a known note frequency (for example 440 Hz), run it through the analyzer, and check that the note bin matching that frequency holds the largest value. This works with no WAV file involved.

**Acceptance Scenarios**:

1. **Given** left and right buffers each containing a pure 440 Hz tone, **When** the analyzer processes one window, **Then** it returns exactly 88 values and the value for the note whose bin covers 440 Hz is the largest of the 88.
2. **Given** a left buffer containing a tone and a right buffer containing silence, **When** the analyzer processes one window, **Then** the tone's note value is half of what it would be if the same tone were present in both channels (the channels are averaged).
3. **Given** left and right buffers that are both silent, **When** the analyzer processes one window, **Then** all 88 values are zero.
4. **Given** a sample rate and window size, **When** note frequencies are mapped to spectrum positions, **Then** each note uses position `int((window size / sample rate) * note frequency)`.

---

### User Story 2 - Analyze an entire WAV file over time (Priority: P2)

A developer provides a stereo `.wav` file, a sample rate, and a window size. The application reads the file, splits it into consecutive windows, runs each window through the note analysis, and returns an ordered series of 88-value results, one per window, so the visualizer can show how the note content changes over time.

**Why this priority**: This makes the analysis usable on real audio. It depends on the P1 analysis and adds file reading and time-slicing.

**Independent Test**: Analyze a WAV file of known length that plays one steady note, and check that the number of results matches the expected number of windows and that every result peaks at that note.

**Acceptance Scenarios**:

1. **Given** a stereo WAV file, a sample rate, and a window size, **When** the file is analyzed, **Then** the output is an ordered list of windows, each with 88 values, covering the whole file from start to end.
2. **Given** a WAV file whose total sample count is not a multiple of the window size, **When** it is analyzed, **Then** the final partial window is still analyzed (padded with silence) and no audio at the end of the file is dropped.
3. **Given** a mono WAV file, **When** it is analyzed, **Then** the single channel is used for both left and right and analysis completes successfully.
4. **Given** a file that is not a readable WAV file, **When** analysis is requested, **Then** the user gets a clear error message and no partial output is presented as valid.

---

### Edge Cases

- **Low notes sharing a spectrum position**: At common settings (for example a 2048-sample window at 44,100 Hz) neighboring low notes map to the same position in the spectrum, so those notes show identical values. This follows from the specified formula and is expected, not an error. Larger window sizes separate them.
- **Window too small or sample rate too low for the top notes**: If a note's computed position falls outside the usable half of the spectrum, which happens when the sample rate is too low to represent the highest note (about 8.4 kHz), the analyzer rejects the parameters with a clear message. It does not silently return wrong data.
- **Sample rate parameter differs from the file's own sample rate**: The supplied value is used in the calculation. The user is warned about the mismatch.
- **Invalid parameters**: A window size or sample rate that is zero, negative, or not a whole number (for window size) is rejected with a clear message.
- **Empty or extremely short file**: A file with no audio samples produces an empty result and a clear message. A file shorter than one window produces one zero-padded window.
- **Left and right buffers of different lengths**: Rejected with a clear message.
- **Very loud or clipped audio**: Values are reported as computed. The analyzer does not clip or crash.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a left-channel buffer, a right-channel buffer, a sample rate, and a window size, and produce one result of exactly 88 note values for that window.
- **FR-002**: The system MUST compute the frequency spectrum of the left channel and of the right channel separately over the window, then average the two spectra value by value into a single spectrum.
- **FR-003**: The system MUST define 88 notes starting at A0 = 55 Hz. Each following note is one semitone higher, so note *n* (n = 0 to 87) has frequency 55 × (2^(1/12))^n. This gives A1 = 110 Hz and B0 = 55 × (2^(1/12))^2.
- **FR-004**: For each note, the system MUST select the spectrum position `int((window size / sample rate) * note frequency)` and use the averaged spectrum value at that position as the note's value.
- **FR-005**: The 88 values for a window MUST be ordered from the lowest note (A0) to the highest (note 87).
- **FR-006**: The system MUST accept a `.wav` file together with a sample rate and a window size, and split the file's audio into consecutive windows of the given size.
- **FR-007**: The system MUST return one 88-value result per window, in time order, so each result can be tied to a position in the file (window index × window size ÷ sample rate gives its start time).
- **FR-008**: The system MUST analyze a final partial window by padding it with silence, so no audio is dropped.
- **FR-009**: The system MUST treat a mono file as identical left and right channels.
- **FR-010**: The system MUST reject invalid input with a clear, human-readable message. Invalid input includes an unreadable or non-WAV file, a non-positive sample rate or window size, mismatched channel buffer lengths, and parameters that put a note's position outside the usable spectrum.
- **FR-011**: The system MUST warn the user when the supplied sample rate differs from the sample rate recorded in the WAV file, and MUST still use the supplied value.
- **FR-012**: Given the same inputs, the system MUST return the same output every time.

### Key Entities

- **Note Bin Analyzer**: The object that holds the sample rate and window size, and turns one pair of left/right buffers into 88 note values. It owns the note frequency table and the note-to-spectrum-position mapping.
- **Note**: One of 88 pitches, identified by its index (0 to 87) and its frequency, starting at 55 Hz and rising by one semitone per index.
- **Window Result**: The 88 note values for one window, plus its position in time within the file.
- **Analysis Result**: The ordered series of window results for a whole file, along with the parameters (sample rate, window size) used to produce it.
- **Audio File**: The input `.wav` file with its left and right channel sample data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a pure tone at any of the 88 note frequencies, the correct note value is the largest in the result in at least 95% of the 88 notes when tested at a window size large enough to separate neighboring notes. Notes that share a spectrum position with a neighbor under the formula are excluded from this count.
- **SC-002**: Every window result contains exactly 88 values, in 100% of analyzed windows.
- **SC-003**: Averaging is verified. A tone present in only one channel produces half the value of the same tone present in both channels, within 1% tolerance.
- **SC-004**: A 3-minute stereo file at 44,100 Hz with a 2048-sample window is analyzed in under 10 seconds on an ordinary laptop.
- **SC-005**: Every invalid-input case listed in the Edge Cases section produces an error or warning message that says what is wrong and how to fix it, with no crashes or unexplained output.
- **SC-006**: Running the same file with the same parameters twice produces identical results.

## Assumptions

- **Note frequencies**: The user's description gives A0 = 55 Hz and A1 = 110 Hz, so octaves are counted from A, and each note is one semitone (a factor of 2^(1/12)) above the previous one. The description lists B0 and C0 with the same expression, which is read as a typo. B0 is two semitones above A0 and C0 follows as the next semitone, so all 88 notes continue the same semitone series. This puts the top note at about 8,372 Hz.
- **Note naming**: The 88 notes follow this series by index. Mapping them to conventional note names, whose octave numbering differs from the 55 Hz = A0 convention, is out of scope. Labeling is left to later work.
- **Spectrum value**: Each spectrum value is the magnitude (absolute size) of the transform at that position. "Averages them" means the mean of the left and right magnitudes at each position.
- **Windowing**: Windows are consecutive and do not overlap. No smoothing function (such as a Hann window) is applied. Either can be added later.
- **Value scale**: Values are raw magnitudes and are not normalized or converted to decibels. Scaling for display belongs to the visualizer.
- **Sample rate parameter**: The sample rate is a caller-supplied parameter, as the description states. It is expected to match the file's rate in normal use.
- **Channel layout**: Input files are mono or stereo. Files with more than two channels are out of scope and are rejected with a clear message.
- **Sample formats**: Common PCM WAV formats (such as 16-bit) are supported. Samples are scaled to a consistent range so results do not depend on bit depth.
- **Scope**: This feature covers analysis only. Playback, rendering, and saving results to disk are out of scope. The visualizer will consume the in-memory result.
- **Language**: The application is written in Python, as stated in the description.
