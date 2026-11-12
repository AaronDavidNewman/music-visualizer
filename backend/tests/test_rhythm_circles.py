"""The numbers of the ``rhythm-circles`` image type (feature 038): the eight series of the peaks, the speeds, the angles.

Every expectation is worked out here with plain loops, not with the code under test.

The circles, outer (column 0) to inner (column 7), are four layers, each a level and the rate of change of that level, the longest aggregation outermost:
the aggregated tempo of 8 peaks (columns 0, 1), of 4 (2, 3), of 2 (4, 5) and the tempo (6, 7). The aggregated tempo of a window of the latest tempos is its average
or its fastest (highest), whichever is closer to the current tempo (the fastest when they are equally close).
"""

import numpy as np
import pytest

from app.services import rhythm_circles as rc
from app.services.local_peaks import LocalPeak, LocalPeaks

DEFAULTS = (60.0, 0.0) * 4
AGG8, AGG4, AGG2, TEMPO = 0, 2, 4, 6  # the column of the level of each layer; the column after it is the rate of change of that level
LEVELS = [AGG8, AGG4, AGG2, TEMPO]
RATES = [column + 1 for column in LEVELS]


def oracle_level(window, current):
    """The average or the fastest (highest) of the window, whichever is closer to the current tempo; the fastest when equally close."""
    average = sum(window) / len(window)
    fastest = max(window)
    return average if abs(average - current) < abs(fastest - current) else fastest


def oracle_series(times, tempos):
    """For each peak i the eight numbers: the aggregated tempo of the latest 8 tempos (of those that exist) and its change, the same for 4 and for 2, and the tempo
    itself with its change. The change of a level x is (x[i] - x[i-1]) / (t[i] - t[i-1]), 0 for the first peak."""
    levels = [[oracle_level(tempos[max(0, i - n + 1) : i + 1], tempos[i]) for i in range(len(tempos))] for n in (8, 4, 2, 1)]
    rows = []
    for i in range(len(times)):
        row = []
        for level in levels:
            row += [level[i], (level[i] - level[i - 1]) / (times[i] - times[i - 1]) if i >= 1 else 0.0]
        rows.append(row)
    return rows


def random_peaks(count, seed):
    rng = np.random.default_rng(seed)
    times = np.cumsum(0.2 + rng.random(count) * 0.8)
    tempos = 40 + rng.random(count) * 120
    return times.tolist(), tempos.tolist()


def oracle_speeds(times, rows, t):
    """The row of the latest peak at or before t, the defaults before the first."""
    speed = DEFAULTS
    for time, row in zip(times, rows):
        if time <= t:
            speed = row
    return speed


def oracle_angles(times, rows, moments, step=1e-4):
    """The running total of speed / 60 by small steps (the midpoint of each step), read at the sorted moments, in turns."""
    order = sorted(range(len(moments)), key=lambda i: moments[i])
    angles = [None] * len(moments)
    total = [0.0] * 8
    t = 0.0
    for i in order:
        target = moments[i]
        while t + step <= target:
            speed = oracle_speeds(times, rows, t + step / 2)
            total = [a + s / 60.0 * step for a, s in zip(total, speed)]
            t += step
        speed = oracle_speeds(times, rows, t + (target - t) / 2)
        angles[i] = [a + s / 60.0 * (target - t) for a, s in zip(total, speed)]
    return np.array(angles).reshape(-1, 8)


def hand_made_peaks(times, rates, file_rate=44100, sample_count=None):
    peaks = tuple(LocalPeak(int(round(t * file_rate)), 1.0, 0.0, 1.0, r) for t, r in zip(times, rates))
    return LocalPeaks(peaks=peaks, file_rate=file_rate, sample_count=sample_count or int(round((times[-1] + 1) * file_rate)) if times else file_rate, min_distance=100.0, prominence=50.0)


# --- the series, peak by peak -------------------------------------------------------------------------------------------


def test_a_steady_tempo_has_no_change_and_the_aggregated_tempos_are_the_tempo():
    series = rc.peak_series([0.5 * i for i in range(1, 11)], [120.0] * 10)
    assert series.shape == (10, 8) and series.dtype == np.float64
    assert (series[:, LEVELS] == 120.0).all()  # the tempo and its aggregates over 2, 4 and 8 peaks
    assert (series[:, RATES] == 0.0).all()  # and the rates of change of all four


