# Quickstart: validating Chromatic Wireframe

Run from the repository root; backend commands use the project's virtual environment.

## 1. The numbers (hand-made points, no audio)

```bash
cd backend
python -B -m pytest tests/test_chromatic_wireframe.py -q
```

Expect: the sum of the waves `S` equals a scalar loop of `1 / 12 x` the sum over the letters of `(r / full) x sin(2pi (p / 16) u / span + 2pi start / span)` squared, and the height is `A x clip((S - 0.05) / (0.8 - 0.05), 0, 1)` with `A` two fifths of the height (never negative, never above `A`); a letter's frequency is `p / 16` turns of the angle across the width (4 at 64 points, none at 0) and its phase that of its start (pi/2 a quarter of the way along); the line is one continuous function with no jump at the start of a letter; twelve letters with the same points, and a silent frame, make a flat line; one steady letter still makes a moving line; `line_geometry(600, 400)` gives `(66, 390.0, 4.0)`: the base on the bottom margin and as many lines, 4 px apart, as fill the picture to the top margin; `line_colors`: a frame at the top of a peak has the last colormap row, the lowest point the first, `None` the first.

## 2. The picture

```bash
python -B -m pytest tests/test_chromatic_wireframe_rendering.py -q
```

Expect: the front line near the bottom and one line for each earlier frame (a first frame has one line), each line one color, a nearer line hiding the ones behind, picture `t` the same as picture `t - 1` with every line one place further back plus the new front line, no non-background pixel outside the margins, identical bytes for identical input.

## 3. The job

```bash
python -B -m pytest tests/test_chromatic_wireframe_api.py -q
```

Expect: the points drawn are `circle_points` of the same file and settings (the same as Chromatic Decay's), a decay rate of 2.5, 0 or 11 refused before the file is read, the Note layout and the decay amounts ignored, no new field, the other twelve types unchanged byte for byte.

## 4. Everything else

```bash
python -B -m pytest -q
cd ../frontend && npx vitest run && npx vue-tsc --noEmit
```

(The failing Decay and Decay Exp tests noted for `decay.NEIGHBOURS` in feature 036 are not part of this feature.)

## 5. By eye

Choose Chromatic Wireframe with a file with a clear beat (`backend/audio/sonata.wav`): a ridge plot with the newest line at the front, older lines going back and up and getting smaller, colors banding with the beat (a repeating beat shows as repeating bands of color going back), the loud letters' bands taller. Make a movie (feature 029).
