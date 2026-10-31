# Contract: The Contour beat wave (API, library and UI)

The change to the job endpoint, the library functions and the settings page. Everything not listed here is as in the earlier contracts (Contour, feature 015; beat coloring, feature 024).

## `POST /api/jobs`

One new optional field, `wave_count`. The existing `beat_coloring`, `peak_distance` and `peak_prominence` now also apply to `image_type=contour`.

| Field | Rule |
|-------|------|
| `wave_count` (new) | A whole number from 2 to 10, as text; not sent means 4. Anything else (also `1`, `11`, `2.5`, `abc`, empty): HTTP 400 `The wave count must be a whole number from 2 to 10.` before any audio is read. Checked for every image type; used by `contour` with `beat_coloring` true only. |
| `beat_coloring` | As before. For `contour`: `true` turns the beat wave on and makes the server measure the beat; `false` or not sent: the plain Contour, no measurement. |
| `peak_distance`, `peak_prominence` | As in feature 024 (100 to 2000 ms, default 100; 0 to 100 percent, default 50; same messages), checked before the file is read for every type; used by `contour` when `beat_coloring` is true. |
| the other fields | As before. |

The response is as for the other types, with the new key `wave_count` (a number) for every image type.

## The frames

`GET /api/jobs/{job_id}/frames/{index}` (unchanged URL and names): for `contour` a 600 × 400 RGB PNG.

- With `beat_coloring` off: exactly the plain Contour picture of before this feature.
- With it on: for a frame at position `k` in the local peak, the frame's grid of values is multiplied by `1 − pattern × sin(π × k)` (the [data model](../data-model.md)) before the contour is drawn; the color scale is that of the unmodified frame; at `k = 0` (the minimum of the beat, no beat known) the picture is byte-identical to the plain one, the effect is deepest half way up the beat and is (all but exactly) gone again at `k = 1`.
- The number, names and timing of the frames are those of the other types. The other six image types are byte-identical to before.

## Library

```python
# app/services/beat_wave.py
MIN_WAVE_COUNT, MAX_WAVE_COUNT, DEFAULT_WAVE_COUNT = 2, 10, 4
check_wave_count(value) -> int                  # a whole number 2..10, else ValueError with the message above
wave_pattern(rows, columns, waves) -> float array (rows, columns)    # 0..1, cached, read-only
wave_modifier(rows, columns, waves, k) -> float array (rows, columns)  # 1 - pattern * sin(pi * k), k in 0..1

# app/services/contour.py
write_contour_frames(values, peak, colormap, directory, columns, rows, width, height, indices=None,
                     beat=None, waves=DEFAULT_WAVE_COUNT) -> None
    # beat: None or (frames,) numbers 0..1; the frames with k = 0 are drawn as without

# app/services/frame_rendering.py
write_frames(..., image_type="contour", beat=..., wave_count=4)   # the wave count is checked for every type
```

## The settings page

- **Image type**: unchanged (seven choices).
- For Contour the groups are Analysis, Colormap, Image type, **Contour** (Threshold, Notes and the new **Wave count**, 2 to 10 waves, default 4), **Local peaks** (the Beat coloring checkbox, Minimum distance and Prominence), Data smoothing and Image smoothing.
- For Tiles and Blended tiles nothing changes; Wave count is not shown for any other type.
- The result summary of a Contour job shows Beat coloring, and, when it is on, Minimum distance, Prominence and Wave count.
