# Feature Specification: Harmonic Color

**Feature Branch**: `007-harmonic-color` (no git branch created; spec directory name only)

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "add some color based on combinations of notes. Render the tiles as an HSV value. For now keep the saturation at 50%, and the existing value is the luminance (scaled to 100% for 255). We will create a new binned value for the hue by adding the luminance of some related tiles: At each sample, the default hue will be 180 (of 360). Average some tiles and divide by 2, this will move in the red direction (subtract). These are: bin n+12, bin n+7, bin n-5, bin n+5. The tiles to move in the blue direction (add to 180) will be: n+4, n+6, n-1, n+1. Use colorsys and convert the HSV values back into RGB values for rendering."

## Clarifications

### Session 2026-10-06

- Q: Why did every tile look green-blue, with no red? → A: With each group's brightness *averaged*, the hue moved by only about ±18° on the sample file, because the average tile is dim and reaching red needed every partner at full brightness. The user changed the rule: the related notes' brightness is now **added up, not averaged**, and the hue is **clipped** to 0°–360°.
- Q: Which notes are related? → A: The user changed the lists. "Down" group: *n* + 4, *n* + 5, *n* + 7. "Up" group: *n* + 3, *n* + 6, *n* + 8, *n* + 11. The groups are different sizes (which is why they are added, not averaged), and there is no octave (*n* + 12) partner any more.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Color each tile by the notes that sound with it (Priority: P1)

A user looking at a frame sees colored tiles instead of gray ones. A tile's **brightness** is the gray level it has today. Its **color** depends on which *related* notes are sounding at the same time. With nothing related sounding, the tile is cyan (hue 180° on the 360° color wheel). Notes in the first related group pull the hue down from 180° (toward green, yellow, then red), and notes in the second group push it up (toward blue, violet, then red). So chords and overtones show up as color, not only as separate bright tiles.

For the tile of note *n*, the related notes are:

- **Pull the hue down** (toward green, yellow, then red), the "down" group: notes *n* + 4, *n* + 5 and *n* + 7.
- **Push the hue up** (toward blue, violet, then back to red), the "up" group: notes *n* + 3, *n* + 6, *n* + 8 and *n* + 11.

The brightness of the notes in each group, on a scale from 0 (black) to 1 (255), is **added up** (not averaged), divided by 2, and moves the hue by that fraction of the whole wheel. So the hue in degrees is 180 + 180 × (sum of the "up" group − sum of the "down" group), clipped to the range 0° to 360°. Because the notes are added, one partner at full brightness is already enough to reach red, while the dim partners of ordinary music move the hue only part of the way. Most tiles are therefore not clipped, and the hue keeps changing with the music.

**Why this priority**: This is the whole feature: turning relationships between notes into color.

**Independent Test**: Make a frame in which a tile is at full brightness and exactly one related note is lit at full brightness (and nothing else is). The tile's color follows the rule: with no related note lit its hue is 180°, with only note *n* + 4 lit at full brightness its hue is 0° (red), and with only note *n* + 4 at half brightness its hue is about 90°.

**Acceptance Scenarios**:

1. **Given** a tile at full brightness and none of its seven related notes lit, **When** the frame is drawn, **Then** its hue is 180° and its color is (128, 255, 255).
2. **Given** a tile at full brightness and only note *n* + 4 (a "down" note) lit at full brightness, **When** the frame is drawn, **Then** its hue is 0° (the "down" sum is 1, so the hue falls by 180°) and its color is (255, 128, 128), a red.
3. **Given** a tile at full brightness and only note *n* + 3 (an "up" note) lit at full brightness, **When** the frame is drawn, **Then** its hue is 360°, which is the same red, and its color is (255, 128, 128).
4. **Given** every note of the "down" group lit at full brightness and none of the "up" group, **When** the frame is drawn, **Then** the sum is more than 1 and the hue is clipped to 0° (red). The same happens with every note of the "up" group lit and none of the "down" group: the hue is clipped to 360°, the same red. It does not wrap around further.
5. **Given** the "down" sum and the "up" sum equal, **When** the frame is drawn, **Then** their effects cancel and the hue is 180°.
6. **Given** a "down" note at half brightness (gray level 128) and nothing else lit, **When** the frame is drawn, **Then** the hue is about 89.6° and the color is (192, 255, 128). A "up" note at half brightness gives about 270.4° and (192, 128, 255). Dimmer partners move the hue less, in proportion to their brightness.
7. **Given** two "up" notes each at quarter brightness (gray level 64), **When** the frame is drawn, **Then** the hue moves exactly twice as far from 180° as with one of them, because their brightness is added.
8. **Given** any frame, **When** it is drawn, **Then** a tile's color is set only by its own brightness and by the brightness of its seven related notes in that same frame.

