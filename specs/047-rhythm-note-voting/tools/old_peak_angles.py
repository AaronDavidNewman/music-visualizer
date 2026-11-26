"""Save the angles of the two local-peak circles as the four-ring Rhythm Circles made them (before feature 047).

Run with the backend's interpreter from the repository root, BEFORE the first edit of ``backend/app/services/rhythm_circles.py``::

    backend/.venv/Scripts/python.exe specs/047-rhythm-note-voting/tools/old_peak_angles.py

It builds ``rhythm_angles()`` for a fixed list of 12 peaks at irregular times and rates over a 20 s file at 30 frames a second and writes columns 2 and 3
(the local peak and its rate of change) to ``old_peak_angles.npy``: ``CircleAngles`` ``(600, 2)`` in turns. After the feature the two inner rings are columns 4 and 5 and
must equal these numbers.
"""

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "backend"))

from app.services.local_peaks import LocalPeak, LocalPeaks  # noqa: E402
from app.services.rhythm_circles import rhythm_angles  # noqa: E402

TIMES = (0.8, 1.7, 2.9, 3.6, 5.2, 6.1, 8.0, 9.4, 11.3, 12.0, 14.6, 17.5)
RATES = (75.0, 66.0, 90.0, 80.0, 70.0, 120.0, 63.0, 95.0, 100.0, 85.0, 60.0, 110.0)
FILE_RATE = 44100
FRAME_RATE = 30.0
FRAMES = 600


def fixed_peaks() -> LocalPeaks:
    """The ``LocalPeaks`` of the fixed list (hand-made peaks, no audio)."""
    peaks = tuple(LocalPeak(int(round(t * FILE_RATE)), 1.0, 0.0, 1.0, r) for t, r in zip(TIMES, RATES))
    return LocalPeaks(peaks=peaks, file_rate=FILE_RATE, sample_count=20 * FILE_RATE, min_distance=350.0, prominence=20.0)


if __name__ == "__main__":
    angles = rhythm_angles(fixed_peaks(), FRAME_RATE, FRAMES).angles
    np.save(HERE / "old_peak_angles.npy", angles[:, 2:4])
    print("saved", angles[:, 2:4].shape)
