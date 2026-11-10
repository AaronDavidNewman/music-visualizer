"""The rings that show the beat in the middle of the ``chromatic-decay`` picture (feature 036): the distance from the peak, the level of every ring, the colors, the geometry.

Every expectation is worked out here with plain loops, not with the code under test.
"""

import numpy as np
import pytest

from app.services import chromatic_decay as cd
from app.services.colormaps import COLORMAPS, lookup_table


def oracle_distances(beat):
    """The distance of every frame from the peak, stretched over the range of the beat of the file (feature 036, second change): a frame outside every peak
    (position 0) is 1; inside the peaks the highest position is 0 and the 1st percentile of the positions inside the peaks is 1, in a straight line between,
    held at the ends; when there is no range (no position inside a peak, or all equal) it is simply 1 - position."""
    inside = [b for b in beat if b > 0]
    if not inside:
        return [1.0 - b for b in beat]
    low, high = float(np.percentile(inside, 1)), max(inside)
    if high - low <= 0:
        return [1.0 - b for b in beat]
    return [1.0 if b <= 0 else min(max((high - b) / (high - low), 0.0), 1.0) for b in beat]


def oracle_levels(beat):
    """Ring 1 is the distance of the current frame; ring k from 2 is the mean of the distances of frames t - (2k - 3) and t - (2k - 2); before the start: 1."""
    distance = oracle_distances(beat)

    def d(i):
        return distance[i] if i >= 0 else 1.0

    out = []
    for t in range(len(beat)):
        row = [d(t)]
        for k in range(2, 13):
            row.append((d(t - (2 * k - 3)) + d(t - (2 * k - 2))) / 2)
        out.append(row)
    return np.array(out).reshape(-1, 12)


# --- the distance from the peak ------------------------------------------------------------------------------------


def test_the_distance_is_one_minus_the_position_in_the_local_peak():
    got = cd.peak_distances(np.array([1.0, 0.0, 0.75, 0.5, 0.25]))
    assert got.shape == (5,) and got.dtype == np.float64
    assert got.tolist() == [0.0, 1.0, 0.25, 0.5, 0.75]


def test_no_frames_have_no_distances():
    assert cd.peak_distances(np.zeros(0)).shape == (0,)


@pytest.mark.parametrize("bad", [np.zeros((2, 2)), np.array([0.0, 1.5]), np.array([-0.1, 0.0]), np.array([np.nan, 0.0]), np.array([True, False]), "ab", None, 0.5])
def test_a_beat_that_is_not_one_number_from_0_to_1_for_each_frame_is_refused(bad):
    with pytest.raises(ValueError):
        cd.peak_distances(bad)
    with pytest.raises(ValueError):
        cd.ring_levels(bad)


# --- the levels of the rings ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("frames", [0, 1, 5, 22, 23, 60])
def test_the_levels_agree_with_the_loop_oracle_for_random_beats_including_beats_shorter_than_the_history(frames):
    beat = np.random.default_rng(frames).random(frames)
    got = cd.ring_levels(beat)
    assert got.shape == (frames, 12) and got.dtype == np.float64
    assert np.allclose(got, oracle_levels(beat.tolist()), rtol=0, atol=1e-12)
    if frames:
        assert got.min() >= 0 and got.max() <= 1


def test_the_center_ring_is_the_current_frame_and_a_peak_travels_one_ring_outward_every_two_frames():
    beat = np.zeros(40)
    beat[10] = 1.0  # a peak at frame 10 only
    levels = cd.ring_levels(beat)
    assert levels[10, 0] == 0.0 and (levels[10, 1:] == 1.0).all()  # at the peak: the center is at the peak, the history before it was far from one
    assert levels[11, 0] == 1.0 and levels[11, 1] == 0.5 and (levels[11, 2:] == 1.0).all()  # ring 2 = frames 10 and 9: (0 + 1) / 2
    assert levels[12, 1] == 0.5 and levels[12, 2] == 1.0  # ring 2 = frames 11 and 10: (1 + 0) / 2
    assert levels[13, 1] == 1.0 and levels[13, 2] == 0.5  # ring 3 = frames 10 and 9 ... frames t-3 = 10 and t-4 = 9
    assert levels[14, 2] == 0.5 and levels[14, 3] == 1.0
    for k in range(2, 13):  # ring k holds the peak at frames 10 + (2k - 3) and 10 + (2k - 2)
        frames_with_half = [t for t in range(40) if levels[t, k - 1] == 0.5]
        assert frames_with_half == [10 + 2 * k - 3, 10 + 2 * k - 2], k
    assert levels[10 + 22, 11] == 0.5 and levels[10 + 23, 11] == 1.0  # the outermost ring forgets it after frame t - 22