---

### User Story 2 - Brightness, layout and everything else stay as they were (Priority: P2)

Turning the picture to color must not change what the tiles mean. Each tile keeps its position, its brightness and its place in the octave grid, a silent file stays black, and nothing about the analysis, the frame count or the timing changes. The page shows the colored frames at the same size and proportions as before, and the project's description of the image is updated.

**Why this priority**: Users rely on the brightness and layout from earlier features. The color is added on top, and it depends on Story 1.

**Independent Test**: Make frames for the same file and settings before and after this feature. Every tile's brightest color channel equals the gray level it had before (give or take 1), the darkest channel is about half of it, and the frame count, tile positions and timing are the same.

**Acceptance Scenarios**:

1. **Given** the same file and settings as before this feature, **When** frames are created, **Then** every tile's brightest color channel equals its previous gray level to within 1, and its darkest channel is about half of that.
2. **Given** a tile with brightness 0, **When** it is drawn, **Then** it is black, whatever its hue would be.
3. **Given** a silent file, **When** frames are created, **Then** every pixel is black (0, 0, 0).
4. **Given** any file, **When** frames are created, **Then** the image is still 252 × 168 pixels, 12 columns by 7 rows of 21 × 24 tiles, with each note in the same tile as in the previous layout.
5. **Given** the same file and settings, **When** frames are created twice, **Then** the images are identical.
6. **Given** a completed submission, **When** the page shows a frame, **Then** it is shown in color at the same size and 3:2 proportions as before, and playback works as before.
7. **Given** a different brightness or smoothing setting, **When** frames are created, **Then** the color is worked out from the brightness the tiles end up with after that setting is applied, and the setting keeps its effect on brightness.
8. **Given** the project's written description of the image, **When** it is read, **Then** it describes the color rule, the related notes, the fixed 50% saturation and the new image format.

---

### Edge Cases

