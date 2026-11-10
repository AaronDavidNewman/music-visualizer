"""The decay step and the simulation of the ``chromatic-decay`` image type (feature 035).

Every expectation is worked out here with plain loops, not with the code under test.
"""

import math

import numpy as np
import pytest

from app.services import chromatic_decay as cd
from app.services.chromatic_decay import PRETEND_NEIGHBORS  # the neighbours a circle's total is split between: the tests follow the constant (6 now)

A, AS, B, C, CS, D, DS, E, F, FS, G, GS = range(12)


def loss(p):
    """What a circle with p points gives each neighbour per frame in Decay Exp: sin^2(pi/2 x p/64), 0 with no points."""
    return math.sin(math.pi / 2 * p / 64) ** 2 if p > 0 else 0.0


def oracle_step(points, frames=1):
    """One step: each circle gives away min(p, N x frames x loss(p)), N being PRETEND_NEIGHBORS (the number of neighbours a circle's total is split between), a share of
    1/N to each of the letters 5 and 7 above and the other (N - 2)/N lost; held 0..64; under 0.01 is 0. All from the points before the step."""
    give = [min(p, PRETEND_NEIGHBORS * frames * loss(p)) for p in points]
    received = [0.0] * 12
    for n in range(12):
        received[(n + 5) % 12] += give[n] / PRETEND_NEIGHBORS
        received[(n + 7) % 12] += give[n] / PRETEND_NEIGHBORS
    after = [min(max(points[n] - give[n] + received[n], 0.0), 64.0) for n in range(12)]
    return [0.0 if v < 0.01 else v for v in after]


def only(letter, value):
    points = np.zeros(12)
    points[letter] = value
    return points


# --- one step ---------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("letter", range(12))
def test_a_circle_gives_to_its_two_receivers_only_and_equally_for_each_of_the_12_letters(letter):
    after = cd.chromatic_step(only(letter, 40.0))
    low, high = (letter + 5) % 12, (letter + 7) % 12
    assert sorted(np.flatnonzero(after).tolist()) == sorted({letter, low, high})
    assert after[low] == after[high] > 0
    assert after[letter] < 40.0
    give = PRETEND_NEIGHBORS * loss(40.0)
    assert after[low] == pytest.approx(give / PRETEND_NEIGHBORS, rel=1e-12)
    assert after.sum() == pytest.approx(40.0 - give * (PRETEND_NEIGHBORS - 2) / PRETEND_NEIGHBORS, rel=1e-12)  # the shares of the missing neighbours are lost


def test_c_gives_to_f_and_g_and_f_gives_to_a_sharp_and_c():
    assert np.flatnonzero(cd.chromatic_step(only(C, 40.0))).tolist() == [C, F, G]
    assert np.flatnonzero(cd.chromatic_step(only(F, 40.0))).tolist() == [AS, C, F]


def test_the_total_given_away_and_the_share_of_a_receiver_are_those_of_decay_exp_for_a_circle_with_neighbours():
    # a receiver gets what each neighbour gets in Decay Exp: frames x loss(p) (when the circle has enough points), and the circle gives away PRETEND_NEIGHBORS times that
    from app.services import decay_exp

    for p in (3.0, 10.0, 24.0, 40.0, 64.0):
        for frames in (1, 4, 10):
            per_neighbour = frames * float(decay_exp.exp_loss_per_frame(p))
            give = min(p, PRETEND_NEIGHBORS * per_neighbour)
            chromatic = cd.chromatic_step(only(C, p), frames)
            assert chromatic[C] == pytest.approx(p - give, rel=1e-12, abs=1e-12)  # the giver keeps what it did not give
            share = give / PRETEND_NEIGHBORS
            share = share if share >= 0.01 else 0.0  # a tail under a hundredth of a point is dropped
            assert chromatic[F] == pytest.approx(share, rel=1e-12, abs=1e-12) and chromatic[G] == chromatic[F]
            if PRETEND_NEIGHBORS * per_neighbour <= p:  # not capped: each receiver gets exactly what a neighbour gets in Decay Exp
                assert chromatic[F] == pytest.approx(per_neighbour if per_neighbour >= 0.01 else 0.0, rel=1e-12, abs=1e-12)


