# Research: Harmonic Color

No `NEEDS CLARIFICATION` items are open. These are the design decisions.

## Decision 1: Hue arithmetic

- **Decision**: For tile `n`, let `L[k]` be the final gray level of note `k` divided by 255 (0 to 1), with `L[k] = 0` for `k` outside 0..87. Then `D = L[n+4] + L[n+5] + L[n+7]` and `U = L[n+3] + L[n+6] + L[n+8] + L[n+11]` (the offsets in `RELATED_DOWN` and `RELATED_UP`, **added, not averaged**), and the hue as a fraction of the wheel is `clip(0.5 + 0.5 × (U − D), 0, 1)`. *(Revised 2026-10-06; see below.)*
- **Rationale**: The sum is divided by 2 and moves the hue by that fraction of the whole wheel (180° ± 180° at most). One "down" note at full brightness gives `D = 1` and a hue of `0.5 − 0.5 = 0`, which is red; one at half brightness gives about 89.6°. Hue 0 and hue 1 are both red, which `colorsys` treats identically.
- **Revision (2026-10-06)**: The first version averaged each group over four notes. On the sample file the average tile has brightness 0.064, the groups differed by at most 0.1 and the hue moved by about ±18° (90% of tiles between 171° and 191°), so tiles looked uniformly teal and never red, and the largest difference over the whole file was 0.32 (57°). The user changed the rule to add the brightness instead of averaging it, clip the hue to 0°–360°, and use new lists (`RELATED_DOWN = (4, 5, 7)`, `RELATED_UP = (3, 6, 8, 11)`), which are not the same size, so averaging would also have favored the smaller group. Measured on the sample file with the new rule (brightness 2, 4, 10): the hue range for 90% of tiles widens from about 163°–231° to 135°–284° to 76°–342°, bright tiles reach 30° to 360° at brightness 4, and clipped tiles stay rare (0.0%, 0.1% and 5.3% of all tiles).
- **Alternatives considered**: Averaging each group (the first version; too small a range on real music); using the 0 to 255 value as degrees (far too small a shift for dim notes); a larger multiplier or a ratio of the two groups (offered to the user, who chose adding and clipping); dropping the "divide by 2" (would double every shift; the user only asked to stop averaging).

## Decision 2: Which luminance

