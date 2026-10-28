"""The note layout (feature 026): the rows layout of today and the spiral around middle C, as a table of which note is in which cell."""

import numpy as np
import pytest

from app.services.note_layout import (
    DEFAULT_NOTE_LAYOUT,
    LAYOUTS,
    MIDDLE_C_CELL,
    MIDDLE_C_NOTE,
    arrange_notes,
    check_note_layout,
    note_order,
)

MESSAGE = "The note layout must be one of rows, spiral."
COLUMNS, ROWS, NOTES = 12, 7, 84

# the table of the spec: the distance of the note in each cell from middle C in semitones (C is middle C itself)
TABLE_TEXT = """
 49 -21 -13  11  12 -12 -11 -10  13  22  36  50
 48 -22 -14  -5   4  -4  -3   5  14  23  37  51
 47 -23 -15  -6  -1   C   1   6  15  24  38  52
 46 -24 -16  -7  -2   3   2   7  16  25  39  53
 45 -25 -17  -8  -9  10   9   8  17  26  40  54
 44 -26 -18 -19 -20  21  20  19  18  27  41  55
 43 -27  35  34  33  32  31  30  29  28  42  56
"""
OFFSETS = [[0 if word == "C" else int(word) for word in line.split()] for line in TABLE_TEXT.strip().splitlines()]

# the semitone steps that are not between neighbouring cells, as (lower, upper) distances from middle C
JUMPS = {(-21, -20), (-13, -12), (-10, -9), (-5, -4), (-3, -2), (3, 4), (4, 5), (10, 11), (12, 13), (21, 22), (35, 36), (42, 43), (49, 50)}


def cell_of(note):
    index = int(np.flatnonzero(note_order("spiral") == note)[0])
    return divmod(index, COLUMNS)


def cell_of_offset(offset):
    return cell_of(MIDDLE_C_NOTE + offset)


# ---------------------------------------------------------------------------------------------------------------------
# the constants and the check
# ---------------------------------------------------------------------------------------------------------------------


def test_the_two_layouts_rows_by_default_and_middle_c_is_the_28th_note_at_row_3_column_6():
    assert LAYOUTS == ("rows", "spiral")
    assert DEFAULT_NOTE_LAYOUT == "rows"
    assert MIDDLE_C_NOTE == 27  # A1 is MIDI 33, middle C MIDI 60
    assert MIDDLE_C_CELL == (2, 5)  # the 3rd row and the 6th column, counted from 1


@pytest.mark.parametrize("value", ["rows", "spiral"])
def test_a_layout_that_is_offered_is_returned(value):
    assert check_note_layout(value) == value


@pytest.mark.parametrize("value", ["Rows", "SPIRAL", " rows", "rows ", "", "row", "spirals", None, 1, ["rows"], b"rows", True])
def test_anything_else_is_refused_with_the_two_names(value):
    with pytest.raises(ValueError) as error:
        check_note_layout(value)
    assert str(error.value) == MESSAGE


# ---------------------------------------------------------------------------------------------------------------------
# the rows layout
# ---------------------------------------------------------------------------------------------------------------------


def test_rows_is_the_identity_note_n_at_row_n_div_12_and_column_n_mod_12():
    order = note_order("rows")
    assert order.shape == (NOTES,) and order.dtype.kind in "iu"
    assert order.tolist() == list(range(NOTES))


# ---------------------------------------------------------------------------------------------------------------------
# the spiral layout
# ---------------------------------------------------------------------------------------------------------------------


def test_the_spiral_is_the_table_of_the_spec_cell_by_cell():
    order = note_order("spiral")
    assert order.shape == (NOTES,)
    for row in range(ROWS):
        for column in range(COLUMNS):
            assert order[row * COLUMNS + column] == MIDDLE_C_NOTE + OFFSETS[row][column], (row, column)


def test_every_cell_holds_a_different_note_and_every_note_is_in_one_cell():
    order = note_order("spiral")
    assert sorted(order.tolist()) == list(range(NOTES))
    assert len(OFFSETS) == ROWS and all(len(row) == COLUMNS for row in OFFSETS)


def test_middle_c_is_at_row_3_column_6_with_the_next_note_up_to_its_right_and_the_next_note_down_to_its_left():
    assert cell_of(27) == (2, 5)
    assert cell_of(28) == (2, 6)  # C#4
    assert cell_of(26) == (2, 4)  # B3


def test_the_first_cells_of_the_two_arms():
    assert [cell_of_offset(k) for k in (1, 2, 3)] == [(2, 6), (3, 6), (3, 5)]  # east, south-east, south of C
    assert [cell_of_offset(k) for k in (-1, -2, -3)] == [(2, 4), (3, 4), (1, 6)]  # west, south-west, north-east of C


def test_the_high_notes_turn_clockwise_around_middle_c_and_the_low_notes_counterclockwise():
    centre_row, centre_column = MIDDLE_C_CELL

    def turn(first, second):
        """The cross product of two steps around the center on the screen (rows grow downward): above 0 is clockwise."""
        (r1, c1), (r2, c2) = first, second
        v1, v2 = (r1 - centre_row, c1 - centre_column), (r2 - centre_row, c2 - centre_column)
        return v1[1] * v2[0] - v1[0] * v2[1]

    high = [cell_of_offset(k) for k in (1, 2, 3)]
    low = [cell_of_offset(k) for k in (-1, -2)]
    assert turn(high[0], high[1]) > 0 and turn(high[1], high[2]) > 0  # east, south-east, south: clockwise
    assert turn(low[0], low[1]) < 0  # west, south-west: counterclockwise


