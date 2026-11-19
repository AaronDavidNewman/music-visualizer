# Data Model: Decouple the frame rate from the frequency buffers

No new kind of array and no new stored data. The entities of the spec map to the existing ones; what changes is where each value comes from.

## Frequency buffer (code name: analysis window)

| Field | Meaning | Source |
|---|---|---|
| strength of 88 notes | one row of `AnalysisResult.frames` (`NoteStrengths` `(windows, 88)`) | `note_analysis.analyze_channels()` then `noise_floor.floor_analysis()` |
| start | `rint(k * step)` samples, buffer `k` counted from 0 | `note_analysis.window_starts()` |
| exact start | `k * step` samples (`AnalysisResult.window_positions`) | used to give each buffer to a frame |

- `step = buffer_interval.buffer_step(sample_rate)` = `sample_rate * 60 / 1000` samples (a float; never below 1).
- It no longer depends on the frame rate, the window size or any setting. `window_size` still decides how long each buffer is (4096 to 32768 samples, a power of 2); a window longer than 60 ms
  makes the buffers overlap.
- Number of buffers: `note_analysis.window_count(samples, step)`; refused above `settings.max_windows`.

## Frame

| Field | Meaning | Source |
|---|---|---|
| index `f` | `0 .. frames - 1`, `frames = ceil(duration * frame_rate)` | `frame_rendering.frame_count()` |
| period | `[f / frame_rate, (f + 1) / frame_rate)` seconds | `frame_rendering.frame_windows()` |
| note strengths | `NoteStrengths` row `(88,)`: the mean of the buffers whose start is in the period, else the latest earlier buffer (the first if none) | `frame_rendering.average_frames()` |

Rules (unchanged code, now the only smoothing of the note data):

- every buffer is owned by exactly one frame;
- a frame owns about `frame period / 60 ms` buffers, one more or fewer: at 10 fps (100 ms) 1 or 2 buffers (1.67 on average); at 2 fps (500 ms) 8 or 9; above 16.7 fps none or one (a
  frame with none repeats the latest buffer).
- there is no blending with earlier frames: the rows go to the image type as they are.

## Removed

| Removed | Was | Replaced by |
|---|---|---|
| `window_spacing` (setting) | a multiple of the window size; default = one frame period | the constant 60 ms |
| `smoothing` (setting) | weight 0 to 0.8 of each earlier frame | the averaging above |
| `smoothing_window` (setting) | 1 to 20 earlier frames | the averaging above |
| `smooth_frames()` | `NoteStrengths` to `NoteStrengths`, weighted running average | nothing |
| `spacing_raised`, `window_spacing`, `smoothing`, `smoothing_window` (answer keys) | settings echoed back | nothing |

## Validation rules

- Frame rate: a number from `min_frame_rate` (1) to `max_frame_rate` (60), as before.
- Window size: one of the powers of 2 from `min_window_size` to `max_window_size`, as before.
- Buffers: at most `max_windows` (60000); frames: at most `max_frames` (30000), as before.
- The removed settings have no validation: whatever is sent for them is ignored.

## State transitions

None. A job is made in one request and its frames are read back; nothing is stored between jobs.
