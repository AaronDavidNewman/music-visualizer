"""The windowed smoothing: ``( A[t] + s*A[t-1] + ... + s*A[t-w] ) / ( 1 + s*k )`` with ``k = min(t, w)``."""

import numpy as np
import pytest

from app.services.frame_rendering import (
    DEFAULT_SMOOTHING_WINDOW,
    MAX_SMOOTHING_WINDOW,
    MIN_SMOOTHING_WINDOW,
    smooth_frames,
)

WINDOW_MESSAGE = "The smoothing window must be a whole number from 1 to 20."


def reference(values, s, w):
    """The formula as a plain loop, written independently of the implementation."""
    values = np.asarray(values, dtype=float)
    out = np.zeros_like(values)
    for t in range(values.shape[0]):
        k = min(t, w)
        total = values[t].copy()
        for j in range(1, k + 1):
            total = total + s * values[t - j]
        out[t] = total / (1 + s * k)
    return out


def column(values):
    return np.asarray(values, dtype=float).reshape(-1, 1)


def test_constants():
    assert (MIN_SMOOTHING_WINDOW, MAX_SMOOTHING_WINDOW, DEFAULT_SMOOTHING_WINDOW) == (1, 20, 1)


def test_the_worked_example_from_the_spec():
    got = smooth_frames(column([8, 4, 2]), 0.5, 2).ravel()
    assert got.tolist() == pytest.approx([8.0, 8 / 1.5, 4.0], abs=1e-9)
    assert got[1] == pytest.approx(5.3333, abs=0.001)


@pytest.mark.parametrize("w, s", [(1, 0.5), (3, 0.8), (20, 0.8), (7, 0.1), (2, 0.3), (50 % 20 + 1, 0.6)])
def test_matches_the_reference_loop_for_random_data(w, s):
    values = np.random.default_rng(w * 7).uniform(0, 5, (30, 5))
    assert smooth_frames(values, s, w) == pytest.approx(reference(values, s, w), abs=1e-12, rel=1e-12)


def test_a_window_longer_than_the_file_uses_all_the_earlier_frames():
    values = np.random.default_rng(4).uniform(0, 5, (6, 3))
    assert smooth_frames(values, 0.5, 20) == pytest.approx(reference(values, 0.5, 20), abs=1e-12)


@pytest.mark.parametrize("w", [1, 2, 5, 20])
@pytest.mark.parametrize("s", [0.1, 0.5, 0.8])
def test_the_first_frame_is_unchanged_and_the_early_frames_divide_by_the_weights_used(w, s):
    values = column(np.arange(1, 31, dtype=float))
    got = smooth_frames(values, s, w).ravel()
    assert got[0] == 1.0
    for t in range(min(w, 4) + 1):
        k = min(t, w)
        expected = (values[t, 0] + s * sum(values[t - j, 0] for j in range(1, k + 1))) / (1 + s * k)
        assert got[t] == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("w", range(1, 21))
@pytest.mark.parametrize("s", [0.1, 0.5, 0.8])
def test_an_impulse_lasts_exactly_the_window_and_is_then_exactly_zero(w, s):
    impulse = np.zeros(w + 6 + 25)
    k = w + 3  # a full window of earlier frames
    impulse[k] = 1.0
    got = smooth_frames(column(impulse), s, w).ravel()
    assert (got[:k] == 0.0).all()
    assert got[k] == pytest.approx(1 / (1 + s * w), abs=1e-12)
    for t in range(k + 1, k + w + 1):
        assert got[t] == pytest.approx(s / (1 + s * w), abs=1e-12)
    assert (got[k + w + 1 :] == 0.0).all()  # exactly zero, not just small


def test_the_spec_example_of_an_impulse_with_window_three():
    impulse = np.zeros(12)
    impulse[5] = 1.0
    got = smooth_frames(column(impulse), 0.5, 3).ravel()
    assert got[5:9].tolist() == pytest.approx([0.4, 0.2, 0.2, 0.2])
    assert (got[9:] == 0.0).all()


@pytest.mark.parametrize("w", [1, 4, 20])
@pytest.mark.parametrize("s", [0.1, 0.5, 0.8])
def test_a_constant_value_stays_constant(w, s):
    got = smooth_frames(np.full((30, 4), 3.7), s, w)
    assert got == pytest.approx(3.7, abs=1e-12)


