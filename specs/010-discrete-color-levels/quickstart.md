# Quickstart: Discrete Color Levels

Validation guide for [spec.md](spec.md). The rounding rule and tables are in [data-model.md](data-model.md) and the interface in [contracts/color-levels-api.md](contracts/color-levels-api.md).

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

Expected: everything passes. New coverage includes the level count for every allowed step; the rounding rule on hand-worked values (nearest, half-way up, ends fixed, N/A unchanged, floating-point noise); each property rounded on its own through `tile_colors` and `write_frames`; smoothing applied before rounding; black tiles staying black; adding a frame leaving earlier frames unchanged; all-N/A output identical to the output with no step arguments; the three API fields (valid, N/A in any case, missing, and every refused kind) and the response; the dropdown option lists, level labels and help texts.

## 2. Run the application

```
cd backend
uvicorn app.main:app --reload       # http://localhost:8000

cd frontend
npm run dev                         # http://localhost:5173
```

Use the sample file from the earlier features (or any music `.wav`). A file with several notes and a loud-to-quiet change shows the effects best.

## 3. Check each story

**Story 1: rounding to levels**

1. Create frames with all three steps at N/A. They look as they did before this feature (compare with a frame from an earlier run if you kept one).
2. Set **Saturation steps** to 20 and create frames. Tiles are now either gray/white or one of five fixed color intensities; none are in between. To read exact values, download a frame (`/api/jobs/<job_id>/frames/<n>`), convert each distinct tile color to HSV (saturation is `(max − min) / max`) and confirm every saturation is one of 0, 20, 40, 60, 80, 100 (to within the rounding of 8-bit color).
3. Set **Hue steps** to 90 (Saturation back to N/A). Every tile's hue is one of 0°, 90°, 180°, 270°, 360°: red, yellow-green, cyan, violet, red.
4. Set **Brightness steps** to 50. Every frame is black, half bright or full bright; the loudest frame is at full brightness and silence is black.
5. Change only one setting at a time and confirm the other two properties look the same as with N/A.
6. Choose the largest steps (Hue 180, the others 50): the picture is made of a handful of flat colors (hue only red or cyan).

**Story 2: the settings on the page**

1. The settings column has three dropdowns, **Hue steps**, **Saturation steps**, **Brightness steps**, each starting at N/A, with "N/A (smooth)" beside it.
2. Pick Hue 90: the readout shows "90 (5 levels)". Pick Saturation 10: "10 (11 levels)". Pick Brightness 50: "50 (3 levels)".
3. Each info button opens a popover with the explanation and the allowed choices; the Hue one mentions that both ends of the wheel are red.
4. While frames are being created the three dropdowns are disabled.
5. After frames are created the summary lists "Hue steps: …", "Saturation steps: …", "Brightness steps: …".
6. Refused requests: with curl (or the interactive API docs at `/docs`) send `saturation_step=7`, `saturation_step=0`, `saturation_step=90`, `hue_step=` (empty) and `brightness_step=abc`; each returns 400 with a message listing the allowed choices. Sending `n/a` or leaving the field out is accepted.

**Story 3: smoothing and stability**

1. Set Smoothing to 0.8 and Saturation steps to 50. Every tile's saturation is exactly 0, 50 or 100, with no flicker between near values.
2. Raise the Saturation or Brightness root settings and confirm the rounded levels still include the maximum (the loudest frame is fully bright at every root).
3. Make the same file one second longer (append silence) with the same settings: every frame that existed before is pixel-for-pixel unchanged, except possibly the last one (its analysis window is cut short by the end of the file, with or without a step); the same frames differ with all steps at N/A.

## 4. Performance

Create frames from the sample file with all steps at N/A and again with all three at their smallest step. The two times differ by no more than 10% (SC-009).
