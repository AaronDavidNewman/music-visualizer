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
place in the local energy peak (0 to 1, see ``local_peaks``; 0 when no beat is given).

Circles give their points to the cells around them in a **decay step**, every ``decay_rate`` frames (a number from 0.25 to 4 in steps of
0.25, counting the frames from 1; below 1 there are several steps in a frame: 0.25 is four, each a quarter of a frame's worth, which is smoother, above all
at higher frame rates). **How much a circle gives depends on its saturation level**, as a rate per neighbour per frame, one **decay amount** for each
of four levels, each a number from 0.5 to 3: *low* (1 to 8 points, 0.5 by default: 1 every 2 frames), *medium* (more than 8 and up to 20
points, 1 by default), *high* (more than 20 and fewer than 64 points, 2 by default) and *saturated* (64 points, 3 by default), to each
neighbour every frame. A step moves ``decay_rate`` frames' worth, so the average rate is the same
whatever the ``decay_rate`` (the setting says how often it happens, not how much; a step is taken at the times ``decay_rate``, ``2 * decay_rate``,
... measured in frames, and frame ``i`` has the steps that fall in ``(i - 1, i]``: one a frame at 1, two at 0.5, 1 or 2 at 0.75, one every other frame at 2). A circle gives to each of the up to 8 cells around it (the grid
does not wrap); a circle on an edge or in a corner decays as if it had 8 neighbours, so it loses the same total, and what the missing
neighbours would have received is lost. A circle never gives more points than it has, and gives in the same proportions to each neighbour,
so no points appear from nothing. All circles give and receive at the same time, from the points before the step. After the gains and after the
step the points are held between 0 and 64, and after a step a circle with less than a hundredth of a point has none, so that a circle that
has faded is really at 0.

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

MIN_DECAY_RATE = 0.25  # frames between decay steps (below 1: several steps in a frame, which is smoother)
MAX_DECAY_RATE = 4.0  # anything higher blinks
DECAY_RATE_STEP = 0.25
DEFAULT_DECAY_RATE = 1.0

MAX_POINTS = 64
GAINS = (24, 20, 16, 12, 8)  # the points of the five loudest notes of a frame, loudest first
BEAT_BONUS = 8  # the extra points of the five at the top of the local peak (the position is 1); 0 at the bottom
NEIGHBOURS = 8  # the cells around a cell; an edge or corner circle loses as if it had all of them
# the four saturation levels of a circle, by the points it has: low (above 0 and up to 8 points), medium (above 8 and up to 20), high (above 20 and below 64)
# and saturated (64 points); each has a decay amount, the points a circle at that level gives to each neighbour per frame (settings of the picture)
LOW_TOP = 8
MID_TOP = 20
LEVELS = ("low", "medium", "high", "saturated")
MIN_DECAY_AMOUNT = 0.5
MAX_DECAY_AMOUNT = 3.0
DEFAULT_DECAY_AMOUNTS = (0.5, 1.0, 2.0, 3.0)  # 1 every 2 frames, 1, 2 and 3 a frame
NEGLIGIBLE = 0.01  # after a decay step a circle with fewer points than this has none: the tail of the fading would never reach 0
SIZE_POINTS = 24  # the circle is full size from here
COLOR_POINTS = 32  # the circle has the last color of the colormap from here, and from here it gets rings
SMALLEST = 1 / 12  # the smallest circle, at 0 points, as a share of the full radius

DECAY_RATE_MESSAGE = f"The decay rate must be a number from {MIN_DECAY_RATE:g} to {MAX_DECAY_RATE:g} in steps of {DECAY_RATE_STEP:g}."


def check_decay_rate(value) -> float:
    """Return ``value`` as a ``float`` when it is a number from 0.25 to 4 in steps of 0.25 (a bool, a string, a non-finite number or a number
    between two steps is refused)."""
    if (
        isinstance(value, bool)
        or not isinstance(value, numbers.Real)
        or not math.isfinite(value)
        or not MIN_DECAY_RATE <= value <= MAX_DECAY_RATE
        or value % DECAY_RATE_STEP != 0
    ):
        raise ValueError(DECAY_RATE_MESSAGE)
    return float(value)


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


def check_decay_amount(value, level: str = "low") -> float:
    """Return ``value`` as a ``float`` when it is a number from 0.5 to 3 (a bool, a string or a non-finite number is refused); ``level`` names the
    saturation level in the message."""
    if (
        isinstance(value, bool)
        or not isinstance(value, numbers.Real)
        or not math.isfinite(value)
        or not MIN_DECAY_AMOUNT <= value <= MAX_DECAY_AMOUNT
    ):
        raise ValueError(f"The {level} saturation decay must be a number from {MIN_DECAY_AMOUNT:g} to {MAX_DECAY_AMOUNT:g}.")
    return float(value)


def check_decay_amounts(amounts) -> tuple[float, float, float, float]:
    """Return the four decay amounts (low, medium, high, saturated) as a tuple of floats, each checked with :func:`check_decay_amount`."""
    try:
        values = tuple(amounts)
    except TypeError:
        raise ValueError("The decay amounts must be four numbers (low, medium, high, saturated).") from None
    if len(values) != len(LEVELS):
        raise ValueError("The decay amounts must be four numbers (low, medium, high, saturated).")
    return tuple(check_decay_amount(v, level) for v, level in zip(values, LEVELS))  # type: ignore[return-value]


