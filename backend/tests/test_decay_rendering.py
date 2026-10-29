"""The pictures of the ``decay`` kind: size and color from the points, smooth edges, ``write_frames`` (feature 027)."""

import numpy as np
import pytest
from PIL import Image

from app.services.colormaps import COLORMAPS, lookup_table
from app.services.decay import circle_colors, circle_points, circle_radii, ring_colors, write_decay_frames
from app.services.frame_rendering import write_frames
from app.services.image_types import tile_edges
from app.services.note_layout import MIDDLE_C_CELL, MIDDLE_C_NOTE

from .frame_size import HEIGHT, WIDTH

MIDDLE = 128
COLUMN_EDGES = tile_edges(12, WIDTH)
ROW_EDGES = tile_edges(7, HEIGHT)


def centre(cell: int) -> tuple[int, int]:
    """The pixel (x, y) at the center of a cell of the 12 x 7 grid."""
    row, column = divmod(cell, 12)
    return (COLUMN_EDGES[column] + COLUMN_EDGES[column + 1]) // 2, (ROW_EDGES[row] + ROW_EDGES[row + 1]) // 2


def draw(directory, points, colormap="viridis") -> np.ndarray:
    write_decay_frames(np.atleast_2d(points), colormap, directory, WIDTH, HEIGHT)
    return np.array(Image.open(directory / "frame_000000.png").convert("RGB"))


def points_of(**cells) -> np.ndarray:
    result = np.zeros(84)
    for name, value in cells.items():
        result[int(name[1:])] = value
    return result


def all_frames(directory) -> list[bytes]:
    return [path.read_bytes() for path in sorted(directory.glob("frame_*.png"))]


def song(frames=30, notes=((30, 1.0),), until=None) -> np.ndarray:
    values = np.zeros((frames, 88))
    for note, value in notes:
        values[: until or frames, note] = value
    return values


# ---- the files ------------------------------------------------------------------------------------------------------------------


def test_one_600_by_400_rgb_png_per_row_of_points_named_from_zero(tmp_path):
    write_decay_frames(np.zeros((3, 84)), "viridis", tmp_path, WIDTH, HEIGHT)
    assert [p.name for p in sorted(tmp_path.glob("*.png"))] == [f"frame_{i:06d}.png" for i in range(3)]
    image = Image.open(tmp_path / "frame_000002.png")
    assert image.size == (WIDTH, HEIGHT) and image.mode == "RGB"


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_background_is_the_middle_color_of_the_colormap(tmp_path, name):
    picture = draw(tmp_path, np.zeros(84), name)
    assert tuple(picture[0, 0]) == tuple(lookup_table(name)[MIDDLE])
    assert tuple(picture[HEIGHT - 1, WIDTH - 1]) == tuple(lookup_table(name)[MIDDLE])


# ---- size and color -------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["viridis", "coolwarm", "Greys"])
@pytest.mark.parametrize("points", [0, 6, 12, 24, 32])
def test_the_circle_has_the_color_and_the_width_of_its_points(tmp_path, name, points):
    cell = 30
    picture = draw(tmp_path, points_of(c30=points), name)
    x, y = centre(cell)
    assert tuple(picture[y, x]) == tuple(circle_colors(np.array(points), name))
    row = picture[y]
    colour = circle_colors(np.array(points), name).astype(int)
    background = lookup_table(name)[MIDDLE].astype(int)
    left, right = COLUMN_EDGES[cell % 12], COLUMN_EDGES[cell % 12 + 1]
    # the width of the disc along the middle row: the coverage of every pixel summed (the pixels of a smooth edge count in part)
    channel = int(np.argmax(np.abs(colour - background)))
    if abs(colour[channel] - background[channel]) < 8:
        pytest.skip("the circle and the background are almost the same color")
    share = (row[left:right, channel].astype(float) - background[channel]) / (colour[channel] - background[channel])
    assert share.sum() == pytest.approx(2 * float(circle_radii(points)), abs=1.0)


def test_a_circle_never_leaves_its_cell_and_the_rest_is_the_background(tmp_path):
    picture = draw(tmp_path, np.full(84, 64.0))
    background = lookup_table("viridis")[MIDDLE]
    corner = picture[ROW_EDGES[3] + 1, COLUMN_EDGES[5] + 1]  # the corner of a cell is outside the full circle
    assert tuple(corner) == tuple(background)
    for cell in (0, 11, 83, 40):
        row, column = divmod(cell, 12)
        left, right = COLUMN_EDGES[column], COLUMN_EDGES[column + 1]
        top, bottom = ROW_EDGES[row], ROW_EDGES[row + 1]
        x, y = centre(cell)
        outside = np.hypot(np.arange(WIDTH)[None, :] + 0.5 - (left + right) / 2, np.arange(HEIGHT)[:, None] + 0.5 - (top + bottom) / 2) > 26
        cell_mask = np.zeros((HEIGHT, WIDTH), bool)
        cell_mask[top:bottom, left:right] = True
        assert (picture[outside & cell_mask] == background).all()


