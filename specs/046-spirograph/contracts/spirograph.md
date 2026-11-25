# Contract: Spirograph

The interfaces this feature adds or changes: the request, the response, the library and the picture. Nothing else changes.

## 1. The request (`POST /api/jobs`)

`image_type=spirograph` is a new allowed value (the list in the 400 message becomes `contour, decay, decay-exp, polar-chords,
energy-graphs, chromatic-decay, rhythm-circles, chromatic-wireframe, polychord, spirograph`). Three new form fields (`spirograph_fade` added 2026-11-22), sent or not
for every image type (they are checked for every type and used by Spirograph only):

| Field | Meaning | Allowed | Default (not sent) | Refusal (400, before the file is read, no files left) |
|---|---|---|---|---|
| `spirograph_notes` | tracked notes in each frame | a whole number 5 to 12 | 8 | `The number of spirograph notes must be a whole number from 5 to 12.` |
| `spirograph_history` | history entries in each picture | a whole number 5 to 12 | 8 | `The history length must be a whole number from 5 to 12.` |
| `spirograph_fade` | the factor an entry's values are multiplied by for each frame it is older | a number 0.4 to 0.85 | 0.7 | `The history fade must be a number from 0.4 to 0.85.` |

A text, an empty value, `nan` or `inf`, and a number outside its range are all refused (for the two whole-number settings also a fraction such as `7.5`). A value is accepted
for another image type if it is allowed, refused if it is not (as `polychord_notes` is).

**Extra notes** (`extra_notes`, feature 044) applies to Spirograph: a whole number from 1 to the smaller of
`spirograph_notes` and 8 (a larger number is a 400 `The extra notes must be a whole number from 1 to <limit>.` with that limit);
not sent is 2 (but never above the limit: with 5 notes the default is 2, which is allowed).

**Peak distance** (`peak_distance`, the Minimum distance of the Local peaks, since 2026-11-24) is used by Spirograph: the job measures the local peaks with it and the beat of every frame sets the turns and the big circle's radius of its entry's curves.

Ignored by Spirograph (accepted as for any type): threshold, resolution, note count, interpolate, gaussian, beat coloring,
note layout, decay rate, wave count, polar notes, the Polychord settings, the decay amounts, export OBJ off
(`export_obj=true` is refused for Spirograph as for any type other than Contour and Chromatic Wireframe).

## 2. The response

Three new keys for every job: `spirograph_notes` (int), `spirograph_history` (int) and `spirograph_fade` (float), the values used. All other keys are
unchanged. The exact-key tests of the existing API gain these three keys.

## 3. The library

`frame_rendering.write_frames(..., spirograph_settings: SpirographSettings = DEFAULT_SPIROGRAPH_SETTINGS)`: checked for every
image type (anything that is not a `SpirographSettings` with allowed values is a `ValueError`); used by `spirograph` only. For
`image_type="spirograph"` it calls `spirograph.write_spirograph_frames(frames, spirograph_settings, colormap, directory,
IMAGE_WIDTH, IMAGE_HEIGHT, extra_notes, beat)` and returns; `beat` (`BeatPositions` `(frames,)` or `None`: every frame at the top of a peak) is used; no `energy`, `rhythm` or `polychord` data is needed or used. `jobs.create_job` measures the beat for Spirograph.
`held_notes.notes_of(image_type, polar_notes, polychord_notes, spirograph_notes=MAX_EXTRA_NOTES)` returns
`min(spirograph_notes, MAX_EXTRA_NOTES)` for `spirograph`; `HELD_NOTES_TYPES` has seven names.

`spirograph.write_spirograph_frames` checks everything first (settings, colormap, values, size, extra notes), writes nothing for
a refusal, then creates the directory and saves `frame_000000.png` and up.

## 4. The picture

600 x 400, three channels, **black** background. For frame `t` with window rows `r = max(0, t - history + 1)` to `t` (oldest
first) and places `j = 0 .. notes - 1` (loudest first), for each step with `val = TrackedValues[r, j] > 0`:

- `loops = (LoudestIndices[r, j] mod 12) val`, `pct = PeakPercents[r]` (1 at the top of the local peak, 0 at the bottom of it), `rc = 5` if `pct > 0.5` else `4`, `turns = 14 pct + 6`;
- points `k = 0 .. 999`, `c1 = 2 pi k / 999`, `c2 = 2 pi turns k / 999`:
  `X = val (rc cos c1 + loops cos c2)`, `Y = val (rc sin c1 + loops sin c2)`;
- pixel `(width / 2 + k X, height / 2 - k Y)`, `k = radius / ext` with `ext = val (rc + loops)` and `radius = smallest + (full - smallest) * min(1, ext s / full)`: `s` the one scale of the file (`pixels_per_unit(file_extent(...))`), `full = min(width, height) / 2 - 10 - 5`, `smallest = min(width, height) / 4` (so every curve is between half the smallest side and the full size across);
- color `ReducedColors[min(floor(12 val), 12)]`, a line 3 pixels wide for the picture's own frame (age 0) and `2 - (age - 1) / (history - 2)` pixels for age 1 and up, rounded half up (2 for age 1 down to 1 for the oldest place; at least 1), anti-aliased.

A frame with no curve is entirely black. The same file and settings give identical pictures (also with several threads). The
frames have the usual names, count and timing and can be made into a movie (feature 029).

## 5. The page

The Image type list has **Spirograph** after Polychord. With it chosen the page shows the group **Spirograph** (Number of notes,
History length: sliders 5 to 12, readouts `8 notes` and `8 frames`; History fade: slider 0.4 to 0.85 in steps of 0.05, readout `0.7 per frame`), then **Held notes** (its slider's top is the smaller of the
number of notes and 8); then **Local peaks** (Minimum distance only, the group `concentric-peaks`); it shows no Note layout, no Beat coloring, no 3D export and no Image smoothing. The values are validated
on the page with the backend's messages and sent as `spirograph_notes` and `spirograph_history`; the result list shows
`Number of notes: n`, `History length: n` and `History fade: x` for this type.
