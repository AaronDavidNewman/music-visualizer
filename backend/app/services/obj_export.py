"""The 3D export (feature 045): the grids of ``contour`` and the lines of ``chromatic-wireframe`` as Wavefront OBJ files,
one file for each frame.

The export is made from the numbers the pictures are made from, without their drawing: no contour levels, no antialiasing,
no projection, no sine. A file is plain text, complete in itself: a few comment lines, ``o <name>``, one ``v x y z r g b``
line for each point (position in grid units, the color as three numbers from 0 to 1) and one ``f a b c d`` line for each
face (the four corners of one cell of the grid, counted from 1, counterclockwise seen from +Z, so that the normal of the
face points up). Everything is in grid units, so the three axes are about the same size when the files are opened in
Blender: one unit is one cell, X runs from 0 to 11, Y from 0 to 6 (contour) or 0 to 11 (wireframe) and Z from 0 to 12. The
surface is not curved: the points are the only points and the curve is left to the modifiers of Blender.

**Contour**: a frame is the 12 x 7 grid of the notes (the 12 note names along X, the 7 octaves along Y) after the picture's
own smoothing and, when the job has the beat wave on, the beat wave: 84 points and 66 faces. Z is the value scaled so that
the largest value of the whole file is 12 (so the heights of different frames can be compared). The color of a point is
the color of the colormap for its value on the scale the picture of that frame uses (0 to the largest value of the
frame); a frame the picture draws in one flat color has that color at every point.

**Chromatic Wireframe**: the file of a frame holds the line of the frame and the lines of the 11 frames before it (as many
as exist for the first frames): each line is 12 points, one for each letter (A first) along X, at ``Y = the age of the
line`` (0 for the frame itself); Z is the amplitude of the letter (its circle's share of the full radius, 1/12 to 1) times
12, so from 1 to 12. The 12 points of a line have the color of the picture's line of that frame. A full file has 144 points
and 121 faces.

The text depends only on its input (fixed four decimals, ``\\n`` line ends, no locale), so the same music and settings give
the same files byte for byte, and the ZIP of a job (``zip_obj_files``) is reproducible too.

Order of operations:
    1. Check the arguments - ``write_contour_obj()`` or ``write_wireframe_obj()`` - the colormap, the beat, the number of
       waves and the shape of the values: ``GridValues`` ``(frames, 84)`` or ``CirclePoints`` ``(frames, 12)``.
    2. Choose the points of each frame and their heights - ``contour.smoothed_grid()`` then the beat wave for the contour
       (``FrameGrid`` ``(7, 12)``), ``amplitude_share()`` for the wireframe (``LetterAmplitudes`` ``(frames, 12)``) -
       scaled to 0 to 12.
    3. Color the points - ``contour_mesh()`` (the colormap's ``ColorTable`` at each value) or ``wireframe_mesh()`` (the
       ``LineColors`` ``(frames, 3)`` of ``chromatic_wireframe.line_colors()``) - and make the faces from neighbouring
       points: ``MeshVertices`` ``(points, 6)`` and ``MeshFaces`` ``(faces, 4)``.
    4. Write the file text - ``format_obj()`` - one ``frame_<index>.obj`` for each frame.
    5. Pack the files of a job when they are asked for - ``zip_obj_files()`` - one ZIP in frame order.
"""

import os
import zipfile
from pathlib import Path

import numpy as np

from .array_types import ArrayLike, BeatPositions, CirclePoints, FrameGrid, GridValues, LetterAmplitudes, LineColors, MeshFaces, MeshVertices
from .beat_wave import DEFAULT_WAVE_COUNT, check_wave_count, wave_modifier
from .chromatic_decay import LETTERS, _check_points
from .chromatic_wireframe import line_colors
from .colormaps import COLORMAP_STEPS, check_beat, check_colormap, lookup_table
from .contour import smoothed_grid
from .decay import SIZE_POINTS, SMALLEST

