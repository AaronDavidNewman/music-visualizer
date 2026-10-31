# Quickstart: Contour Beat Wave

Validation scenarios that prove the feature works end to end. Contract: [contour-beat-wave.md](contracts/contour-beat-wave.md); rules: [data-model.md](data-model.md).

## Prerequisites

- Backend: `cd backend`, the `.venv` active (nothing new to install).
- Frontend: `cd frontend`, `npm install` (nothing new).
- Restart the backend after pulling these changes (a running `uvicorn` keeps the old code).

## Automated checks

```text
cd backend  && python -m pytest
cd frontend && npm test
cd frontend && npm run build   # type check
```

Expected: all green, including `test_beat_wave.py`, `test_contour_beat_wave.py`, `test_contour_beat_wave_api.py` and the reference-hash tests of the other image types.

## Scenario 1: The contour ripples with the beat (User Story 1)

1. Start the backend and the frontend.
2. Upload a file with a steady chord and a clear pulse; choose **Contour**, tick **Beat coloring**, Wave count 4, Create frames.
3. Expected: the frames at the lowest point of the beat look like the plain contour; as a beat rises concentric rings centered on the middle of the picture appear and deepen, darkest half way up the beat, and fade out again towards the top of the beat; with Wave count 10 there are more, thinner rings, close together near the middle and wider towards the edge.

## Scenario 2: Off means as before (User Story 2)

1. Create the frames again with **Beat coloring** off: the frames are exactly the plain Contour frames (compare file for file with a job made before this change, or with `wave_count` changed: nothing differs).
2. Through the API: `curl -F image_type=contour -F beat_coloring=true -F wave_count=6 -F file=@song.wav http://localhost:8000/api/jobs` returns `"wave_count": 6`; `-F wave_count=11` and `-F wave_count=2.5` return 400 `The wave count must be a whole number from 2 to 10.`

## Scenario 3: The page (User Story 2)

On the page choose Contour: the groups are Analysis, Colormap, Image type, Contour (Threshold, Notes, Wave count), Local peaks (checkbox and two sliders), Data smoothing, Image smoothing; the result summary shows Beat coloring, and, with it on, Minimum distance, Prominence and Wave count.

## Scenario 4: Corners (User Story 3)

A silent file and a file without a beat (a steady tone with Prominence 100) give the same frames with the box on as with it off, without errors; a very short file works.

## Scenario 5: Nothing else changed

Create frames with each of the other six image types for the reference file: they match the hashes of the earlier features.

## Scenario 6: Speed (SC-006)

Create the frames of a 60 second file at 30 frames a second with Contour and the box on, and with it off: the first takes no more than a few seconds longer.
