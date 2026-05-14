from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "careeros",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Berlin",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600, # 1 hour max per task
)

# Autodiscover tasks from agents module
celery_app.autodiscover_tasks(["app.agents"])
