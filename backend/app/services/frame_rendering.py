"""Turn per-window note values into per-frame colour images.

Frame ``f`` covers ``[f / frame_rate, (f + 1) / frame_rate)`` seconds. It is the mean of
the windows that start inside that period, or, if none does, the most recent window that
started before the period (which is the window covering its start when windows are consecutive).
Each frame becomes a 12 x 7 grid of coloured tiles (one row per octave, one column per note name,
252 x 168 pixels, 3:2). Each tile is an HSV colour. The frame's brightness (the HSV value, the same for every
tile) comes from the overall energy of the audio in the frame, so louder sounds brighten the whole picture. A
tile's saturation is local to it: its gray level after the brightness root (shown to the user as Saturation).
Its hue starts at 180 degrees and is moved by the (added-up) levels of related notes. Each of hue, saturation and
brightness can finally be rounded to a few evenly spaced levels (see ``color_levels``); by default they are smooth.
"""

import colorsys
import functools
import math
import numbers
from pathlib import Path

import numpy as np
from PIL import Image

from .color_levels import HUE_SCALE, HUE_STEPS, UNIT_SCALE, UNIT_STEPS, check_step, snap
from .note_analysis import NOTE_COUNT, AnalysisResult

# 12 columns (the notes of an octave) by 7 rows (octaves) of tiles 21 wide by 24 tall: tile width is
# 87.5% of its height, so the 252 x 168 image is exactly 3:2, since (12 * 0.875) / 7 = 1.5.
GRID_COLUMNS = 12
GRID_ROWS = 7
SHOWN_NOTES = GRID_COLUMNS * GRID_ROWS  # notes 0..83 are drawn; the four highest (84..87) are not
TILE_WIDTH = 21
TILE_HEIGHT = 24
IMAGE_WIDTH = GRID_COLUMNS * TILE_WIDTH
IMAGE_HEIGHT = GRID_ROWS * TILE_HEIGHT

# The brightness setting of the API is the root applied to each gray level (2 = square root). Since feature 010 a
# tile's boosted gray level is its saturation, so the page labels this setting Saturation. Fixed range; 2 is the default.
MIN_BRIGHTNESS = 2
MAX_BRIGHTNESS = 100
DEFAULT_BRIGHTNESS = 2

# The energy setting of the API is the root that lifts quiet frames' brightness (the page labels it Brightness): the
# brightness of a frame is (its energy / the largest energy) ** (1 / root). A whole number from 1 to 8; 1 (a straight
# proportion) is the default.
MIN_ENERGY = 1
MAX_ENERGY = 8
DEFAULT_ENERGY = 1

# Smoothing is a running average of each note over the frames (0 = none). Fixed range; 0 is the default.
MIN_SMOOTHING = 0.0
MAX_SMOOTHING = 0.8
DEFAULT_SMOOTHING = 0.0

# Colour: each tile is HSV with the frame's value (its brightness, from the frame's energy; see ``value_sequence``), the
# tile's own gray level as the saturation, and a hue that starts at 180 degrees (0.5 of the wheel) and is moved by
# related notes. Notes in RELATED_DOWN pull the hue down (toward green, yellow, red) and notes in RELATED_UP push it up
# (toward blue, violet, red). The offsets are note numbers relative to the tile's own note. Their levels are added up
# (not averaged), and the hue is clipped to 0..360 degrees. The lists may have different lengths.
# Used only by helpers called without a frame brightness (full); the job path always passes the energy-derived one.
DEFAULT_VALUE = 1.0
DEFAULT_HUE = 0.5
RELATED_DOWN = (4, 5, 7)
RELATED_UP = (3, 6, 8, 11)
_PARTNER_REACH = max(abs(o) for o in RELATED_DOWN + RELATED_UP)

assert SHOWN_NOTES <= NOTE_COUNT
assert TILE_WIDTH * 8 == TILE_HEIGHT * 7  # tile width is exactly 87.5% of its height
assert IMAGE_WIDTH * 2 == IMAGE_HEIGHT * 3  # exactly 3:2