def test_the_full_circle_just_touches_its_neighbours_in_a_row(tmp_path):
    picture = draw(tmp_path, points_of(c30=24, c31=24)).astype(int)
    x, y = centre(30)
    last = lookup_table("viridis")[int(np.rint(24 / 32 * 255))].astype(int)
    boundary = COLUMN_EDGES[7]  # between column 6 and column 7
    assert tuple(picture[y, boundary - 1]) == tuple(last) and tuple(picture[y, boundary]) == tuple(last)
    assert tuple(picture[y, boundary - 3]) == tuple(last)


def test_the_edge_is_smooth(tmp_path):
    picture = draw(tmp_path, points_of(c30=12))
    x, y = centre(30)
    colour = tuple(circle_colors(np.array(12), "viridis"))
    background = tuple(lookup_table("viridis")[MIDDLE])
    row = [tuple(p) for p in picture[y, x : x + 30]]
    assert any(p not in (colour, background) for p in row)  # a pixel on the border is a mix


def test_a_smaller_circle_is_inside_a_bigger_one_of_the_same_color_scale(tmp_path):
    small = draw(tmp_path, points_of(c30=3))
    big_dir = tmp_path / "big"
    big = draw(big_dir, points_of(c30=24))
    x, y = centre(30)
    shift = lookup_table("viridis")[MIDDLE].astype(int)
    assert (np.abs(small[y, x - 2 : x + 2].astype(int) - shift).sum(axis=1) > 0).all()
    assert (np.abs(big[y, x - 24 : x + 24].astype(int) - shift).sum(axis=1) > 0).all()


def test_the_picture_is_the_same_for_the_same_points(tmp_path):
    rng = np.random.default_rng(2)
    points = rng.random((4, 84)) * 64
    write_decay_frames(points, "hsv", tmp_path / "a", WIDTH, HEIGHT)
    write_decay_frames(points, "hsv", tmp_path / "b", WIDTH, HEIGHT)
    assert all_frames(tmp_path / "a") == all_frames(tmp_path / "b")


@pytest.mark.parametrize("points", [np.zeros((2, 83)), np.full((1, 84), 65.0), np.full((1, 84), -1.0), np.full((1, 84), np.nan), np.zeros(84)[None, None]])
def test_bad_points_are_refused_before_anything_is_written(tmp_path, points):
    with pytest.raises(ValueError):
        write_decay_frames(points, "viridis", tmp_path / "out", WIDTH, HEIGHT)
    assert not (tmp_path / "out").exists()


def test_a_bad_colormap_is_refused_before_anything_is_written(tmp_path):
    with pytest.raises(ValueError):
        write_decay_frames(np.zeros((1, 84)), "nope", tmp_path / "out", WIDTH, HEIGHT)
    assert not (tmp_path / "out").exists()


# ---- write_frames ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("rate", [1, 5, 10])
def test_write_frames_draws_the_points_of_the_values(tmp_path, rate):
    values = np.random.default_rng(4).random((25, 88))
    beat = np.linspace(0, 1, 25)
    write_frames(values, tmp_path / "a", colormap="viridis", image_type="decay", beat=beat, decay_rate=rate)
    write_decay_frames(circle_points(values, beat, "rows", rate), "viridis", tmp_path / "b", WIDTH, HEIGHT)
    assert all_frames(tmp_path / "a") == all_frames(tmp_path / "b") and len(all_frames(tmp_path / "a")) == 25


def test_write_frames_uses_the_default_rate_5_and_no_beat_means_position_0(tmp_path):
    values = song(12)
    write_frames(values, tmp_path / "a", image_type="decay", colormap="viridis")
    write_frames(values, tmp_path / "b", image_type="decay", colormap="viridis", decay_rate=5, beat=np.zeros(12))
    assert all_frames(tmp_path / "a") == all_frames(tmp_path / "b")


def test_the_rate_changes_the_pictures(tmp_path):
    values = song(12, until=3)
    write_frames(values, tmp_path / "a", image_type="decay", colormap="viridis", decay_rate=1)
    write_frames(values, tmp_path / "b", image_type="decay", colormap="viridis", decay_rate=10)
    assert all_frames(tmp_path / "a") != all_frames(tmp_path / "b")


