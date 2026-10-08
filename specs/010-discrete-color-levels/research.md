# Research: Discrete Color Levels

No `NEEDS CLARIFICATION` items remained in the spec. These are the design decisions the plan rests on.

## Decision 1: One pure rounding function, applied last, per property

- **Decision**: `snap(values, step, scale)` takes values on a 0 to 1 scale, multiplies by `scale` (360 or 100), finds the nearest multiple of `step` with halves rounded up, clips to `[0, scale]`, and divides back. `step=None` (N/A) returns a copy of the input unchanged. It is called on the hues after smoothing, on the frame brightnesses after smoothing, and on each tile's saturation where `tile_colors` forms it.
- **Rationale**: The spec (FR-006, FR-007) requires rounding to be the last step and to depend only on a frame's own finished values. The hue, value and saturation fractions already exist at exactly those points in `frame_rendering.py`, so no function has to be reordered. Because rounding is per value and does not look at neighbors, adding a frame at the end cannot change earlier frames. Smoothing keeps working on unrounded values, so rounding errors never accumulate.
- **Alternatives considered**: Rounding the raw note levels or the energies before the mappings (rejected: it would round something other than the displayed property and the root settings would then change the levels' meaning). Rounding after RGB conversion (rejected: hue, saturation and brightness cannot be recovered exactly from rounded RGB).

## Decision 2: Number of levels, and the rounding rule

- **Decision**: `level_count(step, scale) = floor((scale + step) / step + 0.5)`, written as the user gave it, `round((value + divisor) / divisor)`, with halves up. For the allowed steps every quotient is already a whole number (`scale / step + 1`), so the count is exact. `snap` computes `floor(value × scale / step + 0.5 + 1e-9) × step`; the `1e-9` guards values that are half-way in exact arithmetic but land just below in floating point (for example 6° as a hue fraction times 360 gives 5.999999999999999). The result is then clipped to the scale so the top level is always the scale itself.
- **Rationale**: Matches the spec examples (hue 90 gives 0°, 90°, 180°, 270°, 360°; saturation 20 gives 0, 20, … 100) and keeps the top of the range reachable. Python's built-in `round` rounds halves to even, which would make 50 on step 20 go to 40, so explicit `floor(x + 0.5)` is used as elsewhere in the code (`internal_window` in `energy.py`).
- **Alternatives considered**: `np.rint` (halves to even; breaks "half-way goes up"). Computing levels as an index and looking up from a table (no benefit for three values).

## Decision 3: Where the allowed steps are defined

- **Decision**: `color_levels.py` defines `HUE_STEPS = (12, 36, 90, 180)`, `UNIT_STEPS = (5, 10, 20, 50)`, `HUE_SCALE = 360`, `UNIT_SCALE = 100`. The router validates against these; the frontend repeats them in `validation.ts` (as it already repeats the ranges of the other settings), and both sides have tests that pin the level counts.
- **Rationale**: Mirrors how every other setting is handled: the server is authoritative, the page validates the same rule so a bad value never leaves the browser. Only the listed steps are accepted, so level counts are always whole numbers.
- **Alternatives considered**: Accepting any divisor of the scale (rejected: the spec lists the choices, and the page offers only those). Serving the lists from an endpoint (rejected: new interface for static data; this project repeats such constants in both halves).

## Decision 4: API field names and the N/A value

- **Decision**: New optional form fields `hue_step`, `saturation_step`, `brightness_step`, named after what the page shows. In the backend, the frame brightness is called `value` (HSV) in `frame_rendering.py`, so the argument is `value_step`; the router maps `brightness_step` to it. The text `N/A` (any case, surrounding spaces ignored) means no rounding and is what the page sends for N/A. A field that is not sent also means N/A. A field that is sent empty, `0`, or any number not in its list is refused. The response carries `null` for N/A and the number otherwise.
- **Rationale**: The existing API fields `brightness` (the page's Saturation root) and `energy` (the page's Brightness root) already differ from the page's labels, and a comment says so. Reusing that confusion for three more fields would make it worse; naming by what the user sees keeps the new fields self-explanatory, at the cost of `brightness_step` sitting beside an unrelated `brightness` field. The contract spells this out. Sending `N/A` explicitly matches the spec's wording and the label in the dropdown; accepting a missing field keeps old clients working. JSON `null` is the natural "no value" and types as `number | null`.
- **Alternatives considered**: Naming them `*_divisor` (matches the formula but not the page). Using `0` for N/A (the spec requires `0` to be refused). Returning the string `"N/A"` (a number-or-string union in the response for no gain).

## Decision 5: Validation and error message

- **Decision**: One `_parse_step(text, sent, allowed, label)` in the router, in the style of `_parse_energy`: not sent → N/A; sent → strip, `N/A` → N/A, else parse as a number, require a whole number in `allowed` (so `12`, `12.0` are accepted; `2.5`, `abc`, empty, `nan`, `inf` are refused). The message is `The <label> step must be N/A or one of <list>.`, for example `The hue step must be N/A or one of 12, 36, 90, 180.` HTTP 400, before any audio is read.
- **Rationale**: Same pattern, same status code and same timing as the other settings (FR-011, SC-007), and the message lists the allowed choices as the spec requires.
- **Alternatives considered**: A shared generic validator for all numeric fields (a larger refactor of working code, out of scope).

## Decision 6: Dropdown on the page

- **Decision**: Three `<select>` elements in a new field row below the Brightness / Saturation row, in the order Hue, Saturation, Brightness (as the spec lists them). Option text is `N/A` or the number; the option for the current value is followed by the level count in a small readout beside the dropdown (`20 (6 levels)`, `N/A (smooth)`). Each has an info button. The state is held as the option's text (`"N/A"`, `"12"`, …) and converted to `number | null` when submitting.
- **Rationale**: Clarified with the user: a dropdown list like the existing Window size field. A string state keeps `v-model` simple on a `<select>`, and validation can check it against the list so a tampered value still blocks the submit.
- **Alternatives considered**: A snapping slider (rejected by the user). Putting the level count inside each option's text (rejected: it would repeat the number twice in the open list and the closed select would show "20 (6 levels)" anyway; a separate readout is also easier to test).

## Decision 7: Scope of pixel changes

- **Decision**: Only `tile_colors`'s saturations, the hue sequence and the frame values are rounded. The PNG writing, palette handling, layout, energy measure and note analysis are untouched, and with all steps N/A the code path produces the same arrays as before (`snap` returns its input unchanged).
- **Rationale**: Satisfies FR-002 and FR-014 and SC-001 (byte-identical output at N/A), and keeps the change reviewable.
- **Alternatives considered**: None worth recording.
