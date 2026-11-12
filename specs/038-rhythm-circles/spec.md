# Feature Specification: Rhythm Circles

**Feature Branch**: `038-rhythm-circles` (no git branch created; spec directory name only)

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "create an image type for representing how rhythmic a section of sound is.  There will be a single set of concentric circles.  The inner circles are 'notched', so they are a single color with a notch of 1/16 to 1/8 a contrasting color.  The circles rotate.  The outer circle rotates at a rate of the current tempo, e.g. the current rate of time between local peaks.  The second inner circle rotates based on the rate of change of the outer circle.  In other words, the difference in the tempo divided by the time between the samples.  The third circle is the secondary rate of change, the difference in the last 2 rates of change divided by the total time between the samples.  The next 3 circles are the tempo averaged over the last 2, 4, 8 periods.  The circles rotate in a clockwise positive direction at the tempo rate, in beats per minute.  In the case of the rates of change, the circles could rotate in either direction.  The parameters are the minimum distance and prominence of the local peaks."

**Revised by the user, 2026-11-11 (after the first implementation)**: "I changed my mind about the circle meanings. The outer 2 circles are the current tempo and its rate of change. The 3rd and 4th should be the average over 2 samples, and the rate of change of that average. The 5th and 6th are the average over 4 samples, and the rate of change of that average." The circles below are those of the revision: there is **no secondary rate of change and no average over 8**; every rate-of-change circle follows the circle it is the change of.

**Revised again by the user, 2026-11-11**: "Instead of averaging the tempos, select the fastest one. So in fastest mode, the reported tempo is actually the fastest of the previous samples, not the average. This way, the tempo will always be closest to the minimum distance. Sometimes the peaks are actually multiples of the beat, this will tend to smooth out the tempo of a rhythmic piece." The 3rd and 5th circles are therefore the **fastest** (highest) tempo of the latest 2 and 4 peaks, not the mean; their circles after them turn at the change of that fastest tempo. It replaces the averaging outright (there is no setting for a mode, so the request and the page have no new field).

**Revised a third time by the user, 2026-11-11**: "Display the rings in the opposite order. So the longest aggregation is the outer layer. Also, add a 4th layer so fastest of previous 8 samples." There are now **four layers** (the tempo and the fastest tempo of the latest 2, 4 and 8 peaks), each a **level** circle with, inside it, a circle for the **rate of change of that level**: **eight circles**, from the outer: the fastest of 8 and its rate of change, the fastest of 4 and its rate, the fastest of 2 and its rate, the tempo and its rate. The order of the layers is reversed and the level stays outside its own rate of change (the user did not say whether a rate should come before its level; this is the reading in which each rate circle sits just inside the circle it measures, as before).

**Revised a fourth time by the user, 2026-11-11**: "For the aggregated samples, instead of always taking the fastest of the previous values, choose either the average or the fastest, whichever is closest to the current tempo." The layers of 2, 4 and 8 peaks (the **aggregated tempos**) are therefore, for each peak, the **average** or the **fastest** (highest) of the tempos of the latest 2, 4 or 8 peaks, whichever is closer to the **current tempo** (the tempo of that peak, which is one of the tempos of the window); the circles, their order and the rates of change are as before. When the two are equally close the fastest is taken (the user did not say; the fastest is what the layers took before). There is no setting for this.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Eight rotating notched circles that show the tempo, how it changes and its aggregated tempos (Priority: P1)

The user wants a new image type, **Rhythm Circles** (request value `rhythm-circles`), that shows **how rhythmic a section of sound is**. The picture is **one set of eight concentric circles** in the middle of the frame. Each circle is a **ring of a single color with a notch** (a short arc of a contrasting color, **from 1/16 to 1/8 of the circle**), and **the circles rotate**, so the notch shows the rotation. The rotation of every circle comes from the **local peaks** of the sound (features 023 and 024: the periodic maxima of its energy, the "beats"), as follows, from the **outer** circle to the **innermost**:

