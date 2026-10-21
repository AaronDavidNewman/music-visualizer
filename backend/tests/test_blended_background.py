"""Blended tiles: a tile that the threshold hides is not drawn, so it stays the background, the middle color of the colormap.

The Tiles image type keeps its black for a hidden tile (the user's "testing mode"); Contour is not touched.
"""

import numpy as np
import pytest
from PIL import Image

import app.services.frame_rendering as rendering
from app.services.circles import MIDDLE_COLOR_ROW
from app.services.colormaps import COLORMAPS, lookup_table
from app.services.image_types import make_grid_blender, tile_edges

from .frame_size import COLUMN_EDGES, HEIGHT, WIDTH, tile_center

LIT = 26  # tile (row 2, column 2) of the original grid


def middle(colormap):
    return tuple(int(v) for v in lookup_table(colormap)[MIDDLE_COLOR_ROW])


def top(colormap):
    return tuple(int(v) for v in lookup_table(colormap)[255])


def one_note(note=LIT):
    values = np.zeros((1, 88))
    values[0, note] = 1.0  # every other tile has no value, so the threshold hides it
    return values


def frame(tmp_path, label, values, colormap, **options):
    directory = tmp_path / label
    rendering.write_frames(values, directory, colormap=colormap, **options)
    return [np.asarray(Image.open(f).convert("RGB")).astype(int) for f in sorted(directory.glob("frame_*.png"))]


@pytest.mark.parametrize("colormap", COLORMAPS)
def test_a_hidden_blended_tile_is_the_middle_color_of_the_colormap_and_the_lit_tile_is_its_own_color(tmp_path, colormap):
    picture = frame(tmp_path, "blended", one_note(), colormap, image_type="blended", threshold=5)[0]
    for note in (0, 25, 27, 38, 80, 83):  # tiles far enough from the lit one that the fade does not reach their centers
        assert tuple(picture[tile_center(note)]) == middle(colormap), (colormap, note)
    assert tuple(picture[tile_center(LIT)]) == top(colormap)


@pytest.mark.parametrize("colormap", COLORMAPS)
def test_a_hidden_flat_tile_is_still_black(tmp_path, colormap):
    picture = frame(tmp_path, "tiles", one_note(), colormap, image_type="tiles", threshold=5)[0]
    for note in (0, 25, 27, 80):
        assert tuple(picture[tile_center(note)]) == (0, 0, 0), (colormap, note)
    assert tuple(picture[tile_center(LIT)]) == top(colormap)


@pytest.mark.parametrize("colormap", COLORMAPS)
def test_the_edge_of_a_lit_tile_fades_toward_the_background_not_toward_black(tmp_path, colormap):
    picture = frame(tmp_path, "blended", one_note(), colormap, image_type="blended", threshold=5)[0]
    y = tile_center(LIT)[0]
    lit, background = np.array(top(colormap)), np.array(middle(colormap))
    for edge in (int(COLUMN_EDGES[2]), int(COLUMN_EDGES[3])):  # the left and the right edge of the lit tile
        average = (picture[y, edge - 1] + picture[y, edge]) / 2
        assert np.abs(average - (lit + background) / 2).max() <= 1.5, (colormap, edge)  # an even mix at the edge itself


def test_every_pixel_between_the_lit_tile_and_the_background_is_a_mix_of_just_those_two_colors(tmp_path):
    colormap = COLORMAPS[0]
    picture = frame(tmp_path, "blended", one_note(), colormap, image_type="blended", threshold=5)[0]
    lit, background = np.array(top(colormap)), np.array(middle(colormap))
    low, high = np.minimum(lit, background), np.maximum(lit, background)
    assert ((picture >= low - 1) & (picture <= high + 1)).all()  # no black anywhere: nothing darker than the two colors
    assert (picture == background).all(axis=2).sum() > 0.8 * WIDTH * HEIGHT  # most of the picture is the plain background


@pytest.mark.parametrize("colormap", COLORMAPS)
def test_a_silent_file_hides_nothing_so_both_kinds_keep_the_first_color_of_the_colormap(tmp_path, colormap):
    # the existing rule: the threshold is a share of the loudest note, and a silent file has none, so no tile is hidden
    values = np.zeros((3, 88))
    for image_type in ("blended", "tiles"):
        for picture in frame(tmp_path, image_type, values, colormap, image_type=image_type, threshold=10):
            assert (picture == np.array(lookup_table(colormap)[0])).all()


@pytest.mark.parametrize("colormap", COLORMAPS)
def test_with_the_threshold_off_nothing_is_hidden_and_the_picture_is_the_plain_blend_of_the_colors(tmp_path, colormap):
    values = np.random.default_rng(3).random((2, 88)) ** 2
    pictures = frame(tmp_path, "blended", values, colormap, image_type="blended")
    tiles = frame(tmp_path, "tiles", values, colormap, image_type="tiles")
    blend = make_grid_blender(rendering.DEFAULT_BLEND_WIDTH if hasattr(rendering, "DEFAULT_BLEND_WIDTH") else 25, 12, 7, WIDTH, HEIGHT)
    for i, picture in enumerate(pictures):
        colours = np.array([tiles[i][tile_center(n)] for n in range(84)], dtype=np.uint8)
        assert (picture == blend(colours)).all(), (colormap, i)  # no tile was replaced by the background


def test_a_note_that_fades_below_the_threshold_turns_into_the_background_and_not_into_black(tmp_path):
    colormap = COLORMAPS[0]
    values = np.zeros((4, 88))
    values[:, 60] = 0.02  # a faint note: 2% of the loudest, under a threshold of 5
    values[:, 26] = [1.0, 1.0, 1.0, 1.0]
    values[2:, 60] = 0.0
    values[0:2, 60] = 0.5  # loud enough in frames 0 and 1
    pictures = frame(tmp_path, "blended", values, colormap, image_type="blended", threshold=5)
    shown, hidden = pictures[0][tile_center(60)], pictures[3][tile_center(60)]
    assert tuple(hidden) == middle(colormap) and tuple(shown) != middle(colormap)


@pytest.mark.parametrize("resolution", [2, 3, 5])
def test_it_holds_at_every_oversampling(tmp_path, resolution):
    colormap = COLORMAPS[0]
    picture = frame(tmp_path, "blended", one_note(), colormap, image_type="blended", threshold=5, resolution=resolution)[0]
    columns, rows = 12 * resolution, 7 * resolution
    xs, ys = tile_edges(columns, WIDTH), tile_edges(rows, HEIGHT)
    corner = ((ys[0] + ys[1]) // 2, (xs[0] + xs[1]) // 2)  # the tile in the top left corner, far from the lit one
    assert tuple(picture[corner]) == middle(colormap)
    assert (picture == np.array(middle(colormap))).all(axis=2).sum() > 0.5 * WIDTH * HEIGHT


def test_the_other_ways_of_hiding_nothing_else_changes(tmp_path):
    # the same file with the threshold off has no hidden tile at all, so the background never shows: the frames are not middle colored
    colormap = COLORMAPS[0]
    values = np.random.default_rng(5).random((1, 88)) ** 2 + 0.2
    picture = frame(tmp_path, "blended", values, colormap, image_type="blended")[0]
    assert (picture == np.array(middle(colormap))).all(axis=2).mean() < 0.1