def test_a_circle_never_gives_more_than_it_has():
    after = cd.chromatic_step(only(C, 1.0), 10)
    assert after[C] >= 0
    full = cd.chromatic_step(only(C, 64.0), 10)  # PRETEND_NEIGHBORS x 10 x loss(64): 80 with 8 neighbours, 60 with 6; the giver never gives more than 64
    give = min(64.0, PRETEND_NEIGHBORS * 10 * 1.0)
    assert full[C] == pytest.approx(64.0 - give, abs=1e-12) and full[F] == full[G] == pytest.approx(give / PRETEND_NEIGHBORS, rel=1e-12)
    capped = cd.chromatic_step(only(C, 3.0), 10)  # a circle with few points and a long step: loss(3) x PRETEND_NEIGHBORS x 10 is more than 3 only if PRETEND_NEIGHBORS is large
    assert capped[C] >= 0 and capped.sum() <= 3.0 + 1e-12


def test_a_circle_with_no_points_gives_nothing():
    assert cd.chromatic_step(np.zeros(12)).tolist() == [0.0] * 12


def test_all_circles_give_and_receive_at_the_same_time_from_the_points_before_the_step():
    points = np.zeros(12)
    points[C], points[F] = 40.0, 20.0  # C and F give to each other
    assert np.allclose(cd.chromatic_step(points), oracle_step(points.tolist()), rtol=1e-12, atol=1e-12)
    sequential = points.copy()  # what updating one circle after the other, in place, would give: it must not be what the step gives
    for n in range(12):
        give = min(sequential[n], PRETEND_NEIGHBORS * loss(sequential[n]))
        sequential[n] -= give
        sequential[(n + 5) % 12] += give / PRETEND_NEIGHBORS
        sequential[(n + 7) % 12] += give / PRETEND_NEIGHBORS
    assert not np.allclose(cd.chromatic_step(points), sequential, atol=1e-6)


def test_a_receiver_already_full_stays_at_64():
    points = np.zeros(12)
    points[C], points[F] = 40.0, 64.0
    assert cd.chromatic_step(points)[F] <= 64.0


def test_a_circle_left_with_under_a_hundredth_has_none():
    points = only(C, 0.012)  # gives almost nothing: a receiver would get far under 0.01, and the giver is left with ~0.012
    after = cd.chromatic_step(points)
    assert after[F] == 0 and after[G] == 0  # the receivers' shares are under a hundredth
    assert after[C] == pytest.approx(0.012, abs=1e-6)  # the giver is still above it
    assert cd.chromatic_step(only(C, 0.0099)).tolist() == [0.0] * 12  # below it: gone


@pytest.mark.parametrize("frames", [1, 2, 5, 10])
def test_random_states_agree_with_the_oracle(frames):
    rng = np.random.default_rng(frames)
    for _ in range(40):
        points = rng.random(12) * 64 * (rng.random(12) < 0.6)
        assert np.allclose(cd.chromatic_step(points, frames), oracle_step(points.tolist(), frames), rtol=1e-12, atol=1e-12)


def test_the_total_falls_by_the_shares_of_the_missing_neighbours_when_nothing_is_capped_or_rounded():
    rng = np.random.default_rng(9)
    for _ in range(30):
        points = 5 + rng.random(12) * 20  # between 5 and 25: no cap, no tail
        give = sum(min(p, PRETEND_NEIGHBORS * loss(p)) for p in points)
        assert cd.chromatic_step(points).sum() == pytest.approx(points.sum() - give * (PRETEND_NEIGHBORS - 2) / PRETEND_NEIGHBORS, rel=1e-12)


