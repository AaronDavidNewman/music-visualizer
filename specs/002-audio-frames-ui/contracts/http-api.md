# Contract: HTTP API

Base path: `/api`. All errors are JSON: `{"detail": "<message the UI can show as is>"}`.

## `POST /api/jobs`

Uploads an audio file and creates its frames.

**Request**: `multipart/form-data`

| Field | Type | Notes |
|-------|------|-------|
| `file` | file | The `.wav` audio |
| `window_size` | text | One of 4096, 8192, 16384, 32768 |
| `frame_rate` | text | Number, 1 to 60 |

**Success**: `200 OK`

```json
{
  "job_id": "3f2a9c0e5b7d4e18a6c1d2e3f4a5b6c7",
  "file_name": "song.wav",
  "sample_rate": 44100,
  "duration_seconds": 340.8,
  "window_size": 4096,
  "frame_rate": 30,
  "frame_count": 10224,
  "frame_url_template": "/api/jobs/3f2a9c0e5b7d4e18a6c1d2e3f4a5b6c7/frames/{index}"
}
```

**Errors**

| Status | When | Example `detail` |
|--------|------|------------------|
| 400 | `window_size` or `frame_rate` missing, not a number, or out of range | "The window size must be a power of 2 from 4096 to 32768 (4096, 8192, 16384, 32768)." |
| 400 | File is missing, not a readable WAV, or has more than two channels | "Could not read 'x.wav' as a WAV file: ..." |
| 400 | File has no audio samples | "The file contains no audio." |
| 400 | The request would make more than 30,000 frames | "This would create 54,000 frames; the limit is 30,000. Lower the frame rate or use a shorter file." |
| 400 | The analysis rejects the settings | The message from the note analysis, such as "The sample rate 8000 is too low for a window size of 4096: ..." |
| 413 | Upload larger than 200 MB | "The file is larger than the 200 MB limit." |
| 500 | Unexpected failure | "Something went wrong while creating the frames." |

On any error, nothing from the submission remains stored.

**Guarantees**: The audio is stored under the audio temp root and the frames under the frames temp root, which are different directories, each in a folder named by `job_id`. The same file and settings always give the same images.

## `GET /api/jobs/{job_id}/frames/{index}`

Returns one frame image.

| Part | Rule |
|------|------|
| `job_id` | 32 lowercase hex characters, otherwise 404 |
| `index` | Non-negative integer, otherwise 404 |

**Success**: `200 OK`, `Content-Type: image/png`, with a long-lived `Cache-Control` header. The image is 220 × 160 grayscale.
**Errors**: `404` with `{"detail": "Frame not found."}` if the job or frame does not exist.

## Image content contract

- 11 columns by 8 rows of 20 × 20 pixel squares, no margins or gaps.
- Note index *n* (0 = lowest) is at row `n // 11`, column `n % 11`, so index 0 is top-left.
- Square gray level is `round(255 * value / file_max)`.

## UI contract (what the user can do and see)

| Element | Behavior |
|---------|----------|
| File chooser | Accepts `.wav`. Shows the chosen name and size. |
| Window size dropdown | Offers 4096, 8192, 16384 and 32768, default 4096. |
| Frame rate field | Default 30. Shows the 1–60 range and blocks submission when invalid. |
| Submit button | Disabled with no file, with invalid fields, or while a submission is running. |
| Busy indicator | Shown from submit until the response arrives. |
| Error message | Shows the server's `detail` or a connection failure message. The form keeps its values. |
| Results summary | File name, duration, sample rate, window size, frame rate, frame count. |
| Player | Frame image, position slider over all frames, current time in seconds, play/pause, loop toggle. Playback advances at the chosen frame rate and stops at the last frame unless looping. |
