"""The ``energy-graphs`` kind of picture: a running histogram of the 84 piano notes with two data sets, which updates from frame to frame.

The picture is 600 x 400 pixels on the colormap's middle color: 84 pairs of thin bars, one pair for each note, the lowest (A1) on the left.

* **The frequency data set** (the first bar of a pair, in the start color of the colormap): in every analysis window the 84 notes are ranked by strength and
  each adds its **rank score** to its own total: 84 for the loudest, 83 for the second loudest, and so on down to 1; a note with no strength (under the
  noise floor, feature 033) adds nothing, and neither do the notes ranked below it. Equal strengths: the lower note ranks first.
* **The amplitude data set** (the second bar of a pair, in the end color): in every window each note adds its **quasi-decibel** value, ``20 log10(amp) /
  (20 log10(max))``, to its own total, ``max`` being the largest amplitude of any of the 84 notes in any window of the file. It is 1 for the loudest note of
  the file, and smaller for fainter ones; a silent note adds 0, a value below 0 (an amplitude under 1) is clamped to 0, and a file whose loudest amplitude is
  1 or less (where the ratio of logarithms is meaningless) adds nothing at all.

Both totals **accumulate** from the start of the file up to the frame (a window is counted once, in the frame it starts in, so the last frame holds the sum
over every window). They are not drawn as they are: a total grows with the length of the file and the two have different sizes. Each data set is divided by
its own largest total (so it runs from 0 to 1) and then **softmaxed** over the 84 notes (``exp(x) / sum(exp(x))``), so that the two are on the same scale, each
adding up to 1. A softmax is never 0 and its values are close to each other, so the clear winners would hardly show: **the smallest value of each data set is
given the height 0** (its smallest share is subtracted from all its shares, ``above_smallest``). The bars are then scaled by the larger of all the values of
the frame, so that **the tallest bar is always the same height**. A data set with no total yet (before the first sound), or whose totals are all equal (so
that nothing is above the smallest), has no bars.

The numbers of all frames are worked out first (``frame_energy``, small arrays, testable on their own: the totals are cumulative sums over the windows, so a
frame does not depend on the drawing of the frames before it). Drawing is then independent for every frame: the background (title, legend, baseline,
labels) is drawn once and copied, and the bars are rectangles.

This module knows nothing about the audio, the job or the page: the analysis result, the frame rate and the size are passed in.
"""

import numbers
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .circles import _SAVE_WORKERS, MIDDLE_COLOR_ROW
from .colormaps import COLORMAP_STEPS, check_colormap, lookup_table
from .note_analysis import AnalysisResult

NOTES = 84  # the bars of the histogram: the 84 piano notes (the first 84 of the 88 note values)
RANK_CHUNK = 4096  # windows ranked at a time, so that memory stays bounded for a long file

# The layout of the 600 x 400 picture, in pixels from the top left (specs/034-energy-graphs/contracts/energy-graphs.md). Another size scales it.
REFERENCE_WIDTH = 600
REFERENCE_HEIGHT = 400
MARGIN = 10
TITLE_Y = 10
PLOT_TOP = 36
PLOT_BOTTOM = 372  # the baseline; the bars stand on it and the tallest reaches PLOT_TOP
LABEL_Y = 377
FONT_SIZE = 13
SQUARE = 9  # the colored square of a legend entry
GAP = 1  # pixels at the end of the slot of a note, after its two bars

TITLE = "Notes so far (softmax of the totals)"
LEGEND = ("frequency: rank points", "amplitude: quasi-dB")


@dataclass(frozen=True)
class EnergyGraphData:
    """The totals of every frame, one row per frame: ``histogram`` is ``(frames, 84)`` whole numbers (the rank points of each note so far) and
    ``amplitude`` is ``(frames, 84)`` numbers that are not negative (the quasi-decibel values of each note so far)."""

    histogram: np.ndarray
    amplitude: np.ndarray

    @property
    def frame_count(self) -> int:
        return int(self.histogram.shape[0])


def _check_note_values(values) -> np.ndarray:
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The note values must be numbers.") from None
    if array.ndim != 2 or array.shape[1] < NOTES:
        raise ValueError(f"The note values must be a (windows, {NOTES} or more) array.")
    if array.size and (not np.isfinite(array).all() or array.min() < 0):
        raise ValueError("The note values must be finite numbers that are not negative.")
    return array


