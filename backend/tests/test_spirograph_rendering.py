"""Spirograph (feature 046): the drawing of curves, and the pictures that ``write_frames`` makes of a file."""

import numpy as np
import pytest

from app.services import spirograph as sp


def line(x1: float, y1: float, x2: float, y2: float) -> np.ndarray:
    """One curve of two points, in pixels."""
    return np.array([[[x1, y1], [x2, y2]]], dtype=np.float64)


RED = np.array([[255, 0, 0]], dtype=np.uint8)
BLUE = np.array([[0, 0, 255]], dtype=np.uint8)


# --- the drawing of curves (user story 1) ---------------------------------------------------------------------------


def test_a_picture_with_no_curve_is_black():
    picture = sp._frame(np.zeros((0, 1000, 2)), np.zeros((0, 3), dtype=np.uint8), 300, 200)
    assert picture.shape == (200, 300, 3) and picture.dtype == np.uint8
    assert not picture.any()


def test_a_curve_is_drawn_in_its_color_on_black_and_nowhere_else():
    picture = sp._frame(line(100, 100, 200, 110), RED, 300, 200)  # slanted: a straight horizontal line would be snapped to a pixel row
    column = picture[95:115, 150]
    assert int(column[:, 0].max()) > 100 and not column[:, 1:].any()  # red, and only red
    assert not picture[130, 150].any()  # well off the line
    assert not picture[105, 50].any()  # beyond its end
    assert not picture[:, :, 1:].any()  # only red was used anywhere
    assert picture.any()


def test_a_curve_drawn_later_lies_over_an_earlier_one():
    curves = np.concatenate([line(100, 100, 200, 101), line(150, 50, 151, 150)])  # they cross near (150.5, 100.5)
    picture = sp._frame(curves, np.concatenate([RED, BLUE]), 300, 200)
    patch = picture[98:104, 148:154].astype(int)
    both = (patch[..., 0] > 0) & (patch[..., 2] > 0)  # pixels that were drawn on by both curves
    assert both.any()
    assert (patch[both][:, 2] > patch[both][:, 0]).all()  # the blue one was drawn later and is on top
    swapped = sp._frame(curves, np.concatenate([BLUE, RED]), 300, 200)
    patch = swapped[98:104, 148:154].astype(int)
    both = (patch[..., 0] > 0) & (patch[..., 2] > 0)
    assert both.any() and (patch[both][:, 0] > patch[both][:, 2]).all()


def test_the_same_curves_give_the_same_picture():
    rng = np.random.default_rng(3)
    curves = sp.spiro_curves(rng.random(6), rng.integers(0, 84, 6)) * 5 + np.array([150.0, 100.0])
    colors = sp.reduced_colors("inferno")[rng.integers(0, 13, 6)]
    first = sp._frame(curves, colors, 300, 200)
    assert np.array_equal(first, sp._frame(curves, colors, 300, 200))


@pytest.mark.parametrize("width, height", [(0, 200), (300, 0), (300.5, 200), (True, 200), ("300", 200)])
def test_a_bad_size_is_refused(width, height):
    with pytest.raises(ValueError):
        sp._frame(np.zeros((0, 1000, 2)), np.zeros((0, 3), dtype=np.uint8), width, height)


def test_curves_and_colors_must_match():
    with pytest.raises(ValueError):
        sp._frame(line(1, 1, 5, 5), np.zeros((2, 3), dtype=np.uint8), 300, 200)


# --- the pictures of a file (user story 2) --------------------------------------------------------------------------

import time
from pathlib import Path

from PIL import Image

from app.services import frame_rendering as rendering
from app.services.frame_rendering import write_frames

SETTINGS = sp.SpirographSettings(5, 8)


def synthetic(frames: int = 40, seed: int = 46) -> np.ndarray:
    """``(frames, 88)`` strengths: a few notes that come and go."""
    rng = np.random.default_rng(seed)
    notes = rng.random((frames, 88)) ** 4
    notes[rng.random((frames, 88)) < 0.6] = 0.0
    notes[:, 27] += np.sin(np.linspace(0, 6, frames)) ** 2
    return notes


def pictures(directory: Path) -> list[bytes]:
    return [path.read_bytes() for path in sorted(directory.glob("frame_*.png"))]


def non_black(path: Path) -> int:
    return int(np.asarray(Image.open(path).convert("RGB")).any(axis=2).sum())


