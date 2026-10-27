---

description: "Task list for Local Peaks (feature 023)"
---

# Tasks: Local Peaks

**Input**: Design documents from `/specs/023-local-peaks/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/local-peaks.md, quickstart.md

**Tests**: Written first for each story (the project's practice), on seeded synthetic signals (click tracks and bursts); no audio files and no browser are needed. There is no frontend or API change, so there are no frontend tasks.

**Organization**: By user story: US1 the peaks themselves (P1), US2 asking for the energy and the rate at any point (P2), US3 the two settings (P3). The settings checks and the result types are in the foundation because US1 already needs them.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- Paths are from the repository root. The setup script of Spec Kit cannot run here (PowerShell execution policy), so the feature files were written by hand. Backend checks run with the user's colormap lists possibly still inconsistent: use the temporary-default runner (`scratchpad/run_with_default.py`, file restored) and report the one expected list-mismatch failure. Edit files with their line endings preserved; avoid `sed -i`; scripts with backticks or non-ASCII go in files written with the Write tool; replace test functions only block by block and compare test counts before and after.

---

## Phase 1: Setup

- [x] T001 Record the baseline before adding anything: the backend suite (temporary default colormap, file restored), the frontend suite, typecheck and build; the four reference hashes (`scratchpad/hashes019.py`: tiles `6819990556fd4095`, blended `f32a99c59fcb87fc`, Blues/smoothing/threshold `92b3a27dee73e223`, contour `400cc93e1bfca03d`); the per-file backend test counts (`scratchpad/count_tests.py`). Confirm `scipy` is in `backend/requirements.txt` (`scipy>=1.11`, already there) and that `scipy.signal.find_peaks` imports in the `.venv`.
  - Done: Baseline: backend 3,210 tests (temporary default colormap, file restored), frontend 515 tests, typecheck clean; the four reference hashes `6819990556fd4095`, `f32a99c59fcb87fc`, `92b3a27dee73e223`, `400cc93e1bfca03d`; per-file counts saved (`scratchpad/counts_023_before.txt`); `scipy>=1.11` already in `requirements.txt`, 1.15.3 installed, `find_peaks` imports.

---

## Phase 2: Foundation (blocks every story)

**Purpose**: The signals the tests need and the module's constants, checks and result types.

- [x] T002 [P] Create `backend/tests/local_peaks_signals.py`: seeded helpers (numpy `default_rng`) used by the tests: `click_track(seconds, period, rate=44100, width=8, seed=1, level=0.5, noise=0.005)` returning `(left, right, click_samples)` (quiet noise plus a short burst every `period` seconds, starting at `period`), `two_bursts(gap_seconds, strengths, ...)`, `bumps(...)` (one loud click and quieter bumps at given fractions of its height), `silence(seconds, rate)`, and `direct_energy(left, right)` (a slow per-window reference: a Python loop over 32-sample windows with `numpy.std` per channel, averaged).
  - Done: `backend/tests/local_peaks_signals.py`: `click_track`, `bursts` (bursts of alternating signs so a burst's spread does not depend on chance: a random burst once came out weak enough to fall under the prominence), `silence`, `direct_energy`. There is no separate `two_bursts` or `bumps` helper: `bursts` covers both.
- [x] T003 Create `backend/app/services/local_peaks.py` with the module docstring (what the measurement is, the two windows, the zones, what is returned), the constants of data-model.md (`IMPULSE_SAMPLES = 32`, `PEAKS_WINDOW = 4096`, `MIN/MAX/DEFAULT_MIN_DISTANCE = 100/2000/100`, `MIN/MAX/DEFAULT_PROMINENCE = 0/100/50`, `DEFAULT_RATE = 60.0`), `check_min_distance` and `check_prominence` (real numbers only, booleans, strings, NaN and infinity refused, `-0.0` turned into `0.0`; the exact messages of data-model.md), and the frozen dataclasses `LocalPeak` (`sample`, `energy`, `window_min`, `window_max`, `rate`) and `LocalPeaks` (`peaks` tuple, `file_rate`, `sample_count`, `min_distance`, `prominence`) with the query methods declared but raising `NotImplementedError` until T008.
  - Done: `backend/app/services/local_peaks.py`: constants, `check_min_distance`, `check_prominence`, frozen `LocalPeak` and `LocalPeaks`.

**Checkpoint**: the module imports; the helpers import.

---

## Phase 3: User Story 1 - Find where the overall energy peaks, and how often (Priority: P1) 🎯 MVP

**Goal**: `measure_local_peaks` and `measure_wav` produce the ordered list of peaks, each with its sample, energy, the window's minimum and maximum energy and its rate.

**Independent Test**: `measure_local_peaks` on a 30 s click track with a click every 0.5 s at 44.1 kHz and the default settings: 59 peaks, each within 32 samples of its click, none twice, 120 peaks per minute (within 2%) at every peak after the first.

### Tests for User Story 1 (write first, they fail)

- [x] T004 [P] [US1] Create `backend/tests/test_local_peaks.py` (part 1: Story 1, FR-001 to FR-004, FR-007, FR-008, FR-011, SC-001 to SC-003, SC-007, SC-008): (a) `impulse_energy` equals `direct_energy` for random stereo data, equals the single channel's `std` for a mono (identical channels) input, averages the two standard deviations (a loud left with a silent right gives half the left's `std`, and two channels in opposite phase do not cancel), drops a last partial window, returns a float64 array of `len // 32`, is 0 for silence, and does not modify its inputs; (b) a click track of 0.5 s (59 clicks): every click found within 32 samples, none twice, ordered by sample, the first peak's rate 60 and every other rate 120 within 2%; also 0.75 s (80 within 2%) and 0.3 s (200); the sample is a multiple of 32; `energy` is the impulse energy at that sample (`direct_energy[sample // 32]`); `window_min` and `window_max` are the smallest and largest impulse energies of the window the peak was found in (use `window=` small and large and check the values against `direct_energy` slices of the right window); (c) two bursts less than the minimum distance apart give only the stronger one, whichever comes first, for several distances; bursts exactly across a window-zone border (place them around `window/2 + window/4` impulse samples) also give one, and two distant bursts across the same border give two; (d) a peak is reported once however many windows contain it (a click track with a click in every overlap region, `window` 256 and the default); (e) windows: a file shorter than the window, a file of one impulse window, of fewer than 32 samples, an empty file give no failure (and no peaks for a silent or tiny input); a plateau of equal energies is one peak at its middle; the same peaks for `window` 2,048, 4,096 and 8,192 on well-separated clicks; (f) silence gives no peaks and no failure, and a very quiet click track gives the same peaks as a loud one (the prominence is relative); (g) two runs give equal results and the inputs are unchanged; (h) mono and stereo: a mono file (same array twice) gives the same peaks as the stereo file made from it; (i) `measure_wav` on a small WAV file written to a temp directory (stereo and mono, 22,050 and 48,000 Hz) gives the same result as `measure_local_peaks` on the arrays `read_wav` returns, and an unreadable file raises the usual `AudioAnalysisError`; (j) different sample rates give the same times: the click track at 22,050, 44,100 and 48,000 Hz gives the same rates and the distance in impulse samples differing as expected.
  - Done: `backend/tests/test_local_peaks.py` part 1: the impulse energy (direct calculation, per-channel spread averaged, opposite phase does not cancel, mono, partial window, bit depth), click tracks of 0.5, 0.75 and 0.3 s, the window min and max against the owning window (three window sizes), the rate formula, two bursts closer than the distance (both orders), across a zone border at 256 and at the default window with 2000 ms, farther bursts across a border, the distance on random bursts, once-only reporting, independence of the window size, tiling of the zones, short inputs, a file shorter than the window, a plateau, silence, a quiet file, determinism, mono, three sample rates, WAV files (mono and stereo, 22,050 and 48,000 Hz).