1. **Aggregated tempo of the last 8 periods (outer circle).** It rotates **clockwise at the tempo that stands for the latest 8 peaks** (of those there are while there are fewer), in **beats per minute**: the **average** or the **fastest** (the highest rate, the shortest interval between peaks) of the tempos of the window, whichever is **closer to the current tempo** (the fastest when they are equally close). Peaks are sometimes multiples of the beat: the fastest follows the beat through them and the average steadies the tempo when it falls. The circle makes as many revolutions per minute as that tempo has beats per minute, **clockwise** being positive.
2. **Rate of change of that aggregated tempo (second circle).** It rotates at the change of the aggregated tempo from the previous peak to this one divided by the seconds between those two peaks, per second, taken as revolutions per minute: clockwise when it goes up, counterclockwise when it goes down, and a circle that stands still while it does not change.
3. **Aggregated tempo of the last 4 periods (third circle).** The same, over the latest 4 peaks.
4. **Rate of change of that aggregated tempo (fourth circle).**
5. **Aggregated tempo of the last 2 periods (fifth circle).** The same, over the latest 2 peaks.
6. **Rate of change of that aggregated tempo (sixth circle).**
7. **Tempo (seventh circle).** It rotates at the **current tempo**: the rate of the time between the local peaks, in **beats per minute** (60 divided by the time in seconds between the latest peak and the one before it; the measurement already gives it for every peak). One revolution for every beat, clockwise: at 120 beats per minute the notch comes round 120 times a minute.
8. **Rate of change of the tempo (innermost circle).** It rotates at `(tempo of this peak - tempo of the previous peak) / (seconds between those two peaks)`. A tempo that speeds up gives a positive rate (**clockwise**), one that slows down a negative rate (**counterclockwise**), and a steady tempo a circle that stands still.

A steady, strongly rhythmic sound therefore shows eight circles whose notches (apart from the four rate circles, which stand still) come round together at the same speed; a sound that speeds up and slows down shows the rate circles swinging both ways and the aggregated tempos holding on to the faster beat while the innermost level follows every peak. **The only settings are the minimum distance and the prominence of the local peaks** (the Local peaks settings of the other types, with the same ranges and defaults), besides the colormap and the settings every image type has (frame size, frame rate, window settings).

**The measurements in detail** (in time order, from the peaks of the whole file; the "samples" are the local peaks, and the "periods" the intervals between them):

- The **tempo at a moment** is the rate of the **latest peak at or before it** (a step that changes at every peak): 60 beats per minute before the first peak and for the first peak, which has no predecessor.
- The **rate of change** of a quantity (the tempo and its aggregated tempos of 2, 4 and 8 periods) at a peak is 0 for the first peak and for any peak without a previous one: `(value at this peak - value at the previous peak) / (seconds between the two peaks)`.
- The **aggregated tempos** are, for the latest 2, 4 or 8 peaks (or the peaks there are, while there are fewer), the average or the fastest (highest) of their tempos, whichever is closer to the tempo of the current peak (the fastest when equally close).
- All eight speeds are **constant between two peaks and change at each peak**, so a circle turns smoothly and the angle of every circle is the running total of its speed over time (the notch does not jump when the speed changes).

**Decided by the user, 2026-11-11**: **every circle has a notch of 1/8 of the circle** (45 degrees), a clear notch that reads on the thin inner rings too.

**Decided by the user, 2026-11-11**: **each circle has its own color from the colormap and its notch is the color at the opposite end of the colormap from it**. With eight circles from the outer (1) to the innermost (8), circle `k` takes the colormap at position `p = (k - 1) / 7` (the start for the outer circle, the aggregated tempo of 8, the end for the rate of change of the tempo in the middle) and its notch the colormap at `1 - p`, so the notch always contrasts with its circle and the eight circles are told apart by color.

**Decided by the user, 2026-11-11**: the rates of change are taken **per second** and turn their circles at that many **revolutions per minute**: a tempo that gains 6 beats per minute in a second turns its circle 6 times a minute (slowly and subtly, while the tempo circles turn at around 100 revolutions per minute).

**Why this priority**: It is the whole request.

**Independent Test**: Make a file of clicks at a steady 120 beats per minute: after the first peaks the tempo circle and the three aggregated-tempo circles turn at 120 revolutions per minute (a quarter of a turn every eighth of a second), the four rate circles stand still. Make a file whose clicks speed up: the rate circle of the tempo (the innermost) turns clockwise while it speeds up and counterclockwise when it slows down.

**Acceptance Scenarios**:

