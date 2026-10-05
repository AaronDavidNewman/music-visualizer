# Quickstart: Musical Note Bin Analysis

Validation guide for [spec.md](spec.md). Contract details are in [contracts/note_analysis_api.md](contracts/note_analysis_api.md).

## Prerequisites

```
cd backend
.venv\Scripts\activate
pip install -r requirements-dev.txt     # now includes numpy and scipy
```

## 1. Run the automated tests

```
cd backend
pytest tests/test_note_analysis.py -v
```

Expected: all tests pass. They cover the note table, the position formula, tone detection, channel averaging, silence, padding, mono input, and the error cases.

## 2. Analyze one synthetic window

```
cd backend
python -c "import numpy as np; from app.services.note_analysis import NoteBinAnalyzer; a = NoteBinAnalyzer(44100, 2048); t = np.arange(2048)/44100; x = np.sin(2*np.pi*440*t); r = a.analyze(x, x); print(r.shape, r.argmax(), a.frequencies[r.argmax()])"
```

Expected: shape `(88,)`, and the peak note frequency is close to 440 Hz (the note whose position covers 440 Hz).

## 3. Analyze the sample WAV file

```
cd backend
python -c "from app.services.note_analysis import analyze_wav; r = analyze_wav('audio/fotr-intro1-echo.wav', 44100, 2048); print(r.frames.shape, r.window_start_times()[-1])"
```

Expected: shape `(window_count, 88)` where `window_count = ceil(samples / 2048)`, and a last start time close to the file's duration. This completes in a few seconds.

## 4. Check error handling

```
cd backend
python -c "from app.services.note_analysis import NoteBinAnalyzer; NoteBinAnalyzer(8000, 2048)"
```

Expected: `AudioAnalysisError` explaining that the sample rate is too low for the highest note.
