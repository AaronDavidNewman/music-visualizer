"""The note layout in the pictures (feature 026): Tiles, Blended tiles and Concentric draw the note of each cell of the layout.

Every note gets its own value here, so the color of a tile (or the size of a circle) says which note it is. The central check is
an equivalence: drawing the notes in the spiral layout is byte for byte drawing the notes that are already put in cell order with the
rows layout, so the layout changes nothing but the places.
"""

import numpy as np
import pytest
from PIL import Image

import app.services.frame_rendering as rendering
from app.services.colormaps import COLORMAPS, lookup_table
from app.services.note_layout import arrange_notes, note_order

from .frame_size import HEIGHT, WIDTH, tile_center

ORDER = note_order("spiral")
MESSAGE = "The note layout must be one of rows, spiral."
ALL_TYPES = ["tiles", "blended", "contour", "circles", "circles_paint", "concentric"]
LAID_OUT = ["tiles", "blended", "concentric"]


def notes(frames=3):
    """88 values per frame, a different value for every drawn note (and more in the later frames)."""
    base = (np.arange(88) + 1) / 84.0
    base[84:] = 0.0
    scale = np.array([1.0, 0.6, 0.9, 0.3, 0.8])[:frames]
    return base[None, :] * scale[:, None]


def padded(values):
    """Cell-ordered values, 84 per frame, as 88 columns again (the four undrawn notes are 0)."""
    return np.hstack([values, np.zeros((values.shape[0], 4))])


def files(tmp_path, label, values, image_type, **options):
    directory = tmp_path / label
    rendering.write_frames(values, directory, colormap=options.pop("colormap", COLORMAPS[0]), image_type=image_type, **options)
    return [f.read_bytes() for f in sorted(directory.glob("frame_*.png"))]


def pictures(tmp_path, label, values, image_type, **options):
    directory = tmp_path / label
    rendering.write_frames(values, directory, colormap=options.pop("colormap", COLORMAPS[0]), image_type=image_type, **options)
    return [np.asarray(Image.open(f).convert("RGB")).astype(int) for f in sorted(directory.glob("frame_*.png"))]


# ---------------------------------------------------------------------------------------------------------------------
# rows is what it always was
# ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", ALL_TYPES)
def test_the_rows_layout_gives_the_frames_that_are_made_without_the_argument(tmp_path, image_type):
    plain = files(tmp_path, "plain", notes(), image_type)
    assert files(tmp_path, "rows", notes(), image_type, note_layout="rows") == plain
    assert len(plain) == 3


# ---------------------------------------------------------------------------------------------------------------------
# tiles and blended tiles
# ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", ["tiles", "blended"])
@pytest.mark.parametrize("colormap", COLORMAPS)
def test_the_tile_of_every_cell_has_the_colour_of_the_note_that_the_layout_puts_there(tmp_path, image_type, colormap):
    rows = pictures(tmp_path, "rows", notes(), image_type, colormap=colormap)
    spiral = pictures(tmp_path, "spiral", notes(), image_type, colormap=colormap, note_layout="spiral")
    for frame in range(3):
        for cell in range(84):
            assert tuple(spiral[frame][tile_center(cell)]) == tuple(rows[frame][tile_center(int(ORDER[cell]))]), (frame, cell)
    assert not np.array_equal(rows[0], spiral[0])


@pytest.mark.parametrize("image_type", ["tiles", "blended"])
@pytest.mark.parametrize(
    "options",
    [
        {},
        {"threshold": 5},
        {"smoothing": 0.5, "smoothing_window": 3},
        {"resolution": 3},
        {"resolution": 2, "threshold": 3},
        {"interpolate": 2},
        {"gaussian": 2.0},
        {"beat": np.array([0.0, 0.5, 1.0])},
        {"blend_width": 10},
        {"threshold": 4, "smoothing": 0.3, "smoothing_window": 2, "resolution": 2, "interpolate": 2, "gaussian": 1.0, "beat": np.array([1.0, 0.2, 0.7])},
    ],
)
def test_drawing_the_notes_in_the_spiral_is_drawing_the_cell_ordered_notes_in_rows(tmp_path, image_type, options):
    values = notes()
    spiral = files(tmp_path, "spiral", values, image_type, note_layout="spiral", **options)
    rows = files(tmp_path, "rows", padded(arrange_notes(values, "spiral")), image_type, note_layout="rows", **options)
    assert spiral == rows


@pytest.mark.parametrize("threshold", [3, 6, 10])
def test_the_same_notes_are_hidden_in_both_layouts(tmp_path, threshold):
    values = notes(1)
    spiral = pictures(tmp_path, "spiral", values, "tiles", threshold=threshold, note_layout="spiral")[0]
    rows = pictures(tmp_path, "rows", values, "tiles", threshold=threshold)[0]
    hidden_rows = {n for n in range(84) if tuple(rows[tile_center(n)]) == (0, 0, 0)}
    hidden_spiral = {int(ORDER[cell]) for cell in range(84) if tuple(spiral[tile_center(cell)]) == (0, 0, 0)}
    assert hidden_rows == hidden_spiral and 0 < len(hidden_rows) < 84
    assert hidden_rows == {n for n in range(84) if (n + 1) / 84.0 < threshold / 100.0}


