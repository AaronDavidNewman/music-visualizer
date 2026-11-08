"""The noise floor: a note more than 60 dB (a factor of 1,000 in strength) below the loudest note of the file is 0 (feature 033).

The checks use an independent oracle written here: a loop over the values with the ratio written out as ``0.001``, not the constants of the module.
"""

import numpy as np
import pytest

from app.services.note_analysis import AnalysisResult
from app.services.noise_floor import NOISE_FLOOR, NOISE_FLOOR_DB, apply_noise_floor, floor_analysis

VALUES_MESSAGE = "The note values must be finite numbers that are not negative."
PEAK_MESSAGE = "The peak must be a finite number that is not negative."


def oracle_cut(values, peak=None):
    """Every value strictly below a thousandth of the peak (the largest value anywhere, unless given) is 0; the rest is kept."""
    array = np.asarray(values, dtype=np.float64)
    flat = array.ravel().tolist()
    top = peak if peak is not None else (max(flat) if flat else 0.0)
    return np.array([0.0 if v < top * 0.001 else v for v in flat]).reshape(array.shape)


# ---- the constants -------------------------------------------------------------------------------------------------------------------------


def test_the_level_is_minus_60_db_which_is_a_factor_of_1000_in_strength():
    assert NOISE_FLOOR_DB == -60
    assert NOISE_FLOOR == 0.001
    assert NOISE_FLOOR == 10 ** (-60 / 20)  # 20 log10 of an amplitude ratio


# ---- the cut: the examples -------------------------------------------------------------------------------------------------------------


def test_the_examples_of_the_contract_with_a_loudest_value_of_1():
    result = apply_noise_floor(np.array([[1.0, 0.001, 0.00099999, 0.0, 0.5]]))
    assert result.tolist() == [[1.0, 0.001, 0.0, 0.0, 0.5]]  # exactly at the floor counts, just below is exactly 0


def test_the_cut_values_are_exactly_zero_and_the_kept_values_are_the_very_same_numbers():
    values = np.array([[1.0, 0.3, 0.0005, 0.123456789, 1e-9, 0.002]])
    result = apply_noise_floor(values)
    assert result[0, 2] == 0.0 and result[0, 4] == 0.0 and not np.signbit(result[0, 2])
    assert result[0, [0, 1, 3, 5]].tolist() == values[0, [0, 1, 3, 5]].tolist()


def test_the_reference_is_the_largest_value_anywhere_in_the_array_not_in_the_window():
    values = np.array([[0.5, 0.004, 0.0004], [0.0005, 0.0, 1.0]])  # the loudest value (1.0) is in the second window
    assert apply_noise_floor(values).tolist() == [[0.5, 0.004, 0.0], [0.0, 0.0, 1.0]]  # 0.0005 is under a thousandth of 1.0 although it is the loudest note of its window


def test_the_four_undrawn_notes_count_for_the_loudest_value():
    values = np.zeros((2, 88))
    values[0, 10] = 0.0009
    values[1, 87] = 1.0  # one of the four notes above the 84 piano notes
    assert apply_noise_floor(values)[0, 10] == 0.0
    values[1, 87] = 0.5
    assert apply_noise_floor(values)[0, 10] == 0.0009  # 0.0009 is above a thousandth of 0.5


def test_a_note_is_judged_in_its_own_window_so_the_same_note_can_be_kept_in_one_and_cut_in_another():
    values = np.array([[1.0, 0.01], [1.0, 0.0001]])
    assert apply_noise_floor(values)[:, 1].tolist() == [0.01, 0.0]


# ---- the cut: the peak ---------------------------------------------------------------------------------------------------------------------


def test_a_peak_that_is_given_replaces_the_largest_value_of_the_array():
    values = np.array([[0.5, 0.0005, 0.0000001]])
    assert apply_noise_floor(values, peak=10.0).tolist() == [[0.5, 0.0, 0.0]]
    assert apply_noise_floor(values, peak=0.0).tolist() == values.tolist()  # no peak, no cut
    assert apply_noise_floor(values, peak=0).tolist() == values.tolist()
    assert apply_noise_floor(values, peak=np.float64(1.0)).tolist() == [[0.5, 0.0, 0.0]]


# ---- the cut: shapes, silence, types --------------------------------------------------------------------------------------------------------


def test_silence_and_empty_arrays_come_back_unchanged():
    assert apply_noise_floor(np.zeros((3, 88))).tolist() == np.zeros((3, 88)).tolist()
    for shape in ((0, 88), (0,), (3, 0)):
        result = apply_noise_floor(np.zeros(shape))
        assert result.shape == shape and result.dtype == np.float64


@pytest.mark.parametrize("shape", [(5,), (4, 88), (2, 3, 4)])
def test_arrays_of_any_shape_keep_their_shape(shape):
    rng = np.random.default_rng(1)
    values = rng.random(shape) ** 8
    result = apply_noise_floor(values)
    assert result.shape == shape and result.dtype == np.float64
    np.testing.assert_array_equal(result, oracle_cut(values))


def test_integers_and_lists_are_accepted_and_come_back_as_floats():
    result = apply_noise_floor(np.array([[5000, 4, 5, 0]], dtype=np.int64))
    assert result.dtype == np.float64 and result.tolist() == [[5000.0, 0.0, 5.0, 0.0]]  # 4 is under a thousandth of 5000, 5 is exactly at it
    assert apply_noise_floor([[1.0, 0.0001]]).tolist() == [[1.0, 0.0]]
    assert apply_noise_floor(np.array([[1.0, 0.0001]], dtype=np.float32)).tolist() == [[1.0, 0.0]]


