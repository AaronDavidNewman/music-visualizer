"""The contour picture: ``app/services/contour.py`` and the ``contour`` branch of ``write_frames``.

Nothing here states a number of contour levels (matplotlib chooses them) or names a colormap (the list can be changed by
hand; see ``colormap_names.py``). A color is only ever compared with the colormap by *position along the scale* and to
within one band: "the pixel has the color the colormap has somewhere within 0.25 of the expected position".
"""

import subprocess
import sys
import threading
import time
import warnings
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.services.colormaps import COLORMAPS, DEFAULT_COLORMAP, lookup_table
from app.services.frame_rendering import IMAGE_HEIGHT, IMAGE_WIDTH, write_frames

from .frame_size import HEIGHT, WIDTH
from .colormap_names import INVALID

BACKEND = Path(__file__).resolve().parents[1]
BAND = 0.25  # "within one band" along the scale; matplotlib's automatic levels are never wider than this at these sizes


def notes(*frames):
    """(frames, 88) note values; each frame is a dict {note: value}, every other note is 0."""
    out = np.zeros((len(frames), 88))
    for i, values in enumerate(frames):
        for note, value in values.items():
            out[i, note] = value
    return out


def contour(frames, directory, colormap=DEFAULT_COLORMAP, **options):
    write_frames(frames, directory, colormap=colormap, image_type="contour", **options)
    return sorted(directory.glob("frame_*.png"))


def read(path):
    return np.asarray(Image.open(path))


def at_note(picture, note):
    """The pixel at the grid point of a note: columns spread over the width, rows over the height, first row on top."""
    row, col = divmod(note, 12)
    return picture[round(row / 6 * (IMAGE_HEIGHT - 1)), round(col / 11 * (IMAGE_WIDTH - 1))][:3].astype(int)


def near_scale(colour, name, position, tolerance=BAND, slack=3):
    """Whether ``colour`` is a colour the colormap has somewhere within ``tolerance`` of ``position`` along its scale."""
    from matplotlib import colormaps

    samples = colormaps[name](np.linspace(max(position - tolerance, 0), min(position + tolerance, 1), 1001), bytes=True)
    return bool((np.abs(samples[:, :3].astype(int) - np.asarray(colour)[:3]).max(axis=1) <= slack).any())


# --- the picture ----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", COLORMAPS)
def test_every_frame_is_an_opaque_picture_of_exactly_the_image_size_with_one_file_per_frame(tmp_path, name):
    frames = notes({0: 1.0, 30: 0.5}, {40: 0.8, 41: 0.3}, {5: 0.2, 80: 1.0})
    files = contour(frames, tmp_path / "out", name)
    assert [f.name for f in files] == ["frame_000000.png", "frame_000001.png", "frame_000002.png"]
    for f in files:
        image = Image.open(f)
        assert image.size == (IMAGE_WIDTH, IMAGE_HEIGHT) == (WIDTH, HEIGHT)
        assert (read(f)[..., 3] == 255).all()


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_contour_fills_the_whole_picture_with_no_axes_border_or_margin(tmp_path, name):
    # all notes at half the peak but one in the middle: the edges and corners are colours of the middle of the scale
    values = {n: 0.5 for n in range(84)}
    values[40] = 1.0  # in the middle of the grid, so that the edges stay at the middle of the scale
    picture = read(contour(notes(values), tmp_path, name)[0])
    edges = np.concatenate([picture[0], picture[-1], picture[:, 0], picture[:, -1]])
    assert len(edges) == 2 * WIDTH + 2 * HEIGHT
    bad = [tuple(p[:3]) for p in edges if not near_scale(p, name, 0.5, tolerance=0.3)]
    assert not bad, bad[:5]  # none is the white (or black) of a figure background or a drawn border


