"""The colormaps and the strength-to-color mapping: ``app/services/colormaps.py``.

Nothing here names a colormap: the list can be changed by hand, and every test uses ``COLORMAPS`` and ``DEFAULT_COLORMAP``
(see ``colormap_names.py``). A name only has to be a valid matplotlib colormap and be the same in the frontend.
"""

import re
from pathlib import Path

import numpy as np
import pytest

from app.services.colormaps import (
    COLORMAP_STEPS,
    COLORMAPS,
    DEFAULT_COLORMAP,
    check_colormap,
    colorize,
    lookup_table,
)

from .colormap_names import DECODABLE, FIRST, INVALID, MESSAGE, distinct_rows

SHOWN = 84
FRONTEND_VALIDATION = Path(__file__).resolve().parents[2] / "frontend" / "src" / "utilities" / "validation.ts"


def matplotlib_table(name):
    """Matplotlib's own 8-bit table by a second route: sampling the scale at 256 evenly spaced positions."""
    from matplotlib import colormaps

    return colormaps[name](np.linspace(0, 1, 256), bytes=True)[:, :3]


def row_index(table, colour):
    """The table row of an exact colour. Only for tables whose rows are all different (see DECODABLE)."""
    matches = np.flatnonzero((table == np.asarray(colour)).all(axis=1))
    assert matches.size == 1, colour
    return int(matches[0])


def notes(*frames):
    """(frames, 88) note values; each frame is a dict {note: value}, every other note is 0."""
    out = np.zeros((len(frames), 88))
    for i, values in enumerate(frames):
        for note, value in values.items():
            out[i, note] = value
    return out


# --- the list itself ----------------------------------------------------------------------------------------------------


def test_the_list_is_a_set_of_distinct_names_with_a_default():
    assert len(COLORMAPS) >= 1
    assert all(isinstance(name, str) and name for name in COLORMAPS)
    assert len(set(COLORMAPS)) == len(COLORMAPS)
    assert DEFAULT_COLORMAP in COLORMAPS
    assert COLORMAP_STEPS == 256


@pytest.mark.parametrize("name", COLORMAPS)
def test_every_offered_name_is_a_valid_matplotlib_colormap(name):
    from matplotlib import colormaps

    assert name in colormaps, f"{name!r} is not a matplotlib colormap (matplotlib's names are case-sensitive)"


def frontend_source():
    return FRONTEND_VALIDATION.read_text(encoding="utf-8")


def frontend_names():
    """The values of the frontend's COLORMAPS list, read from the source file, in order."""
    block = re.search(r"export const COLORMAPS = \[(.*?)\] as const;", frontend_source(), re.S).group(1)
    return re.findall(r"value:\s*\"([^\"]+)\"", block)


def test_the_frontends_list_matches_this_one_name_for_name_in_the_same_order():
    assert frontend_names() == list(COLORMAPS)


def test_the_frontends_default_matches_this_one():
    assert re.search(r"export const DEFAULT_COLORMAP = \"([^\"]+)\"", frontend_source()).group(1) == DEFAULT_COLORMAP


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_offered_names_are_accepted(name):
    assert check_colormap(name) == name


@pytest.mark.parametrize("bad", [*INVALID, None, 1, b"bytes"])
def test_any_other_name_is_refused_with_the_choices(bad):
    with pytest.raises(ValueError) as error:
        check_colormap(bad)
    assert str(error.value) == MESSAGE


def test_the_message_lists_every_offered_name_in_order():
    assert MESSAGE == "The colormap must be one of " + ", ".join(COLORMAPS) + "."


# --- the tables ---------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_table_is_matplotlibs_own_eight_bit_table(name):
    table = lookup_table(name)
    assert table.shape == (256, 3) and table.dtype == np.uint8
    assert (table == matplotlib_table(name)).all()


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_table_is_cached_and_read_only(name):
    assert lookup_table(name) is lookup_table(name)
    with pytest.raises(ValueError):
        lookup_table(name)[0, 0] = 1


@pytest.mark.parametrize("name", COLORMAPS)
def test_a_table_has_many_different_colours(name):
    # matplotlib's own 8-bit conversion truncates, so a few neighbouring rows of some tables are the same colour; the table is
    # kept as matplotlib makes it, and only the tables with 256 different rows can be decoded back to a row (DECODABLE)
    assert 2 <= distinct_rows(name) <= 256


def test_an_unknown_name_cannot_make_a_table():
    with pytest.raises(ValueError, match=re.escape(MESSAGE)):
        lookup_table(INVALID[0])


