"""The ``chromatic-wireframe`` kind of picture (feature 039): the 12 letters of Chromatic Decay as a ridge plot in three dimensions.

The data is that of ``chromatic_decay`` and is not changed here: for every frame, the points of the 12 letters (``circle_points``) and the radius that the circle of
a letter has for its points (``circle_radii``). Only the drawing differs.

**One line for each frame, one function across the whole width.** The 12 letters are spread evenly over the width of the plot (the picture less ``MARGIN`` pixels on each
side), in the order of the letters (A first), each starting at ``start = b x xmax`` where ``xmax`` is the width of a letter's share (``band_width``). Every letter
adds a sine to **every** point ``u`` of the line (not only to the points of its own share), so the line is one smooth function and not twelve pieces. The sine of the
letter ``b`` with ``p`` points has **its own frequency, amplitude and phase**:

- the **frequency** comes from the points: the angle makes ``p / (64 / 4)`` turns across the whole width, so a letter with 0 points makes none and a fully charged one
  (64 points) makes 4 (``CYCLES_AT_FULL_POINTS``); the wave is the **sine squared** of the angle, so it has two humps for each turn and is never negative (the letters can only
  add to each other, not cancel);
- the **amplitude** is the radius of its circle as a share of the full radius (a twelfth at 0 points, 1 from 24);
- the **phase** is that of its start: ``2 pi x start / width of the plot``, so a letter a quarter of the way along the axis adds pi/2.

The sum of the 12 waves, divided by 12, is between 0 and 1 (``S``). The height of the line above its base is ``A`` (two fifths of the picture's height) times
``(S - FLOOR_SHARE) / (CEILING_SHARE - FLOOR_SHARE)`` held between 0 and 1: a **stretch of the contrast**, because 12 loud letters never peak together, so real music only uses about 0.28 to 0.78 of
the range and the plot would leave a fifth of the room at the top empty (the floor of loud music, about 0.28, is the sum of the means of its waves: louder is higher). A frame
that is quiet (``S`` at or under the floor, for instance a silent one) is a flat line on the base and nothing leaves the picture. Waves of different frequencies,
phases and amplitudes interfere in a way that need not mean anything musically (``line_angles``, ``line_heights``).

**The view.** The picture shows the line of the current frame in front, with its base at the bottom margin (the line is never below its base), and the lines of the
earlier frames behind it, each ``step`` pixels higher and smaller (to 75 % at the oldest, about the middle of the width), **as many as fill the picture up to the top
margin**: as many as fit without the highest height of the oldest leaving it (``line_geometry``, ``project_line``). A nearer line hides the lines behind it (the area below every line is filled with the background before it is drawn), and the
lines are drawn from the back to the front. The background is **black** (``BACKGROUND_COLOR``), whatever the colormap, so the lines are seen against it.

**The color.** A line is one color along its whole length, taken from the colormap by the place of its frame in the beat (the local peak of ``local_peaks``,
stretched over the range of the file as for the rings of Peak Rings): the **last** color at the top of a peak and the first at the bottom of the beat (the reverse of
Peak Rings). The color belongs to the frame, so it moves back with it (``line_colors``).

This module knows nothing about the audio, the job or the page: the points, the beat, the colormap and the picture size are passed in.
"""

import math
import numbers
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .chromatic_decay import LETTERS, MAX_POINTS, _check_beat, _check_points, beat_distances, circle_radii, ring_geometry
from .circles import _SAVE_WORKERS
from .colormaps import COLORMAP_STEPS, check_colormap, lookup_table

