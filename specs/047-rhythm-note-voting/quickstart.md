# Quickstart: validating the Rhythm Circles voting

Feature 047. Run from `d:\github\music-visualizer`. See [contracts/rhythm-voting.md](contracts/rhythm-voting.md) and [data-model.md](data-model.md).

## 1. The voting alone (no audio)

```text
cd backend
.venv/Scripts/python.exe -m pytest tests/test_tempo_votes.py -q -p no:cacheprovider
```

Expected: the 18 tempos; starts exactly 0.5 s apart (resolution 0) vote for 80, 88, 92 and 120 (120, a quarter note, gets 2 votes a cycle: 2 after the first, `k + 1` after `k`, 20 after 19 cycles, then 20; 80, 88 and 92 fit only as a triplet or a dotted note and stay at 1);
a change of spacing takes one vote a cycle from tempos that no longer fit and never below 0; ties go to the lower tempo; a place without votes is 120; the starts of a synthetic
sound (a sustained note is one start, a chord one start, a note that drops out and returns a new start).

## 2. The circles and the pictures

```text
.venv/Scripts/python.exe -m pytest tests/test_rhythm_circles.py tests/test_rhythm_circles_rendering.py tests/test_rhythm_circles_api.py -q -p no:cacheprovider
```

Expected: six rings in the stated order, the vote rings turning at the voted tempos and their rates, the peak rings unchanged, `vote_limit` accepted/refused/echoed, Extra notes 1..5.

## 3. The two sample files (reported, not gated)

```text
.venv/Scripts/python.exe ../specs/047-rhythm-note-voting/tools/verify_votes.py
```

Prints, for `sonata.wav` and `almost2.wav`: starts, the share of time after 10 s that the first or second tempo is within 10% of 116 / of 90, the changes of the first tempo and
whether two runs agree.

## 4. Nothing else moved

```text
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider 2>&1 | tail -3     # compare the failing ids with baseline-failures-before.txt (32 known failures)
cd ../frontend; npx vue-tsc --noEmit; npx vitest run
```

Expected: the same 32 failing backend ids and no others; `vue-tsc` clean; the frontend tests pass. The frames of the other image types match a baseline made before the work
(`specs/041-code-readability-docs/tools/verify_frames.py`).

## 5. By eye (the page)

Choose Rhythm Circles: the groups are Analysis, Colormap, Image type, Rhythm Circles (Vote limit), Held notes, Local peaks. Make a render of `sonata.wav`: six rings; lower the Vote
limit to 5 and see the outer tempo ring change speed more often.
