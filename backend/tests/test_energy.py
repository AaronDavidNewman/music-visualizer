"""Energy: the overall intensity of the audio in each frame, measured in short internal windows."""

import math
import statistics

import numpy as np
import pytest

from app.services.energy import (
    INTERNAL_WINDOW_AT_44K,
    REFERENCE_RATE,
    frame_energies,
    internal_window,
)

RATE = 44100


def alternating(count: int, amplitude: float) -> np.ndarray:
    """+a, -a, +a, ... (its population standard deviation is exactly ``amplitude``)."""
    return amplitude * np.where(np.arange(count) % 2 == 0, 1.0, -1.0)


def reference_energies(left, right, sample_rate, frame_rate, frames) -> list[float]:
    """The definition written out plainly, with loops and the standard library, as an independent check."""
    left = [float(x) for x in left]
    right = [float(x) for x in right]
    window = max(2, math.floor(32 * sample_rate / 44100 + 0.5))
    out = []
    for f in range(frames):
        start = int(np.rint(f * sample_rate / frame_rate))
        end = min(int(np.rint((f + 1) * sample_rate / frame_rate)), len(left))
        n = (end - start) // window
        spans = [(start + j * window, start + (j + 1) * window) for j in range(n)]
        if n == 0:
            spans = [(start, max(start, end))]
        values = []
        for a, b in spans:
            sl, sr = left[a:b], right[a:b]
            values.append(((statistics.pstdev(sl) if len(sl) else 0.0) + (statistics.pstdev(sr) if len(sr) else 0.0)) / 2)
        out.append(sum(values) / len(values))
    return out


# --- the internal window ---------------------------------------------------------------------------------------------


def test_constants_are_the_ones_in_the_request():
    assert INTERNAL_WINDOW_AT_44K == 32
    assert REFERENCE_RATE == 44100


@pytest.mark.parametrize(
    "rate, expected",
    [(44100, 32), (48000, 35), (22050, 16), (11025, 8), (96000, 70), (32000, 23), (16000, 12)],
)
def test_internal_window_scales_with_the_sample_rate(rate, expected):
    assert internal_window(rate) == expected


def test_internal_window_is_never_below_two_samples():
    assert internal_window(100) == 2
    assert internal_window(1) == 2


def test_internal_window_rounds_halves_up():
    # 32 * 44100 / 44100 = 32 exactly; pick a rate where the proportional value is x.5: 32 * r / 44100 = 16.5.
    assert internal_window(22739.0625) == 17


# --- the energy of a frame -------------------------------------------------------------------------------------------


def test_both_channels_alternating_gives_the_amplitude():
    x = alternating(RATE, 0.5)
    energy = frame_energies(x, x.copy(), RATE, 30, 30)
    assert energy.shape == (30,)
    assert energy.dtype == np.float64
    assert energy == pytest.approx(0.5, abs=0.001)


def test_one_silent_channel_halves_the_energy():
    left = alternating(RATE, 0.5)
    energy = frame_energies(left, np.zeros(RATE), RATE, 30, 30)
    assert energy == pytest.approx(0.25, abs=0.001)


def test_a_constant_level_has_no_energy_however_large():
    for level in (0.0, 0.3, 0.9, -0.7):
        x = np.full(RATE, level)
        assert frame_energies(x, x.copy(), RATE, 30, 30) == pytest.approx(0.0, abs=1e-12)


def test_a_dc_offset_does_not_add_energy():
    x = alternating(RATE, 0.25) + 0.5  # still spread 0.25, shifted up
    assert frame_energies(x, x.copy(), RATE, 30, 30) == pytest.approx(0.25, abs=0.001)


def test_a_mono_signal_gives_its_own_spread():
    x = alternating(RATE, 0.4)
    stereo = frame_energies(x, x.copy(), RATE, 30, 30)
    mono = frame_energies(x, x, RATE, 30, 30)  # the same array for both channels, as read_wav returns for mono
    assert mono == pytest.approx(0.4, abs=0.001)
    assert np.array_equal(mono, stereo)


