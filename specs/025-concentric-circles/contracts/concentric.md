# Contract: The Concentric image type (API, library and UI)

The change to the job endpoint, the library functions and the settings page. Everything not listed here is as in the earlier contracts.

## `POST /api/jobs`

The existing optional field `image_type` accepts a sixth value, `concentric`. No new field is added.

| Field | Rule for `concentric` |
|-------|-----------------------|
| `image_type` | Exactly `tiles`, `blended`, `contour`, `circles`, `circles_paint` or `concentric` (lowercase, no spaces). Anything else, including empty: HTTP 400 `The image type must be one of tiles, blended, contour, circles, circles_paint, concentric.` (before any audio is read). |
| `peak_distance`, `peak_prominence` | As in feature 024 (100 to 2000 ms, default 100; 0 to 100 percent, default 50; same messages), and **always used**: the beat is measured from the audio for every Concentric job. Checked before the file is read. |
| `beat_coloring` | Parsed as before (`true`, `false`, `1`, `0`) and echoed; **no effect** on Concentric. |
| `smoothing`, `smoothing_window`, `colormap` | Apply. |
| `threshold`, `note_count`, `resolution`, `interpolate`, `gaussian`, `blend_width`, the circle fields | Validated as before, accepted and ignored. |

The response is as for the other types: `image_type` is `concentric`, and the values of every field are reported.

## The frames

`GET /api/jobs/{job_id}/frames/{index}` (unchanged URL and names): for `concentric` the body is an RGB PNG of **600 × 400** pixels.

- 84 circles centered on the tiles of the 12 × 7 grid, full radius 25 px, on a background of the colormap's middle color (table row 128).
- The circle of a note has `step` rings, `step = clip(ceil(12 × sqrt(value ÷ loudest) − 1e-9), 1, 12)` (1 for every note of a silent frame); ring `k` is flat in the colormap's color at row `rint((k − 1) / 11 × (0.5 + 0.5 × position) × 255)`, `position` being the frame's position in the local peak (0 when none is known); the edges are smooth.
- The number, names and timing of the frames are those of the other types. The five other image types are byte-identical to before.

## Library

```python
# app/services/concentric.py
RINGS = 12
ring_steps(values) -> int array (frames, 84)               # the steps, 1..12
ring_colors(colormap, beat) -> uint8 array (frames, 12, 3)  # the color of each ring of each frame
write_concentric_frames(values, colormap, directory, beat=None, width=600, height=400) -> None
    # values: (frames, 84) smoothed note values; beat: None (position 0) or (frames,) numbers 0..1

# app/services/frame_rendering.py
write_frames(..., image_type="concentric", beat=...)   # draws it; every setting is still checked; the grid settings are ignored
```

## The settings page

- **Image type** offers six choices; Concentric is the sixth, labelled "Concentric".
- For Concentric the groups are Analysis, Colormap, Image type, **Local peaks** (Minimum distance and Prominence, no Beat coloring checkbox) and Data smoothing; there is no group of its own and no Image smoothing group.
- For Tiles and Blended tiles the Local peaks group still has the checkbox as in feature 024; for the other types there is no Local peaks group.
- The values of the controls that Concentric does not show are kept and sent, and ignored by the server.
- The result summary of a Concentric job shows Minimum distance and Prominence, and none of Threshold, Notes, Interpolate, Oversampling, Gaussian smoothing and Beat coloring.
