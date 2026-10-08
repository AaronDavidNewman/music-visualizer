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
    DEFAULT_VALUE,
    SHOWN_NOTES,
    TILE_HEIGHT,
    TILE_WIDTH,
    average_frames,
    boost_levels,
    frame_count,
    hidden_notes,
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
    """Each pixel's level: the largest colour channel minus the smallest.

    A tile's HSV saturation is its gray level (after the brightness root), and an image drawn at the default full
    brightness has 255 as its largest channel everywhere, so largest minus smallest is 255 times the saturation:
    the displayed gray level of the tile.
    """
    rgb = np.asarray(image.convert("RGB")).astype(int)
    return rgb.max(axis=2) - rgb.min(axis=2)


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
    assert not gray(render_frame(only_omitted)).any()  # nothing appears anywhere (no tile gets any saturation)
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


def test_a_frame_with_no_levels_has_no_saturation_anywhere():
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
    assert DEFAULT_VALUE == 1.0
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
    # the tile's level is its saturation; the frame's brightness (value) is 1 here, as it is by default
    assert tile_colors(lit(40))[40].tolist() == [0, 255, 255]  # full level, nothing related lit: hue 180, saturation 100%
    assert tile_colors(lit(40, down))[40].tolist() == [255, 0, 0]  # one "down" partner at full: hue 0, red
    assert tile_colors(lit(40, up))[40].tolist() == [255, 0, 0]  # one "up" partner at full: hue 360, the same red
    assert tile_colors(lit(40, down, up))[40].tolist() == [0, 255, 255]  # equal pull both ways: they cancel
    assert tile_colors(lit(40, at=64))[40].tolist() == [127, 255, 255]  # gray level 128: saturation 50%, nothing related lit
    # a "down" partner at gray level 128 moves the hue to 0.5 - 0.5 * 128 / 255 (about 89.6 degrees)
    levels = lit(40)
    levels[down] = 64
    expected = [round(c * 255) for c in colorsys.hsv_to_rgb(0.5 - 0.5 * 128 / 255, 1.0, 1.0)]
    assert tile_colors(levels)[40].tolist() == expected
    # the frame's brightness is the value: half of it halves every channel, whatever the saturation
    assert tile_colors(lit(40), value=0.5)[40].tolist() == [0, 128, 128]
    assert tile_colors(lit(40, at=64), value=0.5)[40].tolist() == [64, 128, 128]


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
        assert tile_colors(levels)[40].tolist() == [255, 255, 255]  # tile 40 itself has no level: no saturation, plain white
    both = lit(40, *[40 + o for o in RELATED_DOWN])
    assert tile_hues(both)[40] == 0.0


def test_unlit_tiles_are_plain_white_and_lit_tiles_are_saturated_by_their_level():
    rng = np.random.default_rng(5)
    for _ in range(300):
        levels = (rng.integers(0, 256, 88) * (rng.random(88) < 0.6)).astype(np.uint8)
        shown = displayed_levels(levels)
        colours = tile_colors(levels)
        assert colours.shape == (84, 3) and colours.dtype == np.uint8
        for n in range(84):
            assert int(colours[n].max()) == 255  # the frame is at full brightness: every tile's brightest channel
            if shown[n] == 0:
                assert colours[n].tolist() == [255, 255, 255]  # no level, no saturation
            else:
                assert abs(int(colours[n].max()) - int(colours[n].min()) - shown[n]) <= 1  # saturation = the gray level


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


def test_a_frame_with_no_brightness_is_black_in_every_channel():
    levels = (np.random.default_rng(4).integers(0, 256, 88)).astype(np.uint8)
    arr = np.asarray(render_frame(levels, value=0.0))
    assert arr.shape == (168, 252, 3) and not arr.any()
    # and at full brightness a frame with no levels is plain white: brightness is the frame's, not the tile's
    assert (np.asarray(render_frame(np.zeros(88, dtype=np.uint8))) == 255).all()


def test_the_same_levels_give_the_same_image():
    levels = np.random.default_rng(8).integers(0, 256, 88).astype(np.uint8)
    assert np.array_equal(np.asarray(render_frame(levels)), np.asarray(render_frame(levels.copy())))


