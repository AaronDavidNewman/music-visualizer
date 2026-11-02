# Quickstart: Decay

Validation scenarios that prove the feature works end to end. Contracts: [decay.md](contracts/decay.md); rules: [data-model.md](data-model.md).

## Prerequisites

- Backend: `cd backend`, the `.venv` active, `pip install -r requirements.txt` (nothing new).
- Frontend: `cd frontend`, `npm install` (nothing new).

## Automated checks

```text
cd backend  && python -m pytest
cd frontend && npm test
cd frontend && npm run build   # type check
```

Expected: all green, including `test_decay.py`, `test_decay_rendering.py`, `test_decay_api.py`, and the reference-hash tests of the other six image types.

## Scenario 1: A held note charges and saturates (User Story 1)

1. Start the backend (`uvicorn app.main:app`) and the frontend (`npm run dev`).
2. Upload a file with one steady loud note; choose **Decay**, decay rate 5, Create frames.
3. Expected: that note's circle grows to full size and to the colormap's last color within a few frames and stays; the circles around it grow and brighten shortly after; with the Spiral layout the neighbours are the cells around it.

## Scenario 2: Fading (User Story 1)

1. Use a file where the note stops half way (or a short note followed by silence).
2. Expected: after the note stops the circle shrinks and loses its color over the following decay steps; its neighbours first rise, then fade; a circle in a corner or on an edge fades faster than one in the middle; at the end of a long silence every circle is the smallest dot in the first color.

## Scenario 3: The decay rate (User Story 2)

1. On the page choose Decay: the groups are Analysis, Colormap, Image type, Decay, Note layout, Local peaks (no checkbox) and Data smoothing.
2. Set the decay rate to 0.25, then 4, and create frames each time: at 0.25 the spread is smooth (four steps in every frame); at 4 it moves in visible steps every fourth frame.
3. Through the API: `curl -F image_type=decay -F decay_rate=0.5 -F file=@song.wav http://localhost:8000/api/jobs` returns `"image_type": "decay", "decay_rate": 0.5`; `-F decay_rate=5` and `-F decay_rate=1.1` return 400 `The decay rate must be a number from 0.25 to 4 in steps of 0.25.`.

## Scenario 4: Corners (User Story 3)

1. Create frames from a silent file: every circle is the smallest dot in the first color, without errors.
2. Create frames from a file without a beat (a few seconds of a steady tone): works, with the beat bonus 0.

## Scenario 5: Nothing else changed

Create frames with each of the other six image types for the reference file: they match the hashes of the earlier features.

## Scenario 6: Speed (SC-007)

Create the frames of a 60 second file at 30 frames a second with Decay: under 30 seconds.
