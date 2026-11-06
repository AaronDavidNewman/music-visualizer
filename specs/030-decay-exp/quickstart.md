# Quickstart: Decay Exp

Validation scenarios that prove the feature works end to end. Contract: [decay-exp.md](contracts/decay-exp.md); rules: [data-model.md](data-model.md).

## Prerequisites

- Backend: `cd backend`, the `.venv` active, `pip install -r requirements.txt` (nothing new).
- Frontend: `cd frontend`, `npm install` (nothing new).

## Automated checks

```text
cd backend  && python -m pytest
cd frontend && npm test
cd frontend && npm run build   # type check
```

Expected: all green, including `test_decay_exp.py`, `test_decay_exp_api.py`, the existing Decay tests (the refactor of `decay_step` changes nothing) and the reference-hash tests of the other seven image types.

## Scenario 1: Tapered gain (User Story 1)

1. Start the backend (`uvicorn app.main:app`) and the frontend (`npm run dev`).
2. Upload a file with one steady loud note; choose **Decay Exp**, Create frames; then do the same with **Decay**.
3. Expected: in Decay Exp the note's circle starts small (it gains only `24·e^(−3)` ≈ 1.1949 points in the first frame, where Decay gives 24 and a full-size circle at once) and keeps growing for a long time, because the taper of the gain rises from 8 by 0.01 a frame (about 19.6 points at frame 100, 32.4 at frame 400 and 34.4 for good from about frame 1000, with the taper at 12); its neighbours show as fainter circles around it. Several notes close together fill more than 10 circles over 32 points, which turns the taper down: it then swings between 8 and about 10.3 and the largest circle reaches about 57 and settles near 50; nothing reaches 64. In library terms: `decay_exp.circle_points` of one loud note without a beat at rate 4 gives 1.1949 in frame 1, and `circle_tapers` gives 8.0, 8.01, 8.02, ... for the frames.

## Scenario 2: Fading (User Story 1)

1. Use a file where the note stops half way (or a short note followed by silence).
2. Expected: after the notes stop, charged circles drain at once, the fuller the faster (4 points a frame in all at 32 points, 8 at 64), and the picture shrinks quickly at first; the tail is long, because a faint circle hardly drains: the largest circle is under 1 point after about 3,100 frames (1 minute 43 seconds at 30 frames a second), under a tenth of a point after about 31,800 and exactly 0 after about 228,700, so the last faint dots, which look like the smallest dot, stay for a very long time. A corner or edge circle loses as much as any other (it just sends to fewer neighbours).

## Scenario 3: The page and the API (User Story 2)

1. On the page choose Decay Exp: the groups are Analysis, Colormap, Image type, Decay (Decay rate only), Note layout, Local peaks (no checkbox) and Data smoothing; the four saturation sliders are not there. Choose Decay: they are.
2. `curl -F image_type=decay-exp -F decay_rate=0.5 -F file=@song.wav http://localhost:8000/api/jobs` returns `"image_type": "decay-exp", "decay_rate": 0.5`.
3. `-F decay_rate=1.1` returns 400 `The decay rate must be a number from 0.25 to 4 in steps of 0.25.`; `-F image_type=decay_exp` returns 400 with the list of eight names.
4. `-F decay_low=10` returns 400 `The low saturation decay must be a number from 0.5 to 3.` (checked as always).
5. The result summary of a Decay Exp job lists the Decay rate and none of the four saturation decays.

## Scenario 4: Quiet files (User Story 3)

1. A silent file: every circle is the smallest dot in the first color, without errors.
2. A few seconds of a steady tone (no beat): works, with beat bonus 0.

## Scenario 5: Nothing else changed

Create frames with each of the other seven image types, Decay included, for the reference file: they match the hashes of the earlier features.

## Scenario 6: Speed (SC-005)

Create the frames of a 60 second file at 30 frames a second with Decay Exp: under 30 seconds.

## Scenario 7: The taper (User Story 1)

1. In a Python shell in `backend/`: `from app.services.decay_exp import circle_tapers` and `import numpy as np`.
2. `circle_tapers(np.zeros((450, 88)))[[0, 1, 399, 400, 449]]` is `[8.0, 8.01, 11.99, 12.0, 12.0]`: rising by a hundredth a frame, exactly 12 at the 401st frame, never over.
3. With five steady loud notes (rows 10, 20, 30, 40 and 50 of a 1500-frame array at 1.0, 0.9, 0.8, 0.7, 0.6): `circle_tapers(values).min()` is 8.0 and the maximum is about 10.25: it turns down as soon as 11 circles are over 32 points and goes back down to exactly 8 before it rises again.