- **Related notes past the ends of the range**: Notes below the lowest note or above the highest note do not exist and count as silent (brightness 0). Because brightness is added, a missing partner simply adds nothing. So the highest tiles, whose partners above the top of the range do not exist, pick up less color shift than tiles in the middle.
- **The four notes that are not drawn**: Notes 84 to 87 are not shown, but they are real notes with real brightness. They count as related notes for the tiles whose partners they are (for example note 84 is the *n* + 11 partner of tile 73 and the *n* + 3 partner of tile 81).
- **Hue wraps around**: The hue always stays between 0° and 360°. The two ends are the same red. A tile whose partners add up to more than the wheel allows is clipped at 0° or 360° (both red) and does not wrap around further. With ordinary, dim partners most tiles are not clipped.
- **Dark tiles hide their color**: A tile with brightness 0 is black. A very dim tile has almost no visible color, because its darkest and brightest channels are close together at low values, even though its hue is calculated the same way.
- **Pastel look**: At 50% saturation a tile's darkest channel is half of its brightest, so even the brightest tile is a pastel color, not pure white or a vivid color.
- **Isolated note**: A single steady note lights one tile in cyan. The tiles for its related notes, such as the tile 4 notes below it, get a shifted hue in their own calculation, but they are dark, so little changes on screen. Color becomes visible when related notes sound together.
- **Both groups lit**: A note with partners in both groups can come out at cyan again because the two shifts cancel, even though the tile is not "neutral".
- **Settings**: Brightness, smoothing, window size, frame rate and window spacing work as before. Color is worked out last, from the final brightness of every note. Smoothing also smooths each tile's hue over the frames (see the feature 006 spec, FR-014), so with smoothing above 0 colors change gradually as well as brightness.
- **Earlier submissions**: Images already stored keep their gray look. Only new submissions are in color.
- **Saturation**: It is fixed at 50% for now. There is no control for it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each tile in a frame image MUST be drawn as a single flat color worked out from hue, saturation and value, where saturation is always 50% and value is the tile's final gray level (after scaling and the brightness and smoothing settings), with 255 meaning 100%.
- **FR-002**: The hue of the tile for note *n* MUST be 180° plus 180° × (*U* − *D*), clipped to the range 0° to 360°, where *D* is the sum of the brightness of the notes *n* + 4, *n* + 5 and *n* + 7 (the "down" group), and *U* is the sum of the brightness of the notes *n* + 3, *n* + 6, *n* + 8 and *n* + 11 (the "up" group), each brightness measured from 0 (black) to 1 (255). The brightnesses are added, not averaged, so the groups need not be the same size. This is the same as moving the hue down by *D* ÷ 2 of the wheel and up by *U* ÷ 2 of the wheel from 180°.
- **FR-003**: The brightness used for the related notes MUST be the same final gray level that is used for a tile's value (FR-001), taken from the same frame.
- **FR-004**: Related notes outside the 88-note series (below note 0 or above note 87) MUST count as brightness 0 (they add nothing). Notes 84 to 87 MUST count as related notes even though they are not drawn.
- **FR-005**: With no related note lit, the hue MUST be 180°. With the two sums equal, it MUST be 180°. The hue MUST never leave the range 0° to 360°: a sum beyond the wheel is clipped to 0° or 360°, not wrapped around, and 0° and 360° MUST give the same color.
- **FR-006**: The color MUST be converted from hue, saturation and value to red, green and blue, with each channel rounded to a whole number from 0 to 255, using the standard conversion.
- **FR-007**: A tile with value 0 MUST be black (0, 0, 0). A silent file MUST give images that are entirely black.
- **FR-008**: A tile's brightest color channel MUST equal its gray level from before this feature, to within 1, and its darkest channel MUST be about half of that (saturation 50%).
- **FR-009**: The image size (252 × 168 pixels), the octave grid layout (12 columns by 7 rows of 21 × 24 tiles, note *n* at row *n* ÷ 12, column *n* mod 12), the number of frames, the analysis windows, the window spacing and the frame timing MUST NOT change.
- **FR-010**: Given the same file and settings, the system MUST produce the same images every time.
- **FR-011**: The page MUST show each colored frame at the same size and proportions as before, and playback MUST work as before.
- **FR-012**: There MUST be no user setting for saturation or for the related-note groups in this feature. They are fixed.
- **FR-013**: Images stored by earlier submissions MUST NOT be changed.
- **FR-014**: The project's written description of the frame image MUST be updated to describe the color rule, the fixed saturation and the new image format.

### Key Entities

