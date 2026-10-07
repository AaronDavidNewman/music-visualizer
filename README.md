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

**Layout** (since feature 008): the page has two columns. The left column holds the audio file chooser at the top, then the progress and error messages and the result: the frame preview with its playback controls (play/pause, loop, position slider), followed by the result summary. The right column holds the settings and the *Create frames* button, so new settings can be added there without moving the preview. Window size, frame rate and window spacing share one row. Each setting's explanation sits behind a small info (*i*) button that opens a popover (Escape or a click elsewhere closes it); validation errors and the below-minimum spacing notice stay visible under their field. Below 960 px wide the columns stack, with the chooser and preview first and the settings after. The components are `FilePicker.vue`, `SettingsForm.vue` and `InfoPopover.vue` in `frontend/src/components/`, and the text of the explanations is in `frontend/src/utilities/help.ts`.

Open the frontend, choose a `.wav`, pick the window size from the dropdown (a power of 2: 4096, 8192, 16384 or 32768; default 4096), set the frame rate (1–60, default 30), and press *Create frames*. The server reads the sample rate from the file, runs the note analysis, averages the windows within each frame period, and writes one color PNG per frame (an indexed-colour file that decodes to exact RGB values): a 12 × 7 grid of 21 × 24 pixel tiles (252 × 168, exactly 3:2) with one row per octave and one column per note name, so the tile directly below a note is the same note an octave higher (double the frequency). The lowest note (55 Hz) is the top-left tile, and only the first 84 notes are drawn (up to about 6645 Hz); the four highest of the 88 analyzed notes are left out of the picture but still count when the brightness is scaled. Brightness is set from each value relative to the loudest value in the file, then brightened with the brightness-th root (`255 * (level / 255) ** (1 / brightness)`) so quiet notes are visible. The page then plays the frames as an animation (play/pause, loop, position slider).

- `POST /api/jobs` (multipart: `file`, `window_size`, `frame_rate`) creates the frames. `GET /api/jobs/{job_id}/frames/{index}` returns one PNG. Errors are `{"detail": "..."}`.
- Uploaded audio goes to `<system temp>/music-visualizer/audio/<job_id>/audio.wav` and frames to `<system temp>/music-visualizer/frames/<job_id>/`. Override with `MV_AUDIO_TEMP_DIR` and `MV_FRAMES_TEMP_DIR`. Old submissions are not cleaned up automatically.
- Limits are settings in `backend/app/config.py` and can be overridden with `MV_` environment variables: 200 MB upload (`MV_MAX_AUDIO_BYTES`) and 30,000 frames (`MV_MAX_FRAMES`).
- **Window spacing** sets how far apart windows start, as a multiple of the window size: with a window of 8192 and a spacing of 0.25, windows start at samples 0, 2048, 4096 and so on. Below 1 the windows overlap; 1 is consecutive windows; above 1 there are gaps. The field defaults to one frame period in samples divided by the window size (rounded down to 6 decimals), so each frame gets its own window. It is recalculated whenever the window size, frame rate or file changes (replacing anything typed), using the chosen file's sample rate read from its header, or 44.1 kHz before a file is chosen. A spacing that would give a step under one sample is raised to exactly one sample and the page says so. In the API it is the optional `window_spacing` field (omitted means the default), and the response adds `window_spacing`, `step_samples`, `window_count` and `spacing_raised`.
- **Color** (since feature 007, always on): each tile is drawn as an HSV color. Its *value* is the tile's gray level described below (255 = 100%), its *saturation* is fixed at 50%, and its *hue* starts at 180° (cyan) and is moved by the final gray levels of related notes, whose brightness is **added up, not averaged**, on a 0 to 1 scale: the notes `n+4`, `n+5` and `n+7` pull the hue down (toward green, yellow, red) and the notes `n+3`, `n+6`, `n+8` and `n+11` push it up (toward blue, violet, red), so `hue° = 180 + 180 × (up sum − down sum)`, clipped to 0°–360° (both ends are red). The two lists are the constants `RELATED_DOWN` and `RELATED_UP` in `backend/app/services/frame_rendering.py` and can differ in length. Notes outside the 88-note series add nothing, and the four undrawn notes (84 to 87) still count as partners. Because the brightness is added, one partner at full brightness is already enough to reach red, while dim partners shift the hue only part of the way, so most tiles are not clipped. Examples for a full-brightness tile: nothing related lit gives (128, 255, 255), only `n+4` lit at full brightness gives hue 0° and (255, 128, 128), the same note at half brightness gives hue about 89.6° and (192, 255, 128), and an `n+3` note at half brightness gives hue about 270.4° and (192, 128, 255). Raising the brightness setting makes quiet partners count for more, so more color shows. A tile's brightest color channel equals its gray level and its darkest is about half of it, so colors are pastel and a black tile stays black. A single steady note is a cyan tile; color shows when related notes sound together. The conversion uses Python's `colorsys`. There is no gray-scale option and no saturation setting yet, and images from earlier submissions stay gray.
- **Brightness** is a whole number from 2 to 100 (default 2, the square root, which is how the images looked before this setting existed). It is the root applied to each gray level: a higher value lifts quiet notes more but shows less contrast (at 100 almost everything that is not silent is near white). Black stays black and the loudest value stays white at every setting. Changing it means submitting again. In the API it is the optional `brightness` field (leave it out for 2; an empty or out-of-range value is refused with a 400), and the response adds `brightness`.
- **Smoothing** is a slider from 0.00 to 0.80 (steps of 0.01, default 0) that makes each note a running average over the animation frames: for every frame after the first, `new = s * previous smoothed value + (1 - s) * this frame's value`, per note and using only that note's own history. The first frame is left as it is, and 0 changes nothing. Higher values calm flicker and make notes fade more slowly (at 0.5 a note that stops falls below 10% of its value after 4 frames, at 0.8 after 11), and short bursts look dimmer because they are spread over several frames. It is applied to the note values before they are scaled to gray levels, so brightness is scaled against the loudest smoothed value. Since the tiles are colored, the same smoothing is also applied to each tile's hue over the frames (`new hue = s * previous smoothed hue + (1 - s) * this frame's hue`, the first frame unchanged, the hue treated as a plain 0°–360° number), so colors change gradually too; on the sample file this cuts the frame-to-frame hue change of bright tiles to about 40% of the values-only-smoothed size at 0.8. It works per frame, so the same setting fades faster in real time at a higher frame rate. Changing it means submitting again. In the API it is the optional `smoothing` field (leave it out for 0; an empty value or one outside 0.0 to 0.8 is refused with a 400), and the response adds `smoothing`.
- A submission may create at most 60,000 windows (`MV_MAX_WINDOWS`); a spacing that would create more is refused before any analysis.
- Frontend tests: `cd frontend && npm test`.
