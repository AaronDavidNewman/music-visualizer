"""The ``decay`` kind of picture: 84 circles on the 12 x 7 grid of ``concentric``, each a disc that keeps points from frame to frame.

Every circle has **points** from 0 to 64, 0 before the first frame. The points decide the disc:

* its **size**: one twelfth of the full radius at 0 points (the smallest circle of ``concentric``), the full radius at 24 points or
  more, linear in between;
* its **color**: the colormap's first color at 0 points, its last color at 32 points, linear in between; the disc is flat;
* its **rings**, from 32 to 64 points: the disc is made of the twelve concentric rings of ``concentric`` (ring ``k`` from the center
  out between ``(k - 1) / 12`` and ``k / 12`` of the full radius) and the rings run from the last color of the colormap at the center
  to a color further and further back, so that at 64 points ring 1 is the last color and ring 12 the first: ring ``k`` is at
  ``b - s * (k - 1) / 11`` of the way along the colormap, with ``b = min(points, 32) / 32`` and ``s = (min(points, 64) - 32) / 32``
  clipped to 0 or more. At 32 points (``s = 0``) every ring has the last color, so the disc is flat; as the points fall from 64 the
  outer rings come back to the last color first, which is what shows the decay.

In every frame the five loudest notes (the smoothed values of the 84 drawn notes; ties go to the lower note, a note with value 0 does
not count) **gain** 24, 20, 16, 12 and 8 points in order of loudness, plus ``8 * position`` points each, with ``position`` the frame's
place in the local energy peak (0 to 1, see ``local_peaks``; 0 when no beat is given). Every ``decay_rate`` frames (a whole number from
1 to 10, counting the frames from 1) there is a **decay step**: every circle gives 2 points to each of the cells around it (the up to
8 of them on the grid, which does not wrap) and loses 16 points in all, the part of the 16 that has no neighbour to go to being lost, so
an edge circle sends 10 and loses 6 more and a corner circle sends 6 and loses 10 more. A circle with fewer than 16 points gives only
what it has, in the same proportions, so no points appear from nothing. All circles give and receive at the same time, from the
points before the step. After the gains and after the step the points are held between 0 and 64, and after a step a circle with less than a hundredth of a
point has none, so that a circle that has faded is really at 0.

The points of all frames are worked out first, in one pass over the frames (``circle_points``): the gains are ranked in note order,
put in the cells of the note layout with ``arrange_notes``, and the neighbours are the cells around a cell, whatever notes they hold.
Drawing is then independent for every frame: the cell of every pixel, its distance from the center of its cell, its ring and how much
of the ring on either side of it reaches into it are worked out once (and kept for the frame size), and a pixel is the blend of the
background and the color of its ring with the coverage ``clip(radius - distance + 0.5, 0, 1)``, a smooth edge one pixel wide for any
radius, the edges between the rings being smooth in the same way.

This module knows nothing about the note analysis or the audio: the smoothed note values, the beat positions and the size are passed in.
"""

import math
import numbers
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from .circles import _SAVE_WORKERS, MIDDLE_COLOR_ROW
from .colormaps import COLORMAP_STEPS, check_beat, check_colormap, lookup_table
from .concentric import GRID_COLUMNS, GRID_ROWS, NOTES, RINGS, _check_values, full_radius
from .image_types import tile_edges
from .note_layout import DEFAULT_NOTE_LAYOUT, arrange_notes, check_note_layout

MIN_DECAY_RATE = 1
MAX_DECAY_RATE = 10
DEFAULT_DECAY_RATE = 5

MAX_POINTS = 64
GAINS = (24, 20, 16, 12, 8)  # the points of the five loudest notes of a frame, loudest first
BEAT_BONUS = 8  # the extra points of the five at the top of the local peak (the position is 1); 0 at the bottom
GIVE = 2  # the points a circle gives to each neighbour in a decay step
LOSS = 16  # the points a circle loses in all in a decay step
NEGLIGIBLE = 0.01  # after a decay step a circle with fewer points than this has none: the tail of the fading would never reach 0
SIZE_POINTS = 24  # the circle is full size from here
COLOR_POINTS = 32  # the circle has the last color of the colormap from here, and from here it gets rings
SMALLEST = 1 / 12  # the smallest circle, at 0 points, as a share of the full radius

