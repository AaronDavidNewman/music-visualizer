# Quickstart: Window Spacing Parameter

Validation guide for [spec.md](spec.md). Interface changes are in [contracts/http-api-changes.md](contracts/http-api-changes.md) and [data-model.md](data-model.md).

## Prerequisites

Same as feature 002 (`pip install -r requirements-dev.txt` in `backend/` with the venv active, `npm install` in `frontend/`).

## 1. Automated checks

```
cd backend
pytest -v

cd ..\frontend
npm test
npm run typecheck
npm run build
```

Expected: everything passes. New coverage includes the step and window-start rules, frame averaging with overlap and gaps, the default-spacing table shared by Python and TypeScript, the WAV header reader, and the new API fields and errors.

## 2. Run the application

```
cd backend
uvicorn app.main:app --reload       # http://localhost:8000

cd frontend
npm run dev                         # http://localhost:5173
```

## 3. Walk through the stories

1. **Default follows the settings (Story 2)**: Open the page with no file. Expected: window size 4096, frame rate 30, spacing 0.358886 (the 44,100 Hz default). Change the frame rate to 60: spacing becomes 0.179443. Change the window size to 8192: spacing becomes 0.089721. Choose `backend/audio/fotr-intro1-echo.wav` (44,100 Hz): the value stays as calculated for 44,100 Hz. Type 0.5, then change the frame rate: the field returns to the new default.
2. **Different sample rate**: Choose a 48,000 Hz WAV with the same settings. Expected: the default differs from the 44,100 Hz one (1,600 samples per frame at 30 fps, so 1600 ÷ 4096 = 0.390625).
3. **Spacing sets the windows (Story 1)**: Set window size 8192, frame rate 30, spacing 0.25 and submit. Expected: the summary shows window spacing 0.25, step 2048 samples, and about four times as many windows as with spacing 1. Submit with spacing 1: step 8192. Submit with spacing 2: accepted, step 16384.
4. **Default gives each frame a window**: Submit with the untouched default. Expected: windows analyzed is at least the frame count.
5. **Limits (Story 3)**:
   - Spacing 0.00001 with window 4096: a hint says the value will be raised to 0.000244; after submitting, the summary shows step 1 and a notice that it was raised. This may also exceed the window limit for a long file, in which case the window-count message appears instead. Use a short file to see the raise.
   - Spacing 0, -1, `abc` or empty: Submit is blocked with the message.
   - A tiny spacing on a long file: refused with the window count and the limit, quickly.
6. **Same output twice**: Submit the same file and settings twice and compare a few frames. They are identical.

## 4. Timing (SC-007)

Submit `backend/audio/fotr-intro1-echo.wav` at window 4096, 30 fps and the default spacing. The same measurement without a browser:

```
curl -w "%{time_total}\n" -F file=@backend/audio/fotr-intro1-echo.wav -F window_size=4096 -F frame_rate=30 -F window_spacing=0.358886 http://localhost:8000/api/jobs -o NUL
```

Expected: a few seconds, as for feature 002.
