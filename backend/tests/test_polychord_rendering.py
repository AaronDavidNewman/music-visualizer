"""The Polychord picture (feature 042): the black frame, the single color, the rosette, the turning, the files."""

import numpy as np
import pytest

from app.services import polychord as pc

WIDTH, HEIGHT = 600, 400
COLOR = (200, 100, 50)


def black() -> np.ndarray:
    return np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)


def figure_picture(letters: list[int], start: float = 0.0, copies: int = 1, notes: int = 6, color=COLOR, width=WIDTH, height=HEIGHT):
    letters_row = np.array(letters + [-1] * (notes - len(letters)))
    turns = pc.link_turns(letters_row[None, :])[0]
    segments, widths = pc.figure_segments(turns, letters_row, start, copies, width, height, notes)
    return pc._frame(segments, widths, np.array(color, dtype=np.uint8), width, height)


C, D, G, F_SHARP = 3, 5, 10, 9


# --- one frame ------------------------------------------------------------------------------------------------------


def test_a_picture_is_a_uint8_height_by_width_by_3_array():
    picture = figure_picture([C, G, D])
    assert picture.shape == (HEIGHT, WIDTH, 3)
    assert picture.dtype == np.uint8


def test_a_frame_with_no_letters_is_entirely_black():
    assert np.array_equal(figure_picture([]), black())


def test_the_background_is_black_and_only_the_figure_is_lit():
    picture = figure_picture([C, G, D, 0, F_SHARP])
    lit = picture.sum(axis=2) > 0
    assert 0 < lit.sum() < 0.15 * lit.size  # a figure, not a filled picture
    assert (picture[~lit] == 0).all()


