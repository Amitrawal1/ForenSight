import pytest

from app.pipeline import runner
from app.pipeline.detectors.base import Detector
from app.pipeline.models.registry import ModelNotAvailable, model_path
from tests.helpers import jpeg_bytes, photo_like


class MissingModelDetector(Detector):
    name = "missing"
    label = "Missing model"
    media_types = ("image",)

    def run(self, ctx):
        raise ModelNotAvailable("model file 'x.pt' is missing")


def test_missing_model_is_skipped_with_note(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "DETECTORS", [MissingModelDetector()])
    img = tmp_path / "a.jpg"
    img.write_bytes(jpeg_bytes(photo_like()))

    out = runner.analyse(img, "image", "image/jpeg", tmp_path / "out")

    assert out.verdict == "inconclusive"
    assert any("skipped" in n for n in out.notes)


def test_model_path_raises_when_missing():
    with pytest.raises(ModelNotAvailable):
        model_path("does-not-exist.onnx")
