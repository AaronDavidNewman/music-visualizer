# Contract: Chromatic Wireframe

## Request

`POST` of the existing job endpoint with `image_type=chromatic-wireframe`. **No new field.** The settings that apply are those of Chromatic Decay:

| Field | Meaning for this type |
|-------|-----------------------|
| `decay_rate` | a whole number 1..10 (default 1); anything else is refused with 400 `The decay rate must be a whole number from 1 to 10.` before the file is read; 3 and 3.0 are accepted |
| `threshold` | 0..10 percent, as for Chromatic Decay |
| `peak_distance`, `peak_prominence` | the local peaks that decide the beat (the five loudest letters' bonus and the color of the lines) |
| smoothing, `smoothing_window`, analysis settings, `colormap` | as for every type |
| `note_layout`, the four decay amounts and every grid setting | accepted, checked as for every type, ignored |

The 400 for an unknown `image_type` lists the thirteen names, ending `..., chromatic-decay, rhythm-circles, chromatic-wireframe.` Every other type's frames, and every other type's request handling, are unchanged.

## Response

As for the other types: `image_type` is echoed (`chromatic-wireframe`), `decay_rate` is the integer.

## Library (`app/services/chromatic_wireframe.py`)

```text
band_width(width) -> float                                  # (width - 2 MARGIN) / 12
line_angles(points_row, width) -> ndarray (12, n)           # 2pi (p / 16) u / plot width + 2pi start / plot width: frequency from the points, phase of the start
line_sums(points_row, width, height) -> ndarray (n,)         # S: 1 / 12 x the sum of the 12 letters' radius share x sine squared, 0 to 1
line_heights(points_row, width, height) -> (X, Z)           # each (n,), pixels; Z = A x clip((S - 0.05) / (0.8 - 0.05), 0, 1), 0 <= Z <= A = two fifths of the height
line_geometry(width, height) -> (lines, base, step)         # lines >= 1, ValueError for a picture too small
line_colors(beat, colormap) -> ndarray (frames, 3) uint8    # peak = last colormap row; None = first row
project_line(X, Z, depth, lines, width, height) -> (x, y)   # the screen points of the line at depth k
write_wireframe_frames(points, colormap, directory, width, height, beat=None) -> None
```

`write_frames(..., image_type="chromatic-wireframe", beat=..., decay_rate=..., threshold=...)` computes the points with `chromatic_decay.circle_points` and calls `write_wireframe_frames`.

## The picture

600 x 400 RGB PNG (`frame_000000.png` and up), background **black**. Per spec: one smooth line, the sum of the 12 letters' sines, across the width with 10 px margins; one polyline per frame, the current frame in front near the bottom, the front line's base on the bottom margin, as many lines as fill the picture to the top margin (66 on 600 x 400) going back 4 px each and shrinking to 75%; a nearer line hides what is behind it; every line one color, a local peak the last colormap color and the lowest point of the beat the first; no pixel outside the picture; identical bytes for identical input.
