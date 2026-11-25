"""The ``spirograph`` kind of picture (feature 046): the loudest notes of the last few frames drawn as the classic spirograph
curve, a circle rolling inside a circle, one curve for each note.

**The notes and the history.** In every frame the loudest notes (as many as the *Number of notes* setting, 5 to 12) are
tracked, loudest first: ``tracked_notes()`` keeps for each frame the **value** of each (the square root of its strength over the
largest strength of the whole file, 0 to 1) and its **index** (0 to 83 among the 84 drawn notes). One frame's values and indices are a *history
entry*. The picture of a frame draws the last *History length* entries (5 to 12), the frame's own entry the newest: the outer
loop goes through the entries, the oldest first, the inner loop through the notes of an entry, the loudest first, and a curve is
drawn for each step ``(i, j)`` from the value ``j`` and the index ``j`` of entry ``i`` (``window_curves()``). Consecutive pictures
share all but one entry, so the picture flows. In the first frames the entries that exist are used. The values of an entry are
multiplied by ``fade ** age`` (the *History fade* setting, 0.4 to 0.85; the age is 0 for the frame's own entry, 1 for the one
before it, and so on), so the older the entry the smaller its curves and the lower its colors: the newest is the most prominent.

**The curve.** With ``val`` the value, ``loops = (index mod 12) val`` (the index modulo 12 is the note's letter, so the loops follow
the letter, not the octave) and ``rc`` the radius of the big circle, the curve has 1000 points
``X = val (rc cos c1 + loops cos c2)`` and ``Y = val (rc sin c1 + loops sin c2)``, ``c1`` going in 1000 equal steps from 0 to
2 pi and ``c2`` from 0 to 2 pi ``turns``: the small circle turns ``turns`` times while the pen goes once round the big one
(``spiro_curves()``). ``turns`` and ``rc`` follow where the history entry's frame is in the local energy peak (``peak_percents()``,
``pct``: 1 at the top of a peak, 0 at the bottom, so 0.5 is as far from one as from the other): ``turns = 2 * 7 * pct + 6``, from 6
to 20, and ``rc`` is 5 when the frame is closer to the peak than to the bottom (``pct`` above 0.5), 4 (5 - 1) when it is not. A louder
note is a bigger curve and a later letter has wider loops. A value of 0 draws nothing.

**The color.** Only 13 colors of the colormap are used, at the positions ``sqrt(k / 12) * 256`` (``reduced_colors()``); a curve
takes color number ``min(floor(12 val), 12)`` (``color_numbers()``).

**The size.** The farthest point of a curve is the first one (both cosines are 1), ``ext = val (rc + loops)``, and the largest
of that over the file is the file's extent (``file_extent()``); ``pixels_per_unit()`` is the scale at which that extent just
fits, so ``ext * scale`` is how much of the room a curve would fill. Every curve is drawn **between half and the whole of the
full size**: its farthest point is ``R_min + (R_max - R_min) * ext * scale / R_max`` pixels from the center, ``R_max`` being the
room from the center to the nearer edge (less the margin and the widest line, ``full_radius()``) and ``R_min`` a quarter of the
smallest side of the picture, so the smallest curve is always half of the smallest side across and the loudest of the file
fills the picture (``window_curves()``). The pattern is centered and round. The background is black.

**The line.** The line of a curve is ``entry_line_width(age, history)`` pixels wide: 3 (``MAX_LINE_WIDTH``, whatever the history
length) for the picture's own frame and at most 2 for every older entry, falling in equal steps with the age from 2 at age 1 to 1
for the oldest place of the history, each width rounded to a whole number of at least 1, so the newer curves are drawn thicker
and a thick line does not cover the thin ones.

**The drawing.** One ``matplotlib`` ``LineCollection`` for every curve of a frame (each with its own width), on a ``Figure`` that is not a ``pyplot``
figure, so that the pictures can be drawn by several threads at once with the same result (``_frame()``).

This module knows nothing about the audio, the job or the page: the note values, the settings, the colormap and the picture size
are passed in.

Order of operations:
    1. Check the inputs and the three settings -``write_spirograph_frames()`` with ``check_spirograph_settings()`` -
       ``NoteStrengths`` ``(frames, 88)`` (the note values), the colormap, the picture size, the Extra notes setting and the
       beat (``BeatPositions`` ``(frames,)`` or ``None``).
    2. Take the tracked notes of each frame - ``tracked_notes()`` - ``TrackedValues`` ``(frames, count)`` and
       ``LoudestIndices`` ``(frames, count)``: the value (0 to 1) and the index (0 to 83) of each of the ``count`` loudest of
       the first 84 notes (the held notes: ``held_notes.hold_loudest()``), loudest first.
    3. Work out how near each frame is to the top of the local energy peak - ``peak_percents()`` - ``PeakPercents``
       ``(frames,)``: ``1 - beat_distances`` (1 at the top, 0 at the bottom; 1 for every frame without a beat).
    4. Work out the 13 reduced colors - ``reduced_colors()`` - ``ReducedColors`` ``(13, 3)``: the colormap at
       ``sqrt(k / 12) * 256``.
    5. Find the extent of the file and the scale - ``file_extent()`` then ``pixels_per_unit()``: the largest distance of any
       curve from the center in units (with the ``rc`` of its frame), and the pixels a unit is when that curve fills the room
       (``full_radius()``).
    6. For each frame make the curves of its window - ``window_curves()`` (with ``spiro_curves()`` and ``color_numbers()``) -
       ``SpiroCurves`` ``(curves, 1000, 2)`` in pixels (each sized between half and the whole of the full size, its turns and
       ``rc`` from its own entry's ``PeakPercents``), ``ColorNumbers`` ``(curves,)`` and ``CurveWidths`` ``(curves,)`` (5 for
       the newest entry, 4 down to 1 pixel for the older): the last History length entries, oldest first, each entry's values
       multiplied by ``fade ** age``, the notes whose value is above 0.
    7. Draw each frame on its own (a few threads) - ``_frame()`` - all the curves in one ``LineCollection`` in their colors and
       widths on black: ``Pictures`` ``(height, width, 3)``, saved as ``frame_<index>.png``.
"""

