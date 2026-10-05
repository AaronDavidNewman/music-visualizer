# Data Model: Audio Upload and Frame Visualization UI

## Settings (server configuration)

| Field | Default | Meaning |
|-------|---------|---------|
| `audio_temp_dir` | `<system temp>/music-visualizer/audio` | Root for uploaded audio |
| `frames_temp_dir` | `<system temp>/music-visualizer/frames` | Root for frame images. Always a different directory from `audio_temp_dir`. |
| `max_audio_bytes` | 200 MB | Largest accepted upload |
| `max_frames` | 30,000 | Most frames one submission may produce |
| `min_window_size` / `max_window_size` | 4096 / 32768 | Allowed window sizes are the powers of 2 in this range (4096, 8192, 16384, 32768) |
| `min_frame_rate` / `max_frame_rate` | 1 / 60 | Allowed frame rate range |

## Submission request

| Field | Type | Rules |
|-------|------|-------|
| `file` | uploaded file | Required. Must be a readable mono or stereo WAV with at least one sample. At most `max_audio_bytes`. |
| `window_size` | text parsed as integer | Required. One of 4096, 8192, 16384, 32768. |
| `frame_rate` | text parsed as number | Required. Greater than or equal to 1 and at most 60. |

## Submission (job) result

| Field | Type | Meaning |
|-------|------|---------|
| `job_id` | 32 lowercase hex characters | Names the submission's folders and appears in frame URLs |
| `file_name` | string | Original file name, base name only, for display |
| `sample_rate` | integer | Taken from the WAV header |
| `duration_seconds` | number | `sample_count / sample_rate` |
| `window_size` | integer | As requested |
| `frame_rate` | number | As requested |
| `frame_count` | integer | `ceil(duration_seconds * frame_rate)`, at least 1 |
| `frame_url_template` | string | `/api/jobs/<job_id>/frames/{index}` with `{index}` replaced by 0-based frame number |

A submission is created whole or not at all. If any step fails, both of its folders are deleted and an error is returned, so there is no stored "failed" state.

## Uploaded Audio

`<audio_temp_dir>/<job_id>/audio.wav`: the uploaded bytes. The original file name is not used.

## Frame

Derived, not stored. Frame *f* (0-based) has start time `f / frame_rate` seconds and 88 values, the mean of the note values of the windows starting in `[f / frame_rate, (f + 1) / frame_rate)`. If no window starts in that period, it takes the values of the window covering the start of the period.

## Frame Image

`<frames_temp_dir>/<job_id>/frame_<f, 6 digits>.png`: 8-bit grayscale, 220 × 160 pixels, an 11-column by 8-row grid of 20 × 20 squares. Note *n* occupies row `n // 11` and column `n % 11`. Square brightness is `round(255 * value / file_max)`, where `file_max` is the largest note value in any frame, and 0 if `file_max` is 0.

## Client state (frontend)

| State | Meaning | Allowed next states |
|-------|---------|---------------------|
| `idle` | Form shown, no results | `busy` |
| `busy` | Request in flight, form disabled | `done`, `error` |
| `done` | Result shown in the player, form still usable | `busy` |
| `error` | Message shown, form still filled in | `busy` |

The form's field values are kept in every state. A new submission replaces the displayed result only when it succeeds.

## Changes to feature 001 types

`AnalysisResult` gains `sample_count: int`, the number of audio samples per channel in the file. `read_wav` and `analyze_channels` become public. Existing behavior and tests of `analyze_wav` are unchanged.
