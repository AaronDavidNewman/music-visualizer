# Research: Contour Beat Wave

No `[NEEDS CLARIFICATION]` remains; the interpretations the spec made are in its Assumptions. Facts about the code were read from the repository.

## What exists today

- `contour.write_contour_frames(values, peak, colormap, directory, columns, rows, width, height, indices)` draws, for each frame, `Z = frame.reshape(rows, columns)[::-1]` (a copy), smooths it in place with `directionalSmoothing`, picks `levels = np.linspace(Z.min(), Z.max(), 12)` and calls `contourf(x, y, Z, levels=levels, cmap=colormap, vmin=0, vmax=top)` with `top = frame.max()`. A frame with `peak <= 0` or `frame.min() == frame.max()` is written flat. matplotlib is imported only when a contour is drawn, inside a lock.
- `write_frames` computes `values = interpolate_grid(shown, 12, 7, resolution)` (so `rows = 7r`, `columns = 12r`), hides notes below the threshold with `values[hidden] = 0`, and calls `write_contour_frames(..., indices=frames_to_draw)`; `beat` (feature 024) is already checked for every type with `check_beat` and used by `tiles` and `blended` only.
- `jobs.py` parses `beat_coloring`, `peak_distance`, `peak_prominence`, measures the beat when the type is concentric/decay or (`beat_coloring` and tiles/blended), echoes every setting.
- Frontend: `beatColoringApplies(type)` (tiles, blended) decides the Local peaks group with the checkbox (`groupsFor`), the summary lines (`peakSettingsShown`) and the form; the `contour` group has `threshold`, `notes`.

## Decision 1: The rule is a pure module; the pattern is cached per grid and wave count

