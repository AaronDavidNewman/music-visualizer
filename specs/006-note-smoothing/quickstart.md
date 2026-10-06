# Quickstart: Note Smoothing

Validation guide for [spec.md](spec.md). Interface changes are in [contracts/http-api-changes.md](contracts/http-api-changes.md) and [data-model.md](data-model.md).

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

Expected: everything passes. New coverage includes the worked example (0, 10, 0, 0 at 0.5 gives 0, 5, 2.5, 1.25), the first frame being unchanged at every smoothing, each note being independent, the fade lengths (4 frames at 0.5, 11 at 0.8, 1 at 0), identical output at 0, the API field and its errors, and the slider's range in the validation helper.

## 2. Run the application

```
cd backend
uvicorn app.main:app --reload       # http://localhost:8000

cd frontend
npm run dev                         # http://localhost:5173
```

## 3. Walk through the stories

1. **Default**: Open the page. The smoothing slider is at the far left and shows 0.00. Submit `backend/audio/fotr-intro1-echo.wav`: the frames look as they did before. The summary shows smoothing 0.00.
2. **Smoothing calms the tiles**: Submit the same file with the slider at 0.50, then 0.80. Play each. Tiles still rise and fall with the music, but flicker is reduced, and each tile fades gradually after its note stops instead of switching off. At 0.80 the fade is clearly slower than at 0.50. Frame count, windows analyzed and timing in the summary are the same in all three.
3. **Slider limits (Story 2)**: Drag the slider fully right: it shows 0.80 and goes no further. Drag it fully left: 0.00. Use the arrow keys: it moves in steps of 0.01. While a submission runs, the slider is disabled. After an error (for example a text file renamed `.wav`) the slider is where you left it.
4. **First frame**: Step to the first frame at 0.00 and at 0.80. They are the same picture.
5. **Server check**: Without the form:

   ```
   curl -F file=@backend/audio/fotr-intro1-echo.wav -F window_size=4096 -F frame_rate=30 -F smoothing=0.81 http://localhost:8000/api/jobs
   curl -F file=@backend/audio/fotr-intro1-echo.wav -F window_size=4096 -F frame_rate=30 -F smoothing= http://localhost:8000/api/jobs
   ```

   Expected: both return 400 with "The smoothing must be a number from 0.0 to 0.8.", quickly, and nothing new appears in the temp folders. The same request with `smoothing=0.8` succeeds and reports `"smoothing": 0.8`, and one with no `smoothing` field reports `0.0`.

## 4. Measure SC-004 and SC-008

For SC-004, find a note that stops sounding in the sample file and count the frames its value takes to fall below 10% at smoothing 0.5 and 0.8 (the backend tests check this on constructed data). For SC-008, time the same submission at smoothing 0 and 0.8. Expected: within 10%.
