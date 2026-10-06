# Research: Octave Grid Layout

No `NEEDS CLARIFICATION` items are open; both were resolved in the spec's Clarifications section. These are the design decisions.

## Decision 1: Geometry and whole pixels

- **Decision**: 12 columns × 7 rows of tiles that are 21 pixels wide and 24 pixels tall, giving a 252 × 168 image. Constants `GRID_COLUMNS = 12`, `GRID_ROWS = 7`, `TILE_WIDTH = 21`, `TILE_HEIGHT = 24`, `SHOWN_NOTES = 84`. Import-time assertions check that `TILE_WIDTH × 8 == TILE_HEIGHT × 7` (tile width is 87.5% of height), that `IMAGE_WIDTH × 2 == IMAGE_HEIGHT × 3` (exactly 3:2) and that `GRID_COLUMNS × GRID_ROWS == SHOWN_NOTES`.
- **Rationale**: 7:8 is the exact ratio of 0.875, so the smallest whole-pixel tile is 7 × 8. That makes a 84 × 56 image, too small to see. Scaling by 3 gives 21 × 24 and an image close in size to the old 220 × 160, so file size and speed are unchanged. The ratio is checked by arithmetic on integers, not by comparing floats.
- **Alternatives considered**: A smaller 7 × 8 tile (image too small to read when the page does not scale it); 28 × 32 (larger images and slower writing for no gain, since the page scales the image anyway).

## Decision 2: Note placement

- **Decision**: Tile (row *r*, column *c*) shows note `12 × r + c`, row 0 at the top and column 0 at the left. `render_frame` takes the first 84 of the 88 values, reshapes them to 7 × 12, then repeats each row 24 times and each column 21 times.
- **Rationale**: Row-major order puts the lowest note top-left and the tile below a note exactly 12 notes (one octave, double the frequency) higher. It is the same reading order the previous layout used, so only the grid width and the tile shape change.
- **Alternatives considered**: Highest octave on top, like a piano roll (the spec reads "above" literally, and the clarified answer kept the lowest note top-left); labeling columns with note names (out of scope).

## Decision 3: Gray-level scaling stays on all 88 notes

- **Decision**: `to_gray_levels` is unchanged: it scales against the largest value anywhere in the file across all 88 notes, and the brightness root is applied after. Only `render_frame` drops the four highest values.
- **Rationale**: The spec requires that a note's gray level equal its level in the previous layout for the same file and settings (FR-007, SC-004). Scaling only the 84 shown notes would change levels whenever one of the omitted notes is the loudest.
- **Known consequence**: If one of the four omitted notes (7040 to 8372 Hz) is the loudest value in a file, the visible notes are scaled against a note you cannot see, so none of them reaches full white. This needs an unusually bright top end. During implementation this is measured on the sample file and reported, and the docs mention it.
- **Alternatives considered**: Scaling over the 84 shown notes (always uses the full range, but changes levels against the previous layout and contradicts FR-007).

## Decision 4: Rejecting too-short input

- **Decision**: `render_frame` accepts any array of at least 84 values and uses the first 84. Fewer raises `ValueError`. The pipeline always passes 88.
- **Rationale**: Quietly drawing a partial grid from short input would hide a bug upstream. Accepting the full 88 keeps the call sites in `write_frames` and the tests simple.
- **Alternatives considered**: Requiring exactly 88 (stricter than needed) or exactly 84 (would force callers to slice).

## Decision 5: Showing the new shape in the page

- **Decision**: In `FramePlayer.vue`, add `aspect-ratio: 3 / 2` to the frame image style, keeping `width: min(100%, 660px)` and `image-rendering: pixelated`.
- **Rationale**: Without it the image has no height until the first frame loads, so the page jumps, and again if a frame is slow to arrive. With the ratio declared, the page reserves the exact space, the image keeps 3:2 at every width (SC-007) and stays the same size from frame to frame (FR-009). It matches the 252 × 168 pixels, so nothing is stretched.
- **Alternatives considered**: Reading the width and height from the first loaded frame (more code for no benefit); a fixed pixel height (breaks at narrow widths).

## Decision 6: Existing stored images

- **Decision**: Nothing is migrated or rewritten. Frame URLs contain a new job id for every submission and are served with a long cache lifetime, so a new submission never reuses an old image.
- **Rationale**: FR-011. Old submissions in the temp directory keep their square layout until the operating system clears them.
- **Alternatives considered**: Regenerating old frames (the audio is still there, but nothing asks for it and the spec forbids changing stored images).

## Decision 7: Tests that read pixels

- **Decision**: Update the tests that located squares with `n // 11` and 20-pixel squares. The API test helper reads one pixel from the center of each of the 84 tiles and returns 84 values. A new layout test file section checks geometry, placement, the octave rule, the omitted notes and the image size directly on `render_frame`.
- **Rationale**: One helper replaces scattered position arithmetic, and the new tests express the spec's rules (SC-001 to SC-004) in terms the spec uses.
- **Alternatives considered**: Duplicating the arithmetic in each test (error-prone).

## Decision 8: Documentation

- **Decision**: Update the README and the feature 002 documents that describe the image (spec FR-009 and assumptions, contract, data model, research, plan, quickstart and checklist note) so each says the layout was replaced by feature 005, with the new size and rules. Older text is corrected, not left contradicting the code.
- **Rationale**: FR-010. Leaving "11 × 8" in place would make the spec set disagree with itself.
- **Alternatives considered**: Leaving feature 002 untouched as history (the earlier features have been kept in line with later changes so far, and the spec says the docs must be updated).
