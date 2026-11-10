# Contract: Chromatic Decay

Three interfaces: the library functions, the HTTP request and the picture.

## 1. Library (backend/app/services)

### `chromatic_decay` (new module)

```python
LETTERS = 12
MIN_RATE, MAX_RATE, DEFAULT_RATE = 1, 10, 1
RATE_MESSAGE = "The decay rate must be a whole number from 1 to 10."

def check_chromatic_rate(value) -> int
    # a whole number 1..10 (a real such as 3.0 is accepted); ValueError(RATE_MESSAGE) for anything else.

def ring_position(letter: int) -> int       # 7 * (letter - 3) % 12
def letter_at(position: int) -> int         # (3 + 7 * position) % 12   (inverse of the above)
def receivers(letter: int) -> tuple[int, int]   # ((letter + 5) % 12, (letter + 7) % 12)

def letter_energies(values) -> np.ndarray
    # (frames, >=84) -> (frames, 12): the largest of the 7 octaves of each letter. ValueError as concentric._check_values.

def letter_gains(values, beat=None, taper=TAPER) -> np.ndarray
    # (frames, 12): the five loudest letters gain 24,20,16,12,8 (+8*position) times exp(-g/taper); ties to the lower letter.

def chromatic_step(points, frames=1) -> np.ndarray
    # (12,) -> (12,): one decay step of `frames` frames' worth, each circle giving min(p, 8*frames*loss(p)), one eighth to each receiver and six eighths lost.

def circle_points(values, beat=None, decay_rate=1) -> np.ndarray
    # (frames, 12) points after every frame, letter order.

def circle_tapers(values, beat=None, decay_rate=1) -> np.ndarray
    # (frames,) the taper of every frame (8 for the first).

def write_chromatic_frames(points, colormap, directory, width, height) -> None
    # one PNG per row of `points` (frames, 12), frame_000000.png and up, RGB; everything is checked before anything is written.
```

(Revised 2026-11-10: `8` and "eighth" in `chromatic_step` mean `chromatic_decay.PRETEND_NEIGHBORS`, the module's own constant, 6.)

### `frame_rendering.write_frames`

For `image_type == "chromatic-decay"`: `decay_rate` is checked with `check_chromatic_rate` (for every other type with `check_decay_rate`, unchanged), the points are `chromatic_decay.circle_points(smoothed, beat, decay_rate)` and the frames are written by `write_chromatic_frames`; the other settings are checked as before and ignored (`note_layout`, `decay_amounts`, ...). `beat` is used like Decay Exp's.

### `image_types`

`IMAGE_TYPES` ends with `"chromatic-decay"` (after `"energy-graphs"`); the message of `check_image_type` lists it.

## 2. HTTP

`POST /api/jobs` (existing). `image_type=chromatic-decay` is accepted. **No new request field and no new response field.**

- `decay_rate` is validated **for the image type** before the file is read: for `chromatic-decay` a whole number from 1 to 10 (default 1 when not sent), refused otherwise with 400 `The decay rate must be a whole number from 1 to 10.`; for every other type as before (0.25 to 4 in steps of 0.25, message unchanged). Nothing is left behind on a refusal.
- The response echoes `image_type: "chromatic-decay"` and `decay_rate` (an integer for this type).
- The beat is measured for this type (as for `decay-exp`); the Local peaks settings are validated as always.
- A bad image type is refused with 400 `The image type must be one of tiles, blended, contour, circles, circles_paint, concentric, decay, decay-exp, polar-chords, energy-graphs, chromatic-decay.`
- The Note layout, the four decay amounts and every grid setting are validated as always and ignored.

`GET /api/jobs/{id}/frames/{index}` and the movie export (feature 029) work as for every type.

## 3. The picture (600 x 400, RGB)

Background: the middle color of the colormap. 12 circles on a ring centered at (300, 200):

| Element | Value |
|---------|-------|
| Ring radius `R` | `(200 - 10) / (1 + sin 15°)` = 150.94 px |
| Full radius `full` | `R sin 15°` = 39.06 px: two neighbouring full circles just touch |
| Center of position `k` | `(300 + R sin(30k°), 200 - R cos(30k°))`, `k = 0` at the top, clockwise |
| Letter at position `k` | `(3 + 7k) mod 12`: C, G, D, A, E, B, F#, C#, G#, D#, A#, F |
| Radius of a circle of `p` points | `full x (1/12 + 11/12 x min(p, 24)/24)` |
| Color / rings | those of `decay.ring_colors(p)`: first color at 0 points, last at 32, twelve rings from 32 to 64, each `full / 12` wide |
| Edges | smooth: coverage `clip(radius - distance + 0.5, 0, 1)` |

A circle with 0 points is the smallest circle (`full / 12`, in the first color), as in Decay. Frames are identical for identical input. Other frame sizes scale the ring by `min(w, h)`.
