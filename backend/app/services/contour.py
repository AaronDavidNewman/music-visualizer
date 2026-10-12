"""The ``contour`` kind of picture: the grid of note values drawn as a filled contour map by matplotlib.

Each frame is the grid of one value per drawn note (rows are octaves, columns are note names) drawn with ``contourf`` on
coordinates ``np.linspace(0, top, columns)`` by ``np.linspace(0, top, rows)``, where ``top`` is the largest value of *that
frame* (worked out again for every frame), with the colormap the job selected and the
axis decorations off, and saved with ``pyplot.savefig``. Nothing about the *levels* is decided here: matplotlib chooses
them for the data of each frame. The *color scale* runs from 0 to ``top`` too (``vmin=0, vmax=top``), so the loudest note
of every frame is at the end of the colormap; ``peak`` (the largest value in the whole file) is only used for a frame that
has no contour to draw, below.

A frame whose values are all the same (a quiet moment, a silent file, every note hidden) has no contour to draw and
``contourf`` draws a degenerate picture for it, so it is written as one flat color: the colormap's color at that value on
the scale, which for 0 is the first color of the colormap.

``matplotlib.pyplot`` is imported only when a contour is drawn (with the windowless Agg backend), so starting the server
and making the other kinds of picture never pay for it. ``pyplot`` keeps global state (the current figure and axes) and the
job endpoint runs on a thread pool, so the drawing of a job holds a lock.

This module knows nothing about the note analysis: the values, the geometry and the image size are passed in.
"""

import threading
from pathlib import Path

import numpy as np
from PIL import Image

from .colormaps import COLORMAP_STEPS, check_colormap, lookup_table

# matplotlib sizes a figure in inches; at this many dots per inch a figure of width / DPI by height / DPI inches is
# exactly width by height pixels
DPI = 100

# pyplot's current figure is global: two jobs drawing at once would draw into each other's figure
_DRAWING = threading.Lock()


def _flat_frame(colormap: str, value: float, peak: float, width: int, height: int) -> Image.Image:
    """One color over the whole picture: the colormap's color at ``value`` on the scale from 0 to ``peak``."""
    row = round((COLORMAP_STEPS - 1) * min(max(value / peak, 0.0), 1.0)) if peak > 0 else 0
    colour = tuple(int(c) for c in lookup_table(colormap)[row])
    return Image.new("RGB", (width, height), colour)


def write_contour_frames(
    values: np.ndarray,
    peak: float,
    colormap: str,
    directory: Path,
    columns: int,
    rows: int,
    width: int,
    height: int,
) -> None:
    """Save one PNG of ``width`` x ``height`` pixels per row of ``values`` as ``frame_000000.png`` and up.

    ``values`` is ``(frames, rows * columns)``: the smoothed value of every drawn note in every frame, with the notes the
    threshold hides already set to 0; note ``n`` is at row ``n // columns`` and column ``n % columns`` of the grid, and
    the first row is drawn at the *top* of the picture, like the tiles. ``peak`` is the largest smoothed value of the
    whole file (0 for a silent file).
    """
    colormap = check_colormap(colormap)
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != rows * columns:
        raise ValueError(f"Each frame needs {rows * columns} note values (got shape {values.shape}).")
    directory.mkdir(parents=True, exist_ok=True)
    with _DRAWING:
        import matplotlib

        matplotlib.use("Agg")  # no window; the application runs on a server
        from matplotlib import pyplot

        figure = pyplot.figure(figsize=(width / DPI, height / DPI), dpi=DPI)
        try:
            axes = pyplot.axes([0, 0, 1, 1])  # fills the whole figure: no margin
            for i, frame in enumerate(values):
                path = directory / f"frame_{i:06d}.png"
                if peak <= 0 or frame.min() == frame.max():
                    _flat_frame(colormap, float(frame[0]), peak, width, height).save(path)
                    continue
                axes.clear()
                axes.set_axis_off()
                # the coordinates run from 0 to the largest value of this frame, worked out again for every frame
                top = float(frame.max())
                x = np.linspace(0, top, columns)
                y = np.linspace(0, top, rows)
                # no `levels`: matplotlib chooses them. vmin and vmax are 0 and this frame's largest value (the scale follows the frame).
                axes.contourf(x, y, frame.reshape(rows, columns)[::-1], cmap=colormap, vmin=0, vmax=top)
                pyplot.savefig(path)
        finally:
            pyplot.close(figure)
