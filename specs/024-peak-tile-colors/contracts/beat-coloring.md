# Contract: Beat coloring (API, library and UI)

The change to the job endpoint, the library functions it uses and the settings page. Everything not listed here is as in the earlier contracts.

## `POST /api/jobs`

Three new optional fields. Not sent means the default.

| Field | Rule |
|-------|------|
| `beat_coloring` | `true`, `false`, `1` or `0` in any case; default `false`. Anything else, including empty: HTTP 400 `The beat coloring must be true or false.` |
| `peak_distance` | A number of milliseconds from 100 to 2000, default 100. Anything else, including empty or not a number: HTTP 400 `The minimum distance must be a number from 100 to 2000 milliseconds.` |
| `peak_prominence` | A number of percent from 0 to 100, default 50. Anything else: HTTP 400 `The prominence must be a number from 0 to 100 percent.` |

All three are checked before the file is read, **whether `beat_coloring` is true or false**, and for every image type.

Effect: for `image_type` `tiles` or `blended` **and** `beat_coloring` true, the job measures the local peaks of the audio with the two values and colors the tiles half by note strength and half by the frame's position in the local peak (data-model.md). In every other case (the checkbox off, or another image type) the frames are byte-identical to those made before this feature; the beat is not measured.

The response adds `beat_coloring` (boolean), `peak_distance` and `peak_prominence` (the values sent or their defaults), for every image type.

## Library

```python
# app/services/local_peaks.py
LocalPeaks.position_at(point)                 # 0..1; float for a number, array for a sequence; ValueError for non-finite
LocalPeaks.position_at_time(seconds)
LocalPeaks.frame_positions(frame_rate, frames)  # float64 array (frames,), the middle of every frame

# app/services/colormaps.py
colorize(smoothed, colormap, shown, peak=None, beat=None)
    # beat: None (as before) or a 1-D array, one number 0..1 per row; index = rint((0.5*sqrt(share) + 0.5*beat) * 255)

# app/services/frame_rendering.py
write_frames(frames, directory, ..., gaussian=0.0, beat=None)
    # beat: None or one number 0..1 per frame; used for tiles and blended, ignored for the other types
```

`position_at` before the first peak and for a file without peaks is 0; after the last peak it is computed from the last peak's `energy`, `window_min` and `window_max`.

## The frames

- Beat coloring off, or any image type but Tiles and Blended tiles: unchanged.
- On, Tiles or Blended tiles: the loudest tile has the colormap's middle color (row 128) at position 0 and the right-most (row 255) at position 1; hidden tiles are drawn as before (black for Tiles, row 128 for Blended tiles); sizes, counts, names, smoothing, resolution, interpolation and Gaussian smoothing are as before.

## The settings page

- A group "Local peaks" (collapsible like the others) with the checkbox "Beat coloring" (off), the slider "Minimum distance" (100 to 2000, step 50, "100 ms") and the slider "Prominence" (0 to 100, step 5, "50%"), two controls per row, the last one alone; shown when the image type is Tiles or Blended tiles, after that type's group; not shown for the other types.
- The three values are kept when the group is folded or the type is changed, and are always sent.
- An invalid value shows the backend's message under the control, marks the group as having a problem, and blocks submitting.
- The result summary, for Tiles and Blended tiles, shows "Beat coloring: Off" or "On", and when on "Minimum distance: 100 ms" and "Prominence: 50%".
