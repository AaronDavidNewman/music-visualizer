# Quickstart: validating the Chromatic Decay Threshold

Run from the repository root; backend commands use the project's virtual environment.

## 1. The rule and its effect (no picture)

```bash
cd backend
python -B -m pytest tests/test_chromatic_threshold.py -q
```

Expect: a value strictly below `threshold / 100` of the largest value of the whole array is 0, one exactly at it is kept, with a threshold of 0 nothing changes; a faint note adds nothing to its letter, a letter with nothing above the floor does not count among the five loudest; `circle_points` and `circle_tapers` agree with a loop oracle for random values and every threshold from 0 to 10; a threshold of 0 gives exactly the earlier results (SC-001, SC-002, SC-003).

## 2. The job

```bash
python -B -m pytest tests/test_chromatic_decay_api.py -q
```

Expect: `threshold=5` changes the frames of a file with a loud and a faint note (the faint letter's circle stays smallest); no `threshold` or `0` gives the earlier frames; `11`, `-1`, `x` are refused with the existing message and nothing is left behind; the response echoes the value (SC-003, SC-004).

## 3. Everything else

```bash
python -B -m pytest -q
cd ../frontend && npx vitest run && npx vue-tsc --noEmit
```

Expect: all pass except, while `decay.NEIGHBOURS` is 6 on disk, the 60 Decay and Decay Exp tests that assume 8 (not this feature's).

## 4. By eye

Choose Chromatic Decay: the group shows Decay rate and Threshold; make frames of `backend/audio/sonata.wav` with the threshold off and at 10: with 10 only the clearly loudest letters light the ring.
