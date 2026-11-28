"""The numbers of the ``rhythm-circles`` image type (features 038, 040 and 047): the series of the peaks, the speeds, the angles and the six columns.

Every expectation is worked out here with plain loops or by hand, not with the code under test.

The circles, outer (column 0) to inner (column 5), are three layers, each a level and the rate of change of that level: the average tempo (columns 0, 1: the straight average of the last 5
first voted tempos), the raw first voted tempo (2, 3) and the local peak's own tempo (4, 5). The voted tempos come from ``tempo_votes`` (tested in ``test_tempo_votes.py``) and the starts from ``note_onsets`` (tested in ``test_note_onsets.py``); here they are taken from them and
checked by hand on one example. The tests that make their notes in the note strengths alone give the job's audio as silence, so that the starts stay at the middle of their window. The tempo finder of feature 040 is no longer drawn.
"""

import math
from pathlib import Path

import numpy as np
import pytest

from app.services import rhythm_circles as rc
from app.services import tempo_finder
from app.services import note_onsets as no
from app.services import tempo_votes as tv
from app.services.local_peaks import LocalPeak, LocalPeaks

VOTE_DEFAULTS = (120.0, 0.0, 120.0, 0.0)  # the starting tempo twice, each with no change
PEAK_DEFAULTS = (60.0, 0.0)  # the default rate of a peak, with no change
DEFAULTS = VOTE_DEFAULTS + PEAK_DEFAULTS
AVERAGE, RAW, PEAK = 0, 2, 4  # the column of the level of each layer; the column after it is the rate of change of that level
LEVELS = [AVERAGE, RAW, PEAK]
RATES = [column + 1 for column in LEVELS]
OLD_ANGLES = Path(__file__).resolve().parents[2] / "specs" / "047-rhythm-note-voting" / "tools" / "old_peak_angles.npy"


def oracle_series(times, rates):
    """For each peak i the two numbers: the peak's own rate and its change ``(x[i] - x[i-1]) / (t[i] - t[i-1])`` (0 for the first peak)."""
    rows = []
    for i in range(len(times)):
        rows.append([rates[i], (rates[i] - rates[i - 1]) / (times[i] - times[i - 1]) if i >= 1 else 0.0])
    return rows


def random_peaks(count, seed):
    rng = np.random.default_rng(seed)
    times = np.cumsum(0.2 + rng.random(count) * 0.8)
    rates = 40 + rng.random(count) * 120
    return times.tolist(), rates.tolist()


def oracle_speeds(times, rows, t, defaults):
    """The row of the latest event at or before t, the defaults before the first."""
    speed = defaults
    for time, row in zip(times, rows):
        if time <= t:
            speed = row
    return speed


def oracle_angles(times, rows, moments, defaults, step=1e-4):
    """The running total of speed / 60 by small steps (the midpoint of each step), read at the sorted moments, in turns."""
    width = len(defaults)
    order = sorted(range(len(moments)), key=lambda i: moments[i])
    angles = [None] * len(moments)
    total = [0.0] * width
    t = 0.0
    for i in order:
        target = moments[i]
        while t + step <= target:
            speed = oracle_speeds(times, rows, t + step / 2, defaults)
            total = [a + s / 60.0 * step for a, s in zip(total, speed)]
            t += step
        speed = oracle_speeds(times, rows, t + (target - t) / 2, defaults)
        angles[i] = [a + s / 60.0 * (target - t) for a, s in zip(total, speed)]
    return np.array(angles).reshape(-1, width)


def hand_made_peaks(times, rates, file_rate=44100, sample_count=None):
    peaks = tuple(LocalPeak(int(round(t * file_rate)), 1.0, 0.0, 1.0, r) for t, r in zip(times, rates))
    return LocalPeaks(peaks=peaks, file_rate=file_rate, sample_count=sample_count or int(round((times[-1] + 1) * file_rate)) if times else file_rate, min_distance=350.0, prominence=20.0)


def silent(frames):
    return np.zeros((frames, 88))


def quiet(windows):
    """The two channels of a file with no sound, as long as the 60 ms ``windows`` (any value that has a length): there is no waveform to place a start on, so the starts stay at the middle of their window."""
    samples = int(np.shape(windows)[0] * 0.06 * 44100) + 4096 if np.ndim(windows) else 0
    return np.zeros(samples, dtype=np.int16), np.zeros(samples, dtype=np.int16)


