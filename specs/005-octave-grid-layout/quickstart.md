# Quickstart: Octave Grid Layout

Validation guide for [spec.md](spec.md). The image rules are in [contracts/image-layout.md](contracts/image-layout.md) and [data-model.md](data-model.md).

## Prerequisites

Same as the earlier features (`pip install -r requirements-dev.txt` in `backend/` with the venv active, `npm install` in `frontend/`).

## 1. Automated checks

```
cd backend
pytest -v

cd ..\frontend
npm run typecheck
npm run build
```

Expected: everything passes. New coverage includes the 252 × 168 size and exact 3:2 ratio, 12 × 7 tiles of 21 × 24, the note in every tile (`12 × row + column`), the tile below being double the frequency, the four highest notes not appearing, per-note gray levels matching the previous layout, and silent files staying black.

## 2. Run the application

```
cd backend
uvicorn app.main:app --reload       # http://localhost:8000

cd frontend
npm run dev                         # http://localhost:5173
```

## 3. Walk through the stories

1. **Layout (Story 1)**: Submit `backend/audio/fotr-intro1-echo.wav` with the defaults. The frame is a grid of 12 columns by 7 rows of tall rectangles, 3:2 overall. Open the image in its own tab (right-click the frame, open image) and check it is 252 × 168 pixels.
2. **Octaves line up**: Submit a file with one steady note, such as a 440 Hz tone (note 36, which is row 3, column 0). Expected: the brightest tile is in the fourth row from the top, at the left edge. A tone at 880 Hz lights the tile directly below it (row 4, column 0), and one at 220 Hz lights the tile directly above it (row 2, column 0).
3. **Lowest and highest**: A 55 Hz tone lights the top-left tile. A tone near 6600 Hz lights the bottom-right tile. A tone at 8000 Hz (one of the four omitted notes) lights no tile that you can pick out.
4. **Same brightness as before**: Submit the same file at the same settings as an earlier run. The gray of each note looks the same as it did, just in its new tile. Frame count, windows analyzed and timing in the summary are unchanged.
5. **Silent file**: Every tile is black.
6. **Page shape (Story 2)**: With a completed submission, resize the browser from about 320 pixels wide up to full width. The image stays 3:2, is never stretched or cropped, and the page never scrolls sideways. Press play and watch that the image does not change size from frame to frame.
7. **Old submissions**: Images from before this change that are still in the temp folders keep the square layout.

## 4. Check the scaling caveat

Gray levels are still scaled against the loudest value among all 88 notes. If a file's loudest value is in one of the four omitted notes, the notes you can see will not reach full white. For `backend/audio/fotr-intro1-echo.wav`, check that the loudest value is among the shown notes (the implementation step reports this measurement).
