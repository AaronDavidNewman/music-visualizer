"""The ``circles`` kind of picture: circles that wander as the music plays.

In every frame the few strongest notes of that frame each put down a circle, and the picture shows the circles that were
put down most recently (the picture *remembers* them).

* **The notes** of a frame are the ``notes`` (5 to 12) drawn notes with the largest smoothed value in that frame, sorted
  from the strongest down (ties go to the lower note); a note whose value is 0 puts nothing down. The sorted position is the
  *rank* (0 for the strongest).
* **The place** of the circle of rank ``r`` is the place that rank ``r`` had in the previous frame (the middle of the picture
  at the start, and for a rank that has had no circle yet) moved by the *move* of its note, and the picture wraps around at
  its edges. A rank that gets no note in a frame keeps its place. A rank whose note is the *same note at the same volume* as the
  last note of that rank (the same note and the same color, which is the volume as the picture shows it) does not move: its new
  circle goes on the same place.
* **The move** of a note comes from its real name and octave, not from the application's grid (whose first column is A):
  the angle is 30 degrees times the note name counted from C (C = 0, C# = 1 ... B = 11), mirrored (360 - angle) below octave 4,
  and the distance is ``1 + |octave - 4|`` units of ``unit`` pixels (scientific octave: A4 is 440 Hz). 0 degrees points right
  and angles grow counter-clockwise on the screen. F5 is 150 degrees and 2 units, F3 210 degrees and 2 units, A4 270 degrees
  and 1 unit.
* **The color** is the selected colormap's at the position the tiles use for the same strength: ``sqrt`` of the share of the
  file's largest smoothed value, rounded to one of 256 table entries.
* **The memory** is a circular buffer of the last ``memory`` (100 to 500) circles. Each frame adds its circles weakest
  first, so the strongest of a frame is drawn on top and dropped last, and the picture draws the whole buffer, oldest first.
* **The look**: the background is the *middle color* of the selected colormap (the table entry at the middle of its scale),
  and each circle is a disc of the size ``size`` (its circumference in pixels, 25 to 50) in its own color with an
  *opacity that falls with its age*: the newest circle is opaque, and a circle ``age`` places back in the memory (0 for the
  newest) has the opacity ``(memory - age) / memory``, so the oldest circle, just before it leaves the memory, is barely
  visible. The step of a circle (``unit``) and its size are separate settings.
* **Resize by volume** (off by default): the radius of each circle is multiplied by a factor that grows in a straight line
  with the note's strength on the color scale (the color index ``c`` of 0 to 255), from 1 for the faintest to 3 for the
  strongest note of the file: ``1 + 2 * c / 255``, so no circle is smaller than ``size``. Off, every circle has the radius of ``size``.

A frame depends on the frames before it, so frames are made in order. This module knows nothing about the note analysis or
the other kinds of picture, only that a frame has 84 note values ordered from A1 (55 Hz).
"""

import math
import numbers
import os
from collections import deque
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .colormaps import check_colormap, lookup_table

MIN_CIRCLE_UNIT = 1
MAX_CIRCLE_UNIT = 10
DEFAULT_CIRCLE_UNIT = 4

MIN_CIRCLE_MEMORY = 100
MAX_CIRCLE_MEMORY = 500
DEFAULT_CIRCLE_MEMORY = 300

MIN_CIRCLE_NOTES = 5
MAX_CIRCLE_NOTES = 12
DEFAULT_CIRCLE_NOTES = 8

# the size of a circle is its circumference in pixels: from about the circle that the default unit used to give (4 pixels in radius)
# to about 50 pixels around
MIN_CIRCLE_SIZE = 25
MAX_CIRCLE_SIZE = 50
DEFAULT_CIRCLE_SIZE = 25

# the background is the middle color of the colormap: this row of its 256-entry table (0.5 of the way along its scale)
MIDDLE_COLOR_ROW = 128

# resize by volume: the radius factor goes from the first to the second along the strength of the note (energy 0 to the maximum)
MIN_RESIZE_FACTOR = 1.0
MAX_RESIZE_FACTOR = 3.0
DEFAULT_CIRCLE_RESIZE = False

# smooth edges: a picture is drawn this many times larger in each direction and then shrunk by averaging, so an edge pixel gets the
# share of it that a circle covers (and a circle can sit between pixels) instead of the stair-steps of a hard-edged disc
SUPERSAMPLE = 4

