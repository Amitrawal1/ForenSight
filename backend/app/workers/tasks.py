from app.core.celery_app import celery_app


@celery_app.task(name="forensight.run_analysis")
def run_analysis(analysis_id: str) -> str:
    # Phase 1: load Analysis row -> preprocess -> run detectors -> fusion.combine
    # -> explanations -> save evidence/verdict -> generate PDF.
    return analysis_id
