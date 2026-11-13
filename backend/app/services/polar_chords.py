"""The ``polar-chords`` kind of picture: the notes and the chords of the music as bars of a polar bar graph.

The picture is a circle in the 600 x 400 frame, on the colormap's middle color. Two sets of bars start at its center, each filling an arc of
the circle, measured from straight up:

* **the notes**, **clockwise**, 84 equal arcs (360 / 84 degrees wide): arc ``a`` is the note that the note layout draws in cell ``a`` (``note_layout``): with ``rows``, the default,
  the piano note ``a`` itself (0 is A1), in order of pitch; with ``spiral`` the note that the spiral puts in that cell (middle C, note 27, is in
  cell 29). The ``count`` loudest notes of a frame (``count`` is the setting *Notes shown*, 5 to 8) get a bar; a note with no strength never
  does, ties go to the lower note (not the lower arc). **A bar follows its note one arc a frame**: every volume (the loudest, the second
  loudest, ...) keeps its own bar, and when the note of a volume changes from one frame to the next, its bar moves one arc (2 pi / 84) the
  shorter way round the circle toward the arc of the new note, instead of jumping there, which makes the animation smoother (``follow_arcs``).
  The first frame, and a bar that comes back after a frame without a note for its volume, are in the arc of their note. The color is that of
  the note the bar is following;
* **the chords**, **counterclockwise**, 84 equal arcs (the same width as a note's), one for each of the 12 letters (a letter is a note without its
  octave, with its accidental; 0 is A, like the first note, A1) and each of the 7 chord types of ``POLAR_CHORD_TYPES``: arc ``7 * letter + type``,
  so the 7 types of the first letter come first, then the 7 of the second, and so on. The letter is the root the chord is built on (not the
  octave, and the inversion only decides which note is in the bass). The chord that the chord interval measurement (``chords.measure_chords``)
  records for the frame gets one bar, if there is one. The chords are about the real notes, so the layout does not change them.

Every bar reaches out to ``0.5 + 0.5 * position`` of the full radius, ``position`` being the frame's place in the local energy peak (0 to 1; 0
without a beat). The notes are colored from the middle of the colormap (a faint note) to its start (the loudest), the chord from the middle to
its end, by the square root of the strength as a share of the largest value of the file; the chord is drawn over the notes.

The bars of all frames are worked out first (``polar_bars``, small arrays, testable on their own); the bars follow their notes from frame to
frame, so the bars of a frame depend on the frames before it. Drawing is then independent for every frame: the arcs of every pixel are worked out
once (and kept for the frame size), so that a frame only touches the pixels of its bars.

This module knows nothing about the note analysis, the audio or the beat measurement: the smoothed note values, the beat positions and the size
are passed in.
"""

import numbers
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from .chords import check_chord_type, measure_chords
from .colormaps import COLORMAP_STEPS, MIDDLE_COLOR_ROW, check_beat, check_colormap, lookup_table
from .frame_saving import SAVE_WORKERS
from .note_layout import DEFAULT_NOTE_LAYOUT, check_note_layout, note_order

ARCS = 84  # the arcs of the notes
MIN_POLAR_NOTES = 5
MAX_POLAR_NOTES = 8
DEFAULT_POLAR_NOTES = 5
# the chord types looked for, in the order of the places: the place of a chord is 7 * its root letter + the index of its type
POLAR_CHORD_TYPES = ((7,), (4, 7), (3, 7), (4, 10), (4, 11), (3, 7, 10), (4, 6))
CHORD_ROOTS = 12  # the letters a chord can be built on: a note without its octave
CHORD_ARCS = CHORD_ROOTS * len(POLAR_CHORD_TYPES)  # the arcs of the chords: one for each chord type on each letter, 84
MIN_LENGTH = 0.5  # a bar is this share of the full radius long at the bottom of the local peak, all of it at the top
MARGIN = 10  # pixels between the full radius and the nearer edge of the picture

NOTES_MESSAGE = f"The number of notes shown must be a whole number from {MIN_POLAR_NOTES} to {MAX_POLAR_NOTES}."


