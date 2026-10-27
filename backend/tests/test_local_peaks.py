"""The local_peaks measurement: the periodic local maxima of the overall energy, and the energy and rate asked at any point."""

import inspect

import numpy as np
import pytest
from scipy.io import wavfile
from scipy.signal import find_peaks as real_find_peaks

import app.services.local_peaks as lp
from app.services.local_peaks import (
    DEFAULT_RATE,
    IMPULSE_SAMPLES,
    LocalPeak,
    LocalPeaks,
    impulse_energy,
    measure_local_peaks,
    measure_wav,
)
from app.services.note_analysis import AudioAnalysisError

from .local_peaks_signals import RATE, bursts, click_track, direct_energy, silence


def samples_of(result):
    return np.array([p.sample for p in result.peaks])


def rates_of(result):
    return np.array([p.rate for p in result.peaks])


def near_clicks(result, clicks, tolerance=IMPULSE_SAMPLES):
    """True when every click has a peak within ``tolerance`` samples and every peak is near a click."""
    got = samples_of(result)
    if len(got) == 0:
        return len(clicks) == 0
    by_click = all(np.min(np.abs(got - c)) <= tolerance for c in clicks)
    by_peak = all(np.min(np.abs(clicks - g)) <= tolerance for g in got)
    return by_click and by_peak


def owning_window(index, count, window):
    """The ``(start, end)`` of the peaks window that owns impulse sample ``index``: the zones of the windows tile the file."""
    step, quarter = window // 2, window // 4
    start = 0
    while True:
        end = min(start + window, count)
        last = end == count
        low = 0 if start == 0 else start + quarter
        high = end if last else start + 3 * quarter
        if low <= index < high:
            return start, end
        assert not last, "the zones do not tile the file"
        start += step


# ---------------------------------------------------------------------------------------------------------------------
# the impulse energy
# ---------------------------------------------------------------------------------------------------------------------


def test_the_impulse_energy_is_the_average_of_the_two_standard_deviations_per_32_samples():
    rng = np.random.default_rng(3)
    left, right = rng.normal(0, 1, 32 * 50), rng.normal(0, 3, 32 * 50)
    energy = impulse_energy(left, right)
    assert energy.shape == (50,)
    assert energy.dtype == np.float64
    assert np.allclose(energy, direct_energy(left, right), atol=1e-12)
    # a channel counts on its own: the spreads are averaged, not the samples
    first = energy[0]
    assert first == pytest.approx((np.std(left[:32]) + np.std(right[:32])) / 2)


def test_a_loud_left_and_a_silent_right_give_half_the_spread_of_the_left():
    rng = np.random.default_rng(4)
    left = rng.normal(0, 1, 320)
    energy = impulse_energy(left, np.zeros(320))
    assert np.allclose(energy, [np.std(left[i * 32 : i * 32 + 32]) / 2 for i in range(10)])


def test_two_channels_in_opposite_phase_do_not_cancel():
    rng = np.random.default_rng(5)
    left = rng.normal(0, 1, 640)
    energy = impulse_energy(left, -left)
    assert np.allclose(energy, direct_energy(left, left))
    assert energy.min() > 0.3


def test_a_mono_file_has_the_spread_of_its_one_channel():
    rng = np.random.default_rng(6)
    x = rng.normal(0, 2, 32 * 20)
    assert np.allclose(impulse_energy(x, x), [np.std(x[i * 32 : i * 32 + 32]) for i in range(20)])


def test_a_last_partial_window_is_dropped_and_short_input_gives_nothing():
    rng = np.random.default_rng(7)
    x = rng.normal(0, 1, 32 * 4 + 31)
    assert impulse_energy(x, x).shape == (4,)
    assert impulse_energy(x[:31], x[:31]).shape == (0,)
    assert impulse_energy(x[:0], x[:0]).shape == (0,)


def test_silence_has_no_energy_and_the_input_is_not_changed():
    left, right = silence(0.1)
    assert impulse_energy(left, right).max() == 0
    rng = np.random.default_rng(8)
    a, b = rng.normal(0, 1, 640), rng.normal(0, 1, 640)
    a0, b0 = a.copy(), b.copy()
    impulse_energy(a, b)
    assert np.array_equal(a, a0) and np.array_equal(b, b0)


def test_the_energy_of_integer_samples_does_not_depend_on_the_bit_depth():
    rng = np.random.default_rng(9)
    x = rng.normal(0, 0.1, 640)
    as16 = np.round(x * 32768).astype(np.int16)
    as32 = np.round(x * 2147483648).astype(np.int32)
    assert np.allclose(impulse_energy(as16, as16), impulse_energy(as32, as32), atol=1e-4)
    assert np.allclose(impulse_energy(as16, as16), impulse_energy(x, x), atol=1e-4)


