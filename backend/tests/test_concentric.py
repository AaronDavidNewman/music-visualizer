"""The Concentric image type (feature 025): 84 circles of up to 12 flat rings, sized by the note's volume, colored by the beat.

How a frame is worked out is in ``app/services/concentric.py``; here the steps, the ring colors, the geometry and the pixels are
checked on their own, and against a brute-force drawing of the rings on a 4 x 4 supersampled canvas written in this file.
"""

import math

import numpy as np
import pytest
from PIL import Image

import app.services.frame_rendering as rendering
from app.services.circles import MIDDLE_COLOR_ROW
from app.services.colormaps import COLORMAPS, lookup_table
from app.services.concentric import RINGS, ring_colors, ring_steps
from app.services.concentric import write_concentric_frames as _write_concentric_frames

from .colormap_names import DECODABLE
from .frame_size import COLUMN_EDGES, HEIGHT, ROW_EDGES, WIDTH

NOTES = 84
RADIUS = min(np.diff(COLUMN_EDGES).min(), np.diff(ROW_EDGES).min()) / 2  # 25 pixels
RING = RADIUS / RINGS
ALL_COLORMAPS = COLORMAPS


def write_concentric_frames(values, colormap, directory, beat=None):
    _write_concentric_frames(values, colormap, directory, beat, WIDTH, HEIGHT)


def centre(note):
    """The exact center of the tile of ``note`` in pixel coordinates ``(x, y)``."""
    row, column = divmod(note, 12)
    return (COLUMN_EDGES[column] + COLUMN_EDGES[column + 1]) / 2, (ROW_EDGES[row] + ROW_EDGES[row + 1]) / 2


def cell_box(note):
    row, column = divmod(note, 12)
    return ROW_EDGES[row], ROW_EDGES[row + 1], COLUMN_EDGES[column], COLUMN_EDGES[column + 1]


def one_note(note, value=1.0, others=0.0, frames=1):
    values = np.full((frames, NOTES), others, dtype=float)
    values[:, note] = value
    return values


def render(tmp_path, values, colormap, beat=None, label="frames"):
    directory = tmp_path / label
    write_concentric_frames(values, colormap, directory, beat)
    return [np.asarray(Image.open(f).convert("RGB")).astype(int) for f in sorted(directory.glob("frame_*.png"))]


def rows_of(colormap, beat_value):
    """The table rows of the 12 rings at a position, worked out here from the clarified rule."""
    return [int(np.rint((k - 1) / 11 * (0.5 + 0.5 * beat_value) * 255)) for k in range(1, 13)]


def brute_force(steps, colours, background):
    """The picture drawn the obvious slow way: every circle's rings on a 4 x 4 supersampled canvas, then averaged down."""
    scale = 4
    sub = np.empty((HEIGHT * scale, WIDTH * scale, 3), dtype=float)
    sub[:] = background
    ys = (np.arange(HEIGHT * scale) + 0.5) / scale
    xs = (np.arange(WIDTH * scale) + 0.5) / scale
    for note in range(NOTES):
        cx, cy = centre(note)
        y0, y1, x0, x1 = cell_box(note)
        dist = np.hypot(xs[x0 * scale : x1 * scale][None, :] - cx, ys[y0 * scale : y1 * scale][:, None] - cy)
        ring = np.maximum(np.ceil(dist / RING).astype(int), 1)
        inside = ring <= steps[note]
        block = sub[y0 * scale : y1 * scale, x0 * scale : x1 * scale]
        block[inside] = np.asarray(colours, dtype=float)[ring[inside] - 1]
    return np.rint(sub.reshape(HEIGHT, scale, WIDTH, scale, 3).mean(axis=(1, 3))).astype(int)


def flat_pixel(note, ring):
    """A pixel that lies wholly inside ring ``ring`` (1 to 12) of the circle of ``note`` (its whole square, corners included)."""
    cx, cy = centre(note)
    y0, y1, x0, x1 = cell_box(note)
    for y in range(y0, y1):
        for x in range(x0, x1):
            corners = [math.hypot(px - cx, py - cy) for px in (x, x + 1) for py in (y, y + 1)]
            near = 0.0 if x < cx < x + 1 and y < cy < y + 1 else min(corners)
            far = max(corners)
            if (ring - 1) * RING + 0.02 <= near and far <= ring * RING - 0.02 or ring == 1 and far <= RING - 0.02:
                return y, x
    raise AssertionError(f"no pixel lies wholly inside ring {ring}")


