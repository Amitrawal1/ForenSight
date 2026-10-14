from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./forensight.db"
    redis_url: str = "redis://localhost:6379/0"
    storage_dir: Path = Path("./storage")
    models_dir: Path = Path("./models")
    max_upload_mb: int = 200
    cors_origins: str = "http://localhost:5173"
    # Run Celery tasks inline (tests / no Redis)
    celery_always_eager: bool = False

    @property
    def upload_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def report_dir(self) -> Path:
        return self.storage_dir / "reports"

    @property
    def artifact_dir(self) -> Path:
        """Heatmaps, spectra and thumbnails, one sub-folder per analysis."""
        return self.storage_dir / "artifacts"


@lru_cache
def get_settings() -> Settings:
    return Settings()
