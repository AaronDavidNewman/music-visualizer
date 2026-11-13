# Research: Chromatic Wireframe

No `NEEDS CLARIFICATION` remains (the angle formula was answered: `x` added). The decisions below fix what the spec left as assumptions.

## Decision 1: Reuse Chromatic Decay for all the data

- **Decision**: `chromatic_wireframe.py` calls `chromatic_decay.circle_points(smoothed, beat, decay_rate, threshold)` for the `(frames, 12)` points (letter order, A first), `circle_radii(points, width, height)` for the radius in pixels of a circle with those points, and `beat_distances(beat)` for the place in the beat. Nothing about gains, decay, taper, threshold or the rate is copied or changed.
- **Rationale**: spec FR-002 and SC-001: the points must be identical to Chromatic Decay's. The letters are already in chromatic order from A (column `n` is letter `n`), which is the x order the spec assumes, so no re-ordering is needed.
- **Alternatives considered**: copying the simulation (two copies could drift apart, and the user's changes to `PRETEND_NEIGHBORS` would have to be made twice).

> **Revised 2026-11-12**: the user asked for one function instead of 12 pieces: every letter's sine runs over the whole width and the 12 are summed (divided by 12), with the phase of each letter's start added (2 pi x start / width: pi/2 a quarter of the way) and, in a second change, the frequency of each letter from its points (`p / 16` turns across the width). See the data model, "The line as one function". The text below is the first version.

## Decision 2: The line of one frame (the formula)

- **Decision**: the plot spans `width - 2 x MARGIN` pixels (`MARGIN = 10`, as Chromatic Decay), a band is `xmax = plot_width / 12` (48.33 px on 600). For band `b` (letter `b`) with `p` points, at the position `x` from 0 to `xmax` in the band, `angle = (p x 2pi + x) / (64 + xmax)` (**`x` added, as the user chose**) and the height is `A x (r / full) x sin(angle)` where `r = circle_radii(p)`, `full` is the full radius (`ring_geometry`) and `A = AMPLITUDE_SHARE x height` with `AMPLITUDE_SHARE = 1/5`: a full circle (24 points or more) reaches `A = 80 px` on 400 high, a letter with 0 points `A/12` (6.7 px). `x` and `xmax` are in plot pixels, not scaled by depth. Each band is sampled every half pixel from `x = 0` to `x = xmax` inclusive (`SAMPLES_PER_PIXEL = 2`, 98 samples a band on 600), and the 12 bands are concatenated, so the end of a band and the start of the next have the same screen x and the jump between their heights is a vertical segment of the line (spec edge case).
- **Rationale**: the spec's FR-003/004/005 exactly; the amplitude is the circle's radius in the picture's own proportion (the ratio `r / full` is 1/12 to 1), scaled to the fifth of the height of the spec.
- **Alternatives considered**: the product form `(p x 2pi x x)` (offered, not chosen); sampling once per pixel (gives visible corners on the steepest bands only when the product form is used; with the chosen form the curve is gentle, but half a pixel costs nothing).

## Decision 3: The view: depth, step, shrink, room

- **Decision**: a fixed oblique projection. The base line of the front frame is `base_0 = height - MARGIN - A` (the full downward swing of a sine still inside the picture), each older line is `STEP = 4 x height / 400` pixels higher (`base_k = base_0 - k x STEP`) and **smaller**: scale `s_k = 1 - DEPTH_SHRINK x k / (N - 1)` (`DEPTH_SHRINK = 0.25`, `s_0 = 1`, 1 for a single line), applied about the picture's horizontal center to both `x` and the height (`X = cx + (x - cx) x s_k`, `Y = base_k - z x s_k`). The number of lines that fit is `N = floor((base_0 - (MARGIN + A)) / STEP) + 1` (56 on 600 x 400): the oldest line's highest possible point `base_{N-1} - A` is at least `MARGIN` from the top.
- **Rationale**: "scroll historical data for as far as there's room"; shrink with depth is what makes it read as 3D (spec Story 2); the room is worked out from the worst case (a full circle at its highest swing) so no line ever leaves the picture whatever the data (FR-010, SC-004), using the full `A` even at the back where the lines are smaller (a safe bound).
- **Alternatives considered**: a true perspective camera with a vanishing point (more code and no more information for a plot of 56 lines); no shrink (reads as flat stacking); making `N` depend on the data (the number of lines would change with the music).

## Decision 4: Hidden lines and drawing

- **Decision**: lines are drawn **from the oldest to the newest**. For each, a polygon made of the line's vertices and the two bottom corners below its ends is filled with the background (**black**, `BACKGROUND_COLOR = (0, 0, 0)`, since the user's changes of 2026-11-12; it was the colormap's middle row, `MIDDLE_COLOR_ROW`, as for the other types, then for a moment its first row, which hid every line at the bottom of the beat), then the line is stroked over it in its color, 1.5 px wide (`LINE_WIDTH`, scaled with `height / 400` and never under 1 px: at 300 x 200 the scaled width, 0.75 px, was too faint), with no join between segments (Pillow's `joint="curve"` made a frame ten times slower, 0.20 s against 0.02 s, to round a sub-pixel notch at the sharpest corners). The whole picture is drawn on a canvas `SUPERSAMPLE = 3` times larger (Pillow `ImageDraw`) and reduced with `Image.reduce(3)` (an exact box average), giving smooth lines. Written as RGB PNGs with `compress_level=1`, in the thread pool, like the other types.
- **Rationale**: the assumption of the spec (hidden lines, so up to 56 overlapping lines stay readable); no new dependency (Pillow is used for the PNGs, and `ImageDraw` is part of it); supersampling is deterministic (same bytes for the same input), unlike a backend with its own antialiasing settings.
- **Alternatives considered**: matplotlib 3D (new heavy dependency, slow per frame, not deterministic across versions); numpy coverage rendering of polylines (more code for the same look); see-through lines (unreadable with this many lines; the user can ask for it later: it is dropping the polygon fill).

