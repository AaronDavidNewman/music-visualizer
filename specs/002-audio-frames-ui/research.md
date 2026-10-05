# Research: Audio Upload and Frame Visualization UI

No `NEEDS CLARIFICATION` items were open. These are the design decisions.

## Decision 1: One synchronous request

- **Decision**: `POST /api/jobs` receives the upload, does all the work, and returns the finished metadata. The UI shows a busy state until it returns.
- **Rationale**: Analysis of a 340 s, 90 MB file takes about 0.5 s (feature 001), and writing a few thousand small PNGs takes seconds. A job queue with polling adds state, endpoints and failure modes that the spec's "one request or one background job" does not require. FastAPI runs a plain `def` endpoint in its thread pool, so the server stays responsive to other requests.
- **Alternatives considered**: Background task plus polling endpoint (needed only if rendering proves too slow, which SC-002 will show); server-sent progress events (more machinery than a busy indicator needs).

## Decision 2: Reading the file once, validating before analysis

- **Decision**: Refactor feature 001's `analyze_wav` into two public pieces: `read_wav(path)` returning the file's rate and the two channel arrays, and `analyze_channels(left, right, sample_rate, window_size)` returning the `AnalysisResult`. `analyze_wav` becomes a thin wrapper, so its behavior and tests are unchanged. `AnalysisResult` gains a `sample_count` field so duration is known exactly.
- **Rationale**: FR-016 wants the frame-count and empty-file checks before the analysis, and the file's header rate is needed to compute the frame count. Reading the file once and passing arrays on avoids decoding it twice, and no second WAV parser is needed (the stdlib `wave` module cannot read some 24-bit and extensible files).
- **Alternatives considered**: Parse the RIFF header by hand (extra code to maintain); call `analyze_wav` and check afterwards (violates "before the analysis", though cheap).

## Decision 3: Frame averaging

- **Decision**: Frame *f* covers `[f / fps, (f + 1) / fps)`. Window *i* starts at `i * W / sr`. Frame *f* averages windows `lo ≤ i < hi` with `lo = ceil(f * sr / (fps * W))` and `hi = ceil((f + 1) * sr / (fps * W))`. If the range is empty, it uses window `floor(f * sr / (fps * W))`, clamped to the last window. Averaging is done with a running sum over the window rows, so it is vectorized and exact in one pass. A small epsilon guards the `ceil` against floating-point noise. Frame count is `ceil(sample_count * fps / sr)` with the same guard.
- **Rationale**: Matches FR-007 exactly, handles windows longer than a frame (every frame has data), and keeps the last partial period.
- **Alternatives considered**: Re-running the transform at frame boundaries instead of averaging windows (changes the feature 001 contract and the user's stated design); nearest-window only (ignores "average the windows over that period").

## Decision 4: Image format and layout

- **Decision**: 8-bit grayscale PNG, 11 columns × 8 rows of 20 × 20 pixel squares (220 × 160), note *n* at row `n // 11`, column `n % 11`. Brightness is `round(255 * value / file_max)`, and all black if the file maximum is 0. Built with numpy (`np.repeat` on both axes) and saved with Pillow at a low PNG compression level.
- **Rationale**: Straight from FR-009 and FR-010. PNG is lossless, so brightness values are exact and testable. A low compression level keeps writing fast; the images are tiny.
- **Alternatives considered**: JPEG (lossy, changes values); one sprite sheet (more client logic, and the spec asks for one image per frame); drawing with Pillow shapes (slower than array repetition).

## Decision 5: Temporary storage and naming

- **Decision**: Two roots under `tempfile.gettempdir()/music-visualizer/`: `audio/` and `frames/`, both overridable through `MV_`-prefixed settings. Each submission gets `uuid4().hex` as its folder name in both roots. The audio is stored as `audio.wav` regardless of the original name, and frames as `frame_000000.png` and up. The original name is kept only in the response.
- **Rationale**: FR-004, FR-011, FR-018 and SC-008: separate roots, unique folders, and no user-controlled path pieces. A 32-hex-digit random id is hard to guess, which is the only access control a local single-user tool needs.
- **Alternatives considered**: `tempfile.TemporaryDirectory` objects (deleted when the object goes away, but the frames must outlive the request); a database of jobs (not needed).

## Decision 6: Serving frames safely

- **Decision**: `GET /api/jobs/{job_id}/frames/{index}` accepts `job_id` only if it matches `^[0-9a-f]{32}$` and `index` only as a non-negative integer, builds the path itself, and returns 404 if the file does not exist. Responses carry a long-lived cache header, since a frame never changes.
- **Rationale**: Prevents path traversal by construction, and lets the browser cache frames while looping.
- **Alternatives considered**: Mounting the frames directory as static files (exposes listings and any stray files, with weaker validation).

## Decision 7: Validation and error shape

- **Decision**: All errors return `{"detail": "<plain message>"}`. Form fields arrive as text and are parsed by the server, so a non-numeric value gives the same message shape as any other error (FastAPI's automatic 422 would give a different shape). Status codes: 400 for bad input and unreadable audio, 413 for an oversize upload. The size limit is enforced while streaming the upload to disk, and the partial file is deleted. Errors raised by feature 001 (`AudioAnalysisError`) are passed through with their message. After any failure, the submission's folders are removed.
- **Rationale**: One consistent shape keeps the UI's error handling to one code path (FR-016, FR-017, SC-007).
- **Alternatives considered**: Typed form parameters with FastAPI's default 422 (the UI would need to parse two shapes).

## Decision 8: Limits live in settings

- **Decision**: `max_audio_bytes` (200 MB), `max_frames` (30,000), window size (powers of 2 from 4096 to 32768) and frame rate 1–60 are fields in `app/config.py`. The existing `max_upload_bytes` (20 MB) stays for the image endpoint.
- **Rationale**: Spec assumption; configurable without code changes, and changing the audio limit must not alter the existing image endpoint's behavior.
- **Alternatives considered**: Raising `max_upload_bytes` (would change the existing image endpoint).

## Decision 9: Frontend structure and playback

- **Decision**: Three components (`App.vue`, `UploadForm.vue`, `FramePlayer.vue`), a small `api.ts`, and pure helpers in `lib/`. Playback uses `requestAnimationFrame` and derives the frame index from elapsed time (`floor(elapsed * fps)`), rather than a fixed `setInterval`. The next frames are preloaded into the browser cache a short distance ahead. The image is scaled up with `image-rendering: pixelated`.
- **Rationale**: Time-based indexing holds the chosen rate even when the browser delays a tick, which SC-006 requires. Preloading avoids a flash of empty image on each frame.
- **Alternatives considered**: `setInterval` (drifts); a canvas that draws from an array of loaded images (more memory and code, no benefit at this size); a UI framework or state library (unneeded for one screen).

## Decision 10: Frontend testing

- **Decision**: Add `vitest` as a dev dependency and test only the pure modules (`validation.ts`, `playback.ts`). Components are checked by `vue-tsc`, the production build, and the manual quickstart.
- **Rationale**: The riskiest frontend logic is arithmetic and range checks, which needs no DOM. A component-test stack (jsdom, test-utils) would add a lot of tooling for one small screen.
- **Alternatives considered**: Playwright end-to-end tests (heavy browser install; good later); no frontend tests (leaves playback timing unchecked).
