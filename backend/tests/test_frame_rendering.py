import colorsys

import numpy as np
import pytest
from PIL import Image

from app.services.frame_rendering import (
    DEFAULT_HUE,
    GRID_COLUMNS,
    GRID_ROWS,
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    RELATED_DOWN,
    RELATED_UP,
    SATURATION,
    SHOWN_NOTES,
    TILE_HEIGHT,
    TILE_WIDTH,
    average_frames,
    boost_levels,
    frame_count,
    hue_sequence,
    render_frame,
    smooth_frames,
    tile_colors,
    tile_hues,
    to_gray_levels,
    write_frames,
)
from app.services.note_analysis import NOTE_COUNT, AnalysisResult, note_frequencies


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


# --- octave grid layout (feature 005) -------------------------------------------


def gray(image):
    """Each pixel's brightness: the largest colour channel. Works for a gray or a colour image.

    A tile's HSV value is the largest channel, and that value is the tile's gray level.
    """
    return np.asarray(image.convert("RGB")).max(axis=2)


def tile(arr, n):
    """The pixels of the tile for note n: row n // 12, column n % 12."""
    row, col = divmod(n, GRID_COLUMNS)
    return arr[row * TILE_HEIGHT:(row + 1) * TILE_HEIGHT, col * TILE_WIDTH:(col + 1) * TILE_WIDTH]


def test_geometry_is_12_by_7_tiles_of_21_by_24_and_exactly_three_to_two():
    assert (GRID_COLUMNS, GRID_ROWS, SHOWN_NOTES) == (12, 7, 84)
    assert (TILE_WIDTH, TILE_HEIGHT) == (21, 24)
    assert (IMAGE_WIDTH, IMAGE_HEIGHT) == (252, 168)
    assert IMAGE_WIDTH * 2 == IMAGE_HEIGHT * 3  # exactly 3:2
    assert TILE_WIDTH * 8 == TILE_HEIGHT * 7  # tile width is 87.5% of its height
    assert (GRID_COLUMNS * 0.875) / GRID_ROWS == 1.5


def test_render_frame_is_a_252_by_168_image():
    img = render_frame(np.arange(88, dtype=np.uint8) * 2)
    assert img.size == (252, 168)


