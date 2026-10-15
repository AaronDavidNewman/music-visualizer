"""The size of the frames (feature 021): every frame of every image type is 600 x 400 and is drawn at that size.

The old size, 252 x 168, is rendered here too (by patching the two size constants for the length of a test), so that what must
be equal can be compared: the colors of the tiles, and the contour and blended pictures after reducing the new ones.
"""

import io
import math

import numpy as np
import pytest
from PIL import Image

import app.services.circles as circles
import app.services.frame_rendering as rendering
from app.services.colormaps import COLORMAPS
from app.services.image_types import tile_edges

from .frame_size import HEIGHT, REFERENCE_HEIGHT, REFERENCE_WIDTH, SCALE, WIDTH
from .test_jobs_api import SR, chord_wav, client, wav_bytes  # noqa: F401
from .test_resolution_api import frame_bytes

GRID = (rendering.GRID_COLUMNS, rendering.GRID_ROWS)


def use_size(monkeypatch, width, height):
    """Make the app draw frames of ``width`` x ``height`` for the length of the test (the constants and what is built from them)."""
    monkeypatch.setattr(rendering, "IMAGE_WIDTH", width)
    monkeypatch.setattr(rendering, "IMAGE_HEIGHT", height)
    monkeypatch.setattr(rendering, "_TILE_INDEX_BYTES", rendering._tile_index(*GRID).astype(np.uint8).tobytes())


def music(frames=4, seed=6):
    """(frames, 88) note values: a mix of loud and quiet notes, no two neighbours alike."""
    return np.random.default_rng(seed).random((frames, 88)) ** 2


def write(tmp_path, label, **options):
    directory = tmp_path / label
    rendering.write_frames(music(), directory, colormap=COLORMAPS[0], **options)
    return sorted(directory.glob("frame_*.png"))


CONFIGS = [
    ("tiles", {"image_type": "tiles"}),
    ("tiles res 3", {"image_type": "tiles", "resolution": 3}),
    ("tiles res 5", {"image_type": "tiles", "resolution": 5}),
    ("blended", {"image_type": "blended"}),
    ("blended res 5", {"image_type": "blended", "resolution": 5}),
    ("contour", {"image_type": "contour"}),
    ("contour res 5", {"image_type": "contour", "resolution": 5}),
    ("circles", {"image_type": "circles"}),
]
IDS = [c[0] for c in CONFIGS]


# --- the size itself -------------------------------------------------------------------------------------------------------------


def test_the_frame_is_600_by_400_and_the_reference_frame_is_the_old_252_by_168():
    assert (rendering.IMAGE_WIDTH, rendering.IMAGE_HEIGHT) == (600, 400)
    assert (REFERENCE_WIDTH, REFERENCE_HEIGHT) == (252, 168)
    assert (WIDTH, HEIGHT) == (600, 400)
    assert rendering.IMAGE_WIDTH * 2 == rendering.IMAGE_HEIGHT * 3  # 3:2
    assert rendering.IMAGE_WIDTH * rendering.REFERENCE_HEIGHT == rendering.IMAGE_HEIGHT * rendering.REFERENCE_WIDTH
    assert (rendering.REFERENCE_WIDTH, rendering.REFERENCE_HEIGHT) == (252, 168)
    assert rendering.FRAME_SCALE == pytest.approx(600 / 252) == pytest.approx(SCALE)
    assert circles.REFERENCE_WIDTH == 252


def test_the_tile_constants_of_the_old_whole_pixel_tiles_are_gone():
    assert not hasattr(rendering, "TILE_WIDTH") and not hasattr(rendering, "TILE_HEIGHT")


@pytest.mark.parametrize("config", CONFIGS, ids=IDS)
@pytest.mark.parametrize("interpolate", [1, 3, 5])
def test_every_frame_of_every_image_type_resolution_and_interpolate_is_600_by_400(tmp_path, config, interpolate):
    _, options = config
    files = write(tmp_path, "new", interpolate=interpolate, **options)
    assert [f.name for f in files] == [f"frame_{i:06d}.png" for i in range(4)]
    for f in files:
        assert Image.open(f).size == (600, 400), f.name


@pytest.mark.parametrize("config", CONFIGS, ids=IDS)
def test_the_number_names_and_picture_mode_of_the_frames_are_those_of_the_old_size(tmp_path, monkeypatch, config):
    _, options = config
    with monkeypatch.context() as old:
        use_size(old, 252, 168)
        before = write(tmp_path, "old", **options)
    after = write(tmp_path, "new", **options)
    assert [f.name for f in before] == [f.name for f in after]
    assert [Image.open(f).mode for f in before] == [Image.open(f).mode for f in after]
    assert Image.open(before[0]).size == (252, 168)


# --- the tiles --------------------------------------------------------------------------------------------------------------------


def color_changes(line):
    """The positions along a line of an RGB picture where the color changes."""
    return set((np.flatnonzero((line[1:] != line[:-1]).any(axis=1)) + 1).tolist())


