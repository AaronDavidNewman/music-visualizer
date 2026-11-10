"""The picture of the ``energy-graphs`` image type (feature 034): the two data sets of the histogram, the layout."""

import math

import numpy as np
import pytest
from PIL import Image

from app.services.colormaps import COLORMAPS, lookup_table
from app.services.energy_graphs import EnergyGraphData, write_energy_frames

WIDTH, HEIGHT = 600, 400
PLOT_LEFT, PLOT_RIGHT, PLOT_TOP, PLOT_BOTTOM = 10, 590, 36, 372  # the contract's plot area: x 10 to 590, y 36 to 372
PLOT_HEIGHT = PLOT_BOTTOM - PLOT_TOP  # 336
MIDDLE = 128
TITLE_Y, LABEL_Y = 10, 377


def data_of(histogram, amplitude=None):
    histogram = np.asarray(histogram, dtype=np.int64).reshape(-1, 84)
    return EnergyGraphData(histogram, np.zeros(histogram.shape) if amplitude is None else np.asarray(amplitude, dtype=float).reshape(-1, 84))


def draw(tmp_path, data, colormap="viridis", size=(WIDTH, HEIGHT), name="frames"):
    directory = tmp_path / name
    write_energy_frames(data, colormap, directory, *size)
    return [np.asarray(Image.open(directory / f"frame_{i:06d}.png").convert("RGB")) for i in range(data.frame_count)]


def slots():
    """The columns (x from, x to exclusive) of the slot of each of the 84 notes: the nearest whole pixels of an even split of the plot width."""
    edges = [PLOT_LEFT + int(round(k * (PLOT_RIGHT - PLOT_LEFT) / 84)) for k in range(85)]
    return [(edges[k], edges[k + 1]) for k in range(84)]


