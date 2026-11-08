# Research: Noise Floor

No `NEEDS CLARIFICATION` remains in the spec. The questions below are about where and how to build it. The project constitution is still the unfilled template, so there are no gates to check.

## Decision 1: A new small module, applied once to the analysis result in the job

- **Decision**: Add `backend/app/services/noise_floor.py` with the constant, `apply_noise_floor(values, peak=None)` (a copy of an array of note strengths with every value strictly below the floor set to 0) and `floor_analysis(result)` (the same for an `AnalysisResult`, returned as a new one). The job (`backend/app/routers/jobs.py`, the only production caller of `analyze_channels`) calls `floor_analysis` on the result of the analysis, before `average_frames` and `write_frames`. Nothing else in the pipeline changes.
- **Rationale**: The spec asks for one cut that every picture and measurement sees, before smoothing (FR-001, FR-003, the assumption "one cut for everything"). The job has a single place where the analysed windows exist and a single caller, so one call there covers every image type, with or without a Threshold, with no new field. A separate function keeps the analysis module as it was, so the analysis tests and the reference values do not move, and the cut is testable on its own.
- **Alternatives considered**: inside `analyze_channels` (every direct caller, including the tests of the analysis and the chord tests with synthesized tones, would get a changed analysis, and the analysis would silently stop being the plain spectrum); inside `write_frames` (it works on the frames after they are averaged, so a note would be judged on an average of windows and not on its own window, as FR-001 says, and each image type's tests that call `write_frames` with small arbitrary values would change); inside each picture (one copy for every picture, which is how the thresholds drifted apart before).

## Decision 2: The level, the reference and the comparison

- **Decision**: `NOISE_FLOOR_DB = -60` and `NOISE_FLOOR = 10 ** (NOISE_FLOOR_DB / 20)` (= `0.001`, an amplitude ratio, because the strengths are magnitudes of the spectrum: `np.abs(np.fft.rfft(...))`, averaged over the two channels). The reference is the **largest value of the whole array given, over all its columns** (the 88 analysed notes, the four undrawn ones included), the same reference as `hidden_notes`/`hidden_below`. A value is cut when it is **strictly below** `NOISE_FLOOR * peak`; with `peak` 0 nothing is cut. The cut value is exactly `0.0`.
- **Rationale**: FR-001/FR-002 and the Threshold precedent (`hidden_below`: "strictly below hides; the largest value of the whole file"). The analysed values have no absolute dB scale (they scale with the window size and the recording level), so "−60 dB" can only be a ratio to something in the file; the loudest value is the reference the project already uses for the Threshold and for the colors. A ratio of 1,000 for −60 dB is right for amplitudes (power would be 1,000,000).
- **Alternatives considered**: a power ratio of 10⁻⁶ (wrong unit: it would be −120 dB for these strengths); a reference per window or per passage (the spec rules it out: the floor is file-wide, like the Threshold); an absolute level in dB below full scale (would need the strengths scaled to full scale first, which depends on the window size; out of scope).

## Decision 3: The chord measurement applies the same floor itself, and loses its own weaker floor

- **Decision**: `measure_chords` calls `apply_noise_floor` on the strengths it is given (`values[:, :84]`, with the peak of the whole array as for the Threshold) **first**, before the Notes limit and the Threshold, then combines the octaves of what is left. The older floor of feature 031 (`NOISE_FLOOR = 1e-6` of the loudest letter of the window, in `_letters`) is removed.
- **Rationale**: FR-005: the floor must hold for the chord measurement whatever array it gets, and the notes must be cut **before** the octaves are combined (acceptance scenario 4 of Story 2). The 031 floor is wholly covered by the new one: a letter that survives a millionth of the window's loudest letter but not a thousandth of the file's loudest note would need a window whose loudest letter is more than a thousand times the file's loudest note, which cannot be. Two floors would also be two rules to explain. Applying the floor to an array that is already cut (the pictures' case) changes nothing, because the cut leaves the largest value alone and a cut value is below the floor of its own array: the cut is idempotent.
- **Alternatives considered**: relying on the job having cut the values (the measurement is a library that tests and later features call with any array; the spec says it must hold for any array); keeping the 1e-6 floor as well (dead weight, and it would still need its own tests and words).

## Decision 4: The Threshold and the other limits need no change

- **Decision**: `hidden_below` / `hidden_notes` (the Threshold) and `top_energy_notes` (the Notes setting) are untouched. After the cut the values they see already hold zeros for the faint notes, so the Threshold hides what is below the chosen percentage or the floor, whichever is stricter, and a Threshold of 0 still hides nothing *more*; the Notes setting ranks energy on cut values.
- **Rationale**: FR-006 is true by construction of the order (cut, then the rest). Not touching them keeps SC-006 and the existing tests of both.
- **Alternatives considered**: adding the floor to `hidden_below` (a second place that would need the same constant, and `hidden_below` is used on already smoothed values, where the spec says the values are not cut again).

## Decision 5: The beat is not affected, which the spec left to the plan

- **Decision**: No change to the local peaks measurement. `measure_local_peaks(left, right, ...)` takes the audio channels, not the note strengths, so the cut cannot reach it.
- **Rationale**: Read in `jobs.py` (`beat = measure_local_peaks(left, right, file_rate, ...)`). The spec's assumption "the beat is not expected to change ... the plan checks it" is therefore exact: the beat is identical.
- **Alternatives considered**: none needed.

## Decision 6: Existing expectations that rested on the leakage

- **Decision**: Run the whole suite after the change. A test whose expectation depended on a value below the floor (a leaking neighbour note of a synthesized tone, a colour computed from a very faint value) is changed to the new rule and listed in the tasks and the final report; no picture or measurement is changed to keep an old expectation. Tests of the chord measurement that built faint notes below a thousandth of the loudest are adjusted: the old 1e-6 boundary tests become tests of the new floor, and the oracle works on values cut with the same independent rule.
- **Rationale**: SC-005 says a file with nothing under the floor is unchanged; a file with something under it is meant to change.
- **Alternatives considered**: a switch to turn the floor off for the old tests (FR-003 says there is no setting).

## Decision 7: Documentation, not page text

- **Decision**: The README gets a "Noise floor" paragraph (the level, the reference, fixed, every picture, the chords, exactly at the floor counts) and its chord paragraph loses the "millionth" wording; the 031 documents lose the old floor. The settings page and its help text are not changed.
- **Rationale**: FR-008 asks for documentation; SC-006 asks that the page stays as it was.
- **Alternatives considered**: a sentence in the Threshold help (the page would change, against SC-006).
