from pathlib import Path

from PIL import Image, ImageOps

THUMB_NAME = "thumb.jpg"
ORIENTATION_TAG = 0x0112


def image_size(src: Path) -> tuple[int, int]:
    """(width, height) as the image is shown. Reads only the file header, not the pixels."""
    with Image.open(src) as img:
        width, height = img.size
        # EXIF is photo info inside the file; orientations 5-8 mean the photo is shown turned sideways
        if img.getexif().get(ORIENTATION_TAG) in (5, 6, 7, 8):
            return height, width
    return width, height


def make_image_thumbnail(src: Path, out_dir: Path, size: int = 256) -> str:
    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((size, size))
        img.save(out_dir / THUMB_NAME, "JPEG", quality=85)
    return THUMB_NAME
