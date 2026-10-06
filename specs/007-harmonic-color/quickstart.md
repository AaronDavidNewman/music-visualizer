# Quickstart: Harmonic Color

Validation guide for [spec.md](spec.md). The color rule is in [contracts/image-color.md](contracts/image-color.md) and [data-model.md](data-model.md).

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

Expected: everything passes. New coverage includes the three worked colors from the spec, the hue formula against an independent reference, the ends of the range, the four undrawn notes counting as partners, wrap-around at red, the brightest channel equalling the old gray level, silent files staying black, and the layout and timing being unchanged. The frontend has no code change.

## 2. Run the application

```
cd backend
uvicorn app.main:app --reload       # http://localhost:8000

cd frontend
npm run dev                         # http://localhost:5173
```

## 3. Walk through the stories

1. **Colored tiles (Story 1)**: Submit `backend/audio/fotr-intro1-echo.wav` with the defaults. The frame is in color: pastel teal, green, blue, violet and some magenta tiles instead of gray ones, in the same 12 × 7 octave grid. Quiet tiles are dark. At brightness 4 or higher there is clearly more variety, including brick red and pink tiles.
2. **A single note is cyan**: Submit a file with one steady note (such as a 440 Hz tone). Its tile is a pastel cyan (hue 180°), and the rest of the picture is dark.
3. **Chords shift the hue**: Submit a file that plays a note together with a note 4 semitones above it (for example 220 Hz and 277 Hz at once, notes 24 and 28). The lower of the two tiles shifts toward green and red, because a "down" partner (+4) is lit; the louder the partner, the further it goes, and at full brightness it reaches red. A note 3, 6, 8 or 11 semitones above pushes the lower tile toward blue, violet and then red instead. Notes 4, 5 and 7 semitones above pull toward green; notes 3, 6, 8 and 11 above push toward blue. Raise the brightness setting to 4 or more to make quiet partners count for more and see more color.
4. **Same brightness and layout (Story 2)**: Compare with an earlier run of the same file and settings. Each tile is in the same place and just as bright (the brightest of its three color channels matches the old gray level), the summary shows the same frame count, windows analyzed and timing, and a silent file is entirely black.
5. **The page**: Press play. Frames show in color at the same size and 3:2 shape, and the animation plays as before.
6. **Settings still work**: Change brightness and smoothing. Brightness lifts quiet tiles as before, smoothing calms the flicker, and the colors follow the final brightness of the tiles.
7. **Old submissions**: Frames from before this change that are still in the temp folders stay gray.

## 4. Check the timing (SC-007) and the colors on real data

Time the same submission before and after the change; the new time should be no more than 25% longer. The implementation step also checks, on the sample file, that every tile's brightest channel equals the old gray level, that colors recovered from the pixels match the hue rule, and looks at a frame side by side with its gray version.
