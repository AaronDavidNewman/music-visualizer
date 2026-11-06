# Feature Specification: Decay Exp

**Feature Branch**: `030-decay-exp` (no git branch created; spec directory name only)

**Created**: 2026-11-06

**Status**: Draft

**Revised 2026-11-06** (the user changed the loss): the amount a circle gives to each neighbour per frame is now **`sin²(π/2 × p/64)`**, not `1 / (1 + e^(p/8))`. The first formula was backwards: it made a fuller circle give *less*. With the new one a circle with more points drains *faster* (0 at 0 points, 0.5 at 32, 1 at 64, so a full circle gives 8 points in all). The gain `p × e^(−p/8)` is unchanged. Wherever the text below shows the old formula or its numbers (0.27 at 8 points, 0.0003 at 64, "empties below 3.2 points", "back at 0 in about 6,600 frames"), the revised sections and the Assumptions give the current ones.

**Revised 2026-11-06 (second change)**: the **taper** (the 8 of `e^(−p/8)` in the gain) is no longer fixed. It starts at 8 and **rises by 0.01 in every frame, up to 12**. As soon as **more than 10 circles have more than 32 points**, it stops rising and **falls by 0.01 in every frame until it is back at 8** (it keeps falling whatever the number of full circles is by then), and then rises again. It never goes over 12 or under 8. The first frame is at 8. It changes the gain only (the loss `sin²(π/2 × p/64)` has no 8 in it). Wherever the text below says `e^(−p/8)` for the gain, it means `e^(−p/taper)` with the taper of that frame.

**Input**: User description: "create a new image type called decay-exp.  It uses the same circles and point system as decay image type, but the rate at which the circles take on values is different.  For each cycle, the amount added is multiplied by np.exp(-p/8) where p is the number of points we would add.  The number of points removed is 1/(1 + np.exp(p/8)) where p is the number of points the circle already has."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Decay circles whose gain and loss follow an exponential curve (Priority: P1)

The user wants another image type, **Decay Exp** (request value `decay-exp`). It is the **Decay** picture of feature 027 in every respect except the **rate at which circles gain and lose points**: 84 circles in the places, layout, full radius and background of Concentric; each circle keeps a **point value from 0 to 64** from frame to frame; its **size** (smallest at 0 points, full at 24), **color** (first color at 0 points, last color at 32) and **rings** (from 32 to 64 points) follow the points exactly as in Decay; the five loudest notes of a frame are the ones that gain points, with the beat bonus; and circles give points to the cells around them in decay steps, with the same neighbours, edge behaviour and rounding rules. Only two amounts change, both to an exponential curve:

- **Gain**: for every circle that gains points in a cycle, the points it **would** gain in Decay (24, 20, 16, 12 or 8 by rank, plus the beat bonus of `8 × position`, 0 to 8) are **multiplied by `e^(−p/t)`**, `p` being that number of points and `t` the **taper** of the frame: 8 in the first frame, then rising by 0.01 a frame up to 12, and falling by 0.01 a frame, whenever more than 10 circles have more than 32 points, until it is back at 8. A gain of `p` therefore becomes `p × e^(−p/t)`.
- **Loss**: the points a circle gives away are **not** taken from the four saturation-level amounts of Decay. The amount **removed** (given to each neighbour per frame) is **`sin²(π/2 × p/64)`**, `p` being the points the circle **already has** before the step: 0 at 0 points, about 0.04 at 8, 0.31 at 24, 0.5 at 32, 0.85 at 48 and 1 at 64. A circle with 0 points gives nothing.

Everything else about a decay step is as in Decay: the amount is given to each of the up to 8 cells around the circle, an edge or corner circle decays as if it had 8 neighbours (what the missing neighbours would have had is lost), a circle never gives more than it has, all circles give and receive at the same time from the points before the step, points are held between 0 and 64, and a circle left with less than a hundredth of a point has none.

The picture therefore shows the music as glowing spots whose growth is **tapered** (a big gain is cut back far harder than a small one, and the cut eases off slowly as the picture goes on and tightens again when too many circles are full) and whose draining is **strongest for a full circle and barely there for a nearly empty one**.

**Why this priority**: This is the whole request.

