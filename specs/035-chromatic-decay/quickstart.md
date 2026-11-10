# Quickstart: validating Chromatic Decay

Run from the repository root. Backend commands use the project's virtual environment as for features 032 to 034.

## 1. The numbers (no picture)

```bash
cd backend
python -B -m pytest tests/test_chromatic_decay.py -q
```

Expect: the energy of a letter is the largest of its octaves (not the sum); the five loudest letters gain the amounts of Decay Exp (ties to the lower letter, silent letters not counting); after one decay step from one circle with points exactly three circles have points, the two receivers equal, for each of the 12 letters (SC-002); the total of the points is kept by a step (except the 64 cap); points that are not fed decay to 0 (SC-003); with a rate `r` a step falls at frames `r, 2r, ...` and moves `r` frames' worth; a single note gives the same gain as in Decay Exp whatever its octave (SC-001); `check_chromatic_rate` accepts 1 to 10 and refuses everything else.

## 2. The picture

```bash
python -B -m pytest tests/test_chromatic_decay_rendering.py -q
```

Expect: 600 x 400 RGB frames; the background is the colormap's middle color; the 12 circles are at the ring positions (C at the top, G, D, A ... clockwise), neighbouring full circles touch, and a circle's size, color and rings follow its points like Decay's; identical bytes for identical input.

## 3. The job end to end

```bash
python -B -m pytest tests/test_chromatic_decay_api.py -q
```

Expect: `image_type=chromatic-decay` gives 200 with the frame count of the other types, no new field in the response; `decay_rate` 1 to 10 whole numbers are accepted and 0, 11, 2.5, empty, text are refused with `The decay rate must be a whole number from 1 to 10.` and nothing left behind, while the other types still refuse 5; the settings that do not apply change nothing in the frames; the nine older types and Energy Graphs give the same frames as before (compared byte for byte with a checkout of `HEAD`).

## 4. Nothing else changed

```bash
python -B -m pytest -q
cd ../frontend && npx vitest run && npx vue-tsc --noEmit
```

Expect: all existing tests pass (the lists of image types in older tests were extended) and the type check is clean.

## 5. By eye, with a real file

Start the service and the page as usual, choose **Chromatic Decay**: the page shows Decay rate (1 to 10, whole numbers), Local peaks and Data smoothing, and no Note layout. Create frames from `backend/audio/sonata.wav` and play them: twelve circles on a ring flare with the loudest letters and the glow spreads to the circles next to them on the ring, and back. Try rates 1 and 10 and a file with one steady tone (the circle of its letter grows and its two neighbours light up). Then make a movie (feature 029).
