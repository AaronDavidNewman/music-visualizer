# Feature Specification: Energy Graphs

**Feature Branch**: `034-energy-graphs` (no git branch created; spec directory name only)

**Created**: 2026-11-08

**Status**: Draft

**Revised 2026-11-08 (first change)**: the user decided that **the two pies do not tell anything**, and they are **removed**: there is no harmonic against non-harmonic pie and no loudness pie, and with them the measurement of the rest of the spectrum that only they needed. The **histogram gets a second data set, the amplitude of each note**, accumulated as **quasi-decibels** (`20 log10(amp) / (20 log10(max))`, `max` being the largest amplitude of any bin), added to the note's amplitude total in every window. To put the frequency data set and the amplitude data set **on the same scale**, the graph does not draw the totals but the **softmax** of each. The histogram now fills the whole picture. Two readings were settled with the user: each data set is **divided by its own largest total before the softmax** (a softmax of the raw totals, which are in the thousands, is one single bar), and a contribution under 0 is **clamped to 0**. The original text about the pies is not kept below.

**Revised 2026-11-08 (second change)**: after the softmax the user found it **very hard to see the clear winners**, and asked that **the histogram start the smallest value at height 0**. Each data set now has its **smallest softmax share taken off every one of its shares** (so its smallest bar has height 0, and a note that has never sounded has no bar), and the bars are scaled by the largest remaining value of the frame, as before. Wherever the text below says that a softmax is never 0, or that a note that has never sounded still has a low bar, this replaces it.

**Input**: User description: "create an image type with a few different graphs that update throughout the file.  1: A histogram for each bin, that accumulates throuought the file.  This is done by simply sorting the bin levels, adding to that bin's index each time based on rank.  So loudest harmonic is 84, second 83, etc.  The histogram can changes scale so that the height of the highest bar is always the same.  2) a pie graph that shows the harmonic energy vs. non-harmonic energy.  This can be done by comparing the amplitudess for the 84 note bins to the rest of the bins (sum or RMS).  This is instaneous per window, not cumulative.  3)  Pie graph showing relative loudness vs. the loudest part of the file, for the current window, using RMS."

Then (2026-11-08): "I've changed my mind about the pie graphs, they don't tell us anything.  We can remove those from energy_graphs.py.  For the histogram, I'd like to add the amplitude for each frequency as a second data set.  For this, we should accumulate by the quasi-db:  20*log10(amp)/20*log10(max) where max is the max amplitude of any bin.  This is added to each amplitude bin on each window.  To get the frequency bin and the amplitued bin on the same scale, we can compute the softmax of each for the actual graph rather than graphing the totals directly."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A histogram of which notes have been loudest, by rank and by amplitude (Priority: P1)

The user wants a new image type, **Energy Graphs** (request value `energy-graphs`), whose every frame is a **running histogram of the 84 notes with two data sets**.

- **One pair of bars for each of the 84 notes**, in order of pitch from left to right (the lowest note, A1, on the left): the **frequency bar** and, next to it, the **amplitude bar**.
- **Frequency data set (rank points)**: in every analysis window the 84 notes are **ranked by strength** and each note **adds its rank score to its own total**: the loudest note of the window adds **84**, the second loudest **83**, the third **82**, and so on down to the faintest, which adds **1**. A note that is silent in the window (strength 0, for instance because it is under the noise floor of feature 033) adds **nothing**, and neither do the notes ranked below it.
- **Amplitude data set (quasi-decibels)**: in every window each note **adds `20 log10(amp) / (20 log10(max))` to its own amplitude total**, `amp` being the note's amplitude in the window and `max` the **largest amplitude of any note in any window of the file**. The loudest note of the file therefore adds 1 and a fainter note less, down to 0. A silent note adds nothing. A result under 0 (an amplitude under 1) is **clamped to 0**, and a file whose loudest amplitude is 1 or less (where the ratio of logarithms is meaningless) adds nothing at all.
- **Both accumulate**: the totals **keep what they have collected** from the start of the file up to the frame being drawn, so the first frame is built from the first window only and the last frame from the whole file. They never reset and never shrink.
- **The totals are not drawn as they are.** A total grows with the length of the file and the two data sets have different sizes (a rank total can be 84 times the number of windows, an amplitude total at most the number of windows). Each data set is **divided by its own largest total** (so it runs from 0 to 1) and then **softmaxed over the 84 notes** (`exp(x) / sum of exp(x)`), which puts the two on **the same scale**, each adding up to 1.
- **The smallest value has height 0**: a softmax is never 0 and its values are close to each other, so the clear winners would hardly show. The **smallest share of each data set is subtracted from all the shares of that data set**, so that its smallest bar has height 0 (and the bars that stand out are the ones that are really above the rest).
- **The scale follows the data**: the bars (the shares above the smallest) are scaled by the largest of them in the frame, over both data sets, so that **the tallest bar of the picture is always the same height**.
- **Color**: the frequency bars take the **start** color of the colormap and the amplitude bars its **end** color; a legend says which is which.

