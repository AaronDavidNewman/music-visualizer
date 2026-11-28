"""The starts of the notes of Rhythm Circles (feature 047, fourth round): the rise of the note strengths, its peaks and the waveform refinement.

Every function is tested on small arrays made by hand (the rises, the peaks) or on short synthetic audio (the refinement and the whole path through the analysis), with no sample file.
"""

import numpy as np
import pytest

from app.services import note_onsets as no
from app.services.buffer_interval import buffer_step
from app.services.noise_floor import floor_analysis
from app.services.note_analysis import analyze_channels

WINDOW = 0.06  # seconds from one analysis window to the next
RATE = 44100


def silent(windows):
    return np.zeros((windows, 88))


def time_of(window):
    return (window + 0.5) * WINDOW


# --- the rise of each window ------------------------------------------------------------------------------------------------


def test_silence_does_not_rise_and_the_rises_have_one_entry_for_each_window():
    rises = no.onset_rises(silent(12))
    assert rises.shape == (12,) and rises.dtype == np.float64 and (rises == 0).all()
    assert no.onset_rises(silent(0)).shape == (0,)


def test_everything_that_sounds_in_the_first_window_is_a_rise():
    values = silent(4)
    values[0, [10, 40]] = [2.0, 0.5]
    assert no.onset_rises(values).tolist() == [2.5, 0.0, 0.0, 0.0]