# Guards ceil() against floating-point noise such as 5.000000000000001.
_EPSILON = 1e-9
# Samples. A window starting this close below a frame boundary still belongs to the later frame.
_BOUNDARY_TOLERANCE = 1e-6


def frame_count(sample_count: int, sample_rate: float, frame_rate: float) -> int:
    """Number of frames for audio of ``sample_count`` samples: duration * frame rate, rounded up."""
    return max(0, math.ceil(sample_count * frame_rate / sample_rate - _EPSILON))


def average_frames(result: AnalysisResult, frame_rate: float, frames: int) -> np.ndarray:
    """Average the window rows of ``result`` into ``frames`` rows of 88 values.

    Windows are assigned to frames by their exact start position (``k * step``), not by the rounded
    start sample. A frame whose period has no window start uses the last window that started before it.
    """
    windows = result.frames
    if frames == 0 or windows.shape[0] == 0:
        return np.zeros((frames, NOTE_COUNT))

    positions = result.window_positions
    boundaries = np.arange(frames + 1) * (result.sample_rate / frame_rate) - _BOUNDARY_TOLERANCE
    edges = np.searchsorted(positions, boundaries, side="left")
    first, stop = edges[:-1], edges[1:]
    earlier = np.maximum(first - 1, 0)

    running = np.vstack([np.zeros((1, NOTE_COUNT)), np.cumsum(windows, axis=0)])
    counts = stop - first
    has_windows = counts > 0
    out = windows[earlier].copy()
    out[has_windows] = (running[stop[has_windows]] - running[first[has_windows]]) / counts[has_windows, None]
    return np.maximum(out, 0.0)


def smooth_frames(frames: np.ndarray, smoothing: float = DEFAULT_SMOOTHING) -> np.ndarray:
    """A running average of every note over the frames: ``s * previous + (1 - s) * current``.

    ``frames`` has one row per frame and one column per note. The first frame has nothing before it and
    is left as it is; every later frame is ``smoothing`` times the previous *smoothed* frame plus
    ``1 - smoothing`` times its own values. Each note uses only its own history. ``smoothing`` is a number
    from 0.0 to 0.8; 0 returns the values unchanged. The input is never modified.
    """
    if (
        isinstance(smoothing, bool)
        or not isinstance(smoothing, numbers.Real)
        or not math.isfinite(smoothing)
        or not MIN_SMOOTHING <= smoothing <= MAX_SMOOTHING
    ):
        raise ValueError(f"The smoothing must be a number from {MIN_SMOOTHING} to {MAX_SMOOTHING}.")
    out = np.array(frames, dtype=np.float64, copy=True)
    if smoothing == 0 or out.shape[0] < 2:
        return out
    s = float(smoothing)
    for n in range(1, out.shape[0]):
        out[n] = s * out[n - 1] + (1.0 - s) * out[n]
    return out


def to_gray_levels(frames: np.ndarray) -> np.ndarray:
    """Scale to 0..255 against the largest value anywhere in ``frames`` (linear, no other normalization)."""
    peak = float(frames.max()) if frames.size else 0.0
    if peak <= 0:
        return np.zeros(frames.shape, dtype=np.uint8)
    return np.rint(255.0 * frames / peak).astype(np.uint8)


@functools.lru_cache(maxsize=None)
def _boost_table(brightness: int) -> np.ndarray:
    """Displayed level for each of the 256 input levels: ``255 * (level / 255) ** (1 / brightness)``, rounded."""
    table = np.rint(255.0 * np.power(np.arange(256) / 255.0, 1.0 / brightness)).astype(np.uint8)
    table.setflags(write=False)
    return table


def boost_levels(levels: np.ndarray, brightness: int = DEFAULT_BRIGHTNESS) -> np.ndarray:
    """Brighten quiet values with the ``brightness``-th root: ``255 * (level / 255) ** (1 / brightness)``.

    ``levels`` are integers 0..255 and ``brightness`` is a whole number from 2 to 100 (2 is the square
    root). 0 stays black and 255 stays white at every brightness, and a higher brightness is never darker.
    """
    if (
        isinstance(brightness, bool)
        or not isinstance(brightness, numbers.Integral)
        or not MIN_BRIGHTNESS <= brightness <= MAX_BRIGHTNESS
    ):
        raise ValueError(f"The brightness must be a whole number from {MIN_BRIGHTNESS} to {MAX_BRIGHTNESS}.")
    index = np.asarray(levels)
    if index.size and (index.min() < 0 or index.max() > 255):
        raise ValueError("Gray levels must be from 0 to 255.")
    return _boost_table(int(brightness))[index]


