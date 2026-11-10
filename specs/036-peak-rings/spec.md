# Feature Specification: Peak Rings

**Feature Branch**: `036-peak-rings` (no git branch created; spec directory name only)

**Created**: 2026-11-09

**Status**: Draft

**Revised 2026-11-10 (second note)**: the user restored `decay.NEIGHBOURS` to 8 for Decay and Decay Exp and gave Chromatic Decay **its own constant, `PRETEND_NEIGHBORS = 6`**, in `chromatic_decay.py`. Wherever these documents say `NEIGHBOURS` for Chromatic Decay, read `PRETEND_NEIGHBORS` (6: a circle gives away 6 times the loss per frame, one sixth to each receiver, four sixths lost). Decay and Decay Exp are unchanged.

**Revised 2026-11-10 (third change)**: the user saw that the rings **only went to the middle color of the colormap** and asked that they go **from the first color to the last**. The cause: the position in the local peak is 0 to 1 in principle, but **inside the peaks of real music it hardly goes below about 0.55** (the median is 0.75, the 5th percentile 0.61 on the files tried), so `1 - position` only reaches about 0.45, the first half of the colormap. The distance from the peak is therefore now **stretched over the range of the beat of the file**: the **highest position** is the top of the beat (distance 0, the **first color**), the **1st percentile of the positions inside the peaks** is the bottom of the beat (distance 1, the **last color**), in a straight line between and held at the ends, and a frame outside every peak (position 0) is distance 1. With no position inside a peak, or no range, the distance is `1 - position` as before. Wherever the text below says that the distance is `1 - position`, this replaces it for the colors.

**Input**: User description: "I'd like to add concentric circles to the center for the local peaks (of the Chromatic Decay picture, whose ring is empty in the middle).  The color would indicate the distance from the local peak, from left to right in the colormap.  The center indicates the current level, each level will be an average of the previous 2 samples, to the outside of the circle.  The diameter of the circle I think will be about 140px."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rings in the middle of the Chromatic Decay ring that show where the music is in its beat (Priority: P1)

The 12 circles of **Chromatic Decay** (feature 035) stand on a ring and leave its middle empty. The user wants **concentric circles in that middle that show the local peaks** (the beat, features 023 and 024): a small target of rings, about **140 pixels across**, centered in the picture and drawn inside the ring of letters without touching it.

- **What a ring shows**: the **distance from the local peak** at some moment. The picture already knows, for every frame, the frame's **position in the local energy peak**, from 0 (far from a peak, at the bottom of the beat or between peaks) to 1 (at the top of a peak). The distance from the peak is `1 - position`: 0 at the top of a peak, 1 when far from one.
- **Color**: a ring is colored from the colormap by its distance from the peak, **from left to right in the colormap**: at the peak the color of the **left** (start) of the colormap, far from a peak the color of the **right** (end), in between the colors in between. **Decided by the user, 2026-11-09**: the distance grows from left to right, so the **peak is the start (left) of the colormap and far from a peak is its end (right)**: the first color at the top of a peak, the last color far from one (with Coolwarm: blue at the peak, red far from it).
- **The center is the present**: the **center circle** shows the **current frame's** distance from the peak. **Decided by the user, 2026-11-09**: the rings outward are a **history in time**. With `t` the current frame, ring 1 (the center) is the distance at frame `t`; ring 2 is the **average of the distances at frames `t - 1` and `t - 2`**; ring 3 the average at frames `t - 3` and `t - 4`; and so on: **ring `k` (from 2) is the average of the distances of the 2 frames `t - (2k - 3)` and `t - (2k - 2)`**. The rings are the last moments, the newest in the middle and the oldest outside, so a flash at the top of a beat spreads outward like a ripple as the frames go by.
- **How many rings**: **Decided by the user, 2026-11-09**: **12 rings**, each about **6 pixels** wide (140 / 2 / 12 = 5.83 pixels), the 12 rings that Concentric and Decay use. The history therefore reaches back 22 frames (ring 12 is the average of frames `t - 21` and `t - 22`), about 0.7 seconds at 30 frames a second.

So at the top of a beat the middle of the picture flashes in the start color of the colormap, and the flash spreads outward in the rings as the moments go by, then the rings turn to the end color when the music is far from a peak. It works from the same beat measurement that Chromatic Decay already uses to charge its circles, so **no new setting** is needed (the Local peaks settings of the page, Minimum distance and Prominence, change it as they change the charging).

**Why this priority**: It is the whole request.

**Independent Test**: Make a file with a clear pulse (a note struck at regular intervals) and create Chromatic Decay frames. In the middle of the ring there is a circle about 140 pixels across made of concentric rings; the center ring is in the start color of the colormap at the moment of a pulse and in the end color between pulses, and the colors of the outer rings follow the beat of the moments before.

**Acceptance Scenarios**:

1. **Given** a frame at the top of a local peak (position 1), **When** it is drawn, **Then** the center circle has the first color of the colormap (distance 0).
2. **Given** a frame far from any peak (position 0), **When** it is drawn, **Then** the center circle has the last color of the colormap (distance 1).
3. **Given** a frame with position `p` between 0 and 1, **When** it is drawn, **Then** the center circle has the color of the colormap at `1 - p` of the way from its start to its end.
4. **Given** any frame, **When** it is drawn, **Then** the rings fill a circle about 140 pixels across on a 600 x 400 picture, centered in the picture, and nothing of them reaches the circles of the letters.
5. **Given** the same file and settings, **When** it is made twice, **Then** the images are identical.