def test_the_frame_energy_is_the_mean_over_its_internal_windows():
    # A frame period of exactly 64 samples holds two 32-sample windows: spread 0.5 and spread 0.1.
    period = 64
    frame = np.concatenate([alternating(32, 0.5), alternating(32, 0.1)])
    energy = frame_energies(frame, frame.copy(), RATE, RATE / period, 1)
    assert energy[0] == pytest.approx(0.3, abs=1e-9)


def test_windows_are_laid_end_to_end_from_each_frames_first_sample():
    # Two frames of 64 samples. Frame 1's first window starts at sample 64, not at a multiple of the window
    # counted from a different origin; it is a constant block then an alternating one.
    first = np.concatenate([alternating(32, 0.5), alternating(32, 0.5)])
    second = np.concatenate([np.zeros(32), alternating(32, 0.2)])
    x = np.concatenate([first, second])
    energy = frame_energies(x, x.copy(), RATE, RATE / 64, 2)
    assert energy[0] == pytest.approx(0.5, abs=1e-9)
    assert energy[1] == pytest.approx(0.1, abs=1e-9)


def test_a_leftover_shorter_than_a_window_is_ignored_when_a_full_window_exists():
    # A period of 80 samples: two full windows (64 samples) and 16 left over. The leftover is wild; it must not count.
    period = 80
    frame = np.concatenate([alternating(64, 0.5), np.linspace(-1.0, 1.0, 16) * 37.0])
    energy = frame_energies(frame, frame.copy(), RATE, RATE / period, 1)
    assert energy[0] == pytest.approx(0.5, abs=1e-9)


def test_frames_tile_the_file_with_boundaries_at_the_nearest_sample():
    rng = np.random.default_rng(7)
    left = rng.uniform(-1, 1, 20000)
    right = rng.uniform(-1, 1, 20000) * 0.5
    frame_rate = 29.97  # a non-integer period of 1471.47 samples
    frames = math.ceil(20000 * frame_rate / RATE)
    got = frame_energies(left, right, RATE, frame_rate, frames)
    assert got == pytest.approx(reference_energies(left, right, RATE, frame_rate, frames), rel=1e-9)


@pytest.mark.parametrize("rate, frame_rate", [(44100, 30), (48000, 24), (22050, 60), (11025, 7.5)])
def test_agrees_with_an_independent_reference_at_several_rates(rate, frame_rate):
    rng = np.random.default_rng(rate)
    n = rate // 2
    left = rng.normal(0, 0.2, n)
    right = rng.normal(0, 0.05, n)
    frames = math.ceil(n * frame_rate / rate)
    got = frame_energies(left, right, rate, frame_rate, frames)
    assert got == pytest.approx(reference_energies(left, right, rate, frame_rate, frames), rel=1e-9)


def test_integer_samples_are_scaled_to_about_minus_one_to_one():
    # int16 full scale is 32768, so +-16384 is the same as +-0.5.
    x = alternating(RATE, 16384).astype(np.int16)
    assert frame_energies(x, x.copy(), RATE, 30, 30) == pytest.approx(0.5, abs=0.001)


def test_the_result_is_deterministic():
    rng = np.random.default_rng(3)
    left = rng.normal(0, 0.3, RATE)
    right = rng.normal(0, 0.3, RATE)
    a = frame_energies(left, right, RATE, 30, 30)
    b = frame_energies(left, right, RATE, 30, 30)
    assert np.array_equal(a, b)


def test_it_returns_one_value_per_requested_frame():
    x = alternating(RATE, 0.5)
    assert frame_energies(x, x.copy(), RATE, 30, 30).shape == (30,)
    assert frame_energies(x, x.copy(), RATE, 30, 0).shape == (0,)


# --- sample rate, sample format, channels and short frames (user story 3) --------------------------------------------


def modulated_noise(rate, amplitudes, seed=11):
    """Uniform noise in blocks of 0.1 s, each block with its own amplitude (so the spread is proportional to it)."""
    rng = np.random.default_rng(seed)
    block = rate // 10
    return np.concatenate([rng.uniform(-a, a, block) for a in amplitudes])


AMPLITUDES = [0.8, 0.2, 0.5, 0.1, 0.8, 0.0, 0.4, 0.6, 0.3, 0.7]