def test_write_frames_makes_one_600_by_400_picture_for_each_frame(tmp_path):
    write_frames(synthetic(12), tmp_path / "out", image_type="spirograph")
    names = sorted(p.name for p in (tmp_path / "out").iterdir())
    assert names == [f"frame_{i:06d}.png" for i in range(12)]
    image = Image.open(tmp_path / "out" / names[5])
    assert image.format == "PNG" and image.mode == "RGB" and image.size == (600, 400)


def test_a_silent_file_gives_black_pictures(tmp_path):
    write_frames(np.zeros((6, 88)), tmp_path / "out", image_type="spirograph")
    for path in (tmp_path / "out").glob("frame_*.png"):
        assert not np.asarray(Image.open(path)).any()


def test_the_same_file_gives_the_same_pictures_and_so_do_one_worker_and_several(tmp_path, monkeypatch):
    values = synthetic(16)
    write_frames(values, tmp_path / "a", image_type="spirograph")
    write_frames(values, tmp_path / "b", image_type="spirograph")
    assert pictures(tmp_path / "a") == pictures(tmp_path / "b")
    monkeypatch.setattr(sp, "SAVE_WORKERS", 1)
    write_frames(values, tmp_path / "serial", image_type="spirograph")
    assert pictures(tmp_path / "serial") == pictures(tmp_path / "a")


@pytest.mark.parametrize("width, height", [(600, 400), (150, 100), (400, 400), (100, 300)])
def test_no_curve_comes_near_the_edge_of_the_picture_at_any_size(tmp_path, width, height):
    values = synthetic(20)
    values[:, 83] = 3.0  # the highest drawn note, as loud as the file allows: the widest loops
    sp.write_spirograph_frames(values, sp.SpirographSettings(12, 12), "inferno", tmp_path / "out", width, height)
    frames = [np.asarray(Image.open(p)) for p in sorted((tmp_path / "out").glob("frame_*.png"))]
    assert any(f.any() for f in frames)
    edge = sp.MARGIN - 2  # the room is the margin and a line: the outer margin less 2 pixels stays black
    for f in frames:
        assert f.shape == (height, width, 3)
        assert not f[:edge].any() and not f[-edge:].any() and not f[:, :edge].any() and not f[:, -edge:].any()


def test_the_curves_of_a_note_stay_for_as_many_frames_as_the_history_and_then_go(tmp_path):
    values = np.zeros((40, 88))
    values[10:21, 40] = 1.0  # one note, sounding in frames 10 to 20 only
    sp.write_spirograph_frames(values, SETTINGS, "viridis", tmp_path / "out", 300, 200)
    counts = [non_black(tmp_path / "out" / f"frame_{i:06d}.png") for i in range(40)]
    assert all(c == 0 for c in counts[:10])  # nothing sounded yet
    assert all(c > 0 for c in counts[10:28])  # the note, then its entries as long as they are in the window (20 + 7 = 27)
    assert all(c == 0 for c in counts[28:])  # the last entry with the note has left the window


def test_the_widest_possible_line_is_5_pixels_and_a_wider_line_covers_more(tmp_path):
    curves = line(100, 100, 200, 110)
    thin = sp._frame(curves, RED, 300, 200, [1])
    thick = sp._frame(curves, RED, 300, 200, [5])
    assert (thick.any(axis=2).sum()) > 3 * (thin.any(axis=2).sum())
    assert np.array_equal(thin, sp._frame(curves, RED, 300, 200))  # no widths: one pixel


@pytest.mark.parametrize("widths", [[1, 2], [0], [-1], [float("nan")], [[1]]])
def test_the_widths_must_be_one_number_above_0_for_each_curve(widths):
    with pytest.raises(ValueError):
        sp._frame(line(1, 1, 5, 5), RED, 300, 200, widths)


def test_the_smallest_curves_are_still_half_of_the_smallest_side_across(tmp_path):
    values = np.zeros((12, 88))
    values[0, 40] = 1.0  # the loud note of the file (frame 0) sets the scale
    values[6:, 41] = 1e-4  # a very quiet note in frames 6 to 11 (value 0.01): a window of 5 has only these
    sp.write_spirograph_frames(values, sp.SpirographSettings(5, 5, 0.85), "viridis", tmp_path / "out", 600, 400)
    picture = np.asarray(Image.open(tmp_path / "out" / "frame_000011.png")).any(axis=2)
    columns = np.flatnonzero(picture.any(axis=0))
    across = columns[-1] - columns[0] + 1
    assert 190 <= across <= 215  # a quarter of the smallest side (100) each way from the center: 200 across, plus the line
    loud = np.asarray(Image.open(tmp_path / "out" / "frame_000000.png")).any(axis=2)
    columns = np.flatnonzero(loud.any(axis=0))
    assert columns[-1] - columns[0] + 1 >= 365  # the loudest curve of the file takes the room: 187 each way (200, less the margin of 10 and the widest line of 3)


