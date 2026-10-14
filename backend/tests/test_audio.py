import numpy as np
import pytest

from app.pipeline.preprocessing.audio import (
    SAMPLE_RATE, AudioDecodeError, ffmpeg_exe, is_silent, load_audio, split_windows, waveform_peaks,
)
from tests.helpers import wav_bytes

needs_ffmpeg = pytest.mark.skipif(ffmpeg_exe() is None, reason="ffmpeg not installed")


def seconds(s: float) -> np.ndarray:
    return np.zeros(int(s * SAMPLE_RATE), dtype=np.float32)


def test_windows_overlap_and_cover_the_end():
    wins = split_windows(seconds(9))
    assert [(w.start_s, w.end_s) for w in wins] == [(0, 4), (2, 6), (4, 8), (5, 9)]
    assert all(len(w.samples) == 4 * SAMPLE_RATE for w in wins)


def test_short_clip_is_one_window_and_tiny_clip_none():
    assert len(split_windows(seconds(2.5))) == 1
    assert split_windows(seconds(0.5)) == []


def test_silence_detection():
    assert is_silent(seconds(1))
    assert not is_silent(0.3 * np.sin(np.linspace(0, 1000, SAMPLE_RATE)).astype(np.float32))


def test_waveform_peaks_are_normalised():
    peaks = waveform_peaks(np.linspace(-0.5, 0.5, 10_000, dtype=np.float32), points=50)
    assert len(peaks) == 50 and max(peaks) == 1.0


@needs_ffmpeg
def test_load_wav_resamples_to_16k_mono(tmp_path):
    p = tmp_path / "a.wav"
    p.write_bytes(wav_bytes(seconds=2.0, sr=44100))
    audio = load_audio(p)
    assert audio.dtype == np.float32
    assert abs(len(audio) / SAMPLE_RATE - 2.0) < 0.05


@needs_ffmpeg
def test_broken_file_raises_clear_error(tmp_path):
    p = tmp_path / "broken.wav"
    p.write_bytes(b"RIFF\x00\x00\x00\x00WAVEgarbage")
    with pytest.raises(AudioDecodeError):
        load_audio(p)
