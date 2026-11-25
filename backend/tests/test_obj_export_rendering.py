"""Feature 045: ``write_frames(..., export_obj=True)`` for the contour and the wireframe."""

import importlib.util
import time
from pathlib import Path

import numpy as np
import pytest

from app.services.chromatic_decay import circle_points as chromatic_points
from app.services.chromatic_wireframe import write_wireframe_frames
from app.services.contour import write_contour_frames
from app.services.colormaps import DEFAULT_COLORMAP
from app.services.frame_rendering import SHOWN_NOTES, hidden_below, write_frames
from app.services.note_selection import spread_notes
from app.services.obj_export import OBJ_FOLDER, amplitude_share, write_contour_obj, write_wireframe_obj

_READER = Path(__file__).resolve().parents[2] / "specs" / "045-obj-export-mode" / "tools" / "read_obj.py"
_spec = importlib.util.spec_from_file_location("read_obj", _READER)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
read_obj = _module.read_obj


def stream(frames: int = 5, seed: int = 11) -> np.ndarray:
    """Note values (frames, 88) that change from frame to frame."""
    values = np.random.default_rng(seed).random((frames, 88)) ** 3
    values[0, 20] = 1.0
    return values


def obj_files(directory: Path) -> list[Path]:
    return sorted((directory / OBJ_FOLDER).glob("*.obj"))


def pictures(directory: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(directory.glob("frame_*.png"))}


def texts(directory: Path) -> list[str]:
    return [p.read_text(encoding="ascii") for p in obj_files(directory)]


def z_of(text: str) -> np.ndarray:
    vertices, _, _ = read_obj(text)
    return np.array(vertices)[:, 2]


# ---- the contour --------------------------------------------------------------------------------------------------------------------------


def test_the_contour_export_writes_one_file_per_frame_in_the_obj_folder_and_the_pictures_are_the_same_with_it_on_and_off(tmp_path):
    values = stream(4)
    beat = np.linspace(0, 1, 4)
    write_frames(values, tmp_path / "on", image_type="contour", beat=beat, export_obj=True)
    write_frames(values, tmp_path / "off", image_type="contour", beat=beat)
    assert [p.name for p in obj_files(tmp_path / "on")] == [f"frame_{i:06d}.obj" for i in range(4)]
    assert pictures(tmp_path / "on") == pictures(tmp_path / "off") and len(pictures(tmp_path / "on")) == 4  # byte for byte
    for text in texts(tmp_path / "on"):
        vertices, faces, _ = read_obj(text)
        assert len(vertices) == 84 and len(faces) == 66


def test_without_the_export_there_is_no_obj_folder(tmp_path):
    write_frames(stream(2), tmp_path, image_type="contour")
    write_frames(stream(2), tmp_path / "b", image_type="contour", export_obj=False)
    assert not (tmp_path / OBJ_FOLDER).exists() and not (tmp_path / "b" / OBJ_FOLDER).exists()


def test_the_resolution_makes_the_picture_finer_but_the_export_stays_12_by_7(tmp_path):
    values = stream(2)
    write_frames(values, tmp_path / "r1", image_type="contour", export_obj=True)
    write_frames(values, tmp_path / "r3", image_type="contour", resolution=3, export_obj=True)
    assert texts(tmp_path / "r1") == texts(tmp_path / "r3")
    assert pictures(tmp_path / "r1") != pictures(tmp_path / "r3")  # the pictures did change with the resolution


def test_gaussian_and_interpolate_change_the_pictures_only_and_every_frame_has_a_file(tmp_path):
    values = stream(7)
    write_frames(values, tmp_path / "plain", image_type="contour", export_obj=True)
    write_frames(values, tmp_path / "other", image_type="contour", gaussian=2.0, interpolate=3, export_obj=True)
    assert len(obj_files(tmp_path / "other")) == 7
    assert texts(tmp_path / "plain") == texts(tmp_path / "other")


