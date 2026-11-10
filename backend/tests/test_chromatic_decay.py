"""The numbers of the ``chromatic-decay`` image type (feature 035): letters, the ring, the energy of a letter, the gains, the decay step and the simulation.

Every expectation is worked out here with plain loops, not with the code under test.
"""

import math

import numpy as np
import pytest

from app.services import chromatic_decay as cd

A, AS, B, C, CS, D, DS, E, F, FS, G, GS = range(12)  # the letters, counted from A
NAMES = "A A# B C C# D D# E F F# G G#".split()
RING = [C, G, D, A, E, B, FS, CS, GS, DS, AS, F]  # circle-of-fifths order, clockwise from the top


# --- the letters, the ring and the decay rate -----------------------------------------------------------------


def test_the_constants():
    assert cd.LETTERS == 12
    assert (cd.MIN_RATE, cd.MAX_RATE, cd.DEFAULT_RATE) == (1, 10, 1)
    assert cd.RATE_MESSAGE == "The decay rate must be a whole number from 1 to 10."


def test_c_is_at_the_top_and_the_letters_follow_clockwise_in_circle_of_fifths_order():
    assert [cd.letter_at(k) for k in range(12)] == RING
    assert cd.ring_position(C) == 0
    for k, letter in enumerate(RING):
        assert cd.ring_position(letter) == k


def test_ring_position_and_letter_at_are_inverses():
    for n in range(12):
        assert cd.letter_at(cd.ring_position(n)) == n
        assert cd.ring_position(cd.letter_at(n)) == n


def test_the_receivers_are_the_letters_5_and_7_above_counting_round_the_twelve():
    for n in range(12):
        low, high = cd.receivers(n)
        assert (low, high) == ((n + 5) % 12, (n + 7) % 12)
        assert len({n, low, high}) == 3  # distinct from each other and from the giver
    assert cd.receivers(C) == (F, G)  # C gives to F and G
    assert cd.receivers(F) == (AS, C)  # F gives to A# and C
    assert cd.receivers(G) == (C, D)


def test_the_receivers_of_a_letter_are_the_neighbours_of_its_place_on_the_ring():
    for n in range(12):
        low, high = cd.receivers(n)
        k = cd.ring_position(n)
        assert cd.ring_position(low) == (k - 1) % 12  # the letter 5 above is the next one counterclockwise
        assert cd.ring_position(high) == (k + 1) % 12  # the letter 7 above is the next one clockwise


def test_the_receivers_are_each_others_givers_the_other_way_round():
    for n in range(12):
        low, high = cd.receivers(n)
        assert cd.receivers(low)[1] == n  # n = low + 7
        assert cd.receivers(high)[0] == n  # n = high + 5


@pytest.mark.parametrize("bad", [-1, 12, 3.5, True, "3", None, float("nan")])
def test_a_letter_must_be_a_whole_number_from_0_to_11(bad):
    for function in (cd.receivers, cd.ring_position):
        with pytest.raises(ValueError):
            function(bad)
    with pytest.raises(ValueError):
        cd.letter_at(bad)


@pytest.mark.parametrize("rate", list(range(1, 11)))
def test_a_whole_number_from_1_to_10_is_a_decay_rate(rate):
    assert cd.check_chromatic_rate(rate) == rate
    assert isinstance(cd.check_chromatic_rate(rate), int)
    assert cd.check_chromatic_rate(float(rate)) == rate and isinstance(cd.check_chromatic_rate(float(rate)), int)


@pytest.mark.parametrize("bad", [0, 11, -1, 0.5, 2.5, 10.5, 0.999, 10.001, True, False, "3", "", None, float("nan"), float("inf"), float("-inf"), [3]])
def test_anything_else_is_refused_with_the_message(bad):
    with pytest.raises(ValueError) as error:
        cd.check_chromatic_rate(bad)
    assert str(error.value) == "The decay rate must be a whole number from 1 to 10."


