"""The ``polychord`` kind of picture (feature 042): the loudest notes of a frame drawn as a chain of straight links that
starts at the center and bends by the circle of fifths, repeated as copies turned 30 degrees.

**The figure.** In each frame the loudest notes (as many as the *Number of notes* setting, 5 to 8) are taken, loudest
first, each reduced to its letter (its chromatic tone, whatever its octave). Each note is one **link**, a straight piece
of line. The first link starts at the center of the picture and points along the **starting angle**; every next link
starts where the previous one ended, and its direction is the previous link's direction **turned by 22.5 degrees for
every step of a fifth** from the previous link's letter to its own (``link_turns``), so the 12 steps of the circle of
fifths make 270 degrees, not 360, and the turns are not so sharp: a fifth up is +22.5, a fourth up is -22.5, the same
letter is 0 (straight on), and the tritone is 135 (backwards, but not all the way). Angles are in degrees, clockwise
from straight up, as the ring of fifths of ``chromatic_decay`` is laid out. The pictures are wider than they are high,
so every link is then squeezed to 2/3 of its width and 1/2 of its height (``X_SCALE`` and ``Y_SCALE``): a figure is an
ellipse that follows the shape of the picture. A link is thick where it starts and thinner where it ends,
and it ends as wide as the next link starts, so the figure thins from the center outward (``figure_segments``: each link
is cut into a few short pieces whose widths step down, because one ``LineCollection`` gives one width to each piece).

**The copies.** The figure is drawn again, turned a further 30 degrees from the one before, around the same center, as
many times as the beat says: the *Copies (maximum)* at the top of a local peak and the *Copies (minimum)* at the bottom
of the beat (``copy_counts``, from the beat the other types use). The first copy of frame ``t`` starts at the
**rotation** (degrees a second) times the time of the frame (``start_angles``), so the whole picture turns.

**The color.** Every link of a frame is one color, taken from the colormap by the **current tempo** that the tempo
finder makes of the local peaks (``frame_tempos``, from 60 to 156 beats a minute; 120 before the first peak): the
slowest tempo is the first color and the fastest the last (``tempo_colors``). The background is black.

**The drawing.** One ``matplotlib`` ``LineCollection`` for every piece of every copy, on a ``Figure`` that is not a
``pyplot`` figure, so that the pictures can be drawn by several threads at once with the same result (``_frame``).

This module knows nothing about the audio, the job or the page: the note values, the beat, the tempos, the
settings, the colormap and the picture size are passed in.

Order of operations:
    1. Check the inputs and the four settings - ``write_polychord_frames()`` with ``check_polychord_settings()`` -
       ``NoteStrengths`` ``(frames, 88)`` (the note values), ``BeatPositions`` ``(frames,)`` or ``None``,
       ``FrameTempos`` ``(frames,)`` (from ``frame_tempos()``), and a picture big enough for a figure.
    2. Take the loudest notes of each frame as letters - ``loudest_letters()`` - ``LoudLetters`` ``(frames, count)``:
       the letter of each of the ``count`` loudest of the first 84 notes (the held notes: ``held_notes.hold_loudest()``,
       ``LoudestIndices`` ``(frames, count)``), loudest first, -1 where fewer sound.
    3. Work out the turn of each link - ``link_turns()`` - ``LinkTurns`` ``(frames, count)``: 22.5 degrees for every
       step of a fifth from the previous link's letter (0 for the first link).
    4. Work out how many copies each frame has - ``copy_counts()`` (with ``chromatic_decay.beat_distances()``) -
       ``CopyCounts`` ``(frames,)``: from the minimum at the bottom of the beat to the maximum at its top.
    5. Work out where each frame's figure starts - ``start_angles()`` - ``StartAngles`` ``(frames,)``: the rotation
       times the time of the frame.
    6. Take the color of each frame from its tempo - ``tempo_colors()`` - ``FigureColors`` ``(frames, 3)``: the first
       color of the colormap at 60 beats a minute, the last at 156.
    7. Draw each frame on its own (a few threads) - ``_frame()`` - make the pieces of every copy of the figure with
       ``figure_segments()`` (``LinkSegments`` ``(segments, 2, 2)`` and ``LinkWidths`` ``(segments,)``, using
       ``link_length()``), put them in one ``LineCollection`` in the frame's color: ``Pictures`` ``(height, width, 3)``,
       saved as ``frame_<index>.png``.
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
    BeatPositions,
    CopyCounts,
    FigureColors,
    FrameTempos,
    LinkSegments,
    LinkTurns,
    LinkWidths,
    LoudLetters,
    NoteStrengths,
    Pictures,
    Rgb,
    StartAngles,
)
from .chromatic_decay import FIFTH, FIRST_LETTER_AT_TOP, LETTERS, _check_beat, beat_distances
from .colormaps import COLORMAP_STEPS, check_colormap, lookup_table
from .held_notes import hold_loudest
from .frame_saving import SAVE_WORKERS
from .local_peaks import LocalPeaks
from .tempo_finder import HIGH_LIMIT, LOW_LIMIT, START_TEMPO, find_tempo

NOTE_COLUMNS = 84  # the notes of the 12-letter, 7-octave grid: the first 84 of the 88 columns of the note values
MARGIN = 10  # pixels kept back from the nearer edge of the picture when the length of a link is worked out
LENGTH_FACTOR = 1.7  # links are this much longer than the room, as a figure bends at almost every link
PIECES_PER_LINK = 6  # a link is cut into this many pieces, each with its own width, so that the width steps down in it
START_WIDTH_DIVISOR = 60  # the width at the center is the picture's height over this (6.7 pixels on a 400 high picture)
END_WIDTH_SHARE = 0.2  # the width at the end of the last link, as a share of the width at the center
MIN_WIDTH = 1.0  # pixels: no piece is thinner
MIN_LINK_LENGTH = 1.0  # pixels: a picture where a link would be shorter is too small
DPI = 100  # matplotlib sizes a figure in inches; at this many dots per inch one unit of the axes is one pixel
POINTS_PER_INCH = 72  # a line width of matplotlib is in points
BACKGROUND_COLOR = (0, 0, 0)  # the picture is on black
SIZE_MESSAGE = "The picture size must be two whole numbers, large enough for a figure."
VALUES_MESSAGE = f"The note values must be a (frames, 88) array of numbers from 0 up, with at least {NOTE_COLUMNS} columns."
LETTERS_MESSAGE = f"The letters must be whole numbers from -1 to {LETTERS - 1}."
MIN_NOTES = 5  # the fewest links in a figure
MAX_NOTES = 8  # the most links in a figure
MIN_COPIES = 1  # the fewest copies of a figure in a picture
MAX_COPIES = 12  # the most: 12 copies of 30 degrees make a full turn, so no copy lies exactly over another
MAX_ROTATION = 360.0  # degrees a second, either way
DEFAULT_NOTES = 6
DEFAULT_MIN_COPIES = 3
DEFAULT_MAX_COPIES = 12
DEFAULT_ROTATION = 15.0
COPY_TURN = 30.0  # degrees between one copy of the figure and the next
STEP_TURN = 22.5  # degrees of turn for every step of a fifth between the letters of two links: 12 steps are 270 degrees
X_SCALE = 2 / 3  # every link is this share of its width in the picture: the pictures are wider than they are high
Y_SCALE = 1 / 2  # and this share of its height

NOTES_MESSAGE = f"The number of notes must be a whole number from {MIN_NOTES} to {MAX_NOTES}."
MIN_COPIES_MESSAGE = f"The minimum number of copies must be a whole number from {MIN_COPIES} to {MAX_COPIES}."
MAX_COPIES_MESSAGE = f"The maximum number of copies must be a whole number from {MIN_COPIES} to {MAX_COPIES}."
COPIES_ORDER_MESSAGE = "The maximum number of copies must not be less than the minimum."
ROTATION_MESSAGE = f"The rotation must be a number from -{MAX_ROTATION:g} to {MAX_ROTATION:g} degrees a second."


@dataclass(frozen=True)
class PolychordSettings:
    """The four settings of the Polychord picture.

    Attributes:
        ``notes``: the number of links in a figure, a whole number from 5 to 8.
        ``min_copies``: the number of copies at the bottom of the beat, a whole number from 1 to 12.
        ``max_copies``: the number of copies at the top of a peak, a whole number from 1 to 12, not less than
            ``min_copies``.
        ``rotation``: how fast the whole picture turns, in degrees a second (negative turns the other way).
    """

    notes: int
    min_copies: int
    max_copies: int
    rotation: float


DEFAULT_POLYCHORD_SETTINGS = PolychordSettings(DEFAULT_NOTES, DEFAULT_MIN_COPIES, DEFAULT_MAX_COPIES, DEFAULT_ROTATION)


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


def check_polychord_notes(value: object) -> int:
    """Return ``value`` as an ``int`` when it is a whole number from 5 to 8 (a bool, a string, a fraction or a
    non-finite number is refused)."""
    return _whole_number(value, MIN_NOTES, MAX_NOTES, NOTES_MESSAGE)


def check_polychord_copies(value: object, which: str) -> int:
    """Return ``value`` as an ``int`` when it is a whole number from 1 to 12; ``which`` is ``"minimum"`` or
    ``"maximum"`` and chooses the message that a refusal carries."""
    return _whole_number(value, MIN_COPIES, MAX_COPIES, MIN_COPIES_MESSAGE if which == "minimum" else MAX_COPIES_MESSAGE)


def check_polychord_rotation(value: object) -> float:
    """Return ``value`` as a ``float`` when it is a finite number from -360 to 360 (a bool, a string or a non-finite
    number is refused)."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Real) or not np.isfinite(value):
        raise ValueError(ROTATION_MESSAGE)
    if not -MAX_ROTATION <= value <= MAX_ROTATION:
        raise ValueError(ROTATION_MESSAGE)
    return float(value)


