"""The ``concentric`` kind of picture: a circle for each of the 84 drawn notes, made of up to twelve flat concentric rings.

The circles are centered on the tiles of the 12 x 7 grid (note ``n`` at row ``n // 12`` from the top and column ``n % 12``, as
for the tiles). At full size a circle just touches its neighbours in a row: the **full radius** is half the narrower side of a
cell (25 pixels on the 600 x 400 frame, whose cells are 50 pixels wide and 57 or 58 high). A circle has a **step** from 1 to 12
and a radius of ``step / 12`` of the full radius; it is drawn as ``step`` rings, ring ``k`` filling the radii from ``(k - 1) / 12``
to ``k / 12`` of the full radius, from the center out, so a full-size circle looks like twelve concentric circles and a smaller
circle is a full one with its outer rings left off.

* The **step** of a note comes from its volume relative to the other notes of the same frame: ``ceil(12 * sqrt(value / loudest))``
  (the square root is the scale of the tile colors), at least 1, with ``loudest`` the largest value of the frame's 84 notes. The
  loudest note is step 12 and a frame with no sound at all has every circle at step 1.
* The **color** of ring ``k`` is the colormap's table entry at ``rint((k - 1) / 11 * (0.5 + 0.5 * position) * 255)``, with
  ``position`` the frame's position in the local energy peak (0 to 1, see ``local_peaks``; 0 when no beat is given). At position 1
  the twelve rings run through the whole colormap, from its first color to its last; at position 0 they run half way, and ring 12
  is the middle of the colormap. Every circle of a frame has the same ring colors.
* The **background** is the colormap's middle color (table row 128), as for the other pictures of circles.

The geometry is the same in every frame, so it is worked out once (and kept for the frame size): for every pixel its cell and
what its 4 x 4 sub-pixels are, outside the circle or in which ring. A pixel is at most about 1.4 pixels across and a ring is 2 pixels
wide, so a pixel touches at most two of those classes; the picture of a frame is the blend of the two with the share of each, which
is exactly what drawing the rings on a four times larger canvas and averaging it down gives, with smooth edges. A frame is then two
lookups into a table of the 84 x 13 colors of the frame (class 0 the background, class ``k`` the ring's color when the circle's
step reaches ``k`` and the background when it does not) and a blend.

This module knows nothing about the note analysis or the audio: the smoothed note values, the beat positions and the size are
passed in.
"""

from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from .circles import _SAVE_WORKERS, MIDDLE_COLOR_ROW, SUPERSAMPLE
from .colormaps import COLORMAP_STEPS, check_beat, check_colormap, lookup_table
from .image_types import tile_edges

RINGS = 12
GRID_COLUMNS = 12
GRID_ROWS = 7
NOTES = GRID_COLUMNS * GRID_ROWS  # the 84 drawn notes

# a share such as 25 / 144 should give exactly step 5, but 12 * sqrt(25 / 144) can come out as 5.000000000000001
_STEP_NOISE = 1e-9


def _check_values(values) -> np.ndarray:
    """The note values as a float64 ``(frames, columns)`` array of at least 84 columns, finite and 0 or more."""
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] < NOTES:
        raise ValueError(f"At least {NOTES} note values per frame are needed (got shape {values.shape}).")
    if values.size and not np.isfinite(values).all():
        raise ValueError("The note values must be finite numbers.")
    if values.size and values.min() < 0:
        raise ValueError("The note values must be 0 or more.")
    return values


def ring_steps(values) -> np.ndarray:
    """The step (1 to 12) of every drawn note of every frame: an integer array of shape ``(frames, 84)``.

    ``values`` has one row per frame and at least 84 columns (the notes after the 84th are not drawn and do not count). A frame's
    loudest note is step 12 and a note with no energy is step 1; a frame whose notes are all 0 is all step 1. The input is not changed.
    """
    shown = _check_values(values)[:, :NOTES]
    loudest = shown.max(axis=1, initial=0.0)
    share = np.zeros_like(shown)
    np.divide(shown, loudest[:, None], out=share, where=loudest[:, None] > 0)
    steps = np.ceil(RINGS * np.sqrt(np.minimum(share, 1.0)) - _STEP_NOISE)
    return np.clip(steps, 1, RINGS).astype(np.int64)


def ring_colors(colormap: str, beat) -> np.ndarray:
    """The twelve ring colors of every frame: a ``uint8`` array of shape ``(frames, 12, 3)``, ring 1 (the center) first.

    ``beat`` is one position in the local peak, from 0 to 1, for each frame. The table row of ring ``k`` is
    ``rint((k - 1) / 11 * (0.5 + 0.5 * position) * 255)``.
    """
    array = np.asarray(beat)
    positions = check_beat(array, array.shape[0] if array.ndim == 1 else 0)  # refuses anything but a 1-D array of numbers 0..1
    table = lookup_table(check_colormap(colormap))
    ring = np.arange(RINGS) / (RINGS - 1)
    rows = np.rint(ring[None, :] * (0.5 + 0.5 * positions[:, None]) * (COLORMAP_STEPS - 1)).astype(np.intp)
    return table[rows]


