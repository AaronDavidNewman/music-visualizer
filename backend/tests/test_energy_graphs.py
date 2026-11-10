"""The numbers of the ``energy-graphs`` image type (feature 034): rank scores, quasi-decibels, the two running totals and the softmax.

Every expectation is worked out here with plain loops, not with the code under test.
"""

import math

import numpy as np
import pytest

from app.services.energy_graphs import EnergyGraphData, above_smallest, frame_energy, quasi_db, rank_scores, softmax_shares
from app.services.frame_rendering import frame_count
from app.services.note_analysis import NOTE_COUNT, AnalysisResult

SR = 100.0


def result_of(values, step=10):
    """An analysis result of the given (windows, 88) values, a window every ``step`` samples (a frame at 5 per second is 20 samples)."""
    values = np.asarray(values, dtype=np.float64)
    if values.shape[1] < NOTE_COUNT:
        values = np.hstack([values, np.zeros((values.shape[0], NOTE_COUNT - values.shape[1]))])
    return AnalysisResult(sample_rate=SR, window_size=10, frames=values, sample_count=int(round(values.shape[0] * step)), step=float(step))


def frames_of(result, rate=5):
    return frame_count(result.sample_count, SR, rate)


def energy(values, step=10, rate=5):
    result = result_of(values, step)
    return frame_energy(result, rate, frames_of(result, rate))


def oracle_scores(window):
    """84 for the loudest sounding note, 83 for the next, ...; 0 for a silent note; equal strengths: the lower note first."""
    order = sorted(range(84), key=lambda n: (-window[n], n))
    scores = [0] * 84
    for rank, note in enumerate(order):
        if window[note] > 0:
            scores[note] = 84 - rank
    return scores


def oracle_quasi_db(window, peak):
    """20 log10(amp) / (20 log10(peak)) for a sounding note, clamped at 0; 0 for a silent note and when the peak is 1 or less."""
    if peak <= 1:
        return [0.0] * 84
    return [max(0.0, 20 * math.log10(a) / (20 * math.log10(peak))) if a > 0 else 0.0 for a in window[:84]]


def window(**strengths):
    row = np.zeros(NOTE_COUNT)
    for note, value in strengths.items():
        row[int(note[1:])] = value
    return row


# --- rank scores -----------------------------------------------------------------------


def test_the_loudest_note_scores_84_the_next_83_and_so_on():
    scores = rank_scores(window(n10=3.0, n20=2.0, n30=1.0)[None, :])
    assert scores.shape == (1, 84) and scores.dtype == np.int64
    assert (scores[0, 10], scores[0, 20], scores[0, 30]) == (84, 83, 82)


def test_a_silent_note_scores_nothing_and_neither_do_the_notes_below_it_in_rank():
    scores = rank_scores(window(n5=1.0)[None, :])
    assert scores[0, 5] == 84 and scores.sum() == 84


def test_equal_strengths_go_to_the_lower_note():
    scores = rank_scores(window(n7=2.0, n3=2.0, n50=2.0)[None, :])
    assert (scores[0, 3], scores[0, 7], scores[0, 50]) == (84, 83, 82)


def test_fewer_than_84_sounding_notes_are_not_renumbered():
    row = np.zeros(NOTE_COUNT)
    row[:3] = [1.0, 2.0, 3.0]
    assert rank_scores(row[None, :])[0, :3].tolist() == [82, 83, 84]


def test_the_four_extra_columns_are_left_out():
    row = np.zeros(NOTE_COUNT)
    row[84:] = 9.0
    row[0] = 1.0
    assert rank_scores(row[None, :])[0].tolist() == [84] + [0] * 83


def test_a_silent_window_scores_nothing():
    assert rank_scores(np.zeros((2, NOTE_COUNT))).sum() == 0


def test_rank_scores_agree_with_the_oracle_on_random_windows_with_ties_and_zeros():
    rng = np.random.default_rng(11)
    values = rng.integers(0, 4, size=(60, NOTE_COUNT)).astype(float)  # many ties and many zeros
    got = rank_scores(values)
    for w in range(60):
        assert got[w].tolist() == oracle_scores(values[w])


def test_rank_scores_do_not_depend_on_the_chunk_size(monkeypatch):
    from app.services import energy_graphs

    rng = np.random.default_rng(2)
    values = rng.random((50, NOTE_COUNT))
    whole = rank_scores(values)
    monkeypatch.setattr(energy_graphs, "RANK_CHUNK", 7)
    assert np.array_equal(rank_scores(values), whole)


