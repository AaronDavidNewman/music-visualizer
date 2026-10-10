"""Brightness from energy: the frame's energy, relative to the loudest frame, sets the brightness of the whole frame.

A tile's saturation is its own gray level, so louder sounds brighten the whole picture and each tile's colour
depth stays local to it.
"""

import colorsys

import numpy as np
import pytest
from PIL import Image

from app.services.frame_rendering import (
    DEFAULT_ENERGY,
    DEFAULT_VALUE,
    MAX_ENERGY,
    MIN_ENERGY,
    SHOWN_NOTES,
    boost_levels,
    render_frame,
    smooth_frames,
    tile_colors,
    to_gray_levels,
    value_sequence,
    write_frames,
)

LIT = to_gray_levels(np.linspace(0.3, 1.0, 88)[None, :])[0]


def hsv_of(pixel):
    r, g, b = (int(c) / 255 for c in pixel)
    return colorsys.rgb_to_hsv(r, g, b)


def tile_pixel(img, n):
    """The colour at the middle of tile ``n`` of an RGB image array."""
    return img[(n // 12) * 24 + 12, (n % 12) * 21 + 10]


def frame_pixels(directory, i):
    return np.asarray(Image.open(directory / f"frame_{i:06d}.png").convert("RGB"))


def brightness_of(directory, count, n=40):
    """The brightest channel of tile ``n`` in each frame: the frame's brightness, 0 to 255."""
    return [int(tile_pixel(frame_pixels(directory, i), n).max()) for i in range(count)]


# --- the constants ---------------------------------------------------------------------------------------------------


def test_energy_constants():
    assert (MIN_ENERGY, MAX_ENERGY, DEFAULT_ENERGY) == (1, 8, 1)
    assert DEFAULT_VALUE == 1.0


# --- energy -> brightness of the frame -------------------------------------------------------------------------------


def test_brightness_is_the_energy_as_a_fraction_of_the_loudest():
    values = value_sequence(np.array([0.5, 0.125, 0.0, 0.25]))
    assert values.tolist() == pytest.approx([1.0, 0.25, 0.0, 0.5])
    assert values[0] == 1.0  # the loudest frame is exactly 100%


@pytest.mark.parametrize("root", range(1, 9))
def test_brightness_root_of_a_quarter(root):
    values = value_sequence(np.array([4.0, 1.0, 0.0]), root)
    assert values[0] == 1.0
    assert values[1] == pytest.approx(0.25 ** (1 / root))
    assert values[2] == 0.0


def test_a_higher_root_is_never_darker():
    energies = np.random.default_rng(5).random(50) ** 3
    previous = value_sequence(energies, 1)
    for root in range(2, 9):
        current = value_sequence(energies, root)
        assert (current >= previous - 1e-12).all()
        previous = current


def test_brightness_stays_within_zero_and_one():
    energies = np.random.default_rng(6).random(200) * 1000
    for root in (1, 3, 8):
        for smoothing in (0.0, 0.5, 0.8):
            values = value_sequence(energies, root, smoothing)
            assert values.shape == (200,)
            assert values.min() >= 0.0 and values.max() <= 1.0


def test_silent_energies_give_zero_brightness_without_error():
    assert value_sequence(np.zeros(5), 3, 0.5).tolist() == [0.0] * 5
    assert value_sequence(np.zeros(0)).shape == (0,)


def test_brightness_is_smoothed_like_the_notes_and_hues():
    energies = np.array([1.0, 0.0, 0.0, 0.5])
    mapped = value_sequence(energies, 2, 0.0)
    assert mapped.tolist() == pytest.approx([1.0, 0.0, 0.0, 0.5**0.5])
    smoothed = value_sequence(energies, 2, 0.5)
    assert smoothed == pytest.approx(smooth_frames(mapped.reshape(-1, 1), 0.5).ravel())
    assert smoothed[:3].tolist() == pytest.approx([1.0, 0.5 / 1.5, 0.0])  # the default window is 1
    wider = value_sequence(energies, 2, 0.5, 2)
    assert wider == pytest.approx(smooth_frames(mapped.reshape(-1, 1), 0.5, 2).ravel())
    assert wider[:3].tolist() == pytest.approx([1.0, 0.5 / 1.5, 0.5 / 2])


@pytest.mark.parametrize("root", [0, 9, 2.5, -1, True, "2", None, float("nan")])
def test_a_root_that_is_not_a_whole_number_from_1_to_8_is_refused(root):
    with pytest.raises(ValueError, match="whole number from 1 to 8"):
        value_sequence(np.array([1.0, 0.5]), root)


def test_numpy_integers_and_whole_floats_are_accepted_as_the_root():
    assert value_sequence(np.array([4.0, 1.0]), np.int64(2))[1] == pytest.approx(0.5)
    assert value_sequence(np.array([4.0, 1.0]), 2.0)[1] == pytest.approx(0.5)


def test_energies_must_be_one_dimensional_and_not_negative():
    with pytest.raises(ValueError):
        value_sequence(np.ones((2, 2)))
    with pytest.raises(ValueError):
        value_sequence(np.array([1.0, -0.5]))
    with pytest.raises(ValueError):
        value_sequence(np.array([1.0, np.nan]))


# --- drawing with a brightness ---------------------------------------------------------------------------------------


def test_every_tile_of_a_frame_has_the_frames_brightness_as_its_brightest_channel():
    for value in (0.0, 0.25, 0.5, 1.0):
        colours = tile_colors(LIT, 2, value=value)
        assert (colours.max(axis=1) == round(value * 255)).all(), value


def test_a_tile_with_no_level_is_a_plain_gray_at_the_frames_brightness():
    levels = np.zeros(88, dtype=np.uint8)
    levels[10] = 255
    colours = tile_colors(levels, 2, value=0.5)
    for n in range(SHOWN_NOTES):
        if n != 10:
            assert colours[n].tolist() == [128, 128, 128], n  # no saturation: gray, at half brightness
    assert colours[10].min() == 0 and colours[10].max() == 128  # a full level is fully saturated


def test_a_dark_frame_is_black_whatever_the_levels():
    assert not tile_colors(LIT, 2, value=0.0).any()


def test_only_the_brightness_changes_with_the_brightness():
    low = tile_colors(LIT, 2, value=0.5)
    high = tile_colors(LIT, 2, value=1.0)
    checked = 0
    for n in range(SHOWN_NOTES):
        h1, s1, v1 = hsv_of(low[n])
        h2, s2, v2 = hsv_of(high[n])
        assert v1 == pytest.approx(0.5, abs=1 / 255) and v2 == 1.0
        assert s1 == pytest.approx(s2, abs=0.02), n  # the saturation (the tile's level) is the same
        if s1 > 0.3:  # enough saturation for the hue to survive rounding to 8 bits
            assert min(abs(h1 - h2), 1 - abs(h1 - h2)) < 0.02, n
            checked += 1
    assert checked > 20


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf"), True, "0.5", None])
def test_tile_colors_refuses_a_brightness_outside_zero_to_one(value):
    with pytest.raises(ValueError, match="brightness"):
        tile_colors(LIT, 2, value=value)


def test_render_frame_takes_a_brightness_and_defaults_to_full():
    img = np.asarray(render_frame(LIT, 2, value=0.5))
    assert (img.max(axis=2) == 128).all()
    assert np.array_equal(np.asarray(render_frame(LIT, 2)), np.asarray(render_frame(LIT, 2, value=DEFAULT_VALUE)))
    assert (np.asarray(render_frame(LIT, 2)).max(axis=2) == 255).all()


# --- through write_frames --------------------------------------------------------------------------------------------


def test_write_frames_uses_each_frames_energy_as_its_brightness(tmp_path):
    write_frames(np.ones((3, 88)), tmp_path, brightness=2, energies=np.array([1.0, 0.25, 0.0]))
    assert brightness_of(tmp_path, 3) == [255, 64, 0]


def test_write_frames_applies_the_energy_root(tmp_path):
    write_frames(np.ones((3, 88)), tmp_path, energies=np.array([4.0, 1.0, 0.0]), energy_root=2)
    assert brightness_of(tmp_path, 3) == [255, 128, 0]


def test_every_tile_of_a_frame_shares_the_frames_brightness(tmp_path):
    values = np.random.default_rng(21).random((2, 88)) * 0.7 + 0.3
    values[:, ::3] = 0.0  # some notes are silent: their tiles are gray, but just as bright
    write_frames(values, tmp_path, energies=np.array([2.0, 1.0]))
    for i, expected in enumerate((255, 128)):
        img = frame_pixels(tmp_path, i)
        assert all(int(tile_pixel(img, n).max()) == expected for n in range(SHOWN_NOTES)), i


def test_a_quiet_notes_tile_is_less_saturated_and_a_loud_notes_tile_more(tmp_path):
    values = np.zeros((1, 88))
    values[0, 40], values[0, 41] = 1.0, 0.04  # note 41 is a twenty-fifth of note 40
    write_frames(values, tmp_path, brightness=2, energies=np.array([1.0]))
    img = frame_pixels(tmp_path, 0)
    s40 = hsv_of(tile_pixel(img, 40))[1]
    s41 = hsv_of(tile_pixel(img, 41))[1]
    assert s40 == pytest.approx(1.0, abs=0.01)
    assert s41 == pytest.approx(boost_levels(to_gray_levels(values)[0], 2)[41] / 255, abs=0.02)
    assert hsv_of(tile_pixel(img, 60))[1] == 0.0  # a silent note: no saturation


def test_write_frames_smooths_the_brightness_with_the_same_smoothing(tmp_path):
    write_frames(np.ones((3, 88)), tmp_path, smoothing=0.5, energies=np.array([1.0, 0.0, 0.0]))
    assert brightness_of(tmp_path, 3) == [255, 85, 0]  # window 1: 1, 1/3, 0
    write_frames(
        np.ones((3, 88)), tmp_path / "w2", smoothing=0.5, smoothing_window=2, energies=np.array([1.0, 0.0, 0.0])
    )
    assert brightness_of(tmp_path / "w2", 3) == [255, 85, 64]  # window 2: 1, 1/3, 1/4


def test_write_frames_without_energies_is_at_full_brightness(tmp_path):
    write_frames(np.ones((2, 88)), tmp_path)
    assert brightness_of(tmp_path, 2) == [255, 255]


def test_write_frames_with_silent_energies_is_all_black(tmp_path):
    write_frames(np.ones((2, 88)), tmp_path, energies=np.zeros(2))
    for i in range(2):
        assert not frame_pixels(tmp_path, i).any()


def test_write_frames_wants_one_energy_per_frame_and_a_valid_root(tmp_path):
    with pytest.raises(ValueError, match="energies"):
        write_frames(np.ones((3, 88)), tmp_path, energies=np.array([1.0, 0.5]))
    with pytest.raises(ValueError, match="whole number from 1 to 8"):
        write_frames(np.ones((2, 88)), tmp_path, energies=np.ones(2), energy_root=9)


def test_changing_only_the_energy_root_changes_no_saturation(tmp_path):
    values = np.random.default_rng(22).random((3, 88))
    energies = np.array([1.0, 0.5, 0.25])
    a, b = tmp_path / "a", tmp_path / "b"
    write_frames(values, a, energies=energies, energy_root=1)
    write_frames(values, b, energies=energies, energy_root=8)
    for i in range(3):
        ia, ib = frame_pixels(a, i), frame_pixels(b, i)
        for n in range(SHOWN_NOTES):
            sa, sb = hsv_of(tile_pixel(ia, n))[1], hsv_of(tile_pixel(ib, n))[1]
            assert sa == pytest.approx(sb, abs=0.03), (i, n)  # the tile's own level is the same
    assert brightness_of(a, 3) != brightness_of(b, 3)  # but the frames' brightness differs


def test_the_same_input_gives_identical_files(tmp_path):
    values = np.random.default_rng(23).random((3, 88))
    energies = np.array([0.7, 0.2, 0.0])
    a, b = tmp_path / "a", tmp_path / "b"
    write_frames(values, a, energies=energies, energy_root=3, smoothing=0.3)
    write_frames(values, b, energies=energies, energy_root=3, smoothing=0.3)
    for i in range(3):
        assert (a / f"frame_{i:06d}.png").read_bytes() == (b / f"frame_{i:06d}.png").read_bytes()