**Why this priority**: It is the whole graph. The frequency data set tells *how often* a note has been among the loudest, the amplitude data set *how loud* it has been, which a rank cannot tell (a faint second note scores 83 just as a loud one does).

**Independent Test**: Make a file in which note A3 is always the loudest and note E4 always the second loudest but ten times fainter. Create Energy Graphs frames: the frequency bars of A3 and E4 are nearly as tall as each other (their totals are in the proportion 84 : 83), but the amplitude bar of E4 is clearly shorter than that of A3; the tallest bar touches the top of the graph in the first frame and in the last; the bars of the last frame are the softmax of the totals of all the windows, which can be worked out by hand.

**Acceptance Scenarios**:

1. **Given** a window in which note `a` is the loudest, `b` the second loudest and `c` the third, **When** the totals are accumulated, **Then** the frequency totals receive 84 for `a`, 83 for `b`, 82 for `c`, and so on by rank, and 0 for every silent note.
2. **Given** a note of amplitude `amp` in a file whose largest amplitude is `max` (both above 1), **When** the totals are accumulated, **Then** its amplitude total receives `20 log10(amp) / (20 log10(max))` in every window in which it has that amplitude: 1 for the loudest note of the file.
3. **Given** a note with amplitude under 1, a silent note, or a file whose largest amplitude is 1 or less, **When** the totals are accumulated, **Then** the contribution is 0 (never negative).
4. **Given** any frame, **When** it is drawn, **Then** the tallest bar of the picture reaches the same height, whatever the file and however many windows were counted, and multiplying all the totals by a constant changes nothing in the picture.
5. **Given** a frame before the first sound, **When** it is drawn, **Then** there are no bars (not a division by zero), and a data set that has no total yet (the amplitude of a file that is never above 1) has no bars while the other is drawn.
6. **Given** a data set, **When** a frame is drawn, **Then** its smallest value has height 0, so a note that has never sounded (when others have) has no bar, and a data set whose totals are all equal (nothing above the smallest) has no bars.
7. **Given** the same file and settings, **When** it is made twice, **Then** the images are identical.

---

### User Story 2 - The picture, the type and the page (Priority: P2)

The histogram is **the whole picture**, a frame of the usual frame size of the other image types: a title ("Notes so far (softmax of the totals)"), a **legend** that names the two data sets and their colors, the pairs of bars standing on a baseline, and the octave labels (A1 to A7) under it. The picture is made, listed and chosen like the other image types: it appears in the image type setting, it takes the **colormap** and the frame size and frame settings the same way the other pictures do, and it can be made into a movie (feature 029). It has **no setting of its own**.

**Why this priority**: It is the frame around the graph; the graph is worth the same with any reasonable layout.

**Independent Test**: Choose Energy graphs in the image type setting, make frames of a short file and see the pairs of bars under a title and a legend, in the colormap chosen, with no further control on the page; make the movie of it.

**Acceptance Scenarios**:

1. **Given** the image type setting, **When** the user opens it, **Then** Energy graphs is among the choices and, when chosen, the frames contain the histogram and no setting of its own appears.
2. **Given** a colormap, **When** the frames are made, **Then** the colors of the bars come from it.
3. **Given** the setting that makes a movie from the frames, **When** the type is Energy graphs, **Then** the movie is made like for the other types.

---

### Edge Cases

- A file shorter than one analysis window, or with a single window: there is one frame and the totals are made from that window; nothing fails.
- Ties in strength (two notes with the same strength): they are ranked in the order of their pitch, lowest first, so the result is the same every time.
- Fewer than 84 notes sounding in a window: only the sounding notes get a rank score, starting at 84 for the loudest, not renumbered from the number of notes sounding.
- A file with no sound at all: both totals are 0 and nothing is drawn but the title, the legend, the baseline and the labels; the pictures are still made.
- A quiet file whose loudest amplitude is 1 or less: the frequency data set is drawn, the amplitude data set has no bars.
- A frame between two analysis windows (the frames of the other types are averages or interpolations of windows): the histogram accumulates the windows that start up to the end of the frame, so a window is counted once and a file made at two frame rates gives the same totals at the end.
- Very loud or very quiet files: the scales follow the data (the largest total, the tallest bar), so the files look alike regardless of their absolute level; only the quasi-decibel value depends on the absolute amplitude, through the 1 under which it is clamped.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST offer a new image type, **Energy Graphs** (`energy-graphs`), chosen the same way as the other types, producing one picture per frame with the histogram.
- **FR-002**: The histogram MUST have 84 notes, one pair of bars each (the frequency bar, then the amplitude bar), in order of pitch from the lowest note on the left.
- **FR-003**: In every window the notes MUST be ranked by strength, and each sounding note MUST add to its frequency total the score 84 for the loudest, 83 for the second loudest and so on by rank; a silent note MUST add nothing.
- **FR-004**: In every window each sounding note MUST add `20 log10(amp) / (20 log10(max))` to its amplitude total, `max` being the largest amplitude of any of the 84 notes in any window of the whole file; a negative result MUST be 0, a silent note MUST add 0, and a file whose `max` is 1 or less MUST add nothing.
- **FR-005**: The totals of a frame MUST accumulate the contributions of **all windows from the start of the file up to that frame**, each window once, and MUST NOT reset.
- **FR-006**: Notes of equal strength MUST be ranked by pitch, lowest first, so that the result is repeatable.
- **FR-007**: The graph MUST NOT draw the totals: each data set MUST be divided by its own largest total and then softmaxed over the 84 notes, so that the two are on the same scale, and the smallest share of each data set MUST then be subtracted from all its shares (its smallest bar has height 0); a data set with no total, or with all totals equal, MUST have no bars.
- **FR-008**: The bars MUST be scaled by the largest of the shares above the smallest, over both data sets, so that the tallest bar is always drawn at the same height; an empty graph MUST be drawn without error.
- **FR-009**: The frequency bars MUST be in the start color of the colormap and the amplitude bars in its end color, and a legend MUST say which is which.
- **FR-010**: The histogram MUST fill the picture of the usual frame size, with a title, the legend, a baseline and the octave labels.
- **FR-011**: The picture MUST use the chosen colormap and MUST honour the settings that apply to every image type (frame size, frame count and the like), as the existing pictures do; the type has no setting of its own.
- **FR-012**: The note strengths used MUST be those after the noise floor (feature 033), so that a note under the floor is silent for the ranking and for the amplitude.
- **FR-013**: Results MUST be repeatable: the same file and settings MUST give identical images.
- **FR-014**: The frames of this type MUST be usable for making a movie (feature 029) as the frames of the other types are.

