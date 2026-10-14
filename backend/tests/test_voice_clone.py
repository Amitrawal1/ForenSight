import numpy as np
import pytest

from app.core.config import get_settings
from app.pipeline.detectors.audio.voice_clone import (
    INPUT_SAMPLES, MODEL_FILE, VoiceCloneDetector, longest_fake_run, merge_fake_parts, repeat_to_length,
)
from app.pipeline.detectors.base import MediaContext, Segment
from app.pipeline.preprocessing.audio import SAMPLE_RATE


def _ready() -> bool:
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return False
    return (get_settings().models_dir / MODEL_FILE).is_file()


# Needs onnxruntime (INSTALL_ML=true) and the model (backend/scripts/download_models.py)
needs_model = pytest.mark.skipif(not _ready(), reason="onnxruntime or AI-voice model not installed")


def test_short_audio_is_repeated_to_model_length():
    out = repeat_to_length(np.arange(10, dtype=np.float32))
    assert len(out) == INPUT_SAMPLES
    assert out[10] == 0 and out[25] == 5  # starts again from the beginning


def test_long_audio_is_cut_to_model_length():
    assert len(repeat_to_length(np.zeros(INPUT_SAMPLES * 2, np.float32))) == INPUT_SAMPLES


def test_overlapping_fake_windows_merge_into_one_part():
    segs = [Segment(0, 4, 0.1), Segment(2, 6, 0.9), Segment(4, 8, 0.8), Segment(10, 14, 0.95)]
    assert merge_fake_parts(segs) == [(2, 8), (10, 14)]


def test_no_audio_means_check_does_not_apply(tmp_path):
    assert VoiceCloneDetector().run(MediaContext(tmp_path / "x", "audio", "audio/x-wav", tmp_path)) is None


@needs_model
def test_scores_every_window_of_speech_like_audio(tmp_path):
    t = np.arange(10 * SAMPLE_RATE) / SAMPLE_RATE
    audio = (0.2 * np.sin(2 * np.pi * 150 * t) * (np.sin(2 * np.pi * 2 * t) > 0)).astype(np.float32)
    res = VoiceCloneDetector().run(MediaContext(tmp_path / "x", "audio", "audio/x-wav", tmp_path, audio=audio))
    assert res is not None and len(res.segments) >= 3
    assert all(0.0 <= s.score <= 1.0 for s in res.segments)


@needs_model
def test_silence_is_not_judged(tmp_path):
    audio = np.zeros(8 * SAMPLE_RATE, np.float32)
    assert VoiceCloneDetector().run(MediaContext(tmp_path / "x", "audio", "audio/x-wav", tmp_path, audio=audio)) is None


def test_phone_quality_detection():
    from app.pipeline.detectors.audio.voice_clone import is_phone_quality

    t = np.arange(4 * SAMPLE_RATE) / SAMPLE_RATE
    low_only = np.sin(2 * np.pi * 300 * t).astype(np.float32)  # all sound below 4 kHz
    rng = np.random.default_rng(0)
    full_band = rng.standard_normal(len(t)).astype(np.float32)  # sound at all pitches
    assert is_phone_quality(low_only)
    assert not is_phone_quality(full_band)


@needs_model
def test_compressed_audio_gets_low_trust(tmp_path):
    from app.pipeline.detectors.audio.voice_clone import LOW_RELIABILITY

    rng = np.random.default_rng(0)
    audio = (0.1 * rng.standard_normal(12 * SAMPLE_RATE)).astype(np.float32)
    res = VoiceCloneDetector().run(MediaContext(tmp_path / "x", "audio", "audio/mpeg", tmp_path, audio=audio))
    assert res.reliability == LOW_RELIABILITY
    assert "compressed" in res.reasons[-1]


def test_longest_fake_run():
    scores = [0.9, 0.1, 0.8, 0.9, 1.0, 0.2, 0.7]
    segs = [Segment(i * 2, i * 2 + 4, sc) for i, sc in enumerate(scores)]
    assert longest_fake_run(segs) == [0.8, 0.9, 1.0]