def rank_scores(values) -> np.ndarray:
    """The points each of the 84 notes scores in each window: an ``int64`` array ``(windows, 84)``.

    ``values`` is ``(windows, 84 or more)`` note strengths (columns after the 84th are not piano notes and are left out). In every window the loudest
    note scores 84, the next 83, and so on by rank; a note with no strength (0) scores 0, and so do the notes ranked below it. Equal strengths: the lower
    note ranks first. The input is not changed.
    """
    drawn = _check_note_values(values)[:, :NOTES]
    scores = np.zeros(drawn.shape, dtype=np.int64)
    points = NOTES - np.arange(NOTES, dtype=np.int64)  # 84 for the first in rank, 1 for the last
    for first in range(0, drawn.shape[0], RANK_CHUNK):
        part = drawn[first : first + RANK_CHUNK]
        order = np.argsort(-part, axis=1, kind="stable")  # equal strengths: the lower note first
        ranked = np.zeros(part.shape, dtype=np.int64)
        np.put_along_axis(ranked, order, np.broadcast_to(points, order.shape), axis=1)
        ranked[part <= 0] = 0
        scores[first : first + RANK_CHUNK] = ranked
    return scores


def quasi_db(values, peak=None) -> np.ndarray:
    """What each of the 84 notes adds to its amplitude total in each window: a ``float64`` array ``(windows, 84)``, ``20 log10(amp) / (20 log10(peak))``.

    ``peak`` is the largest amplitude of any note of any window (by default the largest of the 84 columns of ``values``). The loudest note of the file adds
    1 and every fainter note less. A note with no strength adds 0; a negative result (an amplitude under 1) is clamped to 0; with a ``peak`` of 1 or less
    (the ratio of logarithms is not defined, or turned upside down) nothing is added at all. Columns after the 84th are left out; the input is not changed.
    """
    drawn = _check_note_values(values)[:, :NOTES]
    if peak is None:
        peak = float(drawn.max()) if drawn.size else 0.0
    elif isinstance(peak, (bool, np.bool_)) or not isinstance(peak, numbers.Real) or not np.isfinite(peak) or peak < 0:
        raise ValueError("The peak must be a finite number that is not negative.")
    out = np.zeros(drawn.shape, dtype=np.float64)
    if peak <= 1.0:
        return out
    sounding = drawn > 0
    out[sounding] = 20.0 * np.log10(drawn[sounding]) / (20.0 * np.log10(peak))
    return np.maximum(out, 0.0)