def full_radius(width: int, height: int) -> float:
    """The radius at which circles in neighbouring cells just touch: half the narrower side of a cell (25 pixels on 600 x 400)."""
    return min(np.diff(tile_edges(GRID_COLUMNS, width)).min(), np.diff(tile_edges(GRID_ROWS, height)).min()) / 2


@lru_cache(maxsize=4)
def _geometry(width: int, height: int):
    """What never changes between frames: ``(cell, ring_a, ring_b, weight_b)`` flattened, for the frame size.

    For every pixel: the cell (0 to 83) it is in, the two most frequent classes among its 4 x 4 sub-pixels (0 outside the circle, 1 to
    12 the ring) and the share of the second one. The table of a frame is indexed by ``cell * 13 + class``.
    """
    column_edges = tile_edges(GRID_COLUMNS, width)
    row_edges = tile_edges(GRID_ROWS, height)
    radius = full_radius(width, height)
    ring_width = radius / RINGS
    scale = SUPERSAMPLE
    cell = np.zeros((height, width), dtype=np.int32)
    classes = np.zeros((height * scale, width * scale), dtype=np.uint8)
    ys = (np.arange(height * scale) + 0.5) / scale
    xs = (np.arange(width * scale) + 0.5) / scale
    for row in range(GRID_ROWS):
        for column in range(GRID_COLUMNS):
            centre_x = (column_edges[column] + column_edges[column + 1]) / 2
            centre_y = (row_edges[row] + row_edges[row + 1]) / 2
            top, bottom = row_edges[row], row_edges[row + 1]
            left, right = column_edges[column], column_edges[column + 1]
            cell[top:bottom, left:right] = row * GRID_COLUMNS + column
            distance = np.hypot(xs[left * scale : right * scale][None, :] - centre_x, ys[top * scale : bottom * scale][:, None] - centre_y)
            ring = np.ceil(distance / ring_width).astype(np.int64)  # ring k covers ((k - 1) w, k w]
            classes[top * scale : bottom * scale, left * scale : right * scale] = np.where(ring <= RINGS, np.maximum(ring, 1), 0)
    blocks = classes.reshape(height, scale, width, scale).transpose(0, 2, 1, 3).reshape(height, width, scale * scale)
    counts = np.stack([np.count_nonzero(blocks == k, axis=2) for k in range(RINGS + 1)], axis=2)
    order = np.argsort(-counts, axis=2, kind="stable")
    first, second = order[:, :, 0], order[:, :, 1]
    count_first = np.take_along_axis(counts, first[:, :, None], 2)[:, :, 0]
    count_second = np.take_along_axis(counts, second[:, :, None], 2)[:, :, 0]
    if not (count_first + count_second == scale * scale).all():
        raise ValueError("The frame is too small to draw twelve rings: a pixel would touch more than two of them.")
    weight = (count_second / (count_first + count_second)).astype(np.float32)
    base = cell * (RINGS + 1)
    return (
        (base + first).astype(np.int32).ravel(),
        (base + second).astype(np.int32).ravel(),
        weight.ravel()[:, None],
    )


def _frame(steps: np.ndarray, colours: np.ndarray, background: np.ndarray, geometry, width: int, height: int) -> np.ndarray:
    """One picture, a ``uint8`` array ``(height, width, 3)``, from the 84 steps and the 12 ring colors of the frame."""
    first, second, weight = geometry
    table = np.empty((NOTES, RINGS + 1, 3), dtype=np.float32)
    table[:, 0, :] = background
    reaches = steps[:, None] >= np.arange(1, RINGS + 1)[None, :]  # does the circle of this note have ring k?
    table[:, 1:, :] = np.where(reaches[:, :, None], colours[None, :, :], background[None, None, :])
    flat = table.reshape(-1, 3)
    mixed = flat[first] * (1.0 - weight) + flat[second] * weight
    return np.rint(mixed).astype(np.uint8).reshape(height, width, 3)


def write_concentric_frames(values, colormap: str, directory: Path, beat, width: int, height: int) -> None:
    """Save one PNG of ``width`` x ``height`` pixels per row of ``values`` as ``frame_000000.png`` and up.

    ``values`` is ``(frames, 84 or more)``: the smoothed value of every note in every frame (the first 84 are drawn). ``beat`` is
    ``None`` (every frame at position 0) or one position in the local peak, from 0 to 1, for each frame. Everything is checked before
    anything is written.
    """
    colormap = check_colormap(colormap)
    values = _check_values(values)
    frames = values.shape[0]
    positions = np.zeros(frames) if beat is None else check_beat(beat, frames)
    steps = ring_steps(values)
    colours = ring_colors(colormap, positions)
    background = lookup_table(colormap)[MIDDLE_COLOR_ROW].astype(np.float32)
    geometry = _geometry(int(width), int(height))
    directory.mkdir(parents=True, exist_ok=True)

    def write(index: int) -> None:
        picture = _frame(steps[index], colours[index].astype(np.float32), background, geometry, int(width), int(height))
        Image.fromarray(picture, "RGB").save(directory / f"frame_{index:06d}.png", compress_level=1)

    with ThreadPoolExecutor(max_workers=_SAVE_WORKERS) as pool:
        for future in [pool.submit(write, i) for i in range(frames)]:
            future.result()  # raises the first error of a worker, if there was one
