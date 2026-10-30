"""Live progress and the extra evidence for the result page (frames, spectrogram, sizes)."""

import cv2
import numpy as np
import pytest
import redis
from fastapi.testclient import TestClient
from PIL import Image

from app.api.routes.analysis import ARTIFACT_NAME
from app.db.models import Status
from app.main import app
from app.pipeline import runner
from app.pipeline.detectors.audio import voice_clone
from app.pipeline.detectors.base import Detector, DetectorResult, MediaContext
from app.pipeline.detectors.video import ai_frames, faces
from app.pipeline.preprocessing.audio import SAMPLE_RATE, ffmpeg_exe
from app.pipeline.preprocessing.spectrogram import save_spectrogram
from app.pipeline.preprocessing.video import Frame
from app.services import progress
from app.services.storage import artifact_dir
from tests.helpers import jpeg_bytes, photo_like, wav_bytes
from tests.test_tasks import add_analysis

needs_ffmpeg = pytest.mark.skipif(ffmpeg_exe() is None, reason="ffmpeg not installed")


class FakeRedis:
    """Keeps values in a dict, so these tests don't need a real Redis."""

    def __init__(self):
        self.data = {}

    def set(self, key, value, ex=None):
        self.data[key] = value
        self.ttl = ex

    def get(self, key):
        return self.data.get(key)

    def delete(self, key):
        self.data.pop(key, None)


class StubDetector(Detector):
    """Reports items like a real detector, including one number that goes backward."""

    name = "stub"
    label = "Stub"
    media_types = ("image", "video", "audio")

    def run(self, ctx):
        for done in (0, 2, 1, 3):
            ctx.report(done, 4, f"item {done}")
        return DetectorResult(self.name, fake_score=0.1, reliability=0.5)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def no_redis(monkeypatch):
    # Nothing listens on port 1, so every Redis call fails
    dead = redis.Redis.from_url("redis://127.0.0.1:1/0", socket_connect_timeout=0.1, socket_timeout=0.1)
    monkeypatch.setattr(progress, "_client", lambda: dead)


def test_progress_store_round_trip(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(progress, "_client", lambda: fake)
    progress.set_progress("a", 150, "Working")
    assert progress.get_progress("a") == {"percent": 100, "step": "Working"}
    assert fake.ttl == progress.TTL_S
    progress.clear_progress("a")
    assert progress.get_progress("a") is None


def test_progress_store_survives_no_redis(no_redis):
    progress.set_progress("a", 10, "Working")
    assert progress.get_progress("a") is None
    progress.clear_progress("a")


def test_analysis_finishes_without_redis(client, no_redis, monkeypatch):
    monkeypatch.setattr(runner, "DETECTORS", [])
    r = client.post("/api/analyses", files={"file": ("a.jpg", jpeg_bytes(photo_like()))})
    assert r.json()["status"] == "done"
    assert client.get(f"/api/analyses/{r.json()['id']}").json()["progress"] is None


def test_api_shows_progress_only_while_running(client, monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(progress, "_client", lambda: fake)
    running, finished = add_analysis(Status.processing), add_analysis(Status.done)
    progress.set_progress(running, 40, "Checking faces: frame 5 of 12")
    progress.set_progress(finished, 40, "old")

    assert client.get(f"/api/analyses/{running}").json()["progress"] == {
        "percent": 40, "step": "Checking faces: frame 5 of 12"}
    assert client.get(f"/api/analyses/{finished}").json()["progress"] is None
    assert "progress" not in client.get("/api/analyses").json()[0]


def test_percent_never_goes_backward_and_callback_errors_are_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "DETECTORS", [StubDetector(), StubDetector()])
    img = tmp_path / "a.jpg"
    img.write_bytes(jpeg_bytes(photo_like()))
    seen = []

    def on_progress(percent, step):
        seen.append((percent, step))
        raise RuntimeError("progress store is broken")

    out = runner.analyse(img, "image", "image/jpeg", tmp_path / "out", on_progress=on_progress)

    percents = [p for p, _ in seen]
    assert percents == sorted(percents)
    assert percents[0] == 0 and seen[-1] == (runner.CHECKS_END, "Writing the verdict")
    assert len(out.detectors) == 2
    assert (out.media["width"], out.media["height"]) == (256, 256)


def frame_context(tmp_path, count=3):
    frames = [Frame(float(i), photo_like(64, seed=i)) for i in range(count)]
    return MediaContext(path=tmp_path, media_type="video", mime="video/mp4", out_dir=tmp_path, frames=frames)


def test_face_check_reports_each_frame(tmp_path, monkeypatch):
    monkeypatch.setattr(faces, "check_faces", lambda rgb, with_heatmap: [])
    ctx = frame_context(tmp_path)
    seen = []
    ctx.on_item = lambda done, total, step: seen.append((done, total, step))
    assert faces.VideoFaceSwapDetector().run(ctx) is None
    assert seen == [(i, 4, f"Checking faces: frame {i + 1} of 3") for i in range(3)]


def test_ai_frames_check_reports_each_frame_and_keeps_its_score(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_frames, "fake_probability", lambda img: 0.25)
    ctx = frame_context(tmp_path)
    seen = []
    ctx.on_item = lambda done, total, step: seen.append((done, total, step))
    assert ai_frames.VideoAiFramesDetector().run(ctx).fake_score == pytest.approx(0.25)
    assert seen[1] == (1, 3, "Checking frames for AI: frame 2 of 3")


def test_voice_check_reports_each_part(tmp_path, monkeypatch):
    monkeypatch.setattr(voice_clone, "fake_probability", lambda samples: 0.25)
    audio = 0.3 * np.sin(np.arange(10 * SAMPLE_RATE, dtype=np.float32) / 10)
    ctx = MediaContext(path=tmp_path, media_type="audio", mime="audio/x-wav", out_dir=tmp_path, audio=audio)
    seen = []
    ctx.on_item = lambda done, total, step: seen.append((done, total, step))
    assert voice_clone.VoiceCloneDetector().run(ctx).fake_score == pytest.approx(0.25)
    total = seen[0][1]
    assert seen[-1] == (total - 1, total, f"Listening for AI voice: part {total} of {total}")


def test_spectrogram_has_right_size_and_direction(tmp_path):
    # Silence, then a low tone: the bright part must be on the right and near the bottom
    t = np.arange(2 * SAMPLE_RATE, dtype=np.float32) / SAMPLE_RATE
    audio = np.concatenate([np.zeros_like(t), 0.5 * np.sin(2 * np.pi * 300 * t)])
    path = tmp_path / "spectrogram.png"
    save_spectrogram(audio, path)

    picture = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE).astype(float)
    assert picture.shape == (300, 1200)
    assert picture[:, 600:].mean() > picture[:, :500].mean() + 1
    assert picture[-30:, 700:].mean() > picture[:30, 700:].mean() + 1