### Implementation for User Story 1

- [x] T005 [US1] In `backend/app/services/local_peaks.py` implement, following data-model.md and research Decisions 1 to 5: argument checks (`file_rate` positive whole number, the two channels one-dimensional and equal in length, `window` a whole number of at least 8 made even; the messages of data-model.md; the settings checked first), `impulse_energy(left, right)` (reshape and `np.std(axis=1)` per channel on float64, averaged), `measure_local_peaks` (distance, the sliding windows with their zones, `scipy.signal.find_peaks(window, distance=…, prominence=…)` per window with `top > 0`, the merge pass across zone borders, the records with `window_min`/`window_max`, the rates `60 × file_rate / Δsample` with `DEFAULT_RATE` for the first), and `measure_wav(path, min_distance, prominence, display_name)` using `note_analysis.read_wav`. Run the tests of T004 and fix.
  - Done: `local_peaks.py`: `impulse_energy`, `window_zones` (public, so the tiling is testable), `measure_local_peaks`, `measure_wav`. One real finding on the way: with random bursts one click was weak by chance and correctly fell under 50 % prominence, so the test signals were made deterministic.
- [x] T006 [US1] Mutation checks of the measurement, each caught by the tests and restored byte for byte (`scratchpad/mutate_023.py`): the channels averaged before the standard deviation; `ddof=1`; overlapping windows for the energy; a partial last window kept; the left channel only; the zones not tiling (a gap, and an overlap that reports twice); every peak accepted from every window; no merge pass; the merge keeping the weaker; `distance` not converted (the milliseconds passed), converted with 32 forgotten, converted with floor instead of round; the prominence taken as the percentage itself or of the file's maximum rather than the window's; the sample at the centre of the impulse window (`+16`); `window_min`/`window_max` taken from the whole file; the first peak's rate left as the gap to the next one; the rate computed with the file rate forgotten or in peaks per second.
  - Done: Mutation checks (`scratchpad/mutate_023.py peaks`): 21 mutations, 19 caught at once; the rounding one was caught after T010's conversion tests; "a silent window is searched" is an equivalent mutant (`find_peaks` on a flat array returns nothing), so the guard `top > 0` is only an optimisation.

