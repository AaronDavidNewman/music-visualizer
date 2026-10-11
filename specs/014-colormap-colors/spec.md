# Feature Specification: Colormap Colors

**Feature Branch**: `014-colormap-colors` (no git branch created; spec directory name only)

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description: "I don't like the way the colors are being calculated, the animation is very 'blinky'.   The colors need to be set up in a colormap that makes more sense sequentially.  Allow the user to pick a named colormap from imgplotlib, rather than set values for HSV.  This will remove the configured values other than smoothing and threshold."

## Clarifications

### Session 2026-10-11

- Q: Which library is meant by "imgplotlib"? → A: matplotlib, confirmed.
- Q: Is it right that the colormap is applied to each tile's own note strength? → A: Yes, the mapping is fine as specified. The tiles are really a test setting, and more interesting functions (other ways of turning the music into a picture) are expected later; this spec only defines this one.
- Q: Which colormaps should be offered? → A: Only four of matplotlib's: **summer**, **autumn**, **hot** and **cool**. No others are offered or accepted.
- Q: Which colormap should the page start at, and a request that sends none use? → A: **hot** (option A).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Colors that follow one steady colormap (Priority: P1)

Today a tile's color is made from several moving parts at once: its hue is pushed around by the strength of other, related notes, its saturation follows its own note, and the brightness of the **whole picture** follows the overall loudness of that frame. A note that stays equally strong can still change color from one frame to the next because something else changed, and the whole picture dims and brightens with the sound. The animation looks "blinky".

The user wants the colors to come from a **colormap**: an ordered scale of colors. Each tile's color is simply the color at one position on the scale, and the position depends on **how strong that tile's own note is**. A silent note sits at the start of the scale, the strongest note of the file at the end, and everything in between is in between, in order. A colormap is chosen by name from a short list of matplotlib's named colormaps: `summer`, `autumn`, `hot` and `cool`, with `hot` as the default. The same strength gives the same color in every frame, whatever the other notes are doing, and the picture is no longer dimmed or brightened as a whole.

**Why this priority**: This is the whole feature: a steady, ordered way to color the tiles and the choice of the scale. The page and the removal of the old settings (Story 2) and the combination with smoothing, threshold and image types (Story 3) build on it.

**Independent Test**: Make frames from a file with a steady tone. Choose `hot`. The tone's tile has the same color in every frame in which the tone sounds. Change a different note in the file: the tone's tile does not change color. Make the tone louder in a part of the file: its tile moves along the colormap toward the far end of the scale, never backwards. Choose another colormap: the tile colors are those of the other scale and nothing else changes.

**Acceptance Scenarios**:

1. **Given** a colormap is chosen, **When** frames are created, **Then** every tile's color is the color of that colormap at a position that depends only on the strength of that tile's own note in that frame and on the largest note strength in the file.
2. **Given** a note whose strength is the same in two frames, **When** the frames are drawn, **Then** its tile has exactly the same color in both, whatever the other notes and the overall loudness of the two frames are.
3. **Given** two notes of different strength in the same or in different frames, **When** they are drawn, **Then** the stronger one is at a later position on the colormap (or at the same position if the strengths are equal) and never at an earlier one.
4. **Given** the strongest note value of the whole file, **When** it is drawn, **Then** its tile has the last color of the colormap, and a note with no strength has the first color of the colormap.
5. **Given** a colormap other than the default, **When** frames are created, **Then** the same notes in the same frames have the colors of that colormap at the same positions as they would with the default, and nothing else about the frames changes.
6. **Given** no colormap is chosen, **When** frames are created, **Then** `hot` is used.
7. **Given** a steady tone that sounds for several frames, **When** frames are created, **Then** the tone's tile does not change color from one frame to the next while it sounds (it may change at the start and the end of the tone).
8. **Given** the same file and settings, **When** frames are created twice, **Then** the two sets are identical.

---

### User Story 2 - Choose the colormap on the page, and a simpler list of settings (Priority: P2)

