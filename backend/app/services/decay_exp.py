"""The ``decay-exp`` kind of picture: the circles of ``decay``, with the points gained and lost along an exponential
curve.

Everything but two amounts is ``decay``: the 84 circles, the points from 0 to 64 and how they set the size, the color
and the rings, the five loudest notes of a frame gaining points (with the beat bonus), the decay steps at ``decay_rate``
frames, the neighbours (the cells around a cell, an edge or corner circle losing as if it had 8) and the drawing. This
module only has what differs, and takes the rest from ``decay``:

* the **gain** of a note that would gain ``g`` points (24, 20, 16, 12 or 8 by rank, plus ``8 * position``) is
  ``g * exp(-g / taper)``: the more a circle would gain, the more of it is cut back, so the loudest note gains the least
  (about 1.19 points with no beat at a taper of 8) and the fifth loudest the most (about 2.94). **The taper is not
  fixed**: it starts at 8 and rises by 0.01 in every frame, up to 12 (the cut gets gentler, so the gains grow); as soon
  as more than 10 circles have more than 32 points it falls by 0.01 in every frame until it is back at 8, and then rises
  again (see :func:`next_taper`);
* the **loss**, the points a circle gives to **each neighbour** per frame, is ``sin(pi / 2 * p / 64) ** 2`` for a circle
  that has ``p`` points before the step (0 with no points): about 0.0006 at 1 point, 0.038 at 8, 0.31 at 24, 0.5 at 32,
  0.85 at 48 and 1 at 64, so the fuller a circle is the faster it drains (8 points a frame in all at 64) and a nearly
  empty one hardly drains at all, which gives the fading a long tail. A step of ``frames`` frames' worth gives
  ``frames`` times that, and a circle never gives more than it has.

The decay amounts of ``decay`` (one for each saturation level) are not used. The drawing is
``decay.write_decay_frames``.

This module knows nothing about the note analysis or the audio: the smoothed note values and the beat positions are
passed in.

Order of operations:
    1. Check the settings - ``_simulate()`` - the note layout and the decay rate (0.25 to 4 in steps of 0.25).
    2. Work out what every note would gain, before the taper - ``decay.gains()`` - ``PointGains`` ``(frames, 84)``: 24,
       20, 16, 12 and 8 points for the five loudest notes plus ``8 * beat``; put them in cell order
       (``note_layout.arrange_notes()``) and each frame as a ``(7, 12)`` grid.
    3. For each frame in turn, take the taper - ``taper_of()`` - 8 at first, then up 0.01 a frame to 12.
    4. Add the cut gains - ``_simulate()`` - each gain ``g`` becomes ``g * exp(-g / taper)``; the points are held
       between 0 and 64.
    5. Let the circles give points to their neighbours - ``steps_in_frame()``, ``decay_exp_step()``,
       ``exp_loss_per_frame()`` and ``decay._spread()`` - the steps that fall in the frame; a circle with ``p`` points
       gives each neighbour ``sin(pi / 2 * p / 64) ** 2`` per frame: ``CirclePoints`` ``(7, 12)``.
    6. Record the frame - ``_simulate()`` - one row of ``CirclePoints`` ``(frames, 84)`` and the frame's taper in
       ``FrameTapers`` ``(frames,)``.
    7. Work out the taper of the next frame - ``next_taper()`` - it falls instead of rising while more than 10 circles
       have more than 32 points, and rises again at 8.
    8. (Drawing) ``decay.write_decay_frames()`` draws the points exactly as for ``decay``.
"""

import numpy as np

from .array_types import ArrayLike, BeatPositions, CirclePoints, FrameTapers, GivePerFrame, PointGains
from .note_grid import GRID_COLUMNS, GRID_ROWS, NOTES
from .decay import DEFAULT_DECAY_RATE, MAX_POINTS, NEIGHBOURS, _spread, check_decay_rate, gains, steps_in_frame
from .note_layout import DEFAULT_NOTE_LAYOUT, arrange_notes, check_note_layout

TAPER = 8  # the taper at the start and the lowest it goes: the 8 of exp(-g / 8)
MAX_TAPER = 12  # the highest it goes
TAPER_STEP = 0.01  # what is added to or taken from it in every frame
# 400: the taper is TAPER + TAPER_STEP * n for a whole number n from 0 to 400, so it never drifts
TAPER_STEPS = round((MAX_TAPER - TAPER) / TAPER_STEP)
FULL_POINTS = 32  # a circle with more points than this is counted ...
FULL_CIRCLES = 10  # ... and when more than this many are counted the taper falls