def _require_drawable(levels: np.ndarray) -> np.ndarray:
    levels = np.asarray(levels)
    if levels.shape[-1] < SHOWN_NOTES:
        raise ValueError(f"At least {SHOWN_NOTES} gray levels are needed to draw a frame (got {levels.shape[-1]}).")
    return levels


def tile_hues(levels: np.ndarray, brightness: int = DEFAULT_BRIGHTNESS) -> np.ndarray:
    """The hue of each of the 84 drawn tiles, as a fraction of the colour wheel between 0 and 1.

    Brightness is each note's final gray level (after the brightness root) divided by 255. For note ``n``,
    ``D`` is the *sum* of the brightness of the notes ``n + o`` for ``o`` in ``RELATED_DOWN`` and ``U`` the sum
    for ``RELATED_UP`` (the groups need not be the same size, and nothing is averaged). The hue is
    ``0.5 + 0.5 * (U - D)``, clipped to 0..1: 180 degrees, moved down by ``D / 2`` of the wheel and up by
    ``U / 2``. Because sums are used, one partner at full brightness is already enough to reach red; most
    tiles, whose partners are dim, land well inside the wheel and are not clipped. Partners outside the
    88-note series count as silent. Notes 84 to 87 are not drawn but are real partners. 0 and 1 are the same red.
    """
    levels = _require_drawable(levels)
    shown = boost_levels(levels, brightness).astype(np.float64) / 255.0
    padded = np.zeros(shown.shape[0] + 2 * _PARTNER_REACH)
    padded[_PARTNER_REACH : _PARTNER_REACH + shown.shape[0]] = shown
    tiles = np.arange(SHOWN_NOTES) + _PARTNER_REACH

    def total(offsets):
        return sum(padded[tiles + o] for o in offsets)

    hues = DEFAULT_HUE + 0.5 * (total(RELATED_UP) - total(RELATED_DOWN))
    return np.clip(hues, 0.0, 1.0)


def hue_sequence(
    levels: np.ndarray, brightness: int = DEFAULT_BRIGHTNESS, smoothing: float = DEFAULT_SMOOTHING
) -> np.ndarray:
    """The hue of every drawn tile in every frame, shape ``(frames, 84)``, smoothed over the frames.

    ``levels`` has one row of gray levels per frame. Each frame's hues come from ``tile_hues``. They are then
    smoothed with the same running average as the note values (``smooth_frames``): each tile's hue is
    ``smoothing`` times that tile's smoothed hue in the previous frame plus ``1 - smoothing`` times its own
    hue in this frame, and the first frame is left as it is. Hue is treated as a plain number from 0 to 1
    (not as a circle), as it is clipped to that range, so smoothing never leaves it. With smoothing 0 the
    hues are exactly those of ``tile_hues``.
    """
    levels = np.asarray(levels)
    hues = np.array([tile_hues(row, brightness) for row in levels]).reshape(-1, SHOWN_NOTES)
    return smooth_frames(hues, smoothing)


def _check_energy_root(root) -> int:
    if (
        isinstance(root, bool)
        or not isinstance(root, numbers.Real)
        or not math.isfinite(root)
        or root != int(root)
        or not MIN_ENERGY <= root <= MAX_ENERGY
    ):
        raise ValueError(f"The energy must be a whole number from {MIN_ENERGY} to {MAX_ENERGY}.")
    return int(root)