def bar_columns(note):
    """The columns of the frequency bar and of the amplitude bar of a note: the two halves of its slot, with one pixel left at the end."""
    x0, x1 = slots()[note]
    half = max(1, (x1 - x0 - 1) // 2)
    return range(x0, x0 + half), range(x0 + half, x0 + 2 * half)


def bar_height(picture, note, data_set, background):
    """The rows of a bar, counted from the baseline up while the pixel in the middle of the bar differs from the background."""
    columns = bar_columns(note)[data_set]
    column = picture[PLOT_TOP:PLOT_BOTTOM, columns[len(columns) // 2]]
    height = 0
    for row in reversed(range(column.shape[0])):
        if not (column[row] != background).any():
            break
        height += 1
    return height


def oracle_shares(totals):
    """What a bar is made of: the softmax of the totals divided by their largest, and then the smallest value of the data set taken off every one."""
    largest = max(totals)
    if largest <= 0:
        return [0.0] * len(totals)
    x = [t / largest for t in totals]
    total = sum(math.exp(v) for v in x)
    shares = [math.exp(v) / total for v in x]
    return [s - min(shares) for s in shares]


# --- the bars --------------------------------------------------------------------------------


def test_one_png_per_frame_in_rgb_of_the_usual_size(tmp_path):
    pictures = draw(tmp_path, data_of(np.ones((3, 84)), np.ones((3, 84))))
    assert len(pictures) == 3
    assert all(p.shape == (HEIGHT, WIDTH, 3) for p in pictures)
    assert Image.open(tmp_path / "frames" / "frame_000000.png").mode == "RGB"


@pytest.mark.parametrize("colormap", COLORMAPS)
def test_the_background_is_the_middle_color_of_the_colormap(tmp_path, colormap):
    (picture,) = draw(tmp_path, data_of(np.ones((1, 84))), colormap)
    assert tuple(picture[2, 2]) == tuple(lookup_table(colormap)[MIDDLE])


def test_the_tallest_bar_of_the_two_data_sets_is_the_same_height_whatever_the_totals(tmp_path):
    counts = np.zeros(84, dtype=np.int64)
    counts[10], counts[11], counts[40] = 840, 420, 84
    amplitude = np.zeros(84)
    amplitude[10], amplitude[11] = 3.5, 1.0
    small, large = draw(tmp_path, data_of([counts, counts * 1000], [amplitude, amplitude * 1000]))
    background = small[2, 2]
    heights = [bar_height(small, n, s, background) for n in range(84) for s in (0, 1)]
    assert max(heights) == PLOT_HEIGHT
    assert np.array_equal(small, large)  # only the proportions of the totals matter


def test_each_bar_is_the_softmax_share_above_the_smallest_of_its_data_set_scaled_by_the_largest_of_both(tmp_path):
    rng = np.random.default_rng(9)
    counts = rng.integers(0, 5000, 84)
    amplitude = rng.random(84) * 40
    (picture,) = draw(tmp_path, data_of([counts], [amplitude]))
    background = picture[2, 2]
    frequency = oracle_shares(counts.tolist())
    loudness = oracle_shares(amplitude.tolist())
    tallest = max(max(frequency), max(loudness))
    for note in range(84):
        assert abs(bar_height(picture, note, 0, background) - round(PLOT_HEIGHT * frequency[note] / tallest)) <= 1, note
        assert abs(bar_height(picture, note, 1, background) - round(PLOT_HEIGHT * loudness[note] / tallest)) <= 1, note


def test_the_two_data_sets_are_on_the_same_scale_not_each_stretched_to_the_full_height(tmp_path):
    counts = np.zeros(84, dtype=np.int64)
    counts[0] = 100
    amplitude = np.zeros(84)
    amplitude[1] = 0.001  # a tiny total: after dividing by its own largest it is still a full distribution like the other
    (picture,) = draw(tmp_path, data_of([counts], [amplitude]))
    background = picture[2, 2]
    assert bar_height(picture, 0, 0, background) == PLOT_HEIGHT
    assert bar_height(picture, 1, 1, background) == PLOT_HEIGHT  # the same softmax shape: the same height
    assert bar_height(picture, 5, 0, background) == 0  # the smallest value of a data set has no height


def test_the_frequency_bar_is_in_the_start_color_and_the_amplitude_bar_in_the_end_color_of_the_colormap(tmp_path):
    counts = np.zeros(84, dtype=np.int64)
    counts[7] = 9
    amplitude = np.zeros(84)
    amplitude[7] = 2.0
    for colormap in ("viridis", "coolwarm"):
        (picture,) = draw(tmp_path, data_of([counts], [amplitude]), colormap, name=colormap)
        table = lookup_table(colormap)
        frequency, amp = bar_columns(7)
        assert tuple(picture[PLOT_BOTTOM - 4, frequency[0]]) == tuple(table[0])
        assert tuple(picture[PLOT_BOTTOM - 4, amp[0]]) == tuple(table[255])


def test_the_pair_of_bars_of_a_note_is_next_to_each_other_inside_its_slot_and_the_slots_are_in_order_of_pitch(tmp_path):
    counts = np.zeros(84, dtype=np.int64)
    counts[0] = 5
    amplitude = np.zeros(84)
    amplitude[83] = 5.0
    (picture,) = draw(tmp_path, data_of([counts], [amplitude]))
    background = picture[2, 2]
    for note in range(84):
        x0, x1 = slots()[note]
        frequency, amp = bar_columns(note)
        assert frequency.stop == amp.start and amp.stop <= x1 - 1 and frequency.start == x0  # at least one pixel between the pairs of two notes
    assert bar_height(picture, 0, 0, background) > 0 and bar_height(picture, 83, 1, background) > 0
    lit = [x for x in range(PLOT_LEFT, PLOT_RIGHT) if (picture[PLOT_TOP : PLOT_BOTTOM - 1, x] != background).any()]
    assert min(lit) < PLOT_LEFT + 10 and max(lit) >= PLOT_RIGHT - 10  # the first note is at the left, the last at the right


def test_neighbouring_notes_are_separated_by_a_column_of_background_in_the_picture(tmp_path):
    totals = np.arange(84) ** 2 + 1  # every note but the smallest has a bar in both data sets
    (picture,) = draw(tmp_path, data_of([totals], [totals]))
    background = picture[2, 2]
    for note, (x0, x1) in enumerate(slots()):
        assert (picture[PLOT_BOTTOM - 1, x1 - 1] == background).all(), note  # the last column of the slot
        if note > 0:
            frequency, amp = bar_columns(note)
            assert not (picture[PLOT_BOTTOM - 1, frequency[0]] == background).all() and not (picture[PLOT_BOTTOM - 1, amp[-1]] == background).all(), note


def test_the_smallest_value_of_a_data_set_has_height_0_so_the_clear_winners_stand_out(tmp_path):
    counts = np.zeros(84, dtype=np.int64)
    counts[3], counts[4] = 10, 5  # two notes have sounded, one twice as much as the other
    (picture,) = draw(tmp_path, data_of([counts]))
    background = picture[2, 2]
    heights = [bar_height(picture, n, 0, background) for n in range(84)]
    assert heights[3] == PLOT_HEIGHT
    assert abs(heights[4] - round(PLOT_HEIGHT * (math.e**0.5 - 1) / (math.e - 1))) <= 1  # e^x - e^0 for x = 1 and 1/2
    assert sum(1 for n, h in enumerate(heights) if h > 0 and n not in (3, 4)) == 0  # every note that has not sounded is at 0


def test_one_note_that_has_sounded_is_the_only_bar(tmp_path):
    counts = np.zeros(84, dtype=np.int64)
    counts[40] = 10
    (picture,) = draw(tmp_path, data_of([counts]))
    background = picture[2, 2]
    heights = [bar_height(picture, n, 0, background) for n in range(84)]
    assert heights[40] == PLOT_HEIGHT and sum(heights) == PLOT_HEIGHT


def test_totals_that_are_all_equal_have_nothing_above_the_smallest_and_draw_no_bars(tmp_path):
    (picture,) = draw(tmp_path, data_of(np.full((1, 84), 7), np.full((1, 84), 2.5)))
    background = picture[2, 2]
    assert (picture[PLOT_TOP : PLOT_BOTTOM - 1, PLOT_LEFT + 1 : PLOT_RIGHT - 1] == background).all()


def test_a_data_set_with_no_total_has_no_bars_and_the_other_is_drawn(tmp_path):
    counts = np.zeros(84, dtype=np.int64)
    counts[3] = 4
    (picture,) = draw(tmp_path, data_of([counts]))  # the amplitude totals are all 0
    background = picture[2, 2]
    assert all(bar_height(picture, n, 1, background) == 0 for n in range(84))
    assert bar_height(picture, 3, 0, background) == PLOT_HEIGHT
    amplitude = np.zeros(84)
    amplitude[3] = 4.0
    (picture,) = draw(tmp_path, data_of(np.zeros((1, 84)), [amplitude]), name="other")
    assert all(bar_height(picture, n, 0, background) == 0 for n in range(84))
    assert bar_height(picture, 3, 1, background) == PLOT_HEIGHT


def test_empty_totals_draw_no_bar(tmp_path):
    (picture,) = draw(tmp_path, data_of(np.zeros((1, 84))))
    background = picture[2, 2]
    inside = picture[PLOT_TOP : PLOT_BOTTOM - 1, PLOT_LEFT + 1 : PLOT_RIGHT - 1]
    assert (inside == background).all()


def test_the_same_data_draws_the_same_bytes_and_the_directory_is_made(tmp_path):
    data = data_of(np.arange(84)[None, :] + 1, np.arange(84)[None, :] * 0.5)
    first = draw(tmp_path, data, name="a/b/c")
    second = draw(tmp_path, data, name="d")
    assert np.array_equal(first[0], second[0])
    assert (tmp_path / "a/b/c/frame_000000.png").read_bytes() == (tmp_path / "d/frame_000000.png").read_bytes()


@pytest.mark.parametrize(
    "bad",
    [
        EnergyGraphData(np.zeros((2, 83), dtype=np.int64), np.zeros((2, 83))),
        EnergyGraphData(-np.ones((2, 84), dtype=np.int64), np.zeros((2, 84))),
        EnergyGraphData(np.zeros((2, 84), dtype=np.int64), np.zeros((3, 84))),
        EnergyGraphData(np.zeros((2, 84), dtype=np.int64), np.zeros(84)),
        EnergyGraphData(np.zeros((2, 84), dtype=np.int64), -np.ones((2, 84))),
        EnergyGraphData(np.zeros((2, 84), dtype=np.int64), np.full((2, 84), np.nan)),
        EnergyGraphData(np.zeros((2, 84), dtype=np.int64), np.full((2, 84), np.inf)),
        EnergyGraphData(np.zeros((2, 84)), np.zeros((2, 84))),  # floats, not whole counts
    ],
)
def test_bad_data_is_refused_before_anything_is_written(tmp_path, bad):
    with pytest.raises(ValueError):
        write_energy_frames(bad, "viridis", tmp_path / "out", WIDTH, HEIGHT)
    assert not (tmp_path / "out").exists()


def test_a_bad_colormap_or_size_is_refused_before_anything_is_written(tmp_path):
    with pytest.raises(ValueError):
        write_energy_frames(data_of(np.ones((1, 84))), "nope", tmp_path / "out", WIDTH, HEIGHT)
    with pytest.raises(ValueError):
        write_energy_frames(data_of(np.ones((1, 84))), "viridis", tmp_path / "out", 0, HEIGHT)
    assert not (tmp_path / "out").exists()


# --- the picture as a whole ----------------------------------------------------------------------------------------------------------


def luminance(rgb):
    return (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255


def test_the_title_the_legend_and_the_octave_labels_are_drawn_and_nothing_is_in_the_empty_corners(tmp_path):
    (picture,) = draw(tmp_path, data_of(np.ones((1, 84)), np.ones((1, 84))))
    background = tuple(picture[2, 2])
    differs = lambda area: (area != background).any(axis=2)  # noqa: E731
    assert differs(picture[TITLE_Y : TITLE_Y + 14, PLOT_LEFT:330]).sum() > 100  # the title, at the left
    legend = picture[TITLE_Y : TITLE_Y + 14, 300:PLOT_RIGHT]
    assert differs(legend).sum() > 60  # the legend, at the right of the title row
    table = lookup_table("viridis")
    for color in (tuple(table[0]), tuple(table[255])):  # a square in the color of each data set
        assert any(tuple(p) == color for p in legend.reshape(-1, 3))
    assert differs(picture[LABEL_Y : LABEL_Y + 14, PLOT_LEFT:PLOT_RIGHT]).sum() > 100  # A1 to A7
    assert not differs(picture[PLOT_TOP + 5 : PLOT_BOTTOM - 5, 0:PLOT_LEFT]).any()  # the margin


@pytest.mark.parametrize("colormap", COLORMAPS)
def test_every_colormap_gives_the_colors_of_its_own_table_and_readable_text(tmp_path, colormap):
    counts = np.zeros(84, dtype=np.int64)
    counts[10], counts[11] = 10, 5
    amplitude = np.zeros(84)
    amplitude[10] = 3.0
    (picture,) = draw(tmp_path, data_of([counts], [amplitude]), colormap)
    table = lookup_table(colormap)
    frequency, amp = bar_columns(10)
    assert tuple(picture[PLOT_BOTTOM - 4, frequency[0]]) == tuple(table[0])
    assert tuple(picture[PLOT_BOTTOM - 4, amp[0]]) == tuple(table[255])
    background = tuple(int(c) for c in table[MIDDLE])
    ink = (0, 0, 0) if luminance(background) > 0.5 else (255, 255, 255)
    colors = {tuple(int(c) for c in p) for p in picture[TITLE_Y : TITLE_Y + 14, PLOT_LEFT:330].reshape(-1, 3)}
    assert ink in colors  # the title is drawn in the contrasting text color


def test_the_picture_scales_to_another_size(tmp_path):
    (picture,) = draw(tmp_path, data_of(np.ones((1, 84)) * np.arange(84), np.arange(84)[None, :] * 0.1), size=(300, 200))
    assert picture.shape == (200, 300, 3)
    assert len({tuple(p) for p in picture.reshape(-1, 3)}) > 3  # more than the background: the graph is there


def test_a_hundred_frames_draw_in_a_few_seconds(tmp_path):
    import time

    rng = np.random.default_rng(2)
    histogram = np.cumsum(rng.integers(0, 85, size=(100, 84)), axis=0)
    amplitude = np.cumsum(rng.random((100, 84)), axis=0)
    started = time.perf_counter()
    write_energy_frames(data_of(histogram, amplitude), "viridis", tmp_path / "many", WIDTH, HEIGHT)
    assert time.perf_counter() - started < 10.0  # a per-frame matplotlib figure would take far longer