import math
import numbers
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from .array_types import (
    ArrayLike,
    BigRadii,
    ColorNumbers,
    CurveExtents,
    CurveTurns,
    CurveWidths,
    LoudestIndices,
    NoteStrengths,
    PeakPercents,
    Pictures,
    ReducedColors,
    SpiroCurves,
    TrackedValues,
)
from .chromatic_decay import beat_distances
from .colormaps import COLORMAP_STEPS, check_beat, check_colormap, lookup_table
from .frame_saving import SAVE_WORKERS
from .held_notes import hold_loudest

RC = 5.0  # the radius of the big circle of a frame closer to the peak than to the bottom (RC - 1 for any other frame)
COLOR_BINS = 12  # the reduced colors are COLOR_BINS + 1 of the colormap
CURVE_STEPS = 1000  # points in a curve
SMALL_TURNS = 7  # half of the range of turns: turns = 2 * SMALL_TURNS * pct + MIN_TURNS, 6 to 20
MIN_TURNS = 6  # the fewest turns of the small circle round the big one (a frame at the bottom of the local energy)
LETTERS = 12  # the letter names: an index modulo 12 is the letter of the note (the loops depend on it, not on the octave)
NOTE_COLUMNS = 84  # the notes of the 12-letter, 7-octave grid: the first 84 of the 88 columns of the note values
VALUE_FACTOR = 12  # yval = VALUE_FACTOR * val
MIN_NOTES = 5  # the fewest tracked notes
MAX_NOTES = 12  # the most
MIN_HISTORY = 5  # the fewest history entries in a picture
MAX_HISTORY = 12  # the most
DEFAULT_NOTES = 8
DEFAULT_HISTORY = 8
MIN_FADE = 0.4  # the smallest History fade: an entry is multiplied by this for each frame it is older (it fades fast)
MAX_FADE = 0.85  # the largest (it fades slowly)
DEFAULT_FADE = 0.7
MARGIN = 10  # pixels kept back from the nearer edge of the picture
MIN_LINE_WIDTH = 1  # pixels: the line of the oldest place of the history ...
MAX_LINE_WIDTH = 3  # ... and 3 for the picture's own frame whatever the history length (every older entry is at most 2); 5 was too thick
MIN_SIZE_DIVISOR = 4  # the smallest curve reaches a quarter of the smallest side from the center: half of it across
DPI = 100  # matplotlib sizes a figure in inches; at this many dots per inch one unit of the axes is one pixel
POINTS_PER_INCH = 72  # a line width of matplotlib is in points
BACKGROUND_COLOR = (0, 0, 0)  # the picture is on black
EPSILON = 1e-9  # keeps floor(12 * (m / 12)) from falling to m - 1 by rounding

NOTES_MESSAGE = f"The number of spirograph notes must be a whole number from {MIN_NOTES} to {MAX_NOTES}."
HISTORY_MESSAGE = f"The history length must be a whole number from {MIN_HISTORY} to {MAX_HISTORY}."
FADE_MESSAGE = f"The history fade must be a number from {MIN_FADE} to {MAX_FADE}."
VALUES_MESSAGE = f"The note values must be a (frames, 88) array of numbers from 0 up, with at least {NOTE_COLUMNS} columns."
SIZE_MESSAGE = "The picture size must be two whole numbers, large enough for the curves."
CURVE_MESSAGE = f"The values must be numbers from 0 to 1 and the indices whole numbers from 0 to {NOTE_COLUMNS - 1}, one index for each value."
PERCENT_MESSAGE = "The peak percentages must be one number from 0 to 1 for each note (or frame), or none."


