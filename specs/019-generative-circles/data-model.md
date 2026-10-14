# Data Model: Generative Circles

> **Amended 2026-10-14 (feature 020, grouped settings).** On the page the circles settings were renamed: **Unit** is now **Movement**, **Size** is now **Radius**, **Circles per frame** is now **Notes** (and the summary says Memory for the circle memory), all inside a **Circles** group that is shown only for Circles; the controls the type does not use are no longer greyed out but not shown. **The Size setting became a real radius**: a whole number of pixels from **4 to 8** (default 4), request field `circle_radius` with the message `The circle radius must be a whole number from 4 to 8.`, replacing the circumference of 25 to 50 pixels (`circle_size`, now ignored if sent; a radius of 3.98 to 7.96). The unit message is now `The circle movement must be a whole number from 1 to 10.`. Where this document, or its earlier amendments, say size, circumference, 25 to 50 or `circle_size`, the radius governs; the Resize by volume factor (1 to 3) applies to the radius. See `specs/020-grouped-settings-ui/`.

No stored data is added. These are the values that exist while a job is created, and the rules between them.

## Image type

| | |
|-|-|
| Values | `tiles` (default), `blended`, `contour`, `circles` (lowercase, exact) |
| Where it lives | `IMAGE_TYPES` in `backend/app/services/image_types.py`; `IMAGE_TYPES` (value and label) in `frontend/src/utilities/validation.ts` |
| Refusal | any other value, including an empty one: `The image type must be one of tiles, blended, contour, circles.` (built from the tuple) |
| Labels on the page | Tiles, Blended tiles, Contour, Circles |

> **Amended 2026-10-14**: the place of the circle of rank r is the previous place of the rank moved by the note's step, **unless** the note index and the color index are the same as those of the last note of that rank (kept across silent frames, none before the first circle), in which case the place is not changed.

> **Amended 2026-10-14**: a fifth circle setting, `circle_resize`, a boolean (`true`, `false`, `1`, `0`, any case; default `false`; refused with `The circle resize must be true or false.`), reported as a boolean in every response; when on, a circle's radius is `size / (2 pi)` times `1 + 2 c / 255` (c the color index; 1 to 3).

## The four circle settings

| Setting | Field | Range | Default | Refusal |
|---------|-------|-------|---------|---------|
| Unit: the length of a unit in pixels (only the length of a step since the amendment of 2026-10-13) | `circle_unit` | whole number 1 to 10 | 4 | `The circle unit must be a whole number from 1 to 10.` |
| Size: the circumference of a circle in pixels (the radius is size / (2 pi)) | `circle_size` | whole number 25 to 50 | 25 | `The circle size must be a whole number from 25 to 50.` |
| Memory: how many circles are remembered | `circle_memory` | whole number 100 to 500 | 300 | `The circle memory must be a whole number from 100 to 500.` |
| Circles per frame: how many of the strongest notes put a circle down | `circle_notes` | whole number 5 to 12 | 8 | `The number of circle notes must be a whole number from 5 to 12.` |

All four are reported in every response (like `blend_width`); they only have an effect with `image_type=circles`.

## The move of a note

| Name | Definition |
|------|------------|
| `index` | the note's number among the drawn notes, 0 to 83 (0 is A1, 55 Hz) |
| `midi` | `33 + index` |
| `pc` | `midi % 12`: the note name counted from C (C = 0, C# = 1, … B = 11) |
| `octave` | `midi // 12 − 1` (scientific: A4 = 440 Hz = index 36; the drawn notes go from octave 1 to 8) |
| `angle` | `30° × pc`; `(360° − angle) mod 360°` when `octave < 4` |
| `units` | `1 + abs(octave − 4)`: 1 for octave 4, 2 for 3 and 5, … 5 for octave 8 |
| step in pixels | `dx = units × unit × cos(angle)`, `dy = −units × unit × sin(angle)` (0° right, counter-clockwise on the screen) |

Examples: F5 (index 44) is 150° and 2 units; F3 (index 20) is 210° and 2 units; A4 (index 36) is 270° and 1 unit.

## Per-job values

| Name | Definition |
|------|------------|
| `S` | the smoothed note array `(frames, 88)`; `values[t] = S[t, :84]` (unchanged smoothing) |
| `peak` | `S.max()` over all 88 notes (the tiles' scale; 0 for a silent file) |
| notes of frame `t` | the `circle_notes` notes with the largest `values[t]` (stable order: ties to the lower note), without those whose value is 0; rank 0 is the strongest |
| `place[r]` | the last place of rank `r` (pixels): the middle of the picture, `(126, 84)`, at the start, and for a rank that has had no circle |
| new place of rank `r` | `place[r] + step(note of rank r)`, taken modulo `(252, 168)` (wraps around); stored as `place[r]` |
| color | `table[rint(sqrt(min(value / peak, 1)) × 255)]` of the selected colormap (the tiles' rule); the first color when `peak` is 0 |
| memory | a circular buffer of the last `circle_memory` circles `(x, y, color)`; each frame appends its circles weakest first, so the strongest is on top and dropped last |
| the picture of frame `t` | 252 × 168 in the colormap's middle color (table row 128); every circle of the memory, oldest first, as a disc of radius `size / (2 pi)` pixels at `(x, y)`, its color with the opacity `round(255 (m - age) / m)` of 255 (age 0 for the newest circle of the frame, m the memory), blended over what is under it |

## Rules

- A frame with no note of value above 0 appends nothing and its picture is the memory as it was; a silent file gives pictures of the background color alone.
- The picture of frame `t` depends on frames `0..t` (the places and the memory), so the frames are made in order and none can be skipped: the Interpolate setting does not apply, and neither do Resolution, Notes (12 to 84), Threshold and Blend width; they are accepted and ignored.
- Smoothing and its window and the Colormap apply. The frame count, file names, size and timing are those of the other image types; the frames are 8-bit RGB PNGs.
- The tiles, blended and contour frames are unchanged.

## Response

Four changed keys: `image_type` may be `circles`; four new keys `circle_unit`, `circle_size`, `circle_memory`, `circle_notes` (the numbers used, or their defaults).
