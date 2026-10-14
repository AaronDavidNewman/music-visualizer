# Data Model: Top-Energy Notes

No stored data is added. These are the values that exist while a job is created, and the rules between them.

## Number of notes

| | |
|-|-|
| Values | whole numbers 12 to 84 (default 84 = all drawn notes) |
| Where it lives | `MIN_NOTE_COUNT`, `MAX_NOTE_COUNT`, `DEFAULT_NOTE_COUNT`, `check_note_count` in `backend/app/services/note_selection.py`; `NOTE_COUNT_RANGE`, `DEFAULT_NOTE_COUNT`, `validateNoteCount`, `formatNoteCount` in `frontend/src/utilities/validation.ts` |
| Refusal | not a whole number from 12 to 84, including empty: `The number of notes must be a whole number from 12 to 84.` |

## Per-job values

| Name | Definition |
|------|------------|
| `S` | the smoothed note array of the file, `(frames, 88)` (unchanged) |
| `peak` | `S.max()` over all 88 notes (unchanged; the same at every number of notes) |
| `shown` | `S[:, :84]`, the drawn notes: note `n` at row `n // 12`, column `n % 12` |
| `energy` | `shown.sum(axis=0)`, `(84,)`: the total of a note's smoothed values over all frames |
| `chosen` | `np.sort(np.argsort(-energy, kind="stable")[:count])`, `(count,)` note indices in order of pitch; ties go to the lower note; the same for every frame |
| `selected[t]` | `shown[t, chosen]`, `(count,)` |
| `spread[t]` | `np.interp(np.linspace(0, count - 1, 84), np.arange(count), selected[t])`, `(84,)`; at `count = 84` equal to `shown[t]` and `np.interp` is not called |
| After the spread | `spread` takes the place of `shown` in everything that follows: `interpolate_grid(spread, 12, 7, resolution)`, `hidden_below(values, peak, threshold)`, `colorize(values, colormap, n, peak)`, the writers |

## Invariants

- At `count = 84` the spread is exactly `shown` (and the pictures are those made before the feature).
- The first and last values of `spread[t]` are the values of the first and the last chosen note; every value is between the smallest and the largest chosen value, so `spread[t].max()` never exceeds the largest chosen value.
- A note outside `chosen` has no effect on any value of `spread`, in any frame (its value can change freely as long as the ranking of `energy` is unchanged and `peak` is unchanged).
- Notes with no energy are still counted among the `count` (value 0), so `chosen` always has exactly `count` entries; a silent file has all values 0 and flat pictures.
- The four undrawn notes (84 to 87) are never chosen but count for `peak`.

## Rules

- Smoothing comes before the energy and the spread; the Resolution, the Threshold, the colors and the image type come after it and are unchanged.
- The frame count, timing, size and file names are those of the job with 84 notes.

## Response

One new key: `note_count` (the whole number used, 84 when not sent).
