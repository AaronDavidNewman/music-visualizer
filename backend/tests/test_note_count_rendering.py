"""``write_frames(..., note_count=n)``: the pictures made from the n highest-energy notes, for every image type.

No colormap is named and no number of contour levels is assumed (see ``colormap_names.py``). The expected pictures are
worked out here independently: the choice with a plain ranking, the spread and the grid with ``np.interp`` itself, the
colors from the colormap's table.
"""

import numpy as np
import pytest
from PIL import Image

from app.services.colormaps import COLORMAPS, DEFAULT_COLORMAP, lookup_table
from app.services.frame_rendering import SHOWN_NOTES, smooth_frames, write_frames

from .frame_size import HEIGHT, WIDTH
from .colormap_names import INVALID, WITHOUT_BLACK
from .test_note_selection import MESSAGE as NOTE_COUNT_MESSAGE
from .test_note_selection import ranking
from .test_resolution import with_np_interp as grid_interp
from .test_resolution_rendering import far_from_inner_edges, notes, rgb, tile_index, tile_middles, write

COUNTS = [12, 13, 24, 48, 83, 84]
TYPES = ["tiles", "blended", "contour"]


def spread(values, n):
    """The n highest-energy notes of every frame spread over 84 values, worked out independently."""
    chosen = ranking(values, n)
    xs = np.linspace(0, n - 1, 84)
    return np.array([np.interp(xs, np.arange(n), row[chosen]) for row in values])


def expected_values(frames, n, r=1, smoothing=0.0, window=1):
    """(frames, 84 r^2) values and the file's peak: smooth, choose and spread, then the grid made finer."""
    smoothed = smooth_frames(frames, smoothing, window)
    values = spread(smoothed[:, :SHOWN_NOTES], n)
    if r > 1:
        values = grid_interp(values, r)
    return values, float(smoothed.max())


def expected_colors(frames, name, n, r=1, smoothing=0.0, window=1, threshold=0.0):
    values, peak = expected_values(frames, n, r, smoothing, window)
    table = lookup_table(name)
    share = np.minimum(values / peak, 1.0) if peak > 0 else np.zeros_like(values)
    colours = table[np.rint(np.sqrt(share) * 255).astype(int)]
    hidden = values < threshold / 100.0 * peak
    colours[hidden] = 0
    return colours, hidden


def random_notes(frames=6, seed=1):
    return np.random.default_rng(seed).random((frames, 88)) ** 2


def music_with_noise(frames=10, strong=(20, 30, 40, 50), seed=2):
    """Sustained strong notes (the loudest is 1.0) and faint noise everywhere else, undrawn notes included."""
    rng = np.random.default_rng(seed)
    values = rng.random((frames, 88)) * 0.02
    for k, note in enumerate(strong):
        values[:, note] = 1.0 - 0.1 * k
    return values


# --- Tiles ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", COLORMAPS)
@pytest.mark.parametrize("n", COUNTS)
def test_every_tile_is_the_color_of_its_spread_value(tmp_path, name, n):
    frames = random_notes(3, seed=n)
    files = write(frames, tmp_path, colormap=name, note_count=n)
    expected, _ = expected_colors(frames, name, n)
    for i, f in enumerate(files):
        assert (rgb(f) == expected[i][tile_index(1)]).all(), (name, n, i)


