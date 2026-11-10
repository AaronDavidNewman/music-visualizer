"""The ``chromatic-decay`` kind of picture: the circles of ``decay-exp`` for the 12 chromatic tones only, on a ring in circle-of-fifths order.

Everything that is not about the 12 letters is ``decay-exp``: the points from 0 to 64 and how they set the size, the color and the rings (``decay``),
the five loudest circles of a frame gaining 24, 20, 16, 12 and 8 points plus the beat bonus, cut back by ``exp(-g / taper)`` with the taper that moves
between 8 and 12 (``decay_exp``), and the loss ``sin(pi / 2 * p / 64) ** 2`` per receiver per frame. This module only has what differs:

* **12 circles, one for each letter.** A letter is a note without its octave, counted from A (A 0, A# 1, B 2, C 3, ... G# 11); note ``j`` of the 84 is the
  letter ``j mod 12``. The energy of a letter in a frame is the **largest** of the strengths of its 7 octaves (not their sum), and the five loudest
  letters gain, as the five loudest notes do in ``decay-exp`` (ties to the lower letter, a letter with no energy does not count);
* **the decay goes to the letters 5 and 7 above**, counting round the 12 (letter ``n`` gives to ``(n + 5) mod 12`` and ``(n + 7) mod 12``: C to F and G, F
  to A# and C). A fourth and a fifth add up to an octave, so the receivers give back to the giver: a letter gets back part of what it gave. A circle gives
  away ``PRETEND_NEIGHBORS x frames x sin(pi / 2 * p / 64) ** 2`` points (the total of a circle of ``decay-exp`` when ``PRETEND_NEIGHBORS`` is 8; the constant is
  this module's own, 6), each receiver gets ``1 / PRETEND_NEIGHBORS`` of it (what a neighbour gets in ``decay-exp``) and the rest is
  lost, as for an edge circle there; it never gives more than it has, and all circles give and receive at the same time from the points before the step;
* **the decay rate is a whole number of frames from 1 to 10** (default 1): a step falls at every ``rate``-th frame and moves ``rate`` frames' worth, so
  that the average rate is the same whatever the setting;
* **the picture** has the 12 circles on a ring in circle-of-fifths order, clockwise from the top: C, G, D, A, E, B, F#, C#, G#, D#, A#, F, 30 degrees
  apart, so that the two letters a circle decays to are the neighbours of its place. The full radius is the one that lets two neighbouring full circles just
  touch; the size, color and rings of a circle follow its points as in ``decay``.

The points of all frames are worked out first (``circle_points``, in letter order, small arrays, testable on their own); drawing is then independent for every
frame, from a geometry worked out once for the frame size.

This module knows nothing about the note analysis or the audio: the smoothed note values and the beat positions are passed in.
"""

import math
import numbers
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from .circles import _SAVE_WORKERS, MIDDLE_COLOR_ROW
from .colormaps import COLORMAP_STEPS, check_beat, check_colormap, lookup_table
from .concentric import NOTES, RINGS, _check_values
from .decay import BEAT_BONUS, GAINS, MAX_POINTS, NEGLIGIBLE, SIZE_POINTS, SMALLEST, ring_colors
from .decay_exp import FULL_POINTS, TAPER, exp_loss_per_frame, next_taper, taper_of

LETTERS = 12  # the chromatic tones: a note without its octave
MIN_RATE = 1
MAX_RATE = 10
DEFAULT_RATE = 1
RATE_MESSAGE = f"The decay rate must be a whole number from {MIN_RATE} to {MAX_RATE}."
FIRST_LETTER_AT_TOP = 3  # the letter at the top of the ring: C, with the letters counted from A as 0
FIFTH = 7  # semitones: the step round the ring, and the receiver above
FOURTH = 5  # semitones: the other receiver
MARGIN = 10  # pixels between the outermost circle of the ring and the nearer edge of the picture
PEAK_RINGS = 12  # the concentric rings in the middle that show the beat (feature 036)
PEAK_RADIUS = 70  # pixels on a 600 x 400 picture: the rings fill a circle 140 across
PEAK_REFERENCE_SIZE = 400  # the smaller side of the picture that PEAK_RADIUS is for
PEAK_BOTTOM_PERCENTILE = 1  # the percentile of the positions inside the peaks that is the bottom of the beat of a file: the last color of the rings
RING_SIN = math.sin(math.pi / LETTERS)  # sin 15 degrees: half the distance between two neighbouring centers, in ring radii
PRETEND_NEIGHBORS = 6  # the number of neighbours a circle's total is split between, as if it had them (its own constant: Decay and Decay Exp keep decay.NEIGHBOURS)