# --- the energy of a letter and the gains ---------------------------------------------------------------------


def row_of(**notes):
    """One frame of 88 note values with the given notes (``n27=3.0`` is note 27)."""
    row = np.zeros(88)
    for name, value in notes.items():
        row[int(name[1:])] = value
    return row


def oracle_energy(values):
    return [[max(values[f][12 * octave + letter] for octave in range(7)) for letter in range(12)] for f in range(len(values))]


def test_the_energy_of_a_letter_is_the_largest_of_its_octaves_not_their_sum():
    values = np.zeros((1, 84))
    values[0, 3], values[0, 15], values[0, 51] = 2.0, 5.0, 3.0  # the letter C in three octaves
    values[0, 4] = 1.5  # C#
    energy = cd.letter_energies(values)
    assert energy.shape == (1, 12) and energy.dtype == np.float64
    assert energy[0, C] == 5.0  # the largest, not 10
    assert energy[0, CS] == 1.5
    assert energy.sum() == 6.5


def test_the_energies_agree_with_a_loop_on_random_values_with_84_and_88_columns():
    rng = np.random.default_rng(3)
    for columns in (84, 88):
        values = rng.random((20, columns)) * 10
        values[rng.random(values.shape) < 0.4] = 0.0
        assert cd.letter_energies(values).tolist() == oracle_energy(values.tolist())


def test_the_four_extra_columns_are_not_notes_of_a_letter():
    values = np.zeros((1, 88))
    values[0, 84:] = 9.0
    assert cd.letter_energies(values).sum() == 0


@pytest.mark.parametrize("bad", [np.zeros(84), np.zeros((2, 83)), -np.ones((1, 84)), np.full((1, 84), np.nan), np.full((1, 84), np.inf)])
def test_letter_energies_and_gains_refuse_what_is_not_note_values(bad):
    with pytest.raises(ValueError):
        cd.letter_energies(bad)
    with pytest.raises(ValueError):
        cd.letter_gains(bad)


def test_the_energies_do_not_change_their_input():
    values = np.random.default_rng(1).random((3, 88))
    before = values.copy()
    cd.letter_energies(values)
    cd.letter_gains(values)
    assert np.array_equal(values, before)


def oracle_gains(energy, beat=None, taper=8.0):
    """The five loudest letters (ties to the lower letter, silent ones not counting) gain 24, 20, 16, 12, 8 plus 8 x position, times exp(-g / taper)."""
    out = []
    for f, row in enumerate(energy):
        tapers = taper[f] if isinstance(taper, (list, tuple, np.ndarray)) else taper
        position = 0.0 if beat is None else beat[f]
        gains = [0.0] * 12
        order = sorted(range(12), key=lambda n: (-row[n], n))
        for rank, letter in enumerate(order[:5]):
            if row[letter] > 0:
                g = (24, 20, 16, 12, 8)[rank] + 8 * position
                gains[letter] = g * math.exp(-g / tapers)
        out.append(gains)
    return out


def test_the_five_loudest_letters_gain_by_rank_cut_by_the_taper():
    values = np.zeros((1, 84))
    for letter, strength in zip((C, E, G, A, D, F, B), (7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0)):
        values[0, 24 + letter] = strength  # seven letters sound, in one octave each
    gains = cd.letter_gains(values)
    assert gains.shape == (1, 12)
    for letter, amount in zip((C, E, G, A, D), (24, 20, 16, 12, 8)):
        assert gains[0, letter] == pytest.approx(amount * math.exp(-amount / 8), rel=1e-12)
    assert gains[0, F] == 0 and gains[0, B] == 0  # the sixth and the seventh gain nothing


