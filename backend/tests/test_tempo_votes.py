"""Tests of ``tempo_votes`` (feature 047): the setting, the note starts, the fit of a note length to the 18 tempos, the votes, the
ranking and the circle series. Everything is checked with start times or note strengths alone, no audio."""

import numpy as np
import pytest

from app.services import tempo_votes as tv
from app.services.tempo_finder import START_TEMPO

# --- the setting and the constants -------------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", [1, 20, 100, 20.0, np.int64(7), np.float64(50.0)])
def test_a_vote_limit_from_1_to_100_is_accepted_as_an_int(value):
    got = tv.check_vote_limit(value)
    assert got == int(value) and type(got) is int


@pytest.mark.parametrize("value", [0, 101, 2.5, True, False, "20", None, float("nan"), float("inf"), -1, [20], b"20"])
def test_a_vote_limit_that_is_not_allowed_is_refused_with_the_message(value):
    with pytest.raises(ValueError) as caught:
        tv.check_vote_limit(value)
    assert str(caught.value) == "The vote limit must be a whole number from 1 to 100."


def test_the_tempos_are_the_18_metronome_markings_from_76_to_144():
    assert len(tv.TEMPOS) == 18
    assert tv.TEMPOS == tuple(range(76, 145, 4))
    assert 120 in tv.TEMPOS and all(t == 72 + 4 * n for n, t in enumerate(tv.TEMPOS, start=1))


def test_the_note_values_are_the_half_quarter_eighth_sixteenth_dotted_and_the_two_triplets():
    assert len(tv.NOTE_BEATS) == 10
    assert sorted(tv.NOTE_BEATS) == pytest.approx(sorted([2, 1, 1 / 2, 1 / 4, 3, 3 / 2, 3 / 4, 3 / 8, 1 / 3, 2 / 3]))
    assert tv.DEFAULT_VOTE_LIMIT == 40 and tv.NO_VOTES_TEMPO == START_TEMPO == 120.0  # 40 since the fifth round of feature 047 (it was 20)


def test_a_plain_note_gives_two_points_and_a_dotted_note_or_a_triplet_one():
    assert len(tv.NOTE_POINTS) == len(tv.NOTE_BEATS)
    for beats, points in zip(tv.NOTE_BEATS, tv.NOTE_POINTS):
        dotted = any(beats == pytest.approx(plain * 1.5) for plain in (2, 1, 1 / 2, 1 / 4))
        triplet = beats == pytest.approx(1 / 3) or beats == pytest.approx(2 / 3)
        assert points == (1 if dotted or triplet else 2), beats
    assert (tv.PLAIN_POINTS, tv.DOTTED_POINTS, tv.TRIPLET_POINTS) == (2, 1, 1)


# --- the fit of a note length to the tempos ---------------------------------------------------------------------------------


def fit_by_hand(length, resolution):
    """The tempos that a length fits, by a plain double loop of the rule of the spec (FR-006, inclusive)."""
    found = []
    for tempo in tv.TEMPOS:
        for beats in tv.NOTE_BEATS:
            by_tempo = abs(60 * beats / length - tempo) <= 2.0 + 1e-9
            by_length = abs(60 * beats / tempo - length) <= resolution / 2 + 1e-9
            if by_tempo or by_length:
                found.append(tempo)
                break
    return found


def fitting(length, resolution=0.0):
    row = tv.fitting_tempos([length], resolution)[0]
    return [t for t, fits in zip(tv.TEMPOS, row) if fits]


def test_fitting_tempos_is_a_boolean_matrix_with_a_row_for_each_length_and_a_column_for_each_tempo():
    got = tv.fitting_tempos([0.5, 0.25, 1.0], 0.0)
    assert got.shape == (3, 18) and got.dtype == np.bool_
    assert tv.fitting_tempos([], 0.0).shape == (0, 18)


