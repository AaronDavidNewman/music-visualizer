"""Interpolated frames: drawing only every n-th frame and making the frames in between with Pillow.

The *interpolate* value ``n`` (a whole number from 1 to 5) means that only every n-th frame is **drawn** from the music:
with the frames numbered from 0 as their files are, the drawn frames are ``0, n, 2n, ...`` and always the last frame of
the file (so every frame in between has a drawn frame on each side). The drawn frames are made exactly as they are at
``n = 1``. The other frames, the **interpolated** ones, are made from the nearest drawn frame before and after them with
``Image.blend(earlier, later, w)``, the weighted mix of the two pictures, where ``w = k / g`` is the position of the frame
in its gap (``k`` frames after the earlier drawn frame, ``g`` the length of the gap: ``n``, or less at the end of the file).

(The other Pillow operations, ``ImageChops.soft_light``, ``hard_light``, ``overlay``, ``screen`` and ``subtract``, were
offered as a choice in feature 018 and removed again: they take no weight and did not give useful in-between frames.)

All the arithmetic is Pillow's: this module only chooses the pictures and the weights. The interpolated frames are made
from the PNG files of the drawn frames (read back and converted to plain RGB) and written as RGB PNG files with the
numbers they have; the drawn files are not touched. The gaps are independent, so runs of consecutive gaps are made on a few
threads (Pillow releases the interpreter lock; a run reads each drawn frame once), and the files are the same whatever the
number of threads.

This module knows nothing about the note analysis or what the pictures show.
"""

import math
import numbers
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

MIN_INTERPOLATE = 1
MAX_INTERPOLATE = 5
DEFAULT_INTERPOLATE = 1

# the number of threads that make the interpolated frames (read when the frames are made)
_WORKERS = max(1, min(4, os.cpu_count() or 1))


def check_interpolate(value) -> int:
    """Return ``value`` as an ``int`` when it is a whole number from 1 to 5 (no strings, no fractions, no booleans)."""
    if (
        isinstance(value, bool)
        or not isinstance(value, numbers.Real)
        or not math.isfinite(value)
        or int(value) != value
        or not MIN_INTERPOLATE <= value <= MAX_INTERPOLATE
    ):
        raise ValueError(f"The interpolate value must be a whole number from {MIN_INTERPOLATE} to {MAX_INTERPOLATE}.")
    return int(value)


def key_frames(count: int, interpolate: int) -> list[int]:
    """The numbers (from 0) of the frames that are drawn from the music: ``0, n, 2n, ...`` and the last frame."""
    interpolate = check_interpolate(interpolate)
    if count <= 0:
        return []
    drawn = set(range(0, count, interpolate))
    drawn.add(count - 1)
    return sorted(drawn)


def _frame_name(i: int) -> str:
    return f"frame_{i:06d}.png"


def _make_gaps(directory: Path, gaps: list[tuple[int, int]]) -> None:
    """Write the frames between the drawn frames of a run of consecutive gaps.

    Each drawn frame is read once: the later frame of a gap is the earlier frame of the next one.
    """
    earlier_number, earlier = None, None
    for a, b in gaps:
        if earlier_number != a:
            earlier = Image.open(directory / _frame_name(a)).convert("RGB")
        later = Image.open(directory / _frame_name(b)).convert("RGB")
        length = b - a
        for i in range(a + 1, b):
            Image.blend(earlier, later, (i - a) / length).save(directory / _frame_name(i), compress_level=6)
        earlier_number, earlier = b, later


def write_interpolated_frames(directory: Path, count: int, interpolate: int) -> None:
    """Write the frames of ``count`` that were not drawn, from the drawn ones already in ``directory``.

    Does nothing when ``interpolate`` is 1 or there is no gap. The setting is checked before anything is written. The
    first error of a worker is raised.
    """
    interpolate = check_interpolate(interpolate)
    drawn = key_frames(count, interpolate)
    gaps = [(a, b) for a, b in zip(drawn[:-1], drawn[1:]) if b - a > 1]
    if not gaps:
        return
    # runs of consecutive gaps, a few per worker so that the work is shared evenly and each drawn frame is read once per run
    run = max(1, -(-len(gaps) // (_WORKERS * 4)))
    runs = [gaps[k : k + run] for k in range(0, len(gaps), run)]
    pool = ThreadPoolExecutor(max_workers=_WORKERS)
    try:
        futures = [pool.submit(_make_gaps, directory, chunk) for chunk in runs]
        for future in futures:
            future.result()  # raises the first error of a worker, if there was one
    finally:
        pool.shutdown(wait=True)
