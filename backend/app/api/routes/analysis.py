import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Analysis
from app.db.session import get_db
from app.pipeline.preprocessing import file_type
from app.schemas.analysis import AnalysisOut, AnalysisSummary
from app.services.storage import UploadTooLarge, artifact_dir, delete_files, save_upload
from app.workers.tasks import run_analysis

router = APIRouter(prefix="/analyses", tags=["analysis"])

ARTIFACT_NAME = re.compile(r"^[a-z0-9_]+\.(png|jpg)$")


def _get_or_404(db: Session, analysis_id: str) -> Analysis:
    a = db.get(Analysis, analysis_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return a


@router.post("", status_code=201, response_model=AnalysisOut)
def create_analysis(file: UploadFile = File(...), db: Session = Depends(get_db)):
    settings = get_settings()
    try:
        path = save_upload(file.file, settings.max_upload_mb * 1024 * 1024)
    except UploadTooLarge:
        raise HTTPException(status_code=413, detail=f"File is larger than {settings.max_upload_mb} MB")

    detected = file_type.detect(path)
    if detected is None:
        path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Use JPG, PNG, WEBP, MP4, MOV, AVI, WAV, MP3 or M4A.",
        )
    media_type, mime = detected

    a = Analysis(
        filename=Path(file.filename or "upload").name[:255],
        stored_path=str(path),
        media_type=media_type,
        mime_type=mime,
    )
    db.add(a)
    db.commit()

    run_analysis.delay(a.id)
    db.refresh(a)  # in eager mode (tests) the task has already finished
    return a


@router.get("", response_model=list[AnalysisSummary])
def list_analyses(limit: int = 50, db: Session = Depends(get_db)):
    stmt = select(Analysis).order_by(Analysis.created_at.desc()).limit(min(limit, 200))
    return db.scalars(stmt).all()


@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    return _get_or_404(db, analysis_id)


@router.get("/{analysis_id}/original")
def get_original(analysis_id: str, db: Session = Depends(get_db)):
    a = _get_or_404(db, analysis_id)
    return FileResponse(a.stored_path, media_type=a.mime_type)


@router.get("/{analysis_id}/artifacts/{name}")
def get_artifact(analysis_id: str, name: str, db: Session = Depends(get_db)):
    a = _get_or_404(db, analysis_id)
    path = artifact_dir(a.id) / name
    if not ARTIFACT_NAME.match(name) or not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path)


@router.delete("/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: str, db: Session = Depends(get_db)):
    a = _get_or_404(db, analysis_id)
    delete_files(a.stored_path, a.id)
    db.delete(a)
    db.commit()
    return Response(status_code=204)