def check_chromatic_rate(value) -> int:
    """Return ``value`` as an ``int`` when it is a whole number from 1 to 10 (3 and 3.0 are; a bool, a string, None, a non-finite number, 2.5, 0 and 11 are
    refused with ``RATE_MESSAGE``)."""
    if (
        isinstance(value, (bool, np.bool_))
        or not isinstance(value, numbers.Real)
        or not math.isfinite(value)
        or value % 1 != 0
        or not MIN_RATE <= value <= MAX_RATE
    ):
        raise ValueError(RATE_MESSAGE)
    return int(value)


def _check_letter(value) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Integral) or not 0 <= value < LETTERS:
        raise ValueError(f"A letter must be a whole number from 0 to {LETTERS - 1}.")
    return int(value)


def ring_position(letter) -> int:
    """The place of a letter on the ring, 0 (the top) to 11 (clockwise): ``7 (letter - 3) mod 12``, so C is 0, then G, D, A, E, B, F#, C#, G#, D#, A#, F."""
    return FIFTH * (_check_letter(letter) - FIRST_LETTER_AT_TOP) % LETTERS


def letter_at(position) -> int:
    """The letter at a place of the ring: ``(3 + 7 position) mod 12`` (the inverse of :func:`ring_position`; 7 is its own inverse modulo 12)."""
    return (FIRST_LETTER_AT_TOP + FIFTH * _check_letter(position)) % LETTERS


def receivers(letter) -> tuple[int, int]:
    """The two letters a letter gives its points to: the one 5 and the one 7 semitones above it, counting round the 12 letters."""
    letter = _check_letter(letter)
    return (letter + FOURTH) % LETTERS, (letter + FIFTH) % LETTERS


