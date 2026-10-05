"""Reduce stereo audio to 88 musical-note values per analysis window.

For each window the left and right channels are transformed with a real FFT and
their magnitude spectra are averaged. Each of 88 notes (55 Hz, rising one
semitone at a time) then reads the spectrum at position
``int((window_size / sample_rate) * note_frequency)``.
"""

import math
import numbers
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import wavfile

NOTE_COUNT = 88
BASE_FREQUENCY = 55.0

# Upper bound on samples held as float64 per channel while transforming a file.
_CHUNK_SAMPLES = 1 << 22


class AudioAnalysisError(ValueError):
    """Invalid audio or analysis parameters."""


def note_frequencies() -> np.ndarray:
    """Frequencies in Hz of the 88 notes, starting at 55 Hz, one semitone apart."""
    return BASE_FREQUENCY * 2.0 ** (np.arange(NOTE_COUNT) / 12)


class NoteBinAnalyzer:
    """Turns one window of left/right audio into 88 note values."""

    def __init__(self, sample_rate: float, window_size: int):
        if (
            isinstance(sample_rate, bool)
            or not isinstance(sample_rate, numbers.Real)
            or not math.isfinite(sample_rate)
            or sample_rate <= 0
        ):
            raise AudioAnalysisError(f"The sample rate must be a number greater than 0 (got {sample_rate!r}).")
        if isinstance(window_size, bool) or not isinstance(window_size, numbers.Integral) or window_size < 1:
            raise AudioAnalysisError(f"The window size must be a whole number of samples, at least 1 (got {window_size!r}).")

        self.sample_rate = sample_rate
        self.window_size = int(window_size)
        self.frequencies = note_frequencies()
        self.bin_indices = np.array(
            [int((self.window_size / sample_rate) * f) for f in self.frequencies], dtype=np.intp
        )

        last_usable = self.window_size // 2
        too_high = np.flatnonzero(self.bin_indices > last_usable)
        if too_high.size:
            n = int(too_high[0])
            min_rate = math.ceil(2 * self.frequencies[-1])
            raise AudioAnalysisError(
                f"The sample rate {sample_rate} is too low for a window size of {self.window_size}: "
                f"note {n} ({self.frequencies[n]:.1f} Hz) falls beyond the spectrum. "
                f"Use a sample rate of at least {min_rate} Hz."
            )

    def analyze(self, left, right) -> np.ndarray:
        """Return the 88 note values (lowest note first) for one window of audio."""
        try:
            left = np.asarray(left, dtype=np.float64)
            right = np.asarray(right, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise AudioAnalysisError(f"Audio buffers must be numeric: {exc}") from exc
        if left.ndim != 1 or right.ndim != 1:
            raise AudioAnalysisError("Audio buffers must be 1-D (one channel each).")
        if left.shape != right.shape:
            raise AudioAnalysisError(
                f"The left and right buffers must have the same length ({left.size} vs {right.size})."
            )
        if left.size > self.window_size:
            raise AudioAnalysisError(
                f"The buffers ({left.size} samples) are longer than the window size ({self.window_size})."
            )
        return self._note_values(left, right)

    def _note_values(self, left: np.ndarray, right: np.ndarray) -> np.ndarray:
        """Note values for buffers of shape (..., n), zero-padded to the window size on the last axis."""
        left_mag = np.abs(np.fft.rfft(left, n=self.window_size, axis=-1))
        right_mag = np.abs(np.fft.rfft(right, n=self.window_size, axis=-1))
        return ((left_mag + right_mag) / 2)[..., self.bin_indices]


@dataclass(frozen=True)
class AnalysisResult:
    """Note values for every window of a file, in time order."""

    sample_rate: float
    window_size: int
    frames: np.ndarray  # shape (window_count, 88)
    sample_count: int = 0  # samples per channel in the analyzed audio
    starts: np.ndarray | None = None  # start sample of each window; default: consecutive windows
    step: float | None = None  # exact distance in samples between window starts, if known

    @property
    def window_count(self) -> int:
        return self.frames.shape[0]

    @property
    def window_starts(self) -> np.ndarray:
        """Start sample of each window (rounded to whole samples)."""
        if self.starts is not None:
            return self.starts
        return np.arange(self.window_count) * self.window_size

    @property
    def window_positions(self) -> np.ndarray:
        """Exact start position of each window in samples (``k * step``), used to assign windows to frames."""
        if self.step is not None:
            return np.arange(self.window_count) * self.step
        return self.window_starts.astype(np.float64)

    def window_start_times(self) -> np.ndarray:
        """Start time in seconds of each window."""
        return self.window_starts / self.sample_rate


def window_count(sample_count: int, step: float) -> int:
    """Number of windows: how many ``rint(k * step)`` fall before ``sample_count``. No arrays are built."""
    if sample_count <= 0:
        return 0
    n = max(1, math.ceil((sample_count - 0.5) / step - 1e-9))
    while n > 1 and round((n - 1) * step) >= sample_count:
        n -= 1
    while round(n * step) < sample_count:
        n += 1
    return n


def window_starts(sample_count: int, step: float) -> np.ndarray:
    """Start sample of each window: the nearest whole sample to ``k * step``, counted from sample 0."""
    return np.rint(np.arange(window_count(sample_count, step)) * step).astype(np.int64)


def _to_float(samples: np.ndarray) -> np.ndarray:
    """Scale PCM samples to float64 in about [-1, 1] so bit depth does not matter."""
    if samples.dtype == np.uint8:
        return (samples.astype(np.float64) - 128.0) / 128.0
    if np.issubdtype(samples.dtype, np.integer):
        return samples.astype(np.float64) / (float(np.iinfo(samples.dtype).max) + 1.0)
    return samples.astype(np.float64)


def read_wav(path, display_name: str | None = None) -> tuple[int, np.ndarray, np.ndarray]:
    """Read a mono or stereo WAV file. Returns (file sample rate, left, right) as raw PCM arrays.

    ``display_name`` is the file name used in error messages (default: the name in ``path``).
    """
    name = display_name or Path(path).name
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", wavfile.WavFileWarning)
            file_rate, data = wavfile.read(str(path))
    except (OSError, ValueError, EOFError) as exc:
        raise AudioAnalysisError(f"Could not read {name!r} as a WAV file: {exc}") from exc

    if data.ndim == 1:
        return file_rate, data, data
    channels = data.shape[1]
    if channels == 1:
        return file_rate, data[:, 0], data[:, 0]
    if channels == 2:
        return file_rate, data[:, 0], data[:, 1]
    raise AudioAnalysisError(
        f"{name!r} has {channels} channels; only mono and stereo files are supported."
    )


def analyze_wav(path, sample_rate: float, window_size: int) -> AnalysisResult:
    """Analyze a WAV file in consecutive, non-overlapping windows.

    The final partial window is zero-padded. ``sample_rate`` is the value used
    for the note mapping; a warning is issued if it differs from the file's own.
    """
    NoteBinAnalyzer(sample_rate, window_size)  # parameter errors first

    file_rate, left, right = read_wav(path)
    if file_rate != sample_rate:
        warnings.warn(
            f"The supplied sample rate ({sample_rate}) differs from the file's sample rate ({file_rate}); "
            "using the supplied value.",
            UserWarning,
            stacklevel=2,
        )
    return analyze_channels(left, right, sample_rate, window_size)


def analyze_channels(
    left: np.ndarray, right: np.ndarray, sample_rate: float, window_size: int, step: float | None = None
) -> AnalysisResult:
    """Analyze already-read PCM channels in windows ``step`` samples apart (see analyze_wav).

    ``step`` defaults to the window size: consecutive, non-overlapping windows. A smaller step
    overlaps the windows and a larger one leaves gaps between them. It must be at least 1 sample.
    """
    analyzer = NoteBinAnalyzer(sample_rate, window_size)
    window = analyzer.window_size
    step = float(window if step is None else step)
    if not math.isfinite(step) or step < 1:
        raise AudioAnalysisError(f"The step between windows must be at least 1 sample (got {step!r}).")

    total = left.shape[0]
    starts = window_starts(total, step)
    frames = np.empty((starts.size, NOTE_COUNT), dtype=np.float64)

    windows_per_chunk = max(1, _CHUNK_SAMPLES // max(window, math.ceil(step)))
    offsets = np.arange(window)
    for first in range(0, starts.size, windows_per_chunk):
        last = min(first + windows_per_chunk, starts.size)
        seg_start = int(starts[first])
        seg_stop = int(starts[last - 1]) + window
        index = (starts[first:last] - seg_start)[:, None] + offsets[None, :]
        gathered = []
        for channel in (left, right):
            segment = np.zeros(seg_stop - seg_start, dtype=np.float64)
            available = channel[seg_start : min(seg_stop, total)]
            segment[: available.shape[0]] = _to_float(available)
            gathered.append(segment[index])
        frames[first:last] = analyzer._note_values(*gathered)

    return AnalysisResult(
        sample_rate=sample_rate, window_size=window, frames=frames, sample_count=total, starts=starts, step=step
    )
