# Contract: Chromatic Decay Threshold

## 1. Library (backend/app/services/chromatic_decay.py)

```python
MIN_THRESHOLD, MAX_THRESHOLD, DEFAULT_THRESHOLD = 0, 10, 0
THRESHOLD_MESSAGE = "The threshold must be a number from 0 to 10."

def check_threshold(value) -> float
    # a real number from 0 to 10 (bool, str, None, NaN, inf, below 0, above 10: ValueError(THRESHOLD_MESSAGE)); same answers as frame_rendering._check_threshold

def apply_threshold(values, threshold=DEFAULT_THRESHOLD) -> np.ndarray
    # (frames, >=84) smoothed note values -> a float64 copy where every value strictly below threshold / 100 x (the largest value of the whole array) is 0.
    # threshold 0 or an all-0 array: unchanged. ValueError as concentric._check_values for bad values, THRESHOLD_MESSAGE for a bad threshold.

def circle_points(values, beat=None, decay_rate=DEFAULT_RATE, threshold=DEFAULT_THRESHOLD) -> np.ndarray
def circle_tapers(values, beat=None, decay_rate=DEFAULT_RATE, threshold=DEFAULT_THRESHOLD) -> np.ndarray
    # as before, from apply_threshold(values, threshold); threshold=0 is exactly the earlier result.
```

`frame_rendering.write_frames(..., image_type="chromatic-decay", threshold=t)` passes `threshold` to `circle_points`.

## 2. HTTP

No new field. `threshold` (existing, 0 to 10, 0 off, message `The threshold must be a number from 0 to 10.`) now **applies** to `chromatic-decay`; the response echoes `threshold` as before; without it the frames are identical to before. Every other image type is unchanged.

## 3. The page

The Chromatic Decay group has two controls, **Decay rate** and **Threshold** (the existing slider: 0 to 10, readout Off then the percentage, the existing info popover); the result summary shows `Threshold:` for Chromatic Decay.