@pytest.mark.parametrize(
    "bad",
    [np.zeros(NOTE_COUNT), np.zeros((3, 83)), -np.ones((2, NOTE_COUNT)), np.full((2, NOTE_COUNT), np.nan), np.full((2, NOTE_COUNT), np.inf)],
)
def test_rank_scores_and_quasi_db_refuse_what_is_not_note_values(bad):
    with pytest.raises(ValueError):
        rank_scores(bad)
    with pytest.raises(ValueError):
        quasi_db(bad)


def test_rank_scores_do_not_change_their_input():
    values = np.random.default_rng(0).random((4, NOTE_COUNT))
    before = values.copy()
    rank_scores(values)
    quasi_db(values)
    assert np.array_equal(values, before)


# --- quasi-decibels ----------------------------------------------------------------------------


def test_the_loudest_note_of_the_file_adds_1_and_a_note_a_tenth_as_loud_adds_the_ratio_of_the_decibel_values():
    values = np.zeros((2, NOTE_COUNT))
    values[0, 5] = 1000.0
    values[1, 6] = 100.0  # 20 log10(100) / 20 log10(1000) = 40 / 60
    got = quasi_db(values)
    assert got.shape == (2, 84) and got.dtype == np.float64
    assert got[0, 5] == 1.0
    assert got[1, 6] == pytest.approx(40.0 / 60.0, rel=1e-12)


def test_quasi_db_agrees_with_the_oracle_on_random_windows():
    rng = np.random.default_rng(4)
    values = rng.random((40, NOTE_COUNT)) * 500
    values[rng.random(values.shape) < 0.4] = 0.0
    got = quasi_db(values)
    peak = values[:, :84].max()
    for w in range(40):
        assert got[w].tolist() == pytest.approx(oracle_quasi_db(values[w], peak), rel=1e-12, abs=1e-15)


def test_the_peak_is_the_largest_of_the_84_notes_not_of_the_four_extra_columns():
    values = np.zeros((1, NOTE_COUNT))
    values[0, 3] = 100.0
    values[0, 86] = 1e6  # not a piano note
    assert quasi_db(values)[0, 3] == 1.0


def test_a_silent_note_adds_nothing_and_an_amplitude_under_1_is_clamped_at_0():
    values = np.zeros((1, NOTE_COUNT))
    values[0, 0] = 1000.0
    values[0, 1] = 0.5  # 20 log10(0.5) is negative: clamped
    values[0, 2] = 1.0  # exactly 0 dB
    got = quasi_db(values)[0]
    assert got[1] == 0.0 and got[2] == 0.0 and got[3] == 0.0 and (got >= 0).all()


@pytest.mark.parametrize("loudest", [1.0, 0.9, 0.01])
def test_a_file_whose_loudest_amplitude_is_1_or_less_adds_nothing_at_all(loudest):
    values = np.zeros((2, NOTE_COUNT))
    values[0, 0] = loudest
    values[1, 7] = loudest / 2
    assert quasi_db(values).sum() == 0.0


def test_a_silent_file_adds_nothing():
    assert quasi_db(np.zeros((3, NOTE_COUNT))).sum() == 0.0


def test_a_given_peak_overrides_the_one_of_the_array():
    values = np.zeros((1, NOTE_COUNT))
    values[0, 0] = 100.0
    assert quasi_db(values, peak=10000.0)[0, 0] == pytest.approx(0.5, rel=1e-12)
    assert quasi_db(values, peak=1.0).sum() == 0.0
    for bad in (-1.0, float("nan"), True, "x"):
        with pytest.raises(ValueError):
            quasi_db(values, peak=bad)


# --- the running totals ----------------------------------------------------------------------------


def random_windows(count, seed=5):
    rng = np.random.default_rng(seed)
    values = rng.integers(0, 5, size=(count, NOTE_COUNT)).astype(float) * 40
    values[rng.random((count, NOTE_COUNT)) < 0.5] = 0.0
    return values


@pytest.mark.parametrize("step", [5, 20, 40])  # below, equal to and above the frame period (20 samples)
def test_the_last_frame_is_the_sum_over_all_windows_so_each_window_is_counted_once(step):
    values = random_windows(25)
    data = energy(values, step=step)
    ranks = np.zeros(84, dtype=np.int64)
    amplitudes = np.zeros(84)
    peak = values[:, :84].max()
    for w in range(25):
        ranks += oracle_scores(values[w])
        amplitudes += oracle_quasi_db(values[w], peak)
    assert data.histogram.shape == data.amplitude.shape == (data.frame_count, 84)
    assert data.histogram.dtype == np.int64 and data.amplitude.dtype == np.float64
    assert data.histogram[-1].tolist() == ranks.tolist()
    assert data.amplitude[-1].tolist() == pytest.approx(amplitudes.tolist(), rel=1e-12)


