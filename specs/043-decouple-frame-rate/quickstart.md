# Quickstart: validating the fixed 60 ms buffers

Run from the repository root. Details of the behaviour: [spec.md](spec.md); of the request and answer: [contracts/job-api.md](contracts/job-api.md); of the values: [data-model.md](data-model.md).

## 0. Before the first edit (baselines)

```powershell
cd backend
python -m pytest -q -p no:cacheprovider 2>&1 | Select-String "^FAILED" | Out-File ..\specs\043-decouple-frame-rate\baseline-failures-before.txt
python ..\specs\041-code-readability-docs\tools\verify_frames.py --write    # only if you want a fresh baseline; the report compares by number of frames
python ..\specs\043-decouple-frame-rate\tools\verify_drawing.py --write     # hashes of the drawing from fixed note values, all image types
```

Expected: the failing test ids are the known ones (about 25 from `DEFAULT_PROMINENCE`, about 60 Decay/Decay Exp from `NEIGHBOURS`).

## 1. The buffers are the same at every frame rate (User Story 1)

```powershell
cd backend
python -m pytest tests/test_buffer_interval.py tests/test_buffers_api.py -q
```

Expected: for one generated file, `step_samples` and `window_count` are identical at frame rates 1, 10, 24, 30 and 60; the step is `sample_rate * 60 / 1000` for 8000, 11025, 22050,
44100 and 48000 Hz; the window starts are within half a sample of `k * step`; a 62.5 ms tone burst raises its notes in at least one buffer at 5 fps (SC-001 to SC-003).

## 2. Frames average the buffers they own (User Story 2)

```powershell
python -m pytest tests/test_frame_rendering.py -q
```

Expected: at 10 fps each frame is the mean of its buffers and every buffer is counted once (the sum of `stop - first` is the number of buffers); at 30 and 60 fps no frame is empty or
zero because no buffer started in it (SC-004).

## 3. The settings are gone (User Story 3)

```powershell
python -m pytest tests/test_removed_settings_api.py -q
cd ..\frontend
npm test
```

Expected: a request with `smoothing=banana`, `smoothing_window=99`, `window_spacing=-1` gives 200 and the same frames as one without them; the answer has none of the four removed keys; the
frontend tests find no spacing or smoothing control and no `data-smoothing` group, and the request body the page builds has no removed field (SC-005).

## 4. No picture type changed in how it is drawn (User Story 4)

```powershell
cd backend
python ..\specs\043-decouple-frame-rate\tools\verify_drawing.py      # compares with the baseline of step 0: must report 0 differences
python ..\specs\041-code-readability-docs\tools\verify_frames.py     # EXPECTED to report differences (the analysis step changed); every type must still make its frames
```

Expected: `verify_drawing.py` exits 0. `verify_frames.py` reports differences for every type (the default step is no longer one frame period at 30 fps) and the same number of frames per
type; this is the intended effect and is not a failure of this feature (SC-006).

Then run one job of each image type at 10, 16 and 30 fps through the page or `tests/test_frame_rate_independence_api.py`.

## 5. Constitution gates

```powershell
cd backend
python -m pytest tests/test_type_hints.py tests/test_documentation.py -q
python -m pytest -q -p no:cacheprovider 2>&1 | Select-String "^FAILED" | Out-File ..\specs\043-decouple-frame-rate\baseline-failures-after.txt
fc ..\specs\043-decouple-frame-rate\baseline-failures-before.txt ..\specs\043-decouple-frame-rate\baseline-failures-after.txt
python ..\specs\041-code-readability-docs\tools\trace_pipeline.py    # the order of operations shown has no SMOOTH step
```

Expected: both documentation tests pass; the two lists of failures are the same; `grep -ri "smoothing window\|window spacing" backend/app frontend/src` finds nothing (SC-007).

## 6. By hand

Start the app, choose a file, set the frame rate to 10, make the pictures: the page shows no Window spacing or Smoothing fields, the list of settings after the job has no smoothing or
spacing lines, and the frames play. Set it to 30 and make them again: the same `step_samples` and `window_count` are in the answer.
