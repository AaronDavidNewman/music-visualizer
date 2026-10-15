"""The size of a frame, in one place for the tests that need it.

``WIDTH`` and ``HEIGHT`` are the app's frame size; the tests that look at frames read them here so that a change of the size
is a change of two constants. ``test_frame_size.py`` states the size as literal numbers, so that a wrong constant is still
caught. ``REFERENCE_WIDTH`` and ``REFERENCE_HEIGHT`` are the old 252 x 168 frame: the unit in which the circles' Movement and
Radius are measured. The tile edges and centers are those of the original 12 x 7 grid on this frame size.
"""

from app.services.frame_rendering import GRID_COLUMNS, GRID_ROWS
from app.services.frame_rendering import IMAGE_HEIGHT as HEIGHT
from app.services.frame_rendering import IMAGE_WIDTH as WIDTH
from app.services.image_types import tile_edges

REFERENCE_WIDTH = 252
REFERENCE_HEIGHT = 168
SCALE = WIDTH / REFERENCE_WIDTH

COLUMN_EDGES = tile_edges(GRID_COLUMNS, WIDTH)
ROW_EDGES = tile_edges(GRID_ROWS, HEIGHT)


def tile_center(note: int) -> tuple[int, int]:
    """The ``(row, column)`` pixel at the center of the tile of this note (0 to 83) of the original grid."""
    row, column = divmod(note, GRID_COLUMNS)
    return (int(ROW_EDGES[row] + ROW_EDGES[row + 1]) // 2, int(COLUMN_EDGES[column] + COLUMN_EDGES[column + 1]) // 2)