def rhythm(peaks, frame_rate, frames, windows, limit=20):
    """``rhythm_angles`` for note strengths made by hand: the audio is silence (see ``quiet``)."""
    return rc.rhythm_angles(peaks, frame_rate, frames, windows, *quiet(windows), limit)


def starts_of(windows):
    """The starts of the note strengths made by hand: the middle of each window that begins a note."""
    return no.pick_onsets(no.onset_rises(windows))


def no_peaks(seconds=5):
    return LocalPeaks(peaks=(), file_rate=44100, sample_count=44100 * seconds, min_distance=350.0, prominence=20.0)


# --- the constants ------------------------------------------------------------------------------------------------------


def test_there_are_six_circles_in_three_layers_and_the_defaults_are_those_of_the_voted_tempos_and_the_peak():
    assert rc.CIRCLES == 6 and rc.LAYERS == 3
    assert rc.VOTE_DEFAULTS == VOTE_DEFAULTS and rc.PEAK_DEFAULTS == PEAK_DEFAULTS and rc.DEFAULT_SPEEDS == DEFAULTS


# --- the series of the peaks, peak by peak ------------------------------------------------------------------------------


def test_a_worked_example_of_the_peak_series():
    times = [0.5, 1.0, 1.5, 2.5]
    tempos = [60.0, 120.0, 126.0, 90.0]
    series = rc.peak_series(times, tempos)
    assert series.shape == (4, 2)
    # the rate of the peak, then its change per second: (120 - 60) / 0.5, (126 - 120) / 0.5, (90 - 126) / 1.0
    assert np.allclose(series, [[60.0, 0.0], [120.0, 120.0], [126.0, 12.0], [90.0, -36.0]])


def test_the_levels_are_the_peaks_own_rate_and_a_steady_beat_has_no_change():
    series = rc.peak_series([1.0, 1.5, 2.0, 2.5], [100.0] * 4)
    assert series[:, 0].tolist() == [100.0] * 4 and (series[:, 1] == 0.0).all()


def test_the_peak_series_does_not_use_the_tempo_finder(monkeypatch):
    def refuse(times):
        raise AssertionError("the tempo finder must not be called")

    monkeypatch.setattr(tempo_finder, "find_tempo", refuse)
    assert rc.peak_series([1.0, 2.0], [100.0, 90.0]).shape == (2, 2)
    assert not hasattr(rc, "find_tempo")


def test_the_peak_series_agrees_with_the_oracle_for_random_peaks_of_every_size():
    for count in (1, 2, 3, 12, 50):
        times, rates = random_peaks(count, count)
        assert np.allclose(rc.peak_series(times, rates), oracle_series(times, rates), rtol=1e-12, atol=1e-12)


def test_no_peaks_give_no_rows_and_the_inputs_are_not_changed():
    assert rc.peak_series([], []).shape == (0, 2)
    times, rates = [1.0, 2.0, 3.0], [100.0, 90.0, 80.0]
    before = (list(times), list(rates))
    times_array, rates_array = np.array(times), np.array(rates)
    rc.peak_series(times_array, rates_array)
    assert times_array.tolist() == before[0] and rates_array.tolist() == before[1]


@pytest.mark.parametrize(
    "times, tempos",
    [([1.0, 1.0], [100.0, 100.0]), ([2.0, 1.0], [100.0, 100.0]), ([1.0, np.nan], [100.0, 100.0]), ([1.0, 2.0], [100.0]), ([1.0, 2.0], [100.0, 0.0]), ([1.0, 2.0], [100.0, -5.0]), ([1.0, 2.0], [100.0, np.inf]), ("ab", [1.0]), ([[1.0]], [[1.0]])],
)
def test_peaks_that_are_not_peaks_are_refused(times, tempos):
    with pytest.raises(ValueError):
        rc.peak_series(times, tempos)