## Decision 5: The color of a line

- **Decision**: `line_colors(beat, colormap)` returns `(frames, 3)` `uint8`: for each frame the table row `rint((1 - beat_distances(beat)[t]) x 255)`, so a frame **at the top of a local peak (distance 0) has the last row and the lowest point of the beat (distance 1) the first**. A frame's line keeps its color as it moves back: the color belongs to the frame, not to the depth. With `beat=None` every line has the first color (the picture is still drawn).
- **Rationale**: the spec's FR-007/008. Using `beat_distances`, the same stretched distance as the rings of Peak Rings (feature 036), makes the whole colormap used (the raw position hardly goes below 0.55 in real music, as that feature found); before the first peak the distance is 1, the first color. This is the reverse of Peak Rings, as the spec says.
- **Alternatives considered**: the raw position `1 - peak_distances` (uses only the upper half of the colormap in real music).

## Decision 6: One line for each frame

- **Decision**: the picture of frame `t` draws the lines of frames `t, t - 1, ..., t - (N - 1)` (fewer at the start of the file: `t + 1` lines), taking the points of those frames from the same `(frames, 12)` array; the line of frame `t - k` is at depth `k`. The frames are the output frames (one for each window position), as the history of Peak Rings counts frames.
- **Rationale**: spec FR-006; it makes picture `t` equal picture `t - 1` with every line one place further back plus a new front line, which is a testable property (SC-002), apart from the shrink and step that depend on the depth only.
- **Alternatives considered**: interpolated frames are the other types' business (feature 018): this type, like the others, receives the frames after interpolation.

## Decision 7: Wiring and what is not used

- **Decision**: `chromatic_decay.CHROMATIC_TYPES = ("chromatic-decay", "chromatic-wireframe")`. `frame_rendering.write_frames`: `decay_rate = check_chromatic_rate(decay_rate) if image_type in CHROMATIC_TYPES else check_decay_rate(...)`, and a branch `if image_type == "chromatic-wireframe"` that computes `chromatic_points(smoothed, beat, decay_rate, threshold)` and calls `write_wireframe_frames(points, colormap, directory, IMAGE_WIDTH, IMAGE_HEIGHT, beat=beat)`. `jobs.py`: `_parse_decay_rate` tests `image_type in CHROMATIC_TYPES`; the beat is measured for the type as for Chromatic Decay. Note layout, the four decay amounts and every grid setting are checked and ignored. No request or response field is added.
- **Rationale**: the spec's FR-011: the same settings as Chromatic Decay; the least code that cannot drift from it.

## Decision 8: The page

- **Decision**: `IMAGE_TYPES` gets `{ value: "chromatic-wireframe", label: "Chromatic Wireframe" }` at the end; `isChromaticType` is true for both types (so the Decay rate of 1 to 10, the Threshold, the Local peaks group without a checkbox, no Note layout and the summary lines follow), with its own settings group `chromatic-wireframe` (title "Chromatic Wireframe", controls `threshold` and `chromatic-decay-rate`) added to `TYPE_GROUPS` and `TYPE_GROUP_IDS`; the image type help gets a paragraph.
- **Rationale**: the same controls with the same meaning; a group of its own because the group shown follows the image type's value.

## Decision 9: Tests that need no audio

- **Decision**: the pure functions are tested on hand-made `(frames, 12)` points (the formula against a scalar loop, the count and positions of lines, nothing outside the picture for the largest radius), the picture on small hand-made points and a hand-made beat; the job on short generated audio through the API as the other chromatic tests do, with the points compared to `circle_points` of the same smoothed values.

## Open questions

None.
