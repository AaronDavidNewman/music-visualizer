# Research: Energy Graphs

No `NEEDS CLARIFICATION` remains (the one question of the specification, the source of the non-harmonic energy, was answered on 2026-11-08: the full spectrum). The decisions below settle what the specification left to the design.

**Revised 2026-11-08**: Decisions 1, 2, 5 and the pie parts of 6, 7 and 8 are **withdrawn** (the pies and the rest of the spectrum are gone). Decisions 3, 4 and 9 stand (3 now also for the amplitude totals). New decisions:

- **R1. Quasi-decibel**: `20 log10(a) / (20 log10(peak))` with `peak` the largest of the 84 notes in any window of the file, clamped at 0, 0 for silence and for a file with `peak <= 1` (the user chose the clamp; with negatives kept, the ratio would be undefined for `peak = 1` and upside down below it). `peak` over the 84 notes only, so a value never exceeds 1. Alternative: the real dB relative to the peak, `20 log10(a / peak)` (always <= 0, scale free): not what the user wrote.
- **R2. Softmax on the same scale**: the user asked for a softmax of each data set. On sonata.wav a softmax of the raw totals is one single bar for both (totals up to 130,000 and 889), and of totals / windows it is one bar for the rank totals (about 5 bars above 1 percent) and flat for the amplitude. The user chose **totals / their own largest total, then softmax**: both on the same scale, both with a real shape, low contrast (a note that never sounded is `1/e`, about 37 percent, of the tallest when one note has sounded). Alternatives offered: a temperature (more contrast, one more number to choose), plain shares (full contrast, no softmax).
- **R3. Display scale**: the bars are scaled by the largest share of both data sets, so the two stay comparable and the tallest bar is the full height; the totals are unrelated to the picture's scale (multiplying them changes nothing).
- **R5. The smallest value at 0 (second change)**: the softmax of the divided totals sees values from 0 to 1, so its shares differ by at most a factor `e` and the winners hardly show. The user asked that the smallest value start at height 0: the smallest share of each data set is subtracted from its shares (`above_smallest`), then the common scale is the largest remaining value of both. Per data set rather than over both, so that each histogram has its own zero; with one common minimum the data set with the larger spread would keep a visible floor. A data set of equal totals (or one that never sounded) has nothing above its smallest and has no bars. Effect: with one note sounding the bar is the only one; with two, the heights are in the proportion `e^x - 1`.
- **R4. Layout**: with the pies gone the histogram fills the picture: the 84 slots hold a pair of thin bars (frequency in the start color of the colormap, amplitude in its end color, as the notes and the chord of Polar Chords), a legend at the right of the title row, and at least one pixel of background between two notes.

## Decision 1: The non-harmonic energy is measured in the note analysis, from the transform it already makes

