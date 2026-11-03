# Quickstart: validating Frames to MP4

## Prerequisites

- ffmpeg and ffprobe on the PATH (`ffmpeg -version`), or `MV_FFMPEG_PATH` set.
- Backend: `cd backend && pip install -r requirements.txt -r requirements-dev.txt`. Frontend: `cd frontend && npm install`.

## Automated

```text
cd backend && python -m pytest tests/test_video.py tests/test_video_api.py
cd frontend && npx vitest run
```

The real-ffmpeg test in `test_video_api.py` is skipped when ffmpeg is not installed. Expected: everything passes, including the existing suites (nothing else changes).

## By hand

1. Start the backend (`uvicorn app.main:app` in `backend/`) and the frontend (`npm run dev` in `frontend/`).
2. Upload a short WAV, pick any image type, create the frames, and check that **Create video** appears under the player.
3. Click it. Expect a "working" status and a disabled button, then "Video saved to …\backend\output\<job_id>\video.mp4" and a **Download** link.
4. `ffprobe -v error -show_entries stream=codec_type,codec_name,r_frame_rate,duration -of default=nw=1 <that file>` — expect one stream, `codec_type=video`, `codec_name=h264`, the render's frame rate, and a duration of frames ÷ fps (within one frame). No `codec_type=audio`.
5. Play the file; the pictures match the page's player.
6. Click **Create video** again: `backend/output/<job_id>/` still holds only `video.mp4`.
7. Repeat for each image type (spec scenario 5).
8. Failure: set `MV_FFMPEG_PATH=nowhere`, restart the backend, click the button — expect the ffmpeg message and nothing in `backend/output`. Delete the render's frame directory and click — expect the "render again" message.
9. `git status` shows nothing from `backend/output/`.