# ---------------------------------------------------------------------------------------------------------------------
# the steps
# ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("k", range(1, 13))
def test_a_share_of_k_squared_over_144_of_the_loudest_is_step_k(k):
    values = np.zeros((1, NOTES))
    values[0, 0] = 144.0
    values[0, 1] = float(k * k)
    assert ring_steps(values)[0, 1] == k
    values[0, 1] = k * k * 1.001
    assert ring_steps(values)[0, 1] == min(k + 1, 12)


def test_rounding_noise_never_moves_an_exact_share_to_the_next_step():
    rng = np.random.default_rng(11)
    known = [114.94148395457239, 126.82583409022516, 958.4097510860402]  # 12 * sqrt(share) is 9.000000000000002 for k = 9
    for loudest in [*known, *rng.uniform(0.01, 1000.0, 400)]:
        values = np.zeros((1, NOTES))
        values[0, 0] = loudest
        for k in range(1, 13):
            values[0, k] = loudest * (k * k / 144.0)  # the share is k * k / 144 up to the last bit
        assert ring_steps(values)[0, 1:13].tolist() == list(range(1, 13)), loudest


def test_the_loudest_note_of_a_frame_is_step_12_and_a_note_with_no_energy_is_step_1():
    rng = np.random.default_rng(1)
    values = rng.random((20, NOTES)) ** 2
    values[:, 5] = 0.0
    steps = ring_steps(values)
    assert steps.shape == (20, NOTES) and steps.dtype.kind in "iu"
    assert (steps[np.arange(20), values.argmax(axis=1)] == 12).all()
    assert (steps[:, 5] == 1).all()
    assert steps.min() >= 1 and steps.max() == 12


def test_a_silent_frame_is_all_step_1_and_a_frame_of_equal_notes_is_all_step_12():
    steps = ring_steps(np.vstack([np.zeros(NOTES), np.full(NOTES, 0.3)]))
    assert (steps[0] == 1).all() and (steps[1] == 12).all()


def test_a_louder_note_never_has_a_smaller_step_and_each_frame_uses_its_own_loudest():
    rng = np.random.default_rng(2)
    values = rng.random((10, NOTES)) ** 3
    steps = ring_steps(values)
    for frame in range(10):
        order = np.argsort(values[frame])
        assert (np.diff(steps[frame][order]) >= 0).all()
    assert (ring_steps(values * 7.0) == steps).all()  # only the share counts, not the volume
    quiet, loud = values[0] * 0.01, values[0]
    assert (ring_steps(np.vstack([quiet, loud])) == np.vstack([steps[0], steps[0]])).all()  # a quiet frame is as big as a loud one


def test_the_steps_use_the_84_drawn_notes_only_and_do_not_change_the_input():
    values = np.random.default_rng(3).random((4, 88))
    values[:, 86] = 100.0  # a loud undrawn note: it must not shrink the circles
    before = values.copy()
    steps = ring_steps(values)
    assert steps.shape == (4, NOTES)
    assert (steps.max(axis=1) == 12).all()
    assert (values == before).all()


@pytest.mark.parametrize("bad", [np.zeros(84), np.zeros((2, 83)), np.full((2, 84), -1.0), np.full((2, 84), np.nan)])
def test_values_that_are_not_note_values_are_refused(bad):
    with pytest.raises(ValueError):
        ring_steps(bad)


# ---------------------------------------------------------------------------------------------------------------------
# the colors of the rings
# ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("colormap", ALL_COLORMAPS)
@pytest.mark.parametrize("position", [0.0, 0.25, 0.5, 1.0])
def test_ring_k_is_the_colour_at_k_minus_1_over_11_of_the_stretched_colormap(colormap, position):
    got = ring_colors(colormap, np.array([position]))
    assert got.shape == (1, 12, 3) and got.dtype == np.uint8
    table = lookup_table(colormap)
    assert (got[0] == table[rows_of(colormap, position)]).all()


