# Quickstart: validating Energy Graphs

Run from the repository root. Backend commands use the project's virtual environment as for features 032 and 033.

## 1. The numbers (no picture)

```bash
cd backend
python -B -m pytest tests/test_energy_graphs.py tests/test_note_analysis.py -q
```

Expect: the rank scores of a hand-made window are 84, 83, 82, ... for the loudest notes and 0 for a silent one; the quasi-decibel value is 1 for the loudest note of the file, 0 for silence and for amplitudes under 1; the two totals of the last frame of a small file equal the sums over all its windows (SC-002); the softmax of each row divided by its largest total adds up to 1 and does not depend on the size of the totals (SC-003). (`test_note_analysis.py` is not part of this feature any more.)

## 2. The picture

```bash
python -B -m pytest tests/test_energy_graphs_rendering.py -q
```

Expect: 600 x 400 RGB frames; the tallest bar is 336 px in every frame with a sound and there is no bar before the first sound; the frequency bar of a note is in the start color and its amplitude bar in the end color; the smallest value of each data set has no height (a note that never sounded has no bar when others have); the same input gives identical bytes (SC-004).

## 3. The job end to end

```bash
python -B -m pytest tests/test_energy_graphs_api.py tests/test_image_type_api.py -q
```

Expect: `image_type=energy-graphs` gives 200, the frame count of the other types, frames that can be fetched, and a response with no new field; a bad type is refused with the 400 message listing `energy-graphs`; a silent file and a file of two tones work, and the bars of the last frame of the two-tone file are the softmax of the totals worked out by hand (US1 independent test).

## 4. Nothing else changed

```bash
python -B -m pytest -q
cd ../frontend && npm test -- --run
```

Expect: all existing tests pass (the lists of image types in the frontend tests were extended), and the frames of the other nine types are byte for byte what they were.

## 5. By eye, with a real file

Start the service and the page as usual, choose **Energy graphs** in the Image type dropdown (no further control appears; Data smoothing is hidden), create frames from `backend/audio/sonata.wav` and play them: the bars of the two data sets grow and settle into a shape while the tallest stays at the same height, the pairs of bars settle into a shape as the file goes on. Then make a movie of it (feature 029). Time the job against Tiles on the same file (SC-005).
