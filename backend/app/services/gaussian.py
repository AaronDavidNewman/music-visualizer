"""Gaussian smoothing of the finished pictures (the *Gaussian smoothing* setting of the Image smoothing group).

The setting is a number from 0 to 5. At 0 nothing is done and the frames are exactly what they were without it. Above 0 every
drawn frame is blurred with Pillow's ``ImageFilter.GaussianBlur``, whose radius is the standard deviation of the Gaussian in
pixels. The frame is 3:2, so the radius is 3:2 as well: a setting of ``v`` blurs by ``1.5 * v`` pixels across and ``v`` pixels
down (a setting of 4 is a radius of 6 in x and 4 in y), so the smoothing looks the same in both directions.

It applies to the kinds of picture that are made from a grid (tiles, blended tiles and contour); the circles do not use it. The
blur is applied to the frames that are drawn, before the in-between frames of ``interpolate`` are made from them, so an
in-between frame is a blend of blurred frames. A flat-colored tile frame is saved with a palette; once blurred it has more colors
than a palette holds and is saved as a true-color picture.
"""

import math
import numbers
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageFilter

MIN_GAUSSIAN = 0.0
MAX_GAUSSIAN = 5.0
DEFAULT_GAUSSIAN = 0.0

# the shape of a frame is 3:2, so a blur that looks the same in both directions is 3:2 as well
ASPECT = 3 / 2

# each frame is read, blurred and written on its own; Pillow's blur and PNG encoder release the interpreter lock
_WORKERS = max(1, min(4, os.cpu_count() or 1))


def check_gaussian(value) -> float:
    """Return ``value`` as a ``float`` when it is a number from 0 to 5; anything else is refused."""
    if (
        isinstance(value, bool)
        or not isinstance(value, numbers.Real)
        or not math.isfinite(value)
        or not MIN_GAUSSIAN <= value <= MAX_GAUSSIAN
    ):
        raise ValueError(f"The gaussian smoothing must be a number from {MIN_GAUSSIAN:g} to {MAX_GAUSSIAN:g}.")
    return float(value) + 0.0  # turns -0.0 into 0.0


def blur_radius(value: float) -> tuple[float, float]:
    """The ``(x, y)`` radius, in pixels, of a setting: 3:2 like the frame, so 4 gives (6, 4)."""
    return (value * ASPECT, value)


def blur_frames(directory: Path, indices, value: float) -> None:
    """Blur the written frames ``frame_<index>.png`` of ``indices`` in place; a setting of 0 changes nothing at all."""
    value = check_gaussian(value)
    if value == 0.0:
        return
    radius = blur_radius(value)

    def blur(index: int) -> None:
        path = directory / f"frame_{int(index):06d}.png"
        with Image.open(path) as opened:
            image = opened.convert("RGB") if opened.mode == "P" else opened.copy()
        image.filter(ImageFilter.GaussianBlur(radius)).save(path, compress_level=1)

    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        for future in [pool.submit(blur, i) for i in indices]:
            future.result()  # raises the first error of a worker, if there was one
