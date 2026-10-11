# Feature Specification: Image Type (Blended Tiles)

**Feature Branch**: `013-image-type-blended-tiles` (no git branch created; spec directory name only)

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "create a way to specify which type of image we create from the music.  The existing tile image is the default.  Make another image that creates a variation of the tiled image, but for each frame it finds a gradient by creating an alpha-blend at the edge of the tiles.  This part would operate on the actual colors, not just the data, in the sense that the rows/columns of the tiles will matter not just the note they represent."

## Clarifications

### Session 2026-10-10

- Q: Should the width of the blend band be fixed or a setting? → A: A setting, the **blend width**, from **10% to 25% of the tile width**. It is the distance on each side of an edge over which the colors fade (so 10% is about 2 pixels and 25% about 5 pixels of the 21-pixel tile width, each side), the same distance in pixels for every edge. The other assumptions of this spec (finished colors and grid, linear mix, corners, flat outer border, black tiles, true-color pictures, the two named types) were confirmed.
- Q: What blend width should the page start at, and a request that sends none use? → A: **25%** (option A), the widest fade.
- Q (after the first implementation, 2026-10-10): The picture looks too blurry; can the fade be a Gaussian blur inside a feather mask of about 10 × 10 pixels? → A: Yes. The fade is now a **Gaussian feather** instead of a straight-line ramp: a Gaussian blur of the sharp edge, cut off at the blend width on each side of the edge and renormalised, with a standard deviation of a quarter of the blend width. At the default 25% the feather mask is about 10 pixels across (5.25 pixels each side), so the middle of the fade is sharper and only the tails are soft. The blend width keeps its meaning (the reach of the feather) and its range.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get frames whose tiles blend into each other (Priority: P1)

Today every frame is a grid of 12 × 7 flat-colored tiles with hard edges. The user wants another kind of picture made from the same music: the same grid and the same tile colors, but where neighboring tiles meet, the colors **fade into each other** instead of stopping abruptly. The fade is an alpha-blend across each shared edge: moving from the middle of one tile toward the next, the color changes smoothly from the first tile's color to the second tile's color, in the shape of a Gaussian blur of the edge that is kept inside a narrow feather around it, so that the tiles stay crisp and only their edges are softened. How far from the edge the fade reaches is the **blend width**, which the user can set (Story 2).

The blending works on the **finished colors** of the tiles, the ones that would be drawn in the ordinary picture (after smoothing, the level steps, the threshold and the frame brightness), and on **where the tiles are in the grid**, not on which notes they stand for. A tile is blended with the tiles directly beside it, above it and below it in the picture, and at a corner with the tile diagonally opposite as well. Two notes that are far apart in pitch but side by side in the grid blend with each other, and two neighboring notes that are in different rows (the last note of one octave and the first of the next) do not, because they are not side by side in the picture.

Which kind of picture is made is chosen by name. The existing picture is called **tiles** and is the default; the new one is called **blended tiles**.

**Why this priority**: This is the whole feature: a second kind of image and the way to choose it. The page control (Story 2) and the combination with the other settings (Story 3) build on it.

**Independent Test**: Make frames from one file twice, once as tiles and once as blended tiles. The two sets have the same size and number of frames. In the blended set, the middle of every tile has exactly the tile's color, and across the edge between two tiles of different colors the color changes step by step from one to the other, passing through an even mix of the two at the edge itself (the average of the pixels on either side of it). Where two neighboring tiles have the same color, the blended frame looks the same as the tiles frame there.

**Acceptance Scenarios**:

