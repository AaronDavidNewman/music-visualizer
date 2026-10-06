# Quickstart: Audio Upload and Frame Visualization UI

Validation guide for [spec.md](spec.md). Interface details are in [contracts/http-api.md](contracts/http-api.md) and [data-model.md](data-model.md).

## Prerequisites

```
cd backend
.venv\Scripts\activate
pip install -r requirements-dev.txt

cd ..\frontend
npm install
```

## 1. Automated checks

```
cd backend
pytest -v                      # includes test_frame_rendering.py and test_jobs_api.py

cd ..\frontend
npm test                       # vitest: validation and playback helpers
npm run typecheck
npm run build
```

Expected: everything passes.

## 2. Run the application

Two terminals:

```
cd backend
uvicorn app.main:app --reload       # http://localhost:8000

cd frontend
npm run dev                         # http://localhost:5173
```

Open http://localhost:5173.

## 3. Walk through the user stories

1. **Submit (Story 1)**: Choose `backend/audio/fotr-intro1-echo.wav`. Leave window size 4096 and frame rate 30, then submit. Expected: a busy indicator, then the first frame (a 12 × 7 grid of gray tiles, 252 × 168 pixels, since feature 005), a summary with duration about 340.8 s, sample rate 44100, and 10,224 frames.
2. **Silent and steady-note files**: Submit a silent WAV, then a one-note WAV. Expected: all squares black for silence. One clearly brightest square for the single note.
3. **Animation (Story 2)**: Press play. Expected: frames advance at about 30 per second, the time display counts up, and playback stops at the last frame. Turn looping on and check that it restarts. Drag the slider and check the matching frame and time show.
4. **Errors (Story 3)**:
   - Submit a text file renamed `.wav`: a message that it could not be read as WAV audio.
   - Enter window size 0 or frame rate 100: the field shows its range and Submit is blocked.
   - Try a window size outside the dropdown, for example with curl and `-F window_size=2048`: expect a 400 with the "power of 2" message.
   - Submit with no file chosen: Submit is blocked.
5. **Where files go**: With the server running, open the system temp folder, then `music-visualizer`. Expected: separate `audio` and `frames` folders, each with one folder named by the job id. `audio` holds `audio.wav`. `frames` holds `frame_000000.png` and up.

## 4. Check the timing (SC-002)

Submit the sample file (about 340 s, so 10,224 frames at 30 fps) and note the time from pressing Submit to the first frame. SC-002 is stated for a 3-minute file (5,400 frames at 30 fps) and 60 seconds, so this file, with about twice as many frames, should finish in roughly 2 minutes or less. The same measurement can be taken without a browser with `curl -w "%{time_total}\n" -F file=@backend/audio/fotr-intro1-echo.wav -F window_size=4096 -F frame_rate=30 http://localhost:8000/api/jobs -o NUL`.
