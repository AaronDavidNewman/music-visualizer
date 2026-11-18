# Research: Polychord

Every item below was a question the plan had to answer; none is left open. "Probe" means a throw-away script that was run
(`lc_probe.py`, in the session scratchpad, not in the repository).

## Decision 1: draw the links with one `LineCollection` on a `Figure` (no `pyplot`), cut into short pieces

- **Decision**: each frame builds one `matplotlib.collections.LineCollection` holding **every piece of every link of every
  copy**, on a `matplotlib.figure.Figure` drawn by `FigureCanvasAgg` (`figsize = (width / 100, height / 100)`, `dpi = 100`,
  an axes that fills the figure with `xlim = (0, width)` and `ylim = (height, 0)` so that data units are pixels and *y*
  points down, the axes switched off, the figure black). The picture is read back from the canvas as `(height, width, 3)`.
  A link is cut into `PIECES_PER_LINK = 6` pieces so that its **width can step down inside the link** (a
  `LineCollection` gives one width to each of its segments); the width of a piece is the width of the figure at the middle
  of the piece, so the end of one link and the start of the next are the same width by construction. Round caps and joins
  (`capstyle="round"`, `joinstyle="round"`) hide the seams between pieces and between links.
- **Rationale**: the user asked for `LineCollection`. The probe (12 copies x 8 links x 6 pieces = 576 segments on a 600 x
  400 picture) took **10 ms a picture** and gave **identical pixels** whether the 40 pictures were drawn one after the
  other or by four threads, so the worker pool of the other types (`frame_saving.SAVE_WORKERS`) can be used and no lock is
  needed. Using `Figure` directly (not `pyplot`) keeps the global state of `pyplot` out of the threads (the contour type
  needs a lock because it uses `pyplot`).
- **Alternatives considered**: one `LineCollection` for each copy or link (more objects, no gain: the color is one for the
  whole frame, Decision 6); Pillow's `ImageDraw.line` as the wireframe does (no per-piece width without the same cutting,
  and the user named `LineCollection`); a filled polygon for every link (a true taper, but the corners and the joins
  between links need geometry that the cut pieces avoid, and it is not what was asked).

## Decision 2: the turn between two links is `30 x (the shorter way round the circle of fifths)` degrees

- **Decision**: with `ring_position(letter)` of `chromatic_decay` (C = 0, then G, D, A, E, B, F#, C#, G#, D#, A#, F: one
  step is a fifth up), the signed step from the previous link's letter `a` to this link's letter `b` is
  `((pos(b) - pos(a) + 5) mod 12) - 5`, from **-5 to +6**; the turn is `30 x step` degrees, clockwise positive. The same
  letter is step 0 (straight on), a fifth up C to G is +1 (+22.5), a fourth up C to F is -1 (-22.5), a whole tone C to D is +2
  (+45), C to A is +3 (+67.5), C to Eb is -3 (-67.5), and the tritone C to F# is **+6, 135 degrees** (the one step that has the
  same size either way). The first link has no turn: its direction is the starting angle.
- **Rationale**: it is exactly the user's table (a 4th or 5th away is -30 or +30, the same letter is straight, a tritone
  goes backwards), made for every interval by one formula. Reusing `ring_position` keeps the order of the letters the same
  as Chromatic Decay's ring, so a turn of 30 degrees is one step of that ring.
