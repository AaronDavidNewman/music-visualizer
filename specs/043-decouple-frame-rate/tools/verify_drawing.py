"""Prove that removing the smoothing settings changed no way of drawing.

Feature 043 changes the analysis step (so the pictures of a job change on purpose), which makes ``verify_frames.py`` useless as a no-change check. This tool tests the part that
must not move: ``frame_rendering.write_frames()`` called with fixed note values for every image type, with only the arguments that exist both before and after the feature (the
smoothing arguments default to 0, which changed nothing).

    python verify_drawing.py --write     writes baseline-drawing.json (do this BEFORE the first edit of backend/app)
    python verify_drawing.py             compares with baseline-drawing.json and exits with 1 when any frame differs

The hashes depend on the versions of Pillow, matplotlib and NumPy of the machine, so this is a tool and not a test.

Arrays (the shapes and meanings are those of ``backend/app/services/array_types.py``):
    * ``make_notes()`` returns ``NoteStrengths`` ``(FRAMES, 88)``: the strength of each of the 88 notes in each frame, not negative, seeded.
    * ``make_beat()`` returns ``BeatPositions`` ``(FRAMES,)``: the place of each frame in the local peak, 0 to 1.
"""

import hashlib
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BASELINE = HERE / "baseline-drawing.json"
sys.path.insert(0, str(HERE.parents[2] / "backend"))

from app.services.array_types import BeatPositions, NoteStrengths  # noqa: E402
from app.services.energy_graphs import EnergyGraphData  # noqa: E402
from app.services.frame_rendering import write_frames  # noqa: E402
from app.services.image_types import IMAGE_TYPES  # noqa: E402
from app.services.polychord import PolychordData  # noqa: E402
from app.services.rhythm_circles import RhythmData  # noqa: E402

FRAMES = 24


def make_notes() -> NoteStrengths:
    """``NoteStrengths`` ``(FRAMES, 88)``: seeded strengths, most notes weak or 0, a few loud ones that move from frame to frame."""
    rng = np.random.default_rng(43)
    notes = rng.random((FRAMES, 88)) ** 6
    notes[rng.random((FRAMES, 88)) < 0.5] = 0.0
    for frame in range(FRAMES):
        for loud in ((frame * 3) % 84, (frame * 5 + 20) % 84, (frame + 40) % 84):
            notes[frame, loud] += 1.0 + 0.1 * frame
    return notes


def make_beat() -> BeatPositions:
    """``BeatPositions`` ``(FRAMES,)``: a place in the local peak, 0 to 1, rising and falling."""
    return np.abs(np.sin(np.arange(FRAMES) * 0.4))


def run() -> dict[str, list[str]]:
    """The SHA-256 of every frame for each image type (the key is the image type)."""
    notes = make_notes()
    beat = make_beat()
    energy = EnergyGraphData(
        histogram=np.cumsum(np.arange(FRAMES * 84).reshape(FRAMES, 84) % 7, axis=0).astype(np.int64),
        amplitude=np.cumsum(notes[:, :84] * 10.0, axis=0),
    )
    rhythm = RhythmData(angles=np.cumsum(np.full((FRAMES, 4), 0.02) * np.array([1.0, 2.0, 3.0, 4.0]), axis=0))
    polychord = PolychordData(tempos=np.linspace(70.0, 150.0, FRAMES), frame_rate=10.0)
    hashes: dict[str, list[str]] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for image_type in IMAGE_TYPES:
            directory = Path(tmp) / image_type
            directory.mkdir()
            write_frames(
                notes,
                directory,
                image_type=image_type,
                beat=beat,
                energy=energy if image_type == "energy-graphs" else None,
                rhythm=rhythm if image_type == "rhythm-circles" else None,
                polychord=polychord if image_type == "polychord" else None,
            )
            hashes[image_type] = [hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(directory.glob("frame_*.png"))]
    return hashes


def main() -> int:
    hashes = run()
    total = sum(len(v) for v in hashes.values())
    if "--write" in sys.argv:
        BASELINE.write_text(json.dumps(hashes, indent=1), encoding="utf-8")
        print(f"wrote {BASELINE.name}: {len(hashes)} image types, {total} frames")
        for label, frames in hashes.items():
            print(f"  {label:20s} {len(frames)} frames")
        return 0
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    bad = 0
    for label in baseline:
        now = hashes.get(label)
        if now is None:
            print(f"MISSING   {label}")
            bad += 1
        elif now != baseline[label]:
            different = [i for i, (a, b) in enumerate(zip(now, baseline[label])) if a != b]
            print(f"DIFFERENT {label}: {len(different)} of {len(baseline[label])} frames (first: {different[:5]}), frame count {len(now)} vs {len(baseline[label])}")
            bad += 1
        else:
            print(f"identical {label}: {len(now)} frames")
    print("all frames identical to the baseline" if not bad else f"{bad} image type(s) differ")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
