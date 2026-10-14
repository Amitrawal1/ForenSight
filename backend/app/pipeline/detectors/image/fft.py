"""Frequency check for AI-generated images.

Idea: AI image generators build pictures by enlarging small images step by step.
This leaves a tiny repeating pattern in the image's fine noise that the eye can't see.

FFT (Fast Fourier Transform) turns the image into a "frequency map" (spectrum).
A repeating pattern shows up there as a bright isolated dot.

JPEG files have their own repeating 8x8 block pattern, so for JPEGs we ignore
those spots and trust this check less.

The numbers below were picked by hand. In Phase 6 a small trained model replaces them.
"""

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.pipeline.detectors.base import Detector, DetectorResult, MediaContext

MAX_SIZE = 512  # analyse at most a 512x512 square from the centre
PEAK_Z = 4.0  # how much brighter than its neighbours a dot must be to count
SPECTRUM_NAME = "spectrum.png"


class FftDetector(Detector):
    name = "fft"
    label = "Frequency analysis"
    media_types = ("image",)

    def run(self, ctx: MediaContext) -> DetectorResult | None:
        if ctx.media_type != "image":
            return None

        with Image.open(ctx.path) as img:
            gray = np.asarray(ImageOps.exif_transpose(img).convert("L"))
        h, w = gray.shape
        n = min(h, w, MAX_SIZE) // 8 * 8
        # Skip small images, not enough detail
        if n < 128:
            return None
        top, left = (h - n) // 2, (w - n) // 2
        patch = gray[top : top + n, left : left + n]

        # Remove the picture itself and keep only the fine noise
        residual = patch.astype(np.float32) - cv2.medianBlur(patch, 3).astype(np.float32)
        # Turn the noise into a frequency map (window softens the borders)
        window = np.outer(np.hanning(n), np.hanning(n)).astype(np.float32)
        spectrum = np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(residual * window))))

        c = n // 2
        yy, xx = np.mgrid[:n, :n]
        dy, dx = yy - c, xx - c
        r = np.hypot(dy, dx).astype(int)

        # Compare each spot with other spots at the same distance from the centre.
        # z = how much brighter a spot is than its neighbours.
        counts = np.bincount(r.ravel())
        mean_r = np.bincount(r.ravel(), spectrum.ravel()) / np.maximum(counts, 1)
        sq_r = np.bincount(r.ravel(), (spectrum**2).ravel()) / np.maximum(counts, 1)
        std_r = np.sqrt(np.maximum(sq_r - mean_r**2, 0)) + 1e-3
        z = (spectrum - mean_r[r]) / std_r[r]

        # Ignore the centre (big shapes) and the two axis lines (image borders)
        axes = (np.abs(dy) <= 1) | (np.abs(dx) <= 1)
        valid = (r > n * 0.1) & ~axes & (counts[r] > 3)
        if ctx.mime == "image/jpeg":
            # Ignore spots caused by JPEG's 8x8 blocks. Some AI patterns fall on the
            # same spots, which is why this check is weaker for JPEGs.
            step = n // 8
            valid &= ~(_near_multiple(dy, step) & _near_multiple(dx, step))

        peaks = z[valid]
        max_z = float(peaks.max()) if peaks.size else 0.0
        n_peaks = int((peaks > PEAK_Z).sum())

        _save_spectrum(spectrum, ctx.out_dir / SPECTRUM_NAME)

        # Real repeating patterns always make dots in mirrored pairs, so need at least 2
        if n_peaks >= 2:
            score = min(0.95, 0.7 + 0.1 * (max_z - PEAK_Z))
            reasons = ["The image's fine noise contains a repeating frequency pattern, a trace often left "
                       "by the upsampling layers of AI image generators."]
        else:
            score = 0.3
            reasons = ["No unusual repeating patterns were found in the image's frequency spectrum."]

        reliability = 0.15 if ctx.mime == "image/jpeg" else 0.3
        return DetectorResult(self.name, fake_score=score, reliability=reliability, fake_kind="ai_generated",
                              reasons=reasons, heatmap=SPECTRUM_NAME)


def _near_multiple(d: np.ndarray, step: int, tol: int = 2) -> np.ndarray:
    """True where d is close to a multiple of step."""
    m = np.mod(d, step)
    return (m <= tol) | (m >= step - tol)


def _save_spectrum(spectrum: np.ndarray, path) -> None:
    """Save the frequency map as a coloured image for the result page."""
    lo, hi = np.percentile(spectrum, (1, 99.9))
    img = np.clip((spectrum - lo) / (hi - lo + 1e-6), 0, 1)
    cv2.imwrite(str(path), cv2.applyColorMap((img * 255).astype(np.uint8), cv2.COLORMAP_MAGMA))