**Independent Test**: Make a file with one steady loud note and no beat. Create Decay Exp frames: the note gains `24 × e^(−3)` ≈ 1.19 points in the first frame (against 24 in Decay; the taper is 8 there), so its circle starts small and in the first colors and gives away almost nothing in the decay step (about 0.007 points: a circle with so few points hardly drains). It grows over the following frames (about 2.4, 3.5, 4.6, 5.7 and 6.6 points in the next five at the default rate), faster and faster as the taper rises (about 19.6 points at frame 100, 32.4 at frame 400, where the taper reaches 12) and settles near 34.4 points, where what it gains at a taper of 12 balances what it gives to its neighbours. Only one circle is over 32 points, so the taper is never turned down. Five steady notes close together push 13 circles over 32 points; the taper then turns down and swings between 8 and about 10.3, and the biggest circle reaches about 57 and settles near 50, never 64. Decay frames of the same file are unchanged.

**Acceptance Scenarios**:

1. **Given** the frame's note values, **When** the picture is made, **Then** there are 84 circles in the same places, sizes, colors and rings as Decay for the same points, on the same background, with the same Note layout choices.
2. **Given** a circle that would gain `p` points in a cycle (24, 20, 16, 12 or 8 by rank plus `8 × position`), **When** its points are added, **Then** it gains `p × e^(−p/t)` points, `t` being the taper of the frame (so in the first frame, at a taper of 8, 24 gains about 1.19, 20 about 1.64, 16 about 2.17, 12 about 2.68 and 8 about 2.94, with no beat), and the result is held between 0 and 64.
3. **Given** a decay step and a circle with `p` points before it, **When** the step is applied, **Then** the circle gives each neighbour `sin²(π/2 × p/64)` points per frame's worth of the step (so about 0.0006 each at 1 point, 0.038 at 8, 0.31 at 24, 0.5 at 32 and 1 at 64), or everything it has if that is less; a circle with 0 points gives nothing.
4. **Given** a decay step, **When** it is applied to a circle at an edge or in a corner, **Then** it loses as much as a circle with 8 neighbours, as in Decay: the same amount to each neighbour it has, and the rest lost.
5. **Given** a decay step, **When** it is applied, **Then** the total of the points after it is never greater than before it, and no circle has fewer than 0 or more than 64 points.
6. **Given** the same file and settings, **When** the pictures are made twice, **Then** the files are identical.
7. **Given** the other seven image types, **When** they are made, **Then** they are identical, file for file, to those made before this feature (Decay included).
8. **Given** any file, **When** the first frame is made, **Then** the taper is 8; **When** later frames are made and no more than 10 circles have more than 32 points, **Then** the taper is 0.01 higher in every frame than in the one before, until it is 12, where it stays (so 8.01 in the second frame, 12 from the 401st).
9. **Given** a frame after which more than 10 circles have more than 32 points (more than 10, not 10), **When** the next frame is made, **Then** the taper is 0.01 lower than in this one, and it keeps falling by 0.01 in every frame, whatever the number of full circles is by then, until it is 8; only there does it start to rise again. It is never over 12 or under 8.
10. **Given** the taper of a frame, **When** the frame's points are added, **Then** the gains use that taper for every note of the frame; the decay steps (the loss) do not depend on it.

---

### User Story 2 - Choose Decay Exp on the page and set the decay rate (Priority: P2)

