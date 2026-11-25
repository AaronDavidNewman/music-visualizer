# Data model: 3D export of Contour and Chromatic Wireframe

## New arrays (three, to be added to `array_types.py` before use, constitution rule II)

| Alias | Dtype | Shape | Meaning | Made by |
|-------|-------|-------|---------|---------|
| `MeshVertices` | `float64` | `(points, 6)` | One row for each point (vertex) of one frame's mesh: `x, y, z` (grid units, Z the scaled height) and `r, g, b` (the color, 0 to 1). The order of the rows is the order of the `v` lines of the file and the numbering of `MeshFaces` (row `k` is vertex `k + 1`). | `obj_export.contour_mesh`, `obj_export.wireframe_mesh` |
| `MeshFaces` | `intp` | `(faces, 4)` | One row for each four-sided face of one frame's mesh: the numbers of its four corners, counted **from 1** (as in OBJ) in the order round the face, counterclockwise seen from +Z. | `obj_export.contour_mesh`, `obj_export.wireframe_mesh` |
| `LetterAmplitudes` | `float64` | `(frames, 12)` | The amplitude of each letter's sine in the Chromatic Wireframe picture: the radius of the letter's circle as a share of the full radius, from 1/12 (0 points) to 1 (24 points or more); one row for each frame, in letter order (A first). | `obj_export.amplitude_share` |

Existing aliases reused: `GridValues` `(frames, 84)` (the notes after Number of notes and Threshold), `FrameGrid` `(7, 12)` (one smoothed frame, the rows flipped, row 0 at the bottom),
`BeatPositions` `(frames,)`, `CirclePoints` `(frames, 12)` (the points of each letter), `LineColors` `(frames, 3)` (uint8 color of the line of each frame).

## Contour mesh of one frame

| Item | Value |
|------|-------|
| Points | 84: row `r` 0..6 (Y), column `c` 0..11 (X, the note name, A first), vertex number `1 + 12 r + c` |
| X, Y | `c`, `r` (row 0 is the bottom row of the picture's grid: `smoothed_grid` returns the rows flipped, so the picture seen from +Z has the picture's orientation) |
| Z | `12 * grid[r, c] / peak` (`grid` the smoothed, waved frame; `peak` the largest value of the whole file; Z = 0 for all when `peak <= 0`); range 0 to 12 (the smoothing averages a note with its neighbours, so a lone loud note stays under 12) |
| Color | colormap table row `round(255 * clip(grid[r, c] / scale, 0, 1))`, divided by 255 per channel; `scale` = the largest value of the frame before the beat wave; when the picture draws a flat color (`peak <= 0` or every value of the frame equal) the picture's flat color, the same for all 84 points |
| Faces | 66: for `r` 0..5 and `c` 0..10, the corners `1 + 12 r + c`, `1 + 12 r + c + 1`, `1 + 12 (r + 1) + c + 1`, `1 + 12 (r + 1) + c` |

## Wireframe mesh of frame `i`

| Item | Value |
|------|-------|
| Lines | `L = min(i + 1, 12)`; line `j` (0 to `L - 1`) is frame `i - j` |
| Points | `12 L`: line `j`, letter `b` 0..11 (A first), vertex number `1 + 12 j + b` |
| X, Y | `b`, `j` |
| Z | `12 * (SMALLEST + (1 - SMALLEST) * min(points[i - j, b], SIZE_POINTS) / SIZE_POINTS)`, with `SMALLEST = 1/12` and `SIZE_POINTS = 24` (`decay`); range 1 to 12 |
| Color | `line_colors(beat, colormap, frames)[i - j] / 255`: the same for the 12 points of a line |
| Faces | `11 (L - 1)`: for `j` 0..`L - 2` and `b` 0..10, the corners `1 + 12 j + b`, `1 + 12 j + b + 1`, `1 + 12 (j + 1) + b + 1`, `1 + 12 (j + 1) + b` |

A full file (`i >= 11`): 144 points, 121 faces. Frame 0: 12 points, 0 faces.

## The OBJ file

```text
# Music Visualizer 3D export
# contour frame 12 of 300: x = note name 0-11, y = octave row 0-6, z = value 0-12 (colors 0-1)
o frame_000012
v 0.0000 0.0000 1.2345 0.2667 0.0039 0.3294
... (84 or 12 L lines)
f 1 2 14 13
... (66 or 11 (L - 1) lines)
```

Lines end with `\n`; numbers `format(x, ".4f")` (never an exponent, `-0.0000` written `0.0000`); no material, normal or texture lines.

## The files of a job

| Where | What |
|-------|------|
| `frames_temp_dir/<job>/obj/frame_NNNNNN.obj` | one per frame, `NNNNNN` the frame number in 6 digits as the PNGs; written with the frames when `export_obj` is on, never otherwise |
| `output_dir/<job>/obj.zip` | made on the first `GET /api/jobs/<job>/obj`; the same files, stored under the same names, in frame order |

## Validation rules (carried by tests)

- The file count equals the frame count; the names are `frame_000000.obj` and up.
- Contour file: exactly 84 `v` lines of 6 numbers, 66 `f` lines of 4 numbers; every face number from 1 to 84 and the four corners are the corners of one cell; X in 0..11, Y in 0..6, Z in 0..12;
  colors in 0..1.
- Wireframe file of frame `i`: `12 L` `v` lines, `11 (L - 1)` `f` lines; X 0..11, Y 0..`L - 1`, Z 1..12; the 12 points of a line share one color; no vertex is used by no face except in a one-line
  file.
- Same input, same bytes.