def test_the_four_undrawn_notes_change_colours_but_never_saturation():
    base = (np.arange(88) * 2 % 256).astype(np.uint8)
    changed = base.copy()
    changed[84:] = 255 - base[84:]
    a, b = render_frame(base), render_frame(changed)
    assert np.array_equal(gray(a), gray(b))  # same saturation everywhere
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
        s = displayed_levels(levels)[n] / 255
        expected = [round(c * 255) for c in colorsys.hsv_to_rgb(0.25, s, 1.0)]
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
        s = displayed_levels(levels[i])[40] / 255
        expected = [round(c * 255) for c in colorsys.hsv_to_rgb(hue_rows[i][40], s, 1.0)]
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


# --- discrete colour levels (feature 010) ----------------------------------------------------------------------------

LEVEL_FRAMES = np.random.default_rng(3).uniform(0.0, 1.0, (6, 88)) ** 3
LEVEL_ENERGIES = np.array([1.0, 0.7, 0.4, 0.2, 0.05, 0.0])
# an RGB tile read back as 8-bit colour: saturation and hue are only reliable for bright, colourful tiles
HSV_TOLERANCE = 0.03


def read_tiles_hsv(path):
    """(84, 3) array of hue (0..1), saturation, value of every tile of a written frame, from its centre pixel."""
    rgb = np.asarray(Image.open(path).convert("RGB"))
    rows = [(n // GRID_COLUMNS) * TILE_HEIGHT + TILE_HEIGHT // 2 for n in range(SHOWN_NOTES)]
    cols = [(n % GRID_COLUMNS) * TILE_WIDTH + TILE_WIDTH // 2 for n in range(SHOWN_NOTES)]
    return np.array([colorsys.rgb_to_hsv(*(rgb[r, c] / 255.0)) for r, c in zip(rows, cols)])


def write_level_frames(directory, frames=LEVEL_FRAMES, energies=LEVEL_ENERGIES, **kwargs):
    write_frames(frames, directory, energies=energies, **kwargs)
    return [read_tiles_hsv(directory / f"frame_{i:06d}.png") for i in range(frames.shape[0])]


def frame_files(directory):
    return {p.name: p.read_bytes() for p in sorted(directory.glob("*.png"))}


def distance_to_levels(values, step, scale):
    levels = np.arange(0, scale + 1, step) / scale
    return np.abs(np.asarray(values)[:, None] - levels[None, :]).min(axis=1)


def test_tile_colors_saturation_step_gives_only_the_levels_and_leaves_hue_and_value_alone():
    levels = np.arange(84) * 3 % 256
    plain = tile_colors(levels, 2, value=0.9)
    stepped = tile_colors(levels, 2, value=0.9, saturation_step=20)
    plain_hsv = np.array([colorsys.rgb_to_hsv(*(c / 255.0)) for c in plain])
    hsv = np.array([colorsys.rgb_to_hsv(*(c / 255.0)) for c in stepped])
    assert (distance_to_levels(hsv[:, 1], 20, 100) < HSV_TOLERANCE).all()
    assert len(set(np.round(hsv[:, 1], 1))) > 2  # several different levels really occur
    assert stepped.max(axis=1).tolist() == plain.max(axis=1).tolist()  # value
    colored = (hsv[:, 1] > 0.3) & (plain_hsv[:, 1] > 0.3)
    assert np.abs(hsv[colored, 0] - plain_hsv[colored, 0]).max() < 0.02  # hue


def test_tile_colors_without_a_step_or_with_na_is_unchanged():
    levels = np.arange(84) * 3 % 256
    assert (tile_colors(levels, 2, saturation_step=None) == tile_colors(levels, 2)).all()


@pytest.mark.parametrize("step", [0, 7, 51, 2.5, True, "20", float("nan")])
def test_tile_colors_refuses_a_step_that_is_not_allowed(step):
    with pytest.raises(ValueError, match="The saturation step must be N/A or one of 5, 10, 20, 50."):
        tile_colors(np.arange(84), 2, saturation_step=step)


def test_a_black_tile_stays_black_with_any_saturation_step():
    assert not tile_colors(np.arange(84) * 3, 2, value=0.0, saturation_step=50).any()


def test_write_frames_with_na_steps_is_byte_identical_to_no_steps(tmp_path):
    write_frames(LEVEL_FRAMES, tmp_path / "a", energies=LEVEL_ENERGIES, smoothing=0.3)
    write_frames(
        LEVEL_FRAMES,
        tmp_path / "b",
        energies=LEVEL_ENERGIES,
        smoothing=0.3,
        hue_step=None,
        saturation_step=None,
        value_step=None,
    )
    assert frame_files(tmp_path / "a") == frame_files(tmp_path / "b")


def test_hue_step_rounds_every_hue_and_changes_nothing_else(tmp_path):
    plain = write_level_frames(tmp_path / "a")
    stepped = write_level_frames(tmp_path / "b", hue_step=90)
    seen = 0
    for p, s in zip(plain, stepped):
        assert np.abs(p[:, 1:] - s[:, 1:]).max() < HSV_TOLERANCE  # saturation and value unchanged
        good = (s[:, 1] > 0.3) & (s[:, 2] > 0.4)
        degrees = s[good, 0] * 360
        assert (np.abs(((degrees + 45) % 90) - 45) < 3).all()  # a multiple of 90 (360 is the same red as 0)
        seen += int(good.sum())
    assert seen > 20


def test_saturation_step_rounds_every_saturation_and_changes_nothing_else(tmp_path):
    plain = write_level_frames(tmp_path / "a")
    stepped = write_level_frames(tmp_path / "b", saturation_step=20)
    seen = 0
    for p, s in zip(plain, stepped):
        bright = s[:, 2] > 0.4
        assert (distance_to_levels(s[bright, 1], 20, 100) < HSV_TOLERANCE).all()
        assert np.abs(p[:, 2] - s[:, 2]).max() < HSV_TOLERANCE  # value unchanged
        seen += int(bright.sum())
    assert seen > 100


def test_value_step_rounds_every_frames_brightness_and_changes_nothing_else(tmp_path):
    plain = write_level_frames(tmp_path / "a")
    stepped = write_level_frames(tmp_path / "b", value_step=50)
    for i, (p, s) in enumerate(zip(plain, stepped)):
        brightest = float(s[:, 2].max())
        assert round(brightest * 255) in (0, 128, 255)
        assert abs(np.median(s[:, 2]) - brightest) < HSV_TOLERANCE or brightest == 0  # one value per frame
    values = [round(float(s[:, 2].max()) * 255) for s in stepped]
    assert values[0] == 255  # the loudest frame stays fully bright
    assert values[-1] == 0  # no energy stays black
    for p, s in zip(plain, stepped):
        lit = (p[:, 2] > 0.4) & (s[:, 2] > 0.4)
        if lit.any():
            assert np.abs(p[lit, 1] - s[lit, 1]).max() < 0.05  # saturation unchanged where it can be read


def test_na_for_two_properties_leaves_them_exactly_as_with_the_third_alone(tmp_path):
    write_frames(LEVEL_FRAMES, tmp_path / "a", energies=LEVEL_ENERGIES, value_step=50)
    write_frames(LEVEL_FRAMES, tmp_path / "b", energies=LEVEL_ENERGIES, hue_step=None, saturation_step=None, value_step=50)
    assert frame_files(tmp_path / "a") == frame_files(tmp_path / "b")


def test_value_step_without_energies_keeps_full_brightness(tmp_path):
    write_frames(LEVEL_FRAMES, tmp_path, value_step=50)
    assert all(read_tiles_hsv(p)[:, 2].max() > 0.99 for p in sorted(tmp_path.glob("*.png")))


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"hue_step": 5}, "The hue step must be N/A or one of 12, 36, 90, 180."),
        ({"saturation_step": 90}, "The saturation step must be N/A or one of 5, 10, 20, 50."),
        ({"value_step": 0}, "The brightness step must be N/A or one of 5, 10, 20, 50."),
    ],
)
def test_write_frames_refuses_a_bad_step_before_writing_anything(tmp_path, kwargs, message):
    with pytest.raises(ValueError, match=message):
        write_frames(LEVEL_FRAMES, tmp_path / "out", energies=LEVEL_ENERGIES, **kwargs)
    assert not (tmp_path / "out").exists() or not list((tmp_path / "out").glob("*.png"))


