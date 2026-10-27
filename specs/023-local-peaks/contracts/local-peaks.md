# Contract: The local_peaks measurement (Python interface)

The measurement is a library in the backend: **no HTTP endpoint, no request field and no page control is added** (the clarification). This is the interface that later features will call. Module: `app.services.local_peaks`.

## Functions

```python
def check_min_distance(value) -> float      # 100 to 2000 (milliseconds), else ValueError
def check_prominence(value) -> float        # 0 to 100 (percent), else ValueError

def impulse_energy(left, right) -> np.ndarray
    # one float64 per 32 samples: (std(left window) + std(right window)) / 2

def measure_local_peaks(
    left, right, file_rate: int,
    min_distance: float = 100.0, prominence: float = 50.0,
    window: int = 4096,
) -> LocalPeaks

def window_zones(count: int, window: int)
    # yields (start, end, low, high): each peaks window and the zone [low, high) it owns; the zones tile [0, count)

def measure_wav(path, min_distance: float = 100.0, prominence: float = 50.0,
                display_name: str | None = None) -> LocalPeaks
    # read_wav(path, display_name) then measure_local_peaks
```

## `measure_local_peaks`

| Parameter | Rule |
|-----------|------|
| `left`, `right` | 1-D arrays of the same length (any real numeric dtype; integer PCM is scaled to about -1 to 1 as in the note analysis, so the bit depth does not matter; floats are used as they are); mono callers pass the same array twice |
| `file_rate` | Positive whole number, samples per second |
| `min_distance` | Milliseconds, 100 to 2000, default 100 |
| `prominence` | Percent, 0 to 100, default 50 |
| `window` | Peaks window in impulse samples, default 4096; the result does not depend on it for well-separated peaks |

Returns a `LocalPeaks`. Raises `ValueError` (with the messages of the data model) for a setting or input outside the rules, before any measuring. A silent or very short input returns a measurement with no peaks.

Guarantees:

- Peaks are ordered by `sample`, none twice, and no two are closer than the minimum distance (to within one impulse window).
- The call passes `distance` (impulse samples, `max(1, round(ms/1000 × rate / 32))`) and `prominence` (`percent/100 ×` the window's largest energy) to `scipy.signal.find_peaks`.
- The same input and settings always give an equal result; the inputs are not modified.
- The existing note analysis and the frames of every image type are unchanged.

## `LocalPeaks`

```python
@dataclass(frozen=True)
class LocalPeak:
    sample: int; energy: float; window_min: float; window_max: float; rate: float

@dataclass(frozen=True)
class LocalPeaks:
    peaks: tuple[LocalPeak, ...]
    file_rate: int; sample_count: int; min_distance: float; prominence: float

    def energy_at(self, point): ...         # samples
    def rate_at(self, point): ...           # samples
    def energy_at_time(self, seconds): ...
    def rate_at_time(self, seconds): ...
```

| Call | Answer |
|------|--------|
| `energy_at(p)`, `p` at a peak's `sample` | That peak's `energy` |
| `energy_at(p)`, `p` between peaks `a` and `b` | `a.energy + (b.energy − a.energy) × (p − a.sample) / (b.sample − a.sample)` |
| `energy_at(p)`, `p` before the first peak (including negative) | `0.0` |
| `energy_at(p)`, `p` after the last peak (including past the end) | The last peak's `energy` |
| `rate_at(p)` | The `rate` of the last peak with `sample ≤ p`; `60.0` if there is none |
| any call with no peaks | energy `0.0`, rate `60.0` |
| `*_at_time(t)` | `*_at(t × file_rate)` |
| a sequence or array | An array of the same shape (float64); a scalar gives a Python `float` |
| a NaN or infinite point | `ValueError("The point must be a finite number.")` |

## Not part of this contract

The job endpoint (`POST /api/jobs`), its response, the frames and the settings page are untouched; how the energy and rate are used in the pictures is a later feature.
