"""The kinds of picture a frame can be drawn as, and the blend that makes the ``blended`` kind.

``tiles`` is the picture of flat 21 x 24 pixel tiles. ``blended`` has the same grid of finished tile colors, but the colors
of neighbouring tiles fade into each other across every edge the tiles share: a Gaussian feather (a Gaussian blur of the
sharp edge, kept inside a feather mask) that reaches the *blend width* (a percentage of the tile width) on each side of
the edge, the same distance in pixels in both directions. At the default width the feather mask is about 10 pixels across.

For a pixel on one axis, with ``d`` the distance from the pixel's center to the nearest *inner* tile edge and ``R`` the
reach in pixels: if ``d < R`` the pixel's own tile gets the weight ``(Phi(d / sigma) - Phi(-4)) / (1 - 2 * Phi(-4))`` and
the tile across that edge the rest, where ``sigma = R / 4`` and ``Phi`` is the cumulative distribution of the standard
normal (a Gaussian truncated at the reach and renormalised, so the weights add up to 1 and the fade ends exactly at the
reach); otherwise the pixel has its own tile's color exactly. The horizontal and the vertical weights are worked out
separately, and a pixel is the mix of up to four tiles with the products of the weights (a corner where four tiles
meet is 25% each). Compared with a straight ramp over the same distance, the edge itself stays sharper and the tails are soft. The outer border of the picture has no inner edge and is not blended, and the end of a row
does not blend with the start of the next row, because they are not side by side in the picture.

A third kind, ``contour``, is not tile colors at all: the grid of note values is drawn as a filled contour map. It is drawn by
``contour.py``, because it needs matplotlib's drawing; this module stays pure numpy and only lists its name.

This module knows nothing about the note analysis or the grid of the application: the tile geometry is passed in.
"""

import math
import numbers

import numpy as np

IMAGE_TYPES = ("tiles", "blended", "contour")
DEFAULT_IMAGE_TYPE = "tiles"

# The blend width is a percentage of the tile width: the reach of the fade on each side of an edge.
MIN_BLEND_WIDTH = 10
MAX_BLEND_WIDTH = 25
DEFAULT_BLEND_WIDTH = 25

# The feather is a Gaussian blur cut off at the reach: the reach is this many standard deviations.
FEATHER_SIGMAS = 4


def check_image_type(value) -> str:
    """Return ``value`` when it is exactly one of the offered names (no trimming, no case folding)."""
    if not isinstance(value, str) or value not in IMAGE_TYPES:
        raise ValueError(f"The image type must be one of {', '.join(IMAGE_TYPES)}.")
    return value


def check_blend_width(value) -> float:
    """Return the blend width as a float when it is a number from 10 to 25."""
    if (
        isinstance(value, bool)
        or not isinstance(value, numbers.Real)
        or not math.isfinite(value)
        or not MIN_BLEND_WIDTH <= value <= MAX_BLEND_WIDTH
    ):
        raise ValueError(f"The blend width must be a number from {MIN_BLEND_WIDTH} to {MAX_BLEND_WIDTH}.")
    return float(value)


def feather_weight(distance: np.ndarray, reach: float) -> np.ndarray:
    """The weight of a pixel's own tile at ``distance`` pixels from an edge, on the tile's own side (0 <= distance <= reach).

    A Gaussian-blurred step edge truncated at the reach and renormalised: 0.5 at the edge itself, rising to exactly 1 at
    the reach, with ``sigma = reach / FEATHER_SIGMAS``.
    """
    tail = 0.5 * math.erfc(FEATHER_SIGMAS / math.sqrt(2.0))  # the Gaussian mass beyond the reach on one side
    scaled = FEATHER_SIGMAS * np.atleast_1d(distance).astype(np.float64) / reach / math.sqrt(2.0)
    cumulative = 0.5 * (1.0 + np.array([math.erf(v) for v in scaled]))
    return np.clip((cumulative - tail) / (1.0 - 2.0 * tail), 0.5, 1.0)


def axis_weights(size: int, tile: int, count: int, reach: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """For every pixel along one axis: its own tile, the tile it blends with, and its own tile's weight.

    ``size`` pixels in ``count`` tiles of ``tile`` pixels; ``reach`` is the blend width in pixels. A pixel closer than
    ``reach`` to an *inner* edge (measured from its center) has the neighbour across that edge and the own weight from
    ``feather_weight``; every other pixel is its own neighbour with the weight 1. The first tile has no edge on
    its outer side and the last tile none on its outer side, so nothing is blended there.
    """
    position = np.arange(size) + 0.5
    own = np.arange(size) // tile
    from_start = position - own * tile  # distance to the edge at the start of the tile
    from_end = (own + 1) * tile - position  # distance to the edge at the end of the tile
    neighbour = own.copy()
    weight = np.ones(size)
    near_start = (own > 0) & (from_start < reach)
    near_end = (own < count - 1) & (from_end < reach) & ~near_start
    weight[near_start] = feather_weight(from_start[near_start], reach)
    neighbour[near_start] = own[near_start] - 1
    weight[near_end] = feather_weight(from_end[near_end], reach)
    neighbour[near_end] = own[near_end] + 1
    return own, neighbour, weight


def make_blender(blend_width: float, columns: int, rows: int, tile_width: int, tile_height: int):
    """A function that turns the finished tile colors of a frame into the blended picture.

    The returned function takes ``uint8`` colors of shape ``(rows * columns, 3)`` (tile ``(r, c)`` at index
    ``columns * r + c``) and returns a ``uint8`` picture of shape ``(rows * tile_height, columns * tile_width, 3)``.
    The reach is ``blend_width`` percent of ``tile_width``, in pixels, for both directions. The index and weight arrays
    depend only on the blend width, so they are worked out once here, not for every frame. The arithmetic is done in two
    passes (columns of the tile grid first, then rows) in ``float32``; pixels with the weight 1 are exact.
    """
    width = check_blend_width(blend_width)
    reach = width / 100.0 * tile_width
    col, col_other, col_weight = axis_weights(columns * tile_width, tile_width, columns, reach)
    row, row_other, row_weight = axis_weights(rows * tile_height, tile_height, rows, reach)
    ah = col_weight.astype(np.float32)[None, :, None]
    ah_other = (1.0 - col_weight).astype(np.float32)[None, :, None]
    av = row_weight.astype(np.float32)[:, None, None]
    av_other = (1.0 - row_weight).astype(np.float32)[:, None, None]

    def blend(colors) -> np.ndarray:
        grid = np.asarray(colors).reshape(rows, columns, 3).astype(np.float32)
        across = ah * grid[:, col] + ah_other * grid[:, col_other]  # (rows, width, 3)
        picture = av * across[row] + av_other * across[row_other]  # (height, width, 3)
        return np.rint(picture).astype(np.uint8)

    return blend


def blend_tile_colors(
    colors, blend_width: float, columns: int, rows: int, tile_width: int, tile_height: int
) -> np.ndarray:
    """The blended picture of one frame (see ``make_blender``), for callers that draw a single frame."""
    return make_blender(blend_width, columns, rows, tile_width, tile_height)(colors)
