"""Beat coloring of Tiles and Blended tiles (feature 024): half the note strength, half the frame's position in the local peak.

``write_frames`` takes the positions as ``beat`` (one number from 0 to 1 per frame); the router makes them from the audio.
"""

import numpy as np
import pytest
from PIL import Image

import app.services.frame_rendering as rendering
from app.services.colormaps import COLORMAPS, lookup_table

from .colormap_names import DECODABLE
from .frame_size import HEIGHT, WIDTH, tile_center

STRONG = 26  # tile (row 2, column 2) of the original grid
WEAK = 62  # far from the strong one, so that the fade of a blended picture does not reach its center
TYPES = ["tiles", "blended"]
OTHER_TYPES = ["contour", "circles", "circles_paint"]
MESSAGE = "The beat must be one number from 0 to 1 for each of the {} frames."


def melody(frames=3):
    """A steady strong note (the largest value of the file) and a weaker one at a quarter of it, in every frame."""
    values = np.zeros((frames, 88))
    values[:, STRONG] = 1.0
    values[:, WEAK] = 0.25
    return values


def made(tmp_path, label, values, colormap, **options):
    directory = tmp_path / label
    rendering.write_frames(values, directory, colormap=colormap, **options)
    return [np.asarray(Image.open(f).convert("RGB")).astype(int) for f in sorted(directory.glob("frame_*.png"))]


def raw_files(tmp_path, label):
    return [f.read_bytes() for f in sorted((tmp_path / label).glob("frame_*.png"))]


def colour(table, row):
    return tuple(int(v) for v in table[row])


def at(picture, note):
    return tuple(int(v) for v in picture[tile_center(note)])


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("colormap", COLORMAPS)
def test_the_strong_tile_is_the_middle_colour_at_position_0_and_the_last_colour_at_position_1(tmp_path, image_type, colormap):
    pictures = made(tmp_path, "a", melody(), colormap, image_type=image_type, beat=np.array([0.0, 0.5, 1.0]))
    table = lookup_table(colormap)
    assert [at(p, STRONG) for p in pictures] == [colour(table, 128), colour(table, round(0.75 * 255)), colour(table, 255)]
    # the weaker tile (a quarter of the strongest, square root 0.5): 0.25, 0.5 and 0.75 of the way along
    assert [at(p, WEAK) for p in pictures] == [colour(table, round(0.25 * 255)), colour(table, round(0.5 * 255)), colour(table, round(0.75 * 255))]
    assert all(p.shape == (HEIGHT, WIDTH, 3) for p in pictures)


@pytest.mark.parametrize("image_type", TYPES)
def test_every_frame_uses_its_own_position(tmp_path, image_type):
    beat = np.array([1.0, 0.0, 0.25, 1.0, 0.5])
    pictures = made(tmp_path, "b", melody(5), COLORMAPS[0], image_type=image_type, beat=beat)
    table = lookup_table(COLORMAPS[0])
    assert [at(p, STRONG) for p in pictures] == [colour(table, int(np.rint((0.5 + 0.5 * b) * 255))) for b in beat]


@pytest.mark.parametrize("image_type", TYPES)
def test_without_a_beat_the_frames_are_what_they_were(tmp_path, image_type):
    made(tmp_path, "plain", melody(), COLORMAPS[0], image_type=image_type)
    made(tmp_path, "none", melody(), COLORMAPS[0], image_type=image_type, beat=None)
    assert raw_files(tmp_path, "plain") == raw_files(tmp_path, "none")
    picture = made(tmp_path, "plain2", melody(), COLORMAPS[0], image_type=image_type)[0]
    table = lookup_table(COLORMAPS[0])
    assert at(picture, STRONG) == colour(table, 255)  # 100 % harmonic: the strongest tile is the last colour
    assert at(picture, WEAK) == colour(table, round(0.5 * 255))


@pytest.mark.parametrize("image_type", TYPES)
def test_two_runs_give_identical_files(tmp_path, image_type):
    beat = np.array([0.1, 0.9, 0.4])
    made(tmp_path, "one", melody(), COLORMAPS[0], image_type=image_type, beat=beat)
    made(tmp_path, "two", melody(), COLORMAPS[0], image_type=image_type, beat=beat)
    assert raw_files(tmp_path, "one") == raw_files(tmp_path, "two")


@pytest.mark.parametrize("image_type", OTHER_TYPES)
def test_the_other_image_types_ignore_the_beat(tmp_path, image_type):
    options = {"image_type": image_type}
    made(tmp_path, "without", melody(), COLORMAPS[0], **options)
    made(tmp_path, "with", melody(), COLORMAPS[0], beat=np.array([1.0, 0.0, 0.5]), **options)
    assert raw_files(tmp_path, "without") == raw_files(tmp_path, "with")
    assert len(raw_files(tmp_path, "with")) == 3


