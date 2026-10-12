import numpy as np
import pytest
from PIL import Image

from app.services.colormaps import COLORMAPS, DEFAULT_COLORMAP, lookup_table
from app.services.frame_rendering import (
    GRID_COLUMNS,
    GRID_ROWS,
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    SHOWN_NOTES,
    TILE_HEIGHT,
    TILE_WIDTH,
    average_frames,
    frame_count,
    hidden_notes,
    smooth_frames,
    write_frames,
)
from app.services.note_analysis import NOTE_COUNT, AnalysisResult

from app.services.image_types import IMAGE_TYPES

from .colormap_names import FIRST, INVALID, MESSAGE, SECOND, TRACEABLE


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


def note_matrix(*frames):
    """(frames, 88) note values; each frame is a dict {note: value}, every other note is 0."""
    out = np.zeros((len(frames), NOTE_COUNT))
    for i, values in enumerate(frames):
        for note, value in values.items():
            out[i, note] = value
    return out


def hidden_set(mask, frame=0):
    return set(np.flatnonzero(mask[frame]).tolist())


@pytest.mark.parametrize("threshold, expected", [(6, {2}), (8, {2}), (10, {1, 2}), (0, set()), (2, set())])
def test_notes_strictly_below_the_threshold_are_hidden_and_equal_ones_are_shown(threshold, expected):
    values = note_matrix({0: 100.0, 1: 8.0, 2: 4.0})
    # (notes 3 to 83 have no value at all; see the next test)
    assert hidden_set(hidden_notes(values, threshold)) & {0, 1, 2} == expected


def test_notes_with_no_value_at_all_are_below_any_positive_threshold():
    values = note_matrix({0: 100.0})
    assert hidden_set(hidden_notes(values, 1)) == set(range(1, SHOWN_NOTES))
    assert hidden_set(hidden_notes(values, 0)) == set()


@pytest.mark.parametrize("threshold", range(0, 11))
def test_the_note_with_the_largest_value_is_never_hidden(threshold):
    values = note_matrix({5: 80.0, 6: 3.0}, {7: 100.0, 8: 99.0}, {9: 50.0})
    mask = hidden_notes(values, threshold)
    assert not mask[1, 7]


@pytest.mark.parametrize("threshold", range(0, 11))
def test_a_value_exactly_at_the_threshold_is_shown(threshold):
    peak = 0.7311
    values = note_matrix({0: peak, 1: threshold / 100 * peak})
    assert not hidden_notes(values, threshold)[0, 1]


def test_threshold_zero_hides_nothing_even_for_zero_values():
    values = note_matrix({0: 1.0}, {})
    assert not hidden_notes(values, 0).any()
    assert not hidden_notes(values).any()  # off is the default


def test_the_reference_is_the_largest_value_of_the_whole_file_not_of_each_frame():
    values = note_matrix({0: 100.0}, {0: 5.0, 1: 2.0})
    mask = hidden_notes(values, 8)
    assert hidden_set(mask, 0) & {0} == set()
    assert hidden_set(mask, 1) & {0, 1} == {0, 1}  # the quiet frame's notes are hidden


def test_the_four_undrawn_notes_count_towards_the_reference():
    quiet = note_matrix({0: 5.0})
    assert not hidden_notes(quiet, 8)[0, 0]
    louder_undrawn = note_matrix({0: 5.0, 85: 100.0})
    assert hidden_notes(louder_undrawn, 8)[0, 0]


def test_silence_hides_nothing_and_does_not_fail():
    assert not hidden_notes(np.zeros((4, NOTE_COUNT)), 10).any()


def test_no_frames_gives_an_empty_result():
    out = hidden_notes(np.zeros((0, NOTE_COUNT)), 5)
    assert out.shape == (0, SHOWN_NOTES) and out.dtype == bool


def test_hidden_notes_shape_dtype_and_inputs_are_left_alone():
    values = note_matrix({0: 100.0}, {1: 5.0})
    before = values.copy()
    mask = hidden_notes(values, 3)
    assert mask.shape == (2, SHOWN_NOTES) and mask.dtype == bool
    assert (values == before).all()
    mask[:] = True
    assert hidden_notes(values, 3).sum() < mask.sum()  # a fresh array every time


@pytest.mark.parametrize("bad", [-1, 11, float("nan"), float("inf"), True, "20", None, [20]])
def test_hidden_notes_refuses_a_threshold_outside_zero_to_fifty(bad):
    with pytest.raises(ValueError, match="The threshold must be a number from 0 to 10."):
        hidden_notes(np.ones((1, NOTE_COUNT)), bad)


