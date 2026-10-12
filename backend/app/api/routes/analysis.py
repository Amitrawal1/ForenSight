from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/analyses", tags=["analysis"])


@router.post("")
def create_analysis():
    # Phase 1: accept UploadFile, save via services.storage, insert Analysis row,
    # enqueue workers.tasks.run_analysis, return the id.
    raise HTTPException(status_code=501, detail="Upload not implemented yet (Phase 1)")


@router.get("/{analysis_id}")
def get_analysis(analysis_id: str):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 1)")
