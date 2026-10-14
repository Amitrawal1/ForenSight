from pathlib import Path

import numpy as np
import pytest

from app.core.config import get_settings
from app.pipeline.detectors.base import MediaContext
from app.pipeline.detectors.image.face_swap import INPUT_SIZE, MODEL_FILE, face_box, prepare
from app.pipeline.preprocessing.faces import YUNET_FILE, Face

FIXTURES = Path(__file__).parent / "fixtures"


def _ready() -> bool:
    try:
        import timm  # noqa: F401
        import torch  # noqa: F401
    except ImportError:
        return False
    models = get_settings().models_dir
    return (models / MODEL_FILE).is_file() and (models / YUNET_FILE).is_file()


# Needs PyTorch + timm (INSTALL_ML=true) and the models (backend/scripts/download_models.py)
needs_model = pytest.mark.skipif(not _ready(), reason="PyTorch or face models not installed")


def test_face_box_adds_a_third_on_each_side_and_stays_inside_image():
    rgb = np.zeros((300, 300, 3), np.uint8)
    assert face_box(rgb, Face(x=90, y=90, w=60, h=90, score=1.0)) == (70, 60, 170, 210)
    # Face at the corner: box is cut at the image border
    assert face_box(rgb, Face(x=0, y=0, w=60, h=60, score=1.0)) == (0, 0, 80, 80)


def test_prepare_keeps_shape_and_centres_face():
    x, (left, top, w, h) = prepare(np.zeros((200, 100, 3), np.uint8))  # tall face crop
    assert x.shape == (1, 3, INPUT_SIZE, INPUT_SIZE)
    assert h == INPUT_SIZE and w == INPUT_SIZE // 2  # aspect ratio kept
    assert left == (INPUT_SIZE - w) // 2 and top == 0  # centred


@needs_model
def test_real_face_scores_low(tmp_path):
    from app.pipeline.detectors.image.face_swap import FaceSwapDetector

    res = FaceSwapDetector().run(MediaContext(FIXTURES / "face.jpg", "image", "image/jpeg", tmp_path))
    assert res is not None and res.fake_score < 0.5
    assert (tmp_path / res.heatmap).is_file()


@needs_model
def test_no_face_means_check_does_not_apply(tmp_path):
    from app.pipeline.detectors.image.face_swap import FaceSwapDetector

    res = FaceSwapDetector().run(MediaContext(FIXTURES / "ai_sd.jpg", "image", "image/jpeg", tmp_path))
    assert res is None
