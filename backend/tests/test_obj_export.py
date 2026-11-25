"""Feature 045: the 3D export of the contour and the wireframe (``app.services.obj_export``)."""

import importlib.util
import locale
import zipfile
from pathlib import Path

import numpy as np
import pytest

from app.services.beat_wave import wave_modifier
from app.services.chromatic_decay import circle_radii, ring_geometry
from app.services.chromatic_wireframe import line_colors
from app.services.colormaps import COLORMAP_STEPS, lookup_table
from app.services.contour import smoothed_grid
from app.services.obj_export import (
    HEIGHT,
    LINES_PER_FILE,
    OBJ_EXPORT_TYPES,
    amplitude_share,
    contour_mesh,
    format_obj,
    wireframe_mesh,
    write_contour_obj,
    write_wireframe_obj,
    zip_obj_files,
)

# the independent reader, written from the data model and not from the writer
_READER = Path(__file__).resolve().parents[2] / "specs" / "045-obj-export-mode" / "tools" / "read_obj.py"
_spec = importlib.util.spec_from_file_location("read_obj", _READER)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
read_obj = _module.read_obj


def read_file(path: Path):
    """The vertices (an array ``(points, 6)``), the faces (``(faces, 4)``) and the names of one OBJ file."""
    vertices, faces, names = read_obj(path.read_text(encoding="ascii"))
    return np.array(vertices), np.array(faces, dtype=int).reshape(-1, 4), names