def check_polychord_settings(settings: object) -> PolychordSettings:
    """Return ``settings`` with every value checked (and the whole numbers as ``int``) when it is a
    :class:`PolychordSettings` whose four values are allowed and whose maximum number of copies is not less than the
    minimum."""
    if not isinstance(settings, PolychordSettings):
        raise ValueError("The Polychord settings must be a PolychordSettings.")
    notes = check_polychord_notes(settings.notes)
    low = check_polychord_copies(settings.min_copies, "minimum")
    high = check_polychord_copies(settings.max_copies, "maximum")
    if high < low:
        raise ValueError(COPIES_ORDER_MESSAGE)
    return PolychordSettings(notes, low, high, check_polychord_rotation(settings.rotation))


def _check_size(width: object, height: object) -> tuple[int, int]:
    """The picture size as two ``int``; anything that is not two whole numbers of at least 1 is refused."""
    for size in (width, height):
        if isinstance(size, (bool, np.bool_)) or not isinstance(size, numbers.Integral) or size < 1:
            raise ValueError(SIZE_MESSAGE)
    return int(width), int(height)  # type: ignore[call-overload]


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


def _check_letters(letters: object) -> LoudLetters:
    """The letters as an integer ``(frames, count)`` array of whole numbers from -1 to 11; anything else is refused.

    Arrays:
        ``letters``: ``ArrayLike`` ``(frames, count)`` - the letter of each link of each frame, -1 for a missing link.

    Returns:
        ``LoudLetters`` ``(frames, count)`` - the same letters as ``intp``.
    """
    array = np.asarray(letters)
    if array.ndim != 2 or array.dtype.kind not in "iu" or array.size and (array.min() < -1 or array.max() >= LETTERS):
        raise ValueError(LETTERS_MESSAGE)
    return array.astype(np.intp)


