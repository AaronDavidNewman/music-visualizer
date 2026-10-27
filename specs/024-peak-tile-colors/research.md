# Research: Peak Tile Colors

No `[NEEDS CLARIFICATION]` remains (answered on 2026-10-27). Facts about the code were read from the repository; the numbers come from a prototype (`scratchpad/position_proto.py`) on seeded click tracks.

## What exists today

- `colormaps.colorize(smoothed, colormap, shown, peak)`: the table index of a tile is `rint(sqrt(min(value / peak, 1)) × 255)` (0 when `peak` is 0); it is called once, from `write_frames`, with the (possibly interpolated) grid values of every frame.
- `frame_rendering.write_frames(frames, directory, …)` takes only note values; hidden tiles are set after coloring (`0` for tiles, the colormap's row 128 for blended); contour and the circles do not use `colorize`.
- `jobs.create_job` reads the WAV (`file_rate, left, right`), computes the frame count and the note analysis, and calls `write_frames(average_frames(...), …)`. Every setting is parsed by a `_parse_*` function that raises a 400 with a message, before any audio work.
- Frame `i` covers `[i / fps, (i + 1) / fps)` seconds of the file (`average_frames`).
- `local_peaks.LocalPeaks` (feature 023) has `energy_at`, `rate_at` and the per-peak `window_min` / `window_max`; its checks and messages exist.
- The frontend groups model (`groups.ts`) has one type group after Image type; `SettingsForm.vue` keeps every value in a ref, validates it, and has a `problem` flag per group.

## Decision 1: The time of a frame is the middle of its interval

- **Decision**: `t_i = (i + 0.5) / frame_rate` seconds.
- **Rationale**: The note values of a frame are averages over its interval, so its beat should be read in the middle of the same interval. (The spec's assumption.)
- **Alternatives considered**: the frame's start `i / fps` (the first frame would always sit at 0).

## Decision 2: The position follows beat strength, because the energy runs from peak to peak

- **Decision**: As the clarification defines: `position = clip((E − lo) / (hi − lo), 0, 1)` with `E`, `lo`, `hi` the straight-line interpolations of the neighbouring peaks' `energy`, `window_min` and `window_max`; 0 before the first peak and when `hi ≤ lo`; the last peak's values after the last.
- **Rationale**: This is the user's answer to Question 1 (A) and to the measurement's interpolation (feature 023). A prototype shows what it does: for a click track of equal clicks the position is 0.71 to 1.0 with a median of 0.996 (it does not dip between beats, because the line joins equal peak energies); for 37 clicks of strength 0.2 to 1.0 it is 0 to 0.999 with a median of 0.79 (it follows how strong each beat is against its window's range).
- **To confirm with the user** (reported at the end of the work): if a rise and fall *within* each beat is wanted, the position needs the measured impulse-energy curve instead of the peaks' line; that is a different, later change, recorded as an assumption in the spec.
- **Alternatives considered**: reading the impulse energy at the frame's time (a within-beat pulse, but not what was clarified and it needs the energy curve kept in the result); the whole-file range (the other options of Question 1, not chosen).

## Decision 3: `write_frames` takes the positions, not the audio

- **Decision**: `write_frames(..., beat=None)`; `beat` is a 1-D array with one finite number from 0 to 1 per frame (or `None`). It is checked (a `ValueError` for another shape, length, NaN or a value outside 0..1) and used only when the image type is `tiles` or `blended`.
- **Rationale**: `write_frames` and `colorize` stay free of audio and of the measurement and are tested on plain arrays; the router, which owns the audio, makes the positions. A setting that a type does not use is accepted and ignored, as with the circle settings.
- **Alternatives considered**: passing the WAV arrays into `write_frames` (couples the renderer to the measurement and to the sample rate); making the positions inside `write_frames` from a `LocalPeaks` (works, but then the frame times need the frame rate too; the array is simpler).

## Decision 4: `colorize` blends the two halves before rounding

- **Decision**: `index = rint((0.5 × sqrt(share) + 0.5 × beat[:, None]) × 255)` with `beat` of shape `(frames,)`; without `beat` the existing expression is used unchanged (so the off path is the old code).
- **Rationale**: One rounding, exactly "half and half"; a tile at share 1 gives 0.5 × 255 = 127.5 at position 0, which `np.rint` rounds to 128 (the middle row that the Blended background uses), and 255 at position 1. Monotone in both inputs.
- **Alternatives considered**: blending two color lookups (more code, and the middle of the colormap is a position, not a mix of colors).

## Decision 5: The three request fields and their checks

- **Decision**: `beat_coloring` (true, false, 1, 0 in any case; default false; message `The beat coloring must be true or false.`), `peak_distance` (milliseconds, default 100) and `peak_prominence` (percent, default 50), both parsed as numbers and checked with `check_min_distance` / `check_prominence` so the 400 detail is the measurement's own message; all three checked before any file work; when the checkbox is on and the type is `tiles` or `blended` the job measures the beat and passes the positions; the response adds `beat_coloring`, `peak_distance`, `peak_prominence` (the values sent or their defaults).
- **Rationale**: The same pattern as `circle_resize` and `gaussian`. Checking the two numbers when the checkbox is off is the spec's rule.
- **Alternatives considered**: ignoring the two numbers when off (the spec says to check them).

## Decision 6: The page

- **Decision**: A group `local-peaks` titled "Local peaks" with controls `beat-coloring` (a checkbox, label "Beat coloring"), `peak-distance` (a slider 100 to 2000, step 50, shown as "100 ms") and `peak-prominence` (a slider 0 to 100, step 5, shown as "50%"), shown right after the Tiles and Blended Tiles groups and for no other type; the checkbox is off by default and the two sliders stay enabled (their values are kept and sent whatever the checkbox says). A validation error in the group sets the group's problem flag and blocks submitting, as for the other groups. The summary shows "Beat coloring: Off" or "On" and, when on, the two values, for tiles and blended only.
- **Rationale**: Mirrors the circle controls; slider steps keep the numbers on neat values, the backend accepts any number in range.
- **Alternatives considered**: disabling the sliders while the checkbox is off (hides values that are still checked and sent).

## Prototype results

20 s click track, equal clicks every 0.5 s: position after the first click 0.71 / 0.996 / 1.0 (min / median / max). 37 clicks of strength 0.2 to 1.0 every 0.5 s: 23 peaks at the default prominence; position 0.0 / 0.79 / 0.999. The measurement takes 0.03 s for 60 s of audio.
