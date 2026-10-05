---

description: "Task list for Audio Upload and Frame Visualization UI"
---

# Tasks: Audio Upload and Frame Visualization UI

**Input**: Design documents from `/specs/002-audio-frames-ui/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/http-api.md, quickstart.md

**Tests**: Included. The plan specifies pytest tests for the backend and vitest for the frontend's pure helpers. Components are checked with `vue-tsc`, the build, and the quickstart.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2 or US3

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 In `backend/app/config.py` add settings: `audio_temp_dir` = system temp dir / `music-visualizer` / `audio`, `frames_temp_dir` = system temp dir / `music-visualizer` / `frames` (always a different directory from the audio one), `max_audio_bytes` = 200 * 1024 * 1024, `max_frames` = 30000, `min_window_size` = 256, `max_window_size` = 32768, `min_frame_rate` = 1, `max_frame_rate` = 60. Keep the existing `max_upload_bytes` (20 MB) unchanged for the image endpoint.
- [x] T002 [P] In `frontend/package.json` add `vitest` as a dev dependency and a `"test": "vitest run"` script, then run `npm install` in `frontend/`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Make the feature 001 analysis reusable without re-reading the file

- [x] T003 In `backend/app/services/note_analysis.py` refactor without changing behavior: make `_read_wav` public as `read_wav(path)` returning `(file_rate, left, right)`; extract the window loop of `analyze_wav` into a public `analyze_channels(left, right, sample_rate, window_size) -> AnalysisResult`; make `analyze_wav` call `read_wav`, issue the sample-rate mismatch warning, then call `analyze_channels`; add a `sample_count: int` field to `AnalysisResult` (samples per channel, set by `analyze_channels`) and keep `AnalysisResult` frozen
- [x] T004 Run `pytest backend/tests/test_note_analysis.py` from `backend/` and confirm all feature 001 tests still pass unchanged. Add one test there that `analyze_wav(...).sample_count` equals the number of samples written to a temporary WAV.

**Checkpoint**: Reusable analysis in place, feature 001 tests green.

---

## Phase 3: User Story 1 - Submit an audio file and see its frames (Priority: P1) 🎯 MVP

**Goal**: Pick a file and settings in the browser, submit, and see the first frame with a summary. The server stores the audio and the frames in separate temp directories.

**Independent Test**: Submit a one-note WAV. The image count equals `ceil(duration × fps)`, the note's square is the brightest, and a silent file gives all-black frames.

### Tests for User Story 1

- [x] T005 [P] [US1] Create `backend/tests/test_frame_rendering.py` with tests for: `frame_count(sample_count, sample_rate, frame_rate)` equals `ceil(duration * fps)` (for example 10 s at 30 fps is 300, and 10.01 s is 301); frame averaging when several windows start in a period (the result is their mean); when a window is longer than a frame period (a frame with no window start uses the window covering the start of its period); the last partial period is kept; brightness is `round(255 * value / file_max)` with the file maximum giving 255 and all-zero input giving all 0; the grid puts note `n` at row `n // 11`, column `n % 11` with 20 × 20 squares, a 220 × 160 grayscale PNG, and no gaps; identical input gives identical bytes
- [x] T006 [P] [US1] Create `backend/tests/test_jobs_api.py` with a fixture that points `settings.audio_temp_dir` and `settings.frames_temp_dir` at `tmp_path` subfolders and a helper that builds WAV bytes from float audio. Add tests for `POST /api/jobs`: a one-note stereo WAV returns 200 with the fields in `contracts/http-api.md`, `frame_count` equals `ceil(duration * fps)`, one PNG per frame exists in `<frames>/<job_id>/`, `audio.wav` exists in `<audio>/<job_id>/`, the two roots are different directories, and the brightest square of the first frame is the note's square; a silent WAV gives frames that are all black; two submissions get different `job_id`s and separate folders; `GET /api/jobs/{job_id}/frames/{index}` returns `image/png` 220 × 160 grayscale with a `Cache-Control` header; invalid job ids (`../x`, uppercase, short) and out-of-range indexes return 404
- [x] T007 [P] [US1] Create `frontend/src/lib/validation.test.ts` with vitest tests for `validateWindowSize` (accepts 2048, 256, 32768; rejects 255, 32769, 0, -1, 2048.5, empty, "abc"), `validateFrameRate` (accepts 1, 30, 60, 29.97; rejects 0, 61, empty, "abc"), and `validateFile` (rejects null and a name not ending in `.wav`, case-insensitively; accepts `Song.WAV`); each rejection returns a message containing the allowed range or the reason

