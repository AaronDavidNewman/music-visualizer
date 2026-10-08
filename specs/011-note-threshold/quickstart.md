# Quickstart: Note Threshold

Validation guide for [spec.md](spec.md). The comparison rule is in [data-model.md](data-model.md) and the interface in [contracts/threshold-api.md](contracts/threshold-api.md).

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

Expected: everything passes. New coverage includes the hidden-notes rule on hand-worked values (strictly below, equal shown, zero hides nothing, the largest never hidden, silence); `tile_colors` with a mask; `write_frames` at threshold 0 giving byte-identical files; a loud and a faint note; smoothing applied before the comparison; the Saturation root, the steps and the frame brightness leaving the hidden set alone; hidden notes still shifting other tiles' hues; the API field (valid, missing, every refused kind) and its response; the slider's constants, validation, readout and explanation; and the rendered slider.

## 2. Run the application

```
cd backend
uvicorn app.main:app --reload       # http://localhost:8000

cd frontend
npm run dev                         # http://localhost:5173
```

Use a `.wav` with a clear loud note and some fainter ones (a chord whose notes have different levels, or any music).

## 3. Check each story

**Story 1: faint notes disappear**

1. Create frames with the Threshold at the left end ("Off"). They look as they did before this feature (compare with a frame from an earlier run if you kept one).
2. Move the Threshold to 5 and create frames. Some faint tiles are now plain black; tiles that are still colored look exactly as they did with the threshold off.
3. Raise it to 10: only notes with at least a tenth of the file's loudest note value remain; the loudest note's tile is still colored in the frames where it sounds.
4. To read exact values, download a frame (`/api/jobs/<job_id>/frames/<n>`) and read a hidden tile's centre pixel: it is (0, 0, 0).
5. A silent file gives entirely black frames at every threshold.

**Story 2: the slider on the page**

1. The settings column has a Threshold slider after Smoothing, at the left end, with the readout "Off".
2. Moving it shows `1% of the loudest note` … `10% of the loudest note` in steps of 1.
3. Its info button opens a popover with the explanation.
4. While frames are being created the slider is disabled.
5. After frames are created the summary shows "Threshold: Off" or "Threshold: n%".
6. Refused requests: with curl (or the API docs at `/docs`) send `threshold=-1`, `threshold=11`, `threshold=` (empty) and `threshold=abc`; each returns 400 with "The threshold must be a number from 0 to 10." Leaving the field out is accepted (off).

**Story 3: with the other settings**

1. Set Smoothing to 0.8 and the Threshold to 10: a note that stops fades through its colors and turns black in the first frame whose smoothed value is under 10% of the file's loudest value, and stays black.
2. Change the Saturation setting (the root): the set of black tiles does not change, only how strongly the other tiles are colored.
3. Choose Saturation, Brightness and Hue steps: black tiles stay black; the others are rounded as before.
4. Change only the Threshold between two runs: every tile that is shown has the same hue, saturation and brightness in both runs.

## 4. Performance

Create frames from the sample file with the threshold off and at 10. The two times differ by no more than 10% (SC-008).
