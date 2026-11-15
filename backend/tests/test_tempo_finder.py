"""The tempo finder (feature 040) on peak times alone: the rule, the limits and the restarts.

The expected numbers are worked out by hand from the rule (see the comments), not computed by the code under test.
"""

import math

import numpy as np
import pytest

from app.services.tempo_finder import find_tempo

BAD_TIMES_MESSAGE = "The peak times must be a 1-D array of finite numbers in strictly increasing order."


def times_of(intervals):
    """The peak times (the first peak at 0) of a list of intervals between peaks, in seconds."""
    return np.concatenate([[0.0], np.cumsum(intervals)])


def steady(bpm, count):
    return times_of([60.0 / bpm] * (count - 1))


def test_no_peak_and_one_peak_keep_the_start_tempo():
    empty = find_tempo([])
    assert empty.tempos.shape == (0,)
    assert empty.restarts == 0
    one = find_tempo([3.5])
    assert one.tempos.tolist() == [120.0]  # the first peak has no interval, so no sample
    assert one.restarts == 0


def test_a_worked_sequence_with_both_branches_a_faster_tempo_and_a_sample_too_far_from_every_related_tempo():
    # intervals 0.5, 0.6, 0.4, 0.75 s are the samples 120, 100, 150, 80 beats per minute; the tempo starts at 120
    # peak 1: s = 120, the tempo itself; window [120]; no spread, so the minimum step 1; |120 - 120| <= 1: T = (120 + 120) / 2 = 120
    # peak 2: s = 100 (the ratios 1, 2, 1.5, 0.5, 2/3 give 100, 200, 150, 50, 66.7: 100 is the nearest to 120); window [120, 100], mean 110, standard
    #         deviation 10; |100 - 120| = 20 > 10: T = 120 - 10 = 110
    # peak 3: s = 150 stands for 100: the values 150, 300, 225, 75 and 100 are 0.31, 1.0, 0.72, 0.38 and 0.095 away in ratio from T = 110, so 100 (150 as one and a
    #         half times a tempo of 100, a FASTER tempo) is the nearest, and 0.095 is within the tolerance of 15 percent (ln 1.15 = 0.14); window [120, 100, 100],
    #         mean 320/3, deviations 40/3, -20/3, -20/3, variance (1600 + 400 + 400) / 27 = 800 / 9, deviation 9.43; |100 - 110| = 10 > 9.43: T = 110 - sqrt(800 / 9)
    # peak 4: s = 80 would stand for 120 (80 x 1.5, the nearest in ratio to T = 100.57: 0.177 away), but that is more than 15 percent (0.14) away, so it stands
    #         for itself, 80; window [120, 100, 100, 80], mean 100, deviations 20, 0, 0, -20, variance 800 / 4 = 200, deviation 14.14; |80 - 100.57| = 20.57 > 14.14:
    #         T = 100.57 - sqrt(200)
    track = find_tempo(times_of([0.5, 0.6, 0.4, 0.75]))
    low = 110.0 - math.sqrt(800.0 / 9.0)
    assert track.tempos.tolist() == pytest.approx([120.0, 120.0, 110.0, low, low - math.sqrt(200.0)], abs=1e-9)
    assert track.restarts == 0


def test_a_sample_at_half_the_tempo_is_taken_as_the_tempo():
    # an interval of 60 / 58 s is 58 bpm: 58, 116, 87 against T = 120, the nearest is 116 (ratio 2), so the sample stands for 116 and the
    # tempo moves toward 116 by the minimum step 1 (the window holds one sample, so there is no deviation)
    track = find_tempo(times_of([60.0 / 58.0]))
    assert track.tempos.tolist() == [120.0, pytest.approx(119.0)]


def test_the_ratio_picks_the_nearest_in_ratio_and_the_tempo_on_a_tie():
    # (the cases below are within the tolerance of 15 percent of a related tempo: a sample not near one stands for itself, see the next test)
    # T = 120 and s = 68.8: the values 68.8, 137.6 and 103.2. By absolute difference 103.2 is nearer (16.8 against 17.6); in ratio 137.6 is nearer
    # (ln 137.6/120 = 0.137 against ln 120/103.2 = 0.151). The rule is by ratio: the sample stands for 137.6 (within 15 percent of it) and the tempo goes up to 121
    # (by absolute difference it would go down to 119)
    assert find_tempo(times_of([60.0 / 68.8])).tempos[1] == pytest.approx(121.0)
    # on an exact tie of the distance the plain tempo wins: s = 120 gives 120, 240 and 180, the plain tempo is on the tempo and it does not move
    assert find_tempo(times_of([0.5])).tempos[1] == pytest.approx(120.0)