@pytest.mark.parametrize("w", [1, 3, 20])
def test_smoothing_zero_returns_an_equal_new_array_for_every_window(w):
    values = np.random.default_rng(5).uniform(0, 5, (10, 3))
    before = values.copy()
    got = smooth_frames(values, 0.0, w)
    assert (got == values).all()
    assert got is not values and not np.shares_memory(got, values)
    assert (values == before).all()


def test_the_input_is_never_modified():
    values = np.random.default_rng(6).uniform(0, 5, (12, 4))
    before = values.copy()
    smooth_frames(values, 0.7, 5)
    assert (values == before).all()


def test_only_earlier_frames_are_used():
    values = np.random.default_rng(7).uniform(0, 5, (25, 3))
    whole = smooth_frames(values, 0.6, 4)
    for n in (1, 5, 13, 24):
        assert (smooth_frames(values[:n], 0.6, 4) == whole[:n]).all()  # exactly equal, not just close


def test_earlier_frames_are_the_raw_values_not_earlier_results():
    # with an endless running average this series would never reach zero; here it is zero after the window
    values = column([1, 1, 1, 0, 0, 0, 0, 0, 0, 0])
    got = smooth_frames(values, 0.8, 2).ravel()
    assert (got[5:] == 0.0).all()  # the last raw value is at frame 2 and a window of 2 reaches frame 4
    assert got[2] > 0 and got[3] > 0 and got[4] > 0


def test_each_note_uses_only_its_own_history():
    a = np.random.default_rng(8).uniform(0, 5, (15, 4))
    b = a.copy()
    b[:, 2] = np.random.default_rng(9).uniform(0, 5, 15)
    out_a, out_b = smooth_frames(a, 0.5, 3), smooth_frames(b, 0.5, 3)
    for note in (0, 1, 3):
        assert (out_a[:, note] == out_b[:, note]).all()
    assert not (out_a[:, 2] == out_b[:, 2]).all()


def test_short_and_empty_inputs_work_and_keep_the_type():
    one = smooth_frames(np.array([[1.0, 2.0]]), 0.5, 3)
    assert one.tolist() == [[1.0, 2.0]]
    assert smooth_frames(np.zeros((0, 3)), 0.5, 3).shape == (0, 3)
    single_column = smooth_frames(column([1, 2, 3, 4]), 0.5, 2)
    assert single_column.shape == (4, 1) and single_column.dtype == np.float64
    assert smooth_frames(np.array([[1, 2], [3, 4]]), 0.5, 1).dtype == np.float64  # integer input


def test_a_larger_window_keeps_a_stopped_note_longer():
    values = column([0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

    def lasts(w):
        out = smooth_frames(values, 0.5, w).ravel()
        return int((out[5:] > 0).sum())

    assert [lasts(w) for w in (1, 2, 5, 10)] == [1, 2, 5, 10]


@pytest.mark.parametrize("bad", [-0.01, 0.81, 1, True, float("nan"), float("inf"), "0.5", None])
def test_smoothing_outside_zero_to_point_eight_is_still_refused(bad):
    with pytest.raises(ValueError, match="The smoothing must be a number from 0.0 to 0.8."):
        smooth_frames(np.ones((3, 2)), bad, 2)


@pytest.mark.parametrize("bad", [0, -1, 21, 100, 2.5, 3.0, True, "3", None, float("nan"), [3]])
def test_a_window_that_is_not_a_whole_number_from_one_to_twenty_is_refused(bad):
    with pytest.raises(ValueError) as error:
        smooth_frames(np.ones((3, 2)), 0.5, bad)
    assert str(error.value) == WINDOW_MESSAGE


@pytest.mark.parametrize("window", [1, 20, np.int64(5), np.int32(2)])
def test_the_limits_and_numpy_integers_are_accepted(window):
    assert smooth_frames(np.ones((3, 2)), 0.5, window).shape == (3, 2)


def test_the_window_is_checked_even_when_smoothing_is_zero():
    with pytest.raises(ValueError):
        smooth_frames(np.ones((3, 2)), 0.0, 21)
