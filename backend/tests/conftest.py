import os
import tempfile

# Must run before `app` is imported: settings are read once and cached.
_tmp = tempfile.mkdtemp(prefix="forensight-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["STORAGE_DIR"] = f"{_tmp}/storage"
os.environ["CELERY_ALWAYS_EAGER"] = "true"
