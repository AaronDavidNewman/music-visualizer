"""The beat wave of the contour picture: ``write_contour_frames`` and the ``contour`` branch of ``write_frames`` (feature 028)."""

import numpy as np
import pytest
from PIL import Image

from app.services.beat_wave import wave_modifier
from app.services.colormaps import COLORMAPS, lookup_table
from app.services.contour import write_contour_frames
from app.services.frame_rendering import write_frames
from app.services.image_types import IMAGE_TYPES

from .frame_size import HEIGHT, WIDTH

COLORMAP = COLORMAPS[0]
MESSAGE = "The wave count must be a whole number from 2 to 10."


@pytest.fixture
def seen(monkeypatch):
    """A spy on ``Axes.contourf`` (it calls the real one): a list of dicts with ``Z``, ``levels``, ``vmin`` and ``vmax`` of every call."""
    from matplotlib.axes import Axes

    calls = []
    original = Axes.contourf

    def spy(self, x, y, z, *args, **kwargs):
        calls.append({"Z": np.array(z), "levels": np.array(kwargs["levels"]), "vmin": kwargs["vmin"], "vmax": kwargs["vmax"]})
        return original(self, x, y, z, *args, **kwargs)

    monkeypatch.setattr(Axes, "contourf", spy)
    return calls


def grid_values(frames=1, rows=7, columns=12, seed=3):
    """Frames of different, all positive, values in ``(frames, rows * columns)``."""
    rng = np.random.default_rng(seed)
    return rng.random((frames, rows * columns)) * 4 + 1


def draw(directory, values, rows=7, columns=12, beat=None, peak=None, **options):
    write_contour_frames(values, float(values.max()) if peak is None else peak, COLORMAP, directory, columns, rows, WIDTH, HEIGHT, beat=beat, **options)
    return sorted(directory.glob("frame_*.png"))


