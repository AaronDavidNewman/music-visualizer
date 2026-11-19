"""The six pictures that take the n loudest notes use the held notes (feature 044, User Story 4).

Library level: with ``extra`` above 0 a note that is still among the loudest n + k keeps its place (its circle gains points, its bar stays, its letter charges, its link stays) after a louder
note starts; with ``extra=0`` (the library default) the pictures are what they were. A steady chord is the same for every ``extra``.
"""

import numpy as np
import pytest

from app.services import chromatic_decay as cd
from app.services import decay, decay_exp
from app.services import polar_chords as pc
from app.services.energy_graphs import EnergyGraphData
from app.services.frame_rendering import write_frames
from app.services.image_types import IMAGE_TYPES
from app.services.note_layout import note_order
from app.services.polychord import PolychordData, PolychordSettings, loudest_letters
from app.services.rhythm_circles import RhythmData

HELD = (10, 11, 12, 13, 14)  # five notes, loudest first, that are struck in frame 0
NEWCOMER = 40
SIX = ("decay", "decay-exp", "polar-chords", "chromatic-decay", "chromatic-wireframe", "polychord")


def values_with_newcomer(held=HELD, newcomer=NEWCOMER):
    """Two frames: the five held notes alone, then a louder newcomer while the five are the 2nd to 6th loudest."""
    values = np.zeros((2, 88))
    values[0, list(held)] = [5, 4, 3, 2, 1]
    values[1, list(held)] = [5, 4, 3, 2, 1]
    values[1, newcomer] = 9
    return values


def steady(frames=12):
    values = np.zeros((frames, 88))
    values[:, [3, 9, 20, 27, 31, 50, 61]] = [7, 6, 5, 4, 3, 2, 1]
    return values