@pytest.mark.parametrize("image_type", TYPES)
def test_eighty_four_notes_gives_exactly_the_files_made_without_the_setting(tmp_path, image_type):
    frames = random_notes(4, seed=3)
    options = dict(smoothing=0.3, smoothing_window=2, threshold=3, image_type=image_type)
    a = write(frames, tmp_path / "a", **options)
    b = write(frames, tmp_path / "b", note_count=84, **options)
    assert [f.read_bytes() for f in a] == [f.read_bytes() for f in b]


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("n", [12, 48])
def test_a_note_that_is_not_chosen_changes_no_pixel(tmp_path, image_type, n):
    frames = music_with_noise(frames=8, seed=n)
    chosen = set(ranking(frames[:, :SHOWN_NOTES], n))
    changed = frames.copy()
    rng = np.random.default_rng(5)
    for note in range(88):
        if note not in chosen and note != 40:  # the loudest note (1.0 in note 20) stays, so the file's peak is unchanged
            changed[:, note] = frames[:, note] * rng.uniform(0.2, 0.9)  # weaker, so still left out
    assert set(ranking(changed[:, :SHOWN_NOTES], n)) == chosen
    assert changed.max() == frames.max()
    a = write(frames, tmp_path / "a", image_type=image_type, note_count=n, resolution=2)
    b = write(changed, tmp_path / "b", image_type=image_type, note_count=n, resolution=2)
    assert [f.read_bytes() for f in a] == [f.read_bytes() for f in b]


@pytest.mark.parametrize("image_type", TYPES)
def test_a_note_that_is_loud_in_one_frame_only_but_weak_in_total_is_left_out_of_that_frame(tmp_path, image_type):
    frames = np.zeros((10, 88))
    frames[:, 5:17] = 1.0  # twelve sustained notes
    with_blip = frames.copy()
    with_blip[3, 70] = 0.9  # a loud note in frame 3 only, below the file's peak
    a = write(frames, tmp_path / "a", image_type=image_type, note_count=12)
    b = write(with_blip, tmp_path / "b", image_type=image_type, note_count=12)
    assert a[3].read_bytes() == b[3].read_bytes()
    assert [f.read_bytes() for f in a] == [f.read_bytes() for f in b]


def test_with_as_many_notes_as_there_are_strong_ones_the_faint_notes_are_gone_from_the_picture(tmp_path):
    strong = tuple(range(10, 22))  # twelve sustained notes, the weakest at 0.52; everything else is faint noise (below 0.02)
    frames = music_with_noise(strong=strong)
    for k, note in enumerate(strong):
        frames[:, note] = 1.0 - 0.04 * k
    assert set(ranking(frames[:, :SHOWN_NOTES], 12)) == set(strong)
    values, peak = expected_values(frames, 12)
    assert values.min() >= 0.52 - 1e-12  # no faint value is left in the spread
    picture = rgb(write(frames, tmp_path, note_count=12)[0])
    expected, _ = expected_colors(frames, DEFAULT_COLORMAP, 12)
    assert (picture == expected[0][tile_index(1)]).all()
    # at 84 notes the same file shows the faint notes: some tile has a value below the weakest strong note
    values84, _ = expected_values(frames, 84)
    assert values84.min() < 0.1


@pytest.mark.parametrize("n", [12, 36])
def test_blended_and_contour_use_the_same_spread_values(tmp_path, monkeypatch, n):
    from matplotlib.axes import Axes

    frames = random_notes(3, seed=40 + n)
    # Blended equals Tiles wherever it is farther than the reach from an inner edge
    tiles = write(frames, tmp_path / "t", note_count=n)
    blended = write(frames, tmp_path / "b", note_count=n, image_type="blended", blend_width=25)
    far = far_from_inner_edges(1, 25)
    for t, b in zip(tiles, blended):
        assert (rgb(t)[far] == rgb(b)[far]).all()
    # the grid that the contour receives is the spread values
    grids = []
    original = Axes.contourf

    def spy(self, x, y, z, *args, **kwargs):
        grids.append(np.asarray(z)[::-1].reshape(-1))
        return original(self, x, y, z, *args, **kwargs)

    monkeypatch.setattr(Axes, "contourf", spy)
    write(frames, tmp_path / "c", note_count=n, image_type="contour", threshold=5)
    values, peak = expected_values(frames, n)
    for got, want in zip(grids, np.where(values < 0.05 * peak, 0.0, values)):
        assert np.allclose(got, want, atol=1e-12)


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("name", COLORMAPS)
@pytest.mark.parametrize("n", [12, 48, 84])
def test_a_silent_input_is_flat_in_the_first_color_at_every_number_of_notes(tmp_path, image_type, name, n):
    for f in write(np.zeros((3, 88)), tmp_path, colormap=name, image_type=image_type, note_count=n, threshold=5):
        assert (rgb(f) == lookup_table(name)[0]).all()


