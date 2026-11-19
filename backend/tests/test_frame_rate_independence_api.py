"""Every image type through the job endpoint at several frame rates (feature 043, User Story 4).

The notes are measured every 60 ms whatever the frame rate, so a job at 10, 16 or 30 frames a second makes the same buffers and a number of frames that depends on the
frame rate only. What the types measure over the whole file (the beat) is read at the middle of each frame, as before.
"""

import io
import math

import numpy as np
import pytest
from PIL import Image

import app.routers.jobs as jobs
from app.config import settings
from app.services.image_types import IMAGE_TYPES
from app.services.local_peaks import DEFAULT_MIN_DISTANCE, DEFAULT_PROMINENCE, measure_local_peaks
from app.services.note_analysis import read_wav

from .test_jobs_api import SR, client, note_tone, tone, wav_bytes  # noqa: F401
from .test_peak_tile_colors_api import pulse_wav

SECONDS = 2.0
RATES = ("10", "16", "30")


def music():
    """Two seconds of three changing tones: enough for every type to draw something."""
    t = np.arange(int(SECONDS * SR)) / SR
    audio = 0.4 * np.sin(2 * np.pi * 220 * t) + 0.3 * np.sin(2 * np.pi * 330 * t * (1 + 0.05 * t)) + 0.2 * np.sin(2 * np.pi * 440 * t)
    return wav_bytes(audio * np.interp(t, [0, 1, 2], [1.0, 0.4, 0.9]))


def post_type(client, image_type, fps, data):
    form = {"window_size": "4096", "frame_rate": fps, "image_type": image_type}
    return client.post("/api/jobs", files={"file": ("song.wav", data, "audio/wav")}, data=form)


@pytest.mark.parametrize("image_type", IMAGE_TYPES)
def test_every_image_type_makes_its_frames_at_10_16_and_30_frames_a_second(client, image_type):
    data = music()
    jobs_made = {}
    for fps in RATES:
        r = post_type(client, image_type, fps, data)
        assert r.status_code == 200, (image_type, fps, r.text)
        job = r.json()
        assert job["frame_count"] == math.ceil(SECONDS * int(fps) - 1e-9), (image_type, fps)  # the number of frames is the duration times the frame rate
        for index in (0, job["frame_count"] - 1):
            image = client.get(job["frame_url_template"].replace("{index}", str(index)))
            assert image.status_code == 200
            assert Image.open(io.BytesIO(image.content)).size == (600, 400)
        jobs_made[fps] = job
    first = jobs_made[RATES[0]]
    for fps, job in jobs_made.items():
        assert job["step_samples"] == first["step_samples"] == 2646, (image_type, fps)
        assert job["window_count"] == first["window_count"], (image_type, fps)  # SC-006: the same buffers at every frame rate


@pytest.fixture
def given(monkeypatch):
    """The ``beat`` that the job gives ``write_frames``, one for each call."""
    beats = []
    real = jobs.write_frames

    def spy(frames, *args, **kwargs):
        beats.append(kwargs.get("beat"))
        return real(frames, *args, **kwargs)

    monkeypatch.setattr(jobs, "write_frames", spy)
    return beats


@pytest.mark.parametrize("fps", [10, 30])
def test_the_beat_is_measured_from_the_audio_and_read_at_the_middle_of_each_frame(client, given, fps):
    data = pulse_wav(seconds=4.0)
    job = post_type(client, "decay", str(fps), data).json()
    rate, left, right = read_wav(settings.audio_temp_dir / job["job_id"] / "audio.wav")
    expected = measure_local_peaks(left, right, rate, DEFAULT_MIN_DISTANCE, DEFAULT_PROMINENCE).frame_positions(fps, job["frame_count"])
    assert given[0] is not None and given[0].shape == (job["frame_count"],)
    assert np.array_equal(given[0], expected)  # not made from the buffers: only the frame rate decides where it is read