### Key Entities

- **Rank score**: the points a note gets in a window, from 84 for the loudest to 1 for the faintest sounding one, 0 for silence.
- **Quasi-decibel value**: `20 log10(amp) / (20 log10(max))`, clamped at 0, the amount a note adds to its amplitude total in a window.
- **Frequency total / amplitude total**: for each of the 84 notes, the sum of its rank scores / of its quasi-decibel values over all windows from the start of the file to the current one.
- **Softmax share**: a data set's totals divided by its largest total and softmaxed over the 84 notes, minus the smallest of those shares; what is drawn.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a file where one note is the loudest in every window, 100% of frames show that note as the tallest bar, and the tallest bar has the same height in 100% of the frames of any file that has a sound.
- **SC-002**: The totals of the last frame of a file equal the sum of the rank scores and of the quasi-decibel values of all its windows (checked on a small file by hand, for every one of the 84 notes and both data sets), and the bars are the softmax of those totals to within one pixel.
- **SC-003**: Multiplying all the totals by a constant, or making the same file at another frame rate, gives the same bars (at the end of the file, for the frame rate).
- **SC-004**: The same file and settings give images that are identical, and a silent file gives pictures without any failure.
- **SC-005**: A user can choose Energy Graphs and make frames and a movie of a three-minute file with no step beyond choosing the type, in about the time Tiles needs plus the drawing.
- **SC-006**: A first-time viewer can say what the two colors of bars mean from the picture and its legend alone.

## Assumptions

- The **84 notes** are the 7 octaves from A1 (55 Hz) that the other pictures use as "the notes"; the 4 further analysis columns are not notes of the histogram, and the `max` of the quasi-decibel is taken over the 84 notes only (so the value of a note never exceeds 1).
- "Rank by loudness" is on the **note strength after the noise floor**, with ties in order of pitch; silent notes score nothing, as the 84-for-the-loudest rule says nothing about them and the noise floor already defines silence. For the amplitude data set, "the amplitude of a bin" is the same note strength.
- **Settled with the user (2026-11-08)**: each data set is divided by its own largest total before the softmax (the softmax of the raw totals is one single bar, because the totals are in the thousands); a quasi-decibel value under 0 is clamped to 0. The consequence: with the divided totals the softmax sees values from 0 to 1, so **the contrast is low** (a note that has never sounded would have a bar of `1/e`, about 37 percent, of the tallest when only one note has sounded); that is why the second change takes the smallest share off every share of a data set. The smallest value is taken **per data set** (each histogram has its own zero) and not over both, which is a reading of "the smallest value" that is easy to change.
- `max` is the largest amplitude of the **whole file**, not of the frames so far, so that a window's contribution does not depend on the frame number; it makes the amplitude totals depend on the absolute level of the analysis (a file that is never above 1 adds nothing), which is the formula the user gave.
- The graph is **relative**: it does not show how many windows have been counted.
- A **frame** is made from the analysis windows in the same way as for the other image types; how windows are spaced and frames interpolated (features 003 and 018) is not changed.
- The layout (the pair of thin bars, the title and legend above, the octave labels below, the two data sets in the two ends of the colormap) is the author's choice, the user having asked only for the two data sets and the softmax; it can change without changing what the graph means.
- This feature adds an image type only; the analysis, the noise floor and the other pictures are unchanged. (The first version of the type measured the rest of the spectrum of every window for its pies; that measurement was removed with them.)
