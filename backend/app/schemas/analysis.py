from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import MediaType, Status, Verdict


class AnalysisSummary(BaseModel):
    """Row in the history list."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    media_type: MediaType
    status: Status
    verdict: Verdict | None
    confidence: float | None
    thumbnail_path: str | None
    created_at: datetime | None


class AnalysisOut(AnalysisSummary):
    mime_type: str
    evidence: dict | None
    error: str | None
