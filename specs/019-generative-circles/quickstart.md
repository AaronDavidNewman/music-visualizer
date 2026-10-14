# Quickstart: Generative Circles

Validation guide for [spec.md](spec.md). The values are in [data-model.md](data-model.md) and the interface in [contracts/circles-api.md](contracts/circles-api.md).

## Prerequisites

`pip install -r requirements-dev.txt` in `backend/` with the venv active and `npm install` in `frontend/`. The colormap lists of `backend/app/services/colormaps.py` and `frontend/src/utilities/validation.ts` must be consistent (each default must be in its own list, and the two lists must match), or the whole backend suite fails at import; this is the user's own edit and not part of this feature.

## 1. Automated checks

```
cd backend
pytest -v

cd ..\frontend
npm test
npm run typecheck
npm run build
```

Expected: everything passes. New coverage includes: the move of every note (angle and units) against the user's examples and against an independent computation from the frequency; the placement of the circles frame by frame (the example F5 and F3 included); the choice of the strongest notes and ties; the color of every circle; the circular memory (eviction, the count drawn); the three settings and their refusals; the image type list and the response; the page controls, the conditional settings and the disabled settings. The tests use whatever colormap list `colormaps.py` has and never state a number of contour levels.

## 2. The other image types are unchanged

Create frames of the 4-second test file with the image types tiles, blended and contour: the default tiles output hashes to `28e608864383e33d2b3a195e962d2fd0c02005cd64137fcf4c45ad7e7375d780`, blended (width 15) to `187ac9894949dfe4f12435e3da983262d02109dd889876c6e786728059682db0`, the contour default to `fbf26807c2045329bff9bfb41bdfb7a4bef9aa1aaddfc1be60a6f85f931aba04`, and the job with colormap `viridis`, smoothing 0.4, window 3 and threshold 3 to `ae8869d0af777836941edf3998474bef0a19b7e254f60499b5f5722a65c2c3ce` (`baseline.py` in the session's scratchpad; these use the default colormap, so the lists must be consistent).

## 3. Circles from the API

```
curl -F file=@tones.wav -F window_size=4096 -F frame_rate=30 -F image_type=circles http://127.0.0.1:8000/api/jobs
```

Expected: 200 with `"image_type": "circles"`, `"circle_unit": 4`, `"circle_size": 25`, `"circle_memory": 300`, `"circle_notes": 8`. Each frame is a 252 × 168 PNG, the colormap's middle color with colored circles that fade with their age; a steady note walks a path (one new circle a frame) and the earlier circles stay as a trail, until the memory is full and the oldest drop out. Try `circle_unit=10`, `circle_memory=100`, `circle_notes=12`.

Refusals: `circle_unit=0`, `11`, `circle_memory=99`, `501`, `circle_notes=4`, `13`, `2.5`, `abc` and an empty value each return 400 with the matching message; `image_type=Circles` returns 400 with the four-name message.

## 4. With the other settings

Create circle frames with smoothing 0.5, window 3, each colormap on the page and, to see that they are ignored, `interpolate=5`, `resolution=3`, `note_count=24`, `threshold=5`: the colors follow the colormap, the frames are the same with and without the ignored settings, a silent file is the plain middle color of the colormap.

## 5. Time

A 10-second file at 30 frames per second (300 frames) as circles with 12 circles per frame, a memory of 500 and a unit of 10 finishes within a minute (the prototype measured about 2 ms a frame, a second or two in all).

## 6. The page

Open the frontend: choose Circles. Unit, Size, Memory and Circles per frame appear with their readouts, and Interpolate, Resolution, Notes, Threshold and Blend width are disabled. Open the info buttons. Create frames: the player shows the circles and the summary says "Image type: Circles" with the four values. Choose Tiles again: the three settings disappear and the others are enabled.

## 7. Look at it

Not covered by automated tests: step 6 in a real browser, and whether the circles look good, which is for the user. The implementation sends strips of frames for the test file and for a melody.
