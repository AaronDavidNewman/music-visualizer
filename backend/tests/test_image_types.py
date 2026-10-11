"""The blended tiles picture: ``app/services/image_types.py``."""

import math

import numpy as np
import pytest

from app.services.image_types import (
    DEFAULT_BLEND_WIDTH,
    DEFAULT_IMAGE_TYPE,
    IMAGE_TYPES,
    MAX_BLEND_WIDTH,
    MIN_BLEND_WIDTH,
    blend_tile_colors,
    check_blend_width,
    check_image_type,
    make_blender,
)

COLUMNS, ROWS, TW, TH = 12, 7, 21, 24
WIDTH, HEIGHT = COLUMNS * TW, ROWS * TH
GEOMETRY = (COLUMNS, ROWS, TW, TH)


def random_colors(seed, lit=0.6):
    rng = np.random.default_rng(seed)
    return (rng.integers(0, 256, (ROWS * COLUMNS, 3)) * (rng.random((ROWS * COLUMNS, 1)) < lit)).astype(np.uint8)


def flat_picture(colors):
    """The tiles picture: every tile a flat rectangle."""
    grid = colors.reshape(ROWS, COLUMNS, 3)
    return np.repeat(np.repeat(grid, TH, axis=0), TW, axis=1)


def own_weight(distance, reach):
    """The Gaussian feather written out plainly from the specification: sigma = reach / 4, truncated and renormalised."""
    sigma = reach / 4
    tail = 0.5 * (1 + math.erf(-4 / math.sqrt(2)))  # Phi(-4)
    cumulative = 0.5 * (1 + math.erf(distance / sigma / math.sqrt(2)))
    return min(1.0, max(0.5, (cumulative - tail) / (1 - 2 * tail)))


def axis_pair(index, tile, count, reach):
    """Own tile, neighbouring tile and own weight of one pixel, written out plainly from the specification."""
    pos = index + 0.5
    t = index // tile
    if t > 0 and pos - t * tile < reach:
        return t, t - 1, own_weight(pos - t * tile, reach)
    if t < count - 1 and (t + 1) * tile - pos < reach:
        return t, t + 1, own_weight((t + 1) * tile - pos, reach)
    return t, t, 1.0


def reference(colors, pct):
    """A deliberately naive per-pixel version of the blend: the four weighted tile colours of every pixel."""
    reach = pct / 100 * TW
    grid = colors.reshape(ROWS, COLUMNS, 3).astype(float)
    out = np.zeros((HEIGHT, WIDTH, 3))
    contributors = np.zeros((HEIGHT, WIDTH, 4, 3))
    for y in range(HEIGHT):
        r, rn, wv = axis_pair(y, TH, ROWS, reach)
        for x in range(WIDTH):
            c, cn, wh = axis_pair(x, TW, COLUMNS, reach)
            parts = [(wv * wh, grid[r, c]), (wv * (1 - wh), grid[r, cn]), ((1 - wv) * wh, grid[rn, c]), ((1 - wv) * (1 - wh), grid[rn, cn])]
            out[y, x] = sum(w * col for w, col in parts)
            contributors[y, x] = [col for _, col in parts]
    return np.rint(out).astype(np.uint8), contributors


def test_constants():
    assert IMAGE_TYPES == ("tiles", "blended")
    assert DEFAULT_IMAGE_TYPE == "tiles"
    assert (MIN_BLEND_WIDTH, MAX_BLEND_WIDTH, DEFAULT_BLEND_WIDTH) == (10, 25, 25)


@pytest.mark.parametrize("pct", [10, 12.5, 15, 20, 25])
def test_matches_the_naive_reference_to_within_one_level(pct):
    colors = random_colors(int(pct * 10))
    expected, contributors = reference(colors, pct)
    got = blend_tile_colors(colors, pct, *GEOMETRY)
    assert got.shape == (HEIGHT, WIDTH, 3) and got.dtype == np.uint8
    assert np.abs(got.astype(int) - expected.astype(int)).max() <= 1
    # a convex combination never leaves the range of the colours that are mixed (exactly, in 8-bit values)
    assert (got >= contributors.min(axis=2)).all() and (got <= contributors.max(axis=2)).all()


def outside_all_bands(pct):
    """True for the pixels that no inner edge reaches, on either axis."""
    reach = pct / 100 * TW
    # a pixel is in a band of an axis when the plain reference gives it a neighbouring tile
    near_x = np.array([axis_pair(i, TW, COLUMNS, reach)[2] < 1.0 for i in range(WIDTH)])
    near_y = np.array([axis_pair(i, TH, ROWS, reach)[2] < 1.0 for i in range(HEIGHT)])
    return ~near_y[:, None] & ~near_x[None, :]