# --- interactions with smoothing, the roots and the length of the file (feature 010, User Story 3) -------------------


def brightest_channel(path):
    return int(np.asarray(Image.open(path).convert("RGB")).max())


def test_rounding_is_applied_after_smoothing(tmp_path):
    # energies 1, 0, 0 smooth (0.5) to brightness 1, 0.5, 0.25; 0.25 rounds to 0.5 with step 50.
    # Rounding first and smoothing after would leave 0.25 (64) in the last frame.
    write_frames(np.ones((3, 88)), tmp_path, energies=np.array([1.0, 0.0, 0.0]), smoothing=0.5, value_step=50)
    assert [brightest_channel(tmp_path / f"frame_{i:06d}.png") for i in range(3)] == [255, 128, 128]


def test_smoothed_saturations_are_rounded_to_the_levels(tmp_path):
    frames = write_level_frames(tmp_path, smoothing=0.8, saturation_step=50)
    seen = set()
    for hsv in frames:
        bright = hsv[:, 2] > 0.4
        assert (distance_to_levels(hsv[bright, 1], 50, 100) < HSV_TOLERANCE).all()
        seen |= set(np.round(hsv[bright, 1] * 2).astype(int))
    assert len(seen) >= 2


@pytest.mark.parametrize("root", range(1, 9))
def test_the_loudest_frame_stays_fully_bright_and_silence_black_at_every_root(tmp_path, root):
    write_frames(LEVEL_FRAMES, tmp_path, energies=LEVEL_ENERGIES, energy_root=root, value_step=50)
    tops = [brightest_channel(tmp_path / f"frame_{i:06d}.png") for i in range(LEVEL_FRAMES.shape[0])]
    assert tops[0] == 255 and tops[-1] == 0
    assert set(tops) <= {0, 128, 255}


