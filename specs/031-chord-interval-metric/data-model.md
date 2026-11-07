# Data Model: Chord Interval Metric

Entities of [spec.md](spec.md).

## Notes

- The 84 piano notes of the analysis, numbered **0 to 83**: 0 is A1 (55 Hz), each next note one step (half step) higher. The analysis has 88 values per window; the four above note 83 are not used for chords.
- Letter of a note: `note % 12` with 0 = A (A, A#, B, C, C#, D, D#, E, F, F#, G, G#). Middle C (C4) is note 27, C3 is 15, E4 is 31, C5 is 39.

## Chord type

A tuple of `n` whole numbers (1 to 3 of them), the steps above an implied root.

| Rule | Detail |
|------|--------|
| Length | `n` = 1 to 3 intervals; the chord has `n + 1` notes and `n + 1` positions (inversions 0 to `n`) |
| Each interval | A whole number of steps from 1 to 11 |
| Order | Strictly increasing: `(4, 7)` is allowed, `(7, 4)` is refused |
| Given as | A tuple or list; a bare whole number is the one-interval type (`5` is `(5,)`) |
| In a list | No chord type twice; the list is not empty; the order given is kept |

Notes of the chord: `c = (0, t1, ..., tn)`.

**Inversion `k`** (0 to `n`): the pattern of steps above the lowest note when the `k` lowest chord notes are moved up an octave: `(c[k], ..., c[n], c[0] + 12, ..., c[k-1] + 12)` minus `c[k]`.

| Chord type | Inversion 0 | Inversion 1 | Inversion 2 | Inversion 3 |
|------------|-------------|-------------|-------------|-------------|
| `(4)` | 0, 4 | 0, 8 | | |
| `(5)` | 0, 5 | 0, 7 | | |
| `(7)` | 0, 7 | 0, 5 | | |
| `(4, 7)` | 0, 4, 7 | 0, 3, 8 | 0, 5, 9 | |
| `(4, 8)` | 0, 4, 8 | 0, 4, 8 | 0, 4, 8 | |
| `(3, 6, 9)` | 0, 3, 6, 9 | 0, 3, 6, 9 | 0, 3, 6, 9 | 0, 3, 6, 9 |

When the patterns of several inversions are the same (symmetrical chords), the lowest inversion number is the one that is recorded.

## Window match

For one window and one chord type with `n` intervals:

1. **Allowed notes**: the notes 0 to 83, minus the ones the optional limits leave out (see Allowed notes). A note that is not allowed has strength 0.
2. **The letters** (revised 2026-11-07): the allowed notes are combined into the 12 letters (`note mod 12`): a letter's strength is its 7 octaves added up from the lowest octave; a letter at or under `1e-6` of the window's loudest letter has strength 0; a letter's note is its loudest octave (the lowest on a tie). The sounding letters are ranked by strength (ties to the lower letter) and the first `n + 3` are the **reach** of the type (4, 5 or 6). Fewer than `n + 1` sounding in the reach: no match.
3. **Choices**: every choice of `n + 1` letters of the reach (6, 10 or 15 of them) is a candidate. **Fold**: with `L` the lowest of the notes of a choice, each note has `offset = (note − L) mod 12`. The mask has bit `offset` set for each note.
4. **Match**: the mask equals the mask of inversion `k` of the type for some `k`; the lowest such `k` is the inversion. The inversion masks have exactly `n + 1` bits and the letters of a choice are all different, so the number of bits always agrees.

## Selection

Of all candidates (chord type, choice of letters) that match the window, one is recorded: the one with the greatest `(n, loudness, widest interval, −inversion, −index of the choice)` compared in that order: the most intervals, then the loudest letters (strengths added up from the lowest letter), then the largest interval of the type as given, then the lowest inversion number, then the first choice among the combinations of the louder letters. Two different types never tie on all of these, so the order of the list given never decides.

## Chord record

| Field | Meaning |
|-------|---------|
| `chord_type` | The tuple as given, such as `(4, 7)` |
| `inversion` | 0 for root position, 1 to `n` |
| `notes` | The `n + 1` original note numbers (0 to 83), lowest to highest: the loudest octave of each letter of the chord, as it sounds (before folding) |

A window with no chord has no record (`None`).

## Chord series (the stored result)

One entry per analysis window, in window order. `W` is the number of windows.

| Field | Shape and type | Meaning |
|-------|----------------|---------|
| `chord_types` | tuple of tuples | The checked chord types in the order given |
| `type_index` | `(W,)` int16 | Index into `chord_types`; −1 for no chord |
| `inversion` | `(W,)` int8 | 0 to 3; −1 for no chord |
| `notes` | `(W, 4)` int16 | Original note numbers, lowest first; −1 for unused places and for no chord |

Methods: `window_count`, `record(i)` (a chord record or `None`), `records()` (a list of them).

## Allowed notes

| Parameter | Effect |
|-----------|--------|
| `note_count` (optional, whole number 12 to 84) | Only the `note_count` notes with the greatest total strength over all windows (equal strength to the lower note) are allowed, the same in every window; they keep their own pitch |
| `threshold` (optional, number 0 to 10) | In a window, a note whose strength is strictly below `threshold` percent of the largest value anywhere in the array is not allowed |
| neither | All 84 notes are allowed |

Both are applied before the notes are combined into letters; a note must pass both.

## Input

`values`: `(W, 84)` to `(W, 88)` finite, non-negative numbers, one row per window: the note strengths of the analysis (the picture's values if the limits are to agree with the picture). Columns after the 84th are used only for the largest value of the threshold. The input is not changed.
