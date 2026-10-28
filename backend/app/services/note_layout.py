"""Which of the 84 drawn notes is drawn in which cell of the 12 x 7 grid: the ``rows`` layout and the ``spiral`` layout.

The pictures that draw one shape per note (the tiles, the blended tiles and the concentric circles) take the note values of a
frame in **cell order**: value ``i`` is for the cell at row ``i // 12`` and column ``i % 12``, counted from the top left. This
module decides which note that is.

* ``rows`` (the default, as it always was): note ``n`` is in cell ``n``. The notes are listed in order like text, twelve to a row,
  the lowest at the top left.
* ``spiral``: a fixed arrangement around **middle C** (C4, the 28th note, index 27), which is in the 3rd row and the 6th column
  (counted from 1). The next note up is in the cell to its right and the next note down in the cell to its left; the notes above
  C wind **clockwise** outward from it and the notes below it **counterclockwise**. Two walkers start at C's cell, each on a
  square spiral (legs of 1, 1, 2, 2, 3, 3, ... cells): the high one goes east first and turns right at the end of every leg, the
  low one goes west first and turns left. They take turns, the high one first, each putting its next note in the next cell of its
  own spiral that is on the grid and not yet taken; when the 27 low notes are all placed the high walker (56 notes) goes on alone.
  Because a walker skips cells that are off the grid or taken, 13 semitone steps are not between neighbouring cells.

The layout does not depend on the music. Only the order of the values changes (:func:`arrange_notes`): everything that is done with
them afterwards (the threshold, the colors, the interpolation to a finer grid, the blend of tiles, the circles) works on cells, so
it works as before.
"""

import numpy as np

LAYOUTS = ("rows", "spiral")
DEFAULT_NOTE_LAYOUT = "rows"

GRID_COLUMNS = 12
GRID_ROWS = 7
NOTES = GRID_COLUMNS * GRID_ROWS  # the 84 drawn notes: A1 (MIDI 33) to G#8 (MIDI 116)

# middle C is MIDI 60: the 28th of the notes that start at MIDI 33, in the 3rd row and the 6th column (from 1)
MIDDLE_C_NOTE = 60 - 33
MIDDLE_C_CELL = (2, 5)

_EAST, _SOUTH, _WEST, _NORTH = (0, 1), (1, 0), (0, -1), (-1, 0)
_CLOCKWISE = (_EAST, _SOUTH, _WEST, _NORTH)  # a right turn takes the next direction of this list
_COUNTERCLOCKWISE = (_WEST, _SOUTH, _EAST, _NORTH)  # a left turn takes the next direction of this list
_MOST_CELLS_TRIED = 4000  # a walker that has gone this far has left the grid for good (never reached)


def check_note_layout(value) -> str:
    """Return ``value`` when it is exactly one of the offered names (no trimming, no case folding)."""
    if not isinstance(value, str) or value not in LAYOUTS:
        raise ValueError(f"The note layout must be one of {', '.join(LAYOUTS)}.")
    return value


def _spiral_cells(start: tuple[int, int], directions: tuple):
    """The cells of an endless square spiral outward from ``start`` (not including it): legs of 1, 1, 2, 2, 3, 3, ... cells."""
    row, column = start
    turn = 0
    leg = 1
    while True:
        for _ in range(2):
            step_row, step_column = directions[turn % 4]
            for _ in range(leg):
                row, column = row + step_row, column + step_column
                yield row, column
            turn += 1
        leg += 1


def _spiral_order() -> np.ndarray:
    """The note of every cell of the spiral layout, row by row."""
    cells: dict[tuple[int, int], int] = {MIDDLE_C_CELL: MIDDLE_C_NOTE}
    high = _spiral_cells(MIDDLE_C_CELL, _CLOCKWISE)
    low = _spiral_cells(MIDDLE_C_CELL, _COUNTERCLOCKWISE)

    def place(walker, note: int) -> None:
        for _ in range(_MOST_CELLS_TRIED):
            row, column = next(walker)
            if 0 <= row < GRID_ROWS and 0 <= column < GRID_COLUMNS and (row, column) not in cells:
                cells[(row, column)] = note
                return
        raise ValueError("The spiral left the grid before every note was placed.")

    next_high, next_low = MIDDLE_C_NOTE + 1, MIDDLE_C_NOTE - 1
    while next_high < NOTES or next_low >= 0:
        if next_high < NOTES:  # the high notes first, then the low notes, and so on in turns
            place(high, next_high)
            next_high += 1
        if next_low >= 0:
            place(low, next_low)
            next_low -= 1
    order = np.empty(NOTES, dtype=np.int64)
    for (row, column), note in cells.items():
        order[row * GRID_COLUMNS + column] = note
    return order


def _read_only(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


_ORDERS = {
    "rows": _read_only(np.arange(NOTES, dtype=np.int64)),
    "spiral": _read_only(_spiral_order()),
}


def note_order(layout: str) -> np.ndarray:
    """The note drawn in each cell, row by row: an integer array of 84 note indexes (0 is the lowest drawn note, A1)."""
    return _ORDERS[check_note_layout(layout)]


def arrange_notes(values, layout: str) -> np.ndarray:
    """The note values of every frame in the cell order of ``layout``: a float64 array of shape ``(frames, 84)``.

    ``values`` has one row per frame and at least 84 columns (the notes after the 84th are not drawn and are left out). Entry ``i``
    of a result row is the value of the note that the layout draws in cell ``i``. The input is not changed.
    """
    order = note_order(layout)
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] < NOTES:
        raise ValueError(f"At least {NOTES} note values per frame are needed (got shape {values.shape}).")
    return values[:, order]