# --- the strength-to-color mapping ----------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", COLORMAPS)
def test_hand_worked_strengths_land_on_the_expected_rows(name):
    # peak 100: 100 -> share 1 -> row 255; 25 -> 0.5 -> 127.5 -> 128; 4 -> 0.2 -> 51; 1 -> 0.1 -> 25.5 -> 26; 0 -> 0
    values = notes({0: 100.0, 1: 25.0, 2: 4.0, 3: 1.0, 4: 0.0})
    got = colorize(values, name, SHOWN)
    table = lookup_table(name)
    for note, row in enumerate([255, 128, 51, 26, 0]):
        assert (got[0, note] == table[row]).all(), (name, note)


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_strongest_note_is_the_last_colour_and_no_strength_the_first(name):
    rng = np.random.default_rng(3)
    values = rng.random((30, 88)) ** 3
    values[17, 40] = 5.0  # the largest value of the file
    values[3, 7] = 0.0
    got = colorize(values, name, SHOWN)
    table = lookup_table(name)
    assert (got[17, 40] == table[255]).all()
    assert (got[3, 7] == table[0]).all()


@pytest.mark.parametrize("name", DECODABLE)
def test_a_stronger_note_never_has_an_earlier_colour(name):
    sweep = np.linspace(0, 100, 5001)
    values = np.zeros((len(sweep), 88))
    values[:, 0] = sweep
    table = lookup_table(name)
    rows = np.array([row_index(table, c) for c in colorize(values, name, SHOWN)[:, 0]])
    assert (np.diff(rows) >= 0).all()
    assert rows[0] == 0 and rows[-1] == 255


@pytest.mark.parametrize("name", COLORMAPS)
def test_every_colour_is_the_table_entry_of_the_square_root_position(name):
    # an independent route: the table entries are worked out here from the strengths, for every colormap offered
    sweep = np.linspace(0, 100, 2001)
    values = np.zeros((len(sweep), 88))
    values[:, 0] = sweep
    expected = lookup_table(name)[np.rint(np.sqrt(sweep / 100) * 255).astype(int)]
    assert (colorize(values, name, SHOWN)[:, 0] == expected).all()
    assert (colorize(values, name, SHOWN)[-1, 0] == lookup_table(name)[255]).all()


def test_the_scale_is_the_square_root_of_the_share():
    values = notes({0: 100.0, 1: 36.0})
    got = colorize(values, DEFAULT_COLORMAP, SHOWN)
    assert (got[0, 1] == lookup_table(DEFAULT_COLORMAP)[round(255 * 0.6)]).all()  # sqrt(0.36) = 0.6 -> 153


def test_a_silent_input_is_the_first_colour_everywhere_and_does_not_fail():
    for name in COLORMAPS:
        got = colorize(np.zeros((4, 88)), name, SHOWN)
        assert got.shape == (4, SHOWN, 3)
        assert (got == lookup_table(name)[0]).all()


def test_the_same_strength_has_the_same_colour_wherever_and_whenever_it_sounds():
    values = notes({3: 50.0, 70: 100.0}, {10: 50.0, 70: 100.0}, {83: 50.0, 70: 100.0})
    got = colorize(values, DEFAULT_COLORMAP, SHOWN)
    assert (got[0, 3] == got[1, 10]).all() and (got[1, 10] == got[2, 83]).all()


def test_changing_the_other_notes_changes_no_other_tile():
    base = notes({5: 40.0, 60: 100.0})
    other = notes({5: 40.0, 60: 100.0, 20: 70.0, 30: 3.0})  # other notes, the same peak
    a, b = colorize(base, FIRST, SHOWN), colorize(other, FIRST, SHOWN)
    untouched = [n for n in range(SHOWN) if n not in (20, 30)]
    assert (a[:, untouched] == b[:, untouched]).all()
    assert not (a[:, [20, 30]] == b[:, [20, 30]]).all()


def test_a_steady_value_has_one_colour_in_every_frame():
    values = np.zeros((40, 88))
    values[:, 12] = 30.0
    values[7, 50] = 100.0  # the peak, in one frame only
    got = colorize(values, DEFAULT_COLORMAP, SHOWN)
    assert (got[:, 12] == got[0, 12]).all()


def test_the_loudness_of_a_frame_does_not_dim_it():
    # a frame whose notes are all quiet is not brightened or dimmed as a whole: only each note's own strength counts
    loud = notes({0: 100.0, 1: 9.0}, {1: 9.0})
    got = colorize(loud, DEFAULT_COLORMAP, SHOWN)
    assert (got[0, 1] == got[1, 1]).all()


def test_the_undrawn_notes_count_for_the_peak_but_are_not_in_the_result():
    values = notes({0: 10.0, 85: 100.0})
    got = colorize(values, DEFAULT_COLORMAP, SHOWN)
    assert got.shape == (1, SHOWN, 3)
    assert (got[0, 0] == lookup_table(DEFAULT_COLORMAP)[round(255 * np.sqrt(0.1))]).all()