def loudest_letters(values: ArrayLike, count: int, extra: int = 0) -> LoudLetters:
    """The letters of the ``count`` loudest notes of every frame, loudest first: ``(frames, count)``.

    Only the first 84 columns are notes of a letter (note ``j`` is the letter ``j mod 12``, 0 for A, as in
    ``chromatic_decay.letter_energies``); the same letter can appear twice, from two octaves. A tie in loudness goes to
    the lower note, so a file always gives the same letters. With ``extra`` above 0 the notes are the held notes: a note that
    was among the loudest in the frame before keeps its place while it is within the loudest ``count + extra`` (see
    ``held_notes``). A note whose value is not above 0 does not sound and is not
    used: the frame gets -1 for it, and a frame with no sound is all -1. The input is not changed.

    Arrays:
        ``values``: ``ArrayLike`` ``(frames, 84 or more)`` - the strength of each note in each frame
            (``NoteStrengths``).
        ``extra``: the Extra notes setting k, 0 (the default: the old ``count`` loudest) to ``count``.

    Returns:
        ``LoudLetters`` ``(frames, count)`` - the letter (0 is A, up to 11) of each of the ``count`` loudest notes of
        each frame, loudest first, -1 where fewer notes than ``count`` sound.
    """
    count = check_polychord_notes(count)
    shown = _check_values(values)[:, :NOTE_COLUMNS]
    order = hold_loudest(shown, count, extra)  # LoudestIndices (frames, count)
    sounding = np.take_along_axis(shown, order, axis=1) > 0
    return np.where(sounding, order % LETTERS, -1).astype(np.intp)


