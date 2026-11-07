# Data Model: Polar Chords

Entities of [spec.md](spec.md). Notes, chord records and the beat are those of features 031 and 024.

## The circle and its arcs

- The picture is 600 × 400 on the colormap's middle color (table row 128). The center is `(300, 200)`; the **full radius** is `R = min(width, height) / 2 − 10 = 190` pixels.
- The notes have **84 arcs** of `Δ = 360° ÷ 84 ≈ 4.2857°`; the chords have **84 arcs** too (12 letters × 7 types), `Δ' = Δ` (revised 2026-11-07; from 2026-11-06 to 2026-11-07 they had 7 arcs of 51.43°).
- **Angles are measured from straight up.** The notes go **clockwise**, the chords **counterclockwise**.

| Kind | Arc `a` (0 to 83) covers (degrees from straight up) | Direction |
|------|------------------------------------------------------|-----------|
| Note arc `a`: with Rows the note `a` (0 = A1); with Spiral the note that the spiral draws in cell `a` | from `a × Δ` to `(a + 1) × Δ` | clockwise |
| Chord place `a` (0 to 83) | from `a × Δ'` to `(a + 1) × Δ'`, with `Δ' = 360° ÷ 84 ≈ 4.29°` | counterclockwise (the same numbers read the other way: in clockwise terms from `360° − (a + 1) × Δ'` to `360° − a × Δ'`) |

## Chord places

The 7 chord types, in this order (index `t`): `(7)`, `(4, 7)`, `(3, 7)`, `(4, 10)`, `(4, 11)`, `(3, 7, 10)`, `(4, 6)`. **Place = `7 × r + t`** (0 to 83), `r` the root letter (0 to 11, 0 is A: the note number mod 12) and `t` the type. The octave and the inversion do not matter, so a C major triad (`r` = 3, `t` = 1) is place 22 in any voicing. The 7 types of a letter follow one another, then the 7 of the next letter. (Revised 2026-11-07. The first version had 84 places as `t × 12 + root`; the revision of 2026-11-06 had 7, the type alone.)

The root `r` is worked out from the record of the chord measurement: the lowest recorded note `L` is the tone `(0, *type)[inversion]` above the root, so `r = (L − (0, *type)[inversion]) mod 12`. A fourth (C with F above it, recorded as the inverted fifth `(7)`, inversion 1, `L` = C) has `r` = C − 7 = F.

Examples: C4 E4 G4, E4 G4 C5 and G4 C5 E5 are all `(4, 7)`: place 1. C4 and F4 (27, 32) are `(7)` in first inversion, as is C4 and G4 in root position: place 0. A C E (12, 15, 19) is `(3, 7)`: place 2.

## Bars of a frame

| Name | Meaning |
|------|---------|
| `position` `p` | The frame's place in the local energy peak, 0 to 1 (0 when no beat is known) |
| `length` | `0.5 + 0.5 × p` (a share of `R`) |
| Note bars | The `N` loudest notes (`N` = Notes shown, 5 to 8) of the 84 drawn notes, strength above 0, ties to the lower note, each filling its note arc from the center to `length × R` |
| Note strength share `s` | `sqrt(value ÷ peak)` (0 to 1); `peak` = the largest value of the whole smoothed array, all 88 columns; 0 if the peak is 0 |
| Note color | Colormap table row `rint((0.5 − 0.5 × s) × 255)` |
| Chord bar | At most one: the chord recorded for the frame by the chord interval measurement for the 7 types, filling the arc of its type from the center to `length × R` |
| Chord strength share `s` | `sqrt(mean(values of the chord's notes) ÷ peak)` |
| Chord color | Colormap table row `rint((0.5 + 0.5 × s) × 255)` |
| Order of drawing | Background, the note bars, the chord bar over them |

Coverage of a bar at a pixel at distance `r` from the center: `clip(length × R − r + 0.5, 0, 1)`; across an arc edge the neighbouring arc has the share `clip(0.5 − d, 0, 1)` of a pixel whose center is `d` pixels from the edge.

## Following (the note bars move one arc a frame)

For each volume (column of the note bars: 0 the loudest, 1 the second loudest ...) the arc it **is heading for** is the arc of its note in the frame (`-1` if the volume has no note). The arc it **is in** is worked out frame by frame:

| Case | The arc the bar is in |
|------|----------------------|
| The first frame, or a volume that had no note in the frame before | The arc of its note |
| The volume has no note | None (no bar) |
| Otherwise, `d = (target − current) mod 84` | `d = 0`: the same arc. `d` from 1 to 42: `current + 1` (clockwise). `d` from 43 to 83: `current − 1` (counterclockwise), both mod 84 |

A bar thus moves at most one arc a frame, the shorter way round (clockwise for `d = 42`). Where the arcs of two volumes are equal in a frame, the bar of the volume with the higher number is hidden (slot −1, share 0); the following itself goes on. The color and strength share are those of the note of the volume, not of the arc. The chord place, the chord share and the length do not follow anything.

## Polar bars (the worked-out result for a file)

| Field | Shape and type | Meaning |
|-------|----------------|---------|
| `note_slots` | `(frames, N)` int16 | Arc each note bar is drawn in, loudest volume first; −1 where fewer notes sound or where a louder volume's bar is in the same arc |
| `note_shares` | `(frames, N)` float64 | The strength share of each note bar (0 where there is none) |
| `chord_place` | `(frames,)` int16 | Place of the chord bar, `7 × root letter + the number of its type` (0 to 83); −1 for none |
| `chord_share` | `(frames,)` float64 | The strength share of the chord (0 where none) |
| `length` | `(frames,)` float64 | `0.5 + 0.5 × position` |

## Settings

| Setting | Rule |
|---------|------|
| `polar_notes` (Notes shown) | A whole number from 5 to 8, default 5; booleans, fractions and text refused with `The number of notes shown must be a whole number from 5 to 8.`; checked for every image type, used by Polar Chords only; echoed in the response |
| Local peaks (Minimum distance, Prominence), Data smoothing, colormap, analysis | Apply as for Decay (the beat is always measured; no checkbox) |
| `note_layout` | `rows` (the default) or `spiral`, as for the other pictures (`The note layout must be one of rows, spiral.`); gives the arc of each note: arc = the cell in which the layout draws the note (`rows`: the note number; `spiral`: middle C, note 27, is in arc 29); echoed in the response; the chords do not depend on it |
| Threshold, Notes, Oversampling, Interpolate, Gaussian smoothing | Accepted, checked as always, ignored; not shown on the page or in the summary |

## State transitions

None: every frame is independent of the others (unlike Decay).
