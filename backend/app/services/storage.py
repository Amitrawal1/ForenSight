"""Save uploads under STORAGE_DIR/uploads with a generated name (never trust the client filename)."""

import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from app.core.config import get_settings

CHUNK = 1024 * 1024


class UploadTooLarge(Exception):
    pass


def save_upload(src: BinaryIO, max_bytes: int) -> Path:
    upload_dir = get_settings().upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / uuid.uuid4().hex

    size = 0
    too_large = False
    with path.open("wb") as out:
        while chunk := src.read(CHUNK):
            size += len(chunk)
            if size > max_bytes:
                too_large = True
                break
            out.write(chunk)
    if too_large:
        path.unlink(missing_ok=True)
        raise UploadTooLarge
    return path


def artifact_dir(analysis_id: str) -> Path:
    return get_settings().artifact_dir / analysis_id


def delete_files(stored_path: str, analysis_id: str) -> None:
    Path(stored_path).unlink(missing_ok=True)
    shutil.rmtree(artifact_dir(analysis_id), ignore_errors=True)
