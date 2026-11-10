# Contract: Energy Graphs

Three interfaces: the library functions, the HTTP request and the picture. *(Revised 2026-11-08: no pies, no `rest` in the analysis; two data sets and a softmax.)*

## 1. Library (backend/app/services)

### `energy_graphs`

```python
def rank_scores(values) -> np.ndarray
    # (windows, >=84) note strengths -> (windows, 84) int64 scores, 84 for the loudest sounding note ... , 0 for silence.
    # ValueError for a non-2-D array, fewer than 84 columns, a negative or non-finite value.

def quasi_db(values, peak=None) -> np.ndarray
    # (windows, >=84) -> (windows, 84) float64: 20 log10(a) / (20 log10(peak)) clamped at 0; 0 for silence; all 0 when peak <= 1.
    # peak defaults to the largest of the 84 columns; ValueError for a bad peak (negative, not finite, bool) or bad values.

def softmax_shares(totals) -> np.ndarray
    # (rows, n) totals >= 0 -> same shape; each row divided by its largest value and softmaxed; a row with no total is all 0.

def above_smallest(shares) -> np.ndarray
    # (rows, n) shares >= 0 -> same shape, each row minus its smallest value (the smallest becomes 0); an all-equal or all-0 row becomes all 0.

def frame_energy(result: AnalysisResult, frame_rate: float, frames: int) -> EnergyGraphData
    # frames == 0 or no windows -> arrays with `frames` rows of zeros. Deterministic.

@dataclass(frozen=True)
class EnergyGraphData:
    histogram: np.ndarray   # (frames, 84) int64, the rank totals
    amplitude: np.ndarray   # (frames, 84) float64, the quasi-dB totals
    frame_count: int        # property

def write_energy_frames(data: EnergyGraphData, colormap: str, directory: Path, width: int, height: int) -> None
    # one PNG per frame, frame_000000.png and up, RGB, width x height. Everything is checked before anything is written
    # (ValueError for a bad colormap, size or data). Only the 600 x 400 layout is specified (see 3); other sizes scale it.
```

### `frame_rendering`

- `frame_windows(result, frame_rate, frames) -> (first, stop, earlier)`: `average_frames` uses it, its output is unchanged.
- `write_frames(..., energy: EnergyGraphData | None = None)`: for `image_type == "energy-graphs"`, `energy` is required (`ValueError("The energy graphs need the energy data.")`), its `frame_count` must equal `len(frames)` (`ValueError`), and the frames are written by `write_energy_frames`; all other settings are checked and ignored. For other types `energy` is ignored.

### `image_types`

`IMAGE_TYPES` ends with `"energy-graphs"`; the message of `check_image_type` lists it. `note_analysis` is **not changed** by this feature.

## 2. HTTP

`POST /api/jobs` (existing). `image_type=energy-graphs` is accepted. **No new request field and no new response field.** The response echoes `image_type: "energy-graphs"`; `window_count`, `frame_count`, `frame_url_template` as for the other types. A bad image type is refused with 400 `The image type must be one of tiles, blended, contour, circles, circles_paint, concentric, decay, decay-exp, polar-chords, energy-graphs.` Settings that do not apply (smoothing, smoothing window, threshold, resolution, notes, interpolate, gaussian, layout, circle, decay, polar, peak and beat settings) are validated as always and ignored. The beat is not measured for this type.

`GET /api/jobs/{id}/frames/{index}` and the movie export (feature 029) work as for every type.

## 3. The picture (600 x 400, RGB)

Background: the middle color of the colormap (`MIDDLE_COLOR_ROW`). Text and outlines: black when the background's relative luminance is above 0.5, else white. All positions in pixels, from the top left.

| Element | Place | Content |
|---------|-------|---------|
| Title | left x 10, top y 10 | "Notes so far (softmax of the totals)" |
| Legend | right-aligned to x 590, y 10 | a square (9 px, outlined) in the **start** color and "frequency: rank points", then a square in the **end** color and "amplitude: quasi-dB" |
| Plot area | x 10 to 590, y 36 to 372 (336 px) | 84 slots at the nearest whole pixels of an even split of 580 px; each slot holds the **frequency bar** (start color) and, right next to it, the **amplitude bar** (end color), each `max(1, (slot width - 1) // 2)` px wide, so at least 1 px of background at the end of the slot |
| Bar height | | `round(336 * lifted / tallest)` px (at least 1 for a `lifted` above 0), standing on the baseline; `lifted` = the softmax share minus the smallest share of its data set (so the smallest bar of each data set has no height); `tallest` = the largest `lifted` of both data sets in the frame, so the tallest bar is 336 px in every frame that has a sound |
| Baseline | y 372, x 10 to 589 | a 1-pixel line in the text color |
| Octave labels | centered under every 12th slot, top y 377 | "A1" ... "A7" |

An empty graph (no sound yet) is the title, the legend, the baseline and the labels only. Frames are identical for identical input (same file, settings, library versions).