- **Alternatives considered**: a table of 12 turns (the same thing, with more room for a typo); measuring every turn from
  the loudest note (the user only described the second link; the chain reading, from the previous link, is the natural
  extension and is written in the spec's Assumptions).

## Decision 3: the loudest notes come from the smoothed note values, first 84 columns, ties to the lower note

- **Decision**: from the smoothed frames `(frames, 88)` (after `smooth_frames`, as every type), take the first 84 columns
  (the notes of the 12-letter, 7-octave grid, as `chromatic_decay.letter_energies` does: note `j` is the letter
  `j mod 12`), and for each frame the `count` largest values in order (`numpy.argsort` of the negated values with
  `kind="stable"`, so a tie goes to the **lower** note), each reduced to its letter. A note whose value is not above 0 is
  not a note of the frame, so a frame has between 0 and `count` links: the letters array holds `-1` for the missing ones.
- **Rationale**: it is what Decay does for its five loudest notes (`decay.gains`), with the count from the setting; ties
  must be broken the same way every time for repeatable pictures (spec FR-002, FR-013). The noise floor of feature 033
  already makes the faint notes 0 for every type, so "sounding" needs no new threshold.
- **Alternatives considered**: `chromatic_decay.letter_energies` (the 12 letters, the loudest octave of each): it cannot
  give two links with the same letter, which the user's "the same chromatic note is straight" needs.

## Decision 4: the number of copies uses the stretched beat of Chromatic Wireframe

- **Decision**: `position = 1 - chromatic_decay.beat_distances(beat)` (1 at the top of the beat of the file, 0 at its
  bottom, 0 outside every peak), `copies = floor(min + position x (max - min) + 0.5)`; with no beat (`None`) every frame
  has `min` copies.
- **Rationale**: the spec says the top of a peak has the most copies and the lowest point of the beat the fewest.
  `beat_distances` stretches the raw position (which in real music hardly goes below 0.55) over the whole range, so the
  copies really go from the minimum to the maximum; Chromatic Decay's rings and Chromatic Wireframe's colors already use it
  the same way. Rounding by `floor(x + 0.5)` (not `round`) is the same on every platform.
- **Alternatives considered**: the raw position (the copies would only use the upper part of the range, 8 to 12 for 3 to
  12).

## Decision 5: the tempo of a frame is the tempo finder's tempo after the latest peak at the middle of the frame

- **Decision**: a new function `frame_tempos(peaks, frame_rate, frames)` returns `(frames,)` beats a minute: at the middle
  of frame `f`, `(f + 0.5) / frame_rate` seconds, the value of `tempo_finder.find_tempo(times).tempos` for the **latest peak
  at or before that moment**, and `START_TEMPO` (120) before the first peak and with no peak. It lives in the new module
  (it needs `LocalPeaks` and `tempo_finder`, which `tempo_finder` itself must not know).
- **Rationale**: this is "the current tempo" of Rhythm Circles (feature 040), which is constant between two peaks; the
  middle of the frame is the moment that the beat position and the rhythm angles already use.
- **Alternatives considered**: the rate of the latest peak (a poor tempo, as feature 040 found: a peak is not always on the
  beat); the rate of change of the tempo (not asked).

## Decision 6: one color for the whole frame, from the tempo

- **Decision** (the user chose option A of the question): `index = rint(clip((tempo - 60) / (156 - 60), 0, 1) x 255)`
  into the colormap's lookup table (`colormaps.lookup_table`, 256 rows), the same color for every piece of every link of
  every copy; `60` and `156` are `tempo_finder.LOW_LIMIT` and `HIGH_LIMIT`.
- **Rationale**: slow tempo = the first color, fast = the last (spec FR-009). One color a frame means one `colors=[...]`
  for the whole collection.
- **Alternatives considered**: the two other readings that were offered (the colors stepping along the colormap from the
  center, and the colors of earlier tempos); the user did not choose them.

## Decision 7: the starting angle of frame `t` is `rotation x t / frame_rate`, clockwise from straight up

- **Decision**: `start_angle[t] = rotation x t / frame_rate` degrees, `t` the frame's index (frame 0 is at 0 degrees),
  measured clockwise from straight up; the direction of a link at the angle `a` is `(sin a, -cos a)` on the screen (*y*
  points down); copy `k` adds `30 k` degrees. A positive turn is clockwise too.
- **Rationale**: spec FR-008 and SC-004 (consecutive frames differ by `rotation / frame_rate`). Clockwise from the top is
  how the ring of fifths of Chromatic Decay is laid out (C at the top, G next, clockwise), so a fifth up turns the way the
  ring goes.
- **Alternatives considered**: the middle of the frame, `(t + 0.5) / frame_rate` (the beat and the tempo use it; the
  rotation has no measurement to agree with, and frame 0 at 0 degrees is easier to test).

## Decision 8: link length and widths

- **Decision**: the center is `(width / 2, height / 2)`. One link is
  `L = LENGTH_FACTOR x (min(width, height) / 2 - MARGIN - W0 / 2) / notes` long (`LENGTH_FACTOR = 1.4`, the user's change after seeing the first frames), where `notes` is the **setting** (not the number that
  sound), so the room that would just fit the longest possible figure (all links straight on, `MARGIN` (10) pixels inside the
  picture on the shorter side) is used 1.4 times over and such a figure is cut off at the edge; every link has this length. The width starts at `W0 = height / 60` (6.7
  pixels at 400) at the center and falls in a straight line along the links of the figure to `W0 / 5` at the end of the
  last one (`n` links: the width at the start of link `k` is `W0 - (W0 - W0 / 5) k / n`), never under one pixel.
- **Rationale**: spec FR-012 (nothing leaves the picture) and FR-005 (thinner outward, end = next start). Dividing by the
  setting rather than by the number that sound keeps the links the same size from frame to frame, so a figure grows as
  more notes sound instead of jumping in scale.
- **Alternatives considered**: a length that follows the note's strength (a possible later change, written in the spec's
  Assumptions); a length that makes the figure fill the picture whatever the count (the picture would pulse in scale).