def check_polar_notes(value) -> int:
    """Return ``value`` as an ``int`` when it is a whole number from 5 to 8 (a bool, a string, a fraction or a non-finite number is refused)."""
    if (
        isinstance(value, (bool, np.bool_))
        or not isinstance(value, numbers.Real)
        or not np.isfinite(value)
        or int(value) != value
        or not MIN_POLAR_NOTES <= value <= MAX_POLAR_NOTES
    ):
        raise ValueError(NOTES_MESSAGE)
    return int(value)


def chord_place(chord_type, root) -> int:
    """The place of a chord among the 84: ``7 * root + the index of its type`` among ``POLAR_CHORD_TYPES``, ``root`` being the letter (0 to 11, 0 is A)."""
    chord_type = check_chord_type(chord_type)
    if chord_type not in POLAR_CHORD_TYPES:
        raise ValueError(f"The chord type must be one of {', '.join(str(t) for t in POLAR_CHORD_TYPES)} (got {chord_type}).")
    if isinstance(root, (bool, np.bool_)) or not isinstance(root, (int, np.integer)) or not 0 <= root < CHORD_ROOTS:
        raise ValueError(f"The root must be a whole number from 0 to {CHORD_ROOTS - 1} (got {root!r}).")
    return len(POLAR_CHORD_TYPES) * int(root) + POLAR_CHORD_TYPES.index(chord_type)


def chord_root(chord_type, inversion, lowest_note) -> int:
    """The letter (0 to 11, 0 is A) that a chord is built on, from its type, its inversion and its lowest note.

    In inversion ``k`` the lowest note is the chord tone ``(0, *chord_type)[k]`` above the root, so the root is that many steps below it.
    """
    chord = (0, *check_chord_type(chord_type))
    if isinstance(inversion, (bool, np.bool_)) or not isinstance(inversion, (int, np.integer)) or not 0 <= inversion < len(chord):
        raise ValueError(f"The inversion of {chord_type} must be a whole number from 0 to {len(chord) - 1} (got {inversion!r}).")
    return int((int(lowest_note) - chord[int(inversion)]) % CHORD_ROOTS)


@dataclass(frozen=True, eq=False)
class PolarBars:
    """The bars of every frame of a file.

    ``note_slots`` (``int16``, ``(frames, count)``): the arc each note bar is drawn in, loudest first, -1 where fewer notes sound (or where the bar
    is covered by the bar of a louder note in the same arc). ``note_shares`` (``float64``, same shape): the strength share of each, 0 where there is none. ``chord_place`` (``int16``, ``(frames,)``): the place of the
    chord bar, ``7 * root letter + the number of its type`` from 0 to 83, -1 for none; ``chord_share`` (``float64``): its strength share. ``length`` (``float64``, ``(frames,)``): ``0.5 + 0.5 * position``.
    """

    note_slots: np.ndarray
    note_shares: np.ndarray
    chord_place: np.ndarray
    chord_share: np.ndarray
    length: np.ndarray

    @property
    def frame_count(self) -> int:
        return int(self.length.shape[0])


def _check_values(values) -> np.ndarray:
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The note values must be finite numbers that are not negative.") from None
    if array.ndim != 2 or array.shape[1] < ARCS:
        raise ValueError(f"Each frame needs at least {ARCS} note values (got shape {array.shape}).")
    if array.size and (not np.isfinite(array).all() or array.min() < 0):
        raise ValueError("The note values must be finite numbers that are not negative.")
    return array


def _targets(values: np.ndarray, peak: float, count: int, note_layout: str):
    """The arc of the note of each of the ``count`` loudest volumes of every frame (-1 for none) and the strength share of each note."""
    drawn = values[:, :ARCS]
    order = np.argsort(-drawn, axis=1, kind="stable")[:, :count]  # equal strengths: the lower note first
    top = np.take_along_axis(drawn, order, axis=1)
    sounding = top > 0
    arc_of_note = np.argsort(note_order(note_layout))  # the layout names the note of each cell; the arc of a note is its cell
    targets = np.where(sounding, arc_of_note[order], -1).astype(np.int16)
    shares = np.sqrt(top / peak) if peak > 0 else np.zeros_like(top)
    return targets, np.where(sounding, shares, 0.0)


