# Research: Note Threshold

No `NEEDS CLARIFICATION` items remained in the spec. These are the design decisions the plan rests on.

## Decision 1: Compare the smoothed value as a share of the file's largest smoothed value

- **Decision**: In `write_frames`, `smoothed = smooth_frames(frames, smoothing)` is computed once. The reference is `smoothed.max()` over the whole array (all 88 notes, all frames), the same value `to_gray_levels` already scales against. A tile is hidden when `smoothed[f, n] < threshold / 100 * peak` for `n` in 0..83.
- **Rationale**: The spec (FR-003, FR-005, Assumptions) defines "volume" as the note's smoothed value as a share of the file's largest note value, before the Saturation root, and says the comparison must not depend on the roots, steps or hue. `to_gray_levels` already derives the gray level from exactly these two numbers, so the mask and the colors can never disagree about what "the largest" is, including the four undrawn notes that count toward the peak today.
- **Alternatives considered**: (a) Compare the 8-bit gray level (rounded to 0..255): coarse (a 1% threshold is 2.55 levels, so steps of 0.4% could not be told apart) and it would hide or show a note depending on rounding. (b) Compare after the Saturation root (rejected by FR-005: the root would then change which notes are hidden). (c) Per-frame reference (rejected by the spec: one fixed level for the whole file).

## Decision 2: Strictly below hides; zero threshold hides nothing without a special case

- **Decision**: The test is `smoothed < threshold / 100 * peak`. No special case for 0.
- **Rationale**: Note values are never negative (`average_frames` clips at 0 and smoothing is a convex combination), so with a threshold of 0 the comparison `value < 0` is always false and the output is the same as today by construction. A note exactly at the threshold is shown, and the note with the largest value (value = peak, threshold ≤ 10%) is never below it. A silent input (peak 0) gives `0 < 0`, false for every tile, so nothing is hidden and nothing divides by zero.
- **Alternatives considered**: `<=` (would hide the note at the threshold and, at 0, every silent note; the spec says strictly below). A separate "is the threshold off" branch (extra code path to keep identical to the general one).

## Decision 3: Hidden notes stay in the hue calculation

- **Decision**: `tile_hues` and `hue_sequence` still receive the unmasked gray levels. The mask is applied only when the colors are formed, by setting the hidden tiles' RGB to `(0, 0, 0)` in `tile_colors`.
- **Rationale**: FR-007 and Story 3 scenario 4 say only the hidden note's own tile changes and that the hidden note still counts as a related note. This is also the minimal change: the hue code is untouched. If the user decides otherwise in `/speckit-clarify`, the mask can be applied to the levels before `hue_sequence` with a one-line change and the tests that pin this behavior are the ones to update.
- **Alternatives considered**: Zeroing the hidden notes' levels before the hue calculation (rejected as the default because the spec says the opposite; recorded as the easy alternative).

## Decision 4: Where black is applied, and its interaction with the other settings

- **Decision**: `tile_colors(levels, brightness, hues, value, saturation_step=None, hidden=None)` forms the colors as now, then assigns `(0, 0, 0)` to the rows where `hidden` is true. `hidden` is a boolean array of shape `(84,)`; any other shape raises `ValueError`.
- **Rationale**: Black after the fact is independent of the level steps, the roots, the hue and the frame brightness by construction (FR-006), and "RGB all 0" is exactly "HSV (0, 0, 0)". Doing it in `tile_colors` keeps palette writing, layout and `render_frame` unchanged, and a hidden tile merges into the palette's single black.
- **Alternatives considered**: Setting the tile's value to 0 before the HSV conversion (same result but needs a per-tile value path through `colorsys` for no gain). Masking inside `_palette_frame` (mixes colour decisions into the PNG writer).

## Decision 5: The threshold as an API value

- **Decision**: New optional form field `threshold`: a number from 0 to 10 (percent). Not sent: 0. Sent but empty, not a number, `nan`/`inf`, below 0 or above 10: refused with HTTP 400, before any audio is read. Whole numbers are returned as integers (`5`), others as sent (`2.5`). The page offers whole percents only.
- **Rationale**: Mirrors `smoothing`/`energy` handling (`_sent_fields` tells "not sent" from "sent empty"). Percent matches the slider's readout and avoids a second unit; the spec says the server accepts any number in the range while the page moves in steps of 1.
- **Message**: `The threshold must be a number from 0 to 10.`
- **Alternatives considered**: A fraction 0 to 0.5 (a different unit from the page); a whole-number-only field (needlessly strict for an API).

## Decision 6: Slider on the page

- **Decision**: A range input like Smoothing: `THRESHOLD_RANGE = { min: 0, max: 10, step: 1 }`, default 0, placed after Smoothing. The readout is `Off` at 0 and otherwise `n% of the loudest note`. The page sends the number; the server's response is shown in the summary as `Off` or `n%`. Validation (`validateThreshold`) accepts a finite number from 0 to 10 so a tampered value still blocks submission.
- **Rationale**: The user asked for a slider with the left end off and the right end 10% (first 50%, changed to 10% on 2026-10-07); this is the existing Smoothing pattern with the existing styles (`slider-row`, `slider-value`), and its tests can follow the same shape.
- **Alternatives considered**: A number input (the user asked for a slider).

## Decision 7: Silence and the whole-black frame

- **Decision**: No special handling. A silent file has frame energy 0, so the frame brightness is 0 and every tile is already black; a frame whose notes are all below the threshold has all tiles black by the mask.
- **Rationale**: FR-008 is satisfied by the existing energy rule plus the mask. The one case the mask does not cover, a file whose note values are all 0 but whose frames still have energy (sound too quiet or too noisy for the note analysis to see), keeps the plain gray/white tiles it has today, unchanged by this feature.
- **Alternatives considered**: Forcing black when the peak is 0 (would change today's output for that case and break "threshold off is identical").
