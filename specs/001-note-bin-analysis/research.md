# Research: Musical Note Bin Analysis

No `NEEDS CLARIFICATION` items were open. The decisions below cover technology and numeric choices.

## Decision 1: FFT library

- **Decision**: `numpy.fft.rfft` on real input, batched across windows.
- **Rationale**: The input is real audio, so the real FFT gives the same values as the full FFT for positions 0 to N/2 at about half the cost. Every note position the formula can produce must be at most N/2 anyway (see Decision 4). numpy is also the standard dependency for later visualizer work.
- **Alternatives considered**: `scipy.fft` (equivalent, extra import with no gain here); a hand-written FFT (no benefit, slower).

## Decision 2: WAV decoding

- **Decision**: `scipy.io.wavfile.read`.
- **Rationale**: The standard-library `wave` module cannot decode 24-bit samples into numbers directly and rejects WAVE_FORMAT_EXTENSIBLE files. The sample file in `backend/audio/` is 24-bit with a `bext` chunk. `scipy.io.wavfile` handles 8/16/24/32-bit PCM and float, and skips unknown chunks. It also reports the file's own sample rate for the mismatch warning (FR-011).
- **Alternatives considered**: `soundfile` (needs libsndfile, heavier install); stdlib `wave` plus manual byte unpacking (more code and still no extensible-format support).

## Decision 3: Sample scaling

- **Decision**: Convert to float64 in the range about [-1, 1]: int16 ÷ 32768, int32 ÷ 2^31 (scipy returns 24-bit audio left-justified in int32), uint8 as (x − 128) ÷ 128, float used as is.
- **Rationale**: Satisfies the assumption that results do not depend on bit depth.
- **Alternatives considered**: Keep raw integers (results would differ by bit depth).

## Decision 4: Note position and validity

- **Decision**: `index = int((window_size / sample_rate) * freq)` computed in floating point, exactly as written in the spec. Valid only if `index <= window_size // 2` for all 88 notes. Otherwise raise an error naming the offending note and the minimum sample rate.
- **Rationale**: The top note is 55 × 2^(87/12) ≈ 8,372 Hz, so any sample rate of at least about 16.75 kHz works. Anything lower would index past the spectrum.
- **Alternatives considered**: Clamping to the last position (silently wrong data, rejected by FR-010).

## Decision 5: Averaging

- **Decision**: Take the magnitudes of the left and right spectra, then `(|L| + |R|) / 2`.
- **Rationale**: Matches the spec assumption ("mean of the left and right magnitudes"). A tone in one channel then produces exactly half the value of the same tone in both (SC-003). Averaging complex values instead would let out-of-phase channels cancel.
- **Alternatives considered**: Average the raw samples first (phase cancellation); average power (not what the spec says).

## Decision 6: Windowing and padding

- **Decision**: Consecutive, non-overlapping rectangular windows. The last partial window is zero-padded. Magnitudes are raw, with no normalization.
- **Rationale**: Directly from the spec assumptions.
- **Alternatives considered**: Hann window or overlap (explicitly deferred in the spec).

## Decision 7: Memory and speed

- **Decision**: Reshape the padded channel arrays into `(windows, window_size)` and run `rfft` in chunks of about 4M samples per channel (2048 windows at a 2048 window size), converting each chunk to float64 only when it is processed. Only the 88 needed positions are kept from each chunk.
- **Rationale**: Keeps peak memory small for long files and stays fast (vectorized).
- **Alternatives considered**: One FFT call over the entire file (large temporary arrays); a Python loop per window (slow).

## Decision 8: Interface shape

- **Decision**: A class `NoteBinAnalyzer(sample_rate, window_size)` with `analyze(left, right) -> ndarray[88]`, plus a function `analyze_wav(path, sample_rate, window_size) -> AnalysisResult`. Errors are `AudioAnalysisError`, a subclass of `ValueError`. Warnings use the standard `warnings` module.
- **Rationale**: Matches the spec's "an object" and the two user stories. See [contracts/note_analysis_api.md](contracts/note_analysis_api.md).
- **Alternatives considered**: A CLI or REST endpoint (out of scope for this feature).
