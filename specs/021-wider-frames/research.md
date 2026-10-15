# Research: Wider Frames (600 Pixels)

No `[NEEDS CLARIFICATION]` remains (the circles question was answered on 2026-10-14). Facts about the code were read from the repository; the timings come from a prototype (`scratchpad/size_proto.py`) that ran `write_frames` for 1,800 random-but-music-like frames (a few louder low notes, smoothing 0.3, window 3, colormap inferno) with the size constants patched to 600 × 400.

## What exists today

- `frame_rendering.py`: `GRID_COLUMNS = 12`, `GRID_ROWS = 7`, `TILE_WIDTH = 21`, `TILE_HEIGHT = 24`, `IMAGE_WIDTH = 252`, `IMAGE_HEIGHT = 168` (asserted 3:2). `write_frames` passes `IMAGE_WIDTH` and `IMAGE_HEIGHT` to the contour writer, the blender and the circles writer, and uses them for the tiles' index image (`_tile_index`, `_palette_frame`).
- `tile_edges(count, size)` (`image_types.py`) already returns "the nearest whole pixels to an even split", so tiles that do not divide evenly (a finer grid) are already handled and differ by at most one pixel.
- `make_grid_blender(blend_width, columns, rows, width, height)`: the reach of the feather is `percent / 100 * (width / columns)` pixels, so it is proportional to a tile at any frame width.
- `contour.py` draws with matplotlib at `figsize = (width / DPI, height / DPI)` and `dpi = DPI`, an exact `width × height`; it already takes the two sizes as arguments.
- `circles.py`: `plan_circles(..., width=252, height=168)` and `write_circle_frames(..., width=252, height=168)`; the circles start at `(width / 2, height / 2)`, wrap modulo `width` and `height`; the step is `units × unit` pixels and the radius is a whole number of pixels, with a 4 times larger canvas averaged down (`SUPERSAMPLE`).
- `frame_interpolation.py` blends drawn frames read back from their files, so it follows whatever size they are.
- The player (`FramePlayer.vue`): `.frame { width: min(100%, 660px); aspect-ratio: 3 / 2; image-rendering: pixelated }` and the controls `width: min(100%, 660px)`. **This is the cause of the blotchiness**: a 252 px frame is stretched to up to 660 px (2.6 times) with pixelated scaling.
- Tests: about 50 mentions of 252 or 168 in 16 test files, and the 21 × 24 tile constants in `test_frame_rendering.py` (the tile-center lookups and one blended test).

## Decision 1: The size is two constants; the 21 × 24 tile constants go

