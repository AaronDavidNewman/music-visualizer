"""The number of notes: using only the notes with the most energy, spread over the whole grid.

A frame is drawn from one value for each of the 84 drawn notes. The *number of notes* ``n`` (a whole number from 12 to
84) keeps only the ``n`` notes with the most **energy**, where the energy of a note is the sum of its smoothed values over
all frames of the file. The notes are chosen once for the whole file, so the same notes are used in every frame (a choice
made in every frame would flip at the margin); notes of equal energy are ranked by pitch, the lower note first, so the
choice is repeatable. The chosen notes keep their order of pitch.

For each frame the ``n`` values of the chosen notes are then *spread* over 84 values: evenly spaced positions made with
``np.linspace`` from the first to the last chosen note (84 of them), read with ``np.interp`` by linear interpolation. The
first chosen note keeps its value at the first position and the last at the last, every value lies between the values of
its neighbours, and with ``n = 84`` the values are returned unchanged. The 84 values take the place of the 84 note values in
everything that follows (the grid of 12 columns by 7 rows, the resolution, the threshold, the colors, the picture).

This module knows nothing about the note analysis or the pictures.
"""

import math
import numbers

import numpy as np

MIN_NOTE_COUNT = 12
MAX_NOTE_COUNT = 84
DEFAULT_NOTE_COUNT = 84

# the number of values per frame: the drawn notes, and the size of the spread
_NOTES = 84


def check_note_count(value) -> int:
    """Return ``value`` as an ``int`` when it is a whole number from 12 to 84 (no strings, no fractions, no booleans)."""
    if (
        isinstance(value, bool)
        or not isinstance(value, numbers.Real)
        or not math.isfinite(value)
        or int(value) != value
        or not MIN_NOTE_COUNT <= value <= MAX_NOTE_COUNT
    ):
        raise ValueError(f"The number of notes must be a whole number from {MIN_NOTE_COUNT} to {MAX_NOTE_COUNT}.")
    return int(value)


def _check_values(values) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != _NOTES:
        raise ValueError(f"Each frame needs {_NOTES} note values (got shape {values.shape}).")
    return values


def top_energy_notes(values: np.ndarray, count: int) -> np.ndarray:
    """The ``count`` notes with the most energy, as sorted note numbers (0 to 83), the same for every frame.

    ``values`` has one row per frame and 84 columns (the drawn notes, after smoothing). The energy of a note is the sum of
    its column. Notes of equal energy are ranked by pitch, the lower one first.
    """
    count = check_note_count(count)
    values = _check_values(values)
    energy = values.sum(axis=0)
    return np.sort(np.argsort(-energy, kind="stable")[:count])


def spread_notes(values: np.ndarray, count: int) -> np.ndarray:
    """The values of the ``count`` highest-energy notes of every frame, spread over 84 values: shape ``(frames, 84)``.

    See the module docstring. With ``count`` 84 the result equals ``values`` (a copy); the input is never modified.
    """
    count = check_note_count(count)
    values = _check_values(values)
    if count == _NOTES:
        return values.copy()
    selected = values[:, top_energy_notes(values, count)]
    positions = np.linspace(0, count - 1, _NOTES)
    notes = np.arange(count)
    out = np.empty((values.shape[0], _NOTES))
    for t in range(values.shape[0]):
        out[t] = np.interp(positions, notes, selected[t])
    return out