@pytest.mark.parametrize("resolution", [1, 2, 3, 4, 5])
def test_the_tile_columns_and_rows_are_the_same_size_to_within_one_pixel(tmp_path, resolution):
    columns, rows = GRID[0] * resolution, GRID[1] * resolution
    file = write(tmp_path, "tiles", image_type="tiles", resolution=resolution)[0]
    picture = np.asarray(Image.open(file).convert("RGB"))
    for line, count, size in ((picture[HEIGHT // 2], columns, WIDTH), (picture[:, WIDTH // 2], rows, HEIGHT)):
        even_split = np.rint(np.linspace(0, size, count + 1)).astype(int)  # the nearest whole pixels to an even split
        sizes = np.diff(even_split)
        assert sizes.max() - sizes.min() <= 1
        changes = color_changes(line)
        assert changes <= set(even_split.tolist())  # a color only changes at a tile edge
        assert len(changes) >= 0.9 * (count - 1)  # and (two neighbors may share a color) nearly every tile edge is one


def test_the_default_grid_has_columns_of_50_pixels_and_rows_of_57_or_58():
    assert np.diff(tile_edges(12, 600)).tolist() == [50] * 12
    assert sorted(set(np.diff(tile_edges(7, 400)).tolist())) == [57, 58]
    assert np.diff(tile_edges(7, 400)).sum() == 400


def tile_colors(file, columns, rows):
    """The color at the center of every tile of a written frame: (rows, columns, 3)."""
    picture = np.asarray(Image.open(file).convert("RGB"))
    width, height = picture.shape[1], picture.shape[0]
    xs = (tile_edges(columns, width)[:-1] + tile_edges(columns, width)[1:]) // 2
    ys = (tile_edges(rows, height)[:-1] + tile_edges(rows, height)[1:]) // 2
    return picture[np.ix_(ys, xs)]


@pytest.mark.parametrize("resolution", [1, 2, 3, 4, 5])
def test_the_colors_of_the_tiles_are_exactly_the_colors_of_the_old_size(tmp_path, monkeypatch, resolution):
    columns, rows = GRID[0] * resolution, GRID[1] * resolution
    with monkeypatch.context() as old:
        use_size(old, 252, 168)
        before = write(tmp_path, "old", image_type="tiles", resolution=resolution, threshold=3)
    after = write(tmp_path, "new", image_type="tiles", resolution=resolution, threshold=3)
    for a, b in zip(before, after):
        assert (tile_colors(a, columns, rows) == tile_colors(b, columns, rows)).all()


# --- the soft pictures: the same picture, drawn finer ----------------------------------------------------------------------------


def reduced_difference(old_file, new_file):
    """The mean absolute difference per channel between the old frame and the new frame reduced to the old size."""
    old = np.asarray(Image.open(old_file).convert("RGB")).astype(int)
    new = Image.open(new_file).convert("RGB").resize((252, 168), Image.BOX)
    return np.abs(old - np.asarray(new).astype(int)).mean()


@pytest.mark.parametrize("config", [c for c in CONFIGS if c[0].startswith(("blended", "contour"))], ids=lambda c: c[0])
def test_a_contour_or_blended_frame_reduced_to_the_old_size_is_close_to_the_old_frame(tmp_path, monkeypatch, config):
    _, options = config
    with monkeypatch.context() as old:
        use_size(old, 252, 168)
        before = write(tmp_path, "old", **options)
    after = write(tmp_path, "new", **options)
    for a, b in zip(before, after):
        assert reduced_difference(a, b) < 4.0, (a.name, reduced_difference(a, b))  # the same shapes and colors, finer edges


def test_the_blended_feather_is_the_same_share_of_a_tile_at_the_new_size():
    from app.services.image_types import make_grid_blender

    colors = np.zeros((84, 3), dtype=np.uint8)
    colors[26] = 255  # one bright tile among dark ones: (row 2, column 2)
    for width, height in ((252, 168), (600, 400)):
        picture = make_grid_blender(25, 12, 7, width, height)(colors).astype(int)
        y = (tile_edges(7, height)[2] + tile_edges(7, height)[3]) // 2
        left = int(tile_edges(12, width)[2])
        row = picture[y, :, 0]
        tile = width / 12
        reach = 0.25 * tile
        fade = np.flatnonzero((row[left - int(reach) - 3 : left + int(reach) + 4] > 0) & (row[left - int(reach) - 3 : left + int(reach) + 4] < 255))
        assert fade.size > 0 and fade.size <= 2 * math.ceil(reach) + 2  # the fade lies within the reach on each side of the edge
        assert row[left - int(reach) - 2] == 0 and row[left + int(reach) + 2] == 255  # and is gone beyond it


# --- the interpolated frames -------------------------------------------------------------------------------------------------------


def test_the_in_between_frames_are_blends_of_the_drawn_ones_and_have_the_new_size(tmp_path):
    files = write(tmp_path, "new", image_type="blended", interpolate=3)
    assert len(files) == 4
    first, middle, last = (np.asarray(Image.open(f).convert("RGB")).astype(int) for f in (files[0], files[1], files[3]))
    assert first.shape == middle.shape == last.shape == (400, 600, 3)
    lo, hi = np.minimum(first, last), np.maximum(first, last)
    assert ((middle >= lo - 1) & (middle <= hi + 1)).all()  # frame 1 lies between the drawn frames 0 and 3


# --- through the API ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", ["tiles", "blended", "contour", "circles"])
@pytest.mark.parametrize("extra", [{}, {"resolution": "5", "interpolate": "5"}], ids=["defaults", "res5 interpolate5"])
def test_the_frames_the_server_gives_are_600_by_400_for_every_image_type(client, image_type, extra):
    data = chord_wav(2)
    response = client.post(
        "/api/jobs",
        files={"file": ("song.wav", data, "audio/wav")},
        data={"window_size": "4096", "frame_rate": "5", "image_type": image_type, "colormap": COLORMAPS[0], **extra},
    )
    assert response.status_code == 200, response.text
    job = response.json()
    for i in range(job["frame_count"]):
        image = Image.open(io.BytesIO(frame_bytes(client, job, i)))
        assert image.format == "PNG" and image.size == (600, 400), (image_type, i)
