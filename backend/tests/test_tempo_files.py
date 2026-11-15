"""The tempo finder (feature 040) on the two sample files of ``backend/audio``: measured and reported, with the invariants asserted.

``sonata.wav`` is about 116 beats per minute throughout, grouped by three, so peaks about 1.3 seconds apart are frequent; ``almost2.wav`` is mostly around 180 beats
per minute, grouped by fours, so the tempo should gravitate toward 90. Most peaks of both files are faster than the tempo (see ``specs/040-local-tempo-finder/research.md`` D2: with the first rule, which
only took a sample as the tempo, its half or its two thirds, the tempo was near the target 22 % and 7 % of the time, with 40 and 22 restarts; with the faster
tempos considered too it was 27 % and 49 %, with 2 and 1 restarts, and with a sample standing for a related tempo only within 15 percent of it, as now,
it is 49 % and 35 %, with 4 and 0 restarts): the share of time near the target is printed (run with ``-s``), not asserted. What is asserted holds for any version of the rule: one tempo for each peak, each from 60 to 156, the same on every run.
"""

from pathlib import Path

import numpy as np
import pytest

from app.services.local_peaks import measure_wav
from app.services.tempo_finder import find_tempo

AUDIO = Path(__file__).resolve().parents[1] / "audio"
FILES = [("sonata.wav", 116.0), ("almost2.wav", 90.0)]


@pytest.fixture(scope="module")
def tracks():
    found = {}
    for name, target in FILES:
        path = AUDIO / name
        if not path.exists():
            continue
        peaks = measure_wav(path, 350.0, 20.0)
        times = [p.sample / peaks.file_rate for p in peaks.peaks]
        found[name] = (target, times, find_tempo(times), peaks)
    return found


@pytest.mark.parametrize("name, target", FILES)
def test_the_tempo_of_a_sample_file_is_measured_and_reported(tracks, name, target, capsys):
    if name not in tracks:
        pytest.skip(f"{name} is not in backend/audio")
    target, times, track, peaks = tracks[name]
    tempos = track.tempos
    assert len(times) > 20  # the peaks are really there
    assert tempos.shape == (len(times),)
    assert (tempos >= 60.0).all() and (tempos <= 156.0).all()
    again = find_tempo(times)
    assert again.tempos.tolist() == tempos.tolist() and again.restarts == track.restarts  # the same on every run
    assert 0 <= track.restarts < len(times)

    t = np.asarray(times)
    after = t >= 10.0
    near = float(np.mean(np.abs(tempos[after] - target) <= 0.1 * target)) if after.any() else float("nan")
    with capsys.disabled():
        print(f"\n{name}: {len(times)} peaks, {track.restarts} restarts, {near:.0%} of the peaks after 10 s within 10% of {target:g} bpm")
        for second in range(0, int(t[-1]) + 1, 10):
            at = min(int(np.searchsorted(t, second)), len(t) - 1)
            print(f"   {second:4d} s: tempo {tempos[at]:6.1f}")
