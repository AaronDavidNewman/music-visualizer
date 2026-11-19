# Contract: `POST /api/jobs` (the settings of the analysis)

Only what this feature changes is listed; every other field of the request and of the answer is as it is today.

## Request (multipart form)

| Field | Before | After |
|---|---|---|
| `file` | WAV upload | unchanged |
| `window_size` | power of 2, 4096 to 32768 | unchanged |
| `frame_rate` | number 1 to 60 | unchanged (now decides only the number of frames) |
| `window_spacing` | number greater than 0, default one frame period; `400` if not a number | **removed**: not declared; if sent it is ignored |
| `smoothing` | number 0.0 to 0.8, default 0; `400` if wrong or empty | **removed**: ignored |
| `smoothing_window` | whole number 1 to 20, default 1; `400` if wrong or empty | **removed**: ignored |
| all other fields | | unchanged |

**Ignored means ignored** (FR-012): a request that sends `smoothing=banana`, `smoothing_window=99` or `window_spacing=-1` gets the same answer (status 200 and the same frames) as one that
leaves them out. They are not echoed in the answer.

## Analysis the job makes (not a field)

- Step between buffers: `sample_rate * 60 / 1000` samples, whatever `frame_rate` and `window_size` are.
- Frames: `ceil(duration * frame_rate)`; each is the mean of the buffers that start in its period, else the latest earlier buffer.

## Answer (200, JSON)

| Key | Before | After |
|---|---|---|
| `smoothing` | echoed | **removed** |
| `smoothing_window` | echoed | **removed** |
| `window_spacing` | the spacing used | **removed** |
| `spacing_raised` | true when the step was raised to one sample | **removed** |
| `step_samples` | the step in samples | kept: always `sample_rate * 60 / 1000` |
| `window_count` | number of buffers | kept |
| `frame_rate`, `frame_count`, `window_size`, `sample_rate`, `duration_seconds`, and every other key | | unchanged |

## Errors (400)

| Cause | Message |
|---|---|
| more frames than `max_frames` | unchanged: "This would create N frames; the limit is M. Lower the frame rate or use a shorter file." |
| more buffers than `max_windows` | **changed**: "This would create N windows; the limit is M. Use a shorter file." (was "...Use a larger window spacing.") |
| a bad `window_spacing` ("The window spacing must be a number greater than 0.") | **gone** |
| a bad `smoothing` or `smoothing_window` | **gone** |

## Page contract (frontend)

- No control with the ids `window-spacing`, `smoothing` or `smoothing-window`; no group with the id `data-smoothing`; the settings object sent by the page has no `windowSpacing`,
  `smoothing` or `smoothingWindow`.
- The list of settings of a finished job shows no Smoothing, Smoothing window or Window spacing line and no "raised to one sample" notice; the Frame rate, Window size and Gaussian
  smoothing (Contour only) lines stay.
