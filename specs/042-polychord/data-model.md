# Data model: Polychord

Names of arrays follow `backend/app/services/array_types.py`; the new ones (marked **new**) get their alias and their one
description there before they are used (constitution II). `frames` is the number of pictures, `count` the **Number of
notes** setting (5 to 8), `links` the number of links of a figure (0 to `count`), `segments` the number of pieces drawn in a
picture.

## Settings

| Name | Type and limits | Default | Check (new module) |
|---|---|---|---|
| `notes` | whole number 5 to 8 | 6 | `check_polychord_notes()` |
| `min_copies` | whole number 1 to 12 | 3 | `check_polychord_copies()` |
| `max_copies` | whole number 1 to 12, not under `min_copies` | 12 | `check_polychord_copies()`, then `check_polychord_settings()` |
| `rotation` | finite number -360 to 360, degrees a second (negative turns counterclockwise) | 15 | `check_polychord_rotation()` |

`PolychordSettings` (frozen dataclass: `notes`, `min_copies`, `max_copies`, `rotation`) holds the four after
`check_polychord_settings()`; `DEFAULT_POLYCHORD_SETTINGS` holds the defaults. A boolean, text or not-a-number is refused
(as `polar_chords.check_polar_notes` refuses them).

## Arrays

| Alias | Shape | Meaning | Made by |
|---|---|---|---|
| `LoudLetters` **new** | `(frames, count)` int | the letter (0 = A, ..., 11 = G#) of each of the loudest notes of each frame, loudest first; `-1` where fewer than `count` notes sound | `loudest_letters()` |
| `LinkTurns` **new** | `(frames, count)` float64 | the turn in degrees (clockwise positive) of each link from the one before it: 0 for the first link, then `22.5 x step` (`STEP_TURN`), from -112.5 to +135; 0 where the letter is `-1` | `link_turns()` |
| `CopyCounts` **new** | `(frames,)` int | the number of copies of the figure in each frame, from `min_copies` to `max_copies` | `copy_counts()` |
| `FrameTempos` **new** | `(frames,)` float64 | the current tempo at the middle of each frame, in beats a minute, 60 to 156 (120 before the first peak) | `frame_tempos()` |
| `StartAngles` **new** | `(frames,)` float64 | the angle in degrees, clockwise from straight up, of the first link of copy 0 of each frame: `rotation x t / frame_rate` | `start_angles()` |
| `FigureColors` **new** | `(frames, 3)` uint8 | the red, green and blue (0 to 255) of every link of each frame, from the tempo | `tempo_colors()` |
| `LinkSegments` **new** | `(segments, 2, 2)` float64 | the pieces drawn in one picture: for each, the two end points `(x, y)` in pixels (`y` from the top) | `figure_segments()` |
| `LinkWidths` **new** | `(segments,)` float64 | the width in pixels of each piece of `LinkSegments` | `figure_segments()` |
| `BeatPositions` | `(frames,)` | the place of each frame in the local energy peak, 0 to 1 (existing) | `LocalPeaks.frame_positions()` |
| `NoteStrengths` | `(frames, 88)` | the smoothed strength of each of the 88 notes in each frame (existing) | `frame_rendering.smooth_frames()` |
| `Pictures` | `(height, width, 3)` | one picture (existing) | `_frame()` |

## Entities and their rules

- **Letters of a frame** (`loudest_letters`): the first 84 columns of the smoothed values; for each frame the `count` largest
  in order (ties to the lower note), keeping only values above 0; column `j` is the letter `j mod 12`. A frame with no value
  above 0 has every entry `-1` and is drawn as a black picture.
- **Turn** (`link_turns`): for link `i >= 1` with both letters present,
  `step = ((pos(letter[i]) - pos(letter[i-1]) + 5) mod 12) - 5` with `pos = chromatic_decay.ring_position`,
  `turn[i] = 22.5 x step`. `turn[0] = 0`. The 12 intervals from C (pos 0): C 0, G +22.5, D +45, A +67.5, E +90, B +112.5, F# +135,
  C# -112.5, G# -90, D# -67.5, A# -45, F -22.5.
- **Copies** (`copy_counts`): `position = 1 - chromatic_decay.beat_distances(beat)`;
  `copies = floor(min_copies + position x (max_copies - min_copies) + 0.5)`; `beat = None` gives `min_copies`.
- **Tempo of a frame** (`frame_tempos`): `moments = (arange(frames) + 0.5) / frame_rate`; the latest peak at or before each
  moment (`numpy.searchsorted(times, moments, side="right") - 1`) gives its entry of `find_tempo(times).tempos`; no peak
  yet gives 120. No peak at all: every frame is 120.
- **Color** (`tempo_colors`): `index = rint(clip((tempo - 60) / 96, 0, 1) x 255)`; the row of
  `lookup_table(colormap)` at that index.
- **Starting angle** (`start_angles`): `rotation x arange(frames) / frame_rate` degrees.
- **Figure of one copy** (`figure_segments`), for one frame with `n` links (the letters that are not `-1`), the start angle
  `s`, copy `k` (0 to `copies - 1`), the length `L` and the widths below:
  - the direction angle of link `i` is `s + 30 k + sum(turn[0..i])`;
  - link `i` runs from `P[i]` to `P[i+1] = P[i] + L x (sin a_i, -cos a_i)`, `P[0] = (width / 2, height / 2)`;
  - the link is cut into `PIECES_PER_LINK = 6` equal pieces; the width of piece `j` of link `i` is the width of the figure
    at `(i + (j + 0.5) / 6) / n` of its length: `W(x) = W0 - (W0 - W_END) x` for `x` from 0 to 1, `W0 = height / 60`,
    `W_END = W0 / 5`, held at least 1 pixel.
  - `LinkSegments` holds the pieces of every copy of the frame in order (copy 0 first); `LinkWidths` the matching widths.
- **Squeeze** (`X_SCALE = 2/3`, `Y_SCALE = 1/2`): a link of length `L` at angle `a` (degrees clockwise from straight up) is the step
  `(L sin a x 2/3, -L cos a x 1/2)` on the screen; the copies are turned (by `a`) before this squeeze, so the figure is an ellipse.
- **Link length** (`link_length`): `L = LENGTH_FACTOR x (min(width, height) / 2 - MARGIN - W0 / 2) / notes`, `MARGIN = 10`, `LENGTH_FACTOR = 1.4`.
- **Picture** (`_frame`): a black figure, one `LineCollection` of the `LinkSegments` with the `LinkWidths` (points = pixels x
  72 / 100) and the color of the frame, round caps and joins; no pieces when the frame has no letters.

## Invariants (what the tests check)

1. Every link starts where the previous one ends; the first starts at the center.
2. The end width of a link equals the start width of the next, and the width falls from link to link.
3. The turns equal the table above for every pair of letters, and are measured from the previous link's letter.
4. No point of a figure, with its offset from the center divided by `(X_SCALE, Y_SCALE)`, is farther from the center than
   `LENGTH_FACTOR x (min(width, height) / 2 - MARGIN - W0 / 2)`; with the squeeze, a figure stays inside a 600 x 400 picture.
5. `copies` is between `min_copies` and `max_copies`, equal to the maximum at the top of the beat and to the minimum at the
   bottom and with no beat.
6. The starting angle of consecutive frames differs by `rotation / frame_rate`.
7. One color per frame; slower tempo = nearer the first color; tempo outside 60 to 156 is held at the ends.
8. The same inputs give the same picture (also with the pictures drawn by several threads).
9. The pictures of every other image type are unchanged.