@pytest.mark.parametrize("image_type", ["tiles", "blended"])
@pytest.mark.parametrize("count", [12, 36, 60])
def test_the_notes_kept_by_notes_are_spread_in_pitch_order_along_the_spiral(tmp_path, image_type, count):
    values = notes(2)
    values[:, 10] = 5.0  # a few notes that are by far the strongest
    values[:, 70] = 4.0
    rows = pictures(tmp_path, "rows", values, image_type, note_count=count)
    spiral = pictures(tmp_path, "spiral", values, image_type, note_count=count, note_layout="spiral")
    for frame in range(2):
        for cell in range(84):
            assert tuple(spiral[frame][tile_center(cell)]) == tuple(rows[frame][tile_center(int(ORDER[cell]))])
    assert not np.array_equal(rows[0], spiral[0])


def test_a_finer_grid_blends_the_tiles_that_are_next_to_each_other_on_the_screen(tmp_path):
    values = np.zeros((1, 88))
    values[0, 27] = 1.0  # middle C alone: in the spiral it is in the middle of the grid
    spiral = pictures(tmp_path, "spiral", values, "tiles", resolution=3, note_layout="spiral")[0]
    rows = pictures(tmp_path, "rows", values, "tiles", resolution=3)[0]
    background = tuple(spiral[0, 0])
    for picture, cell in ((spiral, 2 * 12 + 5), (rows, 27)):
        row, column = divmod(cell, 12)
        y, x = tile_center(cell)
        assert tuple(picture[y, x]) != background  # the note's own tile
        assert tuple(picture[y, x + 50]) != background or tuple(picture[y, x - 50]) != background or column in (0, 11)  # its neighbours get some of it
    assert not np.array_equal(spiral, rows)


# ---------------------------------------------------------------------------------------------------------------------
# concentric
# ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("beat", [None, np.array([0.0, 0.5, 1.0])])
def test_drawing_concentric_in_the_spiral_is_drawing_the_cell_ordered_notes_in_rows(tmp_path, beat):
    values = notes()
    options = {} if beat is None else {"beat": beat}
    spiral = files(tmp_path, "spiral", values, "concentric", note_layout="spiral", **options)
    rows = files(tmp_path, "rows", padded(arrange_notes(values, "spiral")), "concentric", **options)
    assert spiral == rows
    assert spiral != files(tmp_path, "plain", values, "concentric", **options)


def test_the_loudest_circle_is_centered_on_the_cell_of_its_note_with_all_twelve_rings(tmp_path):
    colormap = COLORMAPS[0]
    background = tuple(lookup_table(colormap)[128])
    for offset in (-27, -3, 0, 1, 4, 56):
        values = np.zeros((1, 88))
        values[0, 27 + offset] = 1.0
        picture = pictures(tmp_path, f"c{offset}", values, "concentric", note_layout="spiral", beat=np.array([1.0]))[0]
        silent = pictures(tmp_path, f"s{offset}", np.zeros((1, 88)), "concentric", note_layout="spiral", beat=np.array([1.0]))[0]
        changed = (picture != silent).any(axis=2)
        cell = int(np.flatnonzero(ORDER == 27 + offset)[0])
        row, column = divmod(cell, 12)
        ys, xs = np.nonzero(changed)
        assert len(ys) > 500
        y0, y1 = int(np.rint(row * HEIGHT / 7)), int(np.rint((row + 1) * HEIGHT / 7))
        x0, x1 = column * 50, (column + 1) * 50
        assert ys.min() >= y0 and ys.max() < y1 and xs.min() >= x0 and xs.max() < x1  # inside its own cell
        assert xs.max() - xs.min() >= 48  # a full circle: 50 pixels across
        assert tuple(picture[0, 0]) == background


# ---------------------------------------------------------------------------------------------------------------------
# the other pictures ignore it, and a bad value is refused
# ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", ["contour", "circles", "circles_paint"])
def test_contour_and_the_circles_ignore_the_layout(tmp_path, image_type):
    assert files(tmp_path, "spiral", notes(), image_type, note_layout="spiral") == files(tmp_path, "rows", notes(), image_type)


@pytest.mark.parametrize("image_type", ALL_TYPES)
@pytest.mark.parametrize("value", ["Spiral", "ROWS", " rows", "", "circle", None, 1])
def test_a_layout_that_is_not_offered_is_refused_before_anything_is_written(tmp_path, image_type, value):
    directory = tmp_path / "refused"
    with pytest.raises(ValueError) as error:
        rendering.write_frames(notes(2), directory, colormap=COLORMAPS[0], image_type=image_type, note_layout=value)
    assert str(error.value) == MESSAGE
    assert not directory.exists() or not list(directory.iterdir())


@pytest.mark.parametrize("image_type", LAID_OUT)
def test_two_runs_are_identical_and_the_frames_keep_their_size(tmp_path, image_type):
    one = files(tmp_path, "one", notes(), image_type, note_layout="spiral")
    two = files(tmp_path, "two", notes(), image_type, note_layout="spiral")
    assert one == two
    assert pictures(tmp_path, "size", notes(1), image_type, note_layout="spiral")[0].shape == (HEIGHT, WIDTH, 3)
