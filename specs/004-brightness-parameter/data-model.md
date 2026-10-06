# Data Model: Brightness Parameter

Only the changes and additions to features 001 to 003 are listed.

## Constants

| Name | Value | Meaning |
|------|-------|---------|
| `MIN_BRIGHTNESS` | 2 | Lowest allowed brightness; also the default (`DEFAULT_BRIGHTNESS`) |
| `MAX_BRIGHTNESS` | 100 | Highest allowed brightness |

Fixed by the spec; not settings.

## Brightness (request field)

| Field | Type | Rules |
|-------|------|-------|
| `brightness` | text parsed as a number, optional | Field absent: 2. Present: must be a whole number from 2 to 100 (a value like `5.0` counts as 5). An empty string, `2.5`, `abc`, `nan`, `inf`, `1` and `101` are refused. |

## Display mapping

| Name | Definition | Notes |
|------|------------|-------|
| `level` | Integer 0..255: `round(255 × value / file_max)` | Unchanged from feature 002 |
| `displayed level` | `round(255 × (level / 255)^(1 / brightness))` | Computed once per level into a 256-entry `uint8` table for each brightness; the table is what is applied to each frame |
| Guarantees | `displayed(0) = 0`; `displayed(255) = 255`; non-decreasing in `level`; non-decreasing in `brightness` | Tested over all 256 levels and all 99 brightness values |

Example, level 64: brightness 2 → 128, 3 → 161, 4 → 180, 10 → 222, 100 → 251.

## Submission result (addition)

| Field | Type | Meaning |
|-------|------|---------|
| `brightness` | integer | The brightness used (2 when none was given) |

All other fields are unchanged. Brightness does not change `frame_count`, `window_count`, `window_spacing`, `step_samples` or any frame timing.

## Client state (frontend additions)

| State | Meaning |
|-------|---------|
| `brightnessText` | The text in the brightness field. Starts at `2`. Kept after errors and completed submissions. Not recalculated when other fields change. |

The submit event now carries `(file, settings)` where `settings` is `{ windowSize, frameRate, windowSpacing, brightness }`.
