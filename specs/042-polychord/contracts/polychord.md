# Contract: Polychord

## Request

`POST` of the existing job endpoint (`/api/jobs`) with `image_type=polychord`. Four new form fields, all optional (not sent
means the default); each is parsed **before the file is read**, so a refusal is a 400 that leaves no files behind:

| Field | Meaning | Allowed | Default | 400 message when refused |
|---|---|---|---|---|
| `polychord_notes` | links in one figure | whole number 5 to 8 (`6` and `6.0` accepted, `5.5`, `4`, `9`, text, empty, `nan` refused) | 6 | `The number of notes must be a whole number from 5 to 8.` |
| `polychord_min_copies` | figures at the lowest point of the beat | whole number 1 to 12 | 3 | `The minimum number of copies must be a whole number from 1 to 12.` |
| `polychord_max_copies` | figures at the top of a peak | whole number 1 to 12 | 12 | `The maximum number of copies must be a whole number from 1 to 12.` |
| (both copies fields) | | maximum not under minimum | | `The maximum number of copies must not be less than the minimum.` |
| `polychord_rotation` | degrees a second the picture turns (negative: the other way; 0 holds still) | finite number -360 to 360 | 15 | `The rotation must be a number from -360 to 360 degrees a second.` |

The settings that apply to this type besides these four: `colormap`, the analysis settings (`window_size`, `frame_rate`,
`window_spacing`), `smoothing` and `smoothing_window`, and the local peaks setting `peak_distance` (it decides the beat and
the tempo). `threshold`, `note_layout`, `decay_rate`, the four decay amounts, `polar_notes` and every grid setting are
accepted, checked as for every type and ignored. The four new fields sent with another image type are checked and ignored.

The 400 for an unknown `image_type` lists the nine names, ending `..., rhythm-circles, chromatic-wireframe, polychord.`
Every other type's request handling and frames are unchanged.

## Response

As for the other types, plus `polychord_notes`, `polychord_min_copies`, `polychord_max_copies` (integers) and
`polychord_rotation` (a float) echoing the values used; `image_type` is echoed as `polychord`.

## Library (`app/services/polychord.py`)

```text
check_polychord_notes(value) -> int                        # whole number 5..8 or ValueError(NOTES_MESSAGE)
check_polychord_copies(value, name) -> int                 # whole number 1..12 or ValueError
check_polychord_rotation(value) -> float                   # finite -360..360 or ValueError
check_polychord_settings(settings) -> PolychordSettings    # all four + maximum >= minimum
loudest_letters(values, count) -> LoudLetters              # (frames, count) int, -1 where fewer sound
link_turns(letters) -> LinkTurns                           # (frames, count) float degrees, 30 x steps round the circle of fifths
copy_counts(beat, min_copies, max_copies, frames=None) -> CopyCounts          # (frames,) int
frame_tempos(peaks, frame_rate, frames) -> FrameTempos     # (frames,) beats a minute, 60..156, 120 before the first peak
start_angles(rotation, frame_rate, frames) -> StartAngles  # (frames,) degrees
tempo_colors(tempos, colormap) -> FigureColors             # (frames, 3) uint8
link_length(width, height, notes) -> float                 # pixels
figure_segments(turns_row, letters_row, start_angle, copies, width, height, notes)
    -> (LinkSegments, LinkWidths)                          # the pieces of every copy of one frame
write_polychord_frames(values, beat, tempos, settings, frame_rate, colormap, directory, width, height) -> None
```

`write_frames(..., image_type="polychord", beat=..., polychord=PolychordData(tempos, frame_rate),
polychord_settings=PolychordSettings(...))` smooths the notes and calls `write_polychord_frames`; `polychord` is required for
this type (`ValueError` when missing or when its tempos do not have one value for each frame) and ignored by the others.

`PolychordData` (frozen dataclass): `tempos` (`FrameTempos`, `(frames,)`) and `frame_rate` (float, > 0).

## The picture

600 x 400 RGB PNG (`frame_000000.png` and up), background **black** (`(0, 0, 0)`), drawn by one matplotlib `LineCollection`.
Per spec: the first link starts at the center for the loudest note; every later link starts at the end of the previous one
and turns by 22.5 degrees for every step of a fifth between the letters (same letter straight on, tritone 135 degrees backwards; each link squeezed to 2/3 across and 1/2 down); links
are thinner at their end than at their start and each link starts as wide as the previous one ends; the figure is drawn
`copies` times, each turned 30 degrees further, `copies` going from the minimum at the bottom of the beat to the maximum at
the top; the first copy starts at `rotation x t / frame_rate` degrees; every link of a frame has one color from the tempo
(slow = first colormap color, fast = last); no pixel outside the picture; a frame with no sound is entirely black; identical
bytes for identical input.
