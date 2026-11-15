"""The ``contour`` kind of picture: the grid of note values drawn as a filled contour map by matplotlib.

Each frame is the grid of one value per drawn note (rows are octaves, columns are note names) drawn with ``contourf`` on
coordinates ``np.linspace(0, top, columns)`` by ``np.linspace(0, top, rows)``, where ``top`` is the largest value of
*that frame* (worked out again for every frame), with the colormap the job selected and the axis decorations off, and
saved with ``pyplot.savefig``. Nothing about the *levels* is decided here: matplotlib chooses them for the data of each
frame. The *color scale* runs from 0 to ``top`` too (``vmin=0, vmax=top``), so the loudest note of every frame is at the
end of the colormap; ``peak`` (the largest value in the whole file) is only used for a frame that has no contour to
draw, below.

With the **beat wave** (feature 028: ``beat`` given, the frame's position in the local energy peak from 0 to 1) the
frame's grid is multiplied by ``1 - pattern * k`` (see ``beat_wave``) after the grid smoothing and before the levels are
chosen; the color scale stays the one of the frame *before* the wave (``vmax`` is the frame's own largest value), so a
point that the wave dims is drawn darker, and at ``k = 0`` nothing is multiplied, so the frame is the plain one, byte
for byte. If the wave leaves nothing to draw (every point equal) the frame is one flat color.

A frame whose values are all the same (a quiet moment, a silent file, every note hidden) has no contour to draw and
``contourf`` draws a degenerate picture for it, so it is written as one flat color: the colormap's color at that value
on the scale, which for 0 is the first color of the colormap.

``matplotlib.pyplot`` is imported only when a contour is drawn (with the windowless Agg backend), so starting the server
and making the other kinds of picture never pay for it. ``pyplot`` keeps global state (the current figure and axes) and
the job endpoint runs on a thread pool, so the drawing of a job holds a lock.

This module knows nothing about the note analysis: the values, the geometry and the image size are passed in.

Order of operations:
    1. Check the arguments - ``write_contour_frames()`` - the colormap, the number of waves, ``values`` (``GridValues``
       ``(frames, rows * columns)``) and the beat.
    2. Take the drawing lock and open one figure of the picture's size - ``write_contour_frames()`` - ``pyplot`` keeps
       global state.
    3. For each frame to draw: if nothing differs in it (a silent file, every value equal) write one flat color -
       ``_flat_frame()`` - and go to the next frame.
    4. Lay the frame out as a grid - ``write_contour_frames()`` - ``FrameGrid`` ``(rows, columns)``, the rows flipped so
       the first row of notes is at the top.
    5. Smooth the grid in place, cell by cell - ``directionalSmoothing()`` - a cell is averaged with the cells before it
       in the first direction (diagonal, then along the row, then down the column) in which the values change faster
       toward it than before it.
    6. (With a beat above 0) multiply the grid by the beat wave - ``beat_wave.wave_modifier()`` - ``FrameGrid`` times
       ``WaveModifier`` ``(rows, columns)``; if that leaves nothing to draw, write a flat color.
    7. Choose 12 levels from the smallest to the largest value of the grid and draw the filled contour -
       ``write_contour_frames()`` - the color scale runs from 0 to the frame's largest value.
    8. Save the figure as a PNG - ``write_contour_frames()`` - ``Pictures`` ``(height, width, 3)`` in the file
       ``frame_<index>.png``.
"""

import threading
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from PIL import Image

from .array_types import BeatPositions, FrameGrid, GridValues
from .beat_wave import DEFAULT_WAVE_COUNT, check_wave_count, wave_modifier
from .colormaps import COLORMAP_STEPS, check_beat, check_colormap, lookup_table

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

def directionalSmoothing(Z: FrameGrid, xix: int, yix: int, rows: int, cols: int) -> None:
  """Smooth one cell of the grid in place, using the cells before it, in the first of three directions in which the
  values are changing faster toward it than before it.

  The directions are tried in this order: diagonally (``Z[xix - 1, yix - 1]`` and ``Z[xix - 2, yix - 2]``), along the
  second index (``Z[xix, yix - 1]``) and along the first index (``Z[xix - 1, yix]``). A direction is used when the
  change from the previous cell to this one is larger than the change between the previous two cells; the cell becomes
  the average of itself and that direction's previous cell (the diagonal averages three cells). Nothing is done for the
  first two rows and columns, or when no direction qualifies. The function returns nothing; ``Z`` is changed.

  Arrays:
      ``Z``: ``FrameGrid`` ``(rows, cols)`` - the values of one frame with the rows flipped (row 0 is the last row of
          notes, drawn at the bottom of the picture), changed in place at the one cell ``(xix, yix)``.
  """
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
    values: GridValues,
    peak: float,
    colormap: str,
    directory: Path,
    columns: int,
    rows: int,
    width: int,
    height: int,
    indices: Sequence[int] | None = None,
    beat: BeatPositions | None = None,
    waves: int = DEFAULT_WAVE_COUNT,
) -> None:
    """Save one PNG of ``width`` x ``height`` pixels per row of ``values`` as ``frame_000000.png`` and up.

    ``indices`` are the numbers of the frames to draw (each into the file with its own number); ``None`` draws them all.

    ``beat`` (``None`` or one number from 0 to 1 for each frame of ``values``, the frame's place in the local energy
    peak) switches the beat wave on, with ``waves`` (a whole number from 2 to 10) waves across the largest dimension of
    the grid; ``None``, or a position of 0, draws the plain contour.

    ``values`` is ``(frames, rows * columns)``: the smoothed value of every drawn note in every frame, with the notes
    the threshold hides already set to 0; note ``n`` is at row ``n // columns`` and column ``n % columns`` of the grid,
    and the first row is drawn at the *top* of the picture, like the grid of notes. ``peak`` is the largest smoothed
    value of the whole file (0 for a silent file).

    Arrays:
        ``values``: ``GridValues`` ``(frames, rows * columns)`` - the smoothed value of each cell of the grid in each
            frame, row by row (the hidden notes are 0).
        ``beat``: ``BeatPositions`` ``(frames,)`` or ``None`` - the place of each frame in the local energy peak, 0 to
            1.
    """
    colormap = check_colormap(colormap)
    waves = check_wave_count(waves)
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != rows * columns:
        raise ValueError(f"Each frame needs {rows * columns} note values (got shape {values.shape}).")
    if beat is not None:
        beat = check_beat(beat, len(values))
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
                # a copy: the smoothing below works in place and must not change the caller's array
                Z = frame.reshape(rows, columns)[::-1].copy()
                for ix in [idx for idx in np.ndindex(Z.shape)]:
                 directionalSmoothing(Z, ix[0], ix[1], rows, columns)
                k = 0.0 if beat is None else float(beat[i])
                # the beat wave: at k = 0 the modifier is all 1, so nothing is multiplied and the frame is the plain one
                if k > 0:
                    Z = Z * wave_modifier(rows, columns, waves, k)
                    if Z.min() == Z.max():  # the wave left nothing to draw: contourf cannot draw equal levels
                        _flat_frame(colormap, float(Z.flat[0]), top, width, height).save(path)
                        continue
                # ADN I added levels
                levels = np.linspace(Z.min(), Z.max(), 12)
                axes.contourf(x, y, Z, levels=levels, cmap=colormap, vmin=0, vmax=top)
                pyplot.savefig(path)
        finally:
            pyplot.close(figure)