def read(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(int)


def files(directory):
    return [p.read_bytes() for p in sorted(directory.glob("frame_*.png"))]


# ---- the plain picture is untouched -----------------------------------------------------------------------------------------------


def test_no_beat_and_a_beat_of_zeros_and_the_default_argument_make_byte_identical_files(tmp_path):
    values = grid_values(3)
    draw(tmp_path / "a", values)
    draw(tmp_path / "b", values, beat=None)
    draw(tmp_path / "c", values, beat=np.zeros(3))
    draw(tmp_path / "d", values, beat=np.zeros(3), waves=9)
    assert files(tmp_path / "a") == files(tmp_path / "b") == files(tmp_path / "c") == files(tmp_path / "d")


def test_at_the_minimum_of_the_beat_the_grid_handed_to_matplotlib_is_the_plain_grid(tmp_path, seen):
    values = grid_values(2)
    draw(tmp_path / "plain", values)
    plain = [c["Z"] for c in seen]
    seen.clear()
    draw(tmp_path / "zero", values, beat=[0.0, 0.0])
    assert len(seen) == 2
    for call, grid in zip(seen, plain):
        assert np.array_equal(call["Z"], grid)


# ---- the wave --------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("rows, columns", [(7, 12), (14, 24)])
@pytest.mark.parametrize("waves", [2, 4, 10])
@pytest.mark.parametrize("k", [0.25, 0.5, 1.0])
def test_the_grid_handed_to_matplotlib_is_the_plain_grid_times_the_modifier(tmp_path, seen, rows, columns, waves, k):
    values = grid_values(1, rows, columns)
    draw(tmp_path / "plain", values, rows, columns)
    plain = seen[0]["Z"]
    seen.clear()
    draw(tmp_path / "wave", values, rows, columns, beat=[k], waves=waves)
    assert len(seen) == 1
    expected = plain * wave_modifier(rows, columns, waves, k)
    assert np.allclose(seen[0]["Z"], expected, atol=1e-12, rtol=0)


def test_the_color_scale_is_the_one_of_the_frame_before_the_wave_and_the_levels_span_the_modified_grid(tmp_path, seen):
    values = grid_values(1)
    draw(tmp_path / "plain", values)
    top = float(values.max())
    seen.clear()
    draw(tmp_path / "wave", values, beat=[0.5])
    call = seen[0]
    assert call["vmin"] == 0 and call["vmax"] == pytest.approx(top)  # not the largest value after the wave
    assert call["Z"].max() < top
    assert len(call["levels"]) == 12
    assert call["levels"][0] == pytest.approx(call["Z"].min()) and call["levels"][-1] == pytest.approx(call["Z"].max())


def test_the_picture_changes_more_and_more_up_to_half_way_up_the_beat_and_is_the_plain_one_again_at_its_top(tmp_path):
    values = grid_values(1)
    draw(tmp_path / "plain", values)
    plain = read(tmp_path / "plain" / "frame_000000.png")
    differences = {}
    for k in (0.1, 0.25, 0.5, 0.75, 1.0):
        draw(tmp_path / f"k{k}", values, beat=[k])
        differences[k] = float(np.abs(read(tmp_path / f"k{k}" / "frame_000000.png") - plain).mean())
    assert 0 < differences[0.1] < differences[0.25] < differences[0.5]
    assert differences[0.75] < differences[0.5]  # coming down the beat
    assert differences[1.0] < 0.01  # the top of the beat: all but exactly the plain picture


def test_the_input_values_are_not_changed(tmp_path):
    values = grid_values(2)
    before = values.copy()
    draw(tmp_path, values, beat=[0.5, 1.0])
    assert np.array_equal(values, before)


def test_the_files_are_the_same_on_two_runs(tmp_path):
    values = grid_values(3)
    draw(tmp_path / "a", values, beat=[0.2, 0.6, 1.0], waves=6)
    draw(tmp_path / "b", values, beat=[0.2, 0.6, 1.0], waves=6)
    assert files(tmp_path / "a") == files(tmp_path / "b")


def test_every_frame_uses_its_own_position_also_when_only_some_frames_are_drawn(tmp_path, seen):
    values = grid_values(4)
    beat = [0.0, 0.3, 0.6, 0.9]
    draw(tmp_path / "plain", values)
    plain = [c["Z"] for c in seen]
    seen.clear()
    write_contour_frames(values, float(values.max()), COLORMAP, tmp_path / "some", 12, 7, WIDTH, HEIGHT, indices=[1, 3], beat=beat)
    assert [p.name for p in sorted((tmp_path / "some").glob("*.png"))] == ["frame_000001.png", "frame_000003.png"]
    assert np.allclose(seen[0]["Z"], plain[1] * wave_modifier(7, 12, 4, 0.3))
    assert np.allclose(seen[1]["Z"], plain[3] * wave_modifier(7, 12, 4, 0.9))


# ---- flat frames ----------------------------------------------------------------------------------------------------------------


def test_a_frame_whose_values_are_all_equal_is_one_flat_color_at_every_position_in_the_beat(tmp_path, seen):
    values = np.full((1, 84), 2.0)
    draw(tmp_path / "plain", values)
    for k in (0.0, 0.5, 1.0):
        draw(tmp_path / f"k{k}", values, beat=[k])
        assert files(tmp_path / f"k{k}") == files(tmp_path / "plain")
    assert seen == []  # contourf was never called


def test_a_silent_input_is_the_same_with_and_without_the_wave(tmp_path):
    values = np.zeros((2, 84))
    draw(tmp_path / "plain", values, peak=0.0)
    draw(tmp_path / "wave", values, peak=0.0, beat=[0.5, 1.0])
    assert files(tmp_path / "plain") == files(tmp_path / "wave")


def test_a_frame_that_the_wave_flattens_is_written_flat_without_failing(tmp_path, seen, monkeypatch):
    # a modifier that is exactly 0 everywhere leaves nothing to draw (with real patterns this only happens when every value on the rings of
    # pattern 1 is all that is sounding at the top of the beat); contourf cannot draw equal levels, so the frame must be written flat
    import app.services.contour as contour_module

    monkeypatch.setattr(contour_module, "wave_modifier", lambda rows, columns, waves, k: np.zeros((rows, columns)))
    values = grid_values(1)
    draw(tmp_path, values, beat=[1.0])
    assert seen == []  # contourf was not called
    picture = read(tmp_path / "frame_000000.png").reshape(-1, 3)
    assert len({tuple(p) for p in picture.tolist()}) == 1
    assert tuple(picture[0]) == tuple(lookup_table(COLORMAP)[0])  # the value 0 on the scale from 0 to the frame's top


# ---- checks ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("beat", [[0.5], [0.5, 0.5, 0.5], [1.5, 0.0], [-0.1, 0.0], [np.nan, 0.0], [[0.1, 0.2]], "ab"])
def test_a_bad_beat_is_refused_before_anything_is_written(tmp_path, beat):
    with pytest.raises(ValueError):
        draw(tmp_path / "out", grid_values(2), beat=beat)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("waves", [0, 1, 11, 2.5, True, "4", None])
def test_a_bad_wave_count_is_refused_before_anything_is_written(tmp_path, waves):
    with pytest.raises(ValueError, match=MESSAGE):
        draw(tmp_path / "out", grid_values(1), beat=[0.5], waves=waves)
    assert not (tmp_path / "out").exists()


# ---- write_frames ---------------------------------------------------------------------------------------------------------------


def note_frames(frames=12):
    values = np.zeros((frames, 88))
    rng = np.random.default_rng(5)
    values[:, 12:80] = rng.random((frames, 68)) ** 2
    return values


def test_write_frames_without_a_beat_is_the_plain_contour_and_a_beat_of_zeros_is_the_same(tmp_path):
    values = note_frames()
    write_frames(values, tmp_path / "a", colormap=COLORMAP, image_type="contour")
    write_frames(values, tmp_path / "b", colormap=COLORMAP, image_type="contour", beat=np.zeros(12))
    write_frames(values, tmp_path / "c", colormap=COLORMAP, image_type="contour", beat=np.zeros(12), wave_count=10)
    assert files(tmp_path / "a") == files(tmp_path / "b") == files(tmp_path / "c")


def test_write_frames_with_a_beat_changes_the_frames_that_are_above_the_minimum(tmp_path):
    values = note_frames()
    beat = np.concatenate([[0.0], np.linspace(0.1, 0.9, 11)])  # the minimum of the beat, then places up the beat (not its top: the wave is gone there)
    write_frames(values, tmp_path / "a", colormap=COLORMAP, image_type="contour")
    write_frames(values, tmp_path / "b", colormap=COLORMAP, image_type="contour", beat=beat)
    a, b = files(tmp_path / "a"), files(tmp_path / "b")
    assert a[0] == b[0]
    assert all(x != y for x, y in zip(a[1:], b[1:]))


def test_the_wave_count_changes_the_frames(tmp_path):
    values = note_frames(3)
    beat = np.full(3, 0.5)
    write_frames(values, tmp_path / "a", colormap=COLORMAP, image_type="contour", beat=beat, wave_count=2)
    write_frames(values, tmp_path / "b", colormap=COLORMAP, image_type="contour", beat=beat, wave_count=10)
    assert files(tmp_path / "a") != files(tmp_path / "b")


@pytest.mark.parametrize("image_type", IMAGE_TYPES)
@pytest.mark.parametrize("bad", [0, 1, 11, 2.5, True, "5", None])
def test_a_bad_wave_count_is_refused_for_every_type_before_anything_is_written(tmp_path, image_type, bad):
    with pytest.raises(ValueError, match=MESSAGE):
        write_frames(note_frames(2), tmp_path / "out", colormap=COLORMAP, image_type=image_type, wave_count=bad)
    assert not (tmp_path / "out").exists()


# Energy graphs needs its own data to be drawn (feature 034: ``energy``), which these frames do not have; its own tests show that it ignores every setting
@pytest.mark.parametrize("image_type", [t for t in IMAGE_TYPES if t not in ("contour", "energy-graphs")])
def test_the_wave_count_has_no_effect_on_the_other_types(tmp_path, image_type):
    values = note_frames(5)
    beat = np.linspace(0, 1, 5)
    write_frames(values, tmp_path / "a", colormap=COLORMAP, image_type=image_type, beat=beat, wave_count=2)
    write_frames(values, tmp_path / "b", colormap=COLORMAP, image_type=image_type, beat=beat, wave_count=10)
    assert files(tmp_path / "a") == files(tmp_path / "b")


def test_with_oversampling_the_pattern_is_worked_out_on_the_finer_grid(tmp_path, seen):
    values = note_frames(1)
    write_frames(values, tmp_path / "plain", colormap=COLORMAP, image_type="contour", resolution=3)
    plain = seen[0]["Z"]
    seen.clear()
    write_frames(values, tmp_path / "wave", colormap=COLORMAP, image_type="contour", resolution=3, beat=np.array([0.7]), wave_count=5)
    assert plain.shape == (21, 36)
    assert np.allclose(seen[0]["Z"], plain * wave_modifier(21, 36, 5, 0.7))


def test_notes_hidden_by_the_threshold_are_zero_before_the_wave_and_stay_zero(tmp_path, seen):
    values = np.zeros((1, 88))
    values[0, 30] = 1.0
    values[0, 31] = 0.02  # under a threshold of 5 % of the peak
    values[0, 32] = 0.5
    write_frames(values, tmp_path / "plain", colormap=COLORMAP, image_type="contour", threshold=5)
    plain = seen[0]["Z"]
    seen.clear()
    write_frames(values, tmp_path / "wave", colormap=COLORMAP, image_type="contour", threshold=5, beat=np.array([1.0]))
    wave = seen[0]["Z"]
    assert np.allclose(wave, plain * wave_modifier(7, 12, 4, 1.0))
    assert (wave[plain == 0] == 0).all()


def test_interpolate_and_gaussian_work_on_the_frames_with_the_wave(tmp_path):
    values = note_frames(7)
    beat = np.linspace(0.2, 1, 7)
    write_frames(values, tmp_path / "one", colormap=COLORMAP, image_type="contour", beat=beat)
    write_frames(values, tmp_path / "three", colormap=COLORMAP, image_type="contour", beat=beat, interpolate=3)
    one, three = files(tmp_path / "one"), files(tmp_path / "three")
    assert len(one) == len(three) == 7
    assert one[0] == three[0] and one[3] == three[3] and one[6] == three[6]  # the key frames are drawn exactly as at 1
    write_frames(values, tmp_path / "blur", colormap=COLORMAP, image_type="contour", beat=beat, gaussian=2.0)
    assert len(files(tmp_path / "blur")) == 7 and files(tmp_path / "blur") != one
    assert all(read(p).shape == (HEIGHT, WIDTH, 3) for p in (tmp_path / "blur").glob("*.png"))


def test_the_lookup_table_is_not_changed_and_the_colors_stay_in_the_colormap(tmp_path):
    table = lookup_table(COLORMAP).copy()
    write_frames(note_frames(2), tmp_path, colormap=COLORMAP, image_type="contour", beat=np.full(2, 0.5))
    assert np.array_equal(table, lookup_table(COLORMAP))

def test_the_effect_is_the_same_on_the_way_up_the_beat_and_on_the_way_down_and_gone_at_the_top(tmp_path, seen):
    values = grid_values(1)
    draw(tmp_path / "plain", values)
    plain = seen[0]["Z"]
    seen.clear()
    for k in (0.2, 0.8):
        draw(tmp_path / f"k{k}", values, beat=[k])
    assert np.allclose(seen[0]["Z"], seen[1]["Z"], atol=1e-12, rtol=0)
    seen.clear()
    draw(tmp_path / "top", values, beat=[1.0])
    assert np.allclose(seen[0]["Z"], plain, atol=1e-12, rtol=0)
