"""The chord measurement on real note analysis: synthesized chords through ``analyze_channels`` (feature 031).

Assumptions about the analysis, checked by the first test: with a window of 8192 samples at 44,100 Hz the notes from about C5 up have a spectrum
bin of their own; ``note_tone`` makes a sine at the exact centre of that bin, so a sine of one note raises that note only (and exactly 0 elsewhere
when the audio is silent, because the spectrum of zeros is zeros).
"""

import numpy as np

from app.services.chords import ChordRecord, measure_chords
from app.services.note_analysis import NoteBinAnalyzer, analyze_channels

from .test_jobs_api import SR, note_tone

WINDOW = 8192
C5, E5, G5, C6 = 39, 43, 46, 51  # note numbers: 0 is A1 (55 Hz)


def chord_frames(notes, silence=1.0, seconds=2.0):
    """The note strengths of a file with ``silence`` seconds of silence, the chord for ``seconds`` seconds, then silence again."""
    gap = np.zeros(int(silence * SR))
    chord = sum(0.2 * note_tone(n, seconds, WINDOW) for n in notes)
    audio = np.concatenate([gap, chord, gap])
    return analyze_channels(audio, audio, SR, WINDOW).frames


def test_the_notes_used_have_a_spectrum_bin_each():
    bins = NoteBinAnalyzer(SR, WINDOW).bin_indices
    assert len({int(bins[n]) for n in (C5, E5, G5, C6)}) == 4


def test_a_synthesized_c_major_triad_is_recorded_as_a_triad_in_root_position_in_the_windows_it_sounds_in():
    frames = chord_frames([C5, E5, G5])
    series = measure_chords(frames, [(4,), (4, 7)])
    assert series.window_count == frames.shape[0]
    middle = range(7, 15)  # one second is 5.4 windows: windows 6 to 15 are entirely inside the chord
    assert all(series.record(i) == ChordRecord((4, 7), 0, (C5, E5, G5)) for i in middle)
    assert all(series.record(i) is None for i in (0, 1, 2, 3, series.window_count - 1))  # silence: no chord (the spectrum of zeros is zeros)


def test_the_same_notes_with_another_note_in_the_bass_are_recorded_as_inversions():
    frames = chord_frames([E5, G5, C6])
    series = measure_chords(frames, [(4,), (4, 7)])
    assert all(series.record(i) == ChordRecord((4, 7), 1, (E5, G5, C6)) for i in range(7, 15))


def test_two_tones_a_third_apart_are_recorded_as_a_third_and_a_fourth_as_an_inverted_fifth():
    series = measure_chords(chord_frames([C5, E5]), [(4,), (5,), (7,)])
    assert all(series.record(i) == ChordRecord((4,), 0, (C5, E5)) for i in range(7, 15))
    fourth = measure_chords(chord_frames([C5, 44]), [(5,), (7,)])  # F5 is 5 steps above C5
    assert all(fourth.record(i) == ChordRecord((7,), 1, (C5, 44)) for i in range(7, 15))


def test_one_tone_alone_is_no_chord_while_it_sustains_once_the_leakage_of_the_spectrum_is_below_a_threshold():
    frames = chord_frames([C5])
    series = measure_chords(frames, [(4,), (4, 7)], threshold=1)
    assert all(series.record(i) is None for i in range(6, 16))  # the windows entirely inside the tone: the other notes are below 1 percent
    # (windows 5 and 16, where the tone starts and stops, are not tested: the step leaks a few percent into the neighbouring notes, and those are enough
    # letters for a third among the 4 loudest. That is the price of looking at more letters than the chord has notes.)


def test_the_limits_work_on_the_frames_of_the_analysis():
    frames = chord_frames([C5, E5, G5])
    limited = measure_chords(frames, [(4, 7)], note_count=12, threshold=5)
    assert all(limited.record(i) == ChordRecord((4, 7), 0, (C5, E5, G5)) for i in range(7, 15))
    # all 84 notes allowed is the same as no limit
    assert measure_chords(frames, [(4, 7)], note_count=84).record(10) == ChordRecord((4, 7), 0, (C5, E5, G5))
