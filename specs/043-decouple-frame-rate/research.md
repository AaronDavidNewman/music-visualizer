# Research: Decouple the frame rate from the frequency buffers

No `NEEDS CLARIFICATION` remained in the Technical Context. The decisions below settle how the spec is built on the code as it is today (read on 2026-11-18).

## 1. How the fixed step is expressed

- **Decision**: a constant `BUFFER_INTERVAL_MS = 60` and `buffer_step(sample_rate) = sample_rate * BUFFER_INTERVAL_MS / 1000`, the step in samples as a float, passed as the existing `step`
  argument of `note_analysis.analyze_channels()`.
- **Rationale**: `analyze_channels()` already takes a step in samples, may be fractional, and `window_starts()` places each window at `rint(k * step)`, so each start is within half a sample
  of its exact place (SC-002). `sample_rate * 60 / 1000` is exact for 44100 (2646.0) and 48000 (2880.0); `0.06 * sample_rate` would give 2646.0000000000005. No spacing "as a multiple of
  the window size" is needed any more, so the 6-decimal rounding of the old `default_spacing()` (which made the step slightly shorter than a frame period) disappears.
- **Alternatives considered**: (a) round the step to a whole number of samples: simpler to explain but 661.5 would become 662 and the error would add up to over a sample in a long file;
  (b) keep `window_spacing` internally with a computed value: keeps a concept the user asked to remove and the 6-decimal drift.

## 2. A step below one sample

- **Decision**: `buffer_step()` returns `max(1.0, ...)`; no raised flag and no message.
- **Rationale**: `analyze_channels()` refuses a step under 1. 60 ms is under one sample only for a sample rate under 16.7 Hz, which `NoteBinAnalyzer` already refuses (a rate too low for
  the window size), so the guard is defence and never changes a result for an accepted file. (The analyzer refuses a sample rate under 16745 Hz at the smallest window, so through the endpoint the steps run from 1005 samples at 16745 Hz upwards; 8000 and 11025 Hz appear only in the unit tests of `buffer_step()`.)

## 3. Frames from buffers

- **Decision**: no change to `frame_count()`, `frame_windows()` or `average_frames()`.
- **Rationale**: they already do what FR-004 and FR-005 say: a frame is the mean of the windows that start inside its period; with none, the latest earlier window; every window is owned
  by exactly one frame (documented in `frame_rendering.frame_windows`). Only the *input* changes (a fixed step).
- **Alternatives considered**: interpolating between buffers above 16.7 fps (frames would change between buffers instead of repeating): not asked, and a spec assumption keeps the
  repeating behaviour; it could be a later feature.

## 4. Removing the two smoothing settings

- **Decision**: delete `smooth_frames()`, `_check_smoothing_window()` and the six constants (`MIN/MAX/DEFAULT_SMOOTHING`, `MIN/MAX/DEFAULT_SMOOTHING_WINDOW`) from `frame_rendering.py`; delete
  the parameters `smoothing` and `smoothing_window` of `write_frames()`; in `write_frames()` the former `smoothed` array is just `frames` (the `peak` is its maximum).
- **Rationale**: FR-006 and FR-007. The default was 0, for which `smooth_frames()` returned a copy of its input, so with the defaults a picture does not change by this removal.
- **Alternatives considered**: keeping `smooth_frames()` in the module "for the future": dead code, and its tests (`test_smoothing_window.py`) would keep describing a setting that is gone.

## 5. The request and the answer of `POST /api/jobs`

- **Decision**: remove the three `Form` parameters (`window_spacing`, `smoothing`, `smoothing_window`) and their `_parse_*` functions; remove `smoothing`, `smoothing_window`,
  `window_spacing` and `spacing_raised` from the answer; keep `step_samples` (now always the 60 ms step) and `window_count`. See [contracts/job-api.md](contracts/job-api.md).
- **Rationale**: FastAPI ignores form fields that the function does not declare, so a request that still sends the old fields (even with a bad value such as `smoothing=banana`) is
  neither refused nor used (FR-012) with no extra code; a test pins that. `step_samples` and `window_count` are kept because they describe the analysis and are cheap; the page does not show
  them today (it shows the window spacing), so it would be harmless to drop them, but the existing tests of the answer's keys then have one fewer change.
- **Detail to remove with them**: `jobs.py` has a `sent` set of the form keys that were sent (used to tell "not sent" from "sent empty"); it stays, as other settings use it.
- **The `max_windows` message** becomes "This would create N windows; the limit is M. Use a shorter file." (FR-011). The limit stays (reachable by a long low-rate file within the
  200 MB upload limit, for example 8 kHz mono 8-bit).

## 6. The documentation sweep (constitution II and III)

