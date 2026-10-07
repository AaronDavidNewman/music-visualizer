---

description: "Task list for Energy Saturation"
---

# Tasks: Energy Saturation

**Input**: Design documents from `/specs/009-energy-saturation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/energy-api.md, quickstart.md

**Tests**: Included, following the plan: pytest for the energy definition, the saturation rule and the API, and vitest for the new validation and explanation text. Component behavior in the browser is checked by the quickstart steps.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root. Backend commands run in `backend/` with the venv's Python (`.venv/Scripts/python -m pytest`), frontend commands in `frontend/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2 or US3

## Phase 1: Setup

- [x] T001 Run `pytest` in `backend/` and `npm test`, `npm run typecheck` and `npm run build` in `frontend/` to confirm a green baseline before changing anything (425 backend and 140 frontend tests at the end of feature 008), and note the numbers

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Make the drawing code accept a saturation without changing any current result, so the stories can build on it.

- [x] T002 In `backend/app/services/frame_rendering.py` rename the constant `SATURATION` to `DEFAULT_SATURATION` (still 0.5; comment that it is only used by helpers called without a saturation, never by the job path) and give `tile_colors` and `render_frame` an optional `saturation: float = DEFAULT_SATURATION` argument used in place of the fixed value in the HSV conversion (a single number from 0 to 1 for all tiles; raise `ValueError` outside that range). Update the import and the `SATURATION == 0.5` assertion in `backend/tests/test_frame_rendering.py` (lines 15 and 495) to `DEFAULT_SATURATION`, then run `pytest` in `backend/` and confirm all tests still pass unchanged in meaning

**Checkpoint**: Same output as before; the drawing code can take a saturation.

---

## Phase 3: User Story 1 - Colors get richer when the music is energetic (Priority: P1) 🎯 MVP

**Goal**: Each frame's saturation comes from its energy (root 1, the default), replacing the fixed 50% (FR-001 to FR-009, FR-013, FR-014).

**Independent Test**: Quickstart sections 2 to 4 "Story 1". With the default settings the loud, quarter-loud and silent stretches of the test file give saturation 100%, 25% and 0%.

### Tests for User Story 1

- [x] T003 [P] [US1] Create `backend/tests/test_energy.py` with tests for `internal_window(sample_rate)` and `frame_energies(left, right, sample_rate, frame_rate, frames)` from `app/services/energy.py` (written in T005): `internal_window` is 32 at 44,100, 35 at 48,000, 16 at 22,050 and 8 at 11,025 and never below 2; with both channels alternating +0.5 and -0.5 the energy is 0.5 (within 0.001); left alternating +0.5/-0.5 with the right silent gives 0.25; a constant level (also a large DC offset) gives 0; a mono signal (the same array passed as both channels) gives that signal's own spread; the energy is the mean over the full internal windows laid end to end from the frame's first sample (use a frame holding windows of two different amplitudes and check the mean); a leftover shorter than the window at the end of a frame is ignored when a full window exists; frame boundaries are `rint(f * rate / frame_rate)` so consecutive frames tile the file; integer PCM input is scaled to about -1..1 first (int16 full scale gives 0.5 for the alternating example at amplitude 0.5 of full scale); the result has one value per requested frame and is deterministic
- [x] T004 [P] [US1] In `backend/tests/test_frame_rendering.py` add tests for the energy-to-saturation rule and its use: `saturation_sequence(energies, energy_root, smoothing)` with root 1 returns each energy divided by the largest (the largest is exactly 1.0, a zero energy is 0.0); all zeros when every energy is 0 (no error); values always within 0..1; with smoothing above 0 the result equals `smooth_frames` applied to the mapped column and with smoothing 0 equals the mapped values; `tile_colors(..., saturation=1.0)` has darkest channel 0 for every tile with a nonzero value, `saturation=0.0` gives three equal channels, the brightest channel always equals the tile's displayed gray level, and changing only the saturation never changes any tile's value or hue (compare the HSV of the results); a tile with value 0 stays black; `write_frames(frames, directory, brightness, smoothing, energies=..., energy_root=...)` on a three-frame input with energies in the ratio 1 : 0.25 : 0 writes PNGs whose tiles have saturation 1.0, 0.25 and 0 (read the PNGs back, convert a tile with a high value to HSV, within 0.02), and with no energies given it still uses `DEFAULT_SATURATION` for every frame; `write_frames` raises `ValueError` if the number of energies differs from the number of frames

### Implementation for User Story 1