### Implementation for User Story 1

- [x] T008 [US1] Create `backend/app/services/frame_rendering.py` with: constants `GRID_COLUMNS = 11`, `GRID_ROWS = 8`, `SQUARE_PIXELS = 20`; `frame_count(sample_count, sample_rate, frame_rate)` using `ceil(sample_count * frame_rate / sample_rate - 1e-9)`; `average_frames(result: AnalysisResult, frame_rate, frame_count)` returning shape `(frame_count, 88)` using `lo = ceil(f * sr / (fps * W) - 1e-9)` and `hi = ceil((f + 1) * sr / (fps * W) - 1e-9)` over a cumulative sum of the window rows, falling back to window `floor(f * sr / (fps * W))` clamped to the last window when `lo >= hi`; `to_gray_levels(frames)` giving uint8 `round(255 * value / file_max)` (all zero when the maximum is 0); `render_frame(levels_row) -> PIL.Image` building the 8 × 11 grid (note `n` at row `n // 11`, column `n % 11`) enlarged with `np.repeat` to 160 × 220 mode `"L"`; `write_frames(frames, directory)` saving `frame_000000.png` and up with `compress_level=1`
- [x] T009 [US1] Create `backend/app/routers/jobs.py` with `POST /jobs` as a plain `def` endpoint taking `file: UploadFile`, `window_size: str = Form(...)`, `frame_rate: str = Form(...)`: parse and range-check both with messages like "The window size must be a whole number from 256 to 32768." (HTTP 400, `detail` string); create `job_id = uuid.uuid4().hex`; copy the upload into `<audio_temp_dir>/<job_id>/audio.wav` (the original name is never used for a path); call `read_wav`, `analyze_channels`, `average_frames`, `write_frames` into `<frames_temp_dir>/<job_id>/`; return the JSON from the contract (`file_name` is the base name only, `duration_seconds = sample_count / sample_rate`, `frame_url_template` with a literal `{index}`)
- [x] T010 [US1] In `backend/app/routers/jobs.py` add `GET /jobs/{job_id}/frames/{index}`: accept `job_id` only if it matches `^[0-9a-f]{32}$` and `index` only as a non-negative integer, build the path from the settings root, return `FileResponse` with `media_type="image/png"` and `Cache-Control: public, max-age=31536000, immutable`, and `404 {"detail": "Frame not found."}` otherwise; register the router in `backend/app/main.py` with prefix `/api`
- [x] T011 [US1] Run `pytest` from `backend/` and fix failures in T005, T006 and the existing tests
- [x] T012 [P] [US1] Create `frontend/src/lib/validation.ts` exporting `WINDOW_SIZE_RANGE`, `FRAME_RATE_RANGE`, `validateWindowSize(text)`, `validateFrameRate(text)`, `validateFile(file)` that each return an error message string or `null`, matching T007; run `npm test` in `frontend/`
- [x] T013 [P] [US1] Create `frontend/src/api.ts` with the `JobResult` type from the contract, `submitJob(file, windowSize, frameRate): Promise<JobResult>` (POST multipart to `/api/jobs`, throw an `Error` whose message is the response `detail`, or a plain "Could not reach the server" message on a network failure), and `frameUrl(result, index)` replacing `{index}` in `frame_url_template`
- [x] T014 [US1] Create `frontend/src/components/UploadForm.vue`: a `.wav` file input showing the chosen name and size; window size (default 2048) and frame rate (default 30) number inputs, each showing its allowed range and its validation message; a Submit button disabled when the file or either field is invalid or `busy` is true; emit `submit` with the file and numbers; keep field values in every state
- [x] T015 [US1] Replace `frontend/src/App.vue` (and remove `frontend/src/components/HelloWorld.vue`): hold the state `idle | busy | done | error`, call `submitJob`, show a busy indicator while waiting, show the summary (file name, duration, sample rate, window size, frame rate, frame count) and the first frame image from `frameUrl(result, 0)` scaled up with `image-rendering: pixelated`, replace the previous result only when a new submission succeeds; add minimal readable styling
- [x] T016 [US1] Run `npm run typecheck` and `npm run build` in `frontend/` and fix errors

