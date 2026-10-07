# Research: Energy Saturation

No `NEEDS CLARIFICATION` items remained in the spec. These are the design decisions the plan rests on.

## Decision 1: Measure energy directly from the samples of each frame's period

- **Decision**: Energy is computed from the raw channels over the frame's own period, in a new `energy.py`, not from the note values and not per analysis window.
- **Rationale**: The request wants "overall energy, not just tonal energy", which the 88 note values (a spectrum read at 88 bins) cannot give: noise and percussion between notes are lost. Using the frame's own period also makes saturation independent of the window size and spacing settings, so changing those never changes the colors' vividness.
- **Alternatives considered**: (a) One energy per analysis window, then averaged into frames like the note values. Ties the measure to window size and spacing (a 32768 window would smear it) and needs the same window-to-frame bookkeeping for no gain. (b) The total spectrum magnitude of each window. Cheaper, but it is a spectral measure again and depends on the window function and size.

## Decision 2: Internal window length and rounding

- **Decision**: `internal_window(sample_rate) = max(2, floor(32 × sample_rate / 44100 + 0.5))`: nearest whole number, halves rounded up.
- **Rationale**: Gives 32 at 44.1 kHz, 16 at 22,050 Hz, 8 at 11,025 Hz, 35 at 48,000 Hz, as the spec states. A window of 1 sample has no spread, so 2 is the floor; the sample rates the analyzer accepts (at least about 14 kHz for the smallest window size) already give 10 or more, so the floor never applies in practice. Python's `round` rounds halves to even; explicit `floor(x + 0.5)` is predictable.
- **Alternatives considered**: Rounding down (a window up to one sample shorter than proportional, and the rule would not match the examples in the spec). A fixed 32 at every rate (the spec asks for proportional scaling).

## Decision 3: Per-frame loop over reshaped slices, not cumulative sums

- **Decision**: For each frame, take the sample slice `[start, end)`, keep `n = (end - start) // w` full windows, reshape the slice to `(n, w)`, take `std(axis=1)` per channel (population, `ddof=0`), average the two channels and then the windows. Samples are converted to the common ±1 scale (the same `_to_float` as the analysis) one slice at a time. A mono file (the same array for both channels) is measured once.
- **Rationale**: Direct standard deviation is numerically exact for quiet signals. A cumulative-sum shortcut (`E[x²] − E[x]²` from running sums) loses precision over files of 10⁸ samples and would give wrong energy for quiet passages. A per-frame loop costs about 12 numpy calls per frame, so about 0.3 s for 10,000 frames, small next to the analysis. Converting only the slice avoids a second float64 copy of the whole file.
- **Alternatives considered**: Cumulative sums (precision, above). A fully vectorized gather of every window of the file (fast but needs chunking to bound memory, more code). Kept as the fallback if the measured time exceeds the 25% budget: frames are batched when they share an integer period.

## Decision 4: Frame boundaries

- **Decision**: Frame `f` covers samples from `rint(f × sample_rate / frame_rate)` to `rint((f + 1) × sample_rate / frame_rate)`, clipped to the file length.
- **Rationale**: Nearest whole sample, the same convention `window_starts` uses for analysis windows. Consecutive frames then tile the file exactly with no gap or overlap. `numpy.rint` (halves to even) is what the existing code uses.
- **Alternatives considered**: Floor (a systematic early bias) or the exact fractional position (not meaningful for samples).

## Decision 5: Saturation per frame, shared by tiles, smoothed like the hue

- **Decision**: `saturation_sequence(energies, energy_root, smoothing)` returns one value per frame: `(energy / peak) ** (1 / root)` (all zeros if the peak is 0), then `smooth_frames` on the column of values with the same smoothing as the notes and the hue.
- **Rationale**: Energy describes the whole sound, so all 84 tiles of a frame share it. Mapping first and smoothing second mirrors `hue_sequence` (hue is computed per frame, then smoothed), so with smoothing 0 the saturation is exactly the mapped value, as the spec requires. Smoothing is a running average, so the values stay inside 0 to 1.
- **Alternatives considered**: Smoothing the energies before the mapping. It would give a different curve than the one the user sees for the hue and would break the "exactly the mapped value at smoothing 0" statement only by the order, but makes the root interact with the smoothing in a less predictable way. Smoothing both. Double smoothing.

## Decision 6: Helpers keep a default saturation of 0.5; the job path always passes one

- **Decision**: `tile_colors`, `render_frame` and `write_frames` take an optional saturation (or energies); when it is omitted they use the old 50% (`DEFAULT_SATURATION`). `create_job` always passes the energy-derived saturation.
- **Rationale**: Feature 007's helper-level tests and any direct callers keep working unchanged, and the user-visible behavior (the job path) is fully replaced as the spec requires. The only tests that change are the two job-level ones that assert 50%.
- **Alternatives considered**: Make the saturation a required argument (rewrites dozens of 007 tests for no behavior gain). Remove the constant and default to 1.0 (silently changes what the helpers return).

## Decision 7: API field `energy`, parsed like `brightness`

- **Decision**: A new optional form field `energy`. Missing means 1. A field that was sent must be a whole number from 1 to 8; an empty or invalid value is refused with 400 and "The energy must be a whole number from 1 to 8." The response gains `"energy"`. The "sent versus missing" distinction already used for `brightness` and `smoothing` is reused.
- **Rationale**: Same behavior as the neighboring settings, so clients and tests treat it the same way.
- **Alternatives considered**: A name like `energy_root` (more descriptive but inconsistent with `brightness`, which is also a root and is named for what the user sees).

## Decision 8: UI placement and wording

- **Decision**: An **Energy** number field next to Brightness, the two sharing one row of the settings column, with an info button and popover. It follows Brightness's rules: whole numbers, error shown under the field, disabled while busy. The result summary gains "Energy: n".
- **Rationale**: Both settings are small whole-number roots and the 008 layout is meant to make room for many parameters, so pairing them saves a row. The label is "Energy", as the request calls the measure.
- **Alternatives considered**: A slider (a whole number from 1 to 8 is as easy to type, and it matches Brightness). A separate full-width row (uses more space for no gain).

## Decision 9: Population standard deviation on the ±1 sample scale

- **Decision**: `numpy.std` with `ddof=0` on samples converted to about ±1 with the analysis's `_to_float`.
- **Rationale**: Matches the spec's assumption. The scale does not matter for the final saturation (energies are divided by the file's peak) but a common scale keeps the intermediate numbers meaningful (0.5, 0.25 in the examples) and independent of bit depth.
- **Alternatives considered**: Sample standard deviation (`ddof=1`): differs by a factor `sqrt(w / (w − 1))` in every window, which is absorbed by normalization but breaks the hand-computed examples.
