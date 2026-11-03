# Contract: Video API

Both endpoints sit under the existing `/api/jobs` prefix. `job_id` is the 32-character lowercase hex id returned by `POST /api/jobs`; anything else gives `404 {"detail": "Render not found."}`.

## POST /api/jobs/{job_id}/video

Makes (or remakes) the silent MP4 from the render's frames. No request body. Returns when the file is complete.

**200 OK**

```json
{
  "job_id": "0123456789abcdef0123456789abcdef",
  "file_name": "video.mp4",
  "path": "D:\\github\\music-visualizer\\backend\\output\\0123456789abcdef0123456789abcdef\\video.mp4",
  "size_bytes": 482113,
  "frame_count": 240,
  "frame_rate": 24,
  "duration_seconds": 10.0,
  "url": "/api/jobs/0123456789abcdef0123456789abcdef/video"
}
```

**Errors** (all `{"detail": "<message fit to show the user>"}`):

| Status | When | Message |
|---|---|---|
| 404 | invalid id, no frames, or no `render.json` | "The frames of this render are no longer available. Render again." |
| 409 | a conversion for this job is running | "A video is already being made for this render." |
| 503 | ffmpeg cannot be started | "ffmpeg was not found. Install it, or set MV_FFMPEG_PATH to its location." |
| 500 | ffmpeg exited with an error | "Something went wrong while making the video." (ffmpeg's stderr goes to the server log) |
| 504 | ffmpeg ran past `video_timeout_seconds` | "Making the video took too long and was stopped." |

After any error, `output_dir/<job_id>/` holds no `video.tmp.mp4`; a previous good `video.mp4` is kept.

## GET /api/jobs/{job_id}/video

Sends the saved file: `200`, `Content-Type: video/mp4`, `Content-Disposition: attachment; filename="video.mp4"`. `404 {"detail": "No video has been made for this render."}` if there is none.

## Files written

- `frames_temp_dir/<job_id>/render.json` by `POST /api/jobs`: `{"frame_rate": <number>}`. The `POST /api/jobs` request and response are otherwise unchanged.
- `output_dir/<job_id>/video.mp4` by `POST /api/jobs/{job_id}/video`.

## Settings (environment, prefix `MV_`)

| Name | Default | Meaning |
|---|---|---|
| `MV_OUTPUT_DIR` | `backend/output` | where the video directories are made |
| `MV_FFMPEG_PATH` | `ffmpeg` | the ffmpeg executable (name on the PATH or full path) |
| `MV_VIDEO_TIMEOUT_SECONDS` | `600` | longest a conversion may run |

## UI contract (`VideoExport`)

Shown under the player whenever a result is shown. Button **Create video**; while working the button is disabled and a status line says the video is being made; when done it shows "Video saved to <path>" and a **Download** link to `url`; on error it shows the message in an alert. A new result resets it to idle.
