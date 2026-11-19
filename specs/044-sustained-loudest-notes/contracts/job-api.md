# Contract: `POST /api/jobs` - the Extra notes (k) setting

Only what this feature changes is listed; every other field of the request and of the answer is as it is today (after feature 043).

## Request (multipart form)

| Field | Before | After |
|---|---|---|
| `extra_notes` | - | **new**, optional. Not sent: 2. Sent: a whole number from 1 to 8; for the six pictures that take the n loudest notes also at most n |

Which picture has which n:

| `image_type` | n | Range of `extra_notes` |
|---|---|---|
| `decay`, `decay-exp`, `chromatic-decay`, `chromatic-wireframe` | 5 | 1 to 5 |
| `polar-chords` | `polar_notes` (5 to 8, default 5) | 1 to that number |
| `polychord` | `polychord_notes` (5 to 8, default 6) | 1 to that number |
| `contour`, `energy-graphs`, `rhythm-circles` | none | 1 to 8, accepted and ignored |

## Errors (400, before the file is read)

| Cause | Message |
|---|---|
| not a whole number from 1 to 8 (empty, text, fractional, `nan`, `inf`, 0, 9, ...) for any picture | `The extra notes must be a whole number from 1 to 8.` |
| above n for a picture that uses it | `The extra notes must be a whole number from 1 to {n}.` (n of that picture) |

The check against n uses the `polar_notes` and `polychord_notes` of the same request. A request that is refused makes no file and leaves nothing behind.

## What the job does with it

The six pictures choose the notes (letters) they count in each frame with the held-notes rule of [data-model.md](data-model.md) with `k = extra_notes`; the other three ignore it. Nothing else in the
analysis changes (the buffers are still 60 ms apart; the frames are still the averages of the buffers).

## Answer (200, JSON)

| Key | Before | After |
|---|---|---|
| `extra_notes` | - | **new**: the number used (2 when not sent), for every picture |
| every other key | | unchanged |

## Page contract (frontend)

- A group with the id `held-notes` and the title *Held notes* with one control, `extra-notes` (label *Extra notes (k)*, a slider from 1 to n, step 1, default 2, with an info button), is shown for
  Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe and Polychord, after the group of the type and before the Note layout / Local peaks group; it is not shown for Contour, Energy
  graphs or Rhythm Circles.
- n follows the picture: 5, or the current Notes shown (Polar Chords) or Number of notes (Polychord). A k above the current n shows `The extra notes must be a whole number from 1 to {n}.` under the
  control and the form cannot be submitted; the group is flagged "needs attention" like the others.
- The settings object sent by the page has `extraNotes` and the body `extra_notes`, for every picture (so it is always in the request; the three other pictures ignore it).
- The result list of a finished job shows *Extra notes (k): {value}* for the six pictures and no such line for the others.
