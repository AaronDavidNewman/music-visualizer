
import numpy as np
import pytest

from app.services.colormaps import COLORMAPS
from app.services.frame_rendering import average_frames, frame_count, frame_windows, hidden_below, write_frames
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
    from app.services.buffer_interval import buffer_step
    from app.services.note_analysis import window_starts

    sample_rate, fps, window = 44100, 11, 4096
    step = buffer_step(sample_rate)
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


# --- the frames are drawn as they are: no smoothing between the averaging and the drawing (feature 043) ----------------


def column(values, notes=88):
    return np.repeat(np.asarray(values, dtype=float)[:, None], notes, axis=1)


def test_the_smoothing_of_the_data_is_gone_from_the_module():
    import app.services.frame_rendering as module

    assert not hasattr(module, "smooth_frames")
    for name in ("MIN_SMOOTHING", "MAX_SMOOTHING", "DEFAULT_SMOOTHING", "MIN_SMOOTHING_WINDOW", "MAX_SMOOTHING_WINDOW", "DEFAULT_SMOOTHING_WINDOW"):
        assert not hasattr(module, name), name


@pytest.mark.parametrize("name", ["smoothing", "smoothing_window"])
def test_write_frames_no_longer_takes_the_smoothing_arguments(tmp_path, name):
    with pytest.raises(TypeError):
        write_frames(column([1, 2, 3]), tmp_path / "out", **{name: 1})
    assert not (tmp_path / "out").exists()


def test_a_note_that_stops_is_not_drawn_in_the_next_frame(tmp_path):
    """With no smoothing a frame depends on its own values only: frame 2 of a note that sounded in frames 0 and 1 only is
    exactly the picture of silence."""
    values = np.zeros((4, 88))
    values[:2, 40] = 1.0
    values[0, 20] = 0.5  # keeps the peak of the file above 0 in the first frames only
    write_frames(values, tmp_path / "out", image_type="contour")
    assert (tmp_path / "out" / "frame_000002.png").read_bytes() == (tmp_path / "out" / "frame_000003.png").read_bytes()
    assert (tmp_path / "out" / "frame_000001.png").read_bytes() != (tmp_path / "out" / "frame_000002.png").read_bytes()


# --- the note threshold: which notes are hidden (feature 011) ------------------------------------------------


# --- helpers for reading the frames that write_frames wrote ---------------------------------------------------


# --- write_frames: the colour of every tile is a colormap lookup at its own note strength (feature 014) -----------------

LEVEL_FRAMES = np.random.default_rng(3).uniform(0.0, 1.0, (6, 88)) ** 3


def frame_files(directory):
    return {p.name: p.read_bytes() for p in sorted(directory.glob("*.png"))}


def test_written_files_repeat_exactly(tmp_path):
    for name in ("a", "b"):
        write_frames(LEVEL_FRAMES, tmp_path / name, colormap=FIRST, threshold=2)
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


# --- the frames average the 60 ms frequency buffers they own (feature 043, User Story 2) ----------------------------------

SAMPLE_RATE = 44100
STEP = 2646.0  # buffer_step(44100): 60 ms


def buffers(count, rate=SAMPLE_RATE):
    """A fabricated AnalysisResult of ``count`` buffers 60 ms apart; every note of buffer ``k`` is ``k + 1`` (so every buffer is told apart)."""
    values = np.repeat((np.arange(count, dtype=float) + 1.0)[:, None], 88, axis=1)
    starts = np.rint(np.arange(count) * STEP).astype(np.int64)
    return AnalysisResult(rate, 4096, values, int(count * STEP), starts=starts, step=STEP)


@pytest.mark.parametrize("fps", [1, 2, 5, 10])
def test_a_frame_longer_than_the_interval_is_the_mean_of_the_buffers_that_start_in_it(fps):
    result = buffers(100)
    frames = frame_count(result.sample_count, SAMPLE_RATE, fps)
    first, stop, _ = frame_windows(result, fps, frames)
    out = average_frames(result, fps, frames)
    for f in range(frames):
        assert stop[f] > first[f], (fps, f)  # at 10 fps or less a frame (100 ms or more) always holds at least one 60 ms buffer
        assert out[f, 0] == pytest.approx(np.arange(first[f], stop[f]).mean() + 1.0), (fps, f)
    assert int((stop - first).sum()) == 100  # every buffer is counted in exactly one frame (SC-004)


def test_a_frame_owns_about_its_period_over_60_ms_buffers_one_more_or_fewer():
    result = buffers(100)
    for fps, owned in ((10, {1, 2}), (5, {3, 4}), (2, {8, 9})):  # 100 ms, 200 ms and 500 ms frames
        frames = frame_count(result.sample_count, SAMPLE_RATE, fps)
        first, stop, _ = frame_windows(result, fps, frames)
        assert set((stop - first)[:-1].tolist()) <= owned, fps


@pytest.mark.parametrize("fps", [20, 24, 30, 60])
def test_above_the_buffer_rate_a_frame_without_a_buffer_repeats_the_latest_one(fps):
    result = buffers(60)
    frames = frame_count(result.sample_count, SAMPLE_RATE, fps)
    first, stop, earlier = frame_windows(result, fps, frames)
    out = average_frames(result, fps, frames)
    assert out.shape == (frames, 88)
    assert (out > 0).all()  # no frame is blank for want of a buffer (FR-005)
    assert ((stop - first) <= 1).all()  # a frame is shorter than a buffer interval
    for f in range(frames):
        want = result.frames[first[f]] if stop[f] > first[f] else result.frames[earlier[f]]
        assert np.array_equal(out[f], want), (fps, f)
    assert int((stop - first).sum()) == 60  # still every buffer exactly once
    assert (np.diff(out[:, 0]) >= 0).all()  # time only moves forward


@pytest.mark.parametrize("fps", [1, 3, 10, 16, 30, 60])
def test_the_number_of_frames_is_the_duration_times_the_frame_rate_rounded_up(fps):
    seconds = 7.3
    samples = int(seconds * SAMPLE_RATE)
    assert frame_count(samples, SAMPLE_RATE, fps) == int(np.ceil(seconds * fps - 1e-9))


def test_a_lower_frame_rate_changes_more_gently_than_a_higher_one():
    """More buffers are averaged into each frame at a low rate, so the same ramp of buffers gives smaller steps relative to its range at 10 fps than a single
    buffer per frame gives at 60 fps: both end on the same level, the low rate with a mean of its buffers."""
    result = buffers(100)
    low = average_frames(result, 5, frame_count(result.sample_count, SAMPLE_RATE, 5))[:, 0]
    high = average_frames(result, 60, frame_count(result.sample_count, SAMPLE_RATE, 60))[:, 0]
    assert low.max() <= high.max()  # a mean never exceeds the largest value of the buffers
    assert low.min() >= high.min()
