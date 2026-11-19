# Quickstart: validating the held notes

Run from the repository root; backend commands use the project's virtual environment (`backend\.venv\Scripts\python.exe`). Details: [spec.md](spec.md), [contracts/job-api.md](contracts/job-api.md),
[data-model.md](data-model.md).

## 0. Before the first edit (baselines)

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -rf 2>&1 | Select-String "^FAILED"   # the known 32 failures; save the ids
.venv\Scripts\python.exe ..\specs\043-decouple-frame-rate\tools\verify_drawing.py               # must say: all frames identical to the baseline
cd ..\frontend; npm test; npm run typecheck                                                      # 876 tests, clean
```

Expected: 32 failing test ids (the `DEFAULT_PROMINENCE` and `NEIGHBOURS` ones), the drawing identical, the frontend green. Do not fix the failures.

## 1. The rule (User Stories 1 and 2)

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests/test_held_notes.py -q
```

Expected: `hold_loudest` agrees with the independent reference (`specs\044-sustained-loudest-notes\tools\reference_selection.py`) on random data for n = 5 to 8 and every k from 0 to n, with ties, zeros and
fewer than n notes sounding; with k = 0 it equals the old `np.argsort(-values, axis=1, kind="stable")[:, :n]`; the scenarios of the spec (a louder newcomer does not displace a held note; a note below
n + k frees its place for the loudest note that is not held; rank n + k is still held and n + k + 1 is not; a note that stops is never held; a note that returns is a newcomer) pass (SC-001 to SC-004).

## 2. The six pictures (User Story 4)

```powershell
.venv\Scripts\python.exe -m pytest tests/test_held_notes_pictures.py -q
.venv\Scripts\python.exe ..\specs\043-decouple-frame-rate\tools\verify_drawing.py
```

Expected: for Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe and Polychord a held, fading note is still drawn after a louder note starts (its circle gains points, its bar stays, its
letter charges, its link stays) with `extra` above 0 and is replaced with `extra = 0`; a steady chord gives the same pictures with and without it (SC-005). `verify_drawing.py` reports all nine types
identical to the baseline: with the library default `extra = 0` nothing moved.

## 3. The setting (User Story 3)

```powershell
.venv\Scripts\python.exe -m pytest tests/test_extra_notes_api.py -q
cd ..\frontend; npm test; npm run typecheck
```

Expected: no `extra_notes` means 2 and the answer says so; 1 and n are accepted; 0, n + 1, 9, empty, text and 2.5 are refused with the messages of the contract and the file is not read; the other three
pictures accept 1 to 8 and ignore it; the page shows the *Held notes* group for exactly the six pictures and the slider's maximum follows Notes shown / Number of notes (SC-006, SC-007).

## 4. Constitution gates

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests/test_type_hints.py tests/test_documentation.py -q
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -rf 2>&1 | Select-String "^FAILED"   # compare by id with step 0: the same 32
.venv\Scripts\python.exe ..\specs\041-code-readability-docs\tools\trace_pipeline.py            # the held-notes step comes before the gains / targets / letters of the six pictures
.venv\Scripts\python.exe ..\specs\041-code-readability-docs\tools\shape_probe.py                # LoudestIndices (frames, count)
```

Expected: both documentation tests pass; the failing ids are the same 32; `grep -rn "held" backend/app/services/array_types.py` finds the new alias (SC-008).

## 5. By hand

Start the app, choose a piano-like file, choose Decay and make pictures with Extra notes at 1 and at 5: with 5 the circles of notes that are still ringing keep gaining points after a louder note
starts; with 1 they are replaced sooner. Choose Contour: the group is not there.