def test_hidden_notes_needs_at_least_84_values_per_frame():
    with pytest.raises(ValueError):
        hidden_notes(np.ones((2, 83)), 10)
    with pytest.raises(ValueError):
        hidden_notes(np.ones(88), 10)
    assert hidden_notes(np.ones((2, 84)), 10).shape == (2, 84)


# --- helpers for reading the frames that write_frames wrote ---------------------------------------------------


def frame_files(directory):
    return {p.name: p.read_bytes() for p in sorted(directory.glob("*.png"))}


def tile_rgb(path):
    """(84, 3) colour of every tile of a written frame, from its centre pixel."""
    rgb = np.asarray(Image.open(path).convert("RGB"))
    return np.array(
        [
            rgb[(n // GRID_COLUMNS) * TILE_HEIGHT + TILE_HEIGHT // 2, (n % GRID_COLUMNS) * TILE_WIDTH + TILE_WIDTH // 2]
            for n in range(SHOWN_NOTES)
        ]
    )


def written_tiles(directory, frames, **kwargs):
    write_frames(frames, directory, **kwargs)
    return [tile_rgb(directory / f"frame_{i:06d}.png") for i in range(frames.shape[0])]


def frame_image(directory, index):
    return Image.open(directory / f"frame_{index:06d}.png")


# --- write_frames: the colour of every tile is a colormap lookup at its own note strength (feature 014) -----------------

LEVEL_FRAMES = np.random.default_rng(3).uniform(0.0, 1.0, (6, 88)) ** 3


def expected_colours(frames, colormap, smoothing=0.0, smoothing_window=1, threshold=0):
    """The (frames, 84, 3) colours worked out independently of ``colorize``: smoothing from ``reference_smooth``, the share
    of the largest smoothed value, the square root, the table entry; black where the threshold hides the note."""
    smoothed = np.array(reference_smooth(np.asarray(frames).tolist(), smoothing, smoothing_window))
    peak = smoothed.max()
    share = smoothed[:, :SHOWN_NOTES] / peak if peak > 0 else np.zeros((len(smoothed), SHOWN_NOTES))
    colours = lookup_table(colormap)[np.rint(np.sqrt(share) * 255).astype(int)].copy()
    if threshold:
        colours[smoothed[:, :SHOWN_NOTES] < threshold / 100 * peak] = 0
    return colours


def written_colours(directory, count):
    return np.array([tile_rgb(directory / f"frame_{i:06d}.png") for i in range(count)])


OPTION_SETS = [
    {},
    {"smoothing": 0.5, "smoothing_window": 3},
    {"smoothing": 0.8, "smoothing_window": 8, "threshold": 7},
    {"threshold": 3},
]


@pytest.mark.parametrize("colormap", COLORMAPS)
@pytest.mark.parametrize("options", OPTION_SETS, ids=["plain", "smoothed", "smoothed-threshold", "threshold"])
def test_every_tile_is_the_colormap_colour_of_its_own_strength(tmp_path, colormap, options):
    write_frames(LEVEL_FRAMES, tmp_path, colormap=colormap, **options)
    got = written_colours(tmp_path, 6)
    assert (got == expected_colours(LEVEL_FRAMES, colormap, **options)).all()


def test_the_default_colormap_is_used_when_none_is_given(tmp_path):
    assert DEFAULT_COLORMAP in COLORMAPS
    write_frames(LEVEL_FRAMES, tmp_path / "none")
    write_frames(LEVEL_FRAMES, tmp_path / "named", colormap=DEFAULT_COLORMAP)
    assert frame_files(tmp_path / "none") == frame_files(tmp_path / "named")


@pytest.mark.parametrize("colormap", COLORMAPS)
def test_the_strongest_note_is_the_last_colour_and_a_note_with_no_strength_the_first(tmp_path, colormap):
    values = np.zeros((3, 88))
    values[1, 40] = 5.0  # the largest value of the file, on a drawn note
    values[0, 10] = 2.0
    write_frames(values, tmp_path, colormap=colormap)
    got = written_colours(tmp_path, 3)
    table = lookup_table(colormap)
    assert (got[1, 40] == table[255]).all()
    assert (got[0, 5] == table[0]).all() and (got[2, 83] == table[0]).all()  # notes with no strength
    assert not (got[0, 10] == table[0]).all()  # a note with some strength is further along


def test_a_note_keeps_its_colour_whatever_the_other_notes_do(tmp_path):
    base = np.zeros((4, 88))
    base[:, 12] = 30.0
    base[2, 60] = 100.0  # the peak, in one frame only
    other = base.copy()
    other[:, 30] = np.array([0.0, 80.0, 5.0, 60.0])  # a lot happening elsewhere, below the peak
    write_frames(base, tmp_path / "base")
    write_frames(other, tmp_path / "other")
    a, b = written_colours(tmp_path / "base", 4), written_colours(tmp_path / "other", 4)
    assert (a[:, 12] == a[0, 12]).all() and (b[:, 12] == a[0, 12]).all()  # steady, and not touched by note 30
    untouched = [n for n in range(SHOWN_NOTES) if n != 30]
    assert (a[:, untouched] == b[:, untouched]).all()


def test_a_silent_matrix_has_the_first_colour_everywhere_and_black_with_a_threshold(tmp_path):
    for colormap in COLORMAPS:
        write_frames(np.zeros((3, 88)), tmp_path / colormap, colormap=colormap)
        assert (written_colours(tmp_path / colormap, 3) == lookup_table(colormap)[0]).all()
        write_frames(np.zeros((3, 88)), tmp_path / f"{colormap}-hidden", colormap=colormap, threshold=1)
        # no note has any strength, so none is below a share of the (zero) largest value: nothing is hidden
        assert (written_colours(tmp_path / f"{colormap}-hidden", 3) == lookup_table(colormap)[0]).all()


def test_with_a_threshold_every_hidden_tile_is_exactly_black_whatever_the_colormap(tmp_path):
    values = np.zeros((2, 88))
    values[:, 26] = 1.0
    values[0, 27] = 0.02  # below 5% of the largest value
    values[1, 27] = 0.5
    for colormap in COLORMAPS:
        write_frames(values, tmp_path / colormap, colormap=colormap, threshold=5)
        got = written_colours(tmp_path / colormap, 2)
        assert not got[0, 27].any() and (got[1, 27] == expected_colours(values, colormap)[1, 27]).all()
        assert (got[:, 26] == lookup_table(colormap)[255]).all()  # the loudest note is shown at every threshold
        assert not got[:, [n for n in range(SHOWN_NOTES) if n not in (26, 27)]].any()  # notes with no value are hidden too


@pytest.mark.skipif(not TRACEABLE, reason="no offered colormap has 256 different colours and no black")
def test_a_fading_note_moves_gradually_along_the_colormap_and_turns_black_below_the_threshold(tmp_path):
    values = np.zeros((16, 88))
    values[:2, 24] = 1.0  # the note stops after two frames; a window of 8 keeps a trace of it for 8 frames
    smoothed = np.array(reference_smooth(values.tolist(), 0.8, 8))[:, 24]
    first_hidden = int(np.argmax(smoothed < 0.1))  # below 10% of the largest smoothed value (1.0)
    assert 5 < first_hidden < 15
    write_frames(values, tmp_path, colormap=TRACEABLE[0], smoothing=0.8, smoothing_window=8, threshold=10)
    got = written_colours(tmp_path, 16)[:, 24]
    table = lookup_table(TRACEABLE[0])
    rows = [int(np.flatnonzero((table == c).all(axis=1))[0]) for c in got[:first_hidden]]
    assert all(a >= b for a, b in zip(rows, rows[1:]))  # fading: never back up the scale
    assert rows[0] > rows[-1]
    assert not got[first_hidden:].any()  # and black from then on


def test_a_frame_whose_notes_are_all_hidden_is_entirely_black_and_its_neighbours_are_not(tmp_path):
    values = np.zeros((3, 88))
    values[0, 24] = values[2, 24] = 1.0
    values[1, :] = 0.05
    write_frames(values, tmp_path, threshold=10)
    got = written_colours(tmp_path, 3)
    assert not got[1].any()
    assert got[0, 24].any() and got[2, 24].any()


def test_adding_silent_frames_at_the_end_changes_no_earlier_frame(tmp_path):
    longer = np.vstack([LEVEL_FRAMES, np.zeros((4, 88))])
    for window in (1, 5, 20):
        kwargs = dict(colormap=SECOND, smoothing=0.5, smoothing_window=window, threshold=3)
        write_frames(LEVEL_FRAMES, tmp_path / f"short{window}", **kwargs)
        write_frames(longer, tmp_path / f"long{window}", **kwargs)
        short, long = frame_files(tmp_path / f"short{window}"), frame_files(tmp_path / f"long{window}")
        assert len(short) == 6 and len(long) == 10
        assert all(long[name] == data for name, data in short.items())  # smoothing looks only backwards


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
        ({"image_type": "blended", "blend_width": 9}, "The blend width must be a number from 10 to 25."),
        ({"blend_width": float("nan")}, "The blend width must be a number from 10 to 25."),
    ],
)
def test_write_frames_refuses_a_bad_argument_before_writing_anything(tmp_path, kwargs, message):
    with pytest.raises(ValueError) as error:
        write_frames(LEVEL_FRAMES, tmp_path / "out", **kwargs)
    assert str(error.value) == message
    assert not (tmp_path / "out").exists() or not list((tmp_path / "out").glob("*.png"))


