# Quickstart: Validating local_peaks

Prerequisites: the repository as it is and the backend `.venv`. If the backend suite fails only at `test_the_frontends_list_matches_this_one_name_for_name_in_the_same_order` (or at import because the default colormap is not in the user's list), that is the user's colormap edit, not this feature; earlier features were verified with a temporary default (`scratchpad/run_with_default.py`).

## 1. Automatic checks

```text
cd backend && .venv\Scripts\python -m pytest -q tests/test_local_peaks.py
cd backend && .venv\Scripts\python -m pytest -q
```

Expected: everything passes. New coverage includes: the impulse energy against a direct per-window calculation (stereo, mono, a dropped partial window); a click track (every click found within 32 samples, none twice, rates within 2%); the minimum distance (converted for several rates and never violated, including across zone borders); the prominence (the value handed to `find_peaks`, bumps below it dropped, a click above it kept); windows (zones tile the file, short files, independence of the window size); the interpolation and the rate (at a peak, between, before the first, after the last, fractional, in seconds, arrays, a file with no peaks); the settings checks and messages; determinism and no change to the inputs.

## 2. The rest of the application did not change

```text
cd backend && .venv\Scripts\python <scratchpad>\hashes019.py
```

Expected: the four reference hashes equal `6819990556fd4095` (tiles), `f32a99c59fcb87fc` (blended), `92b3a27dee73e223` (Blues/smoothing/threshold) and `400cc93e1bfca03d` (contour).

## 3. Try it on a click track

```text
cd backend && .venv\Scripts\python <scratchpad>\peaks_try.py
```

Expected: for 30 s of quiet noise with a click every 0.5 s: 59 peaks, every one within 32 samples of its click, a rate of 120 peaks per minute at each peak after the first (60 at the first), `energy_at` equal to the peak's energy at a click and between the two neighbours half way between, 0 before the first peak and the last peak's energy at the end of the file.

## 4. Time (60 second stereo file)

Expected: under 5 seconds (SC-006); the prototype measured 0.023 s.

## 5. Nothing to check in the browser

The page and the API are unchanged; there is no manual step.
