from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.core.config import get_settings
from app.pipeline.preprocessing.faces import YUNET_FILE, crop_face, detect_faces

FIXTURE = Path(__file__).parent / "fixtures" / "face.jpg"

# Face model is downloaded with backend/scripts/download_models.py
needs_model = pytest.mark.skipif(
    not (get_settings().models_dir / YUNET_FILE).is_file(), reason="face model not downloaded"
)


@needs_model
def test_finds_the_face():
    rgb = np.asarray(Image.open(FIXTURE).convert("RGB"))
    faces = detect_faces(rgb)
    assert len(faces) == 1
    crop = crop_face(rgb, faces[0])
    # Crop is bigger than the face box because of the margin
    assert crop.shape[0] > faces[0].h and crop.shape[1] > faces[0].w


@needs_model
def test_no_face_in_plain_image():
    assert detect_faces(np.full((200, 200, 3), 128, np.uint8)) == []