- **Decision**: (a) remove step 5 *Smooth over the earlier frames* from the order of operations of `frame_rendering.py` and renumber; (b) remove `SMOOTH` from the pipeline overview in
  `image_types.py` and from `SHARED_STEPS` in `test_documentation.py`, and say in AVERAGE that it is the only smoothing of the note data (the mean of the buffers each frame owns);
  (c) `window_spacing.py` becomes `buffer_interval.py` in the module list of `test_documentation.py`, with an `Order of operations:`; (d) `jobs.py` order of operations step 4 uses
  `buffer_interval.buffer_step()`; (e) `note_analysis.py` and `array_types.py` (the *Made by:* of `NoteStrengths`) lose their mention of `smooth_frames` and of a user-chosen step;
  (f) the docstrings that call the note values *smoothed* (`chromatic_decay`, `decay`, `decay_exp`, `polar_chords`, `polychord`, `note_selection`, `jobs`, `frame_rendering`, `image_types`:
  about 70 places by a count of the word) say *the strength of each note in each frame* instead. Words about the **grid** smoothing of Contour (`directionalSmoothing`, "the smoothed
  value of the cell") and the Gaussian smoothing of the picture are **not** changed: they are other settings that stay.
- **Rationale**: rule III says a change to the steps of a module changes its documentation in the same piece of work; a docstring that says "smoothed" after the step is gone is a false
  statement that review (`shape_probe.py`, `trace_pipeline.py`) would flag. The older spec files under `specs/` (history) are not edited. The 041 contracts
  (`documentation-standard.md`, `checks.md`) list `SMOOTH` among the shared steps; they are the *current* statement of the standard, so the two lines are edited and the constitution's
  version is **not** changed (its text does not name the steps).
- **Alternatives considered**: leaving the word "smoothed": cheaper, but wrong; renaming every local variable called `smoothed`: only where it is in a function that is edited anyway.

## 7. How to prove that no picture type changed (replaces the `verify_frames.py` gate)

- **Decision**: a new tool `specs/043-decouple-frame-rate/tools/verify_drawing.py`, in the style of `verify_frames.py`, that builds a fixed seeded `NoteStrengths` `(frames, 88)` and a fixed
  beat, calls `write_frames()` for every image type with default settings and takes the SHA-256 of every frame. `--write` is run **before the first edit** (the old signature with the
  defaults); the plain run after the change must report no difference. `verify_frames.py` itself is run before and after too, and the report says that its hashes are **expected to differ**
  (the default analysis step is now 60 ms and not the frame period at 30 fps) but that every type must still make the same number of frames.
- **Rationale**: the constitution asks for the baseline comparison for any change that could move a picture. This change moves pictures on purpose through the analysis step, so the
  honest check is on the part that must not move: the drawing from the same note values. With smoothing at its default of 0 the old and the new `write_frames()` must give identical
  pictures.
- **Alternatives considered**: re-basing `verify_frames.py`'s baseline after the change: it would pass trivially and prove nothing about the drawing.

## 8. The page: what goes, what stays

- **Decision**: remove the Window spacing field and its hint and notices (`spacingText`, `stepHint`, `isBelowMinimum`, the `spacing_raised` notice), the whole **Data smoothing** group
  (`groups.ts`, `SettingsForm.vue`, the two help texts, `validation.ts`), `spacing.ts` and its test, and the sample-rate reading (`wavHeader.ts`, its test, the `update:sampleRate`
  event of `FilePicker.vue`, `fileSampleRate` in `App.vue`, the `sampleRate` prop of `SettingsForm.vue`). The window size and the frame rate fields stay.
- **Rationale**: FR-003, FR-006, FR-010. The header comment of `wavHeader.ts` says it exists "so the form can compute the default window spacing"; after this feature nothing reads the
  rate, so keeping the code would be dead code with tests. Image smoothing (Oversampling, Interpolate, Gaussian) is a different group and stays.
- **Help text**: `frameRateHelp` says what the frame rate now means: how many pictures are made for each second; the notes are measured every 60 ms; a frame longer than that averages
  the measurements and a shorter one repeats the latest.
- **Group lists**: `groups.ts` has a function that returns the shown groups (a doc comment: "Data smoothing (not for Energy graphs and Rhythm Circles, which do not smooth the data)");
  the group, its id and the comment go; `groups.test.ts` and `SettingsForm.test.ts` are edited to match.

## 9. Frame rate range

- **Decision**: unchanged, 1 to 60, default 30 (spec Assumptions). No code change in `config.py` or `validation.ts`.

## 10. Risks

- The tests that pass `smoothing=` / `smoothing_window=` to `write_frames()` or to the endpoint (listed in the task list) fail until edited; the endpoint ones that send the fields
  through a client keep passing (the fields are ignored) but their assertions on the answer's keys do not.
- Tests that assume the old default spacing (one window per frame at the given frame rate), such as ones that count `window_count` or compare to `frame_windows()` for a given frame
  rate, change their expected numbers. They are found by running the suite and by `grep window_count`.
- The old baseline failures (25 + about 60) are in the same files; the comparison with the baseline list is by test id, not by count.

## 11. What the first full run of the suite taught (added while implementing)

- With a 60 ms step and a window of 4096 or more samples the windows always overlap, so the last one or two windows of a file **overhang its end** and see a tone cut off; a cut tone leaks
  into the notes around it (70 dB down at the faint note of `test_noise_floor_api.py`, enough to light other letters or bars). This is how real files behave and is not a defect of the feature.
  The tests that used the old default (one window per frame, the last one just fitting) therefore check a frame made only from whole windows (`settled()` in the noise-floor tests, `WHOLE` in the
  Chromatic Decay tests, `WHOLE_FRAMES_BEFORE_THE_END` in the Polar Chords tests, `CHECKED` and `windows_to()` in the Energy graphs tests).
- The expected values in the Energy graphs tests are derived from the 60 ms step (`windows_to(frame)`), not from a fixed count of 28.
