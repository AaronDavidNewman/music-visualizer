# Data Model: Energy Graphs

All arrays are numpy arrays. `W` is the number of analysis windows, `F` the number of frames, `N = 84` the notes of the histogram.

*(Revised 2026-11-08: the pies, `rest_rms` and the shares of the first version are gone; the amplitude totals and the softmax are new.)*

## AnalysisResult (existing, unchanged)

`frames` is `(W, 88)` note strengths, floored by feature 033 before use. Only the first 84 columns are notes of the histogram.

## EnergyGraphData (`energy_graphs.py`)

What every frame needs, worked out before any drawing.

| Field | Type | Meaning |
|-------|------|---------|
| `histogram` | `(F, 84)` int64 | for each frame, the sum of the rank scores of every window that starts before the end of that frame, per note, lowest note first |
| `amplitude` | `(F, 84)` float64 | the same for the quasi-decibel values |

Derived: `frame_count = F`.

### Validation (`_check_data`, before anything is written)

- `histogram` is 2-D with 84 columns, integer, no negative value; `amplitude` has the same shape, is numeric, finite and not negative.
- Monotonic by construction (a total never shrinks from frame to frame): tested, not enforced.

## Rank scores (per window, internal)

For a window with note strengths `v[0..83]` (after the noise floor): order the notes by `v` descending, equal values by note number ascending; the note at position `r` (0 = loudest) scores `84 - r` when `v > 0`, else `0`. Value range 0 to 84.

## Quasi-decibels (per window, internal)

`peak` = the largest of the 84 note strengths in any window of the file. For a note of strength `a` in a window: `0` if `a == 0`; `0` for every note if `peak <= 1`; otherwise `max(0, 20 log10(a) / (20 log10(peak)))`. Range 0 to 1 (1 only for a note at the peak).

## Frame mapping (shared with `average_frames`)

`frame_windows(result, frame_rate, frames)` returns `(first, stop, earlier)`, three `(F,)` integer arrays: frame `i` owns windows `first[i] .. stop[i] - 1`; `earlier[i] = max(first[i] - 1, 0)` is the window a frame with no window of its own falls back to (used by `average_frames`; the energy totals do not use it, a frame with no window adds nothing). `average_frames` uses it unchanged: its output is identical to before.

## Totals per frame

`histogram[i] = running_ranks[stop[i]]` and `amplitude[i] = running_amplitudes[stop[i]]`, `running[k]` being the sum of the contributions of windows `0 .. k - 1`. A window is counted once, in the frame it starts in.

## What is drawn (`softmax_shares`, `_frame`)

For each data set and frame: `x = totals / max(totals)` (a row with no total stays all 0 and has no bars); `share = exp(x) / sum(exp(x))` over the 84 notes (each row adds up to 1; at most `e` between the largest and the smallest value, so no overflow); then `lifted = share - min(share)` over the 84 notes of **that data set** (`above_smallest`; the smallest bar has height 0, and a row of equal totals has no bar). The bar height is `round(plot_height * lifted / tallest)` with `tallest` the largest `lifted` of **both** data sets in the frame (so the two are on the same scale and the tallest bar is the full height), and at least 1 pixel for a `lifted` above 0.

## State and lifecycle

The totals are the only quantities with memory, and they are computed for all frames at once from cumulative sums, so frames can be drawn in any order and in parallel. Nothing is stored between jobs.