@pytest.mark.parametrize("root", [2, 100])
def test_the_saturation_root_is_applied_before_the_levels(tmp_path, root):
    frames = write_level_frames(tmp_path, brightness=root, saturation_step=20)
    for hsv in frames:
        bright = hsv[:, 2] > 0.4
        assert (distance_to_levels(hsv[bright, 1], 20, 100) < HSV_TOLERANCE).all()
    levels = np.zeros(84, dtype=np.int64)  # a tile with no level stays unsaturated at every root and step
    rgb = tile_colors(levels, root, value=1.0, saturation_step=20)
    assert (rgb[:, 0] == rgb[:, 1]).all() and (rgb[:, 1] == rgb[:, 2]).all()


@pytest.mark.parametrize(
    "kwargs",
    [{"hue_step": 36}, {"saturation_step": 10}, {"value_step": 20}, {"hue_step": 90, "saturation_step": 20, "value_step": 50}],
)
def test_adding_silence_at_the_end_changes_no_earlier_frame(tmp_path, kwargs):
    # The colors are scaled against the loudest value of the file, so only quiet or silent frames can be appended.
    silent = np.zeros((3, 88))
    longer = np.vstack([LEVEL_FRAMES, silent])
    longer_energies = np.concatenate([LEVEL_ENERGIES, np.zeros(3)])
    write_frames(LEVEL_FRAMES, tmp_path / "short", energies=LEVEL_ENERGIES, smoothing=0.3, **kwargs)
    write_frames(longer, tmp_path / "long", energies=longer_energies, smoothing=0.3, **kwargs)
    short, long = frame_files(tmp_path / "short"), frame_files(tmp_path / "long")
    assert len(short) == 6 and len(long) == 9
    assert all(long[name] == data for name, data in short.items())


def test_silent_frames_stay_black_with_every_step(tmp_path):
    frames = write_level_frames(
        tmp_path, hue_step=12, saturation_step=5, value_step=5, energies=np.array([1.0, 0.5, 0.2, 0.1, 0.0, 0.0])
    )
    assert not frames[-1][:, 2].any() and not frames[-2][:, 2].any()
    assert not any(np.asarray(Image.open(p).convert("RGB")).any() for p in sorted(tmp_path.glob("*.png"))[-2:])