@pytest.mark.parametrize(
    "sample, tempo, stands_for",
    [
        (150.0, 120.0, 150.0),  # 1.5 x 120 = 180 is the nearest related tempo but 150 is 17 percent from it: it stands for itself
        (140.0, 120.0, 140.0),
        (210.0, 120.0, 105.0),  # half of 210 is 105, 0.134 away in ratio from 120: within 15 percent (2/3 x 210 = 140 is 0.154 away)
        (147.0, 120.0, 147.0),  # 98 (2/3 x 147) is 0.20 away and 147 itself 0.20: no related tempo is near, it stands for itself
        (205.0, 120.0, 205.0 * 2 / 3),  # 136.7 is 0.130 away in ratio from 120: within 15 percent, it stands for a tempo of 136.7
        (170.0, 120.0, 170.0 * 2 / 3),
        (62.0, 120.0, 124.0),  # twice 62 is 124, near 120
        (60.0, 120.0, 120.0),
        (77.0, 116.0, 115.5),  # 1.5 x 77 = 115.5, near 116
        (80.0, 100.57, 80.0),  # 1.5 x 80 = 120 is 0.177 away in ratio from 100.57: it stands for itself (the fourth peak of the worked sequence)
    ],
)
def test_a_sample_stands_for_a_related_tempo_only_when_it_is_within_15_percent_of_it_and_otherwise_for_itself(sample, tempo, stands_for):
    from app.services.tempo_finder import match_sample

    assert match_sample(sample, tempo) == pytest.approx(stands_for)


def test_steady_peaks_at_150_beats_per_minute_drift_up_to_150_and_not_down_to_100():
    track = find_tempo(steady(150, 40))
    assert track.tempos[:8].tolist() == pytest.approx([120.0 + k for k in range(8)])  # up, one step a peak
    assert track.tempos[-1] == pytest.approx(150.0) and track.restarts == 0


def test_the_minimum_step_moves_a_steady_sample_by_one_each_peak_and_never_past_it():
    # 0.6 s is 100 bpm, 100 every time: the window holds only 100s (deviation 0, so the step 1): 119, 118, ... 100, then it stays
    track = find_tempo(steady(100, 30))
    assert track.tempos[0] == 120.0
    assert track.tempos[1:21].tolist() == pytest.approx([120.0 - k for k in range(1, 21)])
    assert track.tempos[20:].tolist() == pytest.approx([100.0] * 10)  # never below 100


@pytest.mark.parametrize(
    "bpm, settles_at",
    [
        (100, 100.0),  # the tempo itself
        (116, 116.0),
        (58, 116.0),  # every second peak of 116: 58 stands for 116 (ratio 2)
        (50, 75.0),  # 50 is two thirds of 75 (it could as well be half of 100: the rule settles on the one it reaches first)
        (70, 105.0),  # 70 is two thirds of 105 and the rule cannot tell them apart: it settles there
        (150, 150.0),  # nothing near 100 is ever heard, so 150 is the tempo itself: 150 is not within 15 percent of 1.5 x 120 = 180
        (155, 155.0),
        (75, 112.5),  # every second peak of 150: 75 is two thirds of 112.5
    ],
)
def test_steady_peaks_settle_where_the_ratios_allow(bpm, settles_at):
    track = find_tempo(steady(bpm, 60))
    assert track.tempos[-1] == pytest.approx(settles_at)
    assert track.tempos[-10:].tolist() == pytest.approx([settles_at] * 10)  # a fixed point: it no longer changes
    assert track.restarts == 0


def scripted(monkeypatch, samples):
    """Make the matching hand out the given samples one by one (whatever the intervals), so the deviation can be put exactly where a test wants it."""
    from app.services import tempo_finder

    feed = iter(samples)
    monkeypatch.setattr(tempo_finder, "match_sample", lambda sample, tempo: next(feed))


def test_exactly_one_deviation_away_is_within_it(monkeypatch):
    # samples 122 then 120 on a tempo of 120: the first is 2 away (more than the step 1), so the tempo goes to 121; the window [122, 120] has mean 121 and
    # deviation exactly 1, and 120 is exactly 1 from 121: within (inclusive), so T = (120 + 121) / 2 = 120.5 (a move by one deviation would give 120)
    scripted(monkeypatch, [122.0, 120.0])
    track = find_tempo(times_of([0.5, 0.5]))
    assert track.tempos.tolist() == [120.0, 121.0, 120.5]


def test_the_latest_five_samples_are_kept_and_no_more_or_fewer(monkeypatch):
    # five samples of 100 bring the tempo to 115 (119, 118, 117, 116, 115: the deviation is 0, so the step 1); then a sample of 130 and a window of the
    # latest five, [100, 100, 100, 100, 130]: mean 106, deviation sqrt((4 x 36 + 576) / 5) = 12 exactly; the gap 15 is more than that: T = 115 + 12 = 127
    # (windows of 4 and of 6 would give deviations of 12.99 and 11.18)
    scripted(monkeypatch, [100.0] * 5 + [130.0])
    track = find_tempo(times_of([0.5] * 6))
    assert track.tempos.tolist() == pytest.approx([120.0, 119.0, 118.0, 117.0, 116.0, 115.0, 127.0])


