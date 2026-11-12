# Contract: Rhythm Circles

## 1. Library (backend/app/services/rhythm_circles.py)

```python
CIRCLES = 8
DEFAULT_SPEEDS = (60.0, 0.0) * 4   # revolutions per minute before the first peak
NOTCH = 1 / 8                                          # of a turn

def peak_series(times, tempos) -> np.ndarray
    # (P,) seconds (strictly increasing), (P,) beats per minute -> (P, 8) revolutions per minute: aggregate of 8, its change, aggregate of 4, its change, aggregate of 2, its change, tempo, its change (an aggregate is the mean or the max of the latest tempos, whichever is closer to the peak's own tempo; the max when equally close).
    # ValueError for different lengths, a 2-D array, non-finite values, times not increasing, a tempo not above 0. P = 0 gives (0, 8).

def circle_speeds(times, series, moments) -> np.ndarray
    # (len(moments), 8): the row of the latest peak at or before each moment; DEFAULT_SPEEDS before the first peak and with no peaks.

def circle_angles(times, series, moments) -> np.ndarray
    # (len(moments), 8) turns, unwrapped: the running total of speed / 60 over time from 0; continuous.

@dataclass(frozen=True)
class RhythmData:
    angles: np.ndarray        # (frames, 8) turns
    frame_count: int          # property

def rhythm_angles(peaks: LocalPeaks, frame_rate, frames) -> RhythmData
    # the angles at the middle of every frame ((f + 0.5) / frame_rate seconds) from the peaks and their rates.

def write_rhythm_frames(data: RhythmData, colormap, directory, width, height) -> None
    # one PNG per frame, frame_000000.png and up, RGB width x height; everything checked before anything is written (ValueError for bad data, colormap, size).
```

### `frame_rendering.write_frames`

`write_frames(..., rhythm: RhythmData | None = None)`: for `image_type == "rhythm-circles"`, `rhythm` is required (`ValueError("Rhythm Circles needs the rhythm data.")`), its `frame_count` must equal `len(frames)` (`ValueError`), and the frames are written by `write_rhythm_frames`; every other setting is checked and ignored. For other types `rhythm` is ignored.

### `image_types`

`IMAGE_TYPES` ends with `"rhythm-circles"` (after `"chromatic-decay"`); the message of `check_image_type` lists it.

## 2. HTTP

`POST /api/jobs` (existing). `image_type=rhythm-circles` is accepted. **No new request field and no new response field.** The local peaks are measured with the request's `peak_distance` and `peak_prominence` (validated before the file is read, with their messages, as for every type). The response echoes `image_type: "rhythm-circles"`. A bad image type is refused with 400 `The image type must be one of tiles, blended, contour, circles, circles_paint, concentric, decay, decay-exp, polar-chords, energy-graphs, chromatic-decay, rhythm-circles.` Every other setting is validated as always and ignored. The frames and the movie export (feature 029) work as for every type.

## 3. The picture (600 x 400, RGB)

On the colormap's middle color: eight rings centered at (300, 200), outer radius 190 px, each ring 23.75 px less a 4 px gap, outer to inner; ring `k` is the colormap row `rint((k-1)/7 x 255)`, its notch (an arc of 45 degrees, centered at `theta = angle mod 1` turns clockwise from straight up) the row `rint((1 - (k-1)/7) x 255)`; smooth edges; frames identical for identical input.