def test_half_a_second_exactly_fits_80_88_92_and_120():
    # 120 as a quarter note, 80 as a triplet quarter (2/3 of a beat), 88 and 92 as a dotted eighth (3/4 of a beat) whose implied
    # tempo, 90, is exactly half a bin from both
    assert fitting(0.5) == [80, 88, 92, 120]


@pytest.mark.parametrize("length", [0.2, 0.208, 0.25, 0.3, 0.375, 0.4167, 0.5, 0.6667, 0.75, 0.8333, 1.0, 1.25, 1.5, 2.0, 3.0])
@pytest.mark.parametrize("resolution", [0.0, 0.03, 0.06])
def test_the_fit_matches_a_plain_double_loop_of_the_rule(length, resolution):
    assert fitting(length, resolution) == fit_by_hand(length, resolution)


def test_a_resolution_of_60_ms_makes_a_quarter_of_a_second_fit_sixteen_tempos():
    assert len(fitting(0.25, 0.06)) == 16
    assert len(fitting(0.5, 0.06)) == 8


def test_the_resolution_only_adds_tempos_to_those_of_the_half_bin():
    exact = fitting(0.25, 0.0)
    assert exact == [80, 88, 92, 120]  # the same four as 0.5 s: 0.25 s is half of it
    wide = fitting(0.25, 0.06)
    assert set(exact) < set(wide)


@pytest.mark.parametrize("length", [5.0, 0.01])
def test_a_length_that_is_no_note_of_any_tempo_fits_none(length):
    assert fitting(length, 0.0) == []


def test_each_length_has_its_own_row():
    got = tv.fitting_tempos([0.5, 5.0, 0.5], 0.0)
    assert got[0].tolist() == got[2].tolist() and got[1].sum() == 0 and got[0].sum() == 4


# --- the points a note length gives to the tempos ---------------------------------------------------------------------------


def points(length, resolution=0.0):
    return {t: int(p) for t, p in zip(tv.TEMPOS, tv.tempo_points([length], resolution)[0]) if p}


def test_a_length_of_a_quarter_note_at_92_gives_92_two_points_and_the_dotted_tempos_one():
    # 60 / 92 s is a quarter note at 92 (2 points) and a dotted quarter at 138, between the bins 136 and 140 (1 point each)
    got = points(60 / 92)
    assert got == {92: 2, 136: 1, 140: 1}


def test_half_as_long_gives_92_and_the_dotted_tempos_the_same_points():
    # an eighth note at 92 and a dotted eighth at 138; the triplet quarter (2/3 of a beat) adds 124 with one point
    got = points(30 / 92)
    assert got[92] == 2 and got[136] == 1 and got[140] == 1
    assert got == {92: 2, 124: 1, 136: 1, 140: 1}
    assert {t: p for t, p in points(60 / 92).items()} == {t: p for t, p in got.items() if t != 124}


def test_a_tempo_gets_the_most_its_note_values_give_and_not_their_sum():
    # 0.5 s at 120 is a quarter note (2 points), a dotted eighth (1) and a triplet quarter (1) once the resolution is wide
    assert points(0.5, 0.4)[120] == 2
    assert max(points(0.5, 0.4).values()) == 2


def test_points_are_0_1_or_2_one_row_for_each_length_and_a_column_for_each_tempo():
    got = tv.tempo_points([0.5, 0.25, 1.0, 5.0], 0.06)
    assert got.shape == (4, 18) and got.dtype.kind == "i" and set(np.unique(got)) <= {0, 1, 2}
    assert not got[3].any() and tv.tempo_points([], 0.0).shape == (0, 18)


@pytest.mark.parametrize("resolution", [0.0, 0.03, 0.06])
def test_the_tempos_with_points_are_the_tempos_that_fit(resolution):
    lengths = np.linspace(0.1, 2.5, 60)
    assert np.array_equal(tv.tempo_points(lengths, resolution) > 0, tv.fitting_tempos(lengths, resolution))