def test_the_threshold_and_the_number_of_notes_are_applied_to_the_values(tmp_path):
    values = stream(3)
    write_frames(values, tmp_path / "plain", image_type="contour", export_obj=True)
    write_frames(values, tmp_path / "threshold", image_type="contour", threshold=10, export_obj=True)
    write_frames(values, tmp_path / "notes", image_type="contour", note_count=24, export_obj=True)
    assert texts(tmp_path / "plain") != texts(tmp_path / "threshold")
    assert texts(tmp_path / "plain") != texts(tmp_path / "notes")
    # the threshold hides a note by making it 0, then the grid is smoothed: it is what the picture draws
    peak = float(values.max())
    expected = spread_notes(values[:, :SHOWN_NOTES], 84)
    expected[hidden_below(expected, peak, 10)] = 0
    write_contour_obj(expected, peak, DEFAULT_COLORMAP, tmp_path / "direct")
    assert texts(tmp_path / "threshold") == [p.read_text(encoding="ascii") for p in sorted((tmp_path / "direct").glob("*.obj"))]


def test_the_heights_use_the_peak_of_the_whole_file_not_of_each_frame(tmp_path):
    values = np.zeros((2, 88))
    values[0, 30] = 1.0
    values[1, 30] = 0.25  # a quarter of the loudest value of the file
    write_frames(values, tmp_path, image_type="contour", export_obj=True)
    first, second = (z_of(t).max() for t in texts(tmp_path))
    # the picture's smoothing averages a lone note with its neighbours, so it does not reach 12; a quarter as loud is a quarter as high
    assert 0 < first <= 12.0 and second == pytest.approx(0.25 * first, rel=1e-3)


def test_the_export_follows_the_colormap_of_the_job(tmp_path):
    values = stream(2)
    write_frames(values, tmp_path / "a", image_type="contour", colormap="viridis", export_obj=True)
    write_frames(values, tmp_path / "b", image_type="contour", colormap="hot", export_obj=True)
    assert texts(tmp_path / "a") != texts(tmp_path / "b")


def test_the_beat_wave_of_the_job_is_in_the_export(tmp_path):
    values = stream(3)
    beat = np.array([0.0, 0.5, 1.0])
    write_frames(values, tmp_path / "plain", image_type="contour", export_obj=True)
    write_frames(values, tmp_path / "wave", image_type="contour", beat=beat, wave_count=3, export_obj=True)
    plain, wave = texts(tmp_path / "plain"), texts(tmp_path / "wave")
    assert plain[0] == wave[0] and plain[1] != wave[1]


# ---- the wireframe ------------------------------------------------------------------------------------------------------------------------


def test_the_wireframe_export_writes_one_file_per_frame_and_the_pictures_are_the_same_with_it_on_and_off(tmp_path):
    values = stream(14)
    beat = np.linspace(0, 1, 14)
    write_frames(values, tmp_path / "on", image_type="chromatic-wireframe", beat=beat, export_obj=True)
    write_frames(values, tmp_path / "off", image_type="chromatic-wireframe", beat=beat)
    assert [p.name for p in obj_files(tmp_path / "on")] == [f"frame_{i:06d}.obj" for i in range(14)]
    assert pictures(tmp_path / "on") == pictures(tmp_path / "off") and len(pictures(tmp_path / "on")) == 14
    assert not (tmp_path / "off" / OBJ_FOLDER).exists()
    sizes = [(len(read_obj(t)[0]), len(read_obj(t)[1])) for t in texts(tmp_path / "on")]
    assert sizes[0] == (12, 0) and sizes[5] == (72, 55) and sizes[11] == (144, 121) and sizes[13] == (144, 121)


def test_the_points_of_the_files_are_those_of_chromatic_decay(tmp_path):
    values = stream(6)
    beat = np.linspace(0, 1, 6)
    write_frames(values, tmp_path, image_type="chromatic-wireframe", beat=beat, decay_rate=3, threshold=2, extra_notes=1, export_obj=True)
    points = chromatic_points(values, beat, 3, 2, 1)
    for i, text in enumerate(texts(tmp_path)):
        vertices = np.array(read_obj(text)[0])
        np.testing.assert_allclose(vertices[:12, 2], 12 * amplitude_share(points[i]), atol=6e-5)  # line 0 is the frame itself
        if i:
            np.testing.assert_allclose(vertices[12:24, 2], 12 * amplitude_share(points[i - 1]), atol=6e-5)


