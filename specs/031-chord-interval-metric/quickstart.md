# Quickstart: Chord Interval Metric

Validation scenarios that prove the feature works. Contract: [chords.md](contracts/chords.md); rules and shapes: [data-model.md](data-model.md). The feature has no page, request or picture, so everything is checked from Python and from the tests.

## Prerequisites

- Backend: `cd backend`, the `.venv` active, `pip install -r requirements.txt` (nothing new).
- Nothing to start: no server, no frontend.

## Automated checks

```text
cd backend && python -m pytest tests/test_chords.py tests/test_chords_audio.py
cd backend && python -m pytest        # everything else is unchanged
cd frontend && npm test               # untouched; still green
```

Expected: all green, including the reference-hash tests of the pictures (nothing changed for them).

## Scenario 1: The worked examples (User Story 1)

In a Python shell in `backend/` (note numbers: C3 = 15, C4 = 27, E4 = 31, G4 = 34, C5 = 39):

1. Make an array of zeros `(1, 88)` per window, put strengths on the notes of a window, for example `values[0, [15, 31]] = [1.0, 0.9]` (C3 and E4).
2. `from app.services.chords import measure_chords`; `series = measure_chords(values, [(4,)])`; `series.record(0)` is `ChordRecord(chord_type=(4,), inversion=0, notes=(15, 31))`.
3. E4 and C5 (31, 39) with `[(4,)]`: inversion 1, notes `(31, 39)`.
4. C4, E4, G4 (27, 31, 34) with `[(4,), (4, 7)]`: `(4, 7)`, inversion 0; E4, G4, C5 with the same list: `(4, 7)`, inversion 1; G4, C5, E5: inversion 2.
5. With `[(5,), (7,)]`: notes 7 steps apart give `(7,)` root position; 5 steps apart give `(7,)` first inversion.
6. With `[(4,), (8,)]`: notes 8 steps apart give `(8,)` root position; 4 steps apart give `(8,)` first inversion.

## Scenario 2: One record per window (User Story 2)

1. Make 500 windows with a C major triad in the middle 100 and silence elsewhere; `measure_chords(values, [(4, 7)])`.
2. Expected: `series.window_count == 500`; `series.record(i)` is `None` for the silent windows and `(4, 7)` inversion 0 for the others; `series.type_index`, `series.inversion` and `series.notes` have 500 rows and `-1` where there is no chord.

## Scenario 3: Only the notes the picture would use (User Story 3)

1. Windows where two notes are very loud and a chord's three notes are fainter.
2. With neither limit, the loud notes decide. With `threshold=10` (a note below 10% of the largest value of the file does not count in that window) the faint notes stop counting or the loud ones do, exactly as the picture would hide them; with `note_count=12` only the 12 notes with the most total energy can ever be in a chord.
3. A note outside the allowed ones never appears in `series.notes`.

## Scenario 4: Bad parameters (User Story 4)

`measure_chords(values, [])`, `[()]`, `[(1, 2, 3, 4)]`, `[(0,)]`, `[(12,)]`, `[(7, 4)]`, `[(4,), (4,)]`, `[(4.5,)]` each raise `ValueError` with the message of the contract, before any window is measured; `note_count=5` and `threshold=11` raise the pictures' own messages.

## Scenario 5: With the real analysis

`pytest tests/test_chords_audio.py` synthesizes a C major triad (three sine tones), runs the real note analysis (`analyze_channels`), and measures it: the windows in the middle of the chord record `(4, 7)` in root position with the notes of C, E and G, and the silent windows record no chord.

## Scenario 7: Letters and more notes (revision of 2026-11-07)

1. Notes C4, C5 and E4 (27, 39, 31) with `[(4,)]`: the octaves of C are one letter, so the third is found: `(4,)`, inversion 0 or 1 according to the louder C, notes `(27, 31)` or `(31, 39)`.
2. A louder F# (33) beside C4 and E4 with `[(4,)]`: the third is still found, notes `(27, 31)`.
3. Two loud letters that fit nothing (notes 28 and 29), then C4 and E4: found (4 letters looked at); with a third loud letter first (28, 29, 30) the third is the 5th and 4th loudest letter and is not found.
4. C4, E4, G4 loud with a faint B (38) and `[(4, 7), (4, 11)]`: `(4, 7)`, not `(4, 11)`.
5. `python -B -m pytest tests/test_chords.py -q` runs these and the oracle comparisons.

## Scenario 6: Speed (SC-007)

`measure_chords` on 4,000 windows of random note strengths with 10 chord types takes well under a few seconds.