@pytest.mark.parametrize("lengths", [[0.0], [-0.5], [float("nan")], [[0.5]], "a", None])
def test_tempo_points_refuses_lengths_that_are_not_a_list_of_finite_numbers_above_0(lengths):
    with pytest.raises(ValueError):
        tv.tempo_points(lengths, 0.0)


@pytest.mark.parametrize("lengths", [[0.0], [-0.5], [float("nan")], [float("inf")], [[0.5]], "a", None])
def test_fitting_tempos_refuses_lengths_that_are_not_a_list_of_finite_numbers_above_0(lengths):
    with pytest.raises(ValueError):
        tv.fitting_tempos(lengths, 0.0)


@pytest.mark.parametrize("resolution", [-0.01, float("nan"), float("inf"), "x", None])
def test_fitting_tempos_refuses_a_resolution_that_is_not_a_finite_number_of_0_or_more(resolution):
    with pytest.raises(ValueError):
        tv.fitting_tempos([0.5], resolution)


# --- the votes --------------------------------------------------------------------------------------------------------------


def steady(spacing, count):
    return np.arange(count) * spacing


def test_votes_have_a_row_for_each_start_and_a_column_for_each_tempo():
    got = tv.vote_tempos(steady(0.5, 5), 0.0, 20)
    assert got.shape == (5, 18) and got.dtype.kind == "i"
    assert tv.vote_tempos([], 0.0, 20).shape == (0, 18)
    one = tv.vote_tempos([3.0], 0.0, 20)
    assert one.shape == (1, 18) and not one.any()  # the first start only begins the run


def test_the_first_cycle_gives_the_points_of_the_fitting_tempos_and_none_to_the_rest():
    row = tv.vote_tempos([0.0, 0.5], 0.0, 20)[1]
    # 120 as a quarter note (2 points); 80 as a triplet quarter and 88 and 92 as a dotted eighth (1 point each)
    assert {t: int(v) for t, v in zip(tv.TEMPOS, row) if v} == {80: 1, 88: 1, 92: 1, 120: 2}


def test_a_tempo_that_only_a_dotted_note_or_a_triplet_fits_never_gets_above_one_vote():
    votes = tv.vote_tempos(steady(0.5, 32), 0.0, 20)  # 1 point a cycle against the 1 vote taken a cycle
    for tempo in (80, 88, 92):
        assert (votes[1:, tv.TEMPOS.index(tempo)] == 1).all(), tempo
    assert votes[-1, tv.TEMPOS.index(120)] == 20  # the plain quarter note climbs to the limit


def test_a_steady_spacing_adds_one_vote_a_cycle_up_to_the_limit_and_stays_there():
    votes = tv.vote_tempos(steady(0.5, 32), 0.0, 20)
    column = tv.TEMPOS.index(120)
    for cycle in range(1, 32):
        assert votes[cycle, column] == min(cycle + 1, 20), cycle  # k + 1 after k cycles, 20 after 19
    assert votes[19, column] == 20 and (votes[19:, column] == 20).all()
    others = [i for i, t in enumerate(tv.TEMPOS) if t not in (80, 88, 92, 120)]
    assert not votes[:, others].any()


def test_a_smaller_limit_stops_the_votes_sooner():
    votes = tv.vote_tempos(steady(0.5, 20), 0.0, 5)
    column = tv.TEMPOS.index(120)
    assert votes[:, column].tolist()[:6] == [0, 2, 3, 4, 5, 5] and votes.max() == 5


def test_a_limit_of_1_puts_the_fitting_tempos_at_1_and_leaves_the_others_at_0():
    votes = tv.vote_tempos(steady(0.5, 6), 0.0, 1)
    assert set(np.unique(votes[1:])) == {0, 1} and votes[1:, tv.TEMPOS.index(120)].tolist() == [1] * 5


