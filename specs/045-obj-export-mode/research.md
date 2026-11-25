# Research: 3D export of Contour and Chromatic Wireframe

No `NEEDS CLARIFICATION` was left by the specification; the three questions were answered by the user before it was written. This file records the decisions that the plan rests on and the places where
the spec left room.

## Decision 1: The export has its own module and does not draw

- **Decision**: a new `services/obj_export.py` that takes the numbers the pictures are made from and writes text. It does not import matplotlib or Pillow. `write_frames` calls it after the pictures.
- **Rationale**: the pictures are made by a drawing step that the export does not need (levels, antialiasing, the 3-D projection). Keeping the two apart means the pictures cannot change (FR-001,
  SC-006) and the export is testable with small arrays.
- **Alternatives considered**: writing the OBJ inside `write_contour_frames` and `write_wireframe_frames` (the contour one holds the pyplot lock and skips flat frames: the export must not skip any frame);
  a separate endpoint that recomputes everything from the audio (a second analysis of the file for no gain).

## Decision 2: Contour exports the grid the picture draws, at 12 x 7

- **Decision**: the values are those of `write_frames` for the contour after `spread_notes` (Number of notes) and `hidden_below` (Threshold), taken at **resolution 1** (the 12 x 7 grid, no
  interpolation), then each frame is smoothed with the picture's own `directionalSmoothing` (through a new `smoothed_grid()` that `write_contour_frames` also uses) and, when the job has the beat wave
  on and the frame's beat position `k` is above 0, multiplied by `wave_modifier(7, 12, waves, k)`.
- **Rationale**: the spec says only the 12 x 7 points are exported (so Resolution, which makes a finer grid, is not applied), and that the surface is the one the picture shows from above (so smoothing
  and the beat wave are). Number of notes and Threshold change the values themselves, so they apply. Gaussian blur and Interpolate frames act on the PNG files only and do not apply.