1. **Given** peaks that come every 0.5 s (120 beats per minute), **When** the frames are made, **Then** the notch of the tempo circle advances 720 degrees a second clockwise (24 degrees a frame at 30 frames a second), and so do the three aggregated-tempo circles.
2. **Given** a tempo that changes from `a` to `b` beats per minute between two peaks that are `s` seconds apart, **When** the frames after the second peak are made, **Then** the rate circle of the tempo (the innermost) turns at `(b - a) / s` (clockwise for a positive number, counterclockwise for a negative one, at the scale settled above).
3. **Given** the peaks of a file, **When** a frame is made, **Then** the first, third and fifth circles turn at the average or the fastest of the tempos of the latest 8, 4 and 2 peaks (of all the peaks there are, while there are fewer), whichever is closer to the current tempo: a tempo that is the fastest of its window is its own aggregate; a tempo that has fallen from a faster one is followed by the average of the window; a peak at twice the beat among peaks at the beat is its own aggregate and then fades into the averages until it leaves the window.
4. **Given** the aggregated tempo of the latest 8 (4 or 2) peaks changing from `a` to `b` between two peaks `s` seconds apart, **When** the frames after the second peak are made, **Then** the second (fourth or sixth) circle turns at `(b - a) / s`, clockwise for a positive number and counterclockwise for a negative one; it stands still while the aggregated tempo does not change.
5. **Given** a speed that changes at a peak, **When** the frames on both sides of the peak are made, **Then** the angle of the circle is continuous (the notch does not jump), only the speed changes.
6. **Given** a file with no peak, **When** the frames are made, **Then** the tempo and its three aggregated tempos turn at 60 beats per minute and the four rate circles stand still.
7. **Given** the same file and settings, **When** it is made twice, **Then** the images are identical.

---

### User Story 2 - The picture is chosen, set and exported like the other types (Priority: P2)

Rhythm Circles is chosen from the image type setting, with the label **Rhythm Circles**. Its group on the page has **no control of its own** and shows the **Local peaks** settings, **Minimum distance** and **Prominence** (as Decay Exp and Chromatic Decay do, without the checkbox), besides the Analysis group and the Colormap; the settings that have no meaning for it (Data smoothing, Threshold, Notes, Oversampling, Interpolate, Gaussian smoothing, Note layout and the settings of the other types) are **accepted by the request, checked as for every type, and ignored**, and are not shown. The frames have the usual size, count, names and timing, and can be made into a movie (feature 029). The other image types are not changed, and the request and the response have **no new field**.

**Why this priority**: It is the frame around the picture and the settings the user named.

**Independent Test**: Choose Rhythm Circles on the page: only Analysis, Colormap, Image type and Local peaks are shown; change Minimum distance and the circles turn at the rates of the new beat; make a movie.

**Acceptance Scenarios**:

1. **Given** the image type setting, **When** the user opens it, **Then** Rhythm Circles is among the choices and, when chosen, the page shows the Analysis, Colormap, Image type and Local peaks (Minimum distance and Prominence) groups and nothing else.
2. **Given** a Minimum distance or Prominence that is not allowed, **When** it is sent, **Then** it is refused as for every type.
3. **Given** the other image types, **When** frames are made, **Then** they are exactly what they were before this feature.

---

### Edge Cases

