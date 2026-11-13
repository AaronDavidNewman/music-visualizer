"""The size of the frames (feature 021): every frame of every image type is 600 x 400 and is drawn at that size.

The old size, 252 x 168, is rendered here too (by patching the two size constants for the length of a test), so that what must
be equal can be compared: the contour picture after reducing the new one.
"""

import io

import numpy as np
import pytest
from PIL import Image

import app.services.frame_rendering as rendering
from app.services.colormaps import COLORMAPS

from .frame_size import HEIGHT, WIDTH
from .test_jobs_api import SR, chord_wav, client, wav_bytes  # noqa: F401
from .test_resolution_api import frame_bytes


def use_size(monkeypatch, width, height):
    """Make the app draw frames of ``width`` x ``height`` for the length of the test (the constants and what is built from them)."""
    monkeypatch.setattr(rendering, "IMAGE_WIDTH", width)
    monkeypatch.setattr(rendering, "IMAGE_HEIGHT", height)


def music(frames=4, seed=6):
    """(frames, 88) note values: a mix of loud and quiet notes, no two neighbours alike."""
    return np.random.default_rng(seed).random((frames, 88)) ** 2


def write(tmp_path, label, **options):
    directory = tmp_path / label
    rendering.write_frames(music(), directory, colormap=COLORMAPS[0], **options)
    return sorted(directory.glob("frame_*.png"))


CONFIGS = [
    ("contour", {"image_type": "contour"}),
    ("contour res 5", {"image_type": "contour", "resolution": 5}),
    ("decay", {"image_type": "decay"}),
    ("decay-exp", {"image_type": "decay-exp"}),
    ("polar-chords", {"image_type": "polar-chords"}),
    ("chromatic-decay", {"image_type": "chromatic-decay"}),
    ("chromatic-wireframe", {"image_type": "chromatic-wireframe"}),
]
IDS = [c[0] for c in CONFIGS]


# --- the size itself -------------------------------------------------------------------------------------------------------------


def test_the_frame_is_600_by_400():
    assert (rendering.IMAGE_WIDTH, rendering.IMAGE_HEIGHT) == (600, 400)
    assert (WIDTH, HEIGHT) == (600, 400)
    assert rendering.IMAGE_WIDTH * 2 == rendering.IMAGE_HEIGHT * 3  # 3:2


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


# --- the contour: the same picture, drawn finer ----------------------------------------------------------------------------------


def reduced_difference(old_file, new_file):
    """The mean absolute difference per channel between the old frame and the new frame reduced to the old size."""
    old = np.asarray(Image.open(old_file).convert("RGB")).astype(int)
    new = Image.open(new_file).convert("RGB").resize((252, 168), Image.BOX)
    return np.abs(old - np.asarray(new).astype(int)).mean()


@pytest.mark.parametrize("config", [c for c in CONFIGS if c[0].startswith("contour")], ids=lambda c: c[0])
def test_a_contour_frame_reduced_to_the_old_size_is_close_to_the_old_frame(tmp_path, monkeypatch, config):
    _, options = config
    with monkeypatch.context() as old:
        use_size(old, 252, 168)
        before = write(tmp_path, "old", **options)
    after = write(tmp_path, "new", **options)
    for a, b in zip(before, after):
        assert reduced_difference(a, b) < 4.0, (a.name, reduced_difference(a, b))  # the same shapes and colors, finer edges


# --- the interpolated frames -------------------------------------------------------------------------------------------------------


def test_the_in_between_frames_are_blends_of_the_drawn_ones_and_have_the_new_size(tmp_path):
    files = write(tmp_path, "new", image_type="contour", interpolate=3)
    assert len(files) == 4
    first, middle, last = (np.asarray(Image.open(f).convert("RGB")).astype(int) for f in (files[0], files[1], files[3]))
    assert first.shape == middle.shape == last.shape == (400, 600, 3)
    lo, hi = np.minimum(first, last), np.maximum(first, last)
    assert ((middle >= lo - 1) & (middle <= hi + 1)).all()  # frame 1 lies between the drawn frames 0 and 3


# --- through the API ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", ["contour", "decay", "chromatic-decay"])
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