1. **Given** no image type is chosen, **When** frames are created, **Then** they are the tiles pictures, identical to those made before this feature.
2. **Given** the image type **tiles**, **When** frames are created, **Then** they are identical to those made with no image type.
3. **Given** the image type **blended tiles**, **When** a frame is drawn, **Then** it has the same size (252 × 168 pixels) and the same grid of 12 × 7 tiles, and the number of frames and their timing are the same as for tiles.
4. **Given** the image type **blended tiles**, **When** a frame is drawn, **Then** the pixels in the inner part of each tile, away from its edges, have exactly the tile's color.
5. **Given** two tiles side by side (or one above the other) with different colors, **When** the blended frame is drawn, **Then** across the band around their shared edge the color changes from the first tile's color to the second's in the shape of a Gaussian blur of the edge (steep in the middle, soft at both ends), with an even 50/50 mix at the edge itself (the point between the two pixels beside it, so the average of those two pixels), and every color in the band lies between the two (no new hue appears that neither tile has, no pixel darker or brighter than both).
6. **Given** a blend width *b* (from 10% to 25% of the tile width, which is 2.1 to 5.25 pixels), **When** a blended frame is drawn, **Then** the fade reaches a distance *b* on each side of every edge, the same distance in pixels for edges between tiles side by side and for edges between a tile and the one below it; pixels farther than *b* from every edge have exactly their tile's color; and a larger *b* never makes the fade narrower.
7. **Given** a tile whose neighbors have the same color as itself, **When** the blended frame is drawn, **Then** that tile and the area around it are exactly as in the tiles picture.
8. **Given** a point where four tiles meet, **When** the blended frame is drawn, **Then** its color is the mix of the four tiles' colors, each weighted by how close the point is to that tile in both directions (an even 25% each at the exact corner, which is the average of the four pixels around it).
9. **Given** the tiles on the outer border of the picture, **When** the blended frame is drawn, **Then** their outer edges are not blended with anything: the picture does not fade to black or to any color at its border.
10. **Given** a tile that is black (an unlit tile in a dark frame, or a note hidden by the threshold) next to a colored tile, **When** the blended frame is drawn, **Then** the two blend like any other pair, so the colored tile fades toward black at that edge.
11. **Given** a frame in which every tile is the same color (or entirely black), **When** it is drawn as blended tiles, **Then** it is identical to the tiles picture.
12. **Given** the same file and settings, **When** frames are created twice, **Then** the two sets are identical.

---

### User Story 2 - Choose the image type on the page and see what was used (Priority: P2)

The settings column gets an **Image type** control with the two named choices, **Tiles** (the starting choice) and **Blended tiles**. It has an info button with a short explanation, is disabled while a job is running like the other settings, and the result summary shows the image type that was used. Next to it is a **Blend width** slider from **10% to 25%** of a tile, in steps of 1 percentage point, with a readout (for example "25% of a tile") and its own info button; it only has an effect for Blended tiles, so it is disabled while Tiles is chosen. The result summary also shows the blend width when Blended tiles was used. The frame player shows either kind of picture exactly as it shows the tiles pictures today.

**Why this priority**: The new picture (Story 1) can be asked for through the interface of the server, but users need to pick it on the page, with the other settings.

**Independent Test**: Open the page, choose Blended tiles, create frames, see the blended pictures play, and confirm the result summary says "Blended tiles". Move the Blend width slider and create frames again: the fades are narrower or wider. Choose Tiles and create frames again: the pictures are the flat-tile ones and the Blend width slider is disabled.

**Acceptance Scenarios**:

1. **Given** the page is opened, **When** the settings are shown, **Then** there is an Image type control offering exactly Tiles and Blended tiles, and Tiles is selected.
2. **Given** the user activates the info button, **When** the popover opens, **Then** it explains in a few words what each type looks like.
3. **Given** a job is running, **When** the user looks at the control, **Then** it is disabled like the other settings.
4. **Given** frames have been created, **When** the result is shown, **Then** the result summary includes the image type that was used (and the blend width when it was Blended tiles), and the frames play in the existing frame player.
5. **Given** the page is opened, **When** the settings are shown, **Then** the Blend width slider ranges from 10 to 25 in steps of 1, shows its value as a percentage of a tile, is disabled while Tiles is chosen and while a job is running, and has an info button that explains that it is how far the fade reaches on each side of an edge.
6. **Given** a request that bypasses the page with a blend width that is not a number from 10 to 25 (below 10, above 25, empty, text), **When** the server receives it, **Then** it is refused with a clear message that states the range; a request that does not send a blend width uses the default. A blend width sent together with the image type tiles is accepted and has no effect on the pictures.
7. **Given** a request that bypasses the page with an image type that is not one of the offered names (empty, unknown, different capitalization of a name that is not accepted), **When** the server receives it, **Then** it is refused with a clear message that lists the allowed choices. A request that does not send an image type at all uses tiles.

