# Quickstart: Noise Floor

Validation scenarios that prove the feature works. Contract: [noise-floor.md](contracts/noise-floor.md); rules: [data-model.md](data-model.md). There is no page control or request field, so everything is checked from Python and from the tests.

## Prerequisites

- Backend: `cd backend`, the `.venv` active (nothing new to install).
- Nothing to start.

## Automated checks

```text
cd backend && python -B -m pytest tests/test_noise_floor.py tests/test_noise_floor_api.py tests/test_chords.py
cd backend && python -B -m pytest        # everything else; see the list of changed expectations in tasks.md
cd frontend && npm test                  # untouched; still green
```

## Scenario 1: The cut (User Story 1)

In a Python shell in `backend/`:

1. `import numpy as np; from app.services.noise_floor import apply_noise_floor, NOISE_FLOOR`; `NOISE_FLOOR` is `0.001`.
2. `apply_noise_floor(np.array([[1.0, 0.0009, 0.001, 0.5]]))` is `[[1.0, 0.0, 0.001, 0.5]]`.
3. A silent array comes back unchanged; the input is never changed.

## Scenario 2: Through a job, for every picture (User Stories 1 and 3)

`pytest tests/test_noise_floor_api.py` makes a file with one loud tone and, in the same file, a second tone 70 dB below it, for each image type: the frames equal those of the file without the second tone (so the faint tone is not counted, drawn, ranked among the loudest notes or placed in a chord), with and without a Threshold, and the same file with the second tone only 50 dB down is different. The job request and response are the same as before.

## Scenario 3: The chords (User Story 2)

1. `from app.services.chords import measure_chords`; a window with C, E, G at 1.0, 0.9, 0.8 and Bb (note 37) at 0.0009: `measure_chords(values, [(4, 7), (4, 7, 10)]).record(0)` is `(4, 7)` with the notes `(27, 31, 34)`; with Bb at 0.001 it is `(4, 7, 10)`.
2. A window whose only notes are far below a loud note elsewhere in the array has no chord.
3. Polar Chords through a job: a triad with a faint extra tone gives the triad's chord bar, not a seventh chord's.

## Scenario 4: Nothing else moves (SC-005, SC-006)

The whole backend suite passes. The tests whose expectation rested on a leaking value under the floor are the ones listed (and explained) in `tasks.md`; no other test changes. `git status` shows only `noise_floor.py`, `chords.py`, `jobs.py`, their tests, the README and the spec folders as new or changed.

## Scenario 5: Speed (SC-007)

`apply_noise_floor` on 4,000 windows of 88 notes is a single comparison pass, well under a millisecond-scale time; the job is not measurably slower.
