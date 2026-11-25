"""Check the 3D export of feature 045 on a synthetic job (fixed note values, library defaults).

Usage (from the repository root, with the backend's interpreter):

    backend/.venv/Scripts/python.exe specs/045-obj-export-mode/tools/verify_export.py

It writes the Contour and the Chromatic Wireframe exports of 30 frames into a temporary folder, reads every file with the
independent reader (``read_obj.py``, written from data-model.md and not from the writer), checks the counts and ranges of the
data model and prints ``all files valid`` (exit 0) or the first problem (exit 1). It also prints the SHA-256 of every file, so
that two runs can be compared: the same input must give the same hashes.
"""

import hashlib
import importlib.util
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "backend"))

from app.services.frame_rendering import write_frames  # noqa: E402
from app.services.obj_export import OBJ_FOLDER  # noqa: E402

spec = importlib.util.spec_from_file_location("read_obj", HERE / "read_obj.py")
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

FRAMES = 30


def notes() -> np.ndarray:
    """88 note values for 30 frames: a few notes that come and go, deterministic."""
    rng = np.random.default_rng(45)
    values = rng.random((FRAMES, 88)) ** 4
    values[:, 27] += np.sin(np.linspace(0, 6, FRAMES)) ** 2  # a note that swells
    values[10:14] = 0.0  # a silent stretch
    return values


def problem(message: str) -> None:
    print("PROBLEM:", message)
    sys.exit(1)


def check(image_type: str, directory: Path) -> None:
    files = sorted((directory / OBJ_FOLDER).glob("*.obj"))
    if [f.name for f in files] != [f"frame_{i:06d}.obj" for i in range(FRAMES)]:
        problem(f"{image_type}: the files are not frame_000000.obj to frame_{FRAMES - 1:06d}.obj")
    for i, path in enumerate(files):
        text = path.read_text(encoding="ascii")
        try:
            vertices, faces, names = reader.read_obj(text)
        except ValueError as error:
            problem(f"{image_type} {path.name}: {error}")
        v = np.array(vertices)
        if image_type == "contour":
            want_points, want_faces, y_max, z_low = 84, 66, 6, 0.0
        else:
            lines = min(i + 1, 12)
            want_points, want_faces, y_max, z_low = 12 * lines, 11 * (lines - 1), lines - 1, 1.0
        if (len(vertices), len(faces)) != (want_points, want_faces):
            problem(f"{image_type} {path.name}: {len(vertices)} points and {len(faces)} faces, expected {want_points} and {want_faces}")
        if names != [path.stem]:
            problem(f"{image_type} {path.name}: the object is called {names}")
        if v[:, 0].min() < 0 or v[:, 0].max() > 11 or v[:, 1].min() < 0 or v[:, 1].max() > y_max or v[:, 2].min() < z_low - 1e-4 or v[:, 2].max() > 12 + 1e-4:
            problem(f"{image_type} {path.name}: a coordinate is out of its range")
        if v[:, 3:].min() < 0 or v[:, 3:].max() > 1:
            problem(f"{image_type} {path.name}: a color is out of 0 to 1")
        for face in faces:
            xs, ys = v[np.array(face) - 1, 0], v[np.array(face) - 1, 1]
            twice_area = float(np.sum(xs * np.roll(ys, -1) - np.roll(xs, -1) * ys))
            if abs(twice_area - 2.0) > 1e-6:
                problem(f"{image_type} {path.name}: the face {face} is not one counterclockwise cell")
        print(f"{image_type:20s} {path.name} {hashlib.sha256(path.read_bytes()).hexdigest()[:16]}")


def main() -> None:
    values = notes()
    beat = np.abs(np.sin(np.linspace(0, 9, FRAMES)))
    with tempfile.TemporaryDirectory() as root:
        for image_type in ("contour", "chromatic-wireframe"):
            directory = Path(root) / image_type
            write_frames(values, directory, image_type=image_type, beat=beat, export_obj=True)
            check(image_type, directory)
    print("all files valid")


if __name__ == "__main__":
    main()