- A file with no peaks, or only one: every circle turns as the defaults say (60 beats per minute, rates of change 0); nothing fails.
- Two peaks: the tempo has changed once (the second peak's rate against the first's default of 60), so the rate circle turns for the period after the second peak; the aggregated tempos of 2, 4 and 8 at that peak are those of the two peaks there are.
- A very large rate of change (peaks that suddenly come much closer): the circle turns very fast; the angle is kept as a total of turns and drawn modulo one turn, so it never overflows.
- The frames between two peaks have the same speed for every circle; the first frames of the file (before the first peak) have the default tempo.
- A frame size other than the usual one scales the circles with the picture.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST offer a new image type, **Rhythm Circles** (`rhythm-circles`), chosen the same way as the other types, producing one picture per frame of **eight concentric notched circles**, centered in the picture, from the outer circle to the innermost: the fastest tempo of the latest 8 periods and its rate of change, the same for 4 and for 2 periods, and the tempo and its rate of change (the longest aggregation outermost).
- **FR-002**: Every circle MUST be one color with a **notch** of a contrasting color whose width is a sixteenth to an eighth of the circle (settled above), and MUST rotate, the notch showing the rotation.
- **FR-003**: The **tempo** MUST be the rate of the latest local peak at or before the frame's moment, in beats per minute (60 before the first peak and for the first peak), and the seventh circle MUST rotate **clockwise** at that many revolutions per minute.
- **FR-004**: The eighth circle MUST rotate at `(tempo of a peak - tempo of the previous peak) / (seconds between them)` (0 until there are two peaks), positive clockwise and negative counterclockwise, at the scale settled above.
- **FR-005**: The first, third and fifth circles MUST rotate clockwise at the aggregated tempo of the latest 8, 4 and 2 peaks (of those that exist, when there are fewer): the **average** or the **fastest** (the highest rate, the shortest interval between peaks) of the tempos of the window, whichever is **closer to the current tempo** (the fastest when they are equally close); in revolutions per minute equal to beats per minute.
- **FR-006**: The second, fourth and sixth circles MUST rotate at the rate of change of the 8-peak, 4-peak and 2-peak aggregated tempo, `(aggregated tempo at a peak - aggregated tempo at the previous peak) / (seconds between them)` (0 until there are two peaks), positive clockwise and negative counterclockwise, at the same scale as the eighth circle.
- **FR-007**: Every speed MUST be constant between two peaks and change at each peak, and the angle of every circle MUST be the continuous running total of its speed over time (from the start of the file), so that the notch never jumps.
- **FR-008**: The peaks MUST be those of the Local peaks measurement with the **Minimum distance** and **Prominence** of the request (the existing settings, ranges, defaults and messages); no other setting is used by the picture, and none is added to the request or the response.
- **FR-009**: The settings that have no meaning for this type MUST be accepted, checked as for every type and ignored; the page MUST show only the Analysis, Colormap, Image type and Local peaks groups.
- **FR-010**: Results MUST be repeatable: the same file and settings MUST give identical images; the frames MUST be usable for making a movie (feature 029); the other image types MUST NOT change.

### Key Entities

- **Peak**: a local maximum of the energy of the sound, with its time and its rate (beats per minute, from the time since the previous peak).
- **Tempo**: the rate of the latest peak, in beats per minute.
- **Rate of change**: the difference of a quantity (the tempo or one of its aggregated tempos) at two consecutive peaks divided by the time between them.
- **Circle**: one of the eight rings, with a color, a notch and an angle that is the running total of its speed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For clicks at a steady tempo `T` beats per minute, the notches of the tempo circle and of the three aggregated-tempo circles advance `T x 360 / 60` degrees a second (within one degree over ten seconds), clockwise, and the four rate circles do not move.
- **SC-002**: For a tempo that changes between two peaks, the speed of each of the four rate circles equals the change of its quantity divided by the time between the peaks, with the sign of the change (clockwise for speeding up), for every peak of a hand-made set of peaks.
- **SC-003**: The angle of every circle is continuous across a peak (the difference between two consecutive frames is the speed times the frame time, with no jump), on a hand-made set of peaks.
- **SC-004**: The frames of every other image type, and the request and response fields, are identical to what they were before this feature; the same file and settings give identical images.
- **SC-005**: A user can tell from the picture alone, without a setting, whether a section is steady (the notches of the tempo and its aggregated tempos turn together and the rate circles are still) or not (the rate circles swing and the aggregated tempos differ from the tempo circle).

## Assumptions

- **The "samples" are the local peaks and the "periods" the intervals between them**: the Local peaks measurement already gives each peak its rate in beats per minute (60 times the sample rate over the samples since the previous peak, 60 for the first), and the rate at any moment is that of the latest peak at or before it. "The time between the samples" is the time between the peaks.
- **"At the tempo rate, in beats per minute"** is read as **one revolution per beat**: a tempo of `T` beats per minute is `T` revolutions per minute, so the notch passes any fixed point once for every beat. The averages use the same reading.
- The four **rate circles** turn at the rate of change in beats per minute **per second** taken as **revolutions per minute**, as settled above; positive is clockwise.
- The eight circles are **rings of equal width** filling a circle in the middle of the picture (not stacked discs), separated by a thin gap, on the colormap's middle color, the outer circle being the largest.
- Before the first peak (and for a file with none) the tempo and its aggregated tempos are the default of the measurement, 60 beats per minute; the rates of change are 0.
- The **angle** of a circle is the integral of its speed from the start of the file, measured at the middle of each frame, drawn modulo one turn; the first frames start with the notch at the top.
- The picture is drawn from the local peaks only; **the note analysis, smoothing, thresholds and layouts are not used** (they are accepted and ignored like the other settings that a type does not use).
- The moments are those of the frames (the middle of each frame, as the other types use for the beat).
