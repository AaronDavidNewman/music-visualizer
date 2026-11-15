# Quickstart: checking the Local Tempo Finder

Run from the repository root; the backend commands use `backend/.venv/Scripts/python.exe` with `-B`.

## 1. The rule on peak times alone (no audio)

```text
cd backend
.venv/Scripts/python.exe -B -m pytest tests/test_tempo_finder.py -q
```

Expected: all pass. The tests cover the start (120), steady peaks at 100 and 116 (settle on themselves, also with every second peak), a steady 70 (settles at 105: two thirds), a steady 150 (settles at 150, not at 100), a stray peak (moves the tempo by less than 10%), the restarts at 156 and 60 (tempo becomes 78 or 120, the samples are thrown away) and a tempo that is never outside 60 to 156.

## 2. The two sample files (measured and reported)

```text
.venv/Scripts/python.exe -B -m pytest tests/test_tempo_files.py -q -s
```

Expected: passes, and prints for `sonata.wav` and `almost2.wav` the number of peaks, the restarts, the share of time (after 10 s) near 116 and near 90, and the tempo every 10 seconds. With the faster tempos and the 15 percent tolerance the measurement is about 49% and 4 restarts (sonata) and 35% and 0 restarts (almost2) (27% / 2 and 49% / 1 before the tolerance); the rule with only the tempo, its half and its two thirds gave 22% and 40 restarts and 7% and 22 restarts; see [research.md](research.md) D2.

## 3. Rhythm Circles by eye

1. Start the backend and the frontend as usual and open the page.
2. Choose `sonata.wav` and the image type **Rhythm Circles**. The Local peaks group shows **Minimum distance** at 350 ms and **no Prominence**.
3. Make the animation. From the outer circle to the inner one the four rings are: the current tempo, its rate of change, the local peak and its rate of change. At the start the tempo ring turns at 120 revolutions per minute and the peak ring at 60.

## 4. Nothing else moved

```text
.venv/Scripts/python.exe -B -m pytest -q
cd ../frontend
npx vitest run
npx vue-tsc --noEmit
```

Expected: everything passes (the tests that sent or checked a prominence were changed with the feature).
