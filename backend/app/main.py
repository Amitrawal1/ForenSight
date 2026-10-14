from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analysis, health
from app.core.config import get_settings
from app.db import models  # noqa: F401  (registers tables)
from app.db.session import Base, engine

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.report_dir.mkdir(parents=True, exist_ok=True)
    settings.artifact_dir.mkdir(parents=True, exist_ok=True)
    # TODO: switch to Alembic migrations once the schema settles
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="ForenSight API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
