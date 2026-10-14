# Quickstart: Interpolated Frames

> **Amendment 2026-10-13**: the interpolation function was removed after the user saw the rendered frames ("The others don't really work"). Only `blend` is made: there is no function dropdown, no `interpolate_function` field and no response key for it, and no `soft_light`, `hard_light`, `overlay`, `screen` or `subtract` code. A request that still sends `interpolate_function` is accepted and the field is ignored. [spec.md](spec.md), [data-model.md](data-model.md) and [contracts/interpolate-api.md](contracts/interpolate-api.md) describe the result; this document is kept as it was written, so the passages about the five other functions, option B and the function dropdown describe the first version.

Validation guide for [spec.md](spec.md). The values are in [data-model.md](data-model.md) and the interface in [contracts/interpolate-api.md](contracts/interpolate-api.md).

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

Expected: everything passes. The new coverage includes: the checks and the drawn-frame numbering (1, n + 1, 2n + 1 and the last); the in-between frames against Pillow's own functions and, for blend, against a plain weighted mix; the drawn frames byte-identical to interpolate 1 for every image type and function; the count of pictures drawn; the shorter last gap; the `interpolate` and `interpolate_function` fields, their refusals and the response; the controls, readouts and help on the page. The tests use whatever colormap list `colormaps.py` has and never state a number of contour levels.

## 2. The original output is unchanged (interpolate 1)

Create frames of the 4-second test file with no `interpolate` and with `interpolate=1`, once for each of tiles, blended and contour. The default tiles output hashes to `28e608864383e33d2b3a195e962d2fd0c02005cd64137fcf4c45ad7e7375d780`, blended (width 15) to `187ac9894949dfe4f12435e3da983262d02109dd889876c6e786728059682db0`, the contour default to `fbf26807c2045329bff9bfb41bdfb7a4bef9aa1aaddfc1be60a6f85f931aba04`, and the job with colormap `viridis`, smoothing 0.4, window 3 and threshold 3 to `ae8869d0af777836941edf3998474bef0a19b7e254f60499b5f5722a65c2c3ce` (`baseline.py` in the session's scratchpad).

## 3. Interpolated frames from the API

```
curl -F file=@tones.wav -F window_size=4096 -F frame_rate=25 -F interpolate=5 -F image_type=contour http://127.0.0.1:8000/api/jobs
```

Expected: 200 with `"interpolate": 5` and `"interpolate_function": "blend"`; the same number of frames as without `interpolate`. Frames 1, 6, 11 and so on (files `frame_000000.png`, `frame_000005.png` and so on) and the last frame are the contour pictures, identical to those of a job without `interpolate`; the four frames between each pair are gradual mixes of their two neighbors (frame 2 is four fifths of frame 1 and one fifth of frame 6). Repeat with `interpolate_function=screen` (the in-between frames are brighter) and `subtract` (darker).

Refusals: `interpolate=0`, `6`, `2.5`, `abc` and an empty value each return 400 with `The interpolate value must be a whole number from 1 to 5.`; `interpolate_function=Blend`, `multiply` and an empty value each return 400 with the function message.

## 4. With the other settings

Create frames with interpolate 5, smoothing 0.5, window 3, resolution 3, notes 24, a threshold of 5 and each colormap on the page, for each image type: the drawn frames are those of interpolate 1 with the same settings and the others are blends of them; a silent file gives flat frames.

## 5. Time

A 10-second file at 30 frames per second (300 frames) as contour at interpolate 5 takes at most half the time of the same job at interpolate 1 (the prototype measured about 3 to 5 times less for the picture work); Tiles and Blended tiles jobs take no more than 25% longer at any interpolate value (they break even: drawing one of those frames costs about as much as blending one).

## 6. The page

Open the frontend: Interpolate is at 1 ("1 (every frame drawn)") and the Interpolation function dropdown is at Blend and disabled. Move Interpolate to 5: the readout shows "5 (one frame in 5 drawn)" and the dropdown is enabled with the six choices. Open the info buttons. Create frames: the animation plays at the same speed and the summary says "Interpolate: 5 (Blend)". Both controls are disabled while the job runs.

## 7. Look at it

Not covered by automated tests: step 6 in a real browser, and whether the blended animation looks good. The implementation sends a strip of consecutive frames with each function for you to judge.
