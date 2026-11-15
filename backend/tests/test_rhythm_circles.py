"""The numbers of the ``rhythm-circles`` image type (features 038 and 040): the four series of the peaks, the speeds, the angles.

Every expectation is worked out here with plain loops or by hand, not with the code under test.

The circles, outer (column 0) to inner (column 3), are two layers, each a level and the rate of change of that level: the current tempo (columns 0, 1) and the
local peak's own tempo (2, 3). The current tempo is the one of the tempo finder (``tempo_finder``: it is tested in ``test_tempo_finder.py``; here it is taken from it,
and checked by hand on one small example).
"""

import math

import numpy as np
import pytest

from app.services import rhythm_circles as rc
from app.services.local_peaks import LocalPeak, LocalPeaks
from app.services.tempo_finder import TempoTrack, find_tempo

DEFAULTS = (120.0, 0.0, 60.0, 0.0)  # the starting tempo, and the default rate of a peak, each with no change
TEMPO, PEAK = 0, 2  # the column of the level of each layer; the column after it is the rate of change of that level
LEVELS = [TEMPO, PEAK]
RATES = [column + 1 for column in LEVELS]


def oracle_series(times, rates):
    """For each peak i the four numbers: the current tempo and the peak's own rate, each followed by its change ``(x[i] - x[i-1]) / (t[i] - t[i-1])`` (0 for the
    first peak). The tempo is that of the tempo finder."""
    tempo = find_tempo(times).tempos.tolist()
    levels = [tempo, list(rates)]
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
    rates = 40 + rng.random(count) * 120
    return times.tolist(), rates.tolist()


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
    total = [0.0] * 4
    t = 0.0
    for i in order:
        target = moments[i]
        while t + step <= target:
            speed = oracle_speeds(times, rows, t + step / 2)
            total = [a + s / 60.0 * step for a, s in zip(total, speed)]
            t += step
        speed = oracle_speeds(times, rows, t + (target - t) / 2)
        angles[i] = [a + s / 60.0 * (target - t) for a, s in zip(total, speed)]
    return np.array(angles).reshape(-1, 4)


def hand_made_peaks(times, rates, file_rate=44100, sample_count=None):
    peaks = tuple(LocalPeak(int(round(t * file_rate)), 1.0, 0.0, 1.0, r) for t, r in zip(times, rates))
    return LocalPeaks(peaks=peaks, file_rate=file_rate, sample_count=sample_count or int(round((times[-1] + 1) * file_rate)) if times else file_rate, min_distance=350.0, prominence=20.0)


# --- the series, peak by peak -------------------------------------------------------------------------------------------


def test_a_worked_example_of_the_four_series():
    # the peaks 0, 0.5, 1.1, 1.5, 2.25 s have the rates 60 (the first: the default), 120, 100, 150, 80; the tempo finder's tempo after each (worked out by hand
    # in test_tempo_finder.py for these intervals) is 120, 120, 110, 110 - sqrt(800 / 9) = 100.57, 100.57 - sqrt(200) = 86.43
    times = [0.0, 0.5, 1.1, 1.5, 2.25]
    rates = [60.0, 120.0, 100.0, 150.0, 80.0]
    low = 110.0 - math.sqrt(800.0 / 9.0)
    tempo = [120.0, 120.0, 110.0, low, low - math.sqrt(200.0)]
    series = rc.peak_series(times, rates)
    assert series.shape == (5, 4) and series.dtype == np.float64
    gaps = [0.5, 0.6, 0.4, 0.75]
    for column, level in ((TEMPO, tempo), (PEAK, rates)):
        assert series[:, column].tolist() == pytest.approx(level)
        assert series[:, column + 1].tolist() == pytest.approx([0.0] + [(level[i + 1] - level[i]) / gaps[i] for i in range(4)])
    # a few of the numbers by hand: the tempo falls from 120 to 110 in 0.6 s (-16.67 a second), and the peak rate goes from the default 60 to 120 in half a second
    assert series[2, TEMPO + 1] == pytest.approx(-10.0 / 0.6)
    assert series[1, PEAK + 1] == pytest.approx(60.0 / 0.5)


