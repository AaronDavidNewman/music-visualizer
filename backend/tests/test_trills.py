"""The trills of Rhythm Circles (feature 047, fifth round): the levels of the semitones, the score of each window and the spans.

Everything is tested on short synthetic audio (a trill of C6 and D6 over a bass note every half second) or on small arrays made by hand,
with no sample file.
"""

import numpy as np
import pytest

from app.services import trills as tr
from app.services.buffer_interval import buffer_step
from app.services.noise_floor import floor_analysis
from app.services.note_analysis import analyze_channels

RATE = 44100
C6, D6 = 51, 53  # analysis columns (0 = A1, 55 Hz)


def frequency(column):
    return 55.0 * 2 ** (column / 12)


def tone(x, at, length, hertz, amplitude, decay=0.0):
    i, m = int(round(at * RATE)), int(round(length * RATE))
    t = np.arange(m) / RATE
    x[i : i + m] += amplitude * np.sin(2 * np.pi * hertz * t) * np.exp(-t * decay)


def piece(trill=True, seconds=4.0, note=0.075):
    """A bass note (110 Hz) every half second from 0.25 s and, from 1.5 s to 2.7 s, a trill of C6 and D6 with notes of ``note`` seconds."""
    x = np.zeros(int(RATE * seconds))
    for k in range(int(seconds / 0.5) - 1):
        tone(x, 0.25 + 0.5 * k, 0.4, 110.0, 4000, decay=6)
    if trill:
        for n in range(int(round(1.2 / note))):
            tone(x, 1.5 + n * note, note, frequency(C6 if n % 2 == 0 else D6), 8000, decay=12)
    return np.clip(x, -32767, 32767).astype(np.int16)


def windows_of(channel):
    return floor_analysis(analyze_channels(channel, channel, RATE, 4096, step=buffer_step(RATE))).frames


# --- the constants -----------------------------------------------------------------------------------------------------------


def test_the_semitones_are_c3_to_g_sharp_7_and_the_rule_is_the_one_measured():
    assert frequency(tr.FIRST_COLUMN) == pytest.approx(130.81, abs=0.01)  # C3
    assert frequency(tr.FIRST_COLUMN + tr.SEMITONES - 1) == pytest.approx(3322.44, abs=0.01)  # G#7
    assert (tr.FRAME, tr.HOP, tr.SPAN, tr.FLICKER_BAND, tr.STEPS) == (2048, 256, 0.5, (6.0, 20.0), (1, 2))
    assert (tr.TRILL_SCORE, tr.MAX_GAP_WINDOWS, tr.MIN_WINDOWS, tr.EDGE_WINDOWS, tr.TRILL_MARGIN, tr.SOUNDING_PERCENTILE) == (0.2, 3, 3, 4, 1, 60)


# --- the levels --------------------------------------------------------------------------------------------------------------


