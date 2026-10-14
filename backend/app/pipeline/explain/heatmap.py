from pathlib import Path

import cv2
import numpy as np


def make_overlay(rgb: np.ndarray, intensity: np.ndarray, alpha: float = 0.5) -> np.ndarray:
    """Colour the image blue (normal) to red (suspicious) using values from 0 to 1.

    Returns a BGR image (OpenCV colour order), ready to draw on or save.
    """
    h, w = rgb.shape[:2]
    heat = cv2.resize(np.clip(intensity, 0, 1).astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    colored = cv2.applyColorMap((heat * 255).astype(np.uint8), cv2.COLORMAP_JET)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    # Only colour suspicious areas, so normal areas keep their original look
    weight = (alpha * heat)[..., None]
    return (bgr * (1 - weight) + colored * weight).astype(np.uint8)


def save_overlay(rgb: np.ndarray, intensity: np.ndarray, out_path: Path, alpha: float = 0.5) -> None:
    """Same as make_overlay, but saves the result to a file."""
    cv2.imwrite(str(out_path), make_overlay(rgb, intensity, alpha))


def region_name(cy: float, cx: float, h: int, w: int) -> str:
    """Human description of where a point lies in a 3x3 grid ('upper left', 'centre', ...)."""
    rows = ("upper", "middle", "lower")
    cols = ("left", "centre", "right")
    r = rows[min(int(3 * cy / h), 2)]
    c = cols[min(int(3 * cx / w), 2)]
    if r == "middle" and c == "centre":
        return "centre"
    if r == "middle":
        return f"{c} side"
    return f"{r} {c}" if c != "centre" else f"{r} centre"
