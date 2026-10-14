# Research: Generative Circles

> **Amended 2026-10-14 (feature 020, grouped settings).** On the page the circles settings were renamed: **Unit** is now **Movement**, **Size** is now **Radius**, **Circles per frame** is now **Notes** (and the summary says Memory for the circle memory), all inside a **Circles** group that is shown only for Circles; the controls the type does not use are no longer greyed out but not shown. **The Size setting became a real radius**: a whole number of pixels from **4 to 8** (default 4), request field `circle_radius` with the message `The circle radius must be a whole number from 4 to 8.`, replacing the circumference of 25 to 50 pixels (`circle_size`, now ignored if sent; a radius of 3.98 to 7.96). The unit message is now `The circle movement must be a whole number from 1 to 10.`. Where this document, or its earlier amendments, say size, circumference, 25 to 50 or `circle_size`, the radius governs; the Resize by volume factor (1 to 3) applies to the radius. See `specs/020-grouped-settings-ui/`.

> **Amended 2026-10-13 (look and size of the circles).** After this feature was delivered the user asked for three changes: (1) the background is the **middle color of the colormap** (row 128 of its 256-entry table) instead of black; (2) each circle is drawn with an **opacity that falls with its age** (newest opaque, opacity (m - age) / m in a memory of m circles, so the oldest is barely visible just before it is dropped); (3) a new fourth circle setting, the **circle size** (the circumference in pixels, a whole number from 25 to 50, default 25, radius size / (2 pi)), replaces "the radius is one unit" (the unit is now only the length of a step). Where this document still says black, "radius of one unit" or "three settings", the amended spec (`spec.md`, Clarifications) governs.

No `NEEDS CLARIFICATION` items remain in the spec: the user answered Question 1 (the distance of an octave) with option C, **1 + |octave − 4| units**, and said their examples were wrong. The decisions below were checked with a throwaway prototype (Pillow 12.3.0, a synthetic 300-frame file), not assumed.

## Measurements from the prototype

| Question | Result |
|----------|--------|
| The move of a note (angle, units) for the examples, with the C-based pitch class and the scientific octave | F5 (index 44): 150°, 2 units; F3 (index 20): 210°, 2 units; A4 (index 36): 270°, 1 unit; C3: 0°, 2 units; A1 (index 0): 90°, 4 units; G#8 (index 83): 240°, 5 units |
| Choosing the n strongest notes of a frame and placing the circles | 0.015 to 0.032 ms a frame (n = 5 to 12) |
| Drawing the memory with Pillow `ImageDraw.ellipse` | memory 100, unit 1: 0.10 ms; memory 300, unit 4: 0.24 ms; memory 500, unit 10: 0.47 ms a frame |
| Saving the picture as an RGB PNG (compress level 6) | 0.6 to 1.4 ms a frame; files of 1.4 KB (small circles) to 11 KB (500 circles of radius 10) |
| A 1,800-frame job at the largest settings | about 3 to 4 s of drawing and saving, single-threaded; saving can go to a few threads |

## Decision 1: One module for the settings, the move, the placement and the drawing

- **Decision**: A new module `app/services/circles.py` holds the three settings with their ranges and defaults (`MIN/MAX/DEFAULT_CIRCLE_UNIT` 1/10/4, `MIN/MAX/DEFAULT_CIRCLE_MEMORY` 100/500/300, `MIN/MAX/DEFAULT_CIRCLE_NOTES` 5/12/8), their checks (`check_circle_unit`, `check_circle_memory`, `check_circle_notes`, each a whole number in range, not a bool; messages `The circle unit must be a whole number from 1 to 10.`, `The circle memory must be a whole number from 100 to 500.`, `The number of circle notes must be a whole number from 5 to 12.`), `note_move(index)`, `plan_circles(...)` and `write_circle_frames(...)`. It knows nothing about the note analysis or the other image types, except that a frame's values are 84 drawn notes ordered from A1.
- **Rationale**: Like `contour.py`, the new picture lives in its own module, so the existing writers are not touched and the existing image types stay byte-identical.
- **Alternatives considered**: Putting it in `frame_rendering.py`: that file is the shared pipeline.

## Decision 2: The move of a note comes from its real name and octave