def test_a_tempo_that_goes_from_120_to_126_between_two_peaks_half_a_second_apart_has_the_same_change_in_all_four_layers():
    series = rc.peak_series([0.0, 0.5, 1.0], [120.0, 120.0, 126.0])
    for level in LEVELS:
        assert series[:, level].tolist() == [120.0, 120.0, 126.0]  # the new tempo is the fastest, and the fastest is nearest to it: 126 in every layer
        assert series[:, level + 1].tolist() == [0.0, 0.0, 12.0]  # (126 - 120) / 0.5


def test_a_slowing_tempo_is_followed_by_the_averages_of_the_longer_layers_because_they_are_nearer_to_it_than_the_old_fastest():
    series = rc.peak_series([0.0, 0.5, 1.0, 1.6], [120.0, 120.0, 110.0, 100.0])
    assert series[:, TEMPO].tolist() == [120.0, 120.0, 110.0, 100.0]
    assert series[2, TEMPO + 1] == pytest.approx(-20.0) and series[3, TEMPO + 1] == pytest.approx(-10.0 / 0.6)  # the tempo itself falls at once
    # the window of 2: [120, 110] has the average 115 (5 from 110) and the fastest 120 (10 away): the average; then [110, 100]: 105
    assert series[:, AGG2].tolist() == pytest.approx([120.0, 120.0, 115.0, 105.0])
    assert series[:, AGG2 + 1].tolist() == pytest.approx([0.0, 0.0, -10.0, -10.0 / 0.6])
    # the windows of 4 and of 8 hold the same 3 or 4 peaks: [120, 120, 110] has the average 116.67, [120, 120, 110, 100] the average 112.5
    for level in (AGG4, AGG8):
        assert series[:, level].tolist() == pytest.approx([120.0, 120.0, 350 / 3, 112.5])
        assert series[:, level + 1].tolist() == pytest.approx([0.0, 0.0, (350 / 3 - 120.0) / 0.5, (112.5 - 350 / 3) / 0.6])


def test_the_fastest_is_chosen_when_it_is_closer_to_the_current_tempo_than_the_average_is_and_the_average_when_it_is_closer():
    series = rc.peak_series([0.0, 0.5, 1.0, 1.5], [100.0, 100.0, 200.0, 190.0])
    # at the last peak (the tempo 190): the window of 2 is [200, 190]: the average 195 is 5 away, the fastest 200 is 10 away: the average;
    # the windows of 4 and 8 are [100, 100, 200, 190]: the average 147.5 is 42.5 away, the fastest 200 is 10 away: the fastest
    assert series[3, [AGG8, AGG4, AGG2, TEMPO]].tolist() == [200.0, 200.0, 195.0, 190.0]


def test_when_the_average_and_the_fastest_are_equally_close_the_fastest_is_chosen():
    series = rc.peak_series([0.0, 0.5, 1.0], [60.0, 160.0, 140.0])
    # the window [60, 160, 140]: the average is 120 (20 below 140), the fastest is 160 (20 above 140)
    assert series[2, AGG4] == 160.0 and series[2, AGG8] == 160.0


def test_a_tempo_that_is_the_fastest_of_its_window_is_its_own_aggregate_whatever_the_average():
    series = rc.peak_series([0.0, 0.5, 1.0, 1.5], [80.0, 90.0, 100.0, 200.0])
    assert series[3, [AGG8, AGG4, AGG2, TEMPO]].tolist() == [200.0] * 4  # the fastest is 0 away from it


def test_the_series_agree_with_the_oracle_for_random_peaks_of_every_size_including_fewer_than_the_period():
    for count in (0, 1, 2, 3, 5, 8, 9, 20):
        times, tempos = random_peaks(count, count)
        got = rc.peak_series(times, tempos)
        assert got.shape == (count, 8)
        assert np.allclose(got, np.array(oracle_series(times, tempos)).reshape(-1, 8), rtol=1e-12, atol=1e-12)


