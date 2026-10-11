# Quickstart: Colormap Colors

Validation guide for [spec.md](spec.md). The mapping is in [data-model.md](data-model.md) and the interface in [contracts/colormap-api.md](contracts/colormap-api.md).

## Prerequisites

`pip install -r requirements-dev.txt` in `backend/` with the venv active (this now installs matplotlib), and `npm install` in `frontend/`.

## 1. Automated checks

```
cd backend
pytest -v

cd ..\frontend
npm test
npm run typecheck
npm run build
```

Expected: everything passes. New and rewritten coverage includes: the lookup tables equal to matplotlib's own for every offered name; the strength-to-color mapping on hand-worked values; the strongest note at the last color and no strength at the first; the same strength giving the same color whatever the other notes are; a steady tone giving a steady color; the threshold giving exactly black for every colormap; both image types giving the same tile middles; the `colormap` field (valid, missing, every refused kind) and its response; removed fields accepted and ignored; the removed controls gone from the page and the Colormap dropdown present.

## 2. A test file with a steady tone

Make a 4-second mono WAV at 44.1 kHz with a steady 440 Hz tone from 1 s to 3 s and a quieter 660 Hz tone throughout:

```
import numpy as np
from scipy.io import wavfile
t = np.arange(44100 * 4) / 44100
tone = np.where((t >= 1) & (t < 3), 0.7 * np.sin(2 * np.pi * 440 * t), 0.0) + 0.15 * np.sin(2 * np.pi * 660 * t)
wavfile.write("steady.wav", 44100, tone.astype(np.float32))
```

## 3. Run the application

```
cd backend
uvicorn app.main:app --reload       # http://localhost:8000

cd frontend
npm run dev                         # http://localhost:5173
```

## 4. Check each story

**Story 1: colors from one colormap**

1. Choose `steady.wav` and create frames with the Colormap Hot (the start). While the 440 Hz tone sounds, its tile is higher on the scale (yellower or whiter) than the 660 Hz tile (redder), and both stay the same color from frame to frame while they sound. Quiet tiles are dark. (The note analysis reads one frequency bin per note, so the exact colors depend on how close each tone is to the middle of its bin; the order and the steadiness are what to look for.)
2. Play the animation: it no longer pulses with the loudness, and it does not flash hues when other notes come and go.
3. Choose Summer, Autumn and Cool in turn and create frames: the same tiles are brighter or dimmer in the same order, in each scale's colors (green to yellow, red to yellow, cyan to magenta).
4. To read exact values, download a frame (`/api/jobs/<job_id>/frames/<n>`) and compare a tile's pixel with matplotlib's table (`matplotlib.colormaps["hot"](np.arange(256), bytes=True)`): it is one entry of the table.
5. A silent file gives every tile the colormap's first color (a very dark red for Hot), also with a Threshold above 0.

**Story 2: the page**

1. The settings column has a Colormap dropdown with Summer, Autumn, Hot and Cool, starting at Hot, with an info button. There are no Brightness, Saturation, Hue steps, Saturation steps or Brightness steps controls.
2. While frames are being created the dropdown is disabled. After frames are created the summary shows "Colormap: Hot" and none of the removed settings.
3. Refused requests: with curl (or the API docs at `/docs`) send `colormap=viridis`, `colormap=Hot`, `colormap=hot_r`, `colormap=` (empty): each returns 400 with "The colormap must be one of summer, autumn, hot, cool." Leaving the field out is accepted (hot). A request that still sends `brightness=3`, `energy=2` and `hue_step=90` succeeds and gives the same frames as one without them.

**Story 3: with the other settings**

1. Set Smoothing 0.5 with Smoothing window 3, Threshold 5 and Image type Blended tiles with the Cool colormap: tiles whose note is below 5% of the loudest are black in the middle, the others have Cool colors in the middle, and the edges fade. Choose Tiles with the same settings: the tile middles are the same colors.
2. Frame count, timing and picture size are as before, and the frame player plays both image types.

## 5. Performance

Create frames from a 60 s file as Tiles with the Hot colormap. It takes no longer than before this feature (the energy measure and the hue computation are gone).