@pytest.mark.parametrize("colormap", ALL_COLORMAPS)
def test_at_the_top_of_the_peak_the_rings_run_through_the_whole_colormap_and_at_the_bottom_half_way(colormap):
    table = lookup_table(colormap)
    top, bottom = ring_colors(colormap, np.array([1.0, 0.0]))
    assert (top[0] == table[0]).all() and (top[11] == table[255]).all()
    assert (bottom[0] == table[0]).all() and (bottom[11] == table[128]).all()  # rint(127.5): the middle of the colormap
    assert rows_of(colormap, 0.0)[-1] == MIDDLE_COLOR_ROW  # the same row as the background


def test_the_rows_of_the_rings_rise_with_the_ring_and_with_the_position_and_every_frame_has_its_own():
    positions = np.linspace(0, 1, 21)
    got = ring_colors(DECODABLE[0], positions)
    table = {tuple(c): i for i, c in enumerate(lookup_table(DECODABLE[0]).tolist())}
    rows = np.array([[table[tuple(c)] for c in frame] for frame in got.tolist()])
    assert (np.diff(rows, axis=1) > 0).all()  # ring k + 1 is later than ring k
    assert (np.diff(rows, axis=0) >= 0).all()  # a higher position is never earlier
    assert rows[0, 0] == 0 and rows[-1, -1] == 255 and rows[0, -1] == 128
    assert got.shape == (21, 12, 3)


@pytest.mark.parametrize("bad", [np.zeros((3, 1)), np.array([0.0, 1.5]), np.array([-0.1]), np.array([np.nan]), np.array(["a"]), 0.5, "abc"])
def test_a_position_that_is_not_one_number_from_0_to_1_per_frame_is_refused(bad):
    with pytest.raises(ValueError):
        ring_colors(COLORMAPS[0], bad)


# ---------------------------------------------------------------------------------------------------------------------
# the pixels
# ---------------------------------------------------------------------------------------------------------------------


def test_the_full_radius_is_25_pixels_and_neighbours_in_a_row_touch():
    assert RADIUS == 25.0
    assert (np.diff(COLUMN_EDGES) == 50).all()
    assert set(np.diff(ROW_EDGES).tolist()) <= {57, 58}
    assert (centre(1)[0] - centre(0)[0]) == 2 * RADIUS


@pytest.mark.parametrize("colormap", ALL_COLORMAPS)
def test_the_background_between_the_circles_is_the_middle_colour_of_the_colormap(tmp_path, colormap):
    table = lookup_table(colormap)
    picture = render(tmp_path, np.zeros((1, NOTES)), colormap)[0]
    assert tuple(picture[0, 0]) == tuple(table[MIDDLE_COLOR_ROW])
    assert tuple(picture[HEIGHT - 1, WIDTH - 1]) == tuple(table[MIDDLE_COLOR_ROW])
    gap = ROW_EDGES[1]  # the top of the second row: the full circle of the first row ends about 7 pixels short of it
    full = render(tmp_path, one_note(0), colormap, label="full")[0]
    assert tuple(full[ROW_EDGES[1] - 1, 25]) == tuple(table[MIDDLE_COLOR_ROW])
    assert gap > 0


@pytest.mark.parametrize("colormap", ALL_COLORMAPS)
@pytest.mark.parametrize("position", [0.0, 0.5, 1.0])
def test_every_ring_of_the_loudest_circle_is_flat_in_its_colour(tmp_path, colormap, position):
    table = lookup_table(colormap)
    rows = rows_of(colormap, position)
    for note in (0, 30, 83):
        picture = render(tmp_path, one_note(note), colormap, np.array([position]), label=f"n{note}")[0]
        for ring in range(1, 13):
            y, x = flat_pixel(note, ring)
            assert tuple(picture[y, x]) == tuple(table[rows[ring - 1]]), (colormap, note, ring)


@pytest.mark.parametrize("step", range(1, 13))
def test_a_smaller_circle_is_a_full_one_with_the_outer_rings_left_off(tmp_path, step):
    colormap = COLORMAPS[0]
    table = lookup_table(colormap)
    rows = rows_of(colormap, 0.7)
    values = one_note(40, value=(step * step) / 144.0, others=0.0)
    values[0, 41] = 1.0  # another note is the loudest, so note 40 gets this step
    picture = render(tmp_path, values, colormap, np.array([0.7]))[0]
    background = tuple(table[MIDDLE_COLOR_ROW])
    for ring in range(1, 13):
        y, x = flat_pixel(40, ring)
        want = tuple(table[rows[ring - 1]]) if ring <= step else background
        assert tuple(picture[y, x]) == want, (step, ring)


