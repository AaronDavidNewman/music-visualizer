"""The pictures of the ``decay-exp`` kind through ``write_frames`` (feature 030)."""

import numpy as np
import pytest

from app.services import decay_exp
from app.services.decay import write_decay_frames
from app.services.frame_rendering import write_frames

from .frame_size import HEIGHT, WIDTH


def all_frames(directory) -> list[bytes]:
    return [path.read_bytes() for path in sorted(directory.glob("frame_*.png"))]


def stream(frames=20, seed=4) -> np.ndarray:
    return np.random.default_rng(seed).random((frames, 88))


@pytest.mark.parametrize("rate", [0.25, 0.75, 1, 4])
def test_write_frames_draws_the_points_of_decay_exp(tmp_path, rate):
    values = stream(25)
    beat = np.linspace(0, 1, 25)
    write_frames(values, tmp_path / "a", colormap="viridis", image_type="decay-exp", beat=beat, decay_rate=rate)
    write_decay_frames(decay_exp.circle_points(values, beat, "rows", rate), "viridis", tmp_path / "b", WIDTH, HEIGHT)
    assert all_frames(tmp_path / "a") == all_frames(tmp_path / "b") and len(all_frames(tmp_path / "a")) == 25


def test_the_files_are_600_by_400_and_named_from_zero(tmp_path):
    from PIL import Image

    write_frames(stream(3), tmp_path, colormap="viridis", image_type="decay-exp")
    assert [p.name for p in sorted(tmp_path.glob("*.png"))] == [f"frame_{i:06d}.png" for i in range(3)]
    image = Image.open(tmp_path / "frame_000002.png")
    assert image.size == (WIDTH, HEIGHT) and image.mode == "RGB"


def test_decay_exp_frames_differ_from_decay_frames_of_the_same_stream(tmp_path):
    values = stream(10)
    write_frames(values, tmp_path / "exp", colormap="viridis", image_type="decay-exp")
    write_frames(values, tmp_path / "decay", colormap="viridis", image_type="decay")
    assert all_frames(tmp_path / "exp") != all_frames(tmp_path / "decay")


def test_the_spiral_layout_is_used(tmp_path):
    values = stream(10)
    write_frames(values, tmp_path / "rows", colormap="viridis", image_type="decay-exp", note_layout="rows")
    write_frames(values, tmp_path / "spiral", colormap="viridis", image_type="decay-exp", note_layout="spiral")
    write_decay_frames(decay_exp.circle_points(values, None, "spiral", 1), "viridis", tmp_path / "direct", WIDTH, HEIGHT)
    assert all_frames(tmp_path / "spiral") == all_frames(tmp_path / "direct")
    assert all_frames(tmp_path / "rows") != all_frames(tmp_path / "spiral")


def test_the_settings_that_do_not_apply_do_not_change_the_frames(tmp_path):
    values = stream(10)
    write_frames(values, tmp_path / "a", colormap="viridis", image_type="decay-exp")
    write_frames(
        values,
        tmp_path / "b",
        colormap="viridis",
        image_type="decay-exp",
        threshold=0.9,
        note_count=40,
        resolution=3,
        interpolate=2,
        gaussian=2.0,
        decay_amounts=(3.0, 3.0, 0.5, 0.5),
        wave_count=7,
    )
    assert all_frames(tmp_path / "a") == all_frames(tmp_path / "b")


def test_a_bad_decay_rate_or_amount_is_refused_before_anything_is_written(tmp_path):
    with pytest.raises(ValueError, match="decay rate"):
        write_frames(stream(3), tmp_path / "out", colormap="viridis", image_type="decay-exp", decay_rate=5)
    with pytest.raises(ValueError, match="saturation decay"):
        write_frames(stream(3), tmp_path / "out", colormap="viridis", image_type="decay-exp", decay_amounts=(10.0, 1.0, 2.0, 3.0))
    assert not (tmp_path / "out").exists()


def test_the_decay_rate_and_amounts_have_no_effect_on_the_other_types(tmp_path):
    values = stream(6)
    for image_type in ("contour", "polar-chords"):
        write_frames(values, tmp_path / f"{image_type}-a", colormap="viridis", image_type=image_type)
        write_frames(values, tmp_path / f"{image_type}-b", colormap="viridis", image_type=image_type, decay_rate=4, decay_amounts=(3.0, 3.0, 3.0, 3.0))
        assert all_frames(tmp_path / f"{image_type}-a") == all_frames(tmp_path / f"{image_type}-b")


def test_the_decay_amounts_still_change_decay_but_not_decay_exp(tmp_path):
    values = np.repeat(np.zeros((1, 88)), 8, axis=0)
    values[:, 30] = 1.0
    values[:, 31] = 0.9
    values[:, 32] = 0.8
    values[:, 33] = 0.7
    values[:, 34] = 0.6
    values = np.repeat(values, 4, axis=0)
    write_frames(values, tmp_path / "decay-a", colormap="viridis", image_type="decay")
    write_frames(values, tmp_path / "decay-b", colormap="viridis", image_type="decay", decay_amounts=(3.0, 3.0, 3.0, 3.0))
    assert all_frames(tmp_path / "decay-a") != all_frames(tmp_path / "decay-b")


def test_a_silent_stream_makes_frames_of_84_smallest_dots_in_the_first_color(tmp_path):
    from PIL import Image

    from app.services.colormaps import lookup_table
    from app.services.decay import circle_radii
    from app.services.note_grid import tile_edges

    write_frames(np.zeros((3, 88)), tmp_path, colormap="viridis", image_type="decay-exp")
    image = np.array(Image.open(tmp_path / "frame_000001.png").convert("RGB"))
    table = lookup_table("viridis")
    columns, rows = tile_edges(12, WIDTH), tile_edges(7, HEIGHT)
    for cell in (0, 41, 83):
        row, column = divmod(cell, 12)
        x, y = (columns[column] + columns[column + 1]) // 2, (rows[row] + rows[row + 1]) // 2
        assert tuple(image[y, x]) == tuple(table[0])
    assert circle_radii(0.0, WIDTH, HEIGHT) == pytest.approx(25 / 12)
    assert len(set(all_frames(tmp_path))) == 1
