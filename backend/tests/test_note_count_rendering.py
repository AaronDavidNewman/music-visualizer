"""``write_frames(..., note_count=n)``: the pictures made from the n highest-energy notes, for every image type.

No colormap is named and no number of contour levels is assumed (see ``colormap_names.py``). The expected pictures are
worked out here independently: the choice with a plain ranking, the spread and the grid with ``np.interp`` itself, the
colors from the colormap's table.
"""

import numpy as np
import pytest
from PIL import Image

from app.services.colormaps import COLORMAPS, lookup_table
from app.services.frame_rendering import SHOWN_NOTES, write_frames

from .frame_size import HEIGHT, WIDTH
from .colormap_names import INVALID
from .test_note_selection import MESSAGE as NOTE_COUNT_MESSAGE
from .test_note_selection import ranking
from .test_resolution_rendering import notes, rgb, write

COUNTS = [12, 13, 24, 48, 83, 84]
TYPES = ["contour"]


def spread(values, n):
    """The n highest-energy notes of every frame spread over 84 values, worked out independently."""
    chosen = ranking(values, n)
    xs = np.linspace(0, n - 1, 84)
    return np.array([np.interp(xs, np.arange(n), row[chosen]) for row in values])


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


@pytest.mark.parametrize("image_type", TYPES)
@pytest.mark.parametrize("name", COLORMAPS)
@pytest.mark.parametrize("n", [12, 48, 84])
def test_a_silent_input_is_flat_in_the_first_color_at_every_number_of_notes(tmp_path, image_type, name, n):
    for f in write(np.zeros((3, 88)), tmp_path, colormap=name, image_type=image_type, note_count=n, threshold=5):
        assert (rgb(f) == lookup_table(name)[0]).all()


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