def value_sequence(
    energies: np.ndarray, energy_root: int = DEFAULT_ENERGY, smoothing: float = DEFAULT_SMOOTHING
) -> np.ndarray:
    """The brightness (HSV value) of every frame, from 0 to 1, one per energy (shared by all 84 tiles of the frame).

    ``(energy / the largest energy) ** (1 / energy_root)``: the loudest frame is exactly 1 (100%) and a frame
    with no energy is 0 (black). If no frame has any energy every brightness is 0. ``energy_root`` is a whole number
    from 1 to 8. The values are then smoothed over the frames with the same running average as the notes and
    the hues (``smooth_frames``); with smoothing 0 they are exactly the values above.
    """
    root = _check_energy_root(energy_root)
    energies = np.asarray(energies, dtype=np.float64)
    if energies.ndim != 1:
        raise ValueError("The energies must be a 1-D array with one value per frame.")
    if energies.size and not (np.isfinite(energies).all() and (energies >= 0).all()):
        raise ValueError("The energies must be numbers of 0 or more.")
    peak = float(energies.max()) if energies.size else 0.0
    mapped = np.zeros(energies.shape) if peak <= 0 else (energies / peak) ** (1.0 / root)
    return smooth_frames(mapped.reshape(-1, 1), smoothing).reshape(-1)


def _check_value(value: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, numbers.Real)
        or not math.isfinite(value)
        or not 0.0 <= value <= 1.0
    ):
        raise ValueError("The brightness must be a number from 0 to 1.")
    return float(value)


def tile_colors(
    levels: np.ndarray,
    brightness: int = DEFAULT_BRIGHTNESS,
    hues: np.ndarray | None = None,
    value: float = DEFAULT_VALUE,
    saturation_step: int | None = None,
) -> np.ndarray:
    """The RGB colour (``uint8``, shape ``(84, 3)``) of each drawn tile.

    HSV with the hue from ``tile_hues`` (or the ``hues`` given, 84 values from 0 to 1, such as a row of
    ``hue_sequence``), the ``value`` given (the frame's brightness, one number from 0 to 1 for every tile; full
    when none is given) and the tile's own displayed gray level divided by 255 as its saturation, converted with
    ``colorsys``; each channel is rounded to 0..255 (halves go to the even number). Every tile's largest channel is
    the frame's brightness (``value`` times 255) and its smallest is that times one minus the saturation, so a tile
    with no level is a plain gray or white at the frame's brightness, and a frame with value 0 is black.

    ``saturation_step`` (``None`` = N/A, or 5, 10, 20, 50) rounds each tile's saturation to the nearest of the levels
    0, step, 2 * step ... 100 percent (halves go up) before the conversion; hue and value are not touched.
    """
    saturation_step = check_step(saturation_step, UNIT_STEPS, "saturation")
    value = _check_value(value)
    levels = _require_drawable(levels)
    if hues is None:
        hues = tile_hues(levels, brightness)
    hues = np.asarray(hues, dtype=np.float64)
    if hues.shape != (SHOWN_NOTES,):
        raise ValueError(f"Exactly {SHOWN_NOTES} hues are needed (got shape {hues.shape}).")
    hues = hues.tolist()
    saturations = boost_levels(levels[:SHOWN_NOTES], brightness).astype(np.float64) / 255.0
    saturations = snap(saturations, saturation_step, UNIT_SCALE).tolist()
    rgb = [colorsys.hsv_to_rgb(h, s, value) for h, s in zip(hues, saturations)]
    return np.rint(np.array(rgb) * 255.0).astype(np.uint8)


def render_frame(
    levels: np.ndarray, brightness: int = DEFAULT_BRIGHTNESS, value: float = DEFAULT_VALUE
) -> Image.Image:
    """Draw gray levels (0..255, boosted by the brightness-th root, as each tile's saturation) as 12 x 7 coloured
    tiles of 21 x 24 pixels, all at the frame brightness ``value`` (0 to 1, full by default).

    Tile (row r, column c) is note 12 * r + c, so each row is an octave and each column one note name:
    the tile below a note is the same note one octave higher (double the frequency). Note 0 is the
    top-left tile. Only the first 84 notes are drawn; the four highest notes of the 88-note series are not,
    though they still colour the tiles they are related to. Each tile is one flat colour (see ``tile_colors``)
    and the image is 8-bit RGB.
    """
    colours = tile_colors(levels, brightness, value=value).reshape(GRID_ROWS, GRID_COLUMNS, 3)
    pixels = np.repeat(np.repeat(colours, TILE_HEIGHT, axis=0), TILE_WIDTH, axis=1)
    return Image.fromarray(pixels, mode="RGB")


