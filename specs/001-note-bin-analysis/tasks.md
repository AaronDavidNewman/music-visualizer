---

description: "Task list for Musical Note Bin Analysis"
---

# Tasks: Musical Note Bin Analysis

**Input**: Design documents from `/specs/001-note-bin-analysis/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/note_analysis_api.md, quickstart.md

**Tests**: Included. The plan lists pytest tests for every acceptance scenario, and the quickstart runs them.

**Organization**: Tasks are grouped by user story. All paths are relative to the repository root.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story the task belongs to (US1, US2)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies and file skeletons

- [x] T001 Add `numpy>=1.26` and `scipy>=1.11` to `backend/requirements.txt`, then install them into `backend/.venv` with `pip install -r backend/requirements-dev.txt`
- [x] T002 [P] Make sure `backend/audio/` (sample audio, about 90 MB) is not committed: add `backend/audio/` to `.gitignore` if it is not already ignored
- [x] T003 Create `backend/app/services/note_analysis.py` with a module docstring and imports only, and `backend/tests/test_note_analysis.py` with imports and a small helper that builds a sine-tone buffer

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Items both user stories use

- [x] T004 In `backend/app/services/note_analysis.py`, define `NOTE_COUNT = 88`, `BASE_FREQUENCY = 55.0`, and `AudioAnalysisError(ValueError)`
- [x] T005 In `backend/app/services/note_analysis.py`, add a function `note_frequencies()` returning a float64 array of 88 values, `55 * 2**(n/12)` for n = 0 to 87 (so index 12 is 110 Hz and index 2 is `55 * (2**(1/12))**2`)

**Checkpoint**: Constants, error type, and note table exist.

---

## Phase 3: User Story 1 - One window of stereo audio into 88 note values (Priority: P1) 🎯 MVP

**Goal**: `NoteBinAnalyzer(sample_rate, window_size).analyze(left, right)` returns 88 averaged-spectrum values.

**Independent Test**: A 440 Hz tone in both channels peaks at the note position covering 440 Hz, with no WAV file involved.

### Tests for User Story 1

- [x] T006 [US1] In `backend/tests/test_note_analysis.py`, add tests: note table has 88 entries with index 0 = 55 Hz, index 12 = 110 Hz, index 2 = `55 * (2**(1/12))**2`; `bin_indices` equal `int((window_size / sample_rate) * freq)` for every note (spec scenario 4)
- [x] T007 [US1] In `backend/tests/test_note_analysis.py`, add tests: a 440 Hz tone in both channels (window 2048, rate 44100) returns shape `(88,)` and the maximum is at the note whose position is `int(2048/44100*440)`; silence in both channels returns all zeros; a tone in the left channel only gives half the value of the same tone in both channels, within 1%; the result is identical on a repeat call
- [x] T008 [US1] In `backend/tests/test_note_analysis.py`, add error tests (each expects `AudioAnalysisError`): `sample_rate` of 0 or negative; `window_size` of 0, negative, or a non-integer such as 2048.5; `NoteBinAnalyzer(8000, 2048)` (top note beyond `window_size // 2`); left and right of different lengths; buffer longer than `window_size`; a 2-D buffer
- [x] T009 [US1] In `backend/tests/test_note_analysis.py`, add the SC-001 test: for each of the 88 notes, make a pure tone at the note's frequency with window 32768 at 44100 Hz, exclude notes whose position is shared with a neighbour, and report the fraction whose own position holds the maximum

### Implementation for User Story 1

- [x] T010 [US1] In `backend/app/services/note_analysis.py`, implement `NoteBinAnalyzer.__init__(sample_rate, window_size)`: validate `sample_rate > 0` and `window_size` is a positive integer (reject bool and non-integer floats); compute `frequencies` via `note_frequencies()` and `bin_indices = int((window_size / sample_rate) * freq)` per note; raise `AudioAnalysisError` naming the offending note and the minimum sample rate if `max(bin_indices) > window_size // 2`
- [x] T011 [US1] In `backend/app/services/note_analysis.py`, implement `NoteBinAnalyzer.analyze(left, right)`: validate 1-D numeric input of equal length not above `window_size`; compute `numpy.fft.rfft(buffer, n=window_size)` for each channel (zero-padding short buffers); `spectrum = (abs(left_fft) + abs(right_fft)) / 2`; return `spectrum[bin_indices]` as float64, ordered lowest note first
- [x] T012 [US1] Run `pytest backend/tests/test_note_analysis.py` from `backend/` and fix failures in T006 to T008. Record the T009 result.

