# Implementation Plan: Musical Note Bin Analysis

**Branch**: `001-note-bin-analysis` | **Date**: 2026-10-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-note-bin-analysis/spec.md`

## Summary

Add an analysis service to the existing Python backend. A `NoteBinAnalyzer` object takes the sample rate and window size, then turns one left/right buffer pair into 88 note values: it takes the real FFT of each channel, averages the two magnitude spectra, and reads the position `int((window_size / sample_rate) * freq)` for each of the 88 notes (55 Hz × 2^(n/12)). A file-level function reads a `.wav`, slices it into consecutive zero-padded windows, and returns a `(windows, 88)` array with timing information. No HTTP endpoint is added in this feature; the service is a plain Python module the visualizer can call later.

## Technical Context

**Language/Version**: Python 3.10 (the existing `backend/.venv`)

**Primary Dependencies**: numpy (FFT, array math), scipy (`scipy.io.wavfile` for WAV decoding, including 24-bit PCM). Both are new additions to `backend/requirements.txt`.

**Storage**: N/A. Input is a WAV file and output is in memory. The sample `backend/audio/fotr-intro1-echo.wav` is 24-bit stereo at 44.1 kHz.

**Testing**: pytest (already configured in `backend/pytest.ini`). Tests synthesize tones and temporary WAV files, so they need no fixture audio.

**Target Platform**: Developer machine (Windows here), also Linux/macOS.

**Project Type**: Library module inside the existing web-service backend (`backend/app/services`).

**Performance Goals**: 3-minute stereo file at 44.1 kHz with a 2048-sample window analyzed in under 10 seconds (SC-004).

**Constraints**: Deterministic output. Memory is bounded by transforming windows in chunks, because the sample file is about 90 MB and decodes to roughly 700 MB if converted to float64 all at once, so chunking applies to the FFT stage and the decoded array is converted per chunk.

**Scale/Scope**: One module of roughly 150 lines plus tests. 88 notes, files of up to tens of minutes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so there are no gates to evaluate. Result: **PASS (no constraints defined)**. The design stays simple regardless: one module, no new layers, tests alongside. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/001-note-bin-analysis/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── note_analysis_api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── requirements.txt              # + numpy, scipy
├── app/
│   └── services/
│       └── note_analysis.py      # NoteBinAnalyzer, AnalysisResult, analyze_wav, AudioAnalysisError
└── tests/
    └── test_note_analysis.py     # unit + file-level tests
```

**Structure Decision**: The repository already has a `backend/` Python project with `app/services/` for domain logic and `tests/` for pytest. The analysis goes in one new service module and one test module. The frontend and the API routers are untouched.

## Complexity Tracking

No constitution violations. Nothing to justify.
