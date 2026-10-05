# Music Visualizer

- `backend/` — Python + FastAPI (file and image processing via Pillow)
- `frontend/` — TypeScript + Vue 3, bundled with Vite

## Backend

```
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows; use `source .venv/bin/activate` elsewhere
pip install -r requirements-dev.txt
uvicorn app.main:app --reload  # http://localhost:8000 (docs at /docs)
pytest
```

## Frontend

```
cd frontend
npm install
npm run dev                    # http://localhost:5173, proxies /api to :8000
npm run build
```

## Note analysis

`backend/app/services/note_analysis.py` reduces stereo audio to 88 musical-note values per window (55 Hz, one semitone apart). Left and right spectra are averaged, and each note reads the spectrum at `int((window_size / sample_rate) * freq)`.

```python
from app.services.note_analysis import NoteBinAnalyzer, analyze_wav

result = analyze_wav("audio/song.wav", sample_rate=44100, window_size=2048)
result.frames                 # shape (windows, 88), lowest note first
result.window_start_times()   # seconds

analyzer = NoteBinAnalyzer(44100, 2048)
values = analyzer.analyze(left_buffer, right_buffer)   # shape (88,)
```

Notes: neighbouring low notes share a spectrum position at small window sizes (about 28 of 88 at 2048 samples and 44.1 kHz), so use a larger window if you need them separated. The sample rate must be at least about 16.75 kHz. Put sample files in `backend/audio/` (git-ignored).

## Audio frames UI

Open the frontend, choose a `.wav`, pick the window size from the dropdown (a power of 2: 4096, 8192, 16384 or 32768; default 4096), set the frame rate (1–60, default 30), and press *Create frames*. The server reads the sample rate from the file, runs the note analysis, averages the windows within each frame period, and writes one grayscale PNG per frame: an 11 × 8 grid of squares, one per note (lowest note top-left), with brightness linear against the loudest value in the file. The page then plays the frames as an animation (play/pause, loop, position slider).

- `POST /api/jobs` (multipart: `file`, `window_size`, `frame_rate`) creates the frames. `GET /api/jobs/{job_id}/frames/{index}` returns one PNG. Errors are `{"detail": "..."}`.
- Uploaded audio goes to `<system temp>/music-visualizer/audio/<job_id>/audio.wav` and frames to `<system temp>/music-visualizer/frames/<job_id>/`. Override with `MV_AUDIO_TEMP_DIR` and `MV_FRAMES_TEMP_DIR`. Old submissions are not cleaned up automatically.
- Limits are settings in `backend/app/config.py` and can be overridden with `MV_` environment variables: 200 MB upload (`MV_MAX_AUDIO_BYTES`) and 30,000 frames (`MV_MAX_FRAMES`).
- **Window spacing** sets how far apart windows start, as a multiple of the window size: with a window of 8192 and a spacing of 0.25, windows start at samples 0, 2048, 4096 and so on. Below 1 the windows overlap; 1 is consecutive windows; above 1 there are gaps. The field defaults to one frame period in samples divided by the window size (rounded down to 6 decimals), so each frame gets its own window. It is recalculated whenever the window size, frame rate or file changes (replacing anything typed), using the chosen file's sample rate read from its header, or 44.1 kHz before a file is chosen. A spacing that would give a step under one sample is raised to exactly one sample and the page says so. In the API it is the optional `window_spacing` field (omitted means the default), and the response adds `window_spacing`, `step_samples`, `window_count` and `spacing_raised`.
- A submission may create at most 60,000 windows (`MV_MAX_WINDOWS`); a spacing that would create more is refused before any analysis.
- Frontend tests: `cd frontend && npm test`.
