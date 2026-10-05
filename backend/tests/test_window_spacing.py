import math

import numpy as np
import pytest

from app.services.note_analysis import window_starts
from app.services.window_spacing import default_spacing, resolve_step

# Shared with frontend/src/lib/spacing.test.ts: (sample_rate, frame_rate, window_size, expected)
DEFAULT_TABLE = [
    (44100, 30, 4096, 0.358886),
    (44100, 60, 4096, 0.179443),
    (44100, 60, 8192, 0.089721),
    (48000, 30, 4096, 0.390625),
    (44100, 30, 32768, 0.044860),
]


@pytest.mark.parametrize("sample_rate, frame_rate, window_size, expected", DEFAULT_TABLE)
def test_default_spacing_table(sample_rate, frame_rate, window_size, expected):
    assert default_spacing(sample_rate, frame_rate, window_size) == pytest.approx(expected, abs=1e-12)


def test_default_is_rounded_down_never_longer_than_a_frame_period():
    for sample_rate in (44100, 48000):
        for frame_rate in (1, 7, 24, 29.97, 30, 60):
            for window_size in (4096, 8192, 16384, 32768):
                spacing = default_spacing(sample_rate, frame_rate, window_size)
                assert spacing * window_size <= sample_rate / frame_rate + 1e-9


def test_default_gives_every_frame_period_a_window_start():
    """With the default spacing every frame period holds the exact start (k * step) of a window.

    Exact positions are what frames are assigned by; the rounded start samples only choose which
    audio to read. Non-integer frame periods (44100 / 11 fps, ...) are included on purpose.
    """
    for sample_rate in (44100, 48000):
        for frame_rate in list(range(1, 61)) + [29.97]:
            for window_size in (4096, 8192, 16384, 32768):
                spacing = default_spacing(sample_rate, frame_rate, window_size)
                _, step, _ = resolve_step(spacing, window_size)
                total = sample_rate * 20
                nominal = np.arange(len(window_starts(total, step))) * step
                period = sample_rate / frame_rate
                frames = math.ceil(total / period - 1e-9)
                owner = np.floor((nominal + 1e-6) / period).astype(int)
                # The final frame is exempt: when the audio ends within half a sample of its only
                # candidate window start, that window would begin past the end (all silence), so the
                # frame uses the earlier window instead.
                assert set(owner) >= set(range(frames - 1)), (sample_rate, frame_rate, window_size)


def test_resolve_step():
    assert resolve_step(0.25, 8192) == (0.25, 2048.0, False)
    assert resolve_step(1, 4096) == (1, 4096.0, False)
    assert resolve_step(2, 4096) == (2, 8192.0, False)
    assert resolve_step(0.00001, 4096) == (1 / 4096, 1.0, True)


def test_exactly_one_sample_is_not_raised():
    assert resolve_step(1 / 4096, 4096) == (1 / 4096, 1.0, False)


def test_non_integer_step_is_kept():
    spacing, step, raised = resolve_step(0.3, 4096)
    assert (spacing, raised) == (0.3, False)
    assert step == pytest.approx(1228.8)