def note_targets(smoothed, count: int = DEFAULT_POLAR_NOTES, note_layout: str = DEFAULT_NOTE_LAYOUT):
    """The arc of the note of each of the ``count`` loudest volumes of every frame and its strength share: ``(arcs, shares)``, arrays of shape
    ``(frames, count)``, loudest first, ``-1`` and ``0`` where fewer notes sound. These are the arcs the bars are heading for; ``polar_bars`` moves
    the bars toward them. The input is not changed."""
    count = check_polar_notes(count)
    note_layout = check_note_layout(note_layout)
    values = _check_values(smoothed)
    peak = float(values.max()) if values.size else 0.0
    return _targets(values, peak, count, note_layout)


def follow_arcs(targets) -> np.ndarray:
    """Where the bars are when each follows its note one arc a frame: an ``int16`` array of the shape of ``targets`` (``(frames, volumes)``).

    ``targets`` holds for every frame and every volume (the loudest, the second loudest, ...) the arc of its note, or -1 for none. The bar of a
    volume starts in the arc of its note. When the note of a volume changes it moves one arc (2 pi / 84) a frame, the shorter way round the
    circle (clockwise when both ways are as long), until it is in the arc of the note, where it stays and then follows the note by one arc. A volume
    with no note (-1) has no bar and loses its place: when it has a note again its bar starts in the arc of that note. The input is not changed.
    """
    targets = np.asarray(targets)
    if targets.ndim != 2 or targets.dtype.kind not in "iu" or (targets < -1).any() or (targets >= ARCS).any():
        raise ValueError(f"The targets must be a (frames, volumes) array of whole numbers from -1 to {ARCS - 1}.")
    positions = np.full(targets.shape, -1, dtype=np.int16)
    current = np.full(targets.shape[1], -1, dtype=np.int64)
    for frame in range(targets.shape[0]):
        target = targets[frame].astype(np.int64)
        has = target >= 0
        fresh = has & (current < 0)  # no place yet: start in the arc of the note
        current = np.where(fresh, target, current)
        difference = (target - current) % ARCS  # the way to go clockwise
        step = np.where(difference == 0, 0, np.where(difference <= ARCS // 2, 1, -1))
        current = np.where(has & ~fresh, (current + step) % ARCS, current)
        current = np.where(has, current, -1)
        positions[frame] = current
    return positions


def polar_bars(smoothed, beat=None, count: int = DEFAULT_POLAR_NOTES, note_layout: str = DEFAULT_NOTE_LAYOUT) -> PolarBars:
    """The bars of every frame of a file (see :class:`PolarBars`), worked out before any drawing.

    ``smoothed`` is ``(frames, 84 or more)``, the smoothed note values in note order (the columns after the 84th are never drawn but, like the
    colors of the other pictures, they count for the largest value that sets the scale); ``beat`` is ``None`` or one position from 0 to 1 for each frame; ``count``
    is the number of notes shown, 5 to 8; ``note_layout`` (``"rows"`` or ``"spiral"``) says in which arc each note is, as it says in which cell of the
    grid it is for the other pictures. The bars follow their notes one arc a frame (:func:`follow_arcs`); where the bars of two volumes are in the same
    arc only the louder is shown. The input is not changed.
    """
    count = check_polar_notes(count)
    note_layout = check_note_layout(note_layout)
    values = _check_values(smoothed)
    frames = values.shape[0]
    positions = np.zeros(frames) if beat is None else check_beat(beat, frames)
    peak = float(values.max()) if values.size else 0.0

    drawn = values[:, :ARCS]
    targets, note_shares = _targets(values, peak, count, note_layout)
    arcs = follow_arcs(targets)
    covered = np.zeros(arcs.shape, dtype=bool)
    for volume in range(1, count):  # a bar in the arc of the bar of a louder volume is hidden
        covered[:, volume] = (arcs[:, :volume] == arcs[:, volume : volume + 1]).any(axis=1) & (arcs[:, volume] >= 0)
    note_slots = np.where(covered, -1, arcs).astype(np.int16)
    note_shares = np.where(covered, 0.0, note_shares)

    # the chord of every frame: the one that the chord interval measurement records for the 7 types (no limit on the notes: the image type has none);
    # its place is the number of its type, -1 for none
    series = measure_chords(values, POLAR_CHORD_TYPES)
    found = series.type_index >= 0
    # the root letter of the chord: its lowest note less the chord tone in the bass (the offsets of the tones of every type, by inversion)
    tones = np.zeros((len(POLAR_CHORD_TYPES), 1 + max(len(t) for t in POLAR_CHORD_TYPES)), dtype=np.int64)
    for index, chord_type in enumerate(POLAR_CHORD_TYPES):
        tones[index, : len(chord_type) + 1] = (0, *chord_type)
    kind = np.maximum(series.type_index, 0).astype(np.int64)
    root = (series.notes[:, 0].astype(np.int64) - tones[kind, np.maximum(series.inversion, 0).astype(np.int64)]) % CHORD_ROOTS
    chord_place = np.where(found, len(POLAR_CHORD_TYPES) * root + kind, -1).astype(np.int16)
    used = series.notes >= 0
    chord_values = np.take_along_axis(drawn, np.where(used, series.notes, 0).astype(np.int64), axis=1) * used
    average = chord_values.sum(axis=1) / np.maximum(used.sum(axis=1), 1)
    chord_share = np.where(found & (peak > 0), np.sqrt(average / peak) if peak > 0 else 0.0, 0.0)
    return PolarBars(note_slots, note_shares, chord_place, chord_share, MIN_LENGTH + (1.0 - MIN_LENGTH) * positions)


def _check_bars(bars: PolarBars) -> None:
    frames = bars.length.shape[0]
    if (
        bars.note_slots.ndim != 2
        or bars.note_slots.shape[0] != frames
        or bars.note_shares.shape != bars.note_slots.shape
        or bars.chord_place.shape != (frames,)
        or bars.chord_share.shape != (frames,)
    ):
        raise ValueError("The bars must have one row of notes, one chord place, one chord share and one length for every frame.")
    if (bars.note_slots < -1).any() or (bars.note_slots >= ARCS).any() or (bars.chord_place < -1).any() or (bars.chord_place >= CHORD_ARCS).any():
        raise ValueError(f"The arcs of the bars must be from 0 to {ARCS - 1} for the notes and from 0 to {CHORD_ARCS - 1} for the chord (or -1 for no bar).")


@lru_cache(maxsize=4)
def _geometry(width: int, height: int):
    """What never changes between frames, for the frame size: ``(radius, notes, chords)``.

    ``radius`` is the full radius in pixels. ``notes`` and ``chords`` (84 arcs each) each hold, for each arc, ``(own, neighbour)`` where each is
    ``(pixels, weights, distances)``: the flat pixel numbers, the share of the pixel that belongs to the arc and its distance from the center.
    A pixel belongs to the arc it is in; the part of it that reaches over the nearer side into the next arc (half a pixel on each side of the
    edge, falling to 0) belongs to that neighbouring arc, so that the sides of a bar are smooth and two bars next to each other have no seam.
    """
    radius = min(width, height) / 2 - MARGIN
    ys, xs = np.mgrid[0:height, 0:width]
    dx = (xs + 0.5 - width / 2).ravel()
    dy = (ys + 0.5 - height / 2).ravel()
    distance = np.hypot(dx, dy)
    pixels = np.flatnonzero(distance <= radius + 1.5)  # a bar's tip is smooth over one pixel
    dx, dy, distance = dx[pixels], dy[pixels], distance[pixels]
    clockwise = np.arctan2(dx, -dy) % (2 * np.pi)  # from straight up, clockwise
    kinds = []
    # the notes go clockwise in 84 arcs, the chords counterclockwise in 84
    for angle, arcs in ((clockwise, ARCS), ((2 * np.pi - clockwise) % (2 * np.pi), CHORD_ARCS)):
        arc_width = 2 * np.pi / arcs
        position = angle / arc_width
        arc = np.floor(position).astype(np.int64) % arcs
        fraction = position - np.floor(position)
        edge = np.minimum(fraction, 1.0 - fraction) * arc_width * distance  # pixels from the nearer side
        share = np.clip(0.5 - edge, 0.0, 1.0)
        neighbour = np.where(fraction >= 0.5, arc + 1, arc - 1) % arcs
        own = [(pixels[arc == a], (1.0 - share)[arc == a], distance[arc == a]) for a in range(arcs)]
        over = share > 0
        near = [(pixels[over & (neighbour == a)], share[over & (neighbour == a)], distance[over & (neighbour == a)]) for a in range(arcs)]
        kinds.append([(own[a], near[a]) for a in range(arcs)])
    return radius, kinds[0], kinds[1]


def _layer(arcs, slots, colours, lengths_px, size: int):
    """The coverage and the premultiplied color (``size`` pixels, 3 channels) of the bars in ``slots`` (arc numbers) with their colors and lengths."""
    alpha = np.zeros(size, dtype=np.float32)
    colour = np.zeros((size, 3), dtype=np.float32)
    for arc, rgb, length in zip(slots, colours, lengths_px):
        for pixels, weights, distance in arcs[arc]:
            if pixels.size:
                cover = np.clip(length - distance + 0.5, 0.0, 1.0).astype(np.float32) * weights.astype(np.float32)
                alpha[pixels] += cover
                colour[pixels] += cover[:, None] * rgb
    return alpha, colour


def _frame(bars: PolarBars, index: int, table: np.ndarray, background: np.ndarray, geometry, width: int, height: int) -> np.ndarray:
    """One picture, a ``uint8`` array ``(height, width, 3)``: the note bars over the background, the chord bar over them."""
    radius, notes, chords = geometry
    length = float(bars.length[index]) * radius
    wanted = bars.note_slots[index] >= 0
    slots = bars.note_slots[index][wanted].astype(np.int64)
    rows = np.rint((0.5 - 0.5 * bars.note_shares[index][wanted]) * (COLORMAP_STEPS - 1)).astype(np.intp)
    size = width * height

    alpha, colour = _layer(notes, slots, table[rows].astype(np.float32), [length] * slots.size, size)
    picture = np.empty((size, 3), dtype=np.float32)
    picture[:] = background
    touched = np.flatnonzero(alpha > 0)
    picture[touched] = picture[touched] * (1.0 - np.minimum(alpha[touched], 1.0))[:, None] + colour[touched]

    if bars.chord_place[index] >= 0:
        row = int(np.rint((0.5 + 0.5 * bars.chord_share[index]) * (COLORMAP_STEPS - 1)))
        alpha, colour = _layer(chords, [int(bars.chord_place[index])], table[[row]].astype(np.float32), [length], size)
        touched = np.flatnonzero(alpha > 0)
        picture[touched] = picture[touched] * (1.0 - np.minimum(alpha[touched], 1.0))[:, None] + colour[touched]
    return np.rint(picture).astype(np.uint8).reshape(height, width, 3)


def write_polar_frames(bars: PolarBars, colormap: str, directory: Path, width: int, height: int) -> None:
    """Save one PNG of ``width`` x ``height`` pixels per frame of ``bars`` as ``frame_000000.png`` and up. Everything is checked before anything is written."""
    colormap = check_colormap(colormap)
    _check_bars(bars)
    table = lookup_table(colormap)
    background = table[MIDDLE_COLOR_ROW].astype(np.float32)
    geometry = _geometry(int(width), int(height))
    directory.mkdir(parents=True, exist_ok=True)

    def write(index: int) -> None:
        picture = _frame(bars, index, table, background, geometry, int(width), int(height))
        Image.fromarray(picture, "RGB").save(directory / f"frame_{index:06d}.png", compress_level=1)

    with ThreadPoolExecutor(max_workers=SAVE_WORKERS) as pool:
        for future in [pool.submit(write, i) for i in range(bars.frame_count)]:
            future.result()  # raises the first error of a worker, if there was one
