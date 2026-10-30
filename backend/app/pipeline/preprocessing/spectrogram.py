"""Draw a spectrogram: a picture of the sound, with time left to right and pitch bottom to top.

A short piece of sound is turned into its pitches with an FFT (a sum that splits a sound
into its frequencies). Doing that along the clip is called an STFT (short-time FFT).
We make one column per output pixel, so memory stays small even for a 5-minute file.
"""

from pathlib import Path

import cv2
import numpy as np

SPECTROGRAM_NAME = "spectrogram.png"
WIDTH = 1200
HEIGHT = 300
WINDOW = 512  # 32 ms of sound at 16 kHz
RANGE_DB = 80.0  # sounds this much quieter than the loudest part are drawn black
QUIET_FLOOR_DB = -40.0  # stops a silent file from being stretched to full brightness


def save_spectrogram(audio: np.ndarray, path: Path, width: int = WIDTH, height: int = HEIGHT) -> None:
    """Save a picture of `audio` (16 kHz mono float32). Raises an error if that fails."""
    # Pad very short sounds so that there is at least one full window
    samples = np.pad(audio, (0, max(0, WINDOW - len(audio)))).astype(np.float32)
    starts = np.linspace(0, len(samples) - WINDOW, width).astype(np.int64)
    windows = samples[starts[:, None] + np.arange(WINDOW)] * np.hanning(WINDOW).astype(np.float32)

    # Sound strength in decibels (dB, a scale for loudness): one row per column of the picture
    power = np.abs(np.fft.rfft(windows, axis=1)) ** 2
    db = 10 * np.log10(power + 1e-10)
    top = max(float(db.max()), QUIET_FLOOR_DB)
    levels = np.clip((db - (top - RANGE_DB)) / RANGE_DB, 0, 1)

    # Rows become pitch; flip them because row 0 is the top of an image and low pitch goes at the bottom
    picture = (levels.T[::-1] * 255).astype(np.uint8)
    picture = cv2.resize(picture, (width, height), interpolation=cv2.INTER_LINEAR)
    if not cv2.imwrite(str(path), cv2.applyColorMap(picture, cv2.COLORMAP_INFERNO)):
        raise OSError(f"could not write {path}")