def test_each_frame_holds_the_windows_that_start_before_its_end():
    values = random_windows(12)
    data = energy(values, step=10)  # two windows to a frame
    ranks = np.zeros(84, dtype=np.int64)
    amplitudes = np.zeros(84)
    peak = values[:, :84].max()
    for i in range(data.frame_count):
        for w in (2 * i, 2 * i + 1):
            if w < 12:
                ranks += oracle_scores(values[w])
                amplitudes += oracle_quasi_db(values[w], peak)
        assert data.histogram[i].tolist() == ranks.tolist()
        assert data.amplitude[i].tolist() == pytest.approx(amplitudes.tolist(), rel=1e-12)


def test_the_peak_is_the_loudest_note_of_the_whole_file_even_when_it_comes_late():
    values = np.zeros((6, NOTE_COUNT))
    values[0, 4] = 100.0
    values[5, 9] = 10000.0  # the loudest, in the last window
    data = energy(values, step=20)
    assert data.amplitude[0, 4] == pytest.approx(20 * math.log10(100) / (20 * math.log10(10000)), rel=1e-12)  # 0.5, not 1


def test_a_frame_with_no_window_of_its_own_adds_nothing_to_either_total():
    values = random_windows(4)
    data = energy(values, step=40)  # a window every second frame
    for total in (data.histogram, data.amplitude):
        assert total[1].tolist() == total[0].tolist()
        assert total[3].tolist() == total[2].tolist()
    assert data.histogram[2].tolist() != data.histogram[1].tolist()


def test_a_total_never_shrinks_and_the_first_sound_is_the_first_growth():
    values = np.vstack([np.zeros((4, NOTE_COUNT)), random_windows(8)])
    data = energy(values, step=20)
    assert (np.diff(data.histogram, axis=0) >= 0).all() and (np.diff(data.amplitude, axis=0) >= -1e-12).all()
    assert data.histogram[:4].sum() == 0 and data.amplitude[:4].sum() == 0  # nothing before the first sound


def test_a_silent_file_gives_empty_totals_without_error():
    data = energy(np.zeros((5, NOTE_COUNT)))
    assert data.histogram.sum() == 0 and data.amplitude.sum() == 0


def test_a_loud_file_with_amplitudes_up_to_1_has_rank_points_but_no_amplitude_total():
    values = np.tile(window(n21=1.0, n28=0.5), (4, 1))
    data = energy(values, step=20)
    assert data.histogram[-1, 21] == 84 * 4 and data.amplitude.sum() == 0


def test_the_loudest_and_second_loudest_note_make_rank_totals_in_the_proportion_84_to_83():
    values = np.tile(window(n21=2000.0, n28=1000.0), (6, 1))
    data = energy(values, step=20)
    last = data.histogram[-1]
    assert last[21] == 84 * 6 and last[28] == 83 * 6 and last.sum() == last[21] + last[28]
    assert data.amplitude[-1, 21] == pytest.approx(6.0, rel=1e-12)
    assert data.amplitude[-1, 28] == pytest.approx(6 * math.log10(1000) / math.log10(2000), rel=1e-12)


def test_no_frames_gives_no_rows():
    data = frame_energy(result_of(np.zeros((0, NOTE_COUNT))), 5, 0)
    assert data.histogram.shape == (0, 84) and data.amplitude.shape == (0, 84) and data.frame_count == 0


def test_energy_graph_data_reports_its_frame_count():
    assert EnergyGraphData(np.zeros((3, 84), dtype=np.int64), np.zeros((3, 84))).frame_count == 3


# --- the softmax ------------------------------------------------------------------------------------


def oracle_softmax(row):
    largest = max(row)
    if largest <= 0:
        return [0.0] * len(row)
    x = [v / largest for v in row]
    total = sum(math.exp(v) for v in x)
    return [math.exp(v) / total for v in x]


def test_each_row_is_divided_by_its_largest_total_and_softmaxed():
    rng = np.random.default_rng(6)
    totals = rng.random((5, 84)) * np.array([[1], [10], [1000], [1e5], [3]])
    got = softmax_shares(totals)
    assert got.shape == (5, 84)
    for r in range(5):
        assert got[r].tolist() == pytest.approx(oracle_softmax(totals[r].tolist()), rel=1e-12)
        assert got[r].sum() == pytest.approx(1.0, rel=1e-12)


