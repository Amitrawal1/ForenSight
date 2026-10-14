"""Find faces in an image with OpenCV's YuNet face detector.

YuNet is a tiny (230 KB) model that runs fast on CPU and needs no PyTorch.
"""

from dataclasses import dataclass

import cv2
import numpy as np

from app.pipeline.models.registry import load_cached, model_path

YUNET_FILE = "face_detection_yunet_2023mar.onnx"
MAX_SIDE = 1280  # shrink big images first; faces are still found and it is much faster


@dataclass
class Face:
    # Box in pixels of the original image
    x: int
    y: int
    w: int
    h: int
    score: float  # how sure the detector is that this is a face (0..1)


def detect_faces(rgb: np.ndarray, min_score: float = 0.8) -> list[Face]:
    """Return all faces found in an RGB image, biggest first."""
    h, w = rgb.shape[:2]
    scale = min(1.0, MAX_SIDE / max(h, w))
    small = cv2.resize(rgb, (round(w * scale), round(h * scale))) if scale < 1 else rgb

    detector = load_cached("yunet", lambda: cv2.FaceDetectorYN.create(str(model_path(YUNET_FILE)), "", (320, 320)))
    detector.setScoreThreshold(min_score)
    detector.setInputSize((small.shape[1], small.shape[0]))
    _, found = detector.detect(cv2.cvtColor(small, cv2.COLOR_RGB2BGR))
    if found is None:
        return []

    faces = []
    for row in found:
        # Each row: x, y, w, h, 10 landmark numbers, score. Scale the box back up.
        x, y, fw, fh = (row[:4] / scale).round().astype(int)
        faces.append(Face(int(x), int(y), int(fw), int(fh), float(row[-1])))
    faces.sort(key=lambda f: f.w * f.h, reverse=True)
    return faces


def crop_face(rgb: np.ndarray, face: Face, margin: float = 0.3) -> np.ndarray:
    """Cut out a square around the face, with extra space around it (margin = 30% of face size).

    Deepfake traces are often at the face edges (jaw, hairline), so we keep some border.
    """
    h, w = rgb.shape[:2]
    side = int(max(face.w, face.h) * (1 + 2 * margin))
    cx, cy = face.x + face.w // 2, face.y + face.h // 2
    x0, y0 = max(0, cx - side // 2), max(0, cy - side // 2)
    x1, y1 = min(w, x0 + side), min(h, y0 + side)
    return rgb[y0:y1, x0:x1]