@pytest.mark.parametrize("name", COLORMAPS)
def test_a_loud_note_makes_its_own_region_at_its_own_place_for_every_corner_of_the_grid(tmp_path, name):
    # one loud note in a corner of the grid (the rest is silent): the contour is centred on that corner of the picture.
    # The "heat" of a pixel is its distance from the colour of a grid point whose value is 0; where the heat is, is where
    # the note is. This does not depend on what the colormap looks like.
    for loud, zero, left, top in ((0, 83, True, True), (11, 72, False, True), (72, 11, True, False), (83, 0, False, False)):
        picture = read(contour(notes({loud: 1.0}), tmp_path / f"n{loud}", name)[0])[..., :3].astype(float)
        heat = np.abs(picture - at_note(picture, zero)).sum(axis=2)
        assert heat.sum() > 0
        ys, xs = np.mgrid[0:IMAGE_HEIGHT, 0:IMAGE_WIDTH]
        centre_x, centre_y = (heat * xs).sum() / heat.sum(), (heat * ys).sum() / heat.sum()
        assert (centre_x < IMAGE_WIDTH / 2) == left, (name, loud, centre_x)
        assert (centre_y < IMAGE_HEIGHT / 2) == top, (name, loud, centre_y)


@pytest.mark.parametrize("name", COLORMAPS)
def test_a_grid_point_has_the_colour_of_its_value_on_the_scale_from_zero_to_the_peak_within_one_band(tmp_path, name):
    picture = read(contour(notes({0: 1.0, 30: 0.5, 60: 0.2}), tmp_path, name)[0])
    for note, expected in ((0, 1.0), (30, 0.5), (60, 0.2), (83, 0.0), (11, 0.0), (72, 0.0)):
        assert near_scale(at_note(picture, note), name, expected), (name, note, at_note(picture, note))


@pytest.mark.parametrize("name", COLORMAPS)
def test_the_color_scale_runs_from_zero_to_the_largest_value_of_each_frame(tmp_path, name):
    # the scale follows the frame being drawn (the committed behaviour of 49bab02: vmax is the frame's own largest value),
    # so the loudest note of every frame is at the end of the scale whatever the file's peak is
    frames = notes({30: 0.5, 5: 0.25}, {30: 0.5, 5: 0.25, 60: 1.0}, {60: 0.25})
    files = contour(frames, tmp_path, name)
    assert near_scale(at_note(read(files[0]), 30), name, 1.0), name  # frame 0: its top is 0.5
    assert near_scale(at_note(read(files[0]), 5), name, 0.5), name
    assert near_scale(at_note(read(files[1]), 60), name, 1.0), name  # frame 1: its top is 1.0
    assert near_scale(at_note(read(files[1]), 30), name, 0.5), name
    assert near_scale(at_note(read(files[1]), 5), name, 0.25), name
    assert near_scale(at_note(read(files[2]), 60), name, 1.0), name  # frame 2: its top is 0.25


def test_a_quieter_file_is_not_brighter_than_a_louder_one_for_the_same_note(tmp_path):
    # the same note and the same strength relative to the file's peak is the same, whatever the units are (scale invariance)
    a = read(contour(notes({10: 1.0, 40: 0.5}), tmp_path / "a")[0])
    b = read(contour(notes({10: 0.001, 40: 0.0005}), tmp_path / "b")[0])
    assert (a == b).all()


def test_the_four_undrawn_notes_count_for_the_peak_but_are_not_in_the_grid(tmp_path):
    # the only loud note is note 85, which is not drawn: every drawn note is far below the peak, a flat first-colour picture
    picture = read(contour(notes({85: 1.0, 10: 0.0}), tmp_path)[0])
    assert (picture[..., :3] == lookup_table(DEFAULT_COLORMAP)[0]).all()
    # a note that is only in the grid counts for the scale of its own frame, whatever the undrawn note is
    picture = read(contour(notes({85: 1.0, 10: 0.1, 20: 0.2}), tmp_path / "b")[0])
    assert near_scale(at_note(picture, 20), DEFAULT_COLORMAP, 1.0)
    assert near_scale(at_note(picture, 10), DEFAULT_COLORMAP, 0.5)


