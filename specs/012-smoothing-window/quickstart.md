# Quickstart: Smoothing Window

Validation guide for [spec.md](spec.md). The formula is in [data-model.md](data-model.md) and the interface in [contracts/smoothing-window-api.md](contracts/smoothing-window-api.md).

## Prerequisites

Same as the earlier features (`pip install -r requirements-dev.txt` in `backend/` with the venv active, `npm install` in `frontend/`).

## 1. Automated checks

```
cd backend
pytest -v

cd ..\frontend
npm test
npm run typecheck
npm run build
```

Expected: everything passes. New and rewritten coverage includes the worked example (8, 4, 2 with `w = 2`, `s = 0.5` giving 8, 5.33, 4); the first frames of a file; an impulse that lasts exactly `w` frames then is exactly 0, for every window from 1 to 20; a constant value unchanged; `s = 0` identical for every window; smoothing that looks only backwards; the note values, hues and frame brightness smoothed with the same window and weight; rounding to levels and the threshold applied to the smoothed values; the `smoothing_window` field (valid, missing, every refused kind) and its response; and the rendered field.

## 2. A test file with a single short note

Make a 4-second mono WAV at 44.1 kHz with a 440 Hz tone that sounds from 2.0 s to 2.1 s (about three frames at 30 fps) and silence elsewhere, for example with numpy and scipy:

```
import numpy as np
from scipy.io import wavfile
t = np.arange(44100 * 4) / 44100
tone = np.where((t >= 2.0) & (t < 2.1), 0.8 * np.sin(2 * np.pi * 440 * t), 0.0)
wavfile.write("blip.wav", 44100, tone.astype(np.float32))
```

## 3. Run the application

```
cd backend
uvicorn app.main:app --reload       # http://localhost:8000

cd frontend
npm run dev                         # http://localhost:5173
```

## 4. Check each story

**Story 1: the window**

1. Choose `blip.wav`, leave Smoothing at 0 and the Smoothing window at 1. Create frames. Note the frames in which the tone's tile is visible (about three).
2. Set Smoothing to 0.5 and the window to 1 and create frames again. The tile now lasts about one frame longer than in step 1, weaker on that last frame, and is then gone.
3. Set the window to 5 and create frames again. The tile lasts about five frames longer than in step 1 and then disappears completely (it does not keep a faint trace, as the old smoothing did). The counts are approximate because the note analysis already spreads a short tone over a window of 4096 samples; the exact counts are checked by the automated tests.
4. Set Smoothing back to 0 with the window at 20: the frames are exactly those of step 1.

**Story 2: the field on the page**

1. The settings column has a "Smoothing window (frames)" field with the value 1 directly above the Smoothing slider, with an info button that opens an explanation.
2. Enter 0, 21, 2.5 or leave it empty: an error appears under the field and "Create frames" is unavailable.
3. While frames are being created the field is disabled.
4. After frames are created the summary shows "Smoothing window: n".
5. Refused requests: with curl (or the API docs at `/docs`) send `smoothing_window=0`, `smoothing_window=21`, `smoothing_window=2.5`, `smoothing_window=` (empty) and `smoothing_window=abc`; each returns 400 with "The smoothing window must be a whole number from 1 to 20." Leaving the field out is accepted (window 1).

**Story 3: with the other settings**

1. Set Smoothing 0.8, window 8, Threshold 10 and Saturation steps 20: a note that stops fades, turns black once its smoothed value is under 10% of the loudest, and every tile's saturation is one of the six levels.
2. Hues and the frame brightness are smoothed with the same window: a brightness change (a loud passage after a quiet one) takes several frames to arrive at the larger windows.

## 5. Performance

Create frames from a 60 s file with Smoothing 0 and then with window 20 and Smoothing 0.8. The second takes no more than 25% longer than the first (SC-008), and the first no longer than before this feature.
