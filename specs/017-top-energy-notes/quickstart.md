# Quickstart: Top-Energy Notes

Validation guide for [spec.md](spec.md). The values are in [data-model.md](data-model.md) and the interface in [contracts/note-count-api.md](contracts/note-count-api.md).

## Prerequisites

`pip install -r requirements-dev.txt` in `backend/` with the venv active and `npm install` in `frontend/`.

## 1. Automated checks

```
cd backend
pytest -v

cd ..\frontend
npm test
npm run typecheck
npm run build
```

Expected: everything passes. The new coverage includes: the choice of notes against an independent ranking (ties to the lower note, the same notes in every frame); the spread equal to `np.interp` with its invariants (identity at 84, first and last kept, range); a non-chosen note changing no pixel; the pictures of the three image types from the spread values, also with the Resolution setting; the `note_count` field, its refusals and the response; the control, readout and help on the page. The tests use whatever colormap list `colormaps.py` has and never state a number of contour levels.

## 2. The original output is unchanged (84 notes)

Create frames of the 4-second test file with no `note_count` and with `note_count=84`, once for each of tiles, blended and contour. The default tiles output hashes to `28e608864383e33d2b3a195e962d2fd0c02005cd64137fcf4c45ad7e7375d780`, blended (width 15) to `187ac9894949dfe4f12435e3da983262d02109dd889876c6e786728059682db0`, the contour default to `fbf26807c2045329bff9bfb41bdfb7a4bef9aa1aaddfc1be60a6f85f931aba04`, and the job with colormap `viridis`, smoothing 0.4, window 3 and threshold 3 to `ae8869d0af777836941edf3998474bef0a19b7e254f60499b5f5722a65c2c3ce` (`baseline.py` in the session's scratchpad). The Resolution setting (feature 016) also stays at 1 for these.

## 3. A picture from the strongest notes

```
curl -F file=@tones.wav -F window_size=4096 -F frame_rate=30 -F note_count=24 http://127.0.0.1:8000/api/jobs
```

Expected: 200 with `"note_count": 24`; the frames show features that are larger than at 84 notes, made from the 24 notes with the most energy in the file (the faint notes no longer appear), and the same notes in every frame. Repeat with `image_type=blended`, `image_type=contour` and `resolution=3`.

Refusals: `note_count=11`, `85`, `36.5`, `abc` and an empty value each return 400 with `The number of notes must be a whole number from 12 to 84.`.

## 4. With the other settings

Create frames with 24 notes, smoothing 0.5, window 3, resolution 3, threshold 5 and each colormap on the page, for each image type: the colors use the colormap with the same scale as at 84 notes, the hidden region follows the Threshold, and a silent file is as flat as at 84 notes.

## 5. Time

A 10-second file at 30 frames per second (300 frames) at resolution 5 and any number of notes finishes well within one minute for every image type (the choice and the spread cost a few hundredths of a second).

## 6. The page

Open the frontend: the Notes slider is at 84 ("All 84 notes"). Move it to 24: the readout shows "24 of 84 notes". Open the info button: the text explains the choice. Create frames: the player shows the picture made from the strongest notes and the summary says "Notes: 24 of 84". The slider is disabled while the job runs.

## 7. Look at it

The spec's steadiness hope (fewer notes, a steadier picture) holds only in some cases (see research.md). Compare consecutive frames of a file you know, at 84, 48, 24 and 12 notes, and judge the look: the implementation sends such a strip for the test file. Not covered by automated tests: step 6 in a real browser, and whether the pictures look good, which is for the user.