GRID_X = 12  # the note names: points along X for the contour
GRID_Y = 7  # the octaves: points along Y for the contour
NOTES = GRID_X * GRID_Y  # the 84 notes of the contour grid
LINES_PER_FILE = 12  # the lines of the wireframe in one file: the frame and the 11 before it
HEIGHT = 12.0  # the height of the largest value (contour) or of the full radius (wireframe): the top of Z
OBJ_FOLDER = "obj"  # the folder of the files of a job, inside its frames folder
OBJ_EXPORT_TYPES = ("contour", "chromatic-wireframe")  # the image types that have the export
NOT_AVAILABLE_MESSAGE = "The 3D export is only available for Contour and Chromatic Wireframe."
ZIP_DATE = (2020, 1, 1, 0, 0, 0)  # the date of every file in the ZIP, so that the same files give the same ZIP


def _quads(rows: int, columns: int) -> MeshFaces:
    """The faces of a grid of ``rows`` x ``columns`` points numbered row by row from 1: one face for each cell, its corners
    ``(row, col)``, ``(row, col + 1)``, ``(row + 1, col + 1)``, ``(row + 1, col)`` (counterclockwise seen from +Z when ``col`` runs
    to the right and ``row`` away from the viewer).

    Returns:
        ``MeshFaces`` ``((rows - 1) * (columns - 1), 4)`` - the corner numbers (from 1) of each face, row by row.
    """
    row, col = np.meshgrid(np.arange(rows - 1), np.arange(columns - 1), indexing="ij")
    first = (1 + columns * row + col).reshape(-1)
    return np.stack([first, first + 1, first + columns + 1, first + columns], axis=1).astype(np.intp)


def contour_mesh(grid: FrameGrid, peak: float, scale: float, colormap: str) -> tuple[MeshVertices, MeshFaces]:
    """The mesh of one frame of the contour: 84 points and 66 faces.

    The point of the cell in row ``r`` (0 at the bottom of the picture, the rows of ``grid``) and column ``c`` is vertex ``1 +
    12 r + c`` at ``(c, r, z)``, ``z = 12 * value / peak`` held between 0 and 12 (0 everywhere for a ``peak`` of 0), in the
    color of the colormap at ``value / scale`` (the first color for a ``scale`` of 0).

    Arrays:
        ``grid``: ``FrameGrid`` ``(7, 12)`` - the values of one frame (after the smoothing and the beat wave), row 0 at the
            bottom.

    Returns:
        A tuple of ``MeshVertices`` ``(84, 6)`` (x, y, z, red, green, blue, vertex ``k`` in row ``k - 1``) and
        ``MeshFaces`` ``(66, 4)`` (the corners of each cell, from 1).
    """
    values = np.asarray(grid, dtype=np.float64)
    if values.shape != (GRID_Y, GRID_X):
        raise ValueError(f"The grid of a frame must be {GRID_Y} rows of {GRID_X} values (got shape {values.shape}).")
    y, x = np.indices(values.shape)
    height = np.clip(HEIGHT * values / peak, 0.0, HEIGHT) if peak > 0 else np.zeros_like(values)
    rows = np.rint((COLORMAP_STEPS - 1) * np.clip(values / scale, 0.0, 1.0)).astype(np.intp) if scale > 0 else np.zeros(values.shape, dtype=np.intp)
    colors = lookup_table(colormap)[rows].reshape(-1, 3) / 255.0
    vertices = np.column_stack([x.reshape(-1), y.reshape(-1), height.reshape(-1), colors]).astype(np.float64)
    return vertices, _quads(GRID_Y, GRID_X)


def amplitude_share(points: ArrayLike) -> LetterAmplitudes:
    """The share of the full radius of the circle of each letter: ``SMALLEST + (1 - SMALLEST) * min(points, SIZE_POINTS) /
    SIZE_POINTS``, 1/12 at 0 points and 1 from 24 points (the circle of Chromatic Decay, and the amplitude of the letter's
    sine in the wireframe picture).

    Arrays:
        ``points``: ``ArrayLike`` any shape, usually ``(frames, 12)`` - the points (0 to 64) of each letter.

    Returns:
        ``LetterAmplitudes`` the shape of ``points`` - the share of the full radius, from 1/12 to 1.
    """
    array = np.asarray(points, dtype=np.float64)
    return SMALLEST + (1.0 - SMALLEST) * np.minimum(array, SIZE_POINTS) / SIZE_POINTS