@dataclass(frozen=True)
class SpirographSettings:
    """The three settings of the Spirograph picture.

    Attributes:
        ``notes``: the number of notes tracked in each frame (curves in a history entry), a whole number from 5 to 12.
        ``history``: the number of history entries (frames) in a picture, a whole number from 5 to 12.
        ``fade``: the History fade, a number from 0.4 to 0.85: the values of a history entry are multiplied by this for each
            frame the entry is older than the picture's own frame, so the newest entry is the most prominent.
    """

    notes: int
    history: int
    fade: float = DEFAULT_FADE


DEFAULT_SPIROGRAPH_SETTINGS = SpirographSettings(DEFAULT_NOTES, DEFAULT_HISTORY, DEFAULT_FADE)


def _whole_number(value: object, low: int, high: int, message: str) -> int:
    """``value`` as an ``int`` when it is a whole number from ``low`` to ``high`` (a bool, a string, a fraction or a
    non-finite number is refused with ``message``)."""
    if (
        isinstance(value, (bool, np.bool_))
        or not isinstance(value, numbers.Real)
        or not np.isfinite(value)
        or int(value) != value
        or not low <= value <= high
    ):
        raise ValueError(message)
    return int(value)


def check_spirograph_notes(value: object) -> int:
    """Return ``value`` as an ``int`` when it is a whole number from 5 to 12 (a bool, a string, a fraction or a non-finite
    number is refused)."""
    return _whole_number(value, MIN_NOTES, MAX_NOTES, NOTES_MESSAGE)


def check_spirograph_history(value: object) -> int:
    """Return ``value`` as an ``int`` when it is a whole number from 5 to 12 (a bool, a string, a fraction or a non-finite
    number is refused)."""
    return _whole_number(value, MIN_HISTORY, MAX_HISTORY, HISTORY_MESSAGE)


def check_spirograph_fade(value: object) -> float:
    """Return ``value`` as a ``float`` when it is a number from 0.4 to 0.85 (a bool, a string or a non-finite number is
    refused)."""
    if (
        isinstance(value, (bool, np.bool_))
        or not isinstance(value, numbers.Real)
        or not math.isfinite(value)
        or not MIN_FADE <= value <= MAX_FADE
    ):
        raise ValueError(FADE_MESSAGE)
    return float(value)


def check_spirograph_settings(settings: object) -> SpirographSettings:
    """Return ``settings`` with its values checked (the whole numbers as ``int``, the fade as ``float``) when it is a
    :class:`SpirographSettings` whose number of notes, history length and history fade are allowed."""
    if not isinstance(settings, SpirographSettings):
        raise ValueError("The Spirograph settings must be a SpirographSettings.")
    return SpirographSettings(
        check_spirograph_notes(settings.notes), check_spirograph_history(settings.history), check_spirograph_fade(settings.fade)
    )


def _check_size(width: object, height: object) -> tuple[int, int]:
    """The picture size as two ``int``; anything that is not two whole numbers of at least 1 is refused."""
    for size in (width, height):
        if isinstance(size, (bool, np.bool_)) or not isinstance(size, numbers.Integral) or size < 1:
            raise ValueError(SIZE_MESSAGE)
    return int(width), int(height)  # type: ignore[call-overload]


def entry_line_width(age: int, history: int) -> int:
    """The width in pixels of the lines of a history entry that is ``age`` frames older than the picture's frame, out of a
    history of ``history`` entries: 3 (``MAX_LINE_WIDTH``, whatever the history) for age 0, and for every older entry at most
    2: 2 for age 1, falling in equal steps to 1 for age ``history - 1``, rounded half up to a whole number and never under 1
    (history 5: 3, 2, 2, 1, 1; history 8: 3, 2, 2, 2, 2, 1, 1, 1; history 12: 3, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1). So an entry
    is always thinner than the newest one, and a thick line does not cover the thinner ones.

    Returns:
        The width as an ``int``, 1 to 3.
    """
    history = check_spirograph_history(history)
    if isinstance(age, (bool, np.bool_)) or not isinstance(age, numbers.Integral) or not 0 <= age < history:
        raise ValueError(f"The age must be a whole number from 0 to {history - 1}.")
    if age == 0:
        return MAX_LINE_WIDTH
    older = MAX_LINE_WIDTH - 1  # the widest line of an older entry, the one at age 1
    width = older - (older - MIN_LINE_WIDTH) * (int(age) - 1) / (history - 2)  # history is at least 5
    return max(MIN_LINE_WIDTH, int(math.floor(width + 0.5)))


def full_radius(width: int, height: int) -> float:
    """The farthest a curve may reach from the center, in pixels: the room from the center to the nearer edge, less the margin
    and the widest line. A picture that leaves less than one pixel is refused (too small for the curves)."""
    width, height = _check_size(width, height)
    room = min(width, height) / 2 - MARGIN - MAX_LINE_WIDTH
    if room < 1:
        raise ValueError(SIZE_MESSAGE)
    return room