# --- the speeds ---------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("defaults", [VOTE_DEFAULTS, PEAK_DEFAULTS, DEFAULTS])
def test_before_the_first_event_and_with_no_events_the_speeds_are_the_defaults_of_the_group(defaults):
    width = len(defaults)
    assert (rc.circle_speeds([], np.zeros((0, width)), [0.0, 1.0, 100.0], defaults) == np.array(defaults)).all()
    series = np.full((2, width), 7.0)
    got = rc.circle_speeds([1.0, 1.5], series, [0.0, 0.5, 0.999999], defaults)
    assert got.shape == (3, width) and (got == np.array(defaults)).all()


def test_a_moment_at_an_event_has_the_row_of_that_event_and_between_two_events_the_earlier_one():
    times = [1.0, 1.5, 2.2]
    series = rc.peak_series(times, [100.0, 120.0, 90.0])
    got = rc.circle_speeds(times, series, [1.0, 1.2, 1.5, 1.8, 2.2, 5.0], PEAK_DEFAULTS)
    assert got[0].tolist() == series[0].tolist() and got[1].tolist() == series[0].tolist()  # at the first peak, and after it
    assert got[2].tolist() == series[1].tolist() and got[3].tolist() == series[1].tolist()
    assert got[4].tolist() == series[2].tolist() and got[5].tolist() == series[2].tolist()  # at the last peak, and after it


def test_the_speeds_agree_with_the_oracle_for_random_events_and_moments_in_any_order():
    times, rates = random_peaks(12, 3)
    series = rc.peak_series(times, rates)
    rows = oracle_series(times, rates)
    moments = np.random.default_rng(4).random(60) * (times[-1] + 1)
    got = rc.circle_speeds(times, series, moments, PEAK_DEFAULTS)
    for moment, row in zip(moments, got):
        assert np.allclose(row, oracle_speeds(times, rows, moment, PEAK_DEFAULTS), rtol=1e-12, atol=1e-12)


# --- the angles ---------------------------------------------------------------------------------------------------------


def test_at_120_beats_per_minute_a_tempo_circle_and_the_peak_circle_advance_720_degrees_a_second_clockwise():
    times = [0.5 * i for i in range(1, 21)]
    series = rc.peak_series(times, [120.0] * 20)
    angles = rc.circle_angles(times, series, np.array([5.0, 6.0, 8.0]), PEAK_DEFAULTS)
    assert angles[1, 0] - angles[0, 0] == pytest.approx(2.0)  # 2 turns a second = 720 degrees
    assert angles[2, 0] - angles[1, 0] == pytest.approx(4.0)
    assert (angles[:, 1] == 0.0).all()  # the rate circle stands still
    votes = np.tile(np.array([120.0, 0.0, 120.0, 0.0]), (20, 1))
    angles = rc.circle_angles(times, votes, np.array([5.0, 6.0, 8.0]), VOTE_DEFAULTS)
    for column in (0, 2):
        assert angles[1, column] - angles[0, column] == pytest.approx(2.0)
        assert angles[2, column] - angles[1, column] == pytest.approx(4.0)
    assert (angles[:, [1, 3]] == 0.0).all()


def test_before_the_first_event_the_defaults_turn_at_their_beats_per_minute():
    angles = rc.circle_angles([2.0], rc.peak_series([2.0], [60.0]), np.array([0.0, 0.5, 1.0]), PEAK_DEFAULTS)
    assert angles[:, 0].tolist() == pytest.approx([0.0, 0.5, 1.0])  # 60 beats per minute: a turn a second
    assert (angles[:, 1] == 0.0).all()
    angles = rc.circle_angles([2.0], np.zeros((1, 4)), np.array([0.0, 0.5, 1.0]), VOTE_DEFAULTS)
    assert angles[:, 0].tolist() == pytest.approx([0.0, 1.0, 2.0])  # 120: two turns a second


def test_the_angles_start_at_0_and_are_not_wrapped():
    angles = rc.circle_angles([], np.zeros((0, 6)), np.array([0.0, 10.0, 100.0]))
    assert angles[0].tolist() == [0.0] * 6 and angles[2, 4] == pytest.approx(100.0) and angles[2, 0] == pytest.approx(200.0)