def link_turns(letters: ArrayLike) -> LinkTurns:
    """How much every link turns from the link before it, in degrees, clockwise positive: ``(frames, count)``.

    The first link has no turn (it points along the starting angle). A later link turns by 22.5 degrees for every
    step of a fifth from the previous link's letter to its own, the shorter way round the circle of the 12 letters, so
    from -112.5 to +135: a fifth up is +22.5, a fourth up (a fifth down) -22.5, the same letter 0 (straight on), and
    the tritone 135 (backwards, but not all the way). The turn is measured from the previous link's letter, whatever
    the loudest note was. A missing link (-1) has no turn, and the links after it have none either.

    Arrays:
        ``letters``: ``ArrayLike`` ``(frames, count)`` - the letter of each link of each frame (``LoudLetters``), -1 for
            a missing link.

    Returns:
        ``LinkTurns`` ``(frames, count)`` - the turn in degrees of each link from the one before it.
    """
    letters = _check_letters(letters)
    turns = np.zeros(letters.shape, dtype=np.float64)
    if letters.shape[1] > 1:
        places = (FIFTH * (letters - FIRST_LETTER_AT_TOP)) % LETTERS  # the place on the circle of fifths: C is 0
        steps = ((places[:, 1:] - places[:, :-1] + LETTERS // 2 - 1) % LETTERS) - (LETTERS // 2 - 1)
        present = (letters[:, 1:] >= 0) & (letters[:, :-1] >= 0)
        turns[:, 1:] = np.where(present, STEP_TURN * steps, 0.0)
    return turns


def _check_frame_rate(frame_rate: object) -> float:
    """The frame rate as a ``float``; anything that is not a finite number above 0 is refused."""
    if isinstance(frame_rate, (bool, np.bool_)) or not isinstance(frame_rate, numbers.Real) or not math.isfinite(frame_rate) or frame_rate <= 0:
        raise ValueError("The frame rate must be a positive number.")
    return float(frame_rate)


def _check_frames(frames: object) -> int:
    """The number of frames as an ``int``; anything that is not a whole number of at least 0 is refused."""
    if isinstance(frames, (bool, np.bool_)) or not isinstance(frames, numbers.Integral) or frames < 0:
        raise ValueError("The number of frames must be a whole number of at least 0.")
    return int(frames)


def copy_counts(beat: ArrayLike | None, min_copies: int, max_copies: int, frames: int | None = None) -> CopyCounts:
    """How many copies of the figure every frame has: ``(frames,)`` whole numbers from ``min_copies`` to ``max_copies``.

    ``position = 1 - chromatic_decay.beat_distances(beat)`` is 1 at the top of the beat of the file (its highest
    position inside a peak), 0 at its bottom (the 1st percentile of the positions inside the peaks) and for a frame
    outside every peak, in a straight line between; the copies are ``floor(min + position x (max - min) + 0.5)``. With
    no beat (``None``) every frame has ``min_copies``, for ``frames`` frames (required then).

    Arrays:
        ``beat``: ``ArrayLike`` ``(frames,)`` or ``None`` - the place of each frame in the local energy peak, 0 to 1
            (``BeatPositions``).

    Returns:
        ``CopyCounts`` ``(frames,)`` - the number of copies of the figure in each frame.
    """
    low = check_polychord_copies(min_copies, "minimum")
    high = check_polychord_copies(max_copies, "maximum")
    if high < low:
        raise ValueError(COPIES_ORDER_MESSAGE)
    if beat is None:
        if frames is None:
            raise ValueError("The number of frames is needed when there is no beat.")
        return np.full(_check_frames(frames), low, dtype=np.intp)
    position = 1.0 - beat_distances(beat)
    return np.floor(low + position * (high - low) + 0.5).astype(np.intp)


def start_angles(rotation: float, frame_rate: float, frames: int) -> StartAngles:
    """The angle at which the figure of every frame starts, in degrees clockwise from straight up: ``(frames,)``.

    It is the rotation (degrees a second) times the time of the frame in seconds, ``index / frame_rate`` (frame 0 is at
    0 degrees), so consecutive frames differ by ``rotation / frame_rate``.

    Returns:
        ``StartAngles`` ``(frames,)`` - the starting angle of each frame, in degrees (not wrapped).
    """
    rotation = check_polychord_rotation(rotation)
    return rotation * np.arange(_check_frames(frames)) / _check_frame_rate(frame_rate)


@dataclass(frozen=True)
class PolychordData:
    """What the job measures for a Polychord picture besides the beat: the tempo of every frame and the frame rate.

    Attributes:
        ``tempos``: ``FrameTempos`` ``(frames,)`` - the current tempo at the middle of each frame, in beats per minute,
            from 60 to 156 (``frame_tempos()``).
        ``frame_rate``: the frames a second of the animation, above 0 (the rotation is in degrees a second).
    """

    tempos: FrameTempos
    frame_rate: float


def frame_tempos(peaks: LocalPeaks, frame_rate: float, frames: int) -> FrameTempos:
    """The current tempo at the middle of each of ``frames`` frames: ``(frames,)`` beats a minute, 60 to 156.

    The tempo is the tempo finder's (``tempo_finder.find_tempo``) after the latest peak at or before the moment
    ``(f + 0.5) / frame_rate`` seconds (the moment the beat and the rhythm angles use); it is constant between two
    peaks. Before the first peak, and with no peak at all, it is the starting tempo, 120.

    Returns:
        ``FrameTempos`` ``(frames,)`` - the current tempo of each frame in beats per minute.
    """
    if not isinstance(peaks, LocalPeaks):
        raise ValueError("The peaks must be the local peaks of a file.")
    frame_rate = _check_frame_rate(frame_rate)
    frames = _check_frames(frames)
    if not peaks.peaks:
        return np.full(frames, START_TEMPO)
    times = np.array([peak.sample / peaks.file_rate for peak in peaks.peaks])
    tempos = find_tempo(times).tempos
    moments = (np.arange(frames) + 0.5) / frame_rate
    latest = np.searchsorted(times, moments, side="right") - 1  # the latest peak at or before each moment, -1 for none
    return np.where(latest >= 0, tempos[np.maximum(latest, 0)], START_TEMPO)


def tempo_colors(tempos: ArrayLike, colormap: str) -> FigureColors:
    """The color of the links of every frame: ``(frames, 3)`` ``uint8``, the colormap's table row
    ``rint((tempo - 60) / (156 - 60) x 255)`` with the tempo held between 60 and 156.

    So the slowest tempo is the first color of the colormap and the fastest the last.

    Arrays:
        ``tempos``: ``ArrayLike`` ``(frames,)`` - the current tempo of each frame in beats per minute
            (``FrameTempos``).

    Returns:
        ``FigureColors`` ``(frames, 3)`` - the red, green and blue (0 to 255) of every link of each frame.
    """
    table = lookup_table(check_colormap(colormap))
    try:
        values = np.asarray(tempos, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The tempos must be one number for each frame.") from None
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("The tempos must be one number for each frame.")
    share = np.clip((values - LOW_LIMIT) / (HIGH_LIMIT - LOW_LIMIT), 0.0, 1.0)
    return table[np.rint(share * (COLORMAP_STEPS - 1)).astype(np.intp)]


def start_width(height: int) -> float:
    """The width in pixels of a link where it starts at the center: the picture's height over 60."""
    return height / START_WIDTH_DIVISOR


def figure_width(fraction: float, height: int) -> float:
    """The width in pixels of the figure at ``fraction`` (0 at the center, 1 at the end of the last link) of its length:
    a straight line from the width at the center to a fifth of it, never under one pixel."""
    start = start_width(height)
    return max(MIN_WIDTH, start - (start - start * END_WIDTH_SHARE) * fraction)


def link_length(width: int, height: int, notes: int) -> float:
    """The length in pixels of every link: ``LENGTH_FACTOR`` times the room from the center to the nearer edge, less
    the margin and half the widest stroke, over the number of notes of the setting.

    A figure bends at almost every link, so with links as long as the room allows it fills only about half of the
    picture; the factor makes up for that. This is the length before the squeeze of ``X_SCALE`` and ``Y_SCALE``: a link
    in the picture is 2/3 of it across and 1/2 of it down. The setting, not the number of notes that sound, divides
    the room, so a link keeps its size from frame to frame. A picture where a link would be under one pixel long is
    refused.
    """
    width, height = _check_size(width, height)
    notes = check_polychord_notes(notes)
    length = LENGTH_FACTOR * (min(width, height) / 2 - MARGIN - start_width(height) / 2) / notes
    if length < MIN_LINK_LENGTH:
        raise ValueError(SIZE_MESSAGE)
    return length


def figure_segments(
    turns_row: ArrayLike, letters_row: ArrayLike, start_angle: float, copies: int, width: int, height: int, notes: int
) -> tuple[LinkSegments, LinkWidths]:
    """The pieces of line of every copy of the figure of one frame, and their widths.

    The links are those of the letters that are not -1 (``n`` of them). Link ``i`` points at the angle
    ``start_angle + 30 k + the sum of the turns up to i`` (``k`` is the copy, 0 to ``copies - 1``; degrees clockwise
    from straight up, the screen's y pointing down) and runs ``link_length()`` from the end of the link before it, squeezed to ``X_SCALE`` of its width and ``Y_SCALE`` of its height; the
    first starts at the center of the picture. Each link is cut into ``PIECES_PER_LINK`` equal pieces, each as wide as
    the figure is at the middle of the piece (``figure_width()``, along the ``n`` links), so the widths fall without a
    step where two links meet. The pieces of copy 0 come first.

    Arrays:
        ``turns_row``: ``ArrayLike`` ``(notes,)`` - the turn in degrees of each link of the frame (``LinkTurns`` of one
            frame).
        ``letters_row``: ``ArrayLike`` ``(notes,)`` - the letter of each link of the frame (``LoudLetters`` of one
            frame), -1 for a missing link.

    Returns:
        A tuple of ``LinkSegments`` ``(segments, 2, 2)`` (the two end points, ``(x, y)`` in pixels from the top left, of
        each piece; ``segments`` is ``copies x n x 6``) and ``LinkWidths`` ``(segments,)`` (the width in pixels of each
        piece).
    """
    width, height = _check_size(width, height)
    notes = check_polychord_notes(notes)
    copies = _whole_number(copies, MIN_COPIES, MAX_COPIES, f"The number of copies must be a whole number from {MIN_COPIES} to {MAX_COPIES}.")
    if isinstance(start_angle, (bool, np.bool_)) or not isinstance(start_angle, numbers.Real) or not math.isfinite(start_angle):
        raise ValueError("The starting angle must be a finite number of degrees.")
    letters = np.asarray(letters_row)
    turns = np.asarray(turns_row, dtype=np.float64)
    if letters.shape != (notes,) or turns.shape != (notes,) or letters.dtype.kind not in "iu" or not np.isfinite(turns).all():
        raise ValueError(f"The turns and the letters must be {notes} numbers each (one for every link).")
    length = link_length(width, height, notes)
    missing = letters < 0
    links = int(np.argmax(missing)) if missing.any() else notes  # the letters are packed: the missing ones come last
    if links == 0:
        return np.zeros((0, 2, 2)), np.zeros(0)
    angles = start_angle + np.cumsum(turns[:links])[None, :] + COPY_TURN * np.arange(copies)[:, None]  # (copies, links)
    radians = np.radians(angles)
    steps = length * np.stack([np.sin(radians) * X_SCALE, -np.cos(radians) * Y_SCALE], axis=-1)  # (copies, links, 2)
    starts = np.array([width / 2, height / 2]) + np.concatenate([np.zeros((copies, 1, 2)), np.cumsum(steps, axis=1)[:, :-1]], axis=1)
    fractions = np.arange(PIECES_PER_LINK + 1) / PIECES_PER_LINK
    points = starts[:, :, None, :] + steps[:, :, None, :] * fractions[None, None, :, None]  # (copies, links, 7, 2)
    segments = np.stack([points[:, :, :-1], points[:, :, 1:]], axis=3).reshape(-1, 2, 2)
    middles = (np.arange(links)[:, None] + (np.arange(PIECES_PER_LINK)[None, :] + 0.5) / PIECES_PER_LINK) / links
    widths = np.array([figure_width(float(f), height) for f in middles.reshape(-1)])
    return segments, np.tile(widths, copies)


def _frame(segments: LinkSegments, widths: LinkWidths, color: Rgb, width: int, height: int) -> Pictures:
    """One picture, a ``uint8`` array ``(height, width, 3)``: the pieces in one ``LineCollection``, in one color, on
    black.

    The figure is a matplotlib ``Figure`` (not a ``pyplot`` figure, so that several threads can draw at once) whose axes
    fill it and whose units are pixels with y pointing down; a width of ``w`` pixels is ``w x 72 / 100`` points. The
    ends of the pieces are round, so the seams between pieces and between links do not show. No pieces is a black
    picture.

    Arrays:
        ``segments``: ``LinkSegments`` ``(segments, 2, 2)`` - the two end points of each piece, in pixels.
        ``widths``: ``LinkWidths`` ``(segments,)`` - the width of each piece, in pixels.
        ``color``: ``Rgb`` ``(3,)`` - the color of every piece (0 to 255 each channel).

    Returns:
        ``Pictures`` ``(height, width, 3)`` - the picture.
    """
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.collections import LineCollection
    from matplotlib.figure import Figure

    figure = Figure(figsize=(width / DPI, height / DPI), dpi=DPI, facecolor=tuple(c / 255 for c in BACKGROUND_COLOR))
    canvas = FigureCanvasAgg(figure)
    axes = figure.add_axes((0, 0, 1, 1))
    axes.set_xlim(0, width)
    axes.set_ylim(height, 0)
    axes.axis("off")
    if len(segments):
        rgb = tuple(float(c) / 255 for c in np.asarray(color))
        axes.add_collection(
            LineCollection(segments, linewidths=np.asarray(widths) * POINTS_PER_INCH / DPI, colors=[rgb], capstyle="round", joinstyle="round")
        )
    canvas.draw()
    picture = np.asarray(canvas.buffer_rgba())[:, :, :3].copy()
    if picture.shape != (height, width, 3):
        raise ValueError(SIZE_MESSAGE)
    return picture


def write_polychord_frames(
    values: ArrayLike,
    beat: ArrayLike | None,
    tempos: ArrayLike,
    settings: PolychordSettings,
    frame_rate: float,
    colormap: str,
    directory: Path,
    width: int,
    height: int,
    extra_notes: int = 0,
) -> None:
    """Save one PNG of ``width`` x ``height`` pixels per frame as ``frame_000000.png`` and up.

    Everything is checked before anything is written (nothing is created for a refusal). The letters, turns, copy
    counts, starting angles and colors of every frame are made once, then each frame is drawn on its own (a few threads,
    as for the other types).

    Arrays:
        ``values``: ``ArrayLike`` ``(frames, 84 or more)`` - the strength of each note in each frame
            (``NoteStrengths``).
        ``beat``: ``BeatPositions`` ``(frames,)`` or ``None`` - the place of each frame in the local energy peak, 0 to
            1; ``None`` gives every frame the minimum number of copies.
        ``tempos``: ``ArrayLike`` ``(frames,)`` - the current tempo of each frame in beats per minute
            (``FrameTempos``).

    ``extra_notes`` is the Extra notes setting k, 0 (the default: the old loudest notes) to the number of notes of the figure:
    a note that is still among the loudest ``notes + extra_notes`` keeps its link (see ``held_notes``).
    """
    settings = check_polychord_settings(settings)
    colormap = check_colormap(colormap)
    notes_values = _check_values(values)
    frames = notes_values.shape[0]
    width, height = _check_size(width, height)
    link_length(width, height, settings.notes)  # refuses a picture that is too small for a figure
    frame_rate = _check_frame_rate(frame_rate)
    checked_beat: BeatPositions | None = None
    if beat is not None:
        checked_beat = _check_beat(beat)
        if checked_beat.shape[0] != frames:
            raise ValueError(f"The beat must be one number from 0 to 1 for each of the {frames} frames.")
    tempo_array = np.asarray(tempos, dtype=np.float64) if not isinstance(tempos, str) else np.zeros((0, 0))
    if tempo_array.shape != (frames,):
        raise ValueError(f"The tempos must be one number for each of the {frames} frames.")
    colors = tempo_colors(tempo_array, colormap)
    letters = loudest_letters(notes_values, settings.notes, extra_notes)
    turns = link_turns(letters)
    copies = copy_counts(checked_beat, settings.min_copies, settings.max_copies, frames)
    angles = start_angles(settings.rotation, frame_rate, frames)
    directory.mkdir(parents=True, exist_ok=True)

    def write(index: int) -> None:
        segments, widths = figure_segments(turns[index], letters[index], float(angles[index]), int(copies[index]), width, height, settings.notes)
        picture = _frame(segments, widths, colors[index], width, height)
        Image.fromarray(picture, "RGB").save(directory / f"frame_{index:06d}.png", compress_level=1)

    with ThreadPoolExecutor(max_workers=SAVE_WORKERS) as pool:
        for future in [pool.submit(write, index) for index in range(frames)]:
            future.result()  # raises the first error of a worker, if there was one
