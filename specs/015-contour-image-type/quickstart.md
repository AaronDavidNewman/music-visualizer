# Quickstart: Contour Image Type

Validation guide for [spec.md](spec.md). The values are in [data-model.md](data-model.md) and the interface in [contracts/image-type-api.md](contracts/image-type-api.md).

## Prerequisites

`pip install -r requirements-dev.txt` in `backend/` with the venv active (matplotlib is already part of it) and `npm install` in `frontend/`.

## 1. Automated checks

```
cd backend
pytest -v

cd ..\frontend
npm test
npm run typecheck
npm run build
```

Expected: everything passes. The contour tests use whatever colormap list `colormaps.py` has (see `backend/tests/colormap_names.py`) and never state a number of levels, so they keep passing when you add, remove or rename a colormap, as long as each name is a valid matplotlib name and the page's list equals the server's.

## 2. Contour frames from the API

Start the backend (`uvicorn app.main:app` in `backend/`), then send a WAV with a steady 440 Hz tone and a quieter 660 Hz tone:

```
curl -F file=@tones.wav -F window_size=4096 -F frame_rate=30 -F image_type=contour -F colormap=hot http://127.0.0.1:8000/api/jobs
```

Expected: 200 with `"image_type": "contour"`. Fetch a frame through `frame_url_template`: a 252 × 168 PNG with no axes or border, a bright region around the 440 Hz note's position in the grid (A4: the fourth row from the top, first column) fading to the colormap's start far from it. The same request with `image_type=tiles` returns the flat tiles, with the same frame count.

Refusals: `image_type=Contour` and `image_type=` (empty) both return 400 with `The image type must be one of tiles, blended, contour.`.

## 3. The scale is the same in every frame

Create contour frames of a file in which a tone fades out. The tone's area gets darker (closer to the colormap's start) frame by frame and is not re-brightened to full strength in the quiet frames. A frame with no sound is one flat color, the colormap's first color.

## 4. With the other settings

Create contour frames with smoothing 0.5, window 3, threshold 5 and each colormap on the page: a note below 5% of the loudest leaves no peak; changing the colormap changes only the colors; a silent file is one flat color. Create tiles and blended frames from the same file: they are byte-for-byte what they were before the feature (the default output of the 4-second test file hashes to `28e608864383e33d2b3a195e962d2fd0c02005cd64137fcf4c45ad7e7375d780`).

## 5. Time

A 10-second file at 30 frames per second (300 frames) as contour finishes well within one minute (the prototype measured 2.5 s for the drawing).

## 6. The page

Open the frontend: the Image type dropdown offers Tiles, Blended tiles and Contour, and starts at Tiles. Choose Contour: the Blend width slider is disabled; choose Blended tiles: it is enabled; choose Tiles: disabled. Open the Image type info button: the text also describes Contour. Create frames with Contour: the player plays the pictures and the summary says "Image type: Contour" without a blend width line.

Not covered by automated tests: step 6 in a real browser, and judging whether the contour looks good, which is for the user.