# ---------------------------------------------------------------------------------------------------------------------
# a click track
# ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("period,per_minute", [(0.5, 120), (0.75, 80), (0.3, 200)])
def test_every_click_is_found_once_with_the_rate_of_the_track(period, per_minute):
    left, right, clicks = click_track(30, period)
    result = measure_local_peaks(left, right, RATE)
    assert len(result.peaks) == len(clicks)
    assert near_clicks(result, clicks)
    got = samples_of(result)
    assert np.all(np.diff(got) > 0)  # ordered, none twice
    rates = rates_of(result)
    assert rates[0] == DEFAULT_RATE
    assert np.all(np.abs(rates[1:] - per_minute) <= 0.02 * per_minute)


def test_a_peak_is_at_the_first_sample_of_its_impulse_window_and_has_its_energy():
    left, right, clicks = click_track(10, 0.5)
    result = measure_local_peaks(left, right, RATE)
    energy = direct_energy(left, right)
    assert len(result.peaks) == len(clicks)
    for peak in result.peaks:
        assert isinstance(peak, LocalPeak)
        assert peak.sample % IMPULSE_SAMPLES == 0
        assert peak.energy == pytest.approx(energy[peak.sample // IMPULSE_SAMPLES])
        assert peak.window_min <= peak.energy <= peak.window_max


@pytest.mark.parametrize("window", [64, 256, 4096])
def test_the_minimum_and_maximum_energy_are_those_of_the_window_the_peak_was_found_in(window):
    left, right, clicks = click_track(12, 0.5, seed=11)
    result = measure_local_peaks(left, right, RATE, window=window)
    energy = direct_energy(left, right)
    assert result.peaks
    for peak in result.peaks:
        start, end = owning_window(peak.sample // IMPULSE_SAMPLES, len(energy), window)
        assert peak.window_min == pytest.approx(energy[start:end].min())
        assert peak.window_max == pytest.approx(energy[start:end].max())


def test_the_result_records_the_file_and_the_settings():
    left, right, _ = click_track(5, 0.5)
    result = measure_local_peaks(left, right, RATE, min_distance=250, prominence=30)
    assert isinstance(result, LocalPeaks)
    assert (result.file_rate, result.sample_count, result.min_distance, result.prominence) == (RATE, len(left), 250.0, 30.0)
    assert isinstance(result.peaks, tuple)


def test_the_rate_of_a_peak_is_60_over_the_seconds_since_the_previous_one():
    starts = [int(RATE * t) for t in (1.0, 1.4, 2.6, 3.1)]
    left, right = bursts(starts, [0.5] * 4, 4.0)
    result = measure_local_peaks(left, right, RATE)
    assert len(result.peaks) == 4
    got = samples_of(result)
    for peak, before in zip(result.peaks[1:], got[:-1]):
        assert peak.rate == pytest.approx(60 * RATE / (peak.sample - before))
    assert result.peaks[0].rate == 60.0


# ---------------------------------------------------------------------------------------------------------------------
# the minimum distance, across the borders of the windows' zones
# ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("stronger_first", [True, False])
@pytest.mark.parametrize("gap_ms", [20, 50, 90])
def test_two_bursts_closer_than_the_minimum_distance_give_only_the_stronger(stronger_first, gap_ms):
    first = 20000
    second = first + int(RATE * gap_ms / 1000)
    strengths = [0.6, 0.3] if stronger_first else [0.3, 0.6]
    left, right = bursts([first, second], strengths, 1.0)
    result = measure_local_peaks(left, right, RATE)
    assert len(result.peaks) == 1
    wanted = first if stronger_first else second
    assert abs(result.peaks[0].sample - wanted) <= IMPULSE_SAMPLES


@pytest.mark.parametrize("stronger_first", [True, False])
def test_the_minimum_distance_also_holds_across_the_border_between_two_zones(stronger_first):
    # 256 impulse samples per window, a step of 128: two bursts 136 impulse samples apart (a distance is 138) are never in
    # one window, the first is owned by the first window and the second by the next
    first, second = 127 * IMPULSE_SAMPLES, 263 * IMPULSE_SAMPLES
    strengths = [0.6, 0.3] if stronger_first else [0.3, 0.6]
    left, right = bursts([first, second], strengths, 0.5)
    result = measure_local_peaks(left, right, RATE, window=256)
    assert len(result.peaks) == 1
    assert result.peaks[0].sample == (first if stronger_first else second)


def test_the_longest_distance_also_holds_across_a_border_at_the_default_window():
    # 2000 ms is 2756 impulse samples, longer than a step of 2048: bursts 2700 apart are in no common window
    first, second = 2047 * IMPULSE_SAMPLES, 4747 * IMPULSE_SAMPLES
    left, right = bursts([first, second], [0.3, 0.6], 8.0)
    result = measure_local_peaks(left, right, RATE, min_distance=2000)
    assert [p.sample for p in result.peaks] == [second]


def test_bursts_farther_apart_than_the_distance_across_the_same_border_are_both_reported():
    first, second = 127 * IMPULSE_SAMPLES, 127 * IMPULSE_SAMPLES + 140 * IMPULSE_SAMPLES
    left, right = bursts([first, second], [0.6, 0.3], 0.5)
    result = measure_local_peaks(left, right, RATE, window=256)
    assert [p.sample for p in result.peaks] == [first, second]


@pytest.mark.parametrize("distance_ms", [100, 400, 1000, 2000])
def test_no_two_peaks_are_ever_closer_than_the_distance(distance_ms):
    rng = np.random.default_rng(12)
    starts = np.sort(rng.integers(5000, RATE * 20 - 5000, 120))
    left, right = bursts(starts, rng.uniform(0.2, 0.8, 120), 20.0)
    result = measure_local_peaks(left, right, RATE, min_distance=distance_ms, prominence=5)
    gaps = np.diff(samples_of(result)) / RATE * 1000
    assert len(result.peaks) > 1
    assert gaps.min() >= distance_ms - 1000 * IMPULSE_SAMPLES / RATE


# ---------------------------------------------------------------------------------------------------------------------
# windows
# ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("window", [64, 256, 4096])
def test_a_peak_in_two_overlapping_windows_is_reported_once(window):
    left, right, clicks = click_track(20, 0.5)
    result = measure_local_peaks(left, right, RATE, window=window)
    got = samples_of(result)
    assert len(got) == len(set(got.tolist())) == len(clicks)
    assert near_clicks(result, clicks)


def test_the_result_does_not_depend_on_the_size_of_the_peaks_window():
    left, right, clicks = click_track(30, 0.75)
    results = [measure_local_peaks(left, right, RATE, window=w) for w in (2048, 4096, 8192)]
    for other in results[1:]:
        assert samples_of(other).tolist() == samples_of(results[0]).tolist()
        assert [p.energy for p in other.peaks] == [p.energy for p in results[0].peaks]
        assert rates_of(other).tolist() == pytest.approx(rates_of(results[0]).tolist())
    assert len(results[0].peaks) == len(clicks)


@pytest.mark.parametrize("window", [8, 64, 256, 4096])
def test_the_zones_of_the_windows_tile_the_file(window):
    for count in list(range(0, 600, 7)) + [4095, 4096, 4097, 6144, 9000, 20001]:
        zones = list(lp.window_zones(count, window))
        assert (len(zones) == 0) == (count == 0)
        position = 0
        for number, (start, end, low, high) in enumerate(zones):
            assert low == position  # no gap and no overlap
            assert low < high or count == 0
            assert start <= low and high <= end
            assert start == number * window // 2 and end == min(start + window, count)
            if start > 0:
                assert low - start == window // 4  # at least a quarter window of context before a peak
            if end < count:
                assert end - high == window // 4  # and after it
            position = high
        assert position == count
        if zones:
            assert zones[-1][1] == count


def test_short_inputs_give_no_failure():
    for count in (0, 1, 31, 32, 33, 64, 95, 96, 100, 1000):
        rng = np.random.default_rng(count)
        x = rng.normal(0, 1, count)
        result = measure_local_peaks(x, x, RATE)
        assert isinstance(result, LocalPeaks)
        assert result.sample_count == count
        if count < 96:  # fewer than three impulse windows cannot hold a maximum with a lower point on each side
            assert result.peaks == ()


def test_a_file_shorter_than_the_peaks_window_is_measured_as_one_window():
    left, right, clicks = click_track(1.5, 0.3)  # about 2,000 impulse samples, a window is 4,096
    assert len(left) // IMPULSE_SAMPLES < 4096
    result = measure_local_peaks(left, right, RATE)
    assert len(result.peaks) == len(clicks)
    assert near_clicks(result, clicks)


def test_a_plateau_of_equal_energies_is_one_peak_at_its_middle():
    count = 100
    x = np.zeros(count * IMPULSE_SAMPLES)
    pattern = np.tile([1.0, -1.0], IMPULSE_SAMPLES // 2)  # a standard deviation of exactly the amplitude
    for i in range(count):
        x[i * IMPULSE_SAMPLES : (i + 1) * IMPULSE_SAMPLES] = pattern * (1.0 if 20 <= i <= 24 else 0.01)
    result = measure_local_peaks(x, x, RATE)
    assert [p.sample for p in result.peaks] == [22 * IMPULSE_SAMPLES]
    assert result.peaks[0].energy == pytest.approx(1.0)


# ---------------------------------------------------------------------------------------------------------------------
# silence, quiet files, determinism, mono and other rates
# ---------------------------------------------------------------------------------------------------------------------


def test_silence_has_no_peaks_and_does_not_fail():
    left, right = silence(10)
    result = measure_local_peaks(left, right, RATE)
    assert result.peaks == ()
    assert result.sample_count == len(left)


def test_a_very_quiet_file_has_the_same_peaks_as_a_loud_one():
    loud = click_track(15, 0.5, level=0.5, noise=0.005)
    quiet = click_track(15, 0.5, level=0.5e-4, noise=0.005e-4)
    a = measure_local_peaks(loud[0], loud[1], RATE)
    b = measure_local_peaks(quiet[0], quiet[1], RATE)
    assert samples_of(a).tolist() == samples_of(b).tolist()
    assert len(a.peaks) > 20
    assert b.peaks[0].energy == pytest.approx(a.peaks[0].energy * 1e-4)


def test_the_same_input_gives_the_same_result_and_is_not_changed():
    left, right, _ = click_track(15, 0.4)
    l0, r0 = left.copy(), right.copy()
    first = measure_local_peaks(left, right, RATE)
    second = measure_local_peaks(left, right, RATE)
    assert first == second
    assert np.array_equal(left, l0) and np.array_equal(right, r0)


def test_a_mono_file_gives_the_peaks_of_its_channel():
    left, _, clicks = click_track(15, 0.5)
    result = measure_local_peaks(left, left, RATE)
    assert len(result.peaks) == len(clicks)
    energy = direct_energy(left, left)
    assert result.peaks[3].energy == pytest.approx(energy[result.peaks[3].sample // IMPULSE_SAMPLES])


@pytest.mark.parametrize("rate", [22050, 44100, 48000])
def test_other_sample_rates_give_the_same_times(rate):
    left, right, clicks = click_track(20, 0.5, rate=rate)
    result = measure_local_peaks(left, right, rate)
    assert len(result.peaks) == len(clicks)
    assert near_clicks(result, clicks)
    assert np.all(np.abs(rates_of(result)[1:] - 120) <= 2.4)
    assert result.file_rate == rate


# ---------------------------------------------------------------------------------------------------------------------
# WAV files
# ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("rate", [22050, 48000])
@pytest.mark.parametrize("channels", [1, 2])
def test_measure_wav_gives_the_measurement_of_the_samples_that_are_read(tmp_path, rate, channels):
    left, right, _ = click_track(10, 0.5, rate=rate)
    data = np.round(np.stack([left, right][:channels], axis=1) * 20000).astype(np.int16)
    path = tmp_path / "clicks.wav"
    wavfile.write(path, rate, data if channels == 2 else data[:, 0])
    result = measure_wav(path)
    want_l = data[:, 0]
    want_r = data[:, 1] if channels == 2 else data[:, 0]
    assert result == measure_local_peaks(want_l, want_r, rate)
    assert len(result.peaks) > 15
    assert result.file_rate == rate


def test_measure_wav_passes_the_settings_on(tmp_path):
    left, right, _ = click_track(10, 0.3)
    path = tmp_path / "clicks.wav"
    wavfile.write(path, RATE, np.round(np.stack([left, right], axis=1) * 20000).astype(np.int16))
    short = measure_wav(path, min_distance=100)
    long = measure_wav(path, min_distance=800, prominence=40)
    assert (long.min_distance, long.prominence) == (800.0, 40.0)
    assert len(long.peaks) < len(short.peaks)


def test_measure_wav_reports_an_unreadable_file_as_the_analysis_does(tmp_path):
    path = tmp_path / "not-audio.wav"
    path.write_bytes(b"this is not a wav file")
    with pytest.raises(AudioAnalysisError):
        measure_wav(path)
    with pytest.raises(AudioAnalysisError, match="shown.wav"):
        measure_wav(path, display_name="shown.wav")


def test_measure_wav_checks_the_settings_before_reading(tmp_path):
    with pytest.raises(ValueError, match="minimum distance"):
        measure_wav(tmp_path / "missing.wav", min_distance=5)
    with pytest.raises(ValueError, match="prominence"):
        measure_wav(tmp_path / "missing.wav", prominence=500)


def test_the_module_uses_scipys_find_peaks():
    assert lp.find_peaks.__module__.startswith("scipy.signal")


# ---------------------------------------------------------------------------------------------------------------------
# the energy and the rate at any point
# ---------------------------------------------------------------------------------------------------------------------


def made(*peaks, rate=1000, count=10000):
    """A measurement with the given ``(sample, energy, rate)`` peaks, so that the answers are known exactly."""
    return LocalPeaks(tuple(LocalPeak(s, e, 0.0, 1.0, r) for s, e, r in peaks), rate, count, 100.0, 50.0)


THREE = made((1000, 0.2, 60.0), (3000, 0.8, 30.0), (4000, 0.4, 60.0))


def test_the_energy_at_the_sample_of_a_peak_is_its_energy():
    for sample, energy, _ in [(1000, 0.2, 0), (3000, 0.8, 0), (4000, 0.4, 0)]:
        assert THREE.energy_at(sample) == pytest.approx(energy)
        assert THREE.energy_at(float(sample)) == pytest.approx(energy)


def test_the_energy_between_two_peaks_is_the_straight_line_between_them():
    assert THREE.energy_at(2000) == pytest.approx(0.5)  # half way between 0.2 and 0.8
    assert THREE.energy_at(1500) == pytest.approx(0.2 + 0.6 * 0.25)
    assert THREE.energy_at(3500) == pytest.approx(0.6)  # falling: half way between 0.8 and 0.4
    assert THREE.energy_at(3900) == pytest.approx(0.8 - 0.4 * 0.9)
    for p in range(1001, 3000, 37):
        assert 0.2 < THREE.energy_at(p) < 0.8
    values = [THREE.energy_at(p) for p in range(1000, 3001, 10)]
    assert all(b > a for a, b in zip(values, values[1:]))


def test_before_the_first_peak_the_energy_is_zero_and_after_the_last_it_stays_at_the_last():
    for point in (0, 1, 500, 999, 999.5, -1, -10000, -1e9):
        assert THREE.energy_at(point) == 0.0
    for point in (4001, 4000.5, 9999, 10000, 123456, 1e9):
        assert THREE.energy_at(point) == pytest.approx(0.4)


def test_a_point_between_samples_and_a_time_give_the_same_answer_as_the_sample_position():
    assert THREE.energy_at(2250.5) == pytest.approx(0.2 + 0.6 * 1250.5 / 2000)
    assert THREE.energy_at_time(2.0) == pytest.approx(THREE.energy_at(2000))
    assert THREE.energy_at_time(1.2345) == pytest.approx(THREE.energy_at(1234.5))
    assert THREE.rate_at_time(3.5) == THREE.rate_at(3500) == 30.0
    other = made((22050, 0.5, 60.0), (44100, 1.0, 120.0), rate=22050, count=88200)
    assert other.energy_at_time(1.5) == pytest.approx(other.energy_at(33075)) == pytest.approx(0.75)


def test_the_rate_is_the_rate_of_the_previous_peak_and_is_not_interpolated():
    assert THREE.rate_at(1000) == 60.0
    assert THREE.rate_at(2999) == 60.0
    assert THREE.rate_at(3000) == 30.0  # at a peak: that peak's rate
    assert THREE.rate_at(3999.5) == 30.0
    assert THREE.rate_at(4000) == 60.0
    assert THREE.rate_at(9999) == 60.0 and THREE.rate_at(50000) == 60.0


def test_before_the_first_peak_the_rate_is_the_default_of_one_per_second():
    for point in (0, 999, 999.9, -5, -1e9):
        assert THREE.rate_at(point) == DEFAULT_RATE == 60.0
    odd = made((5000, 0.3, 77.0))
    assert odd.rate_at(4999) == 60.0 and odd.rate_at(5000) == 77.0


def test_a_measurement_without_peaks_answers_zero_energy_and_the_default_rate():
    left, right = silence(2)
    result = measure_local_peaks(left, right, RATE)
    assert result.peaks == ()
    for point in (0, 100, 5000, len(left) - 1, len(left) + 10, -3):
        assert result.energy_at(point) == 0.0
        assert result.rate_at(point) == 60.0
    assert result.energy_at_time(1.0) == 0.0 and result.rate_at_time(1.0) == 60.0
    assert result.energy_at([1, 2, 3]).tolist() == [0.0, 0.0, 0.0]
    assert result.rate_at([1, 2, 3]).tolist() == [60.0, 60.0, 60.0]


def test_a_single_peak_is_the_energy_after_it_and_zero_before():
    one = made((2000, 0.7, 60.0))
    assert one.energy_at(1999) == 0.0 and one.energy_at(2000) == 0.7 and one.energy_at(2001) == 0.7


def test_sequences_give_arrays_of_the_same_shape_and_scalars_give_floats():
    points = [0, 1000, 2000, 3500, 4000, 9000]
    want = [0.0, 0.2, 0.5, 0.6, 0.4, 0.4]
    for kind in (list, tuple, np.array):
        got = THREE.energy_at(kind(points))
        assert isinstance(got, np.ndarray) and got.dtype == np.float64
        assert got.tolist() == pytest.approx(want)
    grid = np.array([[0, 2000], [3500, 9000]])
    assert THREE.energy_at(grid).shape == (2, 2)
    assert np.allclose(THREE.energy_at(grid), [[0.0, 0.5], [0.6, 0.4]])
    assert THREE.rate_at(grid).tolist() == [[60.0, 60.0], [30.0, 60.0]]
    assert THREE.energy_at(np.array([])).shape == (0,)
    for scalar in (THREE.energy_at(2000), THREE.rate_at(2000), THREE.energy_at_time(1.0), THREE.rate_at_time(1.0), THREE.energy_at(np.int64(2000))):
        assert type(scalar) is float
    assert THREE.energy_at(np.float32(2000)) == pytest.approx(0.5)


def test_a_point_that_is_not_a_finite_number_is_refused():
    for bad in (float("nan"), float("inf"), -float("inf")):
        with pytest.raises(ValueError, match="The point must be a finite number."):
            THREE.energy_at(bad)
        with pytest.raises(ValueError, match="The point must be a finite number."):
            THREE.rate_at(bad)
        with pytest.raises(ValueError, match="The point must be a finite number."):
            THREE.energy_at_time(bad)
        with pytest.raises(ValueError, match="The point must be a finite number."):
            THREE.rate_at_time(bad)
        with pytest.raises(ValueError, match="The point must be a finite number."):
            THREE.energy_at([1.0, bad])
    with pytest.raises(ValueError, match="finite number"):
        THREE.energy_at("2000")
    with pytest.raises(ValueError, match="finite number"):
        THREE.energy_at(None)


def test_asking_does_not_change_the_measurement_and_is_deterministic():
    left, right, _ = click_track(10, 0.5)
    result = measure_local_peaks(left, right, RATE)
    before = result.peaks
    answers = [result.energy_at(p) for p in range(0, len(left), 4411)]
    assert result.peaks is before
    assert answers == [result.energy_at(p) for p in range(0, len(left), 4411)]
    with pytest.raises(Exception):
        result.peaks = ()  # frozen


def test_the_answers_at_the_peaks_of_a_click_track_match_the_recorded_peaks():
    left, right, clicks = click_track(20, 0.5)
    result = measure_local_peaks(left, right, RATE)
    for peak, nxt in zip(result.peaks, result.peaks[1:]):
        assert result.energy_at(peak.sample) == pytest.approx(peak.energy)
        assert result.rate_at(peak.sample) == pytest.approx(peak.rate)
        middle = (peak.sample + nxt.sample) // 2
        low, high = sorted((peak.energy, nxt.energy))
        assert low <= result.energy_at(middle) <= high
        assert result.rate_at(middle) == pytest.approx(peak.rate)
    assert result.energy_at(0) == 0.0
    assert result.energy_at(len(left) - 1) == pytest.approx(result.peaks[-1].energy)
    assert result.rate_at(0) == 60.0
    assert result.rate_at_time(10.2) == pytest.approx(120, rel=0.02)


def test_the_energy_of_every_frame_of_a_minute_is_one_fast_call():
    import time

    left, right, _ = click_track(60, 0.5)
    result = measure_local_peaks(left, right, RATE)
    frames = np.arange(1800) / 30.0
    start = time.perf_counter()
    energies = result.energy_at_time(frames)
    rates = result.rate_at_time(frames)
    assert time.perf_counter() - start < 0.5
    assert energies.shape == rates.shape == (1800,)
    assert energies[0] == 0.0 and rates[0] == 60.0
    assert energies.max() <= max(p.energy for p in result.peaks) + 1e-12


# ---------------------------------------------------------------------------------------------------------------------
# the two settings
# ---------------------------------------------------------------------------------------------------------------------

DISTANCE_MESSAGE = "The minimum distance must be a number from 100 to 2000 milliseconds."
PROMINENCE_MESSAGE = "The prominence must be a number from 0 to 100 percent."
WINDOW_MESSAGE = "The peaks window must be a whole number of at least 8 impulse samples."
SHAPE_MESSAGE = "The left and right channels must be one-dimensional and of the same length."


def aligned(seconds, rate=RATE):
    """The sample of a time, moved down to the start of an impulse window so that a burst falls in one window."""
    return int(rate * seconds) // IMPULSE_SAMPLES * IMPULSE_SAMPLES


class Spy:
    """Stands in for ``find_peaks`` in the module: records every call and gives the real answer."""

    def __init__(self):
        self.calls = []

    def __call__(self, x, **kwargs):
        self.calls.append((np.array(x), kwargs))
        return real_find_peaks(x, **kwargs)


@pytest.fixture
def spy(monkeypatch):
    recorder = Spy()
    monkeypatch.setattr(lp, "find_peaks", recorder)
    return recorder


def test_the_defaults_are_100_milliseconds_and_50_percent():
    assert (lp.DEFAULT_MIN_DISTANCE, lp.DEFAULT_PROMINENCE) == (100.0, 50.0)
    signature = inspect.signature(measure_local_peaks).parameters
    assert signature["min_distance"].default == 100.0 and signature["prominence"].default == 50.0
    assert signature["window"].default == lp.PEAKS_WINDOW == 4096
    assert (lp.MIN_MIN_DISTANCE, lp.MAX_MIN_DISTANCE, lp.MIN_PROMINENCE, lp.MAX_PROMINENCE) == (100.0, 2000.0, 0.0, 100.0)
    left, right, _ = click_track(5, 0.5)
    result = measure_local_peaks(left, right, RATE)
    assert (result.min_distance, result.prominence) == (100.0, 50.0)


@pytest.mark.parametrize("value", [100, 100.0, 100.5, 1000, 2000, 1999.9, np.float64(500), np.int32(300)])
def test_a_minimum_distance_from_100_to_2000_is_accepted_as_a_float(value):
    got = lp.check_min_distance(value)
    assert got == float(value) and type(got) is float


@pytest.mark.parametrize("value", [99.9, 0, -100, 2000.1, 5000, float("nan"), float("inf"), -float("inf"), None, True, False, "300", [300], (300,)])
def test_a_minimum_distance_outside_the_range_or_not_a_number_is_refused(value):
    with pytest.raises(ValueError) as error:
        lp.check_min_distance(value)
    assert str(error.value) == DISTANCE_MESSAGE


@pytest.mark.parametrize("value", [0, 0.0, -0.0, 10, 50, 99.5, 100, np.float64(80), np.int64(25)])
def test_a_prominence_from_0_to_100_is_accepted_as_a_float(value):
    got = lp.check_prominence(value)
    assert got == float(value) and type(got) is float
    assert str(got) != "-0.0"


@pytest.mark.parametrize("value", [-0.1, -1, 100.1, 101, 1000, float("nan"), float("inf"), -float("inf"), None, True, False, "50", [50]])
def test_a_prominence_outside_the_range_or_not_a_number_is_refused(value):
    with pytest.raises(ValueError) as error:
        lp.check_prominence(value)
    assert str(error.value) == PROMINENCE_MESSAGE


def test_bad_settings_and_bad_input_are_refused_before_anything_is_measured(spy):
    left, right, _ = click_track(3, 0.5)
    for kwargs, message in [
        ({"min_distance": 50}, DISTANCE_MESSAGE),
        ({"min_distance": 2500}, DISTANCE_MESSAGE),
        ({"min_distance": "100"}, DISTANCE_MESSAGE),
        ({"prominence": -1}, PROMINENCE_MESSAGE),
        ({"prominence": 101}, PROMINENCE_MESSAGE),
        ({"prominence": float("nan")}, PROMINENCE_MESSAGE),
        ({"window": 7}, WINDOW_MESSAGE),
        ({"window": True}, WINDOW_MESSAGE),
        ({"window": 100.5}, WINDOW_MESSAGE),
    ]:
        with pytest.raises(ValueError) as error:
            measure_local_peaks(left, right, RATE, **kwargs)
        assert str(error.value) == message
    for rate in (0, -44100, 44100.5, True, "44100", None):
        with pytest.raises(ValueError) as error:
            measure_local_peaks(left, right, rate)
        assert str(error.value) == "The sample rate must be a positive whole number."
    for a, b in [(left, right[:-1]), (left.reshape(-1, 1), right.reshape(-1, 1)), (left, "abc"), (None, right), (left, np.zeros(len(left), dtype=complex))]:
        with pytest.raises(ValueError) as error:
            measure_local_peaks(a, b, RATE)
        assert str(error.value) == SHAPE_MESSAGE
    assert spy.calls == []  # find_peaks was never reached


@pytest.mark.parametrize(
    "rate,ms,expected",
    [(44100, 100, 138), (44100, 2000, 2756), (8000, 100, 25), (22050, 100, 69), (48000, 100, 150), (11025, 250, 86), (100, 100, 1), (44100, 100.5, 139)],
)
def test_the_minimum_distance_is_converted_to_impulse_samples(spy, rate, ms, expected):
    rng = np.random.default_rng(rate)
    x = rng.normal(0, 1, max(rate // 2, 640))
    measure_local_peaks(x, x, rate, min_distance=ms)
    assert spy.calls
    assert {call[1]["distance"] for call in spy.calls} == {expected}
    assert expected == max(1, round(ms / 1000 * rate / IMPULSE_SAMPLES))


def test_the_prominence_is_the_percentage_of_the_largest_energy_of_each_window(spy):
    starts = [aligned(0.5 * i + 0.3) for i in range(1, 80)]
    left, right = bursts(starts, np.linspace(0.2, 1.0, len(starts)), 41.0)
    for percent in (0, 10, 50, 100):
        spy.calls.clear()
        measure_local_peaks(left, right, RATE, prominence=percent)
        assert len(spy.calls) >= 8  # several windows
        tops = set()
        for window, kwargs in spy.calls:
            assert kwargs["prominence"] == pytest.approx(percent / 100 * window.max())
            tops.add(round(float(window.max()), 6))
        assert len(tops) >= 4  # each window has its own maximum, and its own prominence


def test_the_windows_handed_to_find_peaks_are_the_running_windows_of_the_energy(spy):
    left, right, _ = click_track(10, 0.5)
    measure_local_peaks(left, right, RATE, window=1024)
    energy = direct_energy(left, right)
    starts = [start for start, *_ in lp.window_zones(len(energy), 1024)]
    assert len(spy.calls) == len(starts) > 5
    for (part, _), start in zip(spy.calls, starts):
        assert np.allclose(part, energy[start : start + 1024])


@pytest.mark.parametrize("rate,ms", [(44100, 100), (44100, 700), (22050, 100), (48000, 2000), (8000, 250)])
def test_a_file_in_one_window_gives_exactly_what_find_peaks_gives_on_its_energy(rate, ms):
    rng = np.random.default_rng(ms)
    count = 4000 * IMPULSE_SAMPLES  # 4,000 impulse samples: less than one peaks window
    loudness = rng.uniform(0.1, 2, count // 700 + 1).repeat(700)[:count]
    left, right = rng.normal(0, 1, count) * loudness, rng.normal(0, 1, count)
    energy = direct_energy(left, right)
    assert len(energy) <= 4096
    for percent in (0, 25, 75):
        wanted, _ = real_find_peaks(energy, distance=max(1, round(ms / 1000 * rate / 32)), prominence=percent / 100 * energy.max())
        got = measure_local_peaks(left, right, rate, min_distance=ms, prominence=percent)
        assert (samples_of(got) // 32).tolist() == wanted.tolist()


def test_a_longer_distance_gives_fewer_peaks_and_never_two_closer_than_it():
    left, right, clicks = click_track(30, 0.3)
    counts = []
    for ms in (100, 500, 2000):
        result = measure_local_peaks(left, right, RATE, min_distance=ms)
        counts.append(len(result.peaks))
        gaps = np.diff(samples_of(result)) * 1000 / RATE
        assert gaps.min() >= ms - 1000 * IMPULSE_SAMPLES / RATE
    assert counts[0] == len(clicks) and counts[0] > counts[1] > counts[2] >= 1


def test_a_distance_longer_than_the_file_gives_at_most_one_peak():
    left, right, clicks = click_track(1.5, 0.3)
    assert len(clicks) >= 3
    result = measure_local_peaks(left, right, RATE, min_distance=2000)
    assert len(result.peaks) == 1


@pytest.mark.parametrize("bump,kept", [(0.4, {10: True, 50: False, 90: False}), (0.7, {10: True, 50: True, 90: False})])
def test_bumps_lower_than_the_prominence_share_of_the_loudest_are_dropped_and_the_click_stays(bump, kept):
    # a 2.9 second file is one peaks window, so the share is of the click's energy for every bump
    click = aligned(1.5)
    bump_starts = [aligned(0.5), aligned(1.0), aligned(2.2)]
    left, right = bursts([click, *bump_starts], [1.0, bump, bump, bump], 2.9)
    for percent, bumps_kept in kept.items():
        result = measure_local_peaks(left, right, RATE, prominence=percent)
        got = samples_of(result).tolist()
        assert click in got  # a click above the share is always reported
        for b in bump_starts:
            assert (b in got) == bumps_kept, (percent, b)
        assert len(got) == 1 + (len(bump_starts) if bumps_kept else 0)


def test_a_prominence_of_zero_reports_every_bump_and_100_needs_a_background_of_exact_zero():
    starts = [aligned(0.2 * i) for i in range(1, 14)]
    strengths = [1.0 if i == 6 else 0.1 + 0.02 * i for i in range(1, 14)]
    left, right = bursts(starts, strengths, 2.9)
    every = measure_local_peaks(left, right, RATE, prominence=0)
    half = measure_local_peaks(left, right, RATE, prominence=50)
    assert set(starts) <= set(samples_of(every).tolist())  # every bump, and the ripples of the noise between them
    assert len(every.peaks) > len(starts)
    assert samples_of(half).tolist() == [starts[5]]
    # nothing stands out by the whole of the largest energy when there is noise under the click
    assert measure_local_peaks(left, right, RATE, prominence=100).peaks == ()
    # on exact silence the click stands out by all of its energy, and the share of 100 is reached
    quiet_left, quiet_right = np.zeros(len(left)), np.zeros(len(right))
    for start, strength in zip(starts, strengths):
        quiet_left[start : start + 16] = strength * np.where(np.arange(16) % 2 == 0, 1.0, -1.0)
        quiet_right[start : start + 16] = quiet_left[start : start + 16]
    top = measure_local_peaks(quiet_left, quiet_right, RATE, prominence=100)
    assert samples_of(top).tolist() == [starts[5]]


def test_more_distance_or_more_prominence_never_gives_more_peaks():
    rng = np.random.default_rng(15)
    starts = np.sort(rng.integers(5000, RATE * 20 - 5000, 150))
    left, right = bursts(starts, rng.uniform(0.1, 0.9, 150), 20.0)
    by_distance = [len(measure_local_peaks(left, right, RATE, min_distance=ms, prominence=5).peaks) for ms in (100, 250, 500, 1000, 2000)]
    by_prominence = [len(measure_local_peaks(left, right, RATE, prominence=p).peaks) for p in (0, 10, 30, 50, 80, 100)]
    assert by_distance == sorted(by_distance, reverse=True) and by_distance[0] > by_distance[-1]
    assert by_prominence == sorted(by_prominence, reverse=True) and by_prominence[0] > by_prominence[-1]