def taper_of(steps: int) -> float:
    """The taper after ``steps`` steps of 0.01 up from 8: ``8 + 0.01 * steps``, for a whole number of steps from 0 to
    400 (8 to 12)."""
    if not isinstance(steps, (int, np.integer)) or isinstance(steps, bool) or not 0 <= steps <= TAPER_STEPS:
        raise ValueError(f"The taper steps must be a whole number from 0 to {TAPER_STEPS}.")
    return TAPER + TAPER_STEP * int(steps)


def next_taper(steps: int, rising: bool, full_circles: int) -> tuple[int, bool]:
    """The taper (as ``steps``, see :func:`taper_of`) and the direction for the next frame, from the ones of this frame
    and ``full_circles``, the number of circles with more than 32 points at the end of it.

    While ``rising`` the taper goes up one step (0.01) a frame and stops at 12. When ``full_circles`` is more than 10 it
    turns and ``rising`` becomes false: it then goes down one step a frame, whatever the number of full circles is by
    then, until it is back at 8, where it turns up again. It never leaves 8 to 12.
    """
    if full_circles > FULL_CIRCLES:
        rising = False
    if rising:
        return min(steps + 1, TAPER_STEPS), True
    steps = max(steps - 1, 0)
    return steps, steps == 0


def exp_gains(values: ArrayLike, beat: BeatPositions | None = None, taper: float | ArrayLike = TAPER) -> PointGains:
    """The points every note gains in every frame, in note order: a float64 array of shape ``(frames, 84)``.

    The gains of ``decay`` (``decay.gains``: the five loudest notes, 24, 20, 16, 12 and 8 plus ``8 * position``) each
    multiplied by ``exp(-g / taper)``, ``g`` being that gain: a note that gains nothing still gains nothing. ``taper``
    is one number above 0 (8 by default) or one for each frame. The input is not changed.

    Arrays:
        ``values``: ``ArrayLike`` ``(frames, 84 or more)`` - the smoothed strength of each note in each frame
            (``NoteStrengths``), in note order.
        ``beat``: ``BeatPositions`` ``(frames,)`` or ``None`` - the place of each frame in the local energy peak, 0 to
            1.
        ``taper``: a number or ``FrameTapers`` ``(frames,)`` - the number above 0 in ``exp(-g / taper)`` (8 to 12 in a
            job).

    Returns:
        ``PointGains`` ``(frames, 84)`` - the points each note gains in each frame after the cut, in note order.
    """
    gained = gains(values, beat)
    taper = np.asarray(taper, dtype=np.float64)
    if taper.ndim > 1 or (taper.ndim == 1 and taper.shape[0] != gained.shape[0]) or not np.isfinite(taper).all() or (taper <= 0).any():
        raise ValueError("The taper must be a number above 0, or one for each frame.")
    if taper.ndim == 1:
        taper = taper[:, None]
    return gained * np.exp(-gained / taper)


def exp_loss_per_frame(points: ArrayLike) -> GivePerFrame:
    """The points a circle with ``points`` points gives to each of its neighbours in one frame:
    ``sin(pi / 2 * points / 64) ** 2``, and 0 with no points.

    Arrays:
        ``points``: ``ArrayLike`` any shape - the points (0 to 64) each circle holds: ``(7, 12)`` for the 84 circles,
            ``(12,)`` for the 12 of Chromatic Decay.

    Returns:
        ``GivePerFrame`` the shape of ``points`` - the points each circle gives to each neighbour in one frame.
    """
    points = np.asarray(points, dtype=np.float64)
    return np.where(points > 0.0, np.sin(np.pi/2 * points/64) ** 2, 0.0)


def decay_exp_step(points: ArrayLike, frames: float = 1) -> CirclePoints:
    """One decay step of ``frames`` frames' worth on a ``(7, 12)`` array of points: a new array, the input is not
    changed.

    A circle with ``p`` points gives ``min(p, 8 * frames * exp_loss_per_frame(p))`` in all, ``give / 8`` to each
    neighbour that exists (see
    ``decay._spread``: the rest is lost where it has no neighbour, everything is worked out from the points before the
        step, the result is held
    between 0 and 64 and a circle left with under a hundredth of a point has none).

    Arrays:
        ``points``: ``ArrayLike`` ``(7, 12)`` - the points (0 to 64) each circle holds, laid out as the grid (rows are
            octaves, columns note names).

    Returns:
        ``CirclePoints`` ``(7, 12)`` - the points after the step, held between 0 and 64.
    """
    points = np.asarray(points, dtype=np.float64)
    if points.shape != (GRID_ROWS, GRID_COLUMNS):
        raise ValueError(f"The points must be an array of shape {(GRID_ROWS, GRID_COLUMNS)} (got {points.shape}).")
    return _spread(points, np.minimum(points, NEIGHBOURS * frames * exp_loss_per_frame(points)))


