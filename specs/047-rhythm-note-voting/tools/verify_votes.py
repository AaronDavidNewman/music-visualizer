"""Report how the tempo voting of feature 047 does on the two sample files (nothing is asserted: the numbers are a result to look at).

Usage (from the repository root, with the backend's interpreter):

    backend/.venv/Scripts/python.exe specs/047-rhythm-note-voting/tools/verify_votes.py [extra_notes]

For ``backend/audio/sonata.wav`` (about 116 beats per minute, in groups of three) and ``almost2.wav`` (about 180 beats per minute in groups of four, to be read as
about 90) it makes what a job makes: read the file, analyze it with the fixed 60 ms step, apply the noise floor, then find the starts of the sustained loudest notes in the 60 ms windows
(Extra notes 2, or the number given; the frame rate plays no part, since the second round of feature 047), vote with the time resolution of 60 ms and rank
the tempos. It prints, for each file and for the vote limits 5, 10, 20 and 100: the number of starts, the share of the starts after the first 10 seconds at which the first
or the second tempo is within 10 % of the target, the share for the first tempo alone, how many times the first tempo changes, and a hash of the vote table together
with whether a second run gives the same hash.

Arrays (the shapes and meanings are those of ``backend/app/services/array_types.py``):
    * ``note_windows()`` returns ``NoteStrengths`` ``(windows, 88)``: the strength of each note in each 60 ms window of the file, after the noise floor.
"""

import hashlib
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AUDIO = HERE.parents[2] / "backend" / "audio"
sys.path.insert(0, str(HERE.parents[2] / "backend"))

from app.services.array_types import NoteStrengths  # noqa: E402
from app.services.buffer_interval import BUFFER_INTERVAL_MS, buffer_step  # noqa: E402
from app.services.noise_floor import floor_analysis  # noqa: E402
from app.services.note_analysis import analyze_channels, read_wav  # noqa: E402
from app.services.tempo_votes import average_tempos, note_starts, ranked_tempos, vote_tempos  # noqa: E402

FILES = [("sonata.wav", 116.0), ("almost2.wav", 90.0)]
WINDOW = 4096
EXTRA = int(sys.argv[1]) if len(sys.argv) > 1 else 2
LIMITS = (5, 10, 20, 100)
WINDOW_RATE = 1000.0 / BUFFER_INTERVAL_MS  # windows a second


def note_windows(path: Path) -> NoteStrengths:
    """``NoteStrengths`` ``(windows, 88)``: the file read, analyzed with the 60 ms step and floored, as a job does (the rows ``rhythm_angles`` takes)."""
    rate, left, right = read_wav(path, display_name=path.name)
    result = floor_analysis(analyze_channels(left, right, rate, WINDOW, step=buffer_step(rate)))
    return result.frames


def report(name: str, target: float) -> None:
    """Print the numbers of one file for each vote limit."""
    values = note_windows(AUDIO / name)
    starts = note_starts(values, EXTRA, WINDOW_RATE)
    resolution = BUFFER_INTERVAL_MS / 1000
    print(f"{name}: {values.shape[0]} windows, Extra notes {EXTRA}, {len(starts)} starts, target {target:g} bpm, time resolution {resolution * 1000:.0f} ms")
    for limit in LIMITS:
        votes = vote_tempos(starts, resolution, limit)
        ranked = ranked_tempos(votes)
        again = ranked_tempos(vote_tempos(starts, resolution, limit))
        late = starts >= 10.0
        near = np.abs(ranked - target) <= 0.1 * target
        either = float(near[late].any(axis=1).mean()) if late.any() else float("nan")
        first = float(near[late, 0].mean()) if late.any() else float("nan")
        average = average_tempos(ranked[:, 0])  # the outer circle of Rhythm Circles: the straight average of the last 5 first tempos
        near_average = np.abs(average - target) <= 0.1 * target
        averaged = float(near_average[late].mean()) if late.any() else float("nan")
        changes = int((np.diff(ranked[:, 0]) != 0).sum()) if len(ranked) > 1 else 0
        digest = hashlib.sha256(votes.tobytes()).hexdigest()[:12]
        same = np.array_equal(ranked, again)
        print(
            f"   limit {limit:3d}: first or second within 10% of target {either:5.0%}, first alone {first:5.0%}, averaged first {averaged:5.0%}, "
            f"first tempo changes {changes:4d}, votes hash {digest}, second run identical: {same}"
        )
    ranked = ranked_tempos(vote_tempos(starts, resolution, 10))
    for second in range(0, int(starts[-1]) + 1, 15):
        at = min(int(np.searchsorted(starts, second)), len(starts) - 1)
        print(f"      {second:4d} s: first {ranked[at, 0]:5.0f}, second {ranked[at, 1]:5.0f}")


def main() -> int:
    missing = [name for name, _ in FILES if not (AUDIO / name).exists()]
    if missing:
        print("missing in backend/audio:", ", ".join(missing))
        return 1
    for name, target in FILES:
        report(name, target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