def test_the_largest_steps_together_leave_a_handful_of_flat_colours(tmp_path):
    frames = write_level_frames(tmp_path, hue_step=180, saturation_step=50, value_step=50)
    seen_hues = set()
    for hsv in frames:
        top = float(hsv[:, 2].max())
        assert round(top * 255) in (0, 128, 255)
        bright = hsv[:, 2] > 0.4
        assert (distance_to_levels(hsv[bright, 1], 50, 100) < HSV_TOLERANCE).all()
        good = bright & (hsv[:, 1] > 0.3)
        degrees = hsv[good, 0] * 360
        assert (np.minimum(np.abs(degrees - 180), np.minimum(degrees, 360 - degrees)) < 3).all()  # red or cyan
        seen_hues |= set(np.round(degrees / 180).astype(int) % 2)
    assert seen_hues  # coloured tiles really were found


# --- the note threshold (feature 011) --------------------------------------------------------------------------------


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


# --- hiding notes when drawing (feature 011) -------------------------------------------------------------------------


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


def test_tile_colors_hidden_tiles_are_black_and_the_rest_unchanged():
    levels = np.arange(84) * 3 % 256
    hidden = np.zeros(84, dtype=bool)
    hidden[[3, 10, 50]] = True
    plain = tile_colors(levels, 2, value=0.9)
    masked = tile_colors(levels, 2, value=0.9, hidden=hidden)
    assert plain[hidden].any(axis=1).all()  # they were visible
    assert not masked[hidden].any()  # RGB (0, 0, 0) is HSV (0, 0, 0)
    assert (masked[~hidden] == plain[~hidden]).all()


def test_tile_colors_without_a_mask_or_with_an_empty_one_is_unchanged_and_a_full_one_is_black():
    levels = np.arange(84) * 3 % 256
    plain = tile_colors(levels, 2)
    assert (tile_colors(levels, 2, hidden=None) == plain).all()
    assert (tile_colors(levels, 2, hidden=np.zeros(84, dtype=bool)) == plain).all()
    assert not tile_colors(levels, 2, hidden=np.ones(84, dtype=bool)).any()


@pytest.mark.parametrize("bad", [np.zeros(83, dtype=bool), np.zeros((84, 1), dtype=bool), np.zeros(84, dtype=int)])
def test_tile_colors_refuses_a_mask_of_the_wrong_shape_or_type(bad):
    with pytest.raises(ValueError):
        tile_colors(np.arange(84), 2, hidden=bad)


def test_a_hidden_note_still_shifts_the_hue_of_the_tiles_it_is_related_to():
    levels = np.zeros(88, dtype=np.int64)
    levels[24] = 255
    levels[24 + RELATED_DOWN[0]] = 255  # a partner that pulls tile 24's hue down to red
    hidden = np.zeros(84, dtype=bool)
    hidden[24 + RELATED_DOWN[0]] = True
    masked = tile_colors(levels, 2, hidden=hidden)
    without_partner = levels.copy()
    without_partner[24 + RELATED_DOWN[0]] = 0
    assert not masked[24 + RELATED_DOWN[0]].any()
    assert masked[24].tolist() == tile_colors(levels, 2)[24].tolist()
    assert masked[24].tolist() != tile_colors(without_partner, 2)[24].tolist()


def test_write_frames_with_threshold_zero_is_byte_identical_to_no_threshold(tmp_path):
    common = dict(energies=LEVEL_ENERGIES, smoothing=0.3, hue_step=36, saturation_step=10, value_step=20)
    write_frames(LEVEL_FRAMES, tmp_path / "a", **common)
    write_frames(LEVEL_FRAMES, tmp_path / "b", threshold=0, **common)
    write_frames(LEVEL_FRAMES, tmp_path / "c", threshold=0.0, **common)
    assert frame_files(tmp_path / "a") == frame_files(tmp_path / "b") == frame_files(tmp_path / "c")


LOUD, FAINT = 24, 40
LOUD_AND_FAINT = np.zeros((4, 88))
LOUD_AND_FAINT[:, LOUD] = 1.0
LOUD_AND_FAINT[:, FAINT] = [0.05, 0.05, 0.07, 0.09]  # share of the largest note value (1.0) in each frame