---

### User Story 3 - The new picture works with every other setting and stays practical (Priority: P3)

The image type decides only how the finished tile colors are turned into pixels. Everything that decides those colors works as before for both types (the blend width only shapes the fades of the blended type): the note analysis, the window and frame settings, the smoothing and its window, the Saturation and Brightness roots, the level steps (Hue, Saturation and Brightness steps) and the Threshold. Because the blend is made from the finished colors, the level steps and the threshold decide the colors that are blended; the blended picture then shows in-between colors at the edges, which is intended. A blended frame is a full-color picture rather than a picture of at most 84 flat colors, so its files are larger and take somewhat longer to create, but the job still finishes in a practical time.

**Why this priority**: These are the interactions with the existing settings and the practical limits. They define the result when features are combined but are secondary to the picture itself.

**Independent Test**: Create blended frames with Saturation steps 20, a Threshold of 5 and smoothing 0.5 with a window of 3. Every tile's middle has one of the allowed saturation levels, hidden tiles' middles are black, and the edges between them show the blends. Creating the same frames as tiles gives the same tile colors in the middles.

**Acceptance Scenarios**:

1. **Given** any combination of the other settings, **When** frames are created as blended tiles, **Then** the middle of every tile has exactly the color that the tiles picture has for it with the same settings.
2. **Given** the level steps or the threshold, **When** blended frames are drawn, **Then** they are applied to the tiles' colors as before, before the blend; the blend itself is not rounded to the levels.
3. **Given** a long file, **When** frames are created as blended tiles, **Then** creating them takes no more than about twice as long as the tiles pictures and the job is not refused for this reason.
4. **Given** blended frames, **When** they are served, **Then** they are PNG pictures of the same size as the tiles pictures, are cached and identified the same way, and are identical on every request.

---

### Edge Cases

