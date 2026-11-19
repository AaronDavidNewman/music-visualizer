"""The frequency buffers through ``POST /api/jobs`` (feature 043): always 60 ms apart, whatever the frame rate, and the frames that average them.

User Story 1: the buffers are the same at every frame rate and a very short note is measured. User Story 2: a frame is made from the buffers it owns, so a note
shows at a low frame rate and nothing is blank at a high one.
"""

import io

import numpy as np
import pytest
from PIL import Image

from app.config import settings
from app.services.frame_rendering import average_frames, frame_count, frame_windows
from app.services.noise_floor import floor_analysis
from app.services.note_analysis import analyze_channels, read_wav

from .test_jobs_api import SR, client, note_tone, post, tone, wav_bytes  # noqa: F401

STEP_44100 = 2646.0  # 60 ms at 44100 Hz
NOTE = 36
BURST_SECONDS = 0.0625  # a 32nd note at 120 beats per minute


def burst_file(start=0.3, total=1.2):
    """Silence with one 62.5 ms burst of a single note: a 32nd note at 120 beats per minute."""
    before = np.zeros(int(start * SR))
    burst = note_tone(NOTE, BURST_SECONDS)
    after = np.zeros(int(total * SR) - before.size - burst.size)
    return np.concatenate([before, burst, after])


def analysis_of(job):
    """The analysis the job made, again from the stored file with the step the job reports (the noise floor included)."""
    rate, left, right = read_wav(settings.audio_temp_dir / job["job_id"] / "audio.wav")
    return floor_analysis(analyze_channels(left, right, rate, job["window_size"], step=job["step_samples"]))


def served_image(client, job, index):
    r = client.get(job["frame_url_template"].replace("{index}", str(index)))
    assert r.status_code == 200
    return np.asarray(Image.open(io.BytesIO(r.content)).convert("RGB"))


def is_flat(image):
    """True when the picture is one color (nothing is drawn)."""
    return len({tuple(p) for p in image.reshape(-1, 3).tolist()}) == 1


# ---- User Story 1: the notes are measured at the same rate whatever the frame rate -----------------------------------------------------------------


@pytest.mark.parametrize("window", ["4096", "16384"])
def test_the_buffers_are_the_same_at_every_frame_rate_and_are_60_ms_apart(client, window):
    data = wav_bytes(burst_file())
    jobs = {fps: post(client, data, window=window, fps=fps).json() for fps in ("1", "10", "24", "30", "60")}
    base = jobs["30"]
    assert base["step_samples"] == STEP_44100
    for fps, job in jobs.items():
        assert job["step_samples"] == base["step_samples"], fps
        assert job["window_count"] == base["window_count"], fps
    reference = analysis_of(base).frames
    for fps in ("1", "10", "60"):
        assert np.array_equal(analysis_of(jobs[fps]).frames, reference), fps  # SC-001: changing the frame rate alone changes no buffer


@pytest.mark.parametrize("fps", ["1", "5", "10", "30", "60"])
def test_a_32nd_note_at_120_bpm_is_measured_at_every_frame_rate(client, fps):
    job = post(client, wav_bytes(burst_file()), window="4096", fps=fps).json()
    result = analysis_of(job)
    assert (result.frames[:, NOTE] > 0).any()  # a buffer sees the burst (SC-003)
    frames = average_frames(result, job["frame_rate"], job["frame_count"])
    assert (frames[:, NOTE] > 0).any()  # and so a frame does, even at 1 frame a second, where a frame is 16 buffers long


def test_the_start_of_each_buffer_is_within_half_a_sample_of_its_exact_place(client):
    job = post(client, wav_bytes(tone(440, 3.0)), window="4096", fps="30").json()
    result = analysis_of(job)
    exact = np.arange(result.window_count) * job["step_samples"]
    assert np.abs(result.window_starts - exact).max() <= 0.5
    assert (np.diff(result.window_starts) / SR * 1000).min() > 59.9 and (np.diff(result.window_starts) / SR * 1000).max() < 60.1


def test_a_file_shorter_than_60_ms_is_measured_once(client):
    job = post(client, wav_bytes(tone(440, 1000 / SR)), window="4096", fps="30").json()
    assert job["window_count"] == 1
    assert (analysis_of(job).frames.shape) == (1, 88)


# ---- User Story 2: a frame averages the buffers it owns -------------------------------------------------------------------------------------------


@pytest.mark.parametrize("fps", ["2", "10"])
def test_at_a_low_frame_rate_every_buffer_is_in_exactly_one_frame_and_a_frame_is_their_mean(client, fps):
    job = post(client, wav_bytes(burst_file(total=2.0)), window="4096", fps=fps).json()
    result = analysis_of(job)
    first, stop, _ = frame_windows(result, job["frame_rate"], job["frame_count"])
    assert int((stop - first).sum()) == job["window_count"]
    frames = average_frames(result, job["frame_rate"], job["frame_count"])
    for f in range(job["frame_count"]):
        assert (stop[f] > first[f]) or f == job["frame_count"] - 1
        if stop[f] > first[f]:
            assert np.allclose(frames[f], result.frames[first[f] : stop[f]].mean(axis=0))


def test_a_tone_is_drawn_while_it_sounds_and_not_after_at_10_and_at_30_frames_a_second(client):
    audio = np.concatenate([note_tone(NOTE, 1.0), np.zeros(SR)])
    data = wav_bytes(audio)
    for fps in (10, 30):
        job = post(client, data, window="4096", fps=str(fps)).json()
        assert job["frame_count"] == 2 * fps
        assert not is_flat(served_image(client, job, fps // 2)), fps  # the middle of the tone: not blank, whatever the frame rate
        assert is_flat(served_image(client, job, 2 * fps - 1)), fps  # the end of the silence: nothing
        assert not any(is_flat(served_image(client, job, i)) for i in range(0, fps - 2)), fps  # no frame of the tone is blank for want of a buffer


def test_frames_above_the_buffer_rate_repeat_the_latest_buffer(client):
    job = post(client, wav_bytes(tone(440, 2.0)), window="4096", fps="60").json()
    result = analysis_of(job)
    frames = average_frames(result, 60, job["frame_count"])
    assert frames.shape[0] == frame_count(len(tone(440, 2.0)), SR, 60) == 120
    first, stop, _ = frame_windows(result, 60, job["frame_count"])
    assert ((stop - first) <= 1).all()  # a 16.7 ms frame holds at most one buffer start
    assert frames.any(axis=1).all()  # and none is blank
