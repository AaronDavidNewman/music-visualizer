"""The kinds of picture a frame can be drawn as.

``contour`` is the grid of note values (12 x 7) drawn as a filled contour map. It is drawn by ``contour.py``, because it needs matplotlib's drawing; this module stays
pure Python and only lists its name. ``decay`` has a circle for each of the 84 notes on the 12 x 7 grid (``note_grid.py``), each one flat disc that keeps points
from frame to frame, charged by the loudest notes and spreading into its neighbours as time passes (``decay.py``). ``decay-exp`` is ``decay`` with the points gained and lost
along an exponential curve (``decay_exp.py``). ``polar-chords`` is a polar bar graph of the loudest notes (clockwise) and the chord of the
frame (counterclockwise) (``polar_chords.py``). ``energy-graphs`` is a running histogram of the 84 notes with two data sets, which notes have been loudest (rank points) and
their accumulated amplitude (quasi-decibels), each softmaxed (``energy_graphs.py``). ``chromatic-decay`` is ``decay-exp`` for the 12 chromatic
tones only: 12 circles on a ring in circle-of-fifths order, charged by the loudest octave of each letter, whose points decay to the letters 5 and 7 above
(``chromatic_decay.py``). ``rhythm-circles`` is eight concentric notched rings that turn with the tempo of the local peaks, the aggregated tempos (the average or the fastest) of its latest 2, 4 and 8 peaks
and the rates of change of all four (``rhythm_circles.py``). ``chromatic-wireframe`` draws the points of ``chromatic-decay`` as a ridge plot in three
dimensions: one line for each frame across the 12 letters, the newest in front, each in the color of its place in the beat (``chromatic_wireframe.py``).
(Tiles, blended tiles, circles, circles paint and concentric, the first five kinds of picture, were removed in feature 040.)

This module knows nothing about the note analysis or the grid of the application.
"""

IMAGE_TYPES = ("contour", "decay", "decay-exp", "polar-chords", "energy-graphs", "chromatic-decay", "rhythm-circles", "chromatic-wireframe")
DEFAULT_IMAGE_TYPE = "contour"


def check_image_type(value) -> str:
    """Return ``value`` when it is exactly one of the offered names (no trimming, no case folding)."""
    if not isinstance(value, str) or value not in IMAGE_TYPES:
        raise ValueError(f"The image type must be one of {', '.join(IMAGE_TYPES)}.")
    return value
