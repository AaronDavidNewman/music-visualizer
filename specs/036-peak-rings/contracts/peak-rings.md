# Contract: Peak Rings

## 1. Library (backend/app/services/chromatic_decay.py)

```python
PEAK_RINGS = 12            # the rings of the target
PEAK_RADIUS = 70           # pixels on a 600 x 400 picture: 140 across

def peak_distances(beat) -> np.ndarray
    # (frames,) beat 0..1 -> (frames,) 1 - beat. ValueError for anything that is not one number from 0 to 1 per frame.

def beat_distances(beat) -> np.ndarray
    # (frames,) beat 0..1 -> (frames,) distance stretched over the range of the beat of the file: the highest position is 0, the 1st percentile of the positions
    # inside the peaks (and every frame outside a peak) is 1, held between; with no range it is 1 - beat. (peak_distances stays the plain 1 - beat.)

def ring_levels(beat) -> np.ndarray
    # (frames,) -> (frames, 12): ring 1 = d[t]; ring k (2..12) = mean(d[t-(2k-3)], d[t-(2k-2)]); before the start d = 1.

def peak_circle_geometry(width, height) -> tuple[float, float]
    # (radius, ring_width) in pixels: 70 and 5.83 on 600 x 400; scaled with the picture, never beyond the free middle of the ring of letters.

def write_chromatic_frames(points, colormap, directory, width, height, beat=None) -> None
    # as before; with beat (a (frames,) array of 0..1, one for each row of points) the rings are drawn in the middle of every frame;
    # with beat=None none are. A beat of the wrong length or range is refused with ValueError before anything is written.
```

`frame_rendering.write_frames(..., image_type="chromatic-decay", beat=beat)` passes `beat` on (the job always measures it for this type).

## 2. HTTP

No change: no new request field, no new response field. Frames of `chromatic-decay` now have the rings (the beat is measured as before, with `peak_distance` and `peak_prominence`). Every other image type is unchanged.

## 3. The picture (600 x 400, RGB)

Besides what feature 035 draws (the background and the 12 circles on the ring of radius 150.94 centered at (300, 200)):

| Element | Value |
|---------|-------|
| Target center | (300, 200) |
| Target radius | 70 px (140 across); `70 x min(w, h) / 400` on other sizes |
| Rings | 12, each 5.83 px wide, ring 1 the center disc (radius 5.83) outward to ring 12 |
| Level of ring 1 | the stretched distance (`beat_distances`) of the current frame |
| Level of ring k (2..12) | the mean of the stretched distances of frames `t - (2k - 3)` and `t - (2k - 2)`; frames before the start count as 1 |
| Color | table row `rint(level x 255)` of the colormap: first color at the top of the beat, last at its bottom (the whole colormap is used, whatever range the beat has) |
| Edges | smooth: the outer edge `clip(radius - d + 0.5, 0, 1)`, the edges between rings blended over half a pixel on each side |
| Clearance | the target is inside the free middle of the ring of letters (radius 111.9 px) and never touches a circle |

With `beat=None` there is no target and the picture is exactly the picture of feature 035.
