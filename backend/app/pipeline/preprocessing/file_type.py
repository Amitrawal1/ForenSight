"""Detect media type from the file's bytes (magic numbers), never from the extension."""

from pathlib import Path

import filetype

ALLOWED = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
    "video/mp4": "video",
    "video/quicktime": "video",
    "video/x-msvideo": "video",
    "audio/x-wav": "audio",
    "audio/mpeg": "audio",
    "audio/mp4": "audio",  # m4a
}


def detect(path: Path) -> tuple[str, str] | None:
    """Return (media_type, mime) or None if the file is not a supported type."""
    kind = filetype.guess(str(path))
    if kind is None or kind.mime not in ALLOWED:
        return None
    return ALLOWED[kind.mime], kind.mime
