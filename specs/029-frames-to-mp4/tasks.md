---

description: "Task list for Frames to MP4 (feature 029)"
---

# Tasks: Frames to MP4

**Input**: Design documents from `/specs/029-frames-to-mp4/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/video-api.md, quickstart.md

**Tests**: Written first for each story (the project's practice): the service with a fake runner, the endpoints with a stub or the real ffmpeg (skipped when it is not installed), and the page by server-side rendering and source guards (`renderToString` and `?raw` source checks, as in `SettingsGroup.test.ts`; the project has no DOM test library).

**Organization**: By user story: US1 the silent video and the button (P1), US2 progress and failures (P2), US3 download and replace (P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- Paths are from the repository root. Keep each file's line endings (`backend/app/routers/jobs.py`, `frontend/src/api.ts` and `frontend/src/App.vue` are CRLF; `config.py` and `main.py` are LF; `.gitignore` is mixed, so append with the same ending as its last line). Backend tests run from `backend/` (`python -m pytest`); frontend tests from `frontend/` (`npm test`). Write files with the Write/Edit tools, not shell heredocs (backticks get mangled).

---

## Phase 1: Setup

- [x] T001 Record the baseline before changing anything: run `python -m pytest -q` in `backend/` and `npm test` and `npm run build` in `frontend/`, and note which tests already fail (they are not this feature's). Confirm `ffmpeg -version` and `ffprobe -version` work (the real-conversion test uses both) and that `ffmpeg -hide_banner -encoders` lists `libx264`.
- [x] T002 [P] Add `backend/output/` to `.gitignore` under the "App data" heading next to `backend/uploads/` (spec FR-012).

---

## Phase 2: Foundational (blocks every story)

**Purpose**: the settings and the stored frame rate that the video service needs.

- [x] T003 [P] In `backend/app/config.py` add to `Settings`: `output_dir: Path = Path(__file__).resolve().parent.parent / "output"`, `ffmpeg_path: str = "ffmpeg"` and `video_timeout_seconds: int = 600` (env names `MV_OUTPUT_DIR`, `MV_FFMPEG_PATH`, `MV_VIDEO_TIMEOUT_SECONDS` follow from the existing `env_prefix`).
- [x] T004 In `backend/app/routers/jobs.py`, directly after the `write_frames(...)` call in `create_job`, write `frames_dir / "render.json"` containing `{"frame_rate": fps}` (use `json.dumps`; add `import json`). It is inside the existing `try`, so the existing cleanup (`_remove_job`) still removes everything on failure. The request and the response of `POST /api/jobs` do not change.
- [x] T005 [P] Add a test to `backend/tests/test_jobs_api.py` (or a new `backend/tests/test_render_json.py` using the `client` fixture and `post`/`tone`/`wav_bytes` helpers from `test_jobs_api.py`): after a successful job, `frames_temp_dir/<job_id>/render.json` exists, parses, and `frame_rate` equals the response's `frame_rate`; after a rejected job nothing is left in `frames_temp_dir`. Then run the whole backend suite to see that no existing test is broken by the extra file in the frames directory.

**Checkpoint**: settings exist, every new render records its frame rate.

---

## Phase 3: User Story 1 - Turn the rendered pictures into a silent video (Priority: P1) 🎯 MVP

**Goal**: `POST /api/jobs/{job_id}/video` makes `output_dir/<job_id>/video.mp4`, and a **Create video** button shows where it was saved.

**Independent Test**: upload a short WAV, create frames, click **Create video**; `ffprobe` of the reported file shows one `h264` video stream at the render's frame rate, duration frames ÷ fps (within one frame), and no audio stream.

### Tests for User Story 1 (write first, they fail)

- [x] T006 [P] [US1] Create `backend/tests/test_video.py` for `app.services.video` using a fake runner (monkeypatch `subprocess.run` as imported by the module, or an injectable `run` argument) and `tmp_path` directories: `build_command(ffmpeg, frames_dir, frame_rate, output_file)` returns the list `[ffmpeg, "-y", "-framerate", "<fps>", "-start_number", "0", "-i", "<frames_dir>/frame_%06d.png", "-an", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "<output_file>"]` (assert `-an` is present, no input other than the frames, and that a frame rate of 24.5 is passed as `24.5` and 30 as `30`); `create_video(job_id, ...)` with the fake runner writing the temporary file creates `output_dir/<job_id>/video.mp4`, leaves no `video.tmp.mp4`, and returns an object with `path`, `size_bytes`, `frame_count`, `frame_rate`, `duration_seconds` (frame count ÷ frame rate) computed from the frames and `render.json`; frame count counts only `frame_*.png`.
- [x] T007 [P] [US1] Create `backend/tests/test_video_api.py` using the `client` fixture pattern of `test_jobs_api.py` plus `monkeypatch.setattr(settings, "output_dir", tmp_path / "output")`: `POST /api/jobs/{id}/video` after a real tiny job (use `tiny()`/`post` helpers from `test_resolution_api.py` and `test_jobs_api.py`) returns 200 with exactly the keys of the contract (`job_id`, `file_name` = `video.mp4`, `path`, `size_bytes`, `frame_count`, `frame_rate`, `duration_seconds`, `url`) and `url` = `/api/jobs/<id>/video`; `path` is under the patched `output_dir`. One real-ffmpeg test, skipped with `pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, ...)`: run `ffprobe -v error -show_entries stream=codec_type,codec_name,r_frame_rate -show_entries format=duration -of json` on the file and assert one stream, `codec_type == "video"`, `codec_name == "h264"`, `r_frame_rate` equal to the job's frame rate, `format.duration` within 1 ÷ fps of `frame_count ÷ frame_rate`, and no audio stream (spec scenarios 1 to 4, SC-002, SC-003). Parametrize the real test over every image type in `IMAGE_TYPES` from `app.services.image_types` (spec scenario 5). A job that has a non-integer frame rate (for example `frame_rate=24.5`) gives a duration within one frame of the music's. An odd-sized picture (replace the frames of a tmp render with 599 × 399 PNGs written with Pillow plus a `render.json`) still converts.

### Implementation for User Story 1

- [x] T008 [US1] Create `backend/app/services/video.py`: `class VideoError(Exception)` with a `status` attribute (404, 409, 500, 503, 504) and a user-fit message; `build_command(...)` as in T006; `create_video(job_id, *, frames_root, output_root, ffmpeg, timeout)` that (1) reads `render.json` and counts `frame_*.png` in `frames_root/<job_id>` and raises `VideoError(404, "The frames of this render are no longer available. Render again.")` when either is missing, (2) creates `output_root/<job_id>/`, (3) runs ffmpeg with `subprocess.run(..., capture_output=True, timeout=timeout)` writing `video.tmp.mp4`, (4) on success `os.replace`s it onto `video.mp4`, (5) returns a small dataclass `VideoResult(job_id, path, size_bytes, frame_count, frame_rate, duration_seconds)`. Resolve `ffmpeg` with `shutil.which` and raise `VideoError(503, "ffmpeg was not found. Install it, or set MV_FFMPEG_PATH to its location.")` when it is not found or `FileNotFoundError` is raised.
- [x] T009 [US1] Create `backend/app/routers/video.py`: `router = APIRouter(prefix="/jobs", tags=["video"])` and a plain `def` `POST /{job_id}/video` that validates the id with the same pattern as `jobs._JOB_ID` (`^[0-9a-f]{32}$`; import it or repeat the regex; invalid gives `404 "Render not found."`), calls `create_video` with the three settings from `settings`, and returns the dict of the contract with `url=f"/api/jobs/{job_id}/video"`; a `VideoError` becomes `HTTPException(status_code=e.status, detail=str(e))`. Register it in `backend/app/main.py` (`app.include_router(video.router, prefix="/api")`) before the static mount.
- [x] T010 [P] [US1] In `frontend/src/api.ts` add `export interface VideoResult { job_id: string; file_name: string; path: string; size_bytes: number; frame_count: number; frame_rate: number; duration_seconds: number; url: string }`, `export async function createVideo(job: JobResult): Promise<VideoResult>` (POST `/api/jobs/${job.job_id}/video`; network failure gives the same "Could not reach the server…" message as `submitJob`; a non-OK response throws `Error(detail)` using the same detail-reading code, which you may extract into a shared helper) and `export function videoUrl(job: JobResult): string` returning `/api/jobs/${job.job_id}/video`.
- [x] T011 [P] [US1] Add tests to `frontend/src/api.test.ts` for `createVideo` (stub `fetch`: the URL and method, the parsed result, the server's `detail` shown on an error, the "could not reach" message when `fetch` rejects) and `videoUrl`.
- [x] T012 [US1] Create `frontend/src/components/VideoExport.vue` (script setup, TypeScript, prop `result: JobResult`): a section with a button **Create video**; clicking it calls `createVideo(props.result)`; when it resolves show `Video saved to {{ video.path }}`. Keep the state in refs `status` (`"idle" | "working" | "done" | "error"`), `video`, `message`; a `watch` on `props.result` resets them to idle. Style like `FramePlayer.vue`.
- [x] T013 [US1] In `frontend/src/App.vue` import `VideoExport` and render `<VideoExport :result="result" />` directly below `<FramePlayer :result="result" />` inside the results section.
- [x] T014 [P] [US1] Create `frontend/src/components/VideoExport.test.ts` in the style of `SettingsGroup.test.ts`: server-render the component with a sample `JobResult` and assert the button text `Create video` is present and enabled; a source guard (`?raw`) that the component imports `createVideo` and that `App.vue` renders `<VideoExport`.

**Checkpoint**: the MVP works end to end; run T007's real-ffmpeg tests and the quickstart steps 1 to 5.

---

## Phase 4: User Story 2 - Clear progress and clear failures (Priority: P2)

**Goal**: working state, no double conversion, plain error messages, no partial files.

**Independent Test**: with ffmpeg unreachable the page shows the ffmpeg message and `backend/output` has no file for that attempt; with the render's frames removed it shows "render again".

### Tests for User Story 2 (write first, they fail)

- [x] T015 [P] [US2] Add to `backend/tests/test_video.py` (fake runner): ffmpeg not found (`shutil.which` returns `None`, and separately the runner raises `FileNotFoundError`) gives `VideoError` with status 503 and the message of the contract; no `render.json`, no frames, or an unknown job id gives status 404 and creates nothing in `output_root` (the directory does not even exist); a runner that returns a non-zero exit code gives status 500 with the message "Something went wrong while making the video." and the stderr is logged (use `caplog`), and `video.tmp.mp4` and an empty `output_root/<job_id>` directory are gone; a runner that raises `subprocess.TimeoutExpired` gives status 504 with the contract message and nothing is left behind; a failure after a good video exists keeps the old `video.mp4` unchanged (compare bytes); the in-progress set is empty again after every one of those outcomes.
- [x] T016 [P] [US2] Add to `backend/tests/test_video_api.py`: the error statuses and `{"detail": …}` bodies of the contract for 404 (unknown but well-formed id, malformed ids such as `..`, `ABC`, a 31-character id, and a job whose `render.json` was deleted), 503 (patch `settings.ffmpeg_path` to a name that does not exist) and 500 (patch it to a small script or `python -c` that exits 1 — or patch the service's runner); 409: patch the runner to block on a `threading.Event`, start the first `POST` in a thread, wait until it is running, check the second `POST` for the same id returns 409 with "A video is already being made for this render.", release the first and check it returns 200 and a third `POST` then works; no file other than `video.mp4` ever remains in the render's output directory.
- [x] T017 [P] [US2] Add to `frontend/src/components/VideoExport.test.ts` source guards for the states: the component has the four states, disables the button while working (`:disabled` bound to the working state), shows the message with `role="alert"` on error, shows a working status with `role="status"`, and resets in a `watch` of `props.result`.

### Implementation for User Story 2

- [x] T018 [US2] In `backend/app/services/video.py` add the in-progress set with a `threading.Lock`: `create_video` raises `VideoError(409, "A video is already being made for this render.")` when the job id is in it, adds it before ffmpeg starts and removes it in a `finally`. Handle `subprocess.TimeoutExpired` (504, kill is done by `subprocess.run`), a non-zero exit code (500; log the decoded stderr with `logging.getLogger(__name__).error`), and in every failure delete `video.tmp.mp4` and remove `output_root/<job_id>` if this attempt created it and it is empty.
- [x] T019 [US2] In `frontend/src/components/VideoExport.vue` finish the states: while `working` the button is `disabled` and a `<p role="status">` says "Making the video… this can take a little while for long renders."; on a rejection show `<p role="alert" class="error-box">` with the message (reuse the `error-box` look of `App.vue`) and re-enable the button; a click while working does nothing (guard in the handler as well as the `disabled` attribute).

**Checkpoint**: US1 and US2 both pass; quickstart step 8.

---

## Phase 5: User Story 3 - Find and reuse the video (Priority: P3)

**Goal**: a download link on the page, and a repeat conversion replaces the video.

**Independent Test**: create the video, use the link, create again: one file remains, the link still works.

### Tests for User Story 3 (write first, they fail)

- [x] T020 [P] [US3] Add to `backend/tests/test_video_api.py`: `GET /api/jobs/{id}/video` after a conversion returns 200, `content-type: video/mp4`, a `content-disposition` with `attachment` and `video.mp4`, and a body equal to the file on disk; before any conversion, or for a malformed id, it returns 404 with "No video has been made for this render."; two successive `POST`s leave `output_root/<job_id>` containing exactly `["video.mp4"]` and the second file's modification time is not older than the first (with the fake runner writing different bytes each time, the `GET` body is the second's); two different renders keep two separate directories and neither overwrites the other (SC-006, FR-006).
- [x] T021 [P] [US3] Add to `frontend/src/components/VideoExport.test.ts` a source guard that the done state renders an `<a>` whose `href` is built with `videoUrl(` and that has the `download` attribute.

### Implementation for User Story 3

- [x] T022 [US3] In `backend/app/routers/video.py` add `GET /{job_id}/video` returning `FileResponse(path, media_type="video/mp4", filename="video.mp4")` (this sets the attachment disposition); the id is validated as in T009; a missing file gives `404 "No video has been made for this render."`. (Replacing on repeat already follows from the `os.replace` of T008.)
- [x] T023 [US3] In `frontend/src/components/VideoExport.vue` add, in the done state, `<a :href="videoUrl(result)" download>Download</a>` next to the saved-path text.

**Checkpoint**: all three stories work independently.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T024 [P] Add a short "Video" section to `README.md` (what the button does, the output location `backend/output/<job_id>/video.mp4`, the need for ffmpeg on the PATH or `MV_FFMPEG_PATH`, the silent video and how to add the music afterwards with `ffmpeg -i video.mp4 -i song.wav -c:v copy -shortest out.mp4`).
- [x] T025 Run the complete backend suite and `npm test` and `npm run build`; compare with the T001 baseline (nothing that passed before may fail; SC: no other feature's output changes, FR-011).
- [x] T026 Run `quickstart.md` by hand (steps 1 to 9) with the real app, including a render of about 1,000 frames to check the 60-second goal (SC-004), and confirm `git status` shows nothing from `backend/output/`. (Done with the real ffmpeg through the API: a 1,000-frame render became a 50 s, 20 fps, audio-free h264 video in 1.9 s, saved under `backend/output`. The page itself was not clicked through in a browser.)

---

## Dependencies & Execution Order

- **Phase 1** (T001, T002) first; T002 is independent of everything.
- **Phase 2**: T003 and T005 can run in parallel with each other; T004 needs nothing but should be done before T005's test passes. All of Phase 3 and later waits for Phase 2.
- **US1**: tests T006, T007, T011, T014 are written first and are independent of each other; then T008 (service) → T009 (router; needs T008) ; T010 (api.ts) → T012 (component; needs T010) → T013 (App.vue; needs T012).
- **US2** needs US1's files: T018 extends T008's file; T019 extends T012's file. Tests T015 to T017 can be written together.
- **US3**: T022 extends T009's file; T023 extends T012's file; tests T020, T021 first.
- **Polish** last.

### Parallel opportunities

- T002 with T001; T003 with T005.
- In US1, T006, T007, T010, T011 and T014 touch different files and can be done together.
- The backend chain (T008 → T009) and the frontend chain (T010 → T012 → T013) are independent of each other.

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phases 1 and 2.
2. Phase 3 (US1), then **stop and validate** with the real-ffmpeg tests and the quickstart steps 1 to 5.

### Incremental delivery

1. MVP → add US2 (robustness) → add US3 (download link). Each adds value without breaking the earlier one.

## Notes

- [P] tasks = different files, no dependencies.
- ffmpeg is the 2018 build `N-92806`: do not use options newer than that (the command in T006 is known to be supported).
- Never trust the client: the frame rate comes from `render.json`, the paths from the validated job id.
- Commit after each task or logical group, only when asked.