def letter_energies(values) -> np.ndarray:
    """The energy of every letter in every frame: a float64 array ``(frames, 12)``.

    ``values`` is ``(frames, 84 or more)``, the smoothed note values (the columns after the 84th are not notes of a letter and are left out). Note ``j`` is the
    letter ``j mod 12`` of octave ``j // 12`` (7 octaves), and the energy of a letter is the **largest** of its octaves, not their sum. The input is not
    changed.
    """
    shown = _check_values(values)[:, :NOTES]
    return shown.reshape(shown.shape[0], NOTES // LETTERS, LETTERS).max(axis=1) if shown.shape[0] else np.zeros((0, LETTERS))


def _raw_gains(values, beat=None) -> np.ndarray:
    """The points every letter would gain in every frame before the taper cuts them back: a float64 array ``(frames, 12)`` (the gains of ``decay.gains``
    with the 12 letters in the place of the 84 notes): 24, 20, 16, 12 and 8 plus ``8 * position`` for the five letters with the highest energy of a frame
    (ties to the lower letter; a letter with energy 0 does not count), 0 for every other."""
    energy = letter_energies(values)
    frames = energy.shape[0]
    positions = np.zeros(frames) if beat is None else check_beat(beat, frames)
    order = np.argsort(-energy, axis=1, kind="stable")[:, : len(GAINS)]  # equal energies: the lower letter first
    ranked = np.take_along_axis(energy, order, axis=1)
    gained = np.asarray(GAINS, dtype=np.float64)[None, :] + BEAT_BONUS * positions[:, None]
    gained = np.where(ranked > 0, gained, 0.0)
    result = np.zeros_like(energy)
    np.put_along_axis(result, order, gained, axis=1)
    return result


def letter_gains(values, beat=None, taper=TAPER) -> np.ndarray:
    """The points every letter gains in every frame, in letter order: a float64 array ``(frames, 12)``.

    The five letters with the highest energy of a frame (ties to the lower letter; a letter with energy 0 does not count) get 24, 20, 16, 12 and 8 points in
    that order plus ``8 * position`` (``beat`` is ``None``, position 0, or one position from 0 to 1 for each frame), each multiplied by ``exp(-g / taper)``,
    ``g`` being that gain: the gains of ``decay_exp.exp_gains`` with the 12 letters in the place of the 84 notes. ``taper`` is one number above 0 (8 by
    default) or one for each frame. Every other letter gets 0. The input is not changed.
    """
    gained = _raw_gains(values, beat)  # the bonus is added before the taper cuts the gain back
    taper = np.asarray(taper, dtype=np.float64)
    if taper.ndim > 1 or (taper.ndim == 1 and taper.shape[0] != gained.shape[0]) or not np.isfinite(taper).all() or (taper <= 0).any():
        raise ValueError("The taper must be a number above 0, or one for each frame.")
    if taper.ndim == 1:
        taper = taper[:, None]
    return gained * np.exp(-gained / taper)


def chromatic_step(points, frames=1) -> np.ndarray:
    """One decay step of ``frames`` frames' worth on the ``(12,)`` points of the letters (in letter order): a new array, the input is not changed.

    A circle with ``p`` points gives away ``min(p, PRETEND_NEIGHBORS * frames * loss(p))`` in all, ``loss`` being ``decay_exp.exp_loss_per_frame``: split as if
    it had ``PRETEND_NEIGHBORS`` neighbours (this module's own constant, 6; ``decay.NEIGHBOURS`` is the one of Decay and Decay Exp). Only two of them exist
    here, the letters 5 and 7 above, and each gets ``1 / PRETEND_NEIGHBORS`` of it (what a neighbour gets in ``decay_exp``); **the rest is lost**, as for an edge
    circle there (the ring has no edge, so without this nothing would
    ever vanish). All circles give and receive at the same time, from the points before the step; the result is held between 0 and 64 and a circle left
    with less than a hundredth of a point has none.
    """
    points = np.asarray(points, dtype=np.float64)
    if points.shape != (LETTERS,) or not np.isfinite(points).all() or points.min() < 0 or points.max() > MAX_POINTS:
        raise ValueError(f"The points must be {LETTERS} numbers from 0 to {MAX_POINTS}.")
    frames = check_chromatic_rate(frames)
    # PRETEND because the decay rate is greater than actual neighbors
    give = np.minimum(points, PRETEND_NEIGHBORS * frames * exp_loss_per_frame(points))
    share = give / PRETEND_NEIGHBORS
    received = np.roll(share, FOURTH) + np.roll(share, FIFTH)  # letter m gets from letter m - 5 (whose +5 is m) and from m - 7
    after = np.clip(points - give + received, 0.0, MAX_POINTS)
    after[after < NEGLIGIBLE] = 0.0
    return after


def circle_points(values, beat=None, decay_rate=DEFAULT_RATE) -> np.ndarray:
    """The points of the 12 circles after every frame: a float64 array ``(frames, 12)`` in letter order, each from 0 to 64.

    ``values`` is ``(frames, 84 or more)``, the smoothed note values; ``beat`` is ``None`` or one position from 0 to 1 for each frame; ``decay_rate`` is the
    number of frames between decay steps, a whole number from 1 to 10. Frame ``i`` (counting from 0) adds its gains (:func:`letter_gains` at the taper of the
    frame), then, when ``i + 1`` is a multiple of ``decay_rate``, takes a decay step of ``decay_rate`` frames' worth (:func:`chromatic_step`), and is recorded;
    the taper of the next frame is then worked out as in ``decay_exp`` from the circles with more than 32 points.
    """
    return _simulate(values, beat, decay_rate)[0]


def circle_tapers(values, beat=None, decay_rate=DEFAULT_RATE) -> np.ndarray:
    """The taper that every frame of :func:`circle_points` gained its points with: a float64 array ``(frames,)``, 8 for the first frame."""
    return _simulate(values, beat, decay_rate)[1]


def _simulate(values, beat, decay_rate) -> tuple[np.ndarray, np.ndarray]:
    decay_rate = check_chromatic_rate(decay_rate)
    raw = _raw_gains(values, beat)  # the gains before the taper
    points = np.zeros(LETTERS)
    recorded = np.zeros((raw.shape[0], LETTERS))
    tapers = np.zeros(raw.shape[0])
    steps, rising = 0, True
    for index in range(raw.shape[0]):
        taper = taper_of(steps)
        tapers[index] = taper
        points = np.clip(points + raw[index] * np.exp(-raw[index] / taper), 0.0, MAX_POINTS)
        if (index + 1) % decay_rate == 0:  # a step at the times rate, 2 rate, ... frames, of rate frames' worth: the same average rate whatever the setting
            points = chromatic_step(points, decay_rate)
        recorded[index] = points
        steps, rising = next_taper(steps, rising, int((points > FULL_POINTS).sum()))
    return recorded, tapers


def _check_beat(beat) -> np.ndarray:
    """The beat as a float64 array: one number from 0 to 1 for each frame (see ``colormaps.check_beat``), whatever the number of frames."""
    array = np.asarray(beat)
    return check_beat(array, array.shape[0] if array.ndim == 1 else -1)


def peak_distances(beat) -> np.ndarray:
    """The distance of every frame from the local peak: ``1 - position`` for the ``(frames,)`` positions in the local peak (0 far from a peak or between
    peaks, 1 at the top of one), so 0 at the top of a peak and 1 far from one. The input is not changed."""
    return 1.0 - _check_beat(beat)


def beat_distances(beat) -> np.ndarray:
    """The distance of every frame from the peak, **stretched over the range of the beat of the file** so that the rings use the whole colormap: ``(frames,)``.

    The position in the local peak is 0 to 1 in principle, but inside the peaks of real music it hardly goes below about 0.55 (the energy between two beats does
    not fall to the bottom of the range of the peaks), so ``1 - position`` (:func:`peak_distances`) only reaches 0.45 and a colormap would only be used up to
    its middle. So, with the frames inside a peak being those whose position is above 0: the **highest position** is the top of the beat (distance 0, the first
    color), the **1st percentile of the positions inside the peaks** (``PEAK_BOTTOM_PERCENTILE``: the bottom of the beat, ignoring a few frames far below
    the rest) is distance 1 (the last color), in a straight line between and held at the ends, and a frame outside every peak (position 0) is distance 1.
    With no position inside a peak, or no range between the highest and the bottom, it is just ``1 - position``. The input is not changed.
    """
    beat = _check_beat(beat)
    inside = beat > 0
    if not inside.any():
        return 1.0 - beat
    low = float(np.percentile(beat[inside], PEAK_BOTTOM_PERCENTILE))
    high = float(beat[inside].max())
    if high - low <= 0:
        return 1.0 - beat
    return np.clip((high - beat) / (high - low), 0.0, 1.0)  # a frame outside every peak (position 0) is below the bottom, so it is held at 1


def ring_levels(beat) -> np.ndarray:
    """The level (a distance from the peak, 0 to 1) of each of the 12 rings of the target in every frame: a float64 array ``(frames, 12)``.

    The center ring (column 0) is the distance of the current frame ``t`` (:func:`beat_distances`, stretched over the range of the beat of the file); ring ``k``
    from 2 (column ``k - 1``) is the **average of the distances of frames ``t - (2k - 3)`` and ``t - (2k - 2)``**: ring 2 is frames ``t - 1`` and ``t - 2``,
    ring 3 frames ``t - 3`` and ``t - 4``, ring 12 frames ``t - 21`` and ``t - 22``. The moments before the first frame count as far from a peak (distance 1).
    """
    distance = beat_distances(beat)
    frames = distance.shape[0]
    reach = 2 * PEAK_RINGS - 2  # the farthest frame back that any ring looks at
    padded = np.concatenate([np.ones(reach), distance])
    levels = np.empty((frames, PEAK_RINGS))
    levels[:, 0] = distance
    for ring in range(2, PEAK_RINGS + 1):
        near, far = 2 * ring - 3, 2 * ring - 2
        levels[:, ring - 1] = (padded[reach - near : reach - near + frames] + padded[reach - far : reach - far + frames]) / 2
    return levels


def ring_colors_of(levels, colormap: str) -> np.ndarray:
    """The color of every ring in every frame: a ``uint8`` array ``(frames, 12, 3)``, the colormap's table row ``rint(level * 255)``: the first color at
    the peak (level 0), the last far from it (level 1)."""
    table = lookup_table(check_colormap(colormap))
    levels = np.asarray(levels, dtype=np.float64)
    if levels.ndim != 2 or levels.shape[1] != PEAK_RINGS or not np.isfinite(levels).all() or levels.size and (levels.min() < 0 or levels.max() > 1):
        raise ValueError(f"The levels must be a (frames, {PEAK_RINGS}) array of numbers from 0 to 1.")
    return table[np.rint(levels * (COLORMAP_STEPS - 1)).astype(np.intp)]


def peak_circle_geometry(width: int, height: int) -> tuple[float, float]:
    """The radius of the circle of rings in the middle of the picture and the width of one ring, in pixels: 70 and 5.83 on 600 x 400 (140 across).

    The circle scales with the picture (``70 * min(width, height) / 400``) and is never larger than the free middle of the ring of letters.
    """
    for size in (width, height):
        if isinstance(size, (bool, np.bool_)) or not isinstance(size, numbers.Integral) or size < 1:
            raise ValueError("The picture size must be two whole numbers of at least 1.")
    ring, full = ring_geometry(width, height)
    radius = max(min(PEAK_RADIUS * min(width, height) / PEAK_REFERENCE_SIZE, ring - full - 1), 1.0)
    return radius, radius / PEAK_RINGS


def _check_points(points) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != LETTERS:
        raise ValueError(f"The points must be a (frames, {LETTERS}) array (got shape {points.shape}).")
    if points.size and (not np.isfinite(points).all() or points.min() < 0 or points.max() > MAX_POINTS):
        raise ValueError(f"The points must be numbers from 0 to {MAX_POINTS}.")
    return points


def ring_geometry(width: int, height: int) -> tuple[float, float]:
    """The radius of the ring and the full radius of a circle, in pixels: ``(R, full)``.

    The ring is centered in the picture and as large as the height allows (``R + full`` reaches ``MARGIN`` pixels from the nearer edge), and the full radius
    ``R sin 15`` is half the distance between two neighbouring centers: two neighbouring full circles just touch (150.9 and 39.1 pixels on 600 x 400).
    """
    ring = (min(width, height) / 2 - MARGIN) / (1 + RING_SIN)
    return ring, ring * RING_SIN


def circle_center(position: int, width: int, height: int) -> tuple[float, float]:
    """The center of the circle at a place of the ring: the top is 0 and the places go clockwise, 30 degrees apart."""
    ring, _ = ring_geometry(width, height)
    angle = 2 * math.pi * position / LETTERS
    return width / 2 + ring * math.sin(angle), height / 2 - ring * math.cos(angle)


def circle_radii(points, width: int = 600, height: int = 400) -> np.ndarray:
    """The radius in pixels of circles with ``points`` points: 1/12 of the full radius at 0, the full radius from 24 points on (as in ``decay``)."""
    points = np.asarray(points, dtype=np.float64)
    size = np.minimum(points, SIZE_POINTS) / SIZE_POINTS
    return ring_geometry(width, height)[1] * (SMALLEST + (1.0 - SMALLEST) * size)


def _ring_weights(distance: np.ndarray, ring_width: float) -> np.ndarray:
    """The share of each of the 12 rings in every pixel of ``distance`` (the distance of the pixels from the center of a circle): ``(pixels, 12)`` float32.

    The ring a pixel is in (ring ``k`` covers ``((k - 1) w, k w]``, ``w`` the ring width, and the outside of the circle counts with the last ring) less the shares
    of the ring inside and of the ring outside it that reach into the pixel (0.5 at the edge between two rings, falling to 0 half a pixel away). It is the formula of
    ``decay._geometry``, shared by the circles of the letters and by the target of the beat.
    """
    ring = np.clip(np.ceil(distance / ring_width) - 1, 0, RINGS - 1).astype(np.int32)
    inside = distance - ring * ring_width  # how far the pixel is past the inner edge of its ring
    before = np.where(ring > 0, np.clip(0.5 - inside, 0.0, 1.0), 0.0).astype(np.float32)
    after = np.where(ring < RINGS - 1, np.clip(0.5 - (ring_width - inside), 0.0, 1.0), 0.0).astype(np.float32)
    matrix = np.zeros(ring.shape + (RINGS,), dtype=np.float32)
    index = np.indices(ring.shape)
    np.add.at(matrix, (index[0], index[1], ring), 1.0 - before - after)
    np.add.at(matrix, (index[0], index[1], np.maximum(ring - 1, 0)), before)
    np.add.at(matrix, (index[0], index[1], np.minimum(ring + 1, RINGS - 1)), after)
    return matrix.reshape(-1, RINGS)


@lru_cache(maxsize=4)
def _peak_geometry(width: int, height: int):
    """What never changes between frames for the target of the beat: ``(rows, columns, distance, weights, radius)``, the box around the middle of the picture
    (the radius and 2 pixels more), the distance of each pixel of it from the middle, the ring shares of ``_ring_weights`` and the radius."""
    radius, ring_width = peak_circle_geometry(width, height)
    cx, cy = width / 2, height / 2
    left, right = max(0, int(math.floor(cx - radius - 2))), min(width, int(math.ceil(cx + radius + 2)))
    top, bottom = max(0, int(math.floor(cy - radius - 2))), min(height, int(math.ceil(cy + radius + 2)))
    distance = np.hypot(np.arange(left, right)[None, :] + 0.5 - cx, np.arange(top, bottom)[:, None] + 0.5 - cy)
    return slice(top, bottom), slice(left, right), distance.astype(np.float32), _ring_weights(distance, ring_width), np.float32(radius)


@lru_cache(maxsize=4)
def _geometry(width: int, height: int):
    """What never changes between frames: for each of the 12 places of the ring ``(rows, columns, distance, weights)``.

    ``rows`` and ``columns`` are the slices of the box around the circle (the full radius and 2 pixels more), ``distance`` is the distance of every pixel of the
    box from the center of the circle, and ``weights`` (``(pixels, 12)``) the share of each of the 12 rings in the pixel: the ring it is in (ring ``k`` covers
    ``((k - 1) w, k w]``, ``w`` a twelfth of the full radius, and the outside of the full circle counts with the last ring) less the shares of the ring
    inside and of the ring outside it that reach into the pixel (0.5 at the edge between two rings, falling to 0 half a pixel away). This is the formula of
    ``decay._geometry``, for circles that are not on a grid.
    """
    _, full = ring_geometry(width, height)
    ring_width = full / RINGS
    places = []
    for position in range(LETTERS):
        cx, cy = circle_center(position, width, height)
        left, right = max(0, int(math.floor(cx - full - 2))), min(width, int(math.ceil(cx + full + 2)))
        top, bottom = max(0, int(math.floor(cy - full - 2))), min(height, int(math.ceil(cy + full + 2)))
        distance = np.hypot(np.arange(left, right)[None, :] + 0.5 - cx, np.arange(top, bottom)[:, None] + 0.5 - cy)
        places.append((slice(top, bottom), slice(left, right), distance.astype(np.float32), _ring_weights(distance, ring_width)))
    return places


def _frame(points: np.ndarray, colormap: str, background: np.ndarray, geometry, width: int, height: int, target=None) -> np.ndarray:
    """One picture, a ``uint8`` array ``(height, width, 3)``, from the 12 points of the frame (in letter order).

    ``target`` is ``None`` or the ``(12, 3)`` colors of the rings of the target of the beat (``ring_colors_of``) for this frame: the target is drawn first, in the
    middle of the picture (the middle of the ring of letters is empty, so it never overlaps a circle). The circle of every letter is drawn at its place on the ring,
    blended over what is there with the coverage ``clip(radius - distance + 0.5, 0, 1)``, a smooth edge one pixel wide (where two full circles touch each blends
    half over the other).
    """
    radius = circle_radii(points, width, height).astype(np.float32)
    colours = ring_colors(points, colormap).astype(np.float32)  # (12 letters, 12 rings, 3)
    picture = np.empty((height, width, 3), dtype=np.float32)
    picture[:] = background
    if target is not None:
        rows, columns, distance, weights, peak_radius = _peak_geometry(width, height)
        coverage = np.clip(peak_radius - distance + 0.5, 0.0, 1.0)[..., None]
        colour = (weights @ target.astype(np.float32)).reshape(distance.shape + (3,))
        picture[rows, columns] += (colour - picture[rows, columns]) * coverage
    for position, (rows, columns, distance, weights) in enumerate(geometry):
        letter = letter_at(position)
        coverage = np.clip(radius[letter] - distance + 0.5, 0.0, 1.0)[..., None]
        colour = (weights @ colours[letter]).reshape(distance.shape + (3,))
        picture[rows, columns] += (colour - picture[rows, columns]) * coverage
    return np.rint(picture).astype(np.uint8)


def write_chromatic_frames(points, colormap: str, directory: Path, width: int, height: int, beat=None) -> None:
    """Save one PNG of ``width`` x ``height`` pixels per row of ``points`` as ``frame_000000.png`` and up.

    ``points`` is ``(frames, 12)``: the points of every letter in every frame, in letter order (see :func:`circle_points`). ``beat`` is ``None`` (no target) or one
    position in the local peak from 0 to 1 for each frame: the middle of every picture then has the target of 12 concentric rings that show the beat
    (:func:`ring_levels`, :func:`ring_colors_of`), 140 pixels across on 600 x 400. Everything is checked before anything is written.
    """
    colormap = check_colormap(colormap)
    points = _check_points(points)
    targets = None
    if beat is not None:
        beat = _check_beat(beat)
        if beat.shape[0] != points.shape[0]:
            raise ValueError(f"The beat must be one number from 0 to 1 for each of the {points.shape[0]} frames.")
        targets = ring_colors_of(ring_levels(beat), colormap)  # (frames, 12, 3)
    for size in (width, height):
        if isinstance(size, (bool, np.bool_)) or not isinstance(size, numbers.Integral) or size < 1:
            raise ValueError("The picture size must be two whole numbers of at least 1.")
    width, height = int(width), int(height)
    background = lookup_table(colormap)[MIDDLE_COLOR_ROW].astype(np.float32)
    geometry = _geometry(width, height)
    directory.mkdir(parents=True, exist_ok=True)

    def write(index: int) -> None:
        picture = _frame(points[index], colormap, background, geometry, width, height, None if targets is None else targets[index])
        Image.fromarray(picture, "RGB").save(directory / f"frame_{index:06d}.png", compress_level=1)

    with ThreadPoolExecutor(max_workers=_SAVE_WORKERS) as pool:
        for future in [pool.submit(write, i) for i in range(points.shape[0])]:
            future.result()  # raises the first error of a worker, if there was one