The settings column gets a **Colormap** control that offers the four colormaps (summer, autumn, hot and cool) by name and starts at `hot`, with an info button with a short explanation. Choosing a colormap replaces the color settings that were set by hand. These settings are **removed** from the page and from what the server uses: **Brightness** (the root on the frame's loudness), **Saturation** (the root on each note's strength), **Hue steps**, **Saturation steps** and **Brightness steps**. The settings that remain are the ones that are not about color values: window size, frame rate, window spacing, **Smoothing** and **Smoothing window**, **Threshold**, **Image type** and **Blend width**, plus the new Colormap. The result summary shows the colormap that was used and no longer lists the removed settings.

**Why this priority**: Choosing the scale (Story 1) can be asked for through the server, but users need to pick it on the page, and the page must no longer offer controls that do nothing.

**Independent Test**: Open the page: there is a Colormap control (hot), and none of Brightness, Saturation, Hue steps, Saturation steps, Brightness steps. Choose `autumn`, create frames, and see the autumn colors and "Colormap: autumn" in the summary.

**Acceptance Scenarios**:

1. **Given** the page is opened, **When** the settings are shown, **Then** there is a Colormap control that offers exactly summer, autumn, hot and cool, starts at `hot`, and has an info button with a short explanation, and the removed settings (Brightness, Saturation, Hue steps, Saturation steps, Brightness steps) are not shown.
2. **Given** a job is running, **When** the user looks at the Colormap control, **Then** it is disabled like the other settings.
3. **Given** frames have been created, **When** the result is shown, **Then** the result summary includes the colormap that was used, does not list the removed settings, and the frames play in the existing frame player.
4. **Given** a request that bypasses the page with a colormap name that is not one of the available names (empty, unknown, different capitalization), **When** the server receives it, **Then** it is refused with a clear message that says the name is not an available colormap and lists the four valid names. A request that does not send a colormap uses `hot`. Other matplotlib colormap names (such as `viridis`) are refused too.
5. **Given** a request that still sends one of the removed settings, **When** the server receives it, **Then** the request is accepted, the value has no effect on the frames, and the response does not report it.
6. **Given** the colormaps offered on the page, **When** each is chosen, **Then** the server accepts it (the page offers exactly the names the server accepts).

---

### User Story 3 - It works with smoothing, the threshold and both image types (Priority: P3)

Smoothing and its window, the Threshold and the Image type (with the Blend width) work as before, and they now act on a simpler picture. Smoothing smooths each note's strength before it is turned into a color, so a colormap position glides rather than jumps. The Threshold hides a note whose smoothed strength is below the chosen share of the loudest note: its tile is plain black (not the colormap's first color), so hidden notes stand out from quiet ones. The blended tiles picture blends the colormap colors of neighboring tiles, and the tiles picture is made of flat tiles of those colors.

**Why this priority**: These are the interactions with the settings that remain. They define the result when features are combined but are secondary to the colormap itself.

**Independent Test**: Create frames with smoothing 0.5 and window 3, a Threshold of 5 and Blended tiles with the `cool` colormap. Tiles whose note is below the threshold are black in the middle, the others have plasma colors in the middle, and the edges show the fades; the same frames as Tiles have the same tile middles.

**Acceptance Scenarios**:

1. **Given** smoothing above 0, **When** frames are drawn, **Then** the position on the colormap is worked out from the smoothed strength, so the color of a tile moves gradually while the note fades or rises.
2. **Given** a Threshold above 0, **When** a note's smoothed strength is below the threshold (a share of the loudest note value in the file), **Then** its tile is black (red, green, blue all 0) whatever the colormap is; a note at or above the threshold has its colormap color.
3. **Given** the image type Blended tiles, **When** frames are drawn, **Then** the middle of every tile has the color that the Tiles picture has for it, and the fades blend the colormap colors (and black, for hidden tiles) of neighboring tiles as before.
4. **Given** a silent file, **When** frames are drawn, **Then** every tile has the colormap's first color, also with a Threshold above 0 (no note is below a share of the zero largest value, so nothing is hidden), and nothing fails.
5. **Given** any colormap, **When** frames are drawn, **Then** the layout, size, frame count and timing of the frames and the note analysis are as before.

---

### Edge Cases