def test_the_first_link_starts_at_the_center_of_the_picture():
    picture = figure_picture([C, G, D], start=0.0)
    assert picture[HEIGHT // 2, WIDTH // 2].sum() > 0
    assert picture[HEIGHT // 2 - 3 : HEIGHT // 2 + 3, WIDTH // 2 - 3 : WIDTH // 2 + 3].sum() > 0


def test_a_figure_of_straight_links_is_an_ellipse_four_thirds_as_wide_as_it_is_high_inside_the_picture():
    picture = figure_picture([C] * 8, start=0.0, copies=12, notes=8)  # twelve straight arms
    lit = np.argwhere(picture.sum(axis=2) > 0)
    high = lit[:, 0].max() - lit[:, 0].min() + 1
    wide = lit[:, 1].max() - lit[:, 1].min() + 1
    assert 1.25 < wide / high < 1.42  # 2/3 across over 1/2 down
    assert lit[:, 0].min() > 0 and lit[:, 0].max() < HEIGHT - 1 and lit[:, 1].min() > 0 and lit[:, 1].max() < WIDTH - 1


def test_every_lit_pixel_is_the_color_of_the_frame_or_that_color_blended_with_black():
    picture = figure_picture([C, G, D, F_SHARP], copies=4).astype(float)
    lit = picture[picture.sum(axis=2) > 0]
    share = lit[:, 0] / COLOR[0]
    assert (share <= 1.0 + 1e-9).all()
    assert lit[:, 1] == pytest.approx(share * COLOR[1], abs=3)  # a blend is rounded in each channel
    assert lit[:, 2] == pytest.approx(share * COLOR[2], abs=3)
    assert (lit[:, 0] == COLOR[0]).any()  # and the core of a link is the full color


def test_another_color_gives_another_picture_with_the_same_shape():
    first = figure_picture([C, G, D])
    second = figure_picture([C, G, D], color=(10, 240, 90))
    assert np.array_equal(first.sum(axis=2) > 0, second.sum(axis=2) > 0)
    assert not np.array_equal(first, second)


def test_the_same_frame_drawn_twice_is_identical():
    assert np.array_equal(figure_picture([C, G, D, F_SHARP], 33.0, 7), figure_picture([C, G, D, F_SHARP], 33.0, 7))


def test_the_taper_shows_the_center_is_thicker_than_the_tip():
    picture = figure_picture([C] * 6, start=90.0, copies=1, notes=6)  # straight to the right along the middle row
    column_height = (picture.sum(axis=2) > 0).sum(axis=0)
    near_center = column_height[WIDTH // 2 + 4 : WIDTH // 2 + 12].max()
    near_tip = column_height[WIDTH // 2 + 150 : WIDTH // 2 + 170].max()
    assert near_center > near_tip >= 1


def test_a_smaller_picture_has_a_smaller_figure():
    small = figure_picture([C, G, D, F_SHARP], width=300, height=200)
    assert small.shape == (200, 300, 3)
    assert 0 < (small.sum(axis=2) > 0).sum() < (figure_picture([C, G, D, F_SHARP]).sum(axis=2) > 0).sum()


# --- the whole sequence: copies, rotation, tempo color, files -------------------------------------------------------

import io  # noqa: E402

from PIL import Image  # noqa: E402

from app.services.colormaps import DEFAULT_COLORMAP, lookup_table  # noqa: E402

CHORD = {3: 1.0, 10: 0.9, 5: 0.8, 9: 0.7, 0: 0.6, 7: 0.5, 2: 0.4, 8: 0.3}  # C G D F# A E B G# by loudness (column = note)


def chord_values(frames: int) -> np.ndarray:
    values = np.zeros((frames, 88))
    for column, value in CHORD.items():
        values[:, column] = value
    return values


def read(directory, index: int) -> np.ndarray:
    return np.asarray(Image.open(directory / f"frame_{index:06d}.png").convert("RGB"))


def write(tmp_path, values, beat, tempos, settings, frame_rate=10.0, colormap=DEFAULT_COLORMAP, width=WIDTH, height=HEIGHT, name="frames"):
    directory = tmp_path / name
    pc.write_polychord_frames(values, beat, tempos, settings, frame_rate, colormap, directory, width, height)
    return directory


def expected_picture(values_row, copies, start, color, notes, width=WIDTH, height=HEIGHT):
    letters = pc.loudest_letters(values_row[None, :], notes)
    turns = pc.link_turns(letters)
    segments, widths = pc.figure_segments(turns[0], letters[0], start, copies, width, height, notes)
    return pc._frame(segments, widths, color, width, height)


def lit(picture: np.ndarray) -> np.ndarray:
    return picture.sum(axis=2) > 0


def test_frames_are_saved_as_numbered_pngs_of_the_picture_size(tmp_path):
    directory = write(tmp_path, chord_values(3), None, np.full(3, 120.0), pc.PolychordSettings(6, 3, 12, 15.0))
    assert sorted(p.name for p in directory.iterdir()) == ["frame_000000.png", "frame_000001.png", "frame_000002.png"]
    assert read(directory, 0).shape == (HEIGHT, WIDTH, 3)


def test_a_frame_at_the_top_of_the_beat_has_more_copies_than_one_at_the_bottom(tmp_path):
    beat = [0.0, 1.0]  # outside every peak, then the top of the beat
    directory = write(tmp_path, chord_values(2), beat, np.full(2, 120.0), pc.PolychordSettings(6, 1, 12, 0.0))
    one, twelve = read(directory, 0), read(directory, 1)
    assert lit(one).sum() * 3 < lit(twelve).sum()
    assert not (lit(one) & ~lit(twelve)).any()  # with no rotation the single copy is one of the twelve
    color = pc.tempo_colors(np.array([120.0]), DEFAULT_COLORMAP)[0]
    assert np.array_equal(one, expected_picture(chord_values(1)[0], 1, 0.0, color, 6))
    assert np.array_equal(twelve, expected_picture(chord_values(1)[0], 12, 0.0, color, 6))


def test_the_copies_between_the_two_are_in_proportion_to_the_beat(tmp_path):
    beat = [0.0, 0.5, 0.75, 1.0]
    settings = pc.PolychordSettings(5, 2, 10, 0.0)
    directory = write(tmp_path, chord_values(4), beat, np.full(4, 100.0), settings)
    expected = pc.copy_counts(beat, 2, 10)
    color = pc.tempo_colors(np.array([100.0]), DEFAULT_COLORMAP)[0]
    for index in range(4):
        assert np.array_equal(read(directory, index), expected_picture(chord_values(1)[0], int(expected[index]), 0.0, color, 5))


def test_the_picture_turns_by_the_rotation_over_the_frame_rate_each_frame(tmp_path):
    settings = pc.PolychordSettings(6, 3, 3, 30.0)
    directory = write(tmp_path, chord_values(4), None, np.full(4, 120.0), settings, frame_rate=10.0)
    color = pc.tempo_colors(np.array([120.0]), DEFAULT_COLORMAP)[0]
    for index in range(4):
        assert np.array_equal(read(directory, index), expected_picture(chord_values(1)[0], 3, 3.0 * index, color, 6))
    assert not np.array_equal(read(directory, 0), read(directory, 1))


def test_a_rotation_of_zero_gives_the_same_picture_in_every_frame_and_a_negative_one_turns_the_other_way(tmp_path):
    still = write(tmp_path, chord_values(3), None, np.full(3, 120.0), pc.PolychordSettings(6, 3, 3, 0.0), name="still")
    assert np.array_equal(read(still, 0), read(still, 1)) and np.array_equal(read(still, 1), read(still, 2))
    forward = write(tmp_path, chord_values(3), None, np.full(3, 120.0), pc.PolychordSettings(6, 3, 3, 30.0), name="forward")
    backward = write(tmp_path, chord_values(3), None, np.full(3, 120.0), pc.PolychordSettings(6, 3, 3, -30.0), name="backward")
    assert np.array_equal(read(forward, 0), read(backward, 0))
    assert not np.array_equal(read(forward, 1), read(backward, 1))
    color = pc.tempo_colors(np.array([120.0]), DEFAULT_COLORMAP)[0]
    assert np.array_equal(read(backward, 2), expected_picture(chord_values(1)[0], 3, -6.0, color, 6))


def test_every_frame_is_one_color_from_its_tempo_and_a_faster_tempo_is_later_in_the_colormap(tmp_path):
    tempos = np.array([60.0, 108.0, 156.0])
    directory = write(tmp_path, chord_values(3), None, tempos, pc.PolychordSettings(6, 3, 3, 15.0))
    colors = pc.tempo_colors(tempos, DEFAULT_COLORMAP)
    table = lookup_table(DEFAULT_COLORMAP)
    for index in range(3):
        picture = read(directory, index).astype(float)
        brightest = picture.reshape(-1, 3)[picture.sum(axis=2).argmax()]
        assert list(brightest) == pytest.approx([float(c) for c in colors[index]], abs=1)  # the core of a link
        pixels = picture[lit(picture)]
        assert pixels.max(axis=0) == pytest.approx([float(c) for c in colors[index]], abs=1)
    rows = [int(np.flatnonzero((table == c).all(axis=1))[0]) for c in colors]
    assert rows == sorted(rows) and len(set(rows)) == 3


def test_a_silent_frame_is_black_and_the_other_frames_are_not(tmp_path):
    values = chord_values(3)
    values[1] = 0.0
    directory = write(tmp_path, values, None, np.full(3, 120.0), pc.PolychordSettings(6, 3, 12, 15.0))
    assert not read(directory, 1).any()
    assert read(directory, 0).any() and read(directory, 2).any()


def test_the_files_are_identical_on_two_runs_and_with_one_thread_or_several(tmp_path, monkeypatch):
    beat = [0.0, 0.7, 1.0, 0.8, 0.0, 0.9]
    values = chord_values(6)
    values[3, 3] = 0.0  # a change in the notes of one frame
    settings = pc.PolychordSettings(7, 2, 9, 40.0)
    first = write(tmp_path, values, beat, np.linspace(70, 150, 6), settings, name="first")
    second = write(tmp_path, values, beat, np.linspace(70, 150, 6), settings, name="second")
    monkeypatch.setattr(pc, "SAVE_WORKERS", 1)
    single = write(tmp_path, values, beat, np.linspace(70, 150, 6), settings, name="single")
    monkeypatch.setattr(pc, "SAVE_WORKERS", 4)
    several = write(tmp_path, values, beat, np.linspace(70, 150, 6), settings, name="several")
    for index in range(6):
        name = f"frame_{index:06d}.png"
        data = (first / name).read_bytes()
        assert data == (second / name).read_bytes() == (single / name).read_bytes() == (several / name).read_bytes()


def test_the_input_arrays_are_not_changed(tmp_path):
    values = chord_values(3)
    beat = np.array([0.0, 0.5, 1.0])
    tempos = np.array([80.0, 100.0, 120.0])
    before = (values.copy(), beat.copy(), tempos.copy())
    write(tmp_path, values, beat, tempos, pc.PolychordSettings(6, 3, 12, 15.0))
    assert np.array_equal(values, before[0]) and np.array_equal(beat, before[1]) and np.array_equal(tempos, before[2])


@pytest.mark.parametrize(
    "change",
    [
        {"tempos": np.full(2, 120.0)},  # one tempo for each frame
        {"beat": [0.0, 1.0]},
        {"beat": [0.0, 1.5, 0.5]},
        {"frame_rate": 0.0},
        {"frame_rate": -10.0},
        {"colormap": "not-a-colormap"},
        {"settings": pc.PolychordSettings(9, 3, 12, 15.0)},
        {"settings": pc.PolychordSettings(6, 8, 7, 15.0)},
        {"width": 20, "height": 20},
        {"width": 600.5},
        {"values": np.zeros((3, 10))},
        {"tempos": np.array([120.0, float("nan"), 120.0])},
    ],
)
def test_bad_input_is_refused_before_anything_is_written(tmp_path, change):
    arguments = dict(values=chord_values(3), beat=None, tempos=np.full(3, 120.0), settings=pc.DEFAULT_POLYCHORD_SETTINGS, frame_rate=10.0, colormap=DEFAULT_COLORMAP, width=WIDTH, height=HEIGHT)
    arguments.update(change)
    directory = tmp_path / "frames"
    with pytest.raises(ValueError):
        pc.write_polychord_frames(arguments["values"], arguments["beat"], arguments["tempos"], arguments["settings"], arguments["frame_rate"], arguments["colormap"], directory, arguments["width"], arguments["height"])
    assert not directory.exists()