def test_the_angles_agree_with_a_small_step_integration_of_the_speed_for_random_peaks():
    for seed in (1, 2, 3):
        times, rates = random_peaks(6, seed)
        series = rc.peak_series(times, rates)
        rows = oracle_series(times, rates)
        moments = sorted(np.random.default_rng(seed).random(8) * (times[-1] + 0.5))
        assert np.allclose(rc.circle_angles(times, series, np.array(moments), PEAK_DEFAULTS), oracle_angles(times, rows, moments, PEAK_DEFAULTS), atol=2e-3)


def test_the_angles_do_not_depend_on_the_order_of_the_moments():
    times, rates = random_peaks(8, 5)
    series = rc.peak_series(times, rates)
    moments = np.random.default_rng(6).random(30) * (times[-1] + 1)
    shuffled = rc.circle_angles(times, series, moments, PEAK_DEFAULTS)
    ordered = rc.circle_angles(times, series, np.sort(moments), PEAK_DEFAULTS)
    assert np.allclose(shuffled[np.argsort(moments)], ordered)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_the_angle_is_continuous_across_every_event_while_the_slope_changes_there(seed):
    times, rates = random_peaks(8, seed)
    series = rc.peak_series(times, rates)
    eps = 1e-7
    before = rc.circle_angles(times, series, np.array(times) - eps, PEAK_DEFAULTS)
    at = rc.circle_angles(times, series, np.array(times), PEAK_DEFAULTS)
    after = rc.circle_angles(times, series, np.array(times) + eps, PEAK_DEFAULTS)
    assert np.allclose(before, at, atol=1e-4) and np.allclose(after, at, atol=1e-4)  # no jump (the speeds are at most a few hundred rpm)
    for i in range(8):
        slope_before = (at[i] - before[i]) / eps
        slope_after = (after[i] - at[i]) / eps
        previous = np.array(PEAK_DEFAULTS) if i == 0 else series[i - 1]
        assert np.allclose(slope_after - slope_before, (series[i] - previous) / 60.0, atol=1e-3)


def test_a_peak_rate_that_speeds_up_turns_its_rate_circle_clockwise_and_one_that_slows_down_counterclockwise():
    times = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    rates = [100.0, 100.0, 110.0, 120.0, 120.0, 105.0, 90.0]
    series = rc.peak_series(times, rates)
    angles = rc.circle_angles(times, series, np.array([1.0, 1.5, 2.0, 2.5, 3.0]), PEAK_DEFAULTS)
    assert angles[1, 1] > angles[0, 1] and angles[2, 1] > angles[1, 1]  # speeding up (peaks 2 and 3): the angle increases
    assert angles[4, 1] < angles[3, 1]  # slowing down (peak 5 and 6): decreasing


def test_the_rate_circles_turn_at_the_change_divided_by_the_time_between_the_two_events():
    times, rates = [0.0, 0.5, 1.5], [120.0, 126.0, 126.0]
    series = rc.peak_series(times, rates)
    angles = rc.circle_angles(times, series, np.array([0.5, 1.0]), PEAK_DEFAULTS)
    assert (angles[1, 1] - angles[0, 1]) * 60.0 / 0.5 == pytest.approx(12.0)  # 12 revolutions per minute over half a second: (126 - 120) / 0.5


@pytest.mark.parametrize("function", [rc.circle_speeds, rc.circle_angles])
def test_bad_events_moments_or_widths_are_refused(function):
    series = rc.peak_series([1.0, 2.0], [100.0, 90.0])
    with pytest.raises(ValueError):
        function([1.0, 2.0], series, np.array([np.nan]), PEAK_DEFAULTS)
    with pytest.raises(ValueError):
        function([1.0, 2.0], series, np.array([-1.0]), PEAK_DEFAULTS)
    with pytest.raises(ValueError):
        function([1.0, 2.0, 3.0], series, np.array([1.0]), PEAK_DEFAULTS)  # three times for two rows
    with pytest.raises(ValueError):
        function([1.0, 2.0], series, np.array([1.0]), VOTE_DEFAULTS)  # two columns for four defaults
    with pytest.raises(ValueError):
        function([1.0, 2.0], np.zeros((2, 4)), np.array([1.0]), PEAK_DEFAULTS)  # four columns for two defaults
    with pytest.raises(ValueError):
        function([1.0, 2.0], np.zeros((2, 4)), np.array([1.0]))  # the four columns of the earlier versions of the feature, for the six defaults