_RATE_MESSAGE = f"The decay rate must be a whole number from {MIN_DECAY_RATE} to {MAX_DECAY_RATE}."


def check_decay_rate(value) -> int:
    """Return ``value`` as an ``int`` when it is a whole number from 1 to 10 (a bool, a string or a fraction is refused)."""
    if (
        isinstance(value, bool)
        or not isinstance(value, numbers.Real)
        or not math.isfinite(value)
        or value != int(value)
        or not MIN_DECAY_RATE <= value <= MAX_DECAY_RATE
    ):
        raise ValueError(_RATE_MESSAGE)
    return int(value)


def gains(values, beat=None) -> np.ndarray:
    """The points every note gains in every frame, in note order: a float64 array of shape ``(frames, 84)``.

    The five notes with the highest value of a frame (ties to the lower note; a note with value 0 does not count) get 24, 20, 16, 12
    and 8 points in that order plus ``8 * position``; every other note gets 0. ``beat`` is ``None`` (position 0) or one position from 0
    to 1 for each frame. The input is not changed.
    """
    shown = _check_values(values)[:, :NOTES]
    frames = shown.shape[0]
    positions = np.zeros(frames) if beat is None else check_beat(beat, frames)
    order = np.argsort(-shown, axis=1, kind="stable")[:, : len(GAINS)]
    ranked = np.take_along_axis(shown, order, axis=1)
    gained = np.asarray(GAINS, dtype=np.float64)[None, :] + BEAT_BONUS * positions[:, None]
    gained = np.where(ranked > 0, gained, 0.0)
    result = np.zeros_like(shown)
    np.put_along_axis(result, order, gained, axis=1)
    return result


def decay_step(points) -> np.ndarray:
    """One decay step on a ``(7, 12)`` array of points: a new array, the input is not changed.

    A circle with ``p`` points gives ``min(p, 16)`` points away: ``2 * share`` to each of its neighbours, with ``share = give / 16``
    (so 2 points to each when it has 16 or more), and the rest of the ``give`` is lost where it has no neighbour. Everything is worked
    out from the points before the step; the result is held between 0 and 64, and a circle left with less than a hundredth of a point
    has none (the points spread out and halve again and again, and would otherwise never quite reach 0).
    """
    points = np.asarray(points, dtype=np.float64)
    if points.shape != (GRID_ROWS, GRID_COLUMNS):
        raise ValueError(f"The points must be an array of shape {(GRID_ROWS, GRID_COLUMNS)} (got {points.shape}).")
    give = np.minimum(points, LOSS)
    share = np.zeros((GRID_ROWS + 2, GRID_COLUMNS + 2))  # a border of cells that do not exist, so that nothing wraps around
    share[1:-1, 1:-1] = give / LOSS
    neighbours = np.zeros_like(points)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                neighbours += share[1 + dy : 1 + dy + GRID_ROWS, 1 + dx : 1 + dx + GRID_COLUMNS]
    after = np.clip(points - give + GIVE * neighbours, 0.0, MAX_POINTS)
    after[after < NEGLIGIBLE] = 0.0
    return after


def circle_points(values, beat=None, note_layout: str = DEFAULT_NOTE_LAYOUT, decay_rate: int = DEFAULT_DECAY_RATE) -> np.ndarray:
    """The points of the 84 circles after every frame: a float64 array of shape ``(frames, 84)``, in cell order (row by row).

    ``values`` is ``(frames, 84 or more)``, the smoothed note values in note order; ``beat`` is ``None`` or one position from 0 to 1 for
    each frame; ``note_layout`` says which note is in which cell; ``decay_rate`` is the number of frames between decay steps. Frame ``i``
    (counting from 1) adds its gains, then has a decay step when ``i`` is a multiple of ``decay_rate``, and is recorded.
    """
    note_layout = check_note_layout(note_layout)
    decay_rate = check_decay_rate(decay_rate)
    gained = arrange_notes(gains(values, beat), note_layout).reshape(-1, GRID_ROWS, GRID_COLUMNS)
    points = np.zeros((GRID_ROWS, GRID_COLUMNS))
    recorded = np.zeros((gained.shape[0], NOTES))
    for index in range(gained.shape[0]):
        points = np.clip(points + gained[index], 0.0, MAX_POINTS)
        if (index + 1) % decay_rate == 0:
            points = decay_step(points)
        recorded[index] = points.reshape(NOTES)
    return recorded