- **Tile**: One rectangle in the octave grid, now drawn in a single color.
- **Gray level**: The final 0–255 brightness of a note in a frame, after scaling to the loudest value, the brightness setting and the smoothing setting. It is the tile's value, and it is also the brightness used when the tile counts as a related note for another tile.
- **Related notes**: For note *n*, the "down" group (*n* + 4, *n* + 5, *n* + 7) and the "up" group (*n* + 3, *n* + 6, *n* + 8, *n* + 11). The groups are edited in one place in the code (`RELATED_DOWN` and `RELATED_UP`) and may change size.
- **Hue**: An angle on the 360° color wheel, between 0° and 360°. Starts at 180° (cyan) for every tile and is shifted by the related notes.
- **Saturation**: How far the color is from gray. Fixed at 50%.
- **Frame image**: The picture for one animation frame: a 252 × 168 grid of 12 × 7 tiles, now in color.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every tile in every tested frame, the brightest color channel equals the tile's previous gray level to within 1, and the darkest channel is within 1 of half the brightest, in 100% of tested tiles.
- **SC-002**: A tile at full brightness with no related note lit comes out as (128, 255, 255). With only note *n* + 4 (a "down" note) at full brightness it comes out as (255, 128, 128) (hue 0°). With only note *n* + 3 (an "up" note) at full brightness it comes out as (255, 128, 128) (hue 360°, the same red). With only a "down" note at half brightness it comes out as (192, 255, 128) (hue about 89.6°), and with only an "up" note at half brightness as (192, 128, 255) (hue about 270.4°).
- **SC-003**: For random test frames, the hue of each tile, recovered from its color for tiles with a value of at least 128, is within 2° of 180° + 180° × (*U* − *D*), clipped to the 0°–360° wheel, for all 84 drawn tiles.
- **SC-004**: A silent file gives images in which every pixel is (0, 0, 0), at every brightness and smoothing setting.
- **SC-005**: With every note of one group at full brightness and none of the other, the hue is clipped to 0° (red) for the "down" group and 360° (the same red) for the "up" group, and no hue outside 0° to 360° ever occurs. On ordinary music most tiles are not clipped: in tests on dim, music-like frames more than 90% of the hues are strictly between 0° and 360°.
- **SC-006**: Image size, tile positions, frame count, window count and frame timing are the same as before this feature for 100% of tested files.
- **SC-007**: The time to create frames for the same file and settings is no more than 25% longer than before this feature.
- **SC-008**: The same file and settings give identical images, byte for byte, every time.

## Assumptions

- **Units for the hue arithmetic**: Brightness is taken on a 0 to 1 scale (255 = 1). Each group's brightness is *added* (not averaged, which the user changed after seeing no red), the sum is divided by 2 as in the original request, and that result is a fraction of the whole 360° wheel. So the hue in degrees is 180 + 180 × (*U* − *D*), clipped to 0° to 360°. Example: only note *n* + 4 at full brightness gives a "down" sum of 1, which is half the wheel, and a hue of 0°. The "divide by 2" is kept; dropping it would double every shift again.
- **Which brightness counts**: The "luminance" of a note is its final displayed gray level: after scaling against the loudest value in the file, the brightness (root) setting and the smoothing setting. The same number is used as the tile's value and as the brightness of a related note. The alternative of using the raw note strength is not used.
- **"The notes" are the 88-note series**: Related bins are numbered in the full 88-note series from feature 001, so partners beyond the 84 drawn notes (notes 84 to 87) are real, and only partners outside 0 to 87 are treated as silent.
- **Missing partners count as silence**: A partner outside the series counts as brightness 0 and adds nothing, so a tile at the end of the range is shifted less than a tile in the middle. This follows from adding instead of averaging.
- **Clipping, not wrapping**: A sum that would take the hue beyond the wheel is held at 0° or 360° (both red), as the user asked, so a very loud group of partners saturates at red instead of cycling back through other colors.
- **Fixed saturation**: Saturation is 50% for now, as the request says. It is not a setting yet.
- **Standard conversion**: The conversion from hue, saturation and value to red, green and blue is the standard one. The request names Python's `colorsys` module for it. The spec does not require that module in particular, only the standard result.
- **Rounding**: Each color channel is rounded to the nearest whole number from 0 to 255 (halves round to the nearest even number, so 127.5 becomes 128).
- **Color replaces gray**: Frames are always in color. There is no gray-scale option in this feature.
- **Dependencies**: This changes the frame image from features 002, 004, 005 and 006. It depends on the 88-note series from feature 001, the final gray levels (scaling, brightness, smoothing) and the octave grid layout.
- **Scope**: Only the color of the tiles changes. Analysis, window spacing, frame averaging, smoothing, the brightness setting, the layout and the form are unchanged.
