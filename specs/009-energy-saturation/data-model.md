# Data Model: Energy Saturation

Only what changes from the frame images of features 002 and 004 to 008 is listed.

## Constants

| Name | Value | Where | Meaning |
|------|-------|-------|---------|
| `INTERNAL_WINDOW_AT_44K` | 32 | `energy.py` | Samples in the internal window at 44,100 Hz |
| `REFERENCE_RATE` | 44100 | `energy.py` | The rate that the 32 refers to |
| `MIN_ENERGY` / `MAX_ENERGY` | 1 / 8 | `frame_rendering.py` | Allowed energy roots (whole numbers) |
| `DEFAULT_ENERGY` | 1 | `frame_rendering.py` | Root used when none is given |
| `DEFAULT_SATURATION` | 0.5 | `frame_rendering.py` | Saturation used only by helpers called without one (replaces the old fixed `SATURATION`); the job path never uses it |

Frontend: `ENERGY_RANGE = { min: 1, max: 8 }`, `DEFAULT_ENERGY = 1` in `validation.ts`.

## Internal window

`w(rate) = max(2, floor(32 × rate / 44100 + 0.5))`

| Sample rate (Hz) | 44,100 | 48,000 | 22,050 | 11,025 |
|------------------|--------|--------|--------|--------|
| `w` | 32 | 35 | 16 | 8 |

## Frame period

For frame `f` (0-based) of `N = ceil(samples × frame_rate / rate)` frames:
`start_f = rint(f × rate / frame_rate)`, `end_f = min(rint((f + 1) × rate / frame_rate), samples)`. The frames tile the file with no gap or overlap.

## Energy of a frame

1. Samples are converted to the common scale (about −1 to 1) by the analysis's existing conversion.
2. `n = (end_f − start_f) // w` full internal windows, laid end to end from `start_f`; a leftover shorter than `w` is ignored.
3. For each window `j`, `σL[j]` and `σR[j]` are the population standard deviations (`ddof = 0`) of the left and right samples; `s[j] = (σL[j] + σR[j]) / 2`. A mono file has the same signal in both channels.
4. `E_f = mean(s[0..n−1])`.
5. If `n = 0` (the frame holds fewer than `w` samples, such as a short final frame), the samples it has are measured as a single window; with 0 or 1 samples `E_f = 0`.

Worked values: both channels alternating +0.5 and −0.5 gives `E = 0.5`; left alternating ±0.5 and right silent gives `0.25`; a constant level gives `0`; a mono signal gives its own spread.

## Saturation of a frame

Given `E_0 … E_{N−1}`, the energy root `r` (whole number 1 to 8) and the smoothing `m` (0.0 to 0.8):

| Step | Definition |
|------|------------|
| Peak | `P = max(E_f)` |
| Mapped | `q_f = (E_f / P) ** (1 / r)` if `P > 0`, else `0` |
| Smoothed | `q'_0 = q_0`; `q'_f = m × q'_{f−1} + (1 − m) × q_f`. With `m = 0`, `q'_f = q_f`. |
| Saturation | `S_f = q'_f`, in 0 to 1, the same for all 84 tiles of frame `f` |

For `E_f / P = 0.25`: `S = 0.25, 0.50, 0.630, 0.841` at `r = 1, 2, 3, 8`. The loudest frame is always `1.0` and a frame with no energy is `0.0` (before smoothing).

## Tile color (for each drawn tile `n = 0..83` in frame `f`)

| Component | Definition |
|-----------|------------|
| Hue | Unchanged from feature 007 (`tile_hues`, smoothed by `hue_sequence`) |
| Value | Unchanged: the tile's displayed gray level divided by 255 |
| Saturation | `S_f` (was the fixed 0.5) |
| RGB | `colorsys.hsv_to_rgb(hue, S_f, value)`, each channel × 255 and rounded (halves to even) |

At `S_f = 1` the darkest channel is 0; at `S_f = 0` all channels are equal to the value; the brightest channel always equals the tile's displayed gray level.

## Job settings and result

| Field | Direction | Type | Rule |
|-------|-----------|------|------|
| `energy` | request (optional form field) | text → whole number | 1 to 8; missing means 1; sent but empty or invalid is refused (400) |
| `energy` | response | integer | The root used |

`JobSettings.energy` and `JobResult.energy` in the frontend carry the same value. Nothing else in the request or response changes.

## Entities

- **Internal window**: `w` samples of one channel; no stored form.
- **Energy**: one non-negative number per frame; not stored or returned, only used to draw the frame.
- **Saturation**: one number from 0 to 1 per frame; not stored, only used to draw the frame.
