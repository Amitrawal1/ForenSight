import io

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo


def photo_like(size=256, seed=0) -> np.ndarray:
    """Smooth gradients + noise: a stand-in for a natural photo."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[:size, :size]
    base = np.stack([128 + 60 * np.sin(xx / 23), 128 + 60 * np.cos(yy / 31), 128 + 40 * np.sin((xx + yy) / 41)], -1)
    return np.clip(base + rng.normal(0, 6, base.shape), 0, 255).astype(np.uint8)


def jpeg_bytes(arr, quality=92, exif=None) -> bytes:
    buf = io.BytesIO()
    img = Image.fromarray(arr)
    img.save(buf, "JPEG", quality=quality, **({"exif": exif} if exif is not None else {}))
    return buf.getvalue()


def png_bytes(arr, text: dict | None = None) -> bytes:
    buf = io.BytesIO()
    info = PngInfo()
    for k, v in (text or {}).items():
        info.add_text(k, v)
    Image.fromarray(arr).save(buf, "PNG", pnginfo=info)
    return buf.getvalue()


def wav_bytes(seconds: float = 3.0, freq: float = 220.0, sr: int = 16000, amplitude: float = 0.3) -> bytes:
    """A simple tone saved as a 16-bit WAV file (no ffmpeg needed to create it)."""
    import wave

    t = np.arange(int(seconds * sr)) / sr
    samples = (amplitude * np.sin(2 * np.pi * freq * t) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(samples.tobytes())
    return buf.getvalue()