# --- from the peaks and the notes of a file -----------------------------------------------------------------------------


def three_notes(frames=40):
    values = silent(frames)
    values[0:30, 40] = 1.0
    values[5:20, 45] = 1.0
    values[12:18, 50] = 1.0
    return values


def test_the_angles_are_six_columns_the_vote_rings_then_the_peak_rings():
    times = [0.5 * i for i in range(1, 9)]
    rates = [60.0] + [120.0] * 7  # the first peak has the default rate, the others 120 beats per minute
    peaks = hand_made_peaks(times, rates)
    values = three_notes(50)
    data = rhythm(peaks, 10, 50, values)
    assert data.angles.shape == (50, 6) and data.angles.dtype == np.float64 and data.frame_count == 50
    moments = (np.arange(50) + 0.5) / 10
    peak_times = [p.sample / 44100 for p in peaks.peaks]
    peak_rows = rc.peak_series(peak_times, [p.rate for p in peaks.peaks])
    assert np.allclose(data.angles[:, 4:], rc.circle_angles(peak_times, peak_rows, moments, PEAK_DEFAULTS), rtol=1e-12, atol=1e-12)
    starts = starts_of(values)  # the rows are the 60 ms analysis windows, not the frames
    raw = tv.leading_tempos(starts, rc.START_RESOLUTION, 20)[:, 0]  # the resolution of the starts: 40 ms; both meters, the last 2 starts (fifth round)
    vote_rows = tv.vote_series(starts, np.column_stack([tv.average_tempos(raw), raw]))
    assert np.allclose(data.angles[:, :4], rc.circle_angles(starts, vote_rows, moments, VOTE_DEFAULTS), rtol=1e-12, atol=1e-12)
    # once the peaks come every half second at 120 beats per minute the peak circle advances 2 turns a second: 0.2 turns a frame at 10 frames a second
    assert np.diff(data.angles[:, 4])[-5:] == pytest.approx([0.2] * 5, abs=1e-9)


def test_a_worked_example_of_the_vote_rings_two_starts_0_6_seconds_apart():
    # the rows are 60 ms windows: the starts are in windows 0 and 10, at 0.03 s and 0.63 s; the resolution is 40 ms, so 0.6 s gives 2
    # points to 100 only (a quarter note, within 20 ms; 96 and 104 are 25 and 23 ms off) and 1 point to 76 (a dotted quarter): the first (raw)
    # tempo is 100; before the second start it is the starting 120, so the average of the two is 110. The frames are 100 a second: 120 of them
    windows = silent(30)
    windows[0:3, 40] = 1.0
    windows[10:13, 45] = 1.0
    data = rhythm(no_peaks(), 100, 120, windows)
    angles = data.angles
    moments = (np.arange(120) + 0.5) / 100

    def slope(column, a, b):
        return (angles[b, column] - angles[a, column]) * 60.0 / (moments[b] - moments[a])  # revolutions per minute between two frames

    assert slope(0, 5, 55) == pytest.approx(120.0) and slope(2, 5, 55) == pytest.approx(120.0)  # before the second start: the starting tempo twice
    assert (angles[:63, [1, 3]] == 0.0).all()  # and no change
    assert slope(0, 70, 110) == pytest.approx(110.0) and slope(2, 70, 110) == pytest.approx(100.0)  # after it: the average (120 + 100) / 2 and the raw tempo
    assert slope(1, 70, 110) == pytest.approx((110 - 120) / 0.6) and slope(3, 70, 110) == pytest.approx((100 - 120) / 0.6)  # -16.7 and -33.3 revolutions per minute
    assert slope(4, 0, 110) == pytest.approx(60.0) and (angles[:, 5] == 0.0).all()  # the peak circles: no peaks, the defaults