def _check_points(points) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    if points.ndim < 1 or points.shape[-1] != NOTES:
        raise ValueError(f"The points must have {NOTES} circles in their last dimension (got shape {points.shape}).")
    if points.size and (not np.isfinite(points).all() or points.min() < 0 or points.max() > MAX_POINTS):
        raise ValueError(f"The points must be numbers from 0 to {MAX_POINTS}.")
    return points


def circle_radii(points, width: int = 600, height: int = 400) -> np.ndarray:
    """The radius in pixels of circles with ``points`` points: 1/12 of the full radius at 0, the full radius from 24 points on."""
    points = np.asarray(points, dtype=np.float64)
    size = np.minimum(points, SIZE_POINTS) / SIZE_POINTS
    return full_radius(width, height) * (SMALLEST + (1.0 - SMALLEST) * size)


def ring_positions(points) -> np.ndarray:
    """Where on the colormap (0 to 1) each of the twelve rings of circles with ``points`` points is: shape of ``points`` plus 12.

    Ring ``k`` (1 at the center) is at ``b - s * (k - 1) / 11``, with ``b = min(points, 32) / 32`` and ``s = (points - 32) / 32`` held
    between 0 and 1: every ring at ``b`` up to 32 points, ring 1 at the last color and ring 12 at the first at 64 points.
    """
    points = np.asarray(points, dtype=np.float64)
    base = np.minimum(points, COLOR_POINTS) / COLOR_POINTS
    spread = np.clip((points - COLOR_POINTS) / (MAX_POINTS - COLOR_POINTS), 0.0, 1.0)
    ring = np.arange(RINGS) / (RINGS - 1)
    return base[..., None] - spread[..., None] * ring


def ring_colors(points, colormap: str) -> np.ndarray:
    """The colors of the twelve rings of circles with ``points`` points: ``uint8`` of the shape of ``points`` plus ``(12, 3)``, ring 1 first."""
    table = lookup_table(check_colormap(colormap))
    return table[np.rint(ring_positions(points) * (COLORMAP_STEPS - 1)).astype(np.intp)]


def circle_colors(points, colormap: str) -> np.ndarray:
    """The color at the center of circles with ``points`` points: ``uint8`` of the shape of ``points`` plus 3, table entry ``rint(min(p, 32) / 32 * 255)``.

    It is ring 1, the one color of a flat circle (up to 32 points) and the last color from 32 points on.
    """
    return ring_colors(points, colormap)[..., 0, :]