def test_a_file_with_fewer_sounding_notes_than_the_number_asked_for_still_works(tmp_path):
    frames = notes({30: 1.0, 31: 0.5}, {30: 0.8, 31: 0.4})  # two notes sound, twelve are asked for
    files = write(frames, tmp_path, note_count=12)
    expected, _ = expected_colors(frames, DEFAULT_COLORMAP, 12)
    for i, f in enumerate(files):
        assert (rgb(f) == expected[i][tile_index(1)]).all()


@pytest.mark.parametrize("n", [12, 24, 48])
def test_the_scale_is_the_files_peak_over_all_88_notes_including_the_undrawn_ones(tmp_path, n):
    # twelve equal quiet notes and a loud undrawn one: every spread value is the quiet value, a quarter of the file's peak
    frames = np.zeros((2, 88))
    frames[:, 5:5 + n] = 0.25
    frames[:, 85] = 1.0
    for f in write(frames, tmp_path, note_count=n):
        picture = tile_middles(rgb(f), 1)
        assert (picture == lookup_table(DEFAULT_COLORMAP)[round(np.sqrt(0.25) * 255)]).all()


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("n", COUNTS)
def test_the_frame_count_the_names_and_the_size_do_not_depend_on_the_number_of_notes(tmp_path, image_type, n):
    files = write(random_notes(5, seed=50), tmp_path, image_type=image_type, note_count=n)
    assert [f.name for f in files] == [f"frame_{i:06d}.png" for i in range(5)]
    assert all(Image.open(f).size == (WIDTH, HEIGHT) for f in files)


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("n", [12, 48])
def test_the_same_input_gives_byte_identical_files(tmp_path, image_type, n):
    frames = random_notes(4, seed=60)
    options = dict(image_type=image_type, note_count=n, resolution=2, smoothing=0.4, smoothing_window=3, threshold=4)
    a = write(frames, tmp_path / "a", **options)
    b = write(frames, tmp_path / "b", **options)
    assert [f.read_bytes() for f in a] == [f.read_bytes() for f in b]


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("bad", [0, 11, 85, 36.5, None, "36", True])
def test_a_bad_number_of_notes_is_refused_before_anything_is_written(tmp_path, image_type, bad):
    with pytest.raises(ValueError) as error:
        write_frames(random_notes(), tmp_path / "out", image_type=image_type, note_count=bad)
    assert str(error.value) == NOTE_COUNT_MESSAGE
    assert not (tmp_path / "out").exists()


def test_other_arguments_are_still_checked_with_a_number_of_notes(tmp_path):
    for kwargs in ({"colormap": INVALID[0]}, {"threshold": 11}, {"resolution": 6}):
        with pytest.raises(ValueError):
            write_frames(random_notes(), tmp_path / "out", note_count=24, **kwargs)
    assert not (tmp_path / "out").exists()


# --- With the resolution and the other settings ------------------------------------------------------------------------------


def tiles_picture_expected(frames, name, n, r, **options):
    colours, _ = expected_colors(frames, name, n, r, **options)
    return colours


@pytest.mark.parametrize("r", [1, 2, 3, 5])
@pytest.mark.parametrize("n", [12, 36, 84])
def test_the_spread_comes_first_and_the_resolution_makes_the_spread_grid_finer(tmp_path, n, r):
    frames = random_notes(3, seed=70 + n)
    expected = tiles_picture_expected(frames, DEFAULT_COLORMAP, n, r)
    for i, f in enumerate(write(frames, tmp_path, note_count=n, resolution=r)):
        assert (rgb(f) == expected[i][tile_index(r)]).all(), (n, r, i)
    if n < 84 and r > 1:  # and it is not the other order: the resolution step first, the spread over the finer grid after
        other = expected_values(frames, 84, r)[0]
        assert not np.allclose(expected_values(frames, n, r)[0], other)