def test_the_outer_circle_is_the_straight_average_of_the_last_five_raw_tempos_and_the_third_is_the_raw_tempo():
    rng = np.random.default_rng(21)
    windows = silent(600)  # 60 notes 7 to 12 windows (0.42 to 0.72 s) apart: the voted tempo changes from one start to the next
    row = 0
    for index, gap in enumerate(rng.integers(7, 13, 60)):
        windows[row : row + 3, 20 + index % 40] = 1.0
        row += int(gap)
        if row + 3 > 600:
            break
    data = rhythm(no_peaks(30), 10, 360, windows)
    starts = starts_of(windows)
    raw = tv.leading_tempos(starts, rc.START_RESOLUTION, 20)[:, 0].tolist()
    average = [sum(raw[max(0, i - 4) : i + 1]) / len(raw[max(0, i - 4) : i + 1]) for i in range(len(raw))]  # by hand: the mean of the latest 5 (fewer at the beginning)
    assert len(raw) > 20 and len(set(raw)) > 3 and average != raw  # the example does change tempo, and the average is not the raw tempo
    moments = (np.arange(360) + 0.5) / 10
    # the rows of the two layers after each start: the level and its change per second, by hand
    rows = [[average[i], (average[i] - average[i - 1]) / (starts[i] - starts[i - 1]) if i else 0.0, raw[i], (raw[i] - raw[i - 1]) / (starts[i] - starts[i - 1]) if i else 0.0] for i in range(len(raw))]
    assert np.allclose(data.angles[:, :4], rc.circle_angles(starts, rows, moments, VOTE_DEFAULTS), rtol=1e-12, atol=1e-9)


def test_the_tempo_circles_turn_between_76_and_144_beats_per_minute_or_at_the_starting_tempo():
    rng = np.random.default_rng(8)
    values = (rng.random((300, 88)) ** 6) * (rng.random((300, 88)) < 0.15)
    data = rhythm(no_peaks(30), 10, 300, values)
    for column in (0, 2):
        speed = np.diff(data.angles[:, column]) * 10 * 60  # revolutions per minute over a frame
        assert speed.min() >= 75.999 and speed.max() <= 144.001


def test_with_no_peaks_and_no_starts_every_circle_turns_at_the_defaults_and_the_rate_circles_stand_still():
    data = rhythm(no_peaks(), 10, 20, silent(20))
    for column, step in ((AVERAGE, 0.2), (RAW, 0.2), (PEAK, 0.1)):  # the default rates 120, 120 and 60: turns a frame at 10 frames a second
        assert np.diff(data.angles[:, column]) == pytest.approx([step] * 19)
    assert (data.angles[:, RATES] == 0.0).all()


def test_the_peak_rings_equal_the_two_inner_rings_of_the_four_ring_picture():
    if not OLD_ANGLES.exists():
        pytest.skip("specs/047-rhythm-note-voting/tools/old_peak_angles.npy is missing (made by old_peak_angles.py before the feature)")
    from importlib import util

    spec = util.spec_from_file_location("old_peak_angles", OLD_ANGLES.with_name("old_peak_angles.py"))
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)  # the module only defines the fixed peaks here; its main block does not run
    data = rhythm(module.fixed_peaks(), module.FRAME_RATE, module.FRAMES, silent(module.FRAMES))
    assert np.array_equal(data.angles[:, 4:6], np.load(OLD_ANGLES))


def test_no_frames_give_no_rows_and_a_bad_frame_rate_or_count_is_refused():
    peaks = hand_made_peaks([0.5, 1.0], [60.0, 120.0])
    assert rhythm(peaks, 10, 0, silent(0)).angles.shape == (0, 6)
    for bad in (0, -1, True, float("nan"), "10", None):
        with pytest.raises(ValueError):
            rhythm(peaks, bad, 5, silent(5))
    for bad in (-1, 2.5, True, "3", None):
        with pytest.raises(ValueError):
            rhythm(peaks, 10, bad, silent(5))


def test_note_strengths_of_the_wrong_size_or_a_vote_limit_that_is_not_allowed_are_refused():
    peaks = hand_made_peaks([0.5, 1.0], [60.0, 120.0])
    for bad in (np.zeros(5), np.zeros((5, 80)), np.full((5, 88), -1.0)):
        with pytest.raises(ValueError):
            rhythm(peaks, 10, 5, bad)
    for limit in (0, 101, 2.5, True, "20", None):
        with pytest.raises(ValueError):
            rhythm(peaks, 10, 5, silent(5), limit)


