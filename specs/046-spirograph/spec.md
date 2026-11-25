# Feature Specification: Spirograph

**Feature Branch**: `046-spirograph` (no git branch created; spec directory name only)

**Created**: 2026-11-21

**Status**: Draft

**Input**: User description: "create a new image type called spirograph.  It will express the musical data using the classic pattern of a circle rotating in another circle.  We will track between 5-12 notes (bins) similar to other types.  We also keep a history of between 5-12 previous bins, we use this to keep a smooth flow to the images.  We actually keep history of both the bin values for each note, and the bin indices.   The outer loop is the bin history, and the inner loop is for each note we are tracking.  At each step i, j, we use the bin value and index history [i], and the actual bin value/index value[j].  Let val=the bin value, yval is val*12, and is used as an index into the color map. let bc=the current bin index/84 (so normalized to 1).  The plot for each graph is: X=val*(rc*cos(c1)+bc*yval*cos(c2)), and Y is the same except with sin.  C1 is a 1000-step from 0-2*pi, C2 is 1000 step from 0 to 14*pi.   The index into the colormap for each plot is the minimum of yval and the size of the bin indices.  For this image type, we use a reduced number of colors from the color map, index by the following:  (np.linspace(0, 1, (self.COLOR_BINS+1))**0.5)*256, where colorbins is a constant 12.  The background color should be black or transparent."

**The user's two answers** (asked while this document was written, 2026-11-21):