def test_the_aggregated_tempos_use_the_peaks_there_are_while_there_are_fewer_than_their_period():
    tempos = [190.0, 180.0, 170.0, 160.0, 150.0, 140.0, 130.0, 120.0, 110.0, 100.0]  # slowing down evenly: the tempo is always the lowest of its window
    series = rc.peak_series([0.5 * i for i in range(10)], tempos)
    assert series[0, LEVELS].tolist() == [190.0, 190.0, 190.0, 190.0]  # the first peak: its own tempo
    assert series[1, [AGG2, AGG4, AGG8]].tolist() == [185.0, 185.0, 185.0]  # the two tempos there are: the average is nearer to the lower one than the fastest
    assert series[3, AGG4] == 175.0  # the average of the 4 tempos that exist
    assert series[7, AGG8] == 155.0 and series[8, AGG8] == 145.0 and series[9, AGG8] == 135.0  # the average of the latest 8, then each peak drops the oldest
    assert series[9, AGG4] == 115.0 and series[9, AGG2] == 105.0 and series[9, TEMPO] == 100.0
    assert series[1, RATES].tolist() == [-10.0, -10.0, -10.0, -20.0]  # each aggregate changes at half the pace of the tempo at the start, then at the same pace
    assert series[9, RATES].tolist() == [-20.0] * 4  # (135 - 145) / 0.5, (115 - 125) / 0.5, (105 - 115) / 0.5, (100 - 110) / 0.5


def test_one_fast_peak_among_slower_ones_is_the_aggregate_of_the_peak_itself_then_it_fades_into_the_averages_until_it_leaves_the_window():
    tempos = [100.0, 100.0, 200.0] + [100.0] * 8  # one peak at twice the beat among the beats
    series = rc.peak_series([0.5 * i for i in range(11)], tempos)
    assert series[:, AGG2].tolist() == pytest.approx([100.0, 100.0, 200.0, 150.0] + [100.0] * 7)
    assert series[:, AGG4].tolist() == pytest.approx([100.0, 100.0, 200.0, 125.0, 125.0, 125.0] + [100.0] * 5)
    assert series[:, AGG8].tolist() == pytest.approx([100.0, 100.0, 200.0, 125.0, 120.0, 700 / 6, 800 / 7, 112.5, 112.5, 112.5, 100.0])
    assert series[:, TEMPO].tolist() == tempos


def test_the_oracle_itself_gives_the_numbers_worked_out_by_hand():
    rows = oracle_series([0.0, 0.5, 1.0, 1.6], [120.0, 120.0, 110.0, 100.0])
    assert rows[3] == pytest.approx([112.5, (112.5 - 350 / 3) / 0.6, 112.5, (112.5 - 350 / 3) / 0.6, 105.0, -10.0 / 0.6, 100.0, -10.0 / 0.6])
    assert oracle_level([100.0, 100.0, 200.0, 190.0], 190.0) == 200.0 and oracle_level([200.0, 190.0], 190.0) == 195.0 and oracle_level([60.0, 160.0, 140.0], 140.0) == 160.0


def test_the_longest_aggregation_is_the_outer_circle_and_the_tempo_the_innermost():
    assert (rc.AGGREGATE_PERIODS, rc.LAYERS, rc.CIRCLES) == ((2, 4, 8), 4, 8)
    # at the last peak (the tempo 100) every window has a different average: [200, 100] 150, [100, 100, 200, 100] 125 for 4 and also for 8 (only 4 peaks exist)
    series = rc.peak_series([0.0, 0.5, 1.0, 1.5], [100.0, 100.0, 200.0, 100.0])
    assert series[3, [AGG8, AGG4, AGG2, TEMPO]].tolist() == [125.0, 125.0, 150.0, 100.0]
    # at the last peak of six the window of 2 and of 4 are all 100 and only the window of 8 still holds the 200: its average is 116.67
    series = rc.peak_series([0.5 * i for i in range(6)], [100.0, 200.0, 100.0, 100.0, 100.0, 100.0])
    assert series[5, [AGG8, AGG4, AGG2, TEMPO]].tolist() == pytest.approx([700 / 6, 100.0, 100.0, 100.0])


def test_no_peaks_give_no_rows_and_the_inputs_are_not_changed():
    assert rc.peak_series([], []).shape == (0, 8)
    times, tempos = np.array([0.5, 1.0, 1.7]), np.array([120.0, 118.0, 100.0])
    before = times.copy(), tempos.copy()
    rc.peak_series(times, tempos)
    assert np.array_equal(times, before[0]) and np.array_equal(tempos, before[1])


