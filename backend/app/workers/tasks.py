import logging
from pathlib import Path

from celery.signals import task_failure

from app.core.celery_app import celery_app
from app.db.models import Analysis, Status, Verdict
from app.db.session import SessionLocal
from app.pipeline.runner import analyse
from app.services.storage import artifact_dir

log = logging.getLogger(__name__)

LOST_JOB_MESSAGE = "The analysis stopped unexpectedly, possibly because the server ran out of memory. Please try again."


def mark_lost(analysis_id: str) -> None:
    """Mark a job as failed if its process died, so the page does not wait forever."""
    with SessionLocal() as db:
        a = db.get(Analysis, analysis_id)
        if a is not None and a.status in (Status.queued, Status.processing):
            a.status = Status.failed
            a.error = LOST_JOB_MESSAGE
            db.commit()


@task_failure.connect
def on_task_failure(sender=None, args=None, **_):
    # Runs in Celery's main process, which survives when the job's process is killed
    if sender is not None and sender.name == "forensight.run_analysis" and args:
        mark_lost(args[0])


@celery_app.task(name="forensight.run_analysis")
def run_analysis(analysis_id: str) -> str:
    with SessionLocal() as db:
        a = db.get(Analysis, analysis_id)
        if a is None:
            return analysis_id
        a.status = Status.processing
        db.commit()

        try:
            out = analyse(Path(a.stored_path), a.media_type.value, a.mime_type, artifact_dir(a.id))
            a.verdict = Verdict(out.verdict)
            a.confidence = out.confidence
            a.evidence = out.evidence()
            a.thumbnail_path = out.thumbnail
            a.status = Status.done
        except Exception as e:
            log.exception("analysis %s failed", analysis_id)
            a.status = Status.failed
            a.error = f"{type(e).__name__}: {e}"[:500]
        db.commit()
    return analysis_id