def test_the_beat_changes_the_points_and_the_pictures(tmp_path):
    values = song(3)
    write_frames(values, tmp_path / "a", image_type="decay", colormap="viridis", beat=np.zeros(3))
    write_frames(values, tmp_path / "b", image_type="decay", colormap="viridis", beat=np.ones(3))
    assert all_frames(tmp_path / "a") != all_frames(tmp_path / "b")


def test_a_held_note_charges_its_circle_to_full_size_and_the_last_color_and_keeps_it_there(tmp_path):
    write_frames(song(12), tmp_path, image_type="decay", colormap="viridis", decay_rate=5)
    x, y = centre(30)
    last = tuple(lookup_table("viridis")[255])
    pictures = [np.array(Image.open(tmp_path / f"frame_{i:06d}.png").convert("RGB")) for i in range(12)]
    assert tuple(pictures[0][y, x]) == tuple(lookup_table("viridis")[int(np.rint(24 / 32 * 255))])
    assert all(tuple(p[y, x]) == last for p in pictures[2:])  # from 32 points on, saturated


def test_with_the_spiral_layout_middle_c_is_drawn_at_row_3_column_6(tmp_path):
    values = song(2, notes=((MIDDLE_C_NOTE, 1.0),))
    write_frames(values, tmp_path, image_type="decay", colormap="viridis", note_layout="spiral", decay_rate=10)
    picture = np.array(Image.open(tmp_path / "frame_000000.png").convert("RGB"))
    row, column = MIDDLE_C_CELL
    x, y = centre(row * 12 + column)
    assert tuple(picture[y, x]) == tuple(circle_colors(np.array(24), "viridis"))
    other = centre(0)
    assert tuple(picture[other[1], other[0]]) == tuple(circle_colors(np.array(0), "viridis"))


GRID_FIELDS = [
    {"threshold": 5.0},
    {"note_count": 20},
    {"resolution": 3},
    {"interpolate": 3},
    {"gaussian": 2.0},
    {"blend_width": 10},
    {"circle_unit": 9},
    {"circle_memory": 100},
    {"circle_notes": 12},
    {"circle_radius": 8},
    {"circle_resize": True},
]


@pytest.mark.parametrize("fields", GRID_FIELDS)
def test_the_settings_of_the_other_pictures_are_checked_and_have_no_effect(tmp_path, fields):
    values = np.random.default_rng(6).random((8, 88))
    write_frames(values, tmp_path / "a", image_type="decay", colormap="viridis")
    write_frames(values, tmp_path / "b", image_type="decay", colormap="viridis", **fields)
    assert all_frames(tmp_path / "a") == all_frames(tmp_path / "b")


@pytest.mark.parametrize("image_type", ["tiles", "blended", "contour", "circles", "circles_paint", "concentric", "decay"])
@pytest.mark.parametrize("bad", [0, 11, 2.5, True, "5", None])
def test_a_bad_decay_rate_is_refused_before_anything_is_written_for_every_type(tmp_path, image_type, bad):
    with pytest.raises(ValueError, match="The decay rate must be a whole number from 1 to 10."):
        write_frames(song(3), tmp_path / "out", image_type=image_type, colormap="viridis", decay_rate=bad)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("image_type", ["tiles", "blended", "contour", "circles", "circles_paint", "concentric"])
def test_the_decay_rate_has_no_effect_on_the_other_types(tmp_path, image_type):
    values = np.random.default_rng(8).random((6, 88))
    write_frames(values, tmp_path / "a", image_type=image_type, colormap="viridis")
    write_frames(values, tmp_path / "b", image_type=image_type, colormap="viridis", decay_rate=1)
    assert all_frames(tmp_path / "a") == all_frames(tmp_path / "b")


def test_a_bad_layout_is_refused_for_decay_before_anything_is_written(tmp_path):
    with pytest.raises(ValueError, match="The note layout must be one of rows, spiral."):
        write_frames(song(3), tmp_path / "out", image_type="decay", colormap="viridis", note_layout="Spiral")
    assert not (tmp_path / "out").exists()


# ---- silent and short -----------------------------------------------------------------------------------------------------------


def test_a_silent_file_makes_frames_of_84_identical_smallest_dots_in_the_first_color(tmp_path):
    write_frames(np.zeros((5, 88)), tmp_path, image_type="decay", colormap="viridis")
    assert len(set(all_frames(tmp_path))) == 1
    picture = np.array(Image.open(tmp_path / "frame_000000.png").convert("RGB"))
    first = tuple(lookup_table("viridis")[0])
    for cell in range(84):
        x, y = centre(cell)
        assert tuple(picture[y, x]) == first
    assert tuple(picture[0, 0]) == tuple(lookup_table("viridis")[MIDDLE])


