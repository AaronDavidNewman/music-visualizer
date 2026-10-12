# Quickstart: Interpolated Resolution

Validation guide for [spec.md](spec.md). The values are in [data-model.md](data-model.md) and the interface in [contracts/resolution-api.md](contracts/resolution-api.md).

## Prerequisites

`pip install -r requirements-dev.txt` in `backend/` with the venv active and `npm install` in `frontend/`.

## 1. Automated checks

```
cd backend
pytest -v

cd ..\frontend
npm test
npm run typecheck
npm run build
```

Expected: everything passes. The new coverage includes: the interpolation equal to `np.interp` and its invariants for every resolution; the tile grid read back from the pictures (12 r × 7 r tiles, each tile's color the colormap's color for its interpolated value); both image types at every resolution; the Threshold on the drawn values; the contour drawn from the finer grid; the `resolution` field, its refusals and the response; the control, readout and help on the page. The tests use whatever colormap list `colormaps.py` has and never state a number of contour levels.

## 2. The original output is unchanged (resolution 1)

Create frames of the 4-second test file with no `resolution` and with `resolution=1`, once for each of tiles, blended and contour. The default tiles output hashes to `28e608864383e33d2b3a195e962d2fd0c02005cd64137fcf4c45ad7e7375d780`, blended (width 15) to `187ac9894949dfe4f12435e3da983262d02109dd889876c6e786728059682db0`, the contour default (after the user's change of 2026-10-12 to a per-frame color scale) to `fbf26807c2045329bff9bfb41bdfb7a4bef9aa1aaddfc1be60a6f85f931aba04`, and the job with colormap `viridis`, smoothing 0.4, window 3 and threshold 3 to `ae8869d0af777836941edf3998474bef0a19b7e254f60499b5f5722a65c2c3ce` (the scripts in the session's scratchpad; `baseline.py`).

## 3. A finer picture from the API

```
curl -F file=@tones.wav -F window_size=4096 -F frame_rate=30 -F resolution=3 http://127.0.0.1:8000/api/jobs
```

Expected: 200 with `"resolution": 3`; each frame is a 252 × 168 PNG made of 36 × 21 tiles (7 × 8 pixels each). Between two notes of very different strength, the tiles step gradually from one color to the other. Repeat with `image_type=blended` (the same grid, the tile edges softened over about one pixel at 5×) and `image_type=contour` (finer steps).

Refusals: `resolution=0`, `6`, `2.5`, `abc` and an empty value each return 400 with `The resolution must be a whole number from 1 to 5.`.

## 4. With the other settings

Create frames at resolution 5 with smoothing 0.5, window 3, threshold 5 and each colormap on the page, for each image type: the hidden region has a finer edge (black tiles, or zeros in the contour), the colors are the colormap's with the same scale as at 1×, and a silent file is as flat as at 1×.

## 5. Time

A 10-second file at 30 frames per second (300 frames) at resolution 5 finishes well within one minute for every image type (the prototype measured about 3 s for the contour drawing and under 1 s for tiles).

## 6. The page

Open the frontend: the Resolution slider is at 1 ("1×"). Move it to 3: the readout shows "3× (36 × 21)". Open the info button: the text explains the interpolation. Create frames: the player shows the finer picture and the summary says "Resolution: 3× (36 × 21)". The slider is disabled while the job runs.

Not covered by automated tests: step 6 in a real browser, and judging whether the finer pictures look good, which is for the user.
