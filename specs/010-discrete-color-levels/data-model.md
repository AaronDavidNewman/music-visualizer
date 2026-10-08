# Data Model: Discrete Color Levels

Only what changes from the frame colors of features 007, 009 and the brightness/saturation swap is listed.

## Constants

| Name | Value | Where | Meaning |
|------|-------|-------|---------|
| `HUE_SCALE` | 360 | `color_levels.py` | Size of the hue scale (degrees) |
| `UNIT_SCALE` | 100 | `color_levels.py` | Size of the saturation and brightness scales |
| `HUE_STEPS` | 12, 36, 90, 180 | `color_levels.py` | Allowed hue steps (besides N/A) |
| `UNIT_STEPS` | 5, 10, 20, 50 | `color_levels.py` | Allowed saturation and brightness steps (besides N/A) |

Frontend: the same lists and scales in `validation.ts` (`HUE_STEPS`, `UNIT_STEPS`, `HUE_SCALE`, `UNIT_SCALE`), plus `DEFAULT_STEP = "N/A"`.

## Step

One per property: `hue_step`, `saturation_step`, `brightness_step`. Each is either N/A (no rounding; `None` in the backend, `null` in JSON, the text `N/A` in forms and in the dropdown) or one number from its list. Default N/A.

## Number of levels

`N = round((scale + step) / step)`, halves up. Because each allowed step divides its scale, `N = scale / step + 1`.

| Property | Scale | Step | Levels `N` | The levels |
|----------|-------|------|-----------|------------|
| Hue | 360 | 12 | 31 | 0°, 12°, 24° … 360° |
| Hue | 360 | 36 | 11 | 0°, 36° … 360° |
| Hue | 360 | 90 | 5 | 0°, 90°, 180°, 270°, 360° |
| Hue | 360 | 180 | 3 | 0°, 180°, 360° |
| Saturation, Brightness | 100 | 5 | 21 | 0, 5, 10 … 100 |
| Saturation, Brightness | 100 | 10 | 11 | 0, 10 … 100 |
| Saturation, Brightness | 100 | 20 | 6 | 0, 20, 40, 60, 80, 100 |
| Saturation, Brightness | 100 | 50 | 3 | 0, 50, 100 |

N is never fewer than 3, and the top of the scale is always a level.

## Rounding

For a finished value `x` on the 0 to 1 scale (hue as a fraction of the wheel, saturation, frame brightness), a scale `R` and a step `s`:

```
k = floor(x * R / s + 0.5 + 1e-9)       # nearest level index, halves go up
x' = min(k * s, R) / R                   # back to the 0..1 scale
```

With N/A, `x' = x`. Properties: `0` stays `0` and `1` stays `1` (so a black tile stays black and the loudest frame keeps full brightness); `x'` is non-decreasing in `x`; it depends only on `x`, never on other tiles or frames.

Examples: saturation 0.50 with step 20: `0.5 * 100 / 20 + 0.5 = 3.0` → level 3 → 60 → 0.6. Saturation 0.49 → `2.95` → 2 → 40. Hue fraction 6/360 with step 12: `0.5 + 0.5 = 1.0` → level 1 → 12° (the `1e-9` makes this hold even when the product is 5.999999999999999 before halving).

## Where rounding happens in the color pipeline

For each frame, in `write_frames`:

1. Note values are smoothed and scaled to gray levels (unchanged).
2. **Hue**: `hue_sequence` (related-note shifts, then smoothing over frames) → **round with `hue_step` on the whole `(frames, 84)` array**.
3. **Saturation**: each tile's boosted gray level / 255 (the Saturation root) → **round with `saturation_step` inside `tile_colors`**.
4. **Brightness**: `value_sequence` (energy, root, smoothing) → **round with `value_step`** (the API's `brightness_step`).
5. HSV → RGB with the rounded values; palette PNG as before.

A tile whose brightness is 0 is black whatever its rounded hue and saturation are (HSV with value 0).

## API field to code name

| Page label | API field (request and response) | `write_frames` argument |
|------------|----------------------------------|-------------------------|
| Hue steps | `hue_step` | `hue_step` |
| Saturation steps | `saturation_step` | `saturation_step` |
| Brightness steps | `brightness_step` | `value_step` |

Not to be confused with the existing `brightness` field (the page's Saturation root) and `energy` field (the page's Brightness root), which are unchanged.

## Frontend settings and result

`JobSettings` gains `hueStep`, `saturationStep`, `brightnessStep`: `number | null` (null = N/A). `JobResult` gains `hue_step`, `saturation_step`, `brightness_step`: `number | null`. The form sends `N/A` or the number as text.
