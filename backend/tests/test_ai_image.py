from pathlib import Path

import pytest
from PIL import Image

from app.core.config import get_settings
from app.pipeline.detectors.image.ai_image import CROP, MODEL_DIR, prepare

FIXTURES = Path(__file__).parent / "fixtures"


def _model_ready() -> bool:
    try:
        import torch  # noqa: F401
    except ImportError:
        return False
    return (get_settings().models_dir / MODEL_DIR / "model.safetensors").is_file()


# Needs PyTorch (INSTALL_ML=true) and the model (backend/scripts/download_models.py)
needs_model = pytest.mark.skipif(not _model_ready(), reason="PyTorch or AI-image model not installed")


def test_prepare_shape_for_any_image_size():
    for size in [(1000, 300), (300, 1000), (100, 100)]:
        assert prepare(Image.new("RGB", size)).shape == (1, 3, CROP, CROP)


@needs_model
def test_real_photo_scores_low():
    from app.pipeline.detectors.image.ai_image import fake_probability

    assert fake_probability(Image.open(FIXTURES / "face.jpg")) < 0.35


@needs_model
def test_stable_diffusion_image_scores_high():
    from app.pipeline.detectors.image.ai_image import fake_probability

    assert fake_probability(Image.open(FIXTURES / "ai_sd.jpg")) > 0.65


@needs_model
def test_full_pipeline_verdicts():
    from app.pipeline.runner import analyse

    real = analyse(FIXTURES / "face.jpg", "image", "image/jpeg", Path(get_settings().artifact_dir) / "t1")
    fake = analyse(FIXTURES / "ai_sd.jpg", "image", "image/jpeg", Path(get_settings().artifact_dir) / "t2")
    assert real.verdict == "likely_authentic"
    assert fake.verdict == "ai_generated"