def test_a_faint_note_is_black_while_it_is_below_the_threshold_and_a_loud_one_is_unchanged(tmp_path):
    off = written_tiles(tmp_path / "off", LOUD_AND_FAINT)
    at_6 = written_tiles(tmp_path / "t6", LOUD_AND_FAINT, threshold=6)
    for f in range(4):
        assert off[f][LOUD].any() and off[f][FAINT].any()  # both are visible with the threshold off
        assert at_6[f][LOUD].tolist() == off[f][LOUD].tolist()
    assert not at_6[0][FAINT].any() and not at_6[1][FAINT].any()  # 0.05 is below 0.06
    assert at_6[2][FAINT].tolist() == off[2][FAINT].tolist()  # 0.07 and 0.09 are not
    assert at_6[3][FAINT].tolist() == off[3][FAINT].tolist()


def test_a_threshold_below_every_value_changes_neither_note(tmp_path):
    off = written_tiles(tmp_path / "off", LOUD_AND_FAINT)
    at_4 = written_tiles(tmp_path / "t4", LOUD_AND_FAINT, threshold=4)
    for f in range(4):
        assert at_4[f][[LOUD, FAINT]].tolist() == off[f][[LOUD, FAINT]].tolist()


def test_the_threshold_is_the_same_level_for_every_frame_of_the_file(tmp_path):
    # in a quiet frame the loud note of the file is only 5% of the file's largest value: it is hidden there
    values = np.zeros((2, 88))
    values[0, LOUD] = 1.0
    values[1, LOUD] = 0.05
    tiles = written_tiles(tmp_path, values, threshold=8)
    assert tiles[0][LOUD].any() and not tiles[1][LOUD].any()


@pytest.fixture(scope="module")
def planted_peak_frames():
    values = LEVEL_FRAMES.copy()
    values[2, 40] = 2.0  # the largest value of the file, on a drawn note
    return values


def test_every_tile_is_black_or_exactly_the_tile_without_a_threshold_at_every_threshold(tmp_path, planted_peak_frames):
    off = written_tiles(tmp_path / "off", planted_peak_frames, energies=LEVEL_ENERGIES)
    for t in range(1, 11):
        got = written_tiles(tmp_path / f"t{t}", planted_peak_frames, energies=LEVEL_ENERGIES, threshold=t)
        for f in range(len(off)):
            black = ~got[f].any(axis=1)
            assert (got[f][~black] == off[f][~black]).all(), (t, f)
        assert got[2][40].any(), t  # the note with the largest value is shown at every threshold


def test_a_silent_file_is_entirely_black_at_any_threshold(tmp_path):
    tiles = written_tiles(tmp_path, np.zeros((3, 88)), energies=np.zeros(3), threshold=10)
    assert not any(t.any() for t in tiles)
    for path in tmp_path.glob("*.png"):
        assert not np.asarray(Image.open(path).convert("RGB")).any()


@pytest.mark.parametrize("bad", [-1, 11, float("nan"), float("inf"), True, "20"])
def test_write_frames_refuses_a_bad_threshold_before_writing_anything(tmp_path, bad):
    with pytest.raises(ValueError, match="The threshold must be a number from 0 to 10."):
        write_frames(LEVEL_FRAMES, tmp_path / "out", energies=LEVEL_ENERGIES, threshold=bad)
    assert not (tmp_path / "out").exists() or not list((tmp_path / "out").glob("*.png"))


# --- the threshold with smoothing, the roots, the steps and the length of the file (feature 011, User Story 3) --------


def black_tiles(path):
    return {n for n, colour in enumerate(tile_rgb(path)) if not colour.any()}


def black_sets(directory, count):
    return [black_tiles(directory / f"frame_{i:06d}.png") for i in range(count)]


def test_a_fading_note_turns_black_in_the_first_frame_whose_smoothed_value_is_below_the_threshold(tmp_path):
    values = np.zeros((14, 88))
    values[:2, LOUD] = 1.0  # the note stops after two frames; smoothing 0.8 makes it fade slowly
    smoothed = smooth_frames(values, 0.8)[:, LOUD]
    first_hidden = int(np.argmax(smoothed < 0.1))  # the first frame whose smoothed value is below 10% of the peak (1.0)
    assert 5 < first_hidden < 13  # the setup really fades over several frames
    write_frames(values, tmp_path, smoothing=0.8, threshold=10)
    for i in range(14):
        assert (LOUD in black_tiles(tmp_path / f"frame_{i:06d}.png")) == (i >= first_hidden), i


