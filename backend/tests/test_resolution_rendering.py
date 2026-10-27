"""``write_frames(..., resolution=r)``: the pictures made from the interpolated grid, for every image type.

No colormap is named and no number of contour levels is assumed (see ``colormap_names.py``). The expected pictures are
worked out here independently: the interpolation with ``np.interp`` itself, the tile edges with ``np.rint(np.linspace())``,
the colors from the colormap's table.
"""

import numpy as np
import pytest
from PIL import Image

from app.services.colormaps import COLORMAPS, DEFAULT_COLORMAP, lookup_table
from app.services.frame_rendering import (
    GRID_COLUMNS,
    GRID_ROWS,
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    SHOWN_NOTES,
    smooth_frames,
    write_frames,
)

from .contour_expected import smoothed_flat
from .frame_size import HEIGHT, WIDTH
from .colormap_names import DECODABLE, INVALID, WITHOUT_BLACK
from .test_resolution import MESSAGE as RESOLUTION_MESSAGE
from .test_resolution import with_np_interp

RESOLUTIONS = [1, 2, 3, 4, 5]
TYPES = ["tiles", "blended", "contour"]


def notes(*frames):
    out = np.zeros((len(frames), 88))
    for i, values in enumerate(frames):
        for note, value in values.items():
            out[i, note] = value
    return out


def random_notes(frames=4, seed=1):
    return np.random.default_rng(seed).random((frames, 88)) ** 2


def write(frames, directory, **options):
    write_frames(frames, directory, **options)
    return sorted(directory.glob("frame_*.png"))


def rgb(path):
    return np.asarray(Image.open(path).convert("RGB"))


def edges(count, size):
    return np.rint(np.linspace(0, size, count + 1)).astype(int)


def tile_index(r):
    """The tile number of every pixel, worked out independently from the rounded edges."""
    columns, rows = GRID_COLUMNS * r, GRID_ROWS * r
    x = np.searchsorted(edges(columns, IMAGE_WIDTH), np.arange(IMAGE_WIDTH), side="right") - 1
    y = np.searchsorted(edges(rows, IMAGE_HEIGHT), np.arange(IMAGE_HEIGHT), side="right") - 1
    return y[:, None] * columns + x[None, :]


def expected_tile_colors(frames, name, r, smoothing=0.0, window=1, threshold=0.0):
    """(frames, 7r*12r, 3): the color of every tile worked out from np.interp, the table and the threshold."""
    smoothed = smooth_frames(frames, smoothing, window)
    peak = smoothed.max()
    values = with_np_interp(smoothed[:, :SHOWN_NOTES], r)
    table = lookup_table(name)
    share = np.minimum(values / peak, 1.0) if peak > 0 else np.zeros_like(values)
    colours = table[np.rint(np.sqrt(share) * 255).astype(int)]
    hidden = values < threshold / 100.0 * peak
    colours[hidden] = 0
    return colours, hidden


def tile_middles(picture, r):
    """The color of the middle pixel of every tile of a picture: (7r, 12r, 3)."""
    ye, xe = edges(GRID_ROWS * r, IMAGE_HEIGHT), edges(GRID_COLUMNS * r, IMAGE_WIDTH)
    ys, xs = (ye[:-1] + ye[1:] - 1) // 2, (xe[:-1] + xe[1:] - 1) // 2
    return picture[np.ix_(ys, xs)]