- **Decision**: Both the tile's value and every related note's brightness are the *final displayed gray level*: the output of `boost_levels` applied to the 0–255 levels from `to_gray_levels`, which already follow smoothing and the brightness root. All 88 notes are boosted once per frame and then used.
- **Rationale**: FR-001 and FR-003 want one consistent brightness that matches what the viewer sees. It also keeps the brightest color channel equal to the previous gray level (FR-008), because the HSV value is that level.
- **Alternatives considered**: Using the raw note strength (hue would then respond to levels the viewer cannot see after the brightness root); using the 0–255 level before the boost (a different brightness than the tile's own value).

## Decision 3: Partners at and beyond the ends

- **Decision**: Compute all 84 hues from an 88-note array padded with 12 zeros on each side, so every partner of every drawn tile exists as an array element. Notes 84 to 87 are real elements; partners below 0 or above 87 are zeros and add nothing.
- **Rationale**: FR-004. Padding makes the neighbor lookup a set of shifted slices of one array, with no per-tile branching. The padding on each side is the largest offset in either list (now 11), so the lists can be edited without touching the code.
- **Alternatives considered**: Clamping to the nearest existing note (invents energy); per-tile `if` checks (slower and easier to get wrong).

## Decision 4: HSV to RGB with `colorsys`

- **Decision**: Convert each tile with `colorsys.hsv_to_rgb(hue, 0.5, value)` as the request asks, in a list comprehension over the 84 tiles of a frame, then round all channels at once with `numpy.rint(x * 255)` and store as `uint8`. `numpy.rint` rounds halves to the nearest even number, as the spec states (127.5 becomes 128).
- **Rationale**: The conversion is standard, and the request names the module. Measured cost for a 10,224-frame submission is about 0.4 s, around 6% of the total, against a 25% budget (SC-007). Using the module also means the tests can compare against it directly.
- **Alternatives considered**: A vectorized numpy implementation of the same formula (faster, though not measured here; it is not what was asked, and the budget does not need it); caching conversions (adds state for no need).

## Decision 5: Saturation and the "no controls" rule

- **Decision**: `SATURATION = 0.5` and the two groups are module constants (`RELATED_DOWN = (12, 7, -5, 5)`, `RELATED_UP = (4, 6, -1, 1)`). There is no setting, form field or request field for them.
- **Rationale**: FR-012. "For now" in the request suggests later controls, but none are asked for here. Constants are easy to promote to settings later.
- **Alternatives considered**: A saturation field now (scope the user did not ask for).

## Decision 6: Image format

- **Decision**: `render_frame` builds an `(168, 252, 3)` `uint8` array by reshaping the 84 colors to `(7, 12, 3)` and repeating each row 24 times and each column 21 times, then returns a Pillow `RGB` image. `write_frames` does **not** save that array: it saves an indexed-colour (palette) PNG whose 84-entry palette holds the tile colors and whose pixels are the tile numbers (see Decision 9). The two decode to exactly the same pixels, and a test checks it.
- **Rationale**: Same geometry as feature 005, one more channel. FR-009 (nothing else changes) and FR-011 (the page needs no change) follow because the file names, URLs, size and proportions are identical.
- **Alternatives considered**: Saving 24-bit RGB PNGs directly (the first implementation; correct, but see Decision 9 for why it was dropped); keeping a gray companion image (not asked for).

## Decision 7: What the tests read

- **Decision**: Tests that located a note's gray level from the pixels now take the brightest channel at the tile's center, which equals the old gray level, and the tests that said "gray" or looked at a 2-D array are updated. New tests exercise `tile_hues` and `tile_colors` directly with the spec's worked examples and an independent reference written in the test, and a recovery test: converting random tile colors back with `colorsys.rgb_to_hsv` for tiles with value 128 or more gives the hue within 2° (8-bit rounding error at saturation 0.5 is under 1° there).
- **Rationale**: SC-001 to SC-005 are stated in terms of channels and hues, so the tests check those. The brightest-channel equality is also what keeps the earlier features' tests meaningful.
- **Alternatives considered**: Comparing whole images to stored golden files (fragile, opaque).

## Decision 8: Documentation

- **Decision**: Update the README and the descriptions of the frame image in the feature 002, 004, 005 and 006 documents (gray tiles become colored tiles, and the 0–255 "gray level" is the tile's value), plus a new image contract for this feature. Earlier text is corrected, not left in contradiction.
- **Rationale**: FR-014. Earlier features' docs say the image is grayscale; leaving that would make the spec set disagree with the code.
- **Alternatives considered**: Leaving older specs as history only (earlier features have been kept in line with later changes so far).

## Decision 9: Saving frames as indexed-colour PNGs (found while implementing)

- **Decision**: `write_frames` saves each frame as an indexed-colour PNG: the pixels are a constant image of tile numbers (built once), and the palette is the frame's 84 tile colors. PNG compression level 6.
- **Rationale**: The first implementation saved 24-bit RGB PNGs and missed SC-007: on the sample file, drawing and saving 10,224 frames took 6.9 s against 4.3 s for the old gray frames (+61% on the step, which is most of a submission, so well over the 25% budget). A profile showed the cost was not `colorsys` (0.6 s) but PNG encoding of three channels (2.1 s against 0.7 s for gray) and repeating three channels (1.0 s against 0.3 s); no zlib setting changed the encode time, because it is dominated by PNG row filtering. A frame has at most 84 distinct colors, so a palette image is lossless, and with a constant index image only the palette changes per frame. Measured afterwards: the step is within noise of the gray version (+8%, −5%, −5% over three runs), and the files are 9.8 MB for the sample submission against 5.6 MB for gray. Decoding with any viewer or with Pillow gives exactly the RGB values of `render_frame`.
- **Why level 6**: At level 1 the indexed files were 29 MB per submission, run-length compression made them larger (34 MB), and level 6 gives 9.8 MB for about 0.2 s more.
- **Alternatives considered**: Dropping the 25% target (a 45% slower submission to change a file format nobody sees); vectorizing the color conversion (not the bottleneck); a single cached `Image` per frame count (the palette differs for every frame).
- **Consequence for the contract**: The served file's PNG mode is `P` (indexed), not `RGB`. It decodes to RGB pixels exactly as specified, so nothing a viewer sees differs, and the spec's requirements (colors, size, positions) are unchanged. Code that reads the served images should convert to RGB first, as the tests do.
