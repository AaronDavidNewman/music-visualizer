# Data Model: Spirograph

Everything is numpy arrays and two small settings classes; nothing is stored. Aliases live in
`backend/app/services/array_types.py` (the constitution's rule II): four are new, one is reused.

## Settings

**`SpirographSettings`** (frozen dataclass, `spirograph.py`)

| Field | Type | Allowed | Default |
|---|---|---|---|
| `notes` | `int` | whole number 5 to 12 (a bool, a string, a fraction or a non-finite number is refused) | 8 |
| `history` | `int` | whole number 5 to 12 (the same) | 8 |
| `fade` | `float` | number 0.4 to 0.85 (a bool, a string or a non-finite number is refused) | 0.7 (also the dataclass default) |

`check_spirograph_settings(settings)` returns the settings with both values checked (whole numbers as `int`); anything that is
not a `SpirographSettings` is refused. `DEFAULT_SPIROGRAPH_SETTINGS = SpirographSettings(8, 8, 0.7)`. `check_spirograph_fade(value) -> float` checks the third.

## Constants (not settings)

`RC = 5.0` (the big circle when the frame is closer to the peak than to the bottom; `RC - 1` otherwise), `COLOR_BINS = 12`, `CURVE_STEPS = 1000`, `SMALL_TURNS = 7` and
`MIN_TURNS = 6` (`turns = 2 x 7 x pct + 6`, 6 to 20), `LETTERS = 12` (the loops follow `index mod 12`),
`NOTE_COLUMNS = 84`, `VALUE_FACTOR = 12` (`yval = 12 val`, the color), `MARGIN = 10` pixels, `MAX_LINE_WIDTH = 5` (the newest entry, whatever the history) and
`MIN_LINE_WIDTH = 1` pixel (the oldest entry; every older one is at most 4), `MIN_SIZE_DIVISOR = 4`, `BACKGROUND_COLOR = (0, 0, 0)`, `DPI = 100`, `POINTS_PER_INCH = 72`.

## Arrays

| Alias | Shape | Meaning | Made by |
|---|---|---|---|
| `TrackedValues` (new) | `(frames, count)` `float64` | the value of each tracked note in each frame: the square root of its strength over the largest strength of the whole file, 0 to 1, loudest first; 0 for a place with no sounding note (so nothing is drawn for it) | `spirograph.tracked_notes` |
| `LoudestIndices` (reused) | `(frames, count)` `intp` | the index (0 to 83) of the note at each place of each frame, loudest first, held notes among them; a place with no sounding note holds a note whose strength is 0 | `held_notes.hold_loudest` (through `spirograph.tracked_notes`) |
| `ReducedColors` (new) | `(13, 3)` `uint8` | the 13 colors of the colormap at `sqrt(k / 12) x 256`, `k` 0 to 12: red, green, blue 0 to 255 | `spirograph.reduced_colors` |
| `ColorNumbers` (new) | `(curves,)` `intp` | which of the 13 reduced colors each curve takes: `min(floor(12 val), 12)`, 0 to 12 | `spirograph.color_numbers` |
| `PeakPercents` (new, 2026-11-24) | `(frames,)` `float64` | how near each frame is to the top of the local energy peak: `1 - beat_distances(beat)`, 1 at the top, 0 at the bottom (all 1 without a beat); above 0.5 is closer to the peak | `spirograph.peak_percents` |
| `CurveTurns` (new, 2026-11-24) | `(curves,)` `float64` | the turns of the small circle of each curve, `2 x 7 x pct + 6`, 6 to 20, not rounded | `spirograph.turns_of` |
| `BigRadii` (new, 2026-11-24) | `(curves,)` `float64` | the radius `rc` of the big circle of each curve: 5 above `pct` 0.5, else 4 | `spirograph.big_radii` |
| `CurveExtents` (new, 2026-11-24) | `(curves,)` `float64` | the farthest point of each curve, `val (rc + (index mod 12) val)`, in units | `spirograph._extents` |
| `CurveWidths` (new, 2026-11-24) | `(curves,)` `float64` | the line width in pixels of each curve: 5 (the picture's own frame), at most 4 for an older entry, down to 1 (the oldest place of the history), whole numbers | `spirograph.window_curves` |
| `SpiroCurves` (new) | `(curves, 1000, 2)` `float64` | the points `(X, Y)` of each curve: in units (the formula's, centered on 0, Y up) from `spiro_curves`, in pixels (from the top left, y down) from `window_curves` | `spirograph.spiro_curves`, `spirograph.window_curves` |

`Pictures` `(height, width, 3)` `uint8` and `Rgb` `(3,)` already exist and are used for the drawing.

## Entities and how they relate

- **History entry** `e` of frame `t`: row `e` of `TrackedValues` and of `LoudestIndices`; the picture of frame `t` uses the rows
  `max(0, t - history + 1)` to `t`, oldest first, the values of row `e` multiplied by `fade ** (t - e)` (the indices not). (The window is `history` rows long once `t >= history - 1`.)
- **Curve** `(i, j)`: entry `i` of the window (0 oldest), place `j` (0 loudest): `val = TrackedValues[row, j]`,
  `index = LoudestIndices[row, j]`, `loops = (index mod 12) val`, `pct = PeakPercents[row]`, `rc = 5 if pct > 0.5 else 4`,
  `turns = 14 pct + 6`; drawn only when `val > 0`. Its color is `ReducedColors[color_numbers(val)]`.
- **Extent** of a file: `max over all rows and places of val x (rc + (index mod 12) x val)` with the `rc` of the row's frame; 0 when nothing sounds. **Scale** (pixels a
  unit): `full_radius / extent`, `full_radius = min(width, height) / 2 - MARGIN - MAX_LINE_WIDTH`. **Size of a curve** (its farthest
  point from the center): `smallest_radius + (full_radius - smallest_radius) * min(1, ext x scale / full_radius)`, `smallest_radius =
  min(width, height) / 4`; **line width** of a curve: `entry_line_width(age, history)`, 3 for the newest entry and 2 down to 1 for the older.

## Functions (all in `spirograph.py`; signatures are the plan's, typed, with array aliases)

```text
check_spirograph_notes(value: object) -> int
check_spirograph_history(value: object) -> int
check_spirograph_settings(settings: object) -> SpirographSettings
tracked_notes(values: ArrayLike, count: int, extra: int = 0) -> tuple[TrackedValues, LoudestIndices]
reduced_colors(colormap: str) -> ReducedColors
color_numbers(values: ArrayLike) -> ColorNumbers
peak_percents(beat: ArrayLike | None, frames: int) -> PeakPercents            # 1 - beat_distances; 1 without a beat
turns_of(percents: ArrayLike) -> CurveTurns                                    # 6 .. 20
big_radii(percents: ArrayLike) -> BigRadii                                     # 5 above 0.5, else 4
spiro_curves(values: ArrayLike, indices: ArrayLike, percents: ArrayLike | None = None) -> SpiroCurves   # units
file_extent(values: ArrayLike, indices: ArrayLike, percents: ArrayLike | None = None) -> float           # units
pixels_per_unit(extent: float, width: int, height: int) -> float
entry_line_width(age: int, history: int) -> int                                # 5, then 4 .. 1, rounded half up
full_radius(width: int, height: int) -> float                                  # pixels
smallest_radius(width: int, height: int) -> float                              # pixels: a quarter of the smallest side
window_curves(values: ArrayLike, indices: ArrayLike, frame: int, history: int, scale: float, width: int, height: int,
                  fade: float = 0.7, percents: ArrayLike | None = None) -> tuple[SpiroCurves, ColorNumbers, CurveWidths]
                                                                               # pixels, oldest first, val > 0 only
_frame(curves: SpiroCurves, colors: ArrayLike, width: int, height: int, widths: ArrayLike | None = None) -> Pictures
write_spirograph_frames(values: ArrayLike, settings: SpirographSettings, colormap: str, directory: Path,
                        width: int, height: int, extra_notes: int = 0, beat: ArrayLike | None = None) -> None
```

## Validation rules (from the spec)

- Number of notes and History length: whole numbers 5 to 12; History fade: a number 0.4 to 0.85 (FR-009); refused before the file is read, no files left.
- Values: finite, not negative, at least 84 columns (`VALUES_MESSAGE`, as Polychord's).
- A curve with value 0 draws nothing (FR-006); silent frames give black pictures; the first `history - 1` frames use the rows
  that exist (FR-003).
- A picture too small for the margin and one-pixel lines is refused (`SIZE_MESSAGE`), as Polychord refuses one.