def test_the_older_entries_fade_so_the_newest_is_the_most_prominent(tmp_path):
    values = np.zeros((40, 88))
    values[10:13, 40] = 1.0  # a note in frames 10 to 12 only; the window of frame t holds the entries t - 7 to t
    sizes = {}
    for fade in (0.4, 0.85):
        sp.write_spirograph_frames(values, sp.SpirographSettings(5, 8, fade), "viridis", tmp_path / str(fade), 300, 200)
        sizes[fade] = [non_black(tmp_path / str(fade) / f"frame_{i:06d}.png") for i in range(40)]
    for fade, counts in sizes.items():
        # the picture of frame 12 has the newest entry whole (and two older ones), a later picture has only older entries
        assert counts[12] > counts[13] > counts[14] > 0, fade
    assert sizes[0.4][12] < sizes[0.85][12] and sizes[0.4][14] < sizes[0.85][14]  # a lower fade leaves less of the older entries
    assert sizes[0.4][10] == sizes[0.85][10]  # the first entry is the newest and is the same at any fade


def test_a_steady_loud_note_looks_the_same_at_every_fade_only_in_its_newest_curve(tmp_path):
    values = np.zeros((3, 88))
    values[:, 40] = 1.0
    sp.write_spirograph_frames(values, sp.SpirographSettings(5, 5, 0.4), "viridis", tmp_path / "a", 300, 200)
    sp.write_spirograph_frames(values, sp.SpirographSettings(5, 5, 0.85), "viridis", tmp_path / "b", 300, 200)
    assert pictures(tmp_path / "a")[0] == pictures(tmp_path / "b")[0]  # frame 0 has nothing but its own, whole, entry
    assert pictures(tmp_path / "a")[2] != pictures(tmp_path / "b")[2]


def test_the_picture_changes_when_the_loudest_note_changes(tmp_path):
    values = np.zeros((20, 88))
    values[:10, 20] = 1.0
    values[10:, 60] = 1.0
    sp.write_spirograph_frames(values, SETTINGS, "viridis", tmp_path / "out", 300, 200)
    out = pictures(tmp_path / "out")
    assert out[9] != out[10] and out[10] != out[11]
    assert out[8] == out[9]  # a steady note gives the same curve in every entry: once the window is full (8 entries) the picture does not change


def test_a_louder_note_has_a_later_color_and_a_bigger_curve(tmp_path):
    quiet = np.zeros((1, 88))
    quiet[0, 40] = 0.3
    loud = quiet.copy()
    loud[0, 41] = 1.0  # sets the scale of the file, in both files
    quiet[0, 41] = 1.0
    # one file with both notes: the quiet one (strength 0.3, value sqrt(0.3), color number 6) and the loud one (1.0, color number 12)
    sp.write_spirograph_frames(quiet, SETTINGS, "viridis", tmp_path / "out", 600, 400)
    picture = np.asarray(Image.open(tmp_path / "out" / "frame_000000.png")).reshape(-1, 3)
    colors = sp.reduced_colors("viridis")
    seen = {tuple(c) for c in picture[picture.any(axis=1)]}
    assert tuple(colors[12]) in seen  # the full-color pixels of the loud note
    assert tuple(colors[6]) in seen  # and of the quiet one (the square root pulls it from number 3 up to 6)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"settings": sp.SpirographSettings(4, 8)},
        {"settings": sp.SpirographSettings(8, 13)},
        {"settings": sp.SpirographSettings(8, 8, 0.3)},
        {"settings": sp.SpirographSettings(8, 8, 0.9)},
        {"colormap": "not-a-colormap"},
        {"extra_notes": 6},
        {"values": np.zeros((3, 80))},
        {"values": np.full((3, 88), -1.0)},
        {"width": 20, "height": 20},
        {"width": 0},
    ],
)
def test_a_refusal_raises_and_creates_nothing(tmp_path, kwargs):
    arguments = {"values": synthetic(4), "settings": SETTINGS, "colormap": "viridis", "width": 300, "height": 200, "extra_notes": 0}
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        sp.write_spirograph_frames(
            arguments["values"], arguments["settings"], arguments["colormap"], tmp_path / "out", arguments["width"], arguments["height"], arguments["extra_notes"]
        )
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("extra", [0, 1, 5])
def test_extra_notes_from_0_to_the_number_of_notes_is_accepted(tmp_path, extra):
    sp.write_spirograph_frames(synthetic(6), SETTINGS, "viridis", tmp_path / f"out{extra}", 300, 200, extra)
    assert len(list((tmp_path / f"out{extra}").glob("frame_*.png"))) == 6


