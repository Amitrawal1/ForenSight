"""Load ML models once per worker process and reuse them.

Loading a model can take seconds, so we keep each one in memory after the
first use instead of loading it again for every file.
"""

import threading
from pathlib import Path
from typing import Any, Callable

from app.core.config import get_settings

_cache: dict[str, Any] = {}
_lock = threading.Lock()


class ModelNotAvailable(Exception):
    """A model file or ML library is missing. The check is skipped, not failed."""


def load_cached(key: str, loader: Callable[[], Any]) -> Any:
    """Return the model saved under `key`, loading it with `loader()` the first time."""
    with _lock:
        if key not in _cache:
            _cache[key] = loader()
        return _cache[key]


def model_path(filename: str) -> Path:
    """Full path of a model file in the models folder, or ModelNotAvailable if missing."""
    path = get_settings().models_dir / filename
    if not path.is_file():
        raise ModelNotAvailable(
            f"model file '{filename}' is missing. Run: python backend/scripts/download_models.py"
        )
    return path


def require_torch() -> None:
    """Make sure PyTorch is installed (it is optional to keep the default image small)."""
    try:
        import torch  # noqa: F401
    except ImportError:
        raise ModelNotAvailable("PyTorch is not installed. Set INSTALL_ML=true in .env and rebuild.")
