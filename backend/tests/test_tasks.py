from app.db.models import Analysis, Base, Status
from app.db.session import SessionLocal, engine
from app.workers.tasks import LOST_JOB_MESSAGE, mark_lost


def add_analysis(status: Status) -> str:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        a = Analysis(filename="v.mp4", stored_path="/tmp/v.mp4", media_type="video", mime_type="video/mp4", status=status)
        db.add(a)
        db.commit()
        return a.id


def test_lost_job_is_marked_failed():
    analysis_id = add_analysis(Status.processing)
    mark_lost(analysis_id)
    with SessionLocal() as db:
        a = db.get(Analysis, analysis_id)
        assert a.status == Status.failed and a.error == LOST_JOB_MESSAGE


def test_finished_job_is_left_alone():
    analysis_id = add_analysis(Status.done)
    mark_lost(analysis_id)
    with SessionLocal() as db:
        assert db.get(Analysis, analysis_id).status == Status.done
