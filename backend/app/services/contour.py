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
from collections.abc import Sequence
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

def directionalSmoothing(Z: np.ndarray, xix: int, yix: int, rows: int, cols: int):
  if xix < 2 or yix < 2:
    return
  ix1 = xix - 1
  iy1 = yix - 1
  ix2 = xix - 2
  iy2 = yix - 2
  Zxy = Z[xix, yix]
  Zdx1 = Z[ix1, yix]
  Zdx2 = Z[ix2, yix]
  Zdy1 = Z[xix, iy1]
  Zdy2 = Z[xix, iy2]
  Zdz1 = Z[ix1, iy1]
  Zdz2 = Z[ix2, iy2]
  dz1 = np.abs(Zxy - Zdz1)
  dz2 = np.abs(Zdz1 - Zdz2)
  dx1 = np.abs(Zxy - Zdx1)
  dx2 = np.abs(Zdx1 - Zdx2)
  dy1 = np.abs(Zxy - Zdy1)
  dy2 = np.abs(Zdy1 - Zdy2)
  if dz1 > dz2:
    Z[xix, yix] = (Zxy + Zdz1 + Zdz2) / 3
    return
  if dy1 > dy2:
    Z[xix, yix] = (Zxy + Zdy1) / 2
    return
  if dx1 > dx2:
    Z[xix, yix] = (Zxy + Zdx1) / 2
    return

def write_contour_frames(
    values: np.ndarray,
    peak: float,
    colormap: str,
    directory: Path,
    columns: int,
    rows: int,
    width: int,
    height: int,
    indices: Sequence[int] | None = None,
) -> None:
    """Save one PNG of ``width`` x ``height`` pixels per row of ``values`` as ``frame_000000.png`` and up.

    ``indices`` are the numbers of the frames to draw (each into the file with its own number); ``None`` draws them all.

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
            for i in range(len(values)) if indices is None else indices:
                frame = values[i]
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
                Z = frame.reshape(rows, columns)[::-1].copy()  # a copy: the smoothing below works in place and must not change the caller's array
                for ix in [idx for idx in np.ndindex(Z.shape)]:
                 directionalSmoothing(Z, ix[0], ix[1], rows, columns)
                # ADN I added levels
                levels = np.linspace(Z.min(), Z.max(), 12)
                axes.contourf(x, y, Z, levels=levels, cmap=colormap, vmin=0, vmax=top)
                pyplot.savefig(path)
        finally:
            pyplot.close(figure)