MARGIN = 10  # pixels between the plot and every edge of the picture
AMPLITUDE_SHARE = 2 / 5  # the highest height of a line above its base (it is never below it: the waves are sine squared), as a share of the picture's height
REFERENCE_HEIGHT = 400  # the height that the step and the line width are for
STEP = 4  # pixels from a line to the one behind it, on a picture 400 high (scaled with the height)
DEPTH_SHRINK = 0.25  # how much smaller the oldest line is than the front one
FLOOR_SHARE = 0.05  # the sum of the waves (as a share of the most it can be, 12 x 1) at or under this is height 0 (one steady note makes 0.04 to 0.12, so it must stay low or a solo line goes flat)
CEILING_SHARE = 0.8  # and at or over this it is the highest height (A): real music tops out at about 0.78 (and goes down to about 0.28), so the stretch fills the room without cutting it
CYCLES_AT_FULL_POINTS = 4  # the turns that the sine of a letter with the most points (64) makes across the whole width
SAMPLES_PER_PIXEL = 2  # vertices of the polyline for every pixel along the plot
LINE_WIDTH = 1.5  # pixels, on a picture 400 high (scaled with the height)
SUPERSAMPLE = 3  # the picture is drawn this many times larger and reduced, which smooths the lines
BACKGROUND_COLOR = (0, 0, 0)  # the picture is on black, whatever the colormap (the other types use the colormap's middle color)
SIZE_MESSAGE = "The picture size must be two whole numbers, large enough for one line."


def _check_size(width, height) -> tuple[int, int]:
    for size in (width, height):
        if isinstance(size, (bool, np.bool_)) or not isinstance(size, numbers.Integral) or size < 1:
            raise ValueError(SIZE_MESSAGE)
    return int(width), int(height)