The settings page offers **Decay Exp** as an eighth choice of **Image type**. It shows the same groups as Decay: Analysis, Colormap, Image type, **Local peaks** (Minimum distance and Prominence, no checkbox, because the beat always adds points), **Data smoothing**, **Note layout** (Rows or Spiral) and a **Decay** group. The Decay group holds the **Decay rate** (0.25 to 4 in steps of 0.25, default 1, with the same meaning as in Decay: how often a decay step is taken, each moving that many frames' worth). It does **not** hold the four saturation-level decay amounts, because the loss is given by the formula above and those amounts have no effect on Decay Exp. Threshold, Notes, Oversampling, Interpolate and Gaussian smoothing do not apply: they are accepted by the request and ignored, and not shown on the page or in the summary.

**Why this priority**: The picture exists without the page (through the API), but the user reaches it from the page.

**Independent Test**: On the page choose Decay Exp: the groups listed above appear with the Decay group showing only the Decay rate, the unused groups are gone, and Create frames makes frames. Through the API `image_type=decay-exp&decay_rate=2` makes 600 × 400 frames.

**Acceptance Scenarios**:

1. **Given** the Image type list, **When** the page is shown, **Then** it offers Tiles, Blended tiles, Contour, Circles, Circles paint, Concentric, Decay and **Decay Exp**, and a request with `image_type=decay-exp` is accepted; any other value is refused with a message that lists the eight names.
2. **Given** Decay Exp is chosen on the page, **When** the settings are shown, **Then** the groups Analysis, Colormap, Image type, Local peaks (without a Beat coloring checkbox), Data smoothing, Note layout and Decay (with the Decay rate only) are shown, and the groups of Threshold and Notes and Image smoothing are not.
3. **Given** a Decay Exp request, **When** the decay rate is not a number from 0.25 to 4 in steps of 0.25, **Then** it is refused before any work is done with the message used for Decay; when it is left out, 1 is used.
4. **Given** a Decay Exp request that also sends decay amounts (`decay_low`, `decay_medium`, `decay_high`, `decay_saturated`), **When** the request is checked, **Then** they are checked as always but have no effect on the picture and are not shown on the page or in the summary.
5. **Given** a Decay Exp request, **When** the Local peaks values are not allowed, **Then** they are refused before any work is done, with the messages of the measurement; the beat is measured for every Decay Exp job.
6. **Given** the result summary of a Decay Exp job, **When** it is shown, **Then** it lists the image type, the colormap, the smoothing settings, the note layout, Minimum distance, Prominence and the Decay rate, and not Threshold, Notes, Interpolate, Oversampling, Gaussian smoothing or the four decay amounts.

---

### User Story 3 - Quiet, silent and beat-less moments look sensible (Priority: P3)

Decay Exp behaves as Decay in the quiet cases: all circles start at 0 points, so a **silent file** gives 84 smallest circles in the first color; a frame with **no known beat** has position 0, so the gains are `24 × e^(−3)`, `20 × e^(−2.5)`, `16 × e^(−2)`, `12 × e^(−1.5)` and `8 × e^(−1)`; a **silent frame** adds nothing and the circles only decay; a note with value 0 gets no points; ties go to the lower note; and a circle never gives more than it has, so no points appear from nothing.

**Why this priority**: These define the picture at the edges of the data.

**Independent Test**: A silent file gives 84 dots in the first color; a file with one loud note followed by silence fades, the largest circle falling under 1 point after a few thousand frames, and ends with every circle at 0 points after a very long silence (see the edge cases).

**Acceptance Scenarios**:

1. **Given** a silent file, **When** the pictures are made, **Then** they are made without failing and every circle has 0 points.
2. **Given** a file or frame with no beat, **When** the points are added, **Then** the beat bonus is 0 and the gains are the five tapered values above.
3. **Given** a long silence after a loud passage, **When** enough decay steps have passed, **Then** every circle is back at 0 points (the hundredth-of-a-point rule makes this exact, but with this curve it takes a very long time: see the edge cases), and the total of the points never grows meanwhile.

---

### Edge Cases

- **The gain is not in rank order**: because `p × e^(−p/t)` falls as `p` rises above `t`, at the start (a taper of 8) the loudest note gains the **least** (about 1.19 points) and the fifth loudest the most (about 2.94), the opposite of Decay. As the taper rises the gains grow and the order flattens out; at a taper of 12 the five gain about 3.25, 3.78, 4.22, 4.41 and 4.11. This is what the stated formula gives and is intended to be implemented as written (see Assumptions).
- **A beat bonus raises the gain before it is tapered**: at the top of the peak the loudest note would gain 32, so it gains `32 × e^(−4)` ≈ 0.59 at a taper of 8 (`32 × e^(−32/12)` ≈ 2.22 at 12).
- **Fading has a long tail**: the loss `sin²(π/2 × p/64)` falls with the *square* of the points when they are few (about 0.0006 per neighbour at 1 point, 0.00015 at 0.5), so a faint circle hardly drains and the last traces of a loud passage linger. Measured for five loud notes held for 100 frames and then silence, at the default rate: the largest circle is under 1 point after about 3,100 frames (about 1 minute 43 seconds at 30 frames a second), under a tenth of a point after about 31,800 (about 18 minutes) and exactly 0 only after about 228,700 frames (about 2 hours). A circle with less than 1 point is a dot of at most about 3 pixels of radius, against 2 for a circle with none, so the picture looks empty long before the points are gone.
- **Charged circles drain fast and settle below 64**: a circle with 64 points gives 1 point to each of its 8 neighbours, 8 in all, every frame, so it cannot stay full on the gains of a few notes (at most about 4.4 a frame at the highest taper). A single steady note, once the taper has risen to 12 (400 frames), settles near 34.4 points; five steady notes close together reach about 57 at most and settle near 50, never 64. The clamp at 64 is only a safeguard for this image type.
- **The taper can sit at 12 or swing**: with at most 10 circles over 32 points the taper climbs to 12 and stays there. With more, it turns down at once and falls, whatever happens meanwhile, to 8, then climbs again, so for a busy passage it swings between 8 and a value that depends on how soon the circles fill (about 10.3 for five steady notes). The circles are counted at the end of every frame, after the gains and the decay steps of that frame, and the new taper is used from the next frame; a decay rate below 1 (several steps in a frame) or above 1 does not change how fast the taper moves.
- **Gain and loss in the same frame**: the gain is added first and the decay steps of the frame follow, as in Decay.
- **Different frame rates and window sizes** work as for the other pictures; the frame count, names, size (600 × 400) and timing do not change.
- **A very short file** (shorter than the peaks window) is measured as one window.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: There MUST be an eighth image type, `decay-exp` (label **Decay Exp**), accepted by the job request and offered on the settings page; the list of image types in the refusal message MUST name all eight.
- **FR-002**: A Decay Exp frame MUST draw its circles, with their sizes, colors, rings, places, full radius, background and Note layout, exactly as Decay draws circles with the same points.
- **FR-003**: Every circle MUST keep a point value from 0 to 64 from frame to frame, starting at 0 before the first frame, as in Decay.
- **FR-004**: In every frame the 5 loudest notes (same choice, ties and exclusion of zero values as Decay) MUST gain, for a Decay gain of `p` points (24, 20, 16, 12 or 8 by rank plus `8 × position`), the amount `p × e^(−p/t)`, `t` being the taper of the frame; the result MUST be held within 0 and 64.
- **FR-004a**: The taper MUST be 8 in the first frame and MUST change by 0.01 at most from one frame to the next: up while no more than 10 circles had more than 32 points at the end of the previous frame (stopping at 12), down once more than 10 had, and then down in every frame until it is 8, where it rises again. It MUST never be over 12 or under 8, and it MUST be exactly 8 and 12 at the ends (no accumulated rounding). It MUST NOT change how much a circle gives away.
- **FR-005**: In a decay step a circle with `p` points before the step MUST give each neighbour `sin²(π/2 × p/64)` points per frame's worth of the step (a step moves as many frames' worth as the decay rate says), or everything it has if that is less, and nothing when `p` is 0. Neighbours, edge and corner behaviour, simultaneous giving and receiving, the 0 to 64 limits and the hundredth-of-a-point rule MUST be those of Decay.
- **FR-006**: The Decay rate, the timing of decay steps within frames and the Local peaks and Note layout settings MUST have the meanings, ranges, defaults and checks they have for Decay.
- **FR-007**: The four decay amounts MUST NOT affect Decay Exp; they MUST be accepted and checked as for every image type, and MUST NOT be shown for Decay Exp on the page or in the result summary.
- **FR-008**: The settings that apply to Decay Exp, and only those (colormap, the analysis settings, Smoothing window, Smoothing, Minimum distance, Prominence, Note layout and Decay rate), MUST be shown on the page and in the result summary; Threshold, Notes, Oversampling, Interpolate and Gaussian smoothing MUST be accepted by the request, checked as always, and have no effect.
- **FR-009**: The frames MUST be 600 × 400, with the frame count, names and timing of the other image types; the same file and settings MUST give the same frames; the other seven image types MUST be identical, file for file, to those made before this feature.
- **FR-010**: Creating the frames of a 60 second file at 30 frames a second MUST NOT take noticeably longer than for Decay.
- **FR-011**: The documentation MUST describe Decay Exp, how its gain and loss differ from Decay, and its settings.