def decay_per_frame(points, amounts=DEFAULT_DECAY_AMOUNTS) -> np.ndarray:
    """The points a circle with ``points`` points gives to each of its neighbours in one frame: 0 with no points, then the decay amount of its
    saturation level: ``amounts[0]`` up to 8 points (by default 0.5, 1 every 2 frames), ``amounts[1]`` above 8 and up to 20 (1), ``amounts[2]``
    above 20 and below 64 (2) and ``amounts[3]`` for a saturated circle (64 points: 3)."""
    low, medium, high, saturated = check_decay_amounts(amounts)
    points = np.asarray(points, dtype=np.float64)
    return np.select(
        [points >= MAX_POINTS, points > MID_TOP, points > LOW_TOP, points > 0.0],
        [saturated, high, medium, low],
        default=0.0,
    )


def decay_step(points, frames: int = 1, amounts=DEFAULT_DECAY_AMOUNTS) -> np.ndarray:
    """One decay step of ``frames`` frames' worth on a ``(7, 12)`` array of points: a new array, the input is not changed.

    A circle with ``p`` points would give ``8 * frames * r`` points away, ``r`` being ``decay_per_frame(p, amounts)`` (the decay amount of its
    saturation level, per neighbour per frame: 0.5, 1, 2 or 3 by default), and gives ``give = min(p, 8 * frames * r)``: ``give / 8`` to each of its neighbours (so ``frames * r`` to each
    when it has enough points), and the rest of the ``give`` is lost where it has no neighbour (an edge or corner circle loses as if it had 8).
    Everything is worked out from the points before the step; the result is held between 0 and 64, and a circle left with less than a
    hundredth of a point has none (the points spread out and halve again and again, and would otherwise never quite reach 0).
    """
    points = np.asarray(points, dtype=np.float64)
    if points.shape != (GRID_ROWS, GRID_COLUMNS):
        raise ValueError(f"The points must be an array of shape {(GRID_ROWS, GRID_COLUMNS)} (got {points.shape}).")
    give = np.minimum(points, NEIGHBOURS * frames * decay_per_frame(points, amounts))
    share = np.zeros((GRID_ROWS + 2, GRID_COLUMNS + 2))  # a border of cells that do not exist, so that nothing wraps around
    share[1:-1, 1:-1] = give / NEIGHBOURS  # what each neighbour gets from the circle
    neighbours = np.zeros_like(points)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                neighbours += share[1 + dy : 1 + dy + GRID_ROWS, 1 + dx : 1 + dx + GRID_COLUMNS]
    after = np.clip(points - give + neighbours, 0.0, MAX_POINTS)
    after[after < NEGLIGIBLE] = 0.0
    return after


def steps_in_frame(index: int, decay_rate: float) -> int:
    """The number of decay steps that fall in frame ``index`` (counting from 0, that is in ``(index, index + 1]`` frames) when a step is taken
    at the times ``decay_rate``, ``2 * decay_rate``, ... (frames): none, one or several. 1 gives one a frame, 0.25 four, 2 one every other frame
    (frames 2, 4, ...), 0.75 one, one and two in turn. Worked out in quarters of a frame, which are exact integers."""
    quarters = int(round(check_decay_rate(decay_rate) / DECAY_RATE_STEP))
    return 4 * (index + 1) // quarters - 4 * index // quarters


def circle_points(
    values,
    beat=None,
    note_layout: str = DEFAULT_NOTE_LAYOUT,
    decay_rate: float = DEFAULT_DECAY_RATE,
    decay_amounts=DEFAULT_DECAY_AMOUNTS,
) -> np.ndarray:
    """The points of the 84 circles after every frame: a float64 array of shape ``(frames, 84)``, in cell order (row by row).

    ``values`` is ``(frames, 84 or more)``, the smoothed note values in note order; ``beat`` is ``None`` or one position from 0 to 1 for
    each frame; ``note_layout`` says which note is in which cell; ``decay_rate`` is the number of frames between decay steps (0.25 to 4 in steps of 0.25), each of which moves that
    many frames' worth of decay, each circle at the rate of its saturation level (``decay_amounts``: the four per-neighbour amounts, low, medium,
    high, saturated). Frame ``i`` (counting from 1) adds its gains, then has the decay steps that fall in ``(i - 1, i]`` when steps are taken at the
    times ``decay_rate``, ``2 * decay_rate``, ... in frames (none, one or several: at 0.25 four), and is recorded.
    """
    note_layout = check_note_layout(note_layout)
    decay_rate = check_decay_rate(decay_rate)
    decay_amounts = check_decay_amounts(decay_amounts)
    gained = arrange_notes(gains(values, beat), note_layout).reshape(-1, GRID_ROWS, GRID_COLUMNS)
    points = np.zeros((GRID_ROWS, GRID_COLUMNS))
    recorded = np.zeros((gained.shape[0], NOTES))
    for index in range(gained.shape[0]):
        points = np.clip(points + gained[index], 0.0, MAX_POINTS)
        for _ in range(steps_in_frame(index, decay_rate)):  # the steps that fall in (index, index + 1] frames
            points = decay_step(points, decay_rate, decay_amounts)  # a step of decay_rate frames' worth: the same average rate whatever the setting
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
