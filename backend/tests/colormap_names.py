"""What the tests may assume about the colormaps: only what holds for any list the code offers.

The list in ``app.services.colormaps`` can be changed by hand (names added, removed or renamed). The tests therefore never
name a colormap; they use the names below, which are derived from ``COLORMAPS`` and ``DEFAULT_COLORMAP``. The one thing a
name must always do is to be a valid matplotlib colormap, which ``test_colormaps.py`` checks for every name, together with
the frontend's list matching this one.
"""

from app.services.colormaps import COLORMAPS, DEFAULT_COLORMAP, lookup_table

# the message the server and the library give for a name that is not offered
MESSAGE = f"The colormap must be one of {', '.join(COLORMAPS)}."

# two different offered colormaps for the tests that compare two of them (the same one twice if only one is offered)
FIRST = COLORMAPS[0]
SECOND = COLORMAPS[1] if len(COLORMAPS) > 1 else COLORMAPS[0]


def distinct_rows(name: str) -> int:
    """How many different colors the 256 rows of a table have (matplotlib's own 8-bit conversion can repeat a few)."""
    return len({tuple(row) for row in lookup_table(name).tolist()})


def has_black(name: str) -> bool:
    """Whether a table contains pure black, which a tile hidden by the threshold also is."""
    return bool((lookup_table(name) == 0).all(axis=1).any())


# the colormaps whose 256 rows are all different colors: a color can be decoded back to its row only for these
DECODABLE = [name for name in COLORMAPS if distinct_rows(name) == 256]
# the colormaps without pure black: a black tile is then always a hidden one
WITHOUT_BLACK = [name for name in COLORMAPS if not has_black(name)]
# the colormaps that are both: a tile's row can be decoded and a black tile is a hidden one
TRACEABLE = [name for name in DECODABLE if name in WITHOUT_BLACK]


def not_offered(candidates):
    """The candidates that are not offered (a name that someone adds later drops out of a test's list by itself)."""
    return [c for c in candidates if c not in COLORMAPS]


def invalid_names():
    """Strings that must be refused as colormap names: other spellings of every offered name, and some plain wrong ones."""
    spellings = []
    for name in COLORMAPS:
        spellings += [name.upper(), name.lower(), name.title(), name.swapcase(), f" {name}", f"{name} ", f"{name}_r", f"{name},"]
    return not_offered(["", " ", "no_such_colormap", "1", "hue", "colormap", *spellings])


INVALID = invalid_names()