### Key Entities *(include if feature involves data)*

- **Decay Exp image type**: The new picture, value `decay-exp`; Decay with exponential gain and loss.
- **Tapered gain**: The points a circle receives in a frame: the Decay gain `p` multiplied by `e^(−p/t)`.
- **Taper**: The `t` of the gain, from 8 to 12, 8 in the first frame; it changes by 0.01 a frame, rising until it is 12 and falling, once more than 10 circles have more than 32 points, until it is back at 8.
- **Loss**: The points a circle gives to each neighbour per frame: `sin²(π/2 × p/64)` for a circle that has `p` points.
- **Circle, points, decay step, decay rate**: As in Decay.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a file with one steady loud note and no beat, the points of that note's circle after the first frame are 24 × e^(−3) (about 1.19), within a thousandth of a point.
- **SC-002**: In every decay step the total of all points never grows, no circle has fewer than 0 or more than 64 points afterwards, and a circle with enough points loses exactly 8 times the per-neighbour amount (`sin²(π/2 × p/64)`) times the frames' worth of the step, in the middle of the grid, on an edge and in a corner alike.
- **SC-003**: After a loud passage followed by silence, the largest circle is under 1 point within a few thousand frames and every circle is back at 0 points after a finite (very large) number of steps, and a silent file, a file without a beat and a file shorter than the peaks window make Decay Exp frames without failing.
- **SC-004**: The frames of the other seven image types for the reference test files are identical, file for file, to those made before this feature, and two runs of the same Decay Exp job are identical.
- **SC-005**: A 60 second file at 30 frames a second makes its Decay Exp frames in under 30 seconds on the development machine, as for Decay.
- **SC-006**: For a silent file the taper of frame `k` (counting from 1) is `8 + 0.01 × (k − 1)` until it is exactly 12 at frame 401, and stays 12; for five steady loud notes the taper turns down in the frame after more than 10 circles are over 32 points, falls by 0.01 in each following frame to exactly 8, and never leaves the range 8 to 12.

