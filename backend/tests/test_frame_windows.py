"""Which analysis windows belong to which frame (feature 034): ``frame_windows``, shared with ``average_frames``."""

import numpy as np
import pytest

from app.services.frame_rendering import average_frames, frame_count, frame_windows
from app.services.note_analysis import NOTE_COUNT, AnalysisResult

SR = 100.0


def result_of(values, step):
    values = np.asarray(values, dtype=np.float64)
    return AnalysisResult(sample_rate=SR, window_size=10, frames=values, sample_count=int(len(values) * step), step=float(step))


@pytest.mark.parametrize("step", [5, 10, 20, 7.5])
def test_every_window_belongs_to_exactly_one_frame(step):
    windows = 30
    result = result_of(np.zeros((windows, NOTE_COUNT)), step)
    frames = frame_count(result.sample_count, SR, 5)
    first, stop, earlier = frame_windows(result, 5, frames)
    assert first.shape == stop.shape == earlier.shape == (frames,)
    assert first[0] == 0 and stop[-1] == windows
    assert (stop[:-1] == first[1:]).all()
    assert (stop >= first).all()
    assert (earlier == np.maximum(first - 1, 0)).all()


def test_a_frame_owns_the_windows_that_start_in_its_period():
    result = result_of(np.zeros((6, NOTE_COUNT)), 40)  # a window every 40 samples; a frame is 20 samples
    first, stop, _ = frame_windows(result, 5, 12)
    assert (stop - first).tolist() == [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]


@pytest.mark.parametrize("step", [5, 20, 7.5])
def test_average_frames_is_the_mean_of_the_owned_windows_or_the_window_before(step):
    rng = np.random.default_rng(1)
    values = rng.random((20, NOTE_COUNT))
    result = result_of(values, step)
    frames = frame_count(result.sample_count, SR, 5)
    got = average_frames(result, 5, frames)
    first, stop, earlier = frame_windows(result, 5, frames)
    for i in range(frames):
        want = values[first[i] : stop[i]].mean(axis=0) if stop[i] > first[i] else values[earlier[i]]
        assert np.allclose(got[i], want, rtol=1e-12, atol=1e-12)


def test_no_frames_or_no_windows_give_empty_arrays():
    result = result_of(np.zeros((0, NOTE_COUNT)), 10)
    for arrays in (frame_windows(result, 5, 0), frame_windows(result, 5, 3)):
        assert all(a.dtype.kind == "i" for a in arrays)
    assert all(a.shape == (0,) for a in frame_windows(result, 5, 0))
    assert all(a.shape == (3,) for a in frame_windows(result, 5, 3))
