import os
import tempfile
from pathlib import Path

# Must run before `app` is imported: settings are read once and cached.
_tmp = tempfile.mkdtemp(prefix="forensight-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["STORAGE_DIR"] = f"{_tmp}/storage"
os.environ["CELERY_ALWAYS_EAGER"] = "true"
# Use the project models/ folder unless set (Docker sets /models)
os.environ.setdefault("MODELS_DIR", str(Path(__file__).resolve().parents[2] / "models"))
