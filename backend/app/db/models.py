import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class MediaType(str, enum.Enum):
    image = "image"
    video = "video"
    audio = "audio"


class Status(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    done = "done"
    failed = "failed"


class Verdict(str, enum.Enum):
    authentic = "likely_authentic"
    ai_generated = "ai_generated"
    manipulated = "manipulated"
    inconclusive = "inconclusive"


class Analysis(Base):
    """One uploaded file and its forensic result (powers the history page)."""

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(512))
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType))
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.queued)
    verdict: Mapped[Verdict | None] = mapped_column(Enum(Verdict), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Per-detector scores, reasons, heatmap paths, timeline segments
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    report_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