## Decision 9: the settings, their names and their checks

- **Decision**: four new form fields of `POST /api/jobs`, `polychord_notes`, `polychord_min_copies`,
  `polychord_max_copies` and `polychord_rotation`, parsed like `polar_notes` (not sent means the default; anything sent
  must pass): notes a whole number 5 to 8 (default 6), copies whole numbers 1 to 12 (defaults 3 and 12) with the maximum
  not under the minimum (checked after both are read), rotation a finite number from -360 to 360 (default 15). All four
  are parsed before the file is read, so a refusal leaves nothing behind, and all four are echoed in the response. The checks
  live in the new module as `check_*` functions with their messages (as `polar_chords` does) and are used by the router,
  `write_frames` and the frontend's mirror validators.
- **Rationale**: the pattern of every other image-type setting.
- **Alternatives considered**: one JSON field (a different pattern from every other setting).

## Decision 10: black, not transparent

- **Decision**: the picture is `(height, width, 3)` on `(0, 0, 0)`.
- **Rationale**: every type writes 3-channel PNGs and the movie of feature 029 does not keep an alpha channel; the spec
  says "black/transparent".
- **Alternatives considered**: RGBA frames (nothing downstream would use the alpha).

## Decision 11: what is shared with, and what is not changed in, the other types

- **Decision**: nothing of another type changes. `chromatic_decay.beat_distances`, `ring_position`, `LETTERS` and
  `colormaps.lookup_table` are only imported. `jobs.py` measures the local peaks **once** for Polychord and derives the beat
  and the tempos from that one measurement. The frames of the other eight types are checked against the baseline of
  feature 041 (`verify_frames.py`: 540 frames) after the change.
- **Rationale**: spec FR-014.

## Decision 12: documentation standard (feature 041) applies

- **Decision**: every function is fully typed; the new kinds of array get an alias and a `Shape / Meaning / Made by`
  description in `array_types.py` before they are used; the module docstring has the `Order of operations:` list; the
  Polychord block is added to the `Pipeline overview:` in `image_types.py`; comments and docstrings wrap at 120 columns.
- **Rationale**: the constitution (v1.0.0) and the line-width rule of `documentation-standard.md` section 5.

## Findings for the tests

- Two pre-existing facts hold for every plan of this repo: the working tree has **25 tests that fail before any change**
  (`specs/041-code-readability-docs/tools/baseline-failures.txt`, caused by `DEFAULT_PROMINENCE = 15`); "no regression"
  means exactly those and nothing else. The new tests follow `local_peaks.DEFAULT_PROMINENCE`, never a hard-coded value.
- The tests that spell out the list of image types (`test_image_types.py`, `test_image_type_api.py`, `test_frame_size.py`,
  and the frontend's `SettingsForm`, `groups` and `validation` tests) change with the new name; `tasks.md` lists them.