# --- image types: tiles and blended tiles (features 013 and 014) -------------------------------------------------------


def test_the_tiles_image_type_and_no_argument_write_identical_files(tmp_path):
    common = dict(smoothing=0.3, threshold=3)
    write_frames(LEVEL_FRAMES, tmp_path / "none", **common)
    write_frames(LEVEL_FRAMES, tmp_path / "tiles", image_type="tiles", **common)
    write_frames(LEVEL_FRAMES, tmp_path / "tiles10", image_type="tiles", blend_width=10, **common)
    write_frames(LEVEL_FRAMES, tmp_path / "width25", blend_width=25, **common)  # the width alone changes nothing
    reference = frame_files(tmp_path / "none")
    assert len(reference) == 6
    for name in ("tiles", "tiles10", "width25"):
        assert frame_files(tmp_path / name) == reference


def test_blended_frames_have_the_same_names_size_and_count_but_are_true_colour(tmp_path):
    write_frames(LEVEL_FRAMES, tmp_path / "tiles", image_type="tiles")
    write_frames(LEVEL_FRAMES, tmp_path / "blended", image_type="blended")
    assert sorted(frame_files(tmp_path / "tiles")) == sorted(frame_files(tmp_path / "blended"))
    for i in range(6):
        flat, soft = frame_image(tmp_path / "tiles", i), frame_image(tmp_path / "blended", i)
        assert flat.mode == "P" and soft.mode == "RGB"
        assert flat.size == soft.size == (IMAGE_WIDTH, IMAGE_HEIGHT)