def test_the_input_is_not_changed_and_the_result_does_not_share_memory_with_it():
    values = np.array([[1.0, 0.0001, 0.5]])
    before = values.copy()
    result = apply_noise_floor(values)
    np.testing.assert_array_equal(values, before)
    assert not np.shares_memory(values, result)
    assert apply_noise_floor(np.array([[1.0, 0.5]])).flags.writeable  # with nothing to cut it is still a copy that can be written


# ---- the cut: properties and the oracle ----------------------------------------------------------------------------------------------------


def test_the_cut_is_idempotent_never_makes_a_value_and_never_cuts_a_louder_note_than_one_it_keeps():
    rng = np.random.default_rng(2)
    for _ in range(100):
        values = rng.random((int(rng.integers(1, 20)), 88)) ** int(rng.integers(1, 12))
        values[rng.random(values.shape) < 0.3] = 0.0
        once = apply_noise_floor(values)
        np.testing.assert_array_equal(apply_noise_floor(once), once)
        assert (once <= values).all() and ((once == values) | (once == 0.0)).all()
        kept, cut = values[once > 0], values[(once == 0) & (values > 0)]
        if kept.size and cut.size:
            assert cut.max() < kept.min()  # the louder is never cut when the quieter is kept


def test_random_arrays_and_random_peaks_give_what_the_oracle_gives():
    rng = np.random.default_rng(3)
    for _ in range(300):
        values = rng.random((int(rng.integers(1, 12)), int(rng.integers(1, 90)))) ** float(rng.integers(1, 10))
        values[rng.random(values.shape) < 0.2] = 0.0
        peak = None if rng.random() < 0.5 else float(rng.random() * 3)
        np.testing.assert_array_equal(apply_noise_floor(values, peak=peak), oracle_cut(values, peak))


def test_values_at_exactly_the_floor_of_exactly_representable_peaks_are_kept_and_the_next_lower_one_is_cut():
    for peak in (1.0, 2.0, 0.5, 4.0, 1024.0):
        floor = peak * 0.001
        values = np.array([[peak, floor, np.nextafter(floor, 0.0), np.nextafter(floor, 2 * peak)]])
        assert apply_noise_floor(values).tolist() == [[peak, floor, 0.0, values[0, 3]]], peak


def test_two_calls_give_equal_results():
    values = np.random.default_rng(4).random((6, 88)) ** 6
    np.testing.assert_array_equal(apply_noise_floor(values), apply_noise_floor(values.copy()))


# ---- the cut: bad input ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [np.array([[1.0, np.nan]]), np.array([[1.0, np.inf]]), np.array([[1.0, -0.1]]), [["a", "b"]], None, "text", [[1.0, None]]])
def test_values_that_are_not_finite_numbers_that_are_not_negative_are_refused(bad):
    with pytest.raises(ValueError) as error:
        apply_noise_floor(bad)
    assert str(error.value) == VALUES_MESSAGE


@pytest.mark.parametrize("bad", [-1.0, float("nan"), float("inf"), float("-inf"), "1", True, False, [1.0], np.array([1.0])])
def test_a_peak_that_is_not_a_finite_number_that_is_not_negative_is_refused(bad):
    with pytest.raises(ValueError) as error:
        apply_noise_floor(np.array([[1.0, 0.5]]), peak=bad)
    assert str(error.value) == PEAK_MESSAGE


# ---- the analysis result --------------------------------------------------------------------------------------------------------------------


def test_floor_analysis_cuts_the_frames_of_a_result_and_keeps_everything_else():
    frames = np.zeros((3, 88))
    frames[0, 5] = 1.0
    frames[1, 6] = 0.0009  # a thousandth of 1.0 is 0.001
    frames[2, 7] = 0.0011
    frames[2, 87] = 0.5  # undrawn, and not the loudest
    starts = np.array([0, 4096, 8192])
    result = AnalysisResult(44100.0, 4096, frames, 12000, starts, 4096.0)
    before = frames.copy()
    floored = floor_analysis(result)
    assert floored is not result
    assert floored.frames[0, 5] == 1.0 and floored.frames[1, 6] == 0.0 and floored.frames[2, 7] == 0.0011 and floored.frames[2, 87] == 0.5
    assert (floored.sample_rate, floored.window_size, floored.sample_count, floored.step) == (44100.0, 4096, 12000, 4096.0)
    assert floored.starts is starts and floored.window_count == 3
    np.testing.assert_array_equal(result.frames, before)  # the result that was given is not changed
    np.testing.assert_array_equal(floored.frames, apply_noise_floor(frames))


def test_floor_analysis_of_a_result_without_starts_or_step_and_of_a_silent_one():
    result = AnalysisResult(44100.0, 4096, np.zeros((2, 88)))
    floored = floor_analysis(result)
    assert floored.starts is None and floored.step is None and floored.sample_count == 0
    np.testing.assert_array_equal(floored.frames, result.frames)
    assert floor_analysis(AnalysisResult(44100.0, 4096, np.zeros((0, 88)))).frames.shape == (0, 88)
