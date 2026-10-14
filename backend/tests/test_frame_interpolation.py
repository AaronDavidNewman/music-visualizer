"""The interpolation setting and the in-between frames: ``app/services/frame_interpolation.py``.

Pillow is the definition of the in-between frames: the tests apply ``Image.blend`` themselves to the decoded drawn files,
and check it again against a plain numpy weighted mix.
"""

import numpy as np
import pytest
from PIL import Image

from app.services import frame_interpolation
from app.services.frame_interpolation import (
    DEFAULT_INTERPOLATE,
    MAX_INTERPOLATE,
    MIN_INTERPOLATE,
    check_interpolate,
    key_frames,
    write_interpolated_frames,
)

INTERPOLATE_MESSAGE = "The interpolate value must be a whole number from 1 to 5."
SIZE = (252, 168)


def name(i):
    return f"frame_{i:06d}.png"


def random_picture(seed, kind="RGB"):
    rng = np.random.default_rng(seed)
    if kind == "P":
        image = Image.fromarray(rng.integers(0, 6, size=(SIZE[1], SIZE[0]), dtype=np.uint8), "P")
        image.putpalette(rng.integers(0, 256, size=18, dtype=np.uint8).tolist())
        return image
    array = rng.integers(0, 256, size=(SIZE[1], SIZE[0], 4 if kind == "RGBA" else 3), dtype=np.uint8)
    if kind == "RGBA":
        array[..., 3] = 255
    return Image.fromarray(array, kind)


def make_drawn(directory, count, interpolate, kinds=("RGB",), seed=0):
    """Write the drawn frames of a job as PNG files (of the given kinds in turn) and return their numbers."""
    directory.mkdir(parents=True, exist_ok=True)
    drawn = key_frames(count, interpolate)
    for position, i in enumerate(drawn):
        random_picture(seed + i, kinds[position % len(kinds)]).save(directory / name(i))
    return drawn


def decoded(directory, i):
    return Image.open(directory / name(i)).convert("RGB")


def gaps(drawn):
    return list(zip(drawn[:-1], drawn[1:]))


# --- the setting ---------------------------------------------------------------------------------------------------------------


def test_constants():
    assert (MIN_INTERPOLATE, MAX_INTERPOLATE, DEFAULT_INTERPOLATE) == (1, 5, 1)


def test_the_interpolation_function_is_gone():
    # offered in feature 018 and removed again: only blend is made, so there is nothing to choose
    for gone in ("INTERPOLATE_FUNCTIONS", "DEFAULT_INTERPOLATE_FUNCTION", "check_interpolate_function"):
        assert not hasattr(frame_interpolation, gone)
    assert not hasattr(frame_interpolation, "ImageChops")


@pytest.mark.parametrize("value", [1, 2, 3, 4, 5, np.int64(3), 3.0, np.float64(5.0)])
def test_interpolate_values_from_one_to_five_are_accepted(value):
    assert check_interpolate(value) == int(value) and isinstance(check_interpolate(value), int)


@pytest.mark.parametrize("bad", [0, 6, -1, 2.5, True, False, None, "3", "", float("nan"), float("inf"), -float("inf"), b"3"])
def test_other_interpolate_values_are_refused_with_the_message(bad):
    with pytest.raises(ValueError) as error:
        check_interpolate(bad)
    assert str(error.value) == INTERPOLATE_MESSAGE


# --- the drawn frames ---------------------------------------------------------------------------------------------------------


def test_the_drawn_frames_of_three_hundred_frames_at_five():
    assert key_frames(300, 5) == list(range(0, 300, 5)) + [299]  # the user's frames 1, 6, 11 ... and the last
    assert key_frames(300, 1) == list(range(300))


@pytest.mark.parametrize(
    "count, interpolate, expected",
    [(11, 5, [0, 5, 10]), (12, 5, [0, 5, 10, 11]), (3, 5, [0, 2]), (8, 5, [0, 5, 7]), (1, 5, [0]), (0, 5, []), (2, 5, [0, 1]), (6, 5, [0, 5])],
)
def test_the_last_frame_is_always_drawn_and_the_last_gap_can_be_shorter(count, interpolate, expected):
    assert key_frames(count, interpolate) == expected


@pytest.mark.parametrize("interpolate", [1, 2, 3, 4, 5])
def test_the_drawn_frames_cover_the_file_with_gaps_of_at_most_the_interpolate_value(interpolate):
    for count in range(0, 61):
        drawn = key_frames(count, interpolate)
        assert drawn == sorted(set(drawn))
        if count == 0:
            assert drawn == []
            continue
        assert drawn[0] == 0 and drawn[-1] == count - 1
        assert all(0 < b - a <= interpolate for a, b in gaps(drawn))
        multiples = len(range(0, count, interpolate))
        assert len(drawn) == multiples + (0 if (count - 1) % interpolate == 0 else 1)  # the formula of FR-009


@pytest.mark.parametrize("bad", [0, 6, 2.5, None])
def test_key_frames_refuses_a_bad_interpolate_value(bad):
    with pytest.raises(ValueError):
        key_frames(10, bad)