def test_the_moments_before_the_start_count_as_far_from_a_peak():
    beat = np.ones(30)  # at the top of a peak all the time
    levels = cd.ring_levels(beat)
    assert (levels[0, 1:] == 1.0).all() and levels[0, 0] == 0.0  # at frame 0 nothing exists before it
    assert levels[1, 1] == 0.5 + 0.0 and levels[1, 2] == 1.0  # ring 2 = frames 0 and -1: (0 + 1) / 2
    assert levels[2, 1] == 0.0  # ring 2 = frames 1 and 0
    assert levels[22, 11] == 0.0 and levels[21, 11] == 0.5  # ring 12 = frames t-21 and t-22: the first full history is at frame 22
    assert (levels[23:] == 0.0).all()


def test_a_steady_beat_of_0_is_far_from_a_peak_in_every_ring():
    assert (cd.ring_levels(np.zeros(30)) == 1.0).all()


def test_the_levels_do_not_change_the_input():
    beat = np.random.default_rng(1).random(30)
    before = beat.copy()
    cd.ring_levels(beat)
    cd.peak_distances(beat)
    assert np.array_equal(beat, before)


# --- the colors ------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("colormap", COLORMAPS)
def test_a_ring_at_the_peak_is_the_first_color_far_from_it_the_last_and_between_the_color_at_the_same_share(colormap):
    table = lookup_table(colormap)
    levels = np.array([[0.0, 1.0, 0.5, 0.25, 0.75] + [0.0] * 7])
    colors = cd.ring_colors_of(levels, colormap)
    assert colors.shape == (1, 12, 3) and colors.dtype == np.uint8
    assert colors[0, 0].tolist() == table[0].tolist()
    assert colors[0, 1].tolist() == table[255].tolist()
    assert colors[0, 2].tolist() == table[128].tolist()  # rint(0.5 x 255) = rint(127.5) = 128
    assert colors[0, 3].tolist() == table[int(round(0.25 * 255))].tolist()
    assert colors[0, 4].tolist() == table[int(round(0.75 * 255))].tolist()


def test_the_colors_of_many_frames_follow_the_levels_one_by_one():
    levels = np.random.default_rng(2).random((7, 12))
    table = lookup_table("viridis")
    colors = cd.ring_colors_of(levels, "viridis")
    for f in range(7):
        for k in range(12):
            assert colors[f, k].tolist() == table[int(np.rint(levels[f, k] * 255))].tolist()


@pytest.mark.parametrize("bad", [np.zeros((2, 11)), np.zeros(12), np.full((1, 12), 1.5), np.full((1, 12), -0.1), np.full((1, 12), np.nan)])
def test_levels_that_are_not_levels_are_refused(bad):
    with pytest.raises(ValueError):
        cd.ring_colors_of(bad, "viridis")


def test_a_bad_colormap_is_refused():
    with pytest.raises(ValueError):
        cd.ring_colors_of(np.zeros((1, 12)), "nope")


# --- the geometry ----------------------------------------------------------------------------------------------------------


def test_the_circle_is_140_pixels_across_on_the_usual_picture_in_12_rings_of_equal_width():
    assert cd.PEAK_RINGS == 12 and cd.PEAK_RADIUS == 70
    radius, ring_width = cd.peak_circle_geometry(600, 400)
    assert radius == pytest.approx(70.0) and ring_width == pytest.approx(70.0 / 12)
    assert ring_width * 12 == pytest.approx(radius)


def test_another_size_scales_the_circle_with_the_picture():
    assert cd.peak_circle_geometry(300, 200)[0] == pytest.approx(35.0)
    assert cd.peak_circle_geometry(1200, 800)[0] == pytest.approx(140.0)
    assert cd.peak_circle_geometry(800, 400)[0] == pytest.approx(70.0)  # the smaller side decides


@pytest.mark.parametrize("size", [(600, 400), (300, 200), (200, 200), (100, 100), (60, 60), (50, 50), (40, 40), (1000, 400), (1200, 800)])
def test_the_circle_always_lies_inside_the_free_middle_of_the_ring_of_letters(size):
    radius, ring_width = cd.peak_circle_geometry(*size)
    ring, full = cd.ring_geometry(*size)
    assert radius <= ring - full - 1 + 1e-9
    assert ring_width * 12 == pytest.approx(radius)


@pytest.mark.parametrize("size", [(0, 400), (600, 0), (-1, 400), (True, 400), (600.5, 400), ("600", 400)])
def test_a_bad_size_is_refused(size):
    with pytest.raises(ValueError):
        cd.peak_circle_geometry(*size)