def test_no_frames_gives_an_empty_result():
    got = colorize(np.zeros((0, 88)), DEFAULT_COLORMAP, SHOWN)
    assert got.shape == (0, SHOWN, 3) and got.dtype == np.uint8


def test_shape_dtype_and_the_input_is_left_alone():
    values = np.random.default_rng(4).random((5, 88))
    before = values.copy()
    got = colorize(values, DEFAULT_COLORMAP, SHOWN)
    assert got.shape == (5, SHOWN, 3) and got.dtype == np.uint8
    assert (values == before).all()
    assert (colorize(values, DEFAULT_COLORMAP, SHOWN) == got).all()


@pytest.mark.parametrize("bad", [np.ones((2, 83)), np.ones(88), np.ones((2, 88)) * -1])
def test_bad_input_is_refused(bad):
    with pytest.raises(ValueError):
        colorize(bad, DEFAULT_COLORMAP, SHOWN)


@pytest.mark.parametrize("name", COLORMAPS)
def test_a_given_peak_is_the_same_as_a_column_that_holds_it(name):
    # the peak of the whole file passed in, for an array that does not hold the note that has it
    values = np.random.default_rng(5).random((6, 84)) * 0.7
    with_column = np.hstack([values, np.full((6, 4), 0.0)])
    with_column[2, 85] = 1.0
    assert (colorize(values, name, 84, peak=1.0) == colorize(with_column, name, 84)).all()


def test_the_default_peak_is_the_largest_value_of_the_input():
    values = np.random.default_rng(6).random((4, 88))
    assert (colorize(values, DEFAULT_COLORMAP, 84, peak=float(values.max())) == colorize(values, DEFAULT_COLORMAP, 84)).all()
    assert (colorize(values, DEFAULT_COLORMAP, 84, peak=None) == colorize(values, DEFAULT_COLORMAP, 84)).all()


def test_a_value_above_a_given_peak_gets_the_last_color_and_a_zero_peak_the_first():
    values = np.array([[0.0, 0.5, 1.0, 2.0]])
    got = colorize(values, DEFAULT_COLORMAP, 4, peak=1.0)
    table = lookup_table(DEFAULT_COLORMAP)
    assert (got[0, 2] == table[255]).all() and (got[0, 3] == table[255]).all() and (got[0, 0] == table[0]).all()
    assert (colorize(values, DEFAULT_COLORMAP, 4, peak=0.0) == table[0]).all()


@pytest.mark.parametrize("bad", [-1.0, float("nan"), float("inf"), True, "1", [1.0]])
def test_a_bad_peak_is_refused(bad):
    with pytest.raises(ValueError):
        colorize(np.ones((2, 84)), DEFAULT_COLORMAP, 84, peak=bad)


def test_a_bad_colormap_name_is_refused():
    with pytest.raises(ValueError, match=re.escape(MESSAGE)):
        colorize(np.ones((2, 88)), INVALID[0], SHOWN)


# --- the beat: half the note strength, half the frame's position in the local peak (feature 024) ---------------------------


def beat_message(frames):
    return f"The beat must be one number from 0 to 1 for each of the {frames} frames."


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_strongest_tile_is_the_middle_colour_at_position_0_and_the_last_at_position_1(name):
    values = notes({0: 100.0, 1: 25.0}, {0: 100.0, 1: 25.0}, {0: 100.0, 1: 25.0})
    got = colorize(values, name, SHOWN, beat=np.array([0.0, 0.5, 1.0]))
    table = lookup_table(name)
    assert (got[0, 0] == table[128]).all()  # 0.5 * 1 + 0.5 * 0 = 0.5 -> row 127.5 -> 128
    assert (got[1, 0] == table[round(0.75 * 255)]).all()  # three quarters of the way along the colormap
    assert (got[2, 0] == table[255]).all()
    # a quarter of the peak (share 0.25, square root 0.5): 0.25, 0.5 and 0.75 of the way
    assert (got[0, 1] == table[round(0.25 * 255)]).all()
    assert (got[1, 1] == table[round(0.5 * 255)]).all()
    assert (got[2, 1] == table[round(0.75 * 255)]).all()


@pytest.mark.parametrize("name", COLORMAPS)
def test_every_tile_is_the_table_entry_of_half_the_square_root_plus_half_the_beat(name):
    rng = np.random.default_rng(31)
    values = rng.random((40, 88)) ** 2
    values[7, 3] = 1.5  # the largest value of the file
    beat = rng.random(40)
    got = colorize(values, name, SHOWN, beat=beat)
    share = np.minimum(values[:, :SHOWN] / values.max(), 1.0)
    rows = np.rint((0.5 * np.sqrt(share) + 0.5 * beat[:, None]) * 255).astype(int)
    assert (got == lookup_table(name)[rows]).all()


