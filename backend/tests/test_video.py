import subprocess
from pathlib import Path

import numpy as np
import pytest

from app.pipeline.detectors.video.faces import video_score
from app.pipeline.preprocessing.audio import ffmpeg_exe
from app.pipeline.preprocessing.video import MAX_FRAMES, VideoDecodeError, sample_frames

FIXTURES = Path(__file__).parent / "fixtures"
needs_ffmpeg = pytest.mark.skipif(ffmpeg_exe() is None, reason="ffmpeg not installed")


def make_video(path: Path, seconds: float, with_sound: bool = True) -> Path:
    """A short MP4 of the face photo slowly zooming, optionally with a tone as sound."""
    cmd = [ffmpeg_exe(), "-v", "error", "-y", "-loop", "1", "-i", str(FIXTURES / "face.jpg")]
    if with_sound:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=220:duration={seconds}"]
    cmd += ["-vf", "scale=320:320,format=yuv420p", "-t", str(seconds), "-c:v", "libx264", "-r", "10"]
    cmd += ["-c:a", "aac", "-shortest"] if with_sound else []
    subprocess.run(cmd + [str(path)], check=True)
    return path


def test_video_score_follows_dfdc_strategy():
    assert video_score([0.9] * 6 + [0.1] * 4) == pytest.approx(0.9)  # many clearly fake frames
    assert video_score([0.05] * 10) == pytest.approx(0.05)  # all clearly real
    assert video_score([0.9, 0.1, 0.5, 0.3]) == pytest.approx(0.45)  # mixed: plain average


@needs_ffmpeg
def test_frames_are_spread_over_the_video(tmp_path):
    frames, duration = sample_frames(make_video(tmp_path / "v.mp4", 6.0), tmp_path / "frames")
    assert abs(duration - 6.0) < 0.2
    assert len(frames) == 6  # 1 frame per second for short videos
    assert frames[0].rgb.shape == (320, 320, 3)
    assert not list((tmp_path / "frames").glob("*.jpg"))  # temporary files cleaned up


@needs_ffmpeg
def test_long_video_is_capped(tmp_path):
    frames, _ = sample_frames(make_video(tmp_path / "v.mp4", 40.0, with_sound=False), tmp_path / "frames")
    assert len(frames) <= MAX_FRAMES


@needs_ffmpeg
def test_audio_file_is_not_a_video(tmp_path):
    from tests.helpers import wav_bytes

    p = tmp_path / "a.wav"
    p.write_bytes(wav_bytes())
    with pytest.raises(VideoDecodeError):
        sample_frames(p, tmp_path / "frames")


@needs_ffmpeg
def test_video_pipeline_runs_and_notes_missing_sound(tmp_path):
    from app.pipeline.runner import analyse

    out = analyse(make_video(tmp_path / "v.mp4", 4.0, with_sound=False), "video", "video/mp4", tmp_path / "out")
    assert out.thumbnail == "thumb.jpg" and (tmp_path / "out" / "thumb.jpg").is_file()
    assert abs(out.media["duration_s"] - 4.0) < 0.2
    assert any("no readable sound track" in n for n in out.notes)
    assert out.verdict in {"likely_authentic", "inconclusive", "manipulated", "ai_generated"}
    assert not np.isnan(out.confidence)