**Checkpoint**: Select, submit, and view the first frame all work; audio and frames land in separate temp folders.

---

## Phase 4: User Story 2 - Play the frames as an animation (Priority: P2)

**Goal**: Play, pause, loop and scrub through the frames at the chosen frame rate.

**Independent Test**: Submit a file whose note changes partway; playback shows the bright square move at the right frame, and dragging the slider shows the matching frame and time.

### Tests for User Story 2

- [x] T017 [P] [US2] Create `frontend/src/lib/playback.test.ts` with vitest tests for: `frameAtElapsed(startFrame, elapsedSeconds, frameRate, frameCount, loop)` (0.5 s at 30 fps from frame 0 is frame 15; stops at `frameCount - 1` and reports finished when not looping; wraps around when looping; a long stall skips ahead to the right frame instead of crawling), `frameTime(index, frameRate)` (frame 45 at 30 fps is 1.5 s), and `preloadRange(index, frameCount, ahead)` (clamped to valid indexes)

### Implementation for User Story 2

- [x] T018 [US2] Create `frontend/src/lib/playback.ts` with `frameAtElapsed`, `frameTime` and `preloadRange` as specified in T017; run `npm test`
- [x] T019 [US2] Create `frontend/src/components/FramePlayer.vue` taking `result: JobResult` as a prop: show the current frame image (pixelated scaling); a range slider over `0 .. frame_count - 1` and the current time in seconds; play/pause and loop controls; drive playback with `requestAnimationFrame` using `frameAtElapsed` so the rate holds even when ticks are late; stop on the last frame unless looping; preload upcoming frames (`preloadRange`, about 30 ahead) with `new Image()`; stop playback and reset to frame 0 when a new `result` arrives; cancel the animation frame on unmount
- [x] T020 [US2] In `frontend/src/App.vue` replace the single first-frame image with `<FramePlayer>` shown in the `done` state; run `npm run typecheck` and `npm run build`

**Checkpoint**: Animation playback works with all controls.

---

## Phase 5: User Story 3 - Clear feedback when something is wrong (Priority: P3)

**Goal**: Every bad input or failure gives a plain message, and the user can fix it and retry without reloading.

**Independent Test**: A text file renamed `.wav`, window size 0, a too-low sample rate file, an oversize file and a stopped server each show a clear message, and a correct resubmission then works.

### Tests for User Story 3

- [x] T021 [P] [US3] In `backend/tests/test_jobs_api.py` add error tests (each checks the status, a `detail` string naming the problem, and that no folder for the attempt remains in either temp root): a text file named `x.wav` (400, "Could not read"); a 3-channel WAV (400); a WAV with no samples (400, "no audio"); `window_size` of `0`, `255`, `32769`, `2048.5`, `abc` and missing (400, mentions the range); `frame_rate` of `0`, `61`, `abc` and missing (400); a request that would make more than `max_frames` frames, with `max_frames` lowered through `monkeypatch` (400, mentions the count and the limit, and the analysis was not run); a WAV at 8000 Hz (400, contains "too low"); an upload over `max_audio_bytes`, lowered through `monkeypatch` (413, mentions the limit); a file named `../../evil.wav` is stored only under the job folder and nothing is written outside the temp roots
- [x] T022 [P] [US3] Add tests to `frontend/src/lib/validation.test.ts` for the exact message text shape: each message states the allowed range (for example "from 256 to 32768") so the UI can show it unchanged

