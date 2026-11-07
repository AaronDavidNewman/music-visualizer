# Quickstart: Polar Chords

Validation scenarios that prove the feature works end to end. Contracts: [polar-chords.md](contracts/polar-chords.md); rules: [data-model.md](data-model.md).

## Prerequisites

- Backend: `cd backend`, the `.venv` active, `pip install -r requirements.txt` (nothing new).
- Frontend: `cd frontend`, `npm install` (nothing new).

## Automated checks

```text
cd backend  && python -m pytest
cd frontend && npm test
cd frontend && npm run build   # type check
```

Expected: all green, including `test_polar_chords.py`, `test_polar_chords_rendering.py`, `test_polar_chords_api.py` and the reference-hash tests of the other eight image types.

## Scenario 1: The notes (User Story 1)

1. Start the backend (`uvicorn app.main:app`) and the frontend (`npm run dev`).
2. Upload a file with a steady note and a clear pulse; choose **Polar Chords**, Notes shown 5, Create frames.
3. Expected: one bar at the angle of the note (clockwise from the top, low notes near the top-right, high notes coming round to the top-left), 4.3° wide, whose tip goes in and out between half the radius and the full radius with the pulse, in a color from the first half of the colormap (use Cool Warm to see it: blue).

## Scenario 1b: The bars follow their notes (User Story 1)

1. Use a file with a note that jumps: note 36 for a second and a half, then note 48 (twelve arcs away, an octave up). Create frames at 30 frames a second.
2. Expected: the bar is in the arc of note 36 until the change, then it **moves one arc a frame**, 37, 38, ... 48, and stays there; it never jumps. It takes twelve frames (0.4 seconds). Its color is that of the new note from the first frame of the change.
3. With a pitch jump of more than half the circle the bar goes round the top the shorter way. With a quick passage of different notes the bars are still on their way when the notes change again: that is the smoothing.

## Scenario 2: The chord (User Story 2)

1. Use a file in which a C major triad (C, E, G) sounds for a while.
2. Expected: three note bars (C, E, G at their angles, blue with Cool Warm) and one more, much wider bar in the second half of the colormap (red with Cool Warm) in the chord place 22 (C is the letter 3 from A, `3 × 7 + 1`), 94.3° to 98.6° counterclockwise from the top (type `(4, 7)` on C), the same length as the note bars. An E-G-C voicing gives the same chord bar; the same triad on another root is another place (E major: 50). Two notes a fourth apart (C and F) give the bar of `(7)` on F, place 56 (240.0° to 244.3°).
3. A frame where the loudest notes form none of the seven types has only note bars.

## Scenario 3: The page and the API (User Story 3)

1. On the page choose Polar Chords: the groups are Analysis, Colormap, Image type, Polar chords (Notes shown, 5 to 8), Note layout (Rows or Spiral), Local peaks (no checkbox) and Data smoothing; Image smoothing is not there.
2. `curl -F image_type=polar-chords -F polar_notes=7 -F file=@song.wav http://localhost:8000/api/jobs` returns `"image_type": "polar-chords", "polar_notes": 7`.
3. `-F polar_notes=4`, `-F polar_notes=9` and `-F polar_notes=6.5` return 400 `The number of notes shown must be a whole number from 5 to 8.`; `-F image_type=polar_chords` returns 400 with the list of nine names.
4. The result summary lists Notes shown, Note layout, Minimum distance and Prominence.

## Scenario 4: Quiet moments (User Story 4)

1. A silent file: frames of the background only, without errors.
2. A few seconds of a steady tone with no beat (prominence 100 finds no peak): one bar at half the radius in every frame.
3. A tone and a silence: the bar is there while the tone sounds and gone in the silence.

## Scenario 4b: The note layout (User Story 1)

1. Use a file with a steady middle C (note 27) and choose Polar Chords with Note layout **Rows**: the bar is in arc 27, 27 × 4.29° = 115.7° clockwise from the top. Choose **Spiral**: the bar moves to arc 29 (124.3°).
2. With a chord (C, E, G) the chord bar stays in the chord place 22 (94.3° to 98.6° counterclockwise from the top) in both layouts; only the three note bars change places.
3. `curl -F image_type=polar-chords -F note_layout=spiral ...` returns `"note_layout": "spiral"`; `-F note_layout=Spiral` returns 400 `The note layout must be one of rows, spiral.`

## Scenario 5: Nothing else changed

Create frames with each of the other eight image types for the reference file: they match the hashes of the earlier features.

## Scenario 6: Speed (SC-006)

Create the frames of a 60 second file at 30 frames a second with Polar Chords: under 30 seconds.