def test_the_hidden_set_does_not_depend_on_the_roots_or_the_steps(tmp_path):
    count = LEVEL_FRAMES.shape[0]
    write_frames(LEVEL_FRAMES, tmp_path / "base", threshold=10)
    base = black_sets(tmp_path / "base", count)
    assert any(base) and all(len(s) < SHOWN_NOTES for s in base)  # some notes hidden, some shown
    variations = [
        {"brightness": 100},
        {"saturation_step": 5},
        {"saturation_step": 50},
        {"hue_step": 12},
        {"hue_step": 180},
        {"hue_step": 90, "saturation_step": 20},
    ]
    for n, extra in enumerate(variations):
        write_frames(LEVEL_FRAMES, tmp_path / f"v{n}", threshold=10, **extra)
        assert black_sets(tmp_path / f"v{n}", count) == base, extra


@pytest.mark.parametrize("root", range(1, 9))
def test_the_hidden_set_does_not_depend_on_the_brightness_root(tmp_path, root):
    energies = np.array([1.0, 0.7, 0.4, 0.2, 0.05, 0.05])  # every frame has some brightness, so only the mask is black
    write_frames(LEVEL_FRAMES, tmp_path / "base", threshold=10, energies=energies)
    write_frames(LEVEL_FRAMES, tmp_path / "root", threshold=10, energies=energies, energy_root=root)
    assert black_sets(tmp_path / "root", 6) == black_sets(tmp_path / "base", 6)
    write_frames(LEVEL_FRAMES, tmp_path / "plain", threshold=10)  # and the same notes are hidden without energies
    assert black_sets(tmp_path / "plain", 6) == black_sets(tmp_path / "base", 6)


@pytest.mark.parametrize(
    "steps",
    [
        {"hue_step": 12, "saturation_step": 5, "value_step": 5},
        {"hue_step": 180, "saturation_step": 50, "value_step": 50},
        {"hue_step": 36, "saturation_step": 10},
    ],
)
def test_hidden_tiles_are_black_with_any_steps_and_the_others_are_the_tiles_without_a_threshold(tmp_path, steps):
    off = written_tiles(tmp_path / "off", LEVEL_FRAMES, **steps)
    got = written_tiles(tmp_path / "on", LEVEL_FRAMES, threshold=10, **steps)
    mask = hidden_notes(LEVEL_FRAMES, 10)
    for f in range(len(off)):
        assert not got[f][mask[f]].any()
        shown = ~mask[f]
        assert (got[f][shown] == off[f][shown]).all()


def test_a_frame_whose_notes_are_all_hidden_is_entirely_black_and_its_neighbours_are_not(tmp_path):
    values = np.zeros((3, 88))
    values[0, LOUD] = values[2, LOUD] = 1.0
    values[1, :] = 0.05
    values[1, LOUD] = 0.05
    tiles = written_tiles(tmp_path, values, threshold=10)
    assert not tiles[1].any()
    assert tiles[0][LOUD].any() and tiles[2][LOUD].any()


def test_adding_silence_at_the_end_changes_no_earlier_frame_with_a_threshold(tmp_path):
    longer = np.vstack([LEVEL_FRAMES, np.zeros((3, 88))])
    longer_energies = np.concatenate([LEVEL_ENERGIES, np.zeros(3)])
    kwargs = dict(smoothing=0.3, threshold=10, hue_step=36, saturation_step=10, value_step=20)
    write_frames(LEVEL_FRAMES, tmp_path / "short", energies=LEVEL_ENERGIES, **kwargs)
    write_frames(longer, tmp_path / "long", energies=longer_energies, **kwargs)
    short, long = frame_files(tmp_path / "short"), frame_files(tmp_path / "long")
    assert len(short) == 6 and len(long) == 9
    assert all(long[name] == data for name, data in short.items())