def test_a_tempo_that_stops_fitting_loses_one_vote_a_cycle_and_never_goes_below_0():
    first = steady(0.5, 11)  # 10 cycles of 0.5 s
    starts = np.concatenate([first, first[-1] + 0.4 * np.arange(1, 14)])  # then 13 cycles of 0.4 s
    votes = tv.vote_tempos(starts, 0.0, 20)
    column = tv.TEMPOS.index(120)  # a quarter note at 0.5 s: 2 points a cycle, so it climbs
    assert votes[10, column] == 11
    for step in range(1, 12):
        assert votes[10 + step, column] == 11 - step, step  # one a cycle
    assert (votes[21:, column] == 0).all() and votes.min() == 0
    for tempo in (76, 100, 112):  # the tempos of 0.4 s start to gain (76 as an eighth note, 100 and 112 as a triplet and a dotted note)
        assert votes[-1, tv.TEMPOS.index(tempo)] > 0


def test_a_tempo_gets_its_two_votes_once_however_many_note_values_fit():
    # at a resolution of 0.4 s the length 0.5 s fits 120 as a quarter, as a dotted eighth and as a triplet quarter at once
    row = tv.vote_tempos([0.0, 0.5], 0.4, 20)[1]
    assert row[tv.TEMPOS.index(120)] == 2
    assert row.max() == 2


@pytest.mark.parametrize("limit", [1, 7, 20, 100])
def test_every_vote_is_a_whole_number_from_0_to_the_limit_for_any_starts(limit):
    rng = np.random.default_rng(limit)
    for _ in range(10):
        starts = np.cumsum(rng.uniform(0.05, 1.5, size=int(rng.integers(1, 120))))
        votes = tv.vote_tempos(starts, float(rng.choice([0.0, 0.03, 0.06])), limit)
        assert votes.shape == (len(starts), 18) and votes.min() >= 0 and votes.max() <= limit
        assert votes.dtype.kind == "i" and not votes[0].any()


def test_the_voting_does_not_change_its_input_and_gives_the_same_result_twice():
    starts = np.cumsum(np.random.default_rng(3).uniform(0.1, 1.0, size=40))
    before = starts.copy()
    a, b = tv.vote_tempos(starts, 0.06, 20), tv.vote_tempos(starts, 0.06, 20)
    assert np.array_equal(starts, before) and np.array_equal(a, b)


@pytest.mark.parametrize("limit", [0, 101, 2.5, True, "20", None])
def test_vote_tempos_refuses_a_limit_that_is_not_allowed(limit):
    with pytest.raises(ValueError):
        tv.vote_tempos([0.0, 0.5], 0.0, limit)


@pytest.mark.parametrize("starts", [[0.5, 0.5], [1.0, 0.5], [float("nan"), 1.0], [[0.0, 0.5]], "ab", None])
def test_vote_tempos_refuses_starts_that_are_not_finite_and_strictly_increasing(starts):
    with pytest.raises(ValueError):
        tv.vote_tempos(starts, 0.0, 20)


@pytest.mark.parametrize("resolution", [-1.0, float("nan"), float("inf")])
def test_vote_tempos_refuses_a_resolution_that_is_not_allowed(resolution):
    with pytest.raises(ValueError):
        tv.vote_tempos([0.0, 0.5], resolution, 20)


# --- the ranking and the circle series --------------------------------------------------------------------------------------


def votes_table(*rows):
    votes = np.zeros((len(rows), 18), dtype=np.int64)
    for index, row in enumerate(rows):
        for tempo, count in row.items():
            votes[index, tv.TEMPOS.index(tempo)] = count
    return votes


def test_the_first_and_second_tempo_are_the_two_with_the_most_votes_and_ties_go_to_the_lower_tempo():
    got = tv.ranked_tempos(votes_table({}, {80: 3}, {76: 3, 80: 3}, {144: 5, 120: 4}, {100: 2, 92: 2, 140: 2}))
    assert got.shape == (5, 2)
    assert got.tolist() == [[120, 120], [80, 120], [76, 80], [144, 120], [92, 100]]


