# Quickstart: Brightness Parameter

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

Expected: everything passes. New coverage includes the mapping for all 99 brightness values and all 256 levels, the guarantees at 0 and 255, the monotonic checks, brightness 2 matching the old square root, and the API field and error.

## 2. Run the application

```
cd backend
uvicorn app.main:app --reload       # http://localhost:8000

cd frontend
npm run dev                         # http://localhost:5173
```

## 3. Walk through the stories

1. **Default (Story 1, scenario 1)**: Open the page. Brightness shows 2 with the range 2 to 100. Submit `backend/audio/fotr-intro1-echo.wav`. The frames look like the ones from before this feature, and the summary shows brightness 2.
2. **Brightness lifts quiet notes**: Submit the same file with brightness 4, then 10. Each result is brighter than the last: quiet squares that were nearly black become clearly gray, and at 10 most squares are bright with less difference between them. The summary shows each value. Frame count, windows analyzed and timing are the same in all three.
3. **Extremes**: Submit with brightness 100. Everything that is not silent is close to white. Black squares stay black.
4. **Silent file**: Submit a silent WAV at brightness 2 and at 100. Every square is black both times.
5. **Validation (Story 2)**: Enter 1, 101, 2.5, 0, -3, `abc` and clear the field: each shows "The brightness must be a whole number from 2 to 100." and blocks Submit. Enter 2 and 100: both are accepted. A failed submission (for example a text file renamed `.wav`) leaves the brightness you entered in place.
6. **Server check**: Without the form:

   ```
   curl -F file=@backend/audio/fotr-intro1-echo.wav -F window_size=4096 -F frame_rate=30 -F brightness=101 http://localhost:8000/api/jobs
   curl -F file=@backend/audio/fotr-intro1-echo.wav -F window_size=4096 -F frame_rate=30 -F brightness= http://localhost:8000/api/jobs
   ```

   Expected: both return 400 with the brightness message, quickly, and nothing new appears in the temp folders. The same request with no `brightness` field succeeds and reports `"brightness": 2`.

## 4. Measure SC-003 and SC-006

For SC-003, compare the average gray level of a typical frame from the sample file at brightness 2 and at 4 (the backend tests do not use the 90 MB file). Expected: a rise of at least 25%. For SC-006, note the time for the same submission at brightness 2 and at 10. Expected: within 10%.
