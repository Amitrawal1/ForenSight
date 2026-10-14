"""Error Level Analysis (ELA) for JPEG images.

Idea: save the JPEG again and see how much each part of the picture changes.
If someone pasted or edited a part of the image, that part usually changes
differently from the rest, so it stands out.

Detailed areas (hair, grass, edges) always change more, so we take that into
account before deciding something looks odd.

The numbers below were picked by hand. We will tune them in Phase 6 with real data.
"""

import io

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.pipeline.detectors.base import Detector, DetectorResult, MediaContext
from app.pipeline.explain.heatmap import region_name, save_overlay

BLOCK = 16  # we look at the image in 16x16 pixel squares
RESAVE_QUALITY = 90  # JPEG quality used when saving again
OUTLIER_Z = 4.0  # how unusual a square must be to count as suspicious
MIN_CLUSTER_BLOCKS = 4  # need at least this many suspicious squares together
HEATMAP_NAME = "ela.png"


class ElaDetector(Detector):
    name = "ela"
    label = "Error Level Analysis"
    media_types = ("image",)

    def run(self, ctx: MediaContext) -> DetectorResult | None:
        if ctx.mime != "image/jpeg":
            return None

        with Image.open(ctx.path) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
        rgb = np.asarray(img)
        h, w = rgb.shape[:2]
        # Skip tiny images, too small to analyse
        if min(h, w) < 4 * BLOCK:
            return None

        # Save again and measure how much each pixel changed
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=RESAVE_QUALITY)
        resaved = np.asarray(Image.open(buf).convert("RGB"))
        err = np.abs(rgb.astype(np.int16) - resaved.astype(np.int16)).max(axis=2).astype(np.float32)

        # How detailed each area is (strength of edges)
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
        grad = np.hypot(cv2.Sobel(gray, cv2.CV_32F, 1, 0), cv2.Sobel(gray, cv2.CV_32F, 0, 1))

        bh, bw = h // BLOCK, w // BLOCK
        err_b = _block_mean(err, bh, bw)
        grad_b = _block_mean(grad, bh, bw)

        # Change per square, adjusted for how detailed the square is
        norm = err_b / (grad_b + np.median(grad_b) + 1.0)
        med = np.median(norm)
        # z = how far each square is from a typical square (bigger = more unusual)
        spread = np.median(np.abs(norm - med)) * 1.4826 + 1e-6
        z = (norm - med) / spread

        # Find the biggest group of suspicious squares that touch each other
        mask = (z > OUTLIER_Z).astype(np.uint8)
        n, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
        if n > 1:
            biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            cluster = int(stats[biggest, cv2.CC_STAT_AREA])
            cx, cy = centroids[biggest]
        else:
            cluster, cx, cy = 0, 0.0, 0.0
        fraction = cluster / mask.size

        # Images saved many times (e.g. WhatsApp forwards) barely change, so trust this check less
        reliability = 0.35 if float(np.median(err_b)) >= 0.5 else 0.15

        # A group of odd squares (but not half the image) suggests an edited region
        heatmap = None
        if cluster >= MIN_CLUSTER_BLOCKS and fraction < 0.5:
            # Only save a heatmap when there is something to show
            save_overlay(rgb, z / (2 * OUTLIER_Z), ctx.out_dir / HEATMAP_NAME)
            heatmap = HEATMAP_NAME
            score = 0.5 + 0.5 * min(1.0, cluster / 30)
            where = region_name(cy * BLOCK, cx * BLOCK, h, w)
            reasons = [f"A region in the {where} of the image recompresses differently from the rest, "
                       "which can happen when part of an image is pasted in or edited."]
        else:
            score = 0.2
            # "Found nothing" is weak evidence (the edit may just be invisible to ELA),
            # so it counts less than a real finding
            reliability = min(reliability, 0.15)
            reasons = ["Compression error is consistent across the image; no edited region stands out."]
        if float(np.median(err_b)) < 0.5:
            reasons.append("The image looks heavily recompressed, so this check is less reliable.")

        return DetectorResult(self.name, fake_score=score, reliability=reliability,
                              fake_kind="manipulated", reasons=reasons, heatmap=heatmap)


def _block_mean(a: np.ndarray, bh: int, bw: int) -> np.ndarray:
    """Average value of each 16x16 square."""
    return a[: bh * BLOCK, : bw * BLOCK].reshape(bh, BLOCK, bw, BLOCK).mean(axis=(1, 3))
