# Data Model: Frames to MP4

There is no database; the entities are files.

## Render (existing, one small addition)

Directory `frames_temp_dir/<job_id>/` (`job_id` is 32 lowercase hex characters).

| Part | Description |
|---|---|
| `frame_000000.png` … `frame_NNNNNN.png` | the frames, numbered from 0 without gaps (existing) |
| `render.json` | **new**: `{"frame_rate": <number>}`, the render's frames per second (1 to 60), written by `POST /api/jobs` after the frames |

Derived: the frame count is the number of `frame_*.png` files; the video duration is frame count ÷ frame rate.

A render "exists" for this feature when its directory holds at least one frame and a readable `render.json`. A render made before this feature has no `render.json`, so a video cannot be made for it (treated like "frames gone": render again).

## Video (new)

File `output_dir/<job_id>/video.mp4` (`output_dir` defaults to `backend/output`).

| Attribute | Rule |
|---|---|
| streams | exactly one, video (H.264, `yuv420p`); no audio |
| frame rate | the render's `frame_rate` |
| duration | frame count ÷ frame rate (within one frame) |
| size | the frames' size, padded up to even width and height |
| cardinality | at most one per render; a new conversion replaces it |
| temporary file | `video.tmp.mp4` in the same directory while ffmpeg runs; never left behind |

## Conversion state (in memory only)

The set of `job_id`s with a conversion running. Entered when a `POST` starts, left (always, including on errors) when it ends. Not persisted; empty after a restart.

State transitions on the page: `idle → working → done` or `working → error`; `done`/`error → working` on another click; any state `→ idle` when a new render replaces the result.