- **Decision**: `analyze_channels` gets a keyword `rest: bool = False`. With it, `AnalysisResult.rest_rms` (a `(windows,)` array) holds, for every window, the RMS of the magnitude spectrum `(|L| + |R|) / 2` (the same average the note values read) over **every position of the real spectrum except position 0 (the constant offset) and the distinct positions the 84 notes read**. Computed as `sqrt(sum(mag² · w) / sum(w))` with `w` a 0/1 vector (1 for a position of the rest); with no position left (a tiny window whose every position is a note position) the RMS is 0.
- **Rationale**: the transform of the window is already done for the notes; only the squared magnitude and a matrix-vector product are added (cheap against the transform: SC-005 asks for at most double). Doing it in the analysis keeps the chunked, bounded-memory loop of `analyze_channels` (the spectrum of a whole file is never held). A weight vector avoids the cancellation of "total minus notes".
- **Alternatives considered**: keeping the whole spectrum per window (`windows x window_size/2` floats: gigabytes for long files); a second pass over the audio (twice the transform for the notes too, and a second loop to keep in step); measuring it in the frame renderer (the audio is not there).
- **Detail**: several low notes can read the same position at a small window size; the 84 notes are counted as the **distinct** positions they read (`np.unique` of `bin_indices[:84]`). The 4 extra analysis notes (columns 84 to 87) are **not** notes of this type: their positions belong to the rest (the spec's Assumptions).

## Decision 2: The harmonic energy is the RMS of the 84 note values after the noise floor

- **Decision**: `H` = `sqrt(mean(values[:, :84] ** 2))` of the floored note values of each window; `R` = `rest_rms`, raw (the noise floor does not apply to it, spec Assumptions).
- **Rationale**: FR-012 (floored notes for the ranking, the energies and the loudness); both sides are magnitudes of the same averaged spectrum, so they are comparable; RMS on both sides is the user's "sum or RMS" choice resolved to RMS because the sides have 84 and thousands of positions (a sum would make the notes always tiny).
- **Alternatives considered**: sum (rejected, as above); energy as mean power (the same ordering as RMS, but the loudness pie would then be a share of power, not of amplitude: the user said RMS).

## Decision 3: The histogram counts each window once, in the frame it starts in

- **Decision**: the rank scores of all windows are cumulated (`np.cumsum` over windows); frame `i` shows `running[stop_i]` with `stop_i` the number of windows that start before the end of frame `i` (the assignment of `average_frames`, shared). A window is therefore counted in exactly one frame; a frame with no window of its own adds nothing.
- **Rationale**: SC-002 (the last frame is the sum of the scores of all windows, checked by hand on a small file) and the spec's edge case (two frame rates give the same shape at the end). Repeating the last window for an empty frame (what the averaging does for the other types) would count a window twice.
- **Alternatives considered**: one score set per frame from the averaged note values (a different ranking than the one of the windows, and it makes the histogram depend on the frame rate).

## Decision 4: Rank scores

- **Decision**: per window, `np.argsort(-values[:, :84], axis=1, kind="stable")` (equal strengths: the lower note first, FR-006); the note of rank `r` (0 = loudest) scores `84 - r`; a note with strength 0 scores 0. Done in chunks of windows so that memory stays bounded (`max_windows` is 60,000: 60,000 x 84 x 8 bytes is 40 MB per index array, so a chunk of 4,096 windows).
- **Rationale**: the stable sort is what `polar_chords._targets` already relies on for ties; the scores are small integers (`int64` cumulative: the largest possible bar is 84 x 60,000 = 5.04 million).
- **Alternatives considered**: ranking after the averaging of frames (Decision 3); `np.lexsort` (the same result, slower).

## Decision 5: Frame quantities for the pies

- **Decision**: for each frame, `H²` and `R²` are the **mean of the squares** over the windows assigned to it (cumulative sums, as `average_frames`), or, for a frame with no window of its own, those of the last window before it (the first window if there is none). The harmonic share is `H / (H + R)` (NaN when `H + R == 0`); the loudness share is `min(1, H / H_ref)` with `H_ref` the largest single-window `H` of the file (NaN when `H_ref == 0`).
- **Rationale**: the RMS of a group of windows is the root of their mean square; the loudest window of the file is the reference, as the user said, so the loudest window's frame is a full circle when that window is alone in its frame, and never above one otherwise.
- **Alternatives considered**: averaging amplitudes (not an RMS); taking the first window of each frame only (loses the others at small window spacing).

## Decision 6: Layout of the 600 x 400 picture

- **Decision** (pixels): margin 10. **Top row**: two pies, centers at x = 155 and 445, radius 72, center y = 108; a title above each (y 10) and a legend under each (y 188: a colored square and the name of each slice). **Bottom**: a title (y 214) and the histogram: the plot area x 10 to 590 (580 px), y 236 to 376 (140 px), 84 bars at the nearest whole pixels of an even split with a 1-pixel gap, a baseline, and the octave labels A1 to A7 under every 12th bar (y 380). Titles: "Notes loudest so far", "Harmonic energy", "Loudness against the loudest moment".
- **Rationale**: it fills the usual frame, gives the histogram the whole width (84 bars of about 7 px) and the two pies each a square of about 150 px; every dimension is a constant of the module, nothing is computed from the data, so frames are comparable.
- **Alternatives considered**: pies side by side with the histogram on the right (bars would be 3 px); matplotlib figures (about 100 ms a frame: minutes for a three-minute file).

## Decision 7: Drawing with Pillow, a static background, supersampled pies

- **Decision**: the background (the colormap's middle color, titles, legends, baseline, octave labels, the outlines of the empty pies) is drawn once and copied per frame; the bars are rectangles; each pie is drawn at 4x on a small square and reduced with `Image.LANCZOS`, so its edges are smooth (the other types smooth their edges too). Text is `ImageFont.load_default(size=13)`; its color is black or white by the luminance of the middle color. Frames are written in the thread pool of `circles._SAVE_WORKERS`, `compress_level=1`, like polar.
- **Rationale**: no per-frame matplotlib; deterministic (the same Pillow, the same bytes); the pies are the only antialiasing-sensitive shapes.
- **Alternatives considered**: numpy coverage masks like polar's arcs (more code for two circles); no antialiasing (jagged pies).

## Decision 8: Colors

- **Decision**: the **histogram bars** run from the middle of the colormap (a short bar) to its end (the tallest), by the bar's height as a share of the tallest bar (`row = round((0.5 + 0.5 * share) * 255)`); the **pie slices**: the share the pie is about (harmonic; the current loudness) in the **end** color of the colormap, the remainder in the **start** color; an empty pie is an outline in the text color.
- **Rationale**: the same rule as Polar Chords (a faint element close to the background; a colormap with two different ends, such as Cool Warm, shows it best), so the types look related; the two slices take the two extremes so they always differ.
- **Alternatives considered**: bars over the whole table (the middle bars would vanish into the background); a fixed neutral palette (ignores the colormap setting, which the spec says the graphs use).

## Decision 9: Wiring and what is not used

- **Decision**: `write_frames` gets the keyword `energy` (the `EnergyGraphData`, `None` by default); for `energy-graphs` it must be given (else `ValueError`), its frame count must equal the frames given, and every other setting (smoothing, threshold, resolution, note count, layout, circles, decay, polar notes, beat) is checked as for the other types and **ignored**. The job asks the analysis for the rest only for this type, does not measure the beat for it, and adds **no** request or response field. In the frontend the type has no group of its own and the Data smoothing group is not shown (the data is not smoothed); Image smoothing is not shown either (`gridSettingsApply` already false for non-grid types, extended).
- **Rationale**: the same shape as the other nine types (feature 032): the settings that do not apply are accepted and ignored, so old clients and scripts keep working; no new field means no new validation message.
- **Alternatives considered**: a separate `write_energy_frames` call in the job outside `write_frames` (skips the shared checking and the one place that knows every type); smoothing the histogram increments (the user asked for a plain accumulation).

## Open questions

None.
