"""Face-swap detector: is a face in the image swapped or altered?

Uses the model that won Facebook's Deepfake Detection Challenge (DFDC, 2020):
EfficientNet-B7 by Selim Seferbekov, MIT licence. The original solution averaged
7 models; we use 1 to keep it fast enough on a normal CPU.

Steps for each face:
1. Find faces with YuNet (preprocessing/faces.py).
2. Cut out the face plus 1/3 extra space on each side, as in the original code.
3. Resize to fit 380x380, ask the model for a "fake" chance.
4. For suspicious faces, make a Grad-CAM heatmap showing where the model looked.
"""

import re

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.pipeline.detectors.base import Detector, DetectorResult, MediaContext
from app.pipeline.explain.gradcam import grad_cam
from app.pipeline.explain.heatmap import make_overlay, region_name
from app.pipeline.models.registry import load_cached, model_path, require_torch
from app.pipeline.preprocessing.faces import Face, detect_faces

MODEL_FILE = "dfdc_efficientnet_b7.pt"
INPUT_SIZE = 380
MAX_FACES = 3  # each face takes about a second on CPU
MIN_FACE_PX = 64  # smaller faces have too little detail to judge well
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)  # standard ImageNet colours
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
HEATMAP_NAME = "faces.png"

# Trusted less than the AI-image model: face-swap detectors are known to work worse
# on videos/photos from sources they were not trained on.
RELIABILITY = 0.5


def _load_model():
    require_torch()
    import timm
    import torch
    from numpy._core.multiarray import scalar

    path = model_path(MODEL_FILE)

    class DeepFakeClassifier(torch.nn.Module):
        """Same layout as the original DFDC code, so the saved weights fit exactly."""

        def __init__(self):
            super().__init__()
            self.encoder = timm.create_model("tf_efficientnet_b7.ns_jft_in1k", pretrained=False)
            self.avg_pool = torch.nn.AdaptiveAvgPool2d((1, 1))
            self.dropout = torch.nn.Dropout(0.0)
            self.fc = torch.nn.Linear(2560, 1)

        def forward(self, x):
            x = self.encoder.forward_features(x)
            x = self.avg_pool(x).flatten(1)
            return self.fc(self.dropout(x))

    # Safe loading: only plain weights are allowed. The file also stores one numpy
    # number (a training score), so we allow exactly that type and nothing else.
    allowed = [(scalar, "numpy.core.multiarray.scalar"), np.dtype, np.dtypes.Float64DType]
    with torch.serialization.safe_globals(allowed):
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    state = {re.sub(r"^module\.", "", k): v for k, v in checkpoint["state_dict"].items()}

    model = DeepFakeClassifier()
    model.load_state_dict(state, strict=True)
    model.eval()
    return model


def face_box(rgb: np.ndarray, face: Face) -> tuple[int, int, int, int]:
    """Face area plus 1/3 of its size on each side (same as the original DFDC code)."""
    h, w = rgb.shape[:2]
    pad_w, pad_h = face.w // 3, face.h // 3
    x0, y0 = max(face.x - pad_w, 0), max(face.y - pad_h, 0)
    x1, y1 = min(face.x + face.w + pad_w, w), min(face.y + face.h + pad_h, h)
    return x0, y0, x1, y1


def prepare(crop: np.ndarray) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """Resize the face so its longest side is 380, put it in the middle of a black
    380x380 square, and normalise colours.

    Returns the model input (1x3x380x380) and where the face sits inside the square
    (x, y, width, height), so we can map the heatmap back onto the photo.
    """
    h, w = crop.shape[:2]
    scale = INPUT_SIZE / max(h, w)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    resized = cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)

    square = np.zeros((INPUT_SIZE, INPUT_SIZE, 3), dtype=np.uint8)
    left, top = (INPUT_SIZE - nw) // 2, (INPUT_SIZE - nh) // 2
    square[top : top + nh, left : left + nw] = resized

    arr = (square.astype(np.float32) / 255.0 - MEAN) / STD
    return arr.transpose(2, 0, 1)[None], (left, top, nw, nh)


def face_part(cam: np.ndarray) -> str:
    """Name the part of the face where the heatmap is strongest."""
    row = np.unravel_index(np.argmax(cam), cam.shape)[0] / cam.shape[0]
    if row < 0.4:
        return "eyes and forehead"
    if row < 0.65:
        return "nose and cheeks"
    return "mouth and jaw"


class FaceSwapDetector(Detector):
    name = "face_swap"
    label = "Face-swap model"
    media_types = ("image",)

    def run(self, ctx: MediaContext) -> DetectorResult | None:
        import torch

        with Image.open(ctx.path) as img:
            rgb = np.asarray(ImageOps.exif_transpose(img).convert("RGB"))
        faces = [f for f in detect_faces(rgb) if min(f.w, f.h) >= MIN_FACE_PX][:MAX_FACES]
        if not faces:
            return None  # no face big enough: this check does not apply

        model = load_cached("dfdc_b7", _load_model)
        img_h, img_w = rgb.shape[:2]
        heat = np.zeros((img_h, img_w), dtype=np.float32)
        overlay_boxes = []
        reasons, probs = [], []

        for i, face in enumerate(faces, start=1):
            x0, y0, x1, y1 = face_box(rgb, face)
            x, (left, top, nw, nh) = prepare(rgb[y0:y1, x0:x1])
            tensor = torch.from_numpy(x)

            with torch.no_grad():
                prob = float(torch.sigmoid(model(tensor)[0, 0]))
            probs.append(prob)
            where = region_name(face.y + face.h / 2, face.x + face.w / 2, img_h, img_w)
            label = f"Face {i} ({where})" if len(faces) > 1 else "The face"

            if prob >= 0.5:
                # Where did the model look? Map the heatmap from the 380x380 square
                # back to the face area of the original photo.
                cam = grad_cam(lambda t: model(t)[0, 0], model.encoder.bn2, tensor)
                cam = cv2.resize(cam, (INPUT_SIZE, INPUT_SIZE))[top : top + nh, left : left + nw]
                cam = cv2.resize(cam, (x1 - x0, y1 - y0))
                heat[y0:y1, x0:x1] = np.maximum(heat[y0:y1, x0:x1], cam)
                reasons.append(f"{label} looks {round(prob * 100)}% likely to be swapped or altered; "
                               f"the model focused most on the {face_part(cam)}.")
            overlay_boxes.append((x0, y0, x1, y1, prob))

        # Picture for the result page: heatmap + a box around each face (red = suspicious)
        out = make_overlay(rgb, heat)
        for x0, y0, x1, y1, prob in overlay_boxes:
            color = (0, 0, 230) if prob >= 0.5 else (60, 200, 60)  # BGR
            cv2.rectangle(out, (x0, y0), (x1, y1), color, max(2, img_w // 300))
        cv2.imwrite(str(ctx.out_dir / HEATMAP_NAME), out)

        top_prob = max(probs)
        if not reasons:
            count = f"{len(faces)} faces were" if len(faces) > 1 else "The face was"
            reasons.append(f"{count} checked for face swapping; none looks altered "
                           f"(highest {round(top_prob * 100)}%).")
        reasons.append("Face-swap detection is less reliable on photos unlike its training videos, "
                       "so treat this as one clue among several.")

        return DetectorResult(self.name, fake_score=top_prob, reliability=RELIABILITY,
                              fake_kind="manipulated", reasons=reasons, heatmap=HEATMAP_NAME)
