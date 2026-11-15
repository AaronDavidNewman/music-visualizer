# Research: Local Tempo Finder

No `NEEDS CLARIFICATION` remains in the spec; the questions below are about making the rule exact and about what it does on the two real files.

## D1. The rule, made exact

**Decision**: Process the peaks in time order; the first peak gives no sample (the tempo stays 120). For each later peak `i`:

1. `s = 60 / (time[i] - time[i-1])` (the sample, beats per minute).
2. Match: among the multipliers `RATIOS = (1, 2, 1.5)` (the tempo, its half, its two thirds: a sample near `T/2` stands for `2 s`, one near `T/1.5` for `1.5 s`), choose the one whose value `s * ratio` is nearest to `T` **in ratio** (`|ln(s * ratio / T)|`), the plain tempo on a tie; `s` becomes `s * ratio`.
3. Append `s` to the window of the latest **5** samples (after a restart the window is empty); `mean` and `sd` are the mean and the **population** standard deviation of the window; `sd = max(sd, 1)` (the minimum step the user chose).
4. If `|s - T| <= sd`: `T = (s + mean) / 2`. Otherwise `T += sign(s - T) * min(sd, |s - T|)` (never past the sample).
5. If `T > 156`: `T = 78`, empty the window. If `T < 60`: `T = 120`, empty the window.

The tempo after each peak is the **current tempo** from that peak until the next; its half and its two thirds are `T / 2` and `T / 1.5`.

**Rationale**: It is the user's description, with the three gaps filled by the choices in the spec's Assumptions (population standard deviation, inclusive "within", moving toward the sample and not beyond it, 78 exactly).

**Alternatives considered**: Matching by absolute difference (|s·r − T|): for T = 120 the same candidates win in almost every case, but ratio is symmetric in the octave sense (60 and 240 are equally far from 120) and the spec's edge case already says "nearest in ratio". Using the window **before** adding the sample for the deviation: with an empty window after a restart there would be no deviation at all; adding first gives one sample and the minimum step.

## D2. What the rule does on real music (prototype, 2026-11-14)

I ran the rule above on the peaks measured with Minimum distance 350 ms and Prominence 20% (`scratchpad/tempo_proto.py`, `tempo_variants.py`):

| File | Peaks | Peak tempos (10/50/90th percentile, bpm) | Restarts | Share of time (after 10 s) within 10% of the target |
|---|---|---|---|---|
| sonata.wav (116 bpm, groups of 3) | 393 | 96 / 135 / 168 | 40 | **22%** near 116 |
| almost2.wav (about 180 bpm, groups of 4) | 293 | 81 / 123 / 167 | 22 | **7%** near 90 |

Steady peaks behave as intended where the ratios allow it: steady 100, 116 settle exactly on themselves, also when only every second peak is present (50, 58); 70 settles at **105** (70 is two thirds of 105, and the rule cannot tell them apart), 150 settles at 150, and 150 with every second peak (75) settles at 112.5 (75 is two thirds of it).

**Why the real files fail**: the histogram of the peak tempos of sonata.wav is 4 below 65, 45 from 65 to 100, 126 from 100 to 130, 131 from 130 to 160 and 86 from 160 to 200: **more than half of the peaks (217 of 392) are faster than 130 beats per minute, above the 116 the user expects**. A sample at 168 against a tempo of 116 is 1.45 times the tempo, but the rule only takes a sample as `T`, `T/2` or `T/1.5`, never as `1.5 T` or `2 T`, so it is "far from all three" and moves the tempo up by one standard deviation; a few of those reach 156 and the tempo restarts at 78. Nothing in the rule is wrong in itself; it was written for samples at or below the tempo (peaks of groups, tied notes) and these files have a lot of fast ones.

**Variants tried** (not part of the plan, for the user to decide after seeing the picture):

| Variant | sonata: restarts / near 116 | almost2: restarts / near 90 |
|---|---|---|
| As written (ratios 1, 2, 1.5) | 40 / 22% | 22 / 7% |
| Also take a sample as `T/2` and `T/1.5` upward, i.e. ratios (1, 2, 1.5, 0.5, 2/3) | 2 / 27% | 1 / **49%** |
| Also ratios 3 and 4 | 2 / 29% | 2 / 48% |