def wireframe_mesh(points: CirclePoints, colors: LineColors, frame: int) -> tuple[MeshVertices, MeshFaces]:
    """The mesh of the file of one frame of the wireframe: the line of ``frame`` and the lines of the frames before it, at
    most ``LINES_PER_FILE`` lines in all.

    With ``L = min(frame + 1, 12)`` lines, line ``j`` is the frame ``frame - j`` at ``Y = j``; its letter ``b`` is vertex ``1 +
    12 j + b`` at ``(b, j, 12 * amplitude)`` in the color of the picture's line of that frame (the same for the 12 points).
    The faces join neighbouring letters of neighbouring lines: ``11 * (L - 1)``.

    Arrays:
        ``points``: ``CirclePoints`` ``(frames, 12)`` - the points (0 to 64) of each letter after each frame.
        ``colors``: ``LineColors`` ``(frames, 3)`` - the color (0 to 255) of the line of each frame.

    Returns:
        A tuple of ``MeshVertices`` ``(12 * L, 6)`` and ``MeshFaces`` ``(11 * (L - 1), 4)``.
    """
    if not 0 <= frame < points.shape[0]:
        raise ValueError(f"The frame must be from 0 to {points.shape[0] - 1} (got {frame}).")
    lines = min(frame + 1, LINES_PER_FILE)
    first = frame - np.arange(lines)  # the frame of each line, newest first
    height = HEIGHT * amplitude_share(points[first])  # (lines, 12)
    y, x = np.indices(height.shape)
    colors_of_lines = np.repeat(colors[first][:, None, :], LETTERS, axis=1).reshape(-1, 3) / 255.0
    vertices = np.column_stack([x.reshape(-1), y.reshape(-1), height.reshape(-1), colors_of_lines]).astype(np.float64)
    if lines < 2:
        return vertices, np.zeros((0, 4), dtype=np.intp)
    return vertices, _quads(lines, LETTERS)


def format_obj(vertices: MeshVertices, faces: MeshFaces, comment: str, name: str) -> str:
    """The text of one OBJ file.

    The header is ``# Music Visualizer 3D export``, ``# <comment>`` and ``o <name>``; then one ``v x y z r g b`` line for each
    row of ``vertices`` and one ``f a b c d`` line for each row of ``faces``. Numbers have four decimals (a dot, no exponent,
    ``-0.0000`` written ``0.0000``), lines end with ``\\n`` and the text ends with one.

    Arrays:
        ``vertices``: ``MeshVertices`` ``(points, 6)`` - x, y, z, red, green, blue of each point.
        ``faces``: ``MeshFaces`` ``(faces, 4)`` - the four corners (from 1) of each face.

    Returns:
        The text of the file.
    """
    lines = ["# Music Visualizer 3D export", f"# {comment}", f"o {name}"]
    for row in vertices:
        lines.append("v " + " ".join(f"{value:.4f}" for value in row).replace("-0.0000", "0.0000"))
    for face in faces:
        lines.append("f " + " ".join(str(int(corner)) for corner in face))
    return "\n".join(lines) + "\n"


def _write(directory: Path, index: int, text: str) -> None:
    """Write ``text`` as ``frame_<index>.obj`` (6 digits, as the pictures) in ``directory``, with ``\\n`` line ends."""
    with open(directory / f"frame_{index:06d}.obj", "w", encoding="ascii", newline="\n") as out:
        out.write(text)