def smallest_radius(width: int, height: int) -> float:
    """How far from the center the smallest curve reaches, in pixels: a quarter of the smallest side, so half of the smallest
    side across (and never more than ``full_radius``)."""
    width, height = _check_size(width, height)
    return min(min(width, height) / MIN_SIZE_DIVISOR, full_radius(width, height))


def _check_notes(values: ArrayLike, indices: ArrayLike, ndim: int | None) -> tuple[TrackedValues, LoudestIndices]:
    """The values as float64 and the indices as ``intp``, of one shape (and of ``ndim`` dimensions when it is given);
    anything else is refused.

    Arrays:
        ``values``: ``ArrayLike`` any shape - the value of each note, 0 to 1 (``TrackedValues``).
        ``indices``: ``ArrayLike`` the shape of ``values`` - the index of each note, whole numbers 0 to 83
            (``LoudestIndices``).

    Returns:
        A tuple of the values (``TrackedValues`` shape, float64) and the indices (``LoudestIndices`` shape, ``intp``).
    """
    try:
        vals = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError(CURVE_MESSAGE) from None
    idx = np.asarray(indices)
    if vals.shape != idx.shape or (ndim is not None and vals.ndim != ndim) or idx.dtype.kind not in "iu":
        raise ValueError(CURVE_MESSAGE)
    if vals.size and (
        not np.isfinite(vals).all() or vals.min() < 0 or vals.max() > 1 + EPSILON or idx.min() < 0 or idx.max() >= NOTE_COLUMNS
    ):
        raise ValueError(CURVE_MESSAGE)
    return np.minimum(vals, 1.0), idx.astype(np.intp)


def reduced_colors(colormap: str) -> ReducedColors:
    """The 13 colors that Spirograph takes from ``colormap``: row ``k`` is the colormap's table row at
    ``min(255, floor(sqrt(k / 12) * 256))`` (the position 256 of ``k = 12`` is past the end, so it is the last color).

    Returns:
        ``ReducedColors`` ``(13, 3)`` - the red, green and blue (0 to 255) of color numbers 0 to 12.
    """
    table = lookup_table(check_colormap(colormap))
    steps = np.sqrt(np.arange(COLOR_BINS + 1) / COLOR_BINS) * COLORMAP_STEPS
    positions = np.minimum(COLORMAP_STEPS - 1, np.floor(steps)).astype(np.intp)
    return np.array(table[positions], dtype=np.uint8)


def color_numbers(values: ArrayLike) -> ColorNumbers:
    """Which of the 13 reduced colors each value takes: ``min(floor(12 * value), 12)``.

    A tiny epsilon is added before the floor so that ``m / 12`` takes number ``m`` whatever the rounding of ``m / 12 * 12``;
    a value above 1 (which does not occur) is held at 12.

    Arrays:
        ``values``: ``ArrayLike`` ``(curves,)`` - the value of each curve, 0 or more (``TrackedValues`` of one frame).

    Returns:
        ``ColorNumbers`` ``(curves,)`` - the color number of each curve, 0 to 12.
    """
    try:
        vals = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError(CURVE_MESSAGE) from None
    if vals.ndim != 1 or not np.isfinite(vals).all() or (vals.size and vals.min() < 0):
        raise ValueError(CURVE_MESSAGE)
    return np.minimum(np.floor(VALUE_FACTOR * vals + EPSILON), COLOR_BINS).astype(np.intp)