def test_the_decay_rate_and_the_extra_notes_change_the_wireframe_files(tmp_path):
    values = stream(8)
    write_frames(values, tmp_path / "base", image_type="chromatic-wireframe", decay_rate=1, extra_notes=2, export_obj=True)
    write_frames(values, tmp_path / "rate", image_type="chromatic-wireframe", decay_rate=6, extra_notes=2, export_obj=True)
    write_frames(values, tmp_path / "extra", image_type="chromatic-wireframe", decay_rate=1, extra_notes=5, export_obj=True)
    base = texts(tmp_path / "base")
    for other in ("rate", "extra"):
        assert texts(tmp_path / other) != base, other


def test_the_threshold_changes_the_wireframe_files(tmp_path):
    values = np.zeros((6, 88))
    values[:, 20] = 1.0  # the loudest note of the file
    values[:, 21:25] = 0.05  # four faint ones: under 10 percent of it
    write_frames(values, tmp_path / "base", image_type="chromatic-wireframe", export_obj=True)
    write_frames(values, tmp_path / "threshold", image_type="chromatic-wireframe", threshold=10, export_obj=True)
    assert texts(tmp_path / "base") != texts(tmp_path / "threshold")


def test_the_wireframe_files_do_not_depend_on_the_picture_settings_that_it_ignores(tmp_path):
    values = stream(4)
    write_frames(values, tmp_path / "a", image_type="chromatic-wireframe", export_obj=True)
    write_frames(values, tmp_path / "b", image_type="chromatic-wireframe", resolution=3, note_count=24, interpolate=2, gaussian=1.0, wave_count=7, export_obj=True)
    assert texts(tmp_path / "a") == texts(tmp_path / "b")


# ---- the other pictures and bad values ----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", ["decay", "decay-exp", "polar-chords", "chromatic-decay", "polychord", "energy-graphs", "rhythm-circles"])
def test_the_export_is_refused_for_the_other_pictures_before_anything_is_written(tmp_path, image_type):
    with pytest.raises(ValueError, match="only available for Contour and Chromatic Wireframe"):
        write_frames(stream(2), tmp_path / "out", image_type=image_type, export_obj=True)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("bad", ["yes", 1, 0, None, 1.0])
def test_the_export_switch_must_be_a_bool(tmp_path, bad):
    with pytest.raises(ValueError, match="true or false"):
        write_frames(stream(2), tmp_path / "out", image_type="contour", export_obj=bad)
    assert not (tmp_path / "out").exists()


def test_the_export_off_is_accepted_for_every_picture(tmp_path):
    write_frames(stream(2), tmp_path / "a", image_type="decay", export_obj=False)
    assert not (tmp_path / "a" / OBJ_FOLDER).exists()


# ---- the time (SC-009) --------------------------------------------------------------------------------------------------------------------


def _seconds(work) -> float:
    start = time.perf_counter()
    work()
    return time.perf_counter() - start


def test_the_export_adds_less_than_half_to_the_time_of_the_pictures(tmp_path):
    """Contour and wireframe: writing the OBJ files of 300 frames takes under half the time of writing their (small) PNG files."""
    frames = 300
    rng = np.random.default_rng(3)
    grid = rng.random((frames, 84)) ** 2
    grid[0, 0] = 1.0
    beat = rng.random(frames)
    points = rng.random((frames, 12)) * 64
    contour_png = _seconds(lambda: write_contour_frames(grid, 1.0, "viridis", tmp_path / "c_png", 12, 7, 120, 80, beat=beat))
    if contour_png > 60:
        pytest.skip("this machine is too slow for a fair comparison")
    contour_obj = _seconds(lambda: write_contour_obj(grid, 1.0, "viridis", tmp_path / "c_obj", beat))
    wire_png = _seconds(lambda: write_wireframe_frames(points, "viridis", tmp_path / "w_png", 240, 160, beat=beat))
    wire_obj = _seconds(lambda: write_wireframe_obj(points, "viridis", tmp_path / "w_obj", beat))
    assert contour_obj < 0.5 * contour_png, (contour_obj, contour_png)
    assert wire_obj < 0.5 * wire_png, (wire_obj, wire_png)