- **Gradients cannot cross the picture's border.** The outer edges of the border tiles stay flat up to the border of the picture.
- **A tile next to a tile of the same color** shows no visible gradient between them.
- **The widest fade never reaches across a tile**: at 25% the fades from two opposite edges of a tile together cover half of its width, so a flat middle always remains.
- **Tiles in different rows are neighbors only vertically.** The end of one row and the start of the next are not side by side in the picture (they are at opposite sides of it), so they do not blend; blending follows the picture's grid, not the order of the notes.
- **The four highest notes (84 to 87)**, which are not drawn, do not take part in the blending; only the 84 drawn tiles do.
- **Silent file**: every frame is black as a tiles picture and as a blended one.
- **Results from before this feature** (frames already created) are not changed. Only new submissions can use the new type.
- **Future image types**: the choice is by name, so more types can be offered later without changing how the choice is made. Only the two named here are offered now.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to choose the **image type** of the frames. The choices are **tiles** (the existing picture) and **blended tiles** (the new one). **Tiles** MUST be the default, both on the page and when a request does not say.
- **FR-002**: With the image type tiles (chosen or by default), frames MUST be identical, pixel for pixel and file for file, to those made before this feature.
- **FR-003**: With the image type blended tiles, each frame MUST have the same size (252 × 168 pixels), the same 12 × 7 grid of tiles of 21 × 24 pixels, the same frame count and the same timing as the tiles picture made with the same settings.
- **FR-004**: The colors of the tiles that are blended MUST be the finished colors of the tiles picture for the same frame and settings (after smoothing, the roots, the level steps, the threshold, the hue and the frame brightness), including black for tiles that are unlit or hidden.
- **FR-005**: The blend MUST depend only on the finished colors and on the position of the tiles in the grid. It MUST NOT depend on which notes the tiles stand for or on how loud they are, except through their colors.
- **FR-006**: Around every edge that two drawn tiles share, there MUST be a band that reaches the **blend width** on each side of the edge, in which the color changes from the first tile's color to the second's in the shape of a Gaussian blur of the sharp edge (a Gaussian feather: its standard deviation is a quarter of the blend width, and it is cut off at the blend width and renormalised, so the fade ends exactly at the blend width), with the even 50/50 mix at the edge itself (halfway between the two pixels beside it). The blend width is a distance measured in pixels from the pixel's center to the edge, equal to the chosen percentage of the tile width (21 pixels), and it is the same for edges between tiles side by side and for edges between a tile and the one below it. The weights of the two colors MUST add up to 1 at every pixel.
- **FR-007**: Where four tiles meet, a pixel's color MUST be the weighted mix of the four tiles' colors, with each tile's weight the product of its horizontal and its vertical weight (so the weights add up to 1 and the exact corner is an even 25% each).
- **FR-008**: Pixels outside every band MUST have exactly the color of their tile. The outer edges of the picture MUST NOT be blended: a tile on the border keeps its color up to the border.
- **FR-009**: Every blended pixel MUST lie within the range of the colors that are mixed into it, channel by channel (a mix of colors never goes outside what its parts have).
- **FR-010**: The page MUST show an Image type control with the two choices, the name Tiles selected at the start, an info button with a short explanation, and a disabled state while a job is running. The result summary MUST show the image type that was used.
- **FR-011**: The server MUST refuse an image type that is not one of the offered names, including an empty one, with a clear message that lists the allowed choices, and MUST use tiles when no image type is sent. The response to a job MUST include the image type that was used.
- **FR-012**: The image type MUST NOT change anything that decides the tile colors or the timing: the note analysis, the window and frame settings, the smoothing, the roots, the level steps and the threshold work the same for both types.
- **FR-013**: The same file and settings MUST always give identical frames.
- **FR-014**: The documentation's description of the image and settings MUST be updated to describe the image type, the blend width and the blended tiles picture.
- **FR-015**: Users MUST be able to set the **blend width** from **10% to 25%** of the tile width, in steps of 1 percentage point on the page, with a default of 25%. It MUST affect only the blended tiles picture; the tiles picture MUST be the same for every blend width. On the page it MUST be disabled while a job is running and while Tiles is chosen, and have an info button and a readout of its value.
- **FR-016**: The server MUST refuse a blend width that is not a number from 10 to 25 (below 10, above 25, empty when sent, text, not a number) with a clear message that states the range, and MUST use the default when none is sent. The response to a job and the result summary (for blended tiles) MUST include the blend width that was used.

### Key Entities *(include if feature involves data)*

