"""Report how the tempo voting of feature 047 does on the two sample files (nothing is asserted: the numbers are a result to look at).

Usage (from the repository root, with the backend's interpreter):

    backend/.venv/Scripts/python.exe specs/047-rhythm-note-voting/tools/verify_votes.py

For ``backend/audio/sonata.wav`` (about 116 beats per minute, in groups of three), ``almost2.wav`` (about 180 beats per minute in groups of four, to be read as
about 90) and the three computer-made piano files (``piano-108bpm.wav``, ``piano2-108bpm.wav``, ``piano-120bpm.wav``, steady at the tempo in the name) it makes what a job makes:
read the file, analyze it with the fixed 60 ms step, apply the noise floor, then find the starts of the notes (the rise of the note strengths of the 60 ms windows placed on the waveform:
``note_onsets``, fourth round of feature 047; the frame rate and the Extra notes play no part), vote with the time resolution of 40 ms (``rhythm_circles.START_RESOLUTION``) and rank
the tempos. It prints, for each file and for the vote limits 5, 10, 20 and 100: the number of starts, the share of the starts after the first 10 seconds at which the first
or the second tempo is within 10 % of the target, the share for the first tempo alone, how many times the first tempo changes, and a hash of the vote table together
with whether a second run gives the same hash.

Arrays (the shapes and meanings are those of ``backend/app/services/array_types.py``):
    * ``note_windows()`` returns ``NoteStrengths`` ``(windows, 88)``: the strength of each note in each 60 ms window of the file, after the noise floor.
    * ``file_starts()`` returns ``StartTimes`` ``(starts,)``: the seconds at which a note begins.
"""

import hashlib
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AUDIO = HERE.parents[2] / "backend" / "audio"
sys.path.insert(0, str(HERE.parents[2] / "backend"))

from app.services.array_types import NoteStrengths, StartTimes  # noqa: E402
from app.services.buffer_interval import buffer_step  # noqa: E402
from app.services.noise_floor import floor_analysis  # noqa: E402
from app.services.note_analysis import analyze_channels, read_wav  # noqa: E402
from app.services.note_onsets import onset_starts  # noqa: E402
from app.services.rhythm_circles import START_RESOLUTION  # noqa: E402
from app.services.tempo_votes import DEFAULT_VOTE_LIMIT, average_tempos, leading_tempos  # noqa: E402

FILES = [
    ("sonata.wav", 116.0),
    ("almost2.wav", 90.0),
    ("piano-108bpm.wav", 108.0),
    ("piano2-108bpm.wav", 108.0),
    ("piano-120bpm.wav", 120.0),
    ("Thunderer.wav", 122.0),
    ("WMTS.wav", 105.0),
    ("turnyourlove.wav", 100.0),
    ("02_Mean_.wav", 105.0),
]
WINDOW = 4096
LIMITS = (10, 20, 40, 100)


def note_windows(path: Path) -> NoteStrengths:
    """``NoteStrengths`` ``(windows, 88)``: the file read, analyzed with the 60 ms step and floored, as a job does (the rows ``rhythm_angles`` takes)."""
    rate, left, right = read_wav(path, display_name=path.name)
    result = floor_analysis(analyze_channels(left, right, rate, WINDOW, step=buffer_step(rate)))
    return result.frames


def file_starts(path: Path) -> StartTimes:
    """``StartTimes`` ``(starts,)``: the starts of the notes of the file, found as a job finds them (the rise of the windows, placed on the waveform)."""
    rate, left, right = read_wav(path, display_name=path.name)
    return onset_starts(note_windows(path), left, right, rate)


def report(name: str, target: float) -> None:
    """Print the numbers of one file for each vote limit, as Rhythm Circles finds its tempo (``leading_tempos``, fifth round)."""
    starts = file_starts(AUDIO / name)
    resolution = START_RESOLUTION
    print(f"{name}: {len(starts)} starts, target {target:g} bpm, time resolution {resolution * 1000:.0f} ms")
    for limit in LIMITS:
        leading = leading_tempos(starts, resolution, limit)
        again = leading_tempos(starts, resolution, limit)
        late = starts >= 10.0
        raw = leading[:, 0]
        average = average_tempos(raw)  # the outer circle of Rhythm Circles: the straight average of the last 5 first tempos
        share = lambda tempos, tolerance: float((np.abs(tempos - target) <= tolerance * target)[late].mean()) if late.any() else float("nan")
        triple = float((leading[late, 1] == 3).mean()) if late.any() else float("nan")
        changes = int((np.diff(raw) != 0).sum()) if len(raw) > 1 else 0
        digest = hashlib.sha256(leading.tobytes()).hexdigest()[:12]
        print(
            f"   limit {limit:3d}: first tempo within 10% of target {share(raw, 0.1):5.0%} (within 3% {share(raw, 0.03):5.0%}), averaged {share(average, 0.1):5.0%}, "
            f"beats in 3 {triple:5.0%}, first tempo changes {changes:4d}, hash {digest}, second run identical: {np.array_equal(leading, again)}"
        )
    leading = leading_tempos(starts, resolution, DEFAULT_VOTE_LIMIT)
    for second in range(0, int(starts[-1]) + 1, 15):
        at = min(int(np.searchsorted(starts, second)), len(starts) - 1)
        print(f"      {second:4d} s: first {leading[at, 0]:5.0f}, meter {leading[at, 1]:.0f}")


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