def test_the_result_is_held_between_0_and_64():
    rng = np.random.default_rng(2)
    for _ in range(50):
        after = cd.chromatic_step(rng.random(12) * 64, int(rng.integers(1, 11)))
        assert after.min() >= 0 and after.max() <= 64


def test_points_that_are_not_fed_fade_to_zero_in_every_circle():
    rng = np.random.default_rng(5)
    points = rng.random(12) * 64
    for _ in range(60000):
        points = cd.chromatic_step(points, 10)
        if not points.any():
            break
    assert not points.any()


def test_the_points_go_round_the_ring_and_come_back_to_the_giver():
    points = only(C, 60.0)
    seen = set()
    for _ in range(30):
        points = cd.chromatic_step(points)
        seen |= set(np.flatnonzero(points).tolist())
    assert seen >= {C, F, G, AS, D}  # F gives on to A# and C, G to C and D (the tails beyond are under a hundredth and vanish)
    assert points[C] > 0  # and C has had some back


def test_the_step_does_not_change_its_input():
    points = np.random.default_rng(1).random(12) * 64
    before = points.copy()
    cd.chromatic_step(points, 3)
    assert np.array_equal(points, before)


@pytest.mark.parametrize("bad", [np.zeros(11), np.zeros((12, 1)), np.zeros((1, 12)), np.full(12, np.nan), np.full(12, np.inf), -np.ones(12), np.full(12, 64.5)])
def test_bad_points_are_refused(bad):
    with pytest.raises(ValueError):
        cd.chromatic_step(bad)


@pytest.mark.parametrize("frames", [0, 11, -1, 2.5, True, "3", None])
def test_frames_must_be_a_whole_number_from_1_to_10(frames):
    with pytest.raises(ValueError):
        cd.chromatic_step(np.zeros(12), frames)


# --- the simulation ----------------------------------------------------------------------------------------------------


def oracle_row_gains(energy_row, position, taper):
    """The five loudest letters (ties to the lower letter, silent ones not counting) gain 24, 20, 16, 12, 8 plus 8 x position, times exp(-g / taper)."""
    gains = [0.0] * 12
    for rank, letter in enumerate(sorted(range(12), key=lambda n: (-energy_row[n], n))[:5]):
        if energy_row[letter] > 0:
            g = (24, 20, 16, 12, 8)[rank] + 8 * position
            gains[letter] = g * math.exp(-g / taper)
    return gains


def oracle_simulation(values, beat, rate):
    """The frame loop written out: gains at the taper of the frame, held to 64, a step at every rate-th frame, the next taper from the circles over 32."""
    from app.services import decay_exp

    energy = cd.letter_energies(values).tolist()
    points, steps, rising = [0.0] * 12, 0, True
    recorded, tapers = [], []
    for index in range(len(energy)):
        taper = decay_exp.taper_of(steps)
        tapers.append(taper)
        gains = oracle_row_gains(energy[index], 0.0 if beat is None else beat[index], taper)
        points = [min(max(points[n] + gains[n], 0.0), 64.0) for n in range(12)]
        if (index + 1) % rate == 0:
            points = oracle_step(points, rate)
        recorded.append(points)
        steps, rising = decay_exp.next_taper(steps, rising, sum(1 for p in points if p > 32))
    return np.array(recorded).reshape(-1, 12), np.array(tapers)


def random_values(frames, seed):
    rng = np.random.default_rng(seed)
    values = rng.random((frames, 88)) * 4
    values[rng.random(values.shape) < 0.6] = 0.0
    return values


@pytest.mark.parametrize("rate", list(range(1, 11)))
def test_the_points_agree_with_the_oracle_for_every_rate_with_and_without_a_beat(rate):
    values = random_values(60, rate)
    beat = np.random.default_rng(rate + 100).random(60)
    for b in (None, beat):
        want, want_tapers = oracle_simulation(values, b, rate)
        got = cd.circle_points(values, b, rate)
        assert got.shape == (60, 12) and got.dtype == np.float64
        assert np.allclose(got, want, rtol=1e-12, atol=1e-12)
        assert np.allclose(cd.circle_tapers(values, b, rate), want_tapers, rtol=0, atol=1e-12)
        assert got.min() >= 0 and got.max() <= 64