def test_a_note_rises_when_it_begins_and_not_while_it_is_sustained_or_dies_away():
    values = silent(8)
    values[2:, 30] = [1.0, 1.0, 1.0, 0.8, 0.5, 0.2]  # begins in window 2, holds, then dies away
    assert no.onset_rises(values).tolist() == [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def test_a_rise_is_the_amount_above_the_larger_of_the_two_windows_before():
    values = silent(6)
    values[:, 20] = [0.0, 1.0, 0.0, 1.0, 3.0, 0.0]
    # window 1: 1 above 0; window 2: 0; window 3: 1 against max(0, 1) = 1 -> no rise (it was loud two windows ago); window 4: 3 against max(1, 0) = 1 -> 2
    assert no.onset_rises(values).tolist() == [0.0, 1.0, 0.0, 0.0, 2.0, 0.0]


def test_the_rises_of_the_notes_of_a_window_are_added_and_only_the_84_notes_count():
    values = silent(4)
    values[1, [5, 30, 60]] = [1.0, 2.0, 4.0]
    values[2, 84:] = 9.0  # the four columns after the 84 notes are not notes
    assert no.onset_rises(values).tolist() == [0.0, 7.0, 0.0, 0.0]


def test_one_window_is_enough_and_the_input_is_not_changed():
    values = silent(1)
    values[0, 3] = 1.5
    before = values.copy()
    assert no.onset_rises(values).tolist() == [1.5]
    assert np.array_equal(values, before)


@pytest.mark.parametrize("values", [np.zeros(88), np.zeros((5, 80)), np.zeros((2, 5, 88)), np.full((5, 88), -1.0), np.full((5, 88), np.nan), "abc", None])
def test_onset_rises_refuses_values_that_are_not_note_strengths(values):
    with pytest.raises(ValueError):
        no.onset_rises(values)


# --- the peaks of the rise ------------------------------------------------------------------------------------------------------


def peaks_of(rises):
    return no.pick_onsets(np.asarray(rises, dtype=float))


def test_a_peak_is_a_start_at_the_middle_of_its_window_and_the_starts_are_in_order():
    rises = np.zeros(40)
    rises[[5, 14, 30]] = [1.0, 2.0, 1.5]
    got = peaks_of(rises)
    assert got.dtype == np.float64 and got.tolist() == pytest.approx([time_of(5), time_of(14), time_of(30)])
    assert (np.diff(got) > 0).all()


def test_nothing_rising_has_no_start_and_an_empty_input_has_none():
    assert peaks_of(np.zeros(30)).shape == (0,)
    assert peaks_of([]).shape == (0,)


def test_a_small_rise_next_to_a_big_one_is_not_a_start_but_a_fifth_of_it_is():
    rises = np.zeros(30)
    rises[5] = 10.0
    rises[12] = 1.99  # just under a fifth of the largest within 2 s
    rises[20] = 2.0  # exactly a fifth: allowed
    assert peaks_of(rises).tolist() == pytest.approx([time_of(5), time_of(20)])


def test_a_quiet_passage_keeps_its_starts_when_the_loud_one_is_more_than_two_seconds_away():
    rises = np.zeros(200)
    rises[5] = 10.0
    rises[5 + no.LOCAL_WINDOWS + 1] = 0.5  # 34 windows away: the loud one is out of reach, so 0.5 is the largest nearby
    rises[5 + 10] = 0.5  # 10 windows from the loud one: under a fifth of 10
    assert peaks_of(rises).tolist() == pytest.approx([time_of(5), time_of(5 + no.LOCAL_WINDOWS + 1)])


def test_a_note_that_rises_over_two_windows_is_one_start_at_the_larger_rise():
    assert peaks_of([0, 0, 1.0, 3.0, 0, 0, 0]).tolist() == pytest.approx([time_of(3)])
    assert peaks_of([0, 0, 3.0, 1.0, 0, 0, 0]).tolist() == pytest.approx([time_of(2)])


def test_two_equal_rises_in_neighbouring_windows_are_one_start_the_earlier():
    assert peaks_of([0, 0, 1.0, 1.0, 0, 0, 0]).tolist() == pytest.approx([time_of(2)])


def test_two_peaks_less_than_the_neighbourhood_apart_leave_the_larger_and_three_windows_apart_both_stay():
    assert peaks_of([0, 0, 0, 1.0, 0, 2.0, 0, 0, 0]).tolist() == pytest.approx([time_of(5)])  # two windows apart: the smaller is not the largest within 2
    assert peaks_of([0, 0, 0, 1.0, 0, 0, 2.0, 0, 0, 0]).tolist() == pytest.approx([time_of(3), time_of(6)])  # three apart: both


def test_the_two_equal_peaks_of_the_minimum_gap_both_stay():
    assert peaks_of([0, 0, 0, 1.0, 0, 1.0, 0, 0, 0]).tolist() == pytest.approx([time_of(3), time_of(5)])  # 120 ms apart, not less than the minimum gap


def test_picking_does_not_change_its_input_and_is_the_same_twice():
    rises = np.random.default_rng(3).random(200) ** 4
    before = rises.copy()
    a, b = no.pick_onsets(rises), no.pick_onsets(rises)
    assert np.array_equal(rises, before) and np.array_equal(a, b) and (np.diff(a) > 0).all()


@pytest.mark.parametrize("rises", [np.zeros((3, 2)), [1.0, np.nan], [1.0, np.inf], [1.0, -1.0], "abc", None])
def test_pick_onsets_refuses_rises_that_are_not_a_list_of_finite_numbers_from_zero(rises):
    with pytest.raises(ValueError):
        no.pick_onsets(rises)


# --- placing the starts on the waveform -------------------------------------------------------------------------------------


def burst_at(*begins, length=3.0, dtype=np.int16):
    """Silence of ``length`` seconds with a loud 440 Hz burst that begins at each of ``begins`` seconds: left and right the same."""
    x = np.zeros(int(length * RATE))
    for at in begins:
        i = int(round(at * RATE))
        m = int(0.3 * RATE)
        x[i : i + m] += 8000 * np.sin(2 * np.pi * 440 * np.arange(m) / RATE) * np.exp(-np.arange(m) / RATE * 8)
    return x.astype(dtype), x.astype(dtype)


def test_a_start_moves_to_where_the_waveform_rises_whether_it_was_early_or_late():
    left, right = burst_at(1.0)
    for guess in (0.96, 0.99, 1.0, 1.05, 1.09):  # the burst is from 0.10 s after the guess to 0.05 s before it
        got = no.refine_starts([guess], left, right, RATE)
        assert got.shape == (1,) and abs(got[0] - 1.0) < 0.012


def test_a_start_with_no_rise_near_it_stays_where_it_is_and_so_does_one_after_the_end_of_the_file():
    silence = np.zeros(RATE * 2, dtype=np.int16)
    assert no.refine_starts([0.5, 1.0], silence, silence, RATE).tolist() == [0.5, 1.0]
    left, right = burst_at(1.0, length=1.5)
    assert no.refine_starts([5.0], left, right, RATE).tolist() == [5.0]  # no frame of the file lies there


def test_a_start_at_the_very_beginning_is_refined_without_looking_before_the_file():
    left, right = burst_at(0.01, length=1.0)
    got = no.refine_starts([0.02], left, right, RATE)
    assert got.shape == (1,) and 0.0 <= got[0] < 0.04


def test_starts_refined_to_the_same_moment_are_one_start_and_the_times_stay_in_order():
    left, right = burst_at(1.0)
    got = no.refine_starts([0.96, 0.99, 1.02], left, right, RATE)  # all within the search of the burst: all find it
    assert got.shape == (1,) and abs(got[0] - 1.0) < 0.012
    left, right = burst_at(1.0, 1.5)
    got = no.refine_starts([0.98, 1.48], left, right, RATE)
    assert got.shape == (2,) and (np.diff(got) > 0).all() and abs(got[0] - 1.0) < 0.012 and abs(got[1] - 1.5) < 0.012


def test_refining_gives_no_starts_for_no_starts_and_does_not_change_its_inputs():
    left, right = burst_at(1.0)
    assert no.refine_starts([], left, right, RATE).shape == (0,)
    starts = np.array([0.97])
    before = (starts.copy(), left.copy(), right.copy())
    no.refine_starts(starts, left, right, RATE)
    assert np.array_equal(starts, before[0]) and np.array_equal(left, before[1]) and np.array_equal(right, before[2])


def test_the_samples_may_be_integers_or_floating_point_and_a_quiet_file_gives_the_same_moments():
    left, right = burst_at(1.0, dtype=np.int16)
    as_int = no.refine_starts([0.97], left, right, RATE)
    as_float = no.refine_starts([0.97], left / 32768.0, right / 32768.0, RATE)
    assert as_int.tolist() == pytest.approx(as_float.tolist())  # the level is scaled, the moment of the largest rise is not


@pytest.mark.parametrize("starts", [[0.5, 0.5], [1.0, 0.5], [np.nan], [[0.5]], "abc"])
def test_refine_starts_refuses_starts_that_are_not_in_strictly_increasing_order(starts):
    silence = np.zeros(RATE, dtype=np.int16)
    with pytest.raises(ValueError):
        no.refine_starts(starts, silence, silence, RATE)


def test_refine_starts_refuses_channels_that_do_not_match_or_are_not_numbers_and_a_bad_rate():
    silence = np.zeros(RATE, dtype=np.int16)
    for left, right in ((silence, silence[:-1]), (silence.reshape(2, -1), silence.reshape(2, -1)), (np.array(["a"] * 10), np.array(["a"] * 10))):
        with pytest.raises(ValueError):
            no.refine_starts([0.5], left, right, RATE)
    for rate in (0, -1.0, float("nan"), float("inf"), True, "44100", None):
        with pytest.raises(ValueError):
            no.refine_starts([0.5], silence, silence, rate)


# --- the whole path: analysis windows and waveform -----------------------------------------------------------------------------


def tones(frequencies, spacing, first=0.7):
    """Decaying piano-like tones of the given frequencies ``spacing`` seconds apart, from ``first`` seconds; returns (channel, true onset times)."""
    onsets = first + spacing * np.arange(len(frequencies))
    x = np.zeros(int(RATE * (onsets[-1] + 1.5)))
    for frequency, at in zip(frequencies, onsets):
        i = int(round(at * RATE))
        m = int(0.45 * RATE)
        t = np.arange(m) / RATE
        x[i : i + m] += 8000 * np.sin(2 * np.pi * frequency * t) * np.exp(-t * 6)
    return x.astype(np.int16), onsets


def windows_of(channel):
    return floor_analysis(analyze_channels(channel, channel, RATE, 4096, step=buffer_step(RATE))).frames


def test_each_of_ten_notes_is_one_start_and_it_is_within_a_few_hundredths_of_a_second_of_where_it_begins():
    frequencies = [220.0, 261.63, 329.63, 392.0, 440.0, 349.23, 293.66, 523.25, 246.94, 311.13]
    channel, onsets = tones(frequencies, 0.5)
    got = no.onset_starts(windows_of(channel), channel, channel, RATE)
    assert got.shape == onsets.shape and (np.diff(got) > 0).all()
    assert np.abs(got - onsets).max() < 0.015  # the windows alone are 10 to 40 ms early; on the waveform the error is a few thousandths


def test_notes_of_unequal_spacing_are_found_with_their_own_spacing():
    frequencies = [220.0, 330.0, 247.0, 392.0, 262.0, 349.0]
    spacings = [0.30, 0.45, 0.60, 0.30, 0.45]
    onsets = 0.7 + np.concatenate([[0.0], np.cumsum(spacings)])
    x = np.zeros(int(RATE * (onsets[-1] + 1.5)))
    for frequency, at in zip(frequencies, onsets):
        i, m = int(round(at * RATE)), int(0.25 * RATE)
        t = np.arange(m) / RATE
        x[i : i + m] += 8000 * np.sin(2 * np.pi * frequency * t) * np.exp(-t * 8)
    channel = x.astype(np.int16)
    got = no.onset_starts(windows_of(channel), channel, channel, RATE)
    assert got.shape == onsets.shape and np.abs(np.diff(got) - np.array(spacings)).max() < 0.02


def test_silence_has_no_start_and_the_starts_are_the_same_twice():
    silence = np.zeros(RATE * 3, dtype=np.int16)
    assert no.onset_starts(windows_of(silence), silence, silence, RATE).shape == (0,)
    channel, _ = tones([220.0, 330.0, 440.0], 0.5)
    windows = windows_of(channel)
    assert np.array_equal(no.onset_starts(windows, channel, channel, RATE), no.onset_starts(windows, channel, channel, RATE))


# --- the trills (fifth round) ------------------------------------------------------------------------------------------------


def test_within_a_trill_the_notes_from_one_semitone_below_its_lowest_note_upward_do_not_rise():
    values = silent(10)
    values[4, [20, 39, 40, 60]] = [1.0, 2.0, 4.0, 8.0]  # a low note, the note just below the trill, the trill's note, one above
    values[8, [39, 40]] = [2.0, 4.0]  # after the trill
    spans = np.array([[3, 6, 40]])
    assert no.onset_rises(values).tolist() == [0, 0, 0, 0, 15.0, 0, 0, 0, 6.0, 0]
    assert no.onset_rises(values, spans).tolist() == [0, 0, 0, 0, 1.0, 0, 0, 0, 6.0, 0]  # column 39 and upward left out in windows 3 to 6
    assert no.onset_rises(values, np.zeros((0, 3), dtype=np.int64)).tolist() == no.onset_rises(values).tolist()


@pytest.mark.parametrize("spans", [np.array([[3, 2, 40]]), np.array([[1.0, 2.0, 40.0]]), np.array([1, 2, 40]), np.array([[-1, 2, 40]]), np.array([[1, 2]])])
def test_trills_that_are_not_allowed_are_refused(spans):
    with pytest.raises(ValueError):
        no.onset_rises(silent(5), spans)


def trill_over_bass(trill=True):
    """A bass note (110 Hz) every half second from 0.25 s and, from 1.5 s to 2.7 s, a trill of C6 and D6 in notes of 75 ms."""
    x = np.zeros(RATE * 4)
    for k in range(7):
        i, m = int(round((0.25 + 0.5 * k) * RATE)), int(0.4 * RATE)
        t = np.arange(m) / RATE
        x[i : i + m] += 4000 * np.sin(2 * np.pi * 110.0 * t) * np.exp(-t * 6)
    if trill:
        for n in range(16):
            i, m = int(round((1.5 + n * 0.075) * RATE)), int(round(0.075 * RATE))
            t = np.arange(m) / RATE
            fade = np.minimum(1.0, np.minimum(t, t[::-1]) / 0.005)  # 5 ms in and out, as an instrument would: no click across all the notes
            x[i : i + m] += 8000 * np.sin(2 * np.pi * 55.0 * 2 ** ((51 if n % 2 == 0 else 53) / 12) * t) * fade
    return x.astype(np.int16)


def test_a_trill_makes_fewer_starts_and_the_bass_notes_around_it_still_start():
    channel = trill_over_bass()
    windows = windows_of(channel)
    plain = no.refine_starts(no.pick_onsets(no.onset_rises(windows)), channel, channel, RATE)  # without looking for trills
    got = no.onset_starts(windows, channel, channel, RATE)
    inside = lambda starts: starts[(starts > 1.55) & (starts < 2.7)]
    assert len(inside(got)) < len(inside(plain))
    for at in (0.25, 0.75, 1.25, 2.25, 2.75, 3.25):  # the bass notes but the one at 1.75 s: inside a trill a start is placed on the whole waveform, here a louder trill note
        assert np.abs(got - at).min() < 0.01
    bass = trill_over_bass(trill=False)
    assert np.allclose(no.onset_starts(windows_of(bass), bass, bass, RATE), 0.25 + 0.5 * np.arange(7), atol=0.01)  # no trill: nothing left out
