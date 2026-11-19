"""``write_frames`` for the ``polychord`` image type (feature 042): smoothing, the required data, the ignored arguments."""

import numpy as np
import pytest

import app.services.frame_rendering as rendering
from app.services import polychord as pc
from app.services.colormaps import DEFAULT_COLORMAP

FRAMES = 4


def values(seed: int = 5) -> np.ndarray:
    return np.random.default_rng(seed).random((FRAMES, 88)) ** 2


def data(frames: int = FRAMES, tempo: float = 110.0) -> pc.PolychordData:
    return pc.PolychordData(np.full(frames, tempo), 10.0)


def pngs(directory):
    return [(directory / f"frame_{i:06d}.png").read_bytes() for i in range(FRAMES)]


def test_write_frames_draws_polychord_from_the_frames_as_they_are(tmp_path):
    notes = values()
    beat = np.array([0.0, 0.6, 1.0, 0.8])
    settings = pc.PolychordSettings(7, 2, 9, 40.0)
    rendering.write_frames(notes, tmp_path / "job", colormap=DEFAULT_COLORMAP, image_type="polychord", beat=beat, polychord=data(), polychord_settings=settings)
    pc.write_polychord_frames(notes, beat, data().tempos, settings, 10.0, DEFAULT_COLORMAP, tmp_path / "direct", rendering.IMAGE_WIDTH, rendering.IMAGE_HEIGHT)
    assert pngs(tmp_path / "job") == pngs(tmp_path / "direct")


def test_the_defaults_are_the_default_settings_and_no_beat_means_the_minimum_number_of_copies(tmp_path):
    notes = values()
    rendering.write_frames(notes, tmp_path / "job", colormap=DEFAULT_COLORMAP, image_type="polychord", polychord=data())
    pc.write_polychord_frames(notes, None, data().tempos, pc.DEFAULT_POLYCHORD_SETTINGS, 10.0, DEFAULT_COLORMAP, tmp_path / "direct", rendering.IMAGE_WIDTH, rendering.IMAGE_HEIGHT)
    assert pngs(tmp_path / "job") == pngs(tmp_path / "direct")


def test_polychord_needs_its_data(tmp_path):
    with pytest.raises(ValueError, match="Polychord needs"):
        rendering.write_frames(values(), tmp_path / "job", colormap=DEFAULT_COLORMAP, image_type="polychord")
    assert not (tmp_path / "job").exists()


@pytest.mark.parametrize("frames", [FRAMES - 1, FRAMES + 1, 0])
def test_the_tempos_must_be_one_for_each_frame(tmp_path, frames):
    with pytest.raises(ValueError):
        rendering.write_frames(values(), tmp_path / "job", colormap=DEFAULT_COLORMAP, image_type="polychord", polychord=data(frames))
    assert not (tmp_path / "job").exists()


@pytest.mark.parametrize("settings", [pc.PolychordSettings(9, 3, 12, 15.0), pc.PolychordSettings(6, 9, 8, 15.0), pc.PolychordSettings(6, 3, 12, 400.0), "settings", 6])
def test_settings_that_are_not_valid_are_refused_before_anything_is_written(tmp_path, settings):
    with pytest.raises(ValueError):
        rendering.write_frames(values(), tmp_path / "job", colormap=DEFAULT_COLORMAP, image_type="polychord", polychord=data(), polychord_settings=settings)
    assert not (tmp_path / "job").exists()


@pytest.mark.parametrize("image_type", ["contour", "decay", "decay-exp", "polar-chords", "chromatic-decay", "chromatic-wireframe"])
def test_the_other_types_ignore_the_polychord_arguments(tmp_path, image_type):
    notes = values()
    beat = np.array([0.0, 0.6, 1.0, 0.8])
    rendering.write_frames(notes, tmp_path / "plain", colormap=DEFAULT_COLORMAP, image_type=image_type, beat=beat)
    rendering.write_frames(notes, tmp_path / "with", colormap=DEFAULT_COLORMAP, image_type=image_type, beat=beat, polychord=data(), polychord_settings=pc.PolychordSettings(8, 2, 5, -90.0))
    assert pngs(tmp_path / "plain") == pngs(tmp_path / "with")
