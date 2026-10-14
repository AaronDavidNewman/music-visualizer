"""The resolution setting and the interpolation of the note grid: ``app/services/resolution.py``."""

import numpy as np
import pytest

from app.services.resolution import (
    DEFAULT_RESOLUTION,
    MAX_RESOLUTION,
    MIN_RESOLUTION,
    check_resolution,
    interpolate_grid,
)

COLUMNS, ROWS = 12, 7
MESSAGE = "The oversampling must be a whole number from 1 to 5."
RESOLUTIONS = [1, 2, 3, 4, 5]


def random_frames(frames=6, seed=1):
    return np.random.default_rng(seed).random((frames, COLUMNS * ROWS)) ** 2


def with_np_interp(values, r):
    """The defining computation, written independently: np.interp over every row, then over every new column."""
    out = []
    xs = np.linspace(0, COLUMNS - 1, COLUMNS * r)
    ys = np.linspace(0, ROWS - 1, ROWS * r)
    for frame in values:
        grid = frame.reshape(ROWS, COLUMNS)
        across = np.array([np.interp(xs, np.arange(COLUMNS), row) for row in grid])  # (ROWS, COLUMNS * r)
        down = np.array([np.interp(ys, np.arange(ROWS), across[:, c]) for c in range(COLUMNS * r)])  # (COLUMNS * r, ROWS * r)
        out.append(down.T.reshape(-1))
    return np.array(out)


def test_constants():
    assert (MIN_RESOLUTION, MAX_RESOLUTION, DEFAULT_RESOLUTION) == (1, 5, 1)


@pytest.mark.parametrize("value", [1, 2, 3, 4, 5, np.int64(3), 3.0, np.float64(5.0)])
def test_resolutions_from_one_to_five_are_accepted(value):
    assert check_resolution(value) == int(value)
    assert isinstance(check_resolution(value), int)


@pytest.mark.parametrize("bad", [0, 6, -1, 100, 2.5, 0.5, True, False, None, "3", "", float("nan"), float("inf"), -float("inf"), b"3"])
def test_other_resolutions_are_refused_with_the_message(bad):
    with pytest.raises(ValueError) as error:
        check_resolution(bad)
    assert str(error.value) == MESSAGE


@pytest.mark.parametrize("r", RESOLUTIONS)
def test_the_new_grid_has_twelve_r_columns_and_seven_r_rows(r):
    values = random_frames()
    got = interpolate_grid(values, COLUMNS, ROWS, r)
    assert got.shape == (values.shape[0], (COLUMNS * r) * (ROWS * r))
    assert got.dtype == np.float64


def test_resolution_one_is_exactly_the_input_and_a_new_array():
    values = random_frames()
    before = values.copy()
    got = interpolate_grid(values, COLUMNS, ROWS, 1)
    assert np.array_equal(got, values)
    assert got is not values and not np.shares_memory(got, values)
    got[0, 0] = -5.0
    assert (values == before).all()


@pytest.mark.parametrize("r", RESOLUTIONS)
def test_the_input_is_not_modified(r):
    values = random_frames()
    before = values.copy()
    interpolate_grid(values, COLUMNS, ROWS, r)
    assert (values == before).all()


@pytest.mark.parametrize("r", RESOLUTIONS)
def test_it_equals_np_interp_over_the_rows_and_then_the_columns(r):
    values = random_frames(5, seed=r)
    assert np.allclose(interpolate_grid(values, COLUMNS, ROWS, r), with_np_interp(values, r), atol=1e-12, rtol=0)


@pytest.mark.parametrize("r", RESOLUTIONS)
def test_the_four_corners_are_the_original_corners_exactly(r):
    values = random_frames()
    got = interpolate_grid(values, COLUMNS, ROWS, r).reshape(-1, ROWS * r, COLUMNS * r)
    original = values.reshape(-1, ROWS, COLUMNS)
    assert np.array_equal(got[:, 0, 0], original[:, 0, 0])
    assert np.array_equal(got[:, 0, -1], original[:, 0, -1])
    assert np.array_equal(got[:, -1, 0], original[:, -1, 0])
    assert np.array_equal(got[:, -1, -1], original[:, -1, -1])


@pytest.mark.parametrize("r", RESOLUTIONS)
def test_no_new_value_is_outside_the_range_of_the_original_values_of_its_frame(r):
    values = random_frames(20, seed=10 + r)
    got = interpolate_grid(values, COLUMNS, ROWS, r)
    assert (got.max(axis=1) <= values.max(axis=1) + 1e-12).all()
    assert (got.min(axis=1) >= values.min(axis=1) - 1e-12).all()


