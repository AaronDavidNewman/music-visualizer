"""The colormaps and the strength-to-color mapping: ``app/services/colormaps.py``."""

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

SHOWN = 84
MESSAGE = "The colormap must be one of summer, autumn, hot, cool."


def matplotlib_table(name):
    """Matplotlib's own 8-bit table by a second route: sampling the scale at 256 evenly spaced positions."""
    from matplotlib import colormaps

    return colormaps[name](np.linspace(0, 1, 256), bytes=True)[:, :3]


def row_index(table, colour):
    """The table row of an exact colour. Only for tables whose rows are all different (hot and cool)."""
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


def test_constants():
    assert COLORMAPS == ("summer", "autumn", "hot", "cool")
    assert DEFAULT_COLORMAP == "hot"
    assert COLORMAP_STEPS == 256


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_offered_names_are_accepted(name):
    assert check_colormap(name) == name


@pytest.mark.parametrize("bad", ["", "Hot", "HOT", " hot", "hot ", "viridis", "hot_r", "gray", None, 1, b"hot"])
def test_any_other_name_is_refused_with_the_choices(bad):
    with pytest.raises(ValueError) as error:
        check_colormap(bad)
    assert str(error.value) == MESSAGE


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


@pytest.mark.parametrize("name", ["hot", "cool"])
def test_every_row_of_hot_and_cool_is_a_different_colour_so_a_colour_can_be_decoded(name):
    table = lookup_table(name)
    assert len({tuple(row) for row in table.tolist()}) == 256


@pytest.mark.parametrize("name", ["summer", "autumn"])
def test_summer_and_autumn_have_a_few_identical_neighbouring_rows_as_in_matplotlib(name):
    # matplotlib's own 8-bit conversion truncates, so a few neighbouring entries of these two tables are the same colour;
    # the table is matplotlib's, so we keep it as it is and compare colours, not row numbers, where it matters
    table = lookup_table(name)
    distinct = len({tuple(row) for row in table.tolist()})
    assert 200 <= distinct <= 256  # matplotlib's tables, kept as they are (summer 253 and autumn 232 distinct colours)


def test_the_ends_of_the_scales():
    # matplotlib's hot starts at a very dark red, not at pure black, and ends at white
    assert lookup_table("hot")[0].tolist() == [10, 0, 0]
    assert lookup_table("hot")[255].tolist() == [255, 255, 255]
    assert lookup_table("summer")[0].tolist() == [0, 127, 102]
    assert lookup_table("summer")[255].tolist() == [255, 255, 102]
    assert lookup_table("autumn")[0].tolist() == [255, 0, 0]
    assert lookup_table("autumn")[255].tolist() == [255, 255, 0]
    assert lookup_table("cool")[0].tolist() == [0, 255, 255]
    assert lookup_table("cool")[255].tolist() == [255, 0, 255]


def test_an_unknown_name_cannot_make_a_table():
    with pytest.raises(ValueError, match=MESSAGE):
        lookup_table("viridis")


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


@pytest.mark.parametrize("name", ["hot", "cool"])
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
    # an independent route: the table entries are worked out here from the strengths, for all four colormaps
    sweep = np.linspace(0, 100, 2001)
    values = np.zeros((len(sweep), 88))
    values[:, 0] = sweep
    expected = lookup_table(name)[np.rint(np.sqrt(sweep / 100) * 255).astype(int)]
    assert (colorize(values, name, SHOWN)[:, 0] == expected).all()
    assert (colorize(values, name, SHOWN)[-1, 0] == lookup_table(name)[255]).all()


def test_the_scale_is_the_square_root_of_the_share():
    values = notes({0: 100.0, 1: 36.0})
    table = lookup_table("autumn")
    got = colorize(values, "autumn", SHOWN)
    assert (got[0, 1] == table[round(255 * 0.6)]).all()  # sqrt(0.36) = 0.6 -> 153


def test_a_silent_input_is_the_first_colour_everywhere_and_does_not_fail():
    for name in COLORMAPS:
        got = colorize(np.zeros((4, 88)), name, SHOWN)
        assert got.shape == (4, SHOWN, 3)
        assert (got == lookup_table(name)[0]).all()


def test_the_same_strength_has_the_same_colour_wherever_and_whenever_it_sounds():
    values = notes({3: 50.0, 70: 100.0}, {10: 50.0, 70: 100.0}, {83: 50.0, 70: 100.0})
    got = colorize(values, "hot", SHOWN)
    assert (got[0, 3] == got[1, 10]).all() and (got[1, 10] == got[2, 83]).all()


def test_changing_the_other_notes_changes_no_other_tile():
    base = notes({5: 40.0, 60: 100.0})
    other = notes({5: 40.0, 60: 100.0, 20: 70.0, 30: 3.0})  # other notes, the same peak
    a, b = colorize(base, "cool", SHOWN), colorize(other, "cool", SHOWN)
    untouched = [n for n in range(SHOWN) if n not in (20, 30)]
    assert (a[:, untouched] == b[:, untouched]).all()
    assert not (a[:, [20, 30]] == b[:, [20, 30]]).all()


def test_a_steady_value_has_one_colour_in_every_frame():
    values = np.zeros((40, 88))
    values[:, 12] = 30.0
    values[7, 50] = 100.0  # the peak, in one frame only
    got = colorize(values, "summer", SHOWN)
    assert (got[:, 12] == got[0, 12]).all()


def test_the_loudness_of_a_frame_does_not_dim_it():
    # a frame whose notes are all quiet is not brightened or dimmed as a whole: only each note's own strength counts
    loud = notes({0: 100.0, 1: 9.0}, {1: 9.0})
    got = colorize(loud, "hot", SHOWN)
    assert (got[0, 1] == got[1, 1]).all()


def test_the_undrawn_notes_count_for_the_peak_but_are_not_in_the_result():
    values = notes({0: 10.0, 85: 100.0})
    got = colorize(values, "hot", SHOWN)
    assert got.shape == (1, SHOWN, 3)
    assert row_index(lookup_table("hot"), got[0, 0]) == round(255 * np.sqrt(0.1))


def test_no_frames_gives_an_empty_result():
    got = colorize(np.zeros((0, 88)), "hot", SHOWN)
    assert got.shape == (0, SHOWN, 3) and got.dtype == np.uint8


def test_shape_dtype_and_the_input_is_left_alone():
    values = np.random.default_rng(4).random((5, 88))
    before = values.copy()
    got = colorize(values, "hot", SHOWN)
    assert got.shape == (5, SHOWN, 3) and got.dtype == np.uint8
    assert (values == before).all()
    assert (colorize(values, "hot", SHOWN) == got).all()


@pytest.mark.parametrize("bad", [np.ones((2, 83)), np.ones(88), np.ones((2, 88)) * -1])
def test_bad_input_is_refused(bad):
    with pytest.raises(ValueError):
        colorize(bad, "hot", SHOWN)


def test_a_bad_colormap_name_is_refused():
    with pytest.raises(ValueError, match=MESSAGE):
        colorize(np.ones((2, 88)), "viridis", SHOWN)
