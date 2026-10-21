"""What the middles of the tiles of a blended frame must be, now that a hidden blended tile is the colormap's middle color."""

import numpy as np

from app.services.circles import MIDDLE_COLOR_ROW
from app.services.colormaps import lookup_table


def middle_color(colormap):
    return np.array(lookup_table(colormap)[MIDDLE_COLOR_ROW], dtype=int)


def same_middles(flat, soft, colormap):
    """True where a blended tile's center equals the flat tile's, or where the flat tile is black (hidden by the threshold, or really
    black) and the blended tile is the middle color of the colormap (hidden: it is not drawn). Arrays are (tiles, 3)."""
    flat, soft = np.asarray(flat).astype(int), np.asarray(soft).astype(int)
    equal = (flat == soft).all(axis=-1)
    hidden = (flat == 0).all(axis=-1) & (soft == middle_color(colormap)).all(axis=-1)
    return equal | hidden
