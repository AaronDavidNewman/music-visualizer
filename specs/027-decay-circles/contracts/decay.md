# Contract: The Decay image type (API, library and UI)

The change to the job endpoint, the library functions and the settings page. Everything not listed here is as in the earlier contracts (see [Concentric](../../025-concentric-circles/contracts/concentric.md) and [Note layout](../../026-spiral-note-layout/contracts/note-layout.md)).

## `POST /api/jobs`

The existing optional field `image_type` accepts a seventh value, `decay`. One new optional field is added.

| Field | Rule for `decay` |
|-------|------------------|
| `image_type` | Exactly `tiles`, `blended`, `contour`, `circles`, `circles_paint`, `concentric` or `decay` (lowercase, no spaces). Anything else, including empty: HTTP 400 `The image type must be one of tiles, blended, contour, circles, circles_paint, concentric, decay.` (before any audio is read). |
| `decay_rate` (new) | A whole number from 1 to 10, as text; not sent means 5. Anything else: HTTP 400 `The decay rate must be a whole number from 1 to 10.` (before any audio is read). Checked for every image type; used by `decay` only. |
| `peak_distance`, `peak_prominence` | As in feature 024 and always used: the beat is measured for every Decay job. Checked before the file is read. |
| `note_layout` | Applies (`rows` or `spiral`), as for Concentric. |
| `beat_coloring` | Parsed and echoed as before; no effect on Decay. |
| `smoothing`, `smoothing_window`, `colormap` | Apply. |
| `threshold`, `note_count`, `resolution`, `interpolate`, `gaussian`, `blend_width`, the circle fields | Validated as before, accepted and ignored. |

The response is as for the other types: `image_type` is `decay`, and the values of every field are reported, with the new key `decay_rate` (a number).

## The frames

`GET /api/jobs/{job_id}/frames/{index}` (unchanged URL and names): for `decay` the body is an RGB PNG of **600 × 400** pixels.

- 84 circles centered on the cells of the 12 × 7 grid (in the note layout chosen), on a background of the colormap's middle color.
- The circle of a cell with `p` points has the radius `25 × (1/12 + 11/12 × min(p, 24) / 24)` pixels and are flat in the color at table row `rint(min(p, 32) / 32 × 255)` up to 32 points; above 32 points they are the 12 concentric rings of Concentric, ring `k` at table row `rint((b − s × (k − 1) / 11) × 255)` with `b = min(p, 32) / 32` and `s = max(0, p − 32) / 32` (ring 1 the last color, ring 12 the first at 64 points); the edges, also those between rings, are smooth.
- `p` is kept from frame to frame: it starts at 0, gains `24, 20, 16, 12, 8` (+ `8 × position`) on the five loudest notes of each frame, and every `decay_rate` frames (frame numbers counted from 1) each cell sends 2 points to each of its neighbours and loses 16 in all, as in the [data model](../data-model.md).
- The number, names and timing of the frames are those of the other types. The other six image types are byte-identical to before.

## Library

```python
# app/services/decay.py
MIN_DECAY_RATE, MAX_DECAY_RATE, DEFAULT_DECAY_RATE = 1, 10, 5
check_decay_rate(value) -> int                     # a whole number 1..10, else ValueError with the message above
gains(values, beat) -> float array (frames, 84)     # per note, in note order
circle_points(values, beat, note_layout, decay_rate) -> float array (frames, 84)   # points per cell, in cell order, after each frame
circle_radii(points) -> float array                 # pixels on the 600 x 400 frame
circle_colors(points, colormap) -> uint8 array (..., 3)
write_decay_frames(points, colormap, directory, width=600, height=400) -> None

# app/services/frame_rendering.py
write_frames(..., image_type="decay", decay_rate=5, beat=..., note_layout=...)   # draws it; every setting is still checked
```

## The settings page

- **Image type** offers seven choices; Decay is the seventh, labelled "Decay".
- For Decay the groups are Analysis, Colormap, Image type, **Decay** (one slider, **Decay rate**, 1 to 10 frames, default 5), **Note layout**, **Local peaks** (Minimum distance and Prominence, no Beat coloring checkbox) and Data smoothing; there is no Image smoothing group and no Threshold/Notes group.
- The values of the controls that Decay does not show are kept and sent, and ignored by the server.
- The result summary of a Decay job shows Decay rate, Note layout, Minimum distance and Prominence, and none of Threshold, Notes, Interpolate, Oversampling, Gaussian smoothing and Beat coloring.
