# Research: Smoothing Window

No `NEEDS CLARIFICATION` items remained in the spec; the formula, the integer window and the smoothed quantities were confirmed by the user on 2026-10-10. These are the design decisions the plan rests on.

## Decision 1: Compute the whole file with shifted additions instead of a streaming buffer

- **Decision**: `smooth_frames(frames, smoothing, window)` works on the whole `(frames, notes)` array: `out = A.copy()`; for each offset `j` from 1 to `min(window, frames - 1)`, `out[j:] += s * A[:-j]`; then each row `t` is divided by `1 + s * min(t, window)`. `s = 0` returns the copy at once.
- **Rationale**: The request says a buffer of the last `w` frames is needed. That describes what the formula depends on, and this computes exactly that dependence: row `t` receives `A[t]` and `A[t-1] … A[t-w]` and nothing else (causal). All the frames are already in memory when `write_frames` runs (it receives the whole array and the other steps need the whole file, for example the file's largest value), so a streaming ring buffer would be extra code with the same result. The output is a pure function of the input, easy to test against a plain reference loop. Cost: `w` vectorized additions per array.
- **Alternatives considered**: A `collections.deque` of the last `w` frames inside a Python loop over frames (about 1,800 to 10,000 iterations per job per array, three arrays; slower and no clearer). A convolution (`np.convolve`/`scipy.ndimage`) per column: works but the shrinking denominator at the start needs extra handling, and the dependency on edge modes is easy to get wrong. A cumulative-sum window (`cumsum[t] − cumsum[t−w−1]`): fast for large `w` but loses precision on long files and makes "exactly 0 after `w` frames" fail by rounding (a value minus its own running total is not exactly 0), which the spec requires.

## Decision 2: Earlier frames are the raw values, so the memory is exactly `w` frames

- **Decision**: The sum uses `A` (the unsmoothed input of the function), never earlier outputs.
- **Rationale**: This is what the formula says and it makes "a note that stops is exactly 0 after `w` frames" true (spec scenario 3, SC-002). With the additions in step order the unsmoothed zeros contribute exactly 0.0, so no rounding residue remains.
- **Alternatives considered**: Feeding back smoothed values (the old running average): infinite memory, which the user asked to replace.

## Decision 3: Weights are divided by the weights actually used

- **Decision**: Row `t` is divided by `1 + s * min(t, window)`.
- **Rationale**: Confirmed reading: a weighted average. In the first `w` frames there are fewer than `w` earlier frames; dividing by the full `1 + s·w` would darken the beginning of every file, and the first frame would not be left as it is. This matches the old rule that the first frame is unchanged.
- **Alternatives considered**: Zero-padding the missing frames and dividing by `1 + s·w` (dark start); repeating the first frame to fill the window (invents values).

## Decision 4: `s = 0` is a fast path and an exact identity

- **Decision**: With `s == 0`, return the copy of the input without any arithmetic, for every window.
- **Rationale**: SC-001 requires byte-identical output to before the feature at the default smoothing; `x + 0.0·y` would be exact too, but dividing by `1.0` and adding zeros for 20 passes is wasted work and an unneeded risk (for example `-0.0`, `nan` inputs). The existing function already had this shortcut.
- **Alternatives considered**: None worth recording.

## Decision 5: What is smoothed and in what order

- **Decision**: Unchanged call sites. `write_frames` smooths the note values (`smooth_frames`), `hue_sequence` smooths the 84 hues per frame (as a plain 0..1 number) and `value_sequence` smooths the frame brightness (`(frames, 1)`), each from its own column only, all with the same `smoothing` and the new `smoothing_window`. The gray levels, hue calculation, roots, level steps and threshold come after, as now.
- **Rationale**: Confirmed by the user (underlying values, not pixels). It keeps the order that features 010 and 011 depend on (rounding and the threshold work on smoothed values) and needs no change to them.
- **Alternatives considered**: Averaging the finished pixels (rejected by the user: it would blend black and colored tiles and undo the steps and the threshold).

## Decision 6: Validation and the API field

- **Decision**: `smoothing_window` is an optional form field, a whole number from 1 to 20. Not sent: 1. Sent but empty, not a number (`abc`, `nan`, `inf`), not whole (`2.5`), or outside 1 to 20: refused with HTTP 400 and `The smoothing window must be a whole number from 1 to 20.`, before any audio is read. `5` and `5.0` are accepted; the response carries an integer. In the library function a window that is not an `int` (bools refused) from 1 to 20 raises `ValueError` with the same message.
- **Rationale**: Same handling as `energy` (`_sent_fields` tells "not sent" from "sent empty"), same status code and timing as the other settings.
- **Alternatives considered**: Clamping out-of-range windows (silent surprises); accepting decimals (a window is a count of frames).

## Decision 7: The page control

- **Decision**: A number input (`type="number"`, step 1, min 1, max 20, default 1) labeled "Smoothing window (frames)" placed directly above the Smoothing slider, with an info button, an inline error, disabled while busy, and a summary line "Smoothing window: n". The Smoothing explanation is rewritten.
- **Rationale**: Whole-number settings elsewhere (Brightness, Saturation) are number inputs; a slider already exists for the fractional Smoothing, and placing the window with it makes the pair read as one setting.
- **Alternatives considered**: A second slider (21 stops, harder to hit exact values) or a dropdown of 20 entries (long).

## Decision 8: Existing tests that encode the old running average

These tests assert the old behavior and are rewritten to the new definition (their intent mostly stays):

- `test_frame_rendering.py`: the reference helper `reference_smooth` and the tests built on it (first frame unchanged, matches the formula for random data, a stopped note fades over more frames at higher smoothing, a started note rises over more frames, the limits), the hue smoothing reference `ref_hue_sequence` and its tests, `test_written_frames_have_smoothed_values_and_smoothed_hues`, `test_rounding_is_applied_after_smoothing` and `test_smoothed_saturations_are_rounded_to_the_levels` (feature 010), and the fading-note test of feature 011.
- `test_frame_brightness.py`: the two tests that check brightness is smoothed like the notes and hues.
- `test_jobs_api.py`: `test_half_smoothing_gives_the_running_average_of_each_note`, `test_a_stopped_note_fades_more_slowly_at_higher_smoothing`, the hue-smoothing tests (about lines 1007 to 1043), and any test whose expected numbers were computed from the old formula.
- `test_color_levels_api.py` and `test_threshold_api.py`: only where they use `smoothing=0.8` and depend on how long a value lasts (their assertions are mostly about levels and black tiles and should hold).
- Frontend: `help.test.ts` pins the exact old Smoothing wording; `validation.test.ts` and `SettingsForm.test.ts` need additions, not changes.

Tests that only use smoothing 0 are unaffected.