- **Decision**: For a drawn note with index `i` (0 is A1, 55 Hz): `midi = 33 + i`, pitch class `pc = midi % 12` (C = 0 … B = 11), `octave = midi // 12 − 1` (scientific: A4 is 440 Hz, index 36). The angle is `30° × pc`, mirrored (`(360° − angle) mod 360°`) when `octave < 4`; the distance is `(1 + |octave − 4|)` units. In pixels, with 0° pointing right and angles counter-clockwise on the screen: `dx = distance × unit × cos(angle)`, `dy = −distance × unit × sin(angle)` (the picture's y axis points down).
- **Rationale**: The user's examples (F5: 150°, F3: 210°) count the note names from C and the octave in scientific notation, while the application's grid starts at A (column 0 = A1). This is the spec's first assumption; the prototype reproduces every example.
- **Alternatives considered**: The grid's own column and row: gives F5 → column 8 → 240°, contradicting the user's example.

## Decision 3: Choice and placement, frame by frame, with state per rank

- **Decision**: `plan_circles` goes through the frames in order with a `(12, 2)` array of the last place of each rank, starting at the middle of the picture. In each frame the n strongest notes are `np.argsort(-values, kind="stable")[:n]` of that frame's 84 smoothed values (ties go to the lower note), the notes with value 0 are dropped, and rank `r` (0 for the strongest) moves from its last place by the move of its note; the new place is taken modulo the picture size (`252 × 168`, wrapping around) and is stored as that rank's place. The circle's color is `table[rint(sqrt(min(value / peak, 1)) × 255)]` with `peak` the file's largest smoothed value over all 88 notes (the tiles' scale; 0 when silent). A rank that gets no note in a frame keeps its last place.
- **Rationale**: This is FR-003 to FR-006 and the tiles' color rule (FR-004). Using the rank as the index of the state is the user's "the last note at that index".
- **Alternatives considered**: Following the note across frames instead of the rank: the user said index.

## Decision 4: The memory is a circular buffer of the last m circles

- **Decision**: `collections.deque(maxlen=m)` of `(x, y, color)`; every frame appends its circles **weakest first** so the strongest of a frame is on top and the last to be dropped, then the picture is drawn from the whole buffer in order (oldest first, newest on top) as an RGB image of 252 × 168 on a black background with `ImageDraw.ellipse([x − r, y − r, x + r, y + r], fill=color)` where the radius `r` is the unit (in pixels, as the spec assumes). Circles are drawn at their place only: a circle near an edge is cut off by it, not drawn again on the opposite side.
- **Rationale**: Spec FR-007 and the assumptions. `deque(maxlen=)` is Python's circular buffer.
- **Alternatives considered**: A numpy ring buffer: same behavior, more code. Drawing wrapped copies at the opposite edge: the spec's wrap only keeps the circles' places in the picture.

## Decision 5: Where it plugs in, and what it ignores

- **Decision**: `IMAGE_TYPES` becomes `("tiles", "blended", "contour", "circles")` (the router's validation, the refusal message and the response follow from the tuple). `write_frames` gets `circle_unit`, `circle_memory` and `circle_notes` (all checked first with the other arguments) and a `circles` branch: after the smoothing and the peak, it calls `write_circle_frames(smoothed[:, :84], peak, colormap, directory, circle_notes, circle_unit, circle_memory)` and returns without the spread, the resolution step, the threshold, the grid writers or the interpolation pass. `resolution`, `note_count`, `threshold`, `blend_width` and `interpolate` are still checked and are accepted and ignored. The saving of the pictures is done on a few threads (as the blended writer does); the placement and the drawing stay sequential because they depend on the earlier frames.
- **Rationale**: FR-009. The tiles, blended and contour branches are not edited, so their files cannot change (FR-002; reference hashes).
- **Alternatives considered**: Rejecting the ignored settings for circles: the spec says accepted and ignored.

## Decision 6: API and page

- **Decision**: The router gets three optional fields `circle_unit`, `circle_memory` and `circle_notes` (parsers like `_parse_resolution`: not sent, the default; sent, a whole number in range; `3` and `3.0` accepted; refused with 400 and the messages above, before the file is read), passes them to `write_frames` and reports them in the response (always, like `blend_width`). The frontend gets the image type `{ value: "circles", label: "Circles" }`, three sliders (Unit, Memory, Circles per frame) shown only while Circles is chosen, with readouts (`4 px`, `300 circles`, `8 notes`) and info texts; while Circles is chosen the Interpolate, Resolution, Notes, Threshold and Blend width controls are disabled (a pure helper `gridSettingsApply(imageType)`); the summary shows the three values for circles and hides the lines that do not apply (Threshold, Resolution, Notes, Interpolate, Blend width).
- **Rationale**: The same shape as earlier settings; the dropdown is built from the list, so the choice appears by adding an entry.
- **Alternatives considered**: Hiding the five controls instead of disabling them: the spec says disabled.

## Decision 7: Tests are colormap-list tolerant and independent of the implementation

- **Decision**: The tests follow the rules of features 014 to 018 (no colormap names, no contour levels). The move is tested against the examples (F5, F3, A4) and an independent computation from the note's frequency (pitch class and octave worked out from `440 × 2^((midi − 69) / 12)`), for all 84 notes. Placement is tested with files in which one note sounds (one circle a frame): the center of the newest circle is the previous center moved by the expected `dx, dy`, modulo the picture, to within one pixel, by finding the circle in the picture; the colors by the table; the memory by counting `ImageDraw.ellipse` calls per frame (spy) and by eviction; the ranks with files of several notes; determinism; the other image types against the four reference hashes. The page: the list, the conditional controls, the disabled rule, the summary.
- **Rationale**: The user changes the colormap list by hand; the circle positions come from arithmetic that can be checked exactly.
- **Alternatives considered**: Pixel-exact expectations for the whole picture: would restate the drawing.