- [x] T005 [US1] Create `backend/app/services/energy.py` with `INTERNAL_WINDOW_AT_44K = 32`, `REFERENCE_RATE = 44100`, `internal_window(sample_rate) -> int` returning `max(2, floor(32 * sample_rate / 44100 + 0.5))`, and `frame_energies(left, right, sample_rate, frame_rate, frames) -> np.ndarray` (float64, shape `(frames,)`). Per research Decisions 3 and 4 and data-model.md "Energy of a frame": frame `f` covers `rint(f * sample_rate / frame_rate)` to `min(rint((f + 1) * sample_rate / frame_rate), samples)`; take that slice of each channel, convert with the analysis's `_to_float` (import it from `note_analysis.py`), keep `n = (end - start) // w` full windows, reshape to `(n, w)`, take `np.std(axis=1)` (population, `ddof=0`) per channel, average the two channels, then average the windows; if `n == 0` measure the samples that exist as one window (0 or 1 samples give 0); if `left is right` (a mono file) measure it once. Make T003 pass
- [x] T006 [US1] In `backend/app/services/frame_rendering.py` add `MIN_ENERGY = 1`, `MAX_ENERGY = 8`, `DEFAULT_ENERGY = 1` and `saturation_sequence(energies, energy_root=DEFAULT_ENERGY, smoothing=DEFAULT_SMOOTHING) -> np.ndarray` returning, per data-model.md "Saturation of a frame", `(energy / peak) ** (1 / energy_root)` (zeros if the peak is 0), then `smooth_frames` on the column of values (reshape to `(-1, 1)` and back), values within 0..1; raise `ValueError("The energy must be a whole number from 1 to 8.")` for a root that is not a whole number from 1 to 8 (bools refused, as `boost_levels` does). Extend `write_frames` with `energies: np.ndarray | None = None, energy_root: int = DEFAULT_ENERGY`: when energies are given (one per frame, else `ValueError`), compute `saturation_sequence` and pass each frame's value to `tile_colors`; when `None`, use `DEFAULT_SATURATION` for all frames. Update the module and function docstrings (saturation is no longer fixed). Make T004 pass
- [x] T007 [US1] In `backend/app/routers/jobs.py` compute `energies = frame_energies(left, right, file_rate, fps, frames)` (import from `..services.energy`) after the frame count is known and pass `energies=energies` to `write_frames` (the root is the default 1 until User Story 2 adds the field); update the comment above `write_frames` to say it also smooths the saturation
- [x] T008 [US1] In `backend/tests/test_jobs_api.py` update the two tests that assume 50% saturation, `test_every_tiles_brightest_channel_is_its_gray_level_and_its_darkest_is_half` (around line 821) and the pastel assertion near line 862: the brightest channel must still equal the tile's gray level; the darkest channel must now equal `max * (1 - S)` (within 1) where `S` is the frame's saturation computed in the test from its own independent numpy calculation of the file's energy (not by calling the new code), and rename the first test to match what it now checks
- [x] T009 [US1] In `backend/tests/test_jobs_api.py` add an API test with a generated mono WAV of three 1-second stretches at 44.1 kHz (uniform noise of amplitude 0.8, of amplitude 0.2, and silence) at 30 fps with default settings: a frame in the loud stretch has saturation 1.0, one in the quiet stretch about 0.25 (within 0.05, noise is random but seeded), and one in the silent stretch is entirely black; the same file posted twice gives identical frame bytes (FR-013); a silent file creates frames without error and every pixel is black
- [x] T010 [US1] Run `pytest` in `backend/` and confirm everything passes

**Checkpoint**: Saturation follows energy with the default root, through the API.

---

## Phase 4: User Story 2 - Choose how energy is normalized with a root from 1 to 8 (Priority: P2)

**Goal**: The Energy setting in the API and on the page (FR-010 to FR-012).

**Independent Test**: Quickstart "Story 2". At Energy 1, 2 and 8 the quarter-loud frame is 25%, 50% and about 84% saturated; invalid values are refused.

### Tests for User Story 2

- [x] T011 [P] [US2] In `backend/tests/test_jobs_api.py` add tests for the `energy` form field: not sent gives `"energy": 1` in the response; 1 to 8 are accepted, including `"2.0"`; with the three-stretch file from T009 the quiet frame's saturation is about 0.25, 0.5, 0.63 and 0.84 at 1, 2, 3 and 8 while the loud frame stays 1.0 and the silent one 0; each of `0`, `9`, `2.5`, `abc`, `-1`, `nan`, `inf` and the empty string sent as `energy=` returns 400 with detail "The energy must be a whole number from 1 to 8." and creates no job directory; the refusal happens even when no file is attached
- [x] T012 [P] [US2] In `frontend/src/utilities/validation.test.ts` add tests for `validateEnergy`: whole numbers 1 to 8 (as numbers and as text, `"2"`, `" 3 "`) return null; `0`, `9`, `2.5`, `""`, `"abc"`, `NaN` and `Infinity` return the message "The energy must be a whole number from 1 to 8."; and for `energyHelp` in `frontend/src/utilities/help.test.ts`: the text states the range from `ENERGY_RANGE` and says that higher values lift quiet passages

