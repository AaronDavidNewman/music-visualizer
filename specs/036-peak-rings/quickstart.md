# Quickstart: validating Peak Rings

Run from the repository root; backend commands use the project's virtual environment as for features 032 to 035.

## 1. The numbers

```bash
cd backend
python -B -m pytest tests/test_chromatic_decay_peaks.py -q
```

Expect: the distance of a frame is `1 - position`; ring 1 is the current frame and ring `k` the mean of frames `t-(2k-3)` and `t-(2k-2)` (a loop oracle, for random beats and for beats shorter than the history); frames before the start count as far from a peak; the colors are the first color of the colormap at the peak, the last far from it, in between at the same share (SC-001, SC-003); the radius is 70 pixels on 600 x 400 and the 12 rings fill it (SC-002).

## 2. The picture

```bash
python -B -m pytest tests/test_chromatic_decay_rendering.py -q
```

Expect: with a beat the middle of every frame has the target (center pixel color from the current distance, ring `k` colors from the history, 140 pixels across, 12 rings of equal width, clear of the 12 circles); with no beat the pictures are exactly what they were; the pixels of the 12 circles are the same with and without the target; deterministic.

## 3. The job end to end

```bash
python -B -m pytest tests/test_chromatic_decay_api.py -q
```

Expect: a pulsed file shows the center in the first color at a pulse and in the last between pulses, and the rings spread outward after a pulse; the Local peaks settings change them; a steady tone has every ring in the last color; the request and response have the same fields; the other image types give the same frames as before (compared byte for byte with a checkout of `HEAD`).

## 4. Everything else

```bash
python -B -m pytest -q
cd ../frontend && npx vitest run && npx vue-tsc --noEmit
```

Expect: everything passes except the Decay and Decay Exp tests broken by the `NEIGHBOURS = 6` change (reported to the user, see research Decision 7).

## 5. By eye

Choose Chromatic Decay, create frames of a file with a clear beat (`backend/audio/sonata.wav`): the middle of the ring flashes in the first color of the colormap at each beat, the flash spreads outward ring by ring over the next 22 frames, and the middle is in the last color between beats. Make a movie (feature 029).
