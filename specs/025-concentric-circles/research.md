# Research: Concentric

No `[NEEDS CLARIFICATION]` remains (answered on 2026-10-27). Facts about the code were read from the repository; the numbers come from a prototype (`scratchpad/concentric_proto.py`).

## What exists today

- `image_types.IMAGE_TYPES` lists five names; `check_image_type` builds its message from the tuple; `tile_edges(count, size)` gives the nearest whole-pixel edges of an even split (columns 50 px; rows 57 or 58 px on the 600 × 400 frame).
- `write_frames` checks every setting for every image type, smooths the note values (`smooth_frames`), and has early-return branches for `circles` and `circles_paint` before the grid pipeline; `beat` (feature 024) is checked for every type.
- `circles.py` / `circles_paint.py` draw circles with a four-times supersampled mask and have the background at the colormap's middle row (`MIDDLE_COLOR_ROW = 128`, `SUPERSAMPLE = 4`) and save frames on a few threads with `compress_level=1`.
- `LocalPeaks.frame_positions(fps, frames)` gives each frame's position in the local peak (feature 024); `jobs.py` already measures the beat for Tiles and Blended tiles when the box is on.
- Frontend: `IMAGE_TYPES` (value, label), `gridSettingsApply(imageType)`, `beatColoringApplies`, the groups model (`groupsFor`, `controlsIn`, `groupOf`), `SettingsForm.vue` with the Local peaks group (checkbox, Minimum distance, Prominence), `App.vue`'s summary.

## Decision 1: Work the geometry out once; a frame is two table lookups and a blend

- **Decision**: For the 600 × 400 frame and the 12 × 7 grid, once (cached): the cell of every pixel; from a 4 × 4 supersample of every pixel the share of each class (0 = outside the circle, 1 to 12 = ring) with the circle centered on its cell, ring `k` covering radii `((k − 1) R / 12, k R / 12]` and `R = 25`; keep the two most frequent classes `a` and `b` and the weight `wb = share(b) / (share(a) + share(b))`. A frame builds a table `T[cell, 0..12]` of colors (class 0 the background; class `k` the ring's color when the cell's step is at least `k`, else the background) and the picture is `T[cell, a] × (1 − wb) + T[cell, b] × wb`, rounded.
- **Rationale**: The geometry never changes, so only colors vary per frame. A pixel is at most 1.41 px across and a ring is 2.08 px wide, so a pixel can touch at most two classes (the geometry asserts this when it is built), which makes the two-class blend **identical to drawing the rings on a 4 × 4 supersampled canvas and averaging** (prototype: maximum difference 0 on random steps and colors). Per frame about 11 ms of arithmetic; with the PNG 15 ms; **1,800 frames in 8.7 s** on four threads.
- **Alternatives considered**: drawing the 84 × 12 discs with Pillow for every frame (about 1,000 ellipses a frame, and each frame at 4 × resolution: far slower); keeping the 12 coverage masks and summing them (12 times more arithmetic per frame); drawing the circles without antialiasing (jagged rings; the other circles are smooth).

## Decision 2: The step is the ceiling of 12 × the square root of the share, with a guard against rounding noise

- **Decision**: `share = value ÷ loudest` (0 when the frame's loudest value is 0), `step = clip(ceil(12 × sqrt(share) − 1e-9), 1, 12)`. The loudest of the frame's 84 drawn notes is step 12; a silent frame is all step 1.
- **Rationale**: This is the clarified rule. Floating-point noise could push an exact ratio such as `25 / 144` (whose root should give exactly 5) up to the next whole step (`12 × sqrt(25 / 144)` may come out as `5.000000000000001`); the `1e-9` makes the exact ratios `k² / 144` give `k`. Nothing real depends on the guard (values are never exact ratios).
- **Alternatives considered**: no guard (surprising results at exact ratios, which tests would hit); rounding instead of the ceiling (not what was clarified).

## Decision 3: Ring colors are 12 table lookups per frame

- **Decision**: `rows[f, k − 1] = rint((k − 1) / 11 × (0.5 + 0.5 × position[f]) × 255)` for `k = 1 … 12`; the color is `lookup_table(colormap)[rows]`. With no beat given (`beat=None` in `write_frames`) every position is 0.
- **Rationale**: The clarified colors: ring 1 is always the first color, ring 12 the last at position 1 and the middle (`rint(127.5) = 128`) at position 0. `np.rint` rounds half to even, so 127.5 gives 128, the same row as the background.
- **Alternatives considered**: `k / 12` (ring 12 would not reach the last color at position 1, against the clarification).

## Decision 4: `concentric` has no group of its own; the Local peaks group is shared with a different set of controls

- **Decision**: In the groups model a new group `concentric-peaks` titled "Local peaks" with controls `["peak-distance", "peak-prominence"]`, shown for `concentric` only, after Image type and before Data smoothing; `groupsFor("concentric")` is `analysis, colormap, image-type, concentric-peaks, data-smoothing`. `local-peaks` (with the checkbox) stays for Tiles and Blended tiles. `SettingsForm.vue` renders one group whose id is whichever of the two is shown and shows the checkbox only for `local-peaks`, so the two sliders are written once. `gridSettingsApply("concentric")` is false, so Threshold, Notes, Oversampling, Interpolate and Gaussian are neither shown nor summarised; their values are kept and still sent (and ignored by the server).
- **Rationale**: The group model maps a group id to a fixed control list and a control to the group it is in (`groupOf`); two ids keep that model unchanged. The user's answer (Q2: B) is exactly these controls.
- **Alternatives considered**: making the checkbox conditional inside one group id (the model would need a type-dependent control list); a group titled "Concentric" (it would have no controls of its own).

## Decision 5: The server measures the beat for every Concentric job

- **Decision**: In `create_job`: `beat = measure_local_peaks(...).frame_positions(fps, frames)` when the type is `concentric`, or when the type is `tiles` or `blended` and `beat_coloring` is true; `beat_coloring` is parsed and echoed for every type as before and has no effect on Concentric. The two peak settings are checked before the file is read, as before.
- **Rationale**: The clarification: no checkbox for this type; the beat always colors it. Keeping the field accepted and ignored follows how the other settings that a type does not use behave.
- **Alternatives considered**: refusing `beat_coloring=true` for Concentric (the other unused settings are accepted and ignored).

## Prototype results

Geometry (cells, supersample classes, ring weights): 0.15 s once. A frame: 10.7 ms of arithmetic, 14.6 ms with the PNG (61 KB at `compress_level=1`), 400 frames on four threads in 1.93 s (1,800 in about 8.7 s). Difference to a brute-force drawing of the rings on a 4 × 4 canvas: 0 on random steps and colors.