# --- the distance is stretched over the range of the beat of the file (feature 036, second change) -----------------------------


def test_the_stretched_distance_agrees_with_the_oracle_on_random_beats():
    rng = np.random.default_rng(8)
    for frames in (1, 2, 10, 60, 300):
        beat = 0.5 + 0.5 * rng.random(frames)  # inside the peaks: from 0.5 to 1, like real music
        beat[rng.random(frames) < 0.1] = 0.0  # some frames outside every peak
        got = cd.beat_distances(beat)
        assert got.shape == (frames,) and got.dtype == np.float64
        assert np.allclose(got, oracle_distances(beat.tolist()), rtol=0, atol=1e-12)
        assert got.min() >= 0 and got.max() <= 1


def test_a_beat_that_only_goes_from_0_6_to_1_uses_the_whole_colormap_from_the_first_color_to_the_last():
    beat = np.linspace(0.6, 1.0, 101)  # what real music does: never near the bottom of the position scale
    levels = cd.ring_levels(beat)
    assert levels[:, 0].min() == 0.0  # the top of the beat takes the first color
    assert levels[:, 0][0] > 0.98  # the bottom of the beat (all but the lowest 1 percent of positions) takes the last
    assert levels[:, 0].max() == 1.0
    colors = cd.ring_colors_of(levels, "coolwarm")
    table = lookup_table("coolwarm")
    assert colors[:, 0][-1].tolist() == table[0].tolist() and colors[:, 0][0].tolist() == table[255].tolist()
    # without the stretch the same beat would only reach 1 - 0.6 = 0.4 of the way: the first half of the colormap
    assert cd.peak_distances(beat).max() == pytest.approx(0.4)
    assert levels[:, 0].max() > 2 * cd.peak_distances(beat).max()


def test_the_top_of_the_beat_is_the_highest_position_even_when_it_does_not_reach_1():
    beat = np.array([0.0, 0.5, 0.7, 0.9, 0.7, 0.5, 0.0])  # a beat that peaks at 0.9
    got = cd.beat_distances(beat)
    assert got[3] == 0.0  # the highest position is the first color
    assert got[0] == 1.0 and got[6] == 1.0  # outside every peak: the last color
    assert got[1] == pytest.approx(1.0 - 0.0, abs=0.05)  # the lowest positions inside the peaks are near the last color


def test_the_frames_outside_every_peak_are_always_far_whatever_the_range():
    beat = np.concatenate([np.zeros(5), np.linspace(0.55, 1.0, 40), np.zeros(5)])
    got = cd.beat_distances(beat)
    assert (got[:5] == 1.0).all() and (got[-5:] == 1.0).all()


def test_one_outlier_frame_does_not_squash_the_range_because_the_bottom_is_the_first_percentile():
    rng = np.random.default_rng(3)
    beat = 0.6 + 0.4 * rng.random(400)
    beat[7] = 0.02  # a single frame far below the others
    got = cd.beat_distances(beat)
    assert got[7] == 1.0  # the outlier is held at the last color
    assert np.percentile(got, 50) == pytest.approx(0.5, abs=0.1)  # and the others still spread over the whole range, not squeezed into its first half
    assert got.max() == 1.0 and (got < 0.05).sum() > 5


def test_a_beat_with_no_range_is_just_one_minus_the_position():
    for beat in (np.zeros(10), np.ones(10), np.full(10, 0.8), np.array([0.0, 0.7, 0.7, 0.0])):
        assert np.array_equal(cd.beat_distances(beat), 1.0 - beat) or (cd.beat_distances(beat)[beat > 0] == 1.0 - beat[beat > 0]).all()
    assert (cd.beat_distances(np.zeros(10)) == 1.0).all()
    assert (cd.beat_distances(np.ones(10)) == 0.0).all()
    assert np.allclose(cd.beat_distances(np.full(10, 0.8)), 0.2)


def test_the_stretch_does_not_depend_on_the_order_of_the_frames_and_does_not_change_the_input():
    rng = np.random.default_rng(9)
    beat = 0.5 + 0.5 * rng.random(50)
    before = beat.copy()
    forward = cd.beat_distances(beat)
    backward = cd.beat_distances(beat[::-1])
    assert np.allclose(forward, backward[::-1])
    assert np.array_equal(beat, before)


@pytest.mark.parametrize("bad", [np.zeros((2, 2)), np.array([0.0, 1.5]), np.array([np.nan, 0.5]), np.array([True, False]), "ab", None])
def test_the_stretched_distance_refuses_what_is_not_a_beat(bad):
    with pytest.raises(ValueError):
        cd.beat_distances(bad)
