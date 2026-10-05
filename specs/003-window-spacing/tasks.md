---

description: "Task list for Window Spacing Parameter"
---

# Tasks: Window Spacing Parameter

**Input**: Design documents from `/specs/003-window-spacing/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/http-api-changes.md, quickstart.md

**Tests**: Included, following the plan: pytest for the backend and vitest for the frontend's pure modules. Components are checked with `vue-tsc`, the build and the quickstart.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2 or US3

## Phase 1: Setup

- [x] T001 In `backend/app/config.py` add the setting `max_windows: int = 60000` with a comment saying it caps the analysis windows per submission

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Arbitrary window starts in the analysis, the step rules, and frame averaging from window starts. All three stories use these.

### Tests first

- [x] T002 [P] Create `backend/tests/test_window_spacing.py` with tests for: `default_spacing(sample_rate, frame_rate, window_size)` equals `floor(10**6 * (sample_rate / frame_rate) / window_size) / 10**6` for this table (44100, 30, 4096) → 0.358886, (44100, 60, 4096) → 0.179443, (44100, 60, 8192) → 0.089721, (48000, 30, 4096) → 0.390625, (44100, 30, 32768) → 0.044860; the default never makes `default * window_size` exceed `sample_rate / frame_rate`; for every frame rate 1 to 60, each window size 4096 to 32768 and sample rates 44100 and 48000, a window start sequence built from the default puts at least one start in every frame period; `resolve_step(spacing, window_size)` returns `(spacing_used, step, raised)` with `(0.25, 8192)` → `(0.25, 2048.0, False)`, `(1, 4096)` → `(1, 4096.0, False)`, `(2, 4096)` → `(2, 8192.0, False)`, `(0.00001, 4096)` → `(1/4096, 1.0, True)`, and exactly one sample is not "raised" (`(1/4096, 4096)` → `(1/4096, 1.0, False)`)
- [x] T003 [P] In `backend/tests/test_note_analysis.py` add tests for: `window_starts(sample_count, step)` gives `rint(k * step)` for `k` while below the sample count (step 2048 over 10,000 samples → 0, 2048, 4096, 6144, 8192; step 1228.8 gives the nearest whole samples counted from the start, so the 100th start is 122,880); `window_count(sample_count, step)` equals `len(window_starts(...))` for many steps (including 1, 1.5, 0.5-boundary cases, values larger than the file) and for 0 samples (0 windows); `analyze_channels(..., step=None)` gives the same frames as before (compare with consecutive-window analysis done through `NoteBinAnalyzer.analyze` on slices) and `result.starts` equals `arange(count) * window`; with `window_size=8192` and `step=2048` the starts are 0, 2048, 4096; for audio that is silent until a tone begins at sample 2048 and continues, the second window (start 2048) holds the tone at strictly greater strength than the first window; a step above the window size (gaps) analyzes only the windows at the starts; a step of 1 on a short file gives one window per sample; `window_start_times()` equals `starts / sample_rate`
- [x] T004 [P] In `backend/tests/test_frame_rendering.py` add tests for `average_frames` with explicit `starts`: overlapping windows (window starts every 0.05 s, frames 0.2 s, so four windows per frame, which are averaged); gaps (window starts every 0.4 s with frames of 0.2 s, so odd frames use the most recent earlier window); a start exactly on a frame boundary belongs to the later frame; hand-built results without `starts` behave exactly as before (the existing tests in this file stay unchanged and must still pass)

### Implementation

- [x] T005 Create `backend/app/services/window_spacing.py` with `default_spacing(sample_rate, frame_rate, window_size)` returning `math.floor(1e6 * (sample_rate / frame_rate) / window_size + 1e-9) / 1e6`, and `resolve_step(spacing, window_size)` returning `(spacing_used, step, raised)` where `step = spacing * window_size`, and if `step < 1` the result is `(1 / window_size, 1.0, True)`; document that both are mirrored in `frontend/src/lib/spacing.ts`
- [x] T006 In `backend/app/services/note_analysis.py` add `window_starts(sample_count, step)` (an int array of `rint(k * step)` for each `k` whose start is below `sample_count`) and `window_count(sample_count, step)` (closed form `ceil((sample_count - 0.5) / step - 1e-9)` corrected by at most one against `rint` at the boundary, 0 for no samples); add `starts: np.ndarray | None = None` to `AnalysisResult` with a property `window_starts` falling back to `arange(window_count) * window_size`, and make `window_start_times()` use it; add an optional `step: float | None = None` argument to `analyze_channels` (default `window_size`) that computes the starts, processes windows in chunks (each chunk converts one contiguous segment of the audio with `_to_float` once, builds windows from it by index with zero padding past the end, and sizes chunks so a segment covers at most about `_CHUNK_SAMPLES` samples), and returns the result with `starts` set; keep `analyze_wav` and `NoteBinAnalyzer` unchanged
- [x] T007 In `backend/app/services/frame_rendering.py` change `average_frames` to use the window start samples: frame `f` covers sample positions `[f * sr / fps, (f + 1) * sr / fps)`; use `numpy.searchsorted(starts, boundary - 1e-6, side="left")` for both boundaries to find the windows starting inside the period, average them with a running sum, and where none start inside use the last window that started before the period (index `first - 1`, never below 0); update the module docstring to describe the new fallback
- [x] T008 Run `pytest` from `backend/` and fix failures in T002 to T004 and the existing tests

**Checkpoint**: The analysis and the frames support any spacing; spacing 1 reproduces the old results.

---

## Phase 3: User Story 1 - Choose how far apart analysis windows start (Priority: P1) 🎯 MVP

**Goal**: A spacing field the user can set, applied to the analysis, with the spacing, step and window count shown in the results.

**Independent Test**: Window size 8192, spacing 0.25 reports a step of 2048 samples; spacing 1 reports 8192; spacing 2 is accepted.

### Tests for User Story 1

- [x] T009 [P] [US1] In `backend/tests/test_jobs_api.py` add tests for the new `window_spacing` field: window size 8192 with `window_spacing=0.25` returns 200 with `window_spacing == 0.25`, `step_samples == 2048`, `spacing_raised == False`, and `window_count` equal to the number of starts below the sample count (use a 3-second file, which gives 16 windows); `window_spacing=1` gives `step_samples == 8192` and `window_count == ceil(samples / 8192)`; `window_spacing=2` is accepted with `step_samples == 16384`; a non-integer step (`window_spacing=0.3`, window 4096) reports `step_samples == 1228.8`; the same file and settings submitted twice give byte-identical first frames; frames with `window_spacing=1` equal the frames the analysis gives for consecutive windows (compare one frame image with one built directly from `analyze_channels` and `average_frames`)
- [x] T010 [P] [US1] Create `frontend/src/lib/spacing.test.ts` with vitest tests for `minSpacing(windowSize)` (4096 → 1/4096), `stepSamples(spacing, windowSize)` (0.25 and 8192 → 2048), `stepMilliseconds(spacing, windowSize, sampleRate)` (0.25, 8192, 44100 → about 46.4), `validateSpacing(text)` (accepts "0.25", "1", "2", "1e-3", 0.3; rejects "", "  ", "0", "-1", "abc", "Infinity", "NaN" with the message "The window spacing must be a number greater than 0."), and `formatSpacing(value)` (0.25 → "0.25", 0.358886 → "0.358886", 1 → "1", no exponent notation for values of at least 0.000001)

### Implementation for User Story 1

- [x] T011 [US1] In `backend/app/routers/jobs.py` accept `window_spacing: str | None = Form(None)`: parse it (a number that is finite and greater than 0, otherwise 400 "The window spacing must be a number greater than 0."), treat missing or empty as spacing 1 for now, call `resolve_step`, pass `step` to `analyze_channels`, and add `window_spacing`, `step_samples`, `window_count` (`len(result.starts)`) and `spacing_raised` to the response
- [x] T012 [US1] Run `pytest` from `backend/` and fix failures in T009
- [x] T013 [P] [US1] Create `frontend/src/lib/spacing.ts` exporting `minSpacing`, `stepSamples`, `stepMilliseconds`, `validateSpacing` and `formatSpacing` as in T010; run `npm test` in `frontend/`
- [x] T014 [US1] In `frontend/src/api.ts` add the `windowSpacing` argument to `submitJob` (sent as `window_spacing`) and the new fields to `JobResult` (`window_spacing`, `step_samples`, `window_count`, `spacing_raised`)
- [x] T015 [US1] In `frontend/src/components/UploadForm.vue` add a "Window spacing (× window size)" number input (`step="any"`, disabled while `busy`) bound to `spacingText`, validated with `validateSpacing`, with a hint under it showing the step in samples and milliseconds for the current value (using 44,100 Hz for now); block submit when invalid; pass the number to the `submit` event; update `frontend/src/App.vue` to pass it to `submitJob` and to show spacing used, step in samples, and windows analyzed in the results summary
- [x] T016 [US1] Run `npm test`, `npm run typecheck` and `npm run build` in `frontend/` and fix errors

**Checkpoint**: The spacing can be set and is applied and reported.

---

## Phase 4: User Story 2 - A default spacing that follows the other settings (Priority: P2)

**Goal**: The field always holds the right default for the current frame rate, window size and file, recalculated on every change.

**Independent Test**: 44,100 Hz file, 30 fps, window 4096 → 0.358886; 60 fps → 0.179443; window 8192 → 0.089721; a 48,000 Hz file gives a different value.

### Tests for User Story 2

- [x] T017 [P] [US2] In `frontend/src/lib/spacing.test.ts` add tests for `defaultSpacing(sampleRate, frameRate, windowSize)` using the same table as T002 ((44100, 30, 4096) → 0.358886, (44100, 60, 4096) → 0.179443, (44100, 60, 8192) → 0.089721, (48000, 30, 4096) → 0.390625, (44100, 30, 32768) → 0.04486), returning `null` for a frame rate that is empty, zero, negative or not a number; `DEFAULT_SAMPLE_RATE` is 44100; the default times the window size never exceeds `sampleRate / frameRate`
- [x] T018 [P] [US2] Create `frontend/src/lib/wavHeader.test.ts` with vitest tests for `readSampleRate(file)`: a hand-built `RIFF/WAVE` header with `fmt ` first returns 44100 and 48000 for the two rates; a header with a `LIST` chunk before `fmt ` still works; an `RF64` header works; a file that does not start with `RIFF`/`RF64`, a truncated file, an empty file, and a `RIFF` file with no `fmt ` chunk in the first 64 KB all return `null` without throwing; only the first 64 KB are read (a 1 MB file with the header at the start returns the rate)
- [x] T019 [P] [US2] In `backend/tests/test_jobs_api.py` add tests that a request with no `window_spacing` (and one with an empty string) behaves as the default: for a 3-second 44,100 Hz file at 30 fps and window 4096, the response has `window_spacing == 0.358886` and `window_count >= frame_count`; for a 48,000 Hz file the spacing is `0.390625`; the default response for a long enough file has at least one window starting in every frame period (check `window_count >= frame_count`)

### Implementation for User Story 2

- [x] T020 [P] [US2] In `frontend/src/lib/spacing.ts` add `DEFAULT_SAMPLE_RATE = 44100` and `defaultSpacing(sampleRate, frameRate, windowSize)` returning `Math.floor(1e6 * (sampleRate / frameRate) / windowSize + 1e-9) / 1e6`, or `null` when the frame rate is not a positive finite number; run `npm test`
- [x] T021 [P] [US2] Create `frontend/src/lib/wavHeader.ts` with `readSampleRate(file: Blob): Promise<number | null>`: read `file.slice(0, 65536)`, check `RIFF` or `RF64` then `WAVE`, walk the chunks (8-byte header, even padding) to `fmt `, and return the 32-bit little-endian sample rate at offset 4 of the chunk data; return `null` for anything else and never throw; run `npm test`
- [x] T022 [US2] In `backend/app/routers/jobs.py` make a missing or empty `window_spacing` use `default_spacing(file_rate, fps, window)` (computed after the file is read) instead of 1; run `pytest` from `backend/` and fix failures in T019
- [x] T023 [US2] In `frontend/src/components/UploadForm.vue` keep a `fileSampleRate` that starts at `DEFAULT_SAMPLE_RATE`; when the file input changes, read the rate with `readSampleRate` (ignore a result that arrives after a newer file was chosen) and use `DEFAULT_SAMPLE_RATE` when it returns `null` or no file is chosen; add a watcher on the window size, the frame rate text and `fileSampleRate` that sets `spacingText` to `formatSpacing(defaultSpacing(...))` immediately, leaving it unchanged when `defaultSpacing` returns `null`; initialize the field with the default for 4096, 30 and 44,100; use `fileSampleRate` in the step-milliseconds hint
- [x] T024 [US2] Run `npm test`, `npm run typecheck` and `npm run build` in `frontend/` and fix errors

**Checkpoint**: The default follows the frame rate, window size and file.

---

## Phase 5: User Story 3 - Sensible limits and clear feedback (Priority: P3)

**Goal**: A step below one sample is raised and reported, bad values are refused, and oversized requests are refused up front.

**Independent Test**: Spacing 0.00001 with window 4096 on a short file reports step 1 and a raised notice; 0, -1 and "abc" are refused; a tiny spacing on a long file is refused with the window count and the limit.

### Tests for User Story 3

- [x] T025 [P] [US3] In `backend/tests/test_jobs_api.py` add tests: `window_spacing=0.00001` with window 4096 on a short file (`monkeypatch` `max_windows` high enough, for example 100000, and use 0.3 seconds of audio) returns 200 with `step_samples == 1`, `window_spacing == 1/4096`, `spacing_raised == True`; spacing exactly `1/4096` is not marked raised; `window_spacing` of `0`, `-1`, `abc`, `nan`, `inf`, `-inf` returns 400 with "window spacing" and "greater than 0" and leaves nothing in either temp root; a request that would create more than `max_windows` (lower it with `monkeypatch` to 10 and use a 1-second file at spacing 0.01 with window 4096) returns 400 with the window count, the limit, "larger window spacing", and leaves nothing behind; the analysis is not run in that case (patch `analyze_channels` to fail if called); a spacing larger than the file (for example 1000) returns 200 with `window_count == 1`
- [x] T026 [P] [US3] In `frontend/src/lib/spacing.test.ts` add tests for `isBelowMinimum(spacing, windowSize)` (true for 0.00001 with 4096, false for exactly `1/4096` and above) and the minimum message text `The spacing will be raised to 0.000244 so the step is one sample.` for window 4096 (6 decimals of `1/4096`, trailing zeros trimmed)

### Implementation for User Story 3

- [x] T027 [US3] In `backend/app/routers/jobs.py` compute the window count with `window_count(samples, step)` after reading the file and before `analyze_channels`; if it exceeds `settings.max_windows`, remove the job folders and return 400 `This would create {count:,} windows; the limit is {limit:,}. Use a larger window spacing.`; make sure the parsing rules from T011 also reject `nan` and `inf` and the order of checks is: parameters, file read, no-audio, frame limit, window limit, analysis; run `pytest` from `backend/` and fix failures in T025
- [x] T028 [P] [US3] In `frontend/src/lib/spacing.ts` add `isBelowMinimum(spacing, windowSize)` and `minimumMessage(windowSize)`; run `npm test`
- [x] T029 [US3] In `frontend/src/components/UploadForm.vue` show the minimum message under the spacing field whenever the typed value is valid but below the minimum (without changing the typed value); in `frontend/src/App.vue` show a notice in the results when `spacing_raised` is true, such as "The window spacing was raised to {window_spacing} so the step is one sample."; make sure an error from the server (including the window-count error) is shown in the existing error area and the form keeps its values; run `npm test`, `npm run typecheck` and `npm run build` in `frontend/`

**Checkpoint**: All three stories work.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T030 Run the whole backend suite (`pytest` from `backend/`) and the frontend checks (`npm test`, `npm run typecheck`, `npm run build` in `frontend/`) and confirm all pass
- [x] T031 Start the backend on an unused port from `backend/` with the venv (check that the port is free first; do not stop or reuse a server the user is running) and run `backend/audio/fotr-intro1-echo.wav` through `POST /api/jobs` three ways: the default spacing at window 4096 and 30 fps (record the response, the time against SC-007, that `window_count >= frame_count`, and the PNG count), `window_spacing=0.25` at window 8192 (step 2048), and a deliberately tiny spacing that exceeds the window limit (record the refusal time against SC-008); also compare the frames from `window_spacing=1` before and after this feature using a copy of the previous behavior from `git stash` or by recomputing consecutive windows, to check SC-002; then stop the server and delete the job folders it created in the temp directories
- [x] T032 Report that the browser walkthrough in `quickstart.md` (step 3, including the live default refresh and the file header reading in a real browser) was not run if no browser can be driven from this session. **Not run: no browser could be driven from this session.** The default formula, the header reader, the validation and the minimum notice are unit-tested, and the form builds and type-checks, but the live refresh of the field in `UploadForm.vue` (its `watch`) and the file input handling have not been exercised in a browser and need a manual check.
- [x] T033 [P] Update `README.md`: describe the window spacing field, its default and when it is recalculated, the 1-sample minimum, the `window_spacing` request field and the new response fields, and the `MV_MAX_WINDOWS` setting
- [x] T034 Mark completed tasks `[x]` in this file

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6.
- US2 builds on the field and request plumbing from US1. US3 builds on both.
- Backend and frontend tasks within a story are independent and can run in parallel (for example T009 and T010, T017 to T019, T020 and T021).
- T011, T022 and T027 all edit `backend/app/routers/jobs.py`, and T015, T023 and T029 all edit `frontend/src/components/UploadForm.vue`, so those are sequential.
- Write each group's tests first and see them fail before implementing.

## Implementation Strategy

- **MVP**: Phases 1 to 3: a settable spacing that is applied and reported.
- **Then**: Phase 4 adds the automatic default and the file header reading, Phase 5 adds the limits and notices, and Phase 6 checks the real file, timing and regression against the old output.
