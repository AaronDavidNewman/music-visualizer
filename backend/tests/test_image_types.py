"""The list of kinds of picture and its check: ``app/services/image_types.py``, and the grid that the pictures of notes share: ``app/services/note_grid.py``."""

import numpy as np
import pytest

from app.services.image_types import DEFAULT_IMAGE_TYPE, IMAGE_TYPES, check_image_type
from app.services.note_grid import GRID_COLUMNS, GRID_ROWS, NOTES, RINGS, _check_values, full_radius, tile_edges


def test_the_kinds_of_picture_are_the_eight_that_are_left_and_the_default_is_the_contour():
    assert IMAGE_TYPES == ("contour", "decay", "decay-exp", "polar-chords", "energy-graphs", "chromatic-decay", "rhythm-circles", "chromatic-wireframe")
    assert DEFAULT_IMAGE_TYPE == "contour" and DEFAULT_IMAGE_TYPE in IMAGE_TYPES


@pytest.mark.parametrize("value", IMAGE_TYPES)
def test_the_offered_image_types_are_accepted(value):
    assert check_image_type(value) == value


@pytest.mark.parametrize(
    "bad",
    ["tiles", "blended", "circles", "circles_paint", "concentric", "Contour", " contour", "contour ", "", "gradient", "decay_exp", None, 3, True, ["contour"]],
)
def test_other_image_types_are_refused_and_so_are_the_five_that_were_removed(bad):
    with pytest.raises(ValueError) as error:
        check_image_type(bad)
    assert str(error.value) == f"The image type must be one of {', '.join(IMAGE_TYPES)}."


def test_the_grid_is_12_columns_by_7_rows_of_84_notes_with_12_rings():
    assert (GRID_COLUMNS, GRID_ROWS, NOTES, RINGS) == (12, 7, 84, 12)


def test_tile_edges_are_the_multiples_of_the_tile_size_when_it_divides_and_within_a_pixel_of_even_otherwise():
    assert tile_edges(12, 600).tolist() == list(range(0, 601, 50))
    edges = tile_edges(7, 400)
    assert edges[0] == 0 and edges[-1] == 400 and len(edges) == 8
    widths = np.diff(edges)
    assert widths.min() >= 57 and widths.max() <= 58 and widths.sum() == 400
    for count, size in ((12, 600), (7, 400), (60, 600), (35, 400), (3, 10)):
        edges = tile_edges(count, size)
        assert edges[0] == 0 and edges[-1] == size and np.ptp(np.diff(edges)) <= 1


def test_the_full_radius_is_half_the_narrower_side_of_a_cell():
    assert full_radius(600, 400) == 25  # the cells are 50 pixels wide and 57 or 58 high
    assert full_radius(1200, 800) == 50
    assert full_radius(120, 700) == 5  # a cell narrower than it is high


def test_note_values_are_checked_as_a_float_array_of_at_least_84_columns():
    assert _check_values(np.zeros((3, 88))).shape == (3, 88)
    assert _check_values(np.zeros((0, 84))).shape == (0, 84)
    for bad in (np.zeros((3, 83)), np.zeros(84), np.full((2, 84), np.nan), np.full((2, 84), np.inf), np.full((2, 84), -0.5)):
        with pytest.raises(ValueError):
            _check_values(bad)
