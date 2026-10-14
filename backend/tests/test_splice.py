import numpy as np

from app.pipeline.detectors.audio.splice import SpliceDetector, background_changes
from app.pipeline.detectors.base import MediaContext
from app.pipeline.preprocessing.audio import SAMPLE_RATE

rng = np.random.default_rng(0)


def speech_like(seconds: float = 14.0) -> np.ndarray:
    """Fake 'speech': short voiced bursts (a few harmonics) with small pauses between them."""
    out = np.zeros(int(seconds * SAMPLE_RATE), dtype=np.float32)
    t = 0.0
    while t < seconds - 0.5:
        burst = rng.uniform(0.2, 0.5)
        n = int(burst * SAMPLE_RATE)
        tt = np.arange(n) / SAMPLE_RATE
        f0 = rng.uniform(110, 220)
        tone = sum(np.sin(2 * np.pi * f0 * k * tt) / k for k in range(1, 6))
        start = int(t * SAMPLE_RATE)
        out[start : start + n] += (0.2 * tone * np.hanning(n)).astype(np.float32)
        t += burst + rng.uniform(0.15, 0.35)  # pause
    return out


def noise(n: int, level_db: float, rumble: bool = False) -> np.ndarray:
    w = rng.standard_normal(n)
    if rumble:  # low-frequency hum, like a street or a fan
        w = np.cumsum(w)
        w -= np.convolve(w, np.ones(400) / 400, "same")
    w /= np.sqrt(np.mean(w**2))
    return (w * 10 ** (level_db / 20)).astype(np.float32)


def test_finds_join_between_two_backgrounds():
    a = speech_like()
    half = len(a) // 2
    a[:half] += noise(half, -45)
    a[half:] += noise(len(a) - half, -35, rumble=True)
    joins = background_changes(a)
    assert len(joins) == 1
    assert abs(joins[0][0] - half / SAMPLE_RATE) <= 1.0


def test_same_background_has_no_join():
    a = speech_like() + noise(int(14 * SAMPLE_RATE), -45)
    assert background_changes(a) == []


def test_louder_speaker_is_not_a_join():
    a = speech_like() + noise(int(14 * SAMPLE_RATE), -45)
    a[len(a) // 2 :] *= 2.0
    assert background_changes(a) == []


def test_detector_gives_timeline_segment(tmp_path):
    a = speech_like()
    half = len(a) // 2
    a[:half] += noise(half, -45)
    a[half:] += noise(len(a) - half, -35, rumble=True)
    ctx = MediaContext(tmp_path / "x.wav", "audio", "audio/x-wav", tmp_path, audio=a)
    res = SpliceDetector().run(ctx)
    assert res.fake_score > 0.5 and len(res.segments) == 1
    assert "joined" in res.reasons[0]


def test_short_audio_is_skipped(tmp_path):
    ctx = MediaContext(tmp_path / "x.wav", "audio", "audio/x-wav", tmp_path, audio=speech_like(5.0))
    assert SpliceDetector().run(ctx) is None
