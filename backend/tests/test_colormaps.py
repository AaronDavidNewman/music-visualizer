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


def test_a_bad_colormap_name_is_refused():
    with pytest.raises(ValueError, match=re.escape(MESSAGE)):
        colorize(np.ones((2, 88)), INVALID[0], SHOWN)