@pytest.mark.parametrize("r", RESOLUTIONS)
def test_each_new_value_is_between_the_four_original_values_around_it(r):
    values = random_frames(4, seed=20 + r)
    got = interpolate_grid(values, COLUMNS, ROWS, r).reshape(-1, ROWS * r, COLUMNS * r)
    original = values.reshape(-1, ROWS, COLUMNS)
    xs = np.linspace(0, COLUMNS - 1, COLUMNS * r)
    ys = np.linspace(0, ROWS - 1, ROWS * r)
    for t in range(original.shape[0]):
        for yi, y in enumerate(ys):
            y0, y1 = int(np.floor(y)), min(int(np.ceil(y)), ROWS - 1)
            for xi, x in enumerate(xs):
                x0, x1 = int(np.floor(x)), min(int(np.ceil(x)), COLUMNS - 1)
                around = original[t, [y0, y0, y1, y1], [x0, x1, x0, x1]]
                assert around.min() - 1e-12 <= got[t, yi, xi] <= around.max() + 1e-12


@pytest.mark.parametrize("r", RESOLUTIONS)
def test_a_frame_of_equal_values_gives_a_grid_of_that_value(r):
    values = np.full((3, COLUMNS * ROWS), 0.37)
    assert np.allclose(interpolate_grid(values, COLUMNS, ROWS, r), 0.37, atol=1e-15, rtol=0)
    assert (interpolate_grid(np.zeros((2, COLUMNS * ROWS)), COLUMNS, ROWS, r) == 0).all()


@pytest.mark.parametrize("r", [2, 3, 4, 5])
def test_between_two_neighbours_the_values_step_from_one_to_the_other_in_order(r):
    # a ramp along a row stays a ramp: original columns 0.0, 0.1 ... 1.1 in every row
    ramp = np.tile(np.arange(COLUMNS) / 10.0, ROWS)[None, :]
    got = interpolate_grid(ramp, COLUMNS, ROWS, r).reshape(ROWS * r, COLUMNS * r)
    assert (np.diff(got, axis=1) > 0).all()  # strictly increasing along every new row
    assert np.allclose(got, got[0])  # and the same in every row (the rows are all alike)
    # a step between two neighbours: 0 then 1 in the first two columns, the rest 0
    step = np.zeros((1, COLUMNS * ROWS))
    step[0, 1] = 1.0
    row = interpolate_grid(step, COLUMNS, ROWS, r).reshape(ROWS * r, COLUMNS * r)[0]
    peak = int(np.argmax(row))
    assert (np.diff(row[: peak + 1]) >= 0).all() and (np.diff(row[peak:]) <= 0).all()  # up to the loud note, then down


@pytest.mark.parametrize("r", [2, 3, 5])
def test_rows_and_columns_are_interpolated_separately_the_end_of_a_row_never_touches_the_next_one(r):
    # row 0 is all 1.0 and every other row 0.0: every new value depends on the new row only, never on the column
    values = np.zeros((1, COLUMNS * ROWS))
    values[0, :COLUMNS] = 1.0
    got = interpolate_grid(values, COLUMNS, ROWS, r).reshape(ROWS * r, COLUMNS * r)
    assert np.allclose(got, got[:, [0]])  # the same along every new row
    assert (np.diff(got[:, 0]) <= 1e-15).all()  # and falling from the first row down to 0
    assert got[-1, 0] == 0.0 and got[0, 0] == 1.0


def test_no_frames_gives_an_empty_grid():
    for r in RESOLUTIONS:
        got = interpolate_grid(np.zeros((0, COLUMNS * ROWS)), COLUMNS, ROWS, r)
        assert got.shape == (0, COLUMNS * ROWS * r * r)


@pytest.mark.parametrize("bad", [np.ones((2, 83)), np.ones(84), np.ones((2, 3, 28))])
def test_input_of_the_wrong_shape_is_refused(bad):
    with pytest.raises(ValueError):
        interpolate_grid(bad, COLUMNS, ROWS, 2)


@pytest.mark.parametrize("r", [0, 6, 2.5, None])
def test_a_bad_resolution_is_refused_by_the_interpolation_too(r):
    with pytest.raises(ValueError) as error:
        interpolate_grid(random_frames(), COLUMNS, ROWS, r)
    assert str(error.value) == MESSAGE


@pytest.mark.parametrize("r", RESOLUTIONS)
def test_the_same_input_gives_the_same_output(r):
    values = random_frames()
    assert np.array_equal(interpolate_grid(values, COLUMNS, ROWS, r), interpolate_grid(values, COLUMNS, ROWS, r))


def test_other_grid_shapes_work_too():
    values = np.random.default_rng(3).random((2, 4 * 3))
    got = interpolate_grid(values, 4, 3, 2)
    assert got.shape == (2, 8 * 6)
    assert np.array_equal(got.reshape(2, 6, 8)[:, 0, 0], values.reshape(2, 3, 4)[:, 0, 0])
