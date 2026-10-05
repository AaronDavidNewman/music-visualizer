import math
import warnings

import numpy as np
import pytest
from scipy.io import wavfile

from app.services import note_analysis
from app.services.note_analysis import (
    BASE_FREQUENCY,
    NOTE_COUNT,
    AnalysisResult,
    AudioAnalysisError,
    NoteBinAnalyzer,
    analyze_wav,
    note_frequencies,
)

SR = 44100
WINDOW = 2048


def tone(freq, n, sample_rate=SR, amplitude=1.0):
    t = np.arange(n) / sample_rate
    return amplitude * np.sin(2 * np.pi * freq * t)


def write_wav(path, left, right=None, sample_rate=SR, dtype=np.int16):
    """Write float [-1, 1] audio as a PCM WAV. right=None writes mono."""
    scale = np.iinfo(dtype).max
    data = np.round(np.asarray(left) * scale).astype(dtype)
    if right is not None:
        data = np.stack([data, np.round(np.asarray(right) * scale).astype(dtype)], axis=1)
    wavfile.write(str(path), sample_rate, data)
    return path


# --- User Story 1: one window -> 88 values -----------------------------------


def test_note_table():
    freqs = note_frequencies()
    assert len(freqs) == NOTE_COUNT == 88
    assert freqs[0] == BASE_FREQUENCY == 55.0
    assert freqs[12] == pytest.approx(110.0)
    assert freqs[2] == pytest.approx(55.0 * math.pow(math.pow(2, 1 / 12), 2))
    assert freqs[87] == pytest.approx(55.0 * 2 ** (87 / 12))


def test_bin_indices_follow_formula():
    a = NoteBinAnalyzer(SR, WINDOW)
    expected = [int((WINDOW / SR) * f) for f in note_frequencies()]
    assert a.bin_indices.tolist() == expected
    assert a.bin_indices.shape == (88,)


def test_pure_tone_peaks_at_its_note():
    a = NoteBinAnalyzer(SR, WINDOW)
    x = tone(440, WINDOW)
    result = a.analyze(x, x)
    assert result.shape == (88,)
    assert result.dtype == np.float64
    idx = int((WINDOW / SR) * 440)
    assert result.argmax() == int(np.flatnonzero(a.bin_indices == idx)[0])
    assert result.max() > 0


def test_silence_gives_zeros():
    a = NoteBinAnalyzer(SR, WINDOW)
    z = np.zeros(WINDOW)
    assert not a.analyze(z, z).any()


def test_channels_are_averaged():
    a = NoteBinAnalyzer(SR, WINDOW)
    x = tone(440, WINDOW)
    both = a.analyze(x, x)
    one_side = a.analyze(x, np.zeros(WINDOW))
    assert one_side.max() == pytest.approx(both.max() / 2, rel=0.01)
    assert np.allclose(a.analyze(np.zeros(WINDOW), x), one_side)


def test_deterministic():
    a = NoteBinAnalyzer(SR, WINDOW)
    x, y = tone(440, WINDOW), tone(660, WINDOW)
    assert np.array_equal(a.analyze(x, y), a.analyze(x, y))


def test_short_buffer_is_zero_padded():
    a = NoteBinAnalyzer(SR, WINDOW)
    x = tone(440, 1000)
    padded = np.concatenate([x, np.zeros(WINDOW - 1000)])
    assert np.allclose(a.analyze(x, x), a.analyze(padded, padded))


@pytest.mark.parametrize("sample_rate", [0, -44100])
def test_rejects_bad_sample_rate(sample_rate):
    with pytest.raises(AudioAnalysisError, match="sample rate"):
        NoteBinAnalyzer(sample_rate, WINDOW)


@pytest.mark.parametrize("window", [0, -2048, 2048.5, True, "2048"])
def test_rejects_bad_window_size(window):
    with pytest.raises(AudioAnalysisError, match="window size"):
        NoteBinAnalyzer(SR, window)


def test_rejects_sample_rate_too_low_for_top_note():
    with pytest.raises(AudioAnalysisError, match="too low"):
        NoteBinAnalyzer(8000, WINDOW)


def test_rejects_bad_buffers():
    a = NoteBinAnalyzer(SR, WINDOW)
    with pytest.raises(AudioAnalysisError, match="same length"):
        a.analyze(np.zeros(100), np.zeros(200))
    with pytest.raises(AudioAnalysisError, match="longer than"):
        a.analyze(np.zeros(WINDOW + 1), np.zeros(WINDOW + 1))
    with pytest.raises(AudioAnalysisError, match="1-D"):
        a.analyze(np.zeros((2, 100)), np.zeros((2, 100)))