- **Decision**: `IMAGE_WIDTH = 600`, `IMAGE_HEIGHT = 400`, written directly. `TILE_WIDTH`, `TILE_HEIGHT` and their assertions are removed (a tile is no longer a whole number of pixels: 50 × 57.14), and new `REFERENCE_WIDTH = 252` and `REFERENCE_HEIGHT = 168` (the old frame, the unit of the circles' settings) and `FRAME_SCALE = IMAGE_WIDTH / REFERENCE_WIDTH` are defined next to them with the assertion that the two sizes have the same ratio (`IMAGE_WIDTH * REFERENCE_HEIGHT == IMAGE_HEIGHT * REFERENCE_WIDTH`, which holds: 600 × 168 = 400 × 252).
- **Rationale**: One definition, read everywhere. 600 / 252 = 400 / 168 (both 3:2), so the scale is one number.
- **Alternatives considered**: keep `TILE_*` as floats (they were only used to make the image size; a float tile size would invite rounding bugs); make the size a setting (the spec says it is not).

## Decision 2: Rows that do not divide are spread by `tile_edges`

- **Decision**: No change to the algorithm. At the default grid the 12 columns are exactly 50 px and the 7 rows are 57 or 58 px (`tile_edges(7, 400)` is `[0, 57, 114, 171, 229, 286, 343, 400]`); at the finest grid (60 × 35) tiles are 10 px wide and 11 or 12 px high.
- **Rationale**: Requirement FR-004 is "within one pixel", which `tile_edges` already guarantees; the indexed-colour PNG of the original grid keeps working (an index image of 600 × 400 bytes; the palette is still 84 colours).
- **Alternatives considered**: 399 px high (7 × 57, equal rows, but not 3:2 and not 400); 420 px high (7 × 60, equal rows, but a 10:7 shape).

## Decision 3: Blended and contour need no new code

- **Decision**: Their writers already take `width` and `height`; the feather reach is a percentage of the tile width, so at 25% it is 12.5 px (was 5.25 px): the same in proportion. The contour writer's matplotlib figure is `width / DPI` by `height / DPI` inches. Their docstrings that quote pixel counts (the "10 pixels across" feather, the 252 × 168 mentions) are corrected.
- **Rationale**: This is the "drawn at the new size, not enlarged" requirement (FR-003) for free; the test of equivalence (below) proves that nothing else moved.

## Decision 4: Circles are scaled by `width / 252` inside the writer

- **Decision**: `plan_circles` and `write_circle_frames` get `scale = width / REFERENCE_WIDTH` (derived from the width that is passed, so a call with the default 252 is exactly what it was). The step of a note is `units × unit × scale` pixels (the angle is unchanged), the radius is `radius × scale × resize_factor`, the start is the middle of the frame and the wrap uses `width`/`height` as now. The settings, ranges, messages and request fields do not change.
- **Rationale**: Clarification option A: the same settings give the same picture in proportion to the frame, only sharper. Deriving the scale from the width keeps every existing circles test valid at 252 and makes the new behaviour testable by passing `width=600, height=400`.
- **Alternatives considered**: a `scale` argument with a default of 1 (a second number to keep equal to the frame size); scaling in the router (the writer would then not be correct for its own callers).

## Decision 5: The circles' supersampling stays at 4

- **Decision**: Keep `SUPERSAMPLE = 4`. At 600 × 400 the working canvas is 2400 × 1600 (3.8 million pixels).
- **Rationale**: Measured: circles at 600 × 400 take 11.9 s (defaults) and 19.3 s (the largest settings) for 1,800 frames, against the two-minute limit; the edges are the point of the feature. A smaller factor (2 or 3) is possible if a limit is ever approached, but there is no need.

## Decision 6: The player at most 600 px, smooth scaling

- **Decision**: `.frame { width: 100%; max-width: 600px; aspect-ratio: 3 / 2 }` (the same `max-width` for the controls), and `image-rendering` is removed (the browser's default smooth scaling), because the frames are no longer enlarged and a pixelated downscale on a narrow screen would alias.
- **Rationale**: FR-008, SC-007. At 600 px the frame is shown 1:1; on a narrower window it is scaled down smoothly.
- **Alternatives considered**: keep `min(100%, 660px)` (a 10% enlargement of a sharp frame: soft for no gain); keep `pixelated` (right for enlarging flat tiles, wrong for shrinking anything).

## Decision 7: Help texts say what "px" means for circles

- **Decision**: The Movement and Radius help texts add that the numbers are measured against a frame 252 pixels wide and are drawn 2.4 times larger on the 600-pixel frame; the readout "4 px" stays.
- **Rationale**: The spec left it to the plan; without the sentence "4 px" would be read as 4 pixels of the frame the user sees.

## Decision 8: Tests follow one definition of the size

- **Decision**: `tests/frame_size.py` exports `WIDTH = 600`, `HEIGHT = 400`, `REFERENCE_WIDTH = 252`, `REFERENCE_HEIGHT = 168`, `SCALE`; the tests that used 252/168 import them. `tests/test_frame_size.py` states `(600, 400)` literally and checks the app's constants against it, so a wrong constant is caught even though the other tests read the same constants. The tile-center lookups of `test_frame_rendering.py` use `tile_edges`. The circles tests keep working in reference pixels: the `Discs` spy divides by the scale and the pixel lookups multiply by it.
- **Rationale**: Changing 50 numbers by hand invites mistakes and the next size change would repeat it; the literal test keeps the tests honest.

## Decision 9: Equivalence tests instead of byte equality

- **Decision**: What must be equal is the content. (a) Tiles: the color at the center of every tile at 600 × 400 equals the old tile color (render at 252 × 168 and 600 × 400 and compare the centers, at every oversampling); the tile columns and rows are within one pixel. (b) Blended and contour: the low-level writers are called with `252, 168` and with `600, 400`, the 600 × 400 frame is reduced to 252 × 168 (area average) and compared with the old one: mean absolute difference below a small bound, and the colors of flat regions equal. (c) Circles: `write_circle_frames` at `width=252` and at `width=600` give discs whose centers and radii differ by exactly the scale (spy), and the pictures reduced to 252 × 168 are close. (d) Interpolation: the in-between frames have the new size.
- **Rationale**: SC-003, SC-004 and the circles criterion are about content; the new files cannot equal the old ones.

## Decision 10: Time and room

- **Prototype results** (1,800 frames; old size to new size; room as the sum of the PNG sizes):

| Job | 252 × 168 | 600 × 400 | Room (old → new) |
|-----|-----------|-----------|------------------|
| tiles | 0.7 s | 1.0 s | 2 → 5 MB (2.7×) |
| tiles, oversampling 5 | 2.2 s | 7.1 s | 9 → 12 MB (1.3×) |
| blended | 0.9 s | 7.0 s | 18 → 67 MB (3.6×) |
| blended, oversampling 5 | 1.9 s | 8.5 s | 22 → 77 MB (3.5×) |
| contour | 26.5 s | 34.3 s | 4 → 10 MB (2.5×) |
| contour, oversampling 5 | 17.6 s | 21.8 s | 4 → 11 MB (2.6×) |
| contour, oversampling 5, interpolate 5 | 4.3 s | 6.3 s | 7 → 16 MB (2.4×) |
| circles, defaults | 3.3 s | 11.9 s | 40 → 50 MB (1.3×) |
| circles, largest settings | 9.1 s | 19.3 s | 76 → 139 MB (1.8×) |

- **Decision**: No tuning is needed to meet SC-005 (one minute at the defaults: the slowest default is contour at 34 s; two minutes at the costliest: 22 s) and SC-006 (4 times: the largest is blended at 3.6). The blended files are the closest to the room limit; their PNG compression level stays 1 (level 6 would cost time for a modest gain); if the real measure after the change exceeds 4 times, raising the level is the first thing to try. (The old contour job at resolution 1 is slower than at resolution 5 because the contour work is per frame and the finer grid interpolates fewer features; unchanged by this feature.)
- **Note**: the circles figures above were measured with the unscaled pixel sizes (the scale was not yet applied); the scaled circles are larger discs on the same canvas, which costs about the same (the cost is the canvas size and the number of discs), and the real figure is measured again after the change.

## Decision 11: Documentation

- **Decision**: README states the new size and the changed derived numbers (the 21 × 24 tiles become 50 × 57/58, the 10-pixel feather at the default blend width becomes about 12.5 px) and the circles scaling; the earlier specs that define the old frame size (002, 005, 013, 015, 019) get an amendment note rather than a rewrite, as for earlier changes.

## Open items

None. Not verifiable here: how the 600 px frame looks in the player in a real browser (the quickstart's manual step).
