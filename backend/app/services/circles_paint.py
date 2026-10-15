"""The ``circles_paint`` kind of picture: the circles of ``circles``, with no memory, painted onto a copy of the previous picture.

Which circles are put down in a frame, where, in which color and how large is decided by ``circles.plan_circles`` exactly as for
the ``circles`` kind (the strongest notes of the frame and their ranks, the angle and distance from the note, the stay-in-place
rule, the wrap-around, the scaling of Movement and Radius to the frame). What differs is only how the picture is made:

* There is **no memory**: no buffer of circles, no limit on how many have been painted, no circle that fades or is dropped.
* The first frame is the plain background (the colormap's middle color) with its circles painted on it, and every later frame
  is a copy of the previous frame's picture with this frame's circles painted on top of it. A pixel that no circle of the frame
  touches is exactly the pixel of the previous frame, and a frame without sound is an exact copy of the one before.
* A circle is **solid**: a pixel well inside it has exactly its color, whatever was there. Its edge is smooth, as the edge of a
  circle of ``circles`` is: the circle is drawn on a patch four times larger and averaged down into a coverage mask of 0 to 255,
  and the canvas is mixed with the circle's color through that mask, so an edge pixel is a mix of the color and what was there.
* Within a frame the circles are painted weakest first, so the strongest note's circle is on top. A circle that sticks out of the
  picture is cut off by the edge (it is not painted again on the opposite side).
"""

import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .circles import (
    _NOTES,
    _SAVE_WORKERS,
    DEFAULT_CIRCLE_RADIUS,
    DEFAULT_CIRCLE_RESIZE,
    MIDDLE_COLOR_ROW,
    REFERENCE_WIDTH,
    SUPERSAMPLE,
    check_circle_notes,
    check_circle_radius,
    check_circle_resize,
    check_circle_unit,
    plan_circles,
    resize_factor,
)
from .colormaps import check_colormap, lookup_table


def _paint_circle(canvas: Image.Image, x: float, y: float, radius: float, color: tuple[int, int, int]) -> None:
    """Paint one solid circle of ``color`` with its center at ``(x, y)`` onto ``canvas``, with a smooth edge."""
    scale = SUPERSAMPLE
    x0, y0 = math.floor(x - radius) - 1, math.floor(y - radius) - 1  # the whole-pixel box that holds the circle and its edge
    x1, y1 = math.ceil(x + radius) + 1, math.ceil(y + radius) + 1
    mask = Image.new("L", ((x1 - x0) * scale, (y1 - y0) * scale), 0)
    ImageDraw.Draw(mask).ellipse(
        [(x - radius - x0) * scale, (y - radius - y0) * scale, (x + radius - x0) * scale - 1, (y + radius - y0) * scale - 1],  # the box includes its last pixel
        fill=255,
    )
    mask = mask.reduce(scale)  # the average of each block: the share of the pixel that the circle covers
    left, top = max(x0, 0), max(y0, 0)  # a circle past an edge is cut off by it
    right, bottom = min(x1, canvas.width), min(y1, canvas.height)
    if left >= right or top >= bottom:
        return
    canvas.paste(color, (left, top, right, bottom), mask.crop((left - x0, top - y0, right - x0, bottom - y0)))


def write_paint_frames(
    values: np.ndarray,
    peak: float,
    colormap: str,
    directory: Path,
    notes: int,
    unit: int,
    radius: int = DEFAULT_CIRCLE_RADIUS,
    width: int = 252,
    height: int = 168,
    resize: bool = DEFAULT_CIRCLE_RESIZE,
) -> None:
    """Save one RGB PNG per row of ``values`` as ``frame_000000.png`` and up: the canvas after that frame's circles are painted.

    See the module docstring. All the settings and the colormap are checked before anything is written. ``values`` is
    ``(frames, 84)``, the smoothed value of every drawn note in every frame; ``peak`` is the largest smoothed value of the file.
    """
    colormap = check_colormap(colormap)
    notes = check_circle_notes(notes)
    unit = check_circle_unit(unit)
    radius = check_circle_radius(radius)
    resize = check_circle_resize(resize)
    values = np.asarray(values)
    if values.ndim != 2 or values.shape[1] != _NOTES:
        raise ValueError(f"Each frame needs {_NOTES} note values (got shape {values.shape}).")
    plan = plan_circles(values, peak, notes, unit, None, width, height)  # no memory: only what each frame adds is used
    colors = [tuple(int(v) for v in row) for row in lookup_table(colormap)]
    canvas = Image.new("RGB", (width, height), colors[MIDDLE_COLOR_ROW])
    frame_scale = width / REFERENCE_WIDTH  # the radius is measured in pixels of the reference frame
    directory.mkdir(parents=True, exist_ok=True)
    pool = ThreadPoolExecutor(max_workers=_SAVE_WORKERS)
    try:
        futures = []
        for i, (added, _) in enumerate(plan):
            for x, y, color in added:  # weakest first: the strongest is painted last, on top
                _paint_circle(canvas, x, y, radius * frame_scale * resize_factor(color, resize), colors[color])
            # the picture is saved on another thread while the next frame is painted, so the saved picture is a copy
            futures.append(pool.submit(canvas.copy().save, directory / f"frame_{i:06d}.png", compress_level=6))
        for future in futures:
            future.result()  # raises the first error of a worker, if there was one
    finally:
        pool.shutdown(wait=True)
