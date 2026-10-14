"""``write_frames(..., interpolate=n)``: only every n-th frame is drawn, the rest are blends made with Pillow.

No colormap is named and no number of contour levels is assumed (see ``colormap_names.py``). Pillow defines the
in-between frames, so the tests apply ``Image.blend`` themselves to the decoded drawn files.
"""

import numpy as np
import pytest
from PIL import Image

from app.services import frame_rendering
from app.services.colormaps import COLORMAPS, lookup_table
from app.services.frame_interpolation import key_frames
from app.services.frame_rendering import write_frames

from .colormap_names import INVALID
from .test_frame_interpolation import INTERPOLATE_MESSAGE
from .test_resolution_rendering import rgb

TYPES = ["tiles", "blended", "contour"]


def random_notes(frames=12, seed=1):
    return np.random.default_rng(seed).random((frames, 88)) ** 2


def name(i):
    return f"frame_{i:06d}.png"


def write(frames, directory, **options):
    write_frames(frames, directory, **options)
    return sorted(directory.glob("frame_*.png"))


def bytes_of(directory, i):
    return (directory / name(i)).read_bytes()


def decoded(directory, i):
    return Image.open(directory / name(i)).convert("RGB")


# --- interpolate 1 and the numbering ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", TYPES)
def test_interpolate_one_gives_exactly_the_files_made_without_the_setting(tmp_path, image_type):
    frames = random_notes(8, seed=3)
    options = dict(smoothing=0.3, smoothing_window=2, threshold=3, resolution=2, note_count=40, image_type=image_type)
    a = write(frames, tmp_path / "a", **options)
    b = write(frames, tmp_path / "b", interpolate=1, **options)
    assert [f.read_bytes() for f in a] == [f.read_bytes() for f in b]


@pytest.mark.parametrize("count", [1, 2, 3, 7, 11, 12])
@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("image_type", TYPES)
def test_the_frame_count_the_names_and_the_size_do_not_depend_on_the_interpolate_value(tmp_path, image_type, n, count):
    files = write(random_notes(count, seed=count), tmp_path, image_type=image_type, interpolate=n)
    assert [f.name for f in files] == [name(i) for i in range(count)]
    assert all(Image.open(f).size == (252, 168) for f in files)


@pytest.mark.parametrize("n", [2, 3, 4, 5])
@pytest.mark.parametrize("image_type", TYPES)
def test_the_drawn_frames_are_byte_identical_to_the_frames_of_interpolate_one(tmp_path, image_type, n):
    frames = random_notes(12, seed=n)
    options = dict(smoothing=0.4, smoothing_window=3, image_type=image_type)  # smoothing: values depend on earlier frames
    full = tmp_path / "full"
    write(frames, full, **options)
    part = tmp_path / "part"
    write(frames, part, interpolate=n, **options)
    for i in key_frames(12, n):
        assert bytes_of(part, i) == bytes_of(full, i), (image_type, n, i)


@pytest.mark.parametrize("name_", COLORMAPS)
def test_the_drawn_frames_follow_every_other_setting_exactly_as_without_interpolation(tmp_path, name_):
    frames = random_notes(11, seed=9)
    options = dict(colormap=name_, smoothing=0.5, smoothing_window=3, threshold=5, resolution=3, note_count=24)
    for image_type in TYPES:
        full, part = tmp_path / f"f_{image_type}", tmp_path / f"p_{image_type}"
        write(frames, full, image_type=image_type, **options)
        write(frames, part, image_type=image_type, interpolate=5, **options)
        for i in key_frames(11, 5):
            assert bytes_of(part, i) == bytes_of(full, i), (name_, image_type, i)


# --- how many pictures are drawn ------------------------------------------------------------------------------------------------


