"""The tempo voting (feature 047) on the two sample files of ``backend/audio``: measured and reported, with the invariants asserted.

``sonata.wav`` is about 116 beats per minute throughout, grouped by three; ``almost2.wav`` is mostly around 180 beats per minute, grouped by fours, so it should be read as
about 90. The share of the time that the first or the second voted tempo is within 10 % of the target is printed (run with ``-s``), not asserted: it is a result to look at
(see ``specs/047-rhythm-note-voting/verify_votes-output.txt`` for the numbers of the first measurement). What is asserted holds for any version of the rule: there are 18
tempos, every vote is a whole number from 0 to the limit, every ranked tempo is one of the 18 or the starting 120, and two runs give the same result.

The path is the one of a job: read the file, analyze it with the fixed 60 ms step, apply the noise floor, average the windows into frames at 30 frames a second, then the
starts of the sustained loudest notes, the votes and the ranking.
"""

from pathlib import Path

import numpy as np
import pytest

from app.services.buffer_interval import BUFFER_INTERVAL_MS, buffer_step
from app.services.frame_rendering import average_frames, frame_count
from app.services.noise_floor import floor_analysis
from app.services.note_analysis import analyze_channels, read_wav
from app.services.tempo_votes import TEMPOS, note_starts, ranked_tempos, vote_tempos

AUDIO = Path(__file__).resolve().parents[1] / "audio"
FILES = [("sonata.wav", 116.0), ("almost2.wav", 90.0)]
FPS = 30.0
WINDOW = 4096


@pytest.fixture(scope="module")
def starts_of_files():
    found = {}
    for name, _ in FILES:
        path = AUDIO / name
        if not path.exists():
            continue
        rate, left, right = read_wav(path, display_name=name)
        frames = frame_count(left.shape[0], rate, FPS)
        result = floor_analysis(analyze_channels(left, right, rate, WINDOW, step=buffer_step(rate)))
        found[name] = note_starts(average_frames(result, FPS, frames), 2, FPS)
    return found


@pytest.mark.parametrize("name, target", FILES)
def test_the_voting_of_a_sample_file_is_measured_and_reported(starts_of_files, name, target, capsys):
    if name not in starts_of_files:
        pytest.skip(f"{name} is not in backend/audio")
    starts = starts_of_files[name]
    assert len(starts) > 50 and (np.diff(starts) > 0).all()  # the notes really start
    resolution = max(1.0 / FPS, BUFFER_INTERVAL_MS / 1000)
    for limit in (5, 20, 100):
        votes = vote_tempos(starts, resolution, limit)
        ranked = ranked_tempos(votes)
        assert votes.shape == (len(starts), len(TEMPOS)) == (len(starts), 18)
        assert votes.min() >= 0 and votes.max() <= limit and votes.dtype.kind == "i"
        assert ranked.shape == (len(starts), 2) and set(np.unique(ranked)) <= set(TEMPOS) | {120}
        assert np.array_equal(ranked, ranked_tempos(vote_tempos(starts, resolution, limit)))  # the same on every run
        late = starts >= 10.0
        near = np.abs(ranked - target) <= 0.1 * target
        share = float(near[late].any(axis=1).mean()) if late.any() else float("nan")
        with capsys.disabled():
            print(f"\n{name} limit {limit}: {len(starts)} starts, first or second within 10% of {target:g} bpm for {share:.0%} of the starts after 10 s")
