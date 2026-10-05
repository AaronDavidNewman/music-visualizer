# Research: Window Spacing Parameter

No `NEEDS CLARIFICATION` items are open. These are the design decisions.

## Decision 1: Step and window starts

- **Decision**: `step = spacing × window_size`. If `step < 1`, use `step = 1` and report `spacing_used = 1 / window_size`. Window *k* starts at `rint(k × step)` for every *k* whose start is below the sample count. Starts come from `k × step` each time, not from adding up rounded steps.
- **Rationale**: Matches FR-002 and FR-010 and the spec's edge case on rounding, and avoids drift on long files. At spacing 1, `rint(k × window_size)` equals the old starts exactly.
- **Alternatives considered**: Rounding the step to a whole number (long files would drift away from the requested spacing); truncating starts (biased early).

## Decision 2: Counting windows without building them

- **Decision**: A function computes the window count in closed form, `ceil((total − 0.5) / step)`, then corrects it by at most one against `rint` at the boundary, so the router can check the window cap before any array is built or any transform is run.
- **Rationale**: A one-sample step on a long file would otherwise allocate millions of start values just to be refused (SC-008). Tests compare the closed form with the explicit start list for many steps.
- **Alternatives considered**: Building the starts and then checking (slow and memory-hungry exactly in the case the cap exists for).

## Decision 3: Overlap and gaps in the analysis

- **Decision**: `analyze_channels` takes an optional `step` (samples; default `window_size`, which means spacing 1). It processes windows in chunks. For each chunk it converts one contiguous segment of the audio to float once, and builds the chunk's windows by index from that segment, padding with zeros past the end. Chunk size is chosen so a chunk covers at most about 4M samples. `AnalysisResult` gains a `starts` array of window start samples, and `window_start_times()` uses it.
- **Rationale**: With overlap, converting each window separately would convert the same samples many times. One conversion per chunk keeps memory bounded and the cost low. Gaps (spacing above 1) need no special handling because windows are gathered by start.
- **Alternatives considered**: Converting the whole file to float up front (hundreds of MB for long files); `numpy` sliding-window views (do not handle gaps, padding or rounded starts directly).

## Decision 4: Frame averaging from window starts

- **Decision**: `average_frames` works in samples. Frame *f* covers `[f × sr / fps, (f + 1) × sr / fps)`. Windows are assigned by their **exact** position `k × step` (not the rounded start sample, which only decides which audio is read). It finds with `searchsorted` the windows positioned in the period (with a 1e-6 sample tolerance so a position exactly on a boundary falls in the later frame), and averages them using a running sum. If none are inside, it uses the last window that started before the period.
- **Rationale**: Implements FR-005 for any spacing. At spacing 1 the "last window that started before the period" is the window that covers the period start, so frames are identical to feature 002 (SC-002). Frame 0 always contains window 0, since window 0 starts at sample 0. Using exact positions matters: when the frame period is not a whole number of samples (44,100 Hz at 11 fps is 4009.09), rounded starts can fall just before a boundary and leave a frame with no window even though the step is never longer than a frame. A progression with a gap no longer than the period always has a member in every period. The only exception is the last frame, when its sole position lies within half a sample of the end of the audio (the window would begin past the end and hold only silence), where using the earlier window is better.
- **Alternatives considered**: Weighting windows by overlap (not what the spec asks; changes spacing-1 results).

## Decision 5: Where the default is computed

- **Decision**: In the browser, as `floor(10^6 × (sample_rate / frame_rate) / window_size) / 10^6`. The server has the same function (`default_spacing`) and uses it when a request omits the field, so scripted callers and the UI agree. Both are tested against one shared table of values.
- **Rationale**: SC-004 wants an update in under 1 second on every change. A server round trip per keystroke would add a network dependency to a field refresh, while the formula is one line. Rounding down guarantees the step is never longer than a frame period, so every frame has a window (FR-006, FR-008). 6 decimals keep the step within about 0.03 samples of a frame period at the largest window.
- **Alternatives considered**: A server endpoint for the default (extra requests and failure modes); displaying 4 decimals (up to about 3 samples of drift at the largest window; the spec allows it, but 6 costs nothing).

## Decision 6: Reading the sample rate in the browser

- **Decision**: `wavHeader.ts` reads the first 64 KB of the chosen file with `Blob.slice` and walks the RIFF chunks to the `fmt ` chunk, taking the sample rate (a 32-bit little-endian value 4 bytes into the chunk data). It supports `RIFF` and `RF64`, returns `null` for anything else, and never throws. The form uses 44,100 Hz until a file is chosen and whenever the header cannot be read (the clarified behavior).
- **Rationale**: Only the header is needed, so a 90 MB file is not read into memory. Reading stops after 64 KB; a `fmt ` chunk beyond that is unusual and falls back to 44,100 Hz.
- **Alternatives considered**: Decoding with the Web Audio API (reads the whole file and may resample); asking the server (needs an upload first).

## Decision 7: When the default replaces the field

- **Decision**: The spacing text is replaced by the new default whenever the window size, the frame rate, or the file's sample rate changes. If the frame rate is empty or invalid at that moment, no default can be computed and the field is left alone until it is valid again. A value the user types is kept until one of those three changes.
- **Rationale**: Directly from FR-007 and the user's request. The field is left alone while the frame rate is unusable so partial typing does not blank it.
- **Alternatives considered**: Keeping typed values when other fields change (contradicts the request).

## Decision 8: Telling the user about the 1-sample minimum

- **Decision**: The server applies the minimum and returns `window_spacing` (the value used), `step_samples`, and `spacing_raised`. The results area shows a notice when it was raised. The form also shows a hint under the field while the typed value is below `1 / window_size`, so the user sees it before submitting.
- **Rationale**: The server stays the authority, so scripted callers get the same rule (FR-010), and the user is told both before and after (Story 3).
- **Alternatives considered**: Silently correcting the field in the browser (changes what the user typed without saying why); rejecting low values (the spec says raise).

## Decision 9: Window limit

- **Decision**: `max_windows` setting, default 60,000. The router counts windows from the sample count and step and returns 400 with the count, the limit and a suggestion if exceeded. This is checked after reading the file (the sample count is needed) and before any transform.
- **Rationale**: Spec assumption. A 32768-sample window costs roughly a millisecond per window for both channels, so 60,000 windows is on the order of a minute at worst, which keeps even the worst accepted request bounded.
- **Alternatives considered**: A time-based limit (harder to predict and to test); no limit (a one-sample step could run for hours).

## Decision 10: Backward compatibility

- **Decision**: `analyze_wav` and `NoteBinAnalyzer` keep their signatures and behavior. `analyze_channels(..., step=None)` defaults to the old consecutive windows. `window_spacing` is optional in the HTTP request, and a request without it behaves as the default spacing (one window per frame).
- **Rationale**: Feature 001's tests and callers keep working. Note that the HTTP default changes meaning: before this feature, an HTTP request used spacing 1, and now one that omits the field uses the one-window-per-frame default. The UI always sends the field explicitly.
- **Alternatives considered**: Treating an omitted field as spacing 1 (keeps old HTTP behavior exactly but disagrees with the UI default and the spec's default).