def write_contour_obj(
    values: GridValues,
    peak: float,
    colormap: str,
    directory: Path,
    beat: BeatPositions | None = None,
    waves: int = DEFAULT_WAVE_COUNT,
) -> None:
    """Write one OBJ file of the contour for every row of ``values`` into ``directory`` (no frame is skipped).

    A frame the picture draws in one flat color (``peak`` of 0, or every value of the frame equal) has that color at all 84
    points; any other frame is smoothed as the picture smooths it (``contour.smoothed_grid``), multiplied by the beat wave
    when its ``beat`` position is above 0, and colored on the scale of the frame's largest value before the wave.

    Arrays:
        ``values``: ``GridValues`` ``(frames, 84)`` - the value of each of the 84 notes in each frame, row by row (the
            hidden notes are 0).
        ``beat``: ``BeatPositions`` ``(frames,)`` or ``None`` - the place of each frame in the local energy peak, 0 to 1.
    """
    colormap = check_colormap(colormap)
    waves = check_wave_count(waves)
    grids = np.asarray(values, dtype=np.float64)
    if grids.ndim != 2 or grids.shape[1] != NOTES:
        raise ValueError(f"Each frame needs {NOTES} note values (got shape {grids.shape}).")
    if beat is not None:
        beat = check_beat(beat, len(grids))
    directory.mkdir(parents=True, exist_ok=True)
    frames = len(grids)
    for i, frame in enumerate(grids):
        if peak <= 0 or frame.min() == frame.max():
            flat = np.full((GRID_Y, GRID_X), float(frame[0]))
            vertices, faces = contour_mesh(flat, peak, peak, colormap)
        else:
            grid = smoothed_grid(frame, GRID_Y, GRID_X)
            top = float(frame.max())
            k = 0.0 if beat is None else float(beat[i])
            if k > 0:
                grid = grid * wave_modifier(GRID_Y, GRID_X, waves, k)
            vertices, faces = contour_mesh(grid, peak, top, colormap)
        comment = f"contour frame {i} of {frames}: x = note name 0-11, y = octave row 0-6, z = value 0-12 (colors 0-1)"
        _write(directory, i, format_obj(vertices, faces, comment, f"frame_{i:06d}"))


def write_wireframe_obj(points: CirclePoints, colormap: str, directory: Path, beat: BeatPositions | None = None) -> None:
    """Write one OBJ file of the wireframe for every row of ``points`` into ``directory``: the line of the frame and the 11
    before it (``wireframe_mesh``). Only the 12 amplitudes of each line are written: not the sine, its frequency or the
    picture's contrast stretch.

    Arrays:
        ``points``: ``CirclePoints`` ``(frames, 12)`` - the points (0 to 64) of each letter after each frame.
        ``beat``: ``BeatPositions`` ``(frames,)`` or ``None`` - the place of each frame in the local energy peak, 0 to 1;
            ``None`` gives every line the first color.
    """
    colormap = check_colormap(colormap)
    array = _check_points(points)
    if beat is not None:
        beat = check_beat(beat, array.shape[0])
    colors = line_colors(beat, colormap, frames=array.shape[0])
    directory.mkdir(parents=True, exist_ok=True)
    frames = array.shape[0]
    for i in range(frames):
        vertices, faces = wireframe_mesh(array, colors, i)
        comment = f"chromatic-wireframe frame {i} of {frames}: x = letter 0-11 (A first), y = frame age 0-11, z = amplitude 1-12 (colors 0-1)"
        _write(directory, i, format_obj(vertices, faces, comment, f"frame_{i:06d}"))


def zip_obj_files(directory: Path, archive: Path) -> None:
    """Pack the ``*.obj`` files of ``directory`` into the ZIP ``archive``, in sorted (frame) order, stored under their own
    names, each with the fixed date ``ZIP_DATE``, so that the same files always give the same ZIP. The ZIP is written under a
    temporary name and renamed, so that a half-written ZIP is never offered.

    Raises:
        ``FileNotFoundError`` when ``directory`` holds no ``.obj`` file.
    """
    files = sorted(directory.glob("*.obj")) if directory.is_dir() else []
    if not files:
        raise FileNotFoundError("There are no 3D files to pack.")
    archive.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive.with_name(archive.name + ".tmp")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as pack:
        for path in files:
            info = zipfile.ZipInfo(path.name, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            pack.writestr(info, path.read_bytes())
    os.replace(temporary, archive)