def _check_percents(percents: ArrayLike | None, count: int) -> PeakPercents:
    """The peak percentages as a float64 array of ``count`` numbers from 0 to 1 (all 1 for ``None``: every one at the top of
    a peak); anything else is refused.

    Arrays:
        ``percents``: ``ArrayLike`` or ``None`` ``(count,)`` - how near each one is to the top of the local energy peak
            (``PeakPercents``).

    Returns:
        ``PeakPercents`` ``(count,)`` - the same numbers as float64.
    """
    if percents is None:
        return np.ones(count)
    try:
        array = np.asarray(percents, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError(PERCENT_MESSAGE) from None
    if array.shape != (count,) or not np.isfinite(array).all() or (array.size and (array.min() < 0 or array.max() > 1)):
        raise ValueError(PERCENT_MESSAGE)
    return array


def peak_percents(beat: ArrayLike | None, frames: int) -> PeakPercents:
    """How near each frame is to the top of the local energy peak: 1 at the top, 0 at the bottom, ``(frames,)``.

    It is ``1 - chromatic_decay.beat_distances(beat)``: the beat (the place of the frame in the local peak, 0 to 1) stretched
    over the range of the beat of the file, because inside the peaks of real music the position hardly falls below about
    0.55, which would leave the percentage always above a half. So the highest position of the file is 1, the bottom of the
    beat (and every frame outside a peak) is 0. Without a beat (``None``) every frame is 1. The input is not changed.

    Arrays:
        ``beat``: ``ArrayLike`` or ``None`` ``(frames,)`` - the place of each frame in the local energy peak, 0 to 1
            (``BeatPositions``).

    Returns:
        ``PeakPercents`` ``(frames,)`` - from 0 (the bottom of the beat) to 1 (the top).
    """
    if isinstance(frames, (bool, np.bool_)) or not isinstance(frames, numbers.Integral) or frames < 0:
        raise ValueError("The number of frames must be a whole number of 0 or more.")
    if beat is None:
        return np.ones(int(frames))
    return np.clip(1.0 - beat_distances(check_beat(beat, int(frames))), 0.0, 1.0)


def turns_of(percents: ArrayLike) -> CurveTurns:
    """How many times the small circle turns while the pen goes once round the big one: ``2 * 7 * pct + 6``, from 6 (at the
    bottom of the local energy) to 20 (at the top of a peak), not rounded (so a curve is closed only at a whole number).

    Arrays:
        ``percents``: ``ArrayLike`` any shape - the peak percentages, 0 to 1 (``PeakPercents``).

    Returns:
        The turns, float64, the shape of ``percents``.
    """
    return 2 * SMALL_TURNS * np.asarray(percents, dtype=np.float64) + MIN_TURNS


def big_radii(percents: ArrayLike) -> BigRadii:
    """The radius ``rc`` of the big circle: ``RC`` (5) when the frame is closer to the top of the peak than to the bottom (the
    percentage is above 0.5), ``RC - 1`` (4) otherwise (exactly half way is not closer to the peak).

    Arrays:
        ``percents``: ``ArrayLike`` any shape - the peak percentages, 0 to 1 (``PeakPercents``).

    Returns:
        The radii, float64, the shape of ``percents``.
    """
    return np.where(np.asarray(percents, dtype=np.float64) > 0.5, RC, RC - 1.0)


def _extents(values: TrackedValues, indices: LoudestIndices, percents: PeakPercents) -> CurveExtents:
    """The farthest point of each curve from the center, in units: ``val (rc + (index mod 12) val)``, which is the first point
    and, by the triangle inequality, the farthest.

    Arrays:
        ``values``: ``TrackedValues`` ``(curves,)`` - the value of each curve, above 0 for one that sounds.
        ``indices``: ``LoudestIndices`` ``(curves,)`` - the index of each curve.
        ``percents``: ``PeakPercents`` ``(curves,)`` - how near the frame of each curve is to the top of the peak.

    Returns:
        ``CurveExtents`` ``(curves,)`` - the farthest point of each curve, in units.
    """
    return values * (big_radii(percents) + np.mod(indices, LETTERS) * values)


def spiro_curves(values: ArrayLike, indices: ArrayLike, percents: ArrayLike | None = None) -> SpiroCurves:
    """The spirograph curve of each note, in the units of the formula: ``(curves, 1000, 2)``.

    With ``val`` the value, ``loops = (index mod 12) val`` and ``rc`` (``big_radii()``) and ``turns`` (``turns_of()``) from the
    note's percentage in the peak, the point ``k`` is ``X = val (rc cos c1 + loops cos c2)`` and ``Y = val (rc sin c1 + loops
    sin c2)``, ``c1`` from 0 to 2 pi and ``c2`` from 0 to 2 pi ``turns`` in 1000 equal steps (both ends included). The first
    point is the farthest from the center. A value of 0 gives a curve that is all at the center.

    Arrays:
        ``values``: ``ArrayLike`` ``(curves,)`` - the value of each note, 0 to 1 (``TrackedValues`` of one frame).
        ``indices``: ``ArrayLike`` ``(curves,)`` - the index of each note, whole numbers 0 to 83 (``LoudestIndices`` of one
            frame).
        ``percents``: ``ArrayLike`` or ``None`` ``(curves,)`` - how near the frame of each note is to the top of the local
            energy peak, 0 to 1 (``PeakPercents`` of each curve's frame); ``None`` is 1 for every curve.

    Returns:
        ``SpiroCurves`` ``(curves, 1000, 2)`` - the x and y of the 1000 points of each curve, in units, y up.
    """
    vals, idx = _check_notes(values, indices, 1)
    near = _check_percents(percents, vals.shape[0])
    c1 = np.linspace(0.0, 2 * np.pi, CURVE_STEPS)
    c2 = c1[None, :] * turns_of(near)[:, None]  # (curves, 1000): 0 to 2 pi turns
    loops = (np.mod(idx, LETTERS) * vals)[:, None]
    rc = big_radii(near)[:, None]
    scale = vals[:, None]
    x = scale * (rc * np.cos(c1)[None, :] + loops * np.cos(c2))
    y = scale * (rc * np.sin(c1)[None, :] + loops * np.sin(c2))
    return np.stack([x, y], axis=-1)


def file_extent(values: ArrayLike, indices: ArrayLike, percents: ArrayLike | None = None) -> float:
    """The largest distance of any curve of the file from the center, in units: the maximum of ``val (rc + (index mod 12) val)``,
    with the ``rc`` of the curve's frame (``big_radii()``).

    The farthest point of a curve is the first (``c1 = c2 = 0``: both cosines are 1 and both sines 0), and no point of a curve
    can be farther (the triangle inequality), so no curve has to be sampled.

    Arrays:
        ``values``: ``ArrayLike`` ``(frames, count)`` - the value of every tracked note of every frame (``TrackedValues``).
        ``indices``: ``ArrayLike`` ``(frames, count)`` - their indices (``LoudestIndices``).
        ``percents``: ``ArrayLike`` or ``None`` ``(frames,)`` - how near each frame is to the top of the local energy peak
            (``PeakPercents``); ``None`` is 1 for every frame.

    Returns:
        The extent as a ``float``: 0 when no note sounds.
    """
    vals, idx = _check_notes(values, indices, 2)
    near = _check_percents(percents, vals.shape[0])
    if not vals.size:
        return 0.0
    return float(_extents(vals.reshape(-1), idx.reshape(-1), np.repeat(near, vals.shape[1])).max())


def pixels_per_unit(extent: float, width: int, height: int) -> float:
    """The pixels that one unit of the formula is in the picture, so that a curve of ``extent`` just fills the room
    (``full_radius()``: from the center to the nearer edge, less the margin and the widest line), over ``extent``.

    The pattern is round, so the nearer edge decides. A picture that leaves less than one pixel of room is refused (it is
    too small for the curves); an extent of 0 (nothing sounds) gives a scale of 0.

    Returns:
        The scale as a ``float``, pixels a unit.
    """
    width, height = _check_size(width, height)
    if isinstance(extent, (bool, np.bool_)) or not isinstance(extent, numbers.Real) or not math.isfinite(extent) or extent < 0:
        raise ValueError("The extent must be a finite number of 0 or more.")
    room = full_radius(width, height)
    return 0.0 if extent == 0 else room / float(extent)


def _frame(curves: SpiroCurves, colors: ArrayLike, width: int, height: int, widths: ArrayLike | None = None) -> Pictures:
    """One picture, a ``uint8`` array ``(height, width, 3)``: the curves in one ``LineCollection``, each in its color and its
    width, on black, the first curve first (so a later curve lies over an earlier one).

    The figure is a matplotlib ``Figure`` (not a ``pyplot`` figure, so that several threads can draw at once) whose axes fill
    it and whose units are pixels with y pointing down; a width of ``w`` pixels is ``w * 72 / 100`` points. No curves is a black
    picture.

    Arrays:
        ``curves``: ``SpiroCurves`` ``(curves, points, 2)`` - the x and y of each point of each curve, in pixels from the
            left and the top (1000 points each from ``window_curves``).
        ``colors``: ``ArrayLike`` ``(curves, 3)`` - the red, green and blue (0 to 255) of each curve.
        ``widths``: ``ArrayLike`` ``(curves,)`` or ``None`` - the width of each curve's line in pixels (``CurveWidths``); ``None``
            is the thinnest line, 1 pixel, for every curve.

    Returns:
        ``Pictures`` ``(height, width, 3)`` - the picture.
    """
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.collections import LineCollection
    from matplotlib.figure import Figure

    width, height = _check_size(width, height)
    paths = np.asarray(curves, dtype=np.float64)
    rgb = np.asarray(colors)
    if paths.ndim != 3 or paths.shape[2] != 2 or rgb.shape != (paths.shape[0], 3):
        raise ValueError("The curves must be (curves, points, 2) and the colors one (red, green, blue) row for each curve.")
    line_widths = np.full(len(paths), float(MIN_LINE_WIDTH)) if widths is None else np.asarray(widths, dtype=np.float64)
    if line_widths.shape != (len(paths),) or not np.isfinite(line_widths).all() or (line_widths <= 0).any():
        raise ValueError("The widths must be one number above 0 for each curve.")
    figure = Figure(figsize=(width / DPI, height / DPI), dpi=DPI, facecolor=tuple(c / 255 for c in BACKGROUND_COLOR))
    canvas = FigureCanvasAgg(figure)
    axes = figure.add_axes((0, 0, 1, 1))
    axes.set_xlim(0, width)
    axes.set_ylim(height, 0)
    axes.axis("off")
    if len(paths):
        axes.add_collection(
            LineCollection(
                paths,
                linewidths=line_widths * POINTS_PER_INCH / DPI,
                colors=rgb.astype(np.float64) / 255,
                capstyle="round",
                joinstyle="round",
            )
        )
    canvas.draw()
    picture = np.asarray(canvas.buffer_rgba())[:, :, :3].copy()
    if picture.shape != (height, width, 3):
        raise ValueError(SIZE_MESSAGE)
    return picture


def _check_values(values: object) -> NoteStrengths:
    """The note values as a float64 ``(frames, columns)`` array; anything else is refused.

    Arrays:
        ``values``: ``ArrayLike`` ``(frames, 84 or more)`` - the strength of each note in each frame.

    Returns:
        ``NoteStrengths`` ``(frames, columns)`` - the same values as float64, all finite and at least 0.
    """
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError(VALUES_MESSAGE) from None
    if array.ndim != 2 or array.shape[1] < NOTE_COLUMNS or not np.isfinite(array).all() or (array < 0).any():
        raise ValueError(VALUES_MESSAGE)
    return array


def tracked_notes(values: ArrayLike, count: int, extra: int = 0) -> tuple[TrackedValues, LoudestIndices]:
    """The ``count`` loudest notes of every frame, with their values and their indices: two arrays ``(frames, count)``.

    Only the first 84 columns are notes that are drawn. The notes are the held notes (``held_notes.hold_loudest()``): with
    ``extra`` 0 the ``count`` loudest notes of the frame (a tie goes to the lower note), with ``extra`` above 0 a note that was
    among them in the frame before keeps its place while it is within the loudest ``count + extra`` (feature 044). The value of
    a place is the **square root** of the note's strength over the largest strength of all the columns of the whole file (the
    square root keeps the quiet notes from being tiny: the values cluster toward 1, so the pictures are larger), so the loudest
    note of the file is 1; a place with no sounding note has value 0 (nothing is drawn for it). The input is not changed.

    Arrays:
        ``values``: ``ArrayLike`` ``(frames, 84 or more)`` - the strength of each note in each frame (``NoteStrengths``).

    Returns:
        A tuple of ``TrackedValues`` ``(frames, count)`` (the value of each tracked note, 0 to 1, loudest first; the square root of
        its strength over the file's largest) and
        ``LoudestIndices`` ``(frames, count)`` (the index, 0 to 83, of each; for a place with value 0 the index of a note that
        does not sound).
    """
    count = check_spirograph_notes(count)
    strengths = _check_values(values)
    shown = strengths[:, :NOTE_COLUMNS]
    order = hold_loudest(shown, count, extra)  # LoudestIndices (frames, count)
    peak = float(strengths.max()) if strengths.size else 0.0
    taken = np.take_along_axis(shown, order, axis=1)
    return (np.sqrt(taken / peak) if peak > 0 else np.zeros(taken.shape)), order.astype(np.intp)


def window_curves(
    values: ArrayLike,
    indices: ArrayLike,
    frame: int,
    history: int,
    scale: float,
    width: int,
    height: int,
    fade: float = DEFAULT_FADE,
    percents: ArrayLike | None = None,
) -> tuple[SpiroCurves, ColorNumbers, CurveWidths]:
    """The curves of the picture of one frame, in pixels, with their color numbers.

    The window is the history entries (rows) ``max(0, frame - history + 1)`` to ``frame``, so the picture uses the last
    ``history`` entries, the frame's own the newest (fewer in the first frames). The values of an entry are multiplied by
    ``fade ** age`` where the age is how many frames older than ``frame`` the entry is (0 for the frame's own entry, so it keeps
    its values and is the most prominent; an older curve is smaller, with narrower loops and a color lower in the colormap). The
    outer loop goes through the entries, the oldest first, the inner loop through the places of an entry, the loudest first; the
    curve of step ``(i, j)`` is made from the value ``j`` and the index ``j`` of entry ``i`` and no other. A place whose value is
    not above 0 is left out.

    **Shape.** The turns and the ``rc`` of a curve come from the percentage in the peak of its own entry's frame
    (``percents[row]``, see ``peak_percents()``): a curve is made from its own entry and no other, so an entry keeps its shape in
    the pictures it is in.

    **Size.** A curve's farthest point is ``ext = val (rc + (index mod 12) val)`` units from the center (the faded value); with ``scale``
    the pixels a unit is when the largest curve of the file fills the room (``pixels_per_unit()``), ``share = min(1, ext *
    scale / full_radius)`` is how much of the room it would fill, and the curve is drawn so that its farthest point is
    ``smallest_radius + (full_radius - smallest_radius) * share`` pixels from the center: never under half of the smallest side
    across, the loudest curve of the file the whole room. The shape is the formula's, only its size is set this way. A point of
    the formula ``(X, Y)`` of such a curve is at the pixel ``(width / 2 + k X, height / 2 - k Y)`` with ``k = radius / ext``.

    **Line.** The width of the line of a curve is ``entry_line_width(age, history)`` of its entry.

    Arrays:
        ``values``: ``ArrayLike`` ``(frames, count)`` - the value of every tracked note of every frame (``TrackedValues``).
        ``indices``: ``ArrayLike`` ``(frames, count)`` - their indices (``LoudestIndices``).
        ``percents``: ``ArrayLike`` or ``None`` ``(frames,)`` - how near each frame is to the top of the local energy peak
            (``PeakPercents``); ``None`` is 1 for every frame.

    Returns:
        A tuple of ``SpiroCurves`` ``(curves, 1000, 2)`` (in pixels, in drawing order), ``ColorNumbers`` ``(curves,)`` and
        ``CurveWidths`` ``(curves,)`` (the line width in pixels of each curve).
    """
    vals, idx = _check_notes(values, indices, 2)
    history = check_spirograph_history(history)
    fade = check_spirograph_fade(fade)
    near = _check_percents(percents, len(vals))
    width, height = _check_size(width, height)
    if isinstance(frame, (bool, np.bool_)) or not isinstance(frame, numbers.Integral) or not 0 <= frame < len(vals):
        raise ValueError(f"The frame must be a whole number from 0 to {len(vals) - 1}.")
    if isinstance(scale, (bool, np.bool_)) or not isinstance(scale, numbers.Real) or not math.isfinite(scale) or scale < 0:
        raise ValueError("The scale must be a finite number of 0 or more.")
    first = max(0, int(frame) - history + 1)
    fades = fade ** np.arange(int(frame) - first, -1, -1)  # the oldest entry first: age frame - first, ..., 1, 0
    window_values = (vals[first : int(frame) + 1] * fades[:, None]).reshape(-1)  # row by row: the oldest entry first, the loudest place first
    window_indices = idx[first : int(frame) + 1].reshape(-1)
    ages = np.repeat(np.arange(int(frame) - first, -1, -1), vals.shape[1])  # the age of each (entry, place), in the same order
    window_percents = np.repeat(near[first : int(frame) + 1], vals.shape[1])  # the peak percentage of each (entry, place)'s frame
    sounding = window_values > 0
    shown_values, shown_indices, shown_percents = window_values[sounding], window_indices[sounding], window_percents[sounding]
    curves = spiro_curves(shown_values, shown_indices, shown_percents)
    extents = _extents(shown_values, shown_indices, shown_percents)  # > 0: the farthest point
    full, smallest = full_radius(width, height), smallest_radius(width, height)
    share = np.minimum(1.0, extents * scale / full)
    sizes = (smallest + (full - smallest) * share) / extents  # pixels a unit for each curve
    pixels = np.empty_like(curves)
    pixels[..., 0] = width / 2 + sizes[:, None] * curves[..., 0]
    pixels[..., 1] = height / 2 - sizes[:, None] * curves[..., 1]
    line_widths = np.array([entry_line_width(int(age), history) for age in ages[sounding]], dtype=np.float64)
    return pixels, color_numbers(shown_values), line_widths


def write_spirograph_frames(
    values: ArrayLike,
    settings: SpirographSettings,
    colormap: str,
    directory: Path,
    width: int,
    height: int,
    extra_notes: int = 0,
    beat: ArrayLike | None = None,
) -> None:
    """Save one PNG of ``width`` x ``height`` pixels per frame as ``frame_000000.png`` and up.

    Everything is checked before anything is written (nothing is created for a refusal). The tracked notes, the reduced colors
    and the scale of the whole file are made once, then each frame is drawn on its own (a few threads, as for the other types).

    Arrays:
        ``values``: ``ArrayLike`` ``(frames, 84 or more)`` - the strength of each note in each frame (``NoteStrengths``).

    ``extra_notes`` is the Extra notes setting k, 0 (the default: the plain loudest notes) to the number of notes: a note that
    is still among the loudest ``notes + extra_notes`` keeps its place (see ``held_notes``).

    ``beat`` (``BeatPositions`` ``(frames,)``, the place of each frame in the local energy peak, 0 to 1, or ``None``) sets the
    turns and the ``rc`` of the curves of each frame's entry (``peak_percents()``); without one every frame is at the top of a peak.
    """
    settings = check_spirograph_settings(settings)
    colormap = check_colormap(colormap)
    width, height = _check_size(width, height)
    tracked_values, tracked_indices = tracked_notes(values, settings.notes, extra_notes)
    percents = peak_percents(beat, len(tracked_values))  # refuses a beat that is not one number from 0 to 1 for each frame
    scale = pixels_per_unit(file_extent(tracked_values, tracked_indices, percents), width, height)  # refuses a picture that is too small
    colors = reduced_colors(colormap)
    directory.mkdir(parents=True, exist_ok=True)

    def write(index: int) -> None:
        curves, numbers_of_colors, line_widths = window_curves(
            tracked_values, tracked_indices, index, settings.history, scale, width, height, settings.fade, percents
        )
        picture = _frame(curves, colors[numbers_of_colors], width, height, line_widths)
        Image.fromarray(picture, "RGB").save(directory / f"frame_{index:06d}.png", compress_level=1)

    with ThreadPoolExecutor(max_workers=SAVE_WORKERS) as pool:
        for future in [pool.submit(write, index) for index in range(len(tracked_values))]:
            future.result()  # raises the first error of a worker, if there was one