def test_write_frames_checks_the_spirograph_settings_for_every_image_type_and_the_other_types_do_not_use_them(tmp_path):
    values = synthetic(3)
    with pytest.raises(ValueError, match="number of spirograph notes"):
        write_frames(values, tmp_path / "bad", image_type="contour", spirograph_settings=sp.SpirographSettings(4, 8))
    assert not (tmp_path / "bad").exists()
    write_frames(values, tmp_path / "plain", image_type="contour")
    write_frames(values, tmp_path / "with", image_type="contour", spirograph_settings=sp.SpirographSettings(12, 12))
    assert pictures(tmp_path / "plain") == pictures(tmp_path / "with")


def test_spirograph_needs_no_beat_and_ignores_the_other_settings(tmp_path):
    values = synthetic(8)
    write_frames(values, tmp_path / "plain", image_type="spirograph")
    write_frames(values, tmp_path / "other", image_type="spirograph", threshold=5, resolution=3, note_count=24, interpolate=3, gaussian=2.0, decay_rate=3)
    assert pictures(tmp_path / "plain") == pictures(tmp_path / "other")


def test_the_beat_turns_and_sizes_the_curves_and_without_one_every_frame_is_at_the_top_of_a_peak(tmp_path):
    values = synthetic(8)
    write_frames(values, tmp_path / "plain", image_type="spirograph")
    write_frames(values, tmp_path / "top", image_type="spirograph", beat=np.ones(8))  # one position, so one place in the peak: the top
    write_frames(values, tmp_path / "wave", image_type="spirograph", beat=np.array([0, 0.6, 1.0, 0.7, 0.55, 0.9, 0.0, 0.8]))
    assert pictures(tmp_path / "plain") == pictures(tmp_path / "top")
    assert pictures(tmp_path / "wave") != pictures(tmp_path / "plain")


def test_the_same_note_in_a_frame_at_the_top_of_the_beat_and_one_at_the_bottom_is_drawn_differently(tmp_path):
    values = np.zeros((2, 88))
    values[:, 40] = 1.0  # the same note in both frames: only the beat differs (the first frame has only its own entry)
    sp.write_spirograph_frames(values, sp.SpirographSettings(5, 5), "viridis", tmp_path / "out", 300, 200, 0, np.array([1.0, 0.55]))
    top, bottom = (np.asarray(Image.open(tmp_path / "out" / f"frame_{i:06d}.png")) for i in (0, 1))
    assert top.any() and bottom.any()  # both are drawn (the second also holds the first's entry)
    assert not np.array_equal(top, bottom)


def test_a_beat_that_is_not_one_number_from_0_to_1_for_each_frame_is_refused_and_creates_nothing(tmp_path):
    for beat in (np.zeros(3), np.full(4, 2.0), np.zeros((4, 1))):
        with pytest.raises(ValueError):
            sp.write_spirograph_frames(synthetic(4), SETTINGS, "viridis", tmp_path / "out", 300, 200, 0, beat)
        assert not (tmp_path / "out").exists()


def test_the_largest_settings_take_under_2_seconds_a_picture(tmp_path):
    values = synthetic(30)
    started = time.perf_counter()
    sp.write_spirograph_frames(values, sp.SpirographSettings(12, 12), "inferno", tmp_path / "out", 600, 400)
    assert (time.perf_counter() - started) / 30 < 2.0


def test_300_frames_at_the_defaults_finish(tmp_path):
    values = synthetic(300)
    write_frames(values, tmp_path / "out", image_type="spirograph")
    assert len(list((tmp_path / "out").glob("frame_*.png"))) == 300
    assert rendering.IMAGE_WIDTH == 600