def test_the_levels_are_the_current_tempo_then_the_peaks_own_rate_in_order_from_the_outer_circle():
    assert (rc.LAYERS, rc.CIRCLES) == (2, 4)
    series = rc.peak_series([0.0, 0.5, 1.0], [90.0, 120.0, 80.0])  # intervals of 0.5 s are samples of 120: the tempo stays 120
    assert np.allclose(series[:, [TEMPO, PEAK]], [[120.0, 90.0], [120.0, 120.0], [120.0, 80.0]], rtol=1e-12)


def test_a_steady_beat_has_no_change():
    series = rc.peak_series([0.5 * i for i in range(1, 11)], [120.0] * 10)
    assert (series[:, TEMPO] == 120.0).all() and (series[:, PEAK] == 120.0).all()
    assert (series[:, RATES] == 0.0).all()


def test_a_restart_of_the_tempo_is_a_spike_in_its_rate_of_change_and_not_in_the_peaks(monkeypatch):
    # the tempo of a restart from above (156 to 78), given as it is: the finder itself is tested in test_tempo_finder.py
    monkeypatch.setattr(rc, "find_tempo", lambda times: TempoTrack(np.array([156.0, 78.0, 79.0]), 1))
    series = rc.peak_series([0.0, 0.3, 0.6], [100.0, 100.0, 100.0])
    assert series[:, TEMPO].tolist() == [156.0, 78.0, 79.0]
    assert series[:, TEMPO + 1].tolist() == pytest.approx([0.0, (78.0 - 156.0) / 0.3, 1.0 / 0.3])
    assert series[:, PEAK + 1].tolist() == [0.0, 0.0, 0.0]  # the peak's own rate did not change


def test_the_series_agree_with_the_oracle_for_random_peaks_of_every_size():
    for count in (0, 1, 2, 3, 5, 8, 9, 20, 200):
        times, rates = random_peaks(count, count)
        got = rc.peak_series(times, rates)
        assert got.shape == (count, 4)
        assert np.allclose(got, np.array(oracle_series(times, rates)).reshape(-1, 4), rtol=1e-12, atol=1e-12)


def test_the_current_tempo_never_leaves_its_range():
    times, rates = random_peaks(500, 11)
    series = rc.peak_series(times, rates)
    assert (series[:, TEMPO] >= 60.0).all() and (series[:, TEMPO] <= 156.0).all()


def test_no_peaks_give_no_rows_and_the_inputs_are_not_changed():
    assert rc.peak_series([], []).shape == (0, 4)
    times, rates = np.array([0.5, 1.0, 1.7]), np.array([120.0, 118.0, 100.0])
    before = times.copy(), rates.copy()
    rc.peak_series(times, rates)
    assert np.array_equal(times, before[0]) and np.array_equal(rates, before[1])


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
    assert rc.DEFAULT_SPEEDS == DEFAULTS and rc.CIRCLES == 4
    assert (rc.circle_speeds([], np.zeros((0, 4)), [0.0, 1.0, 100.0]) == np.array(DEFAULTS)).all()
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
    times, rates = random_peaks(12, 3)
    series = rc.peak_series(times, rates)
    rows = oracle_series(times, rates)
    moments = np.random.default_rng(4).random(60) * (times[-1] + 1)
    got = rc.circle_speeds(times, series, moments)
    for moment, row in zip(moments, got):
        assert np.allclose(row, oracle_speeds(times, rows, moment), rtol=1e-12, atol=1e-12)


# --- the angles -----------------------------------------------------------------------------------------------------------


def test_at_120_beats_per_minute_the_tempo_circle_and_the_peak_circle_advance_720_degrees_a_second_clockwise():
    times = [0.5 * i for i in range(1, 21)]
    series = rc.peak_series(times, [120.0] * 20)
    angles = rc.circle_angles(times, series, np.array([5.0, 6.0, 8.0]))
    for column in (TEMPO, PEAK):
        assert angles[1, column] - angles[0, column] == pytest.approx(2.0)  # 2 turns a second = 720 degrees
        assert angles[2, column] - angles[1, column] == pytest.approx(4.0)
    assert (angles[:, RATES] == 0.0).all()  # the two rate circles stand still