def softmax_shares(totals) -> np.ndarray:
    """The softmax of each row of ``totals`` after dividing the row by its largest value: a ``float64`` array of the same shape, each row adding up to 1.

    ``totals`` is ``(rows, n)`` numbers that are not negative. A row of ``x`` becomes ``exp(x / max(x)) / sum(exp(x / max(x)))``, so the values the softmax
    sees run from 0 to 1 whatever the size of the totals. A row with no total (its largest is 0) has nothing to show and becomes all 0.
    """
    try:
        array = np.asarray(totals, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The totals must be numbers.") from None
    if array.ndim != 2 or (array.size and (not np.isfinite(array).all() or array.min() < 0)):
        raise ValueError("The totals must be a 2-D array of finite numbers that are not negative.")
    largest = array.max(axis=1, keepdims=True) if array.shape[1] else np.zeros((array.shape[0], 1))
    scaled = np.where(largest > 0, array / np.where(largest > 0, largest, 1.0), 0.0)
    exponentials = np.exp(scaled)  # at most e, no overflow
    shares = exponentials / exponentials.sum(axis=1, keepdims=True) if array.shape[1] else exponentials
    return np.where(largest > 0, shares, 0.0)


def above_smallest(shares) -> np.ndarray:
    """Each row of ``shares`` lowered so that its smallest value is 0: a ``float64`` array of the same shape; a row that is all 0 stays all 0.

    ``shares`` is ``(rows, n)`` numbers that are not negative (the softmax of the totals, which is never 0 and whose values are close to each other). A row
    that is all equal has nothing above its smallest value and becomes all 0. The input is not changed.
    """
    try:
        array = np.asarray(shares, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("The shares must be numbers.") from None
    if array.ndim != 2 or (array.size and (not np.isfinite(array).all() or array.min() < 0)):
        raise ValueError("The shares must be a 2-D array of finite numbers that are not negative.")
    if not array.shape[1]:
        return array.copy()
    return array - array.min(axis=1, keepdims=True)


def frame_energy(result: AnalysisResult, frame_rate: float, frames: int) -> EnergyGraphData:
    """The totals of every one of ``frames`` frames, from an analysis after the noise floor.

    Windows belong to frames as ``frame_rendering.frame_windows`` says. Frame ``i`` holds, for each note, the sum of the rank scores (``histogram``) and of
    the quasi-decibel values (``amplitude``, see ``quasi_db``; the peak is the largest of the 84 notes in any window of the whole file) of every window that
    starts before the end of the frame, so a window is counted once and a frame with no window of its own adds nothing.
    """
    from .frame_rendering import frame_windows  # here, not at the top: frame_rendering imports this module to draw the type

    frames = int(frames)
    windows = result.frames
    if frames == 0 or windows.shape[0] == 0:
        return EnergyGraphData(np.zeros((frames, NOTES), dtype=np.int64), np.zeros((frames, NOTES)))
    _, stop, _ = frame_windows(result, frame_rate, frames)
    ranks = np.vstack([np.zeros((1, NOTES), dtype=np.int64), np.cumsum(rank_scores(windows), axis=0)])
    amplitudes = np.vstack([np.zeros((1, NOTES)), np.cumsum(quasi_db(windows), axis=0)])
    return EnergyGraphData(ranks[stop], amplitudes[stop])


def _check_data(data: EnergyGraphData) -> None:
    histogram = np.asarray(data.histogram)
    if histogram.ndim != 2 or histogram.shape[1] != NOTES or histogram.dtype.kind not in "iu":
        raise ValueError(f"The histogram must be a (frames, {NOTES}) array of whole numbers.")
    if histogram.size and histogram.min() < 0:
        raise ValueError("The histogram must not hold a negative number.")
    amplitude = np.asarray(data.amplitude)
    if amplitude.shape != histogram.shape or amplitude.dtype.kind not in "iuf":
        raise ValueError(f"The amplitude totals must be a (frames, {NOTES}) array of numbers, like the histogram.")
    if amplitude.size and (not np.isfinite(amplitude.astype(np.float64)).all() or amplitude.min() < 0):
        raise ValueError("The amplitude totals must be finite numbers that are not negative.")


class _Layout:
    """The pixel positions of the picture for a frame size: the 600 x 400 layout scaled by the smaller ratio and centered."""

    def __init__(self, width: int, height: int):
        scale = min(width / REFERENCE_WIDTH, height / REFERENCE_HEIGHT)
        dx = (width - REFERENCE_WIDTH * scale) / 2
        dy = (height - REFERENCE_HEIGHT * scale) / 2
        self.width, self.height, self.scale = width, height, scale
        self.x = lambda v: int(round(dx + v * scale))
        self.y = lambda v: int(round(dy + v * scale))
        self.s = lambda v: max(1, int(round(v * scale)))
        self.left, self.right = self.x(MARGIN), self.x(REFERENCE_WIDTH - MARGIN)
        self.top, self.bottom = self.y(PLOT_TOP), self.y(PLOT_BOTTOM)
        edges = [self.left + int(round(k * (self.right - self.left) / NOTES)) for k in range(NOTES + 1)]
        self.slots = [(edges[k], edges[k + 1]) for k in range(NOTES)]
        self.font_size = max(6, int(round(FONT_SIZE * scale)))

    def bars(self, note: int) -> tuple[tuple[int, int], tuple[int, int]]:
        """The columns (first, last) of the frequency bar and of the amplitude bar of a note: the two halves of its slot, with a gap at the end."""
        x0, x1 = self.slots[note]
        half = max(1, (x1 - x0 - GAP) // 2)
        return (x0, x0 + half - 1), (x0 + half, x0 + 2 * half - 1)


def _text_color(background: np.ndarray) -> tuple[int, int, int]:
    """Black on a light background, white on a dark one (by the relative luminance of the color)."""
    luminance = (0.2126 * background[0] + 0.7152 * background[1] + 0.0722 * background[2]) / 255.0
    return (0, 0, 0) if luminance > 0.5 else (255, 255, 255)


def _background(layout: _Layout, table: np.ndarray, ink: tuple[int, int, int]) -> Image.Image:
    """The part of the picture that never changes: the background color, the title, the legend, the baseline and the octave labels."""
    background = tuple(int(c) for c in table[MIDDLE_COLOR_ROW])
    picture = Image.new("RGB", (layout.width, layout.height), background)
    draw = ImageDraw.Draw(picture)
    font = ImageFont.load_default(size=layout.font_size)
    draw.text((layout.left, layout.y(TITLE_Y)), TITLE, fill=ink, font=font, anchor="lt")
    # the legend, at the right of the title row: a square in the color of each data set and its name
    start, end = (tuple(int(c) for c in table[row]) for row in (0, COLORMAP_STEPS - 1))
    square, gap = layout.s(SQUARE), layout.s(4)
    x = layout.right - sum(square + gap + font.getlength(name) for name in LEGEND) - layout.s(14) * (len(LEGEND) - 1)
    y = layout.y(TITLE_Y)
    for name, color in zip(LEGEND, (start, end)):
        draw.rectangle((x, y, x + square - 1, y + square - 1), fill=color, outline=ink)
        draw.text((x + square + gap, y + square / 2), name, fill=ink, font=font, anchor="lm")
        x += square + gap + font.getlength(name) + layout.s(14)
    draw.line((layout.left, layout.bottom, layout.right - 1, layout.bottom), fill=ink)
    for octave in range(NOTES // 12):
        x0, x1 = layout.slots[12 * octave]
        draw.text(((x0 + x1) / 2, layout.y(LABEL_Y)), f"A{octave + 1}", fill=ink, font=font, anchor="mt")
    return picture


def _frame(shares: tuple[np.ndarray, np.ndarray], base: Image.Image, layout: _Layout, table: np.ndarray) -> Image.Image:
    """One picture: the bars of the two data sets (their softmax shares above the smallest, for this frame) over the background."""
    picture = base.copy()
    tallest = max(float(shares[0].max()), float(shares[1].max()))
    if tallest <= 0:
        return picture
    draw = ImageDraw.Draw(picture)
    plot_height = layout.bottom - layout.top
    colors = [tuple(int(c) for c in table[row]) for row in (0, COLORMAP_STEPS - 1)]
    for note in range(NOTES):
        for data_set, columns in enumerate(layout.bars(note)):
            share = shares[data_set][note]
            if share <= 0:
                continue
            height = max(1, int(round(plot_height * share / tallest)))
            draw.rectangle((columns[0], layout.bottom - height, columns[1], layout.bottom - 1), fill=colors[data_set])
    return picture


def write_energy_frames(data: EnergyGraphData, colormap: str, directory: Path, width: int, height: int) -> None:
    """Save one PNG of ``width`` x ``height`` pixels per frame of ``data`` as ``frame_000000.png`` and up. Everything is checked before anything is written."""
    colormap = check_colormap(colormap)
    _check_data(data)
    if isinstance(width, bool) or isinstance(height, bool) or not isinstance(width, numbers.Integral) or not isinstance(height, numbers.Integral) or width < 1 or height < 1:
        raise ValueError("The picture size must be two whole numbers of at least 1.")
    table = lookup_table(colormap)
    layout = _Layout(int(width), int(height))
    ink = _text_color(table[MIDDLE_COLOR_ROW])
    base = _background(layout, table, ink)
    frequency = above_smallest(softmax_shares(data.histogram))
    amplitude = above_smallest(softmax_shares(data.amplitude))
    directory.mkdir(parents=True, exist_ok=True)

    def write(index: int) -> None:
        _frame((frequency[index], amplitude[index]), base, layout, table).save(directory / f"frame_{index:06d}.png", compress_level=1)

    with ThreadPoolExecutor(max_workers=_SAVE_WORKERS) as pool:
        for future in [pool.submit(write, i) for i in range(data.frame_count)]:
            future.result()  # raises the first error of a worker, if there was one