def test_the_same_sound_at_two_sample_rates_has_the_same_brightness():
    from app.services.frame_rendering import value_sequence

    results = {}
    for rate in (44100, 22050, 48000):
        x = modulated_noise(rate, AMPLITUDES)
        energies = frame_energies(x, x.copy(), rate, 10, len(AMPLITUDES))  # one frame per 0.1 s block
        results[rate] = value_sequence(energies)
    assert results[22050] == pytest.approx(results[44100], abs=0.05)
    assert results[48000] == pytest.approx(results[44100], abs=0.05)
    assert results[44100].max() == 1.0  # the loudest block, whichever of the two equal-amplitude ones is a little louder
    assert results[44100][5] == pytest.approx(0.0, abs=1e-9)  # the silent block


def test_the_same_audio_in_any_sample_format_has_the_same_energy():
    rng = np.random.default_rng(12)
    audio = rng.uniform(-0.8, 0.8, RATE // 2)
    reference = frame_energies(audio, audio.copy(), RATE, 30, 15)
    formats = {
        "uint8": (np.round(audio * 128 + 128).astype(np.uint8), 0.01),
        "int16": (np.round(audio * 32768).astype(np.int16), 1e-3),
        "int32": (np.round(audio * 2147483648.0).astype(np.int32), 1e-6),
        "float32": (audio.astype(np.float32), 1e-6),
    }
    for name, (samples, tolerance) in formats.items():
        got = frame_energies(samples, samples.copy(), RATE, 30, 15)
        assert got == pytest.approx(reference, abs=tolerance), name


def test_one_loud_channel_has_half_the_energy_of_the_same_signal_in_both():
    rng = np.random.default_rng(13)
    x = rng.uniform(-0.5, 0.5, RATE)
    both = frame_energies(x, x.copy(), RATE, 30, 30)
    one = frame_energies(x, np.zeros(RATE), RATE, 30, 30)
    assert one == pytest.approx(both / 2, rel=1e-9)


def test_a_frame_shorter_than_one_internal_window_is_measured_without_error():
    rng = np.random.default_rng(14)
    left = rng.uniform(-1, 1, 4000)
    right = rng.uniform(-1, 1, 4000)
    frame_rate = 5000  # a period of about 9 samples against a window of 32
    frames = math.ceil(4000 * frame_rate / RATE)
    got = frame_energies(left, right, RATE, frame_rate, frames)
    assert got.shape == (frames,)
    assert np.isfinite(got).all() and (got >= 0).all()
    assert got == pytest.approx(reference_energies(left, right, RATE, frame_rate, frames), rel=1e-9)


def test_a_final_frame_with_fewer_samples_than_a_window_measures_the_samples_it_has():
    x = np.concatenate([alternating(RATE, 0.25), alternating(20, 0.5)])  # frame 30 holds 20 samples
    frames = math.ceil(len(x) * 30 / RATE)
    assert frames == 31
    energy = frame_energies(x, x.copy(), RATE, 30, frames)
    assert energy[0] == pytest.approx(0.25, abs=1e-9)
    assert energy[30] == pytest.approx(0.5, abs=1e-9)


def test_a_frame_with_one_sample_or_none_has_no_energy():
    x = np.concatenate([alternating(RATE, 0.25), [0.9]])  # frame 30 holds a single sample
    energy = frame_energies(x, x.copy(), RATE, 30, 33)  # frames 31 and 32 start past the end
    assert energy[30] == 0.0
    assert energy[31] == 0.0 and energy[32] == 0.0
    assert energy[0] == pytest.approx(0.25, abs=1e-9)


def test_unusable_arguments_are_refused():
    x = alternating(100, 0.5)
    for bad in (0, -1, float("nan"), float("inf"), True, "44100", None):
        with pytest.raises(ValueError):
            frame_energies(x, x.copy(), bad, 30, 1)
        with pytest.raises(ValueError):
            frame_energies(x, x.copy(), RATE, bad, 1)
    for bad in (-1, 1.5, True, None):
        with pytest.raises(ValueError):
            frame_energies(x, x.copy(), RATE, 30, bad)
    with pytest.raises(ValueError):
        frame_energies(x, x[:50], RATE, 30, 1)
    with pytest.raises(ValueError):
        frame_energies(np.ones((10, 2)), np.ones((10, 2)), RATE, 30, 1)