def test_a_place_without_votes_holds_120_and_so_does_120_itself_when_it_is_the_only_one_with_votes():
    assert tv.ranked_tempos(votes_table({120: 2})).tolist() == [[120, 120]]
    assert tv.ranked_tempos(votes_table({}, {88: 1})).tolist() == [[120, 120], [88, 120]]


def test_ranked_tempos_refuses_votes_that_are_not_a_table_of_18_whole_numbers():
    for bad in (np.zeros((3, 17)), np.zeros(18), np.full((2, 18), -1), np.full((2, 18), 0.5), np.full((2, 18), np.nan)):
        with pytest.raises(ValueError):
            tv.ranked_tempos(bad)


def test_the_series_has_the_levels_and_their_changes_per_second():
    starts = [0.0, 0.5, 1.0]
    ranked = [[120, 120], [124, 120], [124, 100]]
    got = tv.vote_series(starts, ranked)
    assert got.shape == (3, 4)
    assert got.tolist() == [[120, 0, 120, 0], [124, 8.0, 120, 0.0], [124, 0.0, 100, -40.0]]


def test_the_average_tempo_is_the_straight_mean_of_the_latest_five_and_of_all_there_are_at_the_beginning():
    tempos = [120, 100, 80, 144, 76, 90, 110, 130]
    got = tv.average_tempos(tempos)
    assert got.shape == (8,) and got.dtype == np.float64
    expected = [sum(tempos[max(0, i - 4) : i + 1]) / len(tempos[max(0, i - 4) : i + 1]) for i in range(8)]
    assert got.tolist() == pytest.approx(expected)
    assert got[0] == 120 and got[1] == 110 and got[4] == pytest.approx((120 + 100 + 80 + 144 + 76) / 5) and got[5] == pytest.approx((100 + 80 + 144 + 76 + 90) / 5)


def test_the_average_of_a_steady_tempo_is_that_tempo_and_a_tempo_is_forgotten_after_five_starts():
    assert tv.average_tempos([100] * 9).tolist() == [100.0] * 9
    got = tv.average_tempos([100] * 5 + [140] * 5)
    assert got[4] == 100 and got[5] == 108 and got[9] == 140  # 100, 100, 100, 100, 140 is 108; five 140s later the 100s are gone


def test_the_average_of_no_tempos_is_empty_and_the_input_is_not_changed():
    assert tv.average_tempos([]).shape == (0,)
    given = np.array([100.0, 90.0, 80.0])
    tv.average_tempos(given)
    assert given.tolist() == [100.0, 90.0, 80.0]


@pytest.mark.parametrize("bad", [np.zeros((3, 2)), [1.0, np.nan], [1.0, np.inf], "tempos", [[1.0]], None])
def test_average_tempos_refuses_anything_but_a_list_of_finite_numbers(bad):
    with pytest.raises(ValueError):
        tv.average_tempos(bad)


def test_the_series_of_no_starts_is_empty():
    assert tv.vote_series([], np.zeros((0, 2))).shape == (0, 4)


@pytest.mark.parametrize(
    "starts, ranked",
    [([0.0, 0.5], [[120, 120]]), ([0.0, 0.5], [[120, 120, 1], [1, 2, 3]]), ([0.5, 0.5], [[120, 120], [120, 120]]), ([0.0, 0.5], [[120, np.nan], [1, 2]])],
)
def test_vote_series_refuses_inputs_that_do_not_match(starts, ranked):
    with pytest.raises(ValueError):
        tv.vote_series(starts, ranked)



# --- the fifth round: beats divided in 3, the last 2 starts, the meter and the leading tempo --------------------------------


def column(tempo):
    return tv.TEMPOS.index(tempo)