@pytest.mark.parametrize("name", COLORMAPS)
@pytest.mark.parametrize("n", [12, 36])
def test_smoothing_is_applied_before_the_choice_and_the_threshold_after_the_spread(tmp_path, name, n):
    frames = random_notes(8, seed=80 + n)
    options = dict(smoothing=0.5, smoothing_window=3, threshold=6)
    expected, hidden = expected_colors(frames, name, n, 1, smoothing=0.5, window=3, threshold=6)
    for i, f in enumerate(write(frames, tmp_path, colormap=name, note_count=n, **options)):
        assert (rgb(f) == expected[i][tile_index(1)]).all(), (name, n, i)


def test_the_choice_uses_the_smoothed_values_not_the_raw_ones(tmp_path):
    # twelve steady notes (energy 1.2 raw and smoothed) and a click at the first frame: raw energy 1.0 (left out), smoothed
    # energy 1.44 (kept): with smoothing 0.8 over a window of 1 the click is mixed into the second frame
    frames = np.zeros((6, 88))
    frames[:, 10:22] = 0.2
    frames[0, 60] = 1.0
    smoothed = smooth_frames(frames, 0.8, 1)
    raw_chosen = ranking(frames[:, :84], 12)
    smoothed_chosen = ranking(smoothed[:, :84], 12)
    assert 60 not in raw_chosen and 60 in smoothed_chosen  # the two rankings really differ
    expected, _ = expected_colors(frames, DEFAULT_COLORMAP, 12, smoothing=0.8, window=1)
    raw_expected, _ = expected_colors(frames, DEFAULT_COLORMAP, 12)
    files = write(frames, tmp_path, note_count=12, smoothing=0.8, smoothing_window=1)
    for i, f in enumerate(files):
        assert (rgb(f) == expected[i][tile_index(1)]).all(), i
    assert not all((rgb(f) == raw_expected[i][tile_index(1)]).all() for i, f in enumerate(files))


@pytest.mark.parametrize("r", [1, 3])
def test_the_threshold_hides_exactly_the_tiles_whose_spread_value_is_below_it(tmp_path, r):
    if not WITHOUT_BLACK:
        pytest.skip("every offered colormap has pure black, so a black tile cannot be told from a hidden one")
    name = WITHOUT_BLACK[0]
    frames = music_with_noise(frames=4)
    expected, hidden = expected_colors(frames, name, 12, r, threshold=10)
    picture = tile_middles(rgb(write(frames, tmp_path, colormap=name, note_count=12, resolution=r, threshold=10)[0]), r)
    black = ~picture.reshape(-1, 3).any(axis=1)
    assert (black == hidden[0]).all()
    assert hidden[0].any() and not hidden[0].all()


@pytest.mark.parametrize("name", COLORMAPS)
def test_changing_the_colormap_changes_only_the_colors_not_which_tiles_are_hidden(tmp_path, name):
    other = COLORMAPS[(COLORMAPS.index(name) + 1) % len(COLORMAPS)]
    frames = random_notes(3, seed=90)
    _, hidden_a = expected_colors(frames, name, 24, threshold=7)
    _, hidden_b = expected_colors(frames, other, 24, threshold=7)
    assert (hidden_a == hidden_b).all()
    if other != name:
        a = write(frames, tmp_path / "a", colormap=name, note_count=24, threshold=7)
        b = write(frames, tmp_path / "b", colormap=other, note_count=24, threshold=7)
        assert any(x.read_bytes() != y.read_bytes() for x, y in zip(a, b))