- **`rc` is a constant, 5** (superseded 2026-11-24: the user then made it 5 or 4 by the place in the local peak, see the second revision note). The formula leaves `rc` (the size of the big, fixed circle) undefined; the user said "rc is a constant, use 5".
- **Both the value and the index of a step come from history entry `i`.** The user wrote: `binindex = binIndexHistory[i]`, `binvals = binValueHistory[i]`, `bc = bin[j] / 84`, `val = binvals[j]`. So at step `(i, j)` the **history entry `i`** (one frame's list of tracked notes) gives both lists, and `j` picks the note inside them: the value is the `j`-th value of entry `i` and the index is the `j`-th index of entry `i`. Nothing at a step comes from the "current frame" except through the history entry that *is* the current frame (see Assumptions).

**How the user's words are read** (the terms used in the rest of this document):

- A **tracked note** (the user's "bin") is one of the loudest notes of a frame, with its **value** (how loud it is, 0 to 1) and its **index** (its place among the 84 drawn notes, 0 to 83). The number of tracked notes is **Number of notes**, 5 to 12.
- A **history entry** is the list of the tracked notes of one frame: their values and their indices. The picture of a frame uses the last **History length** entries (5 to 12), the newest being the frame itself.
- A **curve** is one spirograph line, drawn for one tracked note of one history entry (a step `(i, j)`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One spirograph curve for a note: a circle rolling inside a circle (Priority: P1)

The user wants another image type, **Spirograph** (request value `spirograph`), in which the music is drawn as the **classic spirograph pattern**: a small circle rolling round inside a big one, the pen tracing a closed, looping flower-like curve. Every tracked note of every history entry is one such curve, and the **note's loudness and place in the pitch range** decide how big and how wide the loops are and what color it has.

For the note at step `(i, j)`, with `val` its value (0 to 1), `letter` its index modulo 12 (the note name without the octave) and `yval = val x 12` (it picks the color) - and, since 2026-11-24, `pct` the place of the entry's frame in the local energy peak (1 at the top of a peak, 0 at the bottom):

- **Shape** (revised 2026-11-24, see the second revision note): the curve is the set of points `X = val x (rc x cos(c1) + loops x cos(c2))` and `Y = val x (rc x sin(c1) + loops x sin(c2))`, where **`loops = letter x val`**, **`rc` is 5 when `pct` is above 0.5 and 4 otherwise**, `c1` runs in **1000 equal steps from 0 to 2 pi** and `c2` runs in **1000 equal steps from 0 to 2 pi x `turns`**, **`turns = 2 x 7 x pct + 6`** (from 6 to 20; the two angles advance together, step by step, so the small circle turns `turns` times while the pen goes once round the big one). So a louder note is a bigger curve, and a note with a later letter has bigger loops on the rim of the big circle.
- **Color** (a reduced set of colors): the job's colormap is used, but only **13 of its colors**, at the positions `sqrt(k / 12) x 256` for `k = 0 to 12` (the user's `(linspace(0, 1, COLOR_BINS + 1) ** 0.5) x 256` with `COLOR_BINS` the constant 12; the position 256 is past the last color and takes the last color). The curve's color is the one at **place `min(yval, 12)`** in this set of 13 (`yval` rounded down to a whole number), so a quiet note takes a color from the dark end of the colormap and the loudest takes the last color, and the steps between the 13 colors are small at the quiet end and large at the loud end (the square root).
- **Background**: **black** (the pictures have no transparency; see Assumptions).

**Why this priority**: This is the picture's core: the curve, its color and its look. Without it there is no new image type.

**Independent Test**: Make a file in which one note sounds steadily and look at one frame's curves: they are closed loops that go seven times round, whose size grows with the note's loudness; two files with the same note at different loudness give curves of different size and color, and the curve of a high note has wider loops than the curve of a low note of the same loudness.

**Acceptance Scenarios**:

1. **Given** a note with value `val`, index `n` and place in the peak `pct`, **When** its curve is made, **Then** it has 1000 points, the point `k` being `X = val x (rc x cos(c1k) + (n mod 12) x val x cos(c2k))` and `Y` the same with sine, `c1k = 2 pi k / 999`, `c2k = 2 pi x turns x k / 999`, `turns = 14 pct + 6` and `rc` = 5 above `pct` 0.5, else 4.
2. **Given** a note with value 0 (a silent slot), **When** its curve is made, **Then** nothing is drawn for it (all its points lie at the center).
3. **Given** notes of value 1/12 x `m` for `m = 0 to 12`, **When** colored, **Then** the curve of value `m / 12` takes the color number `m` of the reduced set, and a value above 1 would take number 12 (the last).
4. **Given** the 13 colors of the reduced set, **When** they are looked at in order, **Then** color number `k` is the colormap's color at position `min(255, floor(sqrt(k / 12) x 256))`.
5. **Given** any frame, **When** the picture is made, **Then** the background is black.
6. **Given** the same file and settings, **When** it is made twice, **Then** the images are identical.

---

### User Story 2 - A history of notes that flows from frame to frame (Priority: P2)

A single note's curve is a still shape; the picture of a frame is built from **many curves, so that it flows**.

- **What is tracked**: in every frame the **loudest notes** are taken, as many as **Number of notes** (5 to 12), from the loudest to the quietest. For each, its **value** and its **index** are kept: the frame's **history entry** is the list of these values together with the list of these indices.
- **The history**: the picture of a frame uses the **last History length entries** (5 to 12): the frame's own entry (the newest) and the ones of the frames before it. In the first frames, where there are fewer entries than that, the entries that exist are used.
- **The loops**: the outer loop goes through the **history entries** (oldest first, so that the newest are drawn last, on top) and the inner loop goes through the **tracked notes** of the entry (loudest first). At step `(i, j)` the value is the `j`-th value of entry `i` and the index is the `j`-th index of entry `i` (the user's `binvals[j]` and `binindex[j]`), and one curve is drawn for it as in Story 1.
- **Smooth flow**: because each picture holds the last few frames' notes and every frame moves the window by one entry, **consecutive pictures share all but one of their entries**; the picture changes gradually rather than jumping from one frame to the next, and a note that sounded a moment ago is still seen as a curve of its own size and color.

**Why this priority**: The curves of Story 1 make a still picture; the history makes it a moving one that follows the music. It builds on Story 1 and does not change the curve.

**Independent Test**: Make a file in which the loudest note changes at frame 20. In the frames after 20 the old note's curves are still in the picture, for as many frames as the history length, and the new note's curve is there from frame 20; the picture of frame `t + 1` has the same curves as the picture of frame `t`, except that the oldest entry is gone and the new one is added.

**Acceptance Scenarios**:

1. **Given** Number of notes `n` and History length `h`, **When** a picture is made well into the file, **Then** it holds `n x h` curves, one for each step `(i, j)` with `i = 0 to h - 1` and `j = 0 to n - 1`.
2. **Given** frame `t` with `t < h - 1`, **When** its picture is made, **Then** it holds the entries of the frames `0 to t` only (`n x (t + 1)` curves) and nothing fails; frame 0 holds one entry.
3. **Given** the pictures of two consecutive frames, **When** they are compared, **Then** every history entry of the first except the oldest is also in the second, with the same values and indices.
4. **Given** a step `(i, j)`, **When** its curve is made, **Then** its value is the `j`-th value of entry `i`'s value list and its index the `j`-th index of entry `i`'s index list, **not** a value or index of any other entry.
5. **Given** the entries in a picture, **When** they are drawn, **Then** the oldest is drawn first and the newest last, and inside an entry the loudest note first.
6. **Given** a frame with fewer sounding notes than Number of notes, **When** its entry is made, **Then** the silent slots have value 0 and draw nothing (Story 1, scenario 2).
7. **Given** the same file and settings, **When** it is made twice, **Then** the images are identical.

---

### User Story 3 - Choosing it and the two settings that go with it (Priority: P3)

Spirograph is chosen from the image type setting, with the label **Spirograph**. It has three settings of its own (the third added 2026-11-22), each shown only when Spirograph is chosen:

| Setting | Meaning | Allowed | Default |
|---|---|---|---|
| **Number of notes** | how many of the loudest notes are tracked in each frame | a whole number from 5 to 12 | 8 |
| **History length** | how many frames' entries make up a picture | a whole number from 5 to 12 | 8 |
| **History fade** | the factor an entry's values are multiplied by for each frame it is older than the picture's own frame, so that the newest frame is the most prominent | a number from 0.4 to 0.85 | 0.7 |

A value that is not allowed is **refused with a message that says which setting and what is allowed, before the file is read and without leaving files behind**, as for the other image types. The **colormap**, the **analysis settings**, the **data smoothing** and **Extra notes** (feature 044: a note that was among the loudest keeps its place for a little longer, which makes the tracked notes steadier) apply as they do for the other types; the settings of the other image types (the threshold, the decay rate and amounts, the note layout, the local peaks and so on) are accepted and ignored. The frames have the usual size, count, names and timing, and can be made into a movie (feature 029). The other image types are exactly what they were before.

**Why this priority**: It is the frame around the picture, and it follows the pattern of the other types.

**Independent Test**: Choose Spirograph on the page: its two settings are shown with the defaults and the settings of other image types that do not apply are hidden; send each setting at, below and above its limits and check that only the allowed values are accepted and that a refusal leaves no files; make frames and a movie.

**Acceptance Scenarios**:

1. **Given** the image type setting, **When** the user opens it, **Then** Spirograph is among the choices and, when chosen, the page shows Number of notes and History length, each with its default.
2. **Given** a request with `image_type=spirograph` and a number of notes that is not a whole number from 5 to 12, **When** it is sent, **Then** it is refused with a message that says so, before the file is read and without leaving files behind.
3. **Given** a request with a history length that is not a whole number from 5 to 12 (including text, a fraction and not-a-number), **When** it is sent, **Then** it is refused in the same way.
4. **Given** a request without these two settings, **When** it is sent, **Then** the defaults apply.
5. **Given** the other image types, **When** frames are made, **Then** they are exactly what they were before this feature.
6. **Given** a request with `image_type=spirograph`, **When** frames are made and then a movie, **Then** both succeed as for the other types.

---

### Edge Cases

- **The first frames** (fewer entries than the history length): the entries that exist are drawn, so the first picture has one entry and the picture fills up over the first History length frames; nothing is drawn for entries that do not exist.
- **A frame with no sound at all**: its entry has only silent slots (value 0), draws nothing, and the picture holds the curves of the earlier entries that are still in the window; a file that is silent from the start gives black pictures. Nothing fails.
- **Fewer sounding notes than Number of notes**: the slots that are left are silent (value 0) and draw nothing.
- **Ties in loudness** are broken the same way in every run (the lower note first), so that the same file always gives the same picture.
- **A very loud note**: the value is 1 for the loudest note of the whole file, so the largest curve reaches `1 x (5 + 11)` = 16 units from the center (letter 11, `rc` 5); the picture is scaled so that this fits (see Assumptions), and a value above 1 does not occur.
- **A note whose letter is 0** (index 0, 12, 24, ...) has `loops = 0`: its curve is a plain circle of radius `rc x val` (the small circle's part vanishes); this is as the formula gives.
- **A file with no peaks** (nothing counts as a beat) has the beat 0 everywhere, so every frame is at the bottom (`pct` 0): 6 turns and `rc` 4. A job without a beat at all (the library with no `beat`) has every frame at the top: 20 turns and `rc` 5.
- **`turns` is not rounded**: the curve closes only when `turns` is a whole number; in between it stays open (the pen does not come back to its start), which is what the formula gives.
- **Colormaps in which the first colors are close to black** make the curves of quiet notes faint on the black background, as with the other types; no correction is made.
- **A held note that stays for many frames** is drawn once per history entry it is in, with the same values each time, so its curves lie exactly one over another and look like one curve; this is expected.
- Frame sizes other than the usual one scale the picture (the curves, between a quarter of the smallest side and the full size from the center; the line widths are fixed pixels, 3 for the newest entry and 2 down to 1) as for the other types.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST offer a new image type, **Spirograph** (`spirograph`), chosen the same way as the other types, producing one picture per frame on a **black** background (the pictures have no transparency; black is the background).
- **FR-002**: In each frame the system MUST take the **loudest notes**, as many as the **Number of notes** setting, from the loudest to the quietest, with ties broken the same way in every run, and keep for the frame a **history entry** made of the list of their **values** (0 to 1: the square root of the strength over the largest strength of the whole file, the loudest note of the file being 1) and the list of their **indices** (0 to 83, among the 84 drawn notes); slots without a sounding note MUST have value 0.
- **FR-003**: The picture of a frame MUST be made from the **last History length history entries**, the frame's own entry being the newest; in the first frames, the entries that exist MUST be used and nothing MUST fail. **(Revision 2026-11-22)** The values of an entry MUST be multiplied by `fade ** age`, `fade` being the History fade setting and `age` the number of frames the entry is older than the picture's frame (0 for its own entry, which keeps its values), before the curve, its size, its loops and its color number are made from them; the indices are not changed. A faded value above 0 still draws.
- **FR-004**: For each history entry `i` (oldest first) and each tracked note `j` of it (loudest first) the system MUST draw one curve whose value `val` is the `j`-th value of entry `i` and whose index is the `j`-th index of entry `i`; no value or index of another entry or frame MAY be used for it.
- **FR-005** (revised 2026-11-24): A curve MUST have 1000 points with `X = val x (rc x cos(c1) + loops x cos(c2))` and `Y = val x (rc x sin(c1) + loops x sin(c2))`, where `loops = (index mod 12) x val` (the letter of the note, not its octave), `rc` is **5** when the curve's entry's frame is closer to the top of the local energy peak than to the bottom (`pct` above 0.5) and **4** otherwise, `c1` is 1000 equal steps from 0 to 2 pi and `c2` is 1000 equal steps from 0 to 2 pi x `turns` (both inclusive), `turns = 2 x 7 x pct + 6` (from 6 to 20, not rounded).
- **FR-013** (added 2026-11-24): `pct` MUST be 1 at the top of the local energy peak and 0 at the bottom, **of the history entry's own frame** (so an entry keeps its turns and its `rc` in every picture it is in): one minus the distance of the frame from the peak of the beat of the file, stretched over the range of the beat as Chromatic Decay does for its target (the highest position of the file is 1, the bottom of the beat and every frame outside a peak is 0). Without a beat every frame MUST be 1. The size of a curve (FR-008) MUST use the `rc` of its frame.
- **FR-006**: A curve of value 0 MUST draw nothing.
- **FR-007**: The curve's color MUST come from a **reduced set of 13 colors** of the job's colormap: color number `k` (0 to 12) is the colormap's color at position `min(255, floor(sqrt(k / 12) x 256))`, and the curve MUST take color number `min(floor(yval), 12)`. The number of reduced colors, 12, MUST be a constant.
- **FR-008** (revised 2026-11-24, see the revision note): The curves MUST be centered in the picture and each one sized so that its farthest point is **between half of the full size and the full size** from the center: the smallest possible curve MUST be half of the smallest dimension of the picture across, and the curve with the largest extent of the whole file MUST fill the room (the full size: from the center to the nearer edge, less the margin and the widest line). The size of a curve between the two follows its extent compared with the file's largest, with the one scale of the whole file, so that the size does not depend on which other curves are in the picture and does not change from frame to frame for the same note.
- **FR-012** (added 2026-11-24): The line of a curve MUST be wider the newer its history entry: the picture's own frame **3 pixels** (a constant, whatever the History length), every older entry **at most 2**, falling in equal steps with the age from 2 (age 1) to **1 pixel** for the oldest place of the history (age History length - 1), each width rounded to a whole number of at least 1 (revised 2026-11-24: the line widths of the history never repeat the newest one's width, so a thick line does not cover the thin ones; revised again 2026-11-25: the user set the constant to 3, 5 was still too thick); the width follows the age only (not the History fade).
- **FR-009**: The system MUST offer the settings **Number of notes** (whole number 5 to 12, default 8), **History length** (whole number 5 to 12, default 8) and **History fade** (a number from 0.4 to 0.85, default 0.7), shown on the page only when Spirograph is chosen; a value that is not allowed MUST be refused with a message that says so, before the file is read and without leaving files behind. Since 2026-11-24 Spirograph also uses the existing **Minimum distance** setting of the Local peaks group (it decides the peaks of the beat), shown on the page for Spirograph as for Decay and the other beat types.
- **FR-010**: The colormap, the analysis settings, the data smoothing and Extra notes (feature 044) MUST apply as for the other types; the settings that belong to other image types MUST be accepted and ignored.
- **FR-011**: Results MUST be repeatable: the same file and settings MUST give identical images.
- **FR-012**: The frames of this type MUST be usable for making a movie (feature 029) as the frames of the other types are, and the other image types MUST be unchanged.

### Key Entities

- **Tracked note**: one of the loudest notes of a frame, with a value (0 to 1) and an index (0 to 83); silent slots have value 0.
- **History entry**: one frame's list of tracked-note values and list of tracked-note indices; the picture of a frame uses the last History length of them.
- **Curve**: the 1000-point spirograph line for one tracked note of one history entry, with a size set by its value, loop width set by its value and index, and a color set by its value.
- **Reduced color set**: the 13 colors of the colormap at the positions `sqrt(k / 12) x 256`.
- **Constants**: `RC` = 5 (4 in the lower half of the beat), 12 color bins, 1000 steps, 6 to 20 turns of the small circle (`2 x 7 x pct + 6`), 12 letters and 84 notes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every checked note (values from 0 to 1, indices from 0 to 83), the curve's 1000 points equal the formula's points to within a millionth, in 100 % of the checked cases.
- **SC-002**: The 13 reduced colors are the colormap's colors at the specified positions for every colormap offered, and every checked value `val` from 0 to 1 takes color number `min(floor(val x 12), 12)`, in 100 % of the checked cases.
- **SC-003**: Well into a file, every picture holds exactly Number of notes x History length curves (counting silent slots, which draw nothing), and in the first History length - 1 frames the entries that exist, in 100 % of the checked frames.
- **SC-004**: Of the entries of two consecutive frames' pictures, all but one are shared with the same indices and with values that differ by exactly one more factor of the History fade, in 100 % of the checked pairs.
- **SC-005**: Every value of the three settings outside its limits is refused before the file is read with a message that names the setting, and leaves no files behind, in 100 % of the checked cases; every value inside the limits is accepted.
- **SC-006**: Across the frames of the test files, the picture never has a curve outside it: no drawn point lies outside the picture, at the usual size and at another size.
- **SC-007**: Two runs on the same file and settings give identical images, and the pictures of the other image types are identical to those made before this feature, in 100 % of the checked frames.
- **SC-008**: At the largest settings (12 notes, history 12) a frame is made in under 2 seconds on the machine the other pictures are made on, and a 300-frame job at the defaults finishes without failing.

## Assumptions

- **The history includes the frame itself.** The user spoke of "previous bins", but then the picture would never show the sound that is playing: so the history entry of the frame itself is the newest of the entries of its picture (the same reading as a sliding window; the user's `i`/`j` loops do not say otherwise).
- **Value scale** (revised 2026-11-21, see the revision note): a note's value is the **square root** of its energy over the file's largest, so that **the loudest note of the whole file is 1** and the quiet notes are pulled up toward it (as the color of the other types uses `sqrt(value / peak)`), so `yval` lies from 0 to 12 as the user's color index expects. A value is the same for a note in every entry it is in.
- **Index**: 0 to 83 among the 84 drawn notes (the lowest note first), so `bc = index / 84` is from 0 to 83/84, "normalized to 1" as the user said.
- **The color index "the minimum of yval and the size of the bin indices"**: read as the minimum of `yval` and the last number of the reduced color set (12), so that it never runs past the end; with values from 0 to 1 it never has to cut, it is a safety. `yval` is rounded down to a whole number to pick one of the 13 colors.
- **The reduced colors**: position 256 (for `k = 12`) is one past the colormap's last color, so it takes the last color; this is how the user's formula must be read for a 256-color colormap.
- **Drawing order**: oldest entry first, newest last (on top), and loudest note first inside an entry, the order of the user's loops (outer = history, inner = notes).
- **Scale and position**: the user did not say; one fixed scale for the whole file, set so that the largest curve of the whole file just fits with a small margin, and the center of the pattern at the center of the picture, so that the picture does not jump in size between frames and nothing is cut off. A pattern is round, not stretched to the picture's 3:2 shape.
- **Line width** and **no fading of older entries**: a thin line of one width (about a thousandth of the picture's height, at least one pixel) for every curve; the user did not ask for the older entries to fade, so they do not. Fading older entries is a possible later change and is not part of this feature.
- **Defaults** 8 notes and history 8 (64 curves a picture) are mine; the user gave only the ranges 5 to 12.
- **Extra notes (feature 044)** applies as it does for the other types that pick the loudest notes: the tracked notes are the held ones, which fits the user's wish for a smooth flow; with its value 0 the tracked notes are the plain loudest.
- **"Black or transparent"**: the frames are pictures with three color channels, as for every other type, so **black** is used; a transparent background would need a four-channel picture, which no other type has and the movie would not keep, so it is left out unless asked for (the same decision as for Polychord, feature 042).
- **Constants, not settings**: `RC` = 5, the 12 color bins, the 1000 steps, the 6 to 20 turns and the 84 notes are fixed, as the user gave them as constants; only Number of notes, History length and History fade are settings.
- **Scope**: only the new image type, its three settings and their page controls. No other type changes. The documentation standard of feature 041 (types on every function, arrays documented, an `Order of operations:` list in the module, the new type's block in the pipeline overview of `image_types.py`) applies to the new code.
- **Dependencies**: the loudest notes of a frame and the held notes (feature 044) and the analysis and data smoothing already done for every type, the colormaps (feature 014) and the movie feature (feature 029).

## Revision note (2026-11-21)

After seeing the pictures, the user said that they were small most of the time while the largest one filled the window (one scale for the whole file, set by the loudest curve), and asked for the values to be scaled by their square root, "assuming it is between 0 and 1", so that the values are more clustered. I applied it where the value is made: **the value of a note is the square root of its strength over the largest strength of the whole file** (still 0 to 1, the loudest note still 1). It therefore changes the size, the loop width (through `yval`) and the color number of every curve together, not the size alone, and a quiet note has a much larger value than before (a note at a hundredth of the loudest was 0.01 and is now 0.1; at a quarter, 0.25 and now 0.5). The formulas, the one fixed scale and everything else are as before; FR-002 and the first Assumption read "the square root of its strength over the largest" from now on.

## Revision 2026-11-22 - History fade

The user asked that, whenever a frame is made, the history values are multiplied by a number below 1, a parameter from 0.4 to
0.85, so that the current frame's image is more prominent. Reading: the multiplication **compounds** with the age of an entry
(`fade ** age`: the frame's own entry is whole, the one before it is multiplied once, the one before that twice, ...), which is
what gives a gradual fade; a flat factor on every older entry (all of them `fade` times the newest) is the other reading and
would be a one-line change. The default is 0.7 (not given by the user). The multiplication is of the **values**, so an older
curve is smaller, has narrower loops and takes a lower color number; the file's extent (the scale) is unchanged, because the
newest entry is never faded and no faded curve reaches farther than an unfaded one.

## Revision 2026-11-24 - size between half and full, line width by age

The user asked that the size vary between 1/2 and full size, so that the minimum size is always 1/2 of the smallest dimension, and
that the line width (a linewidth parameter) make the more recent drawings thicker, from 5 down to 1 for the older history buffers,
rounded to an integer of at least 1.

Reading: **size** is the diameter of a curve (twice the distance of its farthest point from the center): the smallest curve is
half of the smallest side of the picture across (a quarter of the smallest side from the center, 100 pixels on a 600 x 400
picture) and the largest is the full room (187 pixels since 2026-11-25, i.e. 400 less the 10-pixel margin and the 3-pixel widest line, halved; 185 with the first 5-pixel line).
What decides where a curve is between the two is its extent `val (5 + bc yval)` over the file's largest: the louder (and higher)
the note, the bigger, as before, but never smaller than half; the earlier "one scale for everything" is kept only as the way to
compare extents. The **faded** value is used, so an old entry shrinks toward the half size (it no longer shrinks to nothing).
The **width** is in pixels, 5 for the picture's own frame and 1 for age History length - 1, linearly in between and rounded half
up (History length 8: 5, 4, 4, 3, 3, 2, 2, 1; 5: 5, 4, 3, 2, 1); in the first frames the newest entry is still 5.

## Revision 2026-11-24 (second) - the user's edits to the curve, turns and rc by the local peak, line width

The user changed `spirograph.py` by hand and asked for more. Recorded here:

1. **By the user, in the code**: a local `turns` (the number of turns round the smaller circle: first `idx[0] % 2 * 7 + 6`), a local `rc` (first `idx[0] % 2 + 4`, toggling 4 and 5) and `loops = (index mod 12) x val` in place of `bc x yval` with `bc = index / 84` (the modulo of the index, the letter, not the absolute note).
2. **Requested**: `turns = 2 x SMALL_TURNS x pctDistance + 6` with `pctDistance` 1 at the local peak energy and 0 at the local minimum (so from 6 to 20); the **Minimum distance** (peak distance) setting added to the page for Spirograph, "since we are now using the energy"; `rc` = `RC` when the frame is closer to the local peak than to the local minimum, `RC - 1` otherwise; the maximum line width hard-coded to 5 whatever the History length, and the width reduced by at least 1 after the current period.

Readings and defaults (mine):

- **`pctDistance` is `1 - beat_distances(beat)`**: the beat is the place of each frame in the local energy peak (the same measurement as for Decay, Chromatic Decay and Polychord, with the Minimum distance of the request), stretched over the range of the beat of the file as Chromatic Decay's target does, because inside real peaks the raw position hardly falls below about 0.55, which would leave `rc` always 5 and the turns above 13. The alternative, the raw beat position, is `1 - peak_distances(beat)` (one line).
- **`pct` belongs to the history entry's frame, not to the picture**: each curve takes the turns and the `rc` of its own entry's frame, so an entry keeps its shape in the pictures it is in (as it keeps its value and index, FR-004) and the history shows the beat going by. The alternative (one `pct` of the picture's frame for all of its curves) is one `percents` argument of `window_curves`.
- **Half way is not closer to the peak**: `rc` is `RC` only for `pct` above 0.5; at exactly 0.5 it is `RC - 1`.
- **`turns` is not rounded**, as written; the curve closes only at a whole number (see Edge Cases). Rounding is `np.round` in `turns_of()`.
- **Extents follow the new formula**: the farthest point is the first, `val (rc + (index mod 12) val)`, so `file_extent()` and the sizes of `window_curves()` use it (with the `rc` of the frame) and the loudest curve of the file still fills the room.
- **No beat (`None`) means every frame at the top of a peak** (`pct` 1: 20 turns, `rc` 5), the old look; the job always measures the beat for Spirograph.
- **Line width**: age 0 is 3 (`MAX_LINE_WIDTH`, constant; set by the user on 2026-11-25, it was 5, which was still too thick; the full radius, which keeps the widest line inside the picture, follows it); ages 1 to History length - 1 go from 2 down to 1 in equal steps, rounded half up (History 5: 3, 2, 2, 1, 1; 8: 3, 2, 2, 2, 2, 1, 1, 1; 12: 3, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1; from 5 they were 5, 4, 3, 2, 1; 5, 4, 4, 3, 3, 2, 2, 1; 5, 4, 4, 3, 3, 3, 3, 2, 2, 2, 1, 1). Before, a History of 9 or more gave 5 to the first older entry too. "Reduce by at least 1 after the current period" is read as: the first older entry is already below the newest (at most 4 with the width of 5; at most 2 with 3). **Revision 2026-11-25**: the user changed `MAX_LINE_WIDTH` to 3 (5 was still too thick), and the older entries follow it (`MAX_LINE_WIDTH - 1` at age 1 down to 1); with 3 there are only the widths 2 and 1 for the older entries, so a long history is mostly 2 wide and then 1. The full radius (the room less the margin and the widest line) is 187 on 600 x 400, was 185.