def test_the_radius_of_a_circle_is_its_step_over_12_of_the_full_radius(tmp_path):
    colormap = DECODABLE[0]
    table = lookup_table(colormap)
    background = tuple(table[MIDDLE_COLOR_ROW])
    for step in (1, 3, 6, 12):
        values = np.zeros((1, NOTES))
        values[0, 20] = 1.0 * 144 / 144  # the loudest: step 12
        values[0, 21] = step * step / 144.0
        picture = render(tmp_path, values, colormap, np.array([1.0]), label=f"s{step}")[0]
        y0, y1, x0, x1 = cell_box(21)
        painted = np.array([[tuple(picture[y, x]) != background for x in range(x0, x1)] for y in range(y0, y1)])
        columns = painted.any(axis=0).sum()
        assert abs(columns - 2 * step * RADIUS / 12) <= 1.5, (step, columns)
        cx, cy = centre(21)
        ys, xs = np.nonzero(painted)
        assert abs(xs.mean() + x0 + 0.5 - cx) < 0.6 and abs(ys.mean() + y0 + 0.5 - cy) < 0.6  # centered on its tile


def test_no_circle_leaves_its_cell_and_the_full_circles_of_a_row_touch(tmp_path):
    colormap = DECODABLE[0]
    background = tuple(lookup_table(colormap)[MIDDLE_COLOR_ROW])
    full = render(tmp_path, np.full((1, NOTES), 0.5), colormap, np.array([1.0]))[0]
    silent = render(tmp_path, np.zeros((1, NOTES)), colormap, np.array([1.0]), label="silent")[0]  # every circle is a dot (step 1)
    for note in range(NOTES):
        y0, y1, x0, x1 = cell_box(note)
        single = render(tmp_path, one_note(note), colormap, np.array([1.0]), label=f"c{note}")[0]
        mask = (single != silent).any(axis=2)  # what the loudest note adds to the dots
        assert mask[y0:y1, x0:x1].any(), note
        outside = mask.copy()
        outside[y0:y1, x0:x1] = False
        assert not outside.any(), note
    row = full[28]  # across the middle of the first row: twelve full circles in contact
    painted = (row != np.array(background)).any(axis=1)
    assert painted[25] and painted[75] and painted[575]
    assert painted[2:598].all()  # touching: only the very first and last pixels, where a circle meets the edge, can be background


def test_a_ring_edge_is_smooth_and_a_pixel_of_the_edge_is_a_mix_of_the_two_colours(tmp_path):
    colormap = DECODABLE[0]
    picture = render(tmp_path, one_note(0), colormap, np.array([1.0]))[0]
    table = {tuple(c) for c in lookup_table(colormap).tolist()}
    y0, y1, x0, x1 = cell_box(0)
    colours = {tuple(int(v) for v in picture[y, x]) for y in range(y0, y1) for x in range(x0, x1)}
    assert len(colours - table) > 20  # many mixed colours on the edges of the rings
    assert len(colours & table) >= 12  # and the flat ones


@pytest.mark.parametrize("seed", range(4))
def test_a_frame_is_exactly_the_rings_drawn_on_a_4_by_4_supersampled_canvas(tmp_path, seed):
    rng = np.random.default_rng(seed)
    colormap = COLORMAPS[seed % len(COLORMAPS)]
    values = rng.random((1, NOTES)) ** 2
    position = float(rng.random())
    picture = render(tmp_path, values, colormap, np.array([position]))[0]
    table = lookup_table(colormap)
    steps = ring_steps(values)[0]
    want = brute_force(steps, table[rows_of(colormap, position)], table[MIDDLE_COLOR_ROW])
    assert (picture == want).all()


# ---------------------------------------------------------------------------------------------------------------------
# the frames
# ---------------------------------------------------------------------------------------------------------------------


def test_the_frames_are_numbered_rgb_pictures_of_the_frame_size_and_two_runs_are_identical(tmp_path):
    values = np.random.default_rng(5).random((5, NOTES))
    beat = np.linspace(0, 1, 5)
    write_concentric_frames(values, COLORMAPS[0], tmp_path / "a", beat)
    write_concentric_frames(values, COLORMAPS[0], tmp_path / "b", beat)
    names = sorted(p.name for p in (tmp_path / "a").iterdir())
    assert names == [f"frame_{i:06d}.png" for i in range(5)]
    for name in names:
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
        image = Image.open(tmp_path / "a" / name)
        assert image.mode == "RGB" and image.size == (WIDTH, HEIGHT)