**Update, 2026-11-14 (after seeing the result):** the user asked to "also consider faster tempos if they are more suitable", and the variant above (ratios 0.5 and 2/3 added) was adopted: `RATIOS = (1, 2, 1.5, 0.5, 2/3)`. Measured now: sonata.wav 2 restarts and 27%, almost2.wav 1 restart and 49%. The user also cut the circles from eight to four (the current tempo and the local peak, each with its rate of change; half and two thirds of the tempo dropped). **Second update, 2026-11-14:** the user noticed that steady peaks at 150 beats per minute settled at 100 (150 is 1.5 x 100) although nothing near 100 is ever heard: the nearest reading to the tempo of 120 won, which is path dependent (both 100 and 150 are fixed points). A **tolerance** was added: a sample stands for a related tempo only when within 15 percent of it (`HARMONIC_TOLERANCE = 0.15`), otherwise for itself. Measured (peaks at 350 ms / 20 percent): steady 150 now settles at 150, 155 at 155, 70 at 105, 50 at 75 (was 100); sonata.wav 4 restarts / 49 percent near 116 (was 2 / 27), almost2.wav 0 restarts / 35 percent near 90 (was 1 / 49). Other tolerances tried: 5 percent (26 and 8 restarts), 10 percent (15 and 3), 20 percent (150 goes to 100 again, 8 and 1). The text below is the decision as first made.

**Decision**: Build the rule as written. Put the ratios in one constant (`RATIOS`) so that the variant is a one-line change, and report the measurement of both files (restarts, share of time near the target, tempo every 10 seconds) in a test that asserts only what holds for any version of the rule (tempo always from 60 to 156, deterministic, restarts counted, the same result when run twice). The spec's real-file criteria (SC-004, SC-005) are therefore *measured and reported*. The decision about the variant is the user's, after seeing the circles.

**Alternatives considered**: Adopting the 5-ratio variant now: it reads the user's request differently (they described the three values explicitly) and the improvement for sonata.wav is small (27% against 22%), so it is not worth deciding for them. Gating the tests on the thresholds I first wrote (75% and 60%): they cannot pass with the rule as written, so the test would be red or the thresholds would be fitted to the data.

## D3. Where the peaks come from

**Decision**: `rhythm_angles` already turns a `LocalPeaks` into times (`sample / file_rate`) and tempos (`peak.rate`); the finder takes the **times** only and derives its own samples from the intervals, so it does not depend on `peak.rate` (whose first value is the default 60 and is not a sample). The innermost circle keeps using `peak.rate` exactly as now.

**Rationale**: One definition of a sample (60 over the interval) and a finder testable with a plain list of times.

## D4. The eight circles

**Decision**: From the outer circle (column 0, colormap position 0) to the innermost (column 7, position 1): tempo/1.5, its rate of change, tempo/2, its rate of change, the tempo, its rate of change, the local peak's tempo, its rate of change. The levels per peak are `T[i] / 1.5`, `T[i] / 2`, `T[i]` and `peak.rate[i]`; the rate of change of a level is `(x[i] - x[i-1]) / (time[i] - time[i-1])` (0 for the first peak), as now. Before the first peak (and with no peak) the speeds are the defaults: the local peak 60, the tempo layers 120, 60 and 80 (`DEFAULT_SPEEDS`), all rates 0. A restart makes a one-interval spike in the rate of change of the three tempo circles (for example 156 to 78 over 0.4 s turns the circle at about -195 revolutions per minute for that interval); that is what "rate of change of the current tempo" means and it is kept.

**Rationale**: The user listed the layers from the inside out: peak, tempo, tempo/2, tempo/1.5, each with its rate; the picture code already assumes eight circles, a level before its rate, and the colormap spread `(k-1)/7`, so only the series changes.

**Alternatives considered**: Putting the rates of the tempo layers on separate rings from their levels (the previous layout already pairs them); keeping the old aggregate circles (the user said to replace them).

## D5. Prominence and Minimum distance

**Decision**: `local_peaks.DEFAULT_MIN_DISTANCE = 350` (the range 100 to 2000 and the message are unchanged). The prominence stays a parameter of `measure_local_peaks` with the default changed to 20 and its checks kept (the measurement's own tests keep their meaning), but the request no longer has `peak_prominence` (a value sent is ignored like any unknown form field) and the response no longer has it; the page loses the control. All image types that use the measurement therefore use 20%.

**Rationale**: "Hard-coded" is a request-level decision; keeping the function parameter keeps the measurement testable at other values.

**Alternatives considered**: Removing the parameter from the measurement (breaks about a dozen of its own tests for no gain); keeping `peak_prominence` accepted and echoed (the user said hard-coded and the spec says ignored).

## D6. The other image types

**Decision**: Unchanged (spec Q1 answer A): they keep reading `LocalPeaks.frame_positions`. Their pictures change only through the two new shared settings (Minimum distance 350 by default, Prominence 20%).

## D7. Testing the real files

**Decision**: `test_tempo_files.py` measures `sonata.wav` and `almost2.wav` with 350 ms and 20%, runs the finder, prints the report (restarts, share near the target, the tempo every 10 seconds) and asserts: the tempo is never outside 60 to 156; two runs are identical; the number of tempos equals the number of peaks. A file missing from `backend/audio` skips the test with a message.

**Rationale**: Slow-ish (it measures two files, about 10 seconds), but it is the user's own check, and it keeps the numbers of D2 reproducible.
