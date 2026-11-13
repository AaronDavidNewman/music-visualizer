"""``write_frames(..., resolution=r)``: the pictures made from the interpolated grid, for every image type.

No colormap is named and no number of contour levels is assumed (see ``colormap_names.py``). The expected pictures are
worked out here independently: the interpolation with ``np.interp`` itself, the tile edges with ``np.rint(np.linspace())``,
the colors from the colormap's table.
"""

import numpy as np
import pytest
from PIL import Image

from app.services.colormaps import COLORMAPS, lookup_table
from app.services.frame_rendering import SHOWN_NOTES, write_frames

from .contour_expected import smoothed_flat
from .frame_size import HEIGHT, WIDTH
from .colormap_names import INVALID
from .test_resolution import MESSAGE as RESOLUTION_MESSAGE
from .test_resolution import with_np_interp

RESOLUTIONS = [1, 2, 3, 4, 5]
TYPES = ["contour"]


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


# --- Tiles ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", TYPES)
def test_resolution_one_gives_exactly_the_files_made_without_the_setting(tmp_path, image_type):
    frames = random_notes(4, seed=3)
    options = dict(smoothing=0.3, smoothing_window=2, threshold=3, image_type=image_type)
    a = write(frames, tmp_path / "a", **options)
    b = write(frames, tmp_path / "b", resolution=1, **options)
    assert [f.read_bytes() for f in a] == [f.read_bytes() for f in b]


# --- Blended tiles ---------------------------------------------------------------------------------------------------------


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