@pytest.mark.parametrize(
    "times, tempos",
    [([0.0, 0.5], [120.0]), ([[0.0, 0.5]], [[120.0, 120.0]]), ([0.0, np.nan], [120.0, 120.0]), ([0.0, 0.5], [120.0, np.inf]), ([0.0, 0.5, 0.5], [1.0, 1.0, 1.0]),
     ([0.0, 1.0, 0.5], [1.0, 1.0, 1.0]), ([0.0, 0.5], [120.0, 0.0]), ([0.0, 0.5], [120.0, -5.0]), ("ab", "cd"), (None, None)],
)
def test_peaks_that_are_not_peaks_are_refused(times, tempos):
    with pytest.raises(ValueError):
        rc.peak_series(times, tempos)


# --- the speeds -----------------------------------------------------------------------------------------------------------


def test_before_the_first_peak_and_with_no_peaks_the_speeds_are_the_defaults():
    assert rc.DEFAULT_SPEEDS == DEFAULTS and rc.CIRCLES == 8
    assert (rc.circle_speeds([], np.zeros((0, 8)), [0.0, 1.0, 100.0]) == np.array(DEFAULTS)).all()
    series = rc.peak_series([1.0, 1.5], [100.0, 120.0])
    assert (rc.circle_speeds([1.0, 1.5], series, [0.0, 0.5, 0.999999]) == np.array(DEFAULTS)).all()


def test_a_moment_at_a_peak_has_the_row_of_that_peak_and_between_two_peaks_the_earlier_one():
    times = [1.0, 1.5, 2.2]
    series = rc.peak_series(times, [100.0, 120.0, 90.0])
    got = rc.circle_speeds(times, series, [1.0, 1.2, 1.5, 1.8, 2.2, 5.0])
    assert got[0].tolist() == series[0].tolist() and got[1].tolist() == series[0].tolist()  # at the first peak, and after it
    assert got[2].tolist() == series[1].tolist() and got[3].tolist() == series[1].tolist()
    assert got[4].tolist() == series[2].tolist() and got[5].tolist() == series[2].tolist()  # at the last peak, and after it


def test_the_speeds_agree_with_the_oracle_for_random_peaks_and_moments_in_any_order():
    times, tempos = random_peaks(12, 3)
    series = rc.peak_series(times, tempos)
    rows = oracle_series(times, tempos)
    moments = np.random.default_rng(4).random(60) * (times[-1] + 1)
    got = rc.circle_speeds(times, series, moments)
    for moment, row in zip(moments, got):
        assert np.allclose(row, oracle_speeds(times, rows, moment), rtol=1e-12, atol=1e-12)


# --- the angles -----------------------------------------------------------------------------------------------------------


def test_at_120_beats_per_minute_the_tempo_circle_and_the_aggregated_tempos_advance_720_degrees_a_second_clockwise():
    times = [0.5 * i for i in range(1, 21)]
    series = rc.peak_series(times, [120.0] * 20)
    angles = rc.circle_angles(times, series, np.array([5.0, 6.0, 8.0]))
    for column in LEVELS:
        assert angles[1, column] - angles[0, column] == pytest.approx(2.0)  # 2 turns a second = 720 degrees
        assert angles[2, column] - angles[1, column] == pytest.approx(4.0)
    assert (angles[:, RATES] == 0.0).all()  # the four rate circles stand still


def test_before_the_first_peak_the_defaults_turn_at_60_beats_per_minute_one_turn_a_second():
    angles = rc.circle_angles([2.0], rc.peak_series([2.0], [60.0]), np.array([0.0, 0.5, 1.0]))
    for column in LEVELS:
        assert angles[:, column].tolist() == pytest.approx([0.0, 0.5, 1.0])
    assert (angles[:, RATES] == 0.0).all()


def test_the_angles_start_at_0_and_are_not_wrapped():
    angles = rc.circle_angles([], np.zeros((0, 8)), np.array([0.0, 10.0, 100.0]))
    assert angles[0].tolist() == [0.0] * 8 and angles[2, AGG8] == pytest.approx(100.0)