# --- Tiles ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("r", RESOLUTIONS)
def test_the_geometry_of_the_tiles_is_the_rounded_even_split_in_the_image_size(tmp_path, r):
    index = tile_index(r)
    columns, rows = GRID_COLUMNS * r, GRID_ROWS * r
    assert index.shape == (HEIGHT, WIDTH) and index.max() == columns * rows - 1
    widths = np.diff(edges(columns, WIDTH))
    heights = np.diff(edges(rows, HEIGHT))
    assert widths.sum() == WIDTH and heights.sum() == HEIGHT
    assert widths.max() - widths.min() <= 1 and heights.max() - heights.min() <= 1  # at most one pixel apart
    if r == 1:
        assert set(widths) == {WIDTH // 12} and set(heights) == {HEIGHT // 7, HEIGHT // 7 + 1}  # 50 pixels wide, 57 or 58 high


@pytest.mark.parametrize("name", COLORMAPS)
@pytest.mark.parametrize("r", RESOLUTIONS)
def test_tiles_are_a_grid_of_12r_by_7r_flat_tiles_each_the_color_of_its_interpolated_value(tmp_path, name, r):
    frames = random_notes(3, seed=r)
    files = write(frames, tmp_path, colormap=name, resolution=r)
    assert len(files) == 3
    expected, _ = expected_tile_colors(frames, name, r)
    for i, f in enumerate(files):
        picture = rgb(f)
        assert picture.shape == (HEIGHT, WIDTH, 3)
        assert (picture == expected[i][tile_index(r)]).all(), (name, r, i)  # every pixel: flat tiles in exact positions


@pytest.mark.parametrize("r", RESOLUTIONS)
def test_a_tiles_file_is_a_palette_png_at_the_original_grid_and_true_color_above(tmp_path, r):
    files = write(random_notes(2), tmp_path, resolution=r)
    assert Image.open(files[0]).mode == ("P" if r == 1 else "RGB")


@pytest.mark.parametrize("image_type", TYPES)
def test_resolution_one_gives_exactly_the_files_made_without_the_setting(tmp_path, image_type):
    frames = random_notes(4, seed=3)
    options = dict(smoothing=0.3, smoothing_window=2, threshold=3, image_type=image_type)
    a = write(frames, tmp_path / "a", **options)
    b = write(frames, tmp_path / "b", resolution=1, **options)
    assert [f.read_bytes() for f in a] == [f.read_bytes() for f in b]


@pytest.mark.parametrize("name", [n for n in DECODABLE][:3])
@pytest.mark.parametrize("r", [2, 3, 5])
def test_between_two_neighbouring_notes_the_tiles_step_in_order_from_one_color_to_the_other(tmp_path, name, r):
    # row 0: note 10 is the strongest (1.0), note 11 a tenth of it; the first row of the new grid is the original first row
    values = notes({10: 1.0, 11: 0.1})
    picture = rgb(write(values, tmp_path, colormap=name, resolution=r)[0])
    top_row = tile_middles(picture, r)[0]  # (12r, 3)
    table = lookup_table(name)
    rows = np.array([int(np.flatnonzero((table == c).all(axis=1))[0]) for c in top_row])
    xs = np.linspace(0, 11, 12 * r)
    between = (xs >= 10) & (xs <= 11)
    ordered = rows[between]
    assert (np.diff(ordered) <= 0).all(), (name, r, ordered)  # down from the strong note to the weak one, never back up
    assert ordered.max() <= rows.max() and ordered.min() >= round(np.sqrt(0.1) * 255) - 1  # nothing outside the two
    assert len(set(ordered.tolist())) > 2  # and gradually: several steps, not a jump


@pytest.mark.parametrize("r", RESOLUTIONS)
def test_the_scale_is_the_files_peak_including_the_undrawn_notes_at_every_resolution(tmp_path, r):
    # the loudest value of the file is note 85, which is not drawn; the corner note 0 is a quarter of it
    picture = rgb(write(notes({85: 1.0, 0: 0.25}), tmp_path, resolution=r)[0])
    table = lookup_table(DEFAULT_COLORMAP)
    assert (tile_middles(picture, r)[0, 0] == table[round(np.sqrt(0.25) * 255)]).all()


@pytest.mark.parametrize("r", RESOLUTIONS)
def test_a_note_at_a_corner_of_the_grid_keeps_its_color_at_every_resolution_and_nothing_is_above_the_peak(tmp_path, r):
    frames = notes({0: 1.0, 83: 0.5, 11: 0.2, 72: 0.1})
    picture = tile_middles(rgb(write(frames, tmp_path, resolution=r)[0]), r)
    table = lookup_table(DEFAULT_COLORMAP)
    assert (picture[0, 0] == table[255]).all()  # top-left, the peak
    assert (picture[-1, -1] == table[round(np.sqrt(0.5) * 255)]).all()  # bottom-right
    assert (picture[0, -1] == table[round(np.sqrt(0.2) * 255)]).all()
    assert (picture[-1, 0] == table[round(np.sqrt(0.1) * 255)]).all()


# --- Blended tiles ---------------------------------------------------------------------------------------------------------


def far_from_inner_edges(r, blend_width):
    """The pixels farther than the blend reach from every inner tile edge: they have exactly their tile's color."""
    columns, rows = GRID_COLUMNS * r, GRID_ROWS * r
    reach = blend_width / 100.0 * (WIDTH / columns)
    xe, ye = edges(columns, WIDTH), edges(rows, HEIGHT)

    def far(position_edges, size):
        centre = np.arange(size) + 0.5
        inner = position_edges[1:-1]
        return np.array([np.abs(inner - c).min() > reach if len(inner) else True for c in centre])

    return far(ye, HEIGHT)[:, None] & far(xe, WIDTH)[None, :]


@pytest.mark.parametrize("r", RESOLUTIONS)
@pytest.mark.parametrize("blend_width", [10, 25])
def test_blended_equals_tiles_wherever_it_is_farther_than_the_reach_from_an_edge(tmp_path, r, blend_width):
    frames = random_notes(2, seed=20 + r)
    tiles = write(frames, tmp_path / "t", resolution=r)
    blended = write(frames, tmp_path / "b", resolution=r, image_type="blended", blend_width=blend_width)
    far = far_from_inner_edges(r, blend_width)
    assert far.any()
    for t, b in zip(tiles, blended):
        pt, pb = rgb(t), rgb(b)
        assert pb.shape == (HEIGHT, WIDTH, 3)
        assert (pt[far] == pb[far]).all()  # the middle of each tile stays flat
        reach = blend_width / 100.0 * (WIDTH / (GRID_COLUMNS * r))
        if reach >= 1.0:  # below a pixel the fade is too narrow to change any pixel after rounding (the spec's share of a tile)
            assert (pt[~far] != pb[~far]).any()  # and the fade does something near the edges


@pytest.mark.parametrize("r", RESOLUTIONS)
def test_the_fade_is_a_share_of_the_tile_so_it_gets_narrower_as_the_tiles_shrink(tmp_path, r):
    columns, rows = GRID_COLUMNS * r, GRID_ROWS * r
    reach = 25 / 100.0 * (WIDTH / columns)
    frames = random_notes(2, seed=80 + r)
    tiles = rgb(write(frames, tmp_path / "t", resolution=r)[0])
    blended = rgb(write(frames, tmp_path / "b", resolution=r, image_type="blended", blend_width=25)[0])
    changed = (tiles != blended).any(axis=2)
    ys, xs = np.nonzero(changed)
    xe, ye = edges(columns, WIDTH)[1:-1], edges(rows, HEIGHT)[1:-1]
    near_x = np.abs((xs + 0.5)[:, None] - xe[None, :]).min(axis=1)
    near_y = np.abs((ys + 0.5)[:, None] - ye[None, :]).min(axis=1)
    assert (np.minimum(near_x, near_y) <= reach + 1e-9).all()  # a pixel changes only within the reach of an inner edge
    assert reach == pytest.approx(0.25 * WIDTH / columns)  # and the reach is a quarter of the mean tile width


# --- Contour -----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("r", RESOLUTIONS)
def test_the_contour_is_drawn_from_the_interpolated_grid(tmp_path, monkeypatch, r):
    from matplotlib.axes import Axes

    seen = []
    original = Axes.contourf

    def spy(self, x, y, z, *args, **kwargs):
        seen.append((np.asarray(x), np.asarray(y), np.asarray(z)))
        return original(self, x, y, z, *args, **kwargs)

    monkeypatch.setattr(Axes, "contourf", spy)
    frames = random_notes(3, seed=30 + r)
    files = write(frames, tmp_path, image_type="contour", resolution=r)
    assert len(files) == 3 and len(seen) == 3
    expected = with_np_interp(frames[:, :SHOWN_NOTES], r)
    for i, (x, y, z) in enumerate(seen):
        assert len(x) == 12 * r and len(y) == 7 * r and z.shape == (7 * r, 12 * r)
        # drawn top row first, so the data is flipped; it is the interpolated grid after the contour's own smoothing
        assert np.allclose(z[::-1].reshape(-1), smoothed_flat(expected[i], 7 * r, 12 * r), atol=1e-12)
        assert x[-1] == pytest.approx(expected[i].max()) and y[-1] == pytest.approx(expected[i].max())
    for f in files:
        picture = np.asarray(Image.open(f))
        assert picture.shape == (HEIGHT, WIDTH, 4) and (picture[..., 3] == 255).all()


# --- Every image type ---------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("name", COLORMAPS)
@pytest.mark.parametrize("r", RESOLUTIONS)
def test_a_silent_input_is_flat_in_the_first_color_at_every_resolution(tmp_path, image_type, name, r):
    for f in write(np.zeros((3, 88)), tmp_path, colormap=name, image_type=image_type, resolution=r, threshold=5):
        assert (rgb(f) == lookup_table(name)[0]).all()


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("r", RESOLUTIONS)
def test_a_frame_of_equal_values_is_one_flat_color_at_every_resolution(tmp_path, image_type, r):
    values = {n: 0.5 for n in range(84)}
    files = write(notes(values), tmp_path, image_type=image_type, resolution=r)
    picture = rgb(files[0])
    assert len({tuple(p) for p in picture.reshape(-1, 3).tolist()}) == 1


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("r", RESOLUTIONS)
def test_the_frame_count_the_names_and_the_size_do_not_depend_on_the_resolution(tmp_path, image_type, r):
    files = write(random_notes(5, seed=40), tmp_path, image_type=image_type, resolution=r)
    assert [f.name for f in files] == [f"frame_{i:06d}.png" for i in range(5)]
    assert all(Image.open(f).size == (WIDTH, HEIGHT) for f in files)


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("r", [2, 5])
def test_the_same_input_gives_byte_identical_files(tmp_path, image_type, r):
    frames = random_notes(4, seed=50)
    options = dict(image_type=image_type, resolution=r, smoothing=0.4, smoothing_window=3, threshold=4)
    a = write(frames, tmp_path / "a", **options)
    b = write(frames, tmp_path / "b", **options)
    assert [f.read_bytes() for f in a] == [f.read_bytes() for f in b]


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("bad", [0, 6, -1, 2.5, None, "3", True])
def test_a_bad_resolution_is_refused_before_anything_is_written(tmp_path, image_type, bad):
    with pytest.raises(ValueError) as error:
        write_frames(random_notes(), tmp_path / "out", image_type=image_type, resolution=bad)
    assert str(error.value) == RESOLUTION_MESSAGE
    assert not (tmp_path / "out").exists()


def test_other_arguments_are_still_checked_with_a_resolution(tmp_path):
    with pytest.raises(ValueError):
        write_frames(random_notes(), tmp_path / "out", resolution=3, colormap=INVALID[0])
    with pytest.raises(ValueError):
        write_frames(random_notes(), tmp_path / "out", resolution=3, threshold=11)
    assert not (tmp_path / "out").exists()


# --- With the other settings ----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", COLORMAPS)
@pytest.mark.parametrize("r", [2, 3, 5])
def test_smoothing_then_the_interpolation_then_the_threshold_then_the_colors(tmp_path, name, r):
    frames = random_notes(6, seed=60)
    options = dict(colormap=name, smoothing=0.5, smoothing_window=3, threshold=6, resolution=r)
    expected, _ = expected_tile_colors(frames, name, r, smoothing=0.5, window=3, threshold=6)
    for i, f in enumerate(write(frames, tmp_path, **options)):
        assert (rgb(f) == expected[i][tile_index(r)]).all(), (name, r, i)


@pytest.mark.parametrize("r", [1, 2, 3, 5])
def test_the_threshold_hides_exactly_the_tiles_whose_interpolated_value_is_below_it(tmp_path, r):
    if not WITHOUT_BLACK:
        pytest.skip("every offered colormap has pure black, so a black tile cannot be told from a hidden one")
    name = WITHOUT_BLACK[0]
    # a loud note with a quiet one next to it: the tiles between them fall below the threshold part of the way
    frames = notes({40: 1.0, 41: 0.3, 10: 0.5})
    threshold = 10
    expected, hidden = expected_tile_colors(frames, name, r, threshold=threshold)
    picture = tile_middles(rgb(write(frames, tmp_path, colormap=name, resolution=r, threshold=threshold)[0]), r)
    black = ~picture.reshape(-1, 3).any(axis=1)
    assert (black == hidden[0]).all()
    assert hidden[0].any() and not hidden[0].all()


def test_the_hidden_region_has_a_finer_edge_at_a_higher_resolution(tmp_path):
    if not WITHOUT_BLACK:
        pytest.skip("every offered colormap has pure black")
    name = WITHOUT_BLACK[0]
    frames = notes({40: 1.0, 41: 0.3, 10: 0.5})
    coarse = tile_middles(rgb(write(frames, tmp_path / "a", colormap=name, resolution=1, threshold=10)[0]), 1)
    fine = tile_middles(rgb(write(frames, tmp_path / "b", colormap=name, resolution=5, threshold=10)[0]), 5)
    coarse_hidden = ~coarse.reshape(7, 12, 3).any(axis=2)
    fine_hidden = ~fine.any(axis=2)
    # the coarse mask scaled up to the fine grid is not the fine mask: the edge of the hidden region has moved
    scaled = np.kron(coarse_hidden, np.ones((5, 5), dtype=bool))
    assert fine_hidden.shape == (35, 60) and (fine_hidden != scaled).any()


@pytest.mark.parametrize("r", [2, 5])
def test_the_threshold_zeroes_the_hidden_values_of_the_contour_grid(tmp_path, monkeypatch, r):
    from matplotlib.axes import Axes

    grids = []
    original = Axes.contourf

    def spy(self, x, y, z, *args, **kwargs):
        grids.append(np.asarray(z)[::-1].reshape(-1))
        return original(self, x, y, z, *args, **kwargs)

    monkeypatch.setattr(Axes, "contourf", spy)
    frames = notes({40: 1.0, 41: 0.3, 10: 0.5})
    write(frames, tmp_path, image_type="contour", resolution=r, threshold=10)
    values = with_np_interp(frames[:, :SHOWN_NOTES], r)[0]
    expected = np.where(values < 0.10 * 1.0, 0.0, values)
    assert np.allclose(grids[0], smoothed_flat(expected, 7 * r, 12 * r), atol=1e-12)  # the hidden values are zero before the smoothing
    assert (expected == 0).any() and (values < 0.10).any()


@pytest.mark.parametrize("name", COLORMAPS)
def test_changing_the_colormap_changes_only_the_colors_not_which_tiles_are_hidden(tmp_path, name):
    other = COLORMAPS[(COLORMAPS.index(name) + 1) % len(COLORMAPS)]
    frames = random_notes(3, seed=70)
    _, hidden_a = expected_tile_colors(frames, name, 3, threshold=7)
    _, hidden_b = expected_tile_colors(frames, other, 3, threshold=7)
    assert (hidden_a == hidden_b).all()
    if other != name:
        a = write(frames, tmp_path / "a", colormap=name, resolution=3, threshold=7)
        b = write(frames, tmp_path / "b", colormap=other, resolution=3, threshold=7)
        assert any(x.read_bytes() != y.read_bytes() for x, y in zip(a, b))