def circle_points(values: ArrayLike, beat: BeatPositions | None = None, note_layout: str = DEFAULT_NOTE_LAYOUT, decay_rate: float = DEFAULT_DECAY_RATE) -> CirclePoints:
    """The points of the 84 circles after every frame: a float64 array of shape ``(frames, 84)``, in cell order (row by
    row).

    As ``decay.circle_points`` (``values`` is ``(frames, 84 or more)``, ``beat`` is ``None`` or one position from 0 to 1
    for each frame, ``decay_rate`` is the number of frames between decay steps, 0.25 to 4 in steps of 0.25), with the
    gains of :func:`exp_gains` at the taper of the frame (:func:`circle_tapers`) and the loss of :func:`decay_exp_step`.
    Frame ``i`` (counting from 1) adds its gains, then has the decay steps that fall in ``(i - 1, i]``, and is recorded;
    the taper of the next frame is then worked out from the circles with more than 32 points.

    Arrays:
        ``values``: ``ArrayLike`` ``(frames, 84 or more)`` - the smoothed strength of each note in each frame
            (``NoteStrengths``), in note order.
        ``beat``: ``BeatPositions`` ``(frames,)`` or ``None`` - the place of each frame in the local energy peak, 0 to
            1.

    Returns:
        ``CirclePoints`` ``(frames, 84)`` - the points (0 to 64) of each of the 84 circles after each frame, in cell
        order.
    """
    return _simulate(values, beat, note_layout, decay_rate)[0]


def circle_tapers(values: ArrayLike, beat: BeatPositions | None = None, note_layout: str = DEFAULT_NOTE_LAYOUT, decay_rate: float = DEFAULT_DECAY_RATE) -> FrameTapers:
    """The taper that every frame of :func:`circle_points` gained its points with: a float64 array of shape
    ``(frames,)``, 8 for the first frame.

    Arrays:
        ``values``: ``ArrayLike`` ``(frames, 84 or more)`` - the smoothed strength of each note in each frame, in note
            order.
        ``beat``: ``BeatPositions`` ``(frames,)`` or ``None`` - the place of each frame in the local energy peak, 0 to
            1.

    Returns:
        ``FrameTapers`` ``(frames,)`` - the taper (8 to 12) each frame's gains were cut with.
    """
    return _simulate(values, beat, note_layout, decay_rate)[1]


def _simulate(values: ArrayLike, beat: BeatPositions | None, note_layout: str, decay_rate: float) -> tuple[CirclePoints, FrameTapers]:
    """The whole simulation: the points after every frame and the taper of every frame.

    Arrays:
        ``values``: ``ArrayLike`` ``(frames, 84 or more)`` - the smoothed strength of each note in each frame, in note
            order.
        ``beat``: ``BeatPositions`` ``(frames,)`` or ``None`` - the place of each frame in the local energy peak, 0 to
            1.

    Returns:
        A tuple of ``CirclePoints`` ``(frames, 84)`` (the points of each circle after each frame, in cell order) and
        ``FrameTapers`` ``(frames,)``.
    """
    note_layout = check_note_layout(note_layout)
    decay_rate = check_decay_rate(decay_rate)
    # the gains of decay, before the taper
    raw = arrange_notes(gains(values, beat), note_layout).reshape(-1, GRID_ROWS, GRID_COLUMNS)
    points = np.zeros((GRID_ROWS, GRID_COLUMNS))
    recorded = np.zeros((raw.shape[0], NOTES))
    tapers = np.zeros(raw.shape[0])
    steps, rising = 0, True
    for index in range(raw.shape[0]):
        taper = taper_of(steps)
        tapers[index] = taper
        points = np.clip(points + raw[index] * np.exp(-raw[index] / taper), 0.0, MAX_POINTS)
        for _ in range(steps_in_frame(index, decay_rate)):  # the steps that fall in (index, index + 1] frames
            # a step of decay_rate frames' worth: the same average rate whatever the setting
            points = decay_exp_step(points, decay_rate)
        recorded[index] = points.reshape(NOTES)
        steps, rising = next_taper(steps, rising, int((points > FULL_POINTS).sum()))
    return recorded, tapers