def test_every_note_is_detected_with_a_large_window():
    """SC-001: at least 95% of notes (excluding ones sharing a position) peak at their own bin."""
    window = 32768
    a = NoteBinAnalyzer(SR, window)
    unique, counts = np.unique(a.bin_indices, return_counts=True)
    shared = set(unique[counts > 1].tolist())
    tested = hits = 0
    for n, freq in enumerate(a.frequencies):
        if a.bin_indices[n] in shared:
            continue
        x = tone(freq, window)
        tested += 1
        hits += int(a.analyze(x, x).argmax() == n)
    assert tested > 0
    assert hits / tested >= 0.95, f"{hits}/{tested} notes detected"


# --- User Story 2: whole file -----------------------------------------------


def test_wav_window_count_peaks_and_times(tmp_path):
    n = WINDOW * 5 + 700  # not a multiple of the window size
    x = tone(440, n)
    path = write_wav(tmp_path / "a.wav", x, x)

    result = analyze_wav(path, SR, WINDOW)

    assert isinstance(result, AnalysisResult)
    assert result.frames.shape == (6, 88)
    assert result.window_count == 6
    ref = NoteBinAnalyzer(SR, WINDOW)
    idx = int(np.flatnonzero(ref.bin_indices == int((WINDOW / SR) * 440))[0])
    assert (result.frames[:5].argmax(axis=1) == idx).all()
    assert result.frames[5].any()  # padded final window is analyzed, not dropped
    assert np.allclose(result.window_start_times(), np.arange(6) * WINDOW / SR)


def test_wav_rows_match_single_window_analysis(tmp_path):
    n = WINDOW * 3
    left, right = tone(440, n), tone(880, n)
    path = write_wav(tmp_path / "a.wav", left, right, dtype=np.int32)
    result = analyze_wav(path, SR, WINDOW)
    a = NoteBinAnalyzer(SR, WINDOW)
    for i in range(3):
        sl = slice(i * WINDOW, (i + 1) * WINDOW)
        assert np.allclose(result.frames[i], a.analyze(left[sl], right[sl]), rtol=1e-3, atol=1e-3)


def test_wav_chunking_gives_same_rows(tmp_path, monkeypatch):
    n = WINDOW * 10 + 300
    path = write_wav(tmp_path / "a.wav", tone(440, n), tone(1000, n))
    whole = analyze_wav(path, SR, WINDOW)
    monkeypatch.setattr(note_analysis, "_CHUNK_SAMPLES", WINDOW * 3)  # forces several chunks
    chunked = analyze_wav(path, SR, WINDOW)
    assert chunked.frames.shape == (11, 88)
    assert np.array_equal(whole.frames, chunked.frames)


def test_wav_mono_equals_identical_stereo(tmp_path):
    x = tone(440, WINDOW * 2)
    mono = analyze_wav(write_wav(tmp_path / "m.wav", x), SR, WINDOW)
    stereo = analyze_wav(write_wav(tmp_path / "s.wav", x, x), SR, WINDOW)
    assert np.allclose(mono.frames, stereo.frames)


def test_wav_bit_depth_does_not_change_levels(tmp_path):
    x = tone(440, WINDOW * 2, amplitude=0.5)
    r16 = analyze_wav(write_wav(tmp_path / "a16.wav", x, x, dtype=np.int16), SR, WINDOW)
    r32 = analyze_wav(write_wav(tmp_path / "a32.wav", x, x, dtype=np.int32), SR, WINDOW)
    assert np.allclose(r16.frames, r32.frames, rtol=0.01, atol=1e-3)


def test_wav_empty_file(tmp_path):
    path = write_wav(tmp_path / "e.wav", np.zeros(0), np.zeros(0))
    result = analyze_wav(path, SR, WINDOW)
    assert result.frames.shape == (0, 88)
    assert result.window_count == 0


def test_wav_shorter_than_one_window(tmp_path):
    x = tone(440, 500)
    result = analyze_wav(write_wav(tmp_path / "s.wav", x, x), SR, WINDOW)
    assert result.frames.shape == (1, 88)


def test_wav_missing_file(tmp_path):
    with pytest.raises(AudioAnalysisError, match="Could not read"):
        analyze_wav(tmp_path / "nope.wav", SR, WINDOW)


def test_wav_not_a_wav(tmp_path):
    bad = tmp_path / "fake.wav"
    bad.write_text("this is not audio")
    with pytest.raises(AudioAnalysisError, match="Could not read"):
        analyze_wav(bad, SR, WINDOW)


def test_wav_too_many_channels(tmp_path):
    data = np.zeros((WINDOW, 3), dtype=np.int16)
    path = tmp_path / "three.wav"
    wavfile.write(str(path), SR, data)
    with pytest.raises(AudioAnalysisError, match="channels"):
        analyze_wav(path, SR, WINDOW)