def test_the_coordinates_and_the_color_scale_run_from_zero_to_the_largest_value_of_the_current_frame(
    tmp_path, monkeypatch
):
    from matplotlib.axes import Axes

    seen = []
    original = Axes.contourf

    def spy(self, x, y, z, *args, **kwargs):
        seen.append((np.asarray(x), np.asarray(y), kwargs))
        return original(self, x, y, z, *args, **kwargs)

    monkeypatch.setattr(Axes, "contourf", spy)
    # three frames with three different largest values, each worked out again for its own frame
    contour(notes({10: 0.4, 50: 0.2}, {10: 1.0, 50: 0.2}, {10: 0.25}), tmp_path)
    assert len(seen) == 3
    for (x, y, kwargs), top in zip(seen, (0.4, 1.0, 0.25)):
        assert len(x) == 12 and len(y) == 7  # one X per column and one Y per row
        assert x[0] == y[0] == 0 and x[-1] == y[-1] == pytest.approx(top)
        assert (np.diff(x) > 0).all() and (np.diff(y) > 0).all()
        assert kwargs["vmin"] == 0 and kwargs["vmax"] == pytest.approx(top)  # and so is the colour scale


# --- the other settings -----------------------------------------------------------------------------------------------


def test_a_note_hidden_by_the_threshold_is_drawn_exactly_as_if_its_value_were_0(tmp_path):
    peak, faint = 1.0, 0.05  # 5% of the peak is below a threshold of 10
    hidden = notes({40: peak, 41: faint, 20: 0.5})
    zero = notes({40: peak, 41: 0.0, 20: 0.5})
    a = contour(hidden, tmp_path / "a", threshold=10)
    b = contour(zero, tmp_path / "b")
    c = contour(hidden, tmp_path / "c")  # without the threshold the faint note stays, next to the loud one
    assert a[0].read_bytes() == b[0].read_bytes()
    assert a[0].read_bytes() != c[0].read_bytes()


def test_a_note_at_or_above_the_threshold_is_kept(tmp_path):
    values = notes({40: 1.0, 41: 0.1, 20: 0.5})  # 10% of the peak, exactly at a threshold of 10: shown
    assert contour(values, tmp_path / "a", threshold=10)[0].read_bytes() == contour(values, tmp_path / "b")[0].read_bytes()


def test_smoothing_is_applied_before_the_contour_is_drawn(tmp_path):
    impulse = notes({}, {40: 1.0}, {}, {}, {}, {}, {})
    plain = contour(impulse, tmp_path / "plain")
    smooth = contour(impulse, tmp_path / "smooth", smoothing=0.5, smoothing_window=3)
    flat = lambda f: len({tuple(p) for p in read(f)[..., :3].reshape(-1, 3).tolist()}) == 1  # noqa: E731
    assert flat(plain[2]) and flat(plain[3])  # nothing sounds after the impulse
    assert not flat(smooth[2]) and not flat(smooth[3]) and not flat(smooth[4])  # its trace, for the window
    assert flat(smooth[6])  # and then it is gone


@pytest.mark.parametrize("name", COLORMAPS)
def test_changing_the_colormap_changes_only_the_colours(tmp_path, name):
    other = COLORMAPS[(COLORMAPS.index(name) + 1) % len(COLORMAPS)]
    values = notes({0: 1.0, 30: 0.5, 60: 0.2, 83: 0.7})
    a = read(contour(values, tmp_path / "a", name)[0])
    b = read(contour(values, tmp_path / "b", other)[0])
    if other == name:
        pytest.skip("only one colormap is offered")
    # the bands are where they were: pixels that had the same colour still have the same colour with the other colormap
    a_flat = a[..., :3].reshape(-1, 3)
    b_flat = b[..., :3].reshape(-1, 3)
    pairs = {tuple(x) for x in np.concatenate([a_flat, b_flat], axis=1).tolist()}
    assert len(pairs) == len({tuple(x) for x in a_flat.tolist()})  # one colour of the other map for each colour of this one