### Implementation for User Story 3

- [x] T023 [US3] In `backend/app/routers/jobs.py` stream the upload to disk in 1 MB pieces while counting bytes, stopping with 413 "The file is larger than the 200 MB limit." (using `settings.max_audio_bytes`) and deleting the partial file when exceeded
- [x] T024 [US3] In `backend/app/routers/jobs.py` add the pre-analysis checks and error mapping: convert `AudioAnalysisError` from `read_wav` and `analyze_channels` to 400 with the same message; reject `sample_count == 0` with "The file contains no audio."; compute `frame_count` and reject more than `settings.max_frames` with a message giving both numbers and suggesting a lower frame rate or shorter file, before calling `analyze_channels`; wrap the rest so any other exception returns 500 "Something went wrong while creating the frames." and is logged
- [x] T025 [US3] In `backend/app/routers/jobs.py` make a failed submission leave nothing behind: on any error after the job folders are created, remove `<audio_temp_dir>/<job_id>` and `<frames_temp_dir>/<job_id>` (use a try/except that re-raises after cleanup)
- [x] T026 [US3] Run `pytest` from `backend/` and fix failures in T021
- [x] T027 [US3] In `frontend/src/App.vue` and `frontend/src/components/UploadForm.vue` show the error state: a visible, readable message area (use `role="alert"`) with the server's `detail` or the connection failure text; keep the form's values; clear the message on the next submission; make sure a failed submission does not remove the previous successful result until the new one succeeds; run `npm run typecheck` and `npm run build`

**Checkpoint**: All three stories work, and errors recover without a reload.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T028 Run the whole backend suite (`pytest` from `backend/`) and the frontend checks (`npm test`, `npm run typecheck`, `npm run build` in `frontend/`) and confirm all pass
- [x] T029 Start the backend (`uvicorn app.main:app` from `backend/`) and run a real submission of `backend/audio/fotr-intro1-echo.wav` at window 2048 and 30 fps, for example with `curl -F file=@... -F window_size=2048 -F frame_rate=30 http://localhost:8000/api/jobs`. Record the response, the elapsed time (SC-002 targets 60 s for a 3-minute file, about 5,400 frames), the number of PNGs on disk, and that audio and frames are in separate temp folders. If SC-002 is missed, report the measured time and the likely cause instead of changing the spec.
- [x] T030 Open the built app in a browser, if one is available to drive, or otherwise report that the browser walkthrough in `quickstart.md` (steps 3 and the playback timing of SC-006) was not run and must be done by hand. **Not run: no browser could be driven from this session. The frontend is covered by vitest, `vue-tsc` and the production build only; the walkthrough and SC-006 are still to be checked by hand.**
- [x] T031 [P] Update `README.md` with the new endpoints, the temp directory locations and how to change them (`MV_AUDIO_TEMP_DIR`, `MV_FRAMES_TEMP_DIR`), the limits, `npm test`, and a short "how to use the UI" note
- [x] T032 Mark completed tasks `[x]` in this file

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6.
- US2 needs the `JobResult`, `api.ts` and `App.vue` from US1. US3 hardens the US1 router and UI, so it follows them.
- Backend and frontend tasks within a story are independent of each other and can run in parallel (T005–T007, T012–T013).
- Write each story's tests first and see them fail before implementing.
- T009, T010, T023, T024 and T025 all edit `backend/app/routers/jobs.py`, and T015, T020 and T027 all edit `frontend/src/App.vue`, so those are sequential.

## Implementation Strategy

- **MVP**: Phases 1 to 3. This gives upload, frames and a first-frame view.
- **Then**: Phase 4 adds animation. Phase 5 adds the recovery behavior. Phase 6 checks the real file and timing, and documents the result.

## Change after implementation

- Window size became a dropdown of the powers of 2 from 4096 to 32768 (default 4096), at the user's request. The task descriptions above (T001, T007, T014, T021, T022) show the original 256–32768 free-entry wording and are left as written. The code, tests, spec, contract and README reflect the dropdown.
