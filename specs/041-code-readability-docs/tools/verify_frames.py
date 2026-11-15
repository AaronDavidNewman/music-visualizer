"""Prove that the documentation work changed no picture.

Makes one fixed stereo input (generated here, seeded), runs one job through the application for each of the 8 image types with the default settings (and the Contour
once more with Beat coloring on), and takes the SHA-256 of every frame.

    python verify_frames.py --write     writes baseline-frames.json (do this BEFORE the first edit of backend/app)
    python verify_frames.py             compares with baseline-frames.json and exits with 1 when any frame differs

The hashes depend on the versions of Pillow, matplotlib and NumPy of the machine, so this is a tool and not a test.
"""

import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
BASELINE = HERE / "baseline-frames.json"
sys.path.insert(0, str(HERE.parents[2] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services.image_types import IMAGE_TYPES  # noqa: E402

RATE = 44100
SECONDS = 6.0


def make_audio() -> bytes:
    """Stereo, 44.1 kHz, 6 s: a changing chord (the left channel a little different from the right) with a click every half second, alternately loud and soft."""
    rng = np.random.default_rng(41)
    t = np.arange(int(RATE * SECONDS)) / RATE
    notes = [110.0, 165.0, 220.0, 277.18, 329.63, 440.0]
    left = np.zeros_like(t)
    right = np.zeros_like(t)
    for i, f in enumerate(notes):
        envelope = 0.5 + 0.5 * np.sin(2 * np.pi * (0.2 + 0.07 * i) * t + i)
        left += 0.12 * envelope * np.sin(2 * np.pi * f * t)
        right += 0.12 * (1.0 - 0.5 * envelope) * np.sin(2 * np.pi * f * t + 0.3)
    left += 0.01 * rng.standard_normal(t.shape)
    right += 0.01 * rng.standard_normal(t.shape)
    for n, start in enumerate(np.arange(0.5, SECONDS - 0.1, 0.5)):
        s = int(start * RATE)
        strength = 0.8 if n % 2 == 0 else 0.5
        click = strength * np.where(np.arange(16) % 2 == 0, 1.0, -1.0)
        left[s : s + 16] += click
        right[s : s + 16] += click
    data = np.stack([left, right], axis=1)
    data = np.clip(data, -0.99, 0.99)
    buffer = io.BytesIO()
    wavfile.write(buffer, RATE, (data * 32767).astype(np.int16))
    return buffer.getvalue()


def run() -> dict[str, list[str]]:
    audio = make_audio()
    cases = [(name, name, {}) for name in IMAGE_TYPES] + [("contour+beat-coloring", "contour", {"beat_coloring": "true"})]
    hashes: dict[str, list[str]] = {}
    with tempfile.TemporaryDirectory() as tmp:
        settings.audio_temp_dir = Path(tmp) / "audio"
        settings.frames_temp_dir = Path(tmp) / "frames"
        client = TestClient(app)
        for label, image_type, extra in cases:
            response = client.post(
                "/api/jobs",
                files={"file": ("verify.wav", audio, "audio/wav")},
                data={"window_size": "4096", "frame_rate": "10", "colormap": "viridis", "image_type": image_type, **extra},
            )
            assert response.status_code == 200, (label, response.text)
            job = response.json()
            frames = []
            for index in range(job["frame_count"]):
                frame = client.get(job["frame_url_template"].replace("{index}", str(index)))
                assert frame.status_code == 200, (label, index)
                frames.append(hashlib.sha256(frame.content).hexdigest())
            hashes[label] = frames
    return hashes


def main() -> int:
    hashes = run()
    total = sum(len(v) for v in hashes.values())
    if "--write" in sys.argv:
        BASELINE.write_text(json.dumps(hashes, indent=1), encoding="utf-8")
        print(f"wrote {BASELINE.name}: {len(hashes)} cases, {total} frames")
        for label, frames in hashes.items():
            print(f"  {label:24s} {len(frames)} frames")
        return 0
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    bad = 0
    for label in baseline:
        now = hashes.get(label)
        if now is None:
            print(f"MISSING  {label}")
            bad += 1
        elif now != baseline[label]:
            different = [i for i, (a, b) in enumerate(zip(now, baseline[label])) if a != b]
            print(f"DIFFERENT {label}: {len(different)} of {len(baseline[label])} frames (first: {different[:5]}), frame count {len(now)} vs {len(baseline[label])}")
            bad += 1
        else:
            print(f"identical {label}: {len(now)} frames")
    print("all frames identical to the baseline" if not bad else f"{bad} case(s) differ")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