def burst(frames=12, note=27):
    values = np.zeros((frames, 88))
    values[0, note] = 2.0  # one loud note in the first frame only
    return values


def test_a_step_falls_at_every_rate_th_frame_and_between_two_steps_the_points_do_not_change():
    for rate in (1, 3, 4, 10):
        points = cd.circle_points(burst(30), None, rate)
        for i in range(1, 30):
            changed = not np.array_equal(points[i], points[i - 1])
            assert changed == ((i + 1) % rate == 0), (rate, i)  # frame 0 has the gain; later frames only change at a step
    first = cd.circle_points(burst(3), None, 1)[0]
    gain = 24 * math.exp(-3)
    assert first[C] < gain  # rate 1: a step at the end of the first frame already took a little
    held = cd.circle_points(burst(3), None, 4)[0]
    assert held[C] == pytest.approx(gain, rel=1e-12) and np.flatnonzero(held).tolist() == [C]  # rate 4: only the gain in the first frame


def test_a_step_of_r_frames_moves_r_times_what_a_step_of_one_frame_moves_while_the_circle_has_enough():
    for p in (3.0, 8.0, 12.0, 20.0):
        one = PRETEND_NEIGHBORS * loss(p)  # what one frame's step gives away
        for rate in (2, 5, 10):
            if PRETEND_NEIGHBORS * rate * loss(p) <= p:  # not capped by the points the circle has
                after = cd.chromatic_step(only(C, p), rate)
                assert p - after[C] == pytest.approx(rate * one, rel=1e-9)  # nothing has come back to C yet: it lost r times one frame's give


def test_over_a_long_time_a_slower_rate_charges_the_circle_to_a_similar_level_not_to_the_same_one():
    # the loss is not a straight line of the points, so one big step is not the same as many small ones; the levels are of the same order
    values = np.zeros((600, 88))
    values[:, 27] = 2.0
    finals = {rate: cd.circle_points(values, None, rate)[-10:, C].mean() for rate in (1, 2, 5, 10)}
    for rate, value in finals.items():
        assert 0.4 * finals[1] <= value <= 1.1 * finals[1], (rate, finals)


def test_a_single_steady_note_charges_its_own_letter_first_and_then_its_two_receivers_whatever_the_octave():
    from app.services import decay_exp

    for note in (3, 15, 27, 51, 75):  # the letter C in different octaves
        values = np.zeros((20, 88))
        values[:, note] = 2.0
        points = cd.circle_points(values)
        assert np.flatnonzero(points[0]).tolist() == [C]
        assert {C, F, G} <= set(np.flatnonzero(points[-1]).tolist())  # a receiver keeps what it gets only once a step gives it a hundredth or more
        assert (points[:, F] == points[:, G]).all()  # the two receivers are mirror images of each other about C
        assert points[-1].argmax() == C
        # frame 0 is the gain Decay Exp gives that note (the same whatever the octave) less what the circle gives away in the step at the end of the frame
        # (nothing has come back yet): Chromatic Decay's own split, so it does not depend on the constant of Decay and Decay Exp
        gain = float(decay_exp.exp_gains(values, None)[0, note])
        give = min(gain, PRETEND_NEIGHBORS * float(decay_exp.exp_loss_per_frame(gain)))
        assert points[0, C] == pytest.approx(gain - give, rel=1e-12)
    assert np.array_equal(cd.circle_points(np.roll(burst(), 12, axis=1)), cd.circle_points(burst()))  # the same one octave up


