# Quickstart: validating Rhythm Circles

Run from the repository root; backend commands use the project's virtual environment.

## 1. The numbers (hand-made peaks, no audio)

```bash
cd backend
python -B -m pytest tests/test_rhythm_circles.py -q
```

Expect: for peaks every 0.5 s (120 beats per minute) the tempo and the three aggregated tempos are 120 and the four changes 0; for a tempo that goes from 120 to 126 between two peaks 0.5 s apart the rate of change is `6 / 0.5 = 12` in all four layers (the new tempo is the fastest of any window and is 0 away from itself); for a tempo that then falls (120, 120, 110, 100) the aggregate of 2 is 120, 120, 115, 105 (the average of 115 is nearer to 110 than the fastest 120) and those of 4 and 8 are 120, 120, 116.67, 112.5; for the tempos 100, 100, 200, 190 the aggregate of 2 at the last peak is the average 195 and those of 4 and 8 are the fastest 200; the aggregates use the peaks there are; the columns run from the aggregate of 8 (outer) to the tempo's rate of change (innermost); the angles are continuous across a peak and the tempo circle advances 720 degrees a second at 120 beats per minute (SC-001 to SC-003).

## 2. The picture

```bash
python -B -m pytest tests/test_rhythm_circles_rendering.py -q
```

Expect: eight rings of equal width centered in the picture, each ring its colormap color with a 45 degree notch in the color at the opposite end, the notch at the angle of the data and moving between frames; identical bytes for identical input.

## 3. The job

```bash
python -B -m pytest tests/test_rhythm_circles_api.py -q
```

Expect: a click track at a known tempo makes the notch of the outer circle turn at that tempo (read from the frames), the Minimum distance and Prominence change the result, the settings that do not apply change nothing, no new field, the other types unchanged (SC-004).

## 4. Everything else

```bash
python -B -m pytest -q
cd ../frontend && npx vitest run && npx vue-tsc --noEmit
```

## 5. By eye

Choose Rhythm Circles with a file with a clear beat (`backend/audio/sonata.wav`) and a click track: eight rings with notches; the outer rings hold on to the beat of the last 8 peaks and the inner ones follow the tempo, and the four rate rings swing slowly both ways. Make a movie (feature 029).
