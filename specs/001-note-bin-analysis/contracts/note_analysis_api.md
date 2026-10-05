# Contract: Note Analysis Python API

Module: `app.services.note_analysis` (file `backend/app/services/note_analysis.py`).

## Exceptions and warnings

- `AudioAnalysisError(ValueError)` is raised for every invalid input listed under FR-010. The message says what is wrong and how to fix it.
- `UserWarning` is issued when the supplied sample rate differs from the WAV file's header rate (FR-011).

## `NoteBinAnalyzer(sample_rate: float, window_size: int)`

| Member | Description |
|--------|-------------|
| `sample_rate`, `window_size` | The validated parameters |
| `frequencies` | `numpy.ndarray`, shape `(88,)`, the note frequencies in Hz |
| `bin_indices` | `numpy.ndarray`, shape `(88,)`, the spectrum position for each note |
| `analyze(left, right)` | Returns `numpy.ndarray`, shape `(88,)`, dtype float64 |

`analyze` input: two 1-D numeric sequences of equal length no greater than `window_size`. Shorter input is zero-padded. Integer input is not rescaled here, since callers pass float samples. `analyze_wav` handles scaling for file input.

Errors at construction: `sample_rate <= 0`, `window_size` not a positive integer, or any note position above `window_size // 2`.
Errors in `analyze`: unequal lengths, length above `window_size`, non-1-D input.

## `analyze_wav(path, sample_rate: float, window_size: int) -> AnalysisResult`

Reads the file at `path`, splits it into consecutive windows of `window_size` samples (the last one zero-padded), and returns an `AnalysisResult`.

Errors: file missing or not a readable WAV, more than 2 channels, or any `NoteBinAnalyzer` construction error.
Warnings: sample-rate mismatch (see above).
An empty file returns a result with 0 windows.

## `AnalysisResult`

| Member | Description |
|--------|-------------|
| `sample_rate` | float |
| `window_size` | int |
| `frames` | `numpy.ndarray`, shape `(window_count, 88)` |
| `window_count` | int |
| `window_start_times()` | `numpy.ndarray`, shape `(window_count,)`, seconds |

## Behavior guarantees

- Same inputs always give the same output.
- Row *i* of `frames` covers samples `[i * window_size, (i + 1) * window_size)`.
- Column *n* is the note with frequency `55 * 2**(n/12)`.