@lru_cache(maxsize=4)
def _geometry(width: int, height: int):
    """What never changes between frames: ``(cell, distance, rects, weights)`` for the frame size.

    ``cell`` (0 to 83) is the cell of every pixel (flattened) and ``distance`` (``(height, width)``) its distance from the center of that
    cell; ``rects`` are the row and column slices of the 84 cells. For the rings: ``weights[c]`` is, for the pixels of cell ``c``
    (``(rows * columns, 12)``), the share of each ring in the pixel: the ring it is in (ring ``k`` covers ``((k - 1) w, k w]``, ``w`` a twelfth
    of the full radius, and the outside of the full circle counts with the last ring) less the shares of the ring on the inside and on the
    outside of it that reach into the pixel (0.5 at the edge between two rings, falling to 0 half a pixel away), 0 where there is no such
    ring. A pixel's ring color is then ``weights @ the 12 ring colors``.
    """
    column_edges = tile_edges(GRID_COLUMNS, width)
    row_edges = tile_edges(GRID_ROWS, height)
    cell = np.zeros((height, width), dtype=np.int32)
    distance = np.zeros((height, width), dtype=np.float32)
    rects = []
    xs = np.arange(width) + 0.5
    ys = np.arange(height) + 0.5
    for row in range(GRID_ROWS):
        for column in range(GRID_COLUMNS):
            top, bottom = row_edges[row], row_edges[row + 1]
            left, right = column_edges[column], column_edges[column + 1]
            centre_x = (left + right) / 2
            centre_y = (top + bottom) / 2
            cell[top:bottom, left:right] = row * GRID_COLUMNS + column
            distance[top:bottom, left:right] = np.hypot(xs[None, left:right] - centre_x, ys[top:bottom, None] - centre_y)
            rects.append((slice(top, bottom), slice(left, right)))
    ring_width = full_radius(width, height) / RINGS
    ring = np.clip(np.ceil(distance / ring_width) - 1, 0, RINGS - 1).astype(np.int32)
    inside = distance - ring * ring_width  # how far the pixel is past the inner edge of its ring
    before = np.where(ring > 0, np.clip(0.5 - inside, 0.0, 1.0), 0.0).astype(np.float32)
    after = np.where(ring < RINGS - 1, np.clip(0.5 - (ring_width - inside), 0.0, 1.0), 0.0).astype(np.float32)
    own = 1.0 - before - after
    weights = []
    for rows, columns in rects:
        matrix = np.zeros((rows.stop - rows.start, columns.stop - columns.start, RINGS), dtype=np.float32)
        r = ring[rows, columns]
        index = np.indices(r.shape)
        np.add.at(matrix, (index[0], index[1], r), own[rows, columns])
        np.add.at(matrix, (index[0], index[1], np.maximum(r - 1, 0)), before[rows, columns])
        np.add.at(matrix, (index[0], index[1], np.minimum(r + 1, RINGS - 1)), after[rows, columns])
        weights.append(matrix.reshape(-1, RINGS))
    return cell.ravel(), distance, rects, weights


def _frame(points: np.ndarray, colormap: str, background: np.ndarray, geometry, width: int, height: int) -> np.ndarray:
    """One picture, a ``uint8`` array ``(height, width, 3)``, from the 84 points of the frame.

    Every circle is first drawn flat in its center color, which is the whole picture of a circle with up to 32 points (all its rings are the
    same color); the circles with more points are then drawn again, cell by cell, with their rings.
    """
    cell, distance, rects, weights = geometry
    radius = circle_radii(points, width, height).astype(np.float32)
    colours = ring_colors(points, colormap).astype(np.float32)  # (84, 12, 3)
    coverage = np.clip(radius[cell] - distance.ravel() + 0.5, 0.0, 1.0)
    mixed = np.take(np.ascontiguousarray(colours[:, 0, :]), cell, axis=0)
    mixed -= background
    mixed *= coverage[:, None]
    mixed += background
    picture = mixed.reshape(height, width, 3)
    coverage = coverage.reshape(height, width, 1)
    for index in np.flatnonzero(points > COLOR_POINTS):
        rows, columns = rects[index]
        colour = (weights[index] @ colours[index]).reshape(rows.stop - rows.start, columns.stop - columns.start, 3)  # (12, 3) ring colors
        picture[rows, columns] = background + (colour - background) * coverage[rows, columns]
    return np.rint(picture).astype(np.uint8)


def write_decay_frames(points, colormap: str, directory: Path, width: int, height: int) -> None:
    """Save one PNG of ``width`` x ``height`` pixels per row of ``points`` as ``frame_000000.png`` and up.

    ``points`` is ``(frames, 84)``: the points of every circle in every frame, in cell order (see ``circle_points``). Everything is
    checked before anything is written.
    """
    colormap = check_colormap(colormap)
    points = _check_points(points)
    if points.ndim != 2:
        raise ValueError(f"The points must be a (frames, {NOTES}) array (got shape {points.shape}).")
    background = lookup_table(colormap)[MIDDLE_COLOR_ROW].astype(np.float32)
    geometry = _geometry(int(width), int(height))
    directory.mkdir(parents=True, exist_ok=True)

    def write(index: int) -> None:
        picture = _frame(points[index], colormap, background, geometry, int(width), int(height))
        Image.fromarray(picture, "RGB").save(directory / f"frame_{index:06d}.png", compress_level=1)

    with ThreadPoolExecutor(max_workers=_SAVE_WORKERS) as pool:
        for future in [pool.submit(write, i) for i in range(points.shape[0])]:
            future.result()  # raises the first error of a worker, if there was one