# --- the in-between frames ----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("count", [11, 12, 13, 9, 7, 3])
@pytest.mark.parametrize("interpolate", [2, 3, 4, 5])
def test_the_frames_are_the_weighted_mix_of_the_neighbours_with_the_weight_of_their_own_gap(tmp_path, count, interpolate):
    drawn = make_drawn(tmp_path, count, interpolate, kinds=("P", "RGB", "RGBA"))
    before = {i: (tmp_path / name(i)).read_bytes() for i in drawn}
    write_interpolated_frames(tmp_path, count, interpolate)
    assert sorted(p.name for p in tmp_path.glob("frame_*.png")) == [name(i) for i in range(count)]
    for i in drawn:
        assert (tmp_path / name(i)).read_bytes() == before[i]  # the drawn frames are not touched
    for a, b in gaps(drawn):
        earlier, later = np.asarray(decoded(tmp_path, a), dtype=float), np.asarray(decoded(tmp_path, b), dtype=float)
        for i in range(a + 1, b):
            w = (i - a) / (b - a)  # the position is counted within the gap
            image = Image.open(tmp_path / name(i))
            assert image.mode == "RGB" and image.size == SIZE
            mix = (1 - w) * earlier + w * later
            assert np.abs(np.asarray(image, dtype=float) - mix).max() <= 1.0 + 1e-9, (a, b, i)  # Pillow truncates: within one level


@pytest.mark.parametrize("count, interpolate", [(11, 5), (12, 5), (8, 5), (10, 3)])
def test_the_frames_are_exactly_what_pillows_blend_gives(tmp_path, count, interpolate):
    drawn = make_drawn(tmp_path, count, interpolate, kinds=("RGB", "P", "RGBA"), seed=7)
    write_interpolated_frames(tmp_path, count, interpolate)
    for a, b in gaps(drawn):
        for i in range(a + 1, b):
            want = Image.blend(decoded(tmp_path, a), decoded(tmp_path, b), (i - a) / (b - a))
            assert np.array_equal(np.asarray(decoded(tmp_path, i)), np.asarray(want)), i


def test_the_first_frame_is_nearer_the_earlier_picture_and_the_last_nearer_the_later_one(tmp_path):
    make_drawn(tmp_path, 6, 5, seed=11)
    write_interpolated_frames(tmp_path, 6, 5)
    earlier, later = (np.asarray(decoded(tmp_path, i), dtype=float) for i in (0, 5))
    distance = lambda i, other: np.abs(np.asarray(decoded(tmp_path, i), dtype=float) - other).mean()  # noqa: E731
    assert distance(1, earlier) < distance(1, later) and distance(4, later) < distance(4, earlier)
    assert [round(distance(i, earlier), 1) for i in range(1, 5)] == sorted(round(distance(i, earlier), 1) for i in range(1, 5))


def test_two_identical_drawn_frames_give_identical_frames_between_them(tmp_path):
    picture = random_picture(5)
    for i in (0, 5):
        picture.save(tmp_path / name(i))
    write_interpolated_frames(tmp_path, 6, 5)
    assert all(np.array_equal(np.asarray(Image.open(tmp_path / name(i))), np.asarray(picture)) for i in range(1, 5))


def test_the_result_does_not_depend_on_the_number_of_worker_threads(tmp_path, monkeypatch):
    results = []
    for workers in (1, 4):
        monkeypatch.setattr(frame_interpolation, "_WORKERS", workers)
        directory = tmp_path / f"w{workers}"
        make_drawn(directory, 23, 5, kinds=("P", "RGBA"), seed=9)
        write_interpolated_frames(directory, 23, 5)
        results.append([(directory / name(i)).read_bytes() for i in range(23)])
    assert results[0] == results[1]


def test_a_missing_drawn_frame_raises_the_error_of_the_worker(tmp_path):
    drawn = make_drawn(tmp_path, 11, 5)
    (tmp_path / name(drawn[1])).unlink()
    with pytest.raises(FileNotFoundError):
        write_interpolated_frames(tmp_path, 11, 5)


@pytest.mark.parametrize("count", [0, 1, 2])
def test_nothing_is_made_when_there_is_no_gap(tmp_path, count):
    make_drawn(tmp_path, count, 5)
    before = sorted(p.name for p in tmp_path.glob("*"))
    write_interpolated_frames(tmp_path, count, 5)
    assert sorted(p.name for p in tmp_path.glob("*")) == before


def test_interpolate_one_writes_nothing_and_does_not_need_the_directory(tmp_path):
    write_interpolated_frames(tmp_path / "missing", 10, 1)
    assert not (tmp_path / "missing").exists()


@pytest.mark.parametrize("interpolate", [0, 6, 2.5, None])
def test_a_bad_setting_is_refused_before_anything_is_written(tmp_path, interpolate):
    make_drawn(tmp_path, 11, 5)
    before = sorted(p.name for p in tmp_path.glob("*"))
    with pytest.raises(ValueError):
        write_interpolated_frames(tmp_path, 11, interpolate)
    assert sorted(p.name for p in tmp_path.glob("*")) == before