def area(vertices: np.ndarray, face: np.ndarray) -> float:
    """The signed area of a face seen from +Z (positive: counterclockwise), by the shoelace formula."""
    x, y = vertices[face - 1, 0], vertices[face - 1, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def check_faces(vertices: np.ndarray, faces: np.ndarray) -> None:
    """Every face is one cell of the grid (a unit square in X and Y) in counterclockwise order."""
    for face in faces:
        assert area(vertices, face) == pytest.approx(1.0), face
        corners = vertices[face - 1, :2]
        assert set(map(tuple, corners)) == {(corners[:, 0].min(), corners[:, 1].min()), (corners[:, 0].max(), corners[:, 1].min()), (corners[:, 0].max(), corners[:, 1].max()), (corners[:, 0].min(), corners[:, 1].max())}


# ---- format_obj ---------------------------------------------------------------------------------------------------------------------------


def small_mesh():
    vertices = np.array([[0, 0, 0, 1, 0, 0], [1, 0, 2.5, 0, 1, 0], [1, 1, 0.12341, 0, 0, 1], [0, 1, 12, 0.5, 0.5, 0.5]], dtype=float)
    return vertices, np.array([[1, 2, 3, 4]])


def test_format_obj_writes_the_header_the_points_with_four_decimals_and_the_faces():
    vertices, faces = small_mesh()
    assert format_obj(vertices, faces, "a mesh", "frame_000007") == (
        "# Music Visualizer 3D export\n"
        "# a mesh\n"
        "o frame_000007\n"
        "v 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000\n"
        "v 1.0000 0.0000 2.5000 0.0000 1.0000 0.0000\n"
        "v 1.0000 1.0000 0.1234 0.0000 0.0000 1.0000\n"
        "v 0.0000 1.0000 12.0000 0.5000 0.5000 0.5000\n"
        "f 1 2 3 4\n"
    )


def test_format_obj_has_no_negative_zero_and_no_exponent():
    vertices = np.array([[-0.0, -0.00001, 1e-9, 1e9, -1e-7, 0.25]])
    text = format_obj(vertices, np.zeros((0, 4), dtype=int), "c", "n")
    line = text.split("\n")[3]
    assert line == "v 0.0000 0.0000 0.0000 1000000000.0000 0.0000 0.2500"
    assert "e" not in line and "-" not in line


def test_format_obj_uses_unix_line_ends_and_ends_with_one():
    text = format_obj(*small_mesh(), "c", "n")
    assert "\r" not in text and text.endswith("\n") and not text.endswith("\n\n")


def test_format_obj_gives_the_same_text_twice_and_does_not_depend_on_the_locale():
    vertices, faces = small_mesh()
    first = format_obj(vertices, faces, "c", "n")
    old = locale.setlocale(locale.LC_ALL)
    try:
        for name in ("de_DE.UTF-8", "German_Germany.1252", "fr_FR.UTF-8"):
            try:
                locale.setlocale(locale.LC_ALL, name)
                break
            except locale.Error:
                continue
        assert format_obj(vertices, faces, "c", "n") == first
    finally:
        locale.setlocale(locale.LC_ALL, old)
    assert "," not in first


def test_format_obj_is_read_by_the_independent_reader():
    vertices, faces = small_mesh()
    read_vertices, read_faces, names = read_obj(format_obj(vertices, faces, "c", "frame_000000"))
    assert len(read_vertices) == 4 and read_faces == [(1, 2, 3, 4)] and names == ["frame_000000"]


def test_the_reader_refuses_what_is_not_the_format():
    for bad in ("v 1 2 3\n", "v 1.0000 2.0000 3.0000 0.0000 0.0000 0.0000 0.0000\n", "f 1 2 3 4\n", "x 1\n", "v 1e3 0.0000 0.0000 0.0000 0.0000 0.0000\n", "v 0,5000 0.0000 0.0000 0.0000 0.0000 0.0000\n"):
        with pytest.raises(ValueError):
            read_obj(bad)


# ---- zip_obj_files ------------------------------------------------------------------------------------------------------------------------


def test_the_zip_holds_the_files_in_frame_order_under_their_own_names(tmp_path):
    folder = tmp_path / "obj"
    folder.mkdir()
    for index in (2, 0, 10, 1):
        (folder / f"frame_{index:06d}.obj").write_bytes(f"frame {index}\n".encode())
    (folder / "notes.txt").write_text("not an obj")
    archive = tmp_path / "out" / "obj.zip"
    zip_obj_files(folder, archive)
    with zipfile.ZipFile(archive) as pack:
        assert pack.namelist() == ["frame_000000.obj", "frame_000001.obj", "frame_000002.obj", "frame_000010.obj"]
        assert pack.read("frame_000010.obj") == b"frame 10\n"
        assert {info.date_time for info in pack.infolist()} == {(2020, 1, 1, 0, 0, 0)}
        assert all(info.compress_type == zipfile.ZIP_DEFLATED for info in pack.infolist())
    assert not list((tmp_path / "out").glob("*.tmp"))


def test_two_zips_of_the_same_files_are_identical(tmp_path):
    folder = tmp_path / "obj"
    folder.mkdir()
    for index in range(3):
        (folder / f"frame_{index:06d}.obj").write_bytes((f"frame {index}\n" * 50).encode())
    zip_obj_files(folder, tmp_path / "a.zip")
    zip_obj_files(folder, tmp_path / "b.zip")
    assert (tmp_path / "a.zip").read_bytes() == (tmp_path / "b.zip").read_bytes()


def test_a_folder_without_obj_files_cannot_be_packed(tmp_path):
    with pytest.raises(FileNotFoundError):
        zip_obj_files(tmp_path / "missing", tmp_path / "a.zip")
    (tmp_path / "empty").mkdir()
    with pytest.raises(FileNotFoundError):
        zip_obj_files(tmp_path / "empty", tmp_path / "a.zip")
    assert not (tmp_path / "a.zip").exists()


def test_the_export_is_for_the_contour_and_the_wireframe_only():
    assert OBJ_EXPORT_TYPES == ("contour", "chromatic-wireframe")


# ---- the contour mesh ---------------------------------------------------------------------------------------------------------------------


def ramp(peak: float = 2.0) -> np.ndarray:
    """A (7, 12) grid that rises from 0 to ``peak`` over its 84 cells."""
    return np.arange(84, dtype=float).reshape(7, 12) / 83 * peak


def test_a_contour_mesh_has_84_points_and_66_faces_with_the_point_of_each_cell_at_its_place():
    vertices, faces = contour_mesh(ramp(), 2.0, 2.0, "viridis")
    assert vertices.shape == (84, 6) and faces.shape == (66, 4)
    for row in range(7):
        for col in range(12):
            x, y, z = vertices[12 * row + col, :3]
            assert (x, y) == (col, row)
    assert vertices[0, 2] == 0 and vertices[83, 2] == pytest.approx(HEIGHT)


def test_the_height_is_12_for_the_peak_and_proportional_below_it_and_never_above_12():
    grid = ramp(1.0)
    vertices, _ = contour_mesh(grid, 2.0, 1.0, "viridis")  # the whole file is twice as loud as this frame
    np.testing.assert_allclose(vertices[:, 2], 12 * grid.reshape(-1) / 2.0)
    over, _ = contour_mesh(ramp(3.0), 2.0, 3.0, "viridis")  # (cannot happen in a job) held to 12
    assert over[:, 2].max() == 12.0


def test_a_peak_of_zero_gives_a_flat_mesh_in_the_first_color():
    vertices, faces = contour_mesh(np.zeros((7, 12)), 0.0, 0.0, "viridis")
    assert (vertices[:, 2] == 0).all()
    np.testing.assert_allclose(vertices[:, 3:], np.tile(lookup_table("viridis")[0] / 255.0, (84, 1)))
    assert len(faces) == 66


def test_the_color_of_a_point_is_the_colormap_at_its_value_on_the_scale():
    grid = ramp(1.0)
    vertices, _ = contour_mesh(grid, 5.0, 1.0, "hot")
    table = lookup_table("hot")
    np.testing.assert_allclose(vertices[0, 3:], table[0] / 255.0)  # 0 is the first color
    np.testing.assert_allclose(vertices[83, 3:], table[COLORMAP_STEPS - 1] / 255.0)  # the largest value of the frame is the last
    middle = vertices[12 * 3 + 5, 3:]  # cell 41 of 83
    np.testing.assert_allclose(middle, table[round(255 * 41 / 83)] / 255.0)
    assert vertices[:, 3:].min() >= 0 and vertices[:, 3:].max() <= 1


def test_every_contour_face_is_one_cell_in_counterclockwise_order():
    vertices, faces = contour_mesh(ramp(), 2.0, 2.0, "viridis")
    assert faces.min() == 1 and faces.max() == 84
    check_faces(vertices, faces)
    assert faces[0].tolist() == [1, 2, 14, 13] and faces[-1].tolist() == [71, 72, 84, 83]


def test_a_grid_of_the_wrong_shape_is_refused():
    with pytest.raises(ValueError):
        contour_mesh(np.zeros((12, 7)), 1.0, 1.0, "viridis")


# ---- write_contour_obj --------------------------------------------------------------------------------------------------------------------


def values_of(frames: int = 6, seed: int = 5) -> np.ndarray:
    values = np.random.default_rng(seed).random((frames, 84)) ** 2
    values[0, 3] = 1.0  # the peak
    return values


def test_one_contour_file_per_frame_named_like_the_pictures(tmp_path):
    values = values_of(6)
    write_contour_obj(values, float(values.max()), "viridis", tmp_path)
    assert [p.name for p in sorted(tmp_path.glob("*.obj"))] == [f"frame_{i:06d}.obj" for i in range(6)]


def test_every_contour_file_has_84_points_66_faces_and_stays_in_its_ranges(tmp_path):
    values = values_of(5)
    write_contour_obj(values, float(values.max()), "viridis", tmp_path)
    for path in sorted(tmp_path.glob("*.obj")):
        vertices, faces, names = read_file(path)
        assert vertices.shape == (84, 6) and faces.shape == (66, 4) and names == [path.stem]
        assert 0 <= vertices[:, 0].min() and vertices[:, 0].max() == 11
        assert 0 <= vertices[:, 1].min() and vertices[:, 1].max() == 6
        assert 0 <= vertices[:, 2].min() and vertices[:, 2].max() <= 12
        assert 0 <= vertices[:, 3:].min() and vertices[:, 3:].max() <= 1
        check_faces(vertices, faces)


def test_the_heights_are_the_picture_s_smoothed_grid_scaled_by_the_peak_of_the_file(tmp_path):
    values = values_of(3)
    peak = float(values.max()) * 1.5  # the file is louder than these frames
    write_contour_obj(values, peak, "viridis", tmp_path)
    for i in range(3):
        vertices, _, _ = read_file(tmp_path / f"frame_{i:06d}.obj")
        expected = 12 * smoothed_grid(values[i], 7, 12) / peak
        np.testing.assert_allclose(vertices[:, 2].reshape(7, 12), expected, atol=6e-5)


def test_the_colors_follow_the_scale_of_each_frame(tmp_path):
    values = values_of(3)
    values[1] *= 0.1  # a quiet frame
    write_contour_obj(values, float(values.max()), "viridis", tmp_path)
    table = lookup_table("viridis")
    for i in range(3):
        vertices, _, _ = read_file(tmp_path / f"frame_{i:06d}.obj")
        grid = smoothed_grid(values[i], 7, 12)
        rows = np.rint(255 * np.clip(grid / values[i].max(), 0, 1)).astype(int).reshape(-1)
        np.testing.assert_allclose(vertices[:, 3:], table[rows] / 255.0, atol=6e-5)
    quiet, _, _ = read_file(tmp_path / "frame_000001.obj")
    assert quiet[:, 3:].max(axis=0).tolist() != [0.0, 0.0, 0.0]  # a quiet frame still shows the whole colormap, as the picture does


def test_a_silent_file_is_written_as_flat_meshes_in_the_first_color(tmp_path):
    write_contour_obj(np.zeros((4, 84)), 0.0, "viridis", tmp_path)
    assert len(list(tmp_path.glob("*.obj"))) == 4
    for path in tmp_path.glob("*.obj"):
        vertices, faces, _ = read_file(path)
        assert vertices.shape == (84, 6) and faces.shape == (66, 4) and (vertices[:, 2] == 0).all()
        np.testing.assert_allclose(vertices[:, 3:], np.tile(lookup_table("viridis")[0] / 255.0, (84, 1)), atol=6e-5)


def test_a_frame_of_equal_values_has_the_flat_color_of_the_picture(tmp_path):
    values = np.zeros((2, 84))
    values[0, 5] = 1.0
    values[1] = 0.5  # one flat color in the picture, on the scale of the whole file
    write_contour_obj(values, 1.0, "viridis", tmp_path)
    vertices, _, _ = read_file(tmp_path / "frame_000001.obj")
    np.testing.assert_allclose(vertices[:, 2], 6.0)
    np.testing.assert_allclose(vertices[:, 3:], np.tile(lookup_table("viridis")[round(255 * 0.5)] / 255.0, (84, 1)), atol=6e-5)


def test_the_beat_wave_changes_a_frame_with_a_beat_above_zero_and_leaves_the_others_plain(tmp_path):
    values = values_of(3)
    peak = float(values.max())
    write_contour_obj(values, peak, "viridis", tmp_path / "plain")
    write_contour_obj(values, peak, "viridis", tmp_path / "wave", beat=np.array([0.0, 0.5, 1.0]), waves=4)
    plain0 = (tmp_path / "plain" / "frame_000000.obj").read_text()
    assert (tmp_path / "wave" / "frame_000000.obj").read_text() == plain0  # beat 0: the plain frame, byte for byte
    waved, _, _ = read_file(tmp_path / "wave" / "frame_000001.obj")
    expected = 12 * smoothed_grid(values[1], 7, 12) * wave_modifier(7, 12, 4, 0.5) / peak
    np.testing.assert_allclose(waved[:, 2].reshape(7, 12), expected, atol=6e-5)
    assert (tmp_path / "wave" / "frame_000001.obj").read_text() != (tmp_path / "plain" / "frame_000001.obj").read_text()
    # the colors stay on the scale of the frame before the wave: a point the wave dims is darker
    plain1, _, _ = read_file(tmp_path / "plain" / "frame_000001.obj")
    assert waved[:, 3:].sum() != plain1[:, 3:].sum()


def test_the_same_contour_input_gives_identical_files(tmp_path):
    values = values_of(4)
    beat = np.array([0.0, 0.3, 0.9, 0.1])
    write_contour_obj(values, float(values.max()), "inferno", tmp_path / "a", beat=beat)
    write_contour_obj(values, float(values.max()), "inferno", tmp_path / "b", beat=beat)
    for i in range(4):
        assert (tmp_path / "a" / f"frame_{i:06d}.obj").read_bytes() == (tmp_path / "b" / f"frame_{i:06d}.obj").read_bytes()


def test_the_input_of_write_contour_obj_is_not_changed_and_bad_input_is_refused(tmp_path):
    values = values_of(3)
    before = values.copy()
    write_contour_obj(values, 1.0, "viridis", tmp_path / "a", beat=np.array([0.2, 0.4, 0.6]))
    np.testing.assert_array_equal(values, before)
    with pytest.raises(ValueError):
        write_contour_obj(np.zeros((3, 88)), 1.0, "viridis", tmp_path / "b")
    with pytest.raises(ValueError):
        write_contour_obj(values, 1.0, "nope", tmp_path / "b")
    with pytest.raises(ValueError):
        write_contour_obj(values, 1.0, "viridis", tmp_path / "b", beat=np.array([0.1, 0.2]))
    with pytest.raises(ValueError):
        write_contour_obj(values, 1.0, "viridis", tmp_path / "b", waves=1)
    assert not (tmp_path / "b").exists()


# ---- the wireframe mesh -------------------------------------------------------------------------------------------------------------------


def points_of(frames: int = 14, seed: int = 8) -> np.ndarray:
    return np.random.default_rng(seed).random((frames, 12)) * 64


def test_the_amplitude_is_a_twelfth_at_no_points_and_full_from_24():
    share = amplitude_share(np.array([0.0, 12.0, 24.0, 40.0, 64.0]))
    np.testing.assert_allclose(share, [1 / 12, 1 / 12 + 11 / 12 * 0.5, 1.0, 1.0, 1.0])


def test_the_amplitude_is_the_radius_of_the_circle_of_chromatic_decay_over_the_full_radius():
    points = points_of(4)
    np.testing.assert_allclose(amplitude_share(points), circle_radii(points) / ring_geometry(600, 400)[1])


def test_the_number_of_lines_points_and_faces_of_a_wireframe_file():
    points = points_of(14)
    colors = line_colors(None, "viridis", 14)
    for frame, lines in ((0, 1), (1, 2), (5, 6), (10, 11), (11, 12), (13, 12)):
        vertices, faces = wireframe_mesh(points, colors, frame)
        assert vertices.shape == (12 * lines, 6), frame
        assert faces.shape == (11 * (lines - 1), 4), frame
    vertices, faces = wireframe_mesh(points, colors, 13)
    assert vertices.shape == (144, 6) and faces.shape == (121, 4) and LINES_PER_FILE == 12


def test_line_j_is_the_frame_j_frames_before_at_y_j_and_the_letters_are_along_x():
    points = points_of(14)
    colors = line_colors(None, "viridis", 14)
    vertices, _ = wireframe_mesh(points, colors, 13)
    for j in range(12):
        line = vertices[12 * j : 12 * j + 12]
        assert line[:, 0].tolist() == list(range(12))
        assert (line[:, 1] == j).all()
        np.testing.assert_allclose(line[:, 2], 12 * amplitude_share(points[13 - j]))
    assert vertices[:, 2].min() >= 1.0 - 1e-9 and vertices[:, 2].max() <= 12.0 + 1e-9


def test_the_12_points_of_a_line_have_one_color_the_color_of_their_own_frame():
    points = points_of(14)
    colors = line_colors(np.linspace(0, 1, 14), "viridis", 14)
    vertices, _ = wireframe_mesh(points, colors, 13)
    for j in range(12):
        line = vertices[12 * j : 12 * j + 12, 3:]
        assert (line == line[0]).all()
        np.testing.assert_allclose(line[0], colors[13 - j] / 255.0)
    assert len({tuple(vertices[12 * j, 3:]) for j in range(12)}) > 1  # an earlier line keeps its own color


def test_every_wireframe_face_joins_neighbouring_letters_of_neighbouring_lines_counterclockwise():
    points = points_of(14)
    vertices, faces = wireframe_mesh(points, line_colors(None, "viridis", 14), 13)
    check_faces(vertices, faces)
    assert faces[0].tolist() == [1, 2, 14, 13] and faces[-1].tolist() == [131, 132, 144, 143]
    used = set(faces.reshape(-1).tolist())
    assert used == set(range(1, 145))  # every point is a corner of some face


def test_a_one_line_wireframe_has_points_and_no_faces():
    vertices, faces = wireframe_mesh(points_of(3), line_colors(None, "viridis", 3), 0)
    assert vertices.shape == (12, 6) and faces.shape == (0, 4)


def test_a_frame_outside_the_file_is_refused():
    points = points_of(3)
    colors = line_colors(None, "viridis", 3)
    for frame in (-1, 3):
        with pytest.raises(ValueError):
            wireframe_mesh(points, colors, frame)


# ---- write_wireframe_obj ------------------------------------------------------------------------------------------------------------------


def test_one_wireframe_file_per_frame_that_the_reader_accepts_with_the_ranges_of_the_model(tmp_path):
    points = points_of(14)
    write_wireframe_obj(points, "viridis", tmp_path, beat=np.linspace(0, 1, 14))
    files = sorted(tmp_path.glob("*.obj"))
    assert [p.name for p in files] == [f"frame_{i:06d}.obj" for i in range(14)]
    for i, path in enumerate(files):
        vertices, faces, names = read_file(path)
        lines = min(i + 1, 12)
        assert vertices.shape == (12 * lines, 6) and faces.shape == (11 * (lines - 1), 4) and names == [path.stem]
        assert vertices[:, 0].max() == 11 and vertices[:, 1].max() == lines - 1
        assert 1.0 - 6e-5 <= vertices[:, 2].min() and vertices[:, 2].max() <= 12.0 + 6e-5
        assert 0 <= vertices[:, 3:].min() and vertices[:, 3:].max() <= 1
        check_faces(vertices, faces)


def test_only_the_12_amplitudes_of_each_line_are_written_not_the_sine(tmp_path):
    points = np.tile(np.linspace(0, 23, 12), (2, 1))
    write_wireframe_obj(points, "viridis", tmp_path)
    vertices, _, _ = read_file(tmp_path / "frame_000001.obj")
    first_line = vertices[:12, 2]
    np.testing.assert_allclose(first_line, 12 * amplitude_share(points[1]), atol=6e-5)
    assert len(set(np.round(first_line, 4))) == 12  # 12 distinct heights, nothing sampled in between
    assert len(vertices) == 24  # 2 lines of 12, not hundreds of samples


def test_a_silent_wireframe_is_at_height_1_in_the_first_color(tmp_path):
    write_wireframe_obj(np.zeros((3, 12)), "viridis", tmp_path)
    for path in tmp_path.glob("*.obj"):
        vertices, _, _ = read_file(path)
        np.testing.assert_allclose(vertices[:, 2], 1.0)
        np.testing.assert_allclose(vertices[:, 3:], np.tile(lookup_table("viridis")[0] / 255.0, (len(vertices), 1)), atol=6e-5)


def test_the_beat_gives_the_lines_the_colors_of_the_pictures(tmp_path):
    points = points_of(4)
    beat = np.array([0.0, 0.4, 1.0, 0.7])
    write_wireframe_obj(points, "inferno", tmp_path, beat=beat)
    colors = line_colors(beat, "inferno", 4)
    vertices, _, _ = read_file(tmp_path / "frame_000003.obj")
    for j in range(4):
        np.testing.assert_allclose(vertices[12 * j, 3:], colors[3 - j] / 255.0, atol=6e-5)


def test_the_same_wireframe_input_gives_identical_files_and_is_not_changed(tmp_path):
    points = points_of(5)
    before = points.copy()
    write_wireframe_obj(points, "viridis", tmp_path / "a", beat=np.linspace(0, 1, 5))
    write_wireframe_obj(points, "viridis", tmp_path / "b", beat=np.linspace(0, 1, 5))
    np.testing.assert_array_equal(points, before)
    for i in range(5):
        assert (tmp_path / "a" / f"frame_{i:06d}.obj").read_bytes() == (tmp_path / "b" / f"frame_{i:06d}.obj").read_bytes()


def test_bad_wireframe_input_is_refused_before_anything_is_written(tmp_path):
    with pytest.raises(ValueError):
        write_wireframe_obj(np.zeros((3, 11)), "viridis", tmp_path / "a")
    with pytest.raises(ValueError):
        write_wireframe_obj(np.full((3, 12), 65.0), "viridis", tmp_path / "a")
    with pytest.raises(ValueError):
        write_wireframe_obj(np.zeros((3, 12)), "nope", tmp_path / "a")
    with pytest.raises(ValueError):
        write_wireframe_obj(np.zeros((3, 12)), "viridis", tmp_path / "a", beat=np.array([0.1, 0.2]))
    assert not (tmp_path / "a").exists()