def test_a_stray_peak_at_two_thirds_of_a_beat_moves_a_settled_tempo_by_less_than_ten_percent():
    beat = 60.0 / 116.0
    intervals = [beat] * 20 + [beat * 1.5] + [beat] * 5  # one late peak: a sample of 77.3 bpm, which is two thirds of 116
    track = find_tempo(times_of(intervals))
    settled = track.tempos[19]
    assert settled == pytest.approx(116.0)
    assert abs(track.tempos[20] - settled) < 0.1 * settled


def test_an_extra_peak_between_two_beats_is_a_sample_at_twice_the_tempo_and_does_not_move_it():
    # the version of the rule before the faster ratios restarted the tempo here (research D2): 232 bpm was far from the tempo, its half and its two thirds
    beat = 60.0 / 116.0
    intervals = [beat] * 20 + [beat / 2, beat / 2] + [beat] * 3  # an extra peak half way between two beats: two samples of 232 bpm
    track = find_tempo(times_of(intervals))
    assert track.tempos[21] == pytest.approx(116.0) and track.tempos[22] == pytest.approx(116.0)  # 232 x 0.5 = 116: the tempo itself
    assert track.restarts == 0


@pytest.mark.parametrize("bpm", [240, 180, 60, 80])
def test_samples_at_twice_the_tempo_at_one_and_a_half_times_it_and_at_half_and_two_thirds_of_it_all_stand_for_it(bpm):
    # the values for T = 120 are s, 2 s, 1.5 s, 0.5 s and 2/3 s: 240 x 0.5, 180 x 2/3, 60 x 2 and 80 x 1.5 are 120 on the dot, so the tempo does not move
    track = find_tempo(times_of([60.0 / bpm] * 10))  # 11 peaks
    assert track.tempos.tolist() == pytest.approx([120.0] * 11)


def test_above_156_the_tempo_becomes_78_and_the_samples_are_thrown_away(monkeypatch):
    # samples that stand for 200 (given as they are, whatever the matching): the tempo climbs 1 each peak from 120 (the deviation is 0, so the step 1),
    # 156 is not above 156, the next one is 157 > 156: 78
    scripted(monkeypatch, [200.0] * 40)
    track = find_tempo(times_of([0.3] * 40))
    assert track.tempos[0] == 120.0
    assert track.tempos[1:37].tolist() == pytest.approx([120.0 + k for k in range(1, 37)])
    assert track.tempos[36] == pytest.approx(156.0)
    assert track.tempos[37] == 78.0
    assert track.restarts >= 1


def test_after_a_restart_from_above_the_window_holds_only_the_new_samples(monkeypatch):
    # after the restart a sample of 90 is the only one in the window, so the deviation is the minimum step 1 and the tempo is 78 + 1 = 79 (with the old 200s
    # still in the window the deviation would be large)
    scripted(monkeypatch, [200.0] * 37 + [90.0])
    track = find_tempo(times_of([0.3] * 38))  # 39 peaks, 38 samples
    assert track.tempos[37] == 78.0
    assert track.tempos[38] == pytest.approx(79.0)


def test_below_60_the_tempo_becomes_120_and_the_samples_are_thrown_away():
    # 6 s is 10 bpm: 10, 20, 15 are all far below, the nearest (in ratio) is 20: it pulls the tempo down 1 each peak: 119 ... 60, then 59 < 60: 120
    track = find_tempo(times_of([6.0] * 61))
    assert track.tempos[1:61].tolist() == pytest.approx([120.0 - k for k in range(1, 61)])
    assert track.tempos[60] == pytest.approx(60.0)  # 60 is not below 60
    assert track.tempos[61] == 120.0
    assert track.restarts == 1
    # the window was emptied: the next sample is the only one in it
    after = find_tempo(times_of([6.0] * 61 + [0.5]))  # 120 bpm
    assert after.tempos[62] == pytest.approx(120.0)  # one sample of 120 on a tempo of 120: within the minimum step


def test_every_tempo_is_from_60_to_156_for_random_peaks():
    for seed in range(5):
        rng = np.random.default_rng(seed)
        intervals = rng.uniform(0.05, 6.0, size=2000)
        track = find_tempo(times_of(intervals))
        assert track.tempos.shape == (2001,)
        assert (track.tempos >= 60.0).all() and (track.tempos <= 156.0).all()


def test_the_result_is_the_same_on_two_runs_and_the_input_is_not_changed():
    rng = np.random.default_rng(7)
    times = times_of(rng.uniform(0.2, 2.0, size=300))
    before = times.copy()
    a, b = find_tempo(times), find_tempo(times)
    assert a.tempos.tolist() == b.tempos.tolist() and a.restarts == b.restarts
    assert (times == before).all()


@pytest.mark.parametrize(
    "bad",
    [
        [[0.0, 1.0], [2.0, 3.0]],  # not 1-D
        [0.0, float("nan")],
        [0.0, float("inf")],
        [0.0, 1.0, 1.0],  # not strictly increasing
        [0.0, 2.0, 1.0],
        ["a", "b"],
        None,
    ],
)
def test_peak_times_that_are_not_a_strictly_increasing_list_of_numbers_are_refused(bad):
    with pytest.raises(ValueError, match=BAD_TIMES_MESSAGE):
        find_tempo(bad)