# the number of drawn notes per frame, the lowest being A1 (MIDI note 33)
_NOTES = 84
_FIRST_MIDI_NOTE = 33

# the pictures are saved on a few threads: Pillow's PNG encoder releases the interpreter lock, and each picture is its own image
_SAVE_WORKERS = max(1, min(4, os.cpu_count() or 1))


def _check_whole(value, low: int, high: int, message: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, numbers.Real)
        or not math.isfinite(value)
        or int(value) != value
        or not low <= value <= high
    ):
        raise ValueError(message)
    return int(value)


def check_circle_unit(value) -> int:
    """Return ``value`` as an ``int`` when it is a whole number of pixels from 1 to 10."""
    return _check_whole(value, MIN_CIRCLE_UNIT, MAX_CIRCLE_UNIT, f"The circle unit must be a whole number from {MIN_CIRCLE_UNIT} to {MAX_CIRCLE_UNIT}.")


def check_circle_memory(value) -> int:
    """Return ``value`` as an ``int`` when it is a whole number of circles from 100 to 500."""
    return _check_whole(
        value, MIN_CIRCLE_MEMORY, MAX_CIRCLE_MEMORY, f"The circle memory must be a whole number from {MIN_CIRCLE_MEMORY} to {MAX_CIRCLE_MEMORY}."
    )


def check_circle_notes(value) -> int:
    """Return ``value`` as an ``int`` when it is a whole number of notes from 5 to 12."""
    return _check_whole(
        value, MIN_CIRCLE_NOTES, MAX_CIRCLE_NOTES, f"The number of circle notes must be a whole number from {MIN_CIRCLE_NOTES} to {MAX_CIRCLE_NOTES}."
    )


def check_circle_size(value) -> int:
    """Return ``value`` as an ``int`` when it is a whole number of pixels, the circumference of a circle, from 25 to 50."""
    return _check_whole(
        value, MIN_CIRCLE_SIZE, MAX_CIRCLE_SIZE, f"The circle size must be a whole number from {MIN_CIRCLE_SIZE} to {MAX_CIRCLE_SIZE}."
    )


def check_circle_resize(value) -> bool:
    """Return ``value`` as a ``bool`` when it is one (``True``/``False``, also NumPy's); anything else is refused."""
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    raise ValueError("The circle resize must be true or false.")


def resize_factor(color: int, resize: bool = True) -> float:
    """The factor of a circle's radius for a note of color index ``color`` (0 to 255): 1 at 0 up to 3 at 255 in a straight line;
    1 when ``resize`` is off."""
    if not resize:
        return 1.0
    return MIN_RESIZE_FACTOR + (MAX_RESIZE_FACTOR - MIN_RESIZE_FACTOR) * color / 255


def circle_radius(size: int) -> float:
    """The radius in pixels of a circle whose circumference is ``size`` pixels."""
    return size / (2 * math.pi)


def circle_opacity(age: int, memory: int) -> int:
    """The opacity (0 to 255) of a circle ``age`` places back in a memory of ``memory`` circles (0 is the newest): it falls
    in a straight line from opaque for the newest to ``255 / memory`` (barely visible) for the oldest a full memory holds."""
    return int(round(255 * (memory - age) / memory))


def note_move(index: int) -> tuple[int, int]:
    """The move of the drawn note with this index (0 to 83, 0 being A1): ``(angle in degrees, units)``."""
    if isinstance(index, bool) or not isinstance(index, numbers.Integral) or not 0 <= index < _NOTES:
        raise ValueError(f"The note must be a whole number from 0 to {_NOTES - 1}.")
    midi = _FIRST_MIDI_NOTE + int(index)
    pitch_class, octave = midi % 12, midi // 12 - 1
    angle = 30 * pitch_class
    if octave < 4:
        angle = (360 - angle) % 360
    return angle, 1 + abs(octave - 4)


def step_pixels(index: int, unit: int) -> tuple[float, float]:
    """The step of a note in pixels ``(dx, dy)`` for a unit of ``unit`` pixels (the picture's y axis points down)."""
    angle, units = note_move(index)
    radians = math.radians(angle)
    distance = units * unit
    return distance * math.cos(radians), -distance * math.sin(radians)