def fading_list(frames=14):
    """Five notes struck at once that fade slowly, while a new, louder note starts every other frame from frame 2."""
    values = np.zeros((frames, 88))
    for frame in range(frames):
        values[frame, list(HELD)] = np.array([5, 4, 3, 2, 1]) * 0.95**frame
    for frame in range(2, frames):  # two newcomers at a time: with six places and five held notes only one of them can have the free place
        values[frame, 40 + (frame // 2) % 20] = 9.0
        values[frame, 62 + (frame // 2) % 10] = 8.5
    return values


# ---- Decay and Decay Exp --------------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("gains", [decay.gains, decay_exp.exp_gains])
def test_the_held_note_keeps_gaining_after_a_louder_note_starts_and_the_newcomer_waits(gains):
    values = values_with_newcomer()
    held = gains(values, None, extra=2) if gains is decay.gains else gains(values, None, decay_exp.TAPER, 2)
    plain = gains(values, None) if gains is decay.gains else gains(values, None, decay_exp.TAPER)
    assert held[1, 14] > 0 and held[1, NEWCOMER] == 0  # the fifth held note still gains; the louder newcomer has no place yet
    assert plain[1, 14] == 0 and plain[1, NEWCOMER] > 0  # as before the feature (extra 0): the newcomer replaces the quietest


def test_the_gains_of_the_held_notes_follow_their_loudness_order():
    held = decay.gains(values_with_newcomer(), None, extra=2)[1]
    assert [held[n] for n in HELD] == list(decay.GAINS)  # the loudest held note gains 24, then 20, 16, 12 and 8


def test_decay_circle_points_keep_the_held_circle_alive():
    values = fading_list()
    held = decay.circle_points(values, extra=2)
    plain = decay.circle_points(values)
    assert not np.array_equal(held, plain)  # the pictures change when notes are displaced
    assert held.shape == plain.shape == (14, 84)


def test_decay_exp_circle_points_and_tapers_accept_extra():
    values = fading_list()
    assert not np.array_equal(decay_exp.circle_points(values, extra=2), decay_exp.circle_points(values))
    assert decay_exp.circle_tapers(values, extra=2).shape == (14,)


# ---- Chromatic Decay and Chromatic Wireframe (letters) ---------------------------------------------------------------------------------------------


def letter_values():
    """Five letters (notes 0 to 4: A, A#, B, C, C#) struck in frame 0; in frame 1 the letter G (note 7 and its octave 19) is the loudest."""
    values = np.zeros((2, 88))
    values[0, :5] = [5, 4, 3, 2, 1]
    values[1, :5] = [5, 4, 3, 2, 1]
    values[1, 19] = 9
    return values


def test_a_held_letter_keeps_charging_and_the_louder_letter_waits():
    values = letter_values()
    held = cd._raw_gains(values, None, 2)
    plain = cd._raw_gains(values, None)
    assert held[1, 4] > 0 and held[1, 7] == 0
    assert plain[1, 4] == 0 and plain[1, 7] > 0
    assert cd.letter_gains(values, None, cd.TAPER, 2)[1, 4] > 0


def test_chromatic_circle_points_and_tapers_accept_extra():
    values = fading_list()
    assert not np.array_equal(cd.circle_points(values, extra=2), cd.circle_points(values))
    assert cd.circle_tapers(values, extra=2).shape == (14,)


# ---- Polar Chords --------------------------------------------------------------------------------------------------------------------------------


def test_the_bar_of_a_held_note_stays_and_the_newcomer_has_none():
    values = values_with_newcomer()
    arc_of_note = np.argsort(note_order("rows"))
    arcs, shares = pc.note_targets(values, 5, "rows", extra=2)
    assert set(arcs[1].tolist()) == {int(arc_of_note[n]) for n in HELD}
    assert int(arc_of_note[NEWCOMER]) not in arcs[1].tolist()
    plain, _ = pc.note_targets(values, 5, "rows")
    assert int(arc_of_note[NEWCOMER]) in plain[1].tolist()  # extra 0: the newcomer is the loudest volume
    assert pc.polar_bars(values, None, 5, "rows", 2).note_slots.shape == (2, 5)


# ---- Polychord ---------------------------------------------------------------------------------------------------------------------------------


def test_the_link_of_a_held_note_stays_and_the_newcomers_letter_is_not_in_the_figure():
    values = np.zeros((2, 88))
    values[0, 10:16] = [6, 5, 4, 3, 2, 1]
    values[1, 10:16] = [6, 5, 4, 3, 2, 1]
    values[1, NEWCOMER] = 9  # note 40 is the letter 4
    held = loudest_letters(values, 6, 2)
    plain = loudest_letters(values, 6)
    assert held[1].tolist() == held[0].tolist() and NEWCOMER % 12 not in held[1].tolist()
    assert plain[1, 0] == NEWCOMER % 12  # extra 0: the newcomer is the first link


def test_two_held_notes_of_one_letter_in_two_octaves_stay_two_links():
    values = np.zeros((2, 88))
    values[0, [3, 15, 5, 6, 7, 8]] = [6, 5, 4, 3, 2, 1]  # notes 3 and 15 are the same letter
    values[1, [3, 15, 5, 6, 7, 8]] = [6, 5, 4, 3, 2, 1]
    values[1, NEWCOMER] = 9
    held = loudest_letters(values, 6, 3)
    assert held[1].tolist().count(3) == 2 and held[1].tolist() == held[0].tolist()


# ---- a steady chord changes nothing (SC-005) -------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("extra", [1, 2, 3, 4, 5])
def test_a_steady_chord_is_the_same_for_every_extra_in_every_picture(extra):
    values = steady()
    assert np.array_equal(decay.gains(values, None, extra), decay.gains(values))
    assert np.array_equal(decay.circle_points(values, extra=extra), decay.circle_points(values))
    assert np.array_equal(decay_exp.circle_points(values, extra=extra), decay_exp.circle_points(values))
    assert np.array_equal(cd.circle_points(values, extra=extra), cd.circle_points(values))
    for count in (5, 8):
        if extra <= count:
            assert np.array_equal(pc.note_targets(values, count, "rows", extra)[0], pc.note_targets(values, count, "rows")[0])
            assert np.array_equal(loudest_letters(values, count, extra), loudest_letters(values, count))


# ---- write_frames end to end -------------------------------------------------------------------------------------------------------------------------


def draw(tmp_path, name, image_type, values, **kwargs):
    frames = values.shape[0]
    extra = {}
    if image_type == "energy-graphs":
        extra["energy"] = EnergyGraphData(np.cumsum(np.ones((frames, 84), dtype=np.int64), axis=0), np.cumsum(np.ones((frames, 84)), axis=0))
    if image_type == "rhythm-circles":
        extra["rhythm"] = RhythmData(np.cumsum(np.full((frames, 4), 0.02), axis=0))
    if image_type == "polychord":
        extra["polychord"] = PolychordData(np.full(frames, 100.0), 10.0)
    directory = tmp_path / name
    write_frames(values, directory, image_type=image_type, **extra, **kwargs)
    return [p.read_bytes() for p in sorted(directory.glob("frame_*.png"))]


@pytest.mark.parametrize("image_type", SIX)
def test_when_notes_are_displaced_the_pictures_change_with_extra_and_not_with_extra_0(tmp_path, image_type):
    values = fading_list()
    default = draw(tmp_path, "default", image_type, values)
    off = draw(tmp_path, "off", image_type, values, extra_notes=0)
    held = draw(tmp_path, "held", image_type, values, extra_notes=2)
    assert default == off  # 0 is the library default: nothing changed for a caller that does not pass it
    assert held != off  # the held notes make a different picture


@pytest.mark.parametrize("image_type", SIX)
def test_a_steady_chord_gives_the_same_pictures_at_every_extra(tmp_path, image_type):
    values = steady()
    off = draw(tmp_path, "off", image_type, values, extra_notes=0)
    for extra in (1, 3, 5):
        assert draw(tmp_path, f"held{extra}", image_type, values, extra_notes=extra) == off, extra


@pytest.mark.parametrize("image_type", ["contour", "energy-graphs", "rhythm-circles"])
def test_the_other_pictures_ignore_extra_notes(tmp_path, image_type):
    values = fading_list()
    base = draw(tmp_path, "base", image_type, values)
    for extra in (1, 8):
        assert draw(tmp_path, f"extra{extra}", image_type, values, extra_notes=extra) == base


@pytest.mark.parametrize(
    "image_type, kwargs, extra, message",
    [
        ("decay", {}, 6, "The extra notes must be a whole number from 1 to 5."),
        ("chromatic-decay", {}, 6, "The extra notes must be a whole number from 1 to 5."),
        ("polar-chords", {"polar_notes": 6}, 7, "The extra notes must be a whole number from 1 to 6."),
        ("polychord", {"polychord_settings": PolychordSettings(6, 2, 9, 10.0)}, 7, "The extra notes must be a whole number from 1 to 6."),
        ("contour", {}, 9, "The extra notes must be a whole number from 1 to 8."),
        ("decay", {}, True, "The extra notes must be a whole number from 1 to 5."),
        ("decay", {}, 2.5, "The extra notes must be a whole number from 1 to 5."),
        ("decay", {}, -1, "The extra notes must be a whole number from 1 to 5."),
    ],
)
def test_write_frames_refuses_a_bad_extra_notes_before_writing_anything(tmp_path, image_type, kwargs, extra, message):
    with pytest.raises(ValueError) as error:
        write_frames(steady(4), tmp_path / "out", image_type=image_type, extra_notes=extra, **kwargs)
    assert str(error.value) == message
    assert not (tmp_path / "out").exists()


def test_every_image_type_is_known_to_this_test():
    assert set(SIX) <= set(IMAGE_TYPES) and len(IMAGE_TYPES) == 9