def test_the_note_values_of_a_beat_divided_in_3_and_the_other_constants_of_the_fifth_round():
    assert tv.TRIPLE_NOTE_BEATS == pytest.approx((2.0, 1.0, 2 / 3, 1 / 3, 1 / 6, 0.5, 4 / 3, 3.0))
    assert tv.TRIPLE_NOTE_POINTS == (2, 2, 2, 2, 2, 1, 1, 1)
    assert tv.METERS == (2, 3) and tv.LOOKBACK == 2


def test_a_third_and_a_sixth_of_a_second_are_plain_notes_of_120_when_its_beat_is_divided_in_3_and_triplets_when_in_2():
    for length in (1 / 3, 1 / 6):
        assert tv.tempo_points([length], 0.0, meter=3)[0, column(120)] == 2  # a quarter and an eighth note of a dotted-quarter beat
        assert tv.tempo_points([length], 0.0, meter=2)[0, column(120)] == 1  # the two triplets
        assert tv.tempo_points([length], 0.0)[0, column(120)] == 1  # meter 2 unless said
    assert tv.tempo_points([0.25], 0.0, meter=3)[0, column(120)] == 1  # half a beat: a dotted eighth when the beat is divided in 3
    assert tv.tempo_points([0.25], 0.0, meter=2)[0, column(120)] == 2  # and a plain eighth when it is divided in 2
    assert tv.fitting_tempos([0.5], 0.0, meter=3).shape == (1, 18)


@pytest.mark.parametrize("meter", [1, 4, True, "2", None, 2.5])
def test_a_meter_that_is_not_2_or_3_is_refused(meter):
    with pytest.raises(ValueError):
        tv.tempo_points([0.5], 0.0, meter=meter)
    with pytest.raises(ValueError):
        tv.vote_tempos([0.0, 0.5], 0.0, 20, meter=meter)


def by_hand(starts, resolution, limit, meter, lookback):
    """The votes with a plain loop: at each start the best points of its time since each of the last ``lookback`` starts."""
    votes = [np.zeros(18, dtype=np.int64)]
    for i in range(1, len(starts)):
        lengths = [starts[i] - starts[i - back] for back in range(1, lookback + 1) if i - back >= 0]
        points = tv.tempo_points(lengths, resolution, meter).max(axis=0)
        now = np.maximum(votes[-1] - 1, 0)
        votes.append(np.where(points > 0, np.minimum(now + points, limit), now))
    return np.array(votes)


@pytest.mark.parametrize("meter", [2, 3])
@pytest.mark.parametrize("lookback", [1, 2, 3])
def test_a_start_votes_with_the_best_points_of_its_time_since_each_of_the_last_starts(meter, lookback):
    rng = np.random.default_rng(meter * 10 + lookback)
    starts = np.cumsum(rng.uniform(0.12, 0.8, 40))
    assert np.array_equal(tv.vote_tempos(starts, 0.04, 30, meter, lookback), by_hand(starts, 0.04, 30, meter, lookback))
    assert np.array_equal(tv.vote_tempos(starts, 0.04, 30), by_hand(starts, 0.04, 30, 2, 1))  # one start back and meter 2 unless said
    assert tv.vote_tempos(starts[:1], 0.04, 30, meter, lookback).shape == (1, 18) and tv.vote_tempos([], 0.04, 30, meter, lookback).shape == (0, 18)


def test_a_note_between_the_beats_does_not_hide_the_beat_when_the_last_2_starts_vote():
    beats = np.arange(24) * 0.5  # 120 beats per minute
    starts = np.sort(np.concatenate([beats, beats + 0.29]))  # a note 0.29 s after each beat: 0.29 and 0.21 s fit no note of 120
    one = tv.ranked_tempos(tv.vote_tempos(starts, 0.04, 40, 2, 1))[-1, 0]
    two = tv.ranked_tempos(tv.vote_tempos(starts, 0.04, 40, 2, 2))[-1, 0]
    assert abs(one - 120) > 4 and abs(two - 120) <= 4  # 0.5 s fits 116 and 120 alike (the tie goes to 116)