### Implementation for User Story 2

- [x] T013 [US2] In `backend/app/routers/jobs.py` add `_parse_energy(text, sent)` modeled on `_parse_brightness`: not sent returns `DEFAULT_ENERGY`; anything sent must be a whole number from `MIN_ENERGY` to `MAX_ENERGY` (1 to 8) else `HTTPException(400, "The energy must be a whole number from 1 to 8.")` built from the constants; add the optional `energy: str | None = Form(None)` parameter, parse it with the other settings before the file check, pass `energy_root=` to `write_frames`, and add `"energy": energy_root` to the response. Make T011 pass
- [x] T014 [P] [US2] In `frontend/src/utilities/validation.ts` add `ENERGY_RANGE = { min: 1, max: 8 }`, `DEFAULT_ENERGY = 1` and `validateEnergy(value: string | number): string | null` (a whole number from 1 to 8, same style as `validateBrightness`); in `frontend/src/utilities/help.ts` add `energyHelp` (whole number 1 to 8, built from `ENERGY_RANGE`; higher values make quiet passages more colorful; 1 is a straight proportion of the loudest). Make T012 pass
- [x] T015 [P] [US2] In `frontend/src/api.ts` add `energy: number` to `JobSettings` and `JobResult` and `body.append("energy", String(settings.energy))` in `submitJob`
- [x] T016 [US2] In `frontend/src/components/SettingsForm.vue` add `energyText = ref(String(DEFAULT_ENERGY))`, `energyError = computed(() => validateEnergy(energyText.value))` included in `canSubmit`, and `energy: Number(energyText.value)` in the submitted settings. In the template put Brightness and Energy together in a second `field-row` (same markup as the first row: field head with label and `InfoPopover label="energy" :text="energyHelp"`, a `type="number"` input with `step="1"`, `:min`/`:max` from `ENERGY_RANGE`, `inputmode="numeric"`, `id="energy"`, `:disabled="busy"`, and the error under it only when invalid); Brightness keeps its own markup and rules
- [x] T017 [US2] In `frontend/src/App.vue` add `<li>Energy: {{ result.energy }}</li>` to the result summary after Brightness
- [x] T018 [US2] Run `npm test`, `npm run typecheck` and `npm run build` in `frontend/`, then verify Story 2 in the browser using `quickstart.md` section 4 "Story 2" (the field next to Brightness, the popover, invalid values, the summary line, quarter-loud frame at 25%, 50% and about 84%)

**Checkpoint**: The setting works end to end.

---

## Phase 5: User Story 3 - The measure behaves the same at any sample rate or channel layout (Priority: P3)

**Goal**: Independence from sample rate, bit depth and channel layout, and sensible behavior on short frames (FR-002, FR-004, FR-005, spec Story 3).

**Independent Test**: Quickstart "Story 3".

- [x] T019 [P] [US3] In `backend/tests/test_energy.py` add tests: the same sound (amplitude-modulated seeded noise with blocks of equal duration) generated at 44,100 Hz and at 22,050 Hz gives `saturation_sequence` values for matching frames that agree within 0.05; the same audio stored as uint8, int16, int32 and float32 gives the same energies within the rounding of the format; a stereo signal with one silent channel gives half the energy of the same signal in both channels; a frame period shorter than one internal window (call `frame_energies` directly with a frame rate of 5,000 at 44,100 Hz, a period of about 9 samples against a window of 32) and a final frame with fewer samples than one window measure the samples they have without error; a frame with a single sample has energy 0; 0 samples (a frame starting at or past the end) gives 0
- [x] T020 [US3] Run the tests from T019 and fix any defect they expose in `backend/app/services/energy.py` (for example off-by-one at the file end, or a 0-sample frame)
- [x] T021 [US3] In `backend/tests/test_jobs_api.py` add API tests: a 1.001-second file at 30 fps (a final frame of 44 samples) creates all frames without error; a 22,050 Hz file and a 48,000 Hz file create frames without error; a mono and a stereo-with-identical-channels file of the same signal give identical frames