def counting(monkeypatch, target, attribute):
    calls = []
    original = getattr(target, attribute)

    def spy(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(target, attribute, spy)
    return calls


@pytest.mark.parametrize("count", [1, 2, 3, 11, 12, 13, 31])
@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
def test_only_the_drawn_frames_are_drawn_tiles_blended_and_contour(tmp_path, monkeypatch, count, n):
    from matplotlib.axes import Axes

    palette = counting(monkeypatch, frame_rendering, "_palette_frame")
    blended = counting(monkeypatch, frame_rendering, "_save_blended")
    contour = counting(monkeypatch, Axes, "contourf")
    frames = random_notes(count, seed=n + count)
    expected = len(key_frames(count, n))
    multiples = len(range(0, count, n))
    assert expected == multiples + (0 if (count - 1) % n == 0 else 1)  # the formula of FR-009
    for image_type, calls in (("tiles", palette), ("blended", blended), ("contour", contour)):
        write(frames, tmp_path / image_type, image_type=image_type, interpolate=n)
        assert len(calls) == expected, (image_type, n, count)


@pytest.mark.parametrize("n", [2, 5])
def test_only_the_drawn_true_color_tiles_are_drawn_at_a_finer_grid(tmp_path, monkeypatch, n):
    from_array = counting(monkeypatch, Image, "fromarray")
    write(random_notes(12, seed=2), tmp_path, resolution=2, interpolate=n)
    assert len(from_array) == len(key_frames(12, n))


def test_three_hundred_frames_at_five_draw_sixty_one_pictures_the_users_example(tmp_path, monkeypatch):
    palette = counting(monkeypatch, frame_rendering, "_palette_frame")
    write(random_notes(300, seed=5), tmp_path, interpolate=5)
    assert len(palette) == 60 + 1  # frames 1, 6, 11 ... 296 (counted from 1) and the last, 300
    assert key_frames(300, 5)[:3] == [0, 5, 10]


# --- the in-between frames --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("count, n", [(11, 5), (12, 5), (8, 5), (10, 3), (6, 2)])
def test_the_in_between_frames_are_what_pillows_blend_gives_from_the_drawn_frames(tmp_path, image_type, count, n):
    write(random_notes(count, seed=count), tmp_path, image_type=image_type, interpolate=n)
    drawn = key_frames(count, n)
    for a, b in zip(drawn[:-1], drawn[1:]):
        for i in range(a + 1, b):
            want = np.asarray(Image.blend(decoded(tmp_path, a), decoded(tmp_path, b), (i - a) / (b - a)))
            assert np.array_equal(np.asarray(decoded(tmp_path, i)), want), (image_type, i)


def test_each_pixel_is_the_weighted_mix_within_one_level(tmp_path):
    write(random_notes(11, seed=4), tmp_path, interpolate=5)
    for a, b in ((0, 5), (5, 10)):
        earlier, later = np.asarray(decoded(tmp_path, a), float), np.asarray(decoded(tmp_path, b), float)
        for i in range(a + 1, b):
            w = (i - a) / (b - a)  # frame 2 of 5 is four fifths of frame 1 and one fifth of frame 6
            assert np.abs(np.asarray(decoded(tmp_path, i), float) - ((1 - w) * earlier + w * later)).max() <= 1.0 + 1e-9


def test_the_last_gap_is_shorter_and_its_position_is_counted_within_it(tmp_path):
    write(random_notes(8, seed=6), tmp_path, interpolate=5)  # drawn: 0, 5, 7
    assert key_frames(8, 5) == [0, 5, 7]
    earlier, later = np.asarray(decoded(tmp_path, 5), float), np.asarray(decoded(tmp_path, 7), float)
    assert np.abs(np.asarray(decoded(tmp_path, 6), float) - (earlier + later) / 2).max() <= 1.0 + 1e-9  # w = 1/2, not 1/5
    assert len(list(tmp_path.glob("frame_*.png"))) == 8


def test_drawn_frames_keep_their_kind_and_in_between_frames_are_rgb(tmp_path):
    write(random_notes(11, seed=7), tmp_path / "tiles", interpolate=5)
    assert [Image.open(tmp_path / "tiles" / name(i)).mode for i in range(11)] == ["P"] + ["RGB"] * 4 + ["P"] + ["RGB"] * 4 + ["P"]
    write(random_notes(11, seed=7), tmp_path / "contour", image_type="contour", interpolate=5)
    modes = [Image.open(tmp_path / "contour" / name(i)).mode for i in range(11)]
    assert modes[0] == modes[5] == modes[10] == "RGBA" and set(modes[1:5]) == {"RGB"}


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("name_", COLORMAPS)
def test_a_silent_input_gives_flat_frames_in_every_type_and_colormap(tmp_path, image_type, name_):
    first = lookup_table(name_)[0]
    write(np.zeros((7, 88)), tmp_path, colormap=name_, image_type=image_type, interpolate=3)
    for i in range(7):  # drawn and in between: flat first color (the blend of two equal pictures is that picture)
        assert (rgb(tmp_path / name(i)) == first).all(), (image_type, name_, i)


@pytest.mark.parametrize("image_type", TYPES)
def test_two_runs_give_byte_identical_files(tmp_path, image_type):
    frames = random_notes(12, seed=12)
    options = dict(image_type=image_type, interpolate=4, smoothing=0.4, smoothing_window=3, threshold=4)
    a = write(frames, tmp_path / "a", **options)
    b = write(frames, tmp_path / "b", **options)
    assert [f.read_bytes() for f in a] == [f.read_bytes() for f in b]


# --- refusals ------------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("bad", [0, 6, 2.5, None, "3", True])
def test_a_bad_interpolate_value_is_refused_before_anything_is_written(tmp_path, image_type, bad):
    with pytest.raises(ValueError) as error:
        write_frames(random_notes(), tmp_path / "out", image_type=image_type, interpolate=bad)
    assert str(error.value) == INTERPOLATE_MESSAGE
    assert not (tmp_path / "out").exists()


def test_the_interpolation_function_is_no_longer_an_argument(tmp_path):
    with pytest.raises(TypeError):
        write_frames(random_notes(), tmp_path / "out", interpolate=3, interpolate_function="screen")
    assert not (tmp_path / "out").exists()


def test_other_arguments_are_still_checked_with_interpolation(tmp_path):
    for kwargs in ({"colormap": INVALID[0]}, {"threshold": 11}, {"resolution": 6}, {"note_count": 11}):
        with pytest.raises(ValueError):
            write_frames(random_notes(), tmp_path / "out", interpolate=3, **kwargs)
    assert not (tmp_path / "out").exists()


def test_no_frames_and_one_frame_work(tmp_path):
    assert write(np.zeros((0, 88)), tmp_path / "none", interpolate=5) == []
    assert [f.name for f in write(random_notes(1), tmp_path / "one", interpolate=5)] == [name(0)]
