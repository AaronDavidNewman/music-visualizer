import numpy as np
import pytest
from PIL import Image

from app.services.frame_rendering import (
    GRID_COLUMNS,
    GRID_ROWS,
    SQUARE_PIXELS,
    average_frames,
    frame_count,
    render_frame,
    to_gray_levels,
    write_frames,
)
from app.services.note_analysis import AnalysisResult


def result_with_rows(values, sample_rate, window_size, sample_count):
    """AnalysisResult whose window i has every note equal to values[i]."""
    frames = np.repeat(np.asarray(values, dtype=float)[:, None], 88, axis=1)
    return AnalysisResult(sample_rate, window_size, frames, sample_count)


def test_frame_count_rounds_up():
    assert frame_count(441000, 44100, 30) == 300  # exactly 10 s
    assert frame_count(441441, 44100, 30) == 301  # a little over
    assert frame_count(1, 44100, 30) == 1
    assert frame_count(0, 44100, 30) == 0


def test_average_several_windows_per_frame():
    # windows start every 0.1 s; 5 fps -> 0.2 s frames -> two windows each
    r = result_with_rows([0, 1, 2, 3, 4, 5], 100, 10, 60)
    out = average_frames(r, 5, frame_count(60, 100, 5))
    assert out.shape == (3, 88)
    assert out[:, 0].tolist() == [0.5, 2.5, 4.5]


def test_window_longer_than_frame_uses_covering_window():
    # windows are 0.4 s, frames 0.2 s: odd frames have no window start in their period
    r = result_with_rows([10, 20, 30], 100, 40, 120)
    n = frame_count(120, 100, 5)
    assert n == 6
    assert average_frames(r, 5, n)[:, 0].tolist() == [10, 10, 20, 20, 30, 30]


def test_last_partial_period_is_kept():
    # 1.1 s of audio at 5 fps -> 6 frames; the last frame covers only 0.1 s
    r = result_with_rows(np.arange(11), 100, 10, 110)
    n = frame_count(110, 100, 5)
    assert n == 6
    out = average_frames(r, 5, n)
    assert out[5, 0] == 10  # only window 10 starts in [1.0, 1.2)


def test_gray_levels_scale_to_file_maximum():
    frames = np.zeros((2, 88))
    frames[0, 0] = 50
    frames[1, 1] = 100
    levels = to_gray_levels(frames)
    assert levels.dtype == np.uint8
    assert levels[1, 1] == 255
    assert levels[0, 0] == 128  # round(255 * 50 / 100)
    assert levels[0, 1] == 0


def test_all_zero_input_is_black():
    assert not to_gray_levels(np.zeros((3, 88))).any()


def test_grid_layout_and_size():
    levels = np.arange(88, dtype=np.uint8) * 2
    img = render_frame(levels)
    assert img.mode == "L"
    assert img.size == (GRID_COLUMNS * SQUARE_PIXELS, GRID_ROWS * SQUARE_PIXELS) == (220, 160)
    arr = np.asarray(img)
    for n in (0, 10, 11, 43, 87):
        row, col = divmod(n, GRID_COLUMNS)
        square = arr[row * 20:(row + 1) * 20, col * 20:(col + 1) * 20]
        assert (square == levels[n]).all(), n  # whole square is one gray level


def test_write_frames_names_and_determinism(tmp_path):
    frames = np.random.default_rng(0).random((3, 88))
    a, b = tmp_path / "a", tmp_path / "b"
    write_frames(frames, a)
    write_frames(frames, b)
    names = sorted(p.name for p in a.iterdir())
    assert names == ["frame_000000.png", "frame_000001.png", "frame_000002.png"]
    for name in names:
        assert (a / name).read_bytes() == (b / name).read_bytes()
    assert Image.open(a / "frame_000000.png").size == (220, 160)


# --- window spacing: averaging by window start --------------------------------


def result_with_starts(values, starts, sample_rate, sample_count, step=None, window_size=10):
    frames = np.repeat(np.asarray(values, dtype=float)[:, None], 88, axis=1)
    return AnalysisResult(sample_rate, window_size, frames, sample_count, starts=np.asarray(starts), step=step)


def test_overlapping_windows_are_averaged():
    # 100 Hz "sample rate": windows start every 5 samples, frames are 20 samples (5 fps)
    r = result_with_starts(np.arange(12), np.arange(12) * 5, 100, 60)
    out = average_frames(r, 5, frame_count(60, 100, 5))
    assert out[:, 0].tolist() == [1.5, 5.5, 9.5]


def test_gaps_use_the_most_recent_earlier_window():
    r = result_with_starts([10, 20, 30], [0, 40, 80], 100, 120)
    out = average_frames(r, 5, frame_count(120, 100, 5))
    assert out[:, 0].tolist() == [10, 10, 20, 20, 30, 30]


def test_a_start_on_a_frame_boundary_belongs_to_the_later_frame():
    r = result_with_starts([1, 2, 3], [0, 20, 40], 100, 60)
    out = average_frames(r, 5, 3)
    assert out[:, 0].tolist() == [1, 2, 3]


def test_non_integer_frame_period_never_leaves_a_frame_without_a_window():
    # 44100 Hz at 11 fps: a frame is 4009.09 samples, so rounded window starts can land just
    # before a boundary. Frames are assigned by exact position (k * step) to avoid empty frames.
    from app.services.note_analysis import window_starts
    from app.services.window_spacing import default_spacing

    sample_rate, fps, window = 44100, 11, 4096
    step = default_spacing(sample_rate, fps, window) * window
    total = sample_rate * 30
    starts = window_starts(total, step)
    r = result_with_starts(np.arange(len(starts)), starts, sample_rate, total, step=step, window_size=window)
    frames = frame_count(total, sample_rate, fps)
    out = average_frames(r, fps, frames)

    period = sample_rate / fps
    nominal = np.arange(len(starts)) * step
    owner = np.floor((nominal + 1e-6) / period).astype(int)
    assert set(owner) >= set(range(frames))  # every frame owns a window
    for f in (0, 1, 5, 50, frames - 1):
        assert out[f, 0] == pytest.approx(np.arange(len(starts))[owner == f].mean())


def test_results_without_starts_behave_as_before():
    r = result_with_rows([0, 1, 2, 3, 4, 5], 100, 10, 60)
    assert r.starts is None
    out = average_frames(r, 5, frame_count(60, 100, 5))
    assert out[:, 0].tolist() == [0.5, 2.5, 4.5]