- **Alternatives considered**: exporting the picture's finer grid at Resolution above 1 (more than 84 points: against the spec); skipping the smoothing (the surface would differ from the picture);
  exporting the unsmoothed grid and letting Blender smooth it (the user asked for the picture's surface).

## Decision 3: Heights are scaled by the whole file; colors follow the picture

- **Decision**: contour `Z = 12 * value / peak` (`peak` the largest value of the whole file, 0 gives all Z = 0); colors: the colormap row `round(255 * clip(value / scale, 0, 1))` where `scale` is the
  largest value of the frame before the beat wave (`vmax=top` of the picture); for a frame in which the picture draws one flat color (`peak <= 0`, or every value equal), every point has that flat
  color (the picture's `_flat_frame`: the value on the scale of the whole file's peak). Wireframe `Z = 12 * share` where `share = SMALLEST + (1 - SMALLEST) * min(points, SIZE_POINTS) / SIZE_POINTS`
  (1/12 to 1, from `decay`), so Z is from 1 to 12; the color of a line is `line_colors()` for its frame.
- **Rationale**: a height scaled by each frame's own maximum would make a quiet frame as tall as a loud one and the animation would flicker in height; the whole-file peak keeps the heights
  comparable (the spec's assumption). The color has to agree with the picture, which uses each frame's own scale.
- **Alternatives considered**: Z by each frame's maximum (flicker); colors on the whole-file scale (a quiet frame would be one dark color, unlike the picture).

## Decision 4: What a Wireframe file holds

- **Decision**: the file of frame `i` holds `min(i + 1, 12)` lines, line `j` being frame `i - j` at `Y = j`, each of the 12 letter points at `X = letter` (0 = A); faces join the points of line `j`
  and `j + 1` that are neighbours along X: `11 * (lines - 1)` faces. The data is `chromatic_decay.circle_points()` (the points of every letter of every frame, as the picture draws it), computed once
  in `write_frames`.
- **Rationale**: the user's answer (this frame and the 11 before it). A fixed window (12), unlike the picture's window which depends on the picture's height, keeps Y between 0 and 11 for every
  job.
- **Alternatives considered**: two lines (one strip); the whole history (Y unbounded): both rejected by the user's answer.

## Decision 5: Coordinates, orientation and faces

- **Decision**: X right, Y away, Z up (Blender's import default); one unit per grid cell: Contour X 0..11, Y 0..6 (Y = the row of the picture's grid counted from the bottom, so the picture seen from
  above has the picture's orientation: the first row of notes at the top is the highest Y), Z 0..12; Wireframe X 0..11, Y 0..11, Z 1..12. A quad is written `f a b c d` with the corners in the order
  `(row, col), (row, col + 1), (row + 1, col + 1), (row + 1, col)`: counterclockwise seen from +Z, so its normal points up.
- **Rationale**: the spec's assumptions; the orientation makes the shading come out right in Blender without flipping normals.

## Decision 6: The file text

- **Decision**: ASCII, `\n` line ends, a three-line header of comments (`# ...`) and `o frame_NNNNNN`, then one `v x y z r g b` per point and one `f a b c d` per face. Positions with 4 decimals,
  colors with 4 decimals (`row / 255`, the colormap tables are 8-bit so this is lossless to 4 places). Numbers are formatted with `format(x, ".4f")` (Python's formatting does not depend on the
  locale), `-0.0000` is turned into `0.0000`.
- **Rationale**: FR-003 and FR-015: the same input must give the same bytes on every machine and in every language setting. Comments and the `o` line are valid OBJ and are skipped by readers.
- **Alternatives considered**: `repr` of floats (long and platform-stable but noisy); `%g` (can give exponents).

## Decision 7: Where the files live and how they are delivered

- **Decision**: written to `frames_temp_dir/<job>/obj/frame_000000.obj` and up (6 digits like the PNGs, so `frame_000012.obj` goes with `frame_000012.png`; the spec's `frame_0.obj` was an
  illustration). `GET /api/jobs/{job_id}/obj` makes `output_dir/<job>/obj.zip` from that folder on the first request (stored paths `frame_NNNNNN.obj`, `zipfile.ZIP_DEFLATED`, files added in order,
  a fixed timestamp so the ZIP is also reproducible) and returns it as a download; later requests reuse it. A job without the folder gets 404 `No 3D export was made for this render.`; a malformed job
  number gets 404 `Render not found.` (as the video route).
- **Rationale**: the spec wants all files in one download and none by hand. The video route is the model: a route per job, output in `output_dir/<job>/`. Making the ZIP on request rather than during
  the job keeps the job's time to the OBJ files themselves and costs nothing when the user never downloads.
- **Alternatives considered**: building the ZIP during the job (an archive nobody may want); streaming the ZIP without a file (no reuse, and the video route's pattern is files); a list of file
  links on the page (thousands of links).

## Decision 8: The request field, the refusal and the answer

- **Decision**: form field `export_obj` parsed like `beat_coloring` (not sent: false; `true`, `false`, `1`, `0`, any case; anything else 400 `The 3D export must be true or false.`). With a true
  value and an image type other than `contour` or `chromatic-wireframe`: 400 `The 3D export is only available for Contour and Chromatic Wireframe.` before the file is read (as the settings that
  are refused today). A false value is accepted for every picture. The answer gains `export_obj` (bool) and `obj_url` (`/api/jobs/{job_id}/obj`, or `null` when the export is off).
- **Rationale**: FR-014: a user must never be told they got files they did not get. The answer keys follow the pattern of 044 (`extra_notes`).
- **Alternatives considered**: ignoring the field for other pictures (the spec says refused).

## Decision 9: The page

- **Decision**: a group *3D export* (id `obj-export`) shown right after the group of the type for `contour` and `chromatic-wireframe`, holding one checkbox *Export 3D files (.obj)* (id
  `export-obj`, off by default, an info button with the help text), sent as `export_obj` for every picture (like `beat_coloring`). The result list shows `3D export: yes` for the two pictures when the
  job has it, and a link *Download 3D files (.zip)* to `obj_url` next to the video export. The page sends `false` for other pictures (so a stale checkbox never refuses a job).
- **Rationale**: the spec's Story 3; the same shapes as the *Held notes* group of feature 044.

## Decision 10: Performance and the baseline

- **Decision**: the OBJ writing is a loop over frames in the job's thread after the pictures; no threads. The expected cost is a few tenths of a millisecond per frame beyond the pictures (a contour
  picture takes tens of milliseconds), far under SC-009's 50%. The work is checked with a timing test on 1,000 frames (the export must take under the half of the PNG writing, which is measured with a
  fake or small picture size so the test stays fast) and by hand in the quickstart.
- **Rationale**: the pictures dominate the job.
- **Baseline**: before the first edit, the failing test ids are taken from the 044 baseline (32 ids), and `verify_drawing.py` records the pictures; both are compared at the end.