- **Image type**: The kind of picture made from a frame's tile colors: **tiles** (flat tiles, the default) or **blended tiles**. It is chosen by name for each job.
- **Tile colors**: The 84 finished colors of a frame (one per drawn tile, placed in a grid of 12 columns and 7 rows) from which either kind of picture is made.
- **Blend band**: The strip on both sides of an edge between two tiles in which the colors fade from one tile's color to the other's.
- **Blend width**: A number from 10 to 25 chosen by the user: the percentage of the tile width (21 pixels) that the fade reaches on each side of an edge. It applies to the blended tiles picture only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With no image type, and with the image type tiles, 100% of the frames of a test file are identical, file for file, to those made before this feature.
- **SC-002**: In a blended frame, 100% of the pixels in the inner part of every tile (outside all bands) have exactly the tile's color, and at the edge between two tiles of different colors the average of the two pixels on either side of the edge is the even mix of the two colors to within 1 of 255 in every channel.
- **SC-003**: Across any edge between two tiles of different colors, the color changes monotonically in every channel from one tile's value to the other's (no overshoot) over the whole band.
- **SC-004**: A frame in which all tiles have one color, and a frame that is entirely black, are identical in both image types.
- **SC-005**: For every blended frame of a test file, the middle of every tile has exactly the color of the same tile in the tiles frame made with the same settings, for a representative set of the other settings (smoothing and window, the roots, all three level steps, the threshold).
- **SC-006**: Blended frames have the same size and count as tiles frames, and creating them takes no more than twice as long as creating the tiles frames for the same file.
- **SC-007**: 100% of invalid image types (empty, unknown names) are refused before a job is created, with a message that lists the allowed choices.
- **SC-008**: A user can find and read the explanation of the image type from its info button, and switch between the two types and see the difference in the player, without leaving the settings column.
- **SC-009**: For every blend width from 10 to 25, every pixel farther than the blend width from all edges has exactly its tile's color, and the number of pixels whose color differs from their tile's color never decreases as the blend width grows.
- **SC-010**: 100% of invalid blend widths (below 10, above 25, empty, text) are refused before a job is created, with a message that states the allowed range, and the tiles picture is identical for every blend width.

## Assumptions

- **The blend uses the finished colors of the tiles and the tile grid.** The request says it "operates on the actual colors ... the rows/columns of the tiles will matter". This is read as: the colors to blend are those of the ordinary picture, and the neighbors are the tiles that touch in the 12 × 7 grid. The note order is not used; the end of one row and the start of the next do not touch.
- **The gradient is limited to a band around each edge**, not stretched across whole tiles, as the request says "at the edge of the tiles", so the middle of each tile keeps its flat color. How wide the band is was settled by the user (2026-10-10): a **blend width** setting from 10% to 25% of the tile width.
- **The blend width is the reach on each side of an edge.** At 10% the fade reaches 2.1 pixels either side, at 25% it reaches 5.25 pixels either side (a total band of 4.2 to 10.5 pixels). It is measured from the pixel's center, so every percentage gives a slightly different fade, not only whole-pixel widths. The same distance in pixels is used for edges between tiles side by side and for edges between a tile and the one below it, so the fade looks equally wide in both directions even though the tiles are 21 × 24 pixels.
- **The default blend width is 25%** (confirmed), the widest, which is the fade this spec first described (a quarter of a tile on each side) and makes the effect easy to see. The page starts at 25% and a request that does not send a blend width uses 25%.
- **The blend width is shown and sent even for Tiles**, where it has no effect: the response always reports the value used, and the page just disables the slider when Tiles is chosen.
- **The colors are mixed as a plain weighted average of the 8-bit red, green and blue values** (an alpha-blend), not in a perceptual color space, which keeps results easy to check by hand. How the weights change with the distance from the edge follows a Gaussian feather (changed from a straight ramp on 2026-10-10, see Clarifications).
- **Corners blend in both directions at once**: the weights of the four tiles are the products of the horizontal and the vertical weights.
- **The outer border is not blended**, because there is no neighboring tile there; fading to black or to white at the border would add a color that is not in the picture.
- **Black tiles are tiles like any other**: an unlit or hidden tile next to a colored one fades with it, which makes colored tiles look softer next to dark areas.
- **Blended pictures are true-color images.** They contain many more than 84 colors, so they cannot use the compact palette format of the tiles pictures; their files are larger and they take longer to create, within the limit in SC-006.
- **The names offered now are only two**, written "Tiles" and "Blended tiles" on the page and `tiles` and `blended` in the request (exact lowercase). The mechanism is a choice by name so that more types can be added later. The blend width is sent as its own request field.
- **The image type is chosen when frames are created**, like every other setting; changing it means submitting again.
- This feature is about how frames are drawn. Audio playback, the note analysis, the frame player and the page layout (apart from adding two controls and summary items) are unchanged.