@pytest.mark.parametrize("colormap", COLORMAPS)
@pytest.mark.parametrize("blend_width", [10, 17.5, 25])
def test_the_middle_of_every_tile_of_a_blended_frame_is_the_tiles_colour(tmp_path, colormap, blend_width):
    options = dict(colormap=colormap, smoothing=0.5, smoothing_window=3, threshold=3)
    write_frames(LEVEL_FRAMES, tmp_path / "tiles", image_type="tiles", **options)
    write_frames(LEVEL_FRAMES, tmp_path / "blended", image_type="blended", blend_width=blend_width, **options)
    for i in range(6):
        flat = tile_rgb(tmp_path / "tiles" / f"frame_{i:06d}.png")
        soft = tile_rgb(tmp_path / "blended" / f"frame_{i:06d}.png")
        assert (flat == soft).all(), i


def test_blended_frames_differ_from_tiles_frames_where_colours_meet(tmp_path):
    write_frames(LEVEL_FRAMES, tmp_path / "tiles", image_type="tiles")
    write_frames(LEVEL_FRAMES, tmp_path / "blended", image_type="blended")
    flat = np.asarray(frame_image(tmp_path / "tiles", 0).convert("RGB"))
    soft = np.asarray(frame_image(tmp_path / "blended", 0))
    assert (flat != soft).any(axis=2).sum() > 1000  # a frame has many edges with a fade
    assert soft.min() >= flat.min() and soft.max() <= flat.max()  # no colour outside what the tiles have


def test_a_silent_frame_is_the_same_picture_in_both_types(tmp_path):
    for colormap in COLORMAPS:
        write_frames(np.zeros((2, 88)), tmp_path / colormap / "tiles", colormap=colormap, image_type="tiles")
        write_frames(np.zeros((2, 88)), tmp_path / colormap / "blended", colormap=colormap, image_type="blended")
        for i in range(2):
            flat = np.asarray(frame_image(tmp_path / colormap / "tiles", i).convert("RGB"))
            soft = np.asarray(frame_image(tmp_path / colormap / "blended", i))
            assert (flat == soft).all() and (flat == lookup_table(colormap)[0]).all()