# The number of the tile each pixel belongs to. A frame has at most 84 flat colours, so it is saved as an
# indexed-colour PNG: this index image never changes and only the 84-entry palette differs per frame.
_TILE_INDEX_BYTES = (
    np.repeat(
        np.repeat(np.arange(SHOWN_NOTES, dtype=np.uint8).reshape(GRID_ROWS, GRID_COLUMNS), TILE_HEIGHT, axis=0),
        TILE_WIDTH,
        axis=1,
    )
    .astype(np.uint8)
    .tobytes()
)


def _palette_frame(colours: np.ndarray) -> Image.Image:
    """The frame as an indexed-colour image whose palette is the 84 tile colours (decodes to exactly ``render_frame``)."""
    image = Image.frombytes("P", (IMAGE_WIDTH, IMAGE_HEIGHT), _TILE_INDEX_BYTES)
    image.putpalette(np.ascontiguousarray(colours, dtype=np.uint8).tobytes())
    return image


def write_frames(
    frames: np.ndarray,
    directory: Path,
    brightness: int = DEFAULT_BRIGHTNESS,
    smoothing: float = DEFAULT_SMOOTHING,
    energies: np.ndarray | None = None,
    energy_root: int = DEFAULT_ENERGY,
    hue_step: int | None = None,
    saturation_step: int | None = None,
    value_step: int | None = None,
) -> None:
    """Save one PNG per row of ``frames`` (averaged note values) as ``frame_000000.png`` and up.

    ``smoothing`` (0.0 to 0.8, default none) smooths the note values over the frames (before they are
    scaled to gray levels), each tile's hue and each frame's brightness, all with the same running average.

    ``hue_step`` (12, 36, 90, 180), ``saturation_step`` and ``value_step`` (the frame brightness; 5, 10, 20, 50) round
    that property to evenly spaced levels (``color_levels``) as the very last step, after smoothing and the roots;
    ``None`` (N/A, the default) leaves it smooth. A frame is rounded from its own values only.

    ``energies`` is one energy per frame (see ``energy.frame_energies``). Each frame's brightness, shared by all
    its tiles, comes from it by ``value_sequence`` with ``energy_root`` (a whole number from 1 to 8), so louder
    frames are brighter. Each tile's saturation is its own level (after the ``brightness`` root). Without
    ``energies`` every frame is at full brightness (``DEFAULT_VALUE``).

    The files are indexed-colour PNGs (lossless: each frame has at most 84 flat colours), which decode to
    exactly the pixels ``render_frame`` returns but cost about a third of the time to encode as 24-bit RGB.
    """
    hue_step = check_step(hue_step, HUE_STEPS, "hue")
    saturation_step = check_step(saturation_step, UNIT_STEPS, "saturation")
    value_step = check_step(value_step, UNIT_STEPS, "brightness")
    values = None
    if energies is not None:
        energies = np.asarray(energies, dtype=np.float64)
        if energies.shape != (frames.shape[0],):
            raise ValueError(
                f"There must be one energy per frame (got {energies.size} energies for {frames.shape[0]} frames)."
            )
        values = snap(value_sequence(energies, energy_root, smoothing), value_step, UNIT_SCALE)
    directory.mkdir(parents=True, exist_ok=True)
    levels = to_gray_levels(smooth_frames(frames, smoothing))
    hues = snap(hue_sequence(levels, brightness, smoothing), hue_step, HUE_SCALE)
    for i, row in enumerate(levels):
        value = DEFAULT_VALUE if values is None else float(values[i])
        colours = tile_colors(row, brightness, hues[i], value, saturation_step)
        # Level 6 makes these files about a third of the size of level 1 for roughly 0.2 s more per 10,000 frames.
        _palette_frame(colours).save(directory / f"frame_{i:06d}.png", compress_level=6)
