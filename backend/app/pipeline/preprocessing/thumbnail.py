from pathlib import Path

from PIL import Image, ImageOps

THUMB_NAME = "thumb.jpg"


def make_image_thumbnail(src: Path, out_dir: Path, size: int = 256) -> str:
    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((size, size))
        img.save(out_dir / THUMB_NAME, "JPEG", quality=85)
    return THUMB_NAME
