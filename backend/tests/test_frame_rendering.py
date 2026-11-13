
import numpy as np
import pytest

from app.services.colormaps import COLORMAPS
from app.services.frame_rendering import average_frames, frame_count, hidden_below, smooth_frames, write_frames
from app.services.note_analysis import AnalysisResult

from app.services.image_types import IMAGE_TYPES

from .colormap_names import FIRST, INVALID, MESSAGE


# --- frame counting and averaging notes into frames ---------------------------------------------------------


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


# --- note smoothing: a windowed average over frames (features 006 and 012) -------------------------------


def reference_smooth(frames, s, w=1):
    """Plain-Python version of the windowed average, independent of smooth_frames:
    ( A[t] + s*A[t-1] + ... + s*A[t-k] ) / ( 1 + s*k ) with k = min(t, w), from the raw frames."""
    out = []
    for t in range(len(frames)):
        k = min(t, w)
        out.append(
            [
                (frames[t][n] + s * sum(frames[t - j][n] for j in range(1, k + 1))) / (1 + s * k)
                for n in range(len(frames[t]))
            ]
        )
    return out


def column(values, notes=88):
    return np.repeat(np.asarray(values, dtype=float)[:, None], notes, axis=1)


def test_the_worked_example_from_the_spec():
    out = smooth_frames(column([0, 10, 0, 0]), 0.5)  # the default window is 1: the previous frame only
    assert out[:, 0].tolist() == pytest.approx([0, 10 / 1.5, 5 / 1.5, 0])
    assert (out == out[:, :1]).all()  # every note smoothed the same way


@pytest.mark.parametrize("smoothing", [0, 0.25, 0.5, 0.8])
def test_the_first_frame_is_never_changed(smoothing):
    frames = np.random.default_rng(3).random((10, 88)) * 100
    assert np.array_equal(smooth_frames(frames, smoothing)[0], frames[0])


@pytest.mark.parametrize("smoothing, window", [(0.0, 1), (0.1, 1), (0.3, 2), (0.5, 5), (0.8, 1), (0.8, 20)])
def test_matches_the_formula_for_random_data(smoothing, window):
    frames = np.random.default_rng(11).random((40, 88)) * 50
    expected = np.array(reference_smooth(frames.tolist(), smoothing, window))
    assert np.allclose(smooth_frames(frames, smoothing, window), expected, rtol=1e-6, atol=1e-9)


def test_smoothing_zero_returns_equal_values_in_a_new_array():
    frames = np.random.default_rng(5).random((6, 88))
    out = smooth_frames(frames, 0)
    assert np.array_equal(out, frames)
    out[0, 0] = -1
    assert frames[0, 0] != -1  # a copy, not the same array


def test_the_input_is_never_modified():
    frames = np.random.default_rng(6).random((8, 88))
    before = frames.copy()
    smooth_frames(frames, 0.6)
    assert np.array_equal(frames, before)


def test_each_note_uses_only_its_own_history():
    rng = np.random.default_rng(8)
    frames = rng.random((20, 88)) * 10
    changed = frames.copy()
    changed[:, 5] = rng.random(20) * 10  # a different note 5
    a, b = smooth_frames(frames, 0.7), smooth_frames(changed, 0.7)
    assert not np.allclose(a[:, 5], b[:, 5])
    others = [k for k in range(88) if k != 5]
    assert np.array_equal(a[:, others], b[:, others])


def frames_until(values, smoothing, window, reached):
    """Frames after the change at which the smoothed first note first satisfies `reached` (1 = the change frame)."""
    out = smooth_frames(column(values, 1), smoothing, window)[:, 0]
    change = next(i for i in range(1, len(values)) if values[i] != values[i - 1])
    return next(i - change + 1 for i in range(change, len(values)) if reached(out[i]))


@pytest.mark.parametrize("smoothing, window, frames", [(0.0, 5, 1), (0.5, 1, 2), (0.5, 3, 4), (0.8, 10, 11)])
def test_a_note_that_stops_is_exactly_gone_after_the_window(smoothing, window, frames):
    values = [100.0] * 30 + [0.0] * 40  # a long note, so the window is full when it stops
    # the first frame whose smoothed value is exactly 0: with smoothing 0 the frame it stops, otherwise window + 1 frames on
    assert frames_until(values, smoothing, window, lambda v: v == 0.0) == frames


@pytest.mark.parametrize("smoothing, window, frames", [(0.0, 5, 1), (0.5, 1, 2), (0.5, 3, 4), (0.8, 10, 11)])
def test_a_note_that_starts_reaches_its_full_value_after_the_window(smoothing, window, frames):
    values = [0.0] * 30 + [100.0] * 40
    assert frames_until(values, smoothing, window, lambda v: v >= 100.0 - 1e-9) == frames


