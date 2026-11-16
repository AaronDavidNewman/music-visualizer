# Quickstart: validating Polychord

Run from the repository root; the backend uses `backend/.venv`.

## 1. Automated checks

```text
cd backend
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_polychord.py tests/test_polychord_rendering.py tests/test_polychord_api.py
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_documentation.py tests/test_type_hints.py
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider          # whole suite
cd ..\frontend
npm run test                                                          # vitest
```

Expected: the new tests pass; the whole backend suite fails only in the **25 tests of
`specs/041-code-readability-docs/tools/baseline-failures.txt`** (the user's `DEFAULT_PROMINENCE = 15`); the documentation
and type-hint tests pass (every new function typed, every new array aliased, `Order of operations:` in the module, the
Polychord block in `image_types.py`).

## 2. The other types did not change

```text
backend\.venv\Scripts\python.exe specs\041-code-readability-docs\tools\verify_frames.py
```

Expected: `all frames identical to the baseline` (the 540 frames of the eight existing types).

## 3. The picture, by eye

1. Start the application as usual and open the page; choose the image type **Polychord**. Its four settings (Number of
   notes 6, Copies minimum 3, Copies maximum 12, Rotation 15) appear with the Local peaks group; the settings of the other
   types (Threshold, Decay rate, Note layout, ...) are hidden.
2. Upload `sonata.wav` (about 116 bpm) and make the frames. Look at the pictures: a rosette on black that turns slowly
   (15 degrees a second), whose links are thick at the center and thin at the tips, and which has **more arms at the top of
   each beat and fewer between beats**; every link of a picture has one color, which stays near the same part of the
   colormap while the tempo is steady.
3. Upload `almost2.wav` (about 180 bpm, felt as 90): its color is nearer the end of the colormap than sonata's.
4. Set Rotation to 0: the picture no longer turns; set it to -15: it turns the other way. Set Number of notes to 5 and to 8:
   the figures have fewer or more links. Set Copies minimum 12 and maximum 12: every picture has 12 arms.
5. Send Number of notes 9 (with a script or the browser tools): a message appears and nothing is created. Make a movie from
   the frames (feature 029): it plays.

## 4. A turn, by hand

A file in which C, G, D sound in that order of loudness gives a first link along the starting angle, a second turned 30
degrees clockwise from it and a third 30 degrees further; C then F# gives a second link that goes back along the first.
`test_polychord.py` has this for all twelve intervals.
