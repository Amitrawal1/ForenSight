"""Load audio from any audio or video file and cut it into short windows.

We use ffmpeg (installed in the Docker image) to decode MP3, M4A, WAV and the sound
track of videos into one simple format: 16,000 samples per second, mono.
Most speech models expect exactly this.
"""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16_000
MAX_SECONDS = 300  # only analyse the first 5 minutes, to keep it fast
WINDOW_S = 4.0  # each window is 4 seconds long...
HOP_S = 2.0  # ...and a new window starts every 2 seconds (they overlap)
MIN_LAST_WINDOW_S = 1.0  # a shorter piece at the end is too short to judge


class AudioDecodeError(Exception):
    """The file has no sound track, or ffmpeg could not read it."""


@dataclass
class Window:
    start_s: float
    end_s: float
    samples: np.ndarray  # float32 values between -1 and 1


def ffmpeg_exe() -> str | None:
    """Path to ffmpeg: the system one (Docker), or the pip package imageio-ffmpeg (local dev)."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def load_audio(path: Path) -> np.ndarray:
    """Decode a file to 16 kHz mono float32 samples."""
    exe = ffmpeg_exe()
    if exe is None:
        raise AudioDecodeError("ffmpeg is not installed")

    cmd = [
        exe, "-nostdin", "-v", "error",
        "-i", str(path),
        "-t", str(MAX_SECONDS),  # stop after 5 minutes
        "-vn",  # ignore any video
        "-ac", "1",  # mono
        "-ar", str(SAMPLE_RATE),  # 16 kHz
        "-f", "f32le", "-",  # raw float32 numbers to stdout
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120, check=False)
    except subprocess.TimeoutExpired:
        raise AudioDecodeError("decoding the audio took too long")

    audio = np.frombuffer(result.stdout, dtype=np.float32)
    if result.returncode != 0 or audio.size == 0:
        detail = result.stderr.decode("utf-8", "ignore").strip().splitlines()[-1:] or ["no audio found"]
        raise AudioDecodeError(f"could not read audio ({detail[0][:120]})")
    return audio.copy()


def split_windows(audio: np.ndarray) -> list[Window]:
    """Cut audio into overlapping 4-second windows so each part gets its own score."""
    win, hop = int(WINDOW_S * SAMPLE_RATE), int(HOP_S * SAMPLE_RATE)
    total = len(audio)
    if total < MIN_LAST_WINDOW_S * SAMPLE_RATE:
        return []
    if total <= win:
        return [Window(0.0, total / SAMPLE_RATE, audio)]

    starts = list(range(0, total - win + 1, hop))
    # Make sure the end of the clip is covered too
    if total - (starts[-1] + win) >= MIN_LAST_WINDOW_S * SAMPLE_RATE:
        starts.append(total - win)
    return [Window(s / SAMPLE_RATE, (s + win) / SAMPLE_RATE, audio[s : s + win]) for s in starts]


def is_silent(samples: np.ndarray, threshold_db: float = -45.0) -> bool:
    """True if a piece of audio is too quiet to contain speech."""
    rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2))) + 1e-12
    return 20 * np.log10(rms) < threshold_db


def waveform_peaks(audio: np.ndarray, points: int = 400) -> list[float]:
    """Loudest value in each of `points` slices: enough to draw the waveform on the page."""
    if audio.size == 0:
        return []
    chunks = np.array_split(np.abs(audio), min(points, audio.size))
    peaks = np.array([c.max() for c in chunks], dtype=np.float32)
    peaks /= max(float(peaks.max()), 1e-6)
    return [round(float(p), 3) for p in peaks]