def test_a_frame_with_a_higher_position_has_later_colours_and_no_beat_is_position_zero(tmp_path):
    values = np.random.default_rng(6).random((1, NOTES))
    low = render(tmp_path, values, COLORMAPS[0], np.array([0.0]), label="low")[0]
    high = render(tmp_path, values, COLORMAPS[0], np.array([1.0]), label="high")[0]
    none = render(tmp_path, values, COLORMAPS[0], None, label="none")[0]
    assert not np.array_equal(low, high)
    assert np.array_equal(low, none)


def test_at_the_top_of_the_peak_the_last_colour_is_in_the_picture_and_at_the_bottom_nothing_is_past_the_middle(tmp_path):
    colormap = DECODABLE[0]
    table = lookup_table(colormap)
    rows = {tuple(c): i for i, c in enumerate(table.tolist())}
    values = np.random.default_rng(7).random((1, NOTES))
    values[0, 0] = 5.0
    high = render(tmp_path, values, colormap, np.array([1.0]), label="high")[0]
    low = render(tmp_path, values, colormap, np.array([0.0]), label="low")[0]
    high_rows = {rows[tuple(int(v) for v in c)] for c in np.unique(high.reshape(-1, 3), axis=0) if tuple(int(v) for v in c) in rows}
    low_rows = {rows[tuple(int(v) for v in c)] for c in np.unique(low.reshape(-1, 3), axis=0) if tuple(int(v) for v in c) in rows}
    assert 255 in high_rows and 0 in high_rows
    assert max(low_rows) <= 128 and 128 in low_rows  # the background


@pytest.mark.parametrize(
    "bad",
    [np.zeros((2, 83)), np.zeros(84), np.full((2, 84), -1.0), np.full((2, 84), np.nan), np.zeros((2, 84, 1))],
)
def test_bad_note_values_are_refused_before_anything_is_written(tmp_path, bad):
    with pytest.raises(ValueError):
        write_concentric_frames(bad, COLORMAPS[0], tmp_path / "out", None)
    assert not (tmp_path / "out").exists() or not list((tmp_path / "out").iterdir())


def test_a_bad_colormap_or_beat_is_refused_before_anything_is_written(tmp_path):
    for beat in (np.zeros(3), np.array([0.0, 2.0])):
        with pytest.raises(ValueError):
            write_concentric_frames(np.zeros((2, NOTES)), COLORMAPS[0], tmp_path / "x", beat)
    with pytest.raises(ValueError, match="The colormap must be one of"):
        write_concentric_frames(np.zeros((2, NOTES)), "nonsense", tmp_path / "x", None)
    assert not (tmp_path / "x").exists() or not list((tmp_path / "x").iterdir())


def test_no_frames_make_no_files(tmp_path):
    write_concentric_frames(np.zeros((0, NOTES)), COLORMAPS[0], tmp_path / "none", np.zeros(0))
    assert not list((tmp_path / "none").glob("frame_*.png"))


# ---------------------------------------------------------------------------------------------------------------------
# through write_frames
# ---------------------------------------------------------------------------------------------------------------------


def music(frames=4, seed=8):
    values = np.random.default_rng(seed).random((frames, 88)) ** 2
    values[:, 84:] = 0.0
    return values


def written(tmp_path, label, values, **options):
    directory = tmp_path / label
    rendering.write_frames(values, directory, colormap=COLORMAPS[0], image_type="concentric", **options)
    return [f.read_bytes() for f in sorted(directory.glob("frame_*.png"))]


def test_write_frames_draws_concentric_for_the_smoothed_values_and_the_beat(tmp_path):
    values = music()
    beat = np.array([0.0, 0.3, 0.6, 1.0])
    got = written(tmp_path, "w", values, beat=beat, smoothing=0.4, smoothing_window=2)
    smoothed = rendering.smooth_frames(values, 0.4, 2)
    write_concentric_frames(smoothed[:, :NOTES], COLORMAPS[0], tmp_path / "direct", beat)
    want = [f.read_bytes() for f in sorted((tmp_path / "direct").glob("frame_*.png"))]
    assert got == want and len(got) == 4


