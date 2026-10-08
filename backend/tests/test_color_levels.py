import numpy as np
import pytest

from app.services.color_levels import (
    HUE_SCALE,
    HUE_STEPS,
    UNIT_SCALE,
    UNIT_STEPS,
    check_step,
    level_count,
    snap,
)

ALL = [(step, HUE_SCALE, "hue", HUE_STEPS) for step in HUE_STEPS] + [
    (step, UNIT_SCALE, "saturation", UNIT_STEPS) for step in UNIT_STEPS
]


def test_constants():
    assert (HUE_SCALE, UNIT_SCALE) == (360, 100)
    assert HUE_STEPS == (12, 36, 90, 180)
    assert UNIT_STEPS == (5, 10, 20, 50)


@pytest.mark.parametrize(
    "step, scale, expected",
    [(12, 360, 31), (36, 360, 11), (90, 360, 5), (180, 360, 3), (5, 100, 21), (10, 100, 11), (20, 100, 6), (50, 100, 3)],
)
def test_level_count(step, scale, expected):
    assert level_count(step, scale) == expected


def test_level_count_is_never_below_three():
    assert all(level_count(step, scale) >= 3 for step, scale, _, _ in ALL)


@pytest.mark.parametrize("step, scale, label, allowed", ALL)
def test_check_step_accepts_every_allowed_value(step, scale, label, allowed):
    assert check_step(step, allowed, label) == step
    assert check_step(float(step), allowed, label) == step
    assert check_step(np.int64(step), allowed, label) == step


def test_check_step_accepts_na():
    assert check_step(None, HUE_STEPS, "hue") is None


@pytest.mark.parametrize("bad", [0, -5, 7, 51, 90, 2.5, True, "20", float("nan"), float("inf"), [20]])
def test_check_step_refuses_everything_else_for_the_unit_scale(bad):
    with pytest.raises(ValueError) as error:
        check_step(bad, UNIT_STEPS, "saturation")
    assert str(error.value) == "The saturation step must be N/A or one of 5, 10, 20, 50."


def test_check_step_message_for_hue_and_other_list():
    with pytest.raises(ValueError, match=r"^The hue step must be N/A or one of 12, 36, 90, 180\.$"):
        check_step(5, HUE_STEPS, "hue")
    with pytest.raises(ValueError):
        check_step(12, UNIT_STEPS, "brightness")


def test_snap_step_20_on_the_unit_scale():
    got = snap([0.49, 0.5, 0.1, 0.09, 0.0, 1.0], 20, UNIT_SCALE)
    assert got.tolist() == pytest.approx([0.4, 0.6, 0.2, 0.0, 0.0, 1.0])


def test_snap_half_way_goes_to_the_higher_level():
    # 10 is half-way between 0 and 20 and 30 between 20 and 40, and so on
    for lower in (0, 20, 40, 60, 80):
        assert snap([(lower + 10) / 100], 20, UNIT_SCALE)[0] == pytest.approx((lower + 20) / 100)


def test_snap_hue_half_way_survives_floating_point_noise():
    x = 6 / 360
    assert snap([x], 12, HUE_SCALE)[0] == pytest.approx(12 / 360)
    for degrees in range(6, 360, 12):  # every exact half-way point goes up
        assert snap([degrees / 360], 12, HUE_SCALE)[0] == pytest.approx((degrees + 6) / 360)


def test_snap_largest_steps_leave_three_values():
    sweep = np.linspace(0.0, 1.0, 10001)
    assert set(np.round(snap(sweep, 180, HUE_SCALE), 12)) == {0.0, 0.5, 1.0}
    assert set(np.round(snap(sweep, 50, UNIT_SCALE), 12)) == {0.0, 0.5, 1.0}


@pytest.mark.parametrize("step, scale, label, allowed", ALL)
def test_snap_gives_exactly_the_levels(step, scale, label, allowed):
    sweep = np.linspace(0.0, 1.0, 20001)
    out = snap(sweep, step, scale)
    levels = set(np.round(out * scale, 9))
    assert levels == {float(k * step) for k in range(scale // step + 1)}
    assert len(levels) == level_count(step, scale)
    assert out.min() == 0.0 and out.max() == 1.0
    assert (np.diff(out) >= 0).all()


@pytest.mark.parametrize("step, scale, label, allowed", ALL)
def test_snap_fixes_zero_and_one(step, scale, label, allowed):
    assert snap([0.0, 1.0], step, scale).tolist() == [0.0, 1.0]


def test_snap_values_outside_the_range_are_clipped():
    assert snap([-0.2, 1.3], 20, UNIT_SCALE).tolist() == [0.0, 1.0]


def test_snap_na_returns_an_unchanged_copy():
    values = np.array([0.123, 0.5, 0.987])
    out = snap(values, None, UNIT_SCALE)
    assert out.tolist() == values.tolist()
    out[0] = 9.0
    assert values[0] == 0.123


def test_snap_never_modifies_its_input():
    values = np.array([0.31, 0.77])
    before = values.copy()
    snap(values, 20, UNIT_SCALE)
    assert (values == before).all()


def test_snap_works_on_one_and_two_dimensions_and_keeps_the_shape():
    one = snap(np.array([0.31, 0.77]), 20, UNIT_SCALE)
    two = snap(np.array([[0.31, 0.77], [0.0, 1.0]]), 20, UNIT_SCALE)
    assert one.shape == (2,) and two.shape == (2, 2)
    assert two[0].tolist() == one.tolist()
    assert one.dtype == np.float64
