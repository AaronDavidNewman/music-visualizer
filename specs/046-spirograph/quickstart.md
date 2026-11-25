# Quickstart: validating Spirograph

How to check that the feature works end to end. Run everything from the repository root (`d:\github\music-visualizer`); the
backend interpreter is `backend/.venv/Scripts/python.exe`. Details of the request, response and picture are in
[contracts/spirograph.md](contracts/spirograph.md) and [data-model.md](data-model.md); nothing is repeated here.

## Prerequisites

- The backend virtual environment and the frontend `node_modules` are installed (as for every earlier feature).
- A baseline of the failing tests exists: `specs/045-obj-export-mode/baseline-failures-after.txt` (32 ids). "No regression" means
  those ids fail and no others.

## Scenario 1 - the curve and the colors (no audio needed)

```text
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_spirograph.py -p no:cacheprovider
```

Expected: the curve equals the formula to a millionth for values 0 to 1 and indices 0 to 83; the 13 reduced colors are the
colormap's rows at `sqrt(k / 12) x 256`; the color number of `m / 12` is `m`; the extent is exactly the first point's distance;
a value 0 draws nothing.

## Scenario 2 - the history (no audio needed)

Same test file: with `n` notes and history `h`, a picture well into the file holds `n x h` curves; frame `t < h - 1` holds the
rows `0..t`; two consecutive windows share all but one row; the value and index of a step come from the same row; the oldest
row is drawn first.

## Scenario 3 - the pictures

```text
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_spirograph_rendering.py -p no:cacheprovider
```

Expected: a silent file gives black pictures; the background is black; a one-note file gives curves in the color of that
note's value; the picture of frame `t` differs from the picture of frame `t + 1` only by one entry; two runs and one thread
against several give identical files; no pixel of a curve lies outside the picture at 600 x 400 and at a small size; the largest
settings (12 notes, history 12) take under 2 seconds a picture; 300 frames at the defaults finish.

## Scenario 4 - the job through the API

```text
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_spirograph_api.py -p no:cacheprovider
```

Expected: `image_type=spirograph` with and without the two fields gives 200, the response has `spirograph_notes` 8 and
`spirograph_history` 8 (or the values sent); each field at 4, 5, 12 and 13, at `7.5`, `abc`, empty, `nan` and `inf` is accepted
or refused as the contract says, with the message, before the file is read and with no files left; Extra notes 8 is accepted for
12 notes and refused (`1 to 5`) for 5 notes; no local-peaks measurement is made; the frames can be served and made into a movie.

## Scenario 5 - the other types are unchanged

```text
backend/.venv/Scripts/python.exe specs/045-obj-export-mode/tools/verify_drawing.py
backend/.venv/Scripts/python.exe -m pytest backend -p no:cacheprovider -q
```

Expected: `all frames identical to the baseline`, and the full run's failing ids are exactly those of the baseline (the new tests
all pass; the five exact-key API tests and the type lists have been updated, not weakened).

## Scenario 6 - the page

```text
cd frontend
npm test -- --run
npm run typecheck
```

Expected: all tests pass and the typecheck is clean. By hand (optional): choose Spirograph on the page; the group shows two
sliders with 8 and 8, the Held notes slider ends at 8; the Local peaks group with Minimum distance after Held notes; a value outside 5 to 12 shows the message and
disables the button; run a short file and look at the frames: closed looped curves, black background, the picture flowing from
frame to frame.