# --- frames without a contour ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", COLORMAPS)
def test_a_silent_input_is_flat_in_the_first_colour_and_does_not_warn(tmp_path, name):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        files = contour(np.zeros((4, 88)), tmp_path, name)
    assert len(files) == 4
    for f in files:
        assert (read(f)[..., :3] == lookup_table(name)[0]).all()
        assert Image.open(f).size == (WIDTH, HEIGHT)


@pytest.mark.parametrize("name", COLORMAPS)
def test_a_silent_input_stays_flat_with_a_threshold_and_smoothing(tmp_path, name):
    files = contour(np.zeros((5, 88)), tmp_path, name, threshold=10, smoothing=0.5, smoothing_window=3)
    assert all((read(f)[..., :3] == lookup_table(name)[0]).all() for f in files)


@pytest.mark.parametrize("name", COLORMAPS)
def test_a_quiet_frame_inside_a_file_is_flat_in_the_first_colour_while_its_neighbours_are_not(tmp_path, name):
    files = contour(notes({10: 1.0, 50: 0.4}, {}, {10: 1.0, 50: 0.4}), tmp_path, name)
    assert (read(files[1])[..., :3] == lookup_table(name)[0]).all()
    for f in (files[0], files[2]):
        assert len({tuple(p) for p in read(f)[..., :3].reshape(-1, 3).tolist()}) > 1


@pytest.mark.parametrize("name", COLORMAPS)
def test_a_frame_whose_notes_are_all_hidden_is_flat_in_the_first_colour(tmp_path, name):
    # frame 1 has only a faint note, below 10% of the file's peak (which sounds in frame 0): it is hidden, so nothing is left
    files = contour(notes({10: 1.0, 20: 0.5}, {20: 0.05}), tmp_path, name, threshold=10)
    assert (read(files[1])[..., :3] == lookup_table(name)[0]).all()


@pytest.mark.parametrize("name", COLORMAPS)
def test_a_frame_with_the_same_value_everywhere_is_flat_in_the_colour_of_that_value(tmp_path, name):
    values = {n: 0.5 for n in range(84)}
    files = contour(notes(values, {**values, 3: 1.0}), tmp_path, name)
    picture = read(files[0])
    assert len({tuple(p) for p in picture[..., :3].reshape(-1, 3).tolist()}) == 1
    assert near_scale(picture[5, 5], name, 0.5, tolerance=0.01, slack=3)  # peak is 1.0 (frame 1): half way along the scale


def test_no_frames_writes_nothing_and_does_not_fail(tmp_path):
    assert contour(np.zeros((0, 88)), tmp_path / "none") == []


# --- repetition, the lock, the environment ---------------------------------------------------------------------------------


def test_the_same_input_gives_byte_identical_files_without_any_warning(tmp_path):
    rng = np.random.default_rng(5)
    frames = rng.random((6, 88)) ** 3
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        a = contour(frames, tmp_path / "a", smoothing=0.3, smoothing_window=2)
        b = contour(frames, tmp_path / "b", smoothing=0.3, smoothing_window=2)
    assert [f.read_bytes() for f in a] == [f.read_bytes() for f in b]


