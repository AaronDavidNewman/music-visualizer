# Contract: The Polar Chords image type (API, library and UI)

The change to the job endpoint, the library functions and the settings page. Rules and shapes: [data-model.md](../data-model.md). Everything not listed is as in the earlier contracts (see [Decay](../../027-decay-circles/contracts/decay.md), [Decay Exp](../../030-decay-exp/contracts/decay-exp.md) and [Chords](../../031-chord-interval-metric/contracts/chords.md)).

## `POST /api/jobs`

The existing optional field `image_type` accepts a ninth value, `polar-chords`. One new optional field is added.

| Field | Rule for `polar-chords` |
|-------|--------------------------|
| `image_type` | Exactly `tiles`, `blended`, `contour`, `circles`, `circles_paint`, `concentric`, `decay`, `decay-exp` or `polar-chords` (lowercase, a hyphen). Anything else, including empty: HTTP 400 `The image type must be one of tiles, blended, contour, circles, circles_paint, concentric, decay, decay-exp, polar-chords.` (before any audio is read). |
| `polar_notes` (new) | A whole number from 5 to 8, as text; not sent means 5. Anything else (also 4, 9, 6.5, `abc`, empty, `nan`): HTTP 400 `The number of notes shown must be a whole number from 5 to 8.` (before any audio is read). Checked for every image type; used by `polar-chords` only. |
| `peak_distance`, `peak_prominence` | As in feature 024 and always used: the beat is measured for every Polar Chords job. Checked before the file is read. |
| `smoothing`, `smoothing_window`, `colormap` | Apply. |
| `note_layout` | `rows` (default) or `spiral` as for the other pictures; gives the arc of each note (arc = the cell in which the layout draws the note); the chord bar does not depend on it. Anything else: HTTP 400 `The note layout must be one of rows, spiral.` (before any audio is read). |
| `threshold`, `note_count`, `resolution`, `interpolate`, `gaussian`, `blend_width`, `beat_coloring`, the circle, wave and decay fields | Validated as before, accepted and ignored. |

The response is as for the other types: `image_type` is `polar-chords`, and every field is reported, with the new key `polar_notes` (a number).

## The frames

`GET /api/jobs/{job_id}/frames/{index}` (unchanged URL and names): for `polar-chords` the body is an RGB PNG of **600 × 400** pixels.

- The background is the colormap's middle color (table row 128). The circle is centered at `(300, 200)` with the full radius `R = 190` pixels. Bars start at the center.
- **Note bars**: for each of the `polar_notes` loudest notes of the frame (strength above 0, ties to the lower note), a wedge filling the arc of the note, `Δ = 360° / 84` wide, starting at `arc × Δ` **clockwise** from straight up, `arc` being the number of the note's cell in the note layout (with `rows` the note number; with `spiral` middle C, note 27, is arc 29), reaching out to `(0.5 + 0.5 × p) × R`, `p` the frame's position in the local energy peak (0 without a beat). Color: table row `rint((0.5 − 0.5 × s) × 255)`, `s = sqrt(value / peak)`.
- **Following**: the bar of each volume (the loudest note of the frame, the second loudest, ...) keeps its arc from frame to frame. In the first frame, and after a frame in which the volume had no note, it is in the arc of its note. Otherwise it moves one arc (`Δ`) toward the arc of its note in the frame, the shorter way round (clockwise when both ways are as long), and stays when it is there. The color and the strength are those of the note at once. Where two bars are in the same arc, only the louder is drawn. The chord bar and the length do not follow anything.
- **Chord bar**: for the chord that the chord interval measurement records for the frame among `(7)`, `(4, 7)`, `(3, 7)`, `(4, 10)`, `(4, 11)`, `(3, 7, 10)`, `(4, 6)`, one wedge in the arc `7 × root letter + type` (0 to 83; the letters from A, the types numbered 0 to 6 in this order), `360° / 84` wide, starting at `place × 360° / 84` **counterclockwise** from straight up, the same length. The octave and the inversion do not change the place. Color: table row `rint((0.5 + 0.5 × s) × 255)`, `s = sqrt(mean strength of the chord's notes / peak)`. Drawn over the note bars. No recorded chord: no chord bar.
- The edges of the wedges and their tips are smooth (antialiased).
- The number, names and timing of the frames are those of the other types. The other eight image types are byte-identical to before.

## Library

```python
# app/services/polar_chords.py
POLAR_CHORD_TYPES = ((7,), (4, 7), (3, 7), (4, 10), (4, 11), (3, 7, 10), (4, 6))
MIN_POLAR_NOTES, MAX_POLAR_NOTES, DEFAULT_POLAR_NOTES = 5, 8, 5
ARCS = 84                                                    # the arcs of the notes
CHORD_ROOTS = 12                                             # the letters a chord can be built on
CHORD_ARCS = 84                                              # the arcs of the chords: one for each chord type on each letter

check_polar_notes(value) -> int                               # 5..8, else ValueError with the message above
chord_place(chord_type, root) -> int                          # 7 * root + the index of the type among POLAR_CHORD_TYPES, 0..83 (root 0..11, 0 is A)
chord_root(chord_type, inversion, lowest_note) -> int         # the letter the chord is built on, 0..11
note_targets(smoothed, count=5, note_layout="rows") -> (arcs, shares)  # the arc and the strength share of the note of each volume of every frame (-1 and 0 for none)
follow_arcs(targets) -> int16 array                            # where the bars are when each moves one arc a frame toward its target
polar_bars(smoothed, beat=None, count=5, note_layout="rows") -> PolarBars         # the bars of every frame (data-model "Polar bars")
write_polar_frames(bars, colormap, directory, width=600, height=400) -> None   # one PNG per frame

# app/services/frame_rendering.py
write_frames(..., image_type="polar-chords", polar_notes=5, beat=..., ...)    # draws it; every setting is still checked
```

## The settings page

- **Image type** offers nine choices; Polar Chords is the ninth, labelled "Polar Chords".
- For Polar Chords the groups are Analysis, Colormap, Image type, **Polar chords** (the slider **Notes shown**, 5 to 8 in steps of 1, default 5), **Note layout** (Rows or Spiral), **Local peaks** (Minimum distance and Prominence, no Beat coloring checkbox) and Data smoothing; there is no Image smoothing and no Threshold/Notes group.
- The values of the controls that Polar Chords does not show are kept and sent, and ignored by the server.
- The result summary of a Polar Chords job shows Notes shown, Note layout, Minimum distance and Prominence, and none of Threshold, Notes, Interpolate, Oversampling, Gaussian smoothing and Beat coloring.
