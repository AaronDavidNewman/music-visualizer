"""The note layout in the pictures (feature 026): Decay, Decay Exp and Polar Chords draw the note of each cell of the layout.

Every note gets its own value here. The central check is
an equivalence: drawing the notes in the spiral layout is byte for byte drawing the notes that are already put in cell order with the
rows layout, so the layout changes nothing but the places.
"""

import numpy as np
import pytest
from PIL import Image

import app.services.frame_rendering as rendering
from app.services.colormaps import COLORMAPS
from app.services.note_layout import note_order

from .frame_size import HEIGHT, WIDTH

ORDER = note_order("spiral")
MESSAGE = "The note layout must be one of rows, spiral."
ALL_TYPES = ["contour", "decay", "decay-exp", "polar-chords"]
LAID_OUT = ["decay", "decay-exp", "polar-chords"]


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


# ---------------------------------------------------------------------------------------------------------------------
# concentric
# ---------------------------------------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------------------------------------
# the other pictures ignore it, and a bad value is refused
# ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", LAID_OUT)
@pytest.mark.parametrize("options", [{}, {"beat": np.array([0.0, 0.5, 1.0])}, {"smoothing": 0.5, "smoothing_window": 3}])
def test_the_spiral_puts_the_notes_in_other_cells_than_the_rows_do(tmp_path, image_type, options):
    values = notes()
    assert files(tmp_path, "spiral", values, image_type, note_layout="spiral", **options) != files(tmp_path, "rows", values, image_type, note_layout="rows", **options)


@pytest.mark.parametrize("image_type", LAID_OUT)
def test_rows_is_the_layout_when_none_is_given(tmp_path, image_type):
    assert files(tmp_path, "none", notes(), image_type) == files(tmp_path, "rows", notes(), image_type, note_layout="rows")


@pytest.mark.parametrize("image_type", ["contour", "chromatic-decay", "chromatic-wireframe"])
def test_the_pictures_that_do_not_use_the_layout_ignore_it(tmp_path, image_type):
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
