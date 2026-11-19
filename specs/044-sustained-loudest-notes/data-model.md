# Data Model: Sustained loudest notes

One new kind of array (`LoudestIndices`) and one new setting. Everything else is the existing arrays.

## Selection (of a frame) - `LoudestIndices`

| Item | Value |
|---|---|
| Alias | `LoudestIndices` in `backend/app/services/array_types.py` |
| Shape | `(frames, count)`, dtype `intp` (`count` is n: 5 for Decay, Decay Exp, Chromatic Decay, Chromatic Wireframe; 5 to 8 for Polar Chords and Polychord) |
| Meaning | for each frame, the index of the note (0 to 83; for Chromatic Decay and Chromatic Wireframe the index of the letter, 0 to 11) at each of the `count` places of the selection, **loudest first**. When fewer than `count` notes sound, the last places hold notes whose value is 0 (so the caller's `values[order] > 0` test says "empty"); they are never used as notes. |
| Made by | `held_notes.hold_loudest` |
| Used by | `decay.gains`, `chromatic_decay._raw_gains`, `polar_chords._targets`, `polychord.loudest_letters` |

Rules (the spec's FR-001 to FR-006, written for the array):

- row 0, and any row after a row in which nothing sounded: the n loudest (the old array);
- otherwise: the notes of the previous row that rank within the loudest `n + k` of this frame and have a value above 0 (**held**), followed by the loudest notes that are not held until the row has `n`
  notes or no more notes sound;
- the row is ordered by loudness (stable: the lower note first on equal strength), not by the order in which the notes were selected;
- a row never holds a note twice and never holds a note whose value is 0.

## The setting - Extra notes (k)

| Field | Value |
|---|---|
| Name on the page | *Extra notes (k)* (control id `extra-notes`, group `held-notes`, title *Held notes*) |
| Request field / answer key | `extra_notes` |
| Type | whole number |
| Range | **1 to n** for the six pictures that use it (n as above: 5, or the Notes shown / Number of notes value of the picture); **1 to 8** for any other picture (accepted and ignored) |
| Default | 2 (`DEFAULT_EXTRA_NOTES`) |
| Library value | `extra: int = 0` in the library functions (0 = off, the old n loudest); the job always passes a value from 1 to 8 |

Validation rules (verbatim from the contract):

- not sent: 2;
- sent: a whole number from 1 to 8 (not a bool, not fractional, not empty), else 400 "The extra notes must be a whole number from 1 to 8.";
- for Decay, Decay Exp, Chromatic Decay, Chromatic Wireframe: at most 5, else 400 "The extra notes must be a whole number from 1 to 5.";
- for Polar Chords and Polychord: at most the number of notes chosen (5 to 8), else 400 "The extra notes must be a whole number from 1 to {n}.";
- all of it before the file is read.

## Unchanged

- `NoteStrengths` `(frames, 88)` (the frames after the averaging of feature 043; for Chromatic types after the Threshold), `PointGains`, `BarArcs`, `LoudLetters`: same shapes and meanings; their *Made
  by* lines now name the arrays that come from the selection.
- The chord measurement (`chords.measure_chords`) and `ChordMeasure`.

## State transitions

The selection of frame `f` depends on the selection of frame `f - 1` and the values of frame `f`. It is computed once for the whole file before drawing (not during it), so drawing can still be done a
frame at a time in any order.