def test_wav_parameter_errors_come_before_file_errors(tmp_path):
    with pytest.raises(AudioAnalysisError, match="too low"):
        analyze_wav(tmp_path / "nope.wav", 8000, WINDOW)


def test_wav_sample_rate_mismatch_warns_and_uses_supplied_rate(tmp_path):
    x = tone(440, WINDOW * 2)
    path = write_wav(tmp_path / "a.wav", x, x, sample_rate=SR)
    with pytest.warns(UserWarning, match="sample rate"):
        result = analyze_wav(path, 48000, WINDOW)
    assert result.sample_rate == 48000
    assert result.frames[0].any()
    # computed with the supplied rate: positions differ from a run at the file's rate
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        same = analyze_wav(path, SR, WINDOW)
    assert not np.array_equal(result.frames, same.frames)


def test_wav_sample_count(tmp_path):
    x = tone(440, 1234)
    result = analyze_wav(write_wav(tmp_path / "a.wav", x, x), SR, WINDOW)
    assert result.sample_count == 1234


# --- window spacing: arbitrary window starts ----------------------------------

from app.services.note_analysis import analyze_channels, window_count, window_starts  # noqa: E402


def test_window_starts_follow_step():
    assert window_starts(10000, 2048).tolist() == [0, 2048, 4096, 6144, 8192]
    starts = window_starts(1_000_000, 1228.8)
    assert starts[99] == 121651  # nearest whole sample to 99 * 1228.8, counted from the start
    assert starts[100] == 122880
    assert window_starts(0, 2048).size == 0


@pytest.mark.parametrize("step", [1, 1.5, 2.5, 1228.8, 2048, 5000, 1e9])
@pytest.mark.parametrize("total", [0, 1, 2, 10, 10000, 12345])
def test_window_count_matches_explicit_starts(step, total):
    assert window_count(total, step) == len(window_starts(total, step))


def test_default_step_gives_the_old_consecutive_windows():
    n = WINDOW * 3 + 100
    left, right = tone(440, n), tone(880, n)
    result = analyze_channels(left, right, SR, WINDOW)
    assert result.starts.tolist() == [0, WINDOW, 2 * WINDOW, 3 * WINDOW]
    assert result.sample_count == n
    a = NoteBinAnalyzer(SR, WINDOW)
    for i, start in enumerate(result.starts):
        assert np.allclose(result.frames[i], a.analyze(left[start:start + WINDOW], right[start:start + WINDOW]))


def test_quarter_step_starts():
    n = 8192 * 2
    x = tone(440, n)
    result = analyze_channels(x, x, SR, 8192, step=2048)
    assert result.starts.tolist() == [0, 2048, 4096, 6144, 8192, 10240, 12288, 14336]
    assert np.allclose(result.window_start_times(), result.starts / SR)


def test_window_starting_where_a_tone_starts_sees_exactly_the_tone():
    n = 20000
    burst = tone(440, n - 2048)
    audio = np.zeros(n)
    audio[2048:] = burst
    result = analyze_channels(audio, audio, SR, 8192, step=2048)
    alone = NoteBinAnalyzer(SR, 8192).analyze(burst[:8192], burst[:8192])
    # window 1 starts at sample 2048, so its data is the tone from its first sample
    assert result.starts[1] == 2048
    assert np.allclose(result.frames[1], alone)
    # window 0 starts earlier and holds 2048 samples of silence before the tone
    assert not np.allclose(result.frames[0], alone)


def test_gaps_analyze_only_the_windows_at_the_starts():
    n = WINDOW * 6
    left, right = tone(440, n), tone(660, n)
    result = analyze_channels(left, right, SR, WINDOW, step=2 * WINDOW)
    assert result.starts.tolist() == [0, 2 * WINDOW, 4 * WINDOW]
    a = NoteBinAnalyzer(SR, WINDOW)
    for i, start in enumerate(result.starts):
        assert np.allclose(result.frames[i], a.analyze(left[start:start + WINDOW], right[start:start + WINDOW]))


def test_one_sample_step_gives_a_window_per_sample():
    x = tone(440, 50)
    result = analyze_channels(x, x, SR, WINDOW, step=1)
    assert result.frames.shape == (50, 88)
    assert result.starts.tolist() == list(range(50))


def test_chunking_does_not_change_overlapping_windows(monkeypatch):
    n = WINDOW * 5 + 77
    left, right = tone(440, n), tone(1000, n)
    whole = analyze_channels(left, right, SR, WINDOW, step=WINDOW * 0.3)
    monkeypatch.setattr(note_analysis, "_CHUNK_SAMPLES", WINDOW * 2)
    chunked = analyze_channels(left, right, SR, WINDOW, step=WINDOW * 0.3)
    assert chunked.frames.shape == whole.frames.shape
    assert np.array_equal(whole.frames, chunked.frames)
    assert np.array_equal(whole.starts, chunked.starts)