- **Only the four colormaps are offered.** Any other name, including other matplotlib names, reversed names such as `hot_r`, and names of the wrong capitalization, is refused. Adding more names later changes the list and nothing else.
- **The mapping is one function among several expected later.** How a frame's notes are turned into a picture (here: note strength onto a colormap) is meant to be replaceable by other functions in the future; this spec defines only this one, and the Image type choice (Tiles, Blended tiles) is separate from it.
- **A note with the same strength as another** always has the same color as it, in any frame.
- **The loudest value of the file is set by one loud note** (as with the gray levels today), so the rest of the file sits lower on the scale. This is the same behavior as before and the threshold and the choice of colormap do not change it.
- **Quiet moments**: a quiet part of the file is no longer dimmed as a whole; its tiles simply sit low on the colormap.
- **The four highest notes (84 to 87)**, which are not drawn, still count when the file's loudest value is found, as before.
- **Silent file**: see Story 3, scenario 4.
- **Results from before this feature** (frames already created) are not changed. Only new submissions use colormaps.
- **The removed settings** no longer exist in any form that changes a picture; the harmonic hue (hues moved by related notes), the per-frame brightness from the overall loudness, and the discrete level steps are retired.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to choose a **colormap** by name from exactly four of matplotlib's named colormaps: `summer`, `autumn`, `hot` and `cool`. The default MUST be `hot`, on the page and when a request does not say. The colors of each MUST be those of the matplotlib colormap of that name.
- **FR-002**: Every drawn tile's color MUST be the color of the chosen colormap at a position from 0 to 1 that is worked out from that tile's own note strength only: the note's value in the frame (after smoothing) as a share of the largest note value anywhere in the file (after smoothing), on a fixed square-root scale. The color MUST NOT depend on any other note, on the overall loudness of the frame, or on the frame's number.
- **FR-003**: A note with no strength MUST have the colormap's first color and the note with the file's largest value MUST have its last color. A stronger note MUST never have an earlier position than a weaker one.
- **FR-004**: The whole picture MUST NOT be dimmed or brightened by the loudness of the frame, and the hue MUST NOT be moved by related notes.
- **FR-005**: The Threshold MUST work as before and be applied on the smoothed strength before the scale: a note below the threshold MUST have a black tile (red, green and blue all 0), whatever the colormap is, and a note at or above it MUST have its colormap color.
- **FR-006**: The settings Brightness, Saturation, Hue steps, Saturation steps and Brightness steps MUST be removed from the page. The server MUST accept a request that still sends them and MUST ignore them, and MUST NOT report them in its response. The settings that remain are window size, frame rate, window spacing, smoothing, smoothing window, threshold, image type, blend width and the new colormap.
- **FR-007**: Smoothing and the smoothing window MUST be applied to each note's strength before it is turned into a color, as they are applied to the note values today. Image type and Blend width MUST work as before, on the finished tile colors.
- **FR-008**: The page MUST show a Colormap control that offers exactly the four names the server accepts, starts at `hot`, has an info button with a short explanation and is disabled while a job is running. The result summary MUST show the colormap that was used.
- **FR-009**: The server MUST refuse a colormap name that is not one of the available names (including an empty one and a name of the wrong capitalization) with a clear message that says it is not an available colormap and lists the four valid names, MUST use `hot` when none is sent, and MUST include the colormap used in its response.
- **FR-010**: The same file and settings MUST always give identical frames.
- **FR-011**: Nothing else about the frames MUST change: the layout, size, frame count and timing, the note analysis and the image format.
- **FR-012**: The documentation's description of the image and settings MUST be updated: the colormap, the settings that were removed, and the replaced color rules.

### Key Entities *(include if feature involves data)*