def test_channels_that_do_not_match_are_refused_and_the_extra_notes_setting_is_not_a_parameter():
    peaks = hand_made_peaks([0.5, 1.0], [60.0, 120.0])
    windows = three_notes(40)
    with pytest.raises(ValueError):
        rc.rhythm_angles(peaks, 10, 5, windows, np.zeros(2000, dtype=np.int16), np.zeros(1999, dtype=np.int16), 20)
    with pytest.raises(TypeError):
        rc.rhythm_angles(peaks, 10, 5, windows, *quiet(windows), 2, 20)  # the earlier signature, with the Extra notes before the limit


def test_the_starts_are_placed_on_the_waveform_not_left_at_the_middle_of_their_window():
    # real audio: a loud burst begins at 0.70 s and another at 1.30 s; the starts that the windows give are the middle of their window (0.69 s and 1.29 s), the ones placed on the waveform are on the bursts
    windows = silent(40)
    windows[11:20, 40] = 1.0
    windows[21:30, 45] = 1.0
    x = np.zeros(int(44100 * 2.5))
    for at in (0.70, 1.30):
        i = int(at * 44100)
        t = np.arange(8000) / 44100
        x[i : i + 8000] += 8000 * np.sin(2 * np.pi * 440 * t) * np.exp(-t * 9)
    channel = x.astype(np.int16)
    placed = no.onset_starts(windows, channel, channel, 44100)
    middle = starts_of(windows)
    assert placed.shape == middle.shape == (2,) and not np.allclose(placed, middle, atol=0.002)  # moved onto the burst
    data = rc.rhythm_angles(no_peaks(), 100, 250, windows, channel, channel, 20)
    raw = tv.leading_tempos(placed, rc.START_RESOLUTION, 20)[:, 0]
    rows = tv.vote_series(placed, np.column_stack([tv.average_tempos(raw), raw]))
    assert np.allclose(data.angles[:, :4], rc.circle_angles(placed, rows, (np.arange(250) + 0.5) / 100, VOTE_DEFAULTS), rtol=1e-12, atol=1e-12)


def test_a_different_vote_limit_changes_the_angles_of_a_file_whose_spacing_changes():
    # 30 notes 11 windows (0.66 s) apart, then 29 notes 6 windows (0.36 s) apart (found by trying spacings: the two limits then rank the tempos differently)
    windows = silent(30 * 11 + 29 * 6 + 10)
    row = 0
    for index in range(59):
        windows[row : row + 3, 20 + index % 40] = 1.0
        row += 11 if index < 29 else 6
    frames = int(windows.shape[0] * 0.06 * 100)  # 100 frames a second over the same time
    low = rhythm(no_peaks(40), 100, frames, windows, 2).angles
    high = rhythm(no_peaks(40), 100, frames, windows, 100).angles
    assert not np.array_equal(low[:, :4], high[:, :4])
    assert np.array_equal(low[:, 4:], high[:, 4:])  # the peak rings do not depend on the votes


def test_the_angles_do_not_depend_on_the_frame_rate():
    # the same windows and peaks at 10 and at 30 frames a second: frame 3f + 1 of the second is at the moment of frame f of the first,
    # (3f + 1.5) / 30 = (f + 0.5) / 10, so the two must have the same six angles there (the rate only chooses the moments)
    rng = np.random.default_rng(11)
    windows = (rng.random((200, 88)) ** 6) * (rng.random((200, 88)) < 0.15)
    peaks = hand_made_peaks([0.5 * i for i in range(1, 20)], [60.0 + 7 * (i % 5) for i in range(19)])
    slow = rhythm(peaks, 10, 100, windows).angles
    fast = rhythm(peaks, 30, 300, windows).angles
    assert np.allclose(fast[1::3], slow, rtol=1e-9, atol=1e-9)


def test_the_rhythm_data_checks_its_angles():
    assert rc.RhythmData(np.zeros((3, 6))).frame_count == 3
    rc.RhythmData(np.full((2, 6), 1234.5))  # large unwrapped angles are fine
    for bad in (np.zeros(6), np.zeros((3, 4)), np.zeros((3, 5)), np.zeros((3, 8)), np.full((2, 6), np.nan), np.full((2, 6), np.inf), np.zeros((2, 6, 1))):
        with pytest.raises(ValueError):
            rc._check_data(rc.RhythmData(bad))
