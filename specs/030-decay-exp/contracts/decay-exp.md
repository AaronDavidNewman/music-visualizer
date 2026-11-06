# Contract: The Decay Exp image type (API, library and UI)

The change to the job endpoint, the library functions and the settings page. Everything not listed here is as in the [Decay contract](../../027-decay-circles/contracts/decay.md).

## `POST /api/jobs`

The existing optional field `image_type` accepts an eighth value, `decay-exp`. No field is added.

| Field | Rule for `decay-exp` |
|-------|----------------------|
| `image_type` | Exactly `tiles`, `blended`, `contour`, `circles`, `circles_paint`, `concentric`, `decay` or `decay-exp` (lowercase, a hyphen). Anything else, including empty: HTTP 400 `The image type must be one of tiles, blended, contour, circles, circles_paint, concentric, decay, decay-exp.` (before any audio is read). |
| `decay_rate` | As for `decay` (0.25 to 4 in steps of 0.25, default 1, same refusal message); used by `decay-exp`. |
| `decay_low`, `decay_medium`, `decay_high`, `decay_saturated` | Checked as always (0.5 to 3, same refusal messages, before any audio is read), echoed in the response, **no effect** on `decay-exp`. |
| `peak_distance`, `peak_prominence` | As for `decay`: always used, the beat is measured for every `decay-exp` job. |
| `note_layout`, `smoothing`, `smoothing_window`, `colormap` | Apply, as for `decay`. |
| `beat_coloring`, `threshold`, `note_count`, `resolution`, `interpolate`, `gaussian`, `blend_width`, the circle fields | Validated as before, accepted and ignored. |

The response is as for the other types: `image_type` is `decay-exp`; the keys are those of every job (no new key).

## The frames

`GET /api/jobs/{job_id}/frames/{index}` (unchanged URL and names): for `decay-exp` the body is an RGB PNG of **600 × 400** pixels, drawn exactly as `decay` draws circles with the same points (size, color, rings, places, background, edges).

The points `p` of each cell start at 0 and are kept from frame to frame:

- **Gain**: for each of the five loudest notes of a frame (ties to the lower note, value 0 excluded), with `g = (24, 20, 16, 12, 8)[rank] + 8 × position`, the cell gains `g × e^(−g/t)`, `t` being the taper of the frame (8 in the first frame, then up 0.01 a frame to 12; down 0.01 a frame, to 8, once more than 10 cells have more than 32 points at the end of a frame, and up again from 8); held between 0 and 64.
- **Decay step** at the times `decay_rate`, `2 × decay_rate`, ... frames (frame `i` has the steps in `(i − 1, i]`): a cell with `p > 0` points gives `min(p, 8 × decay_rate × sin²(π/2 × p/64))` in all, one eighth to each neighbour that exists, the rest lost (edge and corner cells lose as if they had 8 neighbours); all cells use the points before the step; the result is held between 0 and 64 and a cell under 0.01 points becomes 0.
- The number, names and timing of the frames are those of the other types. The other seven image types, `decay` included, are byte-identical to before.

## Library

```python
# app/services/decay.py (refactor, no change of result)
_spread(points, give) -> float array (7, 12)       # the part of decay_step after give is known

# app/services/decay_exp.py (new)
TAPER, MAX_TAPER, TAPER_STEP = 8, 12, 0.01          # the taper of the gain e^(-g/taper): start and lowest, highest, step per frame
FULL_POINTS, FULL_CIRCLES = 32, 10                  # more than 10 circles over 32 points turn the taper down
taper_of(steps) -> float                            # 8 + 0.01 * steps, steps a whole number 0..400
next_taper(steps, rising, full_circles) -> (steps, rising)   # the taper for the next frame
circle_tapers(values, beat, note_layout, decay_rate) -> float array (frames,)   # the taper of every frame
exp_gains(values, beat=None, taper=8) -> float array (frames, 84)   # gains(values, beat) * exp(-gains / taper), in note order; taper a number or one for each frame
exp_loss_per_frame(points) -> float array           # sin(pi / 2 * points / 64) ** 2 where points > 0, else 0
decay_exp_step(points, frames=1) -> float array (7, 12)         # one step of `frames` frames' worth
circle_points(values, beat=None, note_layout=..., decay_rate=1.0) -> float array (frames, 84)

# app/services/frame_rendering.py
write_frames(..., image_type="decay-exp", decay_rate=1, decay_amounts=..., beat=..., note_layout=...)   # draws it; every setting is still checked
```

## The settings page

- **Image type** offers eight choices; Decay Exp is the eighth, labelled "Decay Exp".
- For Decay Exp the groups are Analysis, Colormap, Image type, **Decay** (the slider **Decay rate** only, 0.25 to 4 in steps of 0.25, default 1), **Note layout**, **Local peaks** (Minimum distance and Prominence, no Beat coloring checkbox) and Data smoothing; no Image smoothing group, no Threshold/Notes group, and no saturation sliders.
- The values of the controls that Decay Exp does not show are kept and sent, and ignored by the server.
- The result summary of a Decay Exp job shows Decay rate, Note layout, Minimum distance and Prominence, and none of Threshold, Notes, Interpolate, Oversampling, Gaussian smoothing, Beat coloring or the four saturation decays.