def test_the_notes_wind_outward_from_middle_c():
    # the Chebyshev distance of the cells from middle C never falls by more than the one step an arm may turn back in, and the farthest cells are the last notes
    distances = {k: max(abs(cell_of_offset(k)[0] - 2), abs(cell_of_offset(k)[1] - 5)) for k in range(-27, 57)}
    assert distances[0] == 0
    assert distances[1] == distances[-1] == 1
    assert max(distances[k] for k in range(1, 11)) <= 2 and max(distances[k] for k in range(-10, 0)) <= 2
    assert distances[56] == 6 and distances[-27] >= 3
    assert sum(distances[k] for k in range(40, 57)) > sum(distances[k] for k in range(1, 18))
    assert sum(distances[k] for k in range(-27, -10)) > sum(distances[k] for k in range(-10, 0))


def test_exactly_thirteen_semitone_steps_are_not_between_neighbouring_cells():
    not_next_to = set()
    for offset in range(-27, 56):
        (r1, c1), (r2, c2) = cell_of_offset(offset), cell_of_offset(offset + 1)
        if abs(r1 - r2) + abs(c1 - c2) != 1:
            not_next_to.add((offset, offset + 1))
    assert not_next_to == JUMPS
    assert len(not_next_to) == 13


def test_the_rule_made_by_two_walkers_taking_turns_gives_the_same_table():
    """The table, rebuilt here from the rule of the spec by a different route (explicit legs instead of a generator)."""
    east, south, west, north = (0, 1), (1, 0), (0, -1), (-1, 0)

    def cells(start, directions):
        row, column = start
        leg = 1
        index = 0
        while leg < 40:
            for _ in range(2):
                for _ in range(leg):
                    row, column = row + directions[index % 4][0], column + directions[index % 4][1]
                    yield row, column
                index += 1
            leg += 1

    high_cells = cells(MIDDLE_C_CELL, [east, south, west, north])
    low_cells = cells(MIDDLE_C_CELL, [west, south, east, north])
    taken = {MIDDLE_C_CELL}
    placed = {MIDDLE_C_CELL: 0}

    def place(walker, value):
        for cell in walker:
            if 0 <= cell[0] < ROWS and 0 <= cell[1] < COLUMNS and cell not in taken:
                taken.add(cell)
                placed[cell] = value
                return

    high_next, low_next = 1, -1
    while high_next <= 56 or low_next >= -27:
        if high_next <= 56:
            place(high_cells, high_next)
            high_next += 1
        if low_next >= -27:
            place(low_cells, low_next)
            low_next -= 1
    assert len(placed) == NOTES
    for (row, column), offset in placed.items():
        assert OFFSETS[row][column] == offset


def test_the_layout_is_the_same_every_time_and_the_caller_cannot_change_it():
    first = note_order("spiral").copy()
    again = note_order("spiral")
    assert (first == again).all()
    try:
        again[0] = 999
    except ValueError:
        pass  # a read-only array
    assert (note_order("spiral") == first).all()
    rows = note_order("rows")
    try:
        rows[0] = 5
    except ValueError:
        pass
    assert note_order("rows")[0] == 0


def test_a_layout_that_is_not_offered_has_no_order():
    with pytest.raises(ValueError) as error:
        note_order("circle")
    assert str(error.value) == MESSAGE


# ---------------------------------------------------------------------------------------------------------------------
# arranging the values
# ---------------------------------------------------------------------------------------------------------------------


def test_the_values_are_put_in_cell_order():
    values = np.random.default_rng(1).random((5, 88))
    order = note_order("spiral")
    got = arrange_notes(values, "spiral")
    assert got.shape == (5, NOTES)
    for cell in range(NOTES):
        assert (got[:, cell] == values[:, order[cell]]).all()


def test_rows_is_a_copy_of_the_first_84_columns_and_the_undrawn_notes_are_dropped():
    values = np.random.default_rng(2).random((4, 88))
    got = arrange_notes(values, "rows")
    assert (got == values[:, :NOTES]).all()
    got[0, 0] = -5.0
    assert values[0, 0] != -5.0


def test_arranging_does_not_change_the_input_and_is_a_permutation_of_each_frame():
    values = np.random.default_rng(3).random((6, 84))
    before = values.copy()
    got = arrange_notes(values, "spiral")
    assert (values == before).all()
    assert (np.sort(got, axis=1) == np.sort(values, axis=1)).all()
    assert not (got == values).all()


def test_one_note_value_that_is_loud_lands_in_the_cell_of_the_table():
    for offset in (-27, -5, 0, 1, 3, 4, 17, 56):
        values = np.zeros((1, 88))
        values[0, MIDDLE_C_NOTE + offset] = 1.0
        got = arrange_notes(values, "spiral")[0]
        row, column = next((r, c) for r in range(ROWS) for c in range(COLUMNS) if OFFSETS[r][c] == offset)
        assert got[row * COLUMNS + column] == 1.0 and got.sum() == 1.0


@pytest.mark.parametrize("bad", [np.zeros(84), np.zeros((2, 83)), np.zeros((2, 3, 84))])
def test_values_that_are_not_note_values_are_refused(bad):
    with pytest.raises(ValueError, match="At least 84 note values per frame are needed"):
        arrange_notes(bad, "spiral")


def test_a_bad_layout_is_refused_when_arranging():
    with pytest.raises(ValueError) as error:
        arrange_notes(np.zeros((1, 84)), "Spiral")
    assert str(error.value) == MESSAGE


def test_no_frames_give_no_rows():
    assert arrange_notes(np.zeros((0, 88)), "spiral").shape == (0, NOTES)