**Checkpoint**: peaks are found, positioned, rated and ordered; the interpolation is not there yet.

---

## Phase 4: User Story 2 - Ask for the energy and the rate at any point (Priority: P2)

**Goal**: `energy_at`, `rate_at`, `energy_at_time` and `rate_at_time` answer for every finite point, as the clarification says.

**Independent Test**: On the click track: the energy at a click is that peak's; half way between two clicks it is between the two; before the first peak it is 0 and the rate 60; after the last peak it is the last peak's energy; the rate anywhere is the rate of the last peak at or before the point.

### Tests for User Story 2 (write first, they fail)

- [x] T007 [P] [US2] Add to `backend/tests/test_local_peaks.py` (part 2: Story 2, FR-009, SC-005), using hand-made `LocalPeaks` values (to know the exact answers) and results of the click track: `energy_at` at every peak's sample equals its energy; at the midpoint of two peaks it is the mean of their energies and at other points the exact line `a + (b − a)(p − pa)/(pb − pa)` (for rising and falling pairs); strictly between the two values for any inner point; 0.0 before the first peak, at sample 0 and at negative points; the last peak's energy after the last peak, at the last sample of the file and past the end; a non-integer sample and a time in seconds (`energy_at_time(t) == energy_at(t × file_rate)`); a list, a tuple and an array in give an array of the same shape (also 2-D) out with the scalar answers, and a scalar gives a Python `float`; `rate_at` is the rate of the last peak at or before the point (at a peak's sample, one sample before it, between, after the last), 60.0 before the first peak and negative points, never interpolated; a result with no peaks (silent file) answers 0.0 and 60.0 everywhere, including arrays; NaN and infinite points (scalar, or inside an array) raise `ValueError("The point must be a finite number.")`; the answers do not change the result (frozen) and are deterministic; `energy_at` over every frame of a 60 s file (1,800 points) is a single fast call.
  - Done: Part 2 of `test_local_peaks.py`: at a peak, between (exact line, falling and rising, strictly between, monotone), before and after (including negative and past the end), fractional and time, arrays of several kinds and shapes, floats for scalars, the rate not interpolated (at a peak, one before, after), the default before the first peak, no peaks, one peak, non-finite and non-numeric points refused, frozen, the click track's answers, 1,800 frames in one fast call.

### Implementation for User Story 2

- [x] T008 [US2] In `backend/app/services/local_peaks.py` implement the four query methods (research Decision 6): `np.interp(points, samples, energies, left=0.0, right=energies[-1])` (0 everywhere with no peaks), `searchsorted(samples, points, side="right") − 1` for the rate (`DEFAULT_RATE` where the index is −1), the finite check, scalars returned as `float`, sequences as float64 arrays of the same shape; keep the arrays as cached read-only views (or recompute: the object is small) without breaking `frozen`/equality. Run the tests of T007 and fix.
  - Done: `LocalPeaks.energy_at`, `rate_at`, `energy_at_time`, `rate_at_time` with `numpy.interp` and `searchsorted`; cached read-only arrays; `_points` refuses non-finite and non-numeric input.
- [x] T009 [US2] Mutation checks, each caught and restored: the energy 1 (or the first peak's) before the first peak instead of 0; the energy 0 after the last peak; the line interpolated between the wrong pair (the next two); the rate interpolated; the rate of the next peak instead of the previous; `side="left"` (the rate one sample late at a peak); the default rate 0 or 1 instead of 60; seconds not multiplied by the file rate; a scalar returned as an array; the NaN check removed.
  - Done: 15 mutations of the queries (`scratchpad/more_023_queries.py`), all caught.

**Checkpoint**: the whole result can be asked for any frame of a file.

---

## Phase 5: User Story 3 - Choose how close and how prominent peaks must be (Priority: P3)

**Goal**: The two settings are checked, converted and handed to `find_peaks` as specified, and they change the result as the spec says.

**Independent Test**: A 300 ms click track gives every click at 100 ms, fewer at 500 ms (no two closer than 500 ms); bumps at half the click's height disappear at prominence 80 and appear at 10.

### Tests for User Story 3 (write first)

- [x] T010 [P] [US3] Add to `backend/tests/test_local_peaks.py` (part 3: Story 3, FR-005, FR-006, FR-010, SC-003, SC-004): the defaults (100 and 50; the constants and the function defaults); `check_min_distance` accepts 100, 2000, 100.5 and numpy numbers and returns floats; refuses 99.9, 2000.1, NaN, ±infinity, `None`, `True`, strings, lists, with the exact message; `check_prominence` accepts 0, 50, 100 and refuses −0.1, 100.1, NaN, infinity, `None`, `True`, strings, with the exact message; `measure_local_peaks` refuses bad settings, a bad rate and mismatched or 2-D channels before measuring (patch `find_peaks` with a spy that fails the test if called); the conversion: spy on `scipy.signal.find_peaks` (patched in the module) and check the `distance` keyword for several rates and distances (`max(1, round(ms/1000 × rate / 32))`: 44,100 Hz and 100 ms gives 138, 2000 ms gives 2,756, 8,000 Hz and 100 ms gives 25) and the `prominence` keyword (`percent/100 × max(window)` per window, 0 for 0%, the window's max at 100%; windows with a different maximum get different prominences); the effect: the 0.3 s click track at 100, 500 and 2,000 ms (every click, then fewer, then fewer again, every gap at least the distance to within one impulse window); no two peaks closer than the distance on random-ish bursts for ten distances from 100 to 2,000; a distance longer than the file gives at most one peak; prominence 10, 50 and 90 on `bumps`: bumps below the share are never reported and the click always is; prominence 0 reports every local maximum that distance allows; the larger the distance or prominence, the not-more peaks (monotone on the test signals).
  - Done: Part 3 of `test_local_peaks.py`: defaults, ranges and messages (both settings, many bad values), checks before anything is measured (a `find_peaks` spy never called), the distance handed to `find_peaks` for eight rate and distance pairs, the prominence per window with different window maxima, the windows handed to `find_peaks`, a file in one window equal to a direct `find_peaks` on its energy for five rate and distance pairs and three prominences, fewer peaks for longer distances and never closer than the distance, a distance longer than the file, bumps below the share dropped and the click kept (10, 50, 90), prominence 0 and 100 (100 only qualifies on exact silence), monotone counts. Test-setup mistakes fixed on the way: 3 s is more than one window at 44.1 kHz; the bumps must be inside one window because the prominence is of each window's own maximum (the spec's behavior).

### Implementation for User Story 3

- [x] T011 [US3] Run the tests of T010 and fix `local_peaks.py` for whatever they find (the conversion, the keywords, the order of checks). Mutation checks, each caught and restored: the range limits moved by one (99, 2001, −1, 101), a boolean accepted, the settings checked after reading the audio, the prominence applied to the file's maximum, a distance of 0 allowed, the distance rounded down.
  - Done: 13 mutations of the settings handling (`scratchpad/more_023_settings.py`), all caught; no code change was needed.

**Checkpoint**: all three stories work together.

---

## Phase 6: Polish and cross-cutting

- [x] T012 [P] README (`README.md`, CRLF kept): a **Local peaks** paragraph: what is measured (the overall energy: per 32-sample window the average of the left and right standard deviations, a running window of 4,096 of them, `scipy.signal.find_peaks`), the two settings, their ranges and defaults, what each peak records, how to ask for the energy and rate (`energy_at`, `rate_at`, `*_at_time`) with the before-the-first and after-the-last rules, that it is a backend measurement not yet used by the job or the pictures, and that a position is exact to 32 samples. Mark `specs/023-local-peaks/checklists/requirements.md` as is (all checked).
  - Done: README: a **Local peaks** section (CRLF kept) before "Audio frames UI".
- [x] T013 Final verification: the whole backend suite (temporary default colormap) with the per-file counts compared to T001 (nothing dropped, only `test_local_peaks.py` added), the frontend suite, typecheck and build (unchanged), the four reference hashes equal to T001 and no existing file modified except `README.md` (check `git status`), the 60 s timing of quickstart section 4 (under 5 s), the click-track try-out of quickstart section 3 (`scratchpad/peaks_try.py`), and a note in the report that the Spec Kit setup scripts could not be run and why. Mark all tasks `[x]` with a Done line each.
  - Done: Backend 3,346 tests pass (3,210 before + 136 new in `test_local_peaks.py`; no other file's count changed), the frontend was not touched (515 tests and a clean typecheck at the baseline), the four reference hashes equal, `git status`: only `README.md` modified plus the new files; click-track try-out: 59 of 59 clicks, worst distance 22 samples, first rate 60, others 119.84 to 120.01, energy and rate answers as specified; 60 s stereo file measured in 0.03 s. The Spec Kit setup scripts could not be run (PowerShell execution policy), so `plan.md` and `tasks.md` were written by hand from the templates.

---

## Dependencies and order

- T001 first. T002 and T003 are independent of each other (T004 needs both).
- US1: T004 (tests) before T005; T006 after T005.
- US2 needs US1 (it asks a result that T005 produces): T007 before T008; T009 after T008.
- US3's checks exist since T003 and the conversion since T005, so T010 may be written in parallel with T007; T011 after T005.
- T012 any time after T008; T013 last.

## Parallel opportunities

- T002 and T003 (different files).
- T004, T007 and T010 write into one test file, so they are written in turn but can be drafted together before any implementation.
- T012 (README) alongside T009 to T011.

## Implementation strategy

MVP is US1 (the peaks list); US2 is what a later visualization will use, so it follows at once; US3 mostly verifies what US1 already does by default. Nothing user-visible changes in this feature, so the end of Phase 5 is a complete delivery.
