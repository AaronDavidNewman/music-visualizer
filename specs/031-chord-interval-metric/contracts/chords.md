# Contract: The chord measurement (library only)

This feature has **no HTTP, page or picture interface** (spec FR-011): the job request, the response, the settings page and the frames are unchanged. The interface is a library module for later features to call. Rules and shapes: [data-model.md](../data-model.md).

## Module `app/services/chords.py`

```python
MIN_INTERVALS, MAX_INTERVALS, MAX_STEP = 1, 3, 11      # a chord type: 1 to 3 intervals, each 1 to 11 steps
NOTES = 84                                             # the piano notes used; note 0 is A1 (55 Hz)

check_chord_type(value) -> tuple[int, ...]             # one chord type, checked; a bare whole number is a one-interval type
check_chord_types(types) -> tuple[tuple[int, ...], ...]   # the list of chord types, checked, in the order given
inversion_patterns(chord_type) -> tuple[tuple[int, ...], ...]   # steps above the lowest note for inversion 0 .. n

@dataclass(frozen=True)
class ChordRecord:
    chord_type: tuple[int, ...]       # as given, e.g. (4, 7)
    inversion: int                    # 0 = root position
    notes: tuple[int, ...]            # the original notes (0..83), lowest to highest, as they sound

@dataclass(frozen=True)
class ChordSeries:
    chord_types: tuple[tuple[int, ...], ...]
    type_index: np.ndarray            # (W,) int16, -1 = no chord
    inversion: np.ndarray             # (W,) int8,  -1 = no chord
    notes: np.ndarray                 # (W, 4) int16, lowest first, -1 padding / no chord
    window_count -> int
    record(i) -> ChordRecord | None
    records() -> list[ChordRecord | None]

measure_chords(values, chord_types, note_count=None, threshold=None) -> ChordSeries
```

### `measure_chords`

| Parameter | Rule |
|-----------|------|
| `values` | `(W, 84..88)` array of finite, non-negative note strengths, one row per analysis window. Not changed. Anything else: `ValueError` `Each window needs at least 84 note values (got shape ...).` / `The note values must be finite numbers that are not negative.` |
| `chord_types` | The list of chord types to look for, always given (nothing is built in); see `check_chord_types` |
| `note_count` | `None` or a whole number 12 to 84; as the Notes setting of the pictures. Anything else: `The number of notes must be a whole number from 12 to 84.` |
| `threshold` | `None` or a number 0 to 10; as the Threshold setting of the pictures. Anything else: `The threshold must be a number from 0 to 10.` |

All parameters are checked before any window is measured. The result has exactly `W` entries in window order; an entry depends only on its own row of `values` and the parameters (and, for `note_count` and `threshold`, on the whole array, as the picture's choices do). Two calls with the same arguments give equal results.

### `check_chord_types` messages

| Problem | Message |
|---------|---------|
| Not a list, or empty | `The chord types must be a list of one or more chord types.` |
| A chord type with no intervals, more than 3, an interval that is not a whole number from 1 to 11 (a boolean, a float, a string, 0, 12), or not in increasing order | `A chord type must be 1 to 3 intervals, each a whole number of steps from 1 to 11, in increasing order (got <value>).` |
| The same chord type twice | `The chord type (<tuple>) is given more than once.` |

## Examples

Note numbers: C3 = 15, C4 = 27, E4 = 31, G4 = 34, C5 = 39.

With the types `((4,), (4, 7))`:

| Sounding notes of a window | Recorded |
|---------------------------|----------|
| C3, E4 | `(4,)`, inversion 0, notes `(15, 31)` |
| E4, C5 | `(4,)`, inversion 1, notes `(31, 39)` |
| C4, E4, G4 | `(4, 7)`, inversion 0, notes `(27, 31, 34)` (the three letters; two of them, C4 and E4, would also match `(4,)`, but the longest wins) |
| E4, G4, C5 | `(4, 7)`, inversion 1, notes `(31, 34, 39)` |

With the types `((4,), (8,))`: notes 8 steps apart (E4, C5) give `(8,)` root position, and notes 4 steps apart (C3, E4) give `(8,)` in **first inversion**: the widest wins over `(4,)` in root position.

With the types `((5,), (7,))`: a fifth (0, 7) gives `(7,)` root position; a fourth (0, 5) gives `(7,)` first inversion (the widest wins over `(5,)` in root position).

Since 2026-11-07 the notes of a window are combined into 12 letters (octaves added up) and a type with `n` intervals tries every choice of `n + 1` of the `n + 3` loudest letters (4, 5 or 6), so, with `((4,),)`:

| Sounding notes (strengths in this order) | Recorded |
|------------------------------------------|----------|
| F#4 (loudest), C4, E4 | `(4,)`, inversion 0, notes `(27, 31)`: the louder F# fits no chord and does not hide the third |
| C2, E3, C3 | `(4,)`, inversion 0, notes `(3, 19)`: C2 and C3 are one letter, recorded as its louder octave (C2) |
| C2, C3 | no chord (one letter) |

With `((4, 7), (4, 11))` and C4, E4, G4 loud and a faint B4: `(4, 7)` with `(27, 31, 34)`: the louder letters win before the wider interval (C E B would be `(4, 11)`).

## What does not change

`POST /api/jobs` and its response, the settings page, every picture and every frame, the existing measurements (note analysis, local peaks) and the other modules are untouched.