def test_the_levels_have_a_row_for_each_frame_that_fits_and_57_columns():
    channel = piece(trill=False, seconds=1.0)
    levels = tr.semitone_levels(channel, channel, RATE)
    assert levels.shape == ((RATE - 2048) // 256 + 1, 57) and levels.dtype == np.float64 and (levels >= 0).all()
    short = np.zeros(2047, dtype=np.int16)
    assert tr.semitone_levels(short, short, RATE).shape == (0, 57)


def test_a_steady_tone_is_loudest_in_its_own_semitone():
    x = np.zeros(RATE)
    tone(x, 0.0, 1.0, frequency(45), 8000)  # A5, 880 Hz
    channel = x.astype(np.int16)
    levels = tr.semitone_levels(channel, channel, RATE)
    assert (np.argmax(levels, axis=1) + tr.FIRST_COLUMN == 45).all()


def test_silence_has_level_0_and_the_two_channels_are_mixed():
    silence = np.zeros(RATE, dtype=np.int16)
    assert (tr.semitone_levels(silence, silence, RATE) == 0).all()
    x = np.zeros(RATE)
    tone(x, 0.0, 1.0, frequency(45), 8000)
    assert np.allclose(tr.semitone_levels(x, np.zeros(RATE), RATE), tr.semitone_levels(x / 2, x / 2, RATE))  # the mix is (left + right) / 2


def test_every_semitone_has_at_least_one_frequency_of_its_own_band_or_the_nearest():
    bands = tr._band_matrix(RATE)
    assert bands.shape == (1025, 57) and (bands.sum(axis=0) >= 1).all() and set(np.unique(bands)) <= {0.0, 1.0}


@pytest.mark.parametrize("left, right, rate", [
    (np.zeros(10), np.zeros(11), RATE),
    (np.zeros((2, 5)), np.zeros((2, 5)), RATE),
    (np.array(["a"]), np.array(["b"]), RATE),
    (np.zeros(10), np.zeros(10), 0),
    (np.zeros(10), np.zeros(10), True),
    (np.zeros(10), np.zeros(10), float("nan")),
])
def test_channels_or_a_rate_that_are_not_allowed_are_refused(left, right, rate):
    with pytest.raises(ValueError):
        tr.semitone_levels(left, right, rate)


# --- the scores and the spans ------------------------------------------------------------------------------------------------


def test_a_trill_of_c6_and_d6_is_one_span_with_its_lower_note_and_the_bass_alone_is_none():
    channel = piece()
    windows = windows_of(channel).shape[0]
    spans = tr.find_trills(channel, channel, RATE, windows)
    assert spans.shape == (1, 3) and spans.dtype == np.int64
    first, last, lowest = spans[0]
    assert lowest == C6
    assert 1.4 <= first * 0.06 <= 1.6 and 2.6 <= (last + 1) * 0.06 <= 2.8  # the trill is from 1.5 s to 2.7 s
    plain = piece(trill=False)
    assert tr.find_trills(plain, plain, RATE, windows).shape == (0, 3)


def test_the_scores_are_from_0_to_1_and_the_trill_scores_high_in_its_middle_only():
    channel = piece()
    levels = tr.semitone_levels(channel, channel, RATE)
    scores, notes = tr.trill_scores(levels, RATE, 66)
    assert scores.shape == notes.shape == (66,) and scores.dtype == np.float64 and notes.dtype == np.int64
    assert (scores >= 0).all() and (scores <= 1).all()
    assert scores[int(2.1 / 0.06)] >= 0.2 and notes[int(2.1 / 0.06)] == C6  # the middle of the trill
    assert scores[: int(1.0 / 0.06)].max() < 0.2 and scores[int(3.2 / 0.06) :].max() < 0.2  # before and after it
    assert (notes[scores == 0] == -1).all()


def test_a_window_whose_half_second_does_not_fit_in_the_levels_scores_0():
    channel = piece()
    levels = tr.semitone_levels(channel, channel, RATE)
    scores, notes = tr.trill_scores(levels, RATE, 200)  # more windows than the file has
    assert (scores[:3] == 0).all() and (scores[70:] == 0).all() and (notes[70:] == -1).all()
    assert tr.trill_scores(levels, RATE, 0)[0].shape == (0,)


@pytest.mark.parametrize("levels, windows", [(np.zeros((10, 56)), 5), (np.zeros(10), 5), (np.full((10, 57), np.nan), 5), (np.zeros((10, 57)), -1), (np.zeros((10, 57)), 2.5), (np.zeros((10, 57)), True)])
def test_levels_or_a_number_of_windows_that_are_not_allowed_are_refused(levels, windows):
    with pytest.raises(ValueError):
        tr.trill_scores(levels, RATE, windows)


def test_the_windows_in_a_trill_join_across_gaps_of_up_to_3_windows_and_short_spans_are_dropped():
    scores = np.zeros(60)
    notes = np.full(60, -1)
    scores[10:14] = 0.3  # 4 windows
    scores[17:19] = 0.25  # 3 windows later: the same span
    notes[10:14], notes[17:19] = 40, 38
    scores[30:32] = 0.5  # only 2 windows: dropped
    notes[30:32] = 50
    scores[40] = scores[45] = 0.2  # 4 windows apart: not joined, each alone too short
    notes[40] = notes[45] = 44
    spans = tr.trill_spans(scores, notes)
    assert spans.tolist() == [[10 - 4, 18 + 4, 38]]  # widened by 4 windows at each end; the lowest lower note


def test_a_widened_span_stays_inside_the_windows_and_a_score_just_below_the_threshold_is_not_a_trill():
    scores = np.full(8, 0.3)
    notes = np.full(8, 30)
    assert tr.trill_spans(scores, notes).tolist() == [[0, 7, 30]]
    assert tr.trill_spans(np.full(8, 0.1999), notes).shape == (0, 3)
    assert tr.trill_spans(np.zeros(0), np.zeros(0, dtype=np.int64)).shape == (0, 3)


@pytest.mark.parametrize("scores, notes", [(np.zeros(5), np.zeros(4, dtype=np.int64)), (np.zeros(5), np.zeros(5)), (np.full(5, np.inf), np.zeros(5, dtype=np.int64)), (np.zeros((5, 1)), np.zeros((5, 1), dtype=np.int64))])
def test_scores_and_notes_that_do_not_match_are_refused(scores, notes):
    with pytest.raises(ValueError):
        tr.trill_spans(scores, notes)


def test_the_trills_are_the_same_twice_and_the_inputs_are_not_changed():
    channel = piece()
    copy = channel.copy()
    once = tr.find_trills(channel, channel, RATE, 66)
    assert np.array_equal(once, tr.find_trills(channel, channel, RATE, 66)) and np.array_equal(channel, copy)