- **Decision**: `beat_wave.py` with `MIN_WAVE_COUNT = 2`, `MAX_WAVE_COUNT = 10`, `DEFAULT_WAVE_COUNT = 4`, `check_wave_count(value) -> int`, `wave_pattern(rows, columns, waves)` (`lru_cache`, read-only float64 array of shape `(rows, columns)`) and `wave_modifier(rows, columns, waves, k) -> 1 − pattern × sin(π × k)`. The pattern is `(sin(waves × 2π × sqrt(distance ÷ largest)) + 1) ÷ 2`, with `distance = hypot(x − (columns − 1)/2, y − (rows − 1)/2)` for the column `x` and row `y` (from 0) and `largest = max(rows, columns)`. **Revised 2026-10-30** (the user's change): the first version used `distance ÷ largest` without the square root and `1 − pattern × k`; the square root lowers the frequency of the rings towards the outside, and `sin(π × k)` makes the effect swell and fade smoothly over the beat (nothing at `k = 0`, deepest at `k = 0.5`, all but nothing at `k = 1`) instead of rising to a maximum at the top.
- **Rationale**: The user's formula, with their "adjusted for the center" and "mapped from −1…1 to 0…1". The center is the geometric center, `(n − 1) / 2` on each axis (an even-sized axis has it between two points), so the picture's pattern is symmetric and has the same place at every oversampling. The pattern depends only on the grid and the count, so it is worked out once per job; a frame costs one multiply-subtract. A separate pure module is testable without matplotlib and keeps `contour.py`'s lazy import.
- **Alternatives considered**: working the pattern out inside the frame loop (needless repeated trigonometry); putting it into `contour.py` (the unit tests would then import matplotlib's module and need the drawing lock); distance measured in picture pixels (the spec says grid points, and the 12 × 7 grid then gives ellipses in the picture, as the user's `sqrt(x**2 + y**2)` implies).

## Decision 2: Where in the frame the wave is applied

- **Decision**: In `write_contour_frames`, per frame: if `beat` is given and `k > 0`, `Z = Z * wave_modifier(rows, columns, waves, k)` **after** `directionalSmoothing` and **before** the levels are chosen. `top` (the coordinates and `vmax`) is still `frame.max()` of the unmodified frame. The pattern is symmetric under the reversal of the rows (`[::-1]`), so its orientation does not matter.
- **Rationale**: The spec asks for the values to be multiplied before the contour is drawn and for the scale to be the pre-wave one. Doing it after the existing smoothing keeps that (idiosyncratic) smoothing exactly as it is and makes the rings crisp instead of smoothing them with the note values; the levels are then chosen from the modified `Z` (as today they are from the smoothed `Z`), so the 12 bands span the range that is actually drawn, and `vmax` keeps the color of a value as in the plain picture.
- **Alternatives considered**: multiplying before the smoothing (the smoothing would blur the rings, and its tests on differences would change); scaling the color by the modified maximum (cancels the dimming, hides the effect: against the spec).

## Decision 3: `k = 0` and degenerate results are handled so the plain picture is exact

- **Decision**: When `k == 0` (or no beat is given) the multiplication is skipped, so the frame is byte-identical to the plain one. After the multiplication, if `Z.min() == Z.max()` (nothing left to draw: for example all values 0) the frame is written flat with `_flat_frame(colormap, Z.flat[0], top, …)` instead of calling `contourf` with identical levels (which fails). A frame that is flat before the wave stays flat whatever `k` is (the existing check on `frame` comes first). At `k = 1` the modifier is `1 − pattern × 1.2e-16` (`sin(π)` is not exactly 0), so the frame is multiplied but is the plain picture to within rounding.
- **Rationale**: Byte identity at the minimum of the beat is the main promise of the feature (SC-001); `contourf` refuses equal levels. Using `top` as the scale for the flat color keeps a flat result consistent with the colored frames around it.
- **Alternatives considered**: always multiplying by `ones` at `k = 0` (the floats would be identical but the guarantee would depend on it); catching matplotlib's error (hides other problems).

## Decision 4: The existing checkbox switches the wave; the beat is measured exactly then

- **Decision**: `jobs.py` measures the beat when `beat_coloring` is true and the type is `tiles`, `blended` or `contour` (or when the type is `concentric` or `decay` as before); `write_frames` passes `beat` and `wave_count` to the Contour drawing and ignores `wave_count` for the other types. `wave_count` is parsed like the other whole-number fields (`_parse_wave_count`, message `The wave count must be a whole number from 2 to 10.`, not sent → 4), checked before the file is read for every type, and echoed as `wave_count`.
- **Rationale**: The spec (FR-006, FR-007): no new switch, nothing changes for the other types, the beat is not measured with the box off. The checks and the echo follow `decay_rate` (feature 027).
- **Alternatives considered**: a separate checkbox for the wave (two checkboxes for one measurement, and the spec says the existing one); letting the wave count itself turn the wave on (a hidden switch).

## Decision 5: The page treats Contour as a beat type with one more slider

- **Decision**: `beatColoringApplies` is true for `tiles`, `blended` and `contour`, so `groupsFor("contour")` is `analysis, colormap, image-type, contour, local-peaks, data-smoothing, image-smoothing`; the `contour` group's controls are `threshold`, `notes`, `wave-count`; `waveCountApplies(type)` is true for `contour` only; the Wave count slider is shown whenever the Contour group is shown (it simply has no effect while the box is off, as the spec says) with the readout `4 waves`; the summary shows `Beat coloring` for Contour as for the tiles, and `Wave count` when the type is Contour and the box is on. `note-layout` stays off for Contour (it always has the rows layout).
- **Rationale**: Reuses the existing rules (`beatColoringApplies` already drives the group, the summary and the form), so only the one new control and one summary line are new.
- **Alternatives considered**: hiding the slider while the box is off (the spec lists the control in the Contour group; hiding would make the layout jump); a new group for the wave (one control does not need a group).

## Notes for the tests

- The grid handed to matplotlib is observed by wrapping `contourf` (a spy on `matplotlib.axes.Axes.contourf` that records `Z`, `levels` and `vmax` and calls the real one), so the tests compare numbers, not pictures; the pictures are compared only for byte identity (checkbox off, `k = 0`).
- The pattern at known points: the exact center of an odd grid has distance 0 and pattern 0.5; the first extremum (pattern 1) of the sine is at `distance = largest ÷ (16 × waves²)`.
