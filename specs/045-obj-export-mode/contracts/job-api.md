# Contract: the 3D export in the job API

Changes to `POST /api/jobs` and one new route. Everything else in the job API is unchanged.

## Request: `export_obj` (form field, optional)

| Sent | Result |
|------|--------|
| not sent | `false` |
| `true`, `1` (any case, spaces ignored) | export on |
| `false`, `0` | export off |
| anything else | 400 `{"detail": "The 3D export must be true or false."}` |
| on, with `image_type` other than `contour` or `chromatic-wireframe` | 400 `{"detail": "The 3D export is only available for Contour and Chromatic Wireframe."}` |

The refusals are made before the file is read (no job is made, nothing is written). A false value is accepted for every picture.

The other settings behave as before; for the export they apply as follows:

| Setting | Contour export | Chromatic Wireframe export |
|---------|----------------|----------------------------|
| Colormap, frame rate, analysis settings | as for the pictures | as for the pictures |
| Threshold, Number of notes (`note_count`) | applied (they change the values) | Threshold applied (it changes the points), Number of notes not used by the picture |
| Beat coloring + Wave count | applied (the beat wave multiplies the grid, as in the picture) | not used |
| Resolution | not applied (the export is the 12 x 7 grid) | not used |
| Gaussian, Interpolate | not applied (they change PNG files only) | not used |
| Decay rate, Extra notes (k) | not used | applied (they decide the points) |

## Answer of `POST /api/jobs` (two new keys)

```json
{ "...": "all the existing keys", "export_obj": true, "obj_url": "/api/jobs/<job_id>/obj" }
```

`export_obj` is a boolean; `obj_url` is the download route, or `null` when the export is off. The pictures, `frame_count` and `frame_url_template` are as before.

## New route: `GET /api/jobs/{job_id}/obj`

- 200, `application/zip`, a download named `obj.zip`: all the `.obj` files of the job as `frame_000000.obj` and up, in frame order. The ZIP is made on the first request and kept in the output
  folder of the job.
- 404 `{"detail": "Render not found."}` for a job number that is not 32 hex digits (as the video route).
- 404 `{"detail": "No 3D export was made for this render."}` for a job that has no `obj` folder (the export was off, or the job is gone).

## The `.obj` file

See [data-model.md](../data-model.md): header comments, `o frame_NNNNNN`, `v x y z r g b` lines (position in grid units, color 0 to 1, 4 decimals), `f a b c d` lines (four neighbouring points, counted
from 1, counterclockwise seen from +Z). Contour: 84 points, 66 faces. Chromatic Wireframe: `12 L` points and `11 (L - 1)` faces, `L = min(frame + 1, 12)`.

## Library functions (the surface of `services/obj_export.py`)

```text
contour_mesh(grid, peak, scale, colormap)            -> (MeshVertices, MeshFaces)    # one frame
wireframe_mesh(points, beat_colors, frame)           -> (MeshVertices, MeshFaces)    # one frame and the 11 before it
format_obj(vertices, faces, comment, name)           -> str                          # the file text
write_contour_obj(values, peak, colormap, directory, beat, waves) -> None            # all frames
write_wireframe_obj(points, colormap, directory, beat)            -> None            # all frames
zip_obj_files(directory, archive)                    -> None                         # the ZIP of a job
```

`frame_rendering.write_frames(..., export_obj: bool = False)` writes the files into `directory / "obj"` for `contour` and `chromatic-wireframe` after the pictures; every other value of `image_type`
with `export_obj=True` raises `ValueError`.