def test_no_frames_make_no_files_and_no_error(tmp_path):
    write_frames(np.zeros((0, 88)), tmp_path / "out", image_type="decay", colormap="viridis")
    assert not list((tmp_path / "out").glob("*.png"))


# ---- the rings from 32 to 64 points ---------------------------------------------------------------------------------------------


def reference_cell(points: float, colormap: str, cell: int, scale: int = 8) -> np.ndarray:
    """The cell drawn by brute force: ``scale`` x ``scale`` samples a pixel, each in its ring or outside the circle, averaged down."""
    row, column = divmod(cell, 12)
    left, right = COLUMN_EDGES[column], COLUMN_EDGES[column + 1]
    top, bottom = ROW_EDGES[row], ROW_EDGES[row + 1]
    cx, cy = (left + right) / 2, (top + bottom) / 2
    xs = (np.arange((right - left) * scale) + 0.5) / scale + left
    ys = (np.arange((bottom - top) * scale) + 0.5) / scale + top
    distance = np.hypot(xs[None, :] - cx, ys[:, None] - cy)
    radius = float(circle_radii(np.array(points)))
    ring_width = 25.0 / 12
    ring = np.clip(np.ceil(distance / ring_width).astype(int) - 1, 0, 11)
    colours = ring_colors(np.array(points), colormap).astype(float)
    background = lookup_table(colormap)[MIDDLE].astype(float)
    samples = np.where((distance <= radius)[:, :, None], colours[ring], background)
    height, width = bottom - top, right - left
    return samples.reshape(height, scale, width, scale, 3).mean(axis=(1, 3))


@pytest.mark.parametrize("name", ["viridis", "coolwarm", "Greys"])
def test_at_64_points_the_rings_run_from_the_last_color_at_the_center_to_the_first_at_the_edge(tmp_path, name):
    table = lookup_table(name)
    rings = ring_colors(np.array(64.0), name)
    assert [tuple(c) for c in rings[[0, 11]]] == [tuple(table[255]), tuple(table[0])]
    picture = draw(tmp_path, points_of(c30=64), name)
    x, y = centre(30)
    assert tuple(picture[y, x]) == tuple(table[255])  # the center is the last color
    assert np.abs(picture[y, x + 23].astype(int) - table[0].astype(int)).max() < np.abs(picture[y, x + 23].astype(int) - table[255].astype(int)).max()
    assert len({tuple(p) for p in picture[y, x : x + 25]}) >= 8  # the rings are seen


@pytest.mark.parametrize("points", [24, 28, 32])
def test_up_to_32_points_the_circle_is_flat(tmp_path, points):
    picture = draw(tmp_path, points_of(c30=points))
    x, y = centre(30)
    colour = tuple(circle_colors(np.array(points), "viridis"))
    inside = [tuple(p) for p in picture[y, x - 22 : x + 22]]
    assert set(inside) == {colour}


def test_the_rings_open_up_as_the_points_rise_and_close_again_as_they_fall(tmp_path):
    x, y = centre(30)
    spread = []
    for points in (32, 40, 48, 56, 64):
        picture = draw(tmp_path / str(points), points_of(c30=points))
        spread.append(int(np.abs(picture[y, x + 23].astype(int) - picture[y, x].astype(int)).sum()))
    assert spread[0] == 0 or spread[0] < spread[1] < spread[2] < spread[3] < spread[4]


@pytest.mark.parametrize("points", [36, 48, 64])
def test_the_picture_of_the_rings_is_what_drawing_them_on_a_finer_canvas_gives(tmp_path, points):
    picture = draw(tmp_path, points_of(c30=points)).astype(float)
    row, column = divmod(30, 12)
    cell = picture[ROW_EDGES[row] : ROW_EDGES[row + 1], COLUMN_EDGES[column] : COLUMN_EDGES[column + 1]]
    difference = np.abs(cell - reference_cell(points, "viridis", 30))
    assert difference.mean() < 2.5, difference.mean()
    assert difference.max() < 70, difference.max()


def test_each_ring_has_the_color_of_its_position_at_its_middle(tmp_path):
    table = lookup_table("viridis")
    picture = draw(tmp_path, points_of(c30=64))
    x, y = centre(30)
    rings = ring_colors(np.array(64.0), "viridis")
    for k in range(12):
        middle = (k + 0.5) * 25.0 / 12
        sample = picture[y, int(round(x + middle - 0.5))].astype(int)
        # a pixel on the row at the middle of a ring is in that ring, give or take half a pixel of the edge with its neighbours
        near = [rings[j].astype(int) for j in (max(k - 1, 0), k, min(k + 1, 11))]
        assert min(np.abs(sample - c).max() for c in near) <= 16, (k, sample, near)
    assert tuple(rings[0]) == tuple(table[255])
