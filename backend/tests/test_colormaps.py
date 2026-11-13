"""The colormaps: ``app/services/colormaps.py``.

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
    lookup_table,
)

from .colormap_names import INVALID, MESSAGE, distinct_rows

FRONTEND_VALIDATION = Path(__file__).resolve().parents[2] / "frontend" / "src" / "utilities" / "validation.ts"


def matplotlib_table(name):
    """Matplotlib's own 8-bit table by a second route: sampling the scale at 256 evenly spaced positions."""
    from matplotlib import colormaps

    return colormaps[name](np.linspace(0, 1, 256), bytes=True)[:, :3]


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


# --- the beat: half the note strength, half the frame's position in the local peak (feature 024) ---------------------------