def plan_circles(
    values: np.ndarray, peak: float, notes: int, unit: int, memory: int, width: int = 252, height: int = 168
) -> Iterator[tuple[list[tuple[float, float, int]], list[tuple[float, float, int]]]]:
    """For every frame, ``(added, remembered)``: the circles put down in it and the whole memory after it.

    ``values`` is ``(frames, 84)``: the smoothed value of every drawn note in every frame; ``peak`` is the largest smoothed
    value of the whole file. A circle is ``(x, y, color index 0 to 255)``. ``added`` is weakest first; ``remembered`` is the
    last ``memory`` circles, oldest first. The values are never modified.
    """
    notes = check_circle_notes(notes)
    unit = check_circle_unit(unit)
    memory = check_circle_memory(memory)
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != _NOTES:
        raise ValueError(f"Each frame needs {_NOTES} note values (got shape {values.shape}).")
    steps = [step_pixels(i, unit) for i in range(_NOTES)]
    places = [[width / 2, height / 2] for _ in range(notes)]  # the last place of every rank
    last: list = [None] * notes  # the last (note, color) of every rank
    remembered: deque = deque(maxlen=memory)
    for frame in values:
        order = np.argsort(-frame, kind="stable")[:notes]
        added = []
        for rank, note in enumerate(order):
            value = float(frame[note])
            if value <= 0.0:
                continue  # sorted from the strongest down: the rest have no energy either
            share = min(value / peak, 1.0) if peak > 0 else 0.0
            color = int(np.rint(math.sqrt(share) * 255))
            if last[rank] == (int(note), color):
                x, y = places[rank]  # the same note at the same volume: it stays where it is
            else:
                dx, dy = steps[int(note)]
                x, y = (places[rank][0] + dx) % width, (places[rank][1] + dy) % height
                x, y = (0.0 if x >= width else x), (0.0 if y >= height else y)  # a tiny negative step can round up to the edge
                places[rank] = [x, y]
            last[rank] = (int(note), color)
            added.append((x, y, color))
        added.reverse()  # weakest first
        remembered.extend(added)
        yield added, list(remembered)


def write_circle_frames(
    values: np.ndarray,
    peak: float,
    colormap: str,
    directory: Path,
    notes: int,
    unit: int,
    memory: int,
    size: int = DEFAULT_CIRCLE_SIZE,
    width: int = 252,
    height: int = 168,
    resize: bool = DEFAULT_CIRCLE_RESIZE,
) -> None:
    """Save one RGB PNG per row of ``values`` as ``frame_000000.png`` and up: the memory of circles after that frame.

    See the module docstring. All the settings and the colormap are checked before anything is written.
    """
    colormap = check_colormap(colormap)
    notes = check_circle_notes(notes)
    unit = check_circle_unit(unit)
    memory = check_circle_memory(memory)
    size = check_circle_size(size)
    resize = check_circle_resize(resize)
    plan = plan_circles(values, peak, notes, unit, memory, width, height)  # checks the shape of the values at the first frame
    values = np.asarray(values)
    if values.ndim != 2 or values.shape[1] != _NOTES:
        raise ValueError(f"Each frame needs {_NOTES} note values (got shape {values.shape}).")
    colors = [tuple(int(v) for v in row) for row in lookup_table(colormap)]
    background = colors[MIDDLE_COLOR_ROW]
    radius = circle_radius(size)
    scale = SUPERSAMPLE
    directory.mkdir(parents=True, exist_ok=True)
    pool = ThreadPoolExecutor(max_workers=_SAVE_WORKERS)
    try:
        futures = []
        for i, (_, remembered) in enumerate(plan):
            large = Image.new("RGB", (width * scale, height * scale), background)
            draw = ImageDraw.Draw(large, "RGBA")  # a fill with an alpha is blended into the picture
            newest = len(remembered) - 1
            for place, (x, y, color) in enumerate(remembered):
                r = radius * resize_factor(color, resize)
                draw.ellipse(
                    [(x - r) * scale, (y - r) * scale, (x + r) * scale - 1, (y + r) * scale - 1],  # the box includes its last pixel
                    fill=(*colors[color], circle_opacity(newest - place, memory)),
                )
            image = large.reduce(scale)  # the average of each scale x scale block
            futures.append(pool.submit(image.save, directory / f"frame_{i:06d}.png", compress_level=6))
        for future in futures:
            future.result()  # raises the first error of a worker, if there was one
    finally:
        pool.shutdown(wait=True)