def test_the_settings_of_the_grid_and_of_the_other_pictures_do_not_change_a_concentric_frame(tmp_path):
    values = music()
    plain = written(tmp_path, "plain", values)
    for label, options in {
        "threshold": {"threshold": 10},
        "notes": {"note_count": 12},
        "resolution": {"resolution": 5},
        "interpolate": {"interpolate": 5},
        "gaussian": {"gaussian": 5},
        "blend": {"blend_width": 10},
        "circles": {"circle_unit": 10, "circle_memory": 500, "circle_notes": 12, "circle_radius": 8, "circle_resize": True},
    }.items():
        assert written(tmp_path, label, values, **options) == plain, label


def test_the_settings_are_still_checked_for_concentric(tmp_path):
    for options in ({"threshold": 11}, {"resolution": 9}, {"gaussian": 9}, {"interpolate": 0}, {"note_count": 3}):
        with pytest.raises(ValueError):
            written(tmp_path, "bad", music(), **options)
    with pytest.raises(ValueError, match="The beat must be one number from 0 to 1 for each of the 4 frames."):
        written(tmp_path, "bad", music(), beat=np.zeros(3))
    assert not (tmp_path / "bad").exists() or not list((tmp_path / "bad").iterdir())


def test_the_other_image_types_are_the_same_with_the_concentric_code_present(tmp_path):
    for image_type in ("tiles", "blended", "contour", "circles", "circles_paint"):
        rendering.write_frames(music(2), tmp_path / image_type, colormap=COLORMAPS[0], image_type=image_type)
        assert len(list((tmp_path / image_type).glob("frame_*.png"))) == 2


# ---------------------------------------------------------------------------------------------------------------------
# the corners (Story 3)
# ---------------------------------------------------------------------------------------------------------------------


def test_one_sounding_note_is_step_12_and_every_other_circle_a_dot():
    steps = ring_steps(one_note(37, value=0.001))
    assert steps[0, 37] == 12
    assert (np.delete(steps[0], 37) == 1).all()


def test_a_silent_file_is_eighty_four_dots_of_the_first_colour_on_the_background(tmp_path):
    colormap = DECODABLE[0]
    table = lookup_table(colormap)
    picture = render(tmp_path, np.zeros((3, NOTES)), colormap, np.zeros(3))[1]
    want = brute_force(np.ones(NOTES, dtype=int), table[rows_of(colormap, 0.0)], table[MIDDLE_COLOR_ROW])
    assert (picture == want).all()
    for note in (0, 41, 83):
        y, x = flat_pixel(note, 1)
        assert tuple(picture[y, x]) == tuple(table[0])


def test_the_steps_of_a_silent_frame_between_two_loud_ones_follow_the_smoothed_values(tmp_path):
    values = np.zeros((3, 88))
    values[0, :84] = np.linspace(0.2, 1.0, 84)
    values[2, :84] = np.linspace(1.0, 0.2, 84)
    rendering.write_frames(values, tmp_path / "smooth", colormap=COLORMAPS[0], image_type="concentric", smoothing=0.5, smoothing_window=2)
    got = np.asarray(Image.open(tmp_path / "smooth" / "frame_000001.png").convert("RGB")).astype(int)
    smoothed = rendering.smooth_frames(values, 0.5, 2)
    steps = ring_steps(smoothed)[1]
    assert steps.max() == 12 and steps.min() < 12  # the middle frame is not silent after smoothing
    table = lookup_table(COLORMAPS[0])
    want = brute_force(steps, table[rows_of(COLORMAPS[0], 0.0)], table[MIDDLE_COLOR_ROW])
    assert (got == want).all()


def test_the_last_frame_and_a_file_of_one_frame_are_drawn(tmp_path):
    values = np.random.default_rng(9).random((1, NOTES))
    assert len(render(tmp_path, values, COLORMAPS[0], np.array([1.0]))) == 1
    many = np.random.default_rng(10).random((7, NOTES))
    pictures = render(tmp_path, many, COLORMAPS[0], np.linspace(0, 1, 7), label="seven")
    assert len(pictures) == 7 and not np.array_equal(pictures[0], pictures[-1])