**Checkpoint**: User Story 1 works on its own.

---

## Phase 4: User Story 2 - Analyze an entire WAV file over time (Priority: P2)

**Goal**: `analyze_wav(path, sample_rate, window_size)` returns an `AnalysisResult` with one 88-value row per consecutive window.

**Independent Test**: A generated WAV of one steady note yields `ceil(samples / window_size)` rows, each peaking at that note.

### Tests for User Story 2

- [x] T013 [US2] In `backend/tests/test_note_analysis.py`, add a fixture that writes temporary stereo WAV files (use `scipy.io.wavfile.write`, int16 and also int32 to exercise scaling), and tests: row count equals `ceil(samples / window_size)`; every row peaks at the tone's note; `window_start_times()` equals `i * window_size / sample_rate`; a file length that is not a multiple of the window size still produces a final padded row
- [x] T014 [US2] In `backend/tests/test_note_analysis.py`, add tests: a mono file gives the same result as the same audio written as stereo with identical channels; int16 and int32 versions of the same audio give matching results within 1%; an empty file gives shape `(0, 88)`; a file shorter than one window gives one row
- [x] T015 [US2] In `backend/tests/test_note_analysis.py`, add error and warning tests: a missing path and a text file renamed `.wav` raise `AudioAnalysisError`; a 3-channel file raises `AudioAnalysisError`; a supplied sample rate different from the file's header rate emits `UserWarning` (use `pytest.warns`) and still returns a result computed with the supplied rate

### Implementation for User Story 2

- [x] T016 [US2] In `backend/app/services/note_analysis.py`, define the frozen dataclass `AnalysisResult(sample_rate, window_size, frames)` with the properties `window_count` and the method `window_start_times()` returning `arange(window_count) * window_size / sample_rate`
- [x] T017 [US2] In `backend/app/services/note_analysis.py`, implement `analyze_wav(path, sample_rate, window_size)`: build the `NoteBinAnalyzer` first (so parameter errors come before file errors); read with `scipy.io.wavfile.read`, converting any read failure to `AudioAnalysisError`; reject more than 2 channels; duplicate a mono channel; scale integer data to about [-1, 1] (int16 ÷ 32768, int32 ÷ 2**31, uint8 as (x − 128) ÷ 128, float as is); warn with `UserWarning` if the file's rate differs from `sample_rate`
- [x] T018 [US2] In `backend/app/services/note_analysis.py`, complete `analyze_wav` windowing: zero-pad both channels to a multiple of `window_size`, reshape to `(window_count, window_size)`, and process in chunks of at most `_CHUNK_SAMPLES` (4M) samples per channel (`rfft` along axis 1, `(abs(L) + abs(R)) / 2`, take columns `bin_indices`), converting each chunk to float64 only when processed; return `AnalysisResult` with `frames` of shape `(window_count, 88)`, and shape `(0, 88)` for an empty file
- [x] T019 [US2] Run `pytest backend/tests/test_note_analysis.py` from `backend/` and fix failures in T013 to T015

**Checkpoint**: Both stories work.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T020 Run the quickstart steps from `specs/001-note-bin-analysis/quickstart.md` against `backend/audio/fotr-intro1-echo.wav` (24-bit stereo, 44.1 kHz). Record the window count and wall-clock time to check SC-004 (3-minute file, 2048 window, under 10 seconds), and note the peak memory use is reasonable
- [x] T021 Run the whole `backend` test suite (`pytest` from `backend/`) to confirm the existing API tests still pass
- [x] T022 [P] Add a short "Note analysis" section to `README.md` describing `analyze_wav` and `NoteBinAnalyzer` with one usage example
- [x] T023 Mark completed tasks `[x]` in this file

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → Phase 5.
- US2 builds on US1's `NoteBinAnalyzer` (it reuses `bin_indices`), so run them in order.
- Most tasks touch the same two files, so few are parallel. T002 and T022 are independent of the code.
- Write tests T006 to T009 before T010 and T011 and see them fail. Do the same for T013 to T015 before T016 to T018.

## Implementation Strategy

- **MVP**: Phases 1 to 3. This gives a tested `NoteBinAnalyzer` with no file handling.
- **Then**: Phase 4 adds the WAV reader and time slicing, and Phase 5 validates against the real file and the existing suite.