def test_the_angles_agree_with_a_small_step_integration_of_the_speed_for_random_peaks():
    for seed in (1, 2, 3):
        times, tempos = random_peaks(6, seed)
        series = rc.peak_series(times, tempos)
        rows = oracle_series(times, tempos)
        moments = sorted(np.random.default_rng(seed).random(8) * (times[-1] + 0.5))
        assert np.allclose(rc.circle_angles(times, series, np.array(moments)), oracle_angles(times, rows, moments), atol=2e-3)


def test_the_angles_do_not_depend_on_the_order_of_the_moments():
    times, tempos = random_peaks(8, 5)
    series = rc.peak_series(times, tempos)
    moments = np.random.default_rng(6).random(30) * (times[-1] + 1)
    shuffled = rc.circle_angles(times, series, moments)
    ordered = rc.circle_angles(times, series, np.sort(moments))
    assert np.allclose(shuffled[np.argsort(moments)], ordered)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_the_angle_is_continuous_across_every_peak_while_the_slope_changes_there(seed):
    times, tempos = random_peaks(8, seed)
    series = rc.peak_series(times, tempos)
    eps = 1e-7
    before = rc.circle_angles(times, series, np.array(times) - eps)
    at = rc.circle_angles(times, series, np.array(times))
    after = rc.circle_angles(times, series, np.array(times) + eps)
    assert np.allclose(before, at, atol=1e-4) and np.allclose(after, at, atol=1e-4)  # no jump (the speeds are at most a few hundred rpm)
    for i in range(8):
        slope_before = (at[i] - before[i]) / eps
        slope_after = (after[i] - at[i]) / eps
        previous = np.array(DEFAULTS) if i == 0 else series[i - 1]
        assert np.allclose(slope_after - slope_before, (series[i] - previous) / 60.0, atol=1e-3)


def test_a_tempo_that_speeds_up_turns_its_rate_circle_clockwise_and_one_that_slows_down_counterclockwise():
    times = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    tempos = [100.0, 100.0, 110.0, 120.0, 120.0, 105.0, 90.0]
    series = rc.peak_series(times, tempos)
    angles = rc.circle_angles(times, series, np.array([1.0, 1.5, 2.0, 2.5, 3.0]))
    rate = TEMPO + 1
    assert angles[1, rate] > angles[0, rate] and angles[2, rate] > angles[1, rate]  # speeding up (peaks 2 and 3): the angle increases
    assert angles[4, rate] < angles[3, rate]  # slowing down (peak 5 and 6): decreasing


def test_the_tempo_rate_circle_turns_at_the_change_divided_by_the_time_between_the_two_peaks():
    times, tempos = [0.0, 0.5, 1.5], [120.0, 126.0, 126.0]
    series = rc.peak_series(times, tempos)
    angles = rc.circle_angles(times, series, np.array([0.5, 1.0]))
    rate = TEMPO + 1
    assert (angles[1, rate] - angles[0, rate]) * 60.0 / 0.5 == pytest.approx(12.0)  # 12 revolutions per minute over half a second: (126 - 120) / 0.5