- **Colormap**: A named, ordered scale of colors (from matplotlib) used to turn a number from 0 to 1 into a color. Chosen by name for each job.
- **Note strength**: A note's value in a frame after smoothing, as a share of the largest note value in the file, mapped onto the colormap on a square-root scale.
- **Tile color**: The color of one of the 84 drawn tiles in one frame: the colormap's color at the tile's note strength, or black when the threshold hides the note.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a test file, two tiles whose notes have the same strength in two different frames have exactly the same color in both, in 100% of the cases tried, and changing every other note of a frame changes no tile whose own note was left alone.
- **SC-002**: For every colormap offered, the strongest note of a test file has exactly the colormap's last color, a silent note has exactly its first color, and the position of the colors never decreases as the strength grows (checked over a full range of strengths).
- **SC-003**: For a file with a steady tone, the tone's tile changes by no more than 2 levels in any color channel from one frame to the next while the tone sounds (a measure of "not blinky").
- **SC-004**: The page offers no Brightness, Saturation, Hue steps, Saturation steps or Brightness steps control, and a request that sends them gives exactly the same frames as one that does not.
- **SC-005**: 100% of unknown colormap names (empty, unknown, wrong capitalization) are refused before a job is created, with a message that lists the four valid names; 100% of the names the page offers are accepted by the server.
- **SC-006**: With the Threshold above 0, every tile whose note is below the threshold is exactly black and every other tile has its colormap color, for every colormap offered.
- **SC-007**: With Tiles and with Blended tiles, the middle of every tile has the same color in the two pictures, for several colormaps and combinations of smoothing and threshold.
- **SC-008**: Creating the same frames takes no longer than before this feature for the tiles picture (the color work is simpler than before).
- **SC-009**: A user can find and read the explanation of the colormap from its info button, and change the colormap and see the difference in the player, without leaving the settings column.

## Assumptions

- **The library is matplotlib** (confirmed): its named colormaps are used with the names and colors they have there (`summer`, `autumn`, `hot`, `cool`).
- **What is mapped onto the colormap is the strength of the note's own tile** (confirmed). The request asks for colors that "make more sense sequentially" and a choice of colormap, which in matplotlib maps one number to one color. The number chosen is the tile's own note strength (how strongly that note sounds), so a tile gets a color that is "further along the scale" the stronger its note is, and the picture reads like a spectrogram heat map. The user confirmed this mapping and described the tiles as a test setting; other mapping functions are expected later and are not part of this spec.
- **The scale is the square root of the strength share** (confirmed with the mapping), as the removed Saturation setting (default: the second root) used to lift quiet notes. It is fixed, not a setting, so that the picture keeps the contrast it has today. The strength share is the note's smoothed value divided by the largest smoothed value in the whole file (all 88 notes count, as today).
- **The default colormap is `hot`**: the most familiar heat-map scale (dark for quiet, through red and yellow, to white for the loudest). This was chosen by the user (confirmed), knowing that `hot` starts at a very dark red, almost black (matplotlib's first entry of `hot` is (10, 0, 0)), so a quiet note and a note hidden by the Threshold look alike; the other three colormaps start at a color, so hidden notes stay distinct.
- **Only four colormaps are offered** (confirmed): `summer`, `autumn`, `hot` and `cool`. The page lists them by name; the server accepts the same four names and no others, in exactly matplotlib's lowercase spelling (case-sensitive).
- **Settings kept**: window size, frame rate, window spacing, smoothing, smoothing window, threshold, image type and blend width. Of the request's wording "the configured values other than smoothing and threshold", only the settings that were about color values are removed (Brightness, Saturation, Hue steps, Saturation steps, Brightness steps); the others are not about color and are kept, and the smoothing window is part of Smoothing.
- **Old values in a request are ignored, not refused**, so that a client that still sends them keeps working. They are not echoed in the response.
- **The Threshold's hidden tiles stay black**, as specified before, rather than taking the colormap's first color, so that a hidden note can be told apart from a quiet one.
- **A silent file has uniformly the colormap's first color** (not black), because "no strength" is the first position of the scale; a Threshold above 0 hides nothing in a silent file, because no note is below a share of the (zero) largest value.
- **The per-frame loudness (energy) of the audio is no longer used.** The measure and the harmonic hue rules are retired from the colors; the note analysis that gives each note's strength is unchanged.
- **Colors are 8-bit**: the colormap is sampled at 256 positions, as matplotlib does by default, so the strength is rounded to the nearest of 256 steps before it is turned into a color.
- **The image type, the blend width and the image format are unchanged**: tiles pictures are palette PNGs and blended pictures are true-color PNGs, made from the finished tile colors.
- This feature is about how tile colors are worked out and chosen. Audio playback, the note analysis, the frame player and the page layout (apart from adding one control and one summary item and removing five controls) are unchanged.