def test_two_jobs_drawing_at_once_each_get_exactly_their_own_pictures(tmp_path):
    rng = np.random.default_rng(6)
    first, second = rng.random((40, 88)) ** 3, rng.random((40, 88)) ** 2
    expected = {
        "one": [f.read_bytes() for f in contour(first, tmp_path / "e1", "viridis" if "viridis" in COLORMAPS else COLORMAPS[0])],
        "two": [f.read_bytes() for f in contour(second, tmp_path / "e2", COLORMAPS[-1])],
    }
    errors = []

    def job(key, frames, name):
        try:
            contour(frames, tmp_path / key, name)
        except Exception as error:  # noqa: BLE001 - reported below
            errors.append(error)

    threads = [
        threading.Thread(target=job, args=("one", first, "viridis" if "viridis" in COLORMAPS else COLORMAPS[0])),
        threading.Thread(target=job, args=("two", second, COLORMAPS[-1])),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    for key in ("one", "two"):
        assert [f.read_bytes() for f in sorted((tmp_path / key).glob("*.png"))] == expected[key]


def test_a_job_leaves_no_figure_open_and_uses_the_windowless_backend(tmp_path):
    import matplotlib
    from matplotlib import pyplot

    contour(np.random.default_rng(1).random((5, 88)), tmp_path)
    assert pyplot.get_fignums() == []
    assert matplotlib.get_backend().lower() == "agg"


def test_a_failure_while_drawing_still_closes_the_figure(tmp_path):
    from matplotlib import pyplot

    with pytest.raises(ValueError):
        contour(np.random.default_rng(1).random((3, 88)), tmp_path / "x", colormap=INVALID[0])
    assert pyplot.get_fignums() == []


def test_bad_arguments_are_refused_before_anything_is_written(tmp_path):
    frames = np.random.default_rng(1).random((3, 88))
    for kwargs in ({"colormap": INVALID[0]}, {"threshold": 11}, {"smoothing": 0.9}, {"smoothing_window": 0}):
        with pytest.raises(ValueError):
            write_frames(frames, tmp_path / "out", image_type="contour", **kwargs)
    assert not (tmp_path / "out").exists()


def test_the_blend_width_has_no_effect_on_a_contour(tmp_path):
    frames = np.random.default_rng(2).random((3, 88)) ** 2
    a = contour(frames, tmp_path / "a", blend_width=10)
    b = contour(frames, tmp_path / "b", blend_width=25)
    assert [f.read_bytes() for f in a] == [f.read_bytes() for f in b]


def test_drawing_a_contour_does_not_change_the_tiles_or_blended_pictures_made_afterwards(tmp_path):
    frames = np.random.default_rng(3).random((4, 88)) ** 2
    before = {t: [f.read_bytes() for f in (write_frames(frames, tmp_path / f"b{t}", image_type=t), sorted((tmp_path / f"b{t}").glob("*.png")))[1]] for t in ("tiles", "blended")}
    contour(frames, tmp_path / "c")
    for t in ("tiles", "blended"):
        write_frames(frames, tmp_path / f"a{t}", image_type=t)
        assert [f.read_bytes() for f in sorted((tmp_path / f"a{t}").glob("*.png"))] == before[t]


def test_matplotlib_is_imported_only_when_a_contour_is_drawn():
    code = (
        "import sys, tempfile, pathlib, numpy as np\n"
        "import app.main\n"
        "from app.services.frame_rendering import write_frames\n"
        "p = lambda: 'matplotlib.pyplot' in sys.modules\n"
        "d = pathlib.Path(tempfile.mkdtemp())\n"
        "f = np.random.default_rng(1).random((2, 88))\n"
        "a = p()\n"
        "write_frames(f, d / 't', image_type='tiles'); write_frames(f, d / 'b', image_type='blended')\n"
        "b = p()\n"
        "write_frames(f, d / 'c', image_type='contour')\n"
        "print(a, b, p())\n"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split()[-3:] == ["False", "False", "True"]


def test_three_hundred_frames_finish_well_within_a_minute(tmp_path):
    frames = np.random.default_rng(4).random((300, 88)) ** 3
    start = time.perf_counter()
    files = contour(frames, tmp_path, smoothing=0.3, smoothing_window=3)
    elapsed = time.perf_counter() - start
    assert len(files) == 300
    assert elapsed < 60, f"300 contour frames took {elapsed:.1f} s"