def test_short_inputs_come_back_unchanged():
    one = np.random.default_rng(1).random((1, 88))
    none = np.zeros((0, 88))
    assert np.array_equal(smooth_frames(one, 0.7), one)
    assert smooth_frames(none, 0.7).shape == (0, 88)


def test_output_stays_between_zero_and_the_input_maximum():
    frames = np.random.default_rng(2).random((50, 88)) * 30
    out = smooth_frames(frames, 0.8)
    assert out.min() >= 0
    assert out.max() <= frames.max() + 1e-12


@pytest.mark.parametrize("smoothing", [0.0, 0.8, 0.4])
def test_the_limits_are_accepted(smoothing):
    smooth_frames(column([1, 2, 3]), smoothing)
    smooth_frames(column([1, 2, 3]), smoothing, 20)


@pytest.mark.parametrize("smoothing", [-0.01, 0.81, 1, 5, float("nan"), float("inf"), -float("inf"), True, "0.5", None])
def test_smoothing_outside_zero_to_point_eight_is_refused(smoothing):
    with pytest.raises(ValueError, match="smoothing"):
        smooth_frames(column([1, 2, 3]), smoothing)


# --- the note threshold: which notes are hidden (feature 011) ------------------------------------------------


# --- helpers for reading the frames that write_frames wrote ---------------------------------------------------


# --- write_frames: the colour of every tile is a colormap lookup at its own note strength (feature 014) -----------------

LEVEL_FRAMES = np.random.default_rng(3).uniform(0.0, 1.0, (6, 88)) ** 3


def frame_files(directory):
    return {p.name: p.read_bytes() for p in sorted(directory.glob("*.png"))}


def test_with_smoothing_zero_every_window_writes_the_same_files(tmp_path):
    for window in (1, 20):
        write_frames(LEVEL_FRAMES, tmp_path / str(window), smoothing=0.0, smoothing_window=window, threshold=3)
    write_frames(LEVEL_FRAMES, tmp_path / "none", threshold=3)
    assert frame_files(tmp_path / "1") == frame_files(tmp_path / "20") == frame_files(tmp_path / "none")


def test_written_files_repeat_exactly(tmp_path):
    for name in ("a", "b"):
        write_frames(LEVEL_FRAMES, tmp_path / name, colormap=FIRST, smoothing=0.4, smoothing_window=4, threshold=2)
    assert frame_files(tmp_path / "a") == frame_files(tmp_path / "b")


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"colormap": INVALID[0]}, MESSAGE),
        ({"colormap": INVALID[-1]}, MESSAGE),
        ({"colormap": None}, MESSAGE),
        ({"colormap": 3}, MESSAGE),
        ({"colormap": COLORMAPS[0].swapcase() + "x"}, MESSAGE),
        ({"threshold": 11}, "The threshold must be a number from 0 to 10."),
        ({"threshold": -1}, "The threshold must be a number from 0 to 10."),
        ({"smoothing": 0.9}, "The smoothing must be a number from 0.0 to 0.8."),
        ({"smoothing_window": 0}, "The smoothing window must be a whole number from 1 to 20."),
        ({"smoothing_window": 21}, "The smoothing window must be a whole number from 1 to 20."),
        ({"image_type": "Tiles"}, f"The image type must be one of {', '.join(IMAGE_TYPES)}."),
    ],
)
def test_write_frames_refuses_a_bad_argument_before_writing_anything(tmp_path, kwargs, message):
    with pytest.raises(ValueError) as error:
        write_frames(LEVEL_FRAMES, tmp_path / "out", **kwargs)
    assert str(error.value) == message
    assert not (tmp_path / "out").exists() or not list((tmp_path / "out").glob("*.png"))


# --- image types: tiles and blended tiles (features 013 and 014) -------------------------------------------------------


# --- the threshold on any grid of drawn values ---------------------------------------------------------------------------


def test_hidden_below_is_strict_and_works_on_any_shape():
    assert hidden_below(np.array([0.05, 0.1, 0.2, 1.0]), 1.0, 10).tolist() == [True, False, False, False]  # 0.1 is at 10%
    assert hidden_below(np.array([[0.05, 0.5], [0.0, 1.0]]), 1.0, 10).tolist() == [[True, False], [True, False]]
    grid = np.random.default_rng(12).random((3, 336))
    assert hidden_below(grid, 1.0, 5).shape == grid.shape


def test_hidden_below_hides_nothing_without_a_threshold_or_for_a_silent_file():
    values = np.random.default_rng(13).random((4, 50))
    assert not hidden_below(values, 1.0, 0).any()
    assert not hidden_below(np.zeros((3, 8)), 0.0, 10).any()
    with pytest.raises(ValueError):
        hidden_below(values, 1.0, 11)