@pytest.mark.parametrize("pct", [10, 17, 25])
def test_pixels_outside_every_band_have_exactly_their_tile_colour(pct):
    colors = random_colors(5)
    got = blend_tile_colors(colors, pct, *GEOMETRY)
    mask = outside_all_bands(pct)
    flat = flat_picture(colors)
    # the flat middles are about ((21 - 2B) / 21) * ((24 - 2B) / 24) of the picture, a little more at the border
    reach = pct / 100 * TW
    expected_share = (TW - 2 * reach) / TW * (TH - 2 * reach) / TH
    assert mask.mean() > expected_share - 0.02
    assert (got[mask] == flat[mask]).all()
    # a changed pixel is always within the reach of an inner edge on at least one axis
    assert not mask[~(got == flat).all(axis=2)].any()


@pytest.mark.parametrize("pct", [10, 15, 25])
def test_the_pixels_beside_an_inner_edge_average_to_the_even_mix(pct):
    colors = random_colors(7)
    got = blend_tile_colors(colors, pct, *GEOMETRY).astype(int)
    grid = colors.reshape(ROWS, COLUMNS, 3).astype(int)
    for r in range(ROWS):
        for k in range(1, COLUMNS):  # vertical edge between column k-1 and k, on the middle row of tile row r
            y, x = TH * r + TH // 2, TW * k
            average = (got[y, x - 1] + got[y, x]) / 2
            assert np.abs(average - (grid[r, k - 1] + grid[r, k]) / 2).max() <= 1
    for r in range(1, ROWS):
        for c in range(COLUMNS):  # horizontal edge between row r-1 and r, on the middle column of tile column c
            y, x = TH * r, TW * c + TW // 2
            average = (got[y - 1, x] + got[y, x]) / 2
            assert np.abs(average - (grid[r - 1, c] + grid[r, c]) / 2).max() <= 1


@pytest.mark.parametrize("pct", [10, 25])
def test_the_colour_changes_monotonically_across_a_band_without_overshoot(pct):
    colors = random_colors(8)
    got = blend_tile_colors(colors, pct, *GEOMETRY).astype(int)
    grid = colors.reshape(ROWS, COLUMNS, 3).astype(int)
    for r in range(ROWS):
        for k in range(1, COLUMNS):
            y, x = TH * r + TH // 2, TW * k
            seq = got[y, x - 7 : x + 7]
            left, right = grid[r, k - 1], grid[r, k]
            for channel in range(3):
                sign = np.sign(right[channel] - left[channel])
                assert (np.diff(seq[:, channel]) * sign >= 0).all()
                assert seq[:, channel].min() >= min(left[channel], right[channel])
                assert seq[:, channel].max() <= max(left[channel], right[channel])


def test_a_frame_of_one_colour_and_a_black_frame_are_unchanged():
    for color in ((200, 100, 50), (0, 0, 0), (255, 255, 255)):
        colors = np.tile(np.array(color, dtype=np.uint8), (ROWS * COLUMNS, 1))
        assert (blend_tile_colors(colors, 25, *GEOMETRY) == flat_picture(colors)).all()


def test_four_tiles_meet_in_an_even_quarter_each():
    colors = random_colors(9, lit=1.0)
    got = blend_tile_colors(colors, 25, *GEOMETRY).astype(int)
    grid = colors.reshape(ROWS, COLUMNS, 3).astype(int)
    for r in range(1, ROWS):
        for c in range(1, COLUMNS):
            y, x = TH * r, TW * c
            around = got[y - 1 : y + 1, x - 1 : x + 1].reshape(4, 3).mean(axis=0)
            mean = grid[r - 1 : r + 1, c - 1 : c + 1].reshape(4, 3).mean(axis=0)
            assert np.abs(around - mean).max() <= 1