## Assumptions

- **"Cycle" means a frame.** The user said "for each cycle, the amount added is multiplied by…". Points are only added once per frame, so the tapered gain is applied to the gain of each frame. The loss is applied in the decay steps of the frame, at the Decay rate, as in Decay.
- **The gain is taken exactly as written; the loss was revised.** The gain `p × e^(−p/8)` is largest for the *lowest* ranks, so the loudest note gains the least, the opposite of Decay; this is what the request says and what is built (if a different reading was meant, for example `p` being the circle's current points, the formula can be swapped without changing anything else here). The loss as first written, `1 / (1 + e^(p/8))`, made fuller circles give *less*; the user said they meant the opposite ("more saturated values drain faster") and replaced it on 2026-11-06 with `sin²(π/2 × p/64)`, which is what the current text describes. Later the same day the user made the 8 of the gain dynamic (the taper).
- **How the taper moves** (the user's words: "gradually increase the Taper from 8 to 12 by adding 0.01 at each cycle (frame). If more than 10 circles are > 32 value, stop adding to the taper and start subtracting until you are back to 8"): a cycle is a frame, as for the gain. "Start subtracting until you are back to 8" is taken as a state that lasts: once turned down it keeps falling to 8 whatever the number of full circles is by then, and rises again only from 8 (otherwise it would hover). More than 10 means 11 or more; "> 32" means strictly more than 32 points; all 84 circles are counted, at the end of each frame, and the first frame is at 8 because nothing has been counted yet.
- **The loss is per neighbour per frame.** The request says "the number of points removed", without saying whether that is in all or to each neighbour. It replaces the per-neighbour decay amount of Decay (0.5 to 3 by saturation level), so it is taken as the amount given to **each neighbour per frame**, which keeps the rest of the decay step (8 neighbours, edge loss, frames' worth) as it is. A circle then loses 8 times that in all, and `p` is the circle's points before the step.
- **The decay rate stays; the four decay amounts go.** The timing of decay steps is independent of how much is taken, so the Decay rate is kept with its meaning; the saturation-level amounts are replaced by the formula and have no effect on Decay Exp, so they are not offered for it.
- **No new settings.** The constant 8 in both formulas is fixed; it is not a setting.
- **"Same circles and point system"** means the 84 circles, their size, color and rings by points, the 0 to 64 range, the five loudest notes with their rank gains and beat bonus, and the grid, neighbours and Note layout of Decay (feature 027), unchanged.
- **The value is `decay-exp`** with a hyphen, as the user wrote it, although the other image type values use underscores where they have two words (`circles_paint`); the label is "Decay Exp".
- **Settings that do not apply**: as for Decay, Threshold, Notes, Oversampling, Interpolate and Gaussian smoothing are accepted and ignored; the beat always counts, so there is no beat checkbox.