def test_blended_frames_repeat_exactly(tmp_path):
    for name in ("a", "b"):
        write_frames(LEVEL_FRAMES, tmp_path / name, image_type="blended", blend_width=15)
    assert frame_files(tmp_path / "a") == frame_files(tmp_path / "b")


@pytest.mark.parametrize("options", [{}, {"threshold": 5}, {"smoothing": 0.8, "smoothing_window": 8, "threshold": 10}])
@pytest.mark.parametrize("colormap", COLORMAPS)
def test_every_blended_pixel_lies_between_the_tile_colours_around_it(tmp_path, colormap, options):
    from scipy import ndimage

    write_frames(LEVEL_FRAMES, tmp_path / "tiles", colormap=colormap, image_type="tiles", **options)
    write_frames(LEVEL_FRAMES, tmp_path / "blended", colormap=colormap, image_type="blended", **options)
    for i in range(6):
        name = f"frame_{i:06d}.png"
        flat = np.asarray(Image.open(tmp_path / "tiles" / name).convert("RGB"))
        soft = np.asarray(Image.open(tmp_path / "blended" / name))
        # the fade never reaches farther than 5.25 pixels, so every pixel is within the range of the tile colours within 6
        low = ndimage.minimum_filter(flat, size=(13, 13, 1), mode="nearest")
        high = ndimage.maximum_filter(flat, size=(13, 13, 1), mode="nearest")
        assert (soft >= low).all() and (soft <= high).all(), (options, i)


def test_a_hidden_tile_next_to_a_coloured_one_fades_toward_black(tmp_path):
    values = np.zeros((1, 88))
    values[0, 26] = 1.0  # tile (row 2, column 2); every other tile has no value and the threshold hides them
    write_frames(values, tmp_path / "tiles", image_type="tiles", threshold=5)
    write_frames(values, tmp_path / "blended", image_type="blended", threshold=5)
    flat = tile_rgb(tmp_path / "tiles" / "frame_000000.png")
    assert flat[26].any() and not flat[25].any() and not flat[27].any()
    soft = np.asarray(Image.open(tmp_path / "blended" / "frame_000000.png")).astype(int)
    y = 2 * TILE_HEIGHT + TILE_HEIGHT // 2
    for edge_x in (2 * TILE_WIDTH, 3 * TILE_WIDTH):  # the left and the right edge of the coloured tile
        average = (soft[y, edge_x - 1] + soft[y, edge_x]) / 2
        assert np.abs(average - flat[26] / 2).max() <= 1
    assert (soft[y, 2 * TILE_WIDTH + 8 : 3 * TILE_WIDTH - 8] == flat[26]).all()  # the middle stays flat


def test_threaded_writing_gives_exactly_the_plain_blend_of_each_frames_tile_colours(tmp_path):
    """Frames are blended and encoded on several threads: each file must equal a single plain call of the blend."""
    from app.services.image_types import blend_tile_colors

    many = np.vstack([LEVEL_FRAMES] * 6)  # 36 frames, so that several threads really work at once
    write_frames(many, tmp_path / "tiles", colormap=SECOND, image_type="tiles", smoothing=0.3)
    write_frames(many, tmp_path / "blended", colormap=SECOND, image_type="blended", blend_width=17, smoothing=0.3)
    assert len(list((tmp_path / "blended").glob("*.png"))) == 36
    for i in range(36):
        name = f"frame_{i:06d}.png"
        colours = tile_rgb(tmp_path / "tiles" / name)  # the 84 finished tile colours of this frame
        expected = blend_tile_colors(colours, 17, GRID_COLUMNS, GRID_ROWS, TILE_WIDTH, TILE_HEIGHT)
        assert (np.asarray(Image.open(tmp_path / "blended" / name)) == expected).all(), i


def test_an_error_in_a_worker_is_raised_and_no_threads_are_left_running(tmp_path, monkeypatch):
    import threading

    import app.services.frame_rendering as rendering

    def broken(blend, colours, path):
        raise RuntimeError("disk full")

    monkeypatch.setattr(rendering, "_save_blended", broken)
    before = threading.active_count()
    with pytest.raises(RuntimeError, match="disk full"):
        write_frames(LEVEL_FRAMES, tmp_path, image_type="blended")
    assert threading.active_count() == before  # the pool was shut down
