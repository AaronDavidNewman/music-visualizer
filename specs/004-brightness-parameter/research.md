# Research: Brightness Parameter

No `NEEDS CLARIFICATION` items are open. These are the design decisions.

## Decision 1: The mapping

- **Decision**: `display = rint(255 × (level / 255)^(1 / brightness))` for integer `level` in 0..255 and integer `brightness` in 2..100. Brightness 2 is the existing square-root boost.
- **Rationale**: This is the formula the user gave. For `level / 255` between 0 and 1, a higher root gives a larger result, so a higher brightness is never darker (FR-007), and 0 and 255 map to themselves at every brightness (FR-006).
- **Alternatives considered**: A gamma value that can be fractional (the request says integer); a logarithmic curve (explicitly deferred as volume normalization).

## Decision 2: A lookup table, not a power call per frame

- **Decision**: `boost_levels(levels, brightness)` builds, and caches per brightness, a 256-entry `uint8` table from the formula, and applies it by indexing: `table[levels]`. The cache holds at most 99 small tables.
- **Rationale**: The input is already an integer level from 0 to 255, so there are only 256 possible outputs. Indexing is much cheaper than calling `power` on every frame, which matters with up to 30,000 frames per submission and keeps SC-006 safe. The table is also exactly the formula evaluated once per level, so a test can compare the table with the formula for every combination (99 × 256 values).
- **Alternatives considered**: Calling `np.power` per frame (works, slower); applying the formula once to the whole `(frames, 88)` array before rendering (works, but the user described `boost_levels` as the step inside rendering, and the per-frame call keeps the structure from feature 002).

## Decision 3: Where the setting is passed

- **Decision**: `brightness` is an argument of `boost_levels`, `render_frame` and `write_frames`, with the default 2 (`DEFAULT_BRIGHTNESS`). `MIN_BRIGHTNESS = 2` and `MAX_BRIGHTNESS = 100` are module constants in `frame_rendering.py`, used by the router for validation.
- **Rationale**: The default keeps existing callers and tests working unchanged. The range is fixed by the spec, so constants are the right form; the settings used for other limits are things a developer may want to tune, and this is not.
- **Alternatives considered**: Putting the range in `config.py` (invites changing a range the spec fixes); a global default read inside `boost_levels` (hidden state).

## Decision 4: Server validation and the empty value

- **Decision**: The router reads `brightness` as text. A missing field means 2. Any present value, including an empty string, must parse as a number that is a whole number from 2 to 100, otherwise 400 with `The brightness must be a whole number from 2 to 100.` Text that parses to a whole number with a decimal point (`5.0`) is accepted as 5. `nan`, `inf`, `2.5` and `abc` are refused. The check runs with the other parameter checks, before the file is stored, so a refused request leaves nothing behind.
- **Rationale**: Implements FR-003 and FR-004 and SC-005, which asks that an empty value be refused on the server. This differs on purpose from `window_spacing`, where an empty value means "use the default": the spec for spacing says so explicitly, and the spec for brightness says otherwise.
- **Alternatives considered**: Treating an empty string as the default (contradicts SC-005).

## Decision 5: One settings object in the frontend

- **Decision**: Introduce `JobSettings` (`windowSize`, `frameRate`, `windowSpacing`, `brightness`) in `api.ts`. `submitJob(file, settings)` takes it, and the form emits `submit` with `(file, settings)`.
- **Rationale**: `submitJob` already takes four positional numbers of similar type, and adding a fifth makes a swapped argument easy and invisible to the type checker. This is a small mechanical refactor of three files touched by this feature anyway.
- **Alternatives considered**: Adding a fifth positional argument (smallest diff, but error-prone); a store or composable (more machinery than one screen needs).

## Decision 6: The brightness field

- **Decision**: A number input (`step="1"`, `min="2"`, `max="100"`, default 2) validated by `validateBrightness`, which accepts text that parses to a whole number from 2 to 100 (so `5.0` passes and `2.5` does not), shows its range as its hint, and adds the one-line explanation that higher values lift quiet notes more but show less contrast (FR-013). It is disabled while busy and keeps its value after errors and successes like the other fields.
- **Rationale**: Mirrors the other numeric fields. A slider would suggest a continuous setting, and the spec asks for a whole-number field with a visible range.
- **Alternatives considered**: A slider with a number box (more UI, no requirement for it); a dropdown of 99 entries (unwieldy).

## Decision 7: No change to the analysis

- **Decision**: Brightness is used only in `write_frames`. It does not enter `analyze_channels`, `average_frames`, `to_gray_levels`, the window or frame counts, or the limits.
- **Rationale**: FR-009 and SC-006. Keeping it at the last step makes the "same windows, same frames, only different gray levels" guarantee true by construction.
- **Alternatives considered**: None needed.

## Decision 8: Verifying SC-001 and SC-003

- **Decision**: SC-001 (brightness 2 equals the previous images) is tested by comparing the table for 2 with an independent `255 × sqrt(level / 255)` for all 256 levels, and by an API test that compares the rendered pixels with that independent computation on real analysis output. SC-003 (the 25% rise from 2 to 4) is measured on the real sample file at implementation time and recorded, rather than asserted in a unit test that depends on a 90 MB file.
- **Rationale**: Unit tests stay fast and self-contained, and the real-file number is reported as measured.
- **Alternatives considered**: A committed fixture audio file (large, and the sample file is deliberately not committed).