def test_the_size_of_the_totals_does_not_matter_only_their_proportions():
    totals = np.random.default_rng(1).random((1, 84))
    assert softmax_shares(totals * 1e6)[0].tolist() == pytest.approx(softmax_shares(totals)[0].tolist(), rel=1e-12)


def test_the_biggest_total_is_at_most_e_times_the_smallest_share_so_the_bars_keep_a_floor():
    totals = np.zeros((1, 84))
    totals[0, 3] = 5.0  # one note ever sounded
    got = softmax_shares(totals)[0]
    assert got[3] / got[0] == pytest.approx(math.e, rel=1e-12) and got[0] > 0


def test_a_row_with_no_total_has_nothing_to_show():
    assert softmax_shares(np.zeros((2, 84))).sum() == 0.0
    assert softmax_shares(np.zeros((0, 84))).shape == (0, 84)


def test_the_softmax_does_not_overflow_for_huge_totals_and_does_not_change_its_input():
    totals = np.full((1, 84), 1e300)
    before = totals.copy()
    assert np.isfinite(softmax_shares(totals)).all()
    assert np.array_equal(totals, before)


@pytest.mark.parametrize("bad", [np.zeros(84), -np.ones((1, 84)), np.full((1, 84), np.nan), np.full((1, 84), np.inf)])
def test_the_softmax_refuses_what_is_not_totals(bad):
    with pytest.raises(ValueError):
        softmax_shares(bad)


def test_real_analysis_the_totals_have_real_shapes_on_a_tone():
    from app.services.noise_floor import floor_analysis
    from app.services.note_analysis import NoteBinAnalyzer, analyze_channels

    sample_rate, window_size = 44100, 4096
    position = NoteBinAnalyzer(sample_rate, window_size).bin_indices[36]
    t = np.arange(sample_rate) / sample_rate
    audio = np.sin(2 * np.pi * position * sample_rate / window_size * t)
    result = floor_analysis(analyze_channels(audio, audio, sample_rate, window_size))
    data = frame_energy(result, 5, 5)
    assert data.histogram[-1].argmax() == 36 and data.amplitude[-1].argmax() == 36
    # the last partial window is zero padded and leaks into other notes, so only the tallest is certain; the tone adds at most 1 in a window, and nearly 1 in each of the 11 windows
    assert 10.5 < data.amplitude[-1, 36] <= result.window_count
    shares = softmax_shares(data.amplitude)
    assert shares[-1].argmax() == 36 and shares[-1].sum() == pytest.approx(1.0)


# --- the smallest value has height 0 ------------------------------------------------------------------


def test_the_smallest_value_of_each_row_is_taken_off_every_value_of_the_row():
    rows = np.array([[0.2, 0.5, 0.3, 0.9], [4.0, 1.0, 1.0, 2.5], [0.0, 0.0, 0.0, 0.0]])
    got = above_smallest(rows)
    assert got.shape == rows.shape
    assert got[0].tolist() == pytest.approx([0.0, 0.3, 0.1, 0.7], rel=1e-12, abs=1e-15)
    assert got[1].tolist() == pytest.approx([3.0, 0.0, 0.0, 1.5], rel=1e-12, abs=1e-15)
    assert got[2].tolist() == [0.0] * 4  # a row with no total stays empty
    assert (got.min(axis=1) == 0).all() and (got >= 0).all()


def test_a_row_of_equal_values_has_nothing_above_its_smallest():
    assert above_smallest(np.full((2, 84), 0.0119)).sum() == 0.0


def test_above_smallest_does_not_change_its_input_and_refuses_what_is_not_shares():
    rows = np.random.default_rng(3).random((3, 84))
    before = rows.copy()
    above_smallest(rows)
    assert np.array_equal(rows, before)
    for bad in (np.zeros(84), -np.ones((1, 84)), np.full((1, 84), np.nan)):
        with pytest.raises(ValueError):
            above_smallest(bad)
    assert above_smallest(np.zeros((0, 84))).shape == (0, 84)


def test_after_the_softmax_a_clear_winner_is_many_times_the_runner_up_once_the_smallest_is_taken_off():
    totals = np.zeros((1, 84))
    totals[0, 5], totals[0, 6] = 10.0, 4.0  # x = 1 and 0.4
    flat = softmax_shares(totals)[0]
    lifted = above_smallest(softmax_shares(totals))[0]
    assert flat[5] / flat[6] == pytest.approx(math.exp(0.6), rel=1e-12)  # the softmax alone: e^1 / e^0.4, under 2
    assert lifted[5] / lifted[6] == pytest.approx((math.e - 1) / (math.e**0.4 - 1), rel=1e-12)  # more than 3
    assert lifted[5] / lifted[6] > 3