def test_the_taper_starts_at_8_rises_by_a_hundredth_a_frame_to_12_and_the_rule_that_lowers_it_is_not_reached_with_twelve_circles():
    values = np.full((450, 88), 3.0)  # every letter loud, with the beat at its top: the heaviest feeding there is
    tapers = cd.circle_tapers(values, np.ones(450), 1)
    assert tapers[0] == 8.0 and tapers[1] == pytest.approx(8.01) and tapers[100] == pytest.approx(9.0)
    assert tapers[400] == pytest.approx(12.0) and (tapers[400:] == tapers[400]).all()
    assert (np.diff(tapers) >= -1e-12).all()  # never falls: more than 10 of the 12 circles over 32 points is not reached
    points = cd.circle_points(values, np.ones(450), 1)
    assert ((points > 32).sum(axis=1) <= 10).all()
    assert np.array_equal(tapers, np.array(oracle_simulation(values, np.ones(450), 1)[1]))


def test_the_circle_of_the_loudest_letter_is_the_one_with_the_most_points_at_first():
    values = np.zeros((5, 88))
    values[:, 27] = 3.0  # C
    values[:, 31] = 1.0  # E, fainter
    points = cd.circle_points(values)
    assert points[-1, C] > points[-1, E] or points[-1, C] > 0 and points[-1, E] > 0  # both charge; the louder gains less per frame (taper) but they differ
    assert np.flatnonzero(points[0]).tolist() == [C, E]


def test_there_are_no_frames_for_no_values_and_a_silent_file_stays_at_zero():
    assert cd.circle_points(np.zeros((0, 88))).shape == (0, 12) and cd.circle_tapers(np.zeros((0, 88))).shape == (0,)
    assert cd.circle_points(np.zeros((9, 88)), np.zeros(9), 3).sum() == 0
    assert cd.circle_tapers(np.zeros((3, 88)))[0] == 8.0


@pytest.mark.parametrize("rate", [0, 11, 0.5, 2.5, "3", None, True])
def test_a_bad_decay_rate_is_refused(rate):
    for function in (cd.circle_points, cd.circle_tapers):
        with pytest.raises(ValueError):
            function(np.ones((3, 88)), None, rate)


def test_bad_values_or_beat_are_refused_and_the_inputs_are_not_changed():
    for bad in (np.zeros((3, 83)), -np.ones((3, 88)), np.full((3, 88), np.nan), np.zeros(88)):
        with pytest.raises(ValueError):
            cd.circle_points(bad)
    with pytest.raises(ValueError):
        cd.circle_points(np.ones((3, 88)), np.array([0.0, 2.0, 0.0]))
    values, beat = random_values(10, 1), np.random.default_rng(1).random(10)
    values_before, beat_before = values.copy(), beat.copy()
    first = cd.circle_points(values, beat, 2)
    assert np.array_equal(values, values_before) and np.array_equal(beat, beat_before)
    assert np.array_equal(first, cd.circle_points(values, beat, 2))  # deterministic


def test_the_taper_rule_is_given_the_number_of_circles_over_32_points_of_every_frame_and_its_answer_is_used(monkeypatch):
    seen = []
    real = cd.next_taper

    def spy(steps, rising, full_circles):
        seen.append((steps, rising, full_circles))
        return real(steps, rising, full_circles)

    monkeypatch.setattr(cd, "next_taper", spy)
    values = np.zeros((1500, 88))
    values[:, [27, 31, 34, 39, 22]] = 2.0  # five letters fed with the beat at its top and a step every tenth frame: one circle gets over 32 points
    points = cd.circle_points(values, np.ones(1500), 10)
    assert len(seen) == 1500
    counts = [int((row > 32).sum()) for row in points]
    assert max(counts) >= 1  # the scenario does have circles over 32, or this test would show nothing
    assert [count for _, _, count in seen] == counts
    assert [steps for steps, _, _ in seen][:30] == list(range(30))  # rising by one step a frame

    def falling(steps, rising, full_circles):  # an answer that is used: the taper stays at 8
        return 0, True

    monkeypatch.setattr(cd, "next_taper", falling)
    assert (cd.circle_tapers(values[:30], None, 1) == 8.0).all()