@pytest.mark.parametrize("beat_value", [0.0, 1.0])
@pytest.mark.parametrize("colormap", COLORMAPS)
def test_tiles_hidden_by_the_threshold_are_drawn_as_before(tmp_path, colormap, beat_value):
    beat = np.array([beat_value])
    table = lookup_table(colormap)
    values = melody(1)
    values[0, WEAK] = 0.05  # 5 % of the strongest: under the threshold of 10 %
    flat = made(tmp_path, "flat", values, colormap, image_type="tiles", threshold=10, beat=beat)[0]
    blended = made(tmp_path, "blended", values, colormap, image_type="blended", threshold=10, beat=beat)[0]
    assert at(flat, WEAK) == (0, 0, 0)  # the weak tile is under the threshold, so hidden: black for tiles
    assert at(blended, WEAK) == colour(table, 128)  # and the background for blended tiles
    assert at(flat, STRONG) == colour(table, int(np.rint((0.5 + 0.5 * beat_value) * 255)))
    assert at(blended, STRONG) == colour(table, int(np.rint((0.5 + 0.5 * beat_value) * 255)))
    for note in (0, 5, 83):  # silent tiles are hidden too
        assert at(flat, note) == (0, 0, 0)


def test_a_visible_tile_with_no_energy_is_half_the_position(tmp_path):
    table = lookup_table(COLORMAPS[0])
    pictures = made(tmp_path, "silent-tile", melody(2), COLORMAPS[0], image_type="tiles", beat=np.array([0.0, 1.0]))
    assert at(pictures[0], 0) == colour(table, 0)
    assert at(pictures[1], 0) == colour(table, 128)  # rint(127.5)


@pytest.mark.parametrize("image_type", TYPES)
def test_a_finer_grid_uses_the_one_position_of_the_frame(tmp_path, image_type):
    name = DECODABLE[0]  # a colormap whose rows can all be told apart
    table = lookup_table(name)
    rows = {tuple(int(v) for v in c): i for i, c in enumerate(table)}
    low = made(tmp_path, "low", melody(1), name, image_type=image_type, resolution=3, beat=np.array([0.0]))[0]
    high = made(tmp_path, "high", melody(1), name, image_type=image_type, resolution=3, beat=np.array([1.0]))[0]
    rows_of = lambda p: {rows[tuple(int(v) for v in c)] for c in p.reshape(-1, 3) if tuple(int(v) for v in c) in rows}  # noqa: E731
    assert max(rows_of(low)) <= 128  # a position of 0: nothing past the middle of the colormap
    assert min(rows_of(high)) >= 127 and max(rows_of(high)) >= 240  # a position of 1: every tile at least half way
    assert not np.array_equal(low, high)


def test_the_frames_between_the_drawn_ones_are_made_from_their_neighbours(tmp_path):
    table = lookup_table(COLORMAPS[0])
    pictures = made(tmp_path, "interp", melody(3), COLORMAPS[0], image_type="tiles", interpolate=2, beat=np.array([0.0, 0.5, 1.0]))
    assert len(pictures) == 3
    assert at(pictures[0], STRONG) == colour(table, 128)
    assert at(pictures[2], STRONG) == colour(table, 255)
    between = pictures[1][tile_center(STRONG)]
    assert not (between == pictures[0][tile_center(STRONG)]).all() and not (between == pictures[2][tile_center(STRONG)]).all()


def test_gaussian_smoothing_applies_to_the_finished_picture(tmp_path):
    sharp = made(tmp_path, "sharp", melody(1), COLORMAPS[0], image_type="tiles", beat=np.array([1.0]))[0]
    soft = made(tmp_path, "soft", melody(1), COLORMAPS[0], image_type="tiles", gaussian=3, beat=np.array([1.0]))[0]
    assert sharp.shape == soft.shape == (HEIGHT, WIDTH, 3)
    assert not np.array_equal(sharp, soft)


def test_smoothing_of_the_notes_leaves_the_beat_as_it_is(tmp_path):
    values = melody(3)
    values[1, :] = 0  # a silent middle frame that the note smoothing fills from the frame before
    beat = np.array([0.0, 1.0, 0.25])
    smoothed = rendering.smooth_frames(values, 0.5, 2)
    share = np.sqrt(np.minimum(smoothed[:, STRONG] / smoothed.max(), 1.0))
    table = lookup_table(COLORMAPS[0])
    pictures = made(tmp_path, "smooth", values, COLORMAPS[0], image_type="tiles", smoothing=0.5, smoothing_window=2, beat=beat)
    assert 0 < share[1] < 1
    for picture, s, b in zip(pictures, share, beat):
        assert at(picture, STRONG) == colour(table, int(np.rint((0.5 * s + 0.5 * b) * 255)))


@pytest.mark.parametrize("image_type", TYPES + OTHER_TYPES)
@pytest.mark.parametrize(
    "beat",
    [np.zeros(2), np.zeros(4), np.zeros((3, 1)), np.array([0.0, np.nan, 0.0]), np.array([0.0, np.inf, 0.0]), np.array([0.0, 1.2, 0.0]),
     np.array([0.0, -0.1, 0.0]), np.array(["a", "b", "c"]), 0.5, "abc", [0.5, 0.5]],
)
def test_a_beat_that_is_not_one_number_from_0_to_1_for_each_frame_is_refused_before_anything_is_written(tmp_path, image_type, beat):
    directory = tmp_path / "refused"
    with pytest.raises(ValueError) as error:
        rendering.write_frames(melody(3), directory, colormap=COLORMAPS[0], image_type=image_type, beat=beat)
    assert str(error.value) == MESSAGE.format(3)
    assert not directory.exists() or not list(directory.iterdir())