def test_the_border_of_the_picture_is_not_blended():
    colors = random_colors(10)
    got = blend_tile_colors(colors, 25, *GEOMETRY)
    grid = colors.reshape(ROWS, COLUMNS, 3)
    for r in range(ROWS):  # the first and last pixel column, in the middle of each tile row
        assert (got[TH * r + TH // 2, 0] == grid[r, 0]).all()
        assert (got[TH * r + TH // 2, WIDTH - 1] == grid[r, COLUMNS - 1]).all()
    for c in range(COLUMNS):  # the first and last pixel row, in the middle of each tile column
        assert (got[0, TW * c + TW // 2] == grid[0, c]).all()
        assert (got[HEIGHT - 1, TW * c + TW // 2] == grid[ROWS - 1, c]).all()


def test_a_changed_tile_only_reaches_its_own_area_and_the_bands_around_it():
    base = random_colors(11, lit=1.0)
    changed = base.copy()
    r, c = 3, 5
    changed[COLUMNS * r + c] = (255 - base[COLUMNS * r + c]).astype(np.uint8)
    a = blend_tile_colors(base, 25, *GEOMETRY)
    b = blend_tile_colors(changed, 25, *GEOMETRY)
    differs = (a != b).any(axis=2)
    ys, xs = np.nonzero(differs)
    assert ys.min() >= TH * r - 6 and ys.max() < TH * (r + 1) + 6
    assert xs.min() >= TW * c - 6 and xs.max() < TW * (c + 1) + 6


def test_the_end_of_a_row_does_not_blend_with_the_start_of_the_next_row():
    base = random_colors(12, lit=1.0)
    changed = base.copy()
    changed[COLUMNS * 3 + 0] = (255 - base[COLUMNS * 3 + 0]).astype(np.uint8)  # first tile of row 3
    a = blend_tile_colors(base, 25, *GEOMETRY)
    b = blend_tile_colors(changed, 25, *GEOMETRY)
    # the last tile of row 2 (the note just before it) and the last tile of row 3 are far away in the picture
    assert (a[TH * 2 : TH * 3, TW * 11 :] == b[TH * 2 : TH * 3, TW * 11 :]).all()
    assert (a[TH * 3 : TH * 4, TW * 11 :] == b[TH * 3 : TH * 4, TW * 11 :]).all()


def test_a_black_tile_fades_with_its_coloured_neighbour():
    colors = np.zeros((ROWS * COLUMNS, 3), dtype=np.uint8)
    colors[COLUMNS * 2 + 4] = (200, 100, 50)  # tile (2, 4); its neighbours are black
    got = blend_tile_colors(colors, 25, *GEOMETRY).astype(int)
    y, x = TH * 2 + TH // 2, TW * 4  # the edge between tile (2, 3) (black) and tile (2, 4)
    assert np.abs((got[y, x - 1] + got[y, x]) / 2 - np.array([100, 50, 25])).max() <= 1
    assert got[y, x - 5].max() < got[y, x - 1].max()  # darker the farther into the black tile
    assert (got[y, x + 6 : x + 15] == (200, 100, 50)).all()


def test_wider_fades_change_more_pixels_and_never_fewer():
    colors = random_colors(13)
    flat = flat_picture(colors)
    counts = []
    for pct in range(MIN_BLEND_WIDTH, MAX_BLEND_WIDTH + 1):
        got = blend_tile_colors(colors, pct, *GEOMETRY)
        counts.append(int((got != flat).any(axis=2).sum()))
    assert all(a <= b for a, b in zip(counts, counts[1:]))
    assert counts[-1] > counts[0] > 0


def test_the_input_is_not_modified_and_results_repeat():
    colors = random_colors(14)
    before = colors.copy()
    blender = make_blender(18, *GEOMETRY)
    a, b = blender(colors), blender(colors)
    assert (colors == before).all()
    assert (a == b).all()
    assert (blend_tile_colors(colors, 18, *GEOMETRY) == a).all()


@pytest.mark.parametrize("value", ["tiles", "blended"])
def test_the_offered_image_types_are_accepted(value):
    assert check_image_type(value) == value


@pytest.mark.parametrize("bad", ["", "Tiles", "BLENDED", " tiles", "tiles ", "gradient", None, 1, b"tiles"])
def test_other_image_types_are_refused(bad):
    with pytest.raises(ValueError) as error:
        check_image_type(bad)
    assert str(error.value) == "The image type must be one of tiles, blended."


@pytest.mark.parametrize("value", [10, 25, 12.5, np.int64(20), 17])
def test_blend_widths_in_range_are_accepted(value):
    assert check_blend_width(value) == float(value)


@pytest.mark.parametrize("bad", [9.99, 25.01, 0, -1, True, float("nan"), float("inf"), "15", None])
def test_other_blend_widths_are_refused(bad):
    with pytest.raises(ValueError) as error:
        check_blend_width(bad)
    assert str(error.value) == "The blend width must be a number from 10 to 25."


def test_make_blender_refuses_a_bad_width():
    with pytest.raises(ValueError):
        make_blender(30, *GEOMETRY)


def test_the_feather_is_crisper_than_a_straight_ramp_over_the_same_distance():
    # a white tile next to a black one, along one row, at the widest fade (reach 5.25 pixels, so about 10 pixels across)
    colors = np.zeros((ROWS * COLUMNS, 3), dtype=np.uint8)
    colors[COLUMNS * 3 + 5] = (255, 255, 255)  # tile (3, 5); its left neighbour (3, 4) is black
    got = blend_tile_colors(colors, 25, *GEOMETRY).astype(int)
    y, x = TH * 3 + TH // 2, TW * 5  # the edge between them
    reach, sigma = 5.25, 5.25 / 4
    tail = 0.5 * (1 + math.erf(-4 / math.sqrt(2)))

    def white_share(distance_into_white):  # the white tile's weight at a pixel this far into the white side
        cumulative = 0.5 * (1 + math.erf(distance_into_white / sigma / math.sqrt(2)))
        return (cumulative - tail) / (1 - 2 * tail)

    # the pixel just inside the white tile (0.5 px from the edge) and the one just inside the black tile
    assert got[y, x, 0] == pytest.approx(255 * white_share(0.5), abs=1.01)
    assert got[y, x - 1, 0] == pytest.approx(255 * (1 - white_share(0.5)), abs=1.01)
    # 3.5 pixels from the edge the white tile is within 1 level of itself; a straight ramp would still be about 42 levels off
    assert got[y, x + 3, 0] >= 254
    assert got[y, x - 4, 0] <= 1
    # but the whole feather really reaches 5 pixels: the first pixel beyond that is exactly the tile's color
    assert got[y, x + 5, 0] == 255 and got[y, x - 6, 0] == 0