def test_the_rate_circles_of_the_aggregated_tempos_turn_at_the_change_of_the_aggregate_in_either_direction():
    times, tempos = [0.0, 0.5, 1.0, 3.0, 4.0], [120.0, 120.0, 126.0, 100.0, 90.0]
    series = rc.peak_series(times, tempos)
    angles = rc.circle_angles(times, series, np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    steps = np.diff(angles, axis=0) * 60.0  # the revolutions per minute of every circle over each second: between 1.0 and 2.0, 2.0 and 3.0, ...
    # the peak at 1.0 (the tempo 126, the fastest and nearest to itself in every window): every aggregate rose from 120 to 126 in half a second: 12
    for rate in (AGG2 + 1, AGG4 + 1, AGG8 + 1):
        assert steps[0, rate] == pytest.approx(12.0) and steps[1, rate] == pytest.approx(12.0)
    # the peak at 3.0 (the tempo 100): the window of 2 is [126, 100]: the average 113; of 4 and 8 [120, 120, 126, 100]: the average 116.5; two seconds after 126: -6.5, -4.75
    assert steps[2, AGG2 + 1] == pytest.approx((113.0 - 126.0) / 2.0)
    assert steps[2, AGG4 + 1] == pytest.approx((116.5 - 126.0) / 2.0) and steps[2, AGG8 + 1] == pytest.approx((116.5 - 126.0) / 2.0)
    # the peak at 4.0 (the tempo 90): [100, 90] has the average 95; of 4 [120, 126, 100, 90] 109; of 8 [120, 120, 126, 100, 90] 111.2; one second after
    assert steps[3, AGG2 + 1] == pytest.approx(95.0 - 113.0)
    assert steps[3, AGG4 + 1] == pytest.approx(109.0 - 116.5) and steps[3, AGG8 + 1] == pytest.approx(111.2 - 116.5)
    assert steps[3, AGG2 + 1] < 0 and steps[0, AGG2 + 1] > 0  # counterclockwise when slowing down, clockwise when speeding up


def test_bad_peaks_or_moments_are_refused():
    series = rc.peak_series([1.0, 2.0], [100.0, 90.0])
    for function in (rc.circle_speeds, rc.circle_angles):
        with pytest.raises(ValueError):
            function([1.0, 2.0], series, np.array([np.nan]))
        with pytest.raises(ValueError):
            function([1.0, 2.0], series, np.array([-1.0]))
        with pytest.raises(ValueError):
            function([1.0, 2.0, 3.0], series, np.array([1.0]))  # three times for two rows
        with pytest.raises(ValueError):
            function([1.0, 2.0], np.zeros((2, 6)), np.array([1.0]))  # the six columns of an earlier version of the feature


# --- from the peaks of a measurement ------------------------------------------------------------------------------------


def test_the_angles_at_the_middle_of_every_frame_come_from_the_peaks_and_their_rates():
    times = [0.5 * i for i in range(1, 9)]
    rates = [60.0] + [120.0] * 7  # the first peak has the default rate, the others 120 beats per minute
    peaks = hand_made_peaks(times, rates)
    data = rc.rhythm_angles(peaks, 10, 50)
    assert data.angles.shape == (50, 8) and data.angles.dtype == np.float64 and data.frame_count == 50
    moments = (np.arange(50) + 0.5) / 10
    series = rc.peak_series([p.sample / 44100 for p in peaks.peaks], [p.rate for p in peaks.peaks])
    assert np.allclose(data.angles, rc.circle_angles([p.sample / 44100 for p in peaks.peaks], series, moments), rtol=1e-12, atol=1e-12)
    # once the peaks come every half second at 120 beats per minute the tempo circle advances 2 turns a second: 0.2 turns a frame at 10 frames a second
    assert np.diff(data.angles[:, TEMPO])[-5:] == pytest.approx([0.2] * 5, abs=1e-9)


def test_no_peaks_turn_every_circle_at_the_defaults_and_the_rate_circles_stand_still():
    peaks = LocalPeaks(peaks=(), file_rate=44100, sample_count=44100 * 5, min_distance=100.0, prominence=50.0)
    data = rc.rhythm_angles(peaks, 10, 20)
    assert np.diff(data.angles[:, TEMPO]) == pytest.approx([0.1] * 19)  # 60 beats per minute: one turn a second, 0.1 a frame
    assert (data.angles[:, RATES] == 0.0).all()
    for column in LEVELS:
        assert np.allclose(data.angles[:, column], data.angles[:, TEMPO])  # the aggregated tempos of a steady 60 are 60


def test_no_frames_give_no_rows_and_a_bad_frame_rate_or_count_is_refused():
    peaks = hand_made_peaks([0.5, 1.0], [60.0, 120.0])
    assert rc.rhythm_angles(peaks, 10, 0).angles.shape == (0, 8)
    for bad in (0, -1, True, float("nan"), "10", None):
        with pytest.raises(ValueError):
            rc.rhythm_angles(peaks, bad, 5)
    for bad in (-1, 2.5, True, "3", None):
        with pytest.raises(ValueError):
            rc.rhythm_angles(peaks, 10, bad)


def test_the_rhythm_data_checks_its_angles():
    assert rc.RhythmData(np.zeros((3, 8))).frame_count == 3
    rc.RhythmData(np.full((2, 8), 1234.5))  # large unwrapped angles are fine
    for bad in (np.zeros(8), np.zeros((3, 7)), np.zeros((3, 6)), np.full((2, 8), np.nan), np.full((2, 8), np.inf), np.zeros((2, 8, 1))):
        with pytest.raises(ValueError):
            rc._check_data(rc.RhythmData(bad))
