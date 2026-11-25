"""Check the Spirograph pictures of feature 046 on a synthetic file (fixed note values, library defaults).

Usage (from the repository root, with the backend's interpreter):

    backend/.venv/Scripts/python.exe specs/046-spirograph/tools/verify_spirograph.py [output-folder]

It writes 40 frames of a deterministic synthetic file (a few notes that come and go) at the defaults (8 notes, history 8) and at
the largest settings (12, 12) through ``write_frames``, checks the count and names of the files, that every picture is 600 x 400
RGB with black outer edges, that the first frame (one history entry) has fewer lit pixels than the fullest of the frames from 8 on (the history fills up),
and prints the SHA-256 of every file so that two runs can be compared: the same input must give the same hashes. It prints
``all pictures valid`` (exit 0) or the first problem (exit 1). With an output folder it keeps the pictures there to be looked at.
"""

import hashlib
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "backend"))

from app.services.frame_rendering import write_frames  # noqa: E402
from app.services.spirograph import MARGIN, SpirographSettings  # noqa: E402

FRAMES = 40


def notes() -> np.ndarray:
    """``(FRAMES, 88)`` strengths: a few notes that come and go, and one that swells; deterministic."""
    rng = np.random.default_rng(46)
    values = rng.random((FRAMES, 88)) ** 4
    values[rng.random((FRAMES, 88)) < 0.6] = 0.0
    values[:, 27] += np.sin(np.linspace(0, 6, FRAMES)) ** 2
    values[:, 60] += np.where((np.arange(FRAMES) // 8) % 2 == 0, 0.8, 0.0)
    values[10:13] = 0.0  # a silent stretch
    return values


def problem(message: str) -> None:
    print("PROBLEM:", message)
    sys.exit(1)


def check(label: str, directory: Path) -> None:
    files = sorted(directory.glob("*.png"))
    if [f.name for f in files] != [f"frame_{i:06d}.png" for i in range(FRAMES)]:
        problem(f"{label}: the files are not frame_000000.png to frame_{FRAMES - 1:06d}.png")
    lit = []
    for path in files:
        image = Image.open(path)
        if image.size != (600, 400) or image.mode != "RGB":
            problem(f"{label} {path.name}: {image.size} {image.mode}, expected 600 x 400 RGB")
        picture = np.asarray(image)
        edge = MARGIN - 2
        if picture[:edge].any() or picture[-edge:].any() or picture[:, :edge].any() or picture[:, -edge:].any():
            problem(f"{label} {path.name}: a curve comes within {edge} pixels of the edge")
        lit.append(int(picture.any(axis=2).sum()))
        print(f"{label:10s} {path.name} lit {lit[-1]:6d} {hashlib.sha256(path.read_bytes()).hexdigest()[:16]}")
    if not lit[0] < max(lit[8:]):
        problem(f"{label}: the first frame ({lit[0]} lit pixels) is not lighter than the fullest later one ({max(lit[8:])}): the history does not fill up")
    if not any(lit):
        problem(f"{label}: every picture is black")


def main() -> None:
    values = notes()
    keep = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    with tempfile.TemporaryDirectory() as root:
        base = keep or Path(root)
        for label, settings in (("default", SpirographSettings(8, 8)), ("largest", SpirographSettings(12, 12))):
            directory = base / label
            write_frames(values, directory, image_type="spirograph", colormap="inferno", spirograph_settings=settings)
            check(label, directory)
    print("all pictures valid")


if __name__ == "__main__":
    main()
