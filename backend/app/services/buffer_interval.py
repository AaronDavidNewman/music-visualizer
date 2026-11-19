"""The frequency buffers: how far apart they start, which is always 60 ms (feature 043).

A job measures the strength of the notes in a *frequency buffer* (``note_analysis`` calls it an analysis window) every 60 ms of the audio, whatever the frame rate: the frame rate only
decides how many pictures are made from the buffers (see ``frame_rendering``, which averages the buffers that start in each frame). 60 ms is shorter than a 32nd note at 120 beats
per minute (62.5 ms), so a buffer is measured often enough not to skip even a very short note.

Order of operations:
    1. Choose the step - ``buffer_step()`` - the distance in samples between the starts of two neighbouring buffers: 60 ms at the sample rate of the file, a float (11025 Hz gives 661.5).
       This is a number and not an array, so it has no alias; ``note_analysis.window_starts()`` turns it into the start sample of each buffer (``WindowStarts`` ``(windows,)``) by
       rounding ``k * step`` to the nearest sample, so every buffer starts within half a sample of its exact place.
"""

BUFFER_INTERVAL_MS: int = 60  # the time from the start of one buffer to the start of the next


def buffer_step(sample_rate: float) -> float:
    """The step between the starts of two neighbouring buffers, in samples: ``BUFFER_INTERVAL_MS`` at ``sample_rate``.

    The sample rate is multiplied by the milliseconds before it is divided by 1000 so that the usual rates give an exact number (44100 gives 2646.0 and 48000 gives 2880.0, where
    ``0.06 * 44100`` would give 2646.0000000000005). A step under one sample (a sample rate under 16.7 Hz, which the analyzer refuses anyway) is raised to one sample, the least that
    ``note_analysis.analyze_channels()`` accepts.

    Returns:
        The step in samples, at least 1.0, a float that need not be a whole number.
    """
    return max(1.0, sample_rate * BUFFER_INTERVAL_MS / 1000)
