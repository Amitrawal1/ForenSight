from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "forensight",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)
celery_app.conf.update(task_track_started=True, result_expires=3600)

# `celery -A app.core.celery_app` looks for an attribute named `app` or `celery`
app = celery_app
