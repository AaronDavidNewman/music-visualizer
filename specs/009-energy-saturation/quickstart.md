# Quickstart: Energy Saturation

Validation guide for [spec.md](spec.md). The definition and formulas are in [data-model.md](data-model.md) and the interface in [contracts/energy-api.md](contracts/energy-api.md).

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

Expected: everything passes. New coverage includes the internal window at 44.1, 48, 22.05 and 11.025 kHz; the hand-computed energies 0.5, 0.25 and 0; a constant level; mono; one loud channel; the leftover and short final frame rules; the same audio at 8, 16, 24-bit and float giving the same saturation; the same sound at two sample rates agreeing within 5 percentage points; the saturation rule for roots 1 to 8; a silent file; smoothing; `tile_colors` with a given saturation; a three-frame file through the API; the validation of the `energy` field; and determinism.

## 2. A test file with known energy

Make a 3-second mono WAV at 44.1 kHz with three 1-second stretches: uniform noise of amplitude 0.8, uniform noise of amplitude 0.2 (a quarter of the first, since the spread is proportional to the amplitude), and silence. For example, with numpy and scipy:

```
import numpy as np
from scipy.io import wavfile
rng = np.random.default_rng(1)
loud = rng.uniform(-0.8, 0.8, 44100)
soft = rng.uniform(-0.2, 0.2, 44100)
wavfile.write("energy-test.wav", 44100, np.concatenate([loud, soft, np.zeros(44100)]).astype(np.float32))
```

## 3. Run the application

```
cd backend
uvicorn app.main:app --reload       # http://localhost:8000

cd frontend
npm run dev                         # http://localhost:5173
```

Open http://localhost:5173, choose `energy-test.wav` and create frames with the defaults (frame rate 30).

## 4. Check each story

**Story 1: saturation follows energy**

1. Frame 15 (loud) shows vividly colored tiles: its most prominent tile has a darkest channel near 0 (saturation 100%).
2. Frame 45 (a quarter as loud) is paler: saturation about 25%, so its darkest channel is about three quarters of its brightest one.
3. Frame 75 (silence) is all black.
4. To read exact values, download a frame (`/api/jobs/<job_id>/frames/15`) and convert a tile's pixel to HSV; saturation is `(max − min) / max`.
5. Smoothing: raise Smoothing to 0.5 and create frames again. Saturation changes gradually around the loud-to-soft and soft-to-silent boundaries instead of in one step.

**Story 2: the Energy setting**

1. The settings column has an Energy field next to Brightness with the value 1. Its info button opens a popover that explains it.
2. Set Energy to 2 and create frames: frame 45 now has saturation about 50%. At 8, about 84%. Frames 15 (100%) and 75 (black) do not change. The summary shows "Energy: 2" (and so on).
3. Enter 0, 9, 2.5 or clear the field: an error appears under it, "Create frames" is disabled, and nothing is sent.
4. Through the API: `curl -F file=@energy-test.wav -F energy=9 http://localhost:8000/api/jobs` returns 400 with the message. Without the `energy` field the response contains `"energy": 1`.

**Story 3: sample rates and channels**

1. Create the same sound at 22,050 Hz (resample, or generate it at that rate) and confirm the saturation of matching frames agrees with the 44.1 kHz file to within 5 percentage points.
2. A file whose last frame is only a few samples long creates frames without an error.

## 5. Nothing else changed

Create frames with the same file and settings on this branch and on `main`: the frame count, summary text (apart from the new Energy item), tile positions, and each tile's hue and brightest channel are identical; only the saturation differs. Time to create the frames is within 25% of `main`.