def _check_row(points_row) -> np.ndarray:
    try:
        row = np.asarray(points_row, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError(f"The points of a frame must be {LETTERS} numbers from 0 to {MAX_POINTS}.") from None
    if row.shape != (LETTERS,) or not np.isfinite(row).all() or row.min() < 0 or row.max() > MAX_POINTS:
        raise ValueError(f"The points of a frame must be {LETTERS} numbers from 0 to {MAX_POINTS}.")
    return row


def amplitude(height: int) -> float:
    """The highest swing of a line, in pixels: a fifth of the picture's height."""
    return AMPLITUDE_SHARE * height


def band_width(width: int) -> float:
    """``xmax``: the width in pixels of the band of one letter, a twelfth of the plot (the picture less the margins)."""
    return (width - 2 * MARGIN) / LETTERS


def plot_width(width: int) -> float:
    """The width in pixels of the plot: the picture less the margins."""
    return width - 2 * MARGIN


def _samples(width: int) -> int:
    return math.ceil(SAMPLES_PER_PIXEL * plot_width(width)) + 1


def line_angles(points_row, width: int) -> np.ndarray:
    """The angle of the sine of every letter at every sample of the line: ``(12, n)``.

    The sample ``i`` is at ``u`` pixels from the left of the plot (0 to the width of the plot, every half pixel) and the letter ``b`` starts at ``start = b x xmax``:
    ``2 pi x (p / (64 / 4)) x u / width of the plot + 2 pi x start / width of the plot``, with ``p`` the points of the letter. The first term is the **frequency**, from
    the points: ``p / 16`` turns across the whole width (none at 0 points, 4 at 64); the second is the **phase of the start** (pi/2 for a quarter of the way along).
    """
    row = _check_row(points_row)
    span = plot_width(width)
    xmax = band_width(width)
    count = _samples(width)
    u = np.arange(count) * span / (count - 1)
    start = np.arange(LETTERS) * xmax
    cycles = row / (MAX_POINTS / CYCLES_AT_FULL_POINTS)
    return 2 * math.pi * cycles[:, None] * (u[None, :] / span) + (2 * math.pi * start / span)[:, None]


def line_sums(points_row, width: int, height: int) -> np.ndarray:
    """The sum of the 12 waves at every sample of the line, divided by 12: ``(n,)`` from 0 to 1 (``S``).

    The wave of a letter is ``(radius / full radius) x sin(angle) squared`` (:func:`line_angles`), where the radius is that of the circle of Chromatic Decay for the
    letter's points on a picture of this size (a twelfth of the full radius at 0 points, the full radius from 24).
    """
    width, height = _check_size(width, height)
    row = _check_row(points_row)
    angles = line_angles(row, width)
    ratio = circle_radii(row, width, height) / ring_geometry(width, height)[1]
    return (ratio[:, None] * np.sin(angles) ** 2).sum(axis=0) / LETTERS


def line_heights(points_row, width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    """The line of one frame: ``(X, Z)``, two float arrays of ``n`` values in pixels.

    ``X`` is the position across the picture (``MARGIN`` to ``width - MARGIN``, every half pixel) and ``Z`` the height above the base of the line, from 0 to ``A``
    (two fifths of the picture's height): the sum of the waves ``S`` (:func:`line_sums`) stretched,
    ``Z = A x clip((S - FLOOR_SHARE) / (CEILING_SHARE - FLOOR_SHARE), 0, 1)``.
    """
    total = line_sums(points_row, width, height)
    x = MARGIN + np.arange(total.size) * plot_width(width) / (total.size - 1)
    z = amplitude(height) * np.clip((total - FLOOR_SHARE) / (CEILING_SHARE - FLOOR_SHARE), 0.0, 1.0)
    return x, z


def line_geometry(width: int, height: int) -> tuple[int, float, float]:
    """The view: ``(lines, base, step)``, the number of lines that fit, the base of the front line (its height 0, in pixels from the top) and the step between lines.

    A line is never below its base (``Z`` is 0 to ``A``), so the front line's base is at the bottom margin, ``height - MARGIN``. Every older line is ``step``
    (``4 x height / 400``) higher and smaller (``1 - DEPTH_SHRINK`` at the oldest). The lines that fit are as many as leave the highest height of the oldest,
    ``base - (lines - 1) x step - A x (1 - DEPTH_SHRINK)``, not above ``MARGIN``: the stack fills the picture from the bottom margin to the top one. (The highest height
    of the line at depth ``k`` is ``base - k x step - A x (1 - DEPTH_SHRINK x k / (lines - 1))``, which goes down as ``k`` goes up, so the oldest line is the one that decides.)
    A picture that is too small for the front line's highest height, ``base - A``, to be inside the margin is refused with ``ValueError``.
    """
    width, height = _check_size(width, height)
    swing = amplitude(height)
    base = height - MARGIN
    step = STEP * height / REFERENCE_HEIGHT
    if base - swing < MARGIN:
        raise ValueError(SIZE_MESSAGE)
    return int((base - MARGIN - swing * (1 - DEPTH_SHRINK)) // step) + 1, base, step


def project_line(X, Z, depth, lines: int, width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    """The screen positions ``(x, y)`` (pixels, ``y`` from the top) of the line ``(X, Z)`` at ``depth`` frames behind the front one (0 is the front).

    The line is smaller by ``1 - DEPTH_SHRINK x depth / (lines - 1)`` about the middle of the width (both ``X`` and the heights; 1 when there is a single line) and its
    base is ``depth x step`` higher.
    """
    width, height = _check_size(width, height)
    if isinstance(lines, (bool, np.bool_)) or not isinstance(lines, numbers.Integral) or lines < 1:
        raise ValueError("The number of lines must be a whole number of at least 1.")
    if isinstance(depth, (bool, np.bool_)) or not isinstance(depth, numbers.Integral) or not 0 <= depth < lines:
        raise ValueError(f"The depth must be a whole number from 0 to {lines - 1}.")
    _, base, step = line_geometry(width, height)
    scale = 1.0 - DEPTH_SHRINK * depth / (lines - 1) if lines > 1 else 1.0
    X = np.asarray(X, dtype=np.float64)
    Z = np.asarray(Z, dtype=np.float64)
    return width / 2 + (X - width / 2) * scale, base - depth * step - Z * scale


def line_colors(beat, colormap: str, frames: int | None = None) -> np.ndarray:
    """The color of the line of every frame: a ``uint8`` array ``(frames, 3)``, the colormap's table row ``rint((1 - distance) x 255)``.

    ``beat`` is one position in the local peak from 0 to 1 for each frame, and the distance is that of ``chromatic_decay.beat_distances`` (stretched over the range
    of the beat of the file; a frame outside every peak is 1), so the top of a peak has the **last** row and the bottom of the beat the first. ``None`` has no beat: every
    line has the first row, for ``frames`` frames (required then).
    """
    table = lookup_table(check_colormap(colormap))
    if beat is None:
        if frames is None:
            raise ValueError("The number of frames is needed when there is no beat.")
        return np.repeat(table[:1], int(frames), axis=0)
    distance = beat_distances(beat)
    return table[np.rint((1.0 - distance) * (COLORMAP_STEPS - 1)).astype(np.intp)]


def _stroke_width(height: int) -> int:
    """The width of a line on the enlarged canvas, in its pixels: 1.5 pixels of the picture, scaled with the height, and never under one pixel of the picture."""
    return max(SUPERSAMPLE, int(LINE_WIDTH * SUPERSAMPLE * height / REFERENCE_HEIGHT + 0.5))


def _frame(heights: np.ndarray, colors: np.ndarray, t: int, X: np.ndarray, background, width: int, height: int) -> np.ndarray:
    """One picture, a ``uint8`` array ``(height, width, 3)``: the lines of frames ``t``, ``t - 1``, ... (as many as fit) drawn from the oldest to the newest.

    ``heights`` is ``(frames, 12 x n)``, the ``Z`` of every frame's line (``line_heights``), ``colors`` ``(frames, 3)`` the line colors and ``X`` the positions across
    the picture that all lines share. The picture is drawn ``SUPERSAMPLE`` times larger and reduced by an exact box filter, which smooths the lines.
    """
    lines, _, _ = line_geometry(width, height)
    canvas = Image.new("RGB", (width * SUPERSAMPLE, height * SUPERSAMPLE), tuple(int(v) for v in background))
    draw = ImageDraw.Draw(canvas)
    stroke = _stroke_width(height)
    fill = tuple(int(v) for v in background)
    for depth in range(min(lines - 1, t), -1, -1):
        x, y = project_line(X, heights[t - depth], depth, lines, width, height)
        points = list(zip((x * SUPERSAMPLE).tolist(), (y * SUPERSAMPLE).tolist()))
        bottom = height * SUPERSAMPLE
        draw.polygon(points + [(points[-1][0], bottom), (points[0][0], bottom)], fill=fill)  # hides what is behind: everything below the line
        draw.line(points, fill=tuple(int(v) for v in colors[t - depth]), width=stroke)
    return np.asarray(canvas.reduce(SUPERSAMPLE), dtype=np.uint8)


def write_wireframe_frames(points, colormap: str, directory: Path, width: int, height: int, beat=None) -> None:
    """Save one PNG of ``width`` x ``height`` pixels per row of ``points`` as ``frame_000000.png`` and up.

    ``points`` is ``(frames, 12)``: the points of every letter in every frame, in letter order (``chromatic_decay.circle_points``). ``beat`` is ``None`` (every line has
    the first color) or one position in the local peak from 0 to 1 for each frame (:func:`line_colors`). Everything is checked before anything is written.
    """
    colormap = check_colormap(colormap)
    points = _check_points(points)
    if beat is not None:
        beat = _check_beat(beat)
        if beat.shape[0] != points.shape[0]:
            raise ValueError(f"The beat must be one number from 0 to 1 for each of the {points.shape[0]} frames.")
    width, height = _check_size(width, height)
    line_geometry(width, height)  # refuses a picture that is too small for one line
    colors = line_colors(beat, colormap, frames=points.shape[0])
    background = np.array(BACKGROUND_COLOR, dtype=np.uint8)
    X = line_heights(np.zeros(LETTERS), width, height)[0]
    heights = np.array([line_heights(row, width, height)[1] for row in points]).reshape(points.shape[0], X.size)
    directory.mkdir(parents=True, exist_ok=True)

    def write(index: int) -> None:
        picture = _frame(heights, colors, index, X, background, width, height)
        Image.fromarray(picture, "RGB").save(directory / f"frame_{index:06d}.png", compress_level=1)

    with ThreadPoolExecutor(max_workers=_SAVE_WORKERS) as pool:
        for future in [pool.submit(write, i) for i in range(points.shape[0])]:
            future.result()  # raises the first error of a worker, if there was one