**Checkpoint**: The measure is robust across formats.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T022 [P] Update `README.md`: the "Color" bullet that says saturation is fixed at 50% and that no saturation setting exists (feature 007) now says saturation follows the energy as defined in `specs/009-energy-saturation/data-model.md` (internal window of 32 samples at 44.1 kHz scaled with the rate, average of the left and right standard deviations, mean over the frame, relative to the loudest frame, raised to 1 over the Energy root), describe the Energy setting (whole number 1 to 8, default 1, the optional `energy` API field and `energy` in the response), and that the earlier 50% examples now describe `tile_colors` called without a saturation only
- [x] T023 Check SC-007: time `create_job` or its frame step on the same file on this branch and on `main` (for example the 90 MB sample in `backend/audio/`, or a 60-second stereo test file); the total must be no more than 25% longer. If `frame_energies` misses the budget, batch the frames that share an integer period into one vectorized call (research Decision 3) and re-run the tests
- [x] T024 Verify in the browser using `quickstart.md` sections 2 to 5 end to end through the real page (including the popover for Energy and that the layout still has no sideways scroll at 360 px with the new row), and record the saturation values read from downloaded frames
- [x] T025 Run the full checks one last time: `pytest` in `backend/` and `npm test`, `npm run typecheck`, `npm run build` in `frontend/`; confirm the counts are the baseline from T001 plus the new tests and that nothing else changed

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 (T002) → stories.
- **US1** (T003–T010) needs T002. T003 and T004 can be written in parallel (different files); T005 makes T003 pass, T006 makes T004 pass (T005 and T006 are independent files and can run in parallel after their tests); T007 needs T005 and T006; T008 and T009 need T007; T010 last.
- **US2** (T011–T018) needs US1. Backend (T011, T013) and frontend (T012, T014, T015) are independent of each other; T016 needs T014 and T015; T017 needs T015; T018 needs all.
- **US3** (T019–T021) needs T005 and T007 and is independent of US2 (T021 can run before or after the field exists, as it only uses defaults).
- Polish after the stories; T022 can run in parallel with T023 and T024.

## Parallel Example

```
T003 test_energy.py (definition)  |  T004 test_frame_rendering.py (saturation rule)
T005 energy.py  |  T006 frame_rendering.py
T011 backend field tests  |  T012 frontend validation/help tests  |  T015 api.ts
```

## Implementation Strategy

1. **MVP**: Phases 1, 2 and 3 (US1). Saturation follows the energy with the default root, through the API, with no new setting; the page already shows it.
2. **Increment**: US2 (the Energy setting in the API and page), then US3 (rate, format and edge-case coverage), each checked by its quickstart steps.
3. **Finish**: README, the 25% timing check, an end-to-end browser pass and the full test run.

---

## Implementation Notes

- **Counts**: backend 425 tests before and 539 after (114 new: 33 in `test_energy.py`, 48 in `test_saturation.py` and 33 in `test_energy_api.py`, counting parameter cases; the two updated job tests were changed, not added); frontend 140 before and 164 after (24 new: the energy validation cases and the explanation text). `typecheck` and `build` clean.
- **Where the tests went**: the saturation-rule and drawing tests of T004 are in a new `backend/tests/test_saturation.py` instead of being appended to the 800-line `test_frame_rendering.py` (which only had its `SATURATION` import renamed), and the API tests of T009, T011 and T021 are in a new `backend/tests/test_energy_api.py`. `test_jobs_api.py` gained the `energy` argument on its `post` helper, an independent `expected_saturations` helper, and the two updated tests (T008).
- **Test mistake fixed**: in T019 I first asserted that the first of two equal-amplitude blocks was exactly 100%; random noise made the other block slightly louder (0.997). The assertion is now that the loudest block is exactly 1.0. No code change was needed for T020.
- **Browser checks** (T018, T024) ran in headless Chrome over the DevTools protocol against the real page and the running backend, with the 3-second test file (loud noise, a quarter as loud, silence): the Energy field sits beside Brightness with an info button and popover; 0, 9, 2.5 and empty show the error and disable "Create frames"; the summary shows "Energy: n"; saturation read from the downloaded frames was 0.242 (root 1), 0.492 (root 2) and 0.836 (root 8) for the quiet frame, against 0.25, 0.5 and 0.84; the loud frame was above 0.95 and the silent frame black in every case; no sideways scroll at 360 px.
- **Nothing else changed** (quickstart section 5): the existing job tests for each tile's brightest channel and hue pass unchanged, so brightness and hue are as before; only saturation differs.
- **SC-007 (T023)**: on the 90 MB sample (341 s, 10,224 frames at 30 fps, window 4096) analysis took 1.02 s, averaging 0.02 s, `write_frames` 4.27 s before and 4.36 s with energies, and `frame_energies` 0.28 s: the job body went from 5.30 s to 5.68 s, 7.1% longer, inside the 25% budget, so the vectorized fallback was not needed.
- The existing backend on port 8000 (a debugger session running `uvicorn --reload`) picked up the changes, so it was used for the browser checks; the dev frontend was started and stopped by this session.