def test_before_the_first_peak_the_defaults_turn_at_their_beats_per_minute():
    angles = rc.circle_angles([2.0], rc.peak_series([2.0], [60.0]), np.array([0.0, 0.5, 1.0]))
    for column, turns_a_second in ((TEMPO, 2.0), (PEAK, 1.0)):  # 120 and 60 beats per minute
        assert angles[:, column].tolist() == pytest.approx([0.0, 0.5 * turns_a_second, turns_a_second])
    assert (angles[:, RATES] == 0.0).all()


def test_the_angles_start_at_0_and_are_not_wrapped():
    angles = rc.circle_angles([], np.zeros((0, 4)), np.array([0.0, 10.0, 100.0]))
    assert angles[0].tolist() == [0.0] * 4 and angles[2, PEAK] == pytest.approx(100.0)


def test_the_angles_agree_with_a_small_step_integration_of_the_speed_for_random_peaks():
    for seed in (1, 2, 3):
        times, rates = random_peaks(6, seed)
        series = rc.peak_series(times, rates)
        rows = oracle_series(times, rates)
        moments = sorted(np.random.default_rng(seed).random(8) * (times[-1] + 0.5))
        assert np.allclose(rc.circle_angles(times, series, np.array(moments)), oracle_angles(times, rows, moments), atol=2e-3)


def test_the_angles_do_not_depend_on_the_order_of_the_moments():
    times, rates = random_peaks(8, 5)
    series = rc.peak_series(times, rates)
    moments = np.random.default_rng(6).random(30) * (times[-1] + 1)
    shuffled = rc.circle_angles(times, series, moments)
    ordered = rc.circle_angles(times, series, np.sort(moments))
    assert np.allclose(shuffled[np.argsort(moments)], ordered)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_the_angle_is_continuous_across_every_peak_while_the_slope_changes_there(seed):
    times, rates = random_peaks(8, seed)
    series = rc.peak_series(times, rates)
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


def test_a_peak_rate_that_speeds_up_turns_its_rate_circle_clockwise_and_one_that_slows_down_counterclockwise():
    times = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    rates = [100.0, 100.0, 110.0, 120.0, 120.0, 105.0, 90.0]
    series = rc.peak_series(times, rates)
    angles = rc.circle_angles(times, series, np.array([1.0, 1.5, 2.0, 2.5, 3.0]))
    rate = PEAK + 1
    assert angles[1, rate] > angles[0, rate] and angles[2, rate] > angles[1, rate]  # speeding up (peaks 2 and 3): the angle increases
    assert angles[4, rate] < angles[3, rate]  # slowing down (peak 5 and 6): decreasing


def test_the_rate_circles_turn_at_the_change_divided_by_the_time_between_the_two_peaks():
    times, rates = [0.0, 0.5, 1.5], [120.0, 126.0, 126.0]
    series = rc.peak_series(times, rates)
    angles = rc.circle_angles(times, series, np.array([0.5, 1.0]))
    assert (angles[1, PEAK + 1] - angles[0, PEAK + 1]) * 60.0 / 0.5 == pytest.approx(12.0)  # 12 revolutions per minute over half a second: (126 - 120) / 0.5
    # the tempo of the worked example falls from 120 to 110 in 0.6 s: the circle of the tempo turns counterclockwise at 10 / 0.6 revolutions per minute
    times = [0.0, 0.5, 1.1, 1.5]
    series = rc.peak_series(times, [60.0, 120.0, 100.0, 150.0])
    angles = rc.circle_angles(times, series, np.array([1.1, 1.4]))
    assert (angles[1, TEMPO + 1] - angles[0, TEMPO + 1]) * 60.0 / 0.3 == pytest.approx(-10.0 / 0.6)  # from 1.1 s to 1.4 s the speed is that of the peak at 1.1 s
    assert series[2, TEMPO + 1] < 0 and series[3, TEMPO + 1] < 0  # the tempo slows down at the 100 bpm peak, and again at the 150 bpm one (150 stands for 100: 1.5 times it)


