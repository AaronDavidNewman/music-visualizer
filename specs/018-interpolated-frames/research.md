# Research: Interpolated Frames

> **Amendment 2026-10-13**: the interpolation function was removed after the user saw the rendered frames ("The others don't really work"). Only `blend` is made: there is no function dropdown, no `interpolate_function` field and no response key for it, and no `soft_light`, `hard_light`, `overlay`, `screen` or `subtract` code. A request that still sends `interpolate_function` is accepted and the field is ignored. [spec.md](spec.md), [data-model.md](data-model.md) and [contracts/interpolate-api.md](contracts/interpolate-api.md) describe the result; this document is kept as it was written, so the passages about the five other functions, option B and the function dropdown describe the first version.

No `NEEDS CLARIFICATION` items remain in the spec: Question 1 (how the five functions without a weight use the position between two drawn frames) was answered by the user with option B, `f(earlier, blend(earlier, later, k / n))`. The decisions below were checked with a throwaway prototype (Pillow 12.3.0, matplotlib 3.10.9, a synthetic 300-frame file), not assumed.

## Measurements from the prototype

| Question | Result |
|----------|--------|
| Pillow 12.3.0 has `Image.blend` and `ImageChops.soft_light`, `hard_light`, `overlay`, `screen`, `subtract` | yes, all six; only `blend` takes a weight; the others take two pictures (`subtract` also an optional scale and offset) |
| Drawing one frame (including smoothing and colors, averaged over 300 frames) | Tiles 0.55 ms, Blended tiles 0.56 ms, Contour 9.4 ms |
| Computing one in-between frame from two RGB pictures | blend 0.10 ms; `f(earlier, blend(...))` 0.21 to 0.26 ms for the five functions |
| Saving an in-between frame as a PNG | 0.4 to 0.7 ms (compress level 1 and 6 within 0.15 ms of each other; level 6 files about half the size: 0.5 to 1.8 KB for tile pictures, 1.1 to 1.8 KB for contour) |
| Loading a drawn frame from its PNG and converting it to RGB | 2.7 ms (Tiles, palette) to 3.3 ms (Contour, RGBA) |
| A whole 300-frame job at interpolate 5 (61 drawn, 239 in-between), Tiles | drawing 34 ms + in-between 127 ms single-threaded (72 ms on 4 threads) against 165 ms to draw all 300: no saving (the key frames' reloading adds about 150 ms single-threaded) |
| The same, Contour | drawing 576 ms + in-between 201 ms (75 ms on 4 threads) against 2,831 ms to draw all 300: about 3.4 times faster (4 to 5 times faster on 4 threads) |

So interpolation is a real gain for the contour only; for the tile pictures making an in-between frame costs about as much as drawing one. The spec's Story 3 scenario 6 and SC-005 say exactly this.

## Decision 1: One module for the setting, the key frames and the in-between frames

- **Decision**: A new module `app/services/frame_interpolation.py` holds `MIN_INTERPOLATE = 1`, `MAX_INTERPOLATE = 5`, `DEFAULT_INTERPOLATE = 1`, `INTERPOLATE_FUNCTIONS = ("blend", "soft_light", "hard_light", "overlay", "screen", "subtract")`, `DEFAULT_INTERPOLATE_FUNCTION = "blend"`, `check_interpolate(value)` (a whole number from 1 to 5, not a bool; message `The interpolate value must be a whole number from 1 to 5.`), `check_interpolate_function(value)` (exactly one of the six names, no trimming or case folding; message `The interpolation function must be one of blend, soft_light, hard_light, overlay, screen, subtract.`), `key_frames(count, interpolate)` and `write_interpolated_frames(directory, count, interpolate, function)`. It knows nothing about the note analysis or the pictures' content: it only reads PNG files and writes PNG files.
- **Rationale**: Like `resolution.py` and `note_selection.py`: the setting, its checks and the work are one concept used by the writers, the router and the tests.
- **Alternatives considered**: Putting it in `frame_rendering.py`: that file is the shared pipeline, and a separate unit is easier to test.

## Decision 2: Which frames are drawn

- **Decision**: With `count` frames (numbered from 0 as the files are) and interpolate `n`, the drawn frames are `sorted(set(range(0, count, n)) | {count - 1})` (none for `count == 0`). The smoothing and the colors are still worked out for all frames, which costs little; the writers draw only the drawn frames, into the files with their own numbers (`frame_000005.png` for the sixth frame). Each writer takes the list of frames to draw: the Tiles and Blended loops iterate over it, and `write_contour_frames` gets an `indices` argument.
- **Rationale**: FR-002 and FR-009: the drawn frames are exactly the frames of interpolate 1, so their bytes are identical to the ones made without interpolation (the arrays and the writers are the same), and the pictures drawn are about `count / n`. At `n = 1` every frame is drawn and nothing else happens: the output is today's.
- **Alternatives considered**: Computing the values only for the drawn frames: smoothing needs the earlier frames anyway and the values cost microseconds. Holding the last drawn frame instead of drawing the last frame of the file: the spec chose to draw it.

## Decision 3: The in-between frames, from the drawn files, with Pillow

- **Decision**: After the drawing, for every pair of neighboring drawn frames `a < b` (gap length `g = b - a`, at most `n`) and every `i` in `a + 1 .. b - 1`, with `w = (i - a) / g`: load both pictures with `Image.open(...).convert("RGB")` (the palette Tiles frames and the RGBA contour frames become plain RGB; the alpha of a contour frame is 255 everywhere), `mixed = Image.blend(earlier, later, w)`, and the frame is `mixed` for blend or `ImageChops.<function>(earlier, mixed)` for the other five, saved as `frame_{i:06d}.png` with compress level 6. The work of one gap (loading its two drawn frames and writing its in-between frames) is one task on a thread pool of `min(4, cpu_count)` workers: Pillow's blend, channel operations and PNG encoding release the interpreter lock, so the gaps run in parallel and the files are the same whatever the number of threads. The first error of a worker is raised.
- **Rationale**: This is FR-004 to FR-006 (all arithmetic is Pillow's; the application only chooses pictures and weights) and the user's option B. Reading the drawn files keeps the three writers unchanged apart from "which frames", and loads each drawn frame twice (once per neighboring gap), which costs 5.4 to 6.6 ms a gap and is hidden by the pool. Estimated on 4 threads for 300 frames at interpolate 5: about 150 ms for the Tiles pass against 165 ms to draw all of them, and about 80 ms to 150 ms for the contour against 2.8 s.
- **Alternatives considered**: Keeping the drawn images in memory: saves the reloading (about 150 ms single-threaded for 300 frames) but needs each writer to hand over its image, and for the contour a second render or a buffer copy; not worth the coupling. Computing the pixels with numpy: the spec says Pillow, and Pillow's functions are the definition of the result.
- **Note on option B**: the in-between frame next to the later drawn frame approaches `f(earlier, later)`, not `later`, for the five functions, so the animation steps back to the plain drawn frame at the next drawn frame (stated in the spec's Edge Cases). With blend the gap runs smoothly into the drawn frame.

## Decision 4: The in-between frames are RGB PNGs

- **Decision**: In-between frames are saved as 8-bit RGB PNGs whatever kind the drawn frames are (the drawn frames are untouched).
- **Rationale**: `ImageChops` works on color pictures; a blend of two palette pictures has many more colors than a palette holds; and the contour's alpha channel is constant 255. Every frame is 252 × 168 and the player plays any such PNG.
- **Alternatives considered**: RGBA for all: larger files for no gain.

## Decision 5: API and page

- **Decision**: The router gets two optional form fields, `interpolate` (a parser like `_parse_resolution`: not sent 1; `"3"`, `"3.0"` accepted; empty, non-numeric, fractional, out of range refused with the message above) and `interpolate_function` (not sent `blend`; sent, it must be exactly one of the six names, otherwise the message above; an empty value is refused), both checked before the file is read, passed to `write_frames`, and reported in the response as `interpolate` and `interpolate_function`. The frontend gets a slider (1 to 5, step 1, starting at 1) with the readout `1 (every frame drawn)` / `3 (one frame in 3 drawn)` and a dropdown of the six functions (Blend, Soft light, Hard light, Overlay, Screen, Subtract, starting at Blend) that is disabled while Interpolate is 1 and while a job runs, both after the Resolution control, each with an info text; the summary gets `Interpolate: 1` or `Interpolate: 5 (Blend)`.
- **Rationale**: The same shape as every earlier setting; the dropdown follows the colormap and image type dropdowns.
- **Alternatives considered**: A single combined setting: the spec has two fields.

## Decision 6: Tests are colormap-list tolerant and use Pillow as the reference

- **Decision**: The tests follow the rules of features 014 to 017 (no colormap names, no number of contour levels). The in-between frames are checked three ways: against Pillow directly (decode the two drawn files, apply the formula of FR-004/FR-005 with `Image.blend` and `ImageChops` in the test, compare), against plain numpy for blend (each pixel is within one level of the weighted mix), and by their properties (identical neighbors give identical blend frames; the drawn frames equal the frames of interpolate 1 byte for byte for every image type and function; the number of pictures drawn is counted by spying on the writers: `_palette_frame`, `_save_blended` and `Axes.contourf`). The four reference hashes at interpolate 1 must not change.
- **Rationale**: The functions' outputs are Pillow's definition; testing them against Pillow plus independent properties catches wiring errors (wrong weight, wrong order of arguments, wrong gap length at the end of the file) without restating Pillow.
- **Alternatives considered**: Pixel-exact expectations computed by hand for the five functions: would restate Pillow.

## Decision 7: Time criteria

- **Decision**: The tests assert that a 300-frame contour job at interpolate 5 takes at most half the time of the same job at interpolate 1 (measured separately in the task about timings, since a unit test on timing is fragile, with a generous bound in the test suite) and that Tiles and Blended tiles jobs take no more than 25% longer, as in the spec.
- **Rationale**: Honest limits from the measurements: the contour gains about 3 to 5 times, the tile pictures break even.