@pytest.mark.parametrize("audio", [np.zeros(16_000, np.float32), np.ones(10, np.float32) * 0.1])
def test_spectrogram_handles_silent_and_very_short_sound(tmp_path, audio):
    path = tmp_path / "spectrogram.png"
    save_spectrogram(audio, path)
    assert cv2.imread(str(path)).shape == (300, 1200, 3)


def test_broken_spectrogram_only_skips_it(tmp_path, monkeypatch):
    def broken(*_):
        raise RuntimeError("no")

    monkeypatch.setattr(runner, "DETECTORS", [])
    monkeypatch.setattr(runner, "save_spectrogram", broken)
    wav = tmp_path / "a.wav"
    wav.write_bytes(wav_bytes(seconds=1.0))
    out = runner.analyse(wav, "audio", "audio/x-wav", tmp_path / "out")
    assert "spectrogram" not in out.media and "peaks" in out.media


@needs_ffmpeg
def test_video_evidence_is_served_and_deleted(client, tmp_path, monkeypatch):
    from tests.test_video import make_video

    monkeypatch.setattr(runner, "DETECTORS", [])
    data = make_video(tmp_path / "v.mp4", 3.0).read_bytes()
    body = client.post("/api/analyses", files={"file": ("clip.mp4", data)}).json()
    aid, media = body["id"], body["evidence"]["media"]

    assert (media["width"], media["height"]) == (320, 320)
    assert [f["file"] for f in media["frames"]] == ["frame_00.jpg", "frame_01.jpg", "frame_02.jpg"]
    assert media["frames"][1]["time_s"] == pytest.approx(1.5)
    assert media["spectrogram"] == "spectrogram.png"
    for name in ("frame_00.jpg", "spectrogram.png"):
        assert ARTIFACT_NAME.match(name)
        assert client.get(f"/api/analyses/{aid}/artifacts/{name}").status_code == 200
    with Image.open(artifact_dir(aid) / "frame_00.jpg") as img:
        assert img.width <= 320

    assert client.delete(f"/api/analyses/{aid}").status_code == 204
    assert not artifact_dir(aid).exists()


def test_wide_frame_preview_is_shrunk(tmp_path):
    from app.pipeline.preprocessing.video import save_frame_previews

    frames = [Frame(0.5, np.zeros((360, 640, 3), np.uint8))]
    assert save_frame_previews(frames, tmp_path) == [{"file": "frame_00.jpg", "time_s": 0.5}]
    with Image.open(tmp_path / "frame_00.jpg") as img:
        assert img.size == (320, 180)