def test_a_tile_with_no_energy_has_half_the_beat():
    values = notes({0: 100.0}, {0: 100.0}, {0: 100.0})
    got = colorize(values, DEFAULT_COLORMAP, SHOWN, beat=np.array([0.0, 0.5, 1.0]))
    table = lookup_table(DEFAULT_COLORMAP)
    assert (got[:, 5] == table[[0, round(127.5 * 0.5), 128]]).all()  # rint(127.5 * beat)


def test_the_row_never_falls_when_the_strength_or_the_beat_rises():
    name = DECODABLE[0]  # a colormap whose rows can all be told apart, so the row of a color can be read back
    table = lookup_table(name)
    strengths = np.linspace(0, 100, 51)
    beats = np.linspace(0, 1, 51)
    rows = np.empty((len(beats), len(strengths)), dtype=int)
    for j, strength in enumerate(strengths):
        values = np.zeros((len(beats), 88))
        values[:, 0] = 100.0
        values[:, 1] = strength
        got = colorize(values, name, SHOWN, beat=beats)[:, 1]
        rows[:, j] = [row_index(table, c) for c in got]
    assert (np.diff(rows, axis=0) >= 0).all()  # a higher beat: the same row or later
    assert (np.diff(rows, axis=1) >= 0).all()  # a stronger tile: the same row or later
    assert rows[0, 0] == 0 and rows[-1, -1] == 255


def test_within_a_frame_a_stronger_tile_never_has_an_earlier_row():
    rng = np.random.default_rng(32)
    values = rng.random((20, 88)) ** 3
    beat = rng.random(20)
    got = colorize(values, FIRST, SHOWN, beat=beat)
    expected = np.rint((0.5 * np.sqrt(values[:, :SHOWN] / values.max()) + 0.5 * beat[:, None]) * 255)
    order = np.argsort(values[:, :SHOWN], axis=1)
    rows = np.take_along_axis(expected, order, axis=1)
    assert (np.diff(rows, axis=1) >= 0).all()
    assert got.shape == (20, SHOWN, 3)


@pytest.mark.parametrize("name", COLORMAPS)
def test_with_a_beat_of_zero_no_tile_is_past_the_middle_row(name):
    rng = np.random.default_rng(33)
    values = rng.random((10, 88))
    got = colorize(values, name, SHOWN, beat=np.zeros(10))
    table = lookup_table(name)
    rows = np.rint(0.5 * np.sqrt(values[:, :SHOWN] / values.max()) * 255).astype(int)
    assert rows.max() <= 128
    assert (got == table[rows]).all()


def test_without_a_beat_the_result_is_exactly_what_it_was():
    rng = np.random.default_rng(34)
    values = rng.random((12, 88)) ** 2
    plain = colorize(values, FIRST, SHOWN)
    assert (colorize(values, FIRST, SHOWN, beat=None) == plain).all()
    assert (colorize(values, FIRST, SHOWN, None, None) == plain).all()
    old = lookup_table(FIRST)[np.rint(np.sqrt(np.minimum(values[:, :SHOWN] / values.max(), 1.0)) * 255).astype(int)]
    assert (plain == old).all()


def test_a_beat_does_not_change_its_inputs_and_a_peak_of_zero_still_works():
    values = np.random.default_rng(35).random((6, 88))
    beat = np.linspace(0, 1, 6)
    values0, beat0 = values.copy(), beat.copy()
    colorize(values, FIRST, SHOWN, beat=beat)
    assert (values == values0).all() and (beat == beat0).all()
    got = colorize(np.zeros((3, 88)), FIRST, SHOWN, beat=np.array([0.0, 0.5, 1.0]))
    assert (got[:, 0] == lookup_table(FIRST)[[0, round(127.5 * 0.5), 128]]).all()
    assert colorize(np.zeros((0, 88)), FIRST, SHOWN, beat=np.zeros(0)).shape == (0, SHOWN, 3)


@pytest.mark.parametrize(
    "beat",
    [np.zeros(4), np.zeros(6), np.zeros((5, 1)), np.zeros((5, 2)), np.array([0, 0, np.nan, 0, 0]), np.array([0, 0, np.inf, 0, 0]),
     np.array([0, 0, 1.01, 0, 0]), np.array([0, 0, -0.01, 0, 0]), np.array(["a"] * 5), 0.5, [0.5] * 4, "abc"],
)
def test_a_beat_that_is_not_one_number_from_0_to_1_for_each_frame_is_refused(beat):
    with pytest.raises(ValueError) as error:
        colorize(np.zeros((5, 88)), FIRST, SHOWN, beat=beat)
    assert str(error.value) == beat_message(5)