def test_the_gains_agree_with_the_oracle_for_random_frames_with_and_without_a_beat_and_a_taper_for_each_frame():
    rng = np.random.default_rng(7)
    values = rng.random((25, 84)) * 3
    values[rng.random(values.shape) < 0.5] = 0.0
    energy = oracle_energy(values.tolist())
    beat = rng.random(25)
    tapers = 8 + 4 * rng.random(25)
    for got, want in (
        (cd.letter_gains(values), oracle_gains(energy)),
        (cd.letter_gains(values, beat), oracle_gains(energy, beat)),
        (cd.letter_gains(values, beat, tapers), oracle_gains(energy, beat, tapers)),
        (cd.letter_gains(values, None, 12.0), oracle_gains(energy, None, 12.0)),
    ):
        assert got.shape == (25, 12) and np.allclose(got, np.array(want), rtol=1e-12, atol=1e-15)


def test_ties_go_to_the_lower_letter_and_a_silent_letter_does_not_count():
    values = np.zeros((1, 84))
    for letter in (G, C, E, A, B, D, F):
        values[0, 12 + letter] = 2.0  # seven letters tied
    gains = cd.letter_gains(values)[0]
    winners = [letter for letter in range(12) if gains[letter] > 0]
    assert winners == [A, B, C, D, E]  # the five lowest letters of the seven
    assert gains[A] < gains[B] < gains[C] < gains[D] < gains[E]  # in order of rank (24 to 8 before the taper): the taper cuts a big gain back more, so the loudest gains the least
    sparse = np.zeros((1, 84))
    sparse[0, 5], sparse[0, 7] = 1.0, 2.0
    assert (cd.letter_gains(sparse)[0] > 0).sum() == 2  # two sounding letters, two gains
    assert cd.letter_gains(np.zeros((1, 84))).sum() == 0


def test_the_beat_bonus_is_added_before_the_taper():
    values = np.zeros((2, 84))
    values[:, 3] = 1.0
    gains = cd.letter_gains(values, np.array([0.0, 1.0]))
    assert gains[0, C] == pytest.approx(24 * math.exp(-3), rel=1e-12)
    assert gains[1, C] == pytest.approx(32 * math.exp(-4), rel=1e-12)  # (24 + 8) x exp(-(24 + 8) / 8)


@pytest.mark.parametrize("note", [3, 15, 27, 39, 51, 63, 75])  # the letter C in each of the 7 octaves
@pytest.mark.parametrize("with_beat", [False, True])
def test_a_single_note_gains_what_decay_exp_gives_its_note_whatever_the_octave(note, with_beat):
    from app.services import decay_exp

    values = np.zeros((3, 84))
    values[:, note] = 2.0
    beat = np.array([0.0, 0.5, 1.0]) if with_beat else None
    chromatic = cd.letter_gains(values, beat)
    exp = decay_exp.exp_gains(values, beat)
    for frame in range(3):
        assert chromatic[frame, note % 12] == pytest.approx(exp[frame, note], rel=1e-12)
        assert chromatic[frame].sum() == pytest.approx(chromatic[frame, note % 12], rel=1e-12)  # only that letter


def test_two_octaves_of_c_charge_c_as_the_louder_of_the_two_not_their_sum():
    values = np.zeros((1, 84))
    values[0, 15], values[0, 51] = 2.0, 3.0
    both = cd.letter_gains(values)
    alone = np.zeros((1, 84))
    alone[0, 51] = 3.0
    assert both[0].tolist() == cd.letter_gains(alone)[0].tolist()


@pytest.mark.parametrize("beat", [[0.0, 2.0], [-0.1, 0.0], [0.5], np.zeros((2, 1)), "ab"])
def test_a_bad_beat_is_refused(beat):
    with pytest.raises(ValueError):
        cd.letter_gains(np.ones((2, 84)), beat)


@pytest.mark.parametrize("taper", [0, -1, float("nan"), [8.0], [8.0, 0.0]])
def test_a_bad_taper_is_refused(taper):
    with pytest.raises(ValueError):
        cd.letter_gains(np.ones((2, 84)), None, taper)