def test_every_tile_is_one_flat_gray_with_no_gaps():
    levels = (np.arange(88) * 3 % 256).astype(np.uint8)
    arr = gray(render_frame(levels))
    boosted = boost_levels(levels)
    covered = np.zeros(arr.shape, dtype=bool)
    for n in range(SHOWN_NOTES):
        square = tile(arr, n)
        assert square.shape == (24, 21)
        assert (square == boosted[n]).all(), n
        covered[(n // 12) * 24:(n // 12 + 1) * 24, (n % 12) * 21:(n % 12 + 1) * 21] = True
    assert covered.all()  # the 84 tiles fill the whole image: no gaps, no margins


@pytest.mark.parametrize("note", range(SHOWN_NOTES))
def test_note_lights_exactly_its_own_tile(note):
    levels = np.zeros(88, dtype=np.uint8)
    levels[note] = 255
    arr = gray(render_frame(levels))
    lit = {n for n in range(SHOWN_NOTES) if tile(arr, n).any()}
    assert lit == {note}
    assert (tile(arr, note) == 255).all()
    assert divmod(note, 12) == (note // 12, note % 12)  # row = octave, column = note within the octave


def test_tile_below_is_the_same_note_one_octave_up_at_double_the_frequency():
    freqs = note_frequencies()
    for row in range(GRID_ROWS - 1):
        for col in range(GRID_COLUMNS):
            above, below = 12 * row + col, 12 * (row + 1) + col
            assert freqs[below] == pytest.approx(2 * freqs[above], rel=1e-12)


def test_lowest_note_is_top_left_and_last_drawn_note_is_bottom_right():
    only_first = np.zeros(88, dtype=np.uint8)
    only_first[0] = 255
    arr = gray(render_frame(only_first))
    assert (arr[:24, :21] == 255).all() and arr.sum() == 255 * 24 * 21
    only_last = np.zeros(88, dtype=np.uint8)
    only_last[83] = 255
    arr = gray(render_frame(only_last))
    assert (arr[-24:, -21:] == 255).all() and arr.sum() == 255 * 24 * 21
    assert note_frequencies()[0] == pytest.approx(55.0)
    assert note_frequencies()[83] == pytest.approx(6644.9, abs=0.1)


def test_the_four_highest_notes_are_not_drawn():
    only_omitted = np.zeros(88, dtype=np.uint8)
    only_omitted[84:] = 255
    assert not gray(render_frame(only_omitted)).any()  # nothing appears anywhere (brightness only)
    base = (np.arange(88) % 256).astype(np.uint8)
    changed = base.copy()
    changed[84:] = 255 - base[84:]
    assert np.array_equal(gray(render_frame(base)), gray(render_frame(changed)))


def test_render_frame_accepts_88_or_84_values_and_refuses_fewer():
    levels = np.full(NOTE_COUNT, 100, dtype=np.uint8)
    assert np.array_equal(gray(render_frame(levels)), gray(render_frame(levels[:84])))
    with pytest.raises(ValueError, match="84"):
        render_frame(levels[:83])


@pytest.mark.parametrize("brightness", [2, 4])
def test_each_tile_has_the_same_gray_as_the_previous_layout(brightness):
    """Only where a note is drawn changed, not how bright it is: tile gray == boost of the note's level."""
    levels = np.random.default_rng(7).integers(0, 256, size=88).astype(np.uint8)
    arr = gray(render_frame(levels, brightness=brightness))
    expected = boost_levels(levels, brightness)
    for n in range(SHOWN_NOTES):
        assert (tile(arr, n) == expected[n]).all(), n


def test_silent_frame_is_black():
    assert not gray(render_frame(np.zeros(88, dtype=np.uint8))).any()


def test_boost_is_square_root_of_the_level():
    levels = np.array([0, 1, 16, 64, 128, 255], dtype=np.uint8)
    boosted = boost_levels(levels)
    assert boosted.dtype == np.uint8
    assert boosted.tolist() == [round(255 * (v / 255) ** 0.5) for v in levels]
    assert boosted[0] == 0 and boosted[-1] == 255  # black and white are unchanged
    assert (boosted >= levels).all()  # never darker
    assert (np.diff(boosted.astype(int)) > 0).all()  # still strictly brighter for brighter input
    assert boosted[3] == 128  # a quarter of full scale (64) shows at about half brightness


def test_render_frame_applies_the_boost():
    levels = np.full(88, 64, dtype=np.uint8)
    arr = gray(render_frame(levels))
    assert (arr == 128).all()


def test_write_frames_names_and_determinism(tmp_path):
    frames = np.random.default_rng(0).random((3, 88))
    a, b = tmp_path / "a", tmp_path / "b"
    write_frames(frames, a)
    write_frames(frames, b)
    names = sorted(p.name for p in a.iterdir())
    assert names == ["frame_000000.png", "frame_000001.png", "frame_000002.png"]
    for name in names:
        assert (a / name).read_bytes() == (b / name).read_bytes()
    assert Image.open(a / "frame_000000.png").size == (252, 168)


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


# --- brightness: the nth root (feature 004) ------------------------------------


def expected_level(level, brightness):
    return round(255 * (level / 255) ** (1 / brightness))


def test_boost_matches_the_formula_for_every_level_and_brightness():
    levels = np.arange(256, dtype=np.uint8)
    for brightness in range(2, 101):
        boosted = boost_levels(levels, brightness)
        assert boosted.tolist() == [expected_level(int(v), brightness) for v in levels], brightness


def test_black_and_white_are_fixed_at_every_brightness():
    for brightness in range(2, 101):
        boosted = boost_levels(np.array([0, 255], dtype=np.uint8), brightness)
        assert boosted.tolist() == [0, 255], brightness


def test_boost_never_gets_darker_with_level_or_brightness():
    levels = np.arange(256, dtype=np.uint8)
    previous = None
    for brightness in range(2, 101):
        boosted = boost_levels(levels, brightness).astype(int)
        assert (np.diff(boosted) >= 0).all(), brightness  # brighter input is never darker
        if previous is not None:
            assert (boosted >= previous).all(), brightness  # higher brightness is never darker
        previous = boosted


def test_brightness_two_is_the_old_square_root():
    levels = np.arange(256, dtype=np.uint8)
    old = [round(255 * (v / 255) ** 0.5) for v in levels]
    assert boost_levels(levels, 2).tolist() == old
    assert boost_levels(levels).tolist() == old  # 2 is the default


def test_known_values_for_level_64():
    levels = np.array([64], dtype=np.uint8)
    got = {b: int(boost_levels(levels, b)[0]) for b in (2, 3, 4, 10, 100)}
    assert got == {2: 128, 3: 161, 4: 180, 10: 222, 100: 251}


def test_boost_keeps_dtype_and_shape():
    levels = np.arange(88, dtype=np.uint8).reshape(8, 11)
    boosted = boost_levels(levels, 5)
    assert boosted.dtype == np.uint8
    assert boosted.shape == (8, 11)


@pytest.mark.parametrize("brightness", [0, 1, 101, 2.5, -3, "4", None, True])
def test_boost_rejects_a_brightness_outside_two_to_a_hundred(brightness):
    with pytest.raises(ValueError, match="brightness"):
        boost_levels(np.zeros(88, dtype=np.uint8), brightness)


def test_render_frame_uses_the_brightness():
    levels = np.full(88, 64, dtype=np.uint8)
    assert (gray(render_frame(levels, brightness=4)) == 180).all()
    assert (gray(render_frame(levels)) == 128).all()


def test_write_frames_brightness_changes_pixels_not_files(tmp_path):
    frames = np.random.default_rng(1).random((4, 88))
    a, b, c = tmp_path / "a", tmp_path / "b", tmp_path / "c"
    write_frames(frames, a, brightness=2)
    write_frames(frames, b, brightness=10)
    write_frames(frames, c, brightness=10)
    assert sorted(p.name for p in a.iterdir()) == sorted(p.name for p in b.iterdir())
    first_a = gray(Image.open(a / "frame_000000.png"))
    first_b = gray(Image.open(b / "frame_000000.png"))
    assert (first_b >= first_a).all() and (first_b > first_a).any()
    for p in b.iterdir():
        assert p.read_bytes() == (c / p.name).read_bytes()


# --- note smoothing: a running average over frames (feature 006) -----------------


def reference_smooth(frames, s):
    """Plain-Python version of the recurrence, independent of smooth_frames."""
    out = [list(frames[0])]
    for n in range(1, len(frames)):
        out.append([s * out[n - 1][k] + (1 - s) * frames[n][k] for k in range(len(frames[n]))])
    return out


def column(values, notes=88):
    return np.repeat(np.asarray(values, dtype=float)[:, None], notes, axis=1)


def test_the_worked_example_from_the_spec():
    out = smooth_frames(column([0, 10, 0, 0]), 0.5)
    assert out[:, 0].tolist() == [0, 5, 2.5, 1.25]
    assert (out == out[:, :1]).all()  # every note smoothed the same way


@pytest.mark.parametrize("smoothing", [0, 0.25, 0.5, 0.8])
def test_the_first_frame_is_never_changed(smoothing):
    frames = np.random.default_rng(3).random((10, 88)) * 100
    assert np.array_equal(smooth_frames(frames, smoothing)[0], frames[0])


@pytest.mark.parametrize("smoothing", [0.0, 0.1, 0.3, 0.5, 0.8])
def test_matches_the_formula_for_random_data(smoothing):
    frames = np.random.default_rng(11).random((40, 88)) * 50
    expected = np.array(reference_smooth(frames.tolist(), smoothing))
    assert np.allclose(smooth_frames(frames, smoothing), expected, rtol=1e-6, atol=1e-9)


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


def frames_until(values, smoothing, reached):
    """Frames after the change at which the smoothed first note first satisfies `reached`."""
    out = smooth_frames(column(values, 1), smoothing)[:, 0]
    change = next(i for i in range(1, len(values)) if values[i] != values[i - 1])
    return next(i - change + 1 for i in range(change, len(values)) if reached(out[i]))


@pytest.mark.parametrize("smoothing, frames", [(0.0, 1), (0.5, 4), (0.8, 11)])
def test_a_note_that_stops_fades_over_more_frames_at_higher_smoothing(smoothing, frames):
    values = [100.0] * 5 + [0.0] * 30
    assert frames_until(values, smoothing, lambda v: v < 10) == frames  # below 10% of its starting value


@pytest.mark.parametrize("smoothing, frames", [(0.0, 1), (0.5, 4), (0.8, 11)])
def test_a_note_that_starts_rises_over_more_frames_at_higher_smoothing(smoothing, frames):
    values = [0.0] * 5 + [100.0] * 30
    assert frames_until(values, smoothing, lambda v: v >= 90) == frames


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


@pytest.mark.parametrize("smoothing", [-0.01, 0.81, 1, 5, float("nan"), float("inf"), -float("inf"), True, "0.5", None])
def test_smoothing_outside_zero_to_point_eight_is_refused(smoothing):
    with pytest.raises(ValueError, match="smoothing"):
        smooth_frames(column([1, 2, 3]), smoothing)


# --- harmonic colour: hue from related notes (feature 007) -----------------------


def displayed_levels(levels, brightness=2):
    """The final gray levels (after the brightness root), worked out without boost_levels."""
    return [round(255 * (int(v) / 255) ** (1 / brightness)) for v in levels]


def lit(*notes, at=255):
    levels = np.zeros(88, dtype=np.uint8)
    for n in notes:
        levels[n] = at
    return levels


def hue_distance_degrees(a, b):
    d = abs(a - b) % 1.0
    return min(d, 1 - d) * 360


def ref_hues(levels, brightness=2):
    """The hue rule written out as plain Python: 0.5 + 0.5 * (sum of the up notes - sum of the down notes), clipped."""
    shown = displayed_levels(levels, brightness)

    def lum(k):
        return shown[k] / 255 if 0 <= k < len(shown) else 0.0  # notes past the ends are silent

    out = []
    for n in range(84):
        down = sum(lum(n + o) for o in RELATED_DOWN)  # sums: nothing is averaged
        up = sum(lum(n + o) for o in RELATED_UP)
        out.append(min(1.0, max(0.0, 0.5 + 0.5 * (up - down))))
    return np.array(out)


def test_the_colour_constants_describe_two_separate_groups_of_partners():
    assert SATURATION == 0.5
    assert DEFAULT_HUE == 0.5  # 180 of 360
    for group in (RELATED_DOWN, RELATED_UP):
        assert len(group) > 0 and all(isinstance(o, int) for o in group)
        assert len(set(group)) == len(group)
    assert 0 not in RELATED_DOWN + RELATED_UP  # a note is not its own partner
    assert not set(RELATED_DOWN) & set(RELATED_UP)  # a partner pulls one way or the other, not both


def test_hue_is_180_degrees_when_no_related_note_is_lit():
    hues = tile_hues(lit(40))
    assert hues[40] == 0.5  # a note is not its own partner
    affected = {40 - o for o in RELATED_DOWN + RELATED_UP}  # the tiles that have note 40 as a partner
    others = [n for n in range(84) if n not in affected | {40}]
    assert (hues[others] == 0.5).all()


def test_a_full_brightness_partner_reaches_red_from_either_group():
    hues = tile_hues(lit(60))  # note 60 is a partner of the tiles 60 - o
    for o in RELATED_DOWN:
        assert hues[60 - o] == 0.0, o  # sum 1 -> 0.5 - 0.5 = 0: 0 degrees
    for o in RELATED_UP:
        assert hues[60 - o] == 1.0, o  # sum 1 -> 0.5 + 0.5 = 1: 360 degrees, the same red
    affected = {60 - o for o in RELATED_DOWN + RELATED_UP}
    assert (hues[[n for n in range(84) if n not in affected]] == 0.5).all()


def test_a_dimmer_partner_moves_the_hue_in_proportion():
    levels = lit(60, at=64)  # level 64 shows as gray level 128 after the square root: brightness 128 / 255
    hues = tile_hues(levels)
    shift = 0.5 * 128 / 255
    for o in RELATED_DOWN:
        assert hues[60 - o] == pytest.approx(0.5 - shift, abs=1e-12), o
    for o in RELATED_UP:
        assert hues[60 - o] == pytest.approx(0.5 + shift, abs=1e-12), o


def test_the_worked_colours_from_the_spec():
    down, up = 40 + RELATED_DOWN[0], 40 + RELATED_UP[0]
    assert tile_colors(lit(40))[40].tolist() == [128, 255, 255]  # full brightness, nothing related lit: hue 180
    assert tile_colors(lit(40, down))[40].tolist() == [255, 128, 128]  # one "down" partner at full: hue 0, red
    assert tile_colors(lit(40, up))[40].tolist() == [255, 128, 128]  # one "up" partner at full: hue 360, the same red
    assert tile_colors(lit(40, down, up))[40].tolist() == [128, 255, 255]  # equal pull both ways: they cancel
    assert tile_colors(lit(40, at=64))[40].tolist() == [64, 128, 128]  # gray level 128, nothing related lit
    # a "down" partner at gray level 128 moves the hue to 0.5 - 0.5 * 128 / 255 (about 89.6 degrees)
    levels = lit(40)
    levels[down] = 64
    expected = [round(c * 255) for c in colorsys.hsv_to_rgb(0.5 - 0.5 * 128 / 255, 0.5, 1.0)]
    assert tile_colors(levels)[40].tolist() == expected


def test_partners_are_added_not_averaged_and_the_hue_is_clipped():
    # two "up" partners at gray level 64 (level 16) add up to 2 * 64/255 and move the hue twice as far as one does
    one = lit(40, at=64)
    one[40 + RELATED_UP[0]] = 16
    two = one.copy()
    two[40 + RELATED_UP[1]] = 16
    shift_one = tile_hues(one)[40] - 0.5
    shift_two = tile_hues(two)[40] - 0.5
    assert shift_two == pytest.approx(2 * shift_one, abs=1e-12)
    # many full-brightness partners clip at 360 degrees instead of going round the wheel
    everything = lit(40, *[40 + o for o in RELATED_UP])
    assert tile_hues(everything)[40] == 1.0


def test_partners_past_the_ends_are_silent_and_the_undrawn_notes_still_count():
    # note 84 is not drawn, but it is real: it is a partner of the tiles 84 - o
    hues = tile_hues(lit(84))
    for o in RELATED_DOWN:
        assert hues[84 - o] == 0.0, o
    for o in RELATED_UP:
        assert hues[84 - o] == 1.0, o
    # a tile at the very end has partners that do not exist; they count as silent
    assert tile_hues(lit(83))[83] == 0.5
    assert (tile_hues(lit(0))[0] == 0.5)


def test_hues_match_the_reference_and_stay_on_the_wheel():
    rng = np.random.default_rng(42)
    clipped = 0
    for _ in range(2000):
        levels = (rng.integers(0, 256, 88) * (rng.random(88) < 0.5)).astype(np.uint8)
        hues = tile_hues(levels)
        assert hues.shape == (84,)
        assert hues.min() >= 0.0 and hues.max() <= 1.0
        assert np.allclose(hues, ref_hues(levels), rtol=0, atol=1e-9)
        clipped += int(np.sum((hues == 0.0) | (hues == 1.0)))
    assert clipped > 0  # loud random frames do reach the ends of the wheel


def test_dim_realistic_frames_are_mostly_not_clipped():
    # music is mostly quiet: a few bright notes among many dim ones, as in the sample file
    rng = np.random.default_rng(1)
    unclipped = total = 0
    for _ in range(500):
        levels = (rng.random(88) ** 4 * 60).astype(np.uint8)  # dim values with the odd louder one
        hues = tile_hues(levels)
        unclipped += int(np.sum((hues > 0.0) & (hues < 1.0)))
        total += hues.size
    assert unclipped / total > 0.9


def test_all_four_notes_of_either_group_reach_red():
    for group in (RELATED_DOWN, RELATED_UP):
        levels = lit(*[40 + o for o in group])
        assert tile_hues(levels)[40] in (0.0, 1.0)  # 0 and 360 degrees are the same red
        assert tile_colors(levels)[40].tolist() == [0, 0, 0]  # tile 40 itself is dark here
    both = lit(40, *[40 + o for o in RELATED_DOWN])
    assert tile_hues(both)[40] == 0.0


def test_dark_tiles_are_black_and_lit_tiles_keep_their_brightness():
    rng = np.random.default_rng(5)
    for _ in range(300):
        levels = (rng.integers(0, 256, 88) * (rng.random(88) < 0.6)).astype(np.uint8)
        shown = displayed_levels(levels)
        colours = tile_colors(levels)
        assert colours.shape == (84, 3) and colours.dtype == np.uint8
        for n in range(84):
            if shown[n] == 0:
                assert colours[n].tolist() == [0, 0, 0]
            else:
                assert int(colours[n].max()) == shown[n]  # the brightest channel is the old gray level
                assert abs(int(colours[n].min()) - shown[n] / 2) <= 1  # saturation 50%


def test_the_hue_can_be_read_back_from_the_pixels():
    rng = np.random.default_rng(9)
    checked = 0
    for _ in range(300):
        levels = (rng.integers(0, 256, 88) * (rng.random(88) < 0.6)).astype(np.uint8)
        shown, expected = displayed_levels(levels), ref_hues(levels)
        colours = tile_colors(levels)
        for n in range(84):
            if shown[n] >= 128:
                h, _s, _v = colorsys.rgb_to_hsv(*(colours[n] / 255))
                assert hue_distance_degrees(h, expected[n]) <= 2.0, (n, h * 360, expected[n] * 360)
                checked += 1
    assert checked > 1000


def test_render_frame_is_an_rgb_image_of_flat_coloured_tiles():
    levels = (np.random.default_rng(3).integers(0, 256, 88) * 0.7).astype(np.uint8)
    img = render_frame(levels)
    assert img.mode == "RGB" and img.size == (252, 168)
    arr = np.asarray(img)
    colours = tile_colors(levels)
    for n in range(SHOWN_NOTES):
        assert (tile(arr, n) == colours[n]).all(), n  # one flat colour per tile, the colour from tile_colors


def test_a_silent_frame_is_black_in_every_channel():
    arr = np.asarray(render_frame(np.zeros(88, dtype=np.uint8)))
    assert arr.shape == (168, 252, 3) and not arr.any()


def test_the_same_levels_give_the_same_image():
    levels = np.random.default_rng(8).integers(0, 256, 88).astype(np.uint8)
    assert np.array_equal(np.asarray(render_frame(levels)), np.asarray(render_frame(levels.copy())))


def test_the_four_undrawn_notes_change_colours_but_never_brightness():
    base = (np.arange(88) * 2 % 256).astype(np.uint8)
    changed = base.copy()
    changed[84:] = 255 - base[84:]
    a, b = render_frame(base), render_frame(changed)
    assert np.array_equal(gray(a), gray(b))  # same brightness everywhere
    assert not np.array_equal(np.asarray(a), np.asarray(b))  # but colours near the top differ: they are partners
    assert np.array_equal(tile_hues(base)[:60], tile_hues(changed)[:60])  # far from the top nothing changes


def test_tile_hues_and_colors_need_at_least_84_levels():
    with pytest.raises(ValueError, match="84"):
        tile_hues(np.zeros(83, dtype=np.uint8))
    with pytest.raises(ValueError, match="84"):
        tile_colors(np.zeros(83, dtype=np.uint8))
    assert tile_hues(np.zeros(84, dtype=np.uint8)).shape == (84,)


@pytest.mark.parametrize("brightness", [2, 4, 50])
def test_written_png_files_decode_to_exactly_the_rendered_colours(tmp_path, brightness):
    """Frames are saved as indexed-colour PNGs (lossless, at most 84 colours) for speed; the pixels must be the
    same as the RGB image from render_frame, in every pixel and every channel."""
    frames = np.random.default_rng(0).random((6, 88)) * (np.random.default_rng(1).random((6, 88)) < 0.6)
    a, b = tmp_path / "a", tmp_path / "b"
    write_frames(frames, a, brightness=brightness)
    write_frames(frames, b, brightness=brightness)
    levels = to_gray_levels(frames)
    for i in range(len(frames)):
        path = a / f"frame_{i:06d}.png"
        img = Image.open(path)
        assert img.size == (252, 168)
        decoded = np.asarray(img.convert("RGB"))
        assert np.array_equal(decoded, np.asarray(render_frame(levels[i], brightness))), i
        assert path.read_bytes() == (b / path.name).read_bytes()  # deterministic


# --- smoothing also applies to the hues (feature 006 and 007) ---------------------------


def ref_hue_sequence(level_rows, smoothing, brightness=2):
    """Per-frame hues from the independent hue reference, then the running average written out by hand."""
    raw = [ref_hues(row, brightness) for row in level_rows]
    out = [raw[0].copy()]
    for n in range(1, len(raw)):
        out.append(smoothing * out[n - 1] + (1 - smoothing) * raw[n])
    return np.array(out)


def test_hue_sequence_without_smoothing_is_exactly_the_hues_of_each_frame():
    rng = np.random.default_rng(12)
    rows = (rng.integers(0, 256, (30, 88)) * (rng.random((30, 88)) < 0.5)).astype(np.uint8)
    seq = hue_sequence(rows)
    assert seq.shape == (30, 84)
    assert np.array_equal(seq, np.array([tile_hues(r) for r in rows]))
    assert np.array_equal(hue_sequence(rows, smoothing=0.0), seq)


@pytest.mark.parametrize("smoothing", [0.25, 0.5, 0.8])
def test_the_first_frames_hues_are_never_smoothed(smoothing):
    rows = (np.random.default_rng(13).integers(0, 256, (10, 88))).astype(np.uint8)
    assert np.array_equal(hue_sequence(rows, smoothing=smoothing)[0], tile_hues(rows[0]))


def test_the_hue_of_a_tile_is_a_running_average_of_its_own_hue():
    """Tile 40 sees a "down" partner appear at full brightness: its raw hue goes 0.5, 0, 0 and the smoothed hue 0.5, 0.25, 0.125."""
    partner = 40 + RELATED_DOWN[0]
    rows = np.array([lit(40), lit(40, partner), lit(40, partner)])
    assert [tile_hues(r)[40] for r in rows] == [0.5, 0.0, 0.0]
    seq = hue_sequence(rows, smoothing=0.5)
    assert seq[:, 40].tolist() == [0.5, 0.25, 0.125]


@pytest.mark.parametrize("smoothing", [0.1, 0.3, 0.5, 0.8])
def test_hue_smoothing_matches_the_reference_for_random_frames(smoothing):
    rng = np.random.default_rng(int(smoothing * 100))
    rows = (rng.integers(0, 256, (40, 88)) * (rng.random((40, 88)) < 0.4)).astype(np.uint8)
    seq = hue_sequence(rows, smoothing=smoothing)
    assert np.allclose(seq, ref_hue_sequence(rows, smoothing), rtol=0, atol=1e-9)
    assert seq.min() >= 0.0 and seq.max() <= 1.0  # smoothing never leaves the wheel


def test_each_tiles_hue_is_smoothed_only_from_its_own_history():
    rng = np.random.default_rng(14)
    rows = rng.integers(0, 256, (20, 88)).astype(np.uint8)
    other = rows.copy()
    other[:, 70] = rng.integers(0, 256, 20)  # note 70 is not tile 5's own note and not one of its partners
    assert 70 - 5 not in RELATED_DOWN + RELATED_UP
    a, b = hue_sequence(rows, smoothing=0.7), hue_sequence(other, smoothing=0.7)
    assert np.array_equal(a[:, 5], b[:, 5])
    assert not np.array_equal(a, b)  # but other tiles that note 70 is a partner of do change


def test_hue_sequence_handles_no_frames_and_one_frame():
    assert hue_sequence(np.zeros((0, 88), dtype=np.uint8), smoothing=0.5).shape == (0, 84)
    one = np.random.default_rng(15).integers(0, 256, (1, 88)).astype(np.uint8)
    assert np.array_equal(hue_sequence(one, smoothing=0.8), np.array([tile_hues(one[0])]))


def test_hue_sequence_rejects_a_smoothing_outside_the_range():
    rows = np.zeros((3, 88), dtype=np.uint8)
    for bad in (-0.1, 0.81, float("nan")):
        with pytest.raises(ValueError, match="smoothing"):
            hue_sequence(rows, smoothing=bad)


def test_tile_colors_can_take_the_hues_to_use():
    levels = (np.random.default_rng(16).integers(0, 256, 88)).astype(np.uint8)
    assert np.array_equal(tile_colors(levels, 2, tile_hues(levels)), tile_colors(levels))
    shifted = np.full(84, 0.25)
    colours = tile_colors(levels, 2, shifted)
    for n in range(84):
        v = displayed_levels(levels)[n] / 255
        expected = [round(c * 255) for c in colorsys.hsv_to_rgb(0.25, 0.5, v)]
        assert np.abs(colours[n].astype(int) - expected).max() <= 1, n
    with pytest.raises(ValueError, match="84 hues"):
        tile_colors(levels, 2, np.zeros(83))


def test_written_frames_have_smoothed_values_and_smoothed_hues(tmp_path):
    """End to end through write_frames: the colour of tile 40 follows a hand-computed pipeline."""
    partner = 40 + RELATED_DOWN[0]
    values = np.zeros((4, 88))
    values[:, 40] = 1.0
    values[1:, partner] = 1.0  # the partner switches on at frame 1
    s = 0.5
    smoothed = [list(values[0])]
    for n in range(1, 4):
        smoothed.append([s * smoothed[n - 1][k] + (1 - s) * values[n][k] for k in range(88)])
    levels = to_gray_levels(np.array(smoothed))
    hue_rows = ref_hue_sequence(levels, s)

    write_frames(values, tmp_path, brightness=2, smoothing=s)
    for i in range(4):
        img = np.asarray(Image.open(tmp_path / f"frame_{i:06d}.png").convert("RGB"))
        pixel = img[(40 // 12) * 24 + 12, (40 % 12) * 21 + 10]
        v = displayed_levels(levels[i])[40] / 255
        expected = [round(c * 255) for c in colorsys.hsv_to_rgb(hue_rows[i][40], 0.5, v)]
        assert np.abs(pixel.astype(int) - expected).max() <= 1, (i, pixel, expected)
    # the hue really is being smoothed: frame 1's smoothed hue is between the old hue (0.5) and the new raw hue
    raw_hue_frame_1 = ref_hues(levels[1])[40]
    assert raw_hue_frame_1 < hue_rows[1][40] < 0.5


def test_write_frames_without_smoothing_does_not_change_the_hues(tmp_path):
    values = np.random.default_rng(17).random((5, 88)) * (np.random.default_rng(18).random((5, 88)) < 0.5)
    a, b = tmp_path / "a", tmp_path / "b"
    write_frames(values, a)
    write_frames(values, b, smoothing=0.0)
    levels = to_gray_levels(values)
    for i in range(5):
        pa = a / f"frame_{i:06d}.png"
        assert pa.read_bytes() == (b / pa.name).read_bytes()
        assert np.array_equal(np.asarray(Image.open(pa).convert("RGB")), np.asarray(render_frame(levels[i])))
