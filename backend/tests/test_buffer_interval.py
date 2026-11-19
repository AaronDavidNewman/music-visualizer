"""The fixed 60 ms step between frequency buffers (feature 043): ``buffer_step()``."""

import numpy as np
import pytest

from app.services.buffer_interval import BUFFER_INTERVAL_MS, buffer_step
from app.services.note_analysis import window_count, window_starts


def test_the_interval_is_60_ms():
    assert BUFFER_INTERVAL_MS == 60


@pytest.mark.parametrize(
    "sample_rate, step",
    [(8000, 480.0), (11025, 661.5), (22050, 1323.0), (44100, 2646.0), (48000, 2880.0), (96000, 5760.0)],
)
def test_the_step_is_60_ms_in_samples(sample_rate, step):
    assert buffer_step(sample_rate) == step
    assert buffer_step(sample_rate) / sample_rate == pytest.approx(0.060, abs=1e-12)


def test_the_usual_rates_give_exact_numbers_with_no_floating_point_noise():
    assert buffer_step(44100) == 2646.0
    assert buffer_step(48000) == 2880.0


def test_the_step_depends_on_nothing_but_the_sample_rate():
    assert buffer_step(44100) == buffer_step(44100.0)
    assert isinstance(buffer_step(44100), float)


def test_a_step_under_one_sample_is_raised_to_one():
    assert buffer_step(10) == 1.0
    assert buffer_step(16) == 1.0
    assert buffer_step(17) > 1.0


@pytest.mark.parametrize("sample_rate", [8000, 11025, 22050, 44100, 48000])
def test_every_buffer_starts_within_half_a_sample_of_its_exact_place(sample_rate):
    """SC-002: the time between neighbouring buffers is 60 ms to within one sample."""
    step = buffer_step(sample_rate)
    samples = sample_rate * 5
    starts = window_starts(samples, step)
    exact = np.arange(starts.size) * step
    assert np.abs(starts - exact).max() <= 0.5
    gaps = np.diff(starts)
    assert gaps.min() >= np.floor(step) and gaps.max() <= np.ceil(step)
    assert window_count(samples, step) == starts.size
    assert starts.size == pytest.approx(5 / 0.06, abs=1)


def test_a_file_shorter_than_the_interval_has_one_buffer():
    assert window_count(1000, buffer_step(44100)) == 1
