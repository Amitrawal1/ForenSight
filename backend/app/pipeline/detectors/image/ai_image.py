"""AI-generated image detector (learned model).

Uses the Community Forensics ViT model (CVPR 2025, MIT licence). It was trained on
2.7 million images from about 4,800 different AI image generators, so it should
work on many generators it has never seen.

The model gives one number; we turn it into a "chance this is AI-generated" (0..1).
Files come from backend/scripts/download_models.py (pinned version, checked by SHA-256).
"""

import numpy as np
from PIL import Image, ImageOps

from app.pipeline.detectors.base import Detector, DetectorResult, MediaContext
from app.pipeline.models.registry import load_cached, model_path, require_torch

MODEL_DIR = "community_forensics_vit"

# Image preparation, copied from the model card:
# resize so the short side is 440 px, cut out the 384x384 centre, then normalise colours
SHORT_SIDE = 440
CROP = 384
MEAN = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
STD = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)

# How much fusion trusts this check. Highest of all image checks, but not 1.0:
# no detector catches every new generator.
RELIABILITY = 0.7


def prepare(img: Image.Image) -> np.ndarray:
    """Turn a PIL image into the 1x3x384x384 array the model expects."""
    img = img.convert("RGB")
    w, h = img.size
    scale = SHORT_SIDE / min(w, h)
    img = img.resize((max(CROP, round(w * scale)), max(CROP, round(h * scale))), Image.BICUBIC)
    left, top = (img.width - CROP) // 2, (img.height - CROP) // 2
    img = img.crop((left, top, left + CROP, top + CROP))

    arr = (np.asarray(img, dtype=np.float32) / 255.0 - MEAN) / STD
    return arr.transpose(2, 0, 1)[None]  # HWC -> 1xCxHxW


def _load_model():
    require_torch()
    from transformers import ViTForImageClassification

    # model_path() checks the files exist and gives a clear message if not
    model_path(f"{MODEL_DIR}/model.safetensors")
    folder = model_path(f"{MODEL_DIR}/config.json").parent
    model = ViTForImageClassification.from_pretrained(folder)
    model.eval()
    return model


def fake_probability(img: Image.Image) -> float:
    """Chance (0..1) that the image is AI-generated, according to the model."""
    import torch

    model = load_cached("community_forensics_vit", _load_model)
    with torch.no_grad():
        logit = model(pixel_values=torch.from_numpy(prepare(img))).logits[0, 0]
    return float(torch.sigmoid(logit))


class AiImageDetector(Detector):
    name = "ai_image"
    label = "AI-image model"
    media_types = ("image",)

    def run(self, ctx: MediaContext) -> DetectorResult | None:
        with Image.open(ctx.path) as img:
            img = ImageOps.exif_transpose(img)
            prob = fake_probability(img)

        pct = round(prob * 100)
        if prob >= 0.65:
            reason = (f"A model trained on images from about 4,800 AI generators rates this image "
                      f"{pct}% likely to be AI-generated.")
        elif prob <= 0.35:
            reason = (f"A model trained on images from about 4,800 AI generators finds no strong sign of "
                      f"AI generation ({pct}% AI likelihood).")
        else:
            reason = f"The AI-image model is unsure about this image ({pct}% AI likelihood)."

        return DetectorResult(self.name, fake_score=prob, reliability=RELIABILITY,
                              fake_kind="ai_generated", reasons=[reason])