---

### User Story 2 - The rings come with the type and need nothing from the user (Priority: P2)

The rings are part of the Chromatic Decay picture. There is **no setting** for them and no new field in the request or the response: they are drawn whenever a Chromatic Decay picture is made, from the beat that is already measured for that type. The other image types are not changed. The Local peaks settings on the page (Minimum distance and Prominence) apply to the rings as to the rest of the picture, and the help text of Chromatic Decay says what the rings show.

**Why this priority**: It keeps the feature small and the other types unchanged.

**Independent Test**: Choose Chromatic Decay with a pulsed file and see the rings; change Minimum distance and the rings follow the new beat; choose any other type and see no rings; the request and the response have the same fields as before.

**Acceptance Scenarios**:

1. **Given** a Chromatic Decay job, **When** frames are made, **Then** the rings are in every frame, and the request and response have exactly the fields they had.
2. **Given** another image type, **When** frames are made, **Then** the frames are exactly what they were before this feature.
3. **Given** a different Minimum distance or Prominence, **When** the frames are made, **Then** the rings follow the beat that those settings measure.

---

### Edge Cases

- A file with no beat (a steady tone, silence): the position is 0 in every frame, so every ring is in the last color of the colormap (far from a peak), and the picture is otherwise as before.
- The first frames of a file: the moments before the start do not exist; they count as far from a peak (position 0), so the outer rings are in the last color until enough frames have gone by.
- A very short file (fewer frames than rings): the rings that would show older moments than the file has show the moments before its start (far from a peak).
- Other frame sizes scale the circle with the picture (it is about 140 pixels on the 600 x 400 picture and keeps its share of the ring on other sizes).
- A frame in which a letter's circle is full size: the rings are inside the ring of letters and never overlap a circle, because the middle of the ring is 224 pixels across and the rings are 140.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Chromatic Decay picture MUST show, centered in the picture, **concentric rings in a circle about 140 pixels across** (on the 600 x 400 picture; scaled with the picture size), inside the ring of the 12 letters without touching it.
- **FR-002**: The **center circle** MUST show the current frame's distance from the local peak, **stretched over the range of the beat of the file** (see the third change): 0 at the highest position of the file, 1 at the 1st percentile of the positions inside the peaks and for a frame outside every peak, where the position is the frame's place in the local peak (0 to 1), as the type already measures it.
- **FR-003**: Ring `k` outward (from 2) MUST show the average of the distances from the peak of the frames `t - (2k - 3)` and `t - (2k - 2)`, `t` being the current frame.
- **FR-004**: Each ring MUST be colored from the colormap by its distance from the peak: the start (first) color at distance 0 (the top of a peak), the end (last) color at distance 1, and the colors between at the same share of the way.
- **FR-005**: There MUST be **12 rings** of equal width that together fill the circle (about 5.8 pixels each on the 600 x 400 picture).
- **FR-006**: Moments before the first frame MUST count as far from a peak (position 0).
- **FR-007**: The rings MUST need **no new setting**, request field or response field, MUST use the beat that Chromatic Decay already measures (so the Local peaks settings apply), and MUST NOT change the other image types or the 12 circles and their decay.
- **FR-008**: Results MUST be repeatable: the same file and settings MUST give identical images.
- **FR-009**: The help text of Chromatic Decay MUST say what the rings show.

### Key Entities

- **Position in the local peak**: for each frame, a number from 0 (far from a peak) to 1 (at the top of one), already measured for the beat.
- **Distance from the peak**: `1 - position`, from 0 (at the peak) to 1 (far from it).
- **Ring**: one of the concentric rings of the circle in the middle, with a color from the colormap by its distance from the peak.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a frame at the top of a peak the center circle has the first color of the colormap and in a frame far from a peak the last color, in 100% of the frames of a pulsed file.
- **SC-002**: The rings fill a circle of 140 pixels across (within one pixel) on the 600 x 400 picture, centered at the middle of the picture, and none of them touches a circle of a letter.
- **SC-003**: The colors of the rings follow the beat of the moments they stand for, checked on a hand-made beat for every ring.
- **SC-004**: The frames of every other image type, and the request and response fields, are identical to what they were before this feature; the same file and settings give identical images.
- **SC-005**: A user can see where the music is in its beat from the middle of the picture alone, without any setting.

## Assumptions

- "The local peaks" are the **position in the local energy peak** that the pictures already use (Local peaks, features 023 and 024): 0 at the bottom of the beat or between peaks, 1 at the top of a peak. "The distance from the local peak" is `1 - position`.
- The **samples** are the frames: one beat position for each frame, as Chromatic Decay already has for charging its circles.
- The circle is for **Chromatic Decay only**: its ring is the picture with an empty middle (the middle of the ring is 224 pixels across, so a circle of 140 fits). Other types are not changed; the same circle could be offered to them later.
- The rings are always drawn for this type, with no setting and no way to turn them off, the user having asked for none.
- The diameter is "about 140 px" on the 600 x 400 picture; it is taken as exactly 140 pixels there (a radius of 70) and scaled with the picture on other sizes.
- The colors use the colormap's whole range between the two ends; the background stays the middle color of the colormap as before.
- The decay of Chromatic Decay uses the `NEIGHBOURS` constant of `decay.py`, which the user changed from 8 to 6; this feature does not depend on it.
