# Quickstart: Image Type (Blended Tiles)

Validation guide for [spec.md](spec.md). The weights and formulas are in [data-model.md](data-model.md) and the interface in [contracts/image-type-api.md](contracts/image-type-api.md).

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

Expected: everything passes. New coverage includes the blend against an independent per-pixel reference; exact tile colors outside the bands; the even mix at an edge; no overshoot; uniform and all-black frames unchanged; corners; the flat border; no wrapping between rows; every blend width from 10 to 25; `tiles` frames byte-identical to those made before this feature; the tile middles of blended frames equal to the tiles frames for many other settings; the two API fields (valid, missing, every refused kind) and their response; and the rendered controls.

## 2. Run the application

```
cd backend
uvicorn app.main:app --reload       # http://localhost:8000

cd frontend
npm run dev                         # http://localhost:5173
```

Use any music `.wav` with several notes sounding together; chords show the fades best.

## 3. Check each story

**Story 1: blended tiles**

1. Create frames with the Image type Tiles. They look as they did before this feature.
2. Choose Blended tiles (Blend width 25) and create frames again. The grid and the colors are the same, but where two tiles of different colors touch, the color fades from one to the other. The middle of each tile is still flat.
3. Look at a tile next to a dark one: it fades toward black at that edge. Look at the border of the picture: it does not fade.
4. To read exact values, download a frame (`/api/jobs/<job_id>/frames/<n>`) and compare pixels: the middle of a tile has exactly the tiles-picture color; the two pixels beside an edge average to the even mix of the two tiles' colors.
5. A silent file gives entirely black frames for both types.

**Story 2: the controls on the page**

1. The settings column has an Image type dropdown (Tiles selected) and a Blend width slider (25, disabled while Tiles is selected) with the readout "25% of a tile".
2. Choose Blended tiles: the slider becomes available. Move it to 10 and create frames: the fades are narrower (about 2 pixels either side); at 25 about 5 pixels either side.
3. Both info buttons open short explanations. While frames are being created both controls are disabled.
4. After frames are created the summary shows "Image type: Blended tiles" and "Blend width: n%"; for Tiles it shows "Image type: Tiles" only.
5. Refused requests: with curl (or the API docs at `/docs`) send `image_type=Blended`, `image_type=`, `image_type=gradient`, `blend_width=9`, `blend_width=26`, `blend_width=` (empty) and `blend_width=abc`; each returns 400 with the matching message. Leaving both fields out is accepted (tiles, 25).

**Story 3: with the other settings**

1. Set Saturation steps 20, Threshold 5, Smoothing 0.5 with Smoothing window 3, and Blended tiles: the middle of every tile has one of the allowed saturation levels, hidden notes' tiles are black in the middle, and the edges show the fades. Switch to Tiles with the same settings: the tile middles are the same colors.
2. Frame count, timing and picture size are the same for both types, and the frame player plays both.

## 4. Performance

Create frames from a 60 s file as Tiles and as Blended tiles and compare the times. The target in the spec (SC-006) is at most twice as long; planning measured about three times. If the measured figure is above twice, report the numbers and decide the bound with the owner of the spec before finishing.
