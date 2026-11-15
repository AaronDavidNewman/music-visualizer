# Contract: job request and response changes (feature 040)

The endpoint is the existing job creation (`POST /jobs`, form data) in `backend/app/routers/jobs.py`. Only the Local peaks settings change.

## Request

| Field | Before | After |
|---|---|---|
| `peak_distance` | optional, milliseconds, 100 to 2000, default **100** | optional, milliseconds, 100 to 2000, default **350**; same message: `The minimum distance must be a number from 100 to 2000 milliseconds.` |
| `peak_prominence` | optional, percent 0 to 100, default 50, 400 `The prominence must be a number from 0 to 100 percent.` | **removed**: a value that is sent is ignored like any unknown form field (no 400); the measurement always uses 20 |
| `beat_coloring`, `image_type`, others | unchanged | unchanged |

`peak_distance` is still checked before the file is read, whether or not the image type uses it.

## Response (the job)

| Field | Before | After |
|---|---|---|
| `peak_distance` | number | number (default 350) |
| `peak_prominence` | number | **removed** |

## Behaviour by image type

- `rhythm-circles`: the peaks are measured with `peak_distance` and the fixed 20% and turned into the four circles of the tempo finder (the current tempo and the local peak, each with its rate of change) (see [data-model.md](../data-model.md)).
- `decay`, `decay-exp`, `polar-chords`, `chromatic-decay`, `chromatic-wireframe`, and `contour` with `beat_coloring`: measured with `peak_distance` and the fixed 20%; read as before (position in the local peak).
- `energy-graphs`, and `contour` without `beat_coloring`: not measured, as before.

## Internal contract (`backend/app/services`)

- `tempo_finder.find_tempo(times) -> TempoTrack`: `times` strictly increasing finite seconds; returns `tempos` (float64, one per time, each from 60 to 156) and `restarts` (int). Raises `ValueError("The peak times must be a 1-D array of finite numbers in strictly increasing order.")` for anything else. Pure and deterministic.
- `rhythm_circles.peak_series(times, tempos)` keeps its signature; it now returns the columns of the data model (it calls `find_tempo` on `times`). `rhythm_angles(peaks, frame_rate, frames)` and `write_rhythm_frames` keep theirs.
- `local_peaks.DEFAULT_MIN_DISTANCE == 350`; `measure_local_peaks(..., prominence=20)` default; `check_min_distance`/`check_prominence` unchanged.
