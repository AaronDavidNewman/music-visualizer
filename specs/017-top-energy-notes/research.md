# Research: Top-Energy Notes

No `NEEDS CLARIFICATION` items remain in the spec. The user read the defaults the spec chose (energy over the whole file, the other notes dropped, a one-dimensional spread in order of pitch to the 84 values of the original grid, the file's loudest value as the scale) and accepted them ("I think these are OK but I'll need to see it first"), so the plan builds on them and the implementation ends with pictures to look at. The decisions below were checked with throwaway prototypes on synthetic files (20 s, 10 frames per second, melodic and sustained notes plus broadband noise), not assumed.

## Measurements from the prototypes

| Question | Result |
|----------|--------|
| Cost of choosing the notes and spreading them, 6,000 frames, n = 12 | 0.012 s (one `np.interp` call per frame, about 2 µs each) |
| n = 84 | the spread returns the input exactly (`np.array_equal`), because `np.linspace(0, 83, 84)` is exactly the integers 0 to 83 |
| First and last chosen note | keep their exact values at the first and last of the 84 positions |
| Notes chosen from a file with six sustained tones and noise, n = 12 | notes 22 to 32 and 36: the tones' neighborhood, because leakage of a loud tone into the notes next to it carries real energy |
| Average frame-to-frame change of the raw values (as a share of the file's peak), melodic file | 0.021 at 84 notes, 0.031 at 48, 0.041 at 24, 0.060 at 12: it **grows** as notes are dropped |
| The same in color position (`sqrt` of the share, as the tiles use) | 0.037 at 84, 0.053 at 48, 0.060 at 24, 0.068 at 12 (melodic file); for **sustained** tones with noise 0.02: 0.043, 0.054, 0.050, 0.042; with noise 0.3: 0.059, 0.056, 0.053, 0.045 |

## What the jitter measurements mean for the feature

The request hopes for a less jittery picture "in some cases". The prototypes say which cases: dropping notes removes the flicker of the faint notes, but each remaining note is spread over more of the picture, so any change in a remaining note changes a larger area. Measured on synthetic files, the raw average change *grows* with fewer notes, and the colors change less only for sustained notes in strong noise (about 23% less at 12 notes against 84 at the highest noise tried), and about equal at moderate noise. For notes that start and stop quickly the picture is less steady. The spec's SC-007 and its Edge Cases were reworded to say exactly this; the feature is still what the user asked for (the strongest notes, spread), and the user will judge the look from the rendered frames at the end of the implementation.

## Decision 1: One module for the setting, the choice and the spread

- **Decision**: A new module `app/services/note_selection.py` holds `MIN_NOTE_COUNT = 12`, `MAX_NOTE_COUNT = 84`, `DEFAULT_NOTE_COUNT = 84`, `check_note_count(value)` (a whole number from 12 to 84, not a bool, otherwise `ValueError("The number of notes must be a whole number from 12 to 84.")`), `top_energy_notes(values, count)` and `spread_notes(values, count)`. It is pure numpy and knows nothing about the note analysis or the pictures.
- **Rationale**: Like `resolution.py`, the setting, its check and the computation are one concept used by the writer, the router and the tests.
- **Alternatives considered**: Putting it in `frame_rendering.py`: that file is the shared pipeline, and a separate unit is easier to test.

## Decision 2: Energy is the sum of smoothed values over the file; the choice is made once

- **Decision**: For smoothed values `shown` of shape `(frames, 84)`, `energy = shown.sum(axis=0)`; the chosen notes are `np.sort(np.argsort(-energy, kind="stable")[:count])`. A stable sort of the negated energy keeps the lower note first among equal energies, so ties go to the lower note. The same indices are used for every frame.
- **Rationale**: This is FR-002. A choice made once for the file cannot flip from frame to frame. The sum of smoothed values is the simplest measure of "how much the note sounds"; the sum of squares (power) is a one-line alternative, left for later by the spec.
- **Alternatives considered**: Choosing in every frame: follows the music more closely but the set flips at the margin, which adds the flicker the request wants less of. Choosing by the loudest single value: dominated by one click.

## Decision 3: The spread is `np.interp` over the chosen values to 84 positions

- **Decision**: For every frame, `np.interp(np.linspace(0, count - 1, 84), np.arange(count), shown[t, chosen])` gives the 84 values of the original grid (row-major, as note `n` is at row `n // 12`, column `n % 12`). At `count = 84` the values are returned unchanged and `np.interp` is not called.
- **Rationale**: This is the user's method (FR-003) and gives today's picture exactly at 84. Everything after it (the Resolution setting's two-dimensional interpolation, the Threshold, the colors, the image types) is unchanged because it receives the same kind of array as before. A loop of one `np.interp` per frame costs 0.012 s for 6,000 frames, so no vectorization is needed.
- **Alternatives considered**: A smaller two-dimensional grid (for example 12 columns by `count / 12` rows) before the Resolution step: `count` need not be a multiple of 12, so the last row would need padding, and the meaning of a position gets harder to state; it stays an option for `/speckit-clarify`. Setting the other notes to 0 in place: the spec chose to drop them.

## Decision 4: The pipeline and the scale

- **Decision**: In `write_frames`, after smoothing: `peak = smoothed.max()` over all 88 notes (unchanged); `shown = smoothed[:, :84]`; `shown = spread_notes(shown, note_count)` (identity at 84); then `interpolate_grid(shown, 12, 7, resolution)`, the threshold, the colors and the writers exactly as now. A new argument `note_count` (default 84) is checked with the other arguments before anything is written.
- **Rationale**: FR-004 and FR-006: the same strength keeps its color at every n, and the Threshold's reference is unchanged. The cost is the caveat the spec states: dropping the loudest note can leave a dimmer picture.
- **Alternatives considered**: Scaling to the loudest chosen note: would brighten the picture, but makes the same strength a different color at different n.

## Decision 5: API and page

- **Decision**: The router gets the optional form field `note_count` with a parser like `_parse_resolution` (not sent: 84; sent: a whole number from 12 to 84, so `"36"` and `"36.0"` are accepted and `""`, `"abc"`, `"11"`, `"85"`, `"36.5"`, `"nan"` are refused with a 400 `The number of notes must be a whole number from 12 to 84.`, before the file is read), passes it to `write_frames` and reports `note_count`. The frontend gets a slider (12 to 84, step 1, starting at 84) after the Threshold control, with a readout from a pure function (`All 84 notes`, `36 of 84 notes`), a help text, a summary line (`Notes: All 84` or `Notes: 36 of 84`) and the field in `api.ts`.
- **Rationale**: The same shape as every earlier setting.
- **Alternatives considered**: A dropdown of fixed counts: the request says "anywhere from 12 to 84".

## Decision 6: Tests are colormap-list tolerant and independent of the implementation

- **Decision**: The tests follow the rules of features 014 to 016: colormap names come from `colormap_names.py`, no test counts contour levels. The choice is tested against an independent computation (a plain Python ranking), the spread against `np.interp` itself and its invariants (identity at 84, first and last kept, range), the pictures by decoding (a Tiles picture's tile colors compared with the colormap's color for the independently worked-out values), and SC-003 by changing only the values of non-chosen notes (kept below the energy of the chosen ones and below the file's peak) and comparing bytes. The 84-note output is compared with the reference hashes recorded before the change.
- **Rationale**: The user changes the colormap list by hand, and the contour's levels are matplotlib's.
- **Alternatives considered**: Pixel-exact expectations for the contour: they would restate the implementation.
