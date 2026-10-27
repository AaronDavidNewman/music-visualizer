"""What the contour is given: a frame's grid of note values after the contour's own directional smoothing."""

import numpy as np

from app.services.contour import directionalSmoothing


def smoothed_flat(values, rows, columns):
    """A frame's grid values (``rows * columns``, first row at the top of the picture) after the smoothing that the contour writer applies,
    in the same order as they came: the writer flips the grid (the first row is drawn at the top), smooths it point by point and draws it."""
    grid = np.array(values, dtype=float).reshape(rows, columns)[::-1].copy()
    for ix in np.ndindex(grid.shape):
        directionalSmoothing(grid, ix[0], ix[1], rows, columns)
    return grid[::-1].reshape(-1)