@pytest.mark.parametrize("lookback", [0, -1, 1.5, True, "2", None])
def test_a_lookback_that_is_not_a_whole_number_of_at_least_1_is_refused(lookback):
    with pytest.raises(ValueError):
        tv.vote_tempos([0.0, 0.5], 0.0, 20, 2, lookback)


def table(*rows):
    """Votes of the two meters from rows of ({tempo: votes} for 2, {tempo: votes} for 3)."""
    votes = np.zeros((len(rows), 2, 18), dtype=np.int64)
    for i, (two, three) in enumerate(rows):
        for place, given in enumerate((two, three)):
            for tempo, count in given.items():
                votes[i, place, column(tempo)] = count
    return votes


def test_the_meter_starts_as_2_and_the_tempo_as_120_until_there_is_a_vote():
    assert tv.meter_tempos(table(({}, {}), ({}, {}))).tolist() == [[120.0, 2.0], [120.0, 2.0]]
    assert tv.meter_tempos(np.zeros((0, 2, 18))).shape == (0, 2)


def test_the_meter_whose_best_tempo_has_more_votes_is_chosen_and_an_equal_best_keeps_the_meter():
    got = tv.meter_tempos(table(
        ({100: 5}, {132: 4}),  # 2 leads
        ({100: 5}, {132: 6}),  # 3 leads: its tempo
        ({100: 6}, {132: 6}),  # equal: the meter stays 3
        ({100: 7}, {132: 6}),  # 2 leads again
    ))
    assert got.tolist() == [[100.0, 2.0], [132.0, 3.0], [132.0, 3.0], [100.0, 2.0]]


def test_a_tie_keeps_the_tempo_before_when_it_is_one_of_the_best_else_the_lowest_of_them():
    got = tv.meter_tempos(table(
        ({104: 3}, {}),
        ({96: 4, 104: 4}, {}),  # 104 is one of the best: it stays (the ranking would give 96)
        ({96: 5, 112: 5}, {}),  # 104 is not: the lowest of the best
        ({}, {}),  # no vote: the tempo stays
    ))
    assert got[:, 0].tolist() == [104.0, 104.0, 96.0, 96.0]


def test_meter_tempos_refuses_votes_that_are_not_a_table_of_two_meters_of_18_whole_numbers():
    for bad in (np.zeros((3, 18)), np.zeros((3, 3, 18)), np.zeros((3, 2, 17)), np.full((3, 2, 18), -1), np.full((3, 2, 18), 0.5), np.full((3, 2, 18), np.nan)):
        with pytest.raises(ValueError):
            tv.meter_tempos(bad)


def test_the_leading_tempo_is_the_meter_choice_of_the_votes_of_both_meters_with_the_last_2_starts():
    rng = np.random.default_rng(5)
    starts = np.cumsum(rng.uniform(0.15, 0.7, 60))
    votes = np.stack([tv.vote_tempos(starts, 0.04, 40, meter, 2) for meter in (2, 3)], axis=1)
    got = tv.leading_tempos(starts, 0.04, 40)
    assert got.shape == (60, 2) and np.array_equal(got, tv.meter_tempos(votes))
    assert set(np.unique(got[:, 0])) <= set(tv.TEMPOS) | {120.0} and set(np.unique(got[:, 1])) <= {2.0, 3.0}


def test_a_dotted_quarter_then_a_quarter_and_an_eighth_at_120_is_read_with_the_beat_divided_in_3():
    starts = np.cumsum([0.0] + [0.5, 1 / 3, 1 / 6] * 8)  # 6/8 at 120: the beat is a dotted quarter, 0.5 s
    assert tv.leading_tempos(starts, 0.04, 40)[-1].tolist() == [120.0, 3.0]
    assert tv.ranked_tempos(tv.vote_tempos(starts, 0.04, 40, 2, 2))[-1, 0] == 88.0  # with the beat divided in 2 alone the quarter and eighth are an eighth and a sixteenth of 88