def test_bad_peaks_or_moments_are_refused():
    series = rc.peak_series([1.0, 2.0], [100.0, 90.0])
    for function in (rc.circle_speeds, rc.circle_angles):
        with pytest.raises(ValueError):
            function([1.0, 2.0], series, np.array([np.nan]))
        with pytest.raises(ValueError):
            function([1.0, 2.0], series, np.array([-1.0]))
        with pytest.raises(ValueError):
            function([1.0, 2.0, 3.0], series, np.array([1.0]))  # three times for two rows
        for columns in (6, 8):
            with pytest.raises(ValueError):
                function([1.0, 2.0], np.zeros((2, columns)), np.array([1.0]))  # the six and eight columns of the earlier versions of the feature


# --- from the peaks of a measurement ------------------------------------------------------------------------------------


def test_the_angles_at_the_middle_of_every_frame_come_from_the_peaks_and_their_rates():
    times = [0.5 * i for i in range(1, 9)]
    rates = [60.0] + [120.0] * 7  # the first peak has the default rate, the others 120 beats per minute
    peaks = hand_made_peaks(times, rates)
    data = rc.rhythm_angles(peaks, 10, 50)
    assert data.angles.shape == (50, 4) and data.angles.dtype == np.float64 and data.frame_count == 50
    moments = (np.arange(50) + 0.5) / 10
    series = rc.peak_series([p.sample / 44100 for p in peaks.peaks], [p.rate for p in peaks.peaks])
    assert np.allclose(data.angles, rc.circle_angles([p.sample / 44100 for p in peaks.peaks], series, moments), rtol=1e-12, atol=1e-12)
    # once the peaks come every half second at 120 beats per minute the tempo circle and the peak circle advance 2 turns a second: 0.2 turns a frame at 10 frames a second
    assert np.diff(data.angles[:, TEMPO])[-5:] == pytest.approx([0.2] * 5, abs=1e-9)
    assert np.diff(data.angles[:, PEAK])[-5:] == pytest.approx([0.2] * 5, abs=1e-9)


def test_no_peaks_turn_every_circle_at_the_defaults_and_the_rate_circles_stand_still():
    peaks = LocalPeaks(peaks=(), file_rate=44100, sample_count=44100 * 5, min_distance=350.0, prominence=20.0)
    data = rc.rhythm_angles(peaks, 10, 20)
    for column, step in ((PEAK, 0.1), (TEMPO, 0.2)):  # the default rates 60 and 120: turns a frame at 10 frames a second
        assert np.diff(data.angles[:, column]) == pytest.approx([step] * 19)
    assert (data.angles[:, RATES] == 0.0).all()


def test_no_frames_give_no_rows_and_a_bad_frame_rate_or_count_is_refused():
    peaks = hand_made_peaks([0.5, 1.0], [60.0, 120.0])
    assert rc.rhythm_angles(peaks, 10, 0).angles.shape == (0, 4)
    for bad in (0, -1, True, float("nan"), "10", None):
        with pytest.raises(ValueError):
            rc.rhythm_angles(peaks, bad, 5)
    for bad in (-1, 2.5, True, "3", None):
        with pytest.raises(ValueError):
            rc.rhythm_angles(peaks, 10, bad)


def test_the_rhythm_data_checks_its_angles():
    assert rc.RhythmData(np.zeros((3, 4))).frame_count == 3
    rc.RhythmData(np.full((2, 4), 1234.5))  # large unwrapped angles are fine
    for bad in (np.zeros(4), np.zeros((3, 5)), np.zeros((3, 8)), np.zeros((3, 6)), np.full((2, 4), np.nan), np.full((2, 4), np.inf), np.zeros((2, 4, 1))):
        with pytest.raises(ValueError):
            rc._check_data(rc.RhythmData(bad))
